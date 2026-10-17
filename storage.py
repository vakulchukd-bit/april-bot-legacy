"""
APRIL PostgreSQL storage — canonical minimal persistent storage.

Persistent data policy:
  1. users     -> permanent authenticated/account/subscription state.
  2. payments  -> permanent payment history.
  3. dialogue_memory -> authenticated USER↔APRIL pairs with per-pair retention.

The retention lifetime is recorded when each pair is saved: Free = 12 hours,
Premium = 24 hours. A later plan change does not extend or shorten an existing
pair. Legacy rows default to 12 hours; rows from a currently verifiable active Premium
grant are backfilled to 24 hours on the first migration. Reads enforce expiry immediately
and a background worker physically removes expired rows approximately once a minute.
The old feedback/knowledge/memory_states stores are intentionally removed.
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import re
import secrets
import threading
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

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
PREMIUM_MEMORY_WINDOW_HOURS = 24
PREMIUM_MEMORY_WINDOW_SECONDS = PREMIUM_MEMORY_WINDOW_HOURS * 3600
PREMIUM_TEST_DURATION_HOURS = 24

_USERS_COLUMNS = (
    "user_id",
    "april_id",
    "email",
    "name",
    "provider",
    "provider_user_id",
    "plan",
    "subscription_until",
    "premium_id",
    "warned",
    "messages_today",
    "images_today",
    "last_reset",
    "created_at",
    "last_login_at",
    "last_seen_at",
)



_ALLOWED_TABLE_COLUMNS = {
    "users": set(_USERS_COLUMNS),
    # Test grants are recorded for audit, but they are explicitly not paid payments.
    "payments": {"id", "user_id", "plan", "amount", "premium_id", "payment_status", "payment_source", "created_at"},
    "dialogue_memory": {"id", "user_id", "created_at", "retention_hours", "turn_index", "user_text", "april_text", "user_text_en", "april_text_en", "language", "relation", "pair_hash", "dialog_id", "conversation_id", "message_id", "interpretation_id", "structured_request", "structured_response"},
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


def resolve_user_id(user_id: Any) -> str | None:
    """Resolve either the internal user_id or public april_id to the DB key.

    Legacy rows can have different values in these columns. Dialogue memory,
    entitlements and payments are keyed by users.user_id, so all protected paths
    must normalize to that key before reading or writing related records.
    """
    raw = str(user_id or "").strip()
    if not raw:
        return None
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = %s OR april_id = %s
                ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (raw, raw, raw),
            )
            row = cur.fetchone() or {}
            resolved = str(row.get("user_id") or "").strip()
            return resolved or None
    except Exception:
        return None
    finally:
        conn.close()


def is_authenticated_user(user_id: Any) -> bool:
    """Only a registered auth-backed row may own persistent dialogue memory.

    Accept a public April ID at the API boundary, but check the matching DB row
    rather than assuming april_id and user_id are always identical.
    """
    raw = str(user_id or "").strip()
    if not raw:
        return False
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, email, provider
                    FROM users
                    WHERE user_id = %s OR april_id = %s
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (raw, raw, raw),
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
    # Remove the obsolete binary sidecar table; dialogue_memory remains untouched.
    cur.execute("DROP TABLE IF EXISTS dialogue_assets")


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
                        premium_id TEXT,
                        warned BOOLEAN NOT NULL DEFAULT FALSE,
                        messages_today INTEGER NOT NULL DEFAULT 0,
                        images_today INTEGER NOT NULL DEFAULT 0,
                        last_reset TEXT NOT NULL DEFAULT CURRENT_DATE::TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_login_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_id TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS warned BOOLEAN DEFAULT FALSE")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS messages_today INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS images_today INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reset TEXT DEFAULT CURRENT_DATE::TEXT")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")

                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_april_id ON users(april_id) WHERE april_id IS NOT NULL AND april_id <> ''")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL AND email <> ''")
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_premium_id ON users(premium_id) WHERE premium_id IS NOT NULL AND premium_id <> ''")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS payments (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        plan TEXT NOT NULL,
                        amount INTEGER NOT NULL DEFAULT 0,
                        premium_id TEXT,
                        payment_status TEXT NOT NULL DEFAULT 'paid',
                        payment_source TEXT NOT NULL DEFAULT 'legacy',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS id BIGSERIAL")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS user_id TEXT")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS plan TEXT")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount INTEGER DEFAULT 0")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS premium_id TEXT")
                # Existing payment rows remain historical paid records. Test grants are
                # inserted explicitly as payment_status='test_grant' with amount=0.
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'paid'")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_source TEXT NOT NULL DEFAULT 'legacy'")
                cur.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_created ON payments(user_id, created_at DESC)")

                # Detect whether read receipts existed before this migration.
                # Only backfill historical rows once; never auto-clear a genuinely
                # unread message simply because the Bot process restarts later.
                cur.execute(
                    """SELECT
                         EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'admin_read_at') AS has_admin_read_at,
                         EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'user_read_at') AS has_user_read_at"""
                )
                support_read_receipts_preexisting = cur.fetchone() or {}
                had_admin_read_receipt = bool(support_read_receipts_preexisting.get("has_admin_read_at"))
                had_user_read_receipt = bool(support_read_receipts_preexisting.get("has_user_read_at"))

                # Premium support inbox. The cooldown is derived from the last
                # ticket timestamp, so it survives browser/device changes and
                # cannot be bypassed by clearing client storage.
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS premium_support_messages (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        message TEXT NOT NULL,
                        language TEXT NOT NULL DEFAULT 'en',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        admin_reply TEXT,
                        replied_at TIMESTAMPTZ,
                        admin_id TEXT,
                        image_data TEXT,
                        image_mime TEXT,
                        image_name TEXT,
                        admin_reply_language TEXT NOT NULL DEFAULT 'en'
                    )
                    """
                )
                cur.execute("ALTER TABLE premium_support_messages ADD COLUMN IF NOT EXISTS image_data TEXT")
                cur.execute("ALTER TABLE premium_support_messages ADD COLUMN IF NOT EXISTS image_mime TEXT")
                cur.execute("ALTER TABLE premium_support_messages ADD COLUMN IF NOT EXISTS image_name TEXT")
                cur.execute("ALTER TABLE premium_support_messages ADD COLUMN IF NOT EXISTS admin_reply_language TEXT NOT NULL DEFAULT 'en'")
                # One-time cleanup of the previous generic-file columns. Only image
                # data URLs are migrated; PDFs, archives and other file payloads are
                # intentionally discarded from the Premium support feature.
                cur.execute("""
                    DO $support_image_only_migration$
                    BEGIN
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'attachment_data')
                           AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'attachment_mime')
                           AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'attachment_name') THEN
                            EXECUTE $migrate_images$
                                UPDATE premium_support_messages
                                SET image_data = COALESCE(image_data, attachment_data),
                                    image_mime = COALESCE(image_mime, attachment_mime),
                                    image_name = COALESCE(image_name, attachment_name)
                                WHERE image_data IS NULL
                                  AND LOWER(COALESCE(attachment_mime, '')) IN ('image/jpeg', 'image/png', 'image/webp')
                                  AND LOWER(COALESCE(attachment_data, '')) LIKE 'data:image/%'
                            $migrate_images$;
                        END IF;
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'attachment_data') THEN
                            ALTER TABLE premium_support_messages DROP COLUMN attachment_data;
                        END IF;
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'attachment_mime') THEN
                            ALTER TABLE premium_support_messages DROP COLUMN attachment_mime;
                        END IF;
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'premium_support_messages' AND column_name = 'attachment_name') THEN
                            ALTER TABLE premium_support_messages DROP COLUMN attachment_name;
                        END IF;
                    END
                    $support_image_only_migration$
                """)
                # Each administrator reply/addition is an independent text/image
                # event tied to the original Premium request. Legacy summary fields
                # remain for older clients and existing text-only records.
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS premium_support_replies (
                        id BIGSERIAL PRIMARY KEY,
                        support_message_id BIGINT NOT NULL REFERENCES premium_support_messages(id) ON DELETE CASCADE,
                        reply TEXT NOT NULL DEFAULT '',
                        reply_language TEXT NOT NULL DEFAULT 'en',
                        admin_id TEXT,
                        image_data TEXT,
                        image_mime TEXT,
                        image_name TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute("ALTER TABLE premium_support_replies ADD COLUMN IF NOT EXISTS image_data TEXT")
                cur.execute("ALTER TABLE premium_support_replies ADD COLUMN IF NOT EXISTS image_mime TEXT")
                cur.execute("ALTER TABLE premium_support_replies ADD COLUMN IF NOT EXISTS image_name TEXT")
                cur.execute("ALTER TABLE premium_support_replies ALTER COLUMN reply SET DEFAULT ''")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_premium_support_replies_message ON premium_support_replies(support_message_id, created_at, id)")
                # Read receipts are per side: opening a ticket clears only the
                # corresponding badge. Existing tickets are treated as already
                # seen on the admin side to avoid false unread badges after deploy.
                cur.execute("ALTER TABLE premium_support_messages ADD COLUMN IF NOT EXISTS admin_read_at TIMESTAMPTZ")
                cur.execute("ALTER TABLE premium_support_messages ADD COLUMN IF NOT EXISTS user_read_at TIMESTAMPTZ")
                if not had_admin_read_receipt:
                    cur.execute("UPDATE premium_support_messages SET admin_read_at = created_at WHERE admin_read_at IS NULL")
                if not had_user_read_receipt:
                    cur.execute("UPDATE premium_support_messages SET user_read_at = COALESCE(replied_at, created_at) WHERE user_read_at IS NULL")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_premium_support_user_created ON premium_support_messages(user_id, created_at DESC)")
                cur.execute("DROP INDEX IF EXISTS idx_premium_support_pending")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_premium_support_pending ON premium_support_messages(created_at ASC) WHERE replied_at IS NULL AND admin_reply IS NULL")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_premium_support_admin_unread ON premium_support_messages(admin_read_at, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_premium_support_user_unread ON premium_support_messages(user_id, user_read_at, replied_at DESC)")

                # Detect first-time retention migration before CREATE/ALTER adds the field.
                # This lets us backfill currently-verifiable Premium rows once instead of
                # running a correlated update on every request (init_db is called by both executors).
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = 'dialogue_memory'
                          AND column_name = 'retention_hours'
                    ) AS has_retention_hours
                    """
                )
                retention_column_preexisting = bool((cur.fetchone() or {}).get("has_retention_hours"))

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dialogue_memory (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        retention_hours INTEGER NOT NULL DEFAULT 12,
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
                # Retention is attached to each saved pair, not to the user's
                # current plan. Existing rows deliberately default to Free's 12h.
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS retention_hours INTEGER NOT NULL DEFAULT 12")
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

                # Backfill once, only when this deployment first adds retention_hours.
                # Current Premium rows can be identified from the canonical payments ledger;
                # all other historical rows keep the migration default of 12 hours.
                if not retention_column_preexisting:
                    cur.execute(
                        """
                        UPDATE dialogue_memory AS d
                        SET retention_hours = 24
                        FROM users AS u
                        WHERE u.user_id = d.user_id
                          AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                          AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                          AND d.retention_hours = 12
                          AND d.created_at >= (
                              SELECT MAX(p.created_at)
                              FROM payments AS p
                              WHERE p.user_id = d.user_id
                                AND LOWER(COALESCE(p.plan, '')) = 'premium'
                                AND LOWER(COALESCE(p.payment_status, '')) IN ('paid', 'test_grant')
                          )
                          AND d.created_at <= to_timestamp(u.subscription_until)
                        """
                    )

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
                # Every pair expires relative to its own created_at and saved
                # retention_hours. Reads enforce the same deadline immediately;
                # this worker physically removes expired rows within ~5 minutes.
                time.sleep(60.0)
                expired_subscriptions = expire_subscriptions_utc()
                deleted = cleanup_dialogue_memory_utc()
                if expired_subscriptions:
                    print(f"STATE: UTC SUBSCRIPTION EXPIRY switched_to_free={expired_subscriptions}")
                if deleted:
                    print(f"STATE: PER-MESSAGE DIALOGUE RETENTION CLEANUP removed={deleted}")
            except Exception as exc:
                print(f"STATE: UTC DIALOGUE CLEANUP ERROR: {exc}")
                time.sleep(60.0)

    threading.Thread(target=worker, name="april-dialogue-utc-cleanup", daemon=True).start()


def cleanup_dialogue_memory_utc(user_id: Any | None = None, timestamp: float | int | datetime | None = None) -> int:
    """Expire per-message memory; active Premium rows retain the full 24-hour window.

    This backfills the retention field for still-live rows when a previously 12-hour
    user becomes Premium or a deployment changes the plan without recreating the
    retention column. It is conditional on active Premium entitlement and therefore
    does not extend Free accounts' 12-hour memory.
    """
    conn = get_conn()
    if not conn:
        return 0
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc) if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    expired_pairs: list[tuple[str, str]] = []
    try:
        with conn:
            with conn.cursor() as cur:
                # Preserve all still-live history for an active Premium user for
                # 24 hours even when those rows were written before the Premium
                # retention policy was applied. Do not revive already-expired rows.
                if user_id is None:
                    cur.execute(
                        """UPDATE dialogue_memory AS d
                           SET retention_hours = 24
                           FROM users AS u
                           WHERE u.user_id = d.user_id
                             AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                             AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM %s)
                             AND COALESCE(d.retention_hours, 12) < 24
                             AND d.created_at + INTERVAL '24 hours' > %s
                             AND d.created_at <= %s""",
                        (current, current, current),
                    )
                else:
                    uid = str(user_id)
                    if not _is_authenticated_cursor(cur, uid):
                        return 0
                    cur.execute(
                        """UPDATE dialogue_memory AS d
                           SET retention_hours = 24
                           FROM users AS u
                           WHERE d.user_id = %s
                             AND u.user_id = d.user_id
                             AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                             AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM %s)
                             AND COALESCE(d.retention_hours, 12) < 24
                             AND d.created_at + INTERVAL '24 hours' > %s
                             AND d.created_at <= %s""",
                        (uid, current, current, current),
                    )
                if user_id is None:
                    cur.execute(
                        """SELECT user_id, message_id FROM dialogue_memory AS d
                           WHERE d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (current,),
                    )
                else:
                    uid = str(user_id)
                    if not _is_authenticated_cursor(cur, uid):
                        return 0
                    cur.execute(
                        """SELECT user_id, message_id FROM dialogue_memory AS d
                           WHERE d.user_id = %s
                             AND d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (uid, current),
                    )
                expired_pairs = [
                    (str(row.get("user_id") or ""), str(row.get("message_id") or ""))
                    for row in cur.fetchall()
                    if str(row.get("user_id") or "").strip() and str(row.get("message_id") or "").strip()
                ]
                if user_id is None:
                    cur.execute(
                        """DELETE FROM dialogue_memory AS d
                           WHERE d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (current,),
                    )
                else:
                    cur.execute(
                        """DELETE FROM dialogue_memory AS d
                           WHERE d.user_id = %s
                             AND d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (str(user_id), current),
                    )
                deleted = int(cur.rowcount or 0)
        # Remove physical files only after the database transaction commits.
        # Import lazily so Free's normal storage startup does not depend on Premium.
        if expired_pairs:
            try:
                from blocks.premium_asset_store import delete_message_assets
                for expired_uid, expired_mid in expired_pairs:
                    delete_message_assets(expired_uid, expired_mid)
            except Exception as exc:
                print(f"STATE: PREMIUM ASSET CLEANUP ERROR: {exc}")
        return deleted
    except psycopg2.errors.UndefinedTable:
        return 0
    finally:
        conn.close()


def expire_subscriptions_utc(timestamp: float | int | datetime | None = None) -> int:
    """Persist expired timed entitlements as Free, while retaining Premium ID."""
    conn = get_conn()
    if not conn:
        return 0
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc) if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE users SET plan = 'free'
                       WHERE LOWER(COALESCE(plan, 'free')) IN ('lite', 'premium')
                         AND COALESCE(subscription_until, 0) <= %s""",
                    (current.timestamp(),),
                )
                return int(cur.rowcount or 0)
    except psycopg2.errors.UndefinedTable:
        return 0
    finally:
        conn.close()


