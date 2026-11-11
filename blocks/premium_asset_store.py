"""Premium-only file sidecars bound to the lifetime of a dialogue message.

Binary bytes stay on disk; dialogue_memory stores only compact asset references.
The caller deletes a message's directory when its dialogue_memory row expires.
"""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = Path(os.getenv("APRIL_PREMIUM_ASSET_ROOT", "data/premium_dialogue_assets")).resolve()
_MAX_ASSET_BYTES = int(os.getenv("APRIL_PREMIUM_ASSET_MAX_BYTES", str(25 * 1024 * 1024)))


def _safe_component(value: Any) -> str:
    raw = str(value or "").strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40] if raw else "unknown"


def _root() -> Path:
    _DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_ROOT


def _message_dir(user_id: Any, message_id: Any) -> Path:
    return _root() / _safe_component(user_id) / _safe_component(message_id)


def _clean_filename(value: Any) -> str:
    name = Path(str(value or "asset.bin").replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._() -]+", "_", name).strip(" .")
    return (name or "asset.bin")[:160]


def decode_data_uri(value: Any) -> tuple[bytes, str] | None:
    raw = str(value or "").strip()
    if not raw.startswith("data:") or ";base64," not in raw:
        return None
    try:
        header, encoded = raw.split(",", 1)
        mime = header[5:].split(";", 1)[0] or "application/octet-stream"
        content = base64.b64decode(encoded, validate=True)
        return (content, mime) if content else None
    except Exception:
        return None


def save_asset(user_id: Any, message_id: Any, *, filename: str, content: bytes,
               mime_type: str = "application/octet-stream", kind: str = "file",
               asset_role: str = "user_input", output_type: str = "",
               metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Atomically save one asset under the owning Premium message."""
    uid, mid = str(user_id or "").strip(), str(message_id or "").strip()
    if not uid or not mid or not isinstance(content, (bytes, bytearray)):
        return None
    data = bytes(content)
    if not data or len(data) > _MAX_ASSET_BYTES:
        return None
    folder = _message_dir(uid, mid)
    folder.mkdir(parents=True, exist_ok=True)
    asset_id = uuid.uuid4().hex
    safe_name = _clean_filename(filename)
    disk_name = f"{asset_id}_{safe_name}"
    path, tmp_path = folder / disk_name, folder / (disk_name + ".tmp")
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        ref = {
            "asset_id": asset_id, "filename": safe_name,
            "kind": str(kind or "file")[:40],
            "mime_type": str(mime_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream")[:120],
            "asset_role": str(asset_role or "user_input")[:40],
            "output_type": str(output_type or "")[:60], "message_id": mid,
            "storage_key": str(path.relative_to(_root())), "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        _write_manifest(folder, uid, mid, ref)
        return ref
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def _write_manifest(folder: Path, user_id: str, message_id: str, ref: dict[str, Any]) -> None:
    manifest = folder / "manifest.json"
    try:
        existing = json.loads(manifest.read_text("utf-8")) if manifest.exists() else {}
        refs = existing.get("assets") if isinstance(existing.get("assets"), list) else []
        refs = [x for x in refs if isinstance(x, dict) and x.get("asset_id") != ref.get("asset_id")]
        refs.append(ref)
        payload = {"user_key": _safe_component(user_id), "message_key": _safe_component(message_id), "assets": refs}
        tmp = folder / "manifest.json.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, manifest)
    except Exception:
        pass


def read_asset(user_id: Any, ref: dict[str, Any]) -> bytes | None:
    if not isinstance(ref, dict):
        return None
    key = str(ref.get("storage_key") or "").strip()
    if not key:
        return None
    try:
        root = _root()
        path = (root / key).resolve()
        if root not in path.parents or not path.is_file():
            return None
        if len(path.parents) < 3 or path.parents[1].name != _safe_component(user_id):
            return None
        data = path.read_bytes()
        expected = str(ref.get("sha256") or "")
        if expected and hashlib.sha256(data).hexdigest() != expected:
            return None
        return data
    except Exception:
        return None


def load_message_assets(user_id: Any, message_ids: list[str]) -> list[dict[str, Any]]:
    """Load only assets belonging to selected message IDs."""
    results: list[dict[str, Any]] = []
    uid = str(user_id or "").strip()
    if not uid:
        return results
    for mid in list(dict.fromkeys(str(x or "").strip() for x in message_ids if str(x or "").strip())):
        folder = _message_dir(uid, mid)
        try:
            payload = json.loads((folder / "manifest.json").read_text("utf-8"))
            if payload.get("user_key") != _safe_component(uid) or payload.get("message_key") != _safe_component(mid):
                continue
            for ref in payload.get("assets", []):
                if not isinstance(ref, dict):
                    continue
                data = read_asset(uid, ref)
                if data:
                    item = dict(ref)
                    item["content"] = data
                    results.append(item)
        except Exception:
            continue
    return results


def delete_message_assets(user_id: Any, message_id: Any) -> None:
    """Remove every file for one dialogue turn; safe to call more than once."""
    uid, mid = str(user_id or "").strip(), str(message_id or "").strip()
    if not uid or not mid:
        return
    folder = _message_dir(uid, mid)
    try:
        shutil.rmtree(folder, ignore_errors=True)
        parent = folder.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except Exception:
        pass


def delete_user_assets(user_id: Any) -> bool:
    """Delete every persisted Premium asset owned by a user; safe to retry."""
    uid = str(user_id or "").strip()
    if not uid:
        return False
    try:
        # Do not create the storage root merely because an account was deleted.
        folder = _DEFAULT_ROOT / _safe_component(uid)
        if folder.exists():
            shutil.rmtree(folder)
        return not folder.exists()
    except Exception:
        return False
