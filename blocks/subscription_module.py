# blocks/subscription_module.py

# =========================================================
# 🧠 APRIL SUBSCRIPTION MODULE
# =========================================================

"""
APRIL SUBSCRIPTION SYSTEM

ROLE:
- unified subscription access layer
- admin-panel compatible limits
- TXT-plan architecture support
- future web billing integration
- centralized access validation

SUPPORTED PLANS:
- free
- lite
- premium

FUTURE READY:
- txt configs
- db configs
- admin overrides
- dynamic limits
- web dashboard sync

IMPORTANT:
Этот слой НЕ:
- payment processor
- billing engine
- provider limiter
- token counter

Этот слой:
ТОЛЬКО access orchestration.
"""

# =========================================================
# 🔥 IMPORTS
# =========================================================

from blocks.tariffs_config import (

    ADMIN_ID,

    FREE_MESSAGES_LIMIT,
    FREE_IMAGES_LIMIT,

    LITE_IMAGES_LIMIT,

    PREMIUM_IMAGES_LIMIT
)

# =========================================================
# 🔥 PLAN DEFINITIONS
# =========================================================

PLAN_CONFIG = {

    # =====================================================
    # 🆓 FREE
    # =====================================================

    "free": {

        "title": "Free",

        "messages_limit":
            FREE_MESSAGES_LIMIT,

        "images_limit":
            FREE_IMAGES_LIMIT,

        "allow_images":
            True,

        "allow_priority":
            False,

        "allow_visual_boost":
            False,

        "allow_web_tools":
            True,

        "dialog_memory":
            "minimal"
    },

    # =====================================================
    # ⚡ LITE
    # =====================================================

    "lite": {

        "title": "Lite",

        "messages_limit":
            None,

        "images_limit":
            LITE_IMAGES_LIMIT,

        "allow_images":
            True,

        "allow_priority":
            True,

        "allow_visual_boost":
            True,

        "allow_web_tools":
            True,

        "dialog_memory":
            "extended"
    },

    # =====================================================
    # 👑 PREMIUM
    # =====================================================

    "premium": {

        "title": "Premium",

        "messages_limit":
            None,

        "images_limit":
            PREMIUM_IMAGES_LIMIT,

        "allow_images":
            True,

        "allow_priority":
            True,

        "allow_visual_boost":
            True,

        "allow_web_tools":
            True,

        "dialog_memory":
            "maximum"
    }
}

# =========================================================
# 🔥 HELPERS
# =========================================================

def normalize_plan(plan):

    if not plan:
        return "free"

    plan = str(plan).lower().strip()

    if plan not in PLAN_CONFIG:
        return "free"

    return plan


def get_plan_config(plan):

    normalized = normalize_plan(
        plan
    )

    return PLAN_CONFIG.get(
        normalized,
        PLAN_CONFIG["free"]
    )


# =========================================================
# 🔥 SAFE RESPONSE
# =========================================================

def build_limit_response(
    title,
    reason
):

    return {

        "allowed": False,

        "reason":

            f"{title}\n\n"

            f"{reason}"
    }


# =========================================================
# 🔥 MAIN CHECK
# =========================================================

async def check(
    user_id,
    action_type
):

    # =====================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:

        return {

            "allowed": True,

            "plan": "admin",

            "admin": True
        }

    # =====================================================
    # 🔥 STORAGE IMPORT
    # =====================================================

    from storage import (

        can_send_message,
        can_generate_image,
        get_user_plan
    )

    # =====================================================
    # 🔥 PLAN
    # =====================================================

    user_plan = normalize_plan(

        get_user_plan(user_id)
    )

    config = get_plan_config(
        user_plan
    )

    # =====================================================
    # 🔥 BASE RESULT
    # =====================================================

    result = {

        "allowed": True,

        "plan": user_plan,

        "config": config,

        "admin": False
    }

    # =====================================================
    # 💬 MESSAGE LIMITS
    # =====================================================

    if action_type == "message":

        limit = config.get(
            "messages_limit"
        )

        # =================================================
        # ♾️ UNLIMITED
        # =====================================================

        if limit is None:

            return result

        # =================================================
        # 🔥 LIMITED
        # =====================================================

        allowed = can_send_message(

            user_id,
            limit=limit
        )

        if not allowed:

            return build_limit_response(

                "⛔ Лимит сообщений достигнут",

                (
                    "Попробуйте позже "
                    "или откройте Lite / Premium"
                )
            )

        return result

    # =====================================================
    # 🖼 IMAGE LIMITS
    # =====================================================

    if action_type == "image":

        if not config.get(
            "allow_images",
            False
        ):

            return build_limit_response(

                "⚠️ Генерация недоступна",

                "Тариф не поддерживает изображения"
            )

        limit = config.get(
            "images_limit"
        )

        # =================================================
        # ♾️ UNLIMITED
        # =====================================================

        if limit is None:

            return result

        # =================================================
        # 🔥 LIMITED
        # =====================================================

        allowed = can_generate_image(

            user_id,
            limit=limit
        )

        if not allowed:

            if user_plan == "free":

                return build_limit_response(

                    "⛔ Лимит генераций достигнут",

                    (
                        "Попробуйте позже "
                        "или откройте Lite / Premium"
                    )
                )

            if user_plan == "lite":

                return build_limit_response(

                    "⚡ Lite лимит изображений достигнут",

                    (
                        "Попробуйте позже "
                        "или перейдите на Premium"
                    )
                )

            if user_plan == "premium":

                return build_limit_response(

                    "👑 Premium лимит изображений достигнут",

                    "Попробуйте позже"
                )

        return result

    # =====================================================
    # 🔥 UNKNOWN ACTION
    # =====================================================

    return {

        "allowed": True,

        "plan": user_plan,

        "config": config
    }


# =========================================================
# 🔥 FEATURE ACCESS
# =========================================================

def has_feature(
    plan,
    feature
):

    config = get_plan_config(
        plan
    )

    return bool(
        config.get(feature)
    )


# =========================================================
# 🔥 ADMIN PANEL EXPORT
# =========================================================

def export_plan_matrix():

    return {

        key: {

            "title":
                value.get("title"),

            "messages_limit":
                value.get(
                    "messages_limit"
                ),

            "images_limit":
                value.get(
                    "images_limit"
                ),

            "allow_images":
                value.get(
                    "allow_images"
                ),

            "allow_priority":
                value.get(
                    "allow_priority"
                ),

            "allow_visual_boost":
                value.get(
                    "allow_visual_boost"
                ),

            "allow_web_tools":
                value.get(
                    "allow_web_tools"
                ),

            "dialog_memory":
                value.get(
                    "dialog_memory"
                )
        }

        for key, value
        in PLAN_CONFIG.items()
    }
