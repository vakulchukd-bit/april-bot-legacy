# blocks/state_manager.py

state = {}

# 🔥 ДОБАВИЛИ ОТДЕЛЬНОЕ ХРАНИЛИЩЕ (стабильность)
image_storage = {}


def get_state(user_id):
    if user_id not in state:
        state[user_id] = {
            "dialog": [],
            "image_context": None,
            "awaiting": False,
            "last_prompt": None,
            "task_type": None  # 🔥 НОВОЕ ПОЛЕ (тип задачи)
        }
    return state[user_id]


# ===== IMAGE CONTEXT =====
def set_image_context(user_id, ctx):
    # 🔥 сохраняем в двух местах
    image_storage[user_id] = ctx
    get_state(user_id)["image_context"] = ctx


def get_image_context(user_id):
    # 🔥 сначала берём из стабильного хранилища
    ctx = image_storage.get(user_id)

    if ctx:
        return ctx

    # 🔥 fallback (если вдруг потерялось)
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


# ===== DIALOG =====
def add_dialog(user_id, role, content):
    dialog = get_state(user_id)["dialog"]

    dialog.append({
        "role": role,
        "content": content
    })

    # 🔥 ОГРАНИЧЕНИЕ (последние 6 сообщений)
    if len(dialog) > 6:
        dialog.pop(0)
