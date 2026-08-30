# blocks/image_engine.py

import asyncio
import tempfile
import time
from pathlib import Path

# берём существующие функции, НИЧЕГО не удаляем
from blocks.image_module import (
    generate_image_v2,
    generate_image
)

from blocks.image_edit_module import (
    edit_image_bytes,
    edit_image
)

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

    try:

        use_advanced = is_complex_prompt(
            prompt
        )

        img = None

        # ===============================
        # 🔥 2.0 ROUTE (СЛОЖНЫЕ ЗАДАЧИ)
        # ===============================

        if use_advanced:

            print(
                "🧠 ENGINE: 2.0 ACTIVE (complex prompt)"
            )

            try:

                img = await generate_image_v2(
                    prompt
                )

            except Exception as e:

                print(
                    "⚠️ 2.0 GENERATE ERROR:",
                    e
                )

        # ===============================
        # 🔥 ОБЫЧНЫЙ РЕЖИМ
        # ===============================

        if not img:

            print(
                "⚡ ENGINE: using FAST V2"
            )

            img = await generate_image_v2(
                prompt
            )

        # ===============================
        # 🔥 FALLBACK
        # ===============================

        if not img:

            print(
                "↩️ ENGINE FALLBACK → V1"
            )

            img = await generate_image(
                prompt
            )

        # ===============================
        # 🔥 FAIL
        # ===============================

        if not img:

            return {

                "type": "error",

                "data":
                    "⚠️ Генерация изображений временно отключена во время Gemini migration"
            }

        # 🔥 SAVE BYTES
        state["image_current"] = img

        # 🔥 СОХРАНЯЕМ ФАЙЛ
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

            print(
                f"📂 ENGINE FILE SAVED: {path}"
            )

        # 🔥 META
        set_last_entity(
            user_id,
            {
                "type": "image",
                "data": img,
                "source": "engine_generate"
            }
        )

        print(
            "🧠 ENGINE SAVE: image_current + META"
        )

        return {

            "type": "image",

            "data": img
        }

    except Exception as e:

        print(
            "ENGINE GENERATE ERROR:",
            e
        )

        return {

            "type": "error",

            "data":
                "⚠️ Ошибка генерации"
        }


# ===== EDIT =====
async def edit(
    user_id,
    image_bytes,
    prompt,
    state
):

    try:

        print(
            "🛑 IMAGE EDIT DISABLED FOR GEMINI TEST MODE"
        )

        return {

            "type": "error",

            "data":
                "⚠️ Редактирование изображений временно отключено во время Gemini migration"
        }

        print(
            "🧠 ENGINE EDIT START"
        )

        img = None

        use_advanced = is_complex_prompt(
            prompt
        )

        # ===============================
        # 🔥 2.0 EDIT (СЛОЖНЫЕ ЗАДАЧИ)
        # ===============================

        if use_advanced and image_bytes:

            print(
                "🧠 ENGINE: 2.0 EDIT ACTIVE"
            )

            try:

                img = await asyncio.wait_for(

                    edit_image_bytes(
                        image_bytes,
                        prompt
                    ),

                    timeout=40
                )

            except Exception as e:

                print(
                    "⚠️ 2.0 EDIT ERROR:",
                    e
                )

        # ===============================
        # 🔥 1. BYTES
        # ===============================

        if not img and image_bytes:

            try:

                img = await asyncio.wait_for(

                    edit_image_bytes(
                        image_bytes,
                        prompt
                    ),

                    timeout=40
                )

                print(
                    "🧠 EDIT FROM BYTES"
                )

            except Exception as e:

                print(
                    "⚠️ ENGINE BYTES ERROR:",
                    e
                )

        # ===============================
        # 🔥 2. FALLBACK → PATH
        # ===============================

        if not img:

            print(
                "⚠️ ENGINE EDIT: bytes failed → trying path"
            )

            ctx = state.get(
                "image_context"
            ) or {}

            path = ctx.get("path")

            if path:

                try:

                    img = await asyncio.wait_for(

                        edit_image(
                            path,
                            prompt
                        ),

                        timeout=40
                    )

                except Exception as e:

                    print(
                        "⚠️ ENGINE PATH ERROR:",
                        e
                    )

        # ===============================
        # 🔥 FAIL
        # ===============================

        if not img:

            print(
                "❌ ENGINE EDIT FINAL FAIL"
            )

            return {

                "type": "error",

                "data":
                    "⚠️ Не удалось изменить изображение"
            }

        # 🔥 SAVE BYTES
        state["image_current"] = img

        # 🔥 ОБНОВЛЯЕМ ФАЙЛ
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

            print(
                f"📂 ENGINE FILE UPDATED: {path}"
            )

        # 🔥 META
        set_last_entity(
            user_id,
            {
                "type": "image",
                "data": img,
                "source": "engine_edit"
            }
        )

        print(
            "🧠 ENGINE SAVE AFTER EDIT"
        )

        return {

            "type": "image",

            "data": img
        }

    except asyncio.TimeoutError:

        print(
            "⏱ ENGINE EDIT TIMEOUT"
        )

        return {

            "type": "error",

            "data":
                "⏱ Таймаут редактирования"
        }

    except Exception as e:

        print(
            "ENGINE EDIT ERROR:",
            e
        )

        return {

            "type": "error",

            "data":
                "⚠️ Ошибка редактирования"
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
