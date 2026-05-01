# ===============================
# 🔥 CENTRAL CONTROLLER (ГАРАНТИРОВАННЫЙ ПЕРЕХВАТ)
# ===============================

def central_controller(text, state):
    try:
        t = text.lower().strip()

        if any(w in t for w in ["круче", "резче", "плавнее", "мягче"]):
            last = state.get("last_math")

            if last and last.get("type") == "function":
                expr = last.get("expr")

                if "круче" in t or "резче" in t:
                    expr = f"2*({expr})"
                elif "плавнее" in t or "мягче" in t:
                    expr = f"0.5*({expr})"

                state["last_math"]["expr"] = expr

                return {
                    "type": "text",
                    "data": "Окей, изменил функцию. Напиши 'построй'."
                }

        if "=" in t and not any(w in t for w in ["построй", "реши", "сделай"]):
            return {
                "type": "text",
                "data": "Вижу функцию. Напиши 'построй'."
            }

        return None

    except Exception as e:
        print("CONTROLLER ERROR:", e)
        return None


# 🔥 ОТЛОЖЕННЫЙ ПЕРЕХВАТ
def apply_execute_patch():
    try:
        import sys

        module = sys.modules.get(__name__)
        original = getattr(module, "execute", None)

        if not original:
            return

        async def wrapped_execute(user_id, text, chat_id, run_with_typing, callback_data=None):
            state = get_state(user_id)

            control = central_controller(text, state)

            if control:
                return control

            return await original(user_id, text, chat_id, run_with_typing, callback_data)

        setattr(module, "execute", wrapped_execute)

        print("✅ EXECUTE PATCH APPLIED")

    except Exception as e:
        print("PATCH ERROR:", e)


# 🔥 ЗАПУСК ПАТЧА ПОСЛЕ ЗАГРУЗКИ
import threading

def delayed_patch():
    try:
        apply_execute_patch()
    except:
        pass

threading.Timer(1.0, delayed_patch).start()
# ===============================
# 🔥 SAFE PATCH MODE (EXECUTOR)
# ===============================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


# 🔥 PATCH: контроль вызова executor
def patch_executor_start(user_id, text):
    safe_patch_log(f"EXECUTOR START: {user_id} | {text[:50]}")
    return None


# 🔥 PATCH: будущая точка расширения
def patch_executor_hook(*args, **kwargs):
    return None
from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.router import route_request

from blocks.state_manager import (
    get_state,
    get_image_context,
    set_image_context,
    add_dialog
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
from storage import find_knowledge, save_knowledge

from blocks.energy_manager import get_energy

from blocks.experience import update_experience, load_experience

from blocks.interpretation_layer import interpret_request

import re


# ===============================
# 🔥 ACTIVE TASK (УСИЛЕННЫЙ)
# ===============================
def update_active_task(state: dict, text: str, task_type: str):
    t = text.lower()

    if "y=" in t:
        state["active_task"] = {
            "type": "math",
            "data": text.strip()
        }

    elif any(w in t for w in ["сложнее", "проще", "волнист", "резче", "плавнее"]):
        active = state.get("active_task")
        if active and active.get("type") == "math":
            state["active_task"]["modify"] = t

    elif "график" in t:
        if "active_task" not in state:
            state["active_task"] = {
                "type": "math",
                "data": None
            }


def continue_active_task(state: dict, text: str):
    t = text.lower().strip()
    active = state.get("active_task")

    if not active:
        return text

    if any(w in t for w in ["построй", "сделай", "покажи", "давай"]):

        if active.get("type") == "math":

            if active.get("data"):
                return f"{active['data']} построить график"

            return "построй график"

    if "это" in t and "график" in t:
        if active.get("data"):
            return f"{active['data']} построить график"

    return text


# ===============================
# 🔥 SEMANTIC MEMORY (НОВОЕ)
# ===============================
def extract_and_store_semantics(state: dict, text: str, result_type: str = "text"):
    t = text.lower()

    # === 1. ФОРМУЛЫ ===
    match = re.search(r"y\s*=\s*([^\n\r]+)", t)
    if match:
        expr = match.group(1).strip()

        expr = expr.replace("^", "**")
        expr = expr.replace("sin", "np.sin")
        expr = expr.replace("cos", "np.cos")
        expr = expr.replace("tan", "np.tan")
        expr = expr.replace("log", "np.log")

        state["last_math"] = {
            "type": "function",
            "expr": expr
        }

    # === 2. КОД ===
    if "```" in text:
        state["last_code"] = text

    # === 3. ИЗОБРАЖЕНИЕ ===
    if result_type == "image":
        state["last_image"] = {
            "exists": True
        }

    # === 4. НАМЕРЕНИЕ ===
    if any(w in t for w in ["график", "функц"]):
        state["last_intent"] = "math"

    elif any(w in t for w in ["код", "html", "python", "js"]):
        state["last_intent"] = "code"

    elif any(w in t for w in ["изображение", "картин", "арт"]):
        state["last_intent"] = "image"


# ===============================
# ОСТАЛЬНОЕ
# ===============================
def is_vague_request(text: str):
    t = text.lower().strip()
    vague_words = ["что-нибудь", "что то", "что-то", "придумай"]

    if any(v in t for v in vague_words):
        return True

    if len(t.split()) <= 3 and "сделай" in t:
        return True

    return False


def is_dissatisfied(text: str):
    t = text.lower()
    triggers = [
        "не то", "не понял", "не это", "другое",
        "не подходит", "не правильно", "неправильно",
        "ты не понял", "я не это имел"
    ]
    return any(tr in t for tr in triggers)


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

    if any(x in t for x in ["создай", "сгенерируй", "нарисуй"]):
        return "image_generate"

    if "сделай" in t:
        return "text"

    return "text"


# ===============================
# EXECUTE
# ===============================
async def execute(user_id, text, chat_id, run_with_typing, callback_data=None):
    print("🔥 EXECUTOR RUNNING")

    state = get_state(user_id)
    mode = get_mode(user_id)

    # 🔥 сохраняем пользователя
    add_dialog(user_id, "user", text)

    t = text.lower().strip()

    # 🔥 ACTIVE TASK
    try:
        task_type = detect_task_type(text)
        update_active_task(state, text, task_type)
    except Exception as e:
        print("ACTIVE TASK ERROR:", e)

    energy = get_energy(user_id)

    context = {
        "chat_id": chat_id,
        "state": state,
        "mode": mode,
        "task_type": detect_task_type(text),
        "energy": energy,
        "output_mode": detect_output_mode(text)
    }

    # 🔥 ROOMS
    for room in ROOMS:
        try:
            if room.can_handle(text, context):
                result = await room.handle(user_id, text, context, run_with_typing)

                if result and result.get("type"):

                    output_text = str(result.get("data", ""))

                    add_dialog(user_id, "assistant", output_text)

                    # 🔥 НОВОЕ: сохраняем смысл
                    extract_and_store_semantics(
                        state,
                        output_text,
                        result.get("type", "text")
                    )

                    return result

        except Exception as e:
            print(f"ROOM ERROR [{room.name}]:", e)

    # 🔥 FALLBACK
    result = await run_with_typing(
        chat_id,
        text_process(user_id, text, state, energy)
    )

    if result and result.get("content"):
        add_dialog(user_id, "assistant", result["content"])

        # 🔥 НОВОЕ: сохраняем смысл
        extract_and_store_semantics(state, result["content"], "text")

    return {"type": "text", "data": result["content"]}
