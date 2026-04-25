# blocks/image_edit_module.py

import base64
import asyncio
import tempfile
import os
from openai import OpenAI

client = OpenAI()


# ===== СОХРАНЕНИЕ В ФАЙЛ =====
def save_temp_image(image_bytes):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(image_bytes)
    tmp.close()
    return tmp.name


# ===== УДАЛЕНИЕ =====
def cleanup(path):
    try:
        os.remove(path)
    except:
        pass


# ===== EDIT =====
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


# ===== PROCESS =====
async def process(user_id, text, state):
    try:
        ctx = state.get("image_context")

        if not ctx or not ctx.get("image_bytes"):
            return {
                "type": "error",
                "data": "⚠️ Нет изображения для редактирования"
            }

        prompt = text.strip()

        if not prompt:
            return {
                "type": "error",
                "data": "❌ Пустой запрос"
            }

        img = await asyncio.wait_for(
            edit_image_bytes(ctx["image_bytes"], prompt),
            timeout=60
        )

        if not img:
            return {
                "type": "error",
                "data": "⚠️ Не получилось изменить изображение"
            }

        # 🔥 СОХРАНЯЕМ КАК НОВУЮ ВЕРСИЮ
        new_ctx = {
            "type": "edited",
            "prompt": prompt,
            "hint": prompt,
            "image_bytes": img
        }

        state["image_context"] = new_ctx

        return {
            "type": "image",
            "data": img
        }

    except asyncio.TimeoutError:
        return {
            "type": "error",
            "data": "⏱️ Долго обрабатывается, попробуй ещё раз"
        }

    except Exception as e:
        return {
            "type": "error",
            "data": "⚠️ Ошибка при редактировании",
            "error": str(e)
        }
