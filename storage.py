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
from urllib.parse import quote
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
PREMIUM_DAYS = int(os.getenv("APRIL_PREMIUM_DAYS", "28"))

FILE_PATH = "data/subscriptions.json"

DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_SEED_HOURS = 1
DIALOGUE_WINDOW_SECONDS = DIALOGUE_WINDOW_HOURS * 3600
DIALOGUE_SEED_SECONDS = DIALOGUE_SEED_HOURS * 3600
PREMIUM_MEMORY_WINDOW_HOURS = 24
PREMIUM_MEMORY_WINDOW_SECONDS = PREMIUM_MEMORY_WINDOW_HOURS * 3600
PREMIUM_TEST_DURATION_HOURS = 28 * 24

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
    "dialogue_memory": {"id", "user_id", "created_at", "retention_hours", "turn_index", "user_text", "april_text", "user_text_en", "april_text_en", "language", "relation", "pair_hash", "dialog_id", "conversation_id", "message_id", "interpretation_id", "structured_request", "structured_response", "asset_payloads"},
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
                        interpretation_id TEXT,
                        asset_payloads JSONB NOT NULL DEFAULT '[]'::jsonb
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
                cur.execute("ALTER TABLE dialogue_memory ADD COLUMN IF NOT EXISTS asset_payloads JSONB NOT NULL DEFAULT '[]'::jsonb")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_memory_user_created ON dialogue_memory(user_id, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_memory_user_dialog ON dialogue_memory(user_id, dialog_id, created_at DESC)")

                # Required destructive sanitization: known legacy memory stores are
                # no longer part of the schema and must not survive deployment.
                _schema_cleanup(cur)

                # Remove any columns that are not part of the canonical minimal schema.
                _drop_unwanted_columns(cur, "users")
                _drop_unwanted_columns(cur, "payments")
                _drop_unwanted_columns(cur, "dialogue_memory")

                # Public community is deliberately isolated from private dialogue_memory.
                # Names are server-owned and keyed by canonical authenticated users.
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS community_profiles (
                        user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                        display_name TEXT NOT NULL,
                        is_custom BOOLEAN NOT NULL DEFAULT FALSE,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("ALTER TABLE community_profiles ADD COLUMN IF NOT EXISTS is_custom BOOLEAN NOT NULL DEFAULT FALSE")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS community_messages (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        display_name TEXT NOT NULL,
                        message TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        attachment_name TEXT,
                        attachment_mime TEXT,
                        attachment_size BIGINT,
                        attachment_data BYTEA,
                        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                        CHECK (length(message) <= 4000),
                        CHECK (attachment_size IS NULL OR attachment_size <= 3145728)
                    )
                """)
                cur.execute("ALTER TABLE community_messages ADD COLUMN IF NOT EXISTS attachment_name TEXT")
                cur.execute("ALTER TABLE community_messages ADD COLUMN IF NOT EXISTS attachment_mime TEXT")
                cur.execute("ALTER TABLE community_messages ADD COLUMN IF NOT EXISTS attachment_size BIGINT")
                cur.execute("ALTER TABLE community_messages ADD COLUMN IF NOT EXISTS attachment_data BYTEA")
                cur.execute("ALTER TABLE community_messages ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_messages_created ON community_messages(created_at DESC, id DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_messages_user_created ON community_messages(user_id, created_at DESC)")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS community_message_reports (
                        id BIGSERIAL PRIMARY KEY,
                        message_id BIGINT NOT NULL REFERENCES community_messages(id) ON DELETE CASCADE,
                        reporter_user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        reason TEXT NOT NULL DEFAULT 'inappropriate',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (message_id, reporter_user_id)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_reports_created ON community_message_reports(created_at DESC)")
                # Friend circle and private 1:1 messages are separate from public
                # community messages and from the private April↔user memory store.
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS community_friendships (
                        user_a TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        user_b TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        requested_by_user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted')),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_a, user_b),
                        CHECK (user_a < user_b),
                        CHECK (requested_by_user_id = user_a OR requested_by_user_id = user_b)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_friendships_user_a ON community_friendships(user_a, status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_friendships_user_b ON community_friendships(user_b, status)")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS community_direct_messages (
                        id BIGSERIAL PRIMARY KEY,
                        sender_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        recipient_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        message TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        attachment_name TEXT,
                        attachment_mime TEXT,
                        attachment_size BIGINT,
                        attachment_data BYTEA,
                        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                        CHECK (sender_id <> recipient_id),
                        CHECK (length(message) <= 4000),
                        CHECK (attachment_size IS NULL OR attachment_size <= 3145728)
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_dm_pair_created ON community_direct_messages(sender_id, recipient_id, created_at DESC, id DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_community_dm_recipient_created ON community_direct_messages(recipient_id, created_at DESC, id DESC)")

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
                           WHERE (
                               u.user_id = d.user_id
                               OR (
                                   u.april_id = d.user_id
                                   AND NOT EXISTS (
                                       SELECT 1 FROM users AS owner
                                       WHERE owner.user_id = d.user_id
                                         AND owner.user_id <> u.user_id
                                   )
                               )
                           )
                             AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                             AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM %s)
                             AND COALESCE(d.retention_hours, 12) < 24
                             AND d.created_at + INTERVAL '24 hours' > %s
                             AND d.created_at <= %s""",
                        (current, current, current),
                    )
                else:
                    owner_ids = _dialogue_owner_ids_cursor(cur, str(user_id))
                    if not owner_ids:
                        return 0
                    canonical_uid = owner_ids[0]
                    cur.execute(
                        """UPDATE dialogue_memory AS d SET retention_hours = 24
                           WHERE d.user_id = ANY(%s)
                             AND EXISTS (
                               SELECT 1 FROM users AS u
                               WHERE u.user_id = %s
                                 AND LOWER(COALESCE(u.plan, 'free')) = 'premium'
                                 AND COALESCE(u.subscription_until, 0) > EXTRACT(EPOCH FROM %s)
                             )
                             AND COALESCE(d.retention_hours, 12) < 24
                             AND d.created_at + INTERVAL '24 hours' > %s
                             AND d.created_at <= %s""",
                        (owner_ids, canonical_uid, current, current, current),
                    )
                if user_id is None:
                    cur.execute(
                        """SELECT user_id, message_id FROM dialogue_memory AS d
                           WHERE d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (current,),
                    )
                else:
                    owner_ids = _dialogue_owner_ids_cursor(cur, str(user_id))
                    if not owner_ids:
                        return 0
                    cur.execute(
                        """SELECT user_id, message_id FROM dialogue_memory AS d
                           WHERE d.user_id = ANY(%s)
                             AND d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (owner_ids, current),
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
                           WHERE d.user_id = ANY(%s)
                             AND d.created_at + (GREATEST(12, LEAST(24, COALESCE(d.retention_hours, 12))) * INTERVAL '1 hour') <= %s""",
                        (owner_ids, current),
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


def _dialogue_owner_ids_cursor(cur, user_id: Any) -> list[str]:
    """Return internal/public IDs for exactly one authenticated account.

    Older Web deployments could persist dialogue rows under public april_id.
    Query both identifiers only after they resolve to the same authenticated row.
    Never widen access through email, Google ID, or Premium ID aliases.
    """
    raw = str(user_id or "").strip()
    if not raw:
        return []
    cur.execute(
        """SELECT user_id, april_id, email, provider
           FROM users
           WHERE user_id = %s OR april_id = %s
           ORDER BY CASE WHEN user_id = %s THEN 0 ELSE 1 END
           LIMIT 1""",
        (raw, raw, raw),
    )
    account = cur.fetchone()
    if not _is_authenticated_row(account):
        return []
    canonical = str(account.get("user_id") or "").strip()
    public = str(account.get("april_id") or "").strip()
    if public and public != canonical:
        # Do not include a public alias if it collides with another account's
        # internal key; owner IDs must never cross account boundaries.
        cur.execute(
            "SELECT 1 FROM users WHERE user_id = %s AND user_id <> %s LIMIT 1",
            (public, canonical),
        )
        if cur.fetchone():
            public = ""
    return list(dict.fromkeys(value for value in (canonical, public) if value))


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
    asset_payloads: list[dict[str, Any]] | None = None,
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
                        (user_id, created_at, retention_hours, turn_index, user_text, april_text, user_text_en, april_text_en, language, relation, pair_hash, dialog_id, conversation_id, message_id, interpretation_id, structured_request, structured_response, asset_payloads)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                    ON CONFLICT (pair_hash) DO UPDATE SET
                        user_text_en = EXCLUDED.user_text_en,
                        april_text_en = EXCLUDED.april_text_en,
                        structured_request = EXCLUDED.structured_request,
                        structured_response = EXCLUDED.structured_response,
                        asset_payloads = CASE WHEN EXCLUDED.asset_payloads IS NOT NULL AND EXCLUDED.asset_payloads <> '[]'::jsonb THEN EXCLUDED.asset_payloads ELSE dialogue_memory.asset_payloads END,
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
                        json.dumps(asset_payloads or [], ensure_ascii=False, default=str),
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
                owner_ids = _dialogue_owner_ids_cursor(cur, uid)
                if not owner_ids:
                    return []
                cur.execute(
                    """
                    SELECT id, user_id, created_at, retention_hours, turn_index, user_text, april_text, user_text_en, april_text_en,
                           language, relation, dialog_id, conversation_id, message_id, interpretation_id,
                           structured_request, structured_response
                    FROM dialogue_memory
                    WHERE user_id = ANY(%s)
                      AND created_at <= %s
                      AND created_at + (GREATEST(12, LEAST(24, COALESCE(retention_hours, 12))) * INTERVAL '1 hour') > %s
                    ORDER BY created_at ASC, turn_index ASC, id ASC
                    """,
                    (owner_ids, current, current),
                )
                rows = [dict(row) for row in cur.fetchall()]
                for row in rows:
                    # Present one canonical identity to downstream state/search code,
                    # even when the underlying retained row used the old public alias.
                    row["user_id"] = owner_ids[0]
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
                owner_ids = _dialogue_owner_ids_cursor(cur, uid)
                if not owner_ids:
                    return {"authenticated": False}
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
                        WHERE user_id = ANY(%s)
                          AND COALESCE(retention_hours, 12) < 24
                          AND created_at > %s - INTERVAL '24 hours'
                          AND created_at + INTERVAL '24 hours' > %s
                        """,
                        (owner_ids, current, current),
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
                    WHERE user_id = ANY(%s)
                      AND created_at <= %s
                      AND created_at > %s - INTERVAL '24 hours'
                      AND created_at + (
                          GREATEST(12, LEAST(24, COALESCE(retention_hours, 12)))
                          * INTERVAL '1 hour'
                      ) > %s
                    ORDER BY created_at ASC, turn_index ASC, id ASC
                    """,
                    (owner_ids, current, current, current),
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



def dialogue_message_saved(
    user_id: Any,
    message_id: Any,
    *,
    timestamp: float | int | datetime | None = None,
) -> bool:
    """Check whether one authenticated turn has reached durable dialogue storage.

    This is intentionally a tiny indexed existence query used by Web recovery
    polling. It must not hydrate the history index, scene JSON, or binary assets.
    """
    uid = str(user_id or "").strip()
    mid = str(message_id or "").strip()
    if not uid or not mid:
        return False
    conn = get_conn()
    if not conn:
        return False
    current = now() if timestamp is None else (
        timestamp.astimezone(timezone.utc)
        if isinstance(timestamp, datetime)
        else datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    )
    try:
        with conn:
            with conn.cursor() as cur:
                if not _is_authenticated_cursor(cur, uid):
                    return False
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM dialogue_memory
                        WHERE user_id = %s
                          AND message_id = %s
                          AND created_at <= %s
                          AND created_at > %s - INTERVAL '24 hours'
                          AND created_at + (
                              GREATEST(12, LEAST(24, COALESCE(retention_hours, 12)))
                              * INTERVAL '1 hour'
                          ) > %s
                    ) AS saved
                    """,
                    (uid, mid, current, current),
                )
                row = cur.fetchone() or {}
                return bool(row.get("saved")) if isinstance(row, dict) else bool(row[0])
    except psycopg2.errors.UndefinedTable:
        return False
    except Exception:
        # Status polling is advisory; a transient database issue must not crash
        # the canonical Web history/recovery request.
        return False
    finally:
        conn.close()


def load_dialogue_asset_payloads(
    user_id: Any,
    message_ids: list[str],
    *,
    timestamp: float | int | datetime | None = None,
) -> list[dict[str, Any]]:
    """Load saved output bytes only for the authenticated selected dialogue turns.

    This is a narrow recovery path for rendered assets; normal memory search never
    hydrates image payloads and therefore does not pay the binary-memory cost.
    """
    uid = str(user_id or "").strip()
    ids = list(dict.fromkeys(str(value or "").strip() for value in (message_ids or []) if str(value or "").strip()))[:8]
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
                    SELECT message_id, asset_payloads
                    FROM dialogue_memory
                    WHERE user_id = %s
                      AND message_id = ANY(%s)
                      AND created_at <= %s
                      AND created_at > %s - INTERVAL '24 hours'
                      AND created_at + (
                          GREATEST(12, LEAST(24, COALESCE(retention_hours, 12)))
                          * INTERVAL '1 hour'
                      ) > %s
                    ORDER BY created_at DESC, turn_index DESC, id DESC
                    """,
                    (uid, ids, current, current, current),
                )
                return [dict(row) for row in cur.fetchall() if isinstance(row, dict)]
    except psycopg2.errors.UndefinedTable:
        return []
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
                owner_ids = _dialogue_owner_ids_cursor(cur, uid)
                if not owner_ids:
                    return []
                cur.execute(
                    """
                    SELECT id, user_id, created_at, retention_hours, turn_index,
                           user_text, april_text, user_text_en, april_text_en,
                           language, relation, dialog_id, conversation_id,
                           message_id, interpretation_id,
                           structured_request, structured_response, asset_payloads
                    FROM dialogue_memory
                    WHERE user_id = ANY(%s)
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
                    (owner_ids, current, current, current, ids, ids),
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
    """Grant or extend a 28-day test Premium entitlement for an authenticated user.

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
                expires_at = renewal_base + max(1, min(int(hours), PREMIUM_TEST_DURATION_HOURS)) * 3600
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


# =========================================================
# PUBLIC COMMUNITY SPACE (separate from private April memory)
# =========================================================

COMMUNITY_MAX_MESSAGE_CHARS = 4000
COMMUNITY_MAX_ATTACHMENT_BYTES = 3 * 1024 * 1024
COMMUNITY_HISTORY_MAX_MESSAGES = 30
COMMUNITY_RATE_LIMIT_PER_MINUTE = 10
COMMUNITY_USER_ATTACHMENT_QUOTA_BYTES = 30 * 1024 * 1024
_COMMUNITY_BLOCKED_EXTENSIONS = {
    ".exe", ".msi", ".com", ".bat", ".cmd", ".ps1", ".vbs", ".vbe",
    ".scr", ".pif", ".dll", ".sys", ".so", ".dylib", ".apk", ".app",
}


def _community_lock_history(cur, scope: str, key: str = "global") -> None:
    """Serialize retention cleanup/writes so concurrent sends cannot exceed the cap."""
    cur.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
        ("april-community-history:" + str(scope), str(key)),
    )


def _community_prune_public_history(cur) -> None:
    """Physically remove old community rows, retaining only the latest 30 globally."""
    cur.execute(
        """DELETE FROM community_messages
           WHERE id IN (
               SELECT id FROM community_messages
               ORDER BY id DESC OFFSET %s
           )""",
        (COMMUNITY_HISTORY_MAX_MESSAGES,),
    )


def _community_direct_pair_key(user_a: Any, user_b: Any) -> str:
    return "|".join(sorted((str(user_a), str(user_b))))


def _community_prune_direct_history(cur, user_a: Any, user_b: Any) -> None:
    """Physically remove direct messages older than the latest 30 in this pair."""
    a, b = str(user_a), str(user_b)
    cur.execute(
        """DELETE FROM community_direct_messages
           WHERE id IN (
               SELECT id FROM community_direct_messages
               WHERE (sender_id=%s AND recipient_id=%s)
                  OR (sender_id=%s AND recipient_id=%s)
               ORDER BY id DESC OFFSET %s
           )""",
        (a, b, b, a, COMMUNITY_HISTORY_MAX_MESSAGES),
    )


def _community_canonical_user(user_id: Any) -> str | None:
    raw = str(user_id or "").strip()
    if not raw:
        return None
    canonical = resolve_user_id(raw)
    if not canonical or not is_authenticated_user(canonical):
        return None
    return canonical


def _community_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value) if value is not None else None


def _community_payload(row: dict[str, Any]) -> dict[str, Any]:
    deleted = bool(row.get("is_deleted"))
    attachment_name = None if deleted else row.get("attachment_name")
    attachment_size = None if deleted else row.get("attachment_size")
    return {
        "id": int(row.get("id") or 0),
        "display_name": str(row.get("display_name") or "Участник")[:32],
        "plan": "premium" if str(row.get("author_plan") or row.get("plan") or "free").lower() == "premium" else "free",
        "message": "Сообщение удалено автором." if deleted else str(row.get("message") or ""),
        "created_at": _community_iso(row.get("created_at")),
        "is_deleted": deleted,
        "is_own": bool(row.get("is_own")),
        "attachment": ({
            "name": str(attachment_name or "file"),
            "size": int(attachment_size or 0),
            "download_url": f"/api/community?file_id={int(row.get('id') or 0)}",
        } if attachment_name else None),
    }


# =========================================================
# COMMUNITY FRIEND CIRCLE + PRIVATE USER-TO-USER MESSAGES
# =========================================================

def _community_pair(user_a: str, user_b: str) -> tuple[str, str]:
    return (user_a, user_b) if user_a < user_b else (user_b, user_a)


def _community_find_target(cur, peer_april_id: Any, current_user_id: str) -> dict[str, Any] | None:
    public_id = str(peer_april_id or "").strip()
    if not public_id or len(public_id) > 100:
        return None
    cur.execute(
        """SELECT user_id, april_id, name, LOWER(COALESCE(plan, 'free')) AS plan,
                  COALESCE(subscription_until, 0) AS subscription_until
           FROM users
           WHERE LOWER(COALESCE(april_id, '')) = LOWER(%s)
             AND COALESCE(email, '') <> '' AND COALESCE(provider, '') <> ''
           LIMIT 1""",
        (public_id,),
    )
    target = cur.fetchone()
    if not target or str(target.get("user_id") or "") == current_user_id:
        return None
    return dict(target)


def _community_active_plan(row: dict[str, Any]) -> str:
    active = (
        str(row.get("plan") or "free").lower() == "premium"
        and float(row.get("subscription_until") or 0) > now().timestamp()
    )
    return "premium" if active else "free"


def get_community_members(user_id: Any, *, limit: int = 100) -> dict[str, Any]:
    """Return public community members with safe April IDs and friendship state."""
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    safe_limit = max(1, min(100, int(limit or 100)))
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT u.user_id, u.april_id, u.name,
                              LOWER(COALESCE(u.plan, 'free')) AS plan,
                              COALESCE(u.subscription_until, 0) AS subscription_until,
                              p.display_name, p.is_custom,
                              COALESCE(u.last_seen_at, u.last_login_at, u.created_at) AS activity_at
                       FROM users u LEFT JOIN community_profiles p ON p.user_id = u.user_id
                       WHERE u.user_id <> %s
                         AND COALESCE(u.april_id, '') <> ''
                         AND COALESCE(u.email, '') <> '' AND COALESCE(u.provider, '') <> ''
                       ORDER BY
                         CASE WHEN EXISTS (
                           SELECT 1 FROM community_friendships cf WHERE cf.status='accepted'
                             AND ((cf.user_a=%s AND cf.user_b=u.user_id) OR (cf.user_b=%s AND cf.user_a=u.user_id))
                         ) THEN 0
                         WHEN EXISTS (
                           SELECT 1 FROM community_friendships cf WHERE cf.status='pending'
                             AND ((cf.user_a=%s AND cf.user_b=u.user_id) OR (cf.user_b=%s AND cf.user_a=u.user_id))
                         ) THEN 1 ELSE 2 END,
                         COALESCE(u.last_seen_at, u.last_login_at, u.created_at) DESC NULLS LAST
                       LIMIT %s""",
                    (uid, uid, uid, uid, uid, safe_limit),
                )
                rows = [dict(row) for row in (cur.fetchall() or [])]
                cur.execute(
                    """SELECT user_a, user_b, requested_by_user_id, status
                       FROM community_friendships
                       WHERE user_a = %s OR user_b = %s""",
                    (uid, uid),
                )
                relations: dict[str, str] = {}
                for row in cur.fetchall() or []:
                    row = dict(row)
                    other = str(row.get("user_b") if str(row.get("user_a")) == uid else row.get("user_a") or "")
                    if row.get("status") == "accepted":
                        relations[other] = "friend"
                    elif str(row.get("requested_by_user_id") or "") == uid:
                        relations[other] = "outgoing"
                    else:
                        relations[other] = "incoming"
                members = []
                for row in rows:
                    public_id = str(row.get("april_id") or "").strip()
                    if not public_id:
                        continue
                    default_name = str(row.get("name") or "").strip()
                    if not default_name:
                        default_name = f"Участник {public_id[-4:]}"
                    members.append({
                        "april_id": public_id,
                        "display_name": str(row.get("display_name") or default_name).strip()[:32],
                        "plan": _community_active_plan(row),
                        "relation": relations.get(str(row.get("user_id") or ""), "none"),
                    })
                cur.execute(
                    """SELECT u.name, u.april_id, LOWER(COALESCE(u.plan, 'free')) AS plan,
                              COALESCE(u.subscription_until, 0) AS subscription_until,
                              p.display_name, p.is_custom
                       FROM users u LEFT JOIN community_profiles p ON p.user_id = u.user_id
                       WHERE u.user_id = %s LIMIT 1""",
                    (uid,),
                )
                own = dict(cur.fetchone() or {})
                default_own = str(own.get("name") or "").strip() or f"Участник {str(own.get('april_id') or uid)[-4:]}"
                own_name = str(own.get("display_name") or default_own).strip()[:32]
                if not own.get("display_name"):
                    cur.execute(
                        """INSERT INTO community_profiles(user_id, display_name, is_custom)
                           VALUES (%s, %s, FALSE) ON CONFLICT (user_id) DO NOTHING""",
                        (uid, own_name),
                    )
                return {
                    "success": True,
                    "members": members,
                    "profile": {"display_name": own_name, "is_custom": bool(own.get("is_custom"))},
                    "plan": _community_active_plan(own),
                }
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] MEMBERS_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def send_community_friend_request(user_id: Any, peer_april_id: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                target = _community_find_target(cur, peer_april_id, uid)
                if not target:
                    return {"success": False, "error": "COMMUNITY_USER_NOT_FOUND"}
                peer = str(target["user_id"])
                a, b = _community_pair(uid, peer)
                cur.execute("SELECT status, requested_by_user_id FROM community_friendships WHERE user_a=%s AND user_b=%s FOR UPDATE", (a, b))
                existing = cur.fetchone()
                if existing:
                    state = str(existing.get("status") or "")
                    requested_by = str(existing.get("requested_by_user_id") or "")
                    if state == "accepted":
                        return {"success": True, "relation": "friend"}
                    if requested_by == uid:
                        return {"success": True, "relation": "outgoing"}
                    return {"success": True, "relation": "incoming", "error": "FRIEND_REQUEST_INCOMING"}
                cur.execute(
                    """INSERT INTO community_friendships(user_a, user_b, requested_by_user_id, status)
                       VALUES (%s,%s,%s,'pending')""",
                    (a, b, uid),
                )
                return {"success": True, "relation": "outgoing"}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] FRIEND_REQUEST_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def accept_community_friend_request(user_id: Any, requester_april_id: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                target = _community_find_target(cur, requester_april_id, uid)
                if not target:
                    return {"success": False, "error": "COMMUNITY_USER_NOT_FOUND"}
                requester = str(target["user_id"])
                a, b = _community_pair(uid, requester)
                cur.execute(
                    """UPDATE community_friendships SET status='accepted', updated_at=CURRENT_TIMESTAMP
                       WHERE user_a=%s AND user_b=%s AND status='pending' AND requested_by_user_id=%s
                       RETURNING user_a""",
                    (a, b, requester),
                )
                if not cur.fetchone():
                    cur.execute("SELECT status FROM community_friendships WHERE user_a=%s AND user_b=%s", (a, b))
                    row = cur.fetchone() or {}
                    if row.get("status") == "accepted":
                        return {"success": True, "relation": "friend"}
                    return {"success": False, "error": "FRIEND_REQUEST_NOT_FOUND"}
                return {"success": True, "relation": "friend"}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] FRIEND_ACCEPT_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def remove_community_friend(user_id: Any, peer_april_id: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                target = _community_find_target(cur, peer_april_id, uid)
                if not target:
                    return {"success": False, "error": "COMMUNITY_USER_NOT_FOUND"}
                a, b = _community_pair(uid, str(target["user_id"]))
                cur.execute("DELETE FROM community_friendships WHERE user_a=%s AND user_b=%s AND status='accepted'", (a, b))
                return {"success": True, "relation": "none"}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] FRIEND_REMOVE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def _community_require_friends(cur, uid: str, peer: dict[str, Any]) -> str | None:
    peer_uid = str(peer.get("user_id") or "")
    a, b = _community_pair(uid, peer_uid)
    cur.execute("SELECT status FROM community_friendships WHERE user_a=%s AND user_b=%s", (a, b))
    row = cur.fetchone() or {}
    return peer_uid if row.get("status") == "accepted" else None


