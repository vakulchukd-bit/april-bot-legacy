# blocks/image_engine.py
# Image generation is routed exclusively through C_APRIL_IMAGES_GENERATOR.

import asyncio
import os
import tempfile
import time
import threading
from pathlib import Path

# Image creation is owned directly by C_APRIL_IMAGES_GENERATOR.
from blocks.C_APRIL_IMAGES_GENERATOR import (
    generate_from_spec,
    edit_image_result,
)
from blocks.C_ARTIFACT_CONTRACT import _artifact_canonical_render_blocks

from blocks.image_system import (
    analyze_image
)

# =====================================================
# LIVE IMAGE GENERATION STATUS
# =====================================================
# Kept in the existing image engine so Web can observe the
# actual generator state while /api/v1/chat is still running.
_IMAGE_STATUS_LOCK = threading.RLock()
_IMAGE_STATUS: dict[str, dict] = {}
_IMAGE_STATUS_TTL = 120.0


def set_image_generation_status(
    flow_id: str,
    *,
    status: str,
    user_id: str = "",
    asset_url: str = "",
    error: str = "",
) -> None:
    key = str(flow_id or user_id or "").strip()
    if not key:
        return
    now = time.time()
    record = {
        "flow_id": str(flow_id or key),
        "user_id": str(user_id or ""),
        "status": str(status or "idle").strip().lower(),
        "started_at": now,
        "updated_at": now,
        "asset_url": str(asset_url or ""),
        "error": str(error or ""),
        "expires_at": now + _IMAGE_STATUS_TTL,
    }
    with _IMAGE_STATUS_LOCK:
        _IMAGE_STATUS[key] = record


def get_image_generation_status(flow_id: str = "", user_id: str = "") -> dict:
    key = str(flow_id or user_id or "").strip()
    if not key:
        return {"flow_id": "", "status": "idle", "generating": False}

    now = time.time()
    with _IMAGE_STATUS_LOCK:
        record = dict(_IMAGE_STATUS.get(key) or {})
        # Opportunistic cleanup keeps the in-process registry bounded.
        for stale_key, stale in list(_IMAGE_STATUS.items()):
            if float(stale.get("expires_at") or 0) <= now:
                _IMAGE_STATUS.pop(stale_key, None)

    if not record:
        return {
            "flow_id": str(flow_id or key),
            "user_id": str(user_id or ""),
            "status": "idle",
            "generating": False,
        }

    status = str(record.get("status") or "idle").lower()
    return {
        **record,
        "generating": status == "generating",
    }

# 🔥 META
from blocks.state_manager import (
    set_last_entity
)


# ===== простая эвристика сложности =====
def is_complex_prompt(text: str) -> bool:

    if not text:
        return False

    t = text.lower()

    if len(t) > 120:
        return True

    triggers = [

        "несколько",
        "много",
        "сцена",
        "фон",
        "на фоне",
        "стиль",
        "освещение",
        "детально",
        "реалистич",
        "cinematic",
        "4k",
        "ultra",
        "detailed"
    ]

    return any(
        x in t
        for x in triggers
    )


# ===== СОХРАНЕНИЕ ФАЙЛА =====
def _cleanup_expired_image_files():
    now = time.time()
    root = Path(tempfile.gettempdir())
    for path in root.glob("april_image_*.png"):
        try:
            if now - path.stat().st_mtime >= 7 * 24 * 60 * 60:
                path.unlink(missing_ok=True)
        except Exception:
            pass


def save_temp_image(image_bytes):

    try:
        _cleanup_expired_image_files()
        tmp = tempfile.NamedTemporaryFile(
            prefix="april_image_",
            delete=False,
            suffix=".png"
        )
        tmp.write(image_bytes)
        tmp.flush()
        tmp.close()
        return tmp.name

    except Exception as e:

        print(
            "⚠️ FILE SAVE ERROR:",
            e
        )

        return None


