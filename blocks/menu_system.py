print("🔥 MENU SYSTEM LOADED")

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from storage import (
    check_subscription,
    get_limits,
    get_admin_stats,
    get_reset_seconds,
    format_time,
    get_remaining_days,
    get_user_plan
)

# ===== 🔥 CENTRAL TARIFF CONFIG =====
# Все цены и ADMIN_ID теперь берутся из единого config
# Это безопаснее для архитектуры April
from blocks.tariffs_config import (
    ADMIN_ID,
    LITE_PRICE,
    PREMIUM_PRICE
)


# =========================================================
# 👤 USER ROLE
# =========================================================

def get_user_role(user_id):

    # ===== 👑 ADMIN =====
    if user_id == ADMIN_ID:
        return "admin"

    plan = get_user_plan(user_id)

    if plan == "premium":
        return "pro"

    elif plan == "lite":
        return "lite"

    else:
        return "free"


# =========================================================
# 🆓 FREE MENU
# =========================================================

def build_free_menu(user_id):

    limits = get_limits(user_id)

    reset_sec = get_reset_seconds(user_id)
    reset_time = format_time(reset_sec)

    text = (
        "🆓 *FREE*\n\n"

        f"💬 Сообщения:\n"
        f"{limits['messages_used']} / {limits['messages_limit']}\n\n"

        f"🖼 Генерация и изменение:\n"
        f"{limits['images_used']} / {limits['images_limit']}\n\n"

        "📦 Free пакет:\n"
        "• 10 сообщений\n"
        "• 1 генерация\n"
        "• Умная April AI\n\n"

        f"⏳ Обновление:\n"
        f"{reset_time}\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        "✨ Попробуйте больше возможностей"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(
                text=f"⚡ Lite — ${LITE_PRICE}",
                callback_data="buy_lite"
            )
        ],

        [
            InlineKeyboardButton(
                text=f"👑 Premium — ${PREMIUM_PRICE}",
                callback_data="buy_premium"
            )
        ],

        [
            InlineKeyboardButton(
                text="📋 Что включено",
                callback_data="info"
            )
        ]
    ])

    return text, keyboard


# =========================================================
# ⚡ LITE MENU
# =========================================================

def build_lite_menu(user_id):

    days = get_remaining_days(user_id)

    text = (
        "⚡ *LITE*\n\n"

        "♾️ Безлимит сообщений\n"
        "🖼 До 15 генераций\n"
        "⚡ Быстрые ответы\n"
        "🚀 Lite доступ\n\n"

        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(
                text=f"👑 Premium — ${PREMIUM_PRICE}",
                callback_data="buy_premium"
            )
        ],

        [
            InlineKeyboardButton(
                text=f"⚡ Текущий тариф: Lite — ${LITE_PRICE}",
                callback_data="noop"
            )
        ],

        [
            InlineKeyboardButton(
                text="📋 Что включено",
                callback_data="info"
            )
        ]
    ])

    return text, keyboard


# =========================================================
# 👑 PREMIUM MENU
# =========================================================

def build_pro_menu(user_id):

    days = get_remaining_days(user_id)

    text = (
        "👑 *PREMIUM*\n\n"

        "♾️ Безлимит сообщений\n"
        "🖼 До 20 генераций\n"
        "⚡ Priority обработка\n"
        "🛟 Premium Support\n\n"

        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(
                text=f"⚡ Lite — ${LITE_PRICE}",
                callback_data="buy_lite"
            )
        ],

        [
            InlineKeyboardButton(
                text=f"👑 Текущий тариф: Premium — ${PREMIUM_PRICE}",
                callback_data="noop"
            )
        ],

        [
            InlineKeyboardButton(
                text="📋 Что включено",
                callback_data="info"
            )
        ]
    ])

    return text, keyboard


# =========================================================
# ⚙️ ADMIN MENU
# =========================================================

def build_admin_menu(user_id):

    stats = get_admin_stats()

    text = (
        "⚙️ *АДМИН*\n\n"

        f"👥 Пользователи: {stats['users']}\n"
        f"💳 Подписки: {stats['subs']}\n\n"

        f"💰 Доход всего: ${stats['income_total']}\n"
        f"📅 Сегодня: ${stats['income_today']}\n\n"

        "⚠️ Ошибки: 0\n\n"

        "🟢 System Stable\n"
        "🟢 Limits Active\n"
        "🟢 PayPal Ready\n"
        "🟡 Monitoring Enabled"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

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
    ])

    return text, keyboard


# =========================================================
# 📋 TARIFFS MENU
# =========================================================

def build_tariffs_menu(user_id):

    plan = get_user_plan(user_id)

    text = (
        "📋 *ТАРИФЫ*\n\n"

        "🆓 FREE\n"
        "✔️ 10 сообщений в день\n"
        "✔️ 1 генерация / изменение\n"
        "✔️ Умная April AI\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"⚡ LITE — ${LITE_PRICE} (5 дней)\n"
        "✔️ Безлимит сообщений\n"
        "✔️ До 15 генераций\n"
        "✔️ Быстрые ответы\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"👑 PREMIUM — ${PREMIUM_PRICE} (30 дней)\n"
        "✔️ Безлимит сообщений\n"
        "✔️ До 20 генераций\n"
        "✔️ Priority обработка\n"
        "✔️ Premium Support\n"
    )

    # ===== 👑 PREMIUM =====
    if plan == "premium":

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=f"⚡ Lite — ${LITE_PRICE}",
                    callback_data="buy_lite"
                )
            ],

            [
                InlineKeyboardButton(
                    text=f"👑 Текущий: Premium — ${PREMIUM_PRICE}",
                    callback_data="noop"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu"
                )
            ]
        ])

    # ===== ⚡ LITE =====
    elif plan == "lite":

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=f"👑 Premium — ${PREMIUM_PRICE}",
                    callback_data="buy_premium"
                )
            ],

            [
                InlineKeyboardButton(
                    text=f"⚡ Текущий: Lite — ${LITE_PRICE}",
                    callback_data="noop"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu"
                )
            ]
        ])

    # ===== 🆓 FREE =====
    else:

        keyboard = InlineKeyboardMarkup(inline_keyboard=[

            [
                InlineKeyboardButton(
                    text=f"⚡ Купить Lite — ${LITE_PRICE}",
                    callback_data="buy_lite"
                )
            ],

            [
                InlineKeyboardButton(
                    text=f"👑 Купить Premium — ${PREMIUM_PRICE}",
                    callback_data="buy_premium"
                )
            ],

            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu"
                )
            ]
        ])

    return text, keyboard


# =========================================================
# ℹ️ INFO MENU
# =========================================================

def build_info_menu(user_id):

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

        f"⚡ LITE — ${LITE_PRICE} (5 дней)\n"
        "✔️ Безлимит сообщений\n"
        "✔️ До 15 генераций\n"
        "✔️ Быстрые ответы\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        f"👑 PREMIUM — ${PREMIUM_PRICE} (30 дней)\n"
        "✔️ Безлимит сообщений\n"
        "✔️ До 20 генераций\n"
        "✔️ Premium Support\n"
        "✔️ Priority обработка\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="menu"
            )
        ]
    ])

    return text, keyboard


# =========================================================
# 🚪 MAIN MENU ENTRY
# =========================================================

def get_menu(user_id):

    role = get_user_role(user_id)

    if role == "free":
        return build_free_menu(user_id)

    elif role == "lite":
        return build_lite_menu(user_id)

    elif role == "pro":
        return build_pro_menu(user_id)

    elif role == "admin":
        return build_admin_menu(user_id)
