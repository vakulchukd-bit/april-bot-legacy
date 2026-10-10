"""
APRIL PostgreSQL storage — canonical minimal persistent storage.

Persistent data policy:
  1. users     -> permanent authenticated/account/subscription state.
  2. payments  -> permanent payment history.
  3. dialogue_memory -> authenticated users only, rolling UTC 12h dialogue.

The old feedback/knowledge/memory_states stores are intentionally removed.
Dialogue memory is stored as USER↔APRIL pairs only; no topics/entities/tasks are
persisted in PostgreSQL.

UTC rollover rule:
  - PostgreSQL keeps the current fixed UTC 12h cycle.
  - At a cycle boundary (00:00 or 12:00 UTC), the previous 12h segment is
    reduced to its last 1h as a continuity seed.
  - During the new cycle, the seed remains and the new pairs grow until the
    next boundary.
  - Cleanup is idempotent and runs on startup, on dialogue reads/writes, and
    from a lightweight hourly UTC worker.
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import re
import threading
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from rapidfuzz import fuzz

# These values belong to the existing storage contract; the ZIP does not contain
# a separate tariffs_config module, so storage must not import a missing file.
ADMIN_ID = os.getenv("APRIL_ADMIN_ID", "")
FREE_MESSAGES_LIMIT = int(os.getenv("APRIL_FREE_MESSAGES_LIMIT", "20"))
FREE_IMAGES_LIMIT = int(os.getenv("APRIL_FREE_IMAGES_LIMIT", "5"))
LITE_PRICE = int(os.getenv("APRIL_LITE_PRICE", "12"))
PREMIUM_PRICE = int(os.getenv("APRIL_PREMIUM_PRICE", "69"))
LITE_DAYS = int(os.getenv("APRIL_LITE_DAYS", "5"))
PREMIUM_DAYS = int(os.getenv("APRIL_PREMIUM_DAYS", "30"))

FILE_PATH = "data/subscriptions.json"

DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_SEED_HOURS = 1
DIALOGUE_WINDOW_SECONDS = DIALOGUE_WINDOW_HOURS * 3600
DIALOGUE_SEED_SECONDS = DIALOGUE_SEED_HOURS * 3600

_USERS_COLUMNS = (
    "user_id",
    "april_id",
    "email",
    "name",
    "provider",
    "provider_user_id",
    "plan",
    "subscription_until",
    "warned",
    "messages_today",
    "images_today",
    "last_reset",
    "created_at",
    "last_login_at",
)



_ALLOWED_TABLE_COLUMNS = {
    "users": set(_USERS_COLUMNS),
    "payments": {"id", "user_id", "plan", "amount", "created_at"},
    "dialogue_memory": {"id", "user_id", "created_at", "turn_index", "user_text", "april_text", "user_text_en", "april_text_en", "language", "relation", "pair_hash", "dialog_id", "conversation_id", "message_id", "interpretation_id", "structured_request", "structured_response"},
}


def _drop_unwanted_columns(cur, table: str) -> None:
    """Keep only the canonical columns used by the current application contract."""
    allowed = _ALLOWED_TABLE_COLUMNS.get(table, set())
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    for row in cur.fetchall():
        column = str(row["column_name"] if isinstance(row, dict) else row[0])
        if column not in allowed:
            cur.execute(
                f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{column}" CASCADE'
            )

_CLEANUP_LOCK = threading.RLock()
_CLEANUP_WORKER_STARTED = False


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> str:
    return now().date().isoformat()


def utc_cycle_start(timestamp: float | int | datetime | None = None) -> datetime:
    """Return the fixed 00:00/12:00 UTC boundary containing timestamp."""
    if timestamp is None:
        stamp = now()
    elif isinstance(timestamp, datetime):
        stamp = timestamp.astimezone(timezone.utc)
    else:
        stamp = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    hour = 0 if stamp.hour < 12 else 12
    return stamp.replace(hour=hour, minute=0, second=0, microsecond=0)


def dialogue_window_bounds(timestamp: float | int | datetime | None = None) -> tuple[datetime, datetime]:
    """Return [seed_start, now] for the authenticated dialogue store.

    seed_start is one hour before the current fixed UTC cycle boundary. This is
    precisely the retained continuity seed from the previous cycle.
    """
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc)
        if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    cycle = utc_cycle_start(current)
    return cycle - timedelta(hours=DIALOGUE_SEED_HOURS), current


def _is_authenticated_row(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    return bool(
        str(row.get("user_id") or "").strip()
        and str(row.get("email") or "").strip()
        and str(row.get("provider") or "").strip()
    )


def is_authenticated_user(user_id: Any) -> bool:
    """Only a registered auth-backed row may own persistent dialogue memory."""
    conn = get_conn()
    if not conn:
        return False
    uid = str(user_id)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, email, provider
                    FROM users
                    WHERE user_id = %s
                    """,
                    (uid,),
                )
                return _is_authenticated_row(cur.fetchone())
    except Exception:
        return False
    finally:
        conn.close()


