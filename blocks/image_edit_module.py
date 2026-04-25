# blocks/image_edit_module.py

import base64
import asyncio
import tempfile
import os
from openai import OpenAI

client = OpenAI()


# ===== СТАРАЯ ЛОГИКА (НЕ ТРОГАЕМ) =====
async def edit_image(image_path, prompt):
    def run():
        with open(image_path, "rb") as f:
            result = client.images.edit(
                model="gpt-image-1",
                image=f,
                prompt=prompt
            )

        if not result or not result.data:
            return None

        try:
            return base64.b64decode(result.data[0].b64_json)
        except Exception:
            return None

    return await asyncio.to_thread(run)


# ===== НОВОЕ: BYTES → FILE =====
def save_temp_image(image_bytes):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(image_bytes)
    tmp.close()
    return tmp.name


def cleanup(path):
    try:
        os.remove(path)
    except:
        pass


# ===== НОВОЕ: EDIT ЧЕРЕЗ BYTES =====
async def edit_image_bytes(image_bytes, prompt):
    def run():
        path = save_temp_image(image_bytes)

        try:
            with open(path, "rb") as f:
                result = client.images.edit(
                    model="gpt-image-1",
                    image=f,
                    prompt=prompt
                )

            if not result or not result.data:
                return None

            return base64.b64decode(result.data[0].b64_json)

        except Exception as e:
            print("🔥 EDIT ERROR:", e)
            return None

        finally:
            cleanup(path)

    return await asyncio.to_thread(run)


# ===== PROCESS (РАСШИРЕН, НО НЕ СЛОМАН) =====
async def process(user_id, image_path, prompt, state=None):
    try:
        img = None

        # 🔥 ЕСЛИ ЕСТЬ STATE → РАБОТАЕМ С BYTES
        if state:
            ctx = state.get("image_context")

            if ctx and ctx.get("image_bytes"):
                img = await asyncio.wait_for(
                    edit_image_bytes(ctx["image_bytes"], prompt),
                    timeout=60
                )

                if img:
                    # 🔥 СОХРАНЯЕМ НОВУЮ ВЕРСИЮ
                    new_ctx = {
                        "type": "edited",
                        "prompt": prompt,
                        "hint": prompt,
                        "image_bytes": img
                    }
                    state["image_context"] = new_ctx

        # 🔥 FALLBACK (СТАРАЯ ЛОГИКА)
        if not img:
            img = await asyncio.wait_for(
                edit_image(image_path, prompt),
                timeout=40
            )

        if not img:
            return {
                "type": "error",
                "data": None,
                "error": "edit_failed"
            }

        return {
            "type": "image",
            "data": img
        }

    except asyncio.TimeoutError:
        return {
            "type": "error",
            "data": None,
            "error": "timeout"
        }

    except Exception as e:
        return {
            "type": "error",
            "data": None,
            "error": str(e)
        }
