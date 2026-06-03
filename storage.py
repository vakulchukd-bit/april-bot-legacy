import json
import os
import math
from datetime import datetime, timezone, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

# ===== 🔥 CENTRAL TARIFF CONFIG =====
# Все лимиты и цены берутся из одного места
# Это безопаснее для архитектуры April
from blocks.tariffs_config import (
    FREE_MESSAGES_LIMIT,
    FREE_IMAGES_LIMIT,
    LITE_PRICE,
    PREMIUM_PRICE,
    LITE_DAYS,
    PREMIUM_DAYS
)

FILE_PATH = "data/subscriptions.json"


# ===== 🔥 DB CONNECT =====
def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None

    return psycopg2.connect(
        db_url,
        cursor_factory=RealDictCursor
    )


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

            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                plan TEXT,
                amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                is_positive BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id SERIAL PRIMARY KEY,
                key TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

    conn.close()

    # APRIL MEMORY INIT
    init_memory_tables()


# =========================================================
# 🔥 KNOWLEDGE FUNCTIONS
# =========================================================

def save_knowledge(key: str, content: str):
    conn = get_conn()

    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO knowledge (key, content)
            VALUES (%s, %s)
            """, (key, content))


def find_knowledge(text: str):
    conn = get_conn()

    if not conn:
        return None

    t = text.lower()

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT key, content FROM knowledge")
            rows = cur.fetchall()

            for row in rows:
                if row["key"] and row["key"] in t:
                    return row["content"]

    return None


# =========================================================
# ⏰ TIME
# =========================================================

def now():
    return datetime.now(timezone.utc)


def today():
    return now().date().isoformat()


# =========================================================
# 👤 USER DB
# =========================================================

def ensure_user_db(user_id):
    conn = get_conn()

    if not conn:
        return None

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute(
                "SELECT * FROM users WHERE user_id = %s",
                (uid,)
            )

            user = cur.fetchone()

            if not user:
                cur.execute("""
                INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    uid,
                    "free",
                    0,
                    False,
                    0,
                    0,
                    today()
                ))

                return None

            return user


# =========================================================
# 💳 PLAN MANAGEMENT
# =========================================================

def set_subscription(user_id, plan="premium"):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        # ===== 🔥 CONFIG BASED DAYS =====
        if plan == "lite":
            days = LITE_DAYS

        elif plan == "premium":
            days = PREMIUM_DAYS

        else:
            plan = "free"
            days = 0

        expire_date = (
            now().timestamp() + days * 86400
            if days > 0 else 0
        )

        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                INSERT INTO users (
                    user_id,
                    plan,
                    subscription_until,
                    warned,
                    messages_today,
                    images_today,
                    last_reset
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)

                ON CONFLICT (user_id) DO UPDATE SET
                plan = EXCLUDED.plan,
                subscription_until = EXCLUDED.subscription_until,
                warned = FALSE
                """, (
                    uid,
                    plan,
                    expire_date,
                    False,
                    0,
                    0,
                    today()
                ))

        conn.close()
        return


def save_payment(user_id, plan):
    conn = get_conn()

    if not conn:
        return

    uid = str(user_id)

    # ===== 🔥 CONFIG BASED PRICES =====
    amount = (
        LITE_PRICE
        if plan == "lite"
        else PREMIUM_PRICE
        if plan == "premium"
        else 0
    )

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO payments (user_id, plan, amount)
            VALUES (%s, %s, %s)
            """, (
                uid,
                plan,
                amount
            ))


def save_feedback(user_id, is_positive):
    conn = get_conn()

    if not conn:
        return

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO feedback (user_id, is_positive)
            VALUES (%s, %s)
            """, (
                uid,
                is_positive
            ))


# =========================================================
# 📦 SUBSCRIPTIONS
# =========================================================

def get_user_plan(user_id):
    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT plan, subscription_until, warned
                FROM users
                WHERE user_id = %s
                """, (uid,))

                user = cur.fetchone()

                if not user:
                    ensure_user_db(user_id)
                    return "free"

                # ===== 🔥 AUTO DOWNGRADE =====
                # Подписка закончилась → FREE
                if user["subscription_until"] < now().timestamp():
                    return "free"

                return user["plan"]

    return "free"


def check_subscription(user_id):
    return get_user_plan(user_id) in ["lite", "premium"]


# =========================================================
# ⚠️ WARNING
# =========================================================

