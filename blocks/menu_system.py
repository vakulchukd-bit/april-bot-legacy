print("🔥 MENU SYSTEM LOADED")

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

import time

from storage import (

    check_subscription,
    get_limits,
    get_admin_stats,
    get_reset_seconds,
    format_time,
    get_remaining_days,
    get_user_plan
)

# =====================================================
# 🧠 APRIL MENU SYSTEM
# =====================================================

"""
APRIL_FILE_ID:
APRIL_MENU_SYSTEM

ROLE:
UI_STATE_DELIVERY_LAYER

INPUT:
USER_ID
SUBSCRIPTION_STATE
LIMIT_STATE
ADMIN_STATE
TARIFF_CONFIG
SESSION_CONTEXT

OUTPUT:
MENU_TEXT
MENU_KEYBOARD
UI_DELIVERY_PAYLOAD
ROLE_BASED_MENU_STATE

=====================================================

APRIL MENU SYSTEM

Этот слой теперь:

- НЕ telegram-only menu;
- НЕ hard button router;
- НЕ UI authority;
- НЕ monetization controller;
- НЕ callback dispatcher.

Теперь это:

- UI state delivery layer;
- subscription visualization bridge;
- role-aware presentation layer;
- Web April compatible menu provider;
- lightweight interface orchestrator.

=====================================================

APRIL PRINCIPLES:

1. UI != orchestration
2. transport != authority
3. menu != router
4. renderer-safe delivery
5. role-aware presentation
6. continuity-safe UI state
7. transport-independent architecture
"""

# =====================================================
# 🔥 CENTRAL TARIFF CONFIG
# =====================================================

# Все цены и ADMIN_ID теперь берутся
# из единого config

from blocks.tariffs_config import (

    ADMIN_ID,
    LITE_PRICE,
    PREMIUM_PRICE
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "executor_or_ui_layer",

    "type":
        "menu_input",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "ui_delivery_provider",

    "type":
        "menu_output",

    "isolated":
        True
}

# =====================================================
# 🔥 PATCH LOGGING
# =====================================================

PATCH_LOG = []

MAX_PATCH_LOGS = 100


def safe_patch_log(message):

    try:

        print(
            "MENU PATCH:",
            message
        )

        PATCH_LOG.append({

            "timestamp":
                time.time(),

            "message":
                message,

            "file_id":
                "APRIL_MENU_SYSTEM",

            "machine_only":
                True
        })

        if len(PATCH_LOG) > MAX_PATCH_LOGS:

            PATCH_LOG.pop(0)

    except Exception:
        pass

# =====================================================
# 🔥 MENU PAYLOAD
# =====================================================

def build_menu_payload(

    role,
    text,
    keyboard,

    continuity_safe=True
):

    return {

        "role":
            role,

        "text":
            text,

        "keyboard":
            keyboard,

        "continuity_safe":
            continuity_safe,

        "renderer_safe":
            True,

        "transport_independent":
            True,

        "ui_delivery":
            True,

        "machine_only":
            True,

        "timestamp":
            time.time()
    }

# =====================================================
# 👤 USER ROLE
# =====================================================

def get_user_role(user_id):

    safe_patch_log(
        f"ROLE REQUEST: {user_id}"
    )

    # =================================================
    # 👑 ADMIN
    # =====================================================

    if user_id == ADMIN_ID:

        return "admin"

    plan = get_user_plan(
        user_id
    )

    if plan == "premium":

        return "pro"

    elif plan == "lite":

        return "lite"

    else:

        return "free"

# =====================================================
# 🆓 FREE MENU
# =====================================================

