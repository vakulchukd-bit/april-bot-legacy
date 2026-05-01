from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.router import route_request

from blocks.state_manager import (
    get_state,
    get_image_context,
    set_image_context
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
import random  # 🔥 ДОБАВЛЕНО


# ===============================
# 🔥 NEW: CONTEXT ENRICH
# ===============================
def enrich_with_context(text: str, state: dict):
    history = state.get("dialog", [])
    if not history:
        return text

    words = text.strip().split()

    # короткий запрос → возможно продолжение
    if len(words) <= 4:
        last_user = next(
            (m["content"] for m in reversed(history) if m["role"] == "user"),
            None
        )

        if last_user:
            return last_user + " → " + text

    return text


# ===============================
# 🔥 NEW: ACTIVE TASK (КЛЮЧЕВОЕ)
# ===============================
def update_active_task(state: dict, text: str, task_type: str):
    t = text.lower()

    # фиксируем график
    if "y=" in t:
        state["active"] = {
            "type": "graph",
            "function": text.strip()
        }

    # если говорим про графики без формулы
    elif "график" in t and "active" not in state:
        state["active"] = {
            "type": "graph",
            "function": None
        }


def try_continue_active(state: dict, text: str):
    t = text.lower().strip()

    triggers = ["построй", "сделай", "давай", "построй график"]

    if any(t.startswith(tr) for tr in triggers):
        active = state.get("active")

        if active and active.get("type") == "graph":
            func = active.get("function")

            if func:
                return func + " → построить график"
            else:
                return "построй график"

    return text


# ===============================
# 🔥 NEW: SMART FALLBACK
# ===============================
def smart_fallback(text: str, task_type: str):
    t = text.lower()

    if task_type == "math":
        return random.choice([
            "Хочешь построить график? Дай функцию, например: y = x**2 🙂",
            "Могу построить график — напиши формулу, и я сделаю",
            "Давай нарисуем график 🙂 Что именно строим?"
        ])

    if task_type == "image_generate":
        return random.choice([
            "Могу создать изображение 🙂 Опиши, что хочешь увидеть",
            "Хочешь картинку? Дай описание или стиль — сделаю",
            "Давай нарисуем 🙂 Что именно изобразить?"
        ])

    if task_type == "code":
        return random.choice([
            "Могу написать код 🙂 Что именно нужно?",
            "Хочешь что-то создать? Скажи задачу — сделаю код",
            "Давай сделаем 🙂 Это сайт, кнопка или что-то ещё?"
        ])

    return random.choice([
        "Давай уточним 🙂 Что именно ты хочешь сделать?",
        "Могу помочь 🙂 Опиши чуть подробнее задачу",
        "Скажи, что нужно — и я подключусь"
    ])


# ===============================
# ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ
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

    t = text.lower().strip()

    # 🔥 KNOWLEDGE
    try:
        known = find_knowledge(text)
        if known:
            print("🧠 KNOWLEDGE HIT")
            return {"type": "text", "data": known}
    except Exception as e:
        print("🔥 KNOWLEDGE ERROR:", e)

    # INTERPRET
    try:
        interpreted = interpret_request(text)
        if interpreted and interpreted.get("normalized"):
            text = interpreted["normalized"]
    except Exception as e:
        print("🔥 INTERPRET ERROR:", e)

    # 🔥 CONTEXT ENRICH
    try:
        text = enrich_with_context(text, state)
    except Exception as e:
        print("🔥 ENRICH ERROR:", e)

    # 🔥 ACTIVE TASK UPDATE
    try:
        task_type = detect_task_type(text)
        update_active_task(state, text, task_type)
        text = try_continue_active(state, text)
    except Exception as e:
        print("🔥 ACTIVE TASK ERROR:", e)

    # VAGUE
    try:
        if is_vague_request(text):
            result = await run_with_typing(
                chat_id,
                text_process(
                    user_id,
                    "Предложи что можно сделать: график, код или изображение. Ответ живой.",
                    state,
                    energy="LOW"
                )
            )
            return {"type": "text", "data": result.get("content")}
    except Exception as e:
        print("🔥 VAGUE ERROR:", e)

    # DISSATISFACTION
    try:
        if is_dissatisfied(text):
            result = await run_with_typing(
                chat_id,
                text_process(user_id, text, state, energy="LOW")
            )
            return {"type": "text", "data": result.get("content")}
    except Exception as e:
        print("🔥 DISSATISFACTION ERROR:", e)

    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

    energy = get_energy(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    task_type = detect_task_type(text)
    output_mode = detect_output_mode(text)

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": task_type,
        "energy": energy,
        "output_mode": output_mode
    }

    candidates = []

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                score = room.evaluate(text, context)
                candidates.append((score, room))
        except Exception as e:
            print(f"🔥 CAN_HANDLE ERROR [{room.name}]:", e)

    # 🔥 SMART FALLBACK
    if not candidates:
        return {
            "type": "text",
            "data": smart_fallback(text, task_type)
        }

    candidates.sort(reverse=True, key=lambda x: x[0])

    for score, room in candidates:
        try:
            result = await room.handle(user_id, text, context, run_with_typing)
            if result and result.get("type"):

                try:
                    if result["type"] == "text" and len(result.get("data", "")) < 1000:
                        save_knowledge(text.lower(), result["data"])
                except Exception as e:
                    print("🔥 SAVE KNOWLEDGE ERROR:", e)

                return result
        except Exception as e:
            print(f"🔥 ROOM HANDLE ERROR [{room.name}]:", e)

    # 🔥 FALLBACK → OpenAI
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    try:
        if result and result.get("content") and len(result["content"]) < 1000:
            save_knowledge(text.lower(), result["content"])
    except Exception as e:
        print("🔥 SAVE KNOWLEDGE ERROR:", e)

    return {"type": "text", "data": result["content"]}