def cleanup_premium_dialogue_memory_utc(timestamp: float | int | datetime | None = None) -> int:
    """Backward-compatible alias for the canonical per-row expiry cleanup."""
    return cleanup_dialogue_memory_utc(timestamp=timestamp)


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
    retention_hours: int = DIALOGUE_WINDOW_HOURS,
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
                # Purge against wall-clock now, not the browser's send timestamp.
                # The new pair still keeps the validated send timestamp as created_at.
                cleanup_now = now()
                cur.execute(
                    "SELECT LOWER(COALESCE(plan, 'free')) AS plan, COALESCE(subscription_until, 0) AS subscription_until FROM users WHERE user_id = %s",
                    (uid,),
                )
                plan_row = cur.fetchone() or {}
                active_premium = (
                    str(plan_row.get("plan") or "free").lower() == "premium"
                    and float(plan_row.get("subscription_until") or 0) > cleanup_now.timestamp()
                ) if isinstance(plan_row, dict) else False
                if active_premium:
                    # Rows written by a previous 12-hour path may still be live
                    # under the Premium 24-hour entitlement; promote before pruning.
                    cur.execute(
                        """UPDATE dialogue_memory AS d SET retention_hours = 24
                           WHERE d.user_id = %s
                             AND COALESCE(d.retention_hours, 12) < 24
                             AND d.created_at + INTERVAL '24 hours' > %s
                             AND d.created_at <= %s""",
                        (uid, cleanup_now, cleanup_now),
                    )
                cur.execute(
                    """DELETE FROM dialogue_memory AS d
                       WHERE d.user_id = %s
                         AND d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                    (uid, cleanup_now),
                )
                row_retention_hours = 24 if active_premium or int(retention_hours or DIALOGUE_WINDOW_HOURS) >= 24 else 12
                pair_hash = _pair_hash(uid, created_ts, int(turn_index or 0), user_value, april_value)
                cur.execute(
                    """
                    INSERT INTO dialogue_memory
                        (user_id, created_at, retention_hours, turn_index, user_text, april_text, user_text_en, april_text_en, language, relation, pair_hash, dialog_id, conversation_id, message_id, interpretation_id, structured_request, structured_response)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    ON CONFLICT (pair_hash) DO UPDATE SET
                        user_text_en = EXCLUDED.user_text_en,
                        april_text_en = EXCLUDED.april_text_en,
                        structured_request = EXCLUDED.structured_request,
                        structured_response = EXCLUDED.structured_response,
                        interpretation_id = EXCLUDED.interpretation_id
                    """,
                    (
                        uid, dt, row_retention_hours, int(turn_index or 0), user_value, april_value,
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
    """Load authenticated dialogue pairs whose own saved retention has not elapsed."""
    uid = str(user_id)
    conn = get_conn()
    if not conn:
        return []
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc) if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    try:
        with conn:
            with conn.cursor() as cur:
                if not _is_authenticated_cursor(cur, uid):
                    return []
                cur.execute(
                    """
                    SELECT id, user_id, created_at, retention_hours, turn_index, user_text, april_text, user_text_en, april_text_en,
                           language, relation, dialog_id, conversation_id, message_id, interpretation_id,
                           structured_request, structured_response
                    FROM dialogue_memory
                    WHERE user_id = %s
                      AND created_at <= %s
                      AND created_at + (GREATEST(12, LEAST(24, COALESCE(retention_hours, 12))) * INTERVAL '1 hour') > %s
                    ORDER BY created_at ASC, turn_index ASC, id ASC
                    """,
                    (uid, current, current),
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


def load_dialogue_history_index(
    user_id: Any,
    *,
    timestamp: float | int | datetime | None = None,
) -> dict[str, Any] | None:
    """Load the small history-list index without fetching large structured payloads.

    The full ``structured_request`` / ``structured_response`` JSON can contain
    expensive scene, table, graph and image metadata. The history screen only
    needs short labels and message identity, so this query intentionally selects
    only list fields and bounds the index scan to the maximum 24-hour retention.

    Returns None when storage is unavailable, ``authenticated=False`` for an
    unknown/unverified account, or the active plan and lightweight rows.
    """
    raw_uid = str(user_id or "").strip()
    if not raw_uid:
        return {"authenticated": False}
    conn = get_conn()
    if not conn:
        return None
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc)
        if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    try:
        with conn:
            with conn.cursor() as cur:
                # Resolve public April ID/internal user_id and entitlement with one
                # indexed account lookup instead of separate auth/plan round-trips.
                cur.execute(
                    """
                    SELECT user_id, april_id, email, provider, plan, subscription_until
                    FROM users
                    WHERE user_id = %s OR april_id = %s
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (raw_uid, raw_uid, raw_uid),
                )
                account = cur.fetchone()
                if not _is_authenticated_row(account):
                    return {"authenticated": False}

                uid = str(account.get("user_id") or raw_uid).strip()
                raw_plan = str(account.get("plan") or "free").strip().lower()
                expiry = float(account.get("subscription_until") or 0)
                plan = raw_plan if raw_plan in {"lite", "premium"} and expiry > current.timestamp() else "free"
                if raw_plan in {"lite", "premium"} and plan == "free":
                    cur.execute(
                        "UPDATE users SET plan = 'free' WHERE user_id = %s AND plan = %s",
                        (uid, raw_plan),
                    )

                # Retain the existing Premium rule: when an account is actively
                # Premium, extend still-retained candidates to 24 h, but never
                # revive anything older than the maximum 24-hour window.
                if plan == "premium":
                    cur.execute(
                        """
                        UPDATE dialogue_memory
                        SET retention_hours = 24
                        WHERE user_id = %s
                          AND COALESCE(retention_hours, 12) < 24
                          AND created_at <= %s
                          AND created_at > %s - INTERVAL '24 hours'
                          AND created_at + INTERVAL '24 hours' > %s
                        """,
                        (uid, current, current, current),
                    )

                # The explicit 24-hour lower bound allows the existing
                # (user_id, created_at DESC) index to limit work before checking
                # each row's saved 12/24-hour expiry.
                cur.execute(
                    """
                    SELECT
                        id,
                        COALESCE(NULLIF(BTRIM(message_id), ''), 'legacy-memory-' || id::text) AS message_id,
                        user_id,
                        dialog_id,
                        conversation_id,
                        COALESCE(
                            NULLIF(BTRIM(structured_request #>> '{goal}'), ''),
                            NULLIF(BTRIM(structured_request #>> '{intent,user_goal}'), ''),
                            NULLIF(BTRIM(structured_request #>> '{intent,goal}'), ''),
                            NULLIF(BTRIM(structured_request #>> '{request_structure,user_goal}'), ''),
                            NULLIF(LEFT(BTRIM(user_text), 140), ''),
                            'Сохранённый диалог'
                        ) AS title,
                        COALESCE(
                            NULLIF(BTRIM(structured_response #>> '{dialogue_memory_record,topic}'), ''),
                            NULLIF(BTRIM(structured_response #>> '{metadata,dialogue_memory_record,topic}'), ''),
                            NULLIF(BTRIM(structured_request #>> '{dialogue,continuation_context,active_topic}'), ''),
                            NULLIF(BTRIM(structured_request #>> '{request_structure,user_goal}'), ''),
                            NULLIF(LEFT(BTRIM(user_text), 140), ''),
                            'Сохранённый диалог'
                        ) AS topic_label,
                        relation,
                        LEFT(COALESCE(user_text, ''), 1200) AS user_text,
                        LEFT(COALESCE(april_text, ''), 1000) AS april_text,
                        EXTRACT(EPOCH FROM created_at) AS created_at,
                        turn_index
                    FROM dialogue_memory
                    WHERE user_id = %s
                      AND created_at <= %s
                      AND created_at > %s - INTERVAL '24 hours'
                      AND created_at + (
                          GREATEST(12, LEAST(24, COALESCE(retention_hours, 12)))
                          * INTERVAL '1 hour'
                      ) > %s
                    ORDER BY created_at ASC, turn_index ASC, id ASC
                    """,
                    (uid, current, current, current),
                )
                rows = []
                for source in cur.fetchall():
                    row = dict(source)
                    row["id"] = str(row.get("message_id") or row.get("id") or "")
                    row["message_id"] = str(row.get("message_id") or "")
                    row["user_id"] = str(row.get("user_id") or uid)
                    row["dialog_id"] = str(row.get("dialog_id") or "")
                    row["conversation_id"] = str(row.get("conversation_id") or "")
                    row["title"] = str(row.get("title") or row.get("user_text") or "Сохранённый диалог")
                    row["topic_label"] = str(row.get("topic_label") or row.get("title") or row.get("user_text") or "Сохранённый диалог")
                    row["relation"] = str(row.get("relation") or "")
                    row["user_text"] = str(row.get("user_text") or "")
                    row["april_text"] = str(row.get("april_text") or "")
                    row["created_at"] = float(row.get("created_at") or 0.0)
                    row["turn_index"] = int(row.get("turn_index") or 0)
                    rows.append(row)
                return {
                    "authenticated": True,
                    "user_id": uid,
                    "plan": plan,
                    "window_hours": 24 if plan == "premium" else 12,
                    "rows": rows,
                }
    except psycopg2.errors.UndefinedTable:
        return None
    finally:
        conn.close()