def build_free_menu(user_id):

    safe_patch_log(
        "BUILD FREE MENU"
    )

    limits = get_limits(
        user_id
    )

    reset_sec = get_reset_seconds(
        user_id
    )

    reset_time = format_time(
        reset_sec
    )

    text = (

        "🆓 *FREE*\n\n"

        f"💬 Сообщения:\n"
        f"{limits['messages_used']} / "
        f"{limits['messages_limit']}\n\n"

        f"🖼 Генерация и изменение:\n"
        f"{limits['images_used']} / "
        f"{limits['images_limit']}\n\n"

        "📦 Free пакет:\n"
        "• 10 сообщений\n"
        "• 1 генерация\n"
        "• Умная April AI\n\n"

        f"⏳ Обновление:\n"
        f"{reset_time}\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        "✨ Попробуйте больше возможностей"
    )

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=(
                        f"⚡ Lite — "
                        f"${LITE_PRICE}"
                    ),
                    callback_data="buy_lite"
                )
            ],

            [
                InlineKeyboardButton(
                    text=(
                        f"👑 Premium — "
                        f"${PREMIUM_PRICE}"
                    ),
                    callback_data="buy_premium"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📋 Что включено",
                    callback_data="info"
                )
            ]
        ]
    )

    return build_menu_payload(

        role="free",

        text=text,

        keyboard=keyboard
    )

# =====================================================
# ⚡ LITE MENU
# =====================================================

def build_lite_menu(user_id):

    safe_patch_log(
        "BUILD LITE MENU"
    )

    days = get_remaining_days(
        user_id
    )

    text = (

        "⚡ *LITE*\n\n"

        "♾️ Безлимит сообщений\n"
        "🖼 До 15 генераций\n"
        "⚡ Быстрые ответы\n"
        "🚀 Lite доступ\n\n"

        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=(
                        f"👑 Premium — "
                        f"${PREMIUM_PRICE}"
                    ),
                    callback_data="buy_premium"
                )
            ],

            [
                InlineKeyboardButton(
                    text=(
                        "⚡ Текущий тариф: "
                        f"Lite — ${LITE_PRICE}"
                    ),
                    callback_data="noop"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📋 Что включено",
                    callback_data="info"
                )
            ]
        ]
    )

    return build_menu_payload(

        role="lite",

        text=text,

        keyboard=keyboard
    )

# =====================================================
# 👑 PREMIUM MENU
# =====================================================

def build_pro_menu(user_id):

    safe_patch_log(
        "BUILD PREMIUM MENU"
    )

    days = get_remaining_days(
        user_id
    )

    text = (

        "👑 *PREMIUM*\n\n"

        "♾️ Безлимит сообщений\n"
        "🖼 До 20 генераций\n"
        "⚡ Priority обработка\n"
        "🛟 Premium Support\n\n"

        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=(
                        f"⚡ Lite — "
                        f"${LITE_PRICE}"
                    ),
                    callback_data="buy_lite"
                )
            ],

            [
                InlineKeyboardButton(
                    text=(
                        "👑 Текущий тариф: "
                        f"Premium — "
                        f"${PREMIUM_PRICE}"
                    ),
                    callback_data="noop"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📋 Что включено",
                    callback_data="info"
                )
            ]
        ]
    )

    return build_menu_payload(

        role="pro",

        text=text,

        keyboard=keyboard
    )

# =====================================================
# ⚙️ ADMIN MENU
# =====================================================

def build_admin_menu(user_id):

    safe_patch_log(
        "BUILD ADMIN MENU"
    )

    stats = get_admin_stats()

    text = (

        "⚙️ *АДМИН*\n\n"

        f"👥 Пользователи: "
        f"{stats['users']}\n"

        f"💳 Подписки: "
        f"{stats['subs']}\n\n"

        f"💰 Доход всего: "
        f"${stats['income_total']}\n"

        f"📅 Сегодня: "
        f"${stats['income_today']}\n\n"

        "⚠️ Ошибки: 0\n\n"

        "🟢 System Stable\n"
        "🟢 Limits Active\n"
        "🟢 PayPal Ready\n"
        "🟡 Monitoring Enabled"
    )

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📊 Аналитика",
                    callback_data="admin_stats"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💳 Оплаты",
                    callback_data="admin_payments"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📢 Рассылка",
                    callback_data="admin_broadcast"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⚙️ Система",
                    callback_data="admin_system"
                )
            ]
        ]
    )

    return build_menu_payload(

        role="admin",

        text=text,

        keyboard=keyboard
    )

# =====================================================
# 📋 TARIFFS MENU
# =====================================================