# ===== GENERATE =====
async def generate(
    user_id,
    prompt,
    state,
    spec=None,
    context=None,
):
    """Execute image generation for an already-routed Room request.

    A structured ``april_image_spec_v1`` is preferred when Interpretation /
    Provider produced one.  A plain prompt remains a compatibility path, but
    both forms terminate in the same C_APRIL_IMAGES_GENERATOR backend.
    """
    flow_id = str((context or {}).get("request_id") or "").strip() if isinstance(context, dict) else ""
    if not flow_id:
        flow_id = str(user_id or "").strip()

    try:
        set_image_generation_status(
            flow_id,
            status="generating",
            user_id=str(user_id or ""),
        )
        print(
            "🧠 ENGINE: C_APRIL_IMAGES_GENERATOR ACTIVE",
            {
                "route": "rooms_registry.image_generate",
                "artifact_route": "C_ARTIFACT_CONTRACT",
                "prompt_source": "april_image_spec_v1",
                "token_limit_enforced_here": False,
            },
        )

        clean_spec = dict(spec) if isinstance(spec, dict) else {
            "schema": "april_image_spec_v1",
            "prompt": str(prompt or "").strip(),
            "width": 512,
            "height": 512,
            "style": "illustration",
            "quality": "standard",
            "visual_context": dict(context) if isinstance(context, dict) else {},
        }
        clean_spec.setdefault("schema", "april_image_spec_v1")
        if not str(clean_spec.get("prompt") or "").strip():
            clean_spec["prompt"] = str(prompt or "").strip()
        result = await generate_from_spec(
            clean_spec,
            variant="room_registry",
        )

        if not result.get("success") or not result.get("image_bytes"):
            error_value = result.get("error") or result.get("message") or "IMAGE_GENERATION_EMPTY_RESULT"
            set_image_generation_status(
                flow_id,
                status="failed",
                user_id=str(user_id or ""),
                error=str(error_value),
            )
            return {
                "type": "error",
                "data": "⚠️ Внутренний April Images Generation не смог создать изображение",
                "error": error_value,
                "image_generation_status": "failed",
            }

        img = result["image_bytes"]
        state["image_current"] = img

        effective_prompt = str(
            result.get("prompt")
            or (clean_spec or {}).get("prompt")
            or prompt
            or ""
        ).strip()

        path = save_temp_image(img)
        asset_name = Path(path).name if path else ""
        asset_url = f"/api/v1/images/{asset_name}" if asset_name else ""
        public_origin = (
            os.getenv("APRIL_PUBLIC_BASE_URL")
            or os.getenv("RAILWAY_PUBLIC_DOMAIN")
            or "https://april-bot-production-cf51.up.railway.app"
        ).strip().rstrip("/")
        if public_origin and not public_origin.startswith(("http://", "https://")):
            public_origin = "https://" + public_origin
        public_asset_url = f"{public_origin}{asset_url}" if asset_url else ""
        if not path or not asset_url:
            error_value = "IMAGE_ASSET_SAVE_FAILED"
            set_image_generation_status(
                flow_id,
                status="failed",
                user_id=str(user_id or ""),
                error=error_value,
            )
            return {
                "type": "error",
                "data": "⚠️ Изображение создано, но не удалось подготовить его для Web.",
                "error": error_value,
                "image_generation_status": "failed",
            }

        set_image_generation_status(
            flow_id,
            status="success",
            user_id=str(user_id or ""),
            asset_url=public_asset_url or asset_url,
        )
        if path:
            now = time.time()
            state["image_context"] = {
                "type": "generated",
                "path": path,
                "asset_name": asset_name,
                "asset_url": asset_url,
                "hint": effective_prompt,
                "created_at": now,
                "expires_at": now + 7 * 24 * 60 * 60,
            }
            print(f"📂 ENGINE FILE SAVED: {path}")
            print(f"🖼️ ENGINE IMAGE ASSET: {asset_url}")

        contract_obj = result.get("contract")
        artifact_obj = getattr(contract_obj, "artifact", None) if contract_obj is not None else None
        render_blocks = []
        if artifact_obj is not None:
            try:
                render_blocks = _artifact_canonical_render_blocks(artifact_obj)
            except Exception as exc:
                print("⚠️ IMAGE ENGINE ARTIFACT BLOCKS:", exc)

        # Canonical media handoff: GalleryBlock receives a concrete asset URL.
        # Raw bytes stay in the image-engine state and are not used as the UI route.
        if asset_url:
            for block in render_blocks:
                if not isinstance(block, dict):
                    continue
                kind = str(block.get("type") or block.get("artifact_type") or block.get("representation") or "").lower()
                if kind not in {"image", "gallery"}:
                    continue
                payload = dict(block.get("payload") or {}) if isinstance(block.get("payload"), dict) else {}
                payload.update({"asset_url": public_asset_url or asset_url, "image_asset_url": public_asset_url or asset_url, "asset_path": path or "", "image_asset_path": path or "", "asset_name": asset_name})
                images = payload.get("images") if isinstance(payload.get("images"), list) else []
                browser_asset_url = public_asset_url or asset_url
                if images:
                    fixed = []
                    for item in images[:8]:
                        obj = dict(item) if isinstance(item, dict) else {}
                        # One canonical raster reference. Descriptive text remains alt/caption only.
                        obj.update({
                            "src": browser_asset_url,
                            "url": browser_asset_url,
                            "asset_url": browser_asset_url,
                            "image_asset_url": browser_asset_url,
                            "image": browser_asset_url,
                        })
                        fixed.append(obj)
                    payload["images"] = fixed
                else:
                    payload.update({
                        "src": browser_asset_url,
                        "url": browser_asset_url,
                        "image": browser_asset_url,
                        "images": [{
                            "src": browser_asset_url,
                            "url": browser_asset_url,
                            "asset_url": browser_asset_url,
                            "image_asset_url": browser_asset_url,
                            "image": browser_asset_url,
                        }],
                    })
                payload["asset_url"] = browser_asset_url
                payload["image_asset_url"] = browser_asset_url
                block["payload"] = payload
                block["asset_url"] = browser_asset_url
                block["image_asset_url"] = browser_asset_url

                # Critical: _artifact_canonical_render_blocks returns projected
                # dictionaries. Persist the same corrected payload into the real
                # artifact so the later SceneContract projection cannot fall back
                # to the pre-generation prompt/data-uri envelope.
                if artifact_obj is not None:
                    try:
                        artifact_data = dict(getattr(artifact_obj, "data", {}) or {})
                        artifact_data["payload"] = payload
                        artifact_data["asset_url"] = browser_asset_url
                        artifact_data["image_asset_url"] = browser_asset_url
                        artifact_data["asset_name"] = asset_name
                        artifact_data["asset_path"] = path or ""
                        artifact_data["image_asset_path"] = path or ""
                        artifact_obj.data = artifact_data
                    except Exception as exc:
                        print("⚠️ IMAGE ENGINE ARTIFACT PERSIST:", exc)

        artifact_dict = result.get("artifact")
        if isinstance(artifact_dict, dict) and asset_url:
            artifact_dict = dict(artifact_dict)
            artifact_dict.update({"asset_url": public_asset_url or asset_url, "image_asset_url": public_asset_url or asset_url, "asset_path": path or "", "image_asset_path": path or "", "asset_name": asset_name})
            result["artifact"] = artifact_dict
        render_signal = (
            artifact_dict.get("render_signal")
            if isinstance(artifact_dict, dict)
            else {}
        )

        set_last_entity(
            user_id,
            {
                "type": "image",
                "data": img,
                "source": "C_APRIL_IMAGES_GENERATOR",
                "artifact": artifact_dict,
                "contract": contract_obj,
                "render_blocks": render_blocks,
            },
        )

        print("🧠 ENGINE SAVE: image_current + META")

        return {
            "type": "image",
            "data": img,
            "artifact": artifact_dict,
            "contract": contract_obj,
            "artifacts": [artifact_obj] if artifact_obj is not None else [],
            "render_blocks": render_blocks,
            "render_signal": render_signal,
            "image_engine": "April Images Generation",
            "artifact_route": "C_ARTIFACT_CONTRACT",
            "room_route": "rooms_registry.image_generate",
            "image_generation_status": "success",
            "image_generation_backend": result.get("backend"),
            "prompt": effective_prompt,
            "asset_url": public_asset_url or asset_url,
            "image_asset_url": public_asset_url or asset_url,
            "asset_path": path or "",
            "asset_name": asset_name,
            "width": result.get("width"),
            "height": result.get("height"),
        }

    except Exception as e:
        set_image_generation_status(
            flow_id,
            status="failed",
            user_id=str(user_id or ""),
            error=str(e),
        )
        print("ENGINE GENERATE ERROR:", e)
        return {
            "type": "error",
            "data": "⚠️ Ошибка генерации изображения",
            "error": str(e),
            "image_generation_status": "failed",
            "artifact_route": "C_ARTIFACT_CONTRACT",
            "room_route": "rooms_registry.image_generate",
        }