def should_warn(user_id):
    conn = get_conn()

    if not conn:
        return False

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT subscription_until, warned
            FROM users
            WHERE user_id = %s
            """, (uid,))

            user = cur.fetchone()

            if not user:
                return False

            remaining = (
                user["subscription_until"]
                - now().timestamp()
            )

            if remaining < 86400 and not user["warned"]:

                cur.execute("""
                UPDATE users
                SET warned = TRUE
                WHERE user_id = %s
                """, (uid,))

                return True

    return False






# =========================================================
# 🔥 LIMITS FOUNDATION
# =========================================================

# ===== 👑 ADMIN CHECK =====
# Админ полностью выведен из лимитов
# Без ограничений и reset

from blocks.tariffs_config import ADMIN_ID


# =========================================================
# 🔄 RESET HELPERS
# =========================================================

def should_reset_limits(user):

    if not user:
        return False

    return user["last_reset"] != today()


def reset_user_limits(cur, uid):

    cur.execute("""
    UPDATE users
    SET messages_today = 0,
        images_today = 0,
        last_reset = %s
    WHERE user_id = %s
    """, (
        today(),
        uid
    ))


# =========================================================
# 💬 MESSAGE LIMITS
# =========================================================

def can_send_message(
    user_id,
    limit=FREE_MESSAGES_LIMIT
):

    # 👑 ADMIN BYPASS
    if user_id == ADMIN_ID:
        return True

    # ♾️ UNLIMITED
    if limit == -1:
        return True

    conn = get_conn()

    if not conn:
        return True

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT messages_today, images_today, last_reset
            FROM users
            WHERE user_id = %s
            """, (uid,))

            user = cur.fetchone()

            if not user:
                ensure_user_db(user_id)
                return True

            # 🔄 RESET
            if should_reset_limits(user):

                reset_user_limits(cur, uid)

                user["messages_today"] = 0

            # ⛔ LIMIT
            if user["messages_today"] >= limit:
                return False

            # ➕ COUNTER
            cur.execute("""
            UPDATE users
            SET messages_today = messages_today + 1
            WHERE user_id = %s
            """, (uid,))

            return True

    return True


# =========================================================
# 🖼 IMAGE LIMITS
# =========================================================

def can_generate_image(
    user_id,
    limit=FREE_IMAGES_LIMIT
):

    # 👑 ADMIN BYPASS
    if user_id == ADMIN_ID:
        return True

    # ♾️ UNLIMITED
    if limit == -1:
        return True

    conn = get_conn()

    if not conn:
        return True

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT messages_today, images_today, last_reset
            FROM users
            WHERE user_id = %s
            """, (uid,))

            user = cur.fetchone()

            if not user:
                ensure_user_db(user_id)
                return True

            # 🔄 RESET
            if should_reset_limits(user):

                reset_user_limits(cur, uid)

                user["images_today"] = 0

            # ⛔ LIMIT
            if user["images_today"] >= limit:
                return False

            # ➕ COUNTER
            cur.execute("""
            UPDATE users
            SET images_today = images_today + 1
            WHERE user_id = %s
            """, (uid,))

            return True

    return True


# =========================================================
# 📊 REMAINING
# =========================================================

def get_remaining_messages(
    user_id,
    limit=FREE_MESSAGES_LIMIT
):

    if user_id == ADMIN_ID:
        return "∞"

    if limit == -1:
        return "∞"

    conn = get_conn()

    if not conn:
        return limit

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT messages_today
            FROM users
            WHERE user_id = %s
            """, (uid,))

            user = cur.fetchone()

            if not user:
                return limit

            return max(
                0,
                limit - user["messages_today"]
            )

    return limit


def get_remaining_images(
    user_id,
    limit=FREE_IMAGES_LIMIT
):

    if user_id == ADMIN_ID:
        return "∞"

    if limit == -1:
        return "∞"

    conn = get_conn()

    if not conn:
        return limit

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT images_today
            FROM users
            WHERE user_id = %s
            """, (uid,))

            user = cur.fetchone()

            if not user:
                return limit

            return max(
                0,
                limit - user["images_today"]
            )

    return limit


# =========================================================
# 📅 SUB DAYS
# =========================================================

def get_remaining_days(user_id):

    if user_id == ADMIN_ID:
        return "∞"

    conn = get_conn()

    if not conn:
        return 0

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT subscription_until
            FROM users
            WHERE user_id = %s
            """, (uid,))

            user = cur.fetchone()

            if not user:
                return 0

            seconds = (
                user["subscription_until"]
                - now().timestamp()
            )

            return max(
                0,
                math.ceil(seconds / 86400)
            )

    return 0


# =========================================================
# 📦 LIMITS INFO
# =========================================================

