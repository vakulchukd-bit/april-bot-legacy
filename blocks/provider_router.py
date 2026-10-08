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
You are April's single response provider.

The processor has already normalized the request into concise English.
Do not translate again and do not create a second interpretation route.

The processor already decided NEW/CONTINUE and supplied the permitted context.
Do not search memory, invent a second route, or create another context source.

For CONTINUE:
- keep the selected dialogue chain as the active subject;
- answer the current request as the next turn;
- do not ask for information already present in the chain.

For NEW:
- answer the current request independently;
- recent context is only a relevance candidate and must not override the request.

Return JSON only:
{
  "internal_request_en": "concise English semantic form of the current request",
  "internal_answer_en": "concise English semantic form of the answer",
  "answer": "complete human-readable answer in RETURN_LANGUAGE",
  "content": "same answer or concise equivalent",
  "summary": "one-sentence summary",
  "render_blocks": [
    {"type":"text","renderer":"MessageTextBlock","viewer":"MessageTextBlock","content":"..."}
  ]
}

For code, include a code render block.
For a direct URL, include a link render block.
For visual data, preserve the payload needed by the Web renderer.
Never put machine metadata in answer/content.
Never return an empty answer.
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
    plan = req.routing.get("provider_context_plan")
    if not isinstance(plan, dict):
        plan = {}

    relation = str(
        plan.get("relation")
        or req.intent.get("dialogue_relation")
        or "NEW"
    ).upper()

    selected_chain = plan.get("dialogue_chain")
    recent_candidate = plan.get("recent_context_candidate")

    def chain_text(rows: Any, limit: int) -> str:
        if not isinstance(rows, list):
            return ""
        lines: list[str] = []
        for item in rows[-limit:]:
            if not isinstance(item, dict):
                continue
            lines.append(
                "PAIR "
                + str(item.get("position") or "")
                + ": USER_EN="
                + _clip(item.get("user_en"), 700)
                + " | APRIL_EN="
                + _clip(item.get("april_en"), 700)
                + " | USER_ORIGINAL="
                + _clip(item.get("user"), 700)
            )
        return "\n".join(lines)

    chain = chain_text(selected_chain, 4)
    candidate = chain_text(recent_candidate, 1)

    current = _clip(
        plan.get("current_request")
        or req.conversation.get("current_request")
        or req.goal,
        3000,
    )
    language = _text(
        req.constraints.get("provider_output_language") or "en"
    )

    user_text = (
        "RELATION: "
        + relation
        + "\nCURRENT_REQUEST_ORIGINAL:\n"
        + current
        + "\n"
        "SELECTED_DIALOGUE_CHAIN_EN:\n"
        + (chain or "(none)")
        + "\n"
        "RECENT_CONTEXT_CANDIDATE:\n"
        + (candidate or "(none)")
        + "\n"
        "RETURN_LANGUAGE: "
        + language
        + "\n"
        "INTERNAL_LANGUAGE: en\n"
        "TRANSLATION_ROUTE: "
        + TRANSLATION_ROUTE_VERSION
        + "\n"
        "OUTPUT_CONTRACT: internal_request_en + answer + content + "
        "summary + render_blocks"
    )

    content: list[dict[str, Any]] = [{"type": "input_text", "text": user_text}]
    visual = req.visual_context.get("items") if isinstance(req.visual_context, dict) else []
    if isinstance(visual, list):
        for item in visual:
            if not isinstance(item, dict):
                continue
            image_url = _text(item.get("image_url"))
            if image_url:
                content.append({"type": "input_image", "image_url": image_url})

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": content,
        },
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
            "artifacts": [],
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
