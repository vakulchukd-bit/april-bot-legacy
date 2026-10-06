# blocks/image_engine.py
# Image generation is routed exclusively through C_APRIL_IMAGES_GENERATOR.

import asyncio
import os
import tempfile
import time
from copy import deepcopy
import threading
import re
from pathlib import Path

# Image creation is owned directly by C_APRIL_IMAGES_GENERATOR.
from blocks.C_APRIL_IMAGES_GENERATOR import (
    generate_from_spec,
)
from blocks.C_ARTIFACT_CONTRACT import _artifact_canonical_render_blocks

from blocks.image_system import (
    analyze_image
)

# =====================================================
# LIVE GENERIC RENDER GENERATION STATUS
# =====================================================
# Shared lifecycle registry for image/graph/table rendering. It lives in this
# existing module so the project does not need a separate
# render_generation_status.py file.
_RENDER_STATUS_LOCK = threading.RLock()
_RENDER_STATUS: dict[str, dict] = {}
_RENDER_STATUS_TTL = 120.0
_RENDER_KINDS = {"none", "image", "graph", "table"}


def set_render_generation_status(
    flow_id: str,
    *,
    status: str,
    kind: str = "none",
    user_id: str = "",
    asset_url: str = "",
    error: str = "",
) -> None:
    key = str(flow_id or user_id or "").strip()
    if not key:
        return
    normalized_kind = str(kind or "none").strip().lower()
    if normalized_kind not in _RENDER_KINDS:
        normalized_kind = "none"
    normalized_status = str(status or "pending").strip().lower()
    now = time.time()
    with _RENDER_STATUS_LOCK:
        _RENDER_STATUS[key] = {
            "flow_id": str(flow_id or key),
            "user_id": str(user_id or ""),
            "kind": normalized_kind,
            "status": normalized_status,
            "generation_expected": normalized_kind != "none" and normalized_status not in {"not_requested", "cancelled"},
            "generating": normalized_status in {"pending", "generating", "rendering"} and normalized_kind != "none",
            "asset_url": str(asset_url or ""),
            "error": str(error or ""),
            "updated_at": now,
            "expires_at": 0.0 if normalized_status in {"pending", "generating", "rendering"} else now + _RENDER_STATUS_TTL,
        }


