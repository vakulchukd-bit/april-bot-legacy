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
from blocks.image_edit_module import process as image_edit

from blocks.image_system import analyze_image

from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import set_subscription, save_payment

from blocks.energy_manager import get_energy
from blocks.science_room import ScienceRoom

import re


# ===== 🧠 СЕМАНТИКА =====
def detect_task_type(text: str):
    t = text.lower()

    if re.search(r'[0-9x\)\(]+\s*[\+\-\*/=]\s*[0-9x\)\(]+', t):
        return "math"

    if "=" in t and re.search(r'[a-z]', t):
        return "math"

    if any(w in t for w in ["реши", "уравнение", "найди корень"]):
        if re.search(r'[0-9x\+\-\*/=]', t):
            return "math"

    if "y=" in t or "график" in t:
        return "math"

    if any(x in t for x in ["создай", "сгенерируй", "нарисуй", "сделай"]):
        return "image_generate"

    if any(x in t for x in ["измени", "убери", "добавь", "замени"]):
        return "image_edit"

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


def is_edit_request(text: str):
    t = text.lower()
    return any(word in t for word in [
        "убери", "добавь", "измени", "замени",
        "сделай", "усиль", "ярче", "темнее"
    ])


def is_generate_request(text: str):
    t = text.lower()
    return any(v in t for v in ["создай", "сгенерируй", "нарисуй", "сделай"]) and \
           any(o in t for o in ["картинку", "изображение", "фото", "арт", "рисунок"])


def is_image_question(text: str):
    t = text.lower()
    return any(tr in t for tr in [
        "что на картинке", "что это", "что справа",
        "что слева", "что здесь", "что изображено"
    ])


def update_memory_summary(state):
    dialog = state.get("dialog", [])

    if len(dialog) < 10:
        return

    last_chunk = dialog[:-10]
    if not last_chunk:
        return

    texts = [m.get("content", "") for m in last_chunk if m.get("role") == "user"]
    if not texts:
        return

    combined = " ".join(texts)[-1000:]
    prev = state.get("memory_summary", "")

    state["memory_summary"] = (prev + " " + combined)[-2000:]
    state["dialog"] = dialog[-10:]


# ===== 🚀 EXECUTOR =====
async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    update_memory_summary(state)

    if state.get("image_generating"):
        result = await run_with_typing(chat_id, text_process(user_id, "Подожди...", state))
        return {"type": "text", "data": result["content"]}

    if callback_data:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()
    task_type = detect_task_type(text)

    energy = get_energy(user_id)
    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    # ===== МАТЕМАТИКА =====
    if task_type == "math":
        room = ScienceRoom()
        result = await room.handle(user_id, text, {
            "chat_id": chat_id,
            "state": state,
            "image": ctx,
            "anchor": anchor,
            "task_type": task_type,
            "energy": energy
        }, run_with_typing)

        if result and result.get("type") == "text":
            wrapped = await run_with_typing(
                chat_id,
                text_process(user_id, result["data"], state, energy)
            )
            return {"type": "text", "data": wrapped["content"]}

        return result

    # ===== ОРКЕСТР =====
    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "task_type": task_type,
        "energy": energy
    }

    candidates = []
    for room in ROOMS:
        try:
            score = room.evaluate(text, context)
            candidates.append((room, score))
        except:
            pass

    candidates.sort(key=lambda x: x[1], reverse=True)

    if candidates and candidates[0][1] > 0:
        room = candidates[0][0]
        result = await room.handle(user_id, text, context, run_with_typing)

        if result and result.get("type") == "text":
            wrapped = await run_with_typing(
                chat_id,
                text_process(user_id, result["data"], state, energy)
            )
            return {"type": "text", "data": wrapped["content"]}

        return result

    # ===== ФОЛБЭК =====
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