def build_tariffs_menu(user_id):

    safe_patch_log(
        "BUILD TARIFFS MENU"
    )

    plan = get_user_plan(
        user_id
    )

    text = (

        "📋 *ТАРИФЫ*\n\n"

        "🆓 FREE\n"
        "✔️ 10 сообщений в день\n"
        "✔️ 1 генерация / изменение\n"
        "✔️ Умная April AI\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"⚡ LITE — "
        f"${LITE_PRICE} (5 дней)\n"

        "✔️ Безлимит сообщений\n"
        "✔️ До 15 генераций\n"
        "✔️ Быстрые ответы\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"👑 PREMIUM — "
        f"${PREMIUM_PRICE} (30 дней)\n"

        "✔️ Безлимит сообщений\n"
        "✔️ До 20 генераций\n"
        "✔️ Priority обработка\n"
        "✔️ Premium Support\n"
    )

    # =================================================
    # 👑 PREMIUM
    # =====================================================

    if plan == "premium":

        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text=(
                            f"⚡ Lite — "
                            f"${LITE_PRICE}"
                        ),
                        callback_data="buy_lite"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text=(
                            "👑 Текущий: "
                            f"Premium — "
                            f"${PREMIUM_PRICE}"
                        ),
                        callback_data="noop"
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

    # =================================================
    # ⚡ LITE
    # =====================================================

    elif plan == "lite":

        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text=(
                            f"👑 Premium — "
                            f"${PREMIUM_PRICE}"
                        ),
                        callback_data="buy_premium"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text=(
                            "⚡ Текущий: "
                            f"Lite — "
                            f"${LITE_PRICE}"
                        ),
                        callback_data="noop"
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

    # =================================================
    # 🆓 FREE
    # =====================================================

    else:

        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [
                    InlineKeyboardButton(
                        text=(
                            "⚡ Купить Lite — "
                            f"${LITE_PRICE}"
                        ),
                        callback_data="buy_lite"
                    )
                ],

                [
                    InlineKeyboardButton(
                        text=(
                            "👑 Купить Premium — "
                            f"${PREMIUM_PRICE}"
                        ),
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

    return build_menu_payload(

        role=plan,

        text=text,

        keyboard=keyboard
    )

# =====================================================
# ℹ️ INFO MENU
# =====================================================

def build_info_menu(user_id):

    safe_patch_log(
        "BUILD INFO MENU"
    )

    text = (

        "🤖 *Возможности Ayprill*\n\n"

        "💬 Общение и диалог\n"
        "🧠 Идеи и объяснения\n"
        "🖼 Генерация изображений\n"
        "💻 Код и помощь\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        "📋 *Тарифы*\n\n"

        "🆓 FREE\n"
        "✔️ 10 сообщений\n"
        "✔️ 1 генерация / изменение\n"
        "✔️ Умная April AI\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"⚡ LITE — "
        f"${LITE_PRICE} (5 дней)\n"

        "✔️ Безлимит сообщений\n"
        "✔️ До 15 генераций\n"
        "✔️ Быстрые ответы\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"👑 PREMIUM — "
        f"${PREMIUM_PRICE} (30 дней)\n"

        "✔️ Безлимит сообщений\n"
        "✔️ До 20 генераций\n"
        "✔️ Premium Support\n"
        "✔️ Priority обработка\n"
    )

    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu"
                )
            ]
        ]
    )

    return build_menu_payload(

        role="info",

        text=text,

        keyboard=keyboard
    )

# =====================================================
# 🚪 MAIN MENU ENTRY
# =====================================================

def get_menu(user_id):

    safe_patch_log(
        f"MENU ENTRY: {user_id}"
    )

    role = get_user_role(
        user_id
    )

    if role == "free":

        return build_free_menu(
            user_id
        )

    elif role == "lite":

        return build_lite_menu(
            user_id
        )

    elif role == "pro":

        return build_pro_menu(
            user_id
        )

    elif role == "admin":

        return build_admin_menu(
            user_id
        )

    # =================================================
    # 🔥 SAFE FALLBACK
    # =====================================================

    safe_patch_log(
        "UNKNOWN ROLE FALLBACK"
    )

    return build_free_menu(
        user_id
    )
