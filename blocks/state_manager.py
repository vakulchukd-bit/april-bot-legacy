# blocks/state_manager.py

state = {}

# 🔥 ДОБАВИЛИ ОТДЕЛЬНОЕ ХРАНИЛИЩЕ (стабильность)
image_storage = {}

ADMIN_ID = 2016592532


def get_dialog_limit(user_id, plan):
    if user_id == ADMIN_ID:
        return 50  # 🔥 админ почти без лимита

    return {
        "free": 10,
        "lite": 20,
        "premium": 30
    }.get(plan, 10)


def get_state(user_id):
    if user_id not in state:
        state[user_id] = {
            "dialog": [],
            "image_context": None,
            "awaiting": False,
            "last_prompt": None,
            "task_type": None,
            "memory_summary": "",
            "dialog_state": {},
            "active_flow": None,  # 🔥 NEW

            # ===============================
            # 🔥 META (ЕДИНАЯ СВЯЗКА ВСЕГО)
            # ===============================
            "meta": {
                "last_intent": None,
                "last_action": None,
                "last_entity": None  # 🔥 универсально: image / graph / code / etc
            }
        }
    return state[user_id]


# ===== IMAGE CONTEXT =====
def set_image_context(user_id, ctx):
    image_storage[user_id] = ctx
    get_state(user_id)["image_context"] = ctx


def get_image_context(user_id):
    ctx = image_storage.get(user_id)
    if ctx:
        return ctx
    return get_state(user_id).get("image_context")


# ===== AWAITING =====
def set_awaiting(user_id, value: bool):
    get_state(user_id)["awaiting"] = value


def get_awaiting(user_id):
    return get_state(user_id).get("awaiting", False)


# ===== LAST PROMPT =====
def set_last_prompt(user_id, prompt):
    get_state(user_id)["last_prompt"] = prompt


def get_last_prompt(user_id):
    return get_state(user_id).get("last_prompt")


# ===== SUMMARY =====
def update_memory_summary(user_id, new_text):
    """
    🔥 Упрощённое накопление смысла
    """
    state_obj = get_state(user_id)

    current = state_obj.get("memory_summary", "")
    updated = (current + " " + new_text).strip()

    if len(updated) > 500:
        updated = updated[-500:]

    state_obj["memory_summary"] = updated


# ===== 🔥 NEW: HARD MEMORY CLEAN (КЛЮЧЕВОЙ ФИКС)
def compress_dialog_to_summary(state_obj):
    dialog = state_obj.get("dialog", [])

    if not dialog:
        return

    # берём последние 5 сообщений как смысл
    last_messages = dialog[-5:]
    summary_parts = [m.get("content", "")[:80] for m in last_messages]

    short_summary = " | ".join(summary_parts)

    state_obj["memory_summary"] = short_summary

    # 🔥 оставляем только 1 системное сообщение
    state_obj["dialog"] = [{
        "role": "system",
        "content": short_summary
    }]

    print("🧹 DIALOG COMPRESSED")


# ===== 🔥 NEW: IMAGE MEMORY CLEAN =====
def trim_image_memory(state_obj):
    memory = state_obj.get("image_memory", [])

    if not memory:
        return

    if len(memory) > 3:
        state_obj["image_memory"] = memory[-3:]
        print("🧹 IMAGE MEMORY TRIMMED TO 3")


# ===== DIALOG =====
from storage import get_user_plan

def add_dialog(user_id, role, content):
    state_obj = get_state(user_id)
    dialog = state_obj["dialog"]

    dialog.append({
        "role": role,
        "content": content
    })

    # 🔥 META UPDATE (СВЯЗКА ДИАЛОГА)
    meta = state_obj.get("meta", {})

    if role == "user":
        meta["last_user_message"] = content
    else:
        meta["last_bot_message"] = content

    state_obj["meta"] = meta

    # 🔥 ДИНАМИЧЕСКИЙ ЛИМИТ
    plan = get_user_plan(user_id)
    limit = get_dialog_limit(user_id, plan)

    # 🔥 если превышен лимит → не просто pop, а СЖАТИЕ
    if len(dialog) > limit:
        compress_dialog_to_summary(state_obj)

    # 🔥 IMAGE MEMORY CONTROL
    trim_image_memory(state_obj)


# ===== DIALOG STATE =====
def get_dialog_state(user_id):
    return get_state(user_id).get("dialog_state", {})


def set_dialog_state(user_id, data):
    get_state(user_id)["dialog_state"] = data


# ===============================
# 🔥 ACTIVE FLOW (NEW)
# ===============================
def set_active_flow(user_id, flow: dict):
    get_state(user_id)["active_flow"] = flow


def get_active_flow(user_id):
    return get_state(user_id).get("active_flow")


def clear_active_flow(user_id):
    get_state(user_id)["active_flow"] = None


# ===============================
# 🔥 META HELPERS (НОВОЕ)
# ===============================
def set_last_entity(user_id, entity: dict):
    state_obj = get_state(user_id)
    meta = state_obj.get("meta", {})

    meta["last_entity"] = entity
    state_obj["meta"] = meta

    print("🧠 META UPDATED:", meta)


def get_last_entity(user_id):
    return get_state(user_id).get("meta", {}).get("last_entity")
