import traceback
import time

from aiogram.types import BufferedInputFile

from blocks.image_module import (
    process as image_generate
)

# =====================================================
# 🧠 APRIL ERROR ORCHESTRATION
# =====================================================

"""
Unified error handling layer.

Этот слой:

✅ удерживает stable delivery
✅ удерживает renderer continuity
✅ удерживает image pipeline
✅ удерживает structured result flow
✅ помогает executor recovery

❌ НЕ telegram-only layer
❌ НЕ trigger router
❌ НЕ fallback chaos system
❌ НЕ hidden rerouting engine

Главная задача:
безопасная delivery orchestration.
"""

# =====================================================
# 🔥 ADMIN
# =====================================================

ADMIN_ID = 2016592532

# =====================================================
# 🔥 ERROR STORAGE
# =====================================================

error_log = []

MAX_ERROR_LOG = 20

# =====================================================
# 🔥 RESULT TYPES
# =====================================================

RESULT_TEXT = "text"

RESULT_IMAGE = "image"

RESULT_IMAGE_TASK = "image_task"

RESULT_ERROR = "error"

# =====================================================
# 🔥 MODALITY TYPES
# =====================================================

VISUAL_MODALITIES = {

    "image",
    "image_task",
    "graph",
    "diagram",
    "formula",
    "scene",
    "renderer"
}

# =====================================================
# 🔥 ERROR SEMANTICS
# =====================================================

ERROR_CONTEXT_VISUAL = "visual"

ERROR_CONTEXT_EXECUTION = "execution"

ERROR_CONTEXT_RENDERER = "renderer"

ERROR_CONTEXT_UNKNOWN = "unknown"

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(text):

    return (
        text or ""
    ).strip()


def normalize_lower(text):

    return normalize_text(
        text
    ).lower()


def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )


# =====================================================
# 🔥 ERROR STORAGE
# =====================================================

def log_error(error_text):

    error_log.append(
        error_text
    )

    if len(error_log) > MAX_ERROR_LOG:

        error_log.pop(0)


def get_errors():

    return error_log


# =====================================================
# 🔥 RESULT ANALYSIS
# =====================================================

def detect_result_modality(
    result
):

    if not result:

        return ERROR_CONTEXT_UNKNOWN

    result_type = result.get(
        "type",
        RESULT_TEXT
    )

    if result_type in VISUAL_MODALITIES:

        return ERROR_CONTEXT_VISUAL

    return ERROR_CONTEXT_EXECUTION


def is_visual_result(
    result
):

    result_type = result.get(
        "type",
        RESULT_TEXT
    )

    return result_type in VISUAL_MODALITIES


# =====================================================
# 🔥 SAFE USER ERROR
# =====================================================

def build_user_error_message(
    text=None,
    modality=None
):

    lowered = normalize_lower(
        text
    )

    # =================================================
    # 🔥 VISUAL
    # =====================================================

    if modality == ERROR_CONTEXT_VISUAL:

        return (
            "🎨 Не удалось "
            "обработать визуальный запрос. "
            "Попробуй изменить запрос."
        )

    # =================================================
    # 🔥 IMAGE INTENT
    # =====================================================

    if contains_any(

        lowered,

        [
            "картин",
            "изображ",
            "нарисуй",
            "сгенерир",
            "фото",
            "арт",
            "график",
            "схема",
            "диаграм"
        ]
    ):

        return (
            "🖼 Не удалось "
            "выполнить визуальный запрос."
        )

    # =================================================
    # 🔥 DEFAULT
    # =====================================================

    return (
        "⚠️ Не получилось "
        "выполнить запрос. "
        "Попробуй ещё раз."
    )


# =====================================================
# 🔥 SAFE IMAGE TASK
# =====================================================

