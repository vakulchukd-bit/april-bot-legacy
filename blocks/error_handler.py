# =====================================================
# 🧠 APRIL ERROR ORCHESTRATION CORE
# =====================================================

import traceback
import time

from aiogram.types import BufferedInputFile

from blocks.image_module import (
    process as image_generate
)

from blocks.tariffs_config import (
    ADMIN_ID
)

# =====================================================
# 🧠 APRIL ERROR ORCHESTRATION
# =====================================================

"""
APRIL ERROR ORCHESTRATION CORE

APRIL_FILE_ID:
APRIL_ERROR_ORCHESTRATION_CORE

ROLE:
SAFE_DELIVERY_AND_PIPELINE_STABILIZATION

INPUT:
EXECUTOR_RESULTS
RENDERER_RESULTS
IMAGE_PIPELINE_RESULTS
EXCEPTION_OBJECTS
DELIVERY_CONTEXT

OUTPUT:
SAFE_USER_RESPONSE
ADMIN_DIAGNOSTICS
PIPELINE_RECOVERY
STRUCTURED_ERROR_REPORT

THIS FILE IS:
- unified error handling layer
- renderer continuity stabilizer
- image pipeline protector
- structured delivery orchestrator
- executor recovery helper
- admin diagnostics bridge

THIS FILE IS NOT:
- telegram-only layer
- orchestration router
- recursive retry engine
- hidden fallback chaos system
- frontend renderer
- trigger routing layer

GOLDEN APRIL RULES:
- stable delivery first
- preserve renderer continuity
- preserve modality structure
- avoid recursive chaos
- avoid hidden rerouting
- safe user-facing responses
- machine-isolated diagnostics
"""

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

ERROR_TASK_CHANNEL = {

    "channel":
        "error_machine_task_channel",

    "isolated":
        True
}

ERROR_RESPONSE_CHANNEL = {

    "channel":
        "error_machine_response_channel",

    "isolated":
        True
}

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
# 🔥 PIPELINE LOGGING
# =====================================================

def log_error_input(

    context,
    modality,
    user_id=None
):

    """
    INPUT MACHINE TRACE

    Used by:
    - analyzer
    - admin monitoring
    - governance diagnostics
    - recovery tracing
    """

    return {

        "file_id":
            "APRIL_ERROR_ORCHESTRATION_CORE",

        "event":
            "error_input",

        "channel":
            ERROR_TASK_CHANNEL,

        "context":
            context,

        "modality":
            modality,

        "user_id":
            user_id,

        "machine_only":
            True
    }


def log_error_output(

    handled=True,
    context=None
):

    """
    OUTPUT MACHINE TRACE

    Used internally by:
    - analyzer
    - diagnostics systems
    - admin observability
    """

    return {

        "file_id":
            "APRIL_ERROR_ORCHESTRATION_CORE",

        "event":
            "error_output",

        "channel":
            ERROR_RESPONSE_CHANNEL,

        "handled":
            handled,

        "context":
            context,

        "machine_only":
            True
    }

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

    return {

        "channel":
            ERROR_RESPONSE_CHANNEL,

        "errors":
            error_log,

        "machine_only":
            True
    }

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

    """
    Stable image task execution.

    Preserves:
    - image continuity
    - modality integrity
    - renderer-safe delivery
    """

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

    """
    Unified stable delivery layer.

    Supports:
    - text responses
    - visual responses
    - image tasks
    - renderer-safe payloads
    """

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

    User:
    - receives safe response.

    Admin:
    - receives structured traceback.
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

    log_error_input(

        context=context,

        modality=modality,

        user_id=user_id
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

    log_error_output(

        handled=True,

        context=context
    )
