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


# ===== 🧠 СЕМАНТИКА =====
def detect_task_type(text: str):
    t = text.lower()

    if any(x in t for x in ["=", "x", "y=", "график", "реши", "уравнен"]):
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


# 🔥 EDIT
def is_edit_request(text: str):
    t = text.lower()
    triggers = [
        "убери", "добавь", "измени", "замени",
        "сделай", "сделай более", "сделай его",
        "усиль", "сильнее", "ярче", "темнее",
        "злее", "добрее", "переделай", "улучши"
    ]
    return any(word in t for word in triggers)


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


# ===== 🧠 SUMMARY UPDATE =====
def update_memory_summary(state):
    dialog = state.get("dialog", [])

    if len(dialog) < 10:
        return

    last_chunk = dialog[:-10]

    if not last_chunk:
        return

    # 🔥 СЖАТИЕ СМЫСЛА (простое, безопасное)
    texts = [m.get("content", "") for m in last_chunk if m.get("role") == "user"]

    if not texts:
        return

    combined = " ".join(texts)[-1000:]

    prev = state.get("memory_summary", "")

    new_summary = (prev + " " + combined).strip()

    # ограничение размера
    state["memory_summary"] = new_summary[-2000:]

    # оставляем только последние 10
    state["dialog"] = dialog[-10:]


async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)

    # ===== 🔥 ОБНОВЛЕНИЕ ПАМЯТИ =====
    update_memory_summary(state)

    if state.get("image_generating"):
        return {
            "type": "text",
            "data": "⏳ Подожди, я ещё генерирую изображение..."
        }

    mode = get_mode(user_id)

    if "visual_intent" not in state:
        state["visual_intent"] = 0

    if "offered_visual" not in state:
        state["offered_visual"] = False

    if callback_data is not None:
        sub = handle_subscription(callback_data, user_id)
        if sub:
            return sub

    t = text.lower().strip()

    task_type = detect_task_type(text)
    print("🧠 TASK TYPE:", task_type)

    if state.get("offered_visual") and any(w in t for w in ["да", "давай", "покажи", "хочу", "ок", "го"]):
        return {"type": "image_task", "prompt": text}

    try:
        await detect_intent_ai(text)
    except:
        pass

    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

    energy = get_energy(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    route = await route_request(text, ctx)
    print("🧭 ROUTE:", route)

    if ctx:
        if is_edit_request(text):
            path = ctx.get("path")
            if path:
                return await image_edit(user_id, path, text)

        if ctx.get("path") and is_image_question(text):
            return await analyze_image(user_id, ctx.get("path"), text)

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": task_type,
        "energy": energy
    }

    candidates = []

    for room in ROOMS:
        try:
            score = room.evaluate(text, context) if hasattr(room, "evaluate") else \
                (1.0 if room.can_handle(text, context) else 0.0)

            candidates.append((room, score))
        except:
            pass

    candidates.sort(key=lambda x: x[1], reverse=True)

    if candidates and candidates[0][1] > 0:
        room = candidates[0][0]
        return await room.handle(user_id, text, context, run_with_typing)

    if is_generate_request(text):
        return {"type": "image_task", "prompt": text}

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
