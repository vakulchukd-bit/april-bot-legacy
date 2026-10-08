"""APRIL single provider for the canonical WebReal Web route.

The provider receives an already-normalized English request from bot.ru/Exkrutor.
Bot.ru owns the input translation boundary. The provider performs reasoning and
returns the answer in the requested display language. No second chat route exists.
"""
from __future__ import annotations

from typing import Any
import asyncio
import hashlib
import json
import os
import re
import time

from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse


MODEL = os.getenv("APRIL_OPENAI_MODEL", "gpt-5.6-luna")
MAX_OUTPUT_TOKENS = min(
    8000,
    max(256, int(os.getenv("APRIL_MAX_OUTPUT_TOKENS", "2400") or 2400)),
)
INPUT_TOKEN_TARGET = 900
TRANSLATION_ROUTE_VERSION = "botru_embedded_translation_v1"

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_inflight: set[str] = set()
_client: _OpenAICompat | None = None


SYSTEM_PROMPT = r"""
You are April's single response provider in the canonical route.

The processor is authoritative.  It already performed:
- input normalization;
- authenticated identity binding;
- 12-hour dialogue search and compatibility ranking;
- NEW/CONTINUE decision;
- Interpretation structure;
- C-ARTIFACT room and Web renderer selection.

Do not create another route, memory store, interpreter, room registry, or user identity.
Do not expose internal reasoning.

Always treat these sections as structured input:
1. CURRENT_REQUEST
2. CONTINUATION_CONTEXT (empty when NEW)
3. NEW_DIALOGUE_REQUEST (empty when CONTINUE)
4. INPUT_MODALITIES / VISUAL_CONTEXT
5. C_ARTIFACT_RENDER_PLAN
6. MCDOWELL_PRESENTATION_POLICY

For CONTINUE, continue the selected subject and do not repeat questions already answered.
For NEW, answer independently and do not let old context override the request.
For an input image/screenshot, inspect the supplied image and use it as part of the answer when relevant.
For an attached file, read the supplied input_file content and answer from the file itself when relevant; do not claim the file is missing when an input_file is present.
Text supplied together with an image or file is the user's instruction for that same attachment; do not split it into a second request.
For a requested image, return an image artifact specification for C_APRIL_IMAGES_GENERATOR; do not create the raster yourself.
For links/files/tables/diagrams/formulas/code, return the structured render block required by C-ARTIFACT.

Return JSON only:
{
  "internal_request_en": "...",
  "internal_answer_en": "...",
  "answer": "complete human-readable answer in RETURN_LANGUAGE",
  "content": "same answer or concise equivalent",
  "summary": "one-sentence summary",
  "render_blocks": [
    {
      "type": "text",
      "renderer": "MessageTextBlock",
      "viewer": "MessageTextBlock",
      "content": "..."
    }
  ],
  "artifacts": []
}

For an image request, artifacts must contain:
{
  "type": "image",
  "spec": {
    "schema": "april_image_spec_v1",
    "generator_signal": "C_APRIL_IMAGES_GENERATOR",
    "request_anchor": "...",
    "openai_structured_visual_plan_semantic": "...",
    "visual_context": {}
  }
}

Never return an empty answer.
Never put machine metadata into answer/content.
""".strip()



class _ResponseResult:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload
        self.output_text = self._extract_output_text(payload)
        self.usage = _Usage(payload.get("usage") or {})

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        chunks: list[str] = []
        for item in payload.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                value = content.get("text")
                if isinstance(value, str) and value.strip():
                    chunks.append(value)
        return "\n".join(chunks).strip()


class _Usage:
    def __init__(self, data: dict[str, Any]):
        self.input_tokens = int(data.get("input_tokens", 0) or 0)
        self.output_tokens = int(data.get("output_tokens", 0) or 0)
        self.total_tokens = int(data.get("total_tokens", 0) or 0)


class _ResponsesCompat:
    def __init__(self, client: "_OpenAICompat"):
        self._client = client

    def create(
        self,
        *,
        model: str,
        input: Any,
        max_output_tokens: int,
    ) -> _ResponseResult:
        payload = {
            "model": model,
            "input": input,
            "max_output_tokens": max_output_tokens,
        }
        return _ResponseResult(
            self._client._post_json("/v1/responses", payload)
        )


class _TranscriptionsCompat:
    def __init__(self, client: "_OpenAICompat"):
        self._client = client

    def create(self, *, model: str, file: Any) -> Any:
        data = file.read()
        name = os.path.basename(getattr(file, "name", "audio.bin")) or "audio.bin"
        payload = self._client._post_multipart(
            "/v1/audio/transcriptions",
            fields={"model": model},
            file_field=("file", name, "application/octet-stream", data),
        )
        return type(
            "TranscriptionResult",
            (),
            {"text": payload.get("text", "")},
        )()


