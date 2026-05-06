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
        check_subscription,
        can_send_message,
        can_generate_image,
        get_user_plan
    )

    plan = get_user_plan(user_id)

    # =====================================================
    # 🆓 FREE
    # =====================================================

    if plan == "free":

        # ================= MESSAGE =================

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

        # ================= IMAGE =================

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

        if action_type == "image":

            if not can_generate_image(
                user_id,
                limit=LITE_IMAGES_LIMIT
            ):

                return {
                    "allowed": False,
                    "reason":
                        "⚡ Lite лимит изображений достигнут\n\n"
                        "Лимит обновится позже"
                }

    # =====================================================
    # 👑 PREMIUM
    # =====================================================

    elif plan == "premium":

        if action_type == "image":

            if not can_generate_image(
                user_id,
                limit=PREMIUM_IMAGES_LIMIT
            ):

                return {
                    "allowed": False,
                    "reason":
                        "👑 Premium лимит достигнут\n\n"
                        "Попробуйте немного позже"
                }

    # =====================================================
    # ✅ ALLOWED
    # =====================================================

    return {"allowed": True}
