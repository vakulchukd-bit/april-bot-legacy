# blocks/subscription_module.py

async def check(user_id, action_type):
    from storage import check_subscription, can_send_message, can_generate_image

    if not check_subscription(user_id):
        if action_type == "message":
            if not can_send_message(user_id):
                return {"allowed": False, "reason": "⛔ Лимит сообщений"}

        if action_type == "image":
            if not can_generate_image(user_id):
                return {"allowed": False, "reason": "⛔ Лимит картинок"}

    return {"allowed": True}
