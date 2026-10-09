"""Canonical Voice block for the single April chat route.

Responsibilities:
- validate/normalize incoming voice bytes;
- transcribe voice through the existing Provider transcription function;
- never create a second API route;
- never import itself.

Route:
    Web -> POST /api/v1/chat -> input_reader -> voice_reader
        -> Provider transcription -> transcript event -> Exkrutor
"""
from __future__ import annotations

import os
from typing import Any

MAX_VOICE_BYTES = 25 * 1024 * 1024

_AUDIO_EXTENSIONS = {
    ".webm", ".ogg", ".oga", ".mp3", ".wav", ".m4a",
    ".mp4", ".mpeg", ".mpga",
}
_AUDIO_MIME_TYPES = {"video/webm", "application/ogg"}
_FIELD_NAMES = {"audio", "voice", "audio_file", "voice_file"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_mime(content_type: str) -> str:
    return _text(content_type).lower().split(";", 1)[0].strip()


def is_voice_field(
    *,
    field_name: str = "",
    filename: str = "",
    content_type: str = "",
) -> bool:
    field = _text(field_name).lower()
    name = _text(filename).lower()
    mime = _normalized_mime(content_type)
    ext = os.path.splitext(name)[1]
    return (
        field in _FIELD_NAMES
        or mime.startswith("audio/")
        or mime in _AUDIO_MIME_TYPES
        or ext in _AUDIO_EXTENSIONS
    )


def validate_voice(
    data: bytes,
    *,
    filename: str = "voice.webm",
    content_type: str = "",
) -> dict[str, Any]:
    """Validate one voice attachment without doing interpretation."""
    raw = data or b""
    name = _text(filename) or "voice.webm"
    mime = _normalized_mime(content_type)

    if not raw:
        raise ValueError("VOICE_EMPTY")
    if len(raw) > MAX_VOICE_BYTES:
        raise ValueError("VOICE_TOO_LARGE")
    if not is_voice_field(
        filename=name,
        content_type=mime,
    ):
        raise ValueError("VOICE_UNSUPPORTED_FORMAT")

    return {
        "filename": name,
        "mime_type": mime or "application/octet-stream",
        "size_bytes": len(raw),
        "source_type": "voice",
        "transcription_provider": "provider_router",
        "transcription_model": "gpt-4o-mini-transcribe",
    }


def transcribe_voice_bytes(
    data: bytes,
    *,
    filename: str = "voice.webm",
    content_type: str = "",
) -> str:
    """Send voice to the existing Provider transcription endpoint."""
    metadata = validate_voice(
        data,
        filename=filename,
        content_type=content_type,
    )
    # Local import deliberately prevents an import cycle at module load time.
    # provider_router.transcribe_voice is synchronous and accepts audio BYTES,
    # not a temporary-file path. Passing tmp.name here caused
    # TypeError: string argument without an encoding in production.
    from blocks.provider_router import transcribe_voice

    raw = bytes(data)
    return _text(
        transcribe_voice(
            raw,
            filename=metadata["filename"],
            content_type=metadata["mime_type"],
        )
    )