def _community_direct_payload(row: dict[str, Any], *, current_user_id: str, peer_april_id: str) -> dict[str, Any]:
    deleted = bool(row.get("is_deleted"))
    attachment_name = None if deleted else row.get("attachment_name")
    attachment_size = None if deleted else row.get("attachment_size")
    sender_uid = str(row.get("sender_id") or "")
    sender_plan = str(row.get("sender_plan") or "free")
    return {
        "id": int(row.get("id") or 0),
        "sender_name": str(row.get("sender_name") or "Участник")[:32],
        "sender_plan": sender_plan,
        "is_own": sender_uid == current_user_id,
        "message": "Сообщение удалено автором." if deleted else str(row.get("message") or ""),
        "created_at": _community_iso(row.get("created_at")),
        "is_deleted": deleted,
        "attachment": ({
            "name": str(attachment_name or "file"),
            "size": int(attachment_size or 0),
            "download_url": f"/api/community?dm_file_id={int(row.get('id') or 0)}&peer_id={quote(str(peer_april_id), safe='')}",
        } if attachment_name else None),
    }


def get_community_direct_messages(user_id: Any, peer_april_id: Any, *, limit: int = 30) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    safe_limit = max(1, min(COMMUNITY_HISTORY_MAX_MESSAGES, int(limit or COMMUNITY_HISTORY_MAX_MESSAGES)))
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                peer = _community_find_target(cur, peer_april_id, uid)
                if not peer:
                    return {"success": False, "error": "COMMUNITY_USER_NOT_FOUND"}
                peer_uid = _community_require_friends(cur, uid, peer)
                if not peer_uid:
                    return {"success": False, "error": "FRIENDS_REQUIRED"}
                pair_key = _community_direct_pair_key(uid, peer_uid)
                _community_lock_history(cur, "direct", pair_key)
                _community_prune_direct_history(cur, uid, peer_uid)
                cur.execute(
                    """SELECT m.id, m.sender_id, m.recipient_id, m.message, m.created_at,
                              m.attachment_name, m.attachment_size, m.is_deleted,
                              COALESCE(NULLIF(sp.display_name,''), NULLIF(su.name,''), 'Участник') AS sender_name,
                              CASE WHEN LOWER(COALESCE(su.plan,'free'))='premium'
                                      AND COALESCE(su.subscription_until,0) > EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                                   THEN 'premium' ELSE 'free' END AS sender_plan
                       FROM community_direct_messages m
                       JOIN users su ON su.user_id=m.sender_id
                       LEFT JOIN community_profiles sp ON sp.user_id=su.user_id
                       WHERE ((m.sender_id=%s AND m.recipient_id=%s) OR (m.sender_id=%s AND m.recipient_id=%s))
                       ORDER BY m.id DESC LIMIT %s""",
                    (uid, peer_uid, peer_uid, uid, safe_limit),
                )
                messages = [dict(row) for row in (cur.fetchall() or [])]
                messages.reverse()
                peer_name = str(peer.get("name") or "").strip() or f"Участник {str(peer.get('april_id') or '')[-4:]}"
                cur.execute("SELECT display_name FROM community_profiles WHERE user_id=%s", (peer_uid,))
                profile_row = cur.fetchone() or {}
                peer_name = str(profile_row.get("display_name") or peer_name).strip()[:32]
                return {
                    "success": True,
                    "messages": [_community_direct_payload(row, current_user_id=uid, peer_april_id=str(peer.get("april_id") or peer_april_id)) for row in messages],
                    "peer": {"april_id": str(peer.get("april_id") or ""), "display_name": peer_name, "plan": _community_active_plan(peer)},
                }
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] DIRECT_READ_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def create_community_direct_message(
    user_id: Any, peer_april_id: Any, message: Any, *,
    attachment_name: str | None = None, attachment_mime: str | None = None,
    attachment_data: bytes | None = None,
) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    text_value = str(message or "").replace("\x00", "").strip()
    if len(text_value) > COMMUNITY_MAX_MESSAGE_CHARS:
        return {"success": False, "error": "MESSAGE_TOO_LONG"}
    original_name = str(attachment_name or "").replace("\\", "/").split("/")[-1].strip()
    binary = bytes(attachment_data) if attachment_data is not None else None
    if binary is not None and (not binary or len(binary) > COMMUNITY_MAX_ATTACHMENT_BYTES):
        return {"success": False, "error": "ATTACHMENT_TOO_LARGE_OR_EMPTY"}
    if binary is not None and os.path.splitext(original_name)[1].lower() in _COMMUNITY_BLOCKED_EXTENSIONS:
        return {"success": False, "error": "ATTACHMENT_TYPE_BLOCKED"}
    if not text_value and binary is None:
        return {"success": False, "error": "MESSAGE_OR_FILE_REQUIRED"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                peer = _community_find_target(cur, peer_april_id, uid)
                if not peer:
                    return {"success": False, "error": "COMMUNITY_USER_NOT_FOUND"}
                peer_uid = _community_require_friends(cur, uid, peer)
                if not peer_uid:
                    return {"success": False, "error": "FRIENDS_REQUIRED"}
                pair_key = _community_direct_pair_key(uid, peer_uid)
                _community_lock_history(cur, "direct", pair_key)
                _community_prune_direct_history(cur, uid, peer_uid)
                cur.execute("SELECT COUNT(*) AS amount FROM community_direct_messages WHERE sender_id=%s AND created_at > NOW() - INTERVAL '1 minute' AND is_deleted=FALSE", (uid,))
                if int((cur.fetchone() or {}).get("amount") or 0) >= 30:
                    return {"success": False, "error": "RATE_LIMITED"}
                if binary is not None:
                    cur.execute("SELECT COALESCE(SUM(attachment_size),0) AS used FROM community_direct_messages WHERE sender_id=%s AND is_deleted=FALSE", (uid,))
                    used_bytes = int((cur.fetchone() or {}).get("used") or 0)
                    if used_bytes + len(binary) > COMMUNITY_USER_ATTACHMENT_QUOTA_BYTES:
                        return {"success": False, "error": "COMMUNITY_ATTACHMENT_QUOTA_REACHED"}
                cur.execute(
                    """INSERT INTO community_direct_messages(
                           sender_id, recipient_id, message, attachment_name, attachment_mime, attachment_size, attachment_data)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       RETURNING id, sender_id, recipient_id, message, created_at, attachment_name, attachment_size, is_deleted""",
                    (uid, peer_uid, text_value, original_name or None, str(attachment_mime or "application/octet-stream")[:160] if binary is not None else None, len(binary) if binary is not None else None, binary),
                )
                row = dict(cur.fetchone() or {})
                row["sender_name"] = ""
                cur.execute("SELECT COALESCE(NULLIF(p.display_name,''),NULLIF(u.name,''),'Участник') AS sender_name, CASE WHEN LOWER(COALESCE(u.plan,'free'))='premium' AND COALESCE(u.subscription_until,0)>EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) THEN 'premium' ELSE 'free' END AS sender_plan FROM users u LEFT JOIN community_profiles p ON p.user_id=u.user_id WHERE u.user_id=%s", (uid,))
                details = dict(cur.fetchone() or {})
                row.update(details)
                _community_prune_direct_history(cur, uid, peer_uid)
                return {"success": True, "message": _community_direct_payload(row, current_user_id=uid, peer_april_id=str(peer.get("april_id") or peer_april_id))}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] DIRECT_CREATE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def get_community_direct_file(user_id: Any, peer_april_id: Any, message_id: Any) -> dict[str, Any] | None:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    try:
        mid = int(message_id)
        if mid <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                peer = _community_find_target(cur, peer_april_id, uid)
                if not peer or not _community_require_friends(cur, uid, peer):
                    return {"success": False, "error": "COMMUNITY_FILE_NOT_FOUND"}
                peer_uid = str(peer.get("user_id") or "")
                cur.execute(
                    """SELECT attachment_data AS data, attachment_name AS name, attachment_mime AS mime
                       FROM community_direct_messages
                       WHERE id=%s AND is_deleted=FALSE AND attachment_data IS NOT NULL
                         AND ((sender_id=%s AND recipient_id=%s) OR (sender_id=%s AND recipient_id=%s))
                       LIMIT 1""",
                    (mid, uid, peer_uid, peer_uid, uid),
                )
                row = cur.fetchone()
                if not row:
                    return {"success": False, "error": "COMMUNITY_FILE_NOT_FOUND"}
                return {"success": True, "data": bytes(row.get("data") or b""), "name": str(row.get("name") or "shared-file"), "mime": str(row.get("mime") or "application/octet-stream")}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] DIRECT_FILE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def delete_community_direct_message(user_id: Any, message_id: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    try:
        mid = int(message_id)
        if mid <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE community_direct_messages SET is_deleted=TRUE, message='', attachment_name=NULL, attachment_mime=NULL, attachment_size=NULL, attachment_data=NULL WHERE id=%s AND sender_id=%s AND is_deleted=FALSE RETURNING id", (mid, uid))
                if not cur.fetchone():
                    return {"success": False, "error": "MESSAGE_NOT_FOUND_OR_NOT_OWNED"}
                return {"success": True}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] DIRECT_DELETE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()

