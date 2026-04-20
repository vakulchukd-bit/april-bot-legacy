from storage import check_subscription
from blocks.analytics_storage import add_user, add_event, get_stats

# 🔐 твой ID
ADMIN_ID = 2016592532


# ===== РЕГИСТРАЦИЯ =====
def register_user(user_id):
    add_user(user_id)


# ===== СОБЫТИЯ =====
def log_event(user_id, event_type):
    add_event(user_id, event_type)


# ===== ПОДПИСКИ (ПОКА КОСТЫЛЬ, НО СТАБИЛЬНО) =====
def get_active_subscriptions():
    users_count, _, _ = get_stats()
    active = 0

    for user_id in range(1, users_count + 1):
        try:
            if check_subscription(user_id):
                active += 1
        except:
            pass

    return active


# ===== ПАНЕЛЬ =====
def get_admin_panel():
    users_count, messages, images = get_stats()
    active_subs = get_active_subscriptions()

    text = f"""
📊 АДМИН ПАНЕЛЬ

👥 Пользователи: {users_count}
💳 Активные подписки: {active_subs}

💬 Сообщения: {messages}
🖼 Картинки: {images}

🧠 Статус: работает
"""

    return text