def _schema_cleanup(cur) -> None:
    """Remove the old stores so the legacy writer cannot recreate pollution."""
    cur.execute("DROP TABLE IF EXISTS feedback CASCADE")
    cur.execute("DROP TABLE IF EXISTS knowledge CASCADE")
    cur.execute("DROP TABLE IF EXISTS memory_states CASCADE")


def init_db() -> None:
    conn = get_conn()
    if not conn:
        return

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        april_id TEXT,
                        email TEXT,
                        name TEXT,
                        provider TEXT,
                        provider_user_id TEXT,
                        plan TEXT NOT NULL DEFAULT 'free',
                        subscription_until DOUBLE PRECISION NOT NULL DEFAULT 0,
                        warned BOOLEAN NOT NULL DEFAULT FALSE,
                        messages_today INTEGER NOT NULL DEFAULT 0,
                        images_today INTEGER NOT NULL DEFAULT 0,
                        last_reset TEXT NOT NULL DEFAULT CURRENT_DATE::TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_login_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                # Idempotent migration for installations that already have users.
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS april_id TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS provider TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_user_id TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'free'")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_until DOUBLE PRECISION DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS warned BOOLEAN DEFAULT FALSE")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS messages_today INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS images_today INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reset TEXT DEFAULT CURRENT_DATE::TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")

                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_april_id ON users(april_id) WHERE april_id IS NOT NULL AND april_id <> ''")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL AND email <> ''")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payments (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        plan TEXT NOT NULL,
                        amount INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS id BIGSERIAL")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS user_id TEXT")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS plan TEXT")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_created ON payments(user_id, created_at DESC)")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dialogue_memory (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        turn_index INTEGER NOT NULL,
                        user_text TEXT NOT NULL,
                        april_text TEXT NOT NULL,
                        user_text_en TEXT,
                        april_text_en TEXT,
                        language TEXT NOT NULL DEFAULT 'en',
                        relation TEXT NOT NULL DEFAULT 'NEW',
                        pair_hash TEXT NOT NULL UNIQUE,
                        dialog_id TEXT,
                        conversation_id TEXT,
                        message_id TEXT,
                        interpretation_id TEXT
                    )
                    """
                )
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS id BIGSERIAL")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS user_id TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS turn_index INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS user_text TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS april_text TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS user_text_en TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS april_text_en TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en'")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS relation TEXT DEFAULT 'NEW'")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS pair_hash TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS dialog_id TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS conversation_id TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS message_id TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS interpretation_id TEXT")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS structured_request JSONB")
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS structured_response JSONB")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_memory_user_created ON dialogue_memory(user_id, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_memory_user_dialog ON dialogue_memory(user_id, dialog_id, created_at DESC)")

                # Required destructive sanitization: known legacy memory stores are
                # no longer part of the schema and must not survive deployment.
                _schema_cleanup(cur)

                # Remove any columns that are not part of the canonical minimal schema.
                _drop_unwanted_columns(cur, "users")
                _drop_unwanted_columns(cur, "payments")
                _drop_unwanted_columns(cur, "dialogue_memory")

                # Remove orphan dialogue rows before adding the authenticated-user FK.
                cur.execute(
                    """
                    DELETE FROM dialogue_memory d
                    WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.user_id = d.user_id)
                    """
                )
                cur.execute(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conrelid = 'dialogue_memory'::regclass
                              AND conname = 'fk_dialogue_memory_user'
                        ) THEN
                            ALTER TABLE dialogue_memory
                            ADD CONSTRAINT fk_dialogue_memory_user
                            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
                        END IF;
                    END $$;
                    """
                )

                # Repair missing defaults/nulls left by old installations.
                cur.execute("UPDATE users SET plan='free' WHERE plan IS NULL")
                cur.execute("UPDATE users SET subscription_until=0 WHERE subscription_until IS NULL")
                cur.execute("UPDATE users SET warned=FALSE WHERE warned IS NULL")
                cur.execute("UPDATE users SET messages_today=0 WHERE messages_today IS NULL")
                cur.execute("UPDATE users SET images_today=0 WHERE images_today IS NULL")
                cur.execute("UPDATE users SET last_reset=%s WHERE last_reset IS NULL OR last_reset=''", (today(),))
                cur.execute("UPDATE users SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL")
                cur.execute("UPDATE users SET last_login_at=CURRENT_TIMESTAMP WHERE last_login_at IS NULL")

        cleanup_dialogue_memory_utc()
    finally:
        conn.close()

    # Existing installations may predate the authenticated April ID columns.
    backfill_april_ids()
    _start_cleanup_worker()


