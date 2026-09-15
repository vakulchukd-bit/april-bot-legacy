# blocks/image_engine.py
# Image generation is routed exclusively through C_APRIL_IMAGES_GENERATOR.

import asyncio
import tempfile
import time
from pathlib import Path

# Image creation is owned directly by C_APRIL_IMAGES_GENERATOR.
from blocks.C_APRIL_IMAGES_GENERATOR import generate_image_result

from blocks.C_APRIL_IMAGES_GENERATOR import edit_image_result

from blocks.image_system import (
    analyze_image
)

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
    state
):
    """Execute the single canonical image-generation route."""
    try:
        print("🧠 ENGINE: C_APRIL_IMAGES_GENERATOR ACTIVE")

        result = await generate_image_result(
            prompt=prompt,
            size="1024x1024",
            quality="high",
            variant="room",
        )

        if not result.get("success") or not result.get("image_bytes"):
            return {
                "type": "error",
                "data": "⚠️ Внутренний April Images Generation не смог создать изображение",
            }

        img = result["image_bytes"]
        state["image_current"] = img

        path = save_temp_image(img)
        if path:
            now = time.time()
            state["image_context"] = {
                "type": "generated",
                "path": path,
                "hint": prompt,
                "created_at": now,
                "expires_at": now + 7 * 24 * 60 * 60,
            }
            print(f"📂 ENGINE FILE SAVED: {path}")

        set_last_entity(
            user_id,
            {
                "type": "image",
                "data": img,
                "source": "C_APRIL_IMAGES_GENERATOR",
                "artifact": result.get("artifact"),
                "contract": result.get("contract"),
            },
        )

        print("🧠 ENGINE SAVE: image_current + META")

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
        print("ENGINE GENERATE ERROR:", e)
        return {
            "type": "error",
            "data": "⚠️ Ошибка генерации изображения",
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
