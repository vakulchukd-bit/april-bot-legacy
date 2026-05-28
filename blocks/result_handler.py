# =========================================================
# 🧠 APRIL RESULT HANDLER
# =========================================================
#
# APRIL_FILE_ID:
# APRIL_RESULT_HANDLER
#
# ROLE:
# UNIFIED_TRANSPORT_LAYER
#
# INPUT:
# EXECUTOR_RESULT
# RENDERER_PAYLOAD
# MACHINE_RESPONSE
# WEB_MESSAGE
# TELEGRAM_MESSAGE
#
# OUTPUT:
# WEB_PAYLOAD
# TELEGRAM_RESPONSE
# STRUCTURED_RENDER_RESULT
#
# DEPENDENCIES:
# image_module
# canvas_formatter
# renderer_space
# response_decision
# presentation_layer
#
# =========================================================
#
# APRIL RESULT HANDLER
#
# Lightweight unified transport layer.
#
# Этот слой:
# - transport only;
# - renderer-safe;
# - payload-safe;
# - continuity-safe.
#
# Этот слой НЕ:
# - renderer authority;
# - fallback renderer;
# - fake serializer;
# - telegram-first core.
#
# =========================================================

print(
    "🧠 APRIL RESULT HANDLER LOADED"
)

# =========================================================
# 🔥 IMPORTS
# =========================================================

from aiogram.types import BufferedInputFile

from blocks.image_module import (
    process as image_generate
)

from blocks.canvas_formatter import (
    format_code_block,
    format_text
)

# =========================================================
# 🔥 MACHINE CHANNELS
# =========================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "executor",

    "target":
        "result_handler",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "source":
        "result_handler",

    "target":
        "botru_web_ui",

    "isolated":
        True
}

# =========================================================
# 🔥 CONSTANTS
# =========================================================

SAFE_RENDER_TYPES = {

    "function",
    "graph",
    "formula",
    "table",
    "diagram",
    "scene",
    "renderer",
    "blocks",
    "hybrid",
    "layout",
    "visual"
}

RESULT_PATCH_LOG = []

# =========================================================
# 🔥 LOG
# =========================================================

def safe_result_log(msg):

    try:

        print(
            "APRIL RESULT HANDLER:",
            msg
        )

        RESULT_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass


# =========================================================
# 🔥 HELPERS
# =========================================================

def is_renderer_result(result):

    try:

        if not isinstance(result, dict):

            return False

        r_type = result.get(
            "type"
        )

        if r_type in SAFE_RENDER_TYPES:

            return True

        structured_keys = {

            "blocks",
            "graph",
            "function",
            "formula",
            "layout",
            "scene"
        }

        return any(

            result.get(key) is not None

            for key in structured_keys
        )

    except Exception as e:

        safe_result_log(
            f"RENDER DETECTION ERROR: {e}"
        )

        return False


def is_web_message(message):

    try:

        if message is None:

            return False

        web_flags = [

            "is_web",
            "web_mode",
            "renderer_mode",
            "april_web",
            "space_mode"
        ]

        for flag in web_flags:

            if getattr(

                message,
                flag,
                False

            ):

                return True

        return any(

            hasattr(message, attr)

            for attr in [

                "headers",
                "client",
                "scope"
            ]
        )

    except Exception as e:

        safe_result_log(
            f"WEB DETECTION ERROR: {e}"
        )

        return False


def is_machine_payload(result):

    try:

        if not isinstance(
            result,
            dict
        ):

            return False

        return result.get(
            "machine_only",
            False
        )

    except:

        return False


# =========================================================
# 🔥 NORMALIZATION
# =========================================================

def normalize_result(result):

    safe_result_log(
        "NORMALIZE RESULT START"
    )

    if not result:

        return {

            "type": "text",

            "content":
                "⚠️ Пустой ответ"
        }

    if not isinstance(result, dict):

        return {

            "type": "text",

            "content":
                str(result)
        }

    result_type = result.get(
        "type",
        "text"
    )

    # =====================================================
    # 🔥 STRUCTURED PASS
    # =====================================================

    if is_renderer_result(result):

        safe_result_log(
            f"STRUCTURED: {result_type}"
        )

        return result

    # =====================================================
    # 🔥 MACHINE PASS
    # =====================================================

    if is_machine_payload(result):

        safe_result_log(
            "MACHINE PAYLOAD PRESERVED"
        )

        return result

    # =====================================================
    # 🔥 SIMPLE TYPES
    # =====================================================

    simple_map = {

        "text": {

            "type": "text",

            "content":

                result.get("content")

                or result.get("data")

                or ""
        },

        "code": {

            "type": "code",

            "code":
                result.get("code", ""),

            "file":
                result.get("file"),

            "block":
                result.get("block")
        },

        "file": {

            "type": "file",

            "data":
                result.get("data"),

            "filename":
                result.get(
                    "filename",
                    "file.py"
                )
        },

        "image": {

            "type": "image",

            "data":
                result.get("data"),

            "caption":
                result.get(
                    "caption",
                    ""
                ),

            "meta":
                result.get(
                    "meta",
                    {}
                )
        },

        "image_task": {

            "type": "image_task",

            "prompt":
                result.get("prompt")
        },

        "error": {

            "type": "error",

            "text":

                result.get("text")

                or result.get("data")

                or "⚠️ Ошибка"
        }
    }

    if result_type in simple_map:

        return simple_map[
            result_type
        ]

    # =====================================================
    # 🔥 FALLBACK
    # =====================================================

    safe_result_log(
        f"SAFE FALLBACK: {result_type}"
    )

    return {

        "type": "text",

        "content":

            result.get("content")

            or result.get("data")

            or "⚠️ Не удалось обработать результат"
    }