def load_dialogue_history_details(
    user_id: Any,
    message_ids: list[str],
    *,
    timestamp: float | int | datetime | None = None,
) -> list[dict[str, Any]]:
    """Load heavyweight dialogue payloads only for selected, retained memory pairs.

    History listing and topic matching use ``load_dialogue_history_index``. This
    function is the second-stage read for the chosen topic and intentionally
    fetches JSONB scene/render payloads only for the selected message IDs.
    """
    uid = str(user_id or "").strip()
    ids = list(dict.fromkeys(str(value or "").strip() for value in (message_ids or []) if str(value or "").strip()))
    if not uid or not ids:
        return []
    conn = get_conn()
    if not conn:
        return []
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc)
        if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    try:
        with conn:
            with conn.cursor() as cur:
                if not _is_authenticated_cursor(cur, uid):
                    return []
                cur.execute(
                    """
                    SELECT id, user_id, created_at, retention_hours, turn_index,
                           user_text, april_text, user_text_en, april_text_en,
                           language, relation, dialog_id, conversation_id,
                           message_id, interpretation_id,
                           structured_request, structured_response
                    FROM dialogue_memory
                    WHERE user_id = %s
                      AND created_at <= %s
                      AND created_at > %s - INTERVAL '24 hours'
                      AND created_at + (
                          GREATEST(12, LEAST(24, COALESCE(retention_hours, 12)))
                          * INTERVAL '1 hour'
                      ) > %s
                      AND (
                          message_id = ANY(%s)
                          OR ('legacy-memory-' || id::text) = ANY(%s)
                      )
                    ORDER BY created_at ASC, turn_index ASC, id ASC
                    """,
                    (uid, current, current, current, ids, ids),
                )
                rows = [dict(row) for row in cur.fetchall()]
                for row in rows:
                    created = row.get("created_at")
                    if isinstance(created, datetime):
                        row["created_at"] = created.astimezone(timezone.utc).timestamp()
                    elif row.get("created_at") is not None:
                        row["created_at"] = float(row["created_at"])
                    row["message_id"] = str(row.get("message_id") or f"legacy-memory-{row.get('id')}")
                return rows
    except psycopg2.errors.UndefinedTable:
        return []
    finally:
        conn.close()


