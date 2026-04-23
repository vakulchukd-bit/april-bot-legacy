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


# ===== ПОДТВЕРЖДЕНИЕ ПОКУПКИ =====
def buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="buy_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="buy_no")
        ]
    ])


# ===== 🔥 ВЫБОР ТАРИФА =====
def тариф_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Lite", callback_data="buy_lite")],
        [InlineKeyboardButton(text="👑 Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])


# ===== 🔥 ОПЛАТЫ (АДМИН) =====
def payments_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 OpenAI", url="https://platform.openai.com/account/billing")],
        [InlineKeyboardButton(text="🚂 Railway", url="https://railway.app")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])