def _start_cleanup_worker() -> None:
    global _CLEANUP_WORKER_STARTED
    with _CLEANUP_LOCK:
        if _CLEANUP_WORKER_STARTED:
            return
        _CLEANUP_WORKER_STARTED = True

    def worker() -> None:
        while True:
            try:
                current = now()
                cycle = utc_cycle_start(current)
                next_boundary = cycle + timedelta(hours=DIALOGUE_WINDOW_HOURS)
                delay = max(30.0, (next_boundary - current).total_seconds() + 2.0)
                time.sleep(delay)
                deleted = cleanup_dialogue_memory_utc()
                if deleted:
                    print(f"STATE: UTC DIALOGUE ROLLOVER CLEANUP removed={deleted}")
            except Exception as exc:
                print(f"STATE: UTC DIALOGUE CLEANUP ERROR: {exc}")
                time.sleep(300.0)

    threading.Thread(target=worker, name="april-dialogue-utc-cleanup", daemon=True).start()


def cleanup_dialogue_memory_utc(user_id: Any | None = None, timestamp: float | int | datetime | None = None) -> int:
    """Delete rows older than the retained one-hour continuity seed.

    The cutoff is derived exclusively from UTC fixed 12h boundaries, not from
    user session start time. At 00:00/12:00 UTC, this deletes the previous 11h
    and leaves exactly the immediately preceding hour. The current cycle then
    grows until the next boundary.
    """
    conn = get_conn()
    if not conn:
        return 0
    seed_start, _current = dialogue_window_bounds(timestamp)
    cutoff = seed_start
    try:
        with conn:
            with conn.cursor() as cur:
                if user_id is None:
                    cur.execute("DELETE FROM dialogue_memory WHERE created_at < %s", (cutoff,))
                    deleted = int(cur.rowcount or 0)
                else:
                    uid = str(user_id)
                    if not _is_authenticated_cursor(cur, uid):
                        return 0
                    cur.execute(
                        "DELETE FROM dialogue_memory WHERE user_id = %s AND created_at < %s",
                        (uid, cutoff),
                    )
                    deleted = int(cur.rowcount or 0)
                return deleted
    except psycopg2.errors.UndefinedTable:
        return 0
    finally:
        conn.close()


def _is_authenticated_cursor(cur, uid: str) -> bool:
    cur.execute(
        "SELECT user_id, email, provider FROM users WHERE user_id = %s",
        (uid,),
    )
    return _is_authenticated_row(cur.fetchone())