def search_dialogue_memory(user_id: Any, query: str, *, limit: int = 8) -> dict[str, Any]:
    """Compatibility adapter that delegates dialogue retrieval to State Manager.

    This function remains available for legacy callers, but it has no parallel
    ranking algorithm and never queries a separate dialogue table.
    """
    from blocks.state_manager import get_dialogue_pairs, search_dialogue_context

    result = search_dialogue_context(user_id, query, limit=max(1, int(limit or 8)))
    candidates = result.get("matches") if isinstance(result, dict) else []
    # search_dialogue_context has hydrated the canonical store; recover structured
    # JSON fields from that same in-memory snapshot without a second DB query.
    rows_by_message = {
        str(row.get("message_id") or ""): row
        for row in get_dialogue_pairs(user_id)
        if isinstance(row, dict) and str(row.get("message_id") or "")
    }
    matches = []
    for item in candidates or []:
        if not isinstance(item, dict):
            continue
        source_row = rows_by_message.get(str(item.get("message_id") or ""), {})
        matches.append({
            "score": round(float(item.get("score") or 0.0), 6),
            "turn_index": int(item.get("turn_index") or 0),
            "created_at": float(item.get("created_at") or 0.0),
            "user": str(item.get("user") or ""),
            "april": str(item.get("april") or ""),
            "user_text_en": str(item.get("user_en") or ""),
            "april_text_en": str(item.get("april_en") or ""),
            "structured_request": source_row.get("structured_request") or {},
            "structured_response": source_row.get("structured_response") or {},
            "message_id": str(item.get("message_id") or ""),
            "dialog_id": str(item.get("dialog_id") or ""),
            "conversation_id": str(item.get("conversation_id") or ""),
        })
    total_pairs = int(result.get("total_pairs") or 0) if isinstance(result, dict) else 0
    return {
        "engine": str(result.get("engine") or "state_manager_topic_section_search_v6_recovery"),
        "authenticated": (
            bool(result.get("authenticated")) if total_pairs > 0
            else bool(is_authenticated_user(user_id))
        ),
        "window_hours": int(result.get("window_hours") or DIALOGUE_WINDOW_HOURS),
        "seed_hours": DIALOGUE_SEED_HOURS,
        "query": str(query or ""),
        "total_pairs": total_pairs,
        "relation": str(result.get("relation") or "NEW"),
        "reason": str(result.get("reason") or ""),
        "matches": matches,
    }


# =========================================================
# USER / SUBSCRIPTION / PAYMENTS API
# =========================================================

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
    """Create or restore an account only when the trusted provider identity matches."""
    normalized_email = str(email or "").strip().lower()
    normalized_provider = str(provider or "").strip().lower()
    incoming_provider_id = str(provider_user_id or "").strip()
    if not normalized_email or "@" not in normalized_email:
        return None
    if normalized_provider != "google" or not incoming_provider_id:
        return None

    existing = find_user_by_email(normalized_email)
    if existing:
        stored_provider = str(existing.get("provider") or "").strip().lower()
        stored_provider_id = str(existing.get("provider_user_id") or "").strip()
        # Never attach another provider identity to an existing email row.
        if stored_provider != normalized_provider:
            return None
        if stored_provider_id and stored_provider_id != incoming_provider_id:
            return None
        if not stored_provider_id:
            conn = get_conn()
            if not conn:
                return None
            try:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """UPDATE users SET provider_user_id = %s
                               WHERE user_id = %s AND LOWER(provider) = %s
                                 AND (provider_user_id IS NULL OR provider_user_id = '')""",
                            (incoming_provider_id, str(existing.get("user_id") or ""), normalized_provider),
                        )
                existing = find_user_by_email(normalized_email)
                if not existing or str(existing.get("provider_user_id") or "").strip() != incoming_provider_id:
                    return None
            finally:
                conn.close()
        update_last_login(existing["user_id"])
        return existing

    return create_user(
        email=normalized_email,
        name=name,
        provider=normalized_provider,
        provider_user_id=incoming_provider_id,
    )



