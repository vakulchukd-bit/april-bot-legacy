from storage import check_subscription
from blocks.cost_system import calculate_cost

# 🔐 твой ID
ADMIN_ID = 2016592532


# ===== РЕГИСТРАЦИЯ =====
def register_user(user_id):
    try:
        from blocks.analytics_storage import add_user
        add_user(user_id)
    except Exception as e:
        print("🔥 REGISTER USER ERROR:", e)


# ===== СОБЫТИЯ =====
def log_event(user_id, event_type):
    try:
        from blocks.analytics_storage import add_event
        add_event(user_id, event_type)
    except Exception as e:
        print("🔥 LOG EVENT ERROR:", e)


# ===== ПОДПИСКИ =====
def get_active_subscriptions():
    try:
        from blocks.analytics_storage import load_data

        data = load_data()
        users = data.get("users", [])

        active = 0

        for user_id in users:
            try:
                if check_subscription(user_id):
                    active += 1
            except:
                pass

        return active

    except Exception as e:
        print("🔥 SUBSCRIPTIONS ERROR:", e)
        return 0


# ===== ПАНЕЛЬ =====
def get_admin_panel():
    try:
        from blocks.analytics_storage import get_stats

        users_count, messages, images = get_stats()
        active_subs = get_active_subscriptions()

        cost_data = calculate_cost()

        text = f"""
📊 АДМИН ПАНЕЛЬ

👥 Пользователи: {users_count}
💳 Активные подписки: {active_subs}

💬 Сообщения: {messages}
🖼 Картинки: {images}

💰 Расход:
- Текст: {cost_data.get('text', 0)}
- Картинки: {cost_data.get('images', 0)}
- Итого: ${cost_data.get('cost', 0)}

🧠 Статус: работает
"""
        return text

    except Exception as e:
        print("🔥 ADMIN PANEL ERROR:", e)
        return "⚠️ Админ-панель временно недоступна"
