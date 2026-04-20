import traceback
import time

ADMIN_ID = 2016592532


async def handle_error(bot, user_message, error, context=""):
    """
    Универсальный обработчик ошибок:
    - Пользователь получает безопасное сообщение
    - Админ получает полный лог
    """

    # ===== USER MESSAGE =====
    try:
        await user_message.answer(
            "⚠️ Сервис временно недоступен. Мы уже работаем над этим."
        )
    except:
        pass

    # ===== ERROR DATA =====
    user_id = getattr(user_message.from_user, "id", "unknown")
    text = getattr(user_message, "text", None)

    error_text = f"""
❌ ОШИБКА

🕒 Время: {time.strftime('%Y-%m-%d %H:%M:%S')}

👤 User ID: {user_id}
📩 Сообщение: {text}

📦 Контекст: {context}

🧠 Ошибка:
{str(error)}

📄 Traceback:
{traceback.format_exc()}
"""

    error_text = error_text[:4000]

    # ===== ADMIN ALERT =====
    try:
        await bot.send_message(ADMIN_ID, error_text)
    except:
        pass
