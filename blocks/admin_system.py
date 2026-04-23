from storage import check_subscription

ADMIN_ID = 2016592532


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
        active = 0

        for user_id in users:
            try:
                if check_subscription(user_id):
                    active += 1
            except:
                pass

        return active

    except Exception as e:
        print("🔥 SUB ERROR:", e)
        return 0


# ===== ОШИБКИ (заглушка пока) =====
def get_errors_count():
    # пока просто 0 (потом подключим лог ошибок)
    return 0


# ===== ПАНЕЛЬ =====
def get_admin_panel():
    print("🚀 ADMIN PANEL START")

    # --- пользователи ---
    try:
        _, _, get_stats, _ = get_storage()
        stats = get_stats()
        users_count, messages, images = stats if stats and len(stats) == 3 else (0, 0, 0)
    except Exception as e:
        print("🔥 STATS ERROR:", e)
        users_count = 0

    # --- подписки ---
    try:
        active_subs = get_active_subscriptions()
    except:
        active_subs = 0

    # --- доход (через cost пока) ---
    try:
        calculate_cost = get_cost()
        cost_data = calculate_cost() or {}
    except Exception as e:
        print("🔥 COST ERROR:", e)
        cost_data = {}

    total_cost = cost_data.get("cost", 0)

    # --- ошибки ---
    errors = get_errors_count()

    return f"""
⚙️ АДМИН

👥 Пользователи: {users_count}
💳 Подписки: {active_subs}

💰 Доход: ${total_cost}
📅 Сегодня: 0

⚠️ Ошибки: {errors}
"""
