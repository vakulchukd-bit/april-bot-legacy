import json
import os
import math
from datetime import datetime, timezone, timedelta

# 🔥 NEW: DATABASE
import psycopg2
from psycopg2.extras import RealDictCursor

FILE_PATH = "data/subscriptions.json"

# ===== 🔥 DB CONNECT =====
def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                plan TEXT,
                subscription_until DOUBLE PRECISION,
                warned BOOLEAN,
                messages_today INTEGER,
                images_today INTEGER,
                last_reset TEXT
            )
            """)
    conn.close()


# ===== LOAD / SAVE (FALLBACK JSON) =====
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


# ===== 🔥 DB USER =====
def ensure_user_db(user_id):
    conn = get_conn()
    if not conn:
        return None

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
            user = cur.fetchone()

            if not user:
                cur.execute("""
                INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (uid, "free", 0, False, 0, 0, today()))
                return None

            return user


# ===== 🔥 PLAN MANAGEMENT =====
def set_subscription(user_id, plan="premium"):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        if plan == "lite":
            days = 15
        elif plan == "premium":
            days = 30
        else:
            plan = "free"
            days = 0

        expire_date = now().timestamp() + days * 86400 if days > 0 else 0

        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO users (user_id, plan, subscription_until, warned, messages_today, images_today, last_reset)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                plan = EXCLUDED.plan,
                subscription_until = EXCLUDED.subscription_until,
                warned = FALSE
                """, (uid, plan, expire_date, False, 0, 0, today()))
        conn.close()
        return

    # fallback
    data = load_data()
    uid, _ = ensure_user(data, user_id)
    data["users"][uid]["plan"] = plan
    data["users"][uid]["subscription_until"] = now().timestamp() + 30 * 86400
    save_data(data)


def get_user_plan(user_id):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT plan, subscription_until FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    ensure_user_db(user_id)
                    return "free"

                if user["subscription_until"] < now().timestamp():
                    return "free"

                return user["plan"]

    # fallback
    data = load_data()
    uid, _ = ensure_user(data, user_id)
    return data["users"][uid].get("plan", "free")


def check_subscription(user_id):
    return get_user_plan(user_id) in ["lite", "premium"]


# ===== LIMITS (DB VERSION) =====
def can_send_message(user_id, limit=15):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT messages_today, last_reset FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    ensure_user_db(user_id)
                    return True

                if user["last_reset"] != today():
                    cur.execute("""
                    UPDATE users SET messages_today = 0, last_reset = %s WHERE user_id = %s
                    """, (today(), uid))
                    user["messages_today"] = 0

                if user["messages_today"] >= limit:
                    return False

                cur.execute("""
                UPDATE users SET messages_today = messages_today + 1 WHERE user_id = %s
                """, (uid,))
                return True

    # fallback
    data = load_data()
    uid, _ = ensure_user(data, user_id)
    user = data["users"][uid]

    if user["messages_today"] >= limit:
        return False

    user["messages_today"] += 1
    save_data(data)
    return True


# ===== ADMIN =====
def get_all_users():
    conn = get_conn()
    if conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users")
                return [u["user_id"] for u in cur.fetchall()]

    data = load_data()
    return list(data["users"].keys())
