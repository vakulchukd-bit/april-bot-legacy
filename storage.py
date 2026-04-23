import json
import os
from datetime import datetime, timezone, timedelta

FILE_PATH = "data/subscriptions.json"


# ===== LOAD / SAVE =====
def load_data():
    if not os.path.exists(FILE_PATH):
        return {"users": {}}
    
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ===== TIME =====
def now():
    return datetime.now(timezone.utc)


def today():
    return now().date().isoformat()


# ===== USER INIT =====
def ensure_user(data, user_id):
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "is_subscribed": False,
            "subscription_until": 0,
            "warned": False,
            "messages_today": 0,
            "images_today": 0,
            "last_reset": today()
        }

    return uid


# ===== SUBSCRIPTION =====
def set_subscription(user_id, days=30):
    data = load_data()
    uid = ensure_user(data, user_id)

    expire_date = now().timestamp() + days * 86400

    data["users"][uid]["is_subscribed"] = True
    data["users"][uid]["subscription_until"] = expire_date
    data["users"][uid]["warned"] = False

    save_data(data)


def check_subscription(user_id):
    data = load_data()
    uid = ensure_user(data, user_id)

    user = data["users"][uid]

    if not user["is_subscribed"]:
        return False

    if user["subscription_until"] < now().timestamp():
        return False

    return True


# ===== REMAINING TIME =====
def get_remaining_seconds(user_id):
    data = load_data()
    uid = ensure_user(data, user_id)

    user = data["users"][uid]

    if not user["is_subscribed"]:
        return None

    return user["subscription_until"] - now().timestamp()


# ===== WARNING (24 HOURS) =====
def should_warn(user_id):
    data = load_data()
    uid = ensure_user(data, user_id)

    user = data["users"][uid]

    if not user["is_subscribed"]:
        return False

    remaining = user["subscription_until"] - now().timestamp()

    if remaining < 86400 and not user["warned"]:
        user["warned"] = True
        save_data(data)
        return True

    return False


# ===== RESET DAILY LIMITS =====
def reset_if_needed(user):
    if user["last_reset"] != today():
        user["messages_today"] = 0
        user["images_today"] = 0
        user["last_reset"] = today()
        return True
    return False


# ===== LIMITS =====
def can_send_message(user_id, limit=15):
    data = load_data()
    uid = ensure_user(data, user_id)
    user = data["users"][uid]

    if reset_if_needed(user):
        save_data(data)

    if user["messages_today"] >= limit:
        return False

    user["messages_today"] += 1
    save_data(data)
    return True


def can_generate_image(user_id, limit=1):
    data = load_data()
    uid = ensure_user(data, user_id)
    user = data["users"][uid]

    if reset_if_needed(user):
        save_data(data)

    if user["images_today"] >= limit:
        return False

    user["images_today"] += 1
    save_data(data)
    return True


# ===== 🔥 НОВОЕ: ПОЛУЧИТЬ СЧЁТЧИКИ =====
def get_limits(user_id, msg_limit=15, img_limit=1):
    data = load_data()
    uid = ensure_user(data, user_id)
    user = data["users"][uid]

    reset_if_needed(user)

    return {
        "messages_used": user["messages_today"],
        "messages_limit": msg_limit,
        "images_used": user["images_today"],
        "images_limit": img_limit
    }


# ===== 🔥 НОВОЕ: АДМИН СТАТИСТИКА =====
def get_admin_stats():
    data = load_data()

    users = data["users"]

    total_users = len(users)
    subs = 0

    for u in users.values():
        if u.get("is_subscribed") and u.get("subscription_until", 0) > now().timestamp():
            subs += 1

    # 💰 пока заглушка (потом подключим реальные платежи)
    income_total = subs * 150
    income_today = 0

    return {
        "users": total_users,
        "subs": subs,
        "income_total": income_total,
        "income_today": income_today
    }
