import json
import os
import math
from datetime import datetime, timezone, timedelta

FILE_PATH = "data/subscriptions.json"


# ===== LOAD / SAVE =====
def load_data():
    if not os.path.exists(FILE_PATH):
        return {"users": {}}

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
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
            "plan": "free",
            "subscription_until": 0,
            "warned": False,
            "messages_today": 0,
            "images_today": 0,
            "last_reset": today()
        }
        return uid, True

    return uid, False


# ===== 🔥 PLAN MANAGEMENT =====
def set_subscription(user_id, plan="premium"):
    data = load_data()
    uid, _ = ensure_user(data, user_id)

    if plan == "lite":
        days = 15
    elif plan == "premium":
        days = 30
    else:
        # защита от мусора
        plan = "free"
        days = 0

    if days > 0:
        expire_date = now().timestamp() + days * 86400
    else:
        expire_date = 0

    data["users"][uid]["plan"] = plan
    data["users"][uid]["subscription_until"] = expire_date
    data["users"][uid]["warned"] = False

    save_data(data)


def get_user_plan(user_id):
    data = load_data()
    uid, created = ensure_user(data, user_id)

    user = data["users"][uid]

    if created:
        save_data(data)

    # 🔥 ВАЖНО: если истекло → сбрасываем в free
    if user["subscription_until"] < now().timestamp():
        if user["plan"] != "free":
            user["plan"] = "free"
            save_data(data)
        return "free"

    return user.get("plan", "free")


def check_subscription(user_id):
    return get_user_plan(user_id) in ["lite", "premium"]


# ===== REMAINING =====
def get_remaining_seconds(user_id):
    data = load_data()
    uid, created = ensure_user(data, user_id)

    if created:
        save_data(data)

    user = data["users"][uid]

    if user["subscription_until"] < now().timestamp():
        return None

    return user["subscription_until"] - now().timestamp()


def get_remaining_days(user_id):
    seconds = get_remaining_seconds(user_id)

    if not seconds or seconds <= 0:
        return 0

    return math.ceil(seconds / 86400)


# ===== WARNING =====
def should_warn(user_id):
    data = load_data()
    uid, created = ensure_user(data, user_id)

    user = data["users"][uid]

    if created:
        save_data(data)

    if user["subscription_until"] < now().timestamp():
        return False

    remaining = user["subscription_until"] - now().timestamp()

    if remaining < 86400 and not user["warned"]:
        user["warned"] = True
        save_data(data)
        return True

    return False


# ===== LIMITS =====
def reset_if_needed(user):
    if user["last_reset"] != today():
        user["messages_today"] = 0
        user["images_today"] = 0
        user["last_reset"] = today()
        return True
    return False


def can_send_message(user_id, limit=15):
    data = load_data()
    uid, created = ensure_user(data, user_id)
    user = data["users"][uid]

    if created:
        save_data(data)

    if reset_if_needed(user):
        save_data(data)

    if user["messages_today"] >= limit:
        return False

    user["messages_today"] += 1
    save_data(data)
    return True


def get_limits(user_id, msg_limit=15, img_limit=1):
    data = load_data()
    uid, created = ensure_user(data, user_id)
    user = data["users"][uid]

    if created:
        save_data(data)

    reset_if_needed(user)

    return {
        "messages_used": user["messages_today"],
        "messages_limit": msg_limit,
        "images_used": user["images_today"],
        "images_limit": img_limit
    }


def get_remaining_messages(user_id, limit=15):
    data = load_data()
    uid, created = ensure_user(data, user_id)
    user = data["users"][uid]

    if created:
        save_data(data)

    reset_if_needed(user)

    return max(0, limit - user["messages_today"])


# ===== ADMIN =====
def get_admin_stats():
    data = load_data()

    users = data["users"]

    total_users = len(users)
    subs = sum(
        1 for u in users.values()
        if u["subscription_until"] > now().timestamp()
    )

    return {
        "users": total_users,
        "subs": subs,
        "income_total": subs * 150,
        "income_today": 0
    }


# ===== TIMER =====
def get_reset_seconds(user_id):
    now_time = now()
    tomorrow = (now_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now_time).total_seconds())


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02}:{minutes:02}:{secs:02}"