# ===== EDIT =====
async def edit(
    user_id,
    image_bytes,
    prompt,
    state
):
    try:
        print("🧠 ENGINE: C_APRIL_IMAGES_GENERATOR edit route active")

        if not image_bytes:
            return {
                "type": "error",
                "data": "⚠️ Не найдено исходное изображение для редактирования",
            }

        result = await edit_image_result(
            image_bytes,
            prompt,
            quality="high",
        )

        if not result.get("success") or not result.get("image_bytes"):
            return {
                "type": "error",
                "data": "⚠️ Не удалось изменить изображение",
            }

        img = result["image_bytes"]
        state["image_current"] = img

        path = save_temp_image(img)
        if path:
            now = time.time()
            state["image_context"] = {
                "type": "edited",
                "path": path,
                "hint": prompt,
                "created_at": now,
                "expires_at": now + 7 * 24 * 60 * 60,
            }

        set_last_entity(
            user_id,
            {
                "type": "image",
                "data": img,
                "source": "C_APRIL_IMAGES_GENERATOR/edit",
                "artifact": result.get("artifact"),
                "contract": result.get("contract"),
            },
        )

        return {
            "type": "image",
            "data": img,
            "artifact": result.get("artifact"),
            "contract": result.get("contract"),
            "render_signal": (result.get("artifact") or {}).get("render_signal"),
            "image_engine": "April Images Generation",
            "artifact_route": "C_ARTIFACT_CONTRACT",
        }

    except Exception as e:
        print("ENGINE EDIT ERROR:", e)
        return {
            "type": "error",
            "data": "⚠️ Ошибка редактирования",
        }


# ===== ANALYZE =====
async def analyze(
    path,
    state
):

    return await analyze_image(
        path,
        state
    )
