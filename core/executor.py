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

# 🔥 ДОБАВИЛИ (опыт)
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

    # 🔥 ЗАГРУЖАЕМ ОПЫТ (НО НЕ ЛОМАЕМ ЛОГИКУ)
    try:
        experience = load_experience(user_id)
    except:
        experience = {}

    try:
        intent = detect_intent(text)
    except:
        intent = None

    try:
        intent_ai = detect_intent_ai(text)
    except:
        intent_ai = None

    if is_image_question(text) and ctx and ctx.get("path"):
        try:
            result = await analyze_image(user_id, ctx["path"], text)
            if result:
                return result
        except Exception as e:
            print("🔥 IMAGE ANALYZE ERROR:", e)

    context = {
        "chat_id": chat_id,
        "state": state,
        "image": ctx,
        "anchor": anchor,
        "mode": mode,
        "task_type": detect_task_type(text),
        "energy": energy,
        "experience": experience  # 🔥 ПРОКИНУЛИ В КОНТЕКСТ
    }

    def is_valid_result(result):
        if not result:
            return False
        if not isinstance(result, dict):
            return False
        if "type" not in result:
            return False
        if result["type"] == "text" and not result.get("data"):
            return False
        if result["type"] == "image" and not result.get("data"):
            return False
        return True

    candidates = []

    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                try:
                    score = room.evaluate(text, context)
                except:
                    score = 1

                # 🔥 МЯГКОЕ ВЛИЯНИЕ ОПЫТА
                try:
                    actions = experience.get(str(user_id), {}).get("actions", [])
                    if actions:
                        last = actions[-1]
                        if last.get("status") == "positive":
                            score += 0.1
                        elif last.get("status") == "negative":
                            score -= 0.1
                except:
                    pass

                candidates.append((score, room))
                print(f"🧠 CANDIDATE: {room.name} | score={score}")

        except Exception as e:
            print(f"🔥 CAN_HANDLE ERROR [{room.name}]:", e)

    boosted = []

    for score, room in candidates:
        if room.name == "science":
            if "=" in text or "sin" in text or "x" in text:
                score += 5
        boosted.append((score, room))

    candidates = boosted

    if not candidates:
        print("⚠️ NO ROOMS → fallback")
        result = await run_with_typing(
            chat_id,
            text_process(user_id, text, state, energy)
        )
        return {"type": "text", "data": result["content"]}

    candidates.sort(reverse=True, key=lambda x: x[0])

    for score, room in candidates:
        try:
            print(f"🚀 TRY ROOM: {room.name} | score={score}")

            result = await room.handle(user_id, text, context, run_with_typing)

            # ===== SELF CHECK (НЕ БЛОКИРУЕТ) =====
            try:
                from blocks.self_check import self_check

                valid, error = self_check(result, text, energy)

                if not valid:
                    print(f"⚠️ SELF CHECK WARNING: {room.name} | error={error}")

            except Exception as e:
                print("🔥 SELF CHECK ERROR:", e)

            if is_valid_result(result):
                print(f"✅ SUCCESS: {room.name} | type={result['type']}")

                # 🔥 ЗАПИСЬ ОПЫТА
                try:
                    state["last_action"] = {
                        "type": result.get("type"),
                        "intent": context.get("task_type"),
                        "status": "success"
                    }
                    update_experience(user_id, state)
                except Exception as e:
                    print("🔥 EXPERIENCE ERROR:", e)

                return result
            else:
                print(f"❌ INVALID RESULT: {room.name}")

        except Exception as e:
            print(f"🔥 ROOM HANDLE ERROR [{room.name}]:", e)

    try:
        routed = route_request(text, intent=intent, intent_ai=intent_ai)
        if routed:
            return routed
    except Exception as e:
        print("🔥 ROUTER ERROR:", e)

    print("⚠️ ALL ROOMS FAILED → fallback")

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