def get_limits(
    user_id,
    msg_limit=FREE_MESSAGES_LIMIT,
    img_limit=FREE_IMAGES_LIMIT
):

    # 👑 ADMIN
    if user_id == ADMIN_ID:

        return {
            "messages_used": "∞",
            "messages_limit": "∞",
            "images_used": "∞",
            "images_limit": "∞"
        }

    # ♾️ UNLIMITED
    if msg_limit == -1:
        msg_limit = "∞"

    if img_limit == -1:
        img_limit = "∞"

    conn = get_conn()

    if not conn:
        return {
            "messages_used": 0,
            "messages_limit": msg_limit,
            "images_used": 0,
            "images_limit": img_limit
        }

    uid = str(user_id)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            SELECT messages_today, images_today, last_reset
            FROM users
            WHERE user_id = %s
            """, (uid,))

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

            # 🔄 RESET
            if should_reset_limits(user):

                messages = 0
                images = 0

                reset_user_limits(cur, uid)

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

    # =====================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:
        return True

    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT messages_today, images_today, last_reset
                FROM users
                WHERE user_id = %s
                """, (uid,))

                user = cur.fetchone()

                if not user:
                    ensure_user_db(user_id)
                    return True

                # =================================================
                # 🔄 DAILY RESET
                # =================================================

                if user["last_reset"] != today():

                    cur.execute("""
                    UPDATE users
                    SET messages_today = 0,
                        images_today = 0,
                        last_reset = %s
                    WHERE user_id = %s
                    """, (
                        today(),
                        uid
                    ))

                    user["messages_today"] = 0

                # =================================================
                # ♾️ UNLIMITED MODE
                # =================================================

                # -1 = безлимит
                if limit == -1:
                    return True

                # =================================================
                # ⛔ LIMIT CHECK
                # =================================================

                if user["messages_today"] >= limit:
                    return False

                # =================================================
                # ➕ INCREMENT COUNTER
                # =================================================

                cur.execute("""
                UPDATE users
                SET messages_today = messages_today + 1
                WHERE user_id = %s
                """, (uid,))

                return True

    return True


def get_remaining_messages(
    user_id,
    limit=FREE_MESSAGES_LIMIT
):

    # =====================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:
        return "∞"

    # =====================================================
    # ♾️ UNLIMITED MODE
    # =====================================================

    if limit == -1:
        return "∞"

    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT messages_today
                FROM users
                WHERE user_id = %s
                """, (uid,))

                user = cur.fetchone()

                if not user:
                    return limit

                return max(
                    0,
                    limit - user["messages_today"]
                )

    return limit


def get_remaining_days(user_id):

    # =====================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:
        return "∞"

    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT subscription_until
                FROM users
                WHERE user_id = %s
                """, (uid,))

                user = cur.fetchone()

                if not user:
                    return 0

                seconds = (
                    user["subscription_until"]
                    - now().timestamp()
                )

                return max(
                    0,
                    math.ceil(seconds / 86400)
                )

    return 0


