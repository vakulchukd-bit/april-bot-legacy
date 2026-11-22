"""C_VIDEO: one canonical room for April video analysis, generation and editing.

Provider integration, April Video Credits, USD package orders, reservation and settlement
stay together in this module. A narrowly allow-listed test mode can use the
provider account's trial credits without asserting commercial rights. Local
FFmpeg edits remain free. Binary output is returned to the active Free or Premium executor for
authenticated artifact persistence and canonical rendering. Temporary provider URLs
never leave this module.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from urllib.parse import quote
from pathlib import Path
from typing import Any, Callable

MAX_VIDEO_BYTES = 25 * 1024 * 1024
MAX_VIDEO_INPUT_BYTES = 10 * 1024 * 1024
MAX_VIDEO_FRAMES = 8
VIDEO_DEFAULT_DURATION_SECONDS = 3
VIDEO_MAX_DURATION_SECONDS = 60
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi"}


class CVideoError(RuntimeError):
    """Expected, safe-to-report video operation failure."""

# ---------------------------------------------------------------------------
# Authenticated Video Wallet. All video billing data/logic stays inside C_VIDEO.
# Amounts are stored as USD cents; provider credits and the 2x markup are kept
# separately for an auditable, idempotent settlement trail.
# ---------------------------------------------------------------------------

def _wallet_identity(user_id: Any) -> str:
    from storage import resolve_user_id, is_authenticated_user
    canonical = resolve_user_id(user_id)
    if not canonical or not is_authenticated_user(canonical):
        raise CVideoError("VIDEO_WALLET_AUTH_REQUIRED")
    return canonical


def _env_enabled(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _video_test_allowlist() -> set[str]:
    raw = os.getenv("APRIL_VIDEO_TEST_USER_IDS", "")
    return {part.strip() for part in re.split(r"[,;\s]+", raw) if part.strip()}


def is_video_test_account(user_id: Any) -> bool:
    """Return true only for an authenticated account explicitly allow-listed for tests.

    APRIL_VIDEO_TEST_USER_IDS accepts either users.user_id or public users.april_id.
    The test flag alone never exposes the provider to every April account.
    """
    if not _env_enabled("APRIL_VIDEO_TEST_MODE") or not _text(user_id):
        return False
    allowlist = _video_test_allowlist()
    if not allowlist:
        return False
    raw = _text(user_id)
    try:
        canonical = _wallet_identity(raw)
    except Exception:
        return False
    return raw in allowlist or canonical in allowlist


def _magic_hour_billing_mode(user_id: Any) -> str:
    """Resolve provider-use mode without conflating trial tests and commercial use."""
    if is_video_test_account(user_id):
        return "test_bonus"
    if _env_enabled("MAGIC_HOUR_COMMERCIAL_RIGHTS_CONFIRMED"):
        return "commercial"
    if _env_enabled("APRIL_VIDEO_TEST_MODE"):
        raise CVideoError("MAGIC_HOUR_TEST_ACCOUNT_NOT_ALLOWED")
    raise CVideoError("MAGIC_HOUR_COMMERCIAL_RIGHTS_NOT_CONFIRMED")


def magic_hour_video_ready(user_id: Any) -> bool:
    """Cheap readiness check used by the active executor before publishing its pending scene."""
    if not os.getenv("MAGIC_HOUR_API_KEY", "").strip():
        return False
    if os.getenv("APRIL_VIDEO_GENERATION_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return False
    try:
        _video_cost_per_1000_credits(user_id)
        return bool(_magic_hour_billing_mode(user_id))
    except (CVideoError, TypeError, ValueError, OverflowError):
        return False


def _wallet_connection():
    from storage import get_conn
    conn = get_conn()
    if conn is None:
        raise CVideoError("VIDEO_WALLET_DATABASE_UNAVAILABLE")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS april_video_wallets (
                    user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                    balance_minor BIGINT NOT NULL DEFAULT 0,
                    balance_credits BIGINT NOT NULL DEFAULT 0,
                    debt_credits BIGINT NOT NULL DEFAULT 0,
                    credits_migrated BOOLEAN NOT NULL DEFAULT FALSE,
                    credit_conversion_version INTEGER NOT NULL DEFAULT 0,
                    enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS april_video_wallet_transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    reference TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    delta_minor BIGINT NOT NULL DEFAULT 0,
                    delta_credits BIGINT NOT NULL DEFAULT 0,
                    provider_cost_minor BIGINT NOT NULL DEFAULT 0,
                    provider_credits BIGINT NOT NULL DEFAULT 0,
                    markup_multiplier NUMERIC(8,3) NOT NULL DEFAULT 2,
                    operation TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS april_video_wallet_orders (
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    amount_minor BIGINT NOT NULL,
                    credits_to_issue BIGINT NOT NULL DEFAULT 0,
                    usd_per_1000_provider_credits NUMERIC(14,6) NOT NULL DEFAULT 0,
                    markup_multiplier NUMERIC(8,3) NOT NULL DEFAULT 2,
                    billing_mode TEXT NOT NULL DEFAULT 'test_bonus',
                    credit_pricing_version INTEGER NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    payment_status TEXT NOT NULL DEFAULT 'pending',
                    payment_source TEXT NOT NULL DEFAULT 'liqpay_google_pay',
                    provider_payment_id TEXT UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    paid_at TIMESTAMPTZ
                )
            """)
            cur.execute("ALTER TABLE april_video_wallets ADD COLUMN IF NOT EXISTS balance_credits BIGINT NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE april_video_wallets ADD COLUMN IF NOT EXISTS debt_credits BIGINT NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE april_video_wallets ADD COLUMN IF NOT EXISTS credits_migrated BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE april_video_wallets ADD COLUMN IF NOT EXISTS credit_conversion_version INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE april_video_wallet_transactions ADD COLUMN IF NOT EXISTS delta_credits BIGINT NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE april_video_wallet_orders ADD COLUMN IF NOT EXISTS credits_to_issue BIGINT NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE april_video_wallet_orders ADD COLUMN IF NOT EXISTS usd_per_1000_provider_credits NUMERIC(14,6) NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE april_video_wallet_orders ADD COLUMN IF NOT EXISTS markup_multiplier NUMERIC(8,3) NOT NULL DEFAULT 2")
            cur.execute("ALTER TABLE april_video_wallet_orders ADD COLUMN IF NOT EXISTS billing_mode TEXT NOT NULL DEFAULT 'test_bonus'")
            cur.execute("ALTER TABLE april_video_wallet_orders ADD COLUMN IF NOT EXISTS credit_pricing_version INTEGER NOT NULL DEFAULT 0")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_april_video_wallet_tx_user_created ON april_video_wallet_transactions(user_id, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_april_video_wallet_orders_user_created ON april_video_wallet_orders(user_id, created_at DESC)")
        conn.commit()
        return conn
    except Exception:
        conn.rollback()
        conn.close()
        raise


def _april_credits_for_usd_minor(amount_minor: int, usd_per_1000_provider_credits: Any) -> int:
    """Convert a USD payment into internal wallet units.

    One visible April Video Credit is backed by two internal units. The 2x
    customer price is applied once when credits are purchased; video operations
    consume two internal units per provider credit. The cabinet exposes only
    visible credits (internal units / 2), never the internal multiplier.
    """
    rate = Decimal(str(usd_per_1000_provider_credits))
    if rate <= 0:
        raise CVideoError("VIDEO_WALLET_PRICING_NOT_CONFIGURED")
    amount_minor = max(0, int(amount_minor or 0))
    # rate is the provider's cost in USD per 1,000 provider credits.
    # customer pays 2x, so USD cents convert to 2x internal units.
    internal_units = (Decimal(amount_minor) * Decimal("10") / rate).to_integral_value(rounding=ROUND_FLOOR)
    return max(0, int(internal_units))


def _usd_minor_for_april_credits(internal_units: int, usd_per_1000_provider_credits: Any) -> int:
    """Return the user-facing USD equivalent for internal wallet units."""
    rate = Decimal(str(usd_per_1000_provider_credits))
    if rate <= 0:
        raise CVideoError("VIDEO_WALLET_PRICING_NOT_CONFIGURED")
    value = Decimal(max(0, int(internal_units or 0))) * rate / Decimal("10")
    return int(value.to_integral_value(rounding=ROUND_CEILING)) if value else 0


def _rebalance_net_units(balance_units: int, debt_units: int, delta_net_units: int) -> tuple[int, int]:
    """Apply a one-time historical credit correction without losing consumed value."""
    net = int(balance_units or 0) - int(debt_units or 0) + int(delta_net_units or 0)
    return (net, 0) if net >= 0 else (0, -net)


def _ensure_wallet_credit_state(cur: Any, user_id: str, unit_cost: Any) -> dict[str, int]:
    """Migrate legacy USD balances and repair the earlier over-credit conversion once."""
    cur.execute("""
        SELECT balance_minor, balance_credits, debt_credits, credits_migrated,
               credit_conversion_version
        FROM april_video_wallets WHERE user_id=%s FOR UPDATE
    """, (user_id,))
    wallet = cur.fetchone()
    if not wallet:
        raise CVideoError("VIDEO_WALLET_NOT_ENABLED")

    balance = int(wallet.get("balance_credits") or 0)
    debt = int(wallet.get("debt_credits") or 0)
    version = int(wallet.get("credit_conversion_version") or 0)

    if not bool(wallet.get("credits_migrated")):
        legacy_balance_minor = int(wallet.get("balance_minor") or 0)
        legacy_minor = max(0, legacy_balance_minor)
        legacy_debt_minor = max(0, -legacy_balance_minor)
        migrated_units = _april_credits_for_usd_minor(legacy_minor, unit_cost)
        migrated_debt_units = _april_credits_for_usd_minor(legacy_debt_minor, unit_cost)
        balance = migrated_units
        debt = migrated_debt_units
        cur.execute("""
            UPDATE april_video_wallets
            SET balance_minor=0, balance_credits=%s, debt_credits=%s,
                credits_migrated=TRUE, credit_conversion_version=3, updated_at=NOW()
            WHERE user_id=%s
        """, (balance, debt, user_id))
        safe_user = re.sub(r"[^A-Za-z0-9._:-]", "", user_id)[:80] or uuid.uuid4().hex
        if legacy_minor > 0:
            cur.execute("""
                INSERT INTO april_video_wallet_transactions
                    (user_id, reference, kind, status, delta_minor, delta_credits,
                     operation, description, metadata)
                VALUES (%s, %s, 'migration', 'completed', %s, %s,
                        'migration', 'Legacy USD balance converted to April Video Credits', %s::jsonb)
                ON CONFLICT(reference) DO NOTHING
            """, (user_id, f"migration:usd-wallet-v1:{safe_user}", legacy_minor, migrated_units,
                  json.dumps({"legacy_balance_minor": legacy_minor,
                              "usd_per_1000_provider_credits": float(unit_cost),
                              "credit_conversion_version": 3,
                              "conversion": "USD / (2x provider cost per credit); two internal units per visible April credit"})))
        if legacy_debt_minor > 0:
            cur.execute("""
                INSERT INTO april_video_wallet_transactions
                    (user_id, reference, kind, status, delta_minor, delta_credits,
                     operation, description, metadata)
                VALUES (%s, %s, 'migration_debt', 'completed', %s, %s,
                        'migration', 'Legacy wallet overage converted to credit debt', %s::jsonb)
                ON CONFLICT(reference) DO NOTHING
            """, (user_id, f"migration:usd-wallet-v1-debt:{safe_user}", -legacy_debt_minor, -migrated_debt_units,
                  json.dumps({"legacy_debt_minor": legacy_debt_minor,
                              "usd_per_1000_provider_credits": float(unit_cost),
                              "credit_conversion_version": 3})))
        version = 3

    elif version < 3:
        # Previous Stage-1 migration could grant 100,000 credits per dollar if
        # APRIL_MAGIC_HOUR_USD_PER_1000_CREDITS was mis-set. Reprice every
        # historical migration/top-up issuance from its original USD amount.
        cur.execute("""
            SELECT id, reference, kind, delta_minor, delta_credits, metadata
            FROM april_video_wallet_transactions
            WHERE user_id=%s AND kind IN ('migration', 'migration_debt', 'topup', 'reversal')
            ORDER BY created_at ASC, id ASC
            FOR UPDATE
        """, (user_id,))
        rows = cur.fetchall() or []
        net_adjustment = 0
        for row in rows:
            meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if int(meta.get("credit_conversion_version") or meta.get("credit_pricing_version") or 0) >= 3:
                continue
            old_delta = int(row.get("delta_credits") or 0)
            kind = _text(row.get("kind")).lower()
            if kind == "migration":
                original_minor = max(0, int(meta.get("legacy_balance_minor") or row.get("delta_minor") or 0))
                if original_minor <= 0:
                    continue
                target_delta = _april_credits_for_usd_minor(original_minor, unit_cost)
            elif kind == "migration_debt":
                original_minor = max(0, int(meta.get("legacy_debt_minor") or abs(int(row.get("delta_minor") or 0))))
                if original_minor <= 0:
                    continue
                target_delta = -_april_credits_for_usd_minor(original_minor, unit_cost)
            elif kind == "topup":  # historical paid top-up
                original_minor = max(0, int(row.get("delta_minor") or 0))
                if original_minor <= 0 or old_delta <= 0:
                    continue
                target_delta = _april_credits_for_usd_minor(original_minor, unit_cost)
                old_repaid = max(0, int(meta.get("debt_repaid") or 0))
                old_spendable = max(0, int(meta.get("spendable_credits", old_delta - old_repaid) or 0))
                target_repaid = min(target_delta, old_repaid)
                target_spendable = max(0, target_delta - target_repaid)
                meta["debt_repaid"] = target_repaid
                meta["spendable_credits"] = target_spendable
                order_id = _text(meta.get("order_id"))
                if order_id:
                    cur.execute("""
                        UPDATE april_video_wallet_orders
                        SET credits_to_issue=%s, usd_per_1000_provider_credits=%s,
                            markup_multiplier=2, credit_pricing_version=3
                        WHERE order_id=%s AND user_id=%s
                    """, (target_delta, unit_cost, order_id, user_id))
            else:  # payment reversal must be repriced with its original top-up
                order_id = _text(meta.get("order_id"))
                if not order_id:
                    continue
                cur.execute("""
                    SELECT delta_credits, delta_minor FROM april_video_wallet_transactions
                    WHERE user_id=%s AND reference=%s AND kind='topup'
                    FOR UPDATE
                """, (user_id, "topup:" + order_id))
                original_topup = cur.fetchone() or {}
                original_minor = max(0, int(original_topup.get("delta_minor") or abs(int(row.get("delta_minor") or 0))))
                if original_minor <= 0:
                    continue
                target_delta = -_april_credits_for_usd_minor(original_minor, unit_cost)
            if target_delta != old_delta:
                net_adjustment += target_delta - old_delta
                meta["previous_delta_credits"] = old_delta
                meta["credit_conversion_version"] = 3
                meta["credit_pricing_version"] = 3
                meta["reconciled_from_usd_minor"] = original_minor
                cur.execute("""
                    UPDATE april_video_wallet_transactions
                    SET delta_credits=%s, metadata=%s::jsonb, updated_at=NOW()
                    WHERE id=%s
                """, (target_delta, json.dumps(meta), int(row["id"])))
            else:
                meta["credit_conversion_version"] = 3
                meta["credit_pricing_version"] = 3
                cur.execute("""
                    UPDATE april_video_wallet_transactions
                    SET metadata=%s::jsonb, updated_at=NOW() WHERE id=%s
                """, (json.dumps(meta), int(row["id"])))

        balance, debt = _rebalance_net_units(balance, debt, net_adjustment)
        cur.execute("""
            UPDATE april_video_wallets
            SET balance_credits=%s, debt_credits=%s,
                credit_conversion_version=3, updated_at=NOW()
            WHERE user_id=%s
        """, (balance, debt, user_id))
        version = 3

    return {"balance_credits": balance, "debt_credits": debt}


def enable_video_wallet(user_id: Any) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO april_video_wallets(user_id, enabled, credits_migrated)
                VALUES (%s, TRUE, FALSE)
                ON CONFLICT(user_id) DO UPDATE SET enabled=TRUE, updated_at=NOW()
                RETURNING balance_minor, balance_credits, debt_credits, enabled, currency, credits_migrated
            """, (canonical,))
            row = dict(cur.fetchone() or {})
            pricing_ready = False
            try:
                unit_cost = _video_cost_per_1000_credits(canonical)
                credit_state = _ensure_wallet_credit_state(cur, canonical, unit_cost)
                row.update(credit_state)
                pricing_ready = True
            except CVideoError as exc:
                if str(exc) not in {
                    "APRIL_VIDEO_TEST_COST_NOT_CONFIGURED", "APRIL_MAGIC_HOUR_COST_NOT_CONFIGURED",
                    "MAGIC_HOUR_TEST_ACCOUNT_NOT_ALLOWED", "MAGIC_HOUR_COMMERCIAL_RIGHTS_NOT_CONFIRMED",
                }:
                    raise
        conn.commit()
        return {
            "success": True, "enabled": bool(row.get("enabled")),
            "balance_credits": int(row.get("balance_credits") or 0) // 2,
            "debt_credits": (int(row.get("debt_credits") or 0) + 1) // 2,
            "currency": row.get("currency") or "USD", "pricing_ready": pricing_ready,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_video_wallet_status(user_id: Any, *, limit: int = 8) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT balance_minor, balance_credits, debt_credits, credits_migrated,
                       credit_conversion_version, enabled, currency
                FROM april_video_wallets WHERE user_id=%s
            """, (canonical,))
            wallet = cur.fetchone() or {}
            pricing_ready = False
            unit_cost = None
            if wallet and wallet.get("enabled"):
                try:
                    unit_cost = _video_cost_per_1000_credits(canonical)
                    wallet.update(_ensure_wallet_credit_state(cur, canonical, unit_cost))
                    wallet["balance_minor"] = 0
                    pricing_ready = True
                except CVideoError as exc:
                    if str(exc) not in {
                        "APRIL_VIDEO_TEST_COST_NOT_CONFIGURED", "APRIL_MAGIC_HOUR_COST_NOT_CONFIGURED",
                        "MAGIC_HOUR_TEST_ACCOUNT_NOT_ALLOWED", "MAGIC_HOUR_COMMERCIAL_RIGHTS_NOT_CONFIRMED",
                    }:
                        raise
            cur.execute("""
                SELECT id, reference, kind, status, delta_minor, delta_credits,
                       provider_credits, operation, description, created_at
                FROM april_video_wallet_transactions
                WHERE user_id=%s
                ORDER BY created_at DESC, id DESC LIMIT %s
            """, (canonical, max(1, min(30, int(limit or 8)))))
            transactions = []
            for row in cur.fetchall() or []:
                item = dict(row)
                created = item.get("created_at")
                item["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created or "")
                provider_credits = max(0, int(item.get("provider_credits") or 0))
                internal_delta = int(item.get("delta_credits") or 0)
                # Legacy USD-wallet video rows did not persist delta_credits.
                if internal_delta == 0 and provider_credits and _text(item.get("kind")).lower() == "video_debit":
                    internal_delta = -provider_credits * 2
                item["delta_minor"] = int(item.get("delta_minor") or 0)
                if unit_cost is not None and provider_credits and _text(item.get("kind")).lower() == "video_debit":
                    _provider_minor, customer_minor = _video_price_for_credits(provider_credits, unit_cost)
                    item["delta_minor"] = -customer_minor
                item["delta_credits"] = int(internal_delta / 2)
                # Provider accounting and internal multiplier are deliberately private.
                item.pop("provider_credits", None)
                item.pop("markup_multiplier", None)
                item.pop("provider_cost_minor", None)
                transactions.append(item)
        conn.commit()
        balance_units = int(wallet.get("balance_credits") or 0) if wallet else 0
        debt_units = int(wallet.get("debt_credits") or 0) if wallet else 0
        return {
            "success": True,
            "enabled": bool(wallet.get("enabled")) if wallet else False,
            "balance_credits": balance_units // 2,
            "debt_credits": (debt_units + 1) // 2,
            "legacy_balance_minor": int(wallet.get("balance_minor") or 0) if wallet else 0,
            "currency": _text(wallet.get("currency") if wallet else "USD") or "USD",
            "pricing_ready": pricing_ready,
            "package_options": ([
                {"amount_usd": amount, "credits_to_issue": _april_credits_for_usd_minor(amount * 100, unit_cost) // 2}
                for amount in (5, 10, 20, 50)
            ] if unit_cost is not None else []),
            "transactions": transactions,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_video_wallet_topup_order(user_id: Any, amount_usd: Any) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    try:
        amount = int(amount_usd)
    except (TypeError, ValueError):
        raise CVideoError("VIDEO_WALLET_TOPUP_AMOUNT_INVALID")
    if amount not in {5, 10, 20, 50}:
        raise CVideoError("VIDEO_WALLET_TOPUP_AMOUNT_INVALID")
    billing_mode = _magic_hour_billing_mode(canonical)
    unit_cost = _video_cost_per_1000_credits(canonical)
    amount_minor = amount * 100
    credits_to_issue = _april_credits_for_usd_minor(amount_minor, unit_cost)
    if credits_to_issue <= 0:
        raise CVideoError("VIDEO_WALLET_CREDIT_PACKAGE_INVALID")
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT enabled FROM april_video_wallets WHERE user_id=%s FOR UPDATE", (canonical,))
            wallet = cur.fetchone()
            if not wallet or not wallet.get("enabled"):
                raise CVideoError("VIDEO_WALLET_NOT_ENABLED")
            _ensure_wallet_credit_state(cur, canonical, unit_cost)
            order_id = "APRIL-" + uuid.uuid4().hex[:24].upper()
            cur.execute("""
                INSERT INTO april_video_wallet_orders
                    (order_id, user_id, amount_minor, credits_to_issue,
                     usd_per_1000_provider_credits, markup_multiplier, billing_mode, credit_pricing_version, currency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 3, 'USD')
            """, (order_id, canonical, amount_minor, credits_to_issue,
                  unit_cost, _video_markup_multiplier(), billing_mode))
        conn.commit()
        return {
            "success": True, "order_id": order_id, "amount": amount,
            "amount_minor": amount_minor, "currency": "USD",
            "credits_to_issue": credits_to_issue // 2,
            "payment_status": "pending",
            "description": f"April Video Credits top-up ${amount}.",
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_video_wallet_order_status(user_id: Any, order_id: Any) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    order_key = _text(order_id)
    if not re.fullmatch(r"APRIL-[A-F0-9]{24}", order_key):
        return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_FOUND"}
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT order_id, amount_minor, credits_to_issue, currency,
                       payment_status, created_at, paid_at, credit_pricing_version
                FROM april_video_wallet_orders WHERE order_id=%s AND user_id=%s
            """, (order_key, canonical))
            row = cur.fetchone()
        conn.commit()
        if not row:
            return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_FOUND"}
        return {
            "success": True, "order_id": row["order_id"],
            "amount": round(int(row["amount_minor"]) / 100, 2),
            "amount_minor": int(row["amount_minor"]),
            "credits_to_issue": int(row.get("credits_to_issue") or 0) // 2,
            "currency": row["currency"], "payment_status": row["payment_status"],
            "created_at": row["created_at"].isoformat() if row.get("created_at") else "",
            "paid_at": row["paid_at"].isoformat() if row.get("paid_at") else "",
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def set_video_wallet_order_status(order_id: Any, status: str) -> dict[str, Any]:
    order_key = _text(order_id)
    target = _text(status).lower()
    if target not in {"failed", "cancelled", "reversed"}:
        return {"success": False, "error": "VIDEO_WALLET_ORDER_STATUS_INVALID"}
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM april_video_wallet_orders WHERE order_id=%s FOR UPDATE", (order_key,))
            order = cur.fetchone()
            if not order:
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_FOUND"}
            current = _text(order.get("payment_status")).lower()
            if current == target:
                conn.commit()
                return {"success": True, "order_id": order_key, "payment_status": target, "already_settled": True}
            if target == "reversed" and current == "paid":
                reversal_reference = "reversal:" + order_key
                cur.execute("""
                    SELECT delta_credits, metadata FROM april_video_wallet_transactions
                    WHERE user_id=%s AND reference=%s FOR UPDATE
                """, (order["user_id"], "topup:" + order_key))
                topup_tx = cur.fetchone() or {}
                topup_meta = topup_tx.get("metadata") if isinstance(topup_tx.get("metadata"), dict) else {}
                total_credits = max(0, int(topup_tx.get("delta_credits") or order.get("credits_to_issue") or 0))
                debt_repaid = max(0, int(topup_meta.get("debt_repaid") or 0))
                spendable_credits = max(0, int(topup_meta.get("spendable_credits") or (total_credits - debt_repaid)))
                cur.execute("""
                    INSERT INTO april_video_wallet_transactions
                        (user_id, reference, kind, status, delta_minor, delta_credits,
                         operation, description, metadata)
                    VALUES (%s, %s, 'reversal', 'completed', %s, %s,
                            'reversal', 'Video credits payment reversed', %s::jsonb)
                    ON CONFLICT(reference) DO NOTHING
                    RETURNING id
                """, (
                    order["user_id"], reversal_reference, -int(order["amount_minor"]),
                    -total_credits,
                    json.dumps({"order_id": order_key, "provider_payment_id": order.get("provider_payment_id"),
                                "debt_repaid_restored": debt_repaid, "spendable_credits_reversed": spendable_credits}),
                ))
                inserted = cur.fetchone()
                if inserted:
                    cur.execute("""
                        SELECT balance_credits, debt_credits FROM april_video_wallets
                        WHERE user_id=%s FOR UPDATE
                    """, (order["user_id"],))
                    wallet = cur.fetchone() or {}
                    available = max(0, int(wallet.get("balance_credits") or 0))
                    debt = max(0, int(wallet.get("debt_credits") or 0))
                    used = min(available, spendable_credits)
                    new_debt = debt + debt_repaid + max(0, spendable_credits - used)
                    cur.execute("""
                        UPDATE april_video_wallets
                        SET balance_credits=%s, debt_credits=%s, updated_at=NOW()
                        WHERE user_id=%s
                    """, (available - used, new_debt, order["user_id"]))
            elif current != "pending":
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_PENDING"}
            cur.execute("UPDATE april_video_wallet_orders SET payment_status=%s WHERE order_id=%s", (target, order_key))
        conn.commit()
        return {"success": True, "order_id": order_key, "payment_status": target}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def settle_video_wallet_topup(order_id: Any, provider_payment_id: Any, amount_minor: int, currency: str) -> dict[str, Any]:
    order_key = _text(order_id)
    payment_key = _text(provider_payment_id)
    if not order_key or not payment_key:
        return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_FOUND"}
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM april_video_wallet_orders WHERE order_id=%s FOR UPDATE", (order_key,))
            order = cur.fetchone()
            if not order:
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_FOUND"}
            if _text(order.get("payment_status")).lower() == "paid":
                conn.commit()
                return {
                    "success": True, "already_settled": True,
                    "order_id": order_key, "payment_status": "paid",
                    "user_id": order["user_id"],
                    "order_amount_minor": int(order["amount_minor"]),
                    "order_currency": order["currency"],
                    "credited_credits": int(order.get("credits_to_issue") or 0) // 2,
                }
            if _text(order.get("payment_status")).lower() != "pending":
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_PENDING"}
            if int(order["amount_minor"]) != int(amount_minor) or _text(order["currency"]).upper() != _text(currency).upper() or _text(currency).upper() != "USD":
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_PAYMENT_AMOUNT_MISMATCH"}

            unit_cost = Decimal(str(order.get("usd_per_1000_provider_credits") or 0))
            credits_to_issue = int(order.get("credits_to_issue") or 0)
            pricing_version = int(order.get("credit_pricing_version") or 0)
            if unit_cost <= 0 or credits_to_issue <= 0 or pricing_version < 3:
                # Upgrade a pending order created by the previous USD-wallet
                # version without changing its already-fixed payment amount.
                unit_cost = Decimal(str(_video_cost_per_1000_credits(order["user_id"])))
                credits_to_issue = _april_credits_for_usd_minor(int(order["amount_minor"]), unit_cost)
                if credits_to_issue <= 0:
                    conn.rollback()
                    return {"success": False, "error": "VIDEO_WALLET_ORDER_CREDIT_SNAPSHOT_INVALID"}
                billing_mode = _magic_hour_billing_mode(order["user_id"])
                cur.execute("""
                    UPDATE april_video_wallet_orders
                    SET credits_to_issue=%s, usd_per_1000_provider_credits=%s,
                        markup_multiplier=%s, billing_mode=%s, credit_pricing_version=3
                    WHERE order_id=%s
                """, (credits_to_issue, unit_cost, _video_markup_multiplier(), billing_mode, order_key))
                order["credits_to_issue"] = credits_to_issue
                order["usd_per_1000_provider_credits"] = unit_cost

            cur.execute("""
                INSERT INTO april_video_wallets(user_id, enabled, credits_migrated)
                VALUES (%s, TRUE, FALSE)
                ON CONFLICT(user_id) DO UPDATE SET enabled=TRUE, updated_at=NOW()
            """, (order["user_id"],))
            _ensure_wallet_credit_state(cur, str(order["user_id"]), unit_cost)
            cur.execute("""
                SELECT balance_credits, debt_credits FROM april_video_wallets
                WHERE user_id=%s FOR UPDATE
            """, (order["user_id"],))
            wallet = cur.fetchone() or {}
            current_debt = max(0, int(wallet.get("debt_credits") or 0))
            debt_repaid = min(current_debt, credits_to_issue)
            spendable_credits = credits_to_issue - debt_repaid
            cur.execute("""
                UPDATE april_video_wallets
                SET enabled=TRUE, balance_credits=balance_credits+%s,
                    debt_credits=GREATEST(0, debt_credits-%s), updated_at=NOW()
                WHERE user_id=%s
            """, (spendable_credits, debt_repaid, order["user_id"]))
            cur.execute("""
                INSERT INTO april_video_wallet_transactions
                    (user_id, reference, kind, status, delta_minor, delta_credits,
                     markup_multiplier, operation, description, metadata)
                VALUES (%s, %s, 'topup', 'completed', %s, %s, %s,
                        'topup', 'April Video Credits purchase', %s::jsonb)
                ON CONFLICT(reference) DO NOTHING
                RETURNING id
            """, (
                order["user_id"], "topup:" + order_key, int(amount_minor), credits_to_issue,
                float(order.get("markup_multiplier") or 2),
                json.dumps({
                    "order_id": order_key, "provider_payment_id": payment_key,
                    "credited_credits": credits_to_issue, "debt_repaid": debt_repaid,
                    "spendable_credits": spendable_credits,
                    "usd_per_1000_provider_credits": float(unit_cost),
                    "billing_mode": _text(order.get("billing_mode") or "test_bonus"),
                    "credit_pricing_version": 3,
                }),
            ))
            if not cur.fetchone():
                raise CVideoError("VIDEO_WALLET_TOPUP_ALREADY_RECORDED")
            cur.execute("""
                UPDATE april_video_wallet_orders
                SET payment_status='paid', provider_payment_id=%s, paid_at=NOW()
                WHERE order_id=%s
            """, (payment_key, order_key))
            cur.execute("SELECT balance_credits, debt_credits FROM april_video_wallets WHERE user_id=%s", (order["user_id"],))
            after = cur.fetchone() or {}
        conn.commit()
        return {
            "success": True, "order_id": order_key, "payment_status": "paid",
            "user_id": order["user_id"], "order_amount_minor": int(amount_minor),
            "order_currency": "USD", "credited_credits": credits_to_issue // 2,
            "debt_repaid": debt_repaid // 2,
            "balance_credits": int(after.get("balance_credits") or 0) // 2,
            "debt_credits": (int(after.get("debt_credits") or 0) + 1) // 2,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _video_markup_multiplier() -> float:
    # The agreed customer price is exactly 2x the provider's effective cost.
    return 2.0


def _video_cost_per_1000_credits(user_id: Any = None) -> float:
    """Return provider cost per 1,000 credits from a clear 12,000-credit price.

    Current configured baseline is $19 / 12,000 provider credits. The old
    *_USD_PER_1000_CREDITS values are intentionally ignored because they were
    easy to confuse with per-credit or package prices and caused over-crediting.
    """
    billing_mode = _magic_hour_billing_mode(user_id)
    env_name = (
        "APRIL_VIDEO_TEST_USD_PER_12000_CREDITS"
        if billing_mode == "test_bonus"
        else "APRIL_MAGIC_HOUR_USD_PER_12000_CREDITS"
    )
    error_code = "APRIL_VIDEO_TEST_COST_NOT_CONFIGURED" if billing_mode == "test_bonus" else "APRIL_MAGIC_HOUR_COST_NOT_CONFIGURED"
    raw = os.getenv(env_name, "19").strip()
    try:
        bundle_cost = Decimal(raw)
    except Exception as exc:
        raise CVideoError(error_code) from exc
    if not Decimal("1") <= bundle_cost <= Decimal("10000"):
        raise CVideoError(error_code)
    return float(bundle_cost / Decimal("12"))


def _video_price_for_credits(credits: int, unit_cost_per_1000: float) -> tuple[int, int]:
    """Return provider and customer USD-cent equivalents without double rounding."""
    provider_credits = max(0, int(credits or 0))
    provider_value = Decimal(provider_credits) * Decimal(str(unit_cost_per_1000)) / Decimal("10")
    customer_value = provider_value * Decimal(str(_video_markup_multiplier()))
    provider_minor = int(provider_value.to_integral_value(rounding=ROUND_CEILING)) if provider_value else 0
    customer_minor = int(customer_value.to_integral_value(rounding=ROUND_CEILING)) if customer_value else 0
    return provider_minor, customer_minor


def _reserve_video_charge(user_id: Any, operation_ref: Any, operation: str, estimate_credits: int) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    billing_mode = _magic_hour_billing_mode(user_id)
    unit_cost = _video_cost_per_1000_credits(user_id)
    estimate_credits = max(0, int(estimate_credits or 0))
    reference = re.sub(r"[^A-Za-z0-9._:-]", "", _text(operation_ref))[:120] or uuid.uuid4().hex
    reference = "video:" + reference
    provider_minor, estimated_customer_minor = _video_price_for_credits(estimate_credits, unit_cost)
    expected_april_credits = estimate_credits * int(_video_markup_multiplier())
    reserve_credits = int((Decimal(expected_april_credits) * Decimal("1.15")).to_integral_value(rounding=ROUND_CEILING))
    reserve_minor = _usd_minor_for_april_credits(reserve_credits, unit_cost)
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT enabled FROM april_video_wallets WHERE user_id=%s FOR UPDATE", (canonical,))
            wallet = cur.fetchone()
            if not wallet or not wallet.get("enabled"):
                raise CVideoError("VIDEO_WALLET_NOT_ENABLED")
            _ensure_wallet_credit_state(cur, canonical, unit_cost)
            cur.execute("SELECT balance_credits, debt_credits FROM april_video_wallets WHERE user_id=%s FOR UPDATE", (canonical,))
            wallet = cur.fetchone() or {}
            balance_credits = max(0, int(wallet.get("balance_credits") or 0))
            debt_credits = max(0, int(wallet.get("debt_credits") or 0))
            if debt_credits > 0 or balance_credits < reserve_credits:
                raise CVideoError("VIDEO_WALLET_INSUFFICIENT_FUNDS")
            cur.execute("""
                UPDATE april_video_wallets SET balance_credits=balance_credits-%s, updated_at=NOW()
                WHERE user_id=%s
            """, (reserve_credits, canonical))
            cur.execute("""
                INSERT INTO april_video_wallet_transactions
                    (user_id, reference, kind, status, delta_minor, delta_credits,
                     provider_cost_minor, provider_credits, markup_multiplier,
                     operation, description, metadata)
                VALUES (%s, %s, 'video_debit', 'processing', %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT(reference) DO NOTHING
                RETURNING id
            """, (
                canonical, reference, -reserve_minor, -reserve_credits,
                provider_minor, estimate_credits, _video_markup_multiplier(), operation,
                "Video generation" if operation == "generate" else "AI video editing",
                json.dumps({
                    "billing_mode": billing_mode,
                    "unit_cost_usd_per_1000_credits": unit_cost,
                    "estimated_customer_minor": estimated_customer_minor,
                    "expected_april_credits": expected_april_credits,
                    "reserved_april_credits": reserve_credits,
                }),
            ))
            if not cur.fetchone():
                raise CVideoError("VIDEO_OPERATION_ALREADY_PROCESSED")
        conn.commit()
        return {
            "reference": reference, "reserve_minor": reserve_minor,
            "reserve_credits": reserve_credits, "provider_cost_minor": provider_minor,
            "estimate_credits": estimate_credits,
            "markup_multiplier": _video_markup_multiplier(), "billing_mode": billing_mode,
            "unit_cost_usd_per_1000_credits": unit_cost,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _update_video_charge(user_id: Any, reservation: dict[str, Any], *, actual_credits: int, status: str = "completed", refund: bool = False, provider_job_id: str = "") -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    reference = _text(reservation.get("reference"))
    actual_credits = max(0, int(actual_credits or 0))
    unit_cost = reservation.get("unit_cost_usd_per_1000_credits")
    if unit_cost is None:
        unit_cost = _video_cost_per_1000_credits(user_id)
    provider_minor, actual_minor = _video_price_for_credits(actual_credits, float(unit_cost))
    actual_april_credits = actual_credits * int(_video_markup_multiplier())
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT delta_minor, delta_credits, provider_credits, metadata, status
                FROM april_video_wallet_transactions
                WHERE user_id=%s AND reference=%s FOR UPDATE
            """, (canonical, reference))
            tx = cur.fetchone()
            if not tx:
                raise CVideoError("VIDEO_WALLET_RESERVATION_NOT_FOUND")
            if _text(tx.get("status")).lower() != "processing":
                conn.commit()
                return {
                    "success": True, "already_settled": True,
                    "charged_minor": abs(int(tx.get("delta_minor") or 0)),
                    "charged_credits": abs(int(tx.get("delta_credits") or 0)) // 2,
                    "status": _text(tx.get("status")),
                }
            old_reserved_credits = abs(int(tx.get("delta_credits") or reservation.get("reserve_credits") or 0))
            meta = tx.get("metadata") if isinstance(tx.get("metadata"), dict) else {}
            cur.execute("""
                SELECT balance_credits, debt_credits FROM april_video_wallets
                WHERE user_id=%s FOR UPDATE
            """, (canonical,))
            wallet = cur.fetchone() or {}
            balance = max(0, int(wallet.get("balance_credits") or 0))
            debt = max(0, int(wallet.get("debt_credits") or 0))
            if refund:
                balance += old_reserved_credits
                actual_delta_credits = 0
                actual_delta_minor = 0
                actual_april_credits = 0
                actual_minor = 0
            elif old_reserved_credits >= actual_april_credits:
                balance += old_reserved_credits - actual_april_credits
                actual_delta_credits = -actual_april_credits
                actual_delta_minor = -actual_minor
            else:
                extra = actual_april_credits - old_reserved_credits
                extra_from_balance = min(balance, extra)
                balance -= extra_from_balance
                debt += extra - extra_from_balance
                actual_delta_credits = -actual_april_credits
                actual_delta_minor = -actual_minor
            cur.execute("""
                UPDATE april_video_wallets
                SET balance_credits=%s, debt_credits=%s, updated_at=NOW()
                WHERE user_id=%s
            """, (balance, debt, canonical))
            if provider_job_id:
                meta["provider_job_id"] = provider_job_id
            meta["actual_credits"] = actual_credits
            meta["actual_april_credits"] = actual_april_credits
            meta["settlement_debt_created"] = max(0, debt - max(0, int(wallet.get("debt_credits") or 0)))
            cur.execute("""
                UPDATE april_video_wallet_transactions
                SET delta_minor=%s, delta_credits=%s, provider_cost_minor=%s,
                    provider_credits=%s, status=%s, metadata=%s::jsonb, updated_at=NOW()
                WHERE user_id=%s AND reference=%s
            """, (
                actual_delta_minor, actual_delta_credits, provider_minor, actual_credits,
                "refunded" if refund else status, json.dumps(meta), canonical, reference,
            ))
        conn.commit()
        return {
            "success": True, "charged_minor": actual_minor if not refund else 0,
            "charged_credits": (actual_april_credits // 2) if not refund else 0,
            "billing_mode": _text(reservation.get("billing_mode") or "commercial"),
            "balance_credits": balance // 2, "debt_credits": (debt + 1) // 2,
            "status": "refunded" if refund else status,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _record_local_video_edit(user_id: Any, operation_ref: Any, description: str) -> None:
    try:
        canonical = _wallet_identity(user_id)
        conn = _wallet_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT enabled FROM april_video_wallets WHERE user_id=%s", (canonical,))
                wallet = cur.fetchone()
                if wallet and wallet.get("enabled"):
                    reference = "local-edit:" + (re.sub(r"[^A-Za-z0-9._:-]", "", _text(operation_ref))[:100] or __import__("uuid").uuid4().hex)
                    cur.execute("""
                        INSERT INTO april_video_wallet_transactions
                            (user_id, reference, kind, status, delta_minor, operation, description)
                        VALUES (%s, %s, 'local_edit', 'completed', 0, 'edit', %s)
                        ON CONFLICT(reference) DO NOTHING
                    """, (canonical, reference, _text(description)[:180] or "Local FFmpeg edit — no provider charge"))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        # A failed audit log must not break local FFmpeg editing, which has no
        # provider cost and therefore must never be blocked by wallet outages.
        return


def _magic_hour_json(path: str, *, api_key: str, method: str = "GET", body: dict[str, Any] | None = None, timeout: int = 45) -> dict[str, Any]:
    url = "https://api.magichour.ai" + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))
            if not isinstance(parsed, dict):
                raise CVideoError("MAGIC_HOUR_INVALID_RESPONSE")
            return parsed
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read(64 * 1024).decode("utf-8", errors="replace"))
            nested_error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
            detail = _text(
                payload.get("message") or payload.get("code") or payload.get("detail")
                or nested_error.get("message") or nested_error.get("code")
            )
        except Exception:
            pass
        # Preserve Magic Hour's structured reason. A 402 can mean insufficient
        # credits, a subscription gate, or a model/plan restriction; collapsing
        # every case into INSUFFICIENT_CREDITS sends users toward needless top-ups.
        if exc.code == 402:
            raise CVideoError(f"MAGIC_HOUR_HTTP_402: {detail or 'provider billing or plan restriction'}") from exc
        raise CVideoError(f"MAGIC_HOUR_HTTP_{exc.code}: {detail or 'request rejected'}") from exc
    except urllib.error.URLError as exc:
        raise CVideoError(f"MAGIC_HOUR_CONNECTION_FAILED: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise CVideoError(f"MAGIC_HOUR_RESPONSE_FAILED: {type(exc).__name__}") from exc


def _magic_hour_account_credits(*, api_key: str) -> int:
    """Read the balance for the exact API key configured on April (no charge).

    This prevents confusing a funded browser session with a different or stale
    API key deployed on the bot. GET /v1/account is a read-only provider call.
    """
    account = _magic_hour_json("/v1/account", api_key=api_key, method="GET", timeout=30)
    raw_credits = account.get("credits")
    try:
        credits = int(raw_credits)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CVideoError("MAGIC_HOUR_API_ACCOUNT_BALANCE_UNREADABLE") from exc
    if credits < 0:
        raise CVideoError("MAGIC_HOUR_API_ACCOUNT_BALANCE_UNREADABLE")
    return credits


def _magic_hour_upload(data: bytes, *, api_key: str, kind: str, extension: str) -> str:
    created = _magic_hour_json("/v1/files/upload-urls", api_key=api_key, method="POST", body={"items": [{"type": kind, "extension": extension}]})
    items = created.get("items") if isinstance(created.get("items"), list) else []
    target = items[0] if items and isinstance(items[0], dict) else {}
    upload_url = _text(target.get("upload_url"))
    file_path = _text(target.get("file_path"))
    if not upload_url.startswith("https://") or not file_path:
        raise CVideoError("MAGIC_HOUR_UPLOAD_URL_INVALID")
    request = urllib.request.Request(upload_url, data=data, headers={"Content-Type": "application/octet-stream"}, method="PUT")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status not in {200, 201, 204}:
                raise CVideoError("MAGIC_HOUR_ASSET_UPLOAD_FAILED")
    except urllib.error.URLError as exc:
        raise CVideoError(f"MAGIC_HOUR_ASSET_UPLOAD_FAILED: {exc.reason}") from exc
    return file_path


def _magic_hour_download(url: str) -> bytes:
    if not url.startswith("https://"):
        raise CVideoError("MAGIC_HOUR_DOWNLOAD_URL_INVALID")
    request = urllib.request.Request(url, headers={"User-Agent": "April-C-VIDEO/2.0"})
    chunks: list[bytes] = []
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            mime = (response.headers.get("Content-Type") or "video/mp4").split(";", 1)[0].lower()
            if mime not in {"video/mp4", "application/octet-stream", "video/quicktime"}:
                raise CVideoError(f"MAGIC_HOUR_UNSUPPORTED_VIDEO_TYPE: {mime}")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_VIDEO_BYTES:
                raise CVideoError("Generated MP4 exceeds April's 25 MiB artifact limit.")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_VIDEO_BYTES:
                    raise CVideoError("Generated MP4 exceeds April's 25 MiB artifact limit.")
                chunks.append(chunk)
    except urllib.error.URLError as exc:
        raise CVideoError(f"MAGIC_HOUR_DOWNLOAD_FAILED: {exc.reason}") from exc
    content = b"".join(chunks)
    if len(content) < 12 or b"ftyp" not in content[:64]:
        raise CVideoError("Magic Hour result is not a valid MP4 file.")
    return content


async def _magic_hour_run_video_job(
    *, api_key: str, endpoint: str, body: dict[str, Any], timeout_seconds: int,
    progress_callback: Callable[[str], Any] | None, user_id: Any,
    reservation: dict[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    created = await asyncio.to_thread(_magic_hour_json, endpoint, api_key=api_key, method="POST", body=body, timeout=60)
    project_id = _text(created.get("id"))
    if not project_id:
        raise CVideoError(_text(created.get("message") or created.get("code")) or "MAGIC_HOUR_PROJECT_ID_MISSING")
    # Save the provider id immediately; if polling times out, the reserved debit
    # remains visible as processing and can be reconciled rather than refunded
    # while the provider may still be charging.
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE april_video_wallet_transactions
                SET metadata=COALESCE(metadata, '{}'::jsonb) || %s::jsonb, updated_at=NOW()
                WHERE reference=%s
            """, (json.dumps({"provider_job_id": project_id}), reservation["reference"]))
        conn.commit()
    finally:
        conn.close()
    started = time.monotonic()
    last_status = "queued"
    while time.monotonic() - started < max(45, int(timeout_seconds or 285)):
        await asyncio.sleep(10)
        details = await asyncio.to_thread(_magic_hour_json, f"/v1/video-projects/{quote(project_id, safe='')}", api_key=api_key, method="GET", timeout=45)
        last_status = _text(details.get("status")).lower()
        if last_status == "complete":
            downloads = details.get("downloads") if isinstance(details.get("downloads"), list) else []
            download = downloads[0] if downloads and isinstance(downloads[0], dict) else {}
            video_url = _text(download.get("url"))
            actual_credits = int(details.get("credits_charged") or created.get("credits_charged") or reservation.get("estimate_credits") or 0)
            if not video_url:
                raise CVideoError("MAGIC_HOUR_COMPLETED_WITHOUT_DOWNLOAD")
            if progress_callback:
                progress_callback("saving")
            try:
                content = await asyncio.to_thread(_magic_hour_download, video_url)
            except Exception:
                _update_video_charge(user_id, reservation, actual_credits=0, refund=True, provider_job_id=project_id)
                raise
            billing = _update_video_charge(user_id, reservation, actual_credits=actual_credits, provider_job_id=project_id)
            return content, {"task_id": project_id, "actual_credits": actual_credits, "billing": billing, "details": details}
        if last_status in {"error", "canceled", "cancelled"}:
            _update_video_charge(user_id, reservation, actual_credits=0, refund=True, provider_job_id=project_id)
            error = details.get("error") if isinstance(details.get("error"), dict) else {}
            raise CVideoError(_text(error.get("message") or details.get("error") or last_status)[:300])
        if progress_callback:
            progress_callback("generating")
    raise CVideoError(f"MAGIC_HOUR_TASK_PENDING: {project_id} ({last_status})")


def _magic_hour_rates(model: str, resolution: str) -> int:
    model = _text(model).lower()
    resolution = _text(resolution).lower()
    table = {
        "ltx-2.5": {"480p": 24, "720p": 48, "1080p": 72},
        "minimax-h3": {"480p": 24, "720p": 48, "1080p": 72},
    }
    try:
        return table[model][resolution]
    except KeyError as exc:
        raise CVideoError("APRIL_VIDEO_MODEL_OR_RESOLUTION_UNSUPPORTED") from exc



def _next_resolution_for_tier_error(resolution: str, error: Any) -> str:
    """Return one lower supported resolution only for an explicit tier restriction."""
    message = _text(error).lower()
    if not (
        "magic_hour_http_402" in message
        and "resolution" in message
        and "not available" in message
        and "subscription tier" in message
    ):
        return ""
    return {"1080p": "720p", "720p": "480p"}.get(_text(resolution).lower(), "")


def _text(value: Any) -> str:
    return str(value or "").strip()


_VIDEO_NUMBER_WORDS = {
    "одну": 1, "одной": 1, "одного": 1, "один": 1, "одна": 1,
    "две": 2, "дві": 2, "два": 2, "три": 3, "четыре": 4, "чотири": 4,
    "пять": 5, "п'ять": 5, "шесть": 6, "шість": 6,
    "семь": 7, "сім": 7, "восемь": 8, "вісім": 8, "девять": 9, "дев'ять": 9,
    "десять": 10, "одиннадцать": 11, "двенадцать": 12,
    "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
    "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
    "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
    "одинадцять": 11, "дванадцять": 12, "тринадцять": 13, "чотирнадцять": 14,
    "п'ятнадцять": 15, "шістнадцять": 16, "сімнадцять": 17, "вісімнадцять": 18,
    "дев'ятнадцять": 19, "двадцять": 20, "тридцять": 30, "сорок": 40,
    "п'ятдесят": 50, "шістдесят": 60,
    "eleven": 11, "twelve": 12, "one": 1, "two": 2, "three": 3,
    "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60,
}
_VIDEO_TENS_WORDS = {
    "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
    "двадцять": 20, "тридцять": 30, "сорок": 40, "п'ятдесят": 50, "шістдесят": 60,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
}


def _active_video_model_resolution(model: Any = None, resolution: Any = None) -> tuple[str, str]:
    model = _text(model or os.getenv("APRIL_MAGIC_HOUR_VIDEO_MODEL") or "ltx-2.5").lower()
    resolution = _text(resolution or os.getenv("APRIL_VIDEO_RESOLUTION") or "480p").lower()
    return model or "ltx-2.5", resolution or "480p"


def get_video_capability_profile(model: Any = None, resolution: Any = None) -> dict[str, Any]:
    """Return the supported single-clip duration for the effective provider model and resolution."""
    model, resolution = _active_video_model_resolution(model, resolution)
    if model == "ltx-2.5":
        maximum = 30 if resolution == "1080p" else 60 if resolution in {"480p", "720p"} else 0
    elif model == "minimax-h3":
        maximum = 30 if resolution in {"480p", "720p", "1080p"} else 0
    else:
        maximum = 0
    return {
        "provider": "Magic Hour",
        "model": model,
        "resolution": resolution,
        "minimum_duration_seconds": 1 if maximum else None,
        "maximum_duration_seconds": maximum or None,
        "default_duration_seconds": VIDEO_DEFAULT_DURATION_SECONDS,
        "supported": bool(maximum),
        "duration_rule": (
            "LTX 2.5: 1–60 seconds at 480p/720p; up to 30 seconds at 1080p."
            if model == "ltx-2.5" else
            "MiniMax H3: 1–30 seconds at supported resolutions."
            if model == "minimax-h3" else
            "The configured model is not supported by April's current C_VIDEO rate table."
        ),
    }


def _parse_requested_video_duration(request_text: str) -> int | None:
    """Parse an explicitly stated clip length; None means no duration was stated."""
    value = _text(request_text).lower().replace("ё", "е")
    if not value:
        return None

    # Timecode is accepted only when it is clearly marked as a duration.
    timecode = re.search(
        r"(?iu)(?:длительност\w*|длин\w*|хронометраж\w*|duration|length|на протяжении|в течение)\s*[:=]?\s*(\d{1,2}):(\d{2})\b",
        value,
    )
    if timecode:
        minutes, seconds = int(timecode.group(1)), int(timecode.group(2))
        if f"{minutes}:{seconds}" not in {"9:16", "16:9", "1:1", "3:2", "2:3", "4:3"}:
            return minutes * 60 + seconds

    if re.search(r"(?iu)\b(?:полминут\w*|половин\w*\s+минут\w*|пів\s*хвилин\w*|half\s+a\s+minute)\b", value):
        return 30
    if re.search(r"(?iu)\b(?:полторы\s+минут\w*|півтори\s+хвилин\w*)\b", value):
        return 90
    if re.search(r"(?iu)\b(?:на\s+)?(?:минуту|одну\s+минуту|одну\s+хвилину|хвилину|one\s+minute)\b", value):
        return 60

    all_words = set(_VIDEO_NUMBER_WORDS)
    tens = set(_VIDEO_TENS_WORDS)
    word_alt = "|".join(sorted(map(re.escape, all_words), key=len, reverse=True))
    tens_alt = "|".join(sorted(map(re.escape, tens), key=len, reverse=True))
    number_pattern = r"(?P<number>\d{1,3}|(?:" + tens_alt + r")(?:[\s-]+(?:" + word_alt + r"))?|(?:" + word_alt + r"))"
    unit_pattern = r"(?P<unit>секунд\w*|сек\.?|с|seconds?|secs?|s|минут\w*|мин\.?|minutes?|mins?|хвилин\w*|хв\.?|m)"
    match = re.search(number_pattern + r"[\s-]*" + unit_pattern + r"\b", value, re.I)
    if not match:
        return None

    before = value[max(0, match.start() - 28):match.start()]
    if re.search(r"(?iu)(?:через|спустя|after|in\s+the\s+next)\s*$", before):
        return None

    number_raw = match.group("number").lower().replace("ё", "е")
    if number_raw.isdigit():
        amount = int(number_raw)
    else:
        tokens = re.split(r"[\s-]+", number_raw)
        if len(tokens) == 1:
            amount = _VIDEO_NUMBER_WORDS[tokens[0]]
        elif len(tokens) == 2 and tokens[0] in _VIDEO_TENS_WORDS and tokens[1] in _VIDEO_NUMBER_WORDS:
            amount = _VIDEO_TENS_WORDS[tokens[0]] + _VIDEO_NUMBER_WORDS[tokens[1]]
        else:
            return None
    unit = match.group("unit").lower()
    return amount * 60 if unit.startswith(("мин", "min", "хв", "m")) else amount


def resolve_video_duration(request_text: str) -> dict[str, Any]:
    """Resolve requested/default duration and reject values outside active model limits."""
    profile = get_video_capability_profile()
    raw_request = _text(request_text)
    duration_omitted_explicitly = bool(re.search(
        r"(?iu)(?:без\s+(?:указани\w*\s+)?(?:времени|длительност\w*)|"
        r"длительност\w*\s+(?:не\s+указан\w*|не\s+задан\w*|не\s+определен\w*)|"
        r"(?:no|without)\s+(?:specified\s+)?duration|duration\s+(?:not\s+specified|not\s+set))",
        raw_request,
    ))
    requested = None if duration_omitted_explicitly else _parse_requested_video_duration(request_text)
    duration_expression_present = not duration_omitted_explicitly and (
        bool(re.search(r"(?iu)\d+\s*(?:секунд|сек\.?|seconds?|secs?|минут|мин\.?|minutes?|mins?|хвилин|хв\.?)", raw_request))
        or bool(re.search(r"(?iu)(?:длительност\w*|хронометраж|duration|length)\s*[:=]?\s*\S+", raw_request))
        or bool(re.search(r"(?iu)(?:полторы\s+минут|півтори\s+хвилин|полминут|пів\s*хвилин)", raw_request))
    )
    unsupported_duration_expression = requested is None and duration_expression_present
    defaulted = requested is None and not unsupported_duration_expression
    duration = VIDEO_DEFAULT_DURATION_SECONDS if requested is None else int(requested)
    maximum = profile.get("maximum_duration_seconds")
    error = ""
    if unsupported_duration_expression:
        error = "VIDEO_DURATION_EXPRESSION_UNSUPPORTED"
    elif not profile.get("supported"):
        error = "APRIL_VIDEO_MODEL_OR_RESOLUTION_UNSUPPORTED"
    elif duration < int(profile.get("minimum_duration_seconds") or 1) or duration > int(maximum or 0):
        error = f"VIDEO_DURATION_LIMIT_EXCEEDED:requested={duration}:max={maximum}"
    return {
        "duration_seconds": duration,
        "requested_duration_seconds": requested,
        "duration_was_default": defaulted,
        "duration_limit_seconds": maximum,
        "duration_resolution": profile.get("resolution"),
        "duration_model": profile.get("model"),
        "duration_error": error,
    }


def _build_data_uri(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64," + base64.b64encode(data).decode("ascii")


def decode_video_data_uri(value: Any) -> tuple[bytes, str] | None:
    """Decode a bounded video data URI without accepting arbitrary URL fetches."""
    raw = _text(value)
    match = re.match(r"^data:(video/[a-z0-9.+-]+);base64,([a-z0-9+/=\r\n]+)$", raw, re.I)
    if not match:
        return None
    try:
        data = base64.b64decode(re.sub(r"\s+", "", match.group(2)), validate=True)
    except Exception:
        return None
    if not data or len(data) > MAX_VIDEO_INPUT_BYTES:
        return None
    return data, match.group(1).lower()



def explicit_video_companion_outputs(request_text: Any) -> list[str]:
    """Return independently requested outputs explicitly conjoined with a video task.

    A visual noun inside the video's scene description ("video of a diagram") is
    not a second renderer request. A separate output is retained only when the
    user joins it to the video with "and/и" or gives it its own output action.
    """
    text = _text(request_text).lower().replace("ё", "е")
    if not text:
        return []
    video_noun = r"(?:виде\w*|ролик\w*|клип\w*|відео|video|clip)"
    separator = r"(?:\bи\b|\band\b|\balso\b|\bplus\b|\bа\s+также\b|\bа\s+затем\b|\bзатем\b|\bпотом\b|\bthen\b|\bnext\b)"
    action = r"(?:созда\w*|сгенерир\w*|постро\w*|нарис\w*|сдела\w*|слела\w*|слел\w*|зроб\w*|створ\w*|покаж\w*|подготов\w*|напиш\w*|выдай\w*|create|generate|build|draw|make|show|prepare|write|export)"
    patterns = {
        "image": r"(?:картинк\w*|изображени\w*|фото\w*|иллюстраци\w*|\bimage\b|\bphoto\b|\bpicture\b|\billustration\b)",
        "diagram": r"(?:диаграмм\w*|схем\w*|черт[её]ж\w*|блок[- ]схем\w*|\bdiagram\b|\bschematic\b|\bflowchart\b|\bblueprint\b)",
        "graph": r"(?:график\w*|гистограмм\w*|\bgraph\b|\bchart\b|\bplot\b)",
        "table": r"(?:таблиц\w*|\btable\b)",
        "formula": r"(?:формул\w*|уравнен\w*|\bformula\b|\bequation\b)",
        "code": r"(?:код\w*|скрипт\w*|\bcode\b|\bscript\b)",
        "file": r"(?:файл\w*|\bfile\b|\bpdf\b|\bcsv\b|\bxlsx\b|\bdocx\b)",
        "link": r"(?:ссылк\w*|\blink\w*|\burl\b)",
        "audio": r"(?:аудио\w*|звук\w*|озвучк\w*|\baudio\b|\bsound\b|\bvoiceover\b)",
    }
    found: list[str] = []
    video_first = re.search(video_noun, text, re.I)
    video_last = list(re.finditer(video_noun, text, re.I))
    if not video_first or not video_last:
        return found
    first_video_start = video_first.start()
    for output, noun in patterns.items():
        independent = False
        # "video and [create/draw] a diagram" or "video and diagram" (shared verb).
        if re.search(
            video_noun + r"[\s,;:–—-]{0,8}" + separator + r".{0,24}(?:" + action + r".{0,28})?" + noun,
            text, re.I | re.S,
        ):
            independent = True
        # "create a diagram and a video" / "draw a graph, then make a video".
        if not independent and re.search(
            r"(?<![\w])" + action + r".{0,35}" + noun + r"[\s,;:–—-]{0,8}" + separator + r".{0,24}" + video_noun,
            text, re.I | re.S,
        ):
            independent = True
        # If the second action explicitly places that visual inside the video,
        # it is scene content, not a second billable output.
        embedded_visual = bool(re.search(
            r"(?:добав\w*|помест\w*|встав\w*|покаж\w*|размест\w*|put|place|add|insert|show|include)"
            + r".{0,28}" + noun + r".{0,30}(?:в\s+(?:сам\w*\s+)?(?:виде\w*|ролик\w*|клип\w*)|"
            + r"inside\s+(?:the\s+)?(?:video|clip)|in\s+(?:the\s+)?(?:video|clip)|into\s+(?:the\s+)?(?:video|clip))",
            text, re.I | re.S,
        ))
        if embedded_visual:
            independent = False
        if independent:
            found.append(output)
    return found


def normalize_video_question_sequence(
    question_sequence: Any,
    video_plan: Any,
    request_text: str,
) -> list[dict[str, Any]]:
    """Keep a video-generation request and all of its modifiers in one task.

    The generic splitter can separate a scene description from a duration or
    style clause. Those clauses are parameters of the same render operation,
    not independent text answers or extra video jobs. Keep their exact source
    wording together in one canonical step before the Provider prompt is built.
    """
    plan = video_plan if isinstance(video_plan, dict) else {}
    action = _text(plan.get("action")).lower()
    source = _text(request_text)
    items = [dict(item) for item in (question_sequence or []) if isinstance(item, dict)]
    if action not in {"generate", "edit"} or not source:
        return items

    source_clauses = [
        _text(item.get("request")) for item in items if _text(item.get("request"))
    ]
    first = dict(items[0]) if items else {}
    first.update({
        "step_index": 1,
        "request": source,
        "output_types": ["text", "video"],
        "final_output": True,
        "video_task": True,
        "video_action": action,
        "source_clauses": source_clauses[:12],
        "semantic_reason": "video_scene_and_modifiers_are_one_render_task",
    })
    # The prior branch relation remains available for contextual video requests.
    if not isinstance(first.get("dialogue_search"), dict):
        first.pop("dialogue_search", None)
    return [first]


def apply_video_intent_contract(
    interpretation: Any,
    video_plan: Any,
    question_sequence: Any,
    request_text: str,
    *,
    contract_name: str = "C_ARTIFACT_CONTRACT",
) -> list[dict[str, Any]]:
    """Synchronize Interpretation, request sequence and C_VIDEO SceneContract.

    This is shared by Free and Premium so a video action cannot be described as
    unsupported by one layer while another layer schedules the C_VIDEO room.
    """
    if not isinstance(interpretation, dict):
        return [dict(item) for item in (question_sequence or []) if isinstance(item, dict)]
    plan = video_plan if isinstance(video_plan, dict) else {}
    action = _text(plan.get("action")).lower()
    has_final_interpretation_intent = isinstance(interpretation.get("intent"), dict)
    intent = interpretation.get("intent") if has_final_interpretation_intent else {}
    if action in {"generate", "edit"} and has_final_interpretation_intent:
        interpreted_outputs = intent.get("requested_outputs") if isinstance(intent.get("requested_outputs"), list) else []
        # The deterministic room plan is not sufficient authorization to spend.
        # The Interpretation layer must independently request the video renderer.
        interpreted_video = bool(
            plan.get("explicit_user_action") is True
            and intent.get("wants_video") is True
            and "video" in {
                _text(value).lower() for value in interpreted_outputs if _text(value)
            }
        )
        if not interpreted_video:
            plan.update({
                "action": "none", "requires_video_provider": False,
                "requires_ffmpeg": False, "artifact_type": "text",
                "explicit_user_action": False,
            })
            sequence = [dict(item) for item in (question_sequence or []) if isinstance(item, dict)]
            canonical_outputs = list(dict.fromkeys(
                _text(value).lower() for value in interpreted_outputs if _text(value)
            )) or ["text"]
            # Keep every step on the same allow-list. The room denies execution,
            # but it does not remove or replace the output types Interpretation chose.
            for item in sequence:
                item["output_types"] = list(canonical_outputs)
                item.pop("video_task", None)
                item.pop("video_action", None)
            intent["wants_video"] = False
            intent["video_generation_authorized"] = False
            structure = interpretation.get("request_structure")
            if isinstance(structure, dict):
                structure["output_plan"] = list(canonical_outputs)
                structure["requested_outputs"] = list(canonical_outputs)
                structure["question_sequence"] = sequence
                structure["question_search_count"] = len(sequence)
                presentation = structure.get("presentation_contract")
                if isinstance(presentation, dict):
                    presentation["requested_renderers"] = list(canonical_outputs)
                    presentation["video_generation_authorized"] = False
            try:
                print("[APRIL_VIDEO_INTENT_GATE] " + json.dumps({
                    "decision": "blocked_no_interpreted_video_output",
                    "action": action,
                    "requested_outputs": intent["requested_outputs"],
                }, ensure_ascii=False, separators=(",", ":")), flush=True)
            except Exception:
                pass
            return sequence
    sequence = normalize_video_question_sequence(question_sequence, plan, request_text)
    if action == "none" or not action:
        return sequence

    intent["wants_video"] = True
    intent["video_action"] = action
    intent["video_plan"] = dict(plan)
    intent["video_execution_owner"] = "C_VIDEO"
    if action in {"generate", "edit"}:
        # An input still image can be an initial frame; it is never, by itself,
        # permission to create a separate image. Preserve the canonical output
        # allow-list from Interpretation and derive descriptive flags from it.
        intent["task"] = "generate_video" if action == "generate" else "edit_video"
        canonical_outputs = list(dict.fromkeys(
            _text(value).lower() for value in intent.get("requested_outputs", [])
            if _text(value)
        ))
        intent["wants_image"] = "image" in canonical_outputs
        if not intent["wants_image"]:
            intent["image_operation"] = "none"
        intent["wants_video"] = "video" in canonical_outputs
        intent["video_generation_authorized"] = (
            intent["wants_video"] and action in {"generate", "edit"}
            and plan.get("explicit_user_action") is True
        )
        for flag, output in (
            ("wants_diagram", "diagram"), ("wants_graph", "graph"),
            ("wants_table", "table"), ("wants_formula", "formula"),
            ("wants_code", "code"), ("wants_file", "file"),
            ("wants_copy", "copy"), ("wants_links", "link"),
        ):
            intent[flag] = output in canonical_outputs
        if sequence:
            sequence[0]["output_types"] = list(canonical_outputs)
    elif action == "analyze":
        intent["task"] = "analyze_video"
        canonical_outputs = list(dict.fromkeys(
            _text(value).lower() for value in intent.get("requested_outputs", [])
            if _text(value)
        )) or ["text"]
        intent["wants_image"] = "image" in canonical_outputs
        if sequence:
            sequence[0]["output_types"] = list(canonical_outputs)

    interpretation["intent"] = intent
    structure = interpretation.setdefault("request_structure", {})
    structure["question_sequence"] = sequence
    structure["question_search_count"] = len(sequence)
    # Intent, decomposition, output plan and presentation policy are one
    # contract. Synchronize all provider-facing copies so an incidental
    # diagram/image guess cannot request another renderer or a repair call.
    canonical_outputs = list(intent.get("requested_outputs") or ["text"])
    structure["output_plan"] = canonical_outputs
    structure["requested_outputs"] = canonical_outputs
    presentation = structure.get("presentation_contract")
    if not isinstance(presentation, dict):
        presentation = {}
        structure["presentation_contract"] = presentation
    presentation["requested_renderers"] = canonical_outputs
    presentation["video_generation_authorized"] = bool(intent.get("video_generation_authorized"))
    presentation["billable_renderer_owner"] = "C_VIDEO" if intent.get("video_generation_authorized") else "none"
    rendering_guidance = structure.get("rendering_guidance")
    if isinstance(rendering_guidance, list):
        video_policy = (
            "For this explicit C_VIDEO request, render only the requested video output and any separately co-requested renderers in requested_renderers. "
            "Do not create a diagram, graph, image, gallery, table, formula, code or explanatory renderer from the video's subject, setting, motion, style, duration, soundtrack or scene description. "
            "The MP4 description belongs inside the VideoBlock payload; do not emit a separate diagram or video-description block."
        )
        structure["rendering_guidance"] = [video_policy, *[
            _text(item) for item in rendering_guidance
            if _text(item) and "For this explicit C_VIDEO request" not in _text(item)
        ]]
    structure["video_scene_contract"] = {
        "version": "april_video_scene_contract_v1",
        "room": "C_VIDEO",
        "action": action,
        "execution_owner": "C_VIDEO",
        "analysis_method": plan.get("analysis_method"),
        "video_input_count": int(plan.get("video_input_count") or 0),
        "image_input_count": int(plan.get("image_input_count") or 0),
        "requires_video_provider": bool(plan.get("requires_video_provider")),
        "requires_ffmpeg": bool(plan.get("requires_ffmpeg")),
        "required_renderer": "VideoBlock" if action in {"generate", "edit"} else "MessageTextBlock",
        "render_contract": f"{contract_name} -> VideoBlock -> SceneContract",
        "billing_owner": "C_VIDEO.video_wallet" if intent.get("video_generation_authorized") is True else "none",
        "requested_renderers": canonical_outputs,
        "video_generation_authorized": bool(intent.get("video_generation_authorized")),
        "duration_seconds": plan.get("duration_seconds"),
        "requested_duration_seconds": plan.get("requested_duration_seconds"),
        "duration_was_default": bool(plan.get("duration_was_default")),
        "duration_limit_seconds": plan.get("duration_limit_seconds"),
        "duration_error": _text(plan.get("duration_error")),
        "user_request_preserved_verbatim": bool(_text(request_text)),
    }
    return sequence

def classify_video_request(text: str, attachments: Any = None) -> dict[str, Any]:
    """Create a deterministic intent plan; analysis never accidentally generates."""
    value = _text(text)
    low = value.lower().replace("ё", "е")
    items = [item for item in (attachments or []) if isinstance(item, dict)]
    videos = [item for item in items if _text(item.get("kind")).lower() == "video"]
    images = [item for item in items if _text(item.get("kind")).lower() == "image"]

    # Video generation is billable. Require an explicit creation verb directed
    # at a video/clip object; do not infer generation from a diagram "about video".
    create_verb = (
        r"(?:создай(?:те)?|создавай(?:те)?|создать|создавать|сгенерируй(?:те)?|генерируй(?:те)?|сгенерировать|генерировать|"
        r"сними(?:те)?|оживи(?:те)?|анимируй(?:те)?|створи(?:те)?|створіть|створити|"
        r"згенеруй(?:те)?|згенерувати|сделай(?:те)?|сделаем|сделаю|сделать|делать|зроби(?:те)?|зробіть|зробити|"
        r"слелай(?:те)?|generate|create|animate|make)"
    )
    video_noun = r"(?:виде\w*|ролик\w*|клип\w*|відео|video|clip)"
    advice_or_howto_request = bool(re.search(
        r"(?:^|[.!?;]\s*)(?:(?:объясни|расскажи|подскажи|покажи|explain|teach|tell\s+me|show\s+me)\b.{0,35})?"
        r"(?:как\s+(?:мне\s+)?|how\s+(?:to|do\s+i|can\s+i)\s+)"
        r"(?:создай|создать|создавать|сделай|сделать|сгенерируй|сгенерировать|генерировать|"
        r"анимируй|анимировать|обрежи|обрезать|вырежи|вырезать|смонтируй|смонтировать|"
        r"отредактируй|редактировать|улучши|улучшить|trim|crop|cut|edit|create|make|generate|animate)\b.{0,70}" + video_noun,
        low, re.I | re.S,
    ) or re.search(
        r"\b(?:tutorial|guide|instructions?|обучение|инструкци\w*|руководств\w*)\b.{0,90}"
        r"(?:create|make|generate|animate|созда\w*|сдела\w*|сгенерир\w*).{0,70}" + video_noun,
        low, re.I | re.S,
    ))
    capability_question = bool(re.search(
        r"(?iu)^(?:можешь\s+ли|можете\s+ли|могу\s+ли|можно\s+ли|умеешь\s+ли|умеете\s+ли|"
        r"поддерживаешь\s+ли|поддерживаете\s+ли|can\s+you|can\s+i|could\s+you|is\s+it\s+possible|"
        r"можешь|можете|умеешь|умеете)\b.{0,100}" + video_noun, low.strip(), re.I | re.S,
    ))
    advice_or_howto_request = advice_or_howto_request or capability_question
    explicit_create = not advice_or_howto_request and bool(re.search(
        r"(?<![\w])" + create_verb
        + r"(?:(?!\b(?:о|об|про|для|с|со|about|with|containing|including|featuring|of|на\s+тему|по\s+теме)\b).){0,80}?"
        + video_noun,
        low, re.I | re.S,
    ) or (not advice_or_howto_request and re.search(
        r"(?<![\w])" + video_noun + r".{0,55}(?:generate|create|animate)\b",
        low, re.I | re.S,
    )))
    direct_video_creation_phrase = bool(re.search(
        r"(?iu)\b(?:сделай(?:те)?|сделать|создай(?:те)?|создать|сгенерируй(?:те)?|"
        r"генерируй(?:те)?|зроби(?:те)?|створи(?:те)?|згенеруй(?:те)?|"
        r"make|create|generate)\s+(?:(?:мне|нам|коротк\w*|небольш\w*|a|an|the)\s+){0,3}"
        r"(?:виде\w*|ролик\w*|клип\w*|відео|video|clip)\b", low
    ))
    explicit_create = bool(explicit_create or direct_video_creation_phrase)
    generic_create = explicit_create
    # Editing also consumes paid provider credits for remote AI edits. Require
    # an actual editing instruction, not a noun/topic such as "format" or a
    # how-to question such as "how do I trim a video?".
    edit_command = bool(re.search(
        r"(?iu)\b(?:обрежи(?:те)?|обрежь(?:те)?|вырежи(?:те)?|вырежь(?:те)?|укороти(?:те)?|нарежь(?:те)?|склей(?:те)?|"
        r"соедини(?:те)?|вставь(?:те)?|наложи(?:те)?|улучши(?:те)?|стабилизируй(?:те)?|"
        r"кадрируй(?:те)?|смонтируй(?:те)?|перемонтируй(?:те)?|отредактируй(?:те)?|редактируй(?:те)?|"
        r"измени(?:те)?|переделай(?:те)?|переработай(?:те)?|покажи(?:те)?|"
        r"разлей(?:те)?|разлейся|разли\w*|разол\w*|вылей(?:те)?|выливай(?:те)?|вылил\w*|"
        r"опрокинь\w*|опрокид\w*|переверни\w*|урони\w*|разбей(?:те)?|разбрызгай(?:те)?|"
        r"пролей\w*|пролил\w*|плесни\w*|преврати(?:те)?|добавь(?:те)?|убери(?:те)?|замени(?:те)?|"
        r"spill\w*|pour\w*|tip\s+over|knock\s+over|flip|turn\s+over|break\w*|shatter\w*|splash\w*|"
        r"trim|crop|cut|splice|insert|overlay|enhance|improve|sharpen|denoise|stabili[sz]e|edit|montage)\b",
        low,
    ))
    quality_edit_request = bool(re.search(
        r"(?:\b(?:сделай|сделайте)\b.{0,35}\b(?:видео|ролик|клип)\b.{0,30}\bлучше\b|"
        r"\bmake\b.{0,30}\b(?:video|clip)\b.{0,30}\bbetter\b)",
        low, re.I | re.S,
    ))
    edit_words = edit_command or quality_edit_request
    analyze_words = bool(re.search(
        r"(?iu)(?:анализир\w*|проанализир\w*|разбер\w*|опиш\w*|что\s+(?:происходит|на\s+видео)|содерж\w*|определи\w*|"
        r"analy[sz]e|describe|summari[sz]e|what\s+happens|inspect)", low
    ))

    image_animation_request = bool(
        images and re.search(
            r"(?iu)(?:оживи(?:те)?|анимируй(?:те)?|сделай(?:те)?\s+(?:из\s+)?(?:эт\w*\s+)?(?:фото|фотографи\w*|картинк\w*|изображени\w*)\s+(?:коротк\w*\s+)?(?:видео|ролик)|"
            r"(?:из\s+)?(?:эт\w*\s+)?(?:фото|фотографи\w*|картинк\w*|изображени\w*).{0,180}"
            r"(?:сделай(?:те)?|создай(?:те)?|сгенерируй(?:те)?|зроби(?:те)?|створи(?:те)?).{0,45}(?:виде\w*|ролик\w*|відео|video)|"
            r"animate\s+(?:this\s+)?(?:photo|picture|image)|turn\s+(?:this\s+)?image\s+into\s+(?:a\s+)?video)", low, re.I,
        )
    )
    # A request to change events inside an uploaded clip is an AI EDIT even when
    # the user casually ends with "make a video". Never reduce it to image-to-video
    # from a sampled frame: that loses the source timeline and the requested action.
    source_video_scene_edit = bool(videos and edit_words and not advice_or_howto_request)
    # Explicit creation starts a new render. An uploaded source plus a direct
    # editing command starts an edit. Advice/capability questions never start a paid
    # operation; they remain ordinary text questions even when media is attached.
    if advice_or_howto_request:
        action = "none"
    elif source_video_scene_edit:
        action = "edit"
    elif image_animation_request:
        action = "generate"
    elif explicit_create:
        action = "generate"
    elif generic_create and not videos:
        action = "generate"
    elif videos:
        # Never send a plain photo-description request into video analysis.
        # Existing-video analysis requires an actual video attachment.
        action = "analyze"
    else:
        action = "none"

    plan = {
        "room": "C_VIDEO",
        "action": action,
        "has_video_input": bool(videos),
        "video_input_count": len(videos),
        "has_image_input": bool(images),
        "image_input_count": len(images),
        "requires_video_provider": action == "generate" or (action == "edit" and _requires_remote_ai_edit(value)),
        "requires_ffmpeg": action == "edit" or action == "analyze",
        "analysis_method": "sampled_ordered_frames" if action == "analyze" else "not_applicable",
        "artifact_type": "video" if action in {"generate", "edit"} else "text",
        "explicit_user_action": action in {"generate", "edit"},
    }
    if action == "generate":
        plan.update(resolve_video_duration(value))
    return plan


def extract_video_frames(
    video_bytes: bytes,
    filename: str = "input.mp4",
    *,
    max_frames: int = MAX_VIDEO_FRAMES,
) -> list[dict[str, Any]]:
    """Extract timestamped, ordered key frames for April's existing vision model."""
    if not isinstance(video_bytes, (bytes, bytearray)) or not video_bytes:
        return []
    if len(video_bytes) > MAX_VIDEO_INPUT_BYTES:
        raise CVideoError("VIDEO_INPUT_TOO_LARGE_FOR_ANALYSIS: attachment limit is 10 MiB")
    try:
        import imageio_ffmpeg
        from PIL import Image
    except Exception as exc:
        raise CVideoError("C_VIDEO_DEPENDENCIES_MISSING: install Pillow and imageio-ffmpeg") from exc

    frame_limit = max(1, min(MAX_VIDEO_FRAMES, int(max_frames or MAX_VIDEO_FRAMES)))
    suffix = Path(filename or "input.mp4").suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        suffix = ".mp4"
    frames: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="april-c-video-read-") as temp_dir:
        source = Path(temp_dir) / ("source" + suffix)
        pattern = str(Path(temp_dir) / "frame-%02d.jpg")
        source.write_bytes(bytes(video_bytes))
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        duration, _ = _probe_media(ffmpeg, source)
        # Sample the whole clip, not just the first 16 seconds. Long videos are
        # represented by evenly spaced chronological frames with a small end
        # margin so the final frame is included despite source frame-rate rounding.
        sample_interval = max(2.0, duration / max(1.0, frame_limit - 0.5))
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-vf", f"fps=1/{sample_interval:.3f},scale='min(1280,iw)':-2",
            "-frames:v", str(frame_limit), "-q:v", "4", "-y", pattern,
        ]
        result = subprocess.run(command, capture_output=True, timeout=120, check=False)
        if result.returncode != 0:
            details = (result.stderr or b"").decode("utf-8", errors="replace")[-400:]
            raise CVideoError("VIDEO_FRAME_EXTRACTION_FAILED: " + details)
        for index in range(1, frame_limit + 1):
            frame_path = Path(temp_dir) / f"frame-{index:02d}.jpg"
            if not frame_path.exists():
                break
            with Image.open(frame_path) as opened:
                image = opened.convert("RGB")
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=84, optimize=True)
            frames.append({
                "type": "input_image",
                "image_url": _build_data_uri(buffer.getvalue(), "image/jpeg"),
                "filename": f"{Path(filename or 'video').name}-frame-{index:02d}.jpg",
                "source_type": "video_frame",
                "mime_type": "image/jpeg",
                "frame_index": index,
                "timestamp_seconds": round((index - 1) * sample_interval, 2),
                "sequence_index": index - 1,
                "asset_role": "user_input",
            })
    return frames


def _translate_prompt_to_english(prompt: str) -> str:
    """Use the configured Premium provider to translate the prompt only."""
    try:
        from blocks.Premium_provider_router import MODEL, _client_get
    except Exception:
        from blocks.provider_router import MODEL, _client_get
    model = os.getenv("APRIL_VIDEO_PROMPT_TRANSLATION_MODEL", MODEL).strip() or MODEL
    response = _client_get().responses.create(
        model=model,
        max_output_tokens=900,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": (
                "Translate the supplied video-generation instruction faithfully into concise natural English. "
                "Preserve subjects, actions, order, camera directions, style, timing and constraints. Do not answer "
                "or add details. Return JSON with exactly one string field named prompt."
            )}]},
            {"role": "user", "content": [{"type": "input_text", "text": json.dumps({"source": prompt}, ensure_ascii=False)}]},
        ],
    )
    try:
        parsed = json.loads(_text(getattr(response, "output_text", "")))
    except Exception as exc:
        raise CVideoError("C_VIDEO_PROMPT_TRANSLATION_INVALID") from exc
    translated = _text(parsed.get("prompt")) if isinstance(parsed, dict) else ""
    if not translated:
        raise CVideoError("C_VIDEO_PROMPT_TRANSLATION_EMPTY")
    return translated[:18000]


