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

    # 🔥 НОВОЕ: файл
    if r_type == "file":
        return {
            "type": "file",
            "data": result.get("data"),
            "filename": result.get("filename", "file.py")
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

    # 🔥 НОВОЕ: ОТПРАВКА ФАЙЛА
    elif result["type"] == "file":
        code = result.get("data") or ""
        filename = result.get("filename", "file.py")

        # 🔥 ДОБАВЛЯЕМ КОММЕНТ ВНУТРЬ (как ты хотел)
        code = format_code_block(code, filename, None)

        file_bytes = code.encode("utf-8")

        await message.answer_document(
            BufferedInputFile(file_bytes, filename=filename),
            caption=f"📁 {filename}"
        )

    elif result["type"] == "image":
        # 🔥 ИНДИКАТОР РАБОТЫ
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

            # 🔥 ИНДИКАТОР
            await message.answer("🎨 Создаю изображение...")

            # 🔥 ВАЖНО: передаём всё, что нужно
            user_id = message.from_user.id
            state = {}  # временно, чтобы не ломать систему

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