def _pair_hash(uid: str, created_ts: float, turn_index: int, user_text: str, april_text: str) -> str:
    raw = f"{uid}|{int(created_ts * 1000)}|{int(turn_index)}|{user_text}|{april_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_dialogue_pair(
    user_id: Any,
    user_text: str,
    april_text: str,
    *,
    created_at: float | int | datetime | None = None,
    turn_index: int = 0,
    user_en: str = "",
    april_en: str = "",
    language: str = "en",
    relation: str = "NEW",
    dialog_id: str = "",
    conversation_id: str = "",
    message_id: str = "",
    interpretation_id: str = "",
    structured_request: dict[str, Any] | None = None,
    structured_response: dict[str, Any] | None = None,
) -> bool:
    """Persist one authenticated USER↔APRIL pair and nothing else."""
    uid = str(user_id)
    user_value = str(user_text or "").strip()
    april_value = str(april_text or "").strip()
    if not uid or not user_value or not april_value:
        return False

    conn = get_conn()
    if not conn:
        return False

    if isinstance(created_at, datetime):
        dt = created_at.astimezone(timezone.utc)
    elif created_at is None:
        dt = now()
    else:
        dt = datetime.fromtimestamp(float(created_at), tz=timezone.utc)
    created_ts = dt.timestamp()

    try:
        with conn:
            with conn.cursor() as cur:
                if not _is_authenticated_cursor(cur, uid):
                    return False
                # Clean before insert so the database never accumulates stale memory.
                seed_start, _ = dialogue_window_bounds(dt)
                cur.execute(
                    "DELETE FROM dialogue_memory WHERE user_id = %s AND created_at < %s",
                    (uid, seed_start),
                )
                pair_hash = _pair_hash(uid, created_ts, int(turn_index or 0), user_value, april_value)
                cur.execute(
                    """
                    INSERT INTO dialogue_memory
                        (user_id, created_at, turn_index, user_text, april_text, user_text_en, april_text_en, language, relation, pair_hash, dialog_id, conversation_id, message_id, interpretation_id, structured_request, structured_response)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (pair_hash) DO UPDATE SET
                        user_text_en = EXCLUDED.user_text_en,
                        april_text_en = EXCLUDED.april_text_en,
                        structured_request = EXCLUDED.structured_request,
                        structured_response = EXCLUDED.structured_response,
                        interpretation_id = EXCLUDED.interpretation_id
                    """,
                    (
                        uid, dt, int(turn_index or 0), user_value, april_value,
                        str(user_en or user_value), str(april_en or april_value),
                        str(language or "en"), str(relation or "NEW"), pair_hash,
                        str(dialog_id or ""), str(conversation_id or ""),
                        str(message_id or ""), str(interpretation_id or ""),
                        json.dumps(structured_request or {}, ensure_ascii=False, default=str),
                        json.dumps(structured_response or {}, ensure_ascii=False, default=str),
                    ),
                )
                return True
    except psycopg2.errors.UndefinedTable:
        return False
    finally:
        conn.close()


def load_dialogue_pairs(user_id: Any, *, limit: int = 0, timestamp: float | int | datetime | None = None) -> list[dict[str, Any]]:
    """Load authenticated dialogue pairs inside the current UTC seed+cycle window."""
    uid = str(user_id)
    conn = get_conn()
    if not conn:
        return []
    seed_start, current = dialogue_window_bounds(timestamp)
    try:
        with conn:
            with conn.cursor() as cur:
                if not _is_authenticated_cursor(cur, uid):
                    return []
                cur.execute(
                    """
                    SELECT id, user_id, created_at, turn_index, user_text, april_text, user_text_en, april_text_en,
                           language, relation, dialog_id, conversation_id, message_id, interpretation_id,
                           structured_request, structured_response
                    FROM dialogue_memory
                    WHERE user_id = %s
                      AND created_at >= %s
                      AND created_at <= %s
                    ORDER BY created_at ASC, turn_index ASC, id ASC
                    """,
                    (uid, seed_start, current),
                )
                rows = [dict(row) for row in cur.fetchall()]
                for row in rows:
                    if isinstance(row.get("created_at"), datetime):
                        row["created_at"] = row["created_at"].astimezone(timezone.utc).timestamp()
                if limit and len(rows) > int(limit):
                    rows = rows[-int(limit):]
                return rows
    except psycopg2.errors.UndefinedTable:
        return []
    finally:
        conn.close()


