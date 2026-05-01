from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.router import route_request

from blocks.state_manager import (
    get_state,
    get_image_context,
    set_image_context,
    add_dialog
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


# ===============================
# EXECUTE
# ===============================
async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    add_dialog(user_id, "user", text)

    # ===============================
    # 🔥 AI DECISION (ГЛАВНОЕ)
    # ===============================
    try:
        decision = await detect_intent_ai(text, state)

        intent = decision.get("intent")
        expr = decision.get("expr")
        response = decision.get("response")

        # текстовый ответ
        if intent == "text_answer" and response:
            add_dialog(user_id, "assistant", response)
            return {"type": "text", "data": response}

        # модификация функции
        if intent == "math_modify":
            last = state.get("last_math")
            if last and expr:
                last["expr"] = expr
                return {
                    "type": "text",
                    "data": "Окей, изменила. Построить график?"
                }

        # новая функция
        if intent == "math_graph" and expr:
            state["last_math"] = {
                "type": "function",
                "expr": expr
            }
            text = f"y={expr}"

    except Exception as e:
        print("AI ERROR:", e)

    # ===============================
    # 🔥 СТАРАЯ ЛОГИКА (НЕ ТРОГАЕМ)
    # ===============================
    energy = get_energy(user_id)

    context = {
        "chat_id": chat_id,
        "state": state,
        "mode": mode,
        "task_type": "math" if "=" in text else "text",
        "energy": energy,
        "output_mode": "auto"
    }

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(user_id, text, context, run_with_typing)

                if result and result.get("type"):
                    output_text = str(result.get("data", ""))

                    add_dialog(user_id, "assistant", output_text)

                    extract_and_store_semantics(
                        state,
                        output_text,
                        result.get("type", "text")
                    )

                    return result

        except Exception as e:
            print(f"ROOM ERROR [{room.name}]:", e)

    # fallback
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    if result and result.get("content"):
        add_dialog(user_id, "assistant", result["content"])

        extract_and_store_semantics(state, result["content"], "text")

    return {"type": "text", "data": result["content"]}
