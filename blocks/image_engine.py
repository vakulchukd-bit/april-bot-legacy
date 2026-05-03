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

        # 🔥 SAVE
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

        img = None

        # ===============================
        # 🔥 1. ПЫТАЕМСЯ ЧЕРЕЗ BYTES
        # ===============================
        if image_bytes:
            try:
                img = await asyncio.wait_for(
                    edit_image_bytes(image_bytes, prompt),
                    timeout=40
                )
            except Exception as e:
                print("⚠️ ENGINE BYTES ERROR:", e)

        # ===============================
        # 🔥 2. FALLBACK → PATH
        # ===============================
        if not img:
            print("⚠️ ENGINE EDIT: bytes failed → trying path")

            ctx = state.get("image_context") or {}
            path = ctx.get("path")

            if path:
                try:
                    img = await asyncio.wait_for(
                        edit_image(path, prompt),
                        timeout=40
                    )
                except Exception as e:
                    print("⚠️ ENGINE PATH ERROR:", e)

        # ===============================
        # 🔥 3. ЕСЛИ ВСЁ УПАЛО
        # ===============================
        if not img:
            print("❌ ENGINE EDIT FINAL FAIL")
            return {"type": "error", "data": "⚠️ Не удалось изменить изображение"}

        # ===============================
        # 🔥 SAVE ПОСЛЕ EDIT
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
        print("⏱ ENGINE EDIT TIMEOUT")
        return {"type": "error", "data": "⏱ Таймаут редактирования"}

    except Exception as e:
        print("ENGINE EDIT ERROR:", e)
        return {"type": "error", "data": "⚠️ Ошибка редактирования"}


# ===== ANALYZE =====
async def analyze(path, state):
    return await analyze_image(path, state)
