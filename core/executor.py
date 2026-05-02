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

from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from storage import set_subscription, save_payment
from storage import find_knowledge, save_knowledge

from blocks.energy_manager import get_energy

from blocks.experience import update_experience, load_experience

from blocks.interpretation_layer import interpret_request

import re


# ===============================
# 🔥 SAFE PATCH MODE (EXECUTOR)
# ===============================
PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


def patch_executor_start(user_id, text):
    safe_patch_log(f"EXECUTOR START: {user_id} | {text[:50]}")
    return None


def patch_executor_hook(*args, **kwargs):
    return None


# ===============================
# 🔥 ACTIVE TASK
# ===============================
def update_active_task(state: dict, text: str, task_type: str):
    t = text.lower()

    if "y=" in t:
        state["active_task"] = {
            "type": "math",
            "data": text.strip()
        }

    elif any(w in t for w in ["сложнее", "проще", "волнист", "резче", "плавнее"]):
        active = state.get("active_task")
        if active and active.get("type") == "math":
            state["active_task"]["modify"] = t

    elif "график" in t:
        if "active_task" not in state:
            state["active_task"] = {
                "type": "math",
                "data": None
            }


def continue_active_task(state: dict, text: str):
    t = text.lower().strip()
    active = state.get("active_task")

    if not active:
        return text

    if any(w in t for w in ["построй", "сделай", "покажи", "давай"]):
        if active.get("type") == "math":
            if active.get("data"):
                return f"{active['data']} построить график"
            return "построй график"

    if "это" in t and "график" in t:
        if active.get("data"):
            return f"{active['data']} построить график"

    return text


# ===============================
# 🔥 SEMANTIC MEMORY
# ===============================
def extract_and_store_semantics(state: dict, text: str, result_type: str = "text"):
    t = text.lower()

    match = re.search(r"y\s*=\s*([^\n\r]+)", t)
    if match:
        expr = match.group(1).strip()

        expr = expr.replace("^", "**")
        expr = expr.replace("sin", "np.sin")
        expr = expr.replace("cos", "np.cos")
        expr = expr.replace("tan", "np.tan")
        expr = expr.replace("log", "np.log")

        state["last_math"] = {
            "type": "function",
            "expr": expr
        }

    if "```" in text:
        state["last_code"] = text

    if result_type == "image":
        state["last_image"] = {"exists": True}


# ===============================
# EXECUTE
# ===============================
async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    # ===============================
    # 🔥 ACTIVE FLOW CONTROL (NEW)
    # ===============================
    flow = get_active_flow(user_id)
    t = text.lower()

    if flow:
        if flow.get("type") == "math":
            if any(x in t for x in ["объясни", "покажи", "таблица", "график"]):
                text = flow.get("original", text)

        if flow.get("type") == "image":
            if any(x in t for x in ["добавь", "измени", "убери"]):
                return await image_edit(user_id, text, state)

    if any(x in t for x in ["как тебя зовут", "кто ты", "давай поговорим"]):
        clear_active_flow(user_id)

    add_dialog(user_id, "user", text)
    update_memory_summary(user_id, text)
     

    dialog = state.get("dialog_state", {})

    # IMAGE continuation
    if dialog.get("intent") == "image":

        if any(w in t for w in ["сделай", "измени", "добавь", "убери"]):
            return await image_edit(user_id, text, state)

        if "что" in t and "картин" in t:

            ctx = state.get("image_context")

            if not ctx:
                events = state.get("events", [])
                for e in reversed(events):
                    if e.get("type") == "image_uploaded":
                        ctx = {"path": e.get("path")}
                        break

            if ctx and ctx.get("path"):
                result = await analyze_image(ctx["path"], state)

                add_dialog(user_id, "assistant", result)
                update_memory_summary(user_id, result)

                set_dialog_state(user_id, {"intent": "image", "mode": "analyze"})

                return {"type": "text", "data": result}

    


# ===============================
    # 🔥 MAIN FLOW (FIXED + CONTEXT)
    # ===============================
    try:
        task_type = detect_task_type(text)

        if task_type == "math":
            set_active_flow(user_id, {"type": "math", "original": text})

        if task_type == "image_generate":
            set_active_flow(user_id, {"type": "image"})

        update_active_task(state, text, task_type)

    except Exception as e:
        print("ACTIVE TASK ERROR:", e)

    energy = get_energy(user_id)

    context = {
        "chat_id": chat_id,
        "state": state,
        "mode": mode,
        "task_type": detect_task_type(text),
        "energy": energy,
        "output_mode": detect_output_mode(text)
    }

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(user_id, text, context, run_with_typing)

                if result and result.get("type"):
                    output_text = str(result.get("data", ""))

                    add_dialog(user_id, "assistant", output_text)
                    update_memory_summary(user_id, output_text)

                    if result.get("type") == "image":
                        set_active_flow(user_id, {"type": "image"})
                        set_dialog_state(user_id, {"intent": "image"})
                    elif context.get("task_type") == "math":
                        set_dialog_state(user_id, {"intent": "math"})
                    else:
                        set_dialog_state(user_id, {"intent": "text"})

                    extract_and_store_semantics(
                        state,
                        output_text,
                        result.get("type", "text")
                    )

                    return result

        except Exception as e:
            print(f"ROOM ERROR [{room.name}]:", e)

    # 🔥 ВОТ ОН ФИКС (КОНТЕКСТ)
    context_text = build_context_text(user_id, text, state)

    result = await run_with_typing(
        chat_id,
        text_process(user_id, context_text, state, energy)
    )

    if result and result.get("content"):
        add_dialog(user_id, "assistant", result["content"])
        update_memory_summary(user_id, result["content"])
        set_dialog_state(user_id, {"intent": "text"})
        extract_and_store_semantics(state, result["content"], "text")

    return {"type": "text", "data": result["content"]}


# ===============================
# HELPERS
# ===============================
def detect_output_mode(text: str):
    t = text.lower()

    if any(w in t for w in ["файл", "скачать", ".py", "html"]):
        return "file"

    if any(w in t for w in ["код", "code"]):
        return "code"

    if any(w in t for w in ["график html", "интерактив", "браузер"]):
        return "graph_html"

    if any(w in t for w in ["картинкой", "png", "изображением"]):
        return "graph_image"

    return "auto"


def detect_task_type(text: str):
    t = text.lower()

    if "=" in t:
        return "math"

    if "sin(" in t or "cos(" in t:
        return "math"

    if any(op in t for op in ["+", "-", "*", "/"]):
        if any(ch.isdigit() for ch in t):
            return "math"

    if "y=" in t or "график" in t:
        return "math"

    if any(x in t for x in ["измени", "убери", "добавь", "замени"]):
        return "image_edit"

    if any(x in t for x in ["создай", "сгенерируй", "нарисуй"]):
        return "image_generate"

    if "сделай" in t:
        return "text"

    return "text"
