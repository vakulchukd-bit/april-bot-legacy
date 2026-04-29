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

from blocks.energy_manager import get_energy

from blocks.experience import update_experience, load_experience

import re


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

    if any(x in t for x in ["создай", "сгенерируй", "нарисуй", "сделай"]):
        return "image_generate"

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

    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

    energy = get_energy(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    task_type = detect_task_type(text)

    # --- IMAGE EDIT ---
    if task_type == "image_edit":
        if ctx:
            print("🖼️ DIRECT IMAGE EDIT")
            return await image_edit(user_id, text, state)
        else:
            return {
                "type": "text",
                "data": "Сначала нужно создать изображение 🙂"
            }

    # --- IMAGE GENERATE ---
    if task_type == "image_generate":

        # UX как было (но аккуратно)
        try:
            await run_with_typing(chat_id, asyncio.sleep(0))
        except:
            pass

        if len(text.strip()) > 15:
            print("🖼️ DIRECT IMAGE GENERATE (explicit)")
            prompt = extract_image_prompt(text)
            return await image_generate(user_id, prompt, state)

        summary = state.get("memory_summary")
        dialog = state.get("dialog", [])

        if summary:
            prompt = extract_image_prompt(summary)
            print("🖼️ GENERATE FROM SUMMARY")
            return await image_generate(user_id, prompt, state)

        if dialog:
            last_user = next(
                (m["content"] for m in reversed(dialog) if m["role"] == "user"),
                None
            )
            if last_user:
                prompt = extract_image_prompt(last_user)
                print("🖼️ GENERATE FROM DIALOG")
                return await image_generate(user_id, prompt, state)

        return {
            "type": "text",
            "data": "Что именно хочешь изобразить?"
        }

    # ===== ВСЁ ОСТАЛЬНОЕ =====

    try:
        experience = load_experience(user_id)
    except:
        experience = {}

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": detect_task_type(text),
        "energy": energy,
        "experience": experience
    }

    try:
        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state, energy)
        )
        return {"type": "text", "data": result["content"]}
    except Exception as e:
        print("🔥 FINAL FALLBACK ERROR:", e)

    return {
        "type": "text",
        "data": "⚠️ Не удалось обработать запрос."
    }
