from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import (
    check_subscription,
    get_limits,
    get_admin_stats,
    get_reset_seconds,
    format_time,
    get_remaining_days
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
        f"💬 Сообщения: {limits['messages_used']} / {limits['messages_limit']}\n"
        f"🎨 Генерация: {limits['images_used']} / {limits['images_limit']}\n\n"
        f"⏳ Сброс через: *{reset_time}*\n\n"
        "🚀 Открой полный доступ"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Lite", callback_data="buy_lite")],
        [InlineKeyboardButton(text="👑 Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="📋 Что даст подписка", callback_data="tariffs")]
    ])

    return text, keyboard


# ===== PRO =====
def build_pro_menu(user_id):
    days = get_remaining_days(user_id)

    text = (
        "👑 *PRO*\n\n"
        "∞ Без ограничений\n"
        "⚡ Быстрые ответы\n"
        "🧠 Приоритет\n\n"
        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сменить тариф", callback_data="tariffs")],
        [InlineKeyboardButton(text="📋 Что включено", callback_data="tariffs")]
    ])

    return text, keyboard


# ===== ADMIN =====
def build_admin_menu(user_id):
    stats = get_admin_stats()

    text = (
        "⚙️ *АДМИН*\n\n"
        f"👥 Пользователи: {stats['users']}\n"
        f"💳 Подписки: {stats['subs']}\n"
        f"💰 Доход всего: {stats['income_total']} грн\n"
        f"📅 Сегодня: {stats['income_today']} грн\n"
        f"⚠️ Ошибки: 0\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Анализ", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💳 Оплаты", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
    ])

    return text, keyboard


# ===== ТАРИФЫ =====
def build_tariffs_menu(user_id):
    is_pro = check_subscription(user_id)

    text = (
        "📋 *ТАРИФЫ*\n\n"
        "🆓 FREE\n"
        "— 15 сообщений\n"
        "— 1 изображение\n\n"
        "⚡ LITE\n"
        "— больше лимитов\n"
        "— быстрее\n\n"
        "👑 PREMIUM\n"
        "— без ограничений\n"
        "— приоритет\n"
    )

    # 🔥 ЕСЛИ УЖЕ PRO
    if is_pro:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 У тебя уже PREMIUM", callback_data="noop")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Купить Lite", callback_data="buy_lite")],
            [InlineKeyboardButton(text="👑 Купить Premium", callback_data="buy_premium")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
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
