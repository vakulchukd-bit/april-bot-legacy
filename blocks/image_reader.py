"""Canonical image/screenshot reader for bot.ru.

This module validates and normalizes PNG/JPEG/WebP/GIF image bytes. It does not
interpret the picture itself; the normalized image is supplied to the model as
an input_image item so the semantic processor remains the authority.
"""
from __future__ import annotations

import base64
from typing import Any

MAX_IMAGE_BYTES = 8 * 1024 * 1024
_ALLOWED = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


def _mime_from_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return ""


def read_image_bytes(
    data: bytes,
    *,
    filename: str = "image",
    content_type: str = "",
) -> dict[str, Any]:
    if not data:
        raise ValueError("IMAGE_EMPTY")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("IMAGE_TOO_LARGE")

    declared = str(content_type or "").strip().lower()
    detected = _mime_from_bytes(data)
    mime_type = detected or declared
    if mime_type not in _ALLOWED:
        raise ValueError("UNSUPPORTED_IMAGE_TYPE")

    encoded = base64.b64encode(data).decode("ascii")
    return {
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "data_uri": f"data:{mime_type};base64,{encoded}",
        "source_type": "screenshot" if str(filename).lower().startswith(("screenshot", "screen")) else "image",
    }


def build_input_image(image: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "input_image",
        "image_url": str(image.get("data_uri") or ""),
    }