async def generate_video(
    prompt: str,
    *,
    first_frame_data_uri: str = "",
    duration: int = VIDEO_DEFAULT_DURATION_SECONDS,
    resolution: str = "480p",
    ratio: str = "16:9",
    audio: bool = True,
    progress_callback: Callable[[str], Any] | None = None,
    timeout_seconds: int = 420,
    source_language: str = "",
    user_id: Any = None,
    operation_ref: Any = "",
) -> dict[str, Any]:
    """Create a Magic Hour MP4 and settle the authenticated user's Video Wallet."""
    api_key = os.getenv("MAGIC_HOUR_API_KEY", "").strip()
    if not api_key:
        raise CVideoError("MAGIC_HOUR_API_KEY_NOT_CONFIGURED")
    if os.getenv("APRIL_VIDEO_GENERATION_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        raise CVideoError("APRIL_VIDEO_GENERATION_DISABLED")
    if not user_id:
        raise CVideoError("VIDEO_WALLET_AUTH_REQUIRED")
    _video_cost_per_1000_credits(user_id)  # validates test allow-list or commercial authorization

    clean_prompt = _text(prompt)[:18000]
    if not clean_prompt:
        raise CVideoError("VIDEO_PROMPT_EMPTY")
    model = _text(os.getenv("APRIL_MAGIC_HOUR_VIDEO_MODEL") or "ltx-2.5").lower()
    resolution = _text(os.getenv("APRIL_VIDEO_RESOLUTION") or resolution or "480p").lower()
    profile = get_video_capability_profile(model, resolution)
    maximum_duration = int(profile.get("maximum_duration_seconds") or 0)
    try:
        duration = int(duration)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CVideoError("VIDEO_DURATION_VALUE_INVALID") from exc
    if not maximum_duration:
        raise CVideoError("APRIL_VIDEO_MODEL_OR_RESOLUTION_UNSUPPORTED")
    if duration < 1 or duration > maximum_duration:
        raise CVideoError(f"VIDEO_DURATION_LIMIT_EXCEEDED:requested={duration}:max={maximum_duration}")
    # Validate duration before optional prompt translation or provider calls.
    source_language = _text(source_language).lower().replace("_", "-").split("-", 1)[0]
    prompt_language = source_language or "en"
    warning = ""
    translation_enabled = os.getenv("APRIL_VIDEO_PROMPT_TRANSLATE", "1").strip().lower() not in {"0", "false", "no", "off"}
    if source_language not in {"en", "zh"} and translation_enabled:
        try:
            clean_prompt = await asyncio.to_thread(_translate_prompt_to_english, clean_prompt)
            prompt_language = "en"
        except Exception as exc:
            warning = f"Prompt translation unavailable: {type(exc).__name__}"

    rate = _magic_hour_rates(model, resolution)
    ratio = ratio if ratio in {"16:9", "9:16", "1:1", "3:2", "2:3", "4:3"} else "16:9"
    estimate_credits = int(duration * rate)

    # Verify the account behind MAGIC_HOUR_API_KEY before reserving the user's
    # April wallet or submitting a billable job. Browser balance and deployed
    # API-key balance can differ when another key/account is configured.
    provider_credits = await asyncio.to_thread(_magic_hour_account_credits, api_key=api_key)
    if provider_credits < estimate_credits:
        raise CVideoError(
            f"MAGIC_HOUR_API_ACCOUNT_CREDITS_LOW: available={provider_credits} required={estimate_credits}"
        )

    reservation = _reserve_video_charge(user_id, operation_ref, "generate", estimate_credits)
    project_id = ""
    try:
        body: dict[str, Any] = {
            "name": f"April video {int(time.time())}",
            "end_seconds": duration,
            "model": model,
            "resolution": resolution,
            "audio": bool(audio),
            "style": {"prompt": clean_prompt},
            "aspect_ratio": ratio,
        }
        endpoint = "/v1/text-to-video"
        if first_frame_data_uri:
            match = re.match(r"^data:(image/[a-z0-9.+-]+);base64,(.+)$", first_frame_data_uri, re.I | re.S)
            if not match:
                raise CVideoError("IMAGE_TO_VIDEO_SOURCE_INVALID")
            try:
                image_bytes = base64.b64decode(re.sub(r"\s+", "", match.group(2)), validate=True)
            except Exception as exc:
                raise CVideoError("IMAGE_TO_VIDEO_SOURCE_INVALID") from exc
            if not image_bytes or len(image_bytes) > MAX_VIDEO_INPUT_BYTES:
                raise CVideoError("IMAGE_TO_VIDEO_SOURCE_TOO_LARGE")
            extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(match.group(1).lower(), "png")
            file_path = await asyncio.to_thread(_magic_hour_upload, image_bytes, api_key=api_key, kind="image", extension=extension)
            body["assets"] = {"image_file_path": file_path}
            endpoint = "/v1/image-to-video"
        if progress_callback:
            progress_callback("generating")
        # Retry once per tier step only when Magic Hour explicitly rejects the
        # selected resolution for this subscription. The Playground test proved
        # 480p works on the current account. Do not retry unrelated 402 responses.
        while True:
            try:
                content, job = await _magic_hour_run_video_job(
                    api_key=api_key, endpoint=endpoint, body=body,
                    timeout_seconds=timeout_seconds, progress_callback=progress_callback,
                    user_id=user_id, reservation=reservation,
                )
                break
            except CVideoError as provider_error:
                fallback_resolution = _next_resolution_for_tier_error(resolution, provider_error)
                if not fallback_resolution:
                    raise

                fallback_credits = int(duration * _magic_hour_rates(model, fallback_resolution))
                available_credits = await asyncio.to_thread(
                    _magic_hour_account_credits, api_key=api_key
                )
                if available_credits < fallback_credits:
                    raise CVideoError(
                        "MAGIC_HOUR_API_ACCOUNT_CREDITS_LOW: "
                        f"available={available_credits} required={fallback_credits} "
                        f"for fallback_resolution={fallback_resolution}"
                    ) from provider_error

                # The rejected request returned no project id and cannot be billed.
                # Release the original April reserve before reserving the lower tier.
                if reservation:
                    _update_video_charge(
                        user_id, reservation, actual_credits=0, refund=True
                    )
                    reservation = None

                fallback_ref = (
                    f"{_text(operation_ref) or uuid.uuid4().hex}"
                    f":fallback:{fallback_resolution}"
                )
                reservation = _reserve_video_charge(
                    user_id, fallback_ref, "generate", fallback_credits
                )
                resolution = fallback_resolution
                estimate_credits = fallback_credits
                body["resolution"] = fallback_resolution
                print(
                    "[APRIL_C_VIDEO] subscription_tier_resolution_fallback "
                    f"model={model} resolution={fallback_resolution} "
                    f"provider_credits_required={fallback_credits}"
                )

        project_id = _text(job.get("task_id"))
        billing = job.get("billing") if isinstance(job.get("billing"), dict) else {}
        return {
            "success": True, "operation": "generate", "edit_operations": [],
            "video_bytes": content, "mime_type": "video/mp4",
            "filename": f"april-video-{project_id[:8] or int(time.time())}.mp4",
            "provider": "Magic Hour", "model": model, "task_id": project_id,
            "prompt": clean_prompt, "prompt_language": prompt_language,
            "prompt_translation_warning": warning,
            "duration_seconds": float(duration), "fps": None,
            "resolution": resolution, "ratio": ratio, "audio": bool(audio),
            "billing": billing,
        }
    except Exception:
        # A reservation without a provider job means no external generation was
        # submitted and must be refunded. Once a job id exists, keep it reserved
        # because the provider may still complete and charge it after a timeout.
        if not project_id and reservation:
            try:
                conn = _wallet_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT metadata FROM april_video_wallet_transactions WHERE reference=%s", (reservation["reference"],))
                        row = cur.fetchone() or {}
                    conn.commit()
                    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                    known_job = _text(metadata.get("provider_job_id"))
                finally:
                    conn.close()
                if not known_job:
                    _update_video_charge(user_id, reservation, actual_credits=0, refund=True)
            except Exception:
                pass
        raise


def _requires_remote_ai_edit(request_text: str) -> bool:
    low = _text(request_text).lower().replace("ё", "е")
    return bool(re.search(
        r"(?iu)(?:замени|заменить|убери|удали|удалить|добавь\s+(?:объект|эффект|сцену|человека)|измени\s+(?:цвет|внешн|фон|объект|погоду)|поменяй|перерисуй|преврати|сделай\s+(?:киношн|анимац|реалистич)|"
        r"разлей(?:те)?|разлейся|разли\w*|разол\w*|вылей(?:те)?|выливай(?:те)?|вылил\w*|опрокин\w*|опрокид\w*|переверни\w*|"
        r"урони(?:те)?|разбей(?:те)?|разбрызгай(?:те)?|пролей\w*|пролил\w*|плесни\w*|"
        r"spill\w*|pour\w*|tip\s+over|knock\s+over|flip|turn\s+over|break\w*|shatter\w*|splash\w*|"
        r"замена\s+фона|удаление\s+объект|remove\s+(?:the\s+)?object|remove\s+(?:the\s+)?background|replace\s+(?:the\s+)?|change\s+(?:the\s+)?|turn\s+(?:it|this)\s+into|make\s+it\s+(?:cinematic|animated|realistic))", low
    ))


async def edit_video_with_magic_hour(
    request_text: str, attachments: Any, *, user_id: Any,
    operation_ref: Any = "", progress_callback: Callable[[str], Any] | None = None,
    timeout_seconds: int = 420,
) -> dict[str, Any]:
    """AI edit through Magic Hour; all provider cost is reserved and settled in C_VIDEO."""
    api_key = os.getenv("MAGIC_HOUR_API_KEY", "").strip()
    if not api_key:
        raise CVideoError("MAGIC_HOUR_API_KEY_NOT_CONFIGURED")
    if os.getenv("APRIL_VIDEO_GENERATION_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        raise CVideoError("APRIL_VIDEO_GENERATION_DISABLED")
    _video_cost_per_1000_credits(user_id)  # validates test allow-list or commercial authorization
    sources = _extract_attachment_videos(attachments)
    if not sources:
        raise CVideoError("VIDEO_EDIT_SOURCE_REQUIRED")
    filename, source_bytes, _mime = sources[0]
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in {"mp4", "m4v", "mov", "webm"}:
        raise CVideoError("MAGIC_HOUR_VIDEO_FORMAT_UNSUPPORTED")
    if len(source_bytes) > MAX_VIDEO_INPUT_BYTES:
        raise CVideoError("VIDEO_INPUT_TOO_LARGE_FOR_PROVIDER")
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory(prefix="april-c-video-edit-upload-") as directory:
            source_path = Path(directory) / ("source." + extension)
            source_path.write_bytes(source_bytes)
            duration, _has_audio = _probe_media(ffmpeg, source_path)
    except Exception as exc:
        if isinstance(exc, CVideoError):
            raise
        raise CVideoError("VIDEO_EDIT_SOURCE_DURATION_UNREADABLE") from exc
    edit_plan = _edit_plan(request_text, len(sources))
    start_seconds = max(0.0, float(edit_plan.get("trim_start") or 0.0))
    end_seconds = min(duration, float(edit_plan.get("trim_end") or duration))
    if end_seconds <= start_seconds:
        raise CVideoError("VIDEO_EDIT_TIME_RANGE_INVALID")
    clip_duration = max(1, int(round(end_seconds - start_seconds)))
    model = os.getenv("APRIL_MAGIC_HOUR_VIDEO_MODEL", "ltx-2.5").strip().lower() or "ltx-2.5"
    resolution = _text(os.getenv("APRIL_VIDEO_RESOLUTION", "480p")).lower()
    rate = _magic_hour_rates(model, resolution)
    reservation = _reserve_video_charge(user_id, operation_ref, "edit", int(clip_duration * rate))
    project_id = ""
    try:
        file_path = await asyncio.to_thread(_magic_hour_upload, source_bytes, api_key=api_key, kind="video", extension=extension)
        prompt = (
            "EDIT THE PROVIDED SOURCE VIDEO, preserving its original scene, subjects, camera viewpoint, "
            "continuity, and all content not mentioned by the user. Apply the requested event/change to "
            "the source footage itself; do not create an unrelated replacement clip and do not substitute "
            "a zoom or camera move for the requested object action. Make the requested action clearly visible, "
            "with a coherent chronological cause-and-effect sequence and physically plausible motion. "
            "Do not add unrelated objects, text, people, or effects. USER'S EXACT EDIT INSTRUCTION: "
            + _text(request_text)[:10000]
        )
        lang = ""
        try:
            lang = _text((await asyncio.to_thread(_translate_prompt_to_english, prompt))[:12000])
        except Exception:
            lang = prompt
        body = {
            "name": f"April video edit {int(time.time())}",
            "start_seconds": start_seconds,
            "end_seconds": end_seconds,
            "model": model,
            "resolution": resolution,
            "style": {"prompt": lang},
            "assets": {"video_file_path": file_path},
        }
        if progress_callback:
            progress_callback("generating")
        content, job = await _magic_hour_run_video_job(
            api_key=api_key, endpoint="/v1/ai-video-editor", body=body,
            timeout_seconds=timeout_seconds, progress_callback=progress_callback,
            user_id=user_id, reservation=reservation,
        )
        project_id = _text(job.get("task_id"))
        return {
            "success": True, "operation": "edit", "edit_operations": [{"operation": "ai_video_edit", "prompt": _text(request_text)[:500]}],
            "video_bytes": content, "mime_type": "video/mp4", "filename": f"april-ai-edited-{project_id[:8] or int(time.time())}.mp4",
            "provider": "Magic Hour AI Video Editor", "model": model, "task_id": project_id,
            "prompt": _text(request_text)[:1200], "prompt_language": "local", "duration_seconds": end_seconds - start_seconds,
            "fps": None, "resolution": resolution, "ratio": "source", "audio": True,
            "billing": job.get("billing") if isinstance(job.get("billing"), dict) else {},
        }
    except Exception:
        if not project_id:
            try:
                conn = _wallet_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT metadata FROM april_video_wallet_transactions WHERE reference=%s", (reservation["reference"],))
                        row = cur.fetchone() or {}
                    conn.commit()
                    known = _text((row.get("metadata") or {}).get("provider_job_id")) if isinstance(row.get("metadata"), dict) else ""
                finally:
                    conn.close()
                if not known:
                    _update_video_charge(user_id, reservation, actual_credits=0, refund=True)
            except Exception:
                pass
        raise


def _extract_attachment_videos(attachments: Any) -> list[tuple[str, bytes, str]]:
    result: list[tuple[str, bytes, str]] = []
    for item in attachments or []:
        if not isinstance(item, dict) or _text(item.get("kind")).lower() != "video":
            continue
        decoded = decode_video_data_uri(item.get("video_data_uri") or item.get("_video_data_uri") or item.get("data_uri"))
        if decoded:
            data, mime = decoded
            result.append((_text(item.get("filename") or f"input-{len(result) + 1}.mp4"), data, mime))
    return result


def _parse_seconds(value: str) -> float:
    raw = _text(value).replace(",", ".")
    if ":" in raw:
        parts = raw.split(":")
        try:
            values = [float(part) for part in parts]
            total = 0.0
            for part in values:
                total = total * 60 + part
            return max(0.0, total)
        except ValueError:
            return 0.0
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def _edit_plan(request_text: str, video_count: int) -> dict[str, Any]:
    low = _text(request_text).lower().replace("ё", "е")
    trim_start = 0.0
    trim_end: float | None = None
    time_match = re.search(
        r"(?iu)(?:с|от|from)\s*(\d+(?:[.,]\d+)?(?::\d+(?:[.,]\d+)?){0,2})\s*(?:секунд\w*|сек\.?|s)?\s*(?:по|до|to|through)\s*(\d+(?:[.,]\d+)?(?::\d+(?:[.,]\d+)?){0,2})",
        low,
    )
    if time_match:
        trim_start = _parse_seconds(time_match.group(1))
        trim_end = _parse_seconds(time_match.group(2))
    else:
        until_match = re.search(r"(?iu)(?:до|to)\s*(\d+(?:[.,]\d+)?)\s*(?:секунд\w*|сек\.?|seconds?|s)\b", low)
        if until_match and re.search(r"(?iu)обреж|обрез|укорот|trim|cut", low):
            trim_end = _parse_seconds(until_match.group(1))
        start_match = re.search(r"(?iu)(?:начиная\s+с|начни\s+с|start\s+at)\s*(\d+(?:[.,]\d+)?)\s*(?:секунд\w*|сек\.?|seconds?|s)?", low)
        if start_match:
            trim_start = _parse_seconds(start_match.group(1))

    crop_ratio = ""
    if re.search(r"(?iu)(?:9\s*:\s*16|вертикальн\w*|портретн\w*|сторис|reels?|тик.?ток|vertical)", low):
        crop_ratio = "9:16"
    elif re.search(r"(?iu)(?:16\s*:\s*9|горизонтальн\w*|landscape|widescreen)", low):
        crop_ratio = "16:9"
    elif re.search(r"(?iu)(?:1\s*:\s*1|квадратн\w*|square)", low):
        crop_ratio = "1:1"

    stabilize = bool(re.search(r"(?iu)(?:стабилиз\w*|stabili[sz]e)", low))
    enhance = bool(re.search(r"(?iu)(?:улучш\w*|повыс\w*.{0,25}кач\w*|четк\w*|резк\w*|убери\s+шум|enhance|improve|sharpen|denoise)", low))
    trim_requested = bool(re.search(r"(?iu)(?:обреж|обрез|выреж|укорот|trim|cut)", low)) or trim_end is not None or trim_start > 0
    insert_requested = bool(re.search(r"(?iu)(?:встав\w*|добав\w*.{0,30}(?:клип|фрагмент|видео)|налож\w*|insert|overlay|picture.?in.?picture|pip)", low))
    overlay_mode = bool(re.search(r"(?iu)(?:поверх|налож\w*|в\s+угол|в\s+углу|картин\w*\s+в\s+картин\w*|оверле\w*|overlay|picture.?in.?picture|pip)", low))
    insert_position_match = re.search(
        r"(?iu)(?:после|на\s+отметке|в\s+момент|after|at\s+second|at)\s*(\d+(?:[.,]\d+)?)"
        r"|на\s+(\d+(?:[.,]\d+)?)\s*секунд\w*",
        low,
    )
    insert_position = _parse_seconds(next((group for group in insert_position_match.groups() if group), "0")) if insert_position_match else None
    if insert_position is None and re.search(r"(?iu)(?:в\s+самое?\s+начало|в\s+начало|с\s+начала|from\s+the\s+beginning)", low):
        insert_position = 0.0
    elif insert_position is None and re.search(r"(?iu)(?:в\s+самый?\s+конец|в\s+конец|в\s+конце|at\s+the\s+end)", low):
        insert_position = 1e9
    return {
        "trim_start": trim_start,
        "trim_end": trim_end,
        "trim_requested": trim_requested,
        "crop_ratio": crop_ratio,
        "enhance": enhance,
        "stabilize": stabilize,
        "insert_requested": insert_requested,
        "insert_mode": "picture_in_picture" if overlay_mode else "timeline_splice",
        "insert_position": insert_position,
        "requires_second_clip": insert_requested and video_count < 2,
    }


def _crop_filter(ratio: str) -> str:
    if ratio == "9:16":
        return "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'"
    if ratio == "16:9":
        return "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)'"
    if ratio == "1:1":
        return "crop='min(iw,ih)':'min(iw,ih)'"
    return ""


def _probe_media(ffmpeg: str, path: Path) -> tuple[float, bool]:
    """Read duration/audio presence from ffmpeg's input header without rendering."""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True, timeout=30, check=False,
    )
    details = (result.stderr or b"").decode("utf-8", errors="replace")
    duration_match = re.search(r"Duration:\s*(\d{2}:\d{2}:\d{2}(?:\.\d+)?)", details)
    if not duration_match:
        raise CVideoError(f"Could not read video duration: {path.name}")
    return _parse_seconds(duration_match.group(1)), bool(re.search(r"\bAudio:\s*", details))


def edit_video(
    request_text: str,
    attachments: Any,
    *,
    progress_callback: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Apply real MP4 trim/crop/enhancement plus timeline or picture-in-picture insertion."""
    sources = _extract_attachment_videos(attachments)
    if not sources:
        raise CVideoError("Для монтажа не найден исходный MP4. Прикрепите видео или восстановите его из этого диалога.")
    if any(len(source[1]) > MAX_VIDEO_INPUT_BYTES for source in sources):
        raise CVideoError("Каждый исходный видеоклип должен быть не больше 10 MiB.")
    plan = _edit_plan(request_text, len(sources))
    if plan["requires_second_clip"]:
        raise CVideoError("Для вставки второго клипа прикрепите два видео: основное и вставляемое.")
    if not any((plan["trim_requested"], plan["crop_ratio"], plan["enhance"], plan["stabilize"], plan["insert_requested"])):
        # A generic edit request is safely interpreted as enhancement, not as a no-op.
        plan["enhance"] = True

    try:
        import imageio_ffmpeg
    except Exception as exc:
        raise CVideoError("C_VIDEO_DEPENDENCIES_MISSING: install imageio-ffmpeg.") from exc
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    edit_operations: list[dict[str, Any]] = []
    filters: list[str] = []
    if plan["crop_ratio"]:
        filters.append(_crop_filter(plan["crop_ratio"]))
        edit_operations.append({"operation": "crop", "ratio": plan["crop_ratio"], "anchor": "center"})
    if plan["stabilize"]:
        filters.insert(0, "deshake=rx=16:ry=16:edge=mirror")
        edit_operations.append({"operation": "stabilize", "method": "ffmpeg-deshake"})
    if plan["enhance"]:
        filters.extend([
            "hqdn3d=1.5:1.5:6:6",
            "eq=contrast=1.04:saturation=1.06:brightness=0.005",
            "unsharp=5:5:0.55:3:3:0.25",
        ])
        edit_operations.append({"operation": "enhance", "denoise": True, "sharpen": True, "color_adjustment": True})
    if plan["trim_requested"]:
        edit_operations.append({"operation": "trim", "start_seconds": plan["trim_start"], "end_seconds": plan["trim_end"]})
    if plan["insert_requested"]:
        if plan["insert_mode"] == "picture_in_picture":
            edit_operations.append({"operation": "insert_overlay", "mode": "picture_in_picture", "description": "Second clip overlays the main clip at the lower-right corner."})
        else:
            edit_operations.append({"operation": "insert_clip", "mode": "timeline_splice", "description": "Second clip is inserted into the main clip timeline."})

    output_duration: float | None = None
    output_has_audio = True
    with tempfile.TemporaryDirectory(prefix="april-c-video-edit-") as temp_dir:
        temp = Path(temp_dir)
        main_suffix = Path(sources[0][0]).suffix.lower()
        if main_suffix not in VIDEO_EXTENSIONS:
            main_suffix = ".mp4"
        main_path = temp / ("main" + main_suffix)
        output_path = temp / "april-edited.mp4"
        main_path.write_bytes(sources[0][1])
        command = [ffmpeg, "-hide_banner", "-loglevel", "error"]
        if plan["insert_requested"]:
            insert_suffix = Path(sources[1][0]).suffix.lower()
            if insert_suffix not in VIDEO_EXTENSIONS:
                insert_suffix = ".mp4"
            insert_path = temp / ("insert" + insert_suffix)
            insert_path.write_bytes(sources[1][1])
            main_duration, main_has_audio = _probe_media(ffmpeg, main_path)
            insert_duration, insert_has_audio = _probe_media(ffmpeg, insert_path)
            if plan["trim_end"] is not None:
                source_duration = plan["trim_end"] - plan["trim_start"]
                if source_duration <= 0:
                    raise CVideoError("Время обрезки указано неверно: конечная отметка должна быть позже начальной.")
                effective_main_duration = min(source_duration, max(0.0, main_duration - plan["trim_start"]))
            else:
                effective_main_duration = max(0.0, main_duration - plan["trim_start"])
            if effective_main_duration <= 0 or insert_duration <= 0:
                raise CVideoError("Один из клипов имеет нулевую длительность.")
            position = plan.get("insert_position")
            if position is None:
                position = effective_main_duration / 2.0
            position = max(0.0, min(float(position), effective_main_duration))
            output_duration = effective_main_duration + insert_duration
            main_video_trim = f"trim=start={plan['trim_start']:.3f}"
            if plan["trim_end"] is not None:
                main_video_trim += f":end={plan['trim_end']:.3f}"
            main_effects = ",".join(filters)
            main_video_chain = f"{main_video_trim},setpts=PTS-STARTPTS"
            if main_effects:
                main_video_chain += "," + main_effects
            if plan["crop_ratio"] == "9:16":
                canvas_w, canvas_h = 720, 1280
            elif plan["crop_ratio"] == "1:1":
                canvas_w, canvas_h = 1080, 1080
            else:
                canvas_w, canvas_h = 1280, 720
            normalize = (
                f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
                f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
            )
            if plan["insert_mode"] == "picture_in_picture":
                command += ["-i", str(main_path), "-i", str(insert_path)]
                at = position if plan.get("insert_position") is not None else 2.0
                insert_end = min(effective_main_duration, at + min(5.0, insert_duration))
                output_duration = effective_main_duration
                filter_complex = (
                    f"[0:v]{main_video_chain}[base];"
                    f"[1:v]setpts=PTS-STARTPTS,scale=w='min(480,iw)':h=-2[insert];"
                    f"[base][insert]overlay=x=W-w-24:y=H-h-24:"
                    f"enable='between(t,{at:.3f},{insert_end:.3f})':eof_action=pass[v]"
                )
                command += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "0:a?"]
                edit_operations[-1].update({"start_seconds": at, "duration_seconds": max(0.0, insert_end - at)})
                output_has_audio = main_has_audio
            else:
                command += ["-i", str(main_path), "-i", str(insert_path)]
                # Normalize both clips to a common canvas/fps so concat is valid
                # even when the source aspect ratios or frame rates differ.
                base = f"[0:v]{main_video_chain},{normalize},split=2[main_pre_src][main_post_src];"
                inserted = f"[1:v]{normalize},setpts=PTS-STARTPTS[inserted];"
                if position <= 0.001:
                    video_graph = (
                        f"[0:v]{main_video_chain},{normalize}[main_tail];" + inserted +
                        f"[inserted][main_tail]concat=n=2:v=1:a=0[v]"
                    )
                elif position >= effective_main_duration - 0.001:
                    video_graph = (
                        f"[0:v]{main_video_chain},{normalize}[main_head];" + inserted +
                        f"[main_head][inserted]concat=n=2:v=1:a=0[v]"
                    )
                else:
                    video_graph = (
                        base + inserted +
                        f"[main_pre_src]trim=end={position:.3f},setpts=PTS-STARTPTS[pre];"
                        f"[main_post_src]trim=start={position:.3f},setpts=PTS-STARTPTS[post];"
                        f"[pre][inserted][post]concat=n=3:v=1:a=0[v]"
                    )
                if main_has_audio:
                    main_audio_trim = f"atrim=start={plan['trim_start']:.3f}"
                    if plan["trim_end"] is not None:
                        main_audio_trim += f":end={plan['trim_end']:.3f}"
                    if position <= 0.001:
                        audio_graph = (
                            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={insert_duration:.3f}[insert_audio];"
                            if insert_has_audio else
                            f"aevalsrc=0|0:s=48000:d={insert_duration:.3f}[insert_audio];"
                        )
                        audio_graph += f"[0:a]{main_audio_trim},asetpts=PTS-STARTPTS[main_audio];[insert_audio][main_audio]concat=n=2:v=0:a=1[a]"
                    elif position >= effective_main_duration - 0.001:
                        audio_graph = (
                            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={insert_duration:.3f}[insert_audio];"
                            if insert_has_audio else
                            f"aevalsrc=0|0:s=48000:d={insert_duration:.3f}[insert_audio];"
                        )
                        audio_graph += f"[0:a]{main_audio_trim},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[main_audio];[main_audio][insert_audio]concat=n=2:v=0:a=1[a]"
                    else:
                        if insert_has_audio:
                            inserted_audio = f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={insert_duration:.3f}[insert_audio];"
                        else:
                            inserted_audio = f"aevalsrc=0|0:s=48000:d={insert_duration:.3f}[insert_audio];"
                        audio_graph = (
                            f"[0:a]{main_audio_trim},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,asplit=2[a_pre_src][a_post_src];"
                            f"[a_pre_src]atrim=end={position:.3f},asetpts=PTS-STARTPTS[a_pre];"
                            f"[a_post_src]atrim=start={position:.3f},asetpts=PTS-STARTPTS[a_post];"
                            + inserted_audio +
                            "[a_pre][insert_audio][a_post]concat=n=3:v=0:a=1[a]"
                        )
                    filter_complex = video_graph + ";" + audio_graph
                    command += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]
                    output_has_audio = True
                else:
                    command += ["-filter_complex", video_graph, "-map", "[v]"]
                    output_has_audio = False
                edit_operations[-1].update({"position_seconds": position, "inserted_duration_seconds": insert_duration})
            duration = output_duration
        else:
            if plan["trim_start"] > 0:
                command += ["-ss", f"{plan['trim_start']:.3f}"]
            command += ["-i", str(main_path)]
            if plan["trim_end"] is not None:
                duration = plan["trim_end"] - plan["trim_start"]
                if duration <= 0:
                    raise CVideoError("Время обрезки указано неверно: конечная отметка должна быть позже начальной.")
                command += ["-t", f"{duration:.3f}"]
            else:
                duration = None
            if filters:
                command += ["-vf", ",".join(filters)]
            output_duration = duration
            _, output_has_audio = _probe_media(ffmpeg, main_path)

        command += [
            "-map_metadata", "0", "-c:v", "libx264", "-preset", os.getenv("APRIL_VIDEO_EDIT_PRESET", "veryfast"),
            "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ]
        if output_has_audio:
            command += ["-c:a", "aac", "-b:a", "128k"]
        if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice":
            command += ["-r", "30"]
        command += ["-y", str(output_path)]
        if progress_callback:
            progress_callback("rendering")
        result = subprocess.run(command, capture_output=True, timeout=int(os.getenv("APRIL_VIDEO_EDIT_TIMEOUT", "240") or 240), check=False)
        if result.returncode != 0 or not output_path.exists():
            details = (result.stderr or b"").decode("utf-8", errors="replace")[-600:]
            raise CVideoError("VIDEO_EDIT_RENDER_FAILED: " + (details or "ffmpeg did not create an output file."))
        content = output_path.read_bytes()
        if not content or len(content) < 12 or b"ftyp" not in content[:64]:
            raise CVideoError("Edited output is not a valid MP4 file.")
        if len(content) > MAX_VIDEO_BYTES:
            raise CVideoError("Edited MP4 exceeds April's 25 MiB artifact storage limit.")

    if progress_callback:
        progress_callback("saving")
    filename = f"april-edited-video-{int(time.time())}.mp4"
    return {
        "success": True, "operation": "edit", "edit_operations": edit_operations,
        "video_bytes": content, "mime_type": "video/mp4", "filename": filename,
        "provider": "April C_VIDEO / FFmpeg", "model": "ffmpeg-local",
        "prompt": _text(request_text)[:1200], "prompt_language": "local",
        "duration_seconds": output_duration if output_duration is not None else None,
        "fps": 30 if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice" else None,
        "resolution": (
            "720x1280" if plan["crop_ratio"] == "9:16" else
            "1080x1080" if plan["crop_ratio"] == "1:1" else
            "1280x720" if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice" else
            "source-preserving"
        ),
        "ratio": plan["crop_ratio"] or ("16:9" if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice" else "source"),
        "audio": output_has_audio, "insert_mode": plan.get("insert_mode", ""), "task_id": "",
    }


async def execute_video_operation(
    plan: dict[str, Any],
    request_text: str,
    attachments: Any,
    visual_context: Any = None,
    *,
    progress_callback: Callable[[str], Any] | None = None,
    source_language: str = "",
    timeout_seconds: int = 420,
    user_id: Any = None,
    operation_ref: Any = "",
) -> dict[str, Any]:
    """Single entry point used by either plan executor after Interpretation selects C_VIDEO."""
    action = _text(plan.get("action")).lower()
    if action == "generate":
        first_frame = ""
        for item in visual_context or []:
            if not isinstance(item, dict) or item.get("recalled_from_memory"):
                continue
            uri = _text(item.get("image_url") or item.get("data_uri"))
            if uri.startswith("data:image/") and ";base64," in uri:
                first_frame = uri
                break
        prompt = (
            "Create the requested image-to-video scene from the supplied source image. "
            "PRIMARY REQUIREMENT: execute every concrete action explicitly requested by the user; "
            "do not replace the requested event with a camera zoom, pan, close-up, or generic motion. "
            "Preserve the identity, appearance, labels, shape, and relative positions of all source objects "
            "unless the user explicitly asks to change them. Animate the requested cause-and-effect in a "
            "clear chronological sequence with physically plausible motion, visible contact, gravity, and "
            "the requested final state. Keep the camera mostly stable unless camera movement is requested. "
            "Do not invent extra actions, props, text, people, or scene changes. No captions unless requested. "
            "USER'S EXACT DIRECTION: " + _text(request_text)[:12000]
        )
        duration_info = {
            key: plan.get(key) for key in (
                "duration_seconds", "requested_duration_seconds", "duration_was_default",
                "duration_limit_seconds", "duration_resolution", "duration_model", "duration_error",
            ) if key in plan
        }
        if not duration_info:
            duration_info = resolve_video_duration(request_text)
        duration_error = _text(duration_info.get("duration_error"))
        if duration_error:
            raise CVideoError(duration_error)
        duration = int(duration_info.get("duration_seconds") or VIDEO_DEFAULT_DURATION_SECONDS)
        ratio = "9:16" if re.search(r"(?iu)(?:вертикальн|портретн|сторис|reel|тик.?ток|vertical|portrait)", request_text) else (
            "1:1" if re.search(r"(?iu)(?:квадратн|square)", request_text) else "16:9"
        )
        audio = not bool(re.search(r"(?iu)(?:без\s+звука|без\s+аудио|mute|no\s+audio|silent)", request_text))
        result = await generate_video(
            prompt, first_frame_data_uri=first_frame, duration=duration,
            resolution=os.getenv("APRIL_VIDEO_RESOLUTION", "480p"), ratio=ratio,
            audio=audio, progress_callback=progress_callback,
            timeout_seconds=timeout_seconds, source_language=source_language,
            user_id=user_id, operation_ref=operation_ref,
        )
        result.update({
            "duration_was_default": bool(duration_info.get("duration_was_default")),
            "requested_duration_seconds": duration_info.get("requested_duration_seconds"),
            "duration_limit_seconds": duration_info.get("duration_limit_seconds"),
        })
        return result
    if action == "edit":
        if _requires_remote_ai_edit(request_text):
            return await edit_video_with_magic_hour(
                request_text, attachments, user_id=user_id, operation_ref=operation_ref,
                progress_callback=progress_callback, timeout_seconds=timeout_seconds,
            )
        result = await asyncio.to_thread(edit_video, request_text, attachments, progress_callback=progress_callback)
        _record_local_video_edit(user_id, operation_ref, _text(request_text)[:180] or "Local FFmpeg edit — no provider charge")
        result["billing"] = {"charged_minor": 0, "provider_cost_minor": 0, "provider_credits": 0, "markup_multiplier": _video_markup_multiplier(), "billing_type": "local_ffmpeg"}
        return result
    raise CVideoError(f"Unsupported C_VIDEO action: {action or 'none'}")

def build_video_render_block(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a VideoBlock by projecting a C_VIDEO artifact through the canonical contract."""
    from blocks.C_ARTIFACT_CONTRACT import create_artifact, _artifact_canonical_render_blocks

    clean_payload = {key: value for key, value in dict(payload or {}).items() if value is not None}
    artifact = create_artifact(
        "video",
        "C_VIDEO",
        {
            "title": _text(clean_payload.get("filename") or "April video"),
            "answer": _text(clean_payload.get("description") or "Video artifact created by April."),
            "renderer": "VideoBlock",
            "viewer": "VideoBlock",
            "payload": clean_payload,
            "machine_only": False,
            "human_visible": True,
            "priority": 90,
            "complexity": "balanced",
            "layout": "single",
            "capabilities": ["video", "download", "share", "playback"],
            "artifact_outputs": ["video/mp4"],
        },
    )
    blocks = _artifact_canonical_render_blocks(artifact)
    if not blocks:
        raise CVideoError("C_VIDEO could not project its artifact into SceneContract.")
    block = blocks[0]
    block["final_output"] = True
    block["source_room"] = "C_VIDEO"
    return block


class CVideoRoom:
    """Canonical plan-independent video room. It does not own identity or persistence."""

    room_id = "C_VIDEO"
    artifact_type = "video"
    capabilities = (
        "video", "video_analysis", "video_generation", "video_editing",
        "video_render", "timeline_editing", "media_processing", "download", "share",
    )

    @staticmethod
    def interpret(request_text: str, attachments: Any = None) -> dict[str, Any]:
        return classify_video_request(request_text, attachments)

    @staticmethod
    def extract_frames(video_bytes: bytes, filename: str = "input.mp4", *, max_frames: int = MAX_VIDEO_FRAMES) -> list[dict[str, Any]]:
        return extract_video_frames(video_bytes, filename, max_frames=max_frames)

    @staticmethod
    async def execute(plan: dict[str, Any], request_text: str, attachments: Any, visual_context: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await execute_video_operation(plan, request_text, attachments, visual_context, **kwargs)

    @staticmethod
    def render(payload: dict[str, Any]) -> dict[str, Any]:
        return build_video_render_block(payload)


__all__ = [
    "CVideoError", "CVideoRoom", "MAX_VIDEO_BYTES", "MAX_VIDEO_FRAMES",
    "VIDEO_DEFAULT_DURATION_SECONDS", "VIDEO_MAX_DURATION_SECONDS",
    "VIDEO_EXTENSIONS", "build_video_render_block", "classify_video_request",
    "decode_video_data_uri", "edit_video", "edit_video_with_magic_hour", "execute_video_operation",
    "explicit_video_companion_outputs", "get_video_capability_profile", "resolve_video_duration",
    "extract_video_frames", "generate_video", "enable_video_wallet", "get_video_wallet_status",
    "is_video_test_account", "magic_hour_video_ready",
    "create_video_wallet_topup_order", "get_video_wallet_order_status",
    "set_video_wallet_order_status", "settle_video_wallet_topup",
]
