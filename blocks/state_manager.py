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

def update_dialog(user_id, role, content):
    dialog_memory.setdefault(user_id, []).append({
        "role": role,
        "content": content
    })