def get_limits(
    user_id,
    msg_limit=FREE_MESSAGES_LIMIT,
    img_limit=FREE_IMAGES_LIMIT
):

    # =====================================================
    # 👑 ADMIN BYPASS
    # =====================================================

    if user_id == ADMIN_ID:

        return {
            "messages_used": "∞",
            "messages_limit": "∞",
            "images_used": "∞",
            "images_limit": "∞"
        }

    # =====================================================
    # ♾️ UNLIMITED MODE
    # =====================================================

    if msg_limit == -1:
        msg_limit = "∞"

    if img_limit == -1:
        img_limit = "∞"

    conn = get_conn()

    if conn:
        uid = str(user_id)

        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT messages_today, images_today, last_reset
                FROM users
                WHERE user_id = %s
                """, (uid,))

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

                # =================================================
                # 🔄 DAILY RESET
                # =================================================

                if user["last_reset"] != today():

                    messages = 0
                    images = 0

                    # ===== 🔥 RESET SYNC FIX =====
                    cur.execute("""
                    UPDATE users
                    SET messages_today = 0,
                        images_today = 0,
                        last_reset = %s
                    WHERE user_id = %s
                    """, (
                        today(),
                        uid
                    ))

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


# =========================================================
# ⚙️ ADMIN
# =========================================================

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

            cur.execute("""
            SELECT COUNT(*) as count
            FROM users
            """)

            users = cur.fetchone()["count"]

            cur.execute("""
            SELECT COUNT(*) as count
            FROM users
            WHERE plan IN ('lite', 'premium')
            AND subscription_until > %s
            """, (now().timestamp(),))

            subs = cur.fetchone()["count"]

            cur.execute("""
            SELECT SUM(amount) as total
            FROM payments
            """)

            income_total = (
                cur.fetchone()["total"] or 0
            )

            cur.execute("""
            SELECT SUM(amount) as today
            FROM payments
            WHERE DATE(created_at) = CURRENT_DATE
            """)

            income_today = (
                cur.fetchone()["today"] or 0
            )

            return {
                "users": users,
                "subs": subs,
                "income_total": income_total,
                "income_today": income_today
            }


# =========================================================
# ⏳ RESET TIMER
# =========================================================

def get_reset_seconds(user_id):
    now_time = now()

    tomorrow = (
        now_time + timedelta(days=1)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    return int(
        (tomorrow - now_time).total_seconds()
    )


def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02}:{minutes:02}:{secs:02}"


# =========================================================
# 👥 USERS
# =========================================================

def get_all_users():
    conn = get_conn()

    if conn:
        with conn:
            with conn.cursor() as cur:

                cur.execute("""
                SELECT user_id
                FROM users
                """)

                return [
                    u["user_id"]
                    for u in cur.fetchall()
                ]

    return []


# =========================================================
# APRIL UPGRADE PATCHES (STEP-02 + STEP-03)
# =========================================================

# Добавить в init_db()/migration:
# april_id, email, name, provider,
# provider_user_id, created_at, last_login_at

import random

def generate_april_id():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    def part(size):
        return "".join(random.choice(alphabet) for _ in range(size))
    return f"APR-{part(4)}-{part(4)}"

# Далее добавить:
# find_user_by_email()
# get_user_by_april_id()
# update_last_login()
# create_user()
# find_or_create_user()

# STEP-04:
# auth.ts вызывает backend endpoint:
# POST /api/users/find-or-create


# =========================================================
# STEP-05 PERSISTENT MEMORY
# =========================================================

def init_memory_tables():
    conn = get_conn()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS memory_states (
                user_id TEXT PRIMARY KEY,
                memory_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

def save_memory(user_id, memory_data):
    init_memory_tables()
    conn = get_conn()
    if not conn:
        return False

    payload = json.dumps(memory_data, ensure_ascii=False)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO memory_states (
                user_id,
                memory_json,
                updated_at
            )
            VALUES (%s,%s,CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                memory_json = EXCLUDED.memory_json,
                updated_at = CURRENT_TIMESTAMP
            """, (
                str(user_id),
                payload
            ))
    return True

def load_memory(user_id):
    init_memory_tables()
    conn = get_conn()
    if not conn:
        return None

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT memory_json
            FROM memory_states
            WHERE user_id = %s
            """, (str(user_id),))

            row = cur.fetchone()

            if not row:
                return None

            try:
                return json.loads(
                    row["memory_json"]
                )
            except Exception:
                return None

def delete_memory(user_id):
    conn = get_conn()
    if not conn:
        return False

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            DELETE FROM memory_states
            WHERE user_id = %s
            """, (str(user_id),))

    return True


# =========================================================
# APRIL USER MIGRATION V1
# =========================================================

def migrate_users_table_v1():
    conn = get_conn()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS april_id TEXT
            """)

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email TEXT
            """)

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS name TEXT
            """)

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS provider TEXT
            """)

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS provider_user_id TEXT
            """)

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)

            cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)


def find_user_by_email(email):
    conn = get_conn()
    if not conn:
        return None

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE email = %s",
                ((email or "").lower(),)
            )
            return cur.fetchone()


def get_user_by_april_id(april_id):
    conn = get_conn()
    if not conn:
        return None

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE april_id = %s",
                (april_id,)
            )
            return cur.fetchone()


def update_last_login(user_id):
    conn = get_conn()
    if not conn:
        return

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                """,
                (str(user_id),)
            )


def create_user(email, name="", provider="google", provider_user_id=None):

    conn = get_conn()
    if not conn:
        return None

    april_id = generate_april_id()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO users (
                user_id,
                april_id,
                email,
                name,
                provider,
                provider_user_id,
                plan,
                subscription_until,
                warned,
                messages_today,
                images_today,
                last_reset
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,
                'free',0,FALSE,0,0,%s
            )
            """, (
                april_id,
                april_id,
                (email or "").lower(),
                name,
                provider,
                provider_user_id,
                today()
            ))

    return get_user_by_april_id(april_id)


def find_or_create_user(
    email,
    name="",
    provider="google",
    provider_user_id=None
):
    existing = find_user_by_email(email)

    if existing:
        update_last_login(existing["user_id"])
        return existing

    return create_user(
        email=email,
        name=name,
        provider=provider,
        provider_user_id=provider_user_id
    )
