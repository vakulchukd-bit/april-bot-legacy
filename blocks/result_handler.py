# blocks/result_handler.py

from aiogram.types import BufferedInputFile

# 🔥 ДОБАВЛЯЕМ генерацию
from blocks.image_module import process as image_generate


async def send_result(message, result, keyboard=None):
    if result["type"] == "text":
        await message.answer(result["content"], reply_markup=keyboard)

    elif result["type"] == "image":
        await message.answer_photo(
            BufferedInputFile(result["data"], filename="image.png"),
            caption=result.get("caption", ""),
            reply_markup=keyboard
        )

    # 🔥 НОВЫЙ БЛОК (НЕ ЛОМАЕТ СТАРЫЕ)
    elif result["type"] == "image_task":
        try:
            print("🖼 IMAGE TASK START")

            image_bytes = await image_generate(result["prompt"])

            print("🖼 IMAGE GENERATED")

            await message.answer_photo(
                BufferedInputFile(image_bytes, filename="image.png"),
                caption="🖼 Готово"
            )

        except Exception as e:
            print("🔥 IMAGE TASK ERROR:", e)
            await message.answer("❌ Ошибка при генерации изображения")

    elif result["type"] == "error":
        await message.answer(result["text"])
