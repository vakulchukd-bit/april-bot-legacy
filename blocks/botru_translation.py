"""April bot.ru translation boundary.

This is a library layer, not an HTTP route. It keeps the public API at
/api/v1/chat while translating user-language text to the internal English
semantic layer and translating the final English answer back to the user's
display language.

The translator is intentionally stateless; identity and dialogue state remain
owned by the canonical processor/database route.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODEL = os.getenv("APRIL_TRANSLATOR_MODEL", "gpt-5.6-luna")
TRANSLATOR_TIMEOUT = float(os.getenv("APRIL_TRANSLATOR_TIMEOUT", "90"))
TRANSLATION_VERSION = "botru_translation_v2"


def _text(value: Any) -> str:
    return str(value or "").strip()


def detect_language(text: str, requested: str = "auto") -> str:
    requested = _text(requested).lower()
    if requested and requested not in {"auto", "default"}:
        return requested

    value = _text(text).lower()
    if not value:
        return "en"
    if any(ch in value for ch in "іїєґ"):
        return "uk"
    if any("\u0400" <= ch <= "\u04ff" for ch in value):
        return "ru"
    if any("\u3040" <= ch <= "\u30ff" for ch in value):
        return "ja"
    if any("\u4e00" <= ch <= "\u9fff" for ch in value):
        return "zh"
    if any("\uac00" <= ch <= "\ud7af" for ch in value):
        return "ko"
    if any("\u0600" <= ch <= "\u06ff" for ch in value):
        return "ar"
    if any("\u0900" <= ch <= "\u097f" for ch in value):
        return "hi"
    if any("\u0370" <= ch <= "\u03ff" for ch in value):
        return "el"
    return "en"


def _openai_json(prompt: str, *, max_output_tokens: int = 1200) -> str:
    api_key = _text(os.getenv("OPENAI_API_KEY"))
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")

    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "You are April's canonical translation boundary. "
                    "Translate faithfully, preserve technical meaning, numbers, "
                    "code, URLs and names. Return only the translated text. "
                    "Do not explain the translation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": max_output_tokens,
    }

    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=TRANSLATOR_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TRANSLATOR_HTTP_{exc.code}: {detail[:800]}") from exc
    except URLError as exc:
        raise RuntimeError(f"TRANSLATOR_NETWORK_ERROR: {exc.reason}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("TRANSLATOR_INVALID_RESPONSE")

    direct = _text(data.get("output_text"))
    if direct:
        return direct

    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            value = _text(content.get("text"))
            if value:
                chunks.append(value)

    result = "\n".join(chunks).strip()
    if not result:
        raise RuntimeError("TRANSLATOR_EMPTY_OUTPUT")
    return result


def translate_to_english(text: str, language: str = "auto") -> dict[str, str | bool]:
    source = _text(text)
    detected = detect_language(source, language)
    if not source or detected == "en":
        return {
            "text_en": source,
            "source_language": detected,
            "translated": False,
            "version": TRANSLATION_VERSION,
        }

    translated = _openai_json(
        "Translate the following user request into concise internal English. "
        "Preserve all facts and requested operations exactly.\n\n"
        + source
    )
    return {
        "text_en": translated,
        "source_language": detected,
        "translated": True,
        "version": TRANSLATION_VERSION,
    }


def translate_from_english(text: str, language: str) -> dict[str, str | bool]:
    source = _text(text)
    target = _text(language).lower() or "en"
    if not source or target == "en":
        return {
            "text": source,
            "target_language": target,
            "translated": False,
            "version": TRANSLATION_VERSION,
        }

    translated = _openai_json(
        f"Translate this April response faithfully into {target}. "
        "Preserve markdown, code, URLs, numbers, names and structure. "
        "Do not add or remove information.\n\n"
        + source
    )
    return {
        "text": translated,
        "target_language": target,
        "translated": True,
        "version": TRANSLATION_VERSION,
    }


def transcribe_audio_bytes(
    data: bytes,
    *,
    filename: str = "voice.webm",
    content_type: str = "audio/webm",
) -> str:
    """Transcribe voice input at the bot.ru intake boundary."""
    api_key = _text(os.getenv("OPENAI_API_KEY"))
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
    if not data:
        raise ValueError("VOICE_EMPTY")

    import uuid

    boundary = "----AprilVoice" + uuid.uuid4().hex
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="model"\r\n\r\n',
        b"gpt-4o-mini-transcribe\r\n",
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode(),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]

    request = Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=b"".join(parts),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=TRANSLATOR_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"VOICE_TRANSCRIBE_HTTP_{exc.code}: {detail[:800]}") from exc
    except URLError as exc:
        raise RuntimeError(f"VOICE_TRANSCRIBE_NETWORK_ERROR: {exc.reason}") from exc

    transcript = _text(payload.get("text")) if isinstance(payload, dict) else ""
    if not transcript:
        raise RuntimeError("VOICE_TRANSCRIPT_EMPTY")
    return transcript

def translate_if_needed(text: str, source_language: str, target_language: str) -> str:
    if _text(source_language).lower() == _text(target_language).lower():
        return _text(text)
    return str(translate_from_english(text, target_language)["text"])
