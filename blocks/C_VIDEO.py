"""C_VIDEO: one canonical room for April video analysis, generation and editing.

Provider integration, prepaid Video Wallet pricing, reservation and settlement
stay together in this module. A narrowly allow-listed test mode can use the
provider account's trial credits without asserting commercial rights. Local
FFmpeg edits remain free. Binary output is returned to Premium_executor for
authenticated artifact persistence and rendering. Temporary provider URLs
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
from urllib.parse import quote
from pathlib import Path
from typing import Any, Callable

MAX_VIDEO_BYTES = 25 * 1024 * 1024
MAX_VIDEO_INPUT_BYTES = 10 * 1024 * 1024
MAX_VIDEO_FRAMES = 8
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
    """Cheap readiness check used by Premium_executor before publishing its pending scene."""
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
                    currency TEXT NOT NULL DEFAULT 'USD',
                    payment_status TEXT NOT NULL DEFAULT 'pending',
                    payment_source TEXT NOT NULL DEFAULT 'liqpay_google_pay',
                    provider_payment_id TEXT UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    paid_at TIMESTAMPTZ
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_april_video_wallet_tx_user_created ON april_video_wallet_transactions(user_id, created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_april_video_wallet_orders_user_created ON april_video_wallet_orders(user_id, created_at DESC)")
        conn.commit()
        return conn
    except Exception:
        conn.rollback()
        conn.close()
        raise


def enable_video_wallet(user_id: Any) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO april_video_wallets(user_id, enabled)
                VALUES (%s, TRUE)
                ON CONFLICT(user_id) DO UPDATE SET enabled=TRUE, updated_at=NOW()
                RETURNING balance_minor, enabled, currency
            """, (canonical,))
            row = dict(cur.fetchone() or {})
        conn.commit()
        return {"success": True, "enabled": bool(row.get("enabled")), "balance_minor": int(row.get("balance_minor") or 0), "currency": row.get("currency") or "USD"}
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
            cur.execute("SELECT balance_minor, enabled, currency FROM april_video_wallets WHERE user_id=%s", (canonical,))
            wallet = cur.fetchone() or {}
            cur.execute("""
                SELECT id, reference, kind, status, delta_minor, provider_cost_minor,
                       provider_credits, markup_multiplier, operation, description, created_at
                FROM april_video_wallet_transactions
                WHERE user_id=%s
                ORDER BY created_at DESC, id DESC LIMIT %s
            """, (canonical, max(1, min(30, int(limit or 8)))))
            transactions = []
            for row in cur.fetchall() or []:
                item = dict(row)
                created = item.get("created_at")
                item["created_at"] = created.isoformat() if hasattr(created, "isoformat") else str(created or "")
                item["delta_minor"] = int(item.get("delta_minor") or 0)
                item["provider_cost_minor"] = int(item.get("provider_cost_minor") or 0)
                item["provider_credits"] = int(item.get("provider_credits") or 0)
                item["markup_multiplier"] = float(item.get("markup_multiplier") or 2)
                transactions.append(item)
        conn.commit()
        return {
            "success": True,
            "enabled": bool(wallet.get("enabled")) if wallet else False,
            "balance_minor": int(wallet.get("balance_minor") or 0) if wallet else 0,
            "currency": _text(wallet.get("currency") if wallet else "USD") or "USD",
            "markup_multiplier": _video_markup_multiplier(),
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
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT enabled FROM april_video_wallets WHERE user_id=%s FOR UPDATE", (canonical,))
            wallet = cur.fetchone()
            if not wallet or not wallet.get("enabled"):
                raise CVideoError("VIDEO_WALLET_NOT_ENABLED")
            order_id = "APRIL-" + __import__("uuid").uuid4().hex[:24].upper()
            amount_minor = amount * 100
            cur.execute("""
                INSERT INTO april_video_wallet_orders(order_id, user_id, amount_minor, currency)
                VALUES (%s, %s, %s, 'USD')
            """, (order_id, canonical, amount_minor))
        conn.commit()
        return {"success": True, "order_id": order_id, "amount": amount, "amount_minor": amount_minor, "currency": "USD", "payment_status": "pending", "description": f"April Video Wallet top-up ${amount}."}
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
                SELECT order_id, amount_minor, currency, payment_status, created_at, paid_at
                FROM april_video_wallet_orders WHERE order_id=%s AND user_id=%s
            """, (order_key, canonical))
            row = cur.fetchone()
        conn.commit()
        if not row:
            return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_FOUND"}
        return {
            "success": True, "order_id": row["order_id"],
            "amount": round(int(row["amount_minor"]) / 100, 2),
            "amount_minor": int(row["amount_minor"]), "currency": row["currency"],
            "payment_status": row["payment_status"],
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
                    INSERT INTO april_video_wallet_transactions
                        (user_id, reference, kind, status, delta_minor, operation, description, metadata)
                    VALUES (%s, %s, 'reversal', 'completed', %s, 'reversal', 'Video Wallet payment reversed', %s::jsonb)
                    ON CONFLICT(reference) DO NOTHING
                    RETURNING id
                """, (order["user_id"], reversal_reference, -int(order["amount_minor"]), json.dumps({"order_id": order_key, "provider_payment_id": order.get("provider_payment_id")})))
                inserted = cur.fetchone()
                if inserted:
                    cur.execute("""
                        UPDATE april_video_wallets
                        SET balance_minor=balance_minor-%s, updated_at=NOW()
                        WHERE user_id=%s
                    """, (int(order["amount_minor"]), order["user_id"]))
            elif current != "pending":
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_PENDING"}
            cur.execute("""
                UPDATE april_video_wallet_orders SET payment_status=%s
                WHERE order_id=%s
            """, (target, order_key))
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
                return {
                    "success": True, "already_settled": True,
                    "order_id": order_key, "payment_status": "paid",
                    "user_id": order["user_id"],
                    "order_amount_minor": int(order["amount_minor"]),
                    "order_currency": order["currency"],
                }
            if _text(order.get("payment_status")).lower() != "pending":
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_ORDER_NOT_PENDING"}
            if int(order["amount_minor"]) != int(amount_minor) or _text(order["currency"]).upper() != _text(currency).upper() or _text(currency).upper() != "USD":
                conn.rollback()
                return {"success": False, "error": "VIDEO_WALLET_PAYMENT_AMOUNT_MISMATCH"}
            cur.execute("""
                INSERT INTO april_video_wallets(user_id, enabled, balance_minor)
                VALUES (%s, TRUE, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    enabled=TRUE, balance_minor=april_video_wallets.balance_minor + EXCLUDED.balance_minor,
                    updated_at=NOW()
            """, (order["user_id"], amount_minor))
            cur.execute("""
                INSERT INTO april_video_wallet_transactions
                    (user_id, reference, kind, status, delta_minor, operation, description, metadata)
                VALUES (%s, %s, 'topup', 'completed', %s, 'topup', 'Video Wallet top-up', %s::jsonb)
                ON CONFLICT(reference) DO NOTHING
            """, (order["user_id"], "topup:" + order_key, amount_minor, json.dumps({"order_id": order_key, "provider_payment_id": payment_key})))
            cur.execute("""
                UPDATE april_video_wallet_orders
                SET payment_status='paid', provider_payment_id=%s, paid_at=NOW()
                WHERE order_id=%s
            """, (payment_key, order_key))
        conn.commit()
        return {
            "success": True, "order_id": order_key, "payment_status": "paid",
            "user_id": order["user_id"], "order_amount_minor": int(amount_minor),
            "order_currency": "USD",
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
    billing_mode = _magic_hour_billing_mode(user_id)
    env_name = "APRIL_VIDEO_TEST_USD_PER_1000_CREDITS" if billing_mode == "test_bonus" else "APRIL_MAGIC_HOUR_USD_PER_1000_CREDITS"
    error_code = "APRIL_VIDEO_TEST_COST_NOT_CONFIGURED" if billing_mode == "test_bonus" else "APRIL_MAGIC_HOUR_COST_NOT_CONFIGURED"
    raw = os.getenv(env_name, "").strip()
    if not raw:
        raise CVideoError(error_code)
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise CVideoError(error_code) from exc
    if not 0.01 <= value <= 100.0:
        raise CVideoError(error_code)
    return value


def _video_price_for_credits(credits: int, unit_cost_per_1000: float) -> tuple[int, int]:
    from decimal import Decimal, ROUND_CEILING
    credits = max(0, int(credits or 0))
    provider_cost = (Decimal(credits) * Decimal(str(unit_cost_per_1000)) / Decimal(1000) * 100).quantize(Decimal("1"), rounding=ROUND_CEILING)
    provider_minor = int(provider_cost)
    customer_minor = int((Decimal(provider_minor) * Decimal(str(_video_markup_multiplier()))).quantize(Decimal("1"), rounding=ROUND_CEILING))
    return provider_minor, customer_minor


def _reserve_video_charge(user_id: Any, operation_ref: Any, operation: str, estimate_credits: int) -> dict[str, Any]:
    canonical = _wallet_identity(user_id)
    billing_mode = _magic_hour_billing_mode(user_id)
    unit_cost = _video_cost_per_1000_credits(user_id)
    reference = re.sub(r"[^A-Za-z0-9._:-]", "", _text(operation_ref))[:120] or __import__("uuid").uuid4().hex
    reference = "video:" + reference
    provider_minor, charge_minor = _video_price_for_credits(estimate_credits, unit_cost)
    # Keep a 15% reserve for provider FPS/credit corrections. Only the final
    # provider-reported charge is kept; the unused reserve is returned atomically.
    reserve_minor = int((charge_minor * 1.15) + 0.999999)
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance_minor, enabled FROM april_video_wallets WHERE user_id=%s FOR UPDATE", (canonical,))
            wallet = cur.fetchone()
            if not wallet or not wallet.get("enabled"):
                raise CVideoError("VIDEO_WALLET_NOT_ENABLED")
            if int(wallet.get("balance_minor") or 0) < reserve_minor:
                raise CVideoError("VIDEO_WALLET_INSUFFICIENT_FUNDS")
            cur.execute("""
                UPDATE april_video_wallets SET balance_minor=balance_minor-%s, updated_at=NOW()
                WHERE user_id=%s
            """, (reserve_minor, canonical))
            cur.execute("""
                INSERT INTO april_video_wallet_transactions
                    (user_id, reference, kind, status, delta_minor, provider_cost_minor,
                     provider_credits, markup_multiplier, operation, description, metadata)
                VALUES (%s, %s, 'video_debit', 'processing', %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT(reference) DO NOTHING
                RETURNING id
            """, (
                canonical, reference, -reserve_minor, provider_minor, int(estimate_credits),
                _video_markup_multiplier(), operation,
                "Video generation" if operation == "generate" else "AI video editing",
                json.dumps({"billing_mode": billing_mode, "unit_cost_usd_per_1000_credits": unit_cost}),
            ))
            if not cur.fetchone():
                raise CVideoError("VIDEO_OPERATION_ALREADY_PROCESSED")
        conn.commit()
        return {
            "reference": reference, "reserve_minor": reserve_minor,
            "provider_cost_minor": provider_minor, "estimate_credits": int(estimate_credits),
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
    conn = _wallet_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT delta_minor, metadata FROM april_video_wallet_transactions
                WHERE user_id=%s AND reference=%s FOR UPDATE
            """, (canonical, reference))
            tx = cur.fetchone()
            if not tx:
                raise CVideoError("VIDEO_WALLET_RESERVATION_NOT_FOUND")
            old_delta = int(tx.get("delta_minor") or 0)
            old_reserved = abs(old_delta)
            actual_delta = 0 if refund else -actual_minor
            balance_adjustment = old_reserved - actual_minor if not refund else old_reserved
            cur.execute("""
                UPDATE april_video_wallets SET balance_minor=balance_minor+%s, updated_at=NOW()
                WHERE user_id=%s
            """, (balance_adjustment, canonical))
            meta = tx.get("metadata") if isinstance(tx.get("metadata"), dict) else {}
            if provider_job_id:
                meta["provider_job_id"] = provider_job_id
            meta["actual_credits"] = actual_credits
            cur.execute("""
                UPDATE april_video_wallet_transactions
                SET delta_minor=%s, provider_cost_minor=%s, provider_credits=%s,
                    status=%s, metadata=%s::jsonb, updated_at=NOW()
                WHERE user_id=%s AND reference=%s
            """, (actual_delta, provider_minor, actual_credits, "refunded" if refund else status, json.dumps(meta), canonical, reference))
        conn.commit()
        return {
            "success": True, "charged_minor": actual_minor if not refund else 0,
            "provider_cost_minor": provider_minor, "provider_credits": actual_credits,
            "markup_multiplier": _video_markup_multiplier(),
            "billing_mode": _text(reservation.get("billing_mode") or "commercial"),
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
            detail = _text(payload.get("message") or payload.get("code"))
        except Exception:
            pass
        if exc.code == 402:
            raise CVideoError("MAGIC_HOUR_PROVIDER_INSUFFICIENT_CREDITS") from exc
        raise CVideoError(f"MAGIC_HOUR_HTTP_{exc.code}: {detail or 'request rejected'}") from exc
    except urllib.error.URLError as exc:
        raise CVideoError(f"MAGIC_HOUR_CONNECTION_FAILED: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise CVideoError(f"MAGIC_HOUR_RESPONSE_FAILED: {type(exc).__name__}") from exc


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



def _text(value: Any) -> str:
    return str(value or "").strip()


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


def classify_video_request(text: str, attachments: Any = None) -> dict[str, Any]:
    """Create a deterministic intent plan; analysis never accidentally generates."""
    value = _text(text)
    low = value.lower().replace("ё", "е")
    items = [item for item in (attachments or []) if isinstance(item, dict)]
    videos = [item for item in items if _text(item.get("kind")).lower() == "video"]
    images = [item for item in items if _text(item.get("kind")).lower() == "image"]

    explicit_create = bool(re.search(
        r"(?iu)(?:созда\w*|сгенерир\w*|сними\w*|ожив\w*|анимир\w*|створ\w*|згенер\w*|generate|create|animate)"
        r".{0,100}(?:видео|ролик|клип|відео|video|clip)|"
        r"(?:video|clip).{0,70}(?:generate|create|animate)", low
    ))
    generic_create = bool(re.search(
        r"(?iu)(?:сдела\w*|зроб\w*|make).{0,100}(?:видео|ролик|клип|відео|video|clip)", low
    ))
    edit_words = bool(re.search(
        r"(?iu)(?:обреж\w*|обрез\w*|выреж\w*|укорот\w*|нареж\w*|склей\w*|соедин\w*|встав\w*|налож\w*|добав\w*.{0,24}(?:клип|фрагмент|видео)|"
        r"улучш\w*|лучше|ярче|повыс\w*.{0,24}кач\w*|стабилиз\w*|шум\w*|цветокоррек\w*|кадрир\w*|формат\w*|перемонтаж\w*|смонтир\w*|измен\w*|редактир\w*|передел\w*|"
        r"trim|crop|cut|splice|insert|overlay|enhance|improve|better|sharpen|denoise|stabili[sz]e|edit|montage)", low
    ))
    analyze_words = bool(re.search(
        r"(?iu)(?:анализир\w*|проанализир\w*|разбер\w*|опиш\w*|что\s+(?:происходит|на\s+видео)|содерж\w*|определи\w*|"
        r"analy[sz]e|describe|summari[sz]e|what\s+happens|inspect)", low
    ))

    # A source video plus an editing verb means EDIT, even when the user says
    # "сделай видео лучше". Explicit "создай/сгенерируй" still starts a new render.
    if explicit_create:
        action = "generate"
    elif videos and edit_words:
        action = "edit"
    elif generic_create and not videos:
        action = "generate"
    elif videos or analyze_words:
        action = "analyze"
    else:
        action = "none"

    return {
        "room": "C_VIDEO",
        "action": action,
        "has_video_input": bool(videos),
        "video_input_count": len(videos),
        "has_image_input": bool(images),
        "image_input_count": len(images),
        "requires_video_provider": action == "generate",
        "requires_ffmpeg": action == "edit" or action == "analyze",
        "analysis_method": "sampled_ordered_frames" if action == "analyze" else "not_applicable",
        "artifact_type": "video" if action in {"generate", "edit"} else "text",
    }


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
    duration: int = 5,
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

    duration = max(1, min(60, int(duration or 5)))
    model = os.getenv("APRIL_MAGIC_HOUR_VIDEO_MODEL", "ltx-2.5").strip().lower() or "ltx-2.5"
    resolution = _text(os.getenv("APRIL_VIDEO_RESOLUTION", resolution or "480p")).lower()
    rate = _magic_hour_rates(model, resolution)
    ratio = ratio if ratio in {"16:9", "9:16", "1:1", "3:2", "2:3", "4:3"} else "16:9"
    estimate_credits = int(duration * rate)
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
        content, job = await _magic_hour_run_video_job(
            api_key=api_key, endpoint=endpoint, body=body,
            timeout_seconds=timeout_seconds, progress_callback=progress_callback,
            user_id=user_id, reservation=reservation,
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
        if not project_id:
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
        r"(?iu)(?:замени|заменить|убери|удали|удалить|добавь\s+(?:объект|эффект|сцену|человека)|измени\s+(?:цвет|внешн|фон|объект|погоду)|поменяй|перерисуй|преврати|сделай\s+(?:киношн|анимац|реалистич)|замена\s+фона|удаление\s+объект|remove\s+(?:the\s+)?object|remove\s+(?:the\s+)?background|replace\s+(?:the\s+)?|change\s+(?:the\s+)?|turn\s+(?:it|this)\s+into|make\s+it\s+(?:cinematic|animated|realistic))", low
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
        prompt = _text(request_text)[:12000]
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
    """Single entry point used by Premium_executor after Interpretation selects C_VIDEO."""
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
            "Create a coherent, polished video following the user direction. Keep subjects consistent, "
            "use natural motion and intentional camera movement, preserve the requested sequence and style, "
            "avoid captions/text unless explicitly requested. Direction: " + _text(request_text)[:12000]
        )
        # Russian numerals commonly arrive with inflected units ("2 секунды",
        # "10 секунд", "1 секунду"). Match the complete word before applying
        # the configured default; otherwise a two-second request silently became 5s.
        duration_match = re.search(
            r"(?iu)(?<!\d)(60|[1-5]?\d)\s*(?:секунд(?:а|ы|у|е|ой)?|сек\.?|seconds?|secs?|s)(?=\s|[,.!?;:]|$)",
            _text(request_text),
        )
        duration = int(duration_match.group(1)) if duration_match else int(os.getenv("APRIL_VIDEO_DEFAULT_DURATION", "5") or 5)
        ratio = "9:16" if re.search(r"(?iu)(?:вертикальн|портретн|сторис|reel|тик.?ток|vertical|portrait)", request_text) else (
            "1:1" if re.search(r"(?iu)(?:квадратн|square)", request_text) else "16:9"
        )
        audio = not bool(re.search(r"(?iu)(?:без\s+звука|без\s+аудио|mute|no\s+audio|silent)", request_text))
        return await generate_video(
            prompt, first_frame_data_uri=first_frame, duration=duration,
            resolution=os.getenv("APRIL_VIDEO_RESOLUTION", "480p"), ratio=ratio,
            audio=audio, progress_callback=progress_callback,
            timeout_seconds=timeout_seconds, source_language=source_language,
            user_id=user_id, operation_ref=operation_ref,
        )
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
    from blocks.Premium_C_ARTIFACT_CONTRACT import create_artifact, _artifact_canonical_render_blocks

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
    """Canonical Premium video room. It does not own identity or persistence."""

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
    "VIDEO_EXTENSIONS", "build_video_render_block", "classify_video_request",
    "decode_video_data_uri", "edit_video", "edit_video_with_magic_hour", "execute_video_operation",
    "extract_video_frames", "generate_video", "enable_video_wallet", "get_video_wallet_status",
    "is_video_test_account", "magic_hour_video_ready",
    "create_video_wallet_topup_order", "get_video_wallet_order_status",
    "set_video_wallet_order_status", "settle_video_wallet_topup",
]
