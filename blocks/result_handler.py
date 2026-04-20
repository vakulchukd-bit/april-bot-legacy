# blocks/result_handler.py

from aiogram.types import BufferedInputFile

async def send_result(message, result, keyboard=None):
    if result["type"] == "text":
        await message.answer(result["content"], reply_markup=keyboard)

    elif result["type"] == "image":
        await message.answer_photo(
            BufferedInputFile(result["data"], filename="image.png"),
            caption=result.get("caption", ""),
            reply_markup=keyboard
        )

    elif result["type"] == "error":
        await message.answer(result["text"])
