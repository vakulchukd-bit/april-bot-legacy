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
Use the anchor topic and selected USER↔APRIL pairs as the primary continuity evidence. Resolve
pronouns and short follow-ups against that anchor before treating the request as new.
For NEW, answer independently and do not let old context override the request.

For a history_request, use DIALOGUE_HISTORY_TOPICS / DIALOGUE_TABLE_MARKDOWN as an index over
the retained dialogue. Never claim that the dialogue is unavailable when the index contains
topics. Show the requested number of topics, clamped to 10. Default to 7 when the user does
not specify a number. The user may then name a topic or give a hint and April should continue
from the corresponding anchor/pairs. Keep the hidden remainder known to the processor; do not
invent topics that are not in the supplied index.
For every input image/screenshot, inspect the actual supplied pixels. Give a useful grounded description with the main subject, visible colors/markings, posture/shape, nearby objects and scene context. Distinguish direct observations from uncertainty; never invent a breed, material, location or detail that the pixels do not support. For follow-ups, re-inspect the recalled original image if it is included. If multiple images are supplied, keep them labelled by filename/role; compare only when the user asks. An input image is NOT a request to generate an image.
For every attached file, read the actual supplied input_file or ATTACHED_TEXT_FILES content. For source code, describe its real purpose, entry points, key functions, data flow and concrete problems visible in the supplied source; cite filenames/function names rather than giving a generic description. An input file is NOT a request to create/export a file.
Text supplied with image/file inputs is the instruction for those attachments. Keep ATTACHMENT_INDEX, attachment role (USER_INPUT vs APRIL_OUTPUT), source message ID, and CURRENT_REQUEST distinct. In a continuation, use the original asset and its paired prior answer as evidence, not only the short prior user sentence.
Generation/editing is permission-based: only when INTERPRETATION.wants_image=true may C_APRIL_IMAGES_GENERATOR be used. Never infer image generation from image words or attachment contents.
For analyze_image, analyze_file, or analyze_input tasks, answer in explanatory text and retain enough specific facts to support follow-up questions. Avoid generic one-sentence summaries when the user asks what an image/file contains.
For a code modification request, return an explanatory text block followed by a separate render block with type="code", language, filename, and the complete corrected code when size permits. Preserve unaffected behavior, do not replace missing sections with ellipses/placeholders, and do not claim the code was saved as a downloadable file unless an actual file artifact/link is supplied. If INTERPRETATION.wants_file=true and you return corrected source, also include an artifact {"type":"file","filename":"the_real_output_name.ext","mime_type":"the appropriate text MIME type","content":"the same complete corrected source text"}; never invent a filesystem path or URL. For a request to explain code only, do not rewrite it unasked.
Use render blocks that match the requested output: type="code" for code, type="table" for tables, type="diagram" for diagrams, type="formula" for formulas. Keep narrative explanation as a text block before the structured block. Only create an output file artifact if explicitly requested and actual file contents are provided.

Return JSON only:
{
  "internal_request_en": "...",
  "internal_answer_en": "...",
  "answer": "complete human-readable answer in RETURN_LANGUAGE",
  "content": "same answer or concise equivalent",
  "summary": "one-sentence summary",
  "render_blocks": [
    {"type":"text","renderer":"MessageTextBlock","viewer":"MessageTextBlock","content":"Grounded explanation in RETURN_LANGUAGE"}
  ],
  "artifacts": [],
  "dialogue_memory_record": {
    "topic": "short stable subject label",
    "summary": "grounded summary for future follow-ups",
    "entities": [],
    "visual_observations": [],
    "file_purpose": "",
    "code_symbols": [],
    "attachment_refs": []
  }
}

When code is explicitly requested, include a render block like {"type":"code","renderer":"CodeBlock","viewer":"CodeBlock","language":"python","filename":"module.py","code":"<complete source>","content":"<same complete source>"}. The explanatory text remains a separate text block.

