from storage import (
    get_admin_stats,
    get_all_users,
    check_subscription
)

from blocks.error_handler import get_errors

ADMIN_ID = 2016592532


# =========================================================
# 👥 REGISTER USER
# =========================================================

def register_user(user_id):

    # теперь user создаётся через storage.py
    # ensure_user_db вызывается в bot.py

    return True


# =========================================================
# 📋 EVENTS
# =========================================================

def log_event(user_id, event_type):

    # пока оставляем заглушку
    # позже подключим analytics db

    return True


# =========================================================
# 💳 ACTIVE SUBSCRIPTIONS
# =========================================================

def get_active_subscriptions():

    try:

        users = get_all_users()

        active = 0

        for uid in users:

            try:

                if check_subscription(uid):
                    active += 1

            except:
                pass

        return active

    except Exception as e:

        print("🔥 SUB ERROR:", e)

        return 0


# =========================================================
# ⚠️ ERRORS
# =========================================================

def get_errors_count():

    try:

        errors = get_errors()

        return len(errors)

    except:

        return 0


# =========================================================
# ⚙️ SYSTEM STATUS
# =========================================================

def get_system_status():

    try:

        stats = get_admin_stats()

        users = stats.get("users", 0)
        subs = stats.get("subs", 0)

        income_total = stats.get(
            "income_total",
            0
        )

        income_today = stats.get(
            "income_today",
            0
        )

    except Exception as e:

        print("🔥 SYSTEM STATUS ERROR:", e)

        users = 0
        subs = 0
        income_total = 0
        income_today = 0

    errors = get_errors_count()

    db_status = "ONLINE"

    if errors > 10:
        system_status = "WARNING"

    else:
        system_status = "STABLE"

    return f'''
⚙️ СИСТЕМА APRIL

🟢 PostgreSQL: {db_status}
🟢 Core: ONLINE
🟢 Dispatcher: ACTIVE

━━━━━━━━━━━━━━━

👥 Пользователи: {users}
💳 Подписки: {subs}

💰 Доход всего: ${income_total}
📅 Сегодня: ${income_today}

⚠️ Ошибки: {errors}

━━━━━━━━━━━━━━━

🔥 STATUS: {system_status}
'''


# =========================================================
# ⚙️ ADMIN PANEL
# =========================================================

def get_admin_panel():

    try:

        stats = get_admin_stats()

        users = stats.get("users", 0)

        subs = stats.get("subs", 0)

        income_total = stats.get(
            "income_total",
            0
        )

        income_today = stats.get(
            "income_today",
            0
        )

    except Exception as e:

        print("🔥 ADMIN PANEL ERROR:", e)

        users = 0
        subs = 0
        income_total = 0
        income_today = 0

    errors = get_errors_count()

    return f"""
⚙️ АДМИН

👥 Пользователи: {users}
💳 Подписки: {subs}

💰 Доход всего: ${income_total}
📅 Сегодня: ${income_today}

⚠️ Ошибки: {errors}
"""
