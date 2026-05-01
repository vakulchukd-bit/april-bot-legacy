from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.router import route_request

from blocks.state_manager import (
    get_state,
    get_image_context,
    set_image_context,
    add_dialog  # 🔥 ДОБАВИЛИ
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
# 🔥 ACTIVE TASK (УСИЛЕННЫЙ)
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
# ОСТАЛЬНОЕ
# ===============================

def is_vague_request(text: str):
    t = text.lower().strip()
    vague_words = ["что-нибудь", "что то", "что-то", "придумай"]

    if any(v in t for v in vague_words):
        return True

    if len(t.split()) <= 3 and "сделай" in t:
        return True

    return False


def is_dissatisfied(text: str):
    t = text.lower()
    triggers = [
        "не то", "не понял", "не это", "другое",
        "не подходит", "не правильно", "неправильно",
        "ты не понял", "я не это имел"
    ]
    return any(tr in t for tr in triggers)


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


# ===============================
# EXECUTE
# ===============================

async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    # 🔥 СОХРАНЯЕМ ВХОД ПОЛЬЗОВАТЕЛЯ
    add_dialog(user_id, "user", text)

    t = text.lower().strip()

    try:
        known = find_knowledge(text)
        if known:
            return {"type": "text", "data": known}
    except:
        pass

    try:
        interpreted = interpret_request(text)
        if interpreted and interpreted.get("normalized"):
            text = interpreted["normalized"]
    except:
        pass

    try:
        task_type = detect_task_type(text)
        update_active_task(state, text, task_type)
        # text = continue_active_task(state, text)  # 🔥 ОТКЛЮЧИЛИ ПРИНУДИТЕЛЬНЫЙ ТРИГГЕР
    except:
        pass

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

                    # 🔥 СОХРАНЯЕМ ОТВЕТ БОТА
                    if result["type"] == "text":
                        add_dialog(user_id, "assistant", result["data"])

                    return result
        except:
            pass

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    # 🔥 СОХРАНЯЕМ fallback ответ
    if result and result.get("content"):
        add_dialog(user_id, "assistant", result["content"])

    return {"type": "text", "data": result["content"]}
