# =========================================================
# 🧠 APRIL RESULT HANDLER
# =========================================================

"""
APRIL RESULT HANDLER — SPACE RENDER TRANSPORT

Этот модуль больше НЕ:
- telegram-first renderer;
- legacy string transport;
- [[function:x]] bridge;
- fallback visual serializer;
- pseudo-render layer.

Теперь это:
- unified result transport;
- renderer-space bridge;
- web-first payload dispatcher;
- structured multimodal carrier;
- continuity-safe presentation layer.

APRIL PRINCIPLES:

1. renderer-first
2. structured payloads before text
3. no telegram authority
4. no fake renderer strings
5. no hidden fallback rendering
6. pure scene transport
7. provider-safe delivery
"""

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
# 🔥 RENDER TYPES
# =========================================================

SAFE_RENDER_TYPES = [

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
]

# =========================================================
# 🔥 PATCH LOG
# =========================================================

RESULT_PATCH_LOG = []


def safe_result_log(msg):

    try:

        print("RESULT HANDLER:", msg)

        RESULT_PATCH_LOG.append(msg)

    except:
        pass


# =========================================================
# 🔥 RENDER DETECTION
# =========================================================

def is_renderer_result(result):

    try:

        if not isinstance(result, dict):
            return False

        r_type = result.get("type")

        if r_type in SAFE_RENDER_TYPES:
            return True

        structured_keys = [

            "blocks",
            "graph",
            "function",
            "formula",
            "layout",
            "scene"
        ]

        for key in structured_keys:

            if result.get(key) is not None:
                return True

        return False

    except Exception as e:

        print(
            "RENDER DETECTION ERROR:",
            e
        )

        return False


# =========================================================
# 🔥 WEB DETECTION
# =========================================================

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

            if getattr(message, flag, False):
                return True

        if hasattr(message, "headers"):
            return True

        if hasattr(message, "client"):
            return True

        if hasattr(message, "scope"):
            return True

        return False

    except Exception as e:

        print(
            "WEB DETECTION ERROR:",
            e
        )

        return False


# =========================================================
# 🔥 NORMALIZATION
# =========================================================

def normalize_result(result):

    # =====================================================
    # 🔥 EMPTY SAFETY
    # =====================================================

    if not result:

        return {

            "type": "text",

            "content":
                "⚠️ Пустой ответ"
        }

    if not isinstance(result, dict):

        return {

            "type": "text",

            "content": str(result)
        }

    result_type = result.get(
        "type",
        "text"
    )

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if result_type == "text":

        return {

            "type": "text",

            "content":

                result.get("content")

                or result.get("data")

                or ""
        }

    # =====================================================
    # 🔥 CODE
    # =====================================================

    if result_type == "code":

        return {

            "type": "code",

            "code":
                result.get("code", ""),

            "file":
                result.get("file"),

            "block":
                result.get("block")
        }

    # =====================================================
    # 🔥 FILE
    # =====================================================

    if result_type == "file":

        return {

            "type": "file",

            "data":
                result.get("data"),

            "filename":
                result.get(
                    "filename",
                    "file.py"
                )
        }

    # =====================================================
    # 🔥 IMAGE
    # =====================================================

    if result_type == "image":

        return {

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
        }

    # =====================================================
    # 🔥 IMAGE TASK
    # =====================================================

    if result_type == "image_task":

        return {

            "type": "image_task",

            "prompt":
                result.get("prompt")
        }

    # =====================================================
    # 🔥 FUNCTION
    # =====================================================

    if result_type == "function":

        return {

            "type": "function",

            "function":
                result.get("function"),

            "range":
                result.get(
                    "range",
                    [-10, 10]
                ),

            "meta":
                result.get(
                    "meta",
                    {}
                )
        }

    # =====================================================
    # 🔥 GRAPH
    # =====================================================

    if result_type == "graph":

        return {

            "type": "graph",

            "graph":

                result.get("graph")

                or result.get("data"),

            "meta":
                result.get(
                    "meta",
                    {}
                )
        }

    # =====================================================
    # 🔥 FORMULA
    # =====================================================

    if result_type == "formula":

        return {

            "type": "formula",

            "formula":

                result.get("formula")

                or result.get("data"),

            "meta":
                result.get(
                    "meta",
                    {}
                )
        }

    # =====================================================
    # 🔥 BLOCKS
    # =====================================================

    if result_type == "blocks":

        return {

            "type": "blocks",

            "blocks":
                result.get(
                    "blocks",
                    []
                ),

            "meta":
                result.get(
                    "meta",
                    {}
                )
        }

    # =====================================================
    # 🔥 HYBRID
    # =====================================================

    if result_type == "hybrid":

        return {

            "type": "hybrid",

            "text":
                result.get(
                    "text",
                    ""
                ),

            "blocks":
                result.get(
                    "blocks",
                    []
                ),

            "image":
                result.get(
                    "image"
                ),

            "meta":
                result.get(
                    "meta",
                    {}
                )
        }

    # =====================================================
    # 🔥 ERROR
    # =====================================================

    if result_type == "error":

        return {

            "type": "error",

            "text":

                result.get("text")

                or result.get("data")

                or "⚠️ Ошибка"
        }

    # =====================================================
    # 🔥 STRUCTURED PASS
    # =====================================================

    if is_renderer_result(result):

        safe_result_log(
            "STRUCTURED RENDER PASSTHROUGH"
        )

        return result

    # =====================================================
    # 🔥 SAFE TEXT FALLBACK
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
# 🔥 WEB PAYLOAD BUILDER
# =========================================================

