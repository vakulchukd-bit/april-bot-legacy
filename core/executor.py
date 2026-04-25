from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent

from blocks.state_manager import (
    get_state,
    get_image_context
)

from blocks.anchor_system import get_anchor
from blocks.mode_manager import get_mode

from blocks.context_system import build_context_text

from blocks.rooms_registry import ROOMS
from blocks.engineering_system import analyze_code

from blocks.image_module import process as image_generate

from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import set_subscription

# 🔥 ENERGY
from blocks.energy_manager import get_energy

# 🔥 SCIENCE
from blocks.science_room import ScienceRoom

import random


# ===== ЖИВЫЕ РЕАКЦИИ =====
MISSED_REPLIES = [
    "Похоже, не туда попал. Давай чуть подправим — как ты это видишь?",
    "Окей, значит не совсем это. Куда двигаем — схема или уже нормальное изображение?",
    "Ага, мимо. Давай соберём как надо — что поменять?",
    "Поймал, не то. Давай докрутим — что именно не так?",
]


# ===== SUBSCRIPTION HANDLER =====
def handle_subscription(callback_data, user_id):
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


# ===== EXECUTE =====
async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    state = get_state(user_id)
    mode = get_mode(user_id)

    if callback_data is not None:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()

    # ===== TIME =====
    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

    # ===== ENGINEERING =====
    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}
        return {"type": "admin_report", "data": analyze_code(text)}

    if t == "привет":
        return {"type": "text", "data": "Привет 🙂"}

    if t == "2+2":
        return {"type": "text", "data": "4"}

    # ===== ENERGY =====
    energy = get_energy(user_id)

    # ===== НОВОЕ ПОВЕДЕНИЕ (МЫШЛЕНИЕ) =====

    # если пользователь недоволен
    if any(x in t for x in ["не так", "не то", "не нравится"]):
        state["needs_refinement"] = True
        return {
            "type": "text",
            "data": random.choice(MISSED_REPLIES)
        }

    # если ранее было уточнение → можно уже генерить картинку
    if state.get("needs_refinement") and any(x in t for x in ["картинку", "изображение", "сделай нормально", "с деталями"]):
        state["needs_refinement"] = False
        return await image_generate(user_id, text, state)

    # если про "нарисуй", но без уточнений → сначала ASCII (через текст)
    if "нарисуй" in t and not any(x in t for x in ["картинку", "изображение"]):
        state["last_render"] = "ascii"

    # ===== INTENT =====
    intent = detect_intent(text)
    response_mode = detect_response_mode(text)

    # ===== CONTEXT =====
    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": "chat",
        "energy": energy
    }

    # ===== SCIENCE =====
    science = ScienceRoom()

    if science.can_handle(text, context):
        result = await science.handle(user_id, text, context, run_with_typing)
        if result:
            return result

    # ===== ROOMS =====
    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(user_id, text, context, run_with_typing)
                if result:
                    return result
        except Exception as e:
            print(f"🔥 ROOM ERROR [{room.name}]:", e)

    # ===== ССЫЛКИ =====
    if response_mode == "link":
        return {
            "type": "text",
            "data": (
                "Я не могу сократить ссылку прямо здесь,\n"
                "но вот тебе готовый вариант 👇\n\n"
                "👉 https://example.com\n\n"
                "Хочешь — оформлю красиво."
            )
        }

    # ===== COPY =====
    if response_mode == "copy":
        text = f"Напиши готовый текст:\n\n{text}"

    # ===== FORMAT =====
    if response_mode == "format":
        text = f"Оформи красиво:\n\n{text}"

    # ===== QUESTION =====
    if intent == "question":
        if anchor:
            text = f"Контекст: {anchor['current']}\n\n{text}"

        text = f"{build_context_text()}\n\n{text}"

        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state, energy)
        )

        return {"type": "text", "data": result["content"]}

    # ===== FALLBACK =====
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
