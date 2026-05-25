# blocks/result_handler.py

from aiogram.types import BufferedInputFile

from blocks.image_module import process as image_generate
from blocks.canvas_formatter import (
    format_code_block,
    format_text
)

# =========================================================
# 🔥 SAFE NORMALIZE HELPERS
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
    "hybrid"
]


def is_renderer_result(result):

    try:

        if not isinstance(result, dict):
            return False

        r_type = result.get("type")

        if r_type in SAFE_RENDER_TYPES:
            return True

        if result.get("blocks"):
            return True

        if result.get("function"):
            return True

        if result.get("graph"):
            return True

        return False

    except:
        return False


# =========================================================
# 🔥 WEB PAYLOAD DETECTION
# =========================================================

def is_web_message(message):

    try:

        if message is None:
            return False

        # =====================================================
        # 🔥 APRIL WEB TRANSPORT
        # =====================================================

        if getattr(message, "is_web", False):
            return True

        if getattr(message, "web_mode", False):
            return True

        if getattr(message, "renderer_mode", False):
            return True

        # =====================================================
        # 🔥 FASTAPI / WEB OBJECT
        # =====================================================

        if hasattr(message, "client"):
            return True

        if hasattr(message, "headers"):
            return True

        return False

    except:

        return False


# =========================================================
# 🔥 WEB RENDER PAYLOAD
# =========================================================

def build_web_render_payload(
    result
):

    result_type = result.get(
        "type",
        "text"
    )

    # =====================================================
    # 🔥 GRAPH
    # =====================================================

    if result_type == "graph":

        return {

            "type": "graph",

            "graph":
                result.get("graph"),

            "meta":
                result.get(
                    "meta",
                    {}
                )
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
    # 🔥 FORMULA
    # =====================================================

    if result_type == "formula":

        return {

            "type": "formula",

            "formula":
                result.get("formula"),

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

    return result


# =========================================================
# 🔥 NORMALIZE RESULT
# =========================================================

def normalize_result(result):

    if not result or not isinstance(result, dict):

        return {

            "type": "text",

            "content": "⚠️ Пустой ответ"
        }

    r_type = result.get("type")

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if r_type == "text":

        content = (

            result.get("content")

            or result.get("data")

            or ""
        )

        return {

            "type": "text",

            "content": content
        }

    # =====================================================
    # 🔥 CODE
    # =====================================================

    if r_type == "code":

        return {

            "type": "code",

            "code":
                result.get("code") or "",

            "file":
                result.get("file"),

            "block":
                result.get("block")
        }

    # =====================================================
    # 🔥 FILE
    # =====================================================

    if r_type == "file":

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

    if r_type == "image":

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

    if r_type == "image_task":

        return {

            "type": "image_task",

            "prompt":
                result.get("prompt")
        }

    # =====================================================
    # 🔥 FUNCTION RENDER
    # =====================================================

    if r_type == "function":

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
    # 🔥 GRAPH RENDER
    # =====================================================

    if r_type == "graph":

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
    # 🔥 FORMULA RENDER
    # =====================================================

    if r_type == "formula":

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

    if r_type == "blocks":

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

    if r_type == "hybrid":

        return {

            "type": "hybrid",

            "text":
                result.get(
                    "text",
                    ""
                ),

            "image":
                result.get(
                    "image"
                ),

            "blocks":
                result.get(
                    "blocks",
                    []
                )
        }

    # =====================================================
    # 🔥 ERROR
    # =====================================================

    if r_type == "error":

        return {

            "type": "error",

            "text":

                result.get("text")

                or result.get("data")

                or "⚠️ Ошибка"
        }

    # =====================================================
    # 🔥 STRUCTURED RENDERER PROTECTION
    # =====================================================

    if is_renderer_result(result):

        print(
            "🧠 RESULT HANDLER: STRUCTURED RENDER DETECTED"
        )

        return result

    # =====================================================
    # 🔥 SAFE FALLBACK
    # =====================================================

    print(
        "⚠️ RESULT FALLBACK:",
        r_type
    )

    return {

        "type": "text",

        "content":

            result.get("content")

            or result.get("data")

            or "⚠️ Не удалось обработать ответ"
    }


# =========================================================
# 🔥 SEND RESULT
# =========================================================

async def send_result(
    message,
    result,
    keyboard=None
):

    result = normalize_result(result)

    result_type = result.get(
        "type",
        "text"
    )

    # =====================================================
    # 🔥 APRIL WEB MODE
    # =====================================================

    if is_web_message(message):

        print(
            "🧠 RESULT HANDLER: WEB MODE"
        )

        # =====================================================
        # 🔥 STRUCTURED RENDERER RETURN
        # =====================================================

        if result_type in [

            "graph",
            "function",
            "formula",
            "blocks"
        ]:

            print(
                f"🧠 WEB RENDER RETURN: {result_type}"
            )

            return build_web_render_payload(
                result
            )

        # =====================================================
        # 🔥 TEXT WEB RETURN
        # =====================================================

        return result

    # =====================================================
    # 🔥 TELEGRAM MODE
    # =====================================================

    print(
        "🧠 RESULT HANDLER: TELEGRAM MODE"
    )

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if result_type == "text":

        content = format_text(
            result.get("content")
        )

        if not content:

            content = "⚠️ Пустой ответ"

        await message.answer(

            content,

            reply_markup=keyboard
        )

    # =====================================================
    # 🔥 CODE
    # =====================================================

    elif result_type == "code":

        code = format_code_block(

            result.get("code"),

            result.get("file"),

            result.get("block")
        )

        await message.answer(

            f"```python\n{code}\n```",

            reply_markup=keyboard
        )

    # =====================================================
    # 🔥 FILE
    # =====================================================

    elif result_type == "file":

        code = result.get("data") or ""

        filename = result.get(
            "filename",
            "file.py"
        )

        code = format_code_block(
            code,
            filename,
            None
        )

        file_bytes = code.encode("utf-8")

        await message.answer_document(

            BufferedInputFile(
                file_bytes,
                filename=filename
            ),

            caption=f"📁 {filename}"
        )

    # =====================================================
    # 🔥 IMAGE
    # =====================================================

    elif result_type == "image":

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

    # =====================================================
    # 🔥 FUNCTION
    # =====================================================

    elif result_type == "function":

        function_expr = result.get(
            "function"
        )

        await message.answer(

            f"[[function:{function_expr}]]",

            reply_markup=keyboard
        )

    # =====================================================
    # 🔥 GRAPH
    # =====================================================

    elif result_type == "graph":

        graph_data = result.get(
            "graph"
        )

        await message.answer(

            f"[[graph:{graph_data}]]",

            reply_markup=keyboard
        )

    # =====================================================
    # 🔥 FORMULA
    # =====================================================

    elif result_type == "formula":

        formula = result.get(
            "formula"
        )

        await message.answer(

            f"[[formula:{formula}]]",

            reply_markup=keyboard
        )

    # =====================================================
    # 🔥 ERROR
    # =====================================================

    elif result_type == "error":

        await message.answer(

            result.get("text")

            or "⚠️ Ошибка"
        )

    # =====================================================
    # 🔥 FINAL UNKNOWN FALLBACK
    # =====================================================

    else:

        print(
            "⚠️ UNKNOWN RESULT TYPE:",
            result_type
        )

        await message.answer(

            "⚠️ Неизвестный тип результата",

            reply_markup=keyboard
        )
