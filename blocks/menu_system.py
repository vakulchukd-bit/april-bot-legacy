from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import (
    check_subscription,
    get_limits,
    get_admin_stats,
    get_reset_seconds,
    format_time
)

ADMIN_ID = 2016592532


# ===== РОЛЬ =====
def get_user_role(user_id):
    if user_id == ADMIN_ID:
        return "admin"
    elif check_subscription(user_id):
        return "pro"
    else:
        return "free"


# ===== FREE =====
def build_free_menu(user_id):
    limits = get_limits(user_id)

    reset_sec = get_reset_seconds(user_id)
    reset_time = format_time(reset_sec)

    text = (
        "🆓 *FREE*\n\n"
        "📊 *Текущие лимиты:*\n"
        f"💬 Сообщения: {limits['messages_used']} / {limits['messages_limit']}\n"
        f"🎨 Генерация: {limits['images_used']} / {limits['images_limit']}\n\n"
        f"⏳ Сброс через: *{reset_time}*\n\n"
        "🚀 *Перейди на PRO для полного доступа*"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Перейти на PRO", callback_data="buy_yes")],
        [InlineKeyboardButton(text="📋 Тарифы", callback_data="tariffs")]
    ])

    return text, keyboard


# ===== PRO =====
def build_pro_menu(user_id):
    text = (
        "👑 *PRO*\n\n"
        "📊 *Статус:*\n"
        "∞ Без ограничений\n"
        "⚡ Быстрые ответы\n"
        "🧠 Приоритетная обработка\n\n"
        "📅 Подписка активна"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="buy_yes")],
        [InlineKeyboardButton(text="📋 Тарифы", callback_data="tariffs")]
    ])

    return text, keyboard


# ===== ТАРИФЫ =====
def build_tariffs_menu(user_id):
    text = (
        "📋 *ТАРИФЫ*\n\n"
        "🆓 FREE\n"
        "— 15 сообщений в день\n"
        "— 1 изображение\n\n"
        "👑 PRO — 150 грн / 30 дней\n"
        "— Без ограничений\n"
        "— Быстро\n"
        "— Приоритет\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Купить PRO", callback_data="buy_yes")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])

    return text, keyboard


# ===== ADMIN =====
def build_admin_menu(user_id):
    stats = get_admin_stats()

    text = (
        "⚙️ *АДМИН-ПАНЕЛЬ*\n\n"
        f"👥 Пользователей: {stats['users']}\n"
        f"💳 Подписок: {stats['subs']}\n"
        f"💰 Доход всего: {stats['income_total']} грн\n"
        f"💰 Сегодня: {stats['income_today']} грн\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="💳 Подписки", callback_data="admin_subs")],
        [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📢 Рассылки", callback_data="admin_broadcast")]
    ])

    return text, keyboard


# ===== ОБЩИЙ ВХОД =====
def get_menu(user_id):
    role = get_user_role(user_id)

    if role == "free":
        return build_free_menu(user_id)

    elif role == "pro":
        return build_pro_menu(user_id)

    elif role == "admin":
        return build_admin_menu(user_id)
