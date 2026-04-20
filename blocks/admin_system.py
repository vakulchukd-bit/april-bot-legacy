from storage import check_subscription
from blocks.state_manager import get_state

# 🔐 твой ID
ADMIN_ID = 2016592532


# ===== ВРЕМЯ =====
import time

def now():
    return int(time.time())


# ===== ЗАГЛУШКА ХРАНИЛИЩА =====
# (пока простая версия, потом заменим на базу)

users = set()
events = []


def register_user(user_id):
    users.add(user_id)


def log_event(user_id, event_type):
    events.append({
        "user_id": user_id,
        "type": event_type,
        "time": now()
    })


# ===== СТАТИСТИКА =====
def get_stats():
    total_users = len(users)
    total_messages = 0
    total_images = 0

    for e in events:
        if e["type"] == "text":
            total_messages += 1
        elif e["type"] == "image":
            total_images += 1

    return total_users, total_messages, total_images


# ===== ПОДПИСКИ =====
def get_active_subscriptions():
    count = 0
    for user_id in users:
        try:
            if check_subscription(user_id):
                count += 1
        except:
            pass
    return count


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