def delete_april_account(user_id: Any) -> dict[str, Any]:
    """Delete all April-side data linked to an authenticated account.

    The lookup starts from the trusted April ID forwarded by April Web. We then
    close over every identity value stored on the matched users row(s): internal
    user_id, public april_id, Google provider_user_id, email and Premium ID.
    Those aliases are used to remove legacy rows and file sidecars as well.
    Google itself is never contacted and the user's Google account is untouched.
    """
    raw = str(user_id or "").strip()
    if not raw:
        return {"success": False, "error": "USER_ID_REQUIRED"}

    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}

    try:
        identity_rows: dict[str, dict[str, Any]] = {}
        owner_ids: set[str] = {raw}
        email_ids: set[str] = set()
        provider_ids: set[str] = set()
        premium_ids: set[str] = set()

        def absorb_identity(row: dict[str, Any]) -> bool:
            """Add one linked account row and all of its identity aliases."""
            changed = False
            canonical = str(row.get("user_id") or "").strip()
            if canonical and canonical not in identity_rows:
                identity_rows[canonical] = dict(row)
                changed = True
            aliases = (
                (owner_ids, row.get("user_id")),
                (owner_ids, row.get("april_id")),
                (owner_ids, row.get("provider_user_id")),
                (owner_ids, row.get("email")),
                (owner_ids, row.get("premium_id")),
                (email_ids, str(row.get("email") or "").strip().lower()),
                (provider_ids, row.get("provider_user_id")),
                (premium_ids, row.get("premium_id")),
            )
            for target, value in aliases:
                normalized = str(value or "").strip()
                if target is email_ids:
                    normalized = normalized.lower()
                if normalized and normalized not in target:
                    target.add(normalized)
                    changed = True
            return changed

        with conn:
            with conn.cursor() as cur:
                # Resolve the signed-in account first. Do not delete by email or
                # Google ID supplied by the client; the starting value must be a
                # known April identity from the trusted server-to-server header.
                cur.execute(
                    """
                    SELECT user_id, april_id, email, provider, provider_user_id, premium_id
                    FROM users
                    WHERE user_id = %s OR april_id = %s
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (raw, raw, raw),
                )
                primary_row = cur.fetchone()
                if not primary_row:
                    return {"success": False, "error": "ACCOUNT_NOT_FOUND"}
                if not _is_authenticated_row(primary_row):
                    return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
                absorb_identity(dict(primary_row))

                # Follow identity links until no additional user row is found.
                # This also removes legacy duplicate registry rows, should an old
                # deployment have stored the same Google identity under more than
                # one April ID. The loop is bounded to fail closed on bad data.
                for _ in range(20):
                    before = (
                        len(identity_rows), len(owner_ids), len(email_ids),
                        len(provider_ids), len(premium_ids),
                    )
                    cur.execute(
                        """
                        SELECT user_id, april_id, email, provider, provider_user_id, premium_id
                        FROM users
                        WHERE user_id = ANY(%s)
                           OR april_id = ANY(%s)
                           OR LOWER(COALESCE(email, '')) = ANY(%s)
                           OR provider_user_id = ANY(%s)
                           OR premium_id = ANY(%s)
                        FOR UPDATE
                        """,
                        (
                            list(owner_ids), list(owner_ids), list(email_ids),
                            list(provider_ids), list(premium_ids),
                        ),
                    )
                    for linked_row in cur.fetchall():
                        absorb_identity(dict(linked_row))
                    after = (
                        len(identity_rows), len(owner_ids), len(email_ids),
                        len(provider_ids), len(premium_ids),
                    )
                    if after == before:
                        break
                else:
                    raise RuntimeError("APRIL_ACCOUNT_IDENTITY_GRAPH_TOO_LARGE")

                # All IDs remain internal to this transaction. These include the
                # Google provider ID and email only as aliases inside April; no
                # request is made to Google, and no Google-side data is changed.
                account_ids = sorted(owner_ids)
                all_user_ids = sorted(
                    value for value in {
                        str(row.get("user_id") or "").strip()
                        for row in identity_rows.values()
                    } if value
                )
                premium_id_values = sorted(premium_ids)

                # Remove disk-backed Premium uploads/generated assets for every
                # known alias before committing removal of the corresponding rows.
                # If any deletion fails, the account row remains for a safe retry.
                try:
                    from blocks.premium_asset_store import delete_user_assets
                    for asset_owner_id in account_ids:
                        if not delete_user_assets(asset_owner_id):
                            return {"success": False, "error": "ACCOUNT_ASSETS_DELETE_FAILED"}
                except Exception as exc:
                    print(
                        f"[APRIL_ACCOUNT_DELETE] ASSET_CLEANUP_FAILED type={type(exc).__name__}",
                        flush=True,
                    )
                    return {"success": False, "error": "ACCOUNT_ASSETS_DELETE_FAILED"}

                # Every saved prompt/answer, dialogue and interpretation ID, and
                # structured_request/structured_response (formulas, tables, charts,
                # render contracts and metadata) lives on these owner rows. Delete
                # expired and live rows alike; the 12/24-hour TTL does not apply to
                # a deliberate account deletion.
                cur.execute(
                    "DELETE FROM dialogue_memory WHERE user_id = ANY(%s)",
                    (account_ids,),
                )
                dialogue_rows = int(cur.rowcount or 0)

                # Remove all account-side payment/entitlement records, including
                # legacy rows keyed by an alias and rows tied to a Premium ID.
                cur.execute(
                    """
                    DELETE FROM payments
                    WHERE user_id = ANY(%s)
                       OR premium_id = ANY(%s)
                    """,
                    (account_ids, premium_id_values),
                )
                payment_rows = int(cur.rowcount or 0)

                # Deleting every linked registry row removes April IDs, Google
                # provider mappings, emails, Premium IDs and subscription state.
                cur.execute(
                    "DELETE FROM users WHERE user_id = ANY(%s)",
                    (all_user_ids,),
                )
                user_rows = int(cur.rowcount or 0)
                if user_rows != len(all_user_ids):
                    raise RuntimeError("APRIL_ACCOUNT_DELETE_ROW_COUNT_MISMATCH")

        # PostgreSQL has committed. Drop Free and Premium process-local dialogue
        # snapshots too, so the deleted structured memory is not retained in RAM.
        cache_entries_removed = 0
        try:
            from blocks.state_manager import purge_user_state as purge_free_state
            from blocks.Premium_state_manager import purge_user_state as purge_premium_state
            cache_entries_removed += int(purge_free_state(account_ids) or 0)
            cache_entries_removed += int(purge_premium_state(account_ids) or 0)
        except Exception as exc:
            # The database is already deleted; normal reads still require a live
            # users row, but log cache invalidation failures for operational review.
            print(
                f"[APRIL_ACCOUNT_DELETE] CACHE_PURGE_FAILED type={type(exc).__name__}",
                flush=True,
            )

        return {
            "success": True,
            "deleted": True,
            "deleted_user_rows": user_rows,
            "deleted_dialogue_rows": dialogue_rows,
            "deleted_payment_rows": payment_rows,
            "checked_asset_owner_ids": len(account_ids),
            "purged_dialogue_cache_entries": cache_entries_removed,
            "google_account_deleted": False,
        }
    except Exception as exc:
        print(f"[APRIL_ACCOUNT_DELETE] FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "ACCOUNT_DELETE_FAILED"}
    finally:
        conn.close()

def set_subscription(user_id, plan="premium"):
    # Legacy/public April IDs are accepted at entry points, but the canonical
    # subscription row is always keyed by users.user_id.
    resolved_user_id = resolve_user_id(user_id)
    user_id = resolved_user_id or str(user_id or "").strip()
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
    user_id = resolve_user_id(user_id) or str(user_id or "").strip()
    conn = get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT premium_id FROM users WHERE user_id = %s",
                    (str(user_id),),
                )
                user = cur.fetchone() or {}
                premium_id = str(user.get("premium_id") or "").strip() or None
                cur.execute(
                    """
                    INSERT INTO payments
                        (user_id, plan, amount, premium_id, payment_status, payment_source)
                    VALUES (%s, %s, %s, %s, 'paid', 'provider')
                    """,
                    (str(user_id), plan, amount, premium_id),
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
                    """
                    SELECT user_id, plan, subscription_until
                    FROM users
                    WHERE user_id = %s OR april_id = %s
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (uid, uid, uid),
                )
                user = cur.fetchone()
                if not user:
                    _ensure_user_defaults(cur, uid)
                    return "free"
                uid = str(user.get("user_id") or uid).strip()
                plan = str(user.get("plan") or "free").strip().lower()
                expires_at = float(user.get("subscription_until") or 0)
                current_seconds = now().timestamp()
                if plan in {"lite", "premium"} and expires_at <= current_seconds:
                    cur.execute(
                        "UPDATE users SET plan = 'free' WHERE user_id = %s AND plan = %s",
                        (uid, plan),
                    )
                    return "free"
                # Entitlements are determined by the database, never by the
                # client-supplied `package` field or an unrecognized DB value.
                return plan if plan in {"lite", "premium"} else "free"
    finally:
        conn.close()


def get_user_subscription_status(user_id):
    """Return the database-backed entitlement details for an authenticated account.

    Timestamps in storage are Unix seconds. The Web profile contract converts the
    expiry to milliseconds because it compares it with Date.now(). Test activation
    writes an auditable zero-value ``test_grant`` row to ``payments``; that row is
    explicitly excluded from paid-payment history and never grants access by itself.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return None
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, april_id, email, provider, plan, subscription_until, premium_id
                    FROM users
                    WHERE user_id = %s OR april_id = %s
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                    LIMIT 1
                    """,
                    (uid, uid, uid),
                )
                user = cur.fetchone()
                if not _is_authenticated_row(user):
                    return None
                # All linked records use the internal user_id as their key.
                uid = str(user.get("user_id") or uid).strip()

                now_seconds = now().timestamp()
                until_seconds = float(user.get("subscription_until") or 0)
                raw_plan = str(user.get("plan") or "free").strip().lower()
                plan = raw_plan if raw_plan in {"lite", "premium"} and until_seconds > now_seconds else "free"
                if raw_plan in {"lite", "premium"} and plan == "free":
                    cur.execute("UPDATE users SET plan = 'free' WHERE user_id = %s", (uid,))

                # A payment-history flag counts only paid transactions. Test-grant
                # audit rows are intentionally excluded and never grant access by themselves.
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM payments WHERE user_id = %s AND plan = 'premium' AND payment_status = 'paid') AS found",
                    (uid,),
                )
                history_row = cur.fetchone() or {}
                has_premium_history = bool(history_row.get("found"))

                return {
                    "user_id": uid,
                    "april_id": str(user.get("april_id") or uid),
                    "premium_id": str(user.get("premium_id") or "") or None,
                    "plan": plan,
                    "subscription_until": int(until_seconds * 1000) if plan in {"lite", "premium"} else None,
                    "remaining_seconds": max(0, int(until_seconds - now_seconds)) if plan in {"lite", "premium"} else 0,
                    "has_premium_history": has_premium_history,
                }
    finally:
        conn.close()


SUPPORT_COOLDOWN_SECONDS = 24 * 60 * 60


def _support_time_ms(value: Any) -> int | None:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            stamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return int(stamp.timestamp() * 1000)
        return int(float(value) * 1000)
    except (TypeError, ValueError, OverflowError):
        return None


