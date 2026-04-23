import jsonfrom aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ===== ОСНОВНАЯ КЛАВИАТУРА (под ответом) =====
def main_keyboard(msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data=f"like_{msg_id}"),
            InlineKeyboardButton(text="👎", callback_data=f"dislike_{msg_id}"),
            InlineKeyboardButton(text="⋯", callback_data="menu")
        ]
    ])


# ===== ❌ УСТАРЕВШАЯ (НЕ ИСПОЛЬЗУЕМ) =====
# ОСТАВЛЯЮ, НО НЕ ТРОГАЕМ (чтобы ничего не сломать)
def buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="noop"),
            InlineKeyboardButton(text="❌ Нет", callback_data="noop")
        ]
    ])


# ===== 🔥 ВЫБОР ТАРИФА =====
def тариф_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Lite", callback_data="buy_lite")],
        [InlineKeyboardButton(text="👑 Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])


# ===== 🔥 ОПЛАТЫ (АДМИН) =====
def payments_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 OpenAI", url="https://platform.openai.com/account/billing")],
        [InlineKeyboardButton(text="🚂 Railway", url="https://railway.app")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]
    ])
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
            "plan": "free",  # 🔥 free / lite / premium
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
    else:
        days = 30

    expire_date = now().timestamp() + days * 86400

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

    # если истекло → free
    if user["subscription_until"] < now().timestamp():
        return "free"

    return user.get("plan", "free")


def check_subscription(user_id):
    plan = get_user_plan(user_id)
    return plan in ["lite", "premium"]


# ===== REMAINING TIME =====
def get_remaining_seconds(user_id):
    data = load_data()
    uid, created = ensure_user(data, user_id)

    if created:
        save_data(data)

    user = data["users"][uid]

    if user["subscription_until"] < now().timestamp():
        return None

    return user["subscription_until"] - now().timestamp()


# ===== ДНИ =====
def get_remaining_days(user_id):
    seconds = get_remaining_seconds(user_id)

    if not seconds or seconds <= 0:
        return 0

    return math.ceil(seconds / 86400)


# ===== ПРОВЕРКА СКОРОГО ОКОНЧАНИЯ =====
def is_expiring_soon(user_id, days_threshold=2):
    days = get_remaining_days(user_id)
    return 0 < days <= days_threshold


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


def can_generate_image(user_id, limit=1):
    data = load_data()
    uid, created = ensure_user(data, user_id)
    user = data["users"][uid]

    if created:
        save_data(data)

    if reset_if_needed(user):
        save_data(data)

    if user["images_today"] >= limit:
        return False

    user["images_today"] += 1
    save_data(data)
    return True


# ===== СЧЁТЧИКИ =====
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


# ===== ОСТАЛОСЬ СООБЩЕНИЙ =====
def get_remaining_messages(user_id, limit=15):
    data = load_data()
    uid, created = ensure_user(data, user_id)
    user = data["users"][uid]

    if created:
        save_data(data)

    reset_if_needed(user)

    remaining = limit - user["messages_today"]
    return max(0, remaining)


# ===== СПИСКИ =====
def get_all_users():
    data = load_data()
    return list(data["users"].keys())


def get_all_subscriptions():
    data = load_data()

    result = []

    for uid, user in data["users"].items():
        if user.get("subscription_until", 0) > now().timestamp():
            result.append(uid)

    return result


# ===== АДМИН СТАТИСТИКА =====
def get_admin_stats():
    data = load_data()

    users = data["users"]

    total_users = len(users)
    subs = 0

    for u in users.values():
        if u.get("subscription_until", 0) > now().timestamp():
            subs += 1

    income_total = subs * 150
    income_today = 0

    return {
        "users": total_users,
        "subs": subs,
        "income_total": income_total,
        "income_today": income_today
    }


# ===== ТАЙМЕР =====
def get_reset_seconds(user_id):
    now_time = now()
    tomorrow = (now_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now_time).total_seconds())


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02}:{minutes:02}:{secs:02}"
