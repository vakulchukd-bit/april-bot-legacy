"""
APRIL — EXPERIENCE MANAGER / QUANTUM USER-STATE BRIDGE V1

Role:
    Per-user short-term experience state.

It does not become a second memory system.
It stores only compact JSON-safe experience signals and short stabilization
history. Final reasoning remains in QUANTUM_PROCESSOR.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import time


APRIL_FILE_ID = "APRIL_EXPERIENCE_MANAGER_QUANTUM_V1"
DECISION_OWNER = "QUANTUM_PROCESSOR"

DATA_FILE = Path("experience.json")
MAX_EVENTS = 8
EVENT_TTL = 60 * 60 * 6


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _sanitize(value: Any, depth: int = 0) -> Any:
    """JSON-safe, cycle-resistant snapshot."""
    if depth > 5:
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(k): _sanitize(v, depth + 1)
            for k, v in list(value.items())[:80]
            if not str(k).startswith("_")
        }
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(v, depth + 1) for v in list(value)[:80]]
    return _text(value)


def load_experience_store() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_experience_store(data: Dict[str, Any]) -> bool:
    try:
        safe = _sanitize(data)
        temp = DATA_FILE.with_suffix(".tmp")
        temp.write_text(
            json.dumps(safe, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(DATA_FILE)
        return True
    except Exception:
        return False


def _cleanup(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = time.time()
    live = []
    for event in events:
        if not isinstance(event, dict):
            continue
        timestamp = event.get("timestamp", now)
        try:
            keep = now - float(timestamp) <= EVENT_TTL
        except Exception:
            keep = False
        if keep:
            live.append(event)
    return live[-MAX_EVENTS:]


def build_experience_state(
    user_id: Any,
    evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    evidence = _safe_dict(evidence)
    return {
        "user_id": str(user_id),
        "signals": _sanitize(evidence.get("signals", {})),
        "active_flow": _sanitize(evidence.get("active_flow", {})),
        "history_overlap": evidence.get("signals", {}).get("history_overlap", 0.0),
        "temporary": True,
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
    }


def update_experience(
    user_id: Any,
    evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    store = load_experience_store()
    uid = str(user_id)
    bucket = store.setdefault(uid, {"events": []})

    state = build_experience_state(uid, evidence)
    state["timestamp"] = time.time()
    bucket["events"] = _cleanup(_safe_dict(bucket).get("events", []) + [state])

    saved = save_experience_store(store)
    return {
        "success": saved,
        "user_id": uid,
        "events": len(bucket["events"]),
        "state": _sanitize(state),
        "temporary": True,
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
    }


def get_experience(
    user_id: Any,
) -> Dict[str, Any]:
    store = load_experience_store()
    uid = str(user_id)
    bucket = _safe_dict(store.get(uid))
    events = _cleanup(bucket.get("events", []))
    return {
        "user_id": uid,
        "latest": events[-1] if events else {},
        "events": events,
        "temporary": True,
        "machine_only": True,
        "decision_owner": DECISION_OWNER,
    }