For an image generation request, artifacts must contain:
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
        content_type = _audio_content_type(
            name,
            getattr(file, "content_type", ""),
        )
        payload = self._client._post_multipart(
            "/v1/audio/transcriptions",
            fields={"model": model},
            file_field=("file", name, content_type, data),
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
            # Keep provider stalls bounded.  The successful fast path is unchanged;
            # this only limits how long a broken upstream can hold the chat request.
            timeout_seconds = max(
                15.0,
                min(75.0, float(os.getenv("APRIL_OPENAI_TIMEOUT_SECONDS", "45") or 45)),
            )
            with urlopen(req, timeout=timeout_seconds) as response:
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


def _audio_content_type(filename: str, declared: Any = "") -> str:
    """Return a usable audio MIME type for the transcription endpoint."""
    declared_type = _text(declared).lower().split(";", 1)[0].strip()
    if declared_type.startswith("audio/") and declared_type != "audio/x-unknown":
        return declared_type

    suffix = os.path.splitext(os.path.basename(_text(filename).lower()))[1]
    by_suffix = {
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".opus": "audio/ogg",
        ".mp3": "audio/mpeg",
        ".mpeg": "audio/mpeg",
        ".mp4": "audio/mp4",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
    }
    return by_suffix.get(suffix, "application/octet-stream")


def transcribe_voice(
    audio_bytes: bytes,
    *,
    filename: str = "voice.webm",
    content_type: str = "",
) -> str:
    """Public compatibility API imported by blocks.voice_reader.transcribe_voice_bytes.

    Kept synchronous because voice_reader is a synchronous input-normalization
    boundary; its network work is bounded by APRIL_OPENAI_TIMEOUT_SECONDS.
    """
    import io

    raw = bytes(audio_bytes or b"")
    if not raw:
        raise ValueError("VOICE_EMPTY")

    safe_name = os.path.basename(_text(filename) or "voice.webm")
    mime_type = _audio_content_type(safe_name, content_type)
    upload = io.BytesIO(raw)
    upload.name = safe_name
    upload.content_type = mime_type

    model = _text(os.getenv("APRIL_OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"))
    started = time.perf_counter()
    try:
        result = _client_get().audio.transcriptions.create(model=model, file=upload)
        transcript = _text(getattr(result, "text", ""))
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        print(
            f"[APRIL_VOICE] stage=transcription status=error model={model} "
            f"elapsed_ms={elapsed_ms} error={type(exc).__name__}",
            flush=True,
        )
        raise

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    print(
        f"[APRIL_VOICE] stage=transcription status={'ok' if transcript else 'empty'} "
        f"model={model} elapsed_ms={elapsed_ms} audio_bytes={len(raw)} "
        f"transcript_chars={len(transcript)}",
        flush=True,
    )
    if not transcript:
        raise RuntimeError("VOICE_EMPTY_TRANSCRIPT")
    return transcript


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
    # Include attachment fingerprints.  Without these, the 90-second Provider
    # cache could reuse a text-only or previous-image response for different bytes.
    def fingerprint(value: Any) -> str:
        if not isinstance(value, str) or not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    visual = req.visual_context if isinstance(req.visual_context, dict) else {}
    visual_fingerprints = [
        fingerprint(item.get("image_url"))
        for item in (visual.get("items") or [])
        if isinstance(item, dict) and item.get("image_url")
    ]
    metadata = req.metadata if isinstance(req.metadata, dict) else {}
    file_fingerprints = [
        fingerprint(item.get("file_data"))
        for item in (metadata.get("file_inputs") or [])
        if isinstance(item, dict) and item.get("file_data")
    ]
    text_fingerprints = [
        fingerprint(item.get("content"))
        for item in (metadata.get("file_contents") or [])
        if isinstance(item, dict) and item.get("content")
    ]
    raw = json.dumps(
        {
            "user_id": req.fiber.identity.user_id,
            "conversation": req.conversation,
            "intent": req.intent,
            "text": req.conversation.get("current_request") or req.goal,
            "memory": req.memory,
            "routing": req.routing,
            "constraints": req.constraints,
            "visual_fingerprints": visual_fingerprints,
            "file_fingerprints": file_fingerprints,
            "text_fingerprints": text_fingerprints,
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
    history_request = bool(structured_intent.get("history_request") or memory.get("history_request") or request_input.get("history_request"))
    requested_topic_count = int(structured_intent.get("history_count") or memory.get("requested_topic_count") or 7)
    requested_topic_count = max(1, min(10, requested_topic_count))
    render_plan = routing.get("render_plan") if isinstance(routing.get("render_plan"), list) else []
    mcdowell = (routing.get("provider_context_plan") or {}).get("mcdowell")
    if not isinstance(mcdowell, dict):
        mcdowell = {"always": True, "role": "presentation_and_render_layout"}


    history_topics = dialogue.get("continuation_context", {}).get("history_topics")
    if not isinstance(history_topics, list):
        history_topics = memory.get("history_topics") or []
    history_topics = [
        {
            "number": item.get("number"),
            "topic": _clip(item.get("topic"), 100),
            "last_question": _clip(item.get("last_question"), 120),
            "turns": item.get("turns"),
        }
        for item in history_topics
        if isinstance(item, dict)
    ][:10]

    topic_index = memory.get("topic_index") or history_topics
    topic_index = [
        {
            "number": item.get("number"),
            "topic": _clip(item.get("topic"), 100),
            "last_question": _clip(item.get("last_question"), 110),
            "turns": item.get("turns"),
        }
        for item in topic_index
        if isinstance(item, dict)
    ][:5]

    def _pairs(rows: Any, limit: int = 4) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        if not isinstance(rows, list):
            return result
        for item in rows[-limit:]:
            if not isinstance(item, dict):
                continue
            result.append({
                "turn": item.get("turn_index") or item.get("turn"),
                "user": _clip(item.get("user") or item.get("user_text"), 240),
                "april": _clip(item.get("april") or item.get("april_text"), 300),
                "topic": _clip(item.get("topic"), 100),
                "score": item.get("score"),
                "same_dialog": bool(item.get("same_dialog")),
                "message_id": item.get("message_id"),
                "attachment_evidence": _clip(item.get("attachment_evidence"), 1800),
            })
        return result

    anchor = continuation.get("anchor") or memory.get("anchor") or {}

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
                "recalled_from_memory": bool(item.get("recalled_from_memory")),
                "asset_message_id": _clip(item.get("asset_message_id"), 120),
                "asset_role": _clip(item.get("asset_role") or "user_input", 32),
                "output_type": _clip(item.get("output_type"), 40),
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
            "wants_code": bool(structured_intent.get("wants_code")),
            "wants_links": bool(structured_intent.get("wants_links")),
            "explicit_generation_request": bool(structured_intent.get("explicit_generation_request")),
        },
        "DIALOGUE_RELATION": relation,
        "HISTORY_REQUEST": history_request,
        "HISTORY_TOPIC_COUNT": requested_topic_count if history_request else 0,
        "DIALOGUE_ANCHOR": {
            "topic": _clip(anchor.get("topic"), 120),
            "user": _clip(anchor.get("user"), 220),
            "april": _clip(anchor.get("april"), 300),
            "message_id": anchor.get("message_id"),
            "same_dialog": bool(anchor.get("same_dialog")),
        },
        "CONTINUATION_CONTEXT": _pairs(selected_pairs, 5) if relation == "CONTINUE" else [],
        "DIALOGUE_HISTORY_TOPICS": history_topics if history_request else [],
        "DIALOGUE_TOPIC_INDEX": topic_index if relation == "CONTINUE" else [],
        "DIALOGUE_KNOWN_TOPIC_COUNT": int(memory.get("known_topic_count") or len(history_topics) or len(topic_index) or 0),
        "DIALOGUE_TABLE_MARKDOWN": _clip(
            memory.get("topic_table_markdown")
            or (dialogue.get("continuation_context") or {}).get("topic_table_markdown")
            or "",
            2600,
        ),
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
        "RECALLED_ASSETS": memory.get("restored_assets") or [],
        "ATTACHMENT_INDEX": req.metadata.get("attachment_index", []) if isinstance(req.metadata, dict) else [],
        "ATTACHMENTS": req.metadata.get("attachments", []) if isinstance(req.metadata, dict) else [],
        "ATTACHED_TEXT_FILES": req.metadata.get("file_contents", []) if isinstance(req.metadata, dict) else [],
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
                "dialogue_memory_record",
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

    text_files = req.metadata.get("file_contents", []) if isinstance(req.metadata, dict) else []
    if isinstance(text_files, list):
        for item in text_files:
            if not isinstance(item, dict):
                continue
            filename = _clip(item.get("filename") or "file", 160)
            file_content = _clip(item.get("content") or "", 18000)
            role = _clip(item.get("asset_role") or "user_input", 32)
            source_message_id = _clip(item.get("asset_message_id") or "current", 120)
            if file_content:
                content.append({
                    "type": "input_text",
                    "text": f"ATTACHED_TEXT_FILE role={role} source_message_id={source_message_id} filename={filename}:\n{file_content}",
                })

    items = visual.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            image_url = _text(item.get("image_url"))
            if image_url:
                filename = _clip(item.get("filename") or "image", 160)
                role = _clip(item.get("asset_role") or "user_input", 32)
                source_message_id = _clip(item.get("asset_message_id") or "current", 120)
                content.append({
                    "type": "input_text",
                    "text": f"NEXT_INPUT_IMAGE role={role} filename={filename} source_message_id={source_message_id}; inspect the immediately following image as this asset.",
                })
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
            filename = _text(item.get("filename") or "file")
            role = _clip(item.get("asset_role") or "user_input", 32)
            source_message_id = _clip(item.get("asset_message_id") or "current", 120)
            content.append({
                "type": "input_text",
                "text": f"NEXT_INPUT_FILE role={role} filename={filename} source_message_id={source_message_id}; inspect the immediately following file as this asset.",
            })
            # Keep the actual input_file payload to the Provider API's fields;
            # role/identity metadata belongs in the adjacent input_text label.
            file_item: dict[str, Any] = {
                "type": "input_file",
                "filename": filename,
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
        if block_type == "code":
            code_value = _text(item.get("code") or item.get("content") or item.get("text"))
            if code_value:
                item["code"] = code_value
                item.setdefault("content", code_value)
                item.setdefault("language", "text")
                if not _text(item.get("filename")):
                    item["filename"] = "generated-code.txt"

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
        or data.get("summary")
        or data.get("internal_answer_en")
    )
    if not answer:
        raw_blocks = data.get("render_blocks") if isinstance(data.get("render_blocks"), list) else []
        for block in raw_blocks:
            if not isinstance(block, dict):
                continue
            candidate = _text(block.get("content") or block.get("text") or block.get("markdown"))
            if candidate:
                answer = candidate
                break
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

    memory_record = data.get("dialogue_memory_record") or data.get("memory_record") or {}
    if not isinstance(memory_record, dict):
        memory_record = {}
    memory_record = {
        "topic": _clip(memory_record.get("topic") or answer.split("\n", 1)[0], 180),
        "summary": _clip(memory_record.get("summary") or data.get("summary") or answer, 1600),
        "entities": [str(x)[:160] for x in (memory_record.get("entities") or [])[:16]] if isinstance(memory_record.get("entities"), list) else [],
        "visual_observations": [str(x)[:300] for x in (memory_record.get("visual_observations") or [])[:12]] if isinstance(memory_record.get("visual_observations"), list) else [],
        "file_purpose": _clip(memory_record.get("file_purpose"), 600),
        "code_symbols": [str(x)[:160] for x in (memory_record.get("code_symbols") or [])[:20]] if isinstance(memory_record.get("code_symbols"), list) else [],
        "attachment_refs": [dict(x) for x in (memory_record.get("attachment_refs") or [])[:8] if isinstance(x, dict)] if isinstance(memory_record.get("attachment_refs"), list) else [],
    }

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
                "dialogue_memory_record": memory_record,
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
    failure_code = "PROVIDER_EMPTY_ANSWER"
    contract: dict[str, Any] | None = None
    usage_data: dict[str, int] = {}
    try:
        client = _client_get()
        base_input = _build_input(request)
        for attempt in range(2):
            attempt_input = base_input
            if attempt:
                # A targeted one-time retry repairs incomplete JSON without
                # creating a second route or changing the user's identity/context.
                attempt_input = list(base_input) + [{
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": (
                            "Your previous output was empty or not a valid non-empty JSON response. "
                            "Return the full required JSON object now. The answer field must contain "
                            "a useful user-facing answer in RETURN_LANGUAGE. If an attachment is "
                            "present, describe/analyze that actual attachment; do not invent details."
                        ),
                    }],
                }]
            try:
                response = await asyncio.to_thread(
                    client.responses.create,
                    model=MODEL,
                    input=attempt_input,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                )
                raw = _text(getattr(response, "output_text", ""))
                if not raw:
                    failure_code = "OPENAI_EMPTY_OUTPUT"
                    continue
                try:
                    decoded = _json_load(raw)
                    contract = _normalize(decoded)
                    usage = getattr(response, "usage", None)
                    if usage is not None:
                        usage_data = {
                            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                        }
                    break
                except Exception as exc:
                    failure_code = str(exc) or "PROVIDER_INVALID_OUTPUT"
                    contract = None
                    continue
            except Exception as exc:
                failure_code = str(exc) or "PROVIDER_REQUEST_FAILED"
                # Do not spend another full network timeout on auth, bad-request,
                # or stalled-network failures. Retry only immediate transient
                # rate-limit/server errors; malformed/empty model output is handled
                # by the inner retry above.
                retryable_http = any(
                    marker in failure_code.upper()
                    for marker in (
                        "OPENAI_HTTP_429",
                        "OPENAI_HTTP_500",
                        "OPENAI_HTTP_502",
                        "OPENAI_HTTP_503",
                        "OPENAI_HTTP_504",
                    )
                )
                if attempt == 0 and retryable_http:
                    continue
                contract = None
                break

        if contract is None:
            language = _text(
                (request.constraints or {}).get("display_language")
                or (request.constraints or {}).get("provider_output_language")
                or "en"
            ).lower()
            attachments = (request.metadata or {}).get("attachments", []) if isinstance(request.metadata, dict) else []
            has_attachment = bool(attachments or (request.visual_context or {}).get("items") or (request.metadata or {}).get("file_inputs") or (request.metadata or {}).get("file_contents"))
            if language.startswith("ru"):
                answer = (
                    "Не удалось получить содержательный ответ от модели по этому вложению. "
                    "Повтори запрос; если проблема повторится, отправь файл или изображение ещё раз."
                    if has_attachment else
                    "Модель не вернула содержательный ответ. Повтори запрос, пожалуйста."
                )
            elif language.startswith("uk"):
                answer = (
                    "Не вдалося отримати змістовну відповідь моделі щодо цього вкладення. "
                    "Повтори запит; якщо проблема повториться, надішли файл або зображення ще раз."
                    if has_attachment else
                    "Модель не повернула змістовної відповіді. Будь ласка, повтори запит."
                )
            else:
                answer = (
                    "I couldn't get a usable answer about this attachment. Please retry; if it happens again, resend the file or image."
                    if has_attachment else
                    "The model did not return a usable answer. Please retry your request."
                )
            contract = {
                "machine_response": {
                    "answer": answer,
                    "content": answer,
                    "summary": answer,
                    "render_blocks": [{
                        "type": "text",
                        "renderer": "MessageTextBlock",
                        "viewer": "MessageTextBlock",
                        "content": answer,
                    }],
                    "metadata": {
                        "provider_model": MODEL,
                        "provider_context_authority": "PROCESSOR",
                        "provider_fallback": True,
                        "provider_error_code": failure_code,
                    },
                    "artifacts": [],
                }
            }
            print(f"[APRIL_PROVIDER] non-empty fallback returned after retries; code={failure_code}", flush=True)

        machine_response = contract["machine_response"]
        machine_response.setdefault("metadata", {})
        machine_response["metadata"]["provider_ms"] = round((time.perf_counter() - started) * 1000, 1)
        if usage_data:
            machine_response["metadata"]["usage"] = usage_data

        # Successful answers are cached. Failure fallbacks are not, so an
        # immediate user retry has another chance to produce a real answer.
        if not machine_response.get("metadata", {}).get("provider_fallback"):
            _cache[key] = (time.time(), contract)
        return contract
    finally:
        _inflight.discard(key)
