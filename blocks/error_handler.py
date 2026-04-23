import traceback
import time

ADMIN_ID = 2016592532

# ===== 🔥 ХРАНИЛИЩЕ ОШИБОК =====
error_log = []


def log_error(error_text):
    error_log.append(error_text)

    # держим последние 20 ошибок
    if len(error_log) > 20:
        error_log.pop(0)


def get_errors():
    return error_log


# ===== ОБРАБОТЧИК =====
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
🕒 {time.strftime('%H:%M:%S')}
👤 {user_id}
📦 {context}
❌ {str(error)}
"""

    # 🔥 сохраняем ошибку
    log_error(error_text)

    full_error = f"""
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

    full_error = full_error[:4000]

    # ===== ADMIN ALERT =====
    try:
        await bot.send_message(ADMIN_ID, full_error)
    except:
        pass
