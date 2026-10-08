"""Voice intake metadata boundary for bot.ru."""
from __future__ import annotations

from typing import Any

MAX_AUDIO_BYTES = 18 * 1024 * 1024
_ALLOWED_PREFIXES = ("audio/", "video/webm", "application/ogg")


def validate_voice(data: bytes, *, filename: str = "voice.webm", content_type: str = "") -> dict[str, Any]:
    if not data:
        raise ValueError("VOICE_EMPTY")
    if len(data) > MAX_AUDIO_BYTES:
        raise ValueError("VOICE_TOO_LARGE")

    mime = str(content_type or "application/octet-stream").split(";", 1)[0].lower()
    if not (mime.startswith("audio/") or mime in _ALLOWED_PREFIXES):
        raise ValueError("UNSUPPORTED_VOICE_TYPE")

    return {
        "filename": filename,
        "mime_type": mime,
        "size_bytes": len(data),
    }
