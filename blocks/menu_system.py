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

ADMIN_ID = 2016592532


# ===== РОЛЬ =====
def get_user_role(user_id):
    if user_id == ADMIN_ID:
        return "admin"

    plan = get_user_plan(user_id)

    if plan == "premium":
        return "pro"
    elif plan == "lite":
        return "lite"
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
        [InlineKeyboardButton(text="⚡ Перейти на Lite", callback_data="buy_lite")],
        [InlineKeyboardButton(text="👑 Перейти на Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="📋 Что включено", callback_data="info")]
    ])

    return text, keyboard


# ===== LITE =====
def build_lite_menu(user_id):
    days = get_remaining_days(user_id)

    text = (
        "⚡ *LITE*\n\n"
        "🚀 Расширенные лимиты\n"
        "⚡ Быстрее ответы\n\n"
        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Перейти на Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="⚡ Текущий тариф: Lite", callback_data="noop")],
        [InlineKeyboardButton(text="📋 Что включено", callback_data="info")]
    ])

    return text, keyboard


# ===== PREMIUM =====
def build_pro_menu(user_id):
    days = get_remaining_days(user_id)

    text = (
        "👑 *PREMIUM*\n\n"
        "∞ Без ограничений\n"
        "⚡ Быстрые ответы\n"
        "🧠 Приоритет\n\n"
        f"📅 Осталось: {days} дн."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Перейти на Lite", callback_data="confirm_downgrade")],
        [InlineKeyboardButton(text="👑 Текущий тариф: Premium", callback_data="noop")],
        [InlineKeyboardButton(text="📋 Что включено", callback_data="info")]
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
    plan = get_user_plan(user_id)

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

    if plan == "premium":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Перейти на Lite", callback_data="confirm_downgrade")],
            [InlineKeyboardButton(text="👑 Текущий: Premium", callback_data="noop")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
        ])

    elif plan == "lite":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👑 Перейти на Premium", callback_data="buy_premium")],
            [InlineKeyboardButton(text="⚡ Текущий: Lite", callback_data="noop")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
        ])

    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Купить Lite", callback_data="buy_lite")],
            [InlineKeyboardButton(text="👑 Купить Premium", callback_data="buy_premium")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
        ])

    return text, keyboard


# ===== INFO =====
def build_info_menu(user_id):
    text = (
        "🤖 *Возможности Ayprill*\n\n"
        "💬 Общение — ответы и диалог\n"
        "🧠 Интеллект — идеи и объяснения\n"
        "🖼 Генерация — изображения\n"
        "💻 Помощь — код и задачи\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📦 *Тарифы*\n\n"
        "🆓 FREE — базовые лимиты\n"
        "⚡ LITE — больше возможностей\n"
        "👑 PREMIUM — без ограничений\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])

    return text, keyboard


# ===== ОБЩИЙ ВХОД =====
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
