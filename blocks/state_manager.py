# blocks/state_manager.py

dialog_memory = {}
image_context = {}
current_task = {}


def get_state(user_id):
    return {
        "dialog": dialog_memory.get(user_id, []),
        "image_context": image_context.get(user_id),
        "current_task": current_task.get(user_id)
    }


# ===== TASK =====

def set_task(user_id, task):
    current_task[user_id] = task


def get_task(user_id):
    return current_task.get(user_id)


def clear_task(user_id):
    current_task[user_id] = None


# ===== IMAGE =====

def set_image_context(user_id, ctx):
    image_context[user_id] = ctx


def get_image_context(user_id):
    return image_context.get(user_id)


# ===== DIALOG =====

def add_dialog(user_id, role, content):
    dialog_memory.setdefault(user_id, []).append({
        "role": role,
        "content": content
    })
