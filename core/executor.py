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


# 🔥 ДОБАВЛЕНО (SAFE)
def is_code_like(text):
    triggers = [
        "Traceback",
        "File \"",
        "line ",
        "ERROR",
        "Exception",
        "psycopg2",
        "SELECT",
        "INSERT",
        "UPDATE",
        "def ",
        "import "
    ]
    return any(t.lower() in text.lower() for t in triggers)


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

    return None


async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    state = get_state(user_id)
    mode = get_mode(user_id)

    if callback_data is not None:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()

    # 🔥 FIX: безопасный перехват кода
    if callback_data is None and not text.startswith("/"):
        try:
            if is_code_like(text):
                analysis = analyze_code(text)

                if isinstance(analysis, dict):
                    return analysis

                return {"type": "text", "data": str(analysis)}
        except Exception as e:
            return {"type": "text", "data": f"Ошибка анализа кода: {e}"}

    update_visual_state(text, state)

    allowed, seconds = can_send_message(user_id)

    if not allowed:
        return {
            "type": "text",
            "data": f"Лимит закончился 👀\nПопробуй через: {format_time(seconds)}"
        }

    if is_noise(t):
        return {"type": "text", "data": "Я тут 🙂 Что хочешь сделать?"}

    if "время" in t:
        return {"type": "text", "data": datetime.now().strftime("Сейчас %H:%M")}

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, get_energy(user_id))
    )

    return {"type": "text", "data": result["content"]}