def search_dialogue_memory(user_id: Any, query: str, *, limit: int = 8) -> dict[str, Any]:
    """Search the actual USER↔APRIL pairs; no entity/topic index is used."""
    rows = load_dialogue_pairs(user_id, limit=0)
    q = str(query or "").strip().lower()
    if not rows:
        return {
            "engine": "dialogue_pairs_v1",
            "authenticated": False if not is_authenticated_user(user_id) else True,
            "window_hours": DIALOGUE_WINDOW_HOURS,
            "seed_hours": DIALOGUE_SEED_HOURS,
            "query": query,
            "total_pairs": 0,
            "matches": [],
        }

    now_ts = time.time()
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        hay = f"{row.get('user_text') or ''} {row.get('april_text') or ''}".lower()
        lexical = fuzz.token_set_ratio(q, hay) / 100.0 if q else 0.0
        partial = fuzz.partial_ratio(q, hay) / 100.0 if q else 0.0
        created = float(row.get("created_at") or 0.0)
        age = max(0.0, now_ts - created)
        recency = max(0.0, 1.0 - age / DIALOGUE_WINDOW_SECONDS)
        score = max(lexical * 0.68 + partial * 0.22 + recency * 0.10, recency * 0.10)
        scored.append((score, row))

    scored.sort(key=lambda item: (item[0], float(item[1].get("created_at") or 0.0)), reverse=True)
    matches = []
    for score, row in scored[: max(1, int(limit or 8))]:
        matches.append({
            "score": round(float(score), 6),
            "turn_index": int(row.get("turn_index") or 0),
            "created_at": float(row.get("created_at") or 0.0),
            "user": str(row.get("user_text") or ""),
            "april": str(row.get("april_text") or ""),
            "user_text_en": str(row.get("user_text_en") or ""),
            "april_text_en": str(row.get("april_text_en") or ""),
            "structured_request": row.get("structured_request") or {},
            "structured_response": row.get("structured_response") or {},
        })
    return {
        "engine": "dialogue_pairs_v1",
        "authenticated": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "seed_hours": DIALOGUE_SEED_HOURS,
        "query": query,
        "total_pairs": len(rows),
        "matches": matches,
    }


def generate_april_id() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    def part(size: int) -> str:
        return "".join(random.choice(alphabet) for _ in range(size))
    return f"APR-{part(4)}-{part(4)}"


def _ensure_user_defaults(cur, uid: str) -> None:
    cur.execute(
        """
        INSERT INTO users (
            user_id, plan, subscription_until, warned,
            messages_today, images_today, last_reset,
            created_at, last_login_at
        )
        VALUES (%s, 'free', 0, FALSE, 0, 0, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO NOTHING
        """,
        (uid, today()),
    )


def ensure_user_db(user_id):
    conn = get_conn()
    if not conn:
        return None
    uid = str(user_id)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
                user = cur.fetchone()
                if user:
                    return user
                _ensure_user_defaults(cur, uid)
                return None
    finally:
        conn.close()


def find_user_by_email(email):
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE LOWER(email) = %s", ((email or "").lower(),))
                return cur.fetchone()
    finally:
        conn.close()


def get_user_by_april_id(april_id):
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE april_id = %s", (april_id,))
                return cur.fetchone()
    finally:
        conn.close()


def update_last_login(user_id):
    conn = get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE user_id = %s", (str(user_id),))
    finally:
        conn.close()


def backfill_april_ids():
    conn = get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users WHERE april_id IS NULL OR april_id = ''")
                for row in cur.fetchall():
                    april_id = generate_april_id()
                    cur.execute(
                        "SELECT 1 FROM users WHERE april_id = %s",
                        (april_id,),
                    )
                    while cur.fetchone():
                        april_id = generate_april_id()
                        cur.execute("SELECT 1 FROM users WHERE april_id = %s", (april_id,))
                    cur.execute("UPDATE users SET april_id = %s WHERE user_id = %s", (april_id, row["user_id"]))
    finally:
        conn.close()


def migrate_users_table_v1():
    """Compatibility entry point; schema migration is folded into init_db()."""
    init_db()
    backfill_april_ids()