# =========================================================
# 🔥 WEB PAYLOAD
# =========================================================

def build_web_payload(result):

    result_type = result.get(
        "type",
        "text"
    )

    safe_result_log(
        f"WEB PAYLOAD BUILD: {result_type}"
    )

    # =====================================================
    # 🔥 MACHINE SAFE
    # =====================================================

    if is_machine_payload(result):

        return result

    # =====================================================
    # 🔥 RENDER SAFE
    # =====================================================

    if result_type in SAFE_RENDER_TYPES:

        safe_result_log(
            f"WEB STRUCTURED: {result_type}"
        )

        return result

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if result_type == "text":

        return {

            "type": "text",

            "content":
                result.get(
                    "content",
                    ""
                )
        }

    return result


# =========================================================
# 🔥 TELEGRAM VISUAL COMMENT
# =========================================================

def build_telegram_visual_comment(
    result
):

    result_type = result.get(
        "type",
        "text"
    )

    comments = {

        "function":
            "📈 Функция подготовлена.",

        "graph":
            "📊 Графическая сцена подготовлена.",

        "formula":
            "🧠 Формула подготовлена.",

        "blocks":
            "🧩 Пространственная сцена подготовлена.",

        "diagram":
            "🧩 Диаграмма подготовлена.",

        "table":
            "📋 Таблица подготовлена."
    }

    return comments.get(

        result_type,

        "🧠 Structured payload generated."
    )


# =========================================================
# 🔥 TELEGRAM SENDERS
# =========================================================

async def send_text(
    message,
    result,
    keyboard=None
):

    safe_result_log(
        "SEND TEXT"
    )

    content = format_text(

        result.get(
            "content",
            ""
        )
    )

    if not content:

        content = "⚠️ Пустой ответ"

    await message.answer(

        content,

        reply_markup=keyboard
    )


async def send_code(
    message,
    result,
    keyboard=None
):

    safe_result_log(
        "SEND CODE"
    )

    code = format_code_block(

        result.get("code"),

        result.get("file"),

        result.get("block")
    )

    await message.answer(

        f"```python\n{code}\n```",

        reply_markup=keyboard
    )


async def send_file(
    message,
    result
):

    safe_result_log(
        "SEND FILE"
    )

    code = result.get(
        "data",
        ""
    )

    filename = result.get(
        "filename",
        "file.py"
    )

    await message.answer_document(

        BufferedInputFile(

            code.encode("utf-8"),

            filename=filename
        ),

        caption=f"📁 {filename}"
    )


async def send_image(
    message,
    result,
    keyboard=None
):

    safe_result_log(
        "SEND IMAGE"
    )

    if not result.get("data"):

        await message.answer(
            "⚠️ Нет изображения"
        )

        return

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


# =========================================================
# 🔥 MAIN SEND
# =========================================================

async def send_result(
    message,
    result,
    keyboard=None
):

    safe_result_log(
        "SEND RESULT START"
    )

    result = normalize_result(
        result
    )

    result_type = result.get(
        "type",
        "text"
    )

    safe_result_log(
        f"RESULT TYPE: {result_type}"
    )

    # =====================================================
    # 🔥 WEB MODE
    # =====================================================

    if is_web_message(message):

        safe_result_log(
            "WEB MODE ACTIVE"
        )

        return build_web_payload(
            result
        )

    # =====================================================
    # 🔥 TELEGRAM MODE
    # =====================================================

    safe_result_log(
        "TELEGRAM MODE ACTIVE"
    )

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if result_type == "text":

        await send_text(

            message,
            result,
            keyboard
        )

        return

    # =====================================================
    # 🔥 CODE
    # =====================================================

    if result_type == "code":

        await send_code(

            message,
            result,
            keyboard
        )

        return

    # =====================================================
    # 🔥 FILE
    # =====================================================

    if result_type == "file":

        await send_file(
            message,
            result
        )

        return

    # =====================================================
    # 🔥 IMAGE
    # =====================================================

    if result_type == "image":

        await send_image(

            message,
            result,
            keyboard
        )

        return

    # =====================================================
    # 🔥 STRUCTURED
    # =====================================================

    if result_type in SAFE_RENDER_TYPES:

        comment = build_telegram_visual_comment(
            result
        )

        await message.answer(

            comment,

            reply_markup=keyboard
        )

        return

    # =====================================================
    # 🔥 IMAGE TASK
    # =====================================================

    if result_type == "image_task":

        try:

            await message.answer(
                "🎨 Создаю изображение..."
            )

            user_id = message.from_user.id

            result_img = await image_generate(

                user_id,

                result["prompt"],

                {}
            )

            if (

                not result_img
                or result_img.get("type") != "image"
            ):

                await message.answer(
                    "⚠️ Не удалось создать изображение"
                )

                return

            await send_image(

                message,
                result_img
            )

            return

        except Exception as e:

            safe_result_log(
                f"IMAGE TASK ERROR: {e}"
            )

            await message.answer(
                "⚠️ Ошибка генерации изображения"
            )

            return

    # =====================================================
    # 🔥 ERROR
    # =====================================================

    if result_type == "error":

        await message.answer(

            result.get("text")

            or "⚠️ Ошибка"
        )

        return

    # =====================================================
    # 🔥 FINAL FALLBACK
    # =====================================================

    safe_result_log(
        f"UNKNOWN TYPE: {result_type}"
    )

    await message.answer(

        "⚠️ Неизвестный тип результата",

        reply_markup=keyboard
    )

    safe_result_log(
        "SEND RESULT COMPLETE"
    )