def _support_message_payload(
    row: dict[str, Any] | None,
    *,
    include_identity: bool = False,
    include_image: bool = True,
) -> dict[str, Any] | None:
    """Shape a Premium support request; its optional media is an image only.

    Optional media is image-only. Legacy generic-file columns, if present during
    upgrade, are migrated selectively and removed by init_db().
    """
    if not row:
        return None
    raw_image_data = str(row.get("image_data") or "")
    raw_image_mime = str(row.get("image_mime") or "").strip().lower().split(";", 1)[0]
    has_image = raw_image_mime in {"image/jpeg", "image/png", "image/webp"} and (
        "image_data" not in row or raw_image_data.lower().startswith(f"data:{raw_image_mime};base64,")
    )
    result = {
        "id": int(row.get("id") or 0),
        "message": str(row.get("message") or ""),
        "language": str(row.get("language") or "en"),
        "created_at_ms": _support_time_ms(row.get("created_at")),
        "admin_reply": str(row.get("admin_reply") or "") or None,
        "has_admin_reply": bool(row.get("has_admin_reply") or row.get("admin_reply")),
        "replied_at_ms": _support_time_ms(row.get("replied_at")),
        "image_mime": raw_image_mime if has_image else None,
        "image_name": str(row.get("image_name") or "") or None if has_image else None,
        "admin_reply_language": (str(row.get("admin_reply_language") or "en").strip().lower() if row.get("admin_reply") else None),
        "has_image": bool(has_image),
        "admin_read_at_ms": _support_time_ms(row.get("admin_read_at")),
        "user_read_at_ms": _support_time_ms(row.get("user_read_at")),
        "admin_unread": row.get("admin_read_at") is None,
        "user_unread": bool(row.get("has_admin_reply") or row.get("admin_reply")) and row.get("user_read_at") is None,
    }
    if include_image:
        result["image_data"] = raw_image_data if has_image and raw_image_data.lower().startswith("data:image/") else None
    if include_identity:
        result.update({
            "user_id": str(row.get("user_id") or ""),
            "april_id": str(row.get("april_id") or ""),
            "name": str(row.get("name") or ""),
            "email": str(row.get("email") or ""),
            "active_premium": bool(row.get("active_premium")),
        })
    return result

