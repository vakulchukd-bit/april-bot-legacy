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
            "dialog_state": {}
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


# ===== DIALOG =====
from storage import get_user_plan

def add_dialog(user_id, role, content):
    state_obj = get_state(user_id)
    dialog = state_obj["dialog"]

    dialog.append({
        "role": role,
        "content": content
    })

    # 🔥 ДИНАМИЧЕСКИЙ ЛИМИТ
    plan = get_user_plan(user_id)
    limit = get_dialog_limit(user_id, plan)

    if len(dialog) > limit:
        dialog.pop(0)


# ===== DIALOG STATE =====
def get_dialog_state(user_id):
    return get_state(user_id).get("dialog_state", {})


def set_dialog_state(user_id, data):
    get_state(user_id)["dialog_state"] = data
