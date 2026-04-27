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

        print("🔥 PAYMENT SAVED")

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
    t = text.lower()
    triggers = ["убери", "добавь", "измени", "замени"]
    return any(word in t for word in triggers)


def is_generate_request(text: str):
    t = text.lower()
    verbs = ["создай", "сгенерируй", "нарисуй", "сделай"]
    objects = ["картинку", "изображение", "фото", "арт", "рисунок"]
    return any(v in t for v in verbs) and any(o in t for o in objects)


def is_image_question(text: str):
    t = text.lower()
    triggers = [
        "что на картинке",
        "что это",
        "что справа",
        "что слева",
        "что здесь",
        "что изображено"
    ]
    return any(tr in t for tr in triggers)


async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    # 🔥 INIT
    if "visual_intent" not in state:
        state["visual_intent"] = 0

    if "offered_visual" not in state:
        state["offered_visual"] = False

    if callback_data is not None:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()

    # 🔥 накопление намерения
    if any(p in t for p in [
        "хочу увидеть",
        "сложно представить",
        "как выглядит",
        "покажи",
    ]):
        state["visual_intent"] += 1
    else:
        state["visual_intent"] = max(0, state["visual_intent"] - 1)

    print("👁 VISUAL INTENT:", state["visual_intent"])

    # 🔥 AI intent
    ai_intent = None
    try:
        ai_intent = await detect_intent_ai(text)
        print("🧠 AI INTENT:", ai_intent)
    except Exception as e:
        print("🔥 AI INTENT ERROR:", e)

    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

    if mode == "engineering" and not text.startswith("/"):
        if text.lower() == "/analiz":
            return {"type": "text", "data": "📥 Жду код..."}
        return {"type": "admin_report", "data": analyze_code(text)}

    if t == "привет":
        return {"type": "text", "data": "Привет 🙂"}

    energy = get_energy(user_id)

    intent = detect_intent(text)
    response_mode = detect_response_mode(text)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    # 🔥 ROUTER
    route = await route_request(text, ctx)
    print("🧭 ROUTE:", route)

    # 🔥 предложение
    if state["visual_intent"] >= 2 and not state["offered_visual"]:
        state["offered_visual"] = True
        return {
            "type": "text",
            "data": "Хочешь, покажу это на изображении?"
        }

    if ctx:
        state["has_image"] = True
    else:
        state["has_image"] = False

    # ===== GENERATE =====
    if route == "image_generate" or is_generate_request(text):
        result = await run_with_typing(chat_id, image_generate(user_id, text, state))

        if result and result.get("type") == "image":
            set_image_context(user_id, {"type": "generated", "path": None, "prompt": text})
            state["visual_intent"] = 0
            state["offered_visual"] = False

        return result

    # ===== EDIT =====
    if ctx and (route == "image_edit" or is_edit_request(text)):
        path = ctx.get("path")
        if path:
            return await image_edit(user_id, path, text)

    # ===== ANALYZE =====
    if ctx and ctx.get("path") and (
        route == "image_analyze" or is_image_question(text)
    ):
        return await analyze_image(user_id, ctx.get("path"), text)

    # ===== ROOMS =====
    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": None,
        "energy": energy
    }

    science = ScienceRoom()
    if science.can_handle(text, context):
        return await science.handle(user_id, text, context, run_with_typing)

    for room in ROOMS:
        if room.can_handle(text, context):
            return await room.handle(user_id, text, context, run_with_typing)

    # ===== GPT =====
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