async def process_image_task(
    message,
    result
):

    print(
        "🖼 IMAGE TASK START"
    )

    user_id = message.from_user.id

    state = {}

    prompt = result.get(
        "prompt",
        ""
    )

    result_img = await image_generate(

        user_id,

        prompt,

        state
    )

    print(
        "🖼 IMAGE MODULE RESULT:",
        result_img
    )

    if not result_img:

        await message.answer(

            "❌ Не удалось "
            "создать изображение"
        )

        return

    result_type = result_img.get(
        "type"
    )

    if result_type != RESULT_IMAGE:

        await message.answer(

            "❌ Visual pipeline "
            "вернул некорректный результат"
        )

        return

    await message.answer_photo(

        BufferedInputFile(

            result_img["data"],

            filename="image.png"
        ),

        caption=result_img.get(
            "caption",
            "🖼 Готово"
        )
    )


# =====================================================
# 🔥 RESULT DELIVERY
# =====================================================

async def send_result(
    message,
    result,
    keyboard=None
):

    try:

        if not result:
            return

        result_type = result.get(
            "type",
            RESULT_TEXT
        )

        # =================================================
        # 🔥 TEXT
        # =====================================================

        if result_type == RESULT_TEXT:

            await message.answer(

                result.get(
                    "content",
                    ""
                ),

                reply_markup=keyboard
            )

            return

        # =================================================
        # 🔥 IMAGE
        # =====================================================

        if result_type == RESULT_IMAGE:

            await message.answer_photo(

                BufferedInputFile(

                    result["data"],

                    filename="image.png"
                ),

                caption=result.get(
                    "caption",
                    ""
                ),

                reply_markup=keyboard
            )

            return

        # =================================================
        # 🔥 IMAGE TASK
        # =====================================================

        if result_type == RESULT_IMAGE_TASK:

            try:

                await process_image_task(

                    message,

                    result
                )

            except Exception as e:

                print(
                    "🔥 IMAGE TASK ERROR:",
                    e
                )

                await message.answer(

                    "❌ Ошибка "
                    "визуального pipeline"
                )

            return

        # =================================================
        # 🔥 ERROR
        # =====================================================

        if result_type == RESULT_ERROR:

            await message.answer(

                result.get(
                    "text",
                    "⚠️ Ошибка"
                )
            )

            return

        # =================================================
        # 🔥 UNKNOWN
        # =====================================================

        await message.answer(

            str(
                result.get(
                    "content",
                    ""
                )
            )
        )

    except Exception as e:

        await handle_error(

            message.bot,

            message,

            e,

            context="send_result",

            modality=detect_result_modality(
                result
            )
        )


# =====================================================
# 🔥 ERROR HANDLER
# =====================================================

async def handle_error(

    bot,

    user_message,

    error,

    context="",

    modality=ERROR_CONTEXT_UNKNOWN
):

    """
    Unified error handling.

    Пользователь:
    - получает safe response.

    Admin:
    - получает structured traceback.
    """

    user_id = getattr(

        user_message.from_user,

        "id",

        "unknown"
    )

    text = getattr(
        user_message,
        "text",
        None
    )

    # =================================================
    # 🔥 USER RESPONSE
    # =====================================================

    try:

        user_text = build_user_error_message(

            text=text,

            modality=modality
        )

        await user_message.answer(
            user_text
        )

    except:

        try:

            await bot.send_message(

                user_id,

                "⚠️ Ошибка выполнения."
            )

        except:
            pass

    # =================================================
    # 🔥 ERROR LOG
    # =====================================================

    error_text = f"""
🕒 {time.strftime('%H:%M:%S')}
👤 {user_id}
📦 {context}
❌ {str(error)}
"""

    log_error(
        error_text
    )

    # =================================================
    # 🔥 FULL TRACE
    # =====================================================

    full_error = f"""
❌ APRIL ERROR

🕒 Время:
{time.strftime('%Y-%m-%d %H:%M:%S')}

👤 User ID:
{user_id}

📩 Сообщение:
{text}

📦 Контекст:
{context}

🧠 Modality:
{modality}

❌ Ошибка:
{str(error)}

📄 Traceback:
{traceback.format_exc()}
"""

    full_error = full_error[:4000]

    # =================================================
    # 🔥 ADMIN ALERT
    # =====================================================

    try:

        await bot.send_message(

            ADMIN_ID,

            full_error
        )

    except:
        pass
