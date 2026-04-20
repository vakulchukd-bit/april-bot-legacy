# blocks/state_manager.py

dialog_memory = {}
last_prompt = {}
awaiting_image_prompt = {}
image_context = {}


def get_state(user_id):
    return {
        "dialog": dialog_memory.get(user_id, []),
        "last_prompt": last_prompt.get(user_id),
        "awaiting_image": awaiting_image_prompt.get(user_id, False),
        "image_context": image_context.get(user_id)
    }


def set_image_context(user_id, ctx):
    image_context[user_id] = ctx


def get_image_context(user_id):
    return image_context.get(user_id)


def set_awaiting(user_id, value: bool):
    awaiting_image_prompt[user_id] = value


def get_awaiting(user_id):
    return awaiting_image_prompt.get(user_id, False)


def set_last_prompt(user_id, prompt):
    last_prompt[user_id] = prompt


def get_last_prompt(user_id):
    return last_prompt.get(user_id)


def add_dialog(user_id, role, content):
    dialog_memory.setdefault(user_id, []).append({
        "role": role,
        "content": content
    })
