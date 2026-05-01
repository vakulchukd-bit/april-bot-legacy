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

# 🔥 NEW
from storage import find_knowledge, save_knowledge

from blocks.energy_manager import get_energy

from blocks.experience import update_experience, load_experience

from blocks.interpretation_layer import interpret_request

import re


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


def handle_subscription(callback_data, user_id):
    print("🔥 CALLBACK:", callback_data)

    if callback_data == "buy_lite":
        return {
            "type": "text",
            "data": "💳 Подтвердить переход на Lite?",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="buy_yes_lite"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
                ]
            ])
        }

    if callback_data == "buy_premium":
        return {
            "type": "text",
            "data": "💳 Подтвердить переход на Premium?",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="buy_yes_premium"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
                ]
            ])
        }

    if callback_data == "buy_yes_lite":
        return {"type": "admin_request", "plan": "lite"}

    if callback_data == "buy_yes_premium":
        return {"type": "admin_request", "plan": "premium"}

    if callback_data == "buy_no":
        return {"type": "text", "data": "❌ Отменено"}

    if callback_data.startswith("admin_confirm_"):
        parts = callback_data.split("_")
        plan = parts[2]
        uid = int(parts[3])

        set_subscription(uid, plan)
        save_payment(uid, plan)

        return {
            "type": "notify_user",
            "target_user": uid,
            "data": f"✅ Активирован {plan.upper()}"
        }

    return None


def is_image_question(text: str):
    t = text.lower()
    return any(tr in t for tr in [
        "что на картинке", "что это", "что справа",
        "что слева", "что здесь", "что изображено"
    ])


async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    t = text.lower().strip()

    # ===============================
    # 🔥 KNOWLEDGE CHECK (НОВОЕ)
    # ===============================
    try:
        known = find_knowledge(text)
        if known:
            print("🧠 KNOWLEDGE HIT")
            return {"type": "text", "data": known}
    except Exception as e:
        print("🔥 KNOWLEDGE ERROR:", e)

    # ===============================
    # INTERPRET
    # ===============================
    try:
        interpreted = interpret_request(text)
        if interpreted and interpreted.get("normalized"):
            text = interpreted["normalized"]
    except:
        pass

    # ===============================
    # VAGUE
    # ===============================
    if is_vague_request(text):
        result = await run_with_typing(
            chat_id,
            text_process(user_id, "Предложи что можно сделать: график, код или изображение.", state, energy="LOW")
        )
        return {"type": "text", "data": result["content"]}

    # ===============================
    # DISSATISFACTION
    # ===============================
    if is_dissatisfied(text):
        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state, energy="LOW")
        )
        return {"type": "text", "data": result["content"]}

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

    for room in ROOMS:
        if room.can_handle(text, context):
            result = await room.handle(user_id, text, context, run_with_typing)
            if result:
                # 🔥 SAVE KNOWLEDGE
                try:
                    if result["type"] == "text" and len(result["data"]) < 1000:
                        save_knowledge(text.lower(), result["data"])
                except:
                    pass

                return result

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    # 🔥 SAVE KNOWLEDGE
    try:
        if result and result.get("content") and len(result["content"]) < 1000:
            save_knowledge(text.lower(), result["content"])
    except:
        pass

    return {"type": "text", "data": result["content"]}
