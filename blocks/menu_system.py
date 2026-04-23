from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from storage import check_subscription, can_send_message, can_generate_image

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
    # ⚠️ тут ты можешь позже подключить реальные лимиты
    messages_left = "?"
    images_left = "?"

    text = (
        "🆓 Статус: FREE\n\n"
        f"💬 Сообщения: {messages_left}\n"
        f"🎨 Генерация: {images_left}\n\n"
        "⏳ Лимиты обновятся автоматически\n\n"
        "🚀 Перейди на PRO для полного доступа"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Перейти на PRO", callback_data="go_pro")]
    ])

    return text, keyboard


# ===== PRO =====
def build_pro_menu(user_id):
    text = (
        "👑 Статус: PRO\n\n"
        "∞ Без ограничений\n"
        "⚡ Быстрые ответы\n"
        "🧠 Приоритетная обработка\n\n"
        "Спасибо, что ты с Aprill ❤️"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="renew_pro")],
        [InlineKeyboardButton(text="📋 Тарифы", callback_data="tariffs")]
    ])

    return text, keyboard


# ===== ADMIN =====
def build_admin_menu(user_id):
    text = (
        "⚙️ Админ-панель\n\n"
        "Добро пожаловать в управление системой"
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
