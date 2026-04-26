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

            # 🔥 ДОБАВИЛИ payments
            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                plan TEXT,
                amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

    conn.close()


# ===== TIME =====
def now():
    return datetime.now(timezone.utc)


def today():
    return now().date().isoformat()


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
            days = 5
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


# 🔥 СОХРАНЕНИЕ ПЛАТЕЖА (ДОЛЛАРЫ)
def save_payment(user_id, plan):
    conn = get_conn()
    if not conn:
        return

    uid = str(user_id)

    amount = 6 if plan == "lite" else 25 if plan == "premium" else 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO payments (user_id, plan, amount)
            VALUES (%s, %s, %s)
            """, (uid, plan, amount))


def get_user_plan(user_id):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT plan, subscription_until, warned FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    ensure_user_db(user_id)
                    return "free"

                if user["subscription_until"] < now().timestamp():
                    return "free"

                return user["plan"]

    return "free"


def check_subscription(user_id):
    return get_user_plan(user_id) in ["lite", "premium"]


# ===== WARNING =====
def should_warn(user_id):
    conn = get_conn()
    if not conn:
        return False

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT subscription_until, warned FROM users WHERE user_id = %s", (uid,))
            user = cur.fetchone()

            if not user:
                return False

            remaining = user["subscription_until"] - now().timestamp()

            if remaining < 86400 and not user["warned"]:
                cur.execute("UPDATE users SET warned = TRUE WHERE user_id = %s", (uid,))
                return True

    return False


# ===== LIMITS =====
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

    return True


# ===== 🔥 ДОБАВЛЕННЫЕ ФУНКЦИИ =====
def get_remaining_messages(user_id, limit=15):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT messages_today FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    return limit

                return max(0, limit - user["messages_today"])

    return limit


def get_remaining_days(user_id):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subscription_until FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    return 0

                seconds = user["subscription_until"] - now().timestamp()
                return max(0, math.ceil(seconds / 86400))

    return 0


def get_limits(user_id, msg_limit=15, img_limit=1):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT messages_today, images_today, last_reset FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    return {
                        "messages_used": 0,
                        "messages_limit": msg_limit,
                        "images_used": 0,
                        "images_limit": img_limit
                    }

                messages = user["messages_today"] or 0
                images = user["images_today"] or 0

                if user["last_reset"] != today():
                    messages = 0
                    images = 0

                return {
                    "messages_used": messages,
                    "messages_limit": msg_limit,
                    "images_used": images,
                    "images_limit": img_limit
                }

    return {
        "messages_used": 0,
        "messages_limit": msg_limit,
        "images_used": 0,
        "images_limit": img_limit
    }


# 🔥 ДОХОД (теперь в долларах)
def get_admin_stats():
    conn = get_conn()
    if not conn:
        return {
            "users": 0,
            "subs": 0,
            "income_total": 0,
            "income_today": 0
        }

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM users")
            users = cur.fetchone()["count"]

            cur.execute("""
                SELECT COUNT(*) as count FROM users
                WHERE plan IN ('lite', 'premium')
                AND subscription_until > %s
            """, (now().timestamp(),))
            subs = cur.fetchone()["count"]

            cur.execute("SELECT SUM(amount) as total FROM payments")
            income_total = cur.fetchone()["total"] or 0

            cur.execute("""
            SELECT SUM(amount) as today FROM payments
            WHERE DATE(created_at) = CURRENT_DATE
            """)
            income_today = cur.fetchone()["today"] or 0

            return {
                "users": users,
                "subs": subs,
                "income_total": income_total,
                "income_today": income_today
            }


def get_reset_seconds(user_id):
    now_time = now()
    tomorrow = (now_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now_time).total_seconds())


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"


# ===== ADMIN =====
def get_all_users():
    conn = get_conn()
    if conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users")
                return [u["user_id"] for u in cur.fetchall()]

    return []