def _support_resolve_user(raw: str) -> dict[str, Any] | None:
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT user_id, april_id, email, provider, plan, subscription_until
                   FROM users WHERE user_id = %s OR april_id = %s
                   ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END LIMIT 1""",
                (raw, raw, raw),
            )
            row = cur.fetchone()
            return dict(row) if row and _is_authenticated_row(row) else None
    finally:
        conn.close()


def get_premium_support_status(user_id: Any) -> dict[str, Any] | None:
    """Return the current user's support history summary without bulk image bytes."""
    raw = str(user_id or "").strip()
    if not raw:
        return None
    user = _support_resolve_user(raw)
    if not user:
        return None
    canonical_id = str(user.get("user_id") or raw)
    current = now()
    until = float(user.get("subscription_until") or 0)
    active_premium = str(user.get("plan") or "free").lower() == "premium" and until > current.timestamp()
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.id, s.user_id, s.message, s.language, s.created_at, s.admin_reply, s.replied_at,
                          s.image_mime, s.image_name, s.admin_reply_language, s.admin_read_at, s.user_read_at,
                          EXISTS(SELECT 1 FROM premium_support_replies r WHERE r.support_message_id = s.id) AS has_admin_reply
                   FROM premium_support_messages s WHERE s.user_id = %s
                   ORDER BY s.created_at DESC, s.id DESC LIMIT 50""",
                (canonical_id,),
            )
            rows = [dict(row) for row in (cur.fetchall() or [])]
            cur.execute(
                """SELECT COUNT(*) AS unread_count, MAX(s.id) AS newest_unread_id
                   FROM premium_support_messages s
                   WHERE s.user_id = %s AND s.user_read_at IS NULL
                     AND (s.admin_reply IS NOT NULL OR EXISTS(
                         SELECT 1 FROM premium_support_replies r WHERE r.support_message_id = s.id
                     ))""",
                (canonical_id,),
            )
            unread_row = cur.fetchone() or {}
            latest = rows[0] if rows else None
            next_allowed = None
            if latest and latest.get("created_at"):
                created = latest["created_at"]
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                next_allowed = created + timedelta(seconds=SUPPORT_COOLDOWN_SECONDS)
            remaining = max(0, int((next_allowed - current).total_seconds())) if next_allowed else 0
            messages = [_support_message_payload(row, include_image=False) for row in rows]
            latest_payload = _support_message_payload(latest, include_image=False)
            unread_count = max(0, int(unread_row.get("unread_count") or 0))
            return {
                "success": True,
                "is_admin": False,
                "active_premium": active_premium,
                "can_send": bool(active_premium and remaining <= 0),
                "next_allowed_at_ms": _support_time_ms(next_allowed),
                "remaining_seconds": remaining,
                "latest_message": latest_payload,
                "messages": messages,
                "unread_reply_count": unread_count,
                "has_unread_reply": unread_count > 0,
                "unread_reply_message_id": int(unread_row.get("newest_unread_id") or 0) or None,
            }
    except Exception as exc:
        print(f"[APRIL_SUPPORT] STATUS_ERROR type={type(exc).__name__}", flush=True)
        return None
    finally:
        conn.close()


def get_premium_support_message_detail(user_id: Any, message_id: Any, *, is_admin: bool = False) -> dict[str, Any] | None:
    """Load one full ticket (including image bytes) only after authorization."""
    try:
        ticket_id = int(message_id)
    except (TypeError, ValueError, OverflowError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    if ticket_id <= 0:
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    raw = str(user_id or "").strip()
    user = _support_resolve_user(raw)
    if not user:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    canonical_id = str(user.get("user_id") or raw)
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.id, s.user_id, s.message, s.language, s.created_at,
                          s.admin_reply, s.replied_at, s.admin_id, s.image_data, s.image_mime, s.image_name,
                          s.admin_reply_language, s.admin_read_at, s.user_read_at, u.april_id, u.name, u.email,
                          EXISTS(SELECT 1 FROM premium_support_replies r WHERE r.support_message_id = s.id) AS has_admin_reply,
                          (LOWER(COALESCE(u.plan, 'free')) = 'premium' AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)) AS active_premium
                   FROM premium_support_messages s JOIN users u ON u.user_id = s.user_id
                   WHERE s.id = %s LIMIT 1""",
                (ticket_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": "SUPPORT_MESSAGE_NOT_FOUND"}
            data = dict(row)
            if is_admin:
                if not bool(data.get("active_premium")):
                    return {"success": False, "error": "SUPPORT_MESSAGE_NOT_FOUND"}
            elif str(data.get("user_id") or "") != canonical_id:
                return {"success": False, "error": "SUPPORT_MESSAGE_NOT_FOUND"}
            payload = _support_message_payload(data, include_identity=is_admin, include_image=True) or {}
            cur.execute(
                """SELECT id, reply, reply_language, admin_id, image_data, image_mime, image_name, created_at
                   FROM premium_support_replies
                   WHERE support_message_id = %s
                   ORDER BY created_at ASC, id ASC""",
                (ticket_id,),
            )
            reply_rows = [dict(item) for item in (cur.fetchall() or [])]
            replies = [{
                "id": int(item.get("id") or 0),
                "reply": str(item.get("reply") or ""),
                "language": str(item.get("reply_language") or "en").strip().lower(),
                "admin_id": str(item.get("admin_id") or ""),
                "image_data": str(item.get("image_data") or "") or None,
                "image_mime": str(item.get("image_mime") or "").strip().lower() or None,
                "image_name": str(item.get("image_name") or "") or None,
                "has_image": bool(
                    str(item.get("image_mime") or "").strip().lower() in {"image/jpeg", "image/png", "image/webp"}
                    and str(item.get("image_data") or "").lower().startswith(
                        f"data:{str(item.get('image_mime') or '').strip().lower()};base64,"
                    )
                ),
                "created_at_ms": _support_time_ms(item.get("created_at")),
            } for item in reply_rows if str(item.get("reply") or "").strip() or item.get("image_data")]
            legacy_reply = str(data.get("admin_reply") or "").strip()
            # Older deployments stored one reply only on premium_support_messages.
            # Keep it visible after the first new supplement is added post-upgrade.
            if legacy_reply and not any(item["reply"] == legacy_reply for item in replies):
                replies.insert(0, {
                    "id": 0,
                    "reply": legacy_reply,
                    "language": str(data.get("admin_reply_language") or "en").strip().lower(),
                    "admin_id": str(data.get("admin_id") or ""),
                    "image_data": None,
                    "image_mime": None,
                    "image_name": None,
                    "has_image": False,
                    "created_at_ms": _support_time_ms(data.get("replied_at")),
                })
            payload["admin_replies"] = replies
            payload["has_admin_reply"] = bool(replies or legacy_reply)
            payload["user_unread"] = payload["has_admin_reply"] and payload.get("user_read_at_ms") is None
            return {"success": True, "is_admin": bool(is_admin), "message": payload}
    except Exception as exc:
        print(f"[APRIL_SUPPORT] DETAIL_ERROR type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "SUPPORT_UNAVAILABLE"}
    finally:
        conn.close()


def mark_premium_support_message_read(user_id: Any, message_id: Any, *, is_admin: bool = False) -> dict[str, Any]:
    """Mark one visible ticket read by its recipient without affecting the other side."""
    try:
        ticket_id = int(message_id)
    except (TypeError, ValueError, OverflowError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    if ticket_id <= 0:
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    raw = str(user_id or "").strip()
    user = _support_resolve_user(raw)
    if not user:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    canonical_id = str(user.get("user_id") or raw)
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                if is_admin:
                    cur.execute(
                        """UPDATE premium_support_messages s SET admin_read_at = COALESCE(s.admin_read_at, CURRENT_TIMESTAMP)
                           FROM users u WHERE s.id = %s AND u.user_id = s.user_id
                             AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                             AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)""",
                        (ticket_id,),
                    )
                else:
                    cur.execute(
                        """UPDATE premium_support_messages SET user_read_at = CURRENT_TIMESTAMP
                           WHERE id = %s AND user_id = %s""",
                        (ticket_id, canonical_id),
                    )
                if cur.rowcount != 1:
                    return {"success": False, "error": "SUPPORT_MESSAGE_NOT_FOUND"}
        return {"success": True, "message_id": ticket_id, "reader": "admin" if is_admin else "user"}
    except Exception as exc:
        print(f"[APRIL_SUPPORT] MARK_READ_ERROR type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "SUPPORT_UNAVAILABLE"}
    finally:
        conn.close()

def send_premium_support_message(
    user_id: Any, message: Any, language: Any = "en", image_data: Any = None,
    image_mime: Any = None, image_name: Any = None,
) -> dict[str, Any]:
    """Insert a Premium text/image request with an atomic per-account 24h limit."""
    raw = str(user_id or "").strip()
    body = str(message or "").strip()
    lang = str(language or "en").strip().lower()[:8] or "en"
    if not raw:
        return {"success": False, "error": "USER_ID_REQUIRED"}
    if len(body) > 4000:
        return {"success": False, "error": "MESSAGE_TOO_LONG"}
    image_data = str(image_data or "").strip()
    image_mime = str(image_mime or "").strip().lower().split(";", 1)[0]
    safe_image_name = str(image_name or "").replace("\\", "/").split("/")[-1].strip()[:180]
    if image_data:
        # Premium support accepts only image/screenshot media, never generic files.
        allowed_image_mimes = {"image/jpeg", "image/png", "image/webp"}
        if (image_mime not in allowed_image_mimes
                or not image_data.startswith(f"data:{image_mime};base64,")
                or len(image_data) > 850_000):
            return {"success": False, "error": "IMAGE_INVALID"}
        if not safe_image_name:
            suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[image_mime]
            safe_image_name = f"support-image{suffix}"
    else:
        image_data, image_mime, safe_image_name = None, None, None
    # The request payloads are independent: non-empty text, image, or both.
    if not body and not image_data:
        return {"success": False, "error": "MESSAGE_TOO_SHORT"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                # Serialize send attempts for this account, including simultaneous
                # requests arriving from separate tabs/devices.
                cur.execute(
                    """SELECT user_id, email, provider, plan, subscription_until
                       FROM users WHERE user_id = %s OR april_id = %s
                       ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                       LIMIT 1 FOR UPDATE""",
                    (raw, raw, raw),
                )
                user = cur.fetchone()
                if not _is_authenticated_row(user):
                    return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
                canonical_id = str(user.get("user_id") or raw)
                active = str(user.get("plan") or "free").lower() == "premium" and float(user.get("subscription_until") or 0) > now().timestamp()
                if not active:
                    return {"success": False, "error": "PREMIUM_REQUIRED"}
                cur.execute(
                    "SELECT created_at FROM premium_support_messages WHERE user_id = %s ORDER BY created_at DESC, id DESC LIMIT 1",
                    (canonical_id,),
                )
                latest = cur.fetchone()
                if latest and latest.get("created_at"):
                    created = latest["created_at"]
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    next_allowed = created + timedelta(seconds=SUPPORT_COOLDOWN_SECONDS)
                    current = now()
                    if current < next_allowed:
                        return {
                            "success": False,
                            "error": "COOLDOWN_ACTIVE",
                            "next_allowed_at_ms": _support_time_ms(next_allowed),
                            "remaining_seconds": max(0, int((next_allowed - current).total_seconds())),
                        }
                cur.execute(
                    """INSERT INTO premium_support_messages(
                           user_id, message, language, image_data, image_mime, image_name, user_read_at
                       ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                       RETURNING id, user_id, message, language, created_at, admin_reply, replied_at,
                                 image_data, image_mime, image_name""",
                    (canonical_id, body, lang, image_data, image_mime, safe_image_name),
                )
        status = get_premium_support_status(raw)
        return status or {"success": False, "error": "SUPPORT_STATUS_UNAVAILABLE"}
    except Exception as exc:
        print(f"[APRIL_SUPPORT] SEND_ERROR type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "SUPPORT_UNAVAILABLE"}
    finally:
        conn.close()


def list_premium_support_messages(limit: int = 10) -> dict[str, Any] | None:
    """Return at most ten active Premium tickets, unread items first."""
    conn = get_conn()
    if not conn:
        return None
    try:
        safe_limit = max(1, min(int(limit), 10))
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.id, s.user_id, s.message, s.language, s.created_at,
                          s.admin_reply, s.replied_at, s.image_mime, s.image_name,
                          s.admin_reply_language, s.admin_read_at, s.user_read_at, u.april_id, u.name, u.email,
                          EXISTS(SELECT 1 FROM premium_support_replies r WHERE r.support_message_id = s.id) AS has_admin_reply,
                          (LOWER(COALESCE(u.plan, 'free')) = 'premium' AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)) AS active_premium
                   FROM premium_support_messages s
                   JOIN users u ON u.user_id = s.user_id
                   WHERE LOWER(COALESCE(u.plan, 'free')) = 'premium'
                     AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                   ORDER BY (s.admin_read_at IS NULL) DESC,
                            (s.replied_at IS NULL AND s.admin_reply IS NULL AND NOT EXISTS(
                                SELECT 1 FROM premium_support_replies r WHERE r.support_message_id = s.id
                            )) DESC,
                            s.created_at DESC, s.id DESC
                   LIMIT %s""",
                (safe_limit,),
            )
            rows = cur.fetchall() or []
            cur.execute(
                """SELECT COUNT(*) AS unread_count FROM premium_support_messages s
                   JOIN users u ON u.user_id = s.user_id
                   WHERE s.admin_read_at IS NULL
                     AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                     AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)"""
            )
            unread = cur.fetchone() or {}
            return {
                "success": True,
                "is_admin": True,
                "unread_count": max(0, int(unread.get("unread_count") or 0)),
                "messages": [_support_message_payload(dict(row), include_identity=True, include_image=False) for row in rows],
            }
    except Exception as exc:
        print(f"[APRIL_SUPPORT] INBOX_ERROR type={type(exc).__name__}", flush=True)
        return None
    finally:
        conn.close()

def reply_premium_support_message(
    message_id: Any, reply: Any, admin_id: Any, language: Any = "en",
    image_data: Any = None, image_mime: Any = None, image_name: Any = None,
) -> dict[str, Any]:
    """Add a text reply, image reply, or both to an existing Premium request."""
    try:
        ticket_id = int(message_id)
    except (TypeError, ValueError, OverflowError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    body = str(reply or "").strip()
    admin = str(admin_id or "").strip()
    reply_language = str(language or "en").strip().lower()[:8] or "en"
    if ticket_id <= 0:
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    if len(body) > 4000:
        return {"success": False, "error": "REPLY_TOO_LONG"}

    image_data = str(image_data or "").strip()
    image_mime = str(image_mime or "").strip().lower().split(";", 1)[0]
    safe_image_name = str(image_name or "").replace("\\", "/").split("/")[-1].strip()[:180]
    if image_data:
        allowed_image_mimes = {"image/jpeg", "image/png", "image/webp"}
        if (image_mime not in allowed_image_mimes
                or not image_data.startswith(f"data:{image_mime};base64,")
                or len(image_data) > 850_000):
            return {"success": False, "error": "IMAGE_INVALID"}
        if not safe_image_name:
            suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[image_mime]
            safe_image_name = f"support-image{suffix}"
    else:
        image_data, image_mime, safe_image_name = None, None, None
    if len(body) < 2 and not image_data:
        return {"success": False, "error": "REPLY_TOO_SHORT"}

    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT s.id, s.admin_reply,
                              (LOWER(COALESCE(u.plan, 'free')) = 'premium' AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)) AS active_premium
                       FROM premium_support_messages s JOIN users u ON u.user_id = s.user_id
                       WHERE s.id = %s FOR UPDATE OF s""",
                    (ticket_id,),
                )
                row = cur.fetchone()
                if not row or not bool(row.get("active_premium")):
                    return {"success": False, "error": "SUPPORT_MESSAGE_NOT_FOUND"}
                cur.execute(
                    """INSERT INTO premium_support_replies(
                           support_message_id, reply, reply_language, admin_id,
                           image_data, image_mime, image_name
                       ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (ticket_id, body, reply_language, admin, image_data, image_mime, safe_image_name),
                )
                reply_row = cur.fetchone() or {}
                # The legacy summary keeps the first non-empty text for older inbox
                # clients; all replies and images are retained in the new timeline.
                cur.execute(
                    """UPDATE premium_support_messages
                       SET admin_reply = COALESCE(NULLIF(BTRIM(admin_reply), ''), NULLIF(%s, '')),
                           admin_reply_language = CASE
                               WHEN (admin_reply IS NULL OR BTRIM(admin_reply) = '') AND NULLIF(%s, '') IS NOT NULL THEN %s
                               ELSE admin_reply_language
                           END,
                           replied_at = CURRENT_TIMESTAMP, admin_id = %s,
                           admin_read_at = COALESCE(admin_read_at, CURRENT_TIMESTAMP),
                           user_read_at = NULL
                       WHERE id = %s""",
                    (body, body, reply_language, admin, ticket_id),
                )
                if cur.rowcount != 1:
                    return {"success": False, "error": "SUPPORT_MESSAGE_NOT_FOUND"}
        return {"success": True, "message_id": ticket_id, "reply_id": int(reply_row.get("id") or 0), "has_admin_reply": True}
    except Exception as exc:
        print(f"[APRIL_SUPPORT] REPLY_ERROR type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "SUPPORT_UNAVAILABLE"}
    finally:
        conn.close()


def _premium_test_enabled() -> bool:
    """Keep test activation enabled while real payment processing is absent.

    The Web button is the current test adapter, not a payment confirmation. The
    grant is still limited to an authenticated database user and is audited in
    payments as a zero-value ``test_grant``. Disable/remove this adapter when
    real billing replaces it; an old environment value must not silently block
    the current test workflow.
    """
    return True


def _new_premium_id() -> str:
    return "APR-PRM-" + secrets.token_hex(5).upper()


def activate_test_premium(user_id: Any, hours: int = PREMIUM_TEST_DURATION_HOURS) -> dict[str, Any]:
    """Grant or extend a 24-hour test Premium entitlement for an authenticated user.

    The Premium ID is stored once in the canonical users row, copied into a
    zero-value test-grant ledger row, and retained after expiry for reuse. When
    renewing an unexpired Lite/Premium plan, the new duration is added to its
    existing expiry instead of discarding the unused time.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "USER_ID_REQUIRED"}
    if not _premium_test_enabled():
        return {"success": False, "error": "PREMIUM_TEST_MODE_DISABLED"}
    # During the pre-billing phase every registered Google-authenticated account
    # may use the test button. Identity is resolved from the trusted request header
    # and canonical users row; no email allowlist or browser-provided ID is trusted.
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, april_id, email, provider, plan, subscription_until, premium_id
                    FROM users
                    WHERE user_id = %s OR april_id = %s
                    ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (uid, uid, uid),
                )
                user = cur.fetchone()
                if not _is_authenticated_row(user):
                    return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
                # Normalize the inbound API identifier before updating users or
                # writing the payments ledger so they always point to one row.
                uid = str(user.get("user_id") or uid).strip()
                provider = str(user.get("provider") or "").strip().lower()
                if provider != "google":
                    return {"success": False, "error": "PREMIUM_TEST_USER_NOT_ALLOWED"}
                premium_id = str(user.get("premium_id") or "").strip()
                if not premium_id:
                    for _ in range(5):
                        candidate = _new_premium_id()
                        cur.execute("SELECT 1 FROM users WHERE premium_id = %s", (candidate,))
                        if not cur.fetchone():
                            premium_id = candidate
                            break
                    if not premium_id:
                        return {"success": False, "error": "PREMIUM_ID_GENERATION_FAILED"}
                current_seconds = now().timestamp()
                current_plan = str(user.get("plan") or "free").strip().lower()
                current_expiry = float(user.get("subscription_until") or 0)
                renewal_base = (
                    current_expiry
                    if current_plan in {"lite", "premium"} and current_expiry > current_seconds
                    else current_seconds
                )
                expires_at = renewal_base + max(1, min(int(hours), 24)) * 3600
                cur.execute(
                    "UPDATE users SET premium_id = %s, plan = 'premium', subscription_until = %s, warned = FALSE WHERE user_id = %s",
                    (premium_id, expires_at, uid),
                )
                # Keep a trace of each test activation in the same payment ledger,
                # keyed by the canonical April user ID and the exact Premium ID.
                # Zero amount + test_grant status prevent it from being mistaken
                # for a real payment or counted as paid subscription history.
                cur.execute(
                    """
                    INSERT INTO payments
                        (user_id, plan, amount, premium_id, payment_status, payment_source)
                    VALUES (%s, 'premium', 0, %s, 'test_grant', 'test_activation')
                    """,
                    (uid, premium_id),
                )
        status = get_user_subscription_status(uid)
        if not status:
            return {"success": False, "error": "SUBSCRIPTION_STATUS_UNAVAILABLE"}
        return {"success": True, **status}
    except psycopg2.errors.UndefinedColumn:
        return {"success": False, "error": "PREMIUM_SCHEMA_MIGRATION_REQUIRED"}
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


def touch_user_activity(user_id: Any) -> None:
    """Update last activity on existing authenticated chat requests."""
    uid = str(user_id or "").strip()
    if not uid:
        return
    conn = get_conn()
    if not conn:
        return
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_seen_at = CURRENT_TIMESTAMP WHERE user_id = %s", (uid,))
    finally:
        conn.close()


def get_admin_user_telemetry() -> dict[str, int] | None:
    """Count registered identities, excluding guest/voice/system placeholder rows.

    Only rows with a real email and authentication provider are eligible. Email
    is the canonical identity key, so legacy rows keyed by email and April-ID
    rows for the same Google identity are not counted as separate users. If an
    identity has any currently active Premium row, that identity is Premium.
    Online remains based on a recent chat activity mark (last 3 minutes).
    """
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH registered AS (
                        SELECT
                            LOWER(BTRIM(email)) AS account_key,
                            (
                                LOWER(BTRIM(COALESCE(plan, 'free'))) = 'premium'
                                AND COALESCE(subscription_until, 0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                            ) AS premium_active,
                            (last_seen_at >= CURRENT_TIMESTAMP - INTERVAL '3 minutes') AS recently_active
                        FROM users
                        WHERE NULLIF(BTRIM(email), '') IS NOT NULL
                          AND NULLIF(BTRIM(provider), '') IS NOT NULL
                          AND LOWER(BTRIM(user_id)) NOT IN ('guest', 'web_voice')
                    ),
                    accounts AS (
                        SELECT
                            account_key,
                            BOOL_OR(COALESCE(premium_active, FALSE)) AS premium_active,
                            BOOL_OR(COALESCE(recently_active, FALSE)) AS recently_active
                        FROM registered
                        GROUP BY account_key
                    )
                    SELECT
                        COUNT(*)::INT AS total,
                        COUNT(*) FILTER (WHERE premium_active)::INT AS premium,
                        COUNT(*) FILTER (WHERE NOT premium_active)::INT AS free,
                        COUNT(*) FILTER (WHERE recently_active)::INT AS online
                    FROM accounts
                    """
                )
                row = cur.fetchone() or {}
                return {
                    key: max(0, int(row.get(key) or 0))
                    for key in ("online", "premium", "free", "total")
                }
    except Exception as exc:
        print(f"[APRIL_TELEMETRY] READ_ERROR type={type(exc).__name__}", flush=True)
        return None
    finally:
        conn.close()

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
