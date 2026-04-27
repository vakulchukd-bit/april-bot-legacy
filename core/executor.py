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

    if callback_data == "confirm_downgrade":
        return {
            "type": "text",
            "data": "⚠️ Ты уверен, что хочешь перейти на Lite?",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="confirm_downgrade_yes"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="confirm_downgrade_no")
                ]
            ])
        }

    if callback_data == "confirm_downgrade_yes":
        return {"type": "admin_request", "plan": "lite"}

    if callback_data == "confirm_downgrade_no":
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

    if callback_data.startswith("admin_reject_"):
        uid = int(callback_data.split("_")[3])

        return {
            "type": "notify_user",
            "target_user": uid,
            "data": "❌ Запрос отклонён"
        }

    return None


def is_edit_request(text: str):
    return any(w in text.lower() for w in ["убери", "добавь", "измени", "замени"])


def is_generate_request(text: str):
    t = text.lower()
    return any(v in t for v in ["создай", "сгенерируй", "нарисуй", "сделай"]) and \
           any(o in t for o in ["картинку", "изображение", "фото", "арт", "рисунок"])


def is_image_question(text: str):
    return any(t in text.lower() for t in [
        "что на картинке", "что это", "что справа", "что слева"
    ])


async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)

    if "visual_intent" not in state:
        state["visual_intent"] = 0

    if "offered_visual" not in state:
        state["offered_visual"] = False

    if callback_data:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()

    # согласие
    if state.get("offered_visual") and any(w in t for ["да", "давай", "покажи"]):
        return {
            "type": "image_task",
            "prompt": text
        }

    # накопление
    if any(p in t for ["хочу увидеть", "сложно представить", "как выглядит"]):
        state["visual_intent"] += 1
    else:
        state["visual_intent"] = max(0, state["visual_intent"] - 1)

    # предложение
    if state["visual_intent"] >= 2 and not state["offered_visual"]:
        state["offered_visual"] = True
        return {"type": "text", "data": "Хочешь, покажу это на изображении?"}

    ctx = get_image_context(user_id)

    route = await route_request(text, ctx)

    # 🔥 ВАЖНО: теперь не генерим — создаём задачу
    if route == "image_generate" or is_generate_request(text):
        return {
            "type": "image_task",
            "prompt": text
        }

    # остальное оставили как есть
    return {"type": "text", "data": "Обычный ответ"}
