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

# 🔥 INTERPRETATION
from blocks.interpretation_layer import interpret_request

import re


# ===============================
# 🔥 VAGUE DETECTOR
# ===============================
def is_vague_request(text: str):
    t = text.lower().strip()

    vague_words = ["что-нибудь", "что то", "что-то", "придумай"]

    if any(v in t for v in vague_words):
        return True

    if len(t.split()) <= 3 and "сделай" in t:
        return True

    return False


# ===============================
# 🔥 DISSATISFACTION DETECTOR (НОВОЕ)
# ===============================
def is_dissatisfied(text: str):
    t = text.lower()

    triggers = [
        "не то", "не понял", "не это", "другое",
        "не подходит", "не правильно", "неправильно",
        "ты не понял", "я не это имел"
    ]

    return any(tr in t for tr in triggers)


# 🔥 OUTPUT MODE
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

    # ===============================
    # 🔥 INTERPRETATION
    # ===============================
    try:
        interpreted = interpret_request(text)
        if interpreted and interpreted.get("normalized"):
            print("🧠 INTERPRET:", interpreted)
            text = interpreted["normalized"]
    except Exception as e:
        print("🔥 INTERPRET ERROR:", e)

    # ===============================
    # 🔥 VAGUE GUARD
    # ===============================
    try:
        if is_vague_request(text):
            print("🧠 VAGUE DETECTED")

            result = await run_with_typing(
                chat_id,
                text_process(
                    user_id,
                    "Предложи что можно сделать: график, код или изображение. Ответ живой.",
                    state,
                    energy="LOW"
                )
            )

            content = None
            if isinstance(result, dict):
                content = result.get("content")

            if not content:
                content = "Могу сделать что-нибудь интересное 🙂 Например: график, код или изображение."

            return {
                "type": "text",
                "data": content
            }

    except Exception as e:
        print("🔥 VAGUE ERROR:", e)

    # ===============================
    # 🔥 DISSATISFACTION FLOW (НОВОЕ)
    # ===============================
    try:
        if is_dissatisfied(text):
            print("🧠 USER DISSATISFIED → USE AI")

            result = await run_with_typing(
                chat_id,
                text_process(
                    user_id,
                    text,
                    state,
                    energy="LOW"
                )
            )

            content = None
            if isinstance(result, dict):
                content = result.get("content")

            if not content:
                content = "Давай попробуем по-другому 🙂 Уточни, что именно ты хочешь."

            return {
                "type": "text",
                "data": content
            }

    except Exception as e:
        print("🔥 DISSATISFACTION ERROR:", e)

    if "время" in t:
        now = datetime.now().strftime("%H:%M")
        return {"type": "text", "data": f"Сейчас {now}"}

    energy = get_energy(user_id)

    ctx = get_image_context(user_id) or state.get("image_context")
    anchor = get_anchor(user_id)

    task_type = detect_task_type(text)
    output_mode = detect_output_mode(text)

    # ===============================
    # IMAGE EDIT
    # ===============================
    if task_type == "image_edit":
        if ctx:
            return await image_edit(user_id, text, state)
        else:
            return {"type": "text", "data": "Сначала нужно создать изображение 🙂"}

    # ===============================
    # IMAGE GENERATE
    # ===============================
    if task_type == "image_generate":

        if len(text.strip()) > 15:
            prompt = extract_image_prompt(text)
            return await image_generate(user_id, prompt, state)

        summary = state.get("memory_summary")
        dialog = state.get("dialog", [])

        if summary:
            prompt = extract_image_prompt(summary)
            return await image_generate(user_id, prompt, state)

        if dialog:
            last_user = next((m["content"] for m in reversed(dialog) if m["role"] == "user"), None)
            if last_user:
                prompt = extract_image_prompt(last_user)
                return await image_generate(user_id, prompt, state)

        return {"type": "text", "data": "Что именно хочешь изобразить?"}

    # ===============================
    # IMAGE ANALYZE
    # ===============================
    if is_image_question(text) and ctx:
        if ctx.get("type") == "generated" and ctx.get("hint"):
            return {"type": "text", "data": ctx["hint"]}

        if ctx.get("type") == "uploaded" and ctx.get("path"):
            try:
                result = await analyze_image(ctx["path"])
                return {"type": "text", "data": result}
            except Exception as e:
                print("🔥 IMAGE ANALYZE ERROR:", e)

    # ===============================
    # CONTEXT
    # ===============================
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
        "task_type": task_type,
        "energy": energy,
        "experience": experience,
        "output_mode": output_mode
    }

    def is_valid_result(result):
        return (
            result
            and isinstance(result, dict)
            and "type" in result
            and (result["type"] != "text" or result.get("data"))
        )

    candidates = []

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                score = room.evaluate(text, context)
                candidates.append((score, room))
        except Exception as e:
            print(f"🔥 CAN_HANDLE ERROR [{room.name}]:", e)

    if not candidates:
        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state, energy)
        )
        return {"type": "text", "data": result["content"]}

    candidates.sort(reverse=True, key=lambda x: x[0])

    for score, room in candidates:
        try:
            result = await room.handle(user_id, text, context, run_with_typing)
            if is_valid_result(result):
                return result
        except Exception as e:
            print(f"🔥 ROOM HANDLE ERROR [{room.name}]:", e)

    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    return {"type": "text", "data": result["content"]}
