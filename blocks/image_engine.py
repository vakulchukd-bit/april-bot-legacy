# blocks/image_engine.py
import asyncio

# берём существующие функции, НИЧЕГО не удаляем
from blocks.image_module import generate_image_v2, generate_image
from blocks.image_edit_module import edit_image_bytes, edit_image
from blocks.image_system import analyze_image

# 🔥 META
from blocks.state_manager import set_last_entity


# ===== простая эвристика сложности =====
def is_complex_prompt(text: str) -> bool:
    if not text:
        return False

    t = text.lower()

    if len(t) > 120:
        return True

    triggers = [
        "несколько", "много", "сцена", "фон", "на фоне",
        "стиль", "освещение", "детально", "реалистич",
        "cinematic", "4k", "ultra", "detailed"
    ]

    return any(x in t for x in triggers)


# ===== GENERATE =====
async def generate(user_id, prompt, state):
    try:
        use_advanced = is_complex_prompt(prompt)

        if use_advanced:
            print("🧠 ENGINE: using ADVANCED (future 2.0)")
            img = await generate_image_v2(prompt)
        else:
            print("⚡ ENGINE: using FAST V2")
            img = await generate_image_v2(prompt)

        # fallback
        if not img:
            print("↩️ ENGINE FALLBACK → V1")
            img = await generate_image(prompt)

        if not img:
            return {"type": "error", "data": "⚠️ Не удалось создать изображение"}

        # ===============================
        # 🔥 ВОССТАНАВЛИВАЕМ СВЯЗКУ
        # ===============================
        state["image_current"] = img

        set_last_entity(user_id, {
            "type": "image",
            "data": img,
            "source": "engine_generate"
        })

        print("🧠 ENGINE SAVE: image_current + META")

        return {"type": "image", "data": img}

    except Exception as e:
        print("ENGINE GENERATE ERROR:", e)
        return {"type": "error", "data": "⚠️ Ошибка генерации"}


# ===== EDIT =====
async def edit(user_id, image_bytes, prompt, state):
    try:
        print("🧠 ENGINE EDIT (priority advanced)")

        # 🔥 защита (если вдруг нет image_bytes)
        if not image_bytes:
            print("⚠️ ENGINE: image_bytes is None")

        img = await asyncio.wait_for(
            edit_image_bytes(image_bytes, prompt),
            timeout=40
        )

        # fallback через path
        if not img:
            ctx = state.get("image_context") or {}
            path = ctx.get("path")

            if path:
                print("↩️ ENGINE EDIT FALLBACK → PATH")
                img = await asyncio.wait_for(
                    edit_image(path, prompt),
                    timeout=40
                )

        if not img:
            return {"type": "error", "data": "⚠️ Не удалось изменить изображение"}

        # ===============================
        # 🔥 СОХРАНЯЕМ ПОСЛЕ EDIT
        # ===============================
        state["image_current"] = img

        set_last_entity(user_id, {
            "type": "image",
            "data": img,
            "source": "engine_edit"
        })

        print("🧠 ENGINE SAVE AFTER EDIT")

        return {"type": "image", "data": img}

    except asyncio.TimeoutError:
        return {"type": "error", "data": "⏱ Таймаут редактирования"}

    except Exception as e:
        print("ENGINE EDIT ERROR:", e)
        return {"type": "error", "data": "⚠️ Ошибка редактирования"}


# ===== ANALYZE =====
async def analyze(path, state):
    return await analyze_image(path, state)
