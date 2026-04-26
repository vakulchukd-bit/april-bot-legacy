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
from storage import set_subscription, can_edit, get_user_plan, can_send_message, format_time

from blocks.energy_manager import get_energy
from blocks.science_room import ScienceRoom

import random


# 🔥 ДОБАВЛЕНО (улучшенный детектор)
def is_code_like(text):
    t = text.lower()

    strong = ["traceback", "error", "exception", "psycopg2", "sql"]
    weak = ["import", "def ", "select ", "insert ", "update ", "line ", "file \""]

    score = 0

    for s in strong:
        if s in t:
            score += 2

    for s in weak:
        if s in t:
            score += 1

    return score >= 2


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

EDIT_LIMIT_REPLIES = [
    "Ты почти довёл до идеала 👀\nНо на сегодня правок хватит.\nХочешь продолжить без ограничений?",
    "Ещё чуть-чуть — и было бы идеально ✨\nНо лимит правок закончился.\nПродолжим без ограничений?",
    "Ты прямо на финише 🔥\nОсталась пара штрихов… но лимит на сегодня всё.\nДавай добьём в PRO?",
]


ADMIN_ID = 2016592532


def update_visual_state(text, state):
    t = text.lower()

    visual_signals = [
        "представь", "атмосфера", "сцена", "как будто",
        "ночь", "свет", "город", "кадр", "выглядит"
    ]

    if any(x in t for x in visual_signals):
        state["visual_mode"] = True
        state["visual_progress"] = state.get("visual_progress", 0) + 1
    else:
        state["visual_progress"] = max(0, state.get("visual_progress", 0) - 1)

    state["visual_ready"] = state.get("visual_progress", 0) >= 2


def is_action_intent(text):
    t = text.lower()
    return any(x in t for x in [
        "покажи", "давай", "сделай", "зафиксируй", "вот это", "делаем"
    ])


def is_vague(text):
    vague = ["лучше", "не так", "красивее", "переделай", "что-нибудь", "что-то", "придумай"]
    return any(x in text.lower() for x in vague)


def is_noise(text):
    return len(text.strip()) <= 2


def is_ambiguous_request(text):
    t = text.lower()

    triggers = ["сделай", "создай", "кот", "картинку", "нарисуй", "придумай", "идею"]

    if len(t.split()) <= 3 and any(x in t for x in triggers):
        return True

    if is_vague(t) and len(t.split()) <= 4:
        return True

    return False


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


async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    state = get_state(user_id)
    mode = get_mode(user_id)

    if callback_data is not None:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()

    # 🔥 ВСТАВКА (без ломания)
    if callback_data is None and not text.startswith("/"):
        try:
            if is_code_like(text):
                analysis = analyze_code(text)

                if isinstance(analysis, dict):
                    return analysis

                return {
                    "type": "text",
                    "data": str(analysis)
                }
        except Exception:
            pass

    # 🔥 дальше ВСЁ твое как было
    update_visual_state(text, state)

    allowed, seconds = can_send_message(user_id)

    if not allowed:
        time_text = format_time(seconds) if seconds else "скоро"

        return {
            "type": "text",
            "data": (
                f"Лимит закончился 👀\n"
                f"Попробуй через: {time_text}"
            ),
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Перейти на Lite", callback_data="buy_lite")]
            ])
        }

    if state.get("visual_ready") and is_action_intent(text):
        state["scene"] = "image"
        return await image_generate(user_id, text, state)

    if is_noise(t):
        return {
            "type": "text",
            "data": "Я тут 🙂 Что хочешь сделать?"
        }

    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

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

    if scene == "image":

        if not t:
            return {"type": "text", "data": random.choice(IMAGE_OBSERVE)}

        if is_vague(t):
            return {"type": "text", "data": random.choice(IMAGE_GUIDE)}

        if ctx and ctx.get("image_bytes"):

            plan = get_user_plan(user_id)
            is_admin = user_id == ADMIN_ID

            if not is_admin:

                if plan == "free":
                    return {
                        "type": "text",
                        "data": "Редактирование доступно только в Lite и Premium 👀",
                        "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🚀 Выбрать тариф", callback_data="buy_lite")]
                        ])
                    }

                if not can_edit(user_id):
                    return {
                        "type": "text",
                        "data": random.choice(EDIT_LIMIT_REPLIES),
                        "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="👑 Перейти в Premium", callback_data="buy_premium")]
                        ])
                    }

            return await image_edit(user_id, None, text, state)

        if any(x in t for x in ["сделай", "создай", "нарисуй", "картинку"]):
            return await image_generate(user_id, text, state)

        return {"type": "text", "data": "Скажи, что изменить 👀"}

    if any(x in t for x in ["картинку", "изображение", "нарисуй", "создай"]):
        state["scene"] = "image"
        return await image_generate(user_id, text, state)

    intent = detect_intent(text)
    response_mode = detect_response_mode(text)

    anchor = get_anchor(user_id)

    if is_ambiguous_request(t):
        text = f"""
Сообщение пользователя: "{text}"

Ответь как живой собеседник:
- не задавай прямой вопрос
- мягко предложи варианты
- подведи человека к мысли
- не используй шаблоны
"""

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

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