def create_user(email, name="", provider="google", provider_user_id=None):
    conn = get_conn()
    if not conn:
        return None
    april_id = generate_april_id()
    try:
        with conn:
            with conn.cursor() as cur:
                while True:
                    cur.execute("SELECT 1 FROM users WHERE april_id = %s", (april_id,))
                    if not cur.fetchone():
                        break
                    april_id = generate_april_id()
                cur.execute(
                    """
                    INSERT INTO users (
                        user_id, april_id, email, name, provider, provider_user_id,
                        plan, subscription_until, warned, messages_today, images_today,
                        last_reset, created_at, last_login_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,'free',0,FALSE,0,0,%s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                    RETURNING *
                    """,
                    (
                        april_id,
                        april_id,
                        (email or "").strip().lower(),
                        name or "",
                        provider or "google",
                        provider_user_id,
                        today(),
                    ),
                )
                return cur.fetchone()
    finally:
        conn.close()


def find_or_create_user(email, name="", provider="google", provider_user_id=None):
    existing = find_user_by_email(email)
    if existing:
        update_last_login(existing["user_id"])
        return existing
    return create_user(email, name=name, provider=provider, provider_user_id=provider_user_id)


def set_subscription(user_id, plan="premium"):
    if plan == "lite":
        days = LITE_DAYS
    elif plan == "premium":
        days = PREMIUM_DAYS
    else:
        plan, days = "free", 0
    expire = now().timestamp() + days * 86400 if days > 0 else 0
    conn = get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (
                        user_id, plan, subscription_until, warned,
                        messages_today, images_today, last_reset, created_at, last_login_at
                    )
                    VALUES (%s,%s,%s,FALSE,0,0,%s,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        plan=EXCLUDED.plan,
                        subscription_until=EXCLUDED.subscription_until,
                        warned=FALSE
                    """,
                    (str(user_id), plan, expire, today()),
                )
    finally:
        conn.close()


def save_payment(user_id, plan):
    amount = LITE_PRICE if plan == "lite" else PREMIUM_PRICE if plan == "premium" else 0
    conn = get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO payments (user_id, plan, amount) VALUES (%s,%s,%s)",
                    (str(user_id), plan, amount),
                )
    finally:
        conn.close()


def get_user_plan(user_id):
    conn = get_conn()
    if not conn:
        return "free"
    uid = str(user_id)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT plan, subscription_until FROM users WHERE user_id = %s",
                    (uid,),
                )
                user = cur.fetchone()
                if not user:
                    _ensure_user_defaults(cur, uid)
                    return "free"
                if float(user.get("subscription_until") or 0) < now().timestamp():
                    return "free"
                return str(user.get("plan") or "free")
    finally:
        conn.close()


def check_subscription(user_id):
    return get_user_plan(user_id) in {"lite", "premium"}


def should_warn(user_id):
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subscription_until, warned FROM users WHERE user_id=%s", (str(user_id),))
                user = cur.fetchone()
                if not user:
                    return False
                remaining = float(user.get("subscription_until") or 0) - now().timestamp()
                if remaining < 86400 and not bool(user.get("warned")):
                    cur.execute("UPDATE users SET warned=TRUE WHERE user_id=%s", (str(user_id),))
                    return True
                return False
    finally:
        conn.close()


def should_reset_limits(user):
    return bool(user) and str(user.get("last_reset") or "") != today()


def reset_user_limits(cur, uid):
    cur.execute(
        "UPDATE users SET messages_today=0, images_today=0, last_reset=%s WHERE user_id=%s",
        (today(), str(uid)),
    )


def can_send_message(user_id, limit=FREE_MESSAGES_LIMIT):
    if user_id == ADMIN_ID or limit == -1:
        return True
    conn = get_conn()
    if not conn:
        return True
    uid = str(user_id)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT messages_today, images_today, last_reset FROM users WHERE user_id=%s", (uid,))
                user = cur.fetchone()
                if not user:
                    _ensure_user_defaults(cur, uid)
                    return True
                if should_reset_limits(user):
                    reset_user_limits(cur, uid)
                    user["messages_today"] = 0
                if int(user.get("messages_today") or 0) >= limit:
                    return False
                cur.execute("UPDATE users SET messages_today=messages_today+1 WHERE user_id=%s", (uid,))
                return True
    finally:
        conn.close()


def can_generate_image(user_id, limit=FREE_IMAGES_LIMIT):
    if user_id == ADMIN_ID or limit == -1:
        return True
    conn = get_conn()
    if not conn:
        return True
    uid = str(user_id)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT images_today, last_reset FROM users WHERE user_id=%s", (uid,))
                user = cur.fetchone()
                if not user:
                    _ensure_user_defaults(cur, uid)
                    return True
                if should_reset_limits(user):
                    reset_user_limits(cur, uid)
                    user["images_today"] = 0
                if int(user.get("images_today") or 0) >= limit:
                    return False
                cur.execute("UPDATE users SET images_today=images_today+1 WHERE user_id=%s", (uid,))
                return True
    finally:
        conn.close()


def get_remaining_messages(user_id, limit=FREE_MESSAGES_LIMIT):
    if user_id == ADMIN_ID or limit == -1:
        return "∞"
    conn = get_conn()
    if not conn:
        return limit
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT messages_today FROM users WHERE user_id=%s", (str(user_id),))
                user = cur.fetchone()
                return max(0, limit - int((user or {}).get("messages_today") or 0))
    finally:
        conn.close()


def get_remaining_images(user_id, limit=FREE_IMAGES_LIMIT):
    if user_id == ADMIN_ID or limit == -1:
        return "∞"
    conn = get_conn()
    if not conn:
        return limit
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT images_today FROM users WHERE user_id=%s", (str(user_id),))
                user = cur.fetchone()
                return max(0, limit - int((user or {}).get("images_today") or 0))
    finally:
        conn.close()


def get_remaining_days(user_id):
    if user_id == ADMIN_ID:
        return "∞"
    conn = get_conn()
    if not conn:
        return 0
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT subscription_until FROM users WHERE user_id=%s", (str(user_id),))
                user = cur.fetchone()
                seconds = float((user or {}).get("subscription_until") or 0) - now().timestamp()
                return max(0, math.ceil(seconds / 86400))
    finally:
        conn.close()


def get_limits(user_id, msg_limit=FREE_MESSAGES_LIMIT, img_limit=FREE_IMAGES_LIMIT):
    if user_id == ADMIN_ID:
        return {"messages_used":"∞","messages_limit":"∞","images_used":"∞","images_limit":"∞"}
    msg_limit_out = "∞" if msg_limit == -1 else msg_limit
    img_limit_out = "∞" if img_limit == -1 else img_limit
    conn = get_conn()
    if not conn:
        return {"messages_used":0,"messages_limit":msg_limit_out,"images_used":0,"images_limit":img_limit_out}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT messages_today, images_today, last_reset FROM users WHERE user_id=%s", (str(user_id),))
                user = cur.fetchone()
                if not user:
                    return {"messages_used":0,"messages_limit":msg_limit_out,"images_used":0,"images_limit":img_limit_out}
                if should_reset_limits(user):
                    reset_user_limits(cur, user_id)
                    messages = images = 0
                else:
                    messages = int(user.get("messages_today") or 0)
                    images = int(user.get("images_today") or 0)
                return {"messages_used":messages,"messages_limit":msg_limit_out,"images_used":images,"images_limit":img_limit_out}
    finally:
        conn.close()


def get_admin_stats():
    conn = get_conn()
    if not conn:
        return {"users":0,"subs":0,"income_total":0,"income_today":0}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM users")
                users = int(cur.fetchone()["count"])
                cur.execute("SELECT COUNT(*) AS count FROM users WHERE plan IN ('lite','premium') AND subscription_until > %s", (now().timestamp(),))
                subs = int(cur.fetchone()["count"])
                cur.execute("SELECT COALESCE(SUM(amount),0) AS total FROM payments")
                total = int(cur.fetchone()["total"] or 0)
                cur.execute("SELECT COALESCE(SUM(amount),0) AS total FROM payments WHERE created_at::date = %s", (today(),))
                today_income = int(cur.fetchone()["total"] or 0)
                return {"users":users,"subs":subs,"income_total":total,"income_today":today_income}
    finally:
        conn.close()


def get_reset_seconds(user_id):
    current = now()
    nxt = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((nxt - current).total_seconds())


def format_time(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 3600:02}:{(seconds % 3600)//60:02}:{seconds % 60:02}"


def get_all_users():
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM users ORDER BY created_at ASC")
                return [row["user_id"] for row in cur.fetchall()]
    finally:
        conn.close()
