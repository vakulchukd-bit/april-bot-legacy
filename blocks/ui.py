from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =====================================================
# 🧠 APRIL KEYBOARD MODULE
# =====================================================

"""
APRIL KEYBOARD MODULE

ROLE:
- keyboard transport layer
- callback registry
- reaction controls
- tariff controls
- payment controls

WEB STABILIZATION MODE:
- telegram compatible
- web ready
- callback safe
- future reaction system ready
- future payment system ready

IMPORTANT:

Сейчас модуль НЕ управляет:

- web ui
- renderer
- cognition
- routing
- orchestration

Модуль только предоставляет
клавиатуры и callback точки входа.
"""

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = "APRIL_KEYBOARD_MODULE"

APRIL_VERSION = "WEB_STABILIZED"

# =====================================================
# 🔥 MACHINE FLAGS
# =====================================================

KEYBOARD_FLAGS = {

    "web_ready": True,

    "botru_compatible": True,

    "callback_safe": True,

    "future_web_reactions": True,

    "future_web_payments": True,

    "continuity_safe": True,

    "renderer_safe": True,

    "transport_agnostic": True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "KEYBOARD MODULE:",
            msg
        )

        PATCH_LOG.append(
            str(msg)
        )

    except:
        pass


# =====================================================
# 🔥 MAIN KEYBOARD
# =====================================================

def main_keyboard(msg_id):

    safe_patch_log(
        f"MAIN_KEYBOARD:{msg_id}"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍",
                    callback_data=f"like_{msg_id}"
                ),

                InlineKeyboardButton(
                    text="👎",
                    callback_data=f"dislike_{msg_id}"
                ),

                InlineKeyboardButton(
                    text="⋯",
                    callback_data="menu"
                )
            ]
        ]
    )


# =====================================================
# 🔥 LEGACY BUY KEYBOARD
# =====================================================

"""
Оставлено для совместимости.

Не используется напрямую.

Не удалять без проверки:
- callback handlers
- legacy flows
- botru compatibility
"""

def buy_keyboard():

    safe_patch_log(
        "BUY_KEYBOARD"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да",
                    callback_data="noop"
                ),

                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data="noop"
                )
            ]
        ]
    )


# =====================================================
# 🔥 TARIFF KEYBOARD
# =====================================================

def тариф_keyboard():

    safe_patch_log(
        "TARIFF_KEYBOARD"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Lite — $6",
                    callback_data="buy_lite"
                )
            ],

            [
                InlineKeyboardButton(
                    text="👑 Premium — $25",
                    callback_data="buy_premium"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu"
                )
            ]
        ]
    )


# =====================================================
# 🔥 PAYMENTS KEYBOARD
# =====================================================

def payments_keyboard():

    safe_patch_log(
        "PAYMENTS_KEYBOARD"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 OpenAI",
                    url="https://platform.openai.com/account/billing"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🚂 Railway",
                    url="https://railway.app"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu"
                )
            ]
        ]
    )


# =====================================================
# 🔥 WEB REACTION PLACEHOLDERS
# =====================================================

"""
Зарезервировано под будущий April Web.

Будущие системы:

- like tracking
- dislike tracking
- feedback analytics
- reaction memory
- recommendation tuning

Пока не используется.
"""

WEB_REACTION_RESERVED = {

    "enabled": False,

    "future_like_support": True,

    "future_dislike_support": True,

    "future_feedback_support": True
}


# =====================================================
# 🔥 WEB PAYMENT PLACEHOLDERS
# =====================================================

WEB_PAYMENT_RESERVED = {

    "enabled": False,

    "future_checkout_support": True,

    "future_web_billing": True,

    "future_subscription_manager": True
}


# =====================================================
# 🔥 EXPORT
# =====================================================

KEYBOARD_MODULE_EXPORT = {

    "id":
        APRIL_FILE_ID,

    "version":
        APRIL_VERSION,

    "web_ready":
        True,

    "future_reactions":
        True,

    "future_payments":
        True,

    "continuity_safe":
        True,

    "botru_compatible":
        True
}
