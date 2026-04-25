from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ===== ОСНОВНАЯ КЛАВИАТУРА (под ответом) =====
def main_keyboard(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"like_{msg_id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_{msg_id}"),
            InlineKeyboardButton(text="⋯", callback_data="menu")
        ]
    ])


# ===== ❌ СТАРАЯ (НЕ ТРОГАЕМ) =====
def buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="noop"),
            InlineKeyboardButton(text="❌ Нет", callback_data="noop")
        ]
    ])


# ===== 🔥 НОВАЯ КНОПКА ДЛЯ ПРОДАЖИ =====
def upgrade_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Попробовать Lite", callback_data="buy_lite")],
        [InlineKeyboardButton(text="👑 Перейти в Premium", callback_data="buy_premium")]
    ])


# ===== 🔥 ВЫБОР ТАРИФА =====
def тариф_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Lite (пробовать и докручивать)", callback_data="buy_lite")],
        [InlineKeyboardButton(text="👑 Premium (без ограничений)", callback_data="buy_premium")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])


# ===== 🔥 КРАСИВЫЙ ТЕКСТ ЛИМИТА =====
def limit_text():
    return (
        "Ты почти сделал это 👀\n\n"
        "Ещё немного — и результат был бы идеальным.\n\n"
        "Хочешь продолжить без ограничений?"
    )


# ===== 🔥 ОПЛАТЫ (АДМИН) =====
def payments_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 OpenAI", url="https://platform.openai.com/account/billing")],
        [InlineKeyboardButton(text="🚂 Railway", url="https://railway.app")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])
