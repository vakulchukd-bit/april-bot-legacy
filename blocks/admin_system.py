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
    try:
        add_user, _, _, _ = get_storage()
        add_user(user_id)
    except Exception as e:
        print("🔥 REGISTER USER ERROR:", e)


# ===== СОБЫТИЯ =====
def log_event(user_id, event_type):
    try:
        _, add_event, _, _ = get_storage()
        add_event(user_id, event_type)
    except Exception as e:
        print("🔥 LOG EVENT ERROR:", e)


# ===== ПОДПИСКИ =====
def get_active_subscriptions():
    try:
        _, _, _, load_data = get_storage()
        data = load_data()

        users = data.get("users", [])
        if not isinstance(users, list):
            print("❌ USERS NOT LIST:", users)
            return 0

        active = 0

        for user_id in users:
            try:
                if check_subscription(user_id):
                    active += 1
            except Exception as e:
                print(f"⚠️ SUB CHECK ERROR ({user_id}):", e)

        return active

    except Exception as e:
        print("🔥 GET ACTIVE SUBS ERROR:", e)
        return 0


# ===== ПАНЕЛЬ =====
def get_admin_panel():
    try:
        print("🚀 ADMIN PANEL START")

        _, _, get_stats, _ = get_storage()
        calculate_cost = get_cost()

        # --- статистика ---
        stats = get_stats()
        print("📊 RAW STATS:", stats)

        if not stats or len(stats) != 3:
            raise Exception(f"Invalid stats format: {stats}")

        users_count, messages, images = stats

        # --- подписки ---
        active_subs = get_active_subscriptions()

        # --- стоимость ---
        cost_data = calculate_cost()
        print("💰 COST DATA:", cost_data)

        if not isinstance(cost_data, dict):
            raise Exception(f"Invalid cost_data: {cost_data}")

        text_cost = cost_data.get("text", 0)
        image_cost = cost_data.get("images", 0)
        total_cost = cost_data.get("cost", 0)

        text = f"""
📊 АДМИН ПАНЕЛЬ

👥 Пользователи: {users_count}
💳 Активные подписки: {active_subs}

💬 Сообщения: {messages}
🖼 Картинки: {images}

💰 Расход:
- Текст: {text_cost}
- Картинки: {image_cost}
- Итого: ${total_cost}

🧠 Статус: работает
"""
        return text

    except Exception as e:
        print("🔥 ADMIN PANEL ERROR:", e)
        return "⚠️ Админ-панель временно недоступна"
