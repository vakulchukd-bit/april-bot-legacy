"""Input envelope reader used by bot.ru.

Supports JSON and multipart/form-data without introducing a second API route.
Text files are decoded into bounded text; images are normalized for the model;
other binary files remain attachments with metadata.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from typing import Any

from blocks.image_reader import read_image_bytes

MAX_TEXT_FILE_CHARS = 18000
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".csv", ".tsv", ".py", ".js",
    ".jsx", ".tsx", ".html", ".htm", ".css", ".xml", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".log", ".sql", ".sh", ".bat", ".ps1",
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


def normalize_attachment(att: Attachment) -> Attachment:
    filename = att.filename or "file"
    ext = os.path.splitext(filename.lower())[1]
    mime = att.content_type.lower().split(";", 1)[0].strip()

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
        text = _decode_text(att.data)[:MAX_TEXT_FILE_CHARS]
        att.kind = "text_file"
        att.metadata = {
            "filename": filename,
            "mime_type": mime or "text/plain",
            "size_bytes": len(att.data),
            "text": text,
            "truncated": len(_decode_text(att.data)) > MAX_TEXT_FILE_CHARS,
        }
        return att

    att.kind = "file"
    att.metadata = {
        "filename": filename,
        "mime_type": mime or "application/octet-stream",
        "size_bytes": len(att.data),
    }
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
