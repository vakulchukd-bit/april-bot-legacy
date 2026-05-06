# blocks/subscription_module.py

# =========================================================
# 🔥 SUBSCRIPTION MODULE
# Foundation for limits architecture
# =========================================================

from blocks.tariffs_config import (
    ADMIN_ID,
    FREE_MESSAGES_LIMIT,
    FREE_IMAGES_LIMIT,
    LITE_IMAGES_LIMIT,
    PREMIUM_IMAGES_LIMIT
)


async def check(user_id, action_type):

    # =====================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:
        return {"allowed": True}

    from storage import (
        can_send_message,
        can_generate_image,
        get_user_plan
    )

    plan = get_user_plan(user_id)

    # =====================================================
    # 🆓 FREE
    # =====================================================

    if plan == "free":

        # =================================================
        # 💬 MESSAGE LIMIT
        # =================================================

        if action_type == "message":

            if not can_send_message(
                user_id,
                limit=FREE_MESSAGES_LIMIT
            ):

                return {
                    "allowed": False,
                    "reason":
                        "⛔ Лимит сообщений достигнут\n\n"
                        "Попробуйте позже "
                        "или откройте Lite / Premium"
                }

        # =================================================
        # 🖼 IMAGE LIMIT
        # =================================================

        if action_type == "image":

            if not can_generate_image(
                user_id,
                limit=FREE_IMAGES_LIMIT
            ):

                return {
                    "allowed": False,
                    "reason":
                        "⛔ Лимит генераций достигнут\n\n"
                        "Попробуйте позже "
                        "или откройте Lite / Premium"
                }

    # =====================================================
    # ⚡ LITE
    # =====================================================

    elif plan == "lite":

        # =================================================
        # ♾️ UNLIMITED MESSAGES
        # =================================================

        if action_type == "message":
            return {"allowed": True}

        # =================================================
        # 🖼 IMAGE LIMIT
        # =================================================

        if action_type == "image":

            if not can_generate_image(
                user_id,
                limit=LITE_IMAGES_LIMIT
            ):

                return {
                    "allowed": False,
                    "reason":
                        "⚡ Lite лимит изображений достигнут\n\n"
                        "Попробуйте позже "
                        "или перейдите на Premium"
                }

    # =====================================================
    # 👑 PREMIUM
    # =====================================================

    elif plan == "premium":

        # =================================================
        # ♾️ UNLIMITED MESSAGES
        # =================================================

        if action_type == "message":
            return {"allowed": True}

        # =================================================
        # 🖼 IMAGE LIMIT
        # =================================================

        if action_type == "image":

            if not can_generate_image(
                user_id,
                limit=PREMIUM_IMAGES_LIMIT
            ):

                return {
                    "allowed": False,
                    "reason":
                        "👑 Premium лимит изображений достигнут\n\n"
                        "Попробуйте позже"
                }

    # =====================================================
    # ✅ ALLOWED
    # =====================================================

    return {"allowed": True}
