# blocks/result_handler.py

from aiogram.types import BufferedInputFile

from blocks.image_module import process as image_generate
from blocks.canvas_formatter import format_code_block, format_text  # 🔥 ДОБАВЛЕНО


# 🔥 НОВОЕ: НОРМАЛИЗАЦИЯ RESULT
def normalize_result(result):
    if not result or not isinstance(result, dict):
        return {"type": "text", "content": "⚠️ Пустой ответ"}

    r_type = result.get("type")

    # 🔥 текст
    if r_type == "text":
        content = result.get("content") or result.get("data") or ""
        return {"type": "text", "content": content}

    # 🔥 код
    if r_type == "code":
        return {
            "type": "code",
            "code": result.get("code") or "",
            "file": result.get("file"),
            "block": result.get("block")
        }

    # 🔥 изображение
    if r_type == "image":
        return {
            "type": "image",
            "data": result.get("data"),
            "caption": result.get("caption", ""),
            "meta": result.get("meta", {})
        }

    # 🔥 image task
    if r_type == "image_task":
        return {
            "type": "image_task",
            "prompt": result.get("prompt")
        }

    # 🔥 ошибка
    if r_type == "error":
        return {
            "type": "error",
            "text": result.get("text") or result.get("data") or "⚠️ Ошибка"
        }

    # 🔥 fallback
    return {"type": "text", "content": str(result)}


async def send_result(message, result, keyboard=None):
    result = normalize_result(result)  # 🔥 ВКЛЮЧАЕМ НОРМАЛИЗАЦИЮ

    if result["type"] == "text":
        content = format_text(result.get("content"))

        if not content:
            content = "⚠️ Пустой ответ"

        await message.answer(content, reply_markup=keyboard)

    elif result["type"] == "code":
        code = format_code_block(
            result.get("code"),
            result.get("file"),
            result.get("block")
        )

        await message.answer(f"```python\n{code}\n```", reply_markup=keyboard)

    elif result["type"] == "image":
        # 🔥 ИНДИКАТОР
        try:
            meta = result.get("meta", {})
            source = meta.get("source")

            if source == "math_graph":
                await message.answer("📊 Строю график...")
            else:
                await message.answer("🧠 Обрабатываю...")

        except Exception as e:
            print("🔥 INDICATOR ERROR:", e)

        if not result.get("data"):
            await message.answer("⚠️ Ошибка: нет данных изображения")
            return

        await message.answer_photo(
            BufferedInputFile(result["data"], filename="image.png"),
            caption=result.get("caption", ""),
            reply_markup=keyboard
        )

    elif result["type"] == "image_task":
        try:
            print("🖼 IMAGE TASK START")

            await message.answer("🎨 Создаю изображение...")

            user_id = message.from_user.id
            state = {}

            result_img = await image_generate(user_id, result["prompt"], state)

            print("🖼 IMAGE MODULE RESULT:", result_img)

            if not result_img or result_img["type"] != "image":
                await message.answer("❌ Не удалось создать изображение")
                return

            await message.answer_photo(
                BufferedInputFile(result_img["data"], filename="image.png"),
                caption="🖼 Готово"
            )

        except Exception as e:
            print("🔥 IMAGE TASK ERROR:", e)
            await message.answer("❌ Ошибка при генерации изображения")

    elif result["type"] == "error":
        await message.answer(result.get("text") or "⚠️ Ошибка")
