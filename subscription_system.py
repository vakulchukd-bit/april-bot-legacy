# ==================== 💳 SUBSCRIPTION SYSTEM ====================

from datetime import datetime, timedelta

# 🔴 ТВОЙ ID (уже вставил)
ADMIN_ID = 2016592532

FREE_LIMIT = 2

# 🔥 УНИКАЛЬНЫЕ ИМЕНА (чтобы ничего не ломалось)
sub_users_db = {}
sub_pending_payments = set()


# ===== РЕГИСТРАЦИЯ =====
def sub_register(user_id):
    if user_id not in sub_users_db:
        sub_users_db[user_id] = {
            "messages": 0,
            "sub_until": None
        }


# ===== ПРОВЕРКА ДОСТУПА =====
def sub_check_access(user_id):
    if user_id == ADMIN_ID:
        return True, "admin"

    user = sub_users_db.get(user_id)

    if not user:
        return True, "new"

    # подписка активна
    if user["sub_until"]:
        if datetime.now() < user["sub_until"]:
            return True, "sub_active"
        else:
            user["sub_until"] = None

    # бесплатный лимит
    if user["messages"] < FREE_LIMIT:
        return True, "free"

    return False, "limit"


# ===== СЧЁТЧИК =====
def sub_add_message(user_id):
    sub_users_db[user_id]["messages"] += 1


# ===== АКТИВАЦИЯ ПОДПИСКИ =====
def sub_activate(user_id):
    sub_users_db[user_id]["sub_until"] = datetime.now() + timedelta(days=30)