class _AudioCompat:
    def __init__(self, client: "_OpenAICompat"):
        self.transcriptions = _TranscriptionsCompat(client)


class _OpenAICompat:
    """Small stdlib-only OpenAI HTTP client."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.responses = _ResponsesCompat(self)
        self.audio = _AudioCompat(self)

    def _request(
        self,
        path: str,
        body: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen

        req = Request(
            "https://api.openai.com" + path,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": content_type,
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OPENAI_HTTP_{exc.code}: {detail[:1000]}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"OPENAI_NETWORK_ERROR: {exc.reason}"
            ) from exc

        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise RuntimeError("OPENAI_INVALID_JSON_RESPONSE") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("OPENAI_INVALID_RESPONSE")
        if payload.get("error"):
            raise RuntimeError(
                f"OPENAI_API_ERROR: {payload['error']}"
            )
        return payload

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            path,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json",
        )

    def _post_multipart(
        self,
        path: str,
        *,
        fields: dict[str, str],
        file_field: tuple[str, str, str, bytes],
    ) -> dict[str, Any]:
        import uuid

        boundary = "----AprilBoundary" + uuid.uuid4().hex
        chunks: list[bytes] = []

        for key, value in fields.items():
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    (
                        f'Content-Disposition: form-data; name="{key}"'
                        "\r\n\r\n"
                    ).encode(),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )

        field_name, filename, content_type, data = file_field
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{filename}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                data,
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        return self._request(
            path,
            b"".join(chunks),
            f"multipart/form-data; boundary={boundary}",
        )


def _client_get() -> _OpenAICompat:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
        _client = _OpenAICompat(key)
    return _client


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _json_load(raw: str) -> dict[str, Any]:
    raw = _text(raw)
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {}


def _request_key(req: MachineRequest) -> str:
    raw = json.dumps(
        {
            "user_id": req.fiber.identity.user_id,
            "conversation": req.conversation,
            "intent": req.intent,
            "text": req.conversation.get("current_request") or req.goal,
            "memory": req.memory,
            "routing": req.routing,
            "constraints": req.constraints,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _clip(value: Any, chars: int) -> str:
    text = _text(value)
    if len(text) <= chars:
        return text
    return text[: chars - 1].rstrip() + "…"


def _build_input(req: MachineRequest) -> list[dict[str, Any]]:
    intent = req.intent if isinstance(req.intent, dict) else {}
    conversation = req.conversation if isinstance(req.conversation, dict) else {}
    memory = req.memory if isinstance(req.memory, dict) else {}
    routing = req.routing if isinstance(req.routing, dict) else {}
    constraints = req.constraints if isinstance(req.constraints, dict) else {}
    visual = req.visual_context if isinstance(req.visual_context, dict) else {}

    interpretation = intent.get("interpretation") if isinstance(intent.get("interpretation"), dict) else intent
    request_input = interpretation.get("input") if isinstance(interpretation.get("input"), dict) else {}
    structured_intent = interpretation.get("intent") if isinstance(interpretation.get("intent"), dict) else {}
    dialogue = interpretation.get("dialogue") if isinstance(interpretation.get("dialogue"), dict) else {}

    current = _clip(
        conversation.get("current_request")
        or request_input.get("original_request")
        or conversation.get("resolved_request")
        or req.goal,
        1600,
    )
    relation = _text(
        dialogue.get("relation")
        or memory.get("relation")
        or "NEW"
    ).upper()

    continuation = dialogue.get("continuation_context") if isinstance(dialogue.get("continuation_context"), dict) else {}
    selected_pairs = continuation.get("selected_pairs") or memory.get("selected_pairs") or []
    new_dialogue = dialogue.get("new_dialogue") if isinstance(dialogue.get("new_dialogue"), dict) else {}
    render_plan = routing.get("render_plan") if isinstance(routing.get("render_plan"), list) else []
    mcdowell = (routing.get("provider_context_plan") or {}).get("mcdowell")
    if not isinstance(mcdowell, dict):
        mcdowell = {"always": True, "role": "presentation_and_render_layout"}

    def _pairs(rows: Any, limit: int = 4) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if not isinstance(rows, list):
            return result
        for item in rows[-limit:]:
            if not isinstance(item, dict):
                continue
            result.append({
                "position": item.get("turn_index"),
                "user": _clip(item.get("user") or item.get("user_text"), 280),
                "user_en": _clip(item.get("user_en") or item.get("user_text_en"), 280),
                "april": _clip(item.get("april") or item.get("april_text"), 280),
                "april_en": _clip(item.get("april_en") or item.get("april_text_en"), 280),
                "score": item.get("score"),
                "semantic": item.get("semantic"),
                "context": item.get("context"),
                "direction": item.get("direction"),
            })
        return result

    modality_lines = {
        "modalities": request_input.get("modalities") or [],
        "has_image": bool(request_input.get("has_image") or visual.get("has_input_images")),
        "has_voice": bool(request_input.get("has_voice")),
        "has_file": bool(request_input.get("has_file")),
    }

    visual_items = visual.get("items")
    visual_meta = []
    if isinstance(visual_items, list):
        for item in visual_items:
            if not isinstance(item, dict):
                continue
            visual_meta.append({
                "filename": _clip(item.get("filename"), 120),
                "source_type": _clip(item.get("source_type"), 60),
                "mime_type": _clip(item.get("mime_type"), 60),
            })

    structured = {
        "CURRENT_REQUEST": current,
        "RETURN_LANGUAGE": _text(
            constraints.get("provider_output_language")
            or request_input.get("display_language")
            or "en"
        ),
        "INTERPRETATION": {
            "schema": interpretation.get("schema", "april_interpretation_v2"),
            "task": structured_intent.get("task", "answer_request"),
            "requested_outputs": structured_intent.get("requested_outputs") or ["text"],
            "wants_image": bool(structured_intent.get("wants_image")),
            "wants_file": bool(structured_intent.get("wants_file")),
            "wants_links": bool(structured_intent.get("wants_links")),
        },
        "DIALOGUE_RELATION": relation,
        "CONTINUATION_CONTEXT": _pairs(selected_pairs) if relation == "CONTINUE" else [],
        "NEW_DIALOGUE_REQUEST": _clip(
            new_dialogue.get("request") if relation == "NEW" else "",
            1600,
        ),
        "CONTEXT": {
            "active_topic": _clip(
                continuation.get("active_topic") or memory.get("active_topic"),
                600,
            ),
            "reason": _clip(
                continuation.get("reason") or memory.get("reason"),
                400,
            ),
            "confidence": continuation.get("confidence") or memory.get("relation_confidence") or 0,
        },
        "INPUT_MODALITIES": modality_lines,
        "VISUAL_CONTEXT": visual_meta,
        "ATTACHMENTS": req.metadata.get("attachments", []) if isinstance(req.metadata, dict) else [],
        "C_ARTIFACT_RENDER_PLAN": render_plan,
        "SELECTED_ROOMS": routing.get("selected_rooms") or [],
        "MCDOWELL_PRESENTATION_POLICY": mcdowell,
        "OUTPUT_CONTRACT": {
            "required": [
                "internal_request_en",
                "internal_answer_en",
                "answer",
                "content",
                "summary",
                "render_blocks",
                "artifacts",
            ],
            "image_generator": "C_APRIL_IMAGES_GENERATOR",
            "scene_authority": "C_ARTIFACT_CONTRACT",
        },
    }

    text = json.dumps(
        structured,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": text}
    ]

    items = visual.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            image_url = _text(item.get("image_url"))
            if image_url:
                content.append({
                    "type": "input_image",
                    "image_url": image_url,
                })

    # Readable documents stay on the same canonical Provider call as the user's
    # text. The raw data URI is transient request data and is not persisted.
    file_inputs = req.metadata.get("file_inputs", []) if isinstance(req.metadata, dict) else []
    if isinstance(file_inputs, list):
        for item in file_inputs:
            if not isinstance(item, dict):
                continue
            file_data = _text(item.get("file_data"))
            if not file_data:
                continue
            file_item: dict[str, Any] = {
                "type": "input_file",
                "filename": _text(item.get("filename") or "file"),
                "file_data": file_data,
            }
            mime_type = _text(item.get("mime_type")).lower()
            if mime_type == "application/pdf":
                file_item["detail"] = "auto"
            content.append(file_item)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]


def normalize_render_blocks(
    value: Any,
    answer: str,
) -> list[dict[str, Any]]:
    """Normalize renderer identity without changing provider payload."""
    raw = value if isinstance(value, list) else []
    result: list[dict[str, Any]] = []

    renderer_map = {
        "text": ("MessageTextBlock", "MessageTextBlock"),
        "markdown": ("MessageTextBlock", "MessageTextBlock"),
        "code": ("CodeBlock", "CodeBlock"),
        "link": ("LinkCard", "LinkCard"),
        "formula": ("FormulaRenderer", "FormulaRenderer"),
        "graph": ("GraphBlock", "GraphBlock"),
        "table": ("TableBlock", "TableBlock"),
        "diagram": ("DiagramRenderer", "DiagramRenderer"),
        "image": ("GalleryBlock", "GalleryBlock"),
        "gallery": ("GalleryBlock", "GalleryBlock"),
    }

    for block in raw:
        if not isinstance(block, dict):
            continue

        item = dict(block)
        block_type = str(item.get("type") or "text").strip().lower()
        renderer, viewer = renderer_map.get(
            block_type,
            ("MessageTextBlock", "MessageTextBlock"),
        )
        item["type"] = block_type
        item.setdefault("renderer", renderer)
        item.setdefault("viewer", viewer)

        # Do not pass an empty visible text block to Web.
        if block_type in {"text", "markdown"}:
            visible = _text(
                item.get("content")
                or item.get("text")
                or item.get("markdown")
            )
            if not visible:
                continue

        result.append(item)

    if not result:
        result.append(
            {
                "type": "text",
                "renderer": "MessageTextBlock",
                "viewer": "MessageTextBlock",
                "content": answer,
            }
        )
    return result


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    answer = _text(
        data.get("answer")
        or data.get("content")
        or data.get("response")
    )
    if not answer:
        raise RuntimeError("PROVIDER_EMPTY_ANSWER")

    internal_request_en = _text(
        data.get("internal_request_en")
        or data.get("normalized_request_en")
    )
    internal_answer_en = _text(
        data.get("internal_answer_en")
        or data.get("normalized_answer_en")
    )

    blocks = normalize_render_blocks(
        data.get("render_blocks"),
        answer,
    )

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        artifacts = []
    normalized_artifacts = [
        dict(item) for item in artifacts if isinstance(item, dict)
    ]

    image_spec = data.get("image_spec")
    if isinstance(image_spec, dict) and not any(
        str(item.get("type") or item.get("artifact_type") or "").lower() == "image"
        for item in normalized_artifacts
    ):
        normalized_artifacts.append({
            "type": "image",
            "spec": dict(image_spec),
        })

    return {
        "machine_response": {
            "answer": answer,
            "content": _text(data.get("content") or answer),
            "summary": _text(
                data.get("summary") or answer[:180]
            ),
            "render_blocks": blocks,
            "metadata": {
                "provider_model": MODEL,
                "provider_language": "en",
                "provider_context_authority": "PROCESSOR",
                "internal_request_en": internal_request_en,
                "internal_answer_en": internal_answer_en,
                "translation_route_version": TRANSLATION_ROUTE_VERSION,
            },
            "artifacts": normalized_artifacts,
        }
    }


async def generate_text(
    request: MachineRequest | dict[str, Any],
) -> dict[str, Any]:
    if isinstance(request, dict):
        allowed = {
            name: request[name]
            for name in MachineRequest.__dataclass_fields__
            if name in request
        }
        request = MachineRequest(**allowed)

    key = _request_key(request)
    cached = _cache.get(key)
    if cached and time.time() - cached[0] < 90:
        return cached[1]

    if key in _inflight:
        raise RuntimeError("DUPLICATE_PROVIDER_REQUEST")

    _inflight.add(key)
    started = time.perf_counter()

    try:
        response = await asyncio.to_thread(
            _client_get().responses.create,
            model=MODEL,
            input=_build_input(request),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

        raw = _text(getattr(response, "output_text", ""))
        if not raw:
            raise RuntimeError("OPENAI_EMPTY_OUTPUT")

        contract = _normalize(_json_load(raw))
        machine_response = contract["machine_response"]
        machine_response["metadata"]["provider_ms"] = round(
            (time.perf_counter() - started) * 1000,
            1,
        )

        usage = getattr(response, "usage", None)
        if usage is not None:
            machine_response["metadata"]["usage"] = {
                "input_tokens": int(
                    getattr(usage, "input_tokens", 0) or 0
                ),
                "output_tokens": int(
                    getattr(usage, "output_tokens", 0) or 0
                ),
                "total_tokens": int(
                    getattr(usage, "total_tokens", 0) or 0
                ),
            }

        _cache[key] = (time.time(), contract)
        return contract
    finally:
        _inflight.discard(key)


async def transcribe_voice(file_path: str) -> str:
    with open(file_path, "rb") as handle:
        result = await asyncio.to_thread(
            _client_get().audio.transcriptions.create,
            model="gpt-4o-mini-transcribe",
            file=handle,
        )
    return _text(getattr(result, "text", ""))


def normalize_provider_input(value: Any) -> Any:
    return value