def get_community_snapshot(user_id: Any, *, limit: int = 50, before_id: int | None = None) -> dict[str, Any] | None:
    """Read at most the latest 30 public community messages and the server nickname."""
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    safe_limit = max(1, min(COMMUNITY_HISTORY_MAX_MESSAGES, int(limit or 50)))
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                _community_lock_history(cur, "public")
                _community_prune_public_history(cur)
                cur.execute(
                    """SELECT u.name, u.april_id, LOWER(COALESCE(u.plan, 'free')) AS plan,
                              COALESCE(u.subscription_until, 0) AS subscription_until,
                              p.display_name, p.is_custom
                       FROM users u LEFT JOIN community_profiles p ON p.user_id = u.user_id
                       WHERE u.user_id = %s LIMIT 1""",
                    (uid,),
                )
                profile = cur.fetchone() or {}
                default_name = str(profile.get("name") or "").strip()
                if not default_name:
                    suffix = str(profile.get("april_id") or uid)[-4:]
                    default_name = f"Участник {suffix}"
                display_name = str(profile.get("display_name") or default_name).strip()[:32]
                if not profile.get("display_name"):
                    cur.execute(
                        """INSERT INTO community_profiles(user_id, display_name, is_custom)
                           VALUES (%s, %s, FALSE) ON CONFLICT (user_id) DO NOTHING""",
                        (uid, display_name),
                    )
                if before_id and int(before_id) > 0:
                    cur.execute(
                        """SELECT m.id, m.user_id, m.display_name, m.message, m.created_at,
                                  m.attachment_name, m.attachment_size, m.is_deleted,
                                  CASE WHEN LOWER(COALESCE(u.plan,'free'))='premium'
                                            AND COALESCE(u.subscription_until,0)>EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                                       THEN 'premium' ELSE 'free' END AS author_plan
                           FROM community_messages m JOIN users u ON u.user_id=m.user_id
                           WHERE m.id < %s ORDER BY m.id DESC LIMIT %s""",
                        (int(before_id), safe_limit),
                    )
                else:
                    cur.execute(
                        """SELECT m.id, m.user_id, m.display_name, m.message, m.created_at,
                                  m.attachment_name, m.attachment_size, m.is_deleted,
                                  CASE WHEN LOWER(COALESCE(u.plan,'free'))='premium'
                                            AND COALESCE(u.subscription_until,0)>EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
                                       THEN 'premium' ELSE 'free' END AS author_plan
                           FROM community_messages m JOIN users u ON u.user_id=m.user_id
                           ORDER BY m.id DESC LIMIT %s""",
                        (safe_limit,),
                    )
                rows = list(cur.fetchall() or [])
                rows.reverse()
                messages = []
                for row in rows:
                    item = dict(row)
                    item["is_own"] = str(item.get("user_id") or "") == uid
                    messages.append(_community_payload(item))
                active_premium = (
                    str(profile.get("plan") or "free").lower() == "premium"
                    and float(profile.get("subscription_until") or 0) > now().timestamp()
                )
                return {
                    "success": True,
                    "messages": messages,
                    "profile": {"display_name": display_name, "is_custom": bool(profile.get("is_custom"))},
                    "plan": "premium" if active_premium else "free",
                    "can_post": True,
                    "max_message_chars": COMMUNITY_MAX_MESSAGE_CHARS,
                    "max_attachment_bytes": COMMUNITY_MAX_ATTACHMENT_BYTES,
                }
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] SNAPSHOT_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def save_community_display_name(user_id: Any, display_name: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    name = re.sub(r"\s+", " ", str(display_name or "")).strip()
    if not (2 <= len(name) <= 32) or not re.fullmatch(r"[\w .’'-]+", name, flags=re.UNICODE):
        return {"success": False, "error": "INVALID_DISPLAY_NAME"}
    if name.casefold() in {"admin", "administrator", "moderator", "support", "админ", "администратор", "модератор", "техподдержка"}:
        return {"success": False, "error": "RESERVED_DISPLAY_NAME"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO community_profiles(user_id, display_name, is_custom, updated_at)
                       VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
                       ON CONFLICT (user_id) DO UPDATE SET
                         display_name = EXCLUDED.display_name,
                         is_custom = TRUE,
                         updated_at = CURRENT_TIMESTAMP
                       RETURNING display_name""",
                    (uid, name),
                )
                row = cur.fetchone() or {}
                return {"success": True, "profile": {"display_name": str(row.get("display_name") or name)}}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] PROFILE_SAVE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def reset_community_display_name(user_id: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, april_id FROM users WHERE user_id = %s LIMIT 1", (uid,))
                user = cur.fetchone() or {}
                name = str(user.get("name") or "").strip()
                if not name:
                    name = f"Участник {str(user.get('april_id') or uid)[-4:]}"
                name = name[:32]
                cur.execute(
                    """INSERT INTO community_profiles(user_id, display_name, is_custom, updated_at)
                       VALUES (%s, %s, FALSE, CURRENT_TIMESTAMP)
                       ON CONFLICT (user_id) DO UPDATE SET
                         display_name = EXCLUDED.display_name,
                         is_custom = FALSE,
                         updated_at = CURRENT_TIMESTAMP
                       RETURNING display_name""",
                    (uid, name),
                )
                row = cur.fetchone() or {}
                return {"success": True, "profile": {"display_name": str(row.get("display_name") or name), "is_custom": False}}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] PROFILE_RESET_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def create_community_message(
    user_id: Any,
    message: Any,
    *,
    attachment_name: Any = None,
    attachment_mime: Any = None,
    attachment_data: bytes | None = None,
) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    text_value = str(message or "").strip()
    binary = bytes(attachment_data) if attachment_data is not None else None
    if len(text_value) > COMMUNITY_MAX_MESSAGE_CHARS:
        return {"success": False, "error": "MESSAGE_TOO_LONG"}
    if not text_value and not binary:
        return {"success": False, "error": "MESSAGE_OR_FILE_REQUIRED"}
    if binary is not None and (not binary or len(binary) > COMMUNITY_MAX_ATTACHMENT_BYTES):
        return {"success": False, "error": "ATTACHMENT_TOO_LARGE_OR_EMPTY"}

    safe_name = None
    safe_mime = None
    if binary is not None:
        original_name = str(attachment_name or "shared-file").replace("\\", "/").split("/")[-1].strip()
        original_name = "".join(ch for ch in original_name if ch.isprintable() and ch not in "\r\n\x00")[:160]
        if not original_name or original_name in {".", ".."}:
            original_name = "shared-file"
        if os.path.splitext(original_name)[1].lower() in _COMMUNITY_BLOCKED_EXTENSIONS:
            return {"success": False, "error": "ATTACHMENT_TYPE_BLOCKED"}
        safe_name = original_name
        safe_mime = str(attachment_mime or "application/octet-stream").split(";", 1)[0].strip().lower()[:120]
        if not re.fullmatch(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", safe_mime):
            safe_mime = "application/octet-stream"

    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                _community_lock_history(cur, "public")
                _community_prune_public_history(cur)
                cur.execute(
                    """SELECT u.name, u.april_id, p.display_name,
                              LOWER(COALESCE(u.plan,'free')) AS plan,
                              COALESCE(u.subscription_until,0) AS subscription_until
                       FROM users u LEFT JOIN community_profiles p ON p.user_id = u.user_id
                       WHERE u.user_id = %s LIMIT 1""",
                    (uid,),
                )
                profile = cur.fetchone() or {}
                display_name = str(profile.get("display_name") or profile.get("name") or "").strip()
                if not display_name:
                    display_name = f"Участник {str(profile.get('april_id') or uid)[-4:]}"
                display_name = display_name[:32]
                if not profile.get("display_name"):
                    cur.execute(
                        """INSERT INTO community_profiles(user_id, display_name, is_custom)
                           VALUES (%s, %s, FALSE) ON CONFLICT (user_id) DO NOTHING""",
                        (uid, display_name),
                    )
                cur.execute(
                    "SELECT COUNT(*) AS amount FROM community_messages WHERE user_id = %s AND created_at > NOW() - INTERVAL '1 minute'",
                    (uid,),
                )
                if int((cur.fetchone() or {}).get("amount") or 0) >= COMMUNITY_RATE_LIMIT_PER_MINUTE:
                    return {"success": False, "error": "RATE_LIMITED"}
                if binary is not None:
                    cur.execute(
                        """SELECT COALESCE(SUM(attachment_size), 0) AS used_bytes
                           FROM community_messages
                           WHERE user_id = %s AND is_deleted = FALSE""",
                        (uid,),
                    )
                    used_bytes = int((cur.fetchone() or {}).get("used_bytes") or 0)
                    if used_bytes + len(binary) > COMMUNITY_USER_ATTACHMENT_QUOTA_BYTES:
                        return {"success": False, "error": "COMMUNITY_ATTACHMENT_QUOTA_REACHED"}
                cur.execute(
                    """INSERT INTO community_messages(
                           user_id, display_name, message, attachment_name,
                           attachment_mime, attachment_size, attachment_data
                       ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING id, user_id, display_name, message, created_at,
                                 attachment_name, attachment_size, is_deleted""",
                    (uid, display_name, text_value, safe_name, safe_mime, len(binary) if binary is not None else None, binary),
                )
                row = dict(cur.fetchone() or {})
                row["is_own"] = True
                row["author_plan"] = _community_active_plan(profile)
                _community_prune_public_history(cur)
                return {"success": True, "message": _community_payload(row)}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] MESSAGE_CREATE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def get_community_file(user_id: Any, message_id: Any) -> dict[str, Any] | None:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    try:
        mid = int(message_id)
    except (TypeError, ValueError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    if mid <= 0:
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT attachment_name, attachment_mime, attachment_size, attachment_data
                       FROM community_messages WHERE id = %s AND is_deleted = FALSE LIMIT 1""",
                    (mid,),
                )
                row = cur.fetchone()
                if not row or row.get("attachment_data") is None:
                    return {"success": False, "error": "COMMUNITY_FILE_NOT_FOUND"}
                return {
                    "success": True,
                    "name": str(row.get("attachment_name") or "shared-file"),
                    "mime": str(row.get("attachment_mime") or "application/octet-stream"),
                    "size": int(row.get("attachment_size") or 0),
                    "data": bytes(row.get("attachment_data") or b""),
                }
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] FILE_READ_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def delete_community_message(user_id: Any, message_id: Any) -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    try:
        mid = int(message_id)
    except (TypeError, ValueError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE community_messages
                       SET is_deleted = TRUE, message = '', attachment_name = NULL,
                           attachment_mime = NULL, attachment_size = NULL, attachment_data = NULL
                       WHERE id = %s AND user_id = %s AND is_deleted = FALSE""",
                    (mid, uid),
                )
                if cur.rowcount != 1:
                    return {"success": False, "error": "MESSAGE_NOT_FOUND_OR_NOT_OWNED"}
                return {"success": True, "message_id": mid}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] MESSAGE_DELETE_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()


def report_community_message(user_id: Any, message_id: Any, reason: Any = "inappropriate") -> dict[str, Any]:
    uid = _community_canonical_user(user_id)
    if not uid:
        return {"success": False, "error": "AUTHENTICATED_USER_REQUIRED"}
    try:
        mid = int(message_id)
    except (TypeError, ValueError):
        return {"success": False, "error": "MESSAGE_ID_INVALID"}
    safe_reason = str(reason or "inappropriate").strip().lower()[:40]
    if safe_reason not in {"inappropriate", "spam", "abuse", "malware", "other"}:
        safe_reason = "other"
    conn = get_conn()
    if not conn:
        return {"success": False, "error": "DATABASE_UNAVAILABLE"}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM community_messages WHERE id = %s AND user_id <> %s AND is_deleted = FALSE", (mid, uid))
                if not cur.fetchone():
                    return {"success": False, "error": "MESSAGE_NOT_FOUND"}
                cur.execute(
                    """INSERT INTO community_message_reports(message_id, reporter_user_id, reason)
                       VALUES (%s, %s, %s) ON CONFLICT (message_id, reporter_user_id) DO NOTHING""",
                    (mid, uid, safe_reason),
                )
                return {"success": True, "reported": cur.rowcount == 1}
    except Exception as exc:
        print(f"[APRIL_COMMUNITY] MESSAGE_REPORT_FAILED type={type(exc).__name__}", flush=True)
        return {"success": False, "error": "COMMUNITY_UNAVAILABLE"}
    finally:
        conn.close()
