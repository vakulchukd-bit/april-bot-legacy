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
from blocks.image_edit_module import process as image_edit

from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import set_subscription, can_edit, get_user_plan  # 🔥 ДОБАВИЛИ

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

IMAGE_OBSERVE = [
    "Интересный кадр. Тут можно поиграть со светом или фоном.",
    "Красивая сцена. Либо усилить детали, либо поменять атмосферу.",
    "Есть настроение. Можно аккуратно доработать или сделать сильнее.",
]

IMAGE_GUIDE = [
    "Можно пойти мягко — подкрутить цвет/свет, или сильнее — поменять стиль. Как ближе?",
    "Тут либо слегка улучшить, либо переделать заметнее. В какую сторону идём?",
    "Можно усилить акцент или поменять окружение. Что тебе ближе?",
]

# 🔥 НОВОЕ — лимит edit
EDIT_LIMIT_REPLIES = [
    "Ты почти довёл до идеала 👀\nНо на сегодня правок хватит.\nХочешь продолжить без ограничений?",
    "Ещё чуть-чуть — и было бы идеально ✨\nНо лимит правок закончился.\nПродолжим без ограничений?",
    "Ты прямо на финише 🔥\nОсталась пара штрихов… но лимит на сегодня всё.\nДавай добьём в PRO?",
]


def is_vague(text):
    vague = ["лучше", "не так", "красивее", "переделай", "что-нибудь"]
    return any(x in text.lower() for x in vague)


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

    energy = get_energy(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")

    if ctx:
        state["scene"] = "image"

    scene = state.get("scene", "text")

    # ===== IMAGE SCENE =====
    if scene == "image":

        if not t:
            return {"type": "text", "data": random.choice(IMAGE_OBSERVE)}

        if is_vague(t):
            return {"type": "text", "data": random.choice(IMAGE_GUIDE)}

        # 🔥 ЕСЛИ РЕДАКТИРОВАНИЕ
        if ctx and ctx.get("image_bytes"):

            plan = get_user_plan(user_id)

            # FREE вообще не может редактировать
            if plan == "free":
                return {
                    "type": "text",
                    "data": "Редактирование доступно только в Lite и Premium 👀",
                    "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚀 Выбрать тариф", callback_data="buy_lite")]
                    ])
                }

            # проверка лимита
            if not can_edit(user_id):
                return {
                    "type": "text",
                    "data": random.choice(EDIT_LIMIT_REPLIES),
                    "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="👑 Перейти в Premium", callback_data="buy_premium")]
                    ])
                }

            return await image_edit(user_id, None, text, state)

        # иначе генерация
        return await image_generate(user_id, text, state)

    # ===== НЕДОВОЛЬСТВО =====
    if any(x in t for x in ["не так", "не то", "не нравится"]):
        state["needs_refinement"] = True
        return {"type": "text", "data": random.choice(MISSED_REPLIES)}

    # ===== ПЕРЕХОД В IMAGE =====
    if any(x in t for x in ["картинку", "изображение", "сделай нормально", "с деталями"]):
        state["scene"] = "image"
        return await image_generate(user_id, text, state)

    # ===== INTENT =====
    intent = detect_intent(text)
    response_mode = detect_response_mode(text)

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

    science = ScienceRoom()

    if science.can_handle(text, context):
        result = await science.handle(user_id, text, context, run_with_typing)
        if result:
            return result

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(user_id, text, context, run_with_typing)
                if result:
                    return result
        except Exception as e:
            print(f"🔥 ROOM ERROR [{room.name}]:", e)

    if response_mode == "link":
        return {
            "type": "text",
            "data": "Вот тебе ссылка 👇\n👉 https://example.com"
        }

    if response_mode == "copy":
        text = f"Напиши готовый текст:\n\n{text}"

    if response_mode == "format":
        text = f"Оформи красиво:\n\n{text}"

    if intent == "question":
        if anchor:
            text = f"Контекст: {anchor['current']}\n\n{text}"

        text = f"{build_context_text()}\n\n{text}"

        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state, energy)
        )

        return {"type": "text", "data": result["content"]}

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
