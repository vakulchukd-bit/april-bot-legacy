"""Input envelope reader used by bot.ru.

Supports JSON and multipart/form-data without introducing a second API route.
Text files are decoded into bounded text; images are normalized for the model;
other readable files are preserved as inline file inputs for the Provider.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from typing import Any

from blocks.image_reader import read_image_bytes
from blocks.voice_reader import is_voice_field, validate_voice

MAX_TEXT_FILE_CHARS = 18000
MAX_INLINE_FILE_BYTES = 10 * 1024 * 1024
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".csv", ".tsv", ".py", ".js",
    ".jsx", ".tsx", ".html", ".htm", ".css", ".xml", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".log", ".sql", ".sh", ".bat", ".ps1",
}
_READABLE_FILE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".rtf", ".odt", ".ods", ".odp",
}


@dataclass
class Attachment:
    field_name: str
    filename: str
    content_type: str
    data: bytes
    kind: str = "file"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def size_bytes(self) -> int:
        return len(self.data)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _mime_type(filename: str, declared: str = "") -> str:
    clean_declared = str(declared or "").split(";", 1)[0].strip().lower()
    if clean_declared and clean_declared != "application/octet-stream":
        return clean_declared
    guessed, _ = mimetypes.guess_type(filename)
    return str(guessed or clean_declared or "application/octet-stream").lower()


def _build_data_uri(data: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def normalize_attachment(att: Attachment) -> Attachment:
    filename = att.filename or "file"
    ext = os.path.splitext(filename.lower())[1]
    mime = _mime_type(filename, att.content_type)

    if is_voice_field(
        field_name=att.field_name,
        filename=filename,
        content_type=mime,
    ):
        voice = validate_voice(
            att.data,
            filename=filename,
            content_type=mime,
        )
        att.kind = "voice"
        att.metadata = voice
        return att

    if mime.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        image = read_image_bytes(
            att.data,
            filename=filename,
            content_type=mime,
        )
        att.kind = "image"
        att.metadata = image
        return att

    if mime.startswith("text/") or ext in _TEXT_EXTENSIONS:
        decoded = _decode_text(att.data)
        text = decoded[:MAX_TEXT_FILE_CHARS]
        att.kind = "text_file"
        att.metadata = {
            "filename": filename,
            "mime_type": mime or "text/plain",
            "size_bytes": len(att.data),
            "text": text,
            "truncated": len(decoded) > MAX_TEXT_FILE_CHARS,
            "source_type": "text_file",
        }
        return att

    readable = ext in _READABLE_FILE_EXTENSIONS or mime in {
        "application/pdf",
        "application/rtf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.oasis.opendocument.text",
        "application/vnd.oasis.opendocument.spreadsheet",
        "application/vnd.oasis.opendocument.presentation",
    }

    att.kind = "file"
    metadata: dict[str, Any] = {
        "filename": filename,
        "mime_type": mime or "application/octet-stream",
        "size_bytes": len(att.data),
        "source_type": "document" if readable else "file",
        "provider_readable": bool(readable and len(att.data) <= MAX_INLINE_FILE_BYTES),
    }

    # The original bytes stay in the request memory only. bot.py strips this
    # field from the persistent attachment metadata and passes it separately to
    # the Provider as an input_file item.
    if readable and len(att.data) <= MAX_INLINE_FILE_BYTES:
        metadata["data_uri"] = _build_data_uri(
            att.data,
            mime or "application/octet-stream",
        )

    att.metadata = metadata
    return att


def parse_json_payload(body: bytes) -> tuple[dict[str, Any], list[Attachment]]:
    data = json.loads(body.decode("utf-8") or "{}")
    if not isinstance(data, dict):
        raise ValueError("JSON_OBJECT_REQUIRED")
    return data, []


def parse_multipart_payload(
    body: bytes,
    *,
    content_type: str,
) -> tuple[dict[str, Any], list[Attachment]]:
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
    message = BytesParser(policy=policy.default).parsebytes(header)
    if not message.is_multipart():
        raise ValueError("MULTIPART_REQUIRED")

    fields: dict[str, Any] = {}
    attachments: list[Attachment] = []

    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition") or ""
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        ctype = part.get_content_type() or "application/octet-stream"
        if filename:
            attachments.append(
                normalize_attachment(
                    Attachment(
                        field_name=_text(name) or "file",
                        filename=_text(filename) or "file",
                        content_type=ctype,
                        data=payload,
                    )
                )
            )
        else:
            value = payload.decode("utf-8", errors="replace")
            fields[_text(name)] = value

    return fields, attachments