def get_render_generation_status(flow_id: str = "", user_id: str = "") -> dict:
    key = str(flow_id or user_id or "").strip()
    if not key:
        return {
            "flow_id": "",
            "user_id": str(user_id or ""),
            "kind": "none",
            "status": "not_requested",
            "generation_expected": False,
            "generating": False,
        }

    now = time.time()
    with _RENDER_STATUS_LOCK:
        for stale_key, record in list(_RENDER_STATUS.items()):
            if float(record.get("expires_at") or 0.0) <= now:
                _RENDER_STATUS.pop(stale_key, None)
        record = dict(_RENDER_STATUS.get(key) or {})

    if not record:
        return {
            "flow_id": str(flow_id or key),
            "user_id": str(user_id or ""),
            "kind": "none",
            "status": "not_requested",
            "generation_expected": False,
            "generating": False,
        }

    return record


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
    normalized_status = str(status or "idle").strip().lower()
    record = {
        "flow_id": str(flow_id or key),
        "user_id": str(user_id or ""),
        "status": normalized_status,
        "started_at": now,
        "updated_at": now,
        "asset_url": str(asset_url or ""),
        "error": str(error or ""),
        # A long-running CPU image generation must never fall back to `idle`
        # merely because its normal post-completion TTL elapsed.  Keep the
        # generating record alive until the engine explicitly reports success
        # or failure; completed/failed records retain the existing short TTL.
        "expires_at": 0.0 if normalized_status in {"generating", "rendering"} else now + _IMAGE_STATUS_TTL,
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
            stale_status = str(stale.get("status") or "idle").strip().lower()
            if stale_status in {"generating", "rendering"}:
                continue
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
    flow_id = ""
    turn_id = ""
    scene_id = ""
    conversation_id = ""
    dialogue_sequence_id = ""
    if isinstance(context, dict):
        flow_id = str(
            context.get("flow_id")
            or context.get("request_id")
            or ""
        ).strip()
        turn_id = str(context.get("turn_id") or "").strip()
        scene_id = str(context.get("scene_id") or "").strip()
        conversation_id = str(context.get("conversation_id") or "").strip()
        dialogue_sequence_id = str(context.get("dialogue_sequence_id") or "").strip()
    if not flow_id:
        flow_id = str(user_id or "").strip()

    try:
        set_image_generation_status(
            flow_id,
            status="generating",
            user_id=str(user_id or ""),
        )
        set_render_generation_status(
            flow_id,
            status="generating",
            kind="image",
            user_id=str(user_id or ""),
        )
        print(
            "🧠 ENGINE: C_APRIL_IMAGES_GENERATOR ACTIVE",
            {
                "route": "rooms_registry.image_generate",
                "artifact_route": "C_ARTIFACT_CONTRACT",
                "prompt_source": "april_image_spec_v1",
                "token_limit_enforced_here": False,
                "flow_id": flow_id,
                "user_id": str(user_id or ""),
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
        provider_metadata = context.get("provider_metadata") if isinstance(context, dict) and isinstance(context.get("provider_metadata"), dict) else {}
        provider_signal = context.get("image_generation_signal") if isinstance(context, dict) and isinstance(context.get("image_generation_signal"), dict) else provider_metadata.get("image_generation_signal") if isinstance(provider_metadata.get("image_generation_signal"), dict) else {}
        current_request = str(context.get("current_user_request") or "").strip() if isinstance(context, dict) else ""
        dialogue_contract = context.get("dialogue_contract") if isinstance(context, dict) and isinstance(context.get("dialogue_contract"), dict) else {}
        visual_generation_request = str(
            context.get("visual_generation_request")
            or dialogue_contract.get("visual_generation_request")
            or provider_metadata.get("visual_generation_request")
            or ""
        ).strip() if isinstance(context, dict) else ""
        signal_route = str(provider_signal.get("route") or "").strip().upper()
        signal_execute = provider_signal.get("execute") is True
        signal_anchor = str(provider_signal.get("request_anchor") or "").strip()
        signal_anchor_matches = bool(
            signal_anchor
            and current_request
            and re.sub(r"\s+", " ", signal_anchor).casefold() == re.sub(r"\s+", " ", current_request).casefold()
        )
        signal_valid = signal_route == "C_APRIL_IMAGES_GENERATOR" and signal_execute and signal_anchor_matches

        signal_prompt = str(provider_signal.get("prompt") or "").strip()

        # request_anchor is the immutable user trigger. The actual semantic image
        # prompt comes from Provider/OpenAI and must never be overwritten by that
        # trigger. User/Interpretation text is only a final compatibility fallback.
        spec_semantic_prompt = str(
            clean_spec.get("openai_structured_visual_plan_semantic")
            or clean_spec.get("prompt")
            or ""
        ).strip()
        if signal_valid and signal_prompt:
            clean_spec["prompt"] = signal_prompt
            prompt_source = "provider_signal_semantic_plan"
        elif spec_semantic_prompt:
            clean_spec["prompt"] = spec_semantic_prompt
            prompt_source = "provider_spec_semantic_plan"
        elif visual_generation_request:
            clean_spec["prompt"] = visual_generation_request
            prompt_source = "interpreted_visual_request_fallback"
        elif current_request:
            clean_spec["prompt"] = current_request
            prompt_source = "current_request_fallback"
        elif str(prompt or "").strip():
            clean_spec["prompt"] = str(prompt or "").strip()
            prompt_source = "room_prompt_fallback"
        else:
            prompt_source = "empty_prompt"
        clean_spec["generator_signal"] = "C_APRIL_IMAGES_GENERATOR"
        clean_spec["request_anchor"] = current_request
        clean_spec["flow_id"] = flow_id
        clean_spec["turn_id"] = turn_id
        clean_spec["scene_id"] = scene_id
        clean_spec["conversation_id"] = conversation_id
        clean_spec["dialogue_sequence_id"] = dialogue_sequence_id
        print(
            "🧭 IMAGE ENGINE HANDOFF:",
            {
                "provider_signal_valid": signal_valid,
                "signal_route": signal_route or "none",
                "request_anchor_matches": signal_anchor_matches,
                "prompt_source": prompt_source,
                "visual_generation_request": visual_generation_request,
                "target": "C_APRIL_IMAGES_GENERATOR",
            },
        )
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
            set_render_generation_status(
                flow_id,
                status="failed",
                kind="image",
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

        # Diffusion is finished at this point and the real image bytes exist.
        # Do not advertise `rendering` before an asset exists: that produced an
        # empty GalleryBlock during long CPU generations.  The Web lifecycle
        # switches at the concrete asset-ready boundary below.
        path = save_temp_image(img)
        if path:
            try:
                if not Path(path).is_file() or Path(path).stat().st_size <= 0:
                    path = None
            except Exception:
                path = None
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
            set_render_generation_status(
                flow_id,
                status="failed",
                kind="image",
                user_id=str(user_id or ""),
                error=error_value,
            )
            return {
                "type": "error",
                "data": "⚠️ Изображение создано, но не удалось подготовить его для Web.",
                "error": error_value,
                "image_generation_status": "failed",
            }

        # `success` now means: the real PNG is on disk and the canonical
        # browser asset URL is ready.  Yield once so the Web status poller can
        # observe that boundary while the final SceneContract is still being
        # assembled by the same canonical route.
        set_image_generation_status(
            flow_id,
            status="success",
            user_id=str(user_id or ""),
            asset_url=public_asset_url or asset_url,
        )
        set_render_generation_status(
            flow_id,
            status="success",
            kind="image",
            user_id=str(user_id or ""),
            asset_url=public_asset_url or asset_url,
        )
        await asyncio.sleep(0)

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
        if contract_obj is not None:
            try:
                contract_obj.fiber.identity.user_id = str(user_id or contract_obj.fiber.identity.user_id or "")
                identity_meta = {
                    "flow_id": flow_id,
                    "turn_id": turn_id,
                    "scene_id": scene_id or f"{flow_id}:scene",
                    "conversation_id": conversation_id,
                    "dialogue_sequence_id": dialogue_sequence_id,
                    "dialogue_development": context.get("dialogue_development", {}) if isinstance(context, dict) else {},
                }
                if isinstance(getattr(contract_obj, "metadata", None), dict):
                    contract_obj.metadata.update(identity_meta)
                scene_contract = getattr(contract_obj, "scene_contract", None)
                if scene_contract is not None:
                    scene_contract.user_id = str(user_id or getattr(scene_contract, "user_id", "") or "")
                    scene_contract.flow_id = flow_id
                    scene_contract.turn_id = turn_id
                    scene_contract.scene_id = identity_meta["scene_id"]
                    scene_contract.conversation_id = conversation_id
                    scene_contract.dialogue_sequence_id = dialogue_sequence_id
                    scene_contract.dialogue_development = deepcopy(identity_meta["dialogue_development"]) if isinstance(identity_meta["dialogue_development"], dict) else {}
                    scene_contract.authenticated_scope = {
                        "user_id": scene_contract.user_id,
                        "conversation_id": conversation_id,
                        "dialogue_sequence_id": dialogue_sequence_id,
                    }
                    if isinstance(getattr(scene_contract, "metadata", None), dict):
                        scene_contract.metadata.update(identity_meta)
                    for scene_block in getattr(scene_contract, "render_blocks", []) or []:
                        if isinstance(scene_block, dict):
                            scene_block.update({
                                "scene_id": scene_contract.scene_id,
                                "turn_id": turn_id,
                                "flow_id": flow_id,
                                "user_id": scene_contract.user_id,
                                "conversation_id": conversation_id,
                                "dialogue_sequence_id": dialogue_sequence_id,
                            })
            except Exception as identity_exc:
                print("⚠️ IMAGE ENGINE CONTRACT IDENTITY BIND:", identity_exc)
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
                block["scene_id"] = scene_id or block.get("scene_id") or f"{flow_id}:scene"
                block["turn_id"] = turn_id or block.get("turn_id") or ""
                block["flow_id"] = flow_id or block.get("flow_id") or ""
                block["user_id"] = str(user_id or block.get("user_id") or "")
                block["conversation_id"] = conversation_id or block.get("conversation_id") or ""
                block["dialogue_sequence_id"] = dialogue_sequence_id or block.get("dialogue_sequence_id") or ""
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

        # The generator returns the former large prompt as machine-only dialogue
        # evidence. Keep it on the internal route; Executor commits it to the
        # authenticated 12-hour dialog pair. It is never placed in the artifact
        # or sent back to GPT Image 2.
        generator_metadata = result.get("metadata") if isinstance(result, dict) else {}
        dialogue_visual_generation_memory = (
            deepcopy(generator_metadata.get("_dialogue_visual_generation_memory"))
            if isinstance(generator_metadata, dict)
            and isinstance(generator_metadata.get("_dialogue_visual_generation_memory"), dict)
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
            "metadata": {
                "_dialogue_visual_generation_memory": dialogue_visual_generation_memory,
            } if dialogue_visual_generation_memory else {},
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
        set_render_generation_status(
            flow_id,
            status="failed",
            kind="image",
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


# ===== EDIT (DISABLED) =====
async def edit(
    user_id,
    image_bytes,
    prompt,
    state,
    **kwargs,
):
    """Compatibility shim: editing is disabled in the current image engine.

    Active visual requests create a new image only. This callable remains present
    so the future Images 2.0 edit route can be added without changing imports.
    """
    _ = (user_id, image_bytes, prompt, state, kwargs)
    return {
        "type": "error",
        "data": "Редактирование изображений пока отключено.",
        "error": "IMAGE_EDIT_DISABLED",
        "image_generation_status": "not_requested",
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