def build_web_payload(result):

    result_type = result.get(
        "type",
        "text"
    )

    # =====================================================
    # 🔥 PURE STRUCTURED PAYLOADS
    # =====================================================

    if result_type in [

        "function",
        "graph",
        "formula",
        "blocks",
        "scene",
        "diagram",
        "table",
        "layout",
        "renderer",
        "visual"
    ]:

        safe_result_log(
            f"WEB STRUCTURED PAYLOAD: {result_type}"
        )

        return result

    # =====================================================
    # 🔥 HYBRID
    # =====================================================

    if result_type == "hybrid":

        return result

    # =====================================================
    # 🔥 IMAGE
    # =====================================================

    if result_type == "image":

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

    # =====================================================
    # 🔥 ERROR
    # =====================================================

    if result_type == "error":

        return result

    return result


# =========================================================
# 🔥 TELEGRAM TEXT SAFETY
# =========================================================

def build_telegram_visual_comment(
    result
):

    result_type = result.get(
        "type",
        "text"
    )

    # =====================================================
    # 🔥 FUNCTION
    # =====================================================

    if result_type == "function":

        expr = result.get(
            "function",
            ""
        )

        return (
            "📈 Функция подготовлена:\n\n"
            f"{expr}\n\n"
            "Renderer payload отправлен."
        )

    # =====================================================
    # 🔥 GRAPH
    # =====================================================

    if result_type == "graph":

        return (
            "📊 Графическая сцена подготовлена."
        )

    # =====================================================
    # 🔥 FORMULA
    # =====================================================

    if result_type == "formula":

        formula = result.get(
            "formula",
            ""
        )

        return (
            "🧠 Формула подготовлена:\n\n"
            f"{formula}"
        )

    # =====================================================
    # 🔥 BLOCKS
    # =====================================================

    if result_type == "blocks":

        return (
            "🧩 Пространственная сцена подготовлена."
        )

    return (
        "🧠 Structured payload generated."
    )


# =========================================================
# 🔥 SEND RESULT
# =========================================================

async def send_result(
    message,
    result,
    keyboard=None
):

    result = normalize_result(
        result
    )

    result_type = result.get(
        "type",
        "text"
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
        "TELEGRAM PASSIVE MODE"
    )

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if result_type == "text":

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

        return

    # =====================================================
    # 🔥 CODE
    # =====================================================

    if result_type == "code":

        code = format_code_block(

            result.get("code"),

            result.get("file"),

            result.get("block")
        )

        await message.answer(

            f"```python\n{code}\n```",

            reply_markup=keyboard
        )

        return

    # =====================================================
    # 🔥 FILE
    # =====================================================

    if result_type == "file":

        code = result.get(
            "data",
            ""
        )

        filename = result.get(
            "filename",
            "file.py"
        )

        file_bytes = code.encode(
            "utf-8"
        )

        await message.answer_document(

            BufferedInputFile(
                file_bytes,
                filename=filename
            ),

            caption=f"📁 {filename}"
        )

        return

    # =====================================================
    # 🔥 IMAGE
    # =====================================================

    if result_type == "image":

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

        return

    # =====================================================
    # 🔥 STRUCTURED VISUALS
    # =====================================================

    if result_type in [

        "function",
        "graph",
        "formula",
        "blocks",
        "scene",
        "diagram",
        "table",
        "layout"
    ]:

        # =================================================
        # 🔥 NO LEGACY [[FUNCTION:X]]
        # =================================================

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

            state = {}

            result_img = await image_generate(

                user_id,

                result["prompt"],

                state
            )

            if (

                not result_img
                or result_img.get("type") != "image"
            ):

                await message.answer(
                    "⚠️ Не удалось создать изображение"
                )

                return

            await message.answer_photo(

                BufferedInputFile(
                    result_img["data"],
                    filename="image.png"
                ),

                caption="🖼 Готово"
            )

            return

        except Exception as e:

            print(
                "IMAGE TASK ERROR:",
                e
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
