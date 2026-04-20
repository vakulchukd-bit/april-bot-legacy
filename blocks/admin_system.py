from storage import check_subscription

# 🔐 твой ID
ADMIN_ID = 2016592532


# ===== ЛЕНИВЫЕ ИМПОРТЫ =====
def get_storage():
    from blocks.analytics_storage import add_user, add_event, get_stats, load_data
    return add_user, add_event, get_stats, load_data


def get_cost():
    from blocks.cost_system import calculate_cost
    return calculate_cost


# ===== РЕГИСТРАЦИЯ =====
def register_user(user_id):
    add_user, _, _, _ = get_storage()
    add_user(user_id)


# ===== СОБЫТИЯ =====
def log_event(user_id, event_type):
    _, add_event, _, _ = get_storage()
    add_event(user_id, event_type)


# ===== ПОДПИСКИ =====
def get_active_subscriptions():
    _, _, _, load_data = get_storage()
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


# ===== ПАНЕЛЬ =====
def get_admin_panel():
    _, _, get_stats, _ = get_storage()
    calculate_cost = get_cost()

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
- Текст: {cost_data['text']}
- Картинки: {cost_data['images']}
- Итого: ${cost_data['cost']}

🧠 Статус: работает
"""

    return text
