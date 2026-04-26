import json
import os
import math
from datetime import datetime, timezone, timedelta
import pytz  # 🔥 ДОБАВЛЕНО

# 🔥 NEW: DATABASE
import psycopg2
from psycopg2.extras import RealDictCursor

FILE_PATH = "data/subscriptions.json"

# 👑 ADMIN
ADMIN_ID = 2016592532

# 🔥 ЛОКАЛЬНАЯ ЗОНА (FALLBACK)
DEFAULT_TZ = "Europe/Kyiv"


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
                edits_today INTEGER,
                last_reset TEXT,
                timezone TEXT
            )
            """)

            # 🔥 ДОБАВЛЕНО: гарантируем наличие колонок (ничего не ломает)
            try:
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS edits_today INTEGER DEFAULT 0")
            except:
                pass

            try:
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS images_today INTEGER DEFAULT 0")
            except:
                pass

            try:
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT")
            except:
                pass

    conn.close()


# ===== TIME =====
def now():
    return datetime.now(timezone.utc)


def get_user_timezone(user):
    tz = user.get("timezone") if user else None
    if not tz:
        tz = DEFAULT_TZ
    try:
        return pytz.timezone(tz)
    except:
        return pytz.timezone(DEFAULT_TZ)


def now_local(user=None):
    tz = get_user_timezone(user)
    return datetime.now(tz)


def today(user=None):
    return now_local(user).date().isoformat()


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
                INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (uid, "free", 0, False, 0, 0, 0, today(), DEFAULT_TZ))
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
                INSERT INTO users (user_id, plan, subscription_until, warned, messages_today, images_today, edits_today, last_reset, timezone)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                plan = EXCLUDED.plan,
                subscription_until = EXCLUDED.subscription_until,
                warned = FALSE
                """, (uid, plan, expire_date, False, 0, 0, 0, today(), DEFAULT_TZ))
        conn.close()
        return


def get_user_plan(user_id):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
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
            cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
            user = cur.fetchone()

            if not user:
                return False

            remaining = user["subscription_until"] - now().timestamp()

            if remaining < 86400 and not user["warned"]:
                cur.execute("UPDATE users SET warned = TRUE WHERE user_id = %s", (uid,))
                return True

    return False


# ===== 🔥 ВРЕМЯ СБРОСА (ТЕПЕРЬ С УЧЁТОМ TZ) =====
def get_reset_seconds(user):
    now_time = now_local(user)

    tomorrow = (now_time + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    return int((tomorrow - now_time).total_seconds())


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}ч {minutes}м"


# ===== RESET =====
def sync_reset(cur, uid, user):
    if user["last_reset"] != today(user):
        cur.execute("""
        UPDATE users SET messages_today = 0, edits_today = 0, images_today = 0, last_reset = %s WHERE user_id = %s
        """, (today(user), uid))
        user["messages_today"] = 0
        user["edits_today"] = 0
        user["images_today"] = 0


# ===== LIMITS =====
def can_send_message(user_id, limit=15):
    if user_id == ADMIN_ID:
        return True, None

    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()

                if not user:
                    ensure_user_db(user_id)
                    return True, None

                sync_reset(cur, uid, user)

                if user["messages_today"] >= limit:
                    seconds = get_reset_seconds(user)
                    return False, seconds

                cur.execute("""
                UPDATE users SET messages_today = messages_today + 1 WHERE user_id = %s
                """, (uid,))
                return True, None

    return True, None


# ===== 🔥 EDIT LIMIT =====
def can_edit(user_id):
    if user_id == ADMIN_ID:
        return True

    conn = get_conn()
    if not conn:
        return True

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
            user = cur.fetchone()

            if not user:
                return False

            sync_reset(cur, uid, user)

            plan = user["plan"]

            if plan == "premium":
                return True

            limit = 2 if plan == "lite" else 0

            if user["edits_today"] >= limit:
                return False

            cur.execute("""
            UPDATE users SET edits_today = edits_today + 1 WHERE user_id = %s
            """, (uid,))

            return True


# ===== ОСТАЛЬНОЕ НЕ ТРОГАЛ =====
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
                cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
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

                if user["last_reset"] != today(user):
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


def get_admin_stats():
    return {
        "users": 0,
        "subs": 0,
        "income_total": 0,
        "income_today": 0
    }


def get_all_users():
    conn = get_conn()
    if conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users")
                return [u["user_id"] for u in cur.fetchall()]

    return []
