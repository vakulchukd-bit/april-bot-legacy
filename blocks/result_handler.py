# blocks/result_handler.py

from aiogram.types import BufferedInputFile

from blocks.image_module import process as image_generate
from blocks.canvas_formatter import format_code_block, format_text  # 🔥 ДОБАВЛЕНО


async def send_result(message, result, keyboard=None):
    if result["type"] == "text":
        content = result.get("content") or result.get("data")  # 🔥 УНИФИКАЦИЯ

        content = format_text(content)  # 🔥 ФОРМАТИРОВАНИЕ

        await message.answer(content, reply_markup=keyboard)

    # 🔥 НОВОЕ: ПОДДЕРЖКА КОДА
    elif result["type"] == "code":
        code = format_code_block(
            result.get("code"),
            result.get("file"),
            result.get("block")
        )

        await message.answer(f"```python\n{code}\n```", reply_markup=keyboard)

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
        await message.answer(result["text"])
