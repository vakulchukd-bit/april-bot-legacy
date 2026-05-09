from blocks.intent_resolver import resolve_input

from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.router import route_request

from blocks.state_manager import (
    get_state,
    get_image_context,
    set_image_context,
    add_dialog,
    set_dialog_state,
    update_memory_summary,
    get_active_flow,
    set_active_flow,
    clear_active_flow
)

from blocks.anchor_system import get_anchor
from blocks.mode_manager import get_mode

from blocks.context_system import build_context_text

from blocks.rooms_registry import ROOMS
from blocks.engineering_system import analyze_code

from blocks.image_module import process as image_generate
from blocks.image_module import extract_image_prompt
from blocks.image_edit_module import process as image_edit

from blocks.image_system import analyze_image

from blocks.semantic_core import analyze as semantic_analyze

from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from storage import set_subscription, save_payment
from storage import find_knowledge, save_knowledge

from blocks.energy_manager import get_energy

from blocks.experience import update_experience, load_experience

from blocks.interpretation_layer import interpret_request

import re


PATCH_LOG = []


def safe_patch_log(msg):
    try:
        print("PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


def patch_executor_start(user_id, text):
    safe_patch_log(
        f"EXECUTOR START: {user_id} | {text[:50]}"
    )
    return None


def patch_executor_hook(*args, **kwargs):
    return None


# =====================================================
# 🔥 SAFE TASK DETECTION
# =====================================================

def detect_task_type(text: str):

    t = text.lower().strip()

    image_edit_words = [
        "измени",
        "убери",
        "добавь",
        "замени",
        "улучши"
    ]

    if any(x in t for x in image_edit_words):
        return "image_edit"

    image_generate_words = [
        "создай",
        "сгенерируй",
        "нарисуй",
        "создай изображение",
        "сделай картинку"
    ]

    if any(x in t for x in image_generate_words):
        return "image_generate"

    math_words = [
        "график",
        "функция",
        "уравнение",
        "реши",
        "матем",
        "sin(",
        "cos(",
        "tan(",
        "y="
    ]

    if any(x in t for x in math_words):
        return "math"

    if "=" in t:

        has_digits = any(
            ch.isdigit()
            for ch in t
        )

        if has_digits:
            return "math"

    operators = ["+", "-", "*", "/"]

    if any(op in t for op in operators):

        digit_count = sum(
            ch.isdigit()
            for ch in t
        )

        if digit_count >= 2:
            return "math"

    return "text"


# =====================================================
# 🔥 OUTPUT MODE
# =====================================================

def detect_output_mode(text: str):

    t = text.lower()

    if any(w in t for w in [
        "файл",
        "скачать",
        ".py",
        "html"
    ]):
        return "file"

    if any(w in t for w in [
        "код",
        "code"
    ]):
        return "code"

    if any(w in t for w in [
        "график html",
        "интерактив",
        "браузер"
    ]):
        return "graph_html"

    if any(w in t for w in [
        "картинкой",
        "png",
        "изображением"
    ]):
        return "graph_image"

    return "auto"


# =====================================================
# 🔥 ACTIVE TASK
# =====================================================

def update_active_task(
    state: dict,
    text: str,
    task_type: str
):

    t = text.lower()

    if "y=" in t:

        state["active_task"] = {
            "type": "math",
            "data": text.strip()
        }


def continue_active_task(
    state: dict,
    text: str
):
    return text


# =====================================================
# 🔥 MEMORY
# =====================================================

def extract_and_store_semantics(
    state: dict,
    text: str,
    result_type: str = "text"
):

    t = text.lower()

    match = re.search(
        r"y\s*=\s*([^\n\r]+)",
        t
    )

    if match:

        expr = match.group(1).strip()

        state["last_math"] = {
            "type": "function",
            "expr": expr
        }

    if "```" in text:
        state["last_code"] = text

    if result_type == "image":
        state["last_image"] = {
            "exists": True
        }


# =====================================================
# 🚀 EXECUTE
# =====================================================

async def execute(
    user_id,
    text,
    chat_id,
    run_with_typing,
    callback_data=None
):

    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    t = text.lower().strip()

    # =================================================
    # 🔥 SEMANTIC CORE
    # =================================================

    semantic = semantic_analyze(
        text=text,
        state=state,
        history=state.get("dialog", []),
        active_flow=get_active_flow(user_id),
        dialog_state=state.get("dialog_state", {})
    )

    print("🧠 SEMANTIC:", semantic)

    # =================================================
    # 🔒 IMAGE LOCK
    # =================================================

    if state.get("image_lock"):

        return {
            "type": "text",
            "data":
                "⏳ Изображение ещё обрабатывается"
        }

    # =================================================
    # 💬 DIALOG
    # =================================================

    add_dialog(user_id, "user", text)

    update_memory_summary(
        user_id,
        text
    )

    dialog = (
        state.get("dialog_state", {})
        or {}
    )

    # =================================================
    # 🖼 IMAGE PRIORITY
    # =================================================

    if dialog.get("intent") == "image":

        image_words = [
            "что",
            "картин",
            "фото",
            "изображ",
            "добавь",
            "измени",
            "убери",
            "замени"
        ]

        if any(x in t for x in image_words):

            ctx = state.get("image_context")

            if ctx and ctx.get("path"):

                edit_words = [
                    "добавь",
                    "измени",
                    "убери",
                    "замени"
                ]

                if any(x in t for x in edit_words):

                    result = await image_edit(
                        user_id,
                        text,
                        state
                    )

                    return result

                result = await analyze_image(
                    ctx["path"],
                    state
                )

                add_dialog(
                    user_id,
                    "assistant",
                    result
                )

                update_memory_summary(
                    user_id,
                    result
                )

                return {
                    "type": "text",
                    "data": result
                }

    # =================================================
    # 🔥 TASK TYPE
    # =================================================

    # =================================================
    # 🧠 SEMANTIC TASK TYPE
    # =================================================

    semantic_intent = semantic.get(
        "intent"
    )

    if semantic_intent:

        task_type = semantic_intent

    else:

        # 🔥 legacy fallback only
        task_type = detect_task_type(
            text
        )

    if task_type == "math":

        set_active_flow(
            user_id,
            {
                "type": "math",
                "original": text
            }
        )

    elif task_type in [
        "image_generate",
        "image_edit",
        "image"
    ]:

        set_active_flow(
            user_id,
            {
                "type": "image"
            }
        )

    # =================================================
    # ⚡ ENERGY
    # =================================================

    energy = get_energy(user_id)

    # =================================================
    # 🧠 CONTEXT
    # =================================================

    context = {
        "chat_id": chat_id,
        "state": state,
        "mode": mode,
        "task_type": task_type,
        "energy": energy,
        "output_mode":
            detect_output_mode(text),
        "semantic": semantic
    }

    ## =================================================
    # 🏠 ROOMS
    # =================================================

    # =================================================
    # 🧠 SEMANTIC ROOM SELECTION
    # =================================================

    scored_rooms = []

    for room in ROOMS:

        try:

            score = room.evaluate(
                text,
                context
            )

            # 🔥 fallback legacy support
            if score <= 0:

                if room.can_handle(
                    text,
                    context
                ):
                    score = 0.2

            scored_rooms.append(
                (score, room)
            )

        except Exception as e:

            print(
                f"ROOM EVALUATE ERROR [{room.name}]",
                e
            )

    # 🔥 BEST ROOM FIRST
    scored_rooms.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # =================================================
    # 🚀 ROOM EXECUTION
    # =================================================

    for score, room in scored_rooms:

        try:

            if score <= 0:
                continue

            print(
                f"🧠 ROOM SELECTED: "
                f"{room.name} | score={score}"
            )

            result = await room.handle(
                user_id,
                text,
                context,
                run_with_typing
            )

            if (
                result
                and result.get("type")
            ):

                # =========================
                # 🖼 IMAGE GENERATION
                # =========================

                if result.get("type") == "image_task":

                    state["image_lock"] = True

                    try:

                        result = await image_generate(
                            user_id,
                            result["prompt"],
                            state
                        )

                    finally:

                        state["image_lock"] = False

                output_text = str(
                    result.get("data", "")
                )

                add_dialog(
                    user_id,
                    "assistant",
                    output_text
                )

                update_memory_summary(
                    user_id,
                    output_text
                )

                # =========================
                # 🔥 DIALOG STATE
                # =========================

                if result.get("type") == "image":

                    set_active_flow(
                        user_id,
                        {
                            "type": "image"
                        }
                    )

                    set_dialog_state(
                        user_id,
                        {
                            "intent": "image"
                        }
                    )

                elif task_type == "math":

                    set_dialog_state(
                        user_id,
                        {
                            "intent": "math"
                        }
                    )

                else:

                    set_dialog_state(
                        user_id,
                        {
                            "intent": "text"
                        }
                    )

                extract_and_store_semantics(
                    state,
                    output_text,
                    result.get(
                        "type",
                        "text"
                    )
                )

                return result

        except Exception as e:

            print(
                f"ROOM ERROR [{room.name}]",
                e
            )

    # =================================================
    # 💬 TEXT FALLBACK
    # =================================================

    context_text = build_context_text(
        user_id,
        text,
        state
    )

    result = await run_with_typing(
        chat_id,
        text_process(
            user_id,
            context_text,
            state,
            energy
        )
    )

    if result and result.get("content"):

        add_dialog(
            user_id,
            "assistant",
            result["content"]
        )

        update_memory_summary(
            user_id,
            result["content"]
        )

        set_dialog_state(
            user_id,
            {
                "intent": "text"
            }
        )

        extract_and_store_semantics(
            state,
            result["content"],
            "text"
        )

    return {
        "type": "text",
        "data": result["content"]
    }
