# blocks/state_manager.py
# =====================================================
# APRIL QUANTUM STATE / MEMORY ENGINE
# =====================================================
"""
Canonical State Manager for April.

Design:
- one unified Quantum Memory Engine owns state evolution;
- the seven-day memory window is preserved exactly as a rolling window;
- visual, dialog, focus, goals, loops and scene continuity are one memory field;
- semantic retrieval is evidence generation for the Quantum Processor;
- this module does not choose routes, renderers, providers or orchestration;
- no parallel memory engines are maintained.

The public function API is preserved for existing callers.
"""

from datetime import datetime, timezone
import time
import threading
import re
import hashlib
from copy import deepcopy

try:
    from storage import get_user_plan, load_memory, save_memory
    _STORAGE_IMPORT_ERROR = None
except Exception as exc:
    get_user_plan = None
    load_memory = None
    save_memory = None
    _STORAGE_IMPORT_ERROR = exc


APRIL_FILE_ID = "APRIL_STATE_MANAGER"
STATE_MACHINE_CHANNEL = {
    "type": "state_runtime",
    "mode": "quantum_memory_field",
    "isolated": True,
    "renderer_safe": True,
    "web_safe": True,
}

ADMIN_ID = 2016592532

# The canonical memory window. day_0 is today; day_6 is the oldest slot.
# Live window: day_0..day_6. day_7 is a deletion boundary, not a memory day.
MEMORY_DAYS = 7
MEMORY_TTL_SECONDS = MEMORY_DAYS * 24 * 60 * 60
TOPIC_CLASSES = ["A", "B", "C", "D", "E"]

SESSION_MEMORY_LIMIT = 1600
HOT_DIALOG_LIMIT = 30  # canonical Free window: 15 USER + 15 APRIL
VISUAL_HISTORY_LIMIT = 8
IMAGE_MEMORY_LIMIT = 5
TOPIC_MEMORY_LIMIT = 5

# Actual rendered visual artifacts may remain the active visual scene.
# Plain text responses do not become visual scenes merely because a SceneContract exists.
VISUAL_SCENE_BLOCK_TYPES = {
    "graph", "plot", "chart", "diagram", "schematic",
    "gallery", "image", "media", "visual", "scene", "table",
}

# Runtime semantic model is deliberately lazy: importing State Manager must
# remain cheap. The engine is loaded only when semantic memory is requested.
SEMANTIC_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # compatibility metadata; runtime is shared

STATE_ENGINE_LOG = []
# Compatibility name retained for callers that may inspect the old log.
STATE_PATCH_LOG = STATE_ENGINE_LOG

SEMANTIC_ENGINE_OWNER = "blocks.interpretation_layer.QUANTUM_EMBEDDING_ENGINE"

_state_lock = threading.RLock()
semantic_lock = threading.RLock()
_semantic_encoder = None


def safe_state_log(msg):
    try:
        message = str(msg)
        print("STATE:", message)
        STATE_ENGINE_LOG.append(message)
        if len(STATE_ENGINE_LOG) > 200:
            del STATE_ENGINE_LOG[:-200]
    except Exception:
        pass


safe_state_log("QUANTUM MEMORY ENGINE INITIALIZED")


# =====================================================
# CORE DATA BUILDERS
# =====================================================

def safe_trim_text(text, limit=120):
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit]


def safe_list(value):
    return value if isinstance(value, list) else []


def compact_dialog_message(role, content):
    return {
        "role": role,
        "content": safe_trim_text(content, 320),
    }


def get_dialog_limit(user_id, plan=None):
    """One active Free hot-dialog window; future plans remain reserved."""
    return HOT_DIALOG_LIMIT


def utc_day_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_default_scene():
    return {
        "mode": "idle",
        "type": None,
        "goal": None,
        "continuity_mode": None,
        "render_type": None,
        "renderer_active": False,
        "visual_active": False,
        "active_flow": None,
        "trajectory_locked": False,
        "anchor": None,
        "anchor_type": None,
        "confidence": 0.0,
        "updated_at": time.time(),
    }


def build_memory_day():
    return {
        "A": [],
        "B": [],
        "C": [],
        "D": [],
        "E": [],
        "visual_scenes": [],
        "topics": [],
        "objects": [],
        "intent_signals": [],
        "created_at": time.time(),
    }


def build_memory_timeline():
    return {f"day_{i}": build_memory_day() for i in range(MEMORY_DAYS)}


def build_default_state():
    return {
        "dialog": [],
        "memory_summary": "",
        "memory_summary_meta": {
            "created_at": None,
            "expires_after_days": MEMORY_DAYS,
            "memory_kind": "summary",
        },
        "memory_matrix": {},
        "active_scene": {},
        "scene_history": [],
        "scene_stack": [],
        "scene_relation": {},
        "dynamic_focus": {},
        "goal_hierarchy": {},
        "open_loops": [],
        "memory_signals": {},
        "image_context": None,
        "image_memory": [],
        "active_visual_scene": None,
        "active_visual_scene_turn": None,
        "stored_visual_scene_turn": None,
        "active_visual_topic": None,
        "visual_topic_history": [],
        "conversation_id": None,
        "current_visual_scene": None,
        "visual_scene_turn_id": None,
        "visual_scene_version": 0,
        "visual_scene_history": [],
        "visual_topic_registry": [],
        "task_context_storage": [],
        "continuity_context_storage": [],
        "memory_anchor_storage": [],
        "active_topic_slot": "A",
        "active_flow": None,
        "awaiting": False,
        "last_prompt": None,
        "task_type": None,
        "scene_state": build_default_scene(),
        "image_analysis": None,
        "image_analysis_path": None,
        "meta": {
            "last_user_message": None,
            "last_bot_message": None,
            "last_entity": None,
            "last_intent": None,
        },
        "current_object": None,
        "current_topic": None,
        "active_entity": None,
        "machine_runtime": True,
        "renderer_safe": True,
        "continuity_alive": True,
        "web_safe": True,
        "last_user_turn": "",
        "last_april_turn": "",
        "dialog_state": {},
        "focus_snapshot": {},
        "focus_state": {
            "active_topic": None,
            "active_scene": None,
            "active_object": None,
            "active_goal": None,
            "priority_score": 0.0,
            "intent_freshness": 0.0,
        },
        "memory_timeline": build_memory_timeline(),
        "memory_cycle": {
            "last_day_key": utc_day_key(),
            "last_rollover": time.time(),
        },
        "memory_version": "QUANTUM-7D-V2",
        "active_scene_contract": {},
        "current_scene_request": "",
        "visual_summary": {},
        "semantic_scene_state": {},
    }


# =====================================================
# UNIFIED QUANTUM MEMORY ENGINE
# =====================================================

class QuantumMemoryEngine:
    """
    One engine for all state/memory semantics.

    It does not own routing. It produces a compact evidence field that the
    existing Executor/Quantum Processor can consume.
    """

    VERSION = "QUANTUM-MEMORY-7D-V2"
    MATRIX_VERSION = "QUANTUM-MEMORY-MATRIX-7D-V1"

    def __init__(self):
        self._encoder = None
        self._encoder_ready = False
        self._encoder_error = None

    # ---------- normalization ----------

    def ensure(self, state_obj):
        if not isinstance(state_obj, dict):
            raise TypeError("state_obj must be dict")

        defaults = build_default_state()
        for key, value in defaults.items():
            if key not in state_obj:
                state_obj[key] = deepcopy(value)

        if not isinstance(state_obj.get("scene_state"), dict):
            state_obj["scene_state"] = build_default_scene()

        if not isinstance(state_obj.get("memory_timeline"), dict):
            state_obj["memory_timeline"] = build_memory_timeline()

        self.normalize_timeline(state_obj)
        if not isinstance(state_obj.get("memory_summary_meta"), dict):
            state_obj["memory_summary_meta"] = {
                "created_at": None,
                "expires_after_days": MEMORY_DAYS,
                "memory_kind": "summary",
            }
        if not isinstance(state_obj.get("memory_matrix"), dict):
            state_obj["memory_matrix"] = {}
        return state_obj

    def normalize_timeline(self, state_obj):
        timeline = state_obj.get("memory_timeline")
        if not isinstance(timeline, dict):
            timeline = {}

        canonical = {}
        for i in range(MEMORY_DAYS):
            key = f"day_{i}"
            day = timeline.get(key)
            canonical[key] = day if isinstance(day, dict) else build_memory_day()
            for slot in TOPIC_CLASSES:
                if not isinstance(canonical[key].get(slot), list):
                    canonical[key][slot] = []
            for field in ("visual_scenes", "topics", "objects", "intent_signals"):
                if not isinstance(canonical[key].get(field), list):
                    canonical[key][field] = []

        state_obj["memory_timeline"] = canonical
        return canonical

    # ---------- seven-day cycle / TTL lifecycle ----------

    @staticmethod
    def _record_timestamp(record):
        if not isinstance(record, dict):
            return 0.0
        for key in (
            "created_at", "timestamp", "archived_at", "updated_at",
            "turn_timestamp", "expires_at",
        ):
            value = record.get(key)
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return 0.0

    @staticmethod
    def _is_expired(timestamp, now=None):
        try:
            created = float(timestamp or 0.0)
        except (TypeError, ValueError):
            return False
        if created <= 0.0:
            return False
        current = float(now if now is not None else time.time())
        return (current - created) >= MEMORY_TTL_SECONDS

    @staticmethod
    def _memory_age_days(timestamp, now=None):
        try:
            created = float(timestamp or 0.0)
        except (TypeError, ValueError):
            return None
        if created <= 0.0:
            return None
        current = float(now if now is not None else time.time())
        return max(0.0, (current - created) / 86400.0)

    def _purge_sequence(self, value, *, now=None):
        if not isinstance(value, list):
            return value, 0
        kept = []
        removed = 0
        for item in value:
            ts = self._record_timestamp(item)
            if ts > 0.0 and self._is_expired(ts, now=now):
                removed += 1
                continue
            kept.append(item)
        return kept, removed

    def _cleanup_top_level_memory(self, state_obj, now=None):
        """Expire timestamped derived ledgers with the same seven-day TTL."""
        now = float(now if now is not None else time.time())
        removed = 0
        by_field = {}

        for field in (
            "visual_scene_history",
            "visual_topic_history",
            "visual_topic_registry",
            "task_context_storage",
            "continuity_context_storage",
            "memory_anchor_storage",
        ):
            cleaned, count = self._purge_sequence(state_obj.get(field), now=now)
            if isinstance(state_obj.get(field), list):
                state_obj[field] = cleaned
            if count:
                by_field[field] = count
                removed += count

        # Legacy scene history can contain undated records. It remains
        # compatibility storage only and is not queried by semantic retrieval.
        cleaned, count = self._purge_sequence(state_obj.get("scene_history"), now=now)
        if isinstance(state_obj.get("scene_history"), list):
            state_obj["scene_history"] = cleaned
        if count:
            by_field["scene_history"] = count
            removed += count

        # Summary has one explicit birth timestamp. A legacy summary without
        # provenance is quarantined, so stale text cannot leak into new context.
        meta = state_obj.get("memory_summary_meta")
        if not isinstance(meta, dict):
            meta = {}
            state_obj["memory_summary_meta"] = meta
        summary_ts = self._record_timestamp(meta)

        if state_obj.get("memory_summary") and summary_ts <= 0.0:
            state_obj["legacy_memory_summary"] = state_obj.get("memory_summary")
            state_obj["memory_summary"] = ""
            state_obj["memory_summary_meta"] = {
                "created_at": None,
                "expires_after_days": MEMORY_DAYS,
                "memory_kind": "summary_legacy_quarantined",
            }
            safe_state_log(
                "MEMORY SUMMARY QUARANTINED: no timestamp; excluded from active memory"
            )
        elif summary_ts > 0.0 and self._is_expired(summary_ts, now=now):
            state_obj["memory_summary"] = ""
            state_obj["memory_summary_meta"] = {
                "created_at": None,
                "expires_after_days": MEMORY_DAYS,
                "memory_kind": "summary_expired",
            }
            by_field["memory_summary"] = 1
            removed += 1
            safe_state_log("MEMORY SUMMARY EXPIRED: TTL_EXPIRED -> DELETE")

        # The active visual pointer is subject to the same TTL.
        hot = state_obj.get("active_visual_scene")
        hot_ts = self._record_timestamp(hot)
        if isinstance(hot, dict) and hot and hot_ts > 0.0 and self._is_expired(hot_ts, now=now):
            state_obj["active_visual_scene"] = None
            state_obj["current_visual_scene"] = None
            state_obj["active_visual_scene_turn"] = None
            state_obj["stored_visual_scene_turn"] = None
            state_obj["active_visual_topic"] = None
            by_field["active_visual_scene"] = 1
            removed += 1
            safe_state_log("ACTIVE VISUAL MEMORY EXPIRED: TTL_EXPIRED -> DELETE")

        state_obj["memory_cleanup"] = {
            "last_cleanup_at": now,
            "last_cleanup_utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "removed_count": removed,
            "removed_by_field": by_field,
            "window": "day_0..day_6",
            "expired_slot": "day_7",
            "ttl_seconds": MEMORY_TTL_SECONDS,
        }
        if removed:
            safe_state_log(
                f"MEMORY TTL CLEANUP: removed={removed} "
                f"window=day_0..day_6 boundary=day_7 fields={by_field}"
            )
        return removed

    def _purge_expired_records_from_timeline(self, state_obj, now=None):
        """Remove timestamped records that are seven days old or older."""
        now = float(now if now is not None else time.time())
        timeline = state_obj["memory_timeline"]
        removed = 0
        by_day = {}

        for i in range(MEMORY_DAYS):
            key = f"day_{i}"
            day = timeline.get(key)
            if not isinstance(day, dict):
                continue
            day_removed = 0
            for field, items in list(day.items()):
                if not isinstance(items, list):
                    continue
                kept = []
                for item in items:
                    ts = self._record_timestamp(item)
                    if ts > 0.0 and self._is_expired(ts, now=now):
                        day_removed += 1
                        continue
                    kept.append(item)
                day[field] = kept
            if day_removed:
                by_day[key] = day_removed
                removed += day_removed

        if removed:
            safe_state_log(
                f"MEMORY TTL CLEANUP: removed={removed} "
                f"window=day_0..day_6 boundary=day_7 by_day={by_day}"
            )
        return removed, by_day

    def _log_rollover_deletion(self, expired_records, today, previous):
        safe_state_log(
            f"MEMORY DAY_7 DELETE: utc={today} previous_utc={previous} "
            f"records_removed={expired_records} window=day_0..day_6"
        )

    def rollover(self, state_obj):
        self.ensure(state_obj)
        today = utc_day_key()
        cycle = state_obj["memory_cycle"]
        previous = cycle.get("last_day_key")
        now = time.time()

        # Real-age TTL cleanup runs even without a UTC day change. This protects
        # against process downtime and legacy records that missed a rollover.
        self._purge_expired_records_from_timeline(state_obj, now=now)
        self._cleanup_top_level_memory(state_obj, now=now)

        if previous == today:
            return False

        shift = 1
        try:
            old_date = datetime.strptime(str(previous), "%Y-%m-%d").date()
            new_date = datetime.strptime(today, "%Y-%m-%d").date()
            shift = max(1, min(MEMORY_DAYS, (new_date - old_date).days))
        except Exception:
            shift = 1

        timeline = state_obj["memory_timeline"]
        expired_records = 0

        for _ in range(shift):
            # day_6 is the oldest live slot. It leaves the live window here;
            # its lifecycle state is day_7 -> DELETE. day_7 is never stored.
            expired_slot = timeline.pop("day_6", build_memory_day())
            for items in expired_slot.values():
                if isinstance(items, list):
                    expired_records += len(items)

            for i in range(MEMORY_DAYS - 1, 0, -1):
                timeline[f"day_{i}"] = timeline.get(f"day_{i-1}", build_memory_day())
            timeline["day_0"] = build_memory_day()

        state_obj["memory_cycle"] = {
            "last_day_key": today,
            "last_rollover": now,
        }

        self._purge_expired_records_from_timeline(state_obj, now=now)
        self._cleanup_top_level_memory(state_obj, now=now)
        self._log_rollover_deletion(expired_records, today, previous)
        safe_state_log(
            f"MEMORY_WINDOW_ROLLED: day_0..day_6 active; day_7 deleted; utc={today}"
        )
        return True

    @staticmethod
    def _ensure_user_scope_for_runtime(state_obj):
        scope = state_obj.get("memory_scope")
        user_id = str(
            (scope or {}).get("user_id")
            or state_obj.get("user_id")
            or ""
        ).strip()
        if not user_id:
            return
        conversation_id = str(
            (scope or {}).get("conversation_id")
            or state_obj.get("conversation_id")
            or f"april-{hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:24]}"
        )
        state_obj["user_id"] = user_id
        state_obj["conversation_id"] = conversation_id
        state_obj["memory_scope"] = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "scope_version": "USER_SCOPED_SCENE_V2",
        }

    @staticmethod
    def _migrate_legacy_visual_hot_pointer(state_obj):
        """Migrate legacy visual hot pointers into live day_0..day_6 memory.

        Old deployments stored rendered tables/images as active_visual_scene without
        the canonical USER↔APRIL scene fields. The migrated record stays live only
        within the seven-day memory window and can no longer remain the hot pointer.
        """
        scene = state_obj.get("active_visual_scene")
        if not isinstance(scene, dict) or not scene:
            return

        canonical_current = bool(
            scene.get("memory_kind") == "current_visual_dialogue"
            and scene.get("user_request")
            and scene.get("april_answer")
            and scene.get("user_id")
            and scene.get("conversation_id")
        )
        if canonical_current:
            return

        if scene.get("legacy_hot_pointer_migrated"):
            state_obj["active_visual_scene"] = None
            return

        user_id = str(state_obj.get("memory_scope", {}).get("user_id") or "")
        if not user_id:
            return

        # Preserve the old record as an archival visual scene.
        archived = deepcopy(scene)
        archived["memory_kind"] = "visual_dialogue_archive"
        archived["legacy_hot_pointer_migrated"] = True
        archived["user_id"] = user_id
        archived["conversation_id"] = str(
            state_obj.get("memory_scope", {}).get("conversation_id")
            or state_obj.get("conversation_id")
            or ""
        )
        archived["archived_at"] = time.time()

        day0 = state_obj["memory_timeline"]["day_0"]
        day0.setdefault("visual_scenes", []).append(archived)
        day0["visual_scenes"] = day0["visual_scenes"][-VISUAL_HISTORY_LIMIT:]

        slot = str(state_obj.get("active_topic_slot") or "A").upper()
        if slot not in TOPIC_CLASSES:
            slot = "A"
        day0.setdefault(slot, []).append({
            "record_type": "visual_dialogue_scene",
            "user_id": user_id,
            "conversation_id": archived["conversation_id"],
            "topic": safe_trim_text(
                archived.get("topic")
                or archived.get("current_request")
                or archived.get("summary"),
                500,
            ),
            "summary": safe_trim_text(
                archived.get("summary")
                or archived.get("april_answer")
                or archived.get("answer"),
                1000,
            ),
            "scene": deepcopy(archived),
            "timestamp": archived["archived_at"],
            "memory_kind": "visual_dialogue_scene",
        })
        day0[slot] = day0[slot][-TOPIC_MEMORY_LIMIT:]

        state_obj.setdefault("visual_topic_history", []).append(archived)
        state_obj["visual_topic_history"] = state_obj["visual_topic_history"][-VISUAL_HISTORY_LIMIT:]
        state_obj["active_visual_scene"] = None
        state_obj["current_visual_scene"] = None
        state_obj["active_visual_scene_turn"] = None
        state_obj["stored_visual_scene_turn"] = None
        state_obj["active_visual_topic"] = None

    def ensure_runtime(self, state_obj):
        self.ensure(state_obj)
        # Normalize legacy hot visual pointers exactly once. Nothing is deleted;
        # the old scene is preserved in dynamic/7-day memory.
        self._ensure_user_scope_for_runtime(state_obj)
        self._migrate_legacy_visual_hot_pointer(state_obj)
        self.rollover(state_obj)
        return state_obj

    # ---------- semantic engine ----------

    def _get_encoder(self):
        if self._encoder_ready:
            return self._encoder

        with semantic_lock:
            if self._encoder_ready:
                return self._encoder

            # One shared semantic engine for Interpretation, Visual Reference,
            # and Memory. No second SentenceTransformer instance is created here.
            from blocks.interpretation_layer import get_shared_semantic_encoder
            self._encoder = get_shared_semantic_encoder()
            self._encoder_ready = True
            safe_state_log("SEMANTIC MEMORY ENGINE LINKED: SHARED_INTERPRETATION_ENCODER")
            return self._encoder

    @staticmethod
    def _cosine(a, b):
        try:
            dot = sum(x * y for x, y in zip(a, b))
            na = sum(x * x for x in a) ** 0.5
            nb = sum(y * y for y in b) ** 0.5
            if not na or not nb:
                return 0.0
            return max(-1.0, min(1.0, dot / (na * nb)))
        except Exception:
            return 0.0

    def semantic_score(self, query, candidate):
        scores = self.semantic_scores(query, [candidate])
        return float(scores.get(safe_trim_text(candidate, 1600), 0.0))

    def semantic_scores(self, query, candidates):
        """Batch comparison through the one shared interpretation embedding engine."""
        q = safe_trim_text(query, 1600)
        unique = []
        seen = set()

        for candidate in candidates:
            c = safe_trim_text(candidate, 1600)
            if c and c not in seen:
                seen.add(c)
                unique.append(c)

        if not q or not unique:
            return {}

        from blocks.interpretation_layer import QUANTUM_EMBEDDING_ENGINE
        # The interpretation engine owns the encoder/cache. State Manager only
        # consumes its measurement, so no second model/runtime can appear here.
        return QUANTUM_EMBEDDING_ENGINE.similarities(q, unique)

    # ---------- memory field ----------

    @staticmethod
    def _record_text(record):
        if not isinstance(record, dict):
            return ""
        parts = [
            record.get("topic"),
            record.get("summary"),
            record.get("text"),
            record.get("current_request"),
            record.get("user_meaning"),
            record.get("april_meaning"),
            record.get("answer_summary"),
            record.get("goal"),
            record.get("object"),
        ]
        scene = record.get("scene")
        if isinstance(scene, dict):
            parts.extend([
                scene.get("scene_type"),
                scene.get("topic"),
                scene.get("goal"),
                scene.get("current_request"),
                scene.get("april_answer"),
            ])
            scene_semantics = scene.get("semantic_state")
            if isinstance(scene_semantics, dict):
                parts.extend([
                    scene_semantics.get("task_phase"),
                    scene_semantics.get("operation"),
                    scene_semantics.get("requested_representation"),
                    scene_semantics.get("previous_operation"),
                    scene_semantics.get("previous_representation"),
                ])
        semantic_state = record.get("semantic_state")
        if isinstance(semantic_state, dict):
            parts.extend([
                semantic_state.get("task_phase"),
                semantic_state.get("operation"),
                semantic_state.get("requested_representation"),
            ])
        return " ".join(str(x) for x in parts if x)

    def iter_memory_records(self, state_obj):
        self.ensure(state_obj)
        timeline = state_obj["memory_timeline"]

        for day_index in range(MEMORY_DAYS):
            day = timeline[f"day_{day_index}"]
            age = day_index

            for slot in TOPIC_CLASSES:
                for item in day.get(slot, []):
                    if isinstance(item, dict):
                        yield {
                            **item,
                            "memory_kind": "topic",
                            "day_index": age,
                            "slot": slot,
                        }

            for item in day.get("visual_scenes", []):
                if isinstance(item, dict):
                    yield {
                        **item,
                        "memory_kind": "visual_scene",
                        "day_index": age,
                    }

            # Completed USER↔APRIL pairs are the canonical dynamic dialogue
            # memory. They were previously stored but never queried here.
            for item in day.get("dialog_pairs", []):
                if isinstance(item, dict):
                    yield {
                        **item,
                        "memory_kind": "dialog_pair",
                        "day_index": age,
                    }

            for item in day.get("intent_signals", []):
                if isinstance(item, dict):
                    yield {
                        **item,
                        "memory_kind": "intent",
                        "day_index": age,
                    }

    def build_memory_matrix(self, state_obj, query="", limit=8):
        """Build one quantum-matrix evidence field over live day_0..day_6 memory."""
        self.ensure_runtime(state_obj)
        query = str(query or "").strip()
        now = time.time()
        records = list(self.iter_memory_records(state_obj))
        texts = [self._record_text(r) for r in records]
        semantic_map = self.semantic_scores(query, texts) if query else {}

        rows = []
        for record, text in zip(records, texts):
            ts = self._record_timestamp(record)
            age_days = self._memory_age_days(ts, now=now)
            base_age = age_days if age_days is not None else float(record.get("day_index", 0))
            age_ratio = min(1.0, max(0.0, base_age / MEMORY_DAYS))
            semantic = float(semantic_map.get(text, 0.0)) if query and text else 0.0
            rows.append({
                "day_index": int(record.get("day_index", 0)),
                "memory_kind": record.get("memory_kind"),
                "age_days": round(age_days, 6) if age_days is not None else None,
                "semantic": round(semantic, 6),
                "visual": 1.0 if record.get("memory_kind") == "visual_scene" else 0.0,
                "dialogue": 1.0 if record.get("memory_kind") == "dialog_pair" else 0.0,
                "freshness": round(max(0.0, 1.0 - age_ratio), 6),
                "ttl_state": "LIVE",
                "text": safe_trim_text(text, 600),
            })

        rows.sort(key=lambda r: (r["semantic"], r["freshness"]), reverse=True)
        return {
            "version": self.MATRIX_VERSION,
            "window": "day_0..day_6",
            "expired_boundary": "day_7",
            "ttl_seconds": MEMORY_TTL_SECONDS,
            "query": query,
            "rows": rows[: max(1, int(limit))],
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }

    def query(self, state_obj, query, *, limit=8, retrieval_mode="semantic"):

        """
        Produce memory evidence. Stored visual scenes remain in the 7-day
        memory, but the current active visual context is exposed only when its
        semantic relevance survives the current-turn measurement.
        """
        self.ensure_runtime(state_obj)
        query = str(query or "").strip()
        retrieval_mode = str(retrieval_mode or "semantic").strip().lower()

        if not query:
            return {
                "engine": self.VERSION,
                "window_days": MEMORY_DAYS,
                "matches": [],
                "active_scene": state_obj.get("active_scene", {}),
                "active_visual_scene": state_obj.get("active_visual_scene"),
                "active_visual_context_relevant": bool(state_obj.get("active_visual_scene")),
                "decision_owner": "QUANTUM_PROCESSOR",
                "evidence_only": True,
            }

        focus = state_obj.get("focus_state", {})
        active_topic = focus.get("active_topic") or state_obj.get("current_topic")
        active_scene = focus.get("active_scene") or state_obj.get("active_visual_scene")
        current_visual = state_obj.get("active_visual_scene")

        candidates = list(self.iter_memory_records(state_obj))
        if retrieval_mode == "memory_query":
            # A recall request asks "what did I ask / discuss", so the memory
            # field should search completed dialogue pairs first rather than
            # visually rendered artifacts or old topic labels.
            dialogue_pairs = [r for r in candidates if r.get("memory_kind") == "dialog_pair"]
            candidates = dialogue_pairs or [
                r for r in candidates if r.get("memory_kind") in {"topic", "dialog_pair"}
            ]
        candidate_texts = []
        candidate_records = []
        for record in candidates:
            candidate_text = self._record_text(record)
            if candidate_text:
                candidate_texts.append(candidate_text)
                candidate_records.append(record)

        active_scene_text = self._record_text(
            active_scene if isinstance(active_scene, dict) else {"text": active_scene}
        )
        comparison_texts = list(candidate_texts)
        if active_topic:
            comparison_texts.append(safe_trim_text(active_topic, 1600))
        if active_scene_text:
            comparison_texts.append(active_scene_text)

        semantic_map = self.semantic_scores(query, comparison_texts)

        active_topic_score = (
            float(semantic_map.get(safe_trim_text(active_topic, 1600), 0.0))
            if active_topic else 0.0
        )
        active_scene_similarity = (
            float(semantic_map.get(active_scene_text, 0.0))
            if active_scene_text else 0.0
        )

        latest_created_at = max(
            [float(r.get("created_at") or r.get("timestamp") or 0.0) for r in candidate_records] or [0.0]
        )
        ranked = []
        for record, candidate_text in zip(candidate_records, candidate_texts):
            semantic = float(semantic_map.get(candidate_text, 0.0))
            day_recency = max(0.0, 1.0 - (record.get("day_index", 0) / MEMORY_DAYS))
            created_at = float(record.get("created_at") or record.get("timestamp") or 0.0)
            temporal_recency = (
                max(0.0, min(1.0, created_at / latest_created_at))
                if latest_created_at > 0.0 and created_at > 0.0
                else day_recency
            )

            # Memory relation is semantic, never substring/keyword routing.
            relation = 0.10 * active_topic_score
            if record.get("memory_kind") == "visual_scene":
                relation += 0.15 * active_scene_similarity

            if retrieval_mode == "memory_query":
                # Within completed dialogue pairs, chronological order is the
                # decisive axis for an unqualified recall request; semantics
                # differentiates ties instead of replacing temporal order.
                score = min(1.0, (semantic * 0.30) + (temporal_recency * 0.70))
                threshold = 0.20
            else:
                score = min(1.0, (semantic * 0.65) + (day_recency * 0.20) + relation)
                threshold = 0.30
            if score >= threshold:
                ranked.append((score, record))

        ranked.sort(key=lambda x: x[0], reverse=True)
        matches = []
        for score, record in ranked[: max(1, int(limit))]:
            matches.append({
                "score": round(score, 6),
                "day_index": record.get("day_index", 0),
                "memory_kind": record.get("memory_kind"),
                "slot": record.get("slot"),
                "record_type": record.get("record_type"),
                "topic": record.get("topic"),
                "user_meaning": safe_trim_text(record.get("user_meaning"), 800),
                "april_meaning": safe_trim_text(record.get("april_meaning"), 1200),
                "answer_summary": safe_trim_text(record.get("answer_summary"), 800),
                "summary": safe_trim_text(
                    record.get("summary") or record.get("text") or record.get("answer_summary") or self._record_text(record),
                    800,
                ),
                "scene": record.get("scene"),
                "visual": record.get("scene") if record.get("memory_kind") == "visual_scene" else None,
                "timestamp": record.get("timestamp"),
            })

        # Visual memory is already TTL-cleaned before this query. This block
        # only measures whether still-live visual context is relevant now.
        dialog_state = state_obj.get("dialog_state") if isinstance(state_obj.get("dialog_state"), dict) else {}
        turn_relation = (
            state_obj.get("_turn_dialogue_relation")
            if isinstance(state_obj.get("_turn_dialogue_relation"), dict)
            else {}
        )
        context_dependency = str(
            turn_relation.get("relation")
            or dialog_state.get("context_dependency")
            or ""
        ).strip().lower()
        measured_continuation = bool(
            turn_relation.get("continuation")
            or turn_relation.get("same_scene")
            or dialog_state.get("continuation")
            or dialog_state.get("reference_to_previous")
        )
        if context_dependency in {"new_topic", "independent"} and not measured_continuation:
            active_visual_context_relevant = False
        else:
            active_visual_context_relevant = bool(
                current_visual and (
                    active_scene_similarity >= 0.55
                    or turn_relation.get("same_scene")
                    or turn_relation.get("continuation")
                    or turn_relation.get("reference_to_previous")
                )
            )

        matrix = self.build_memory_matrix(state_obj, query=query, limit=limit)
        state_obj["memory_matrix"] = matrix
        return {
            "engine": self.VERSION,
            "matrix_version": self.MATRIX_VERSION,
            "window_days": MEMORY_DAYS,
            "matches": matches,
            "memory_matrix": matrix,
            "memory_cleanup": deepcopy(state_obj.get("memory_cleanup", {})),
            "active_scene_similarity": round(active_scene_similarity, 6),
            "active_visual_scene": current_visual if active_visual_context_relevant else None,
            "stored_visual_scene": current_visual,
            "active_visual_context_relevant": active_visual_context_relevant,
            "active_topic_similarity": round(active_topic_score, 6),
            "retrieval_mode": retrieval_mode,
            "focus_state": deepcopy(focus),
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }

    @staticmethod
    def _is_visual_scene_contract(block_types):
        return any(
            str(block_type or "").strip().lower() in VISUAL_SCENE_BLOCK_TYPES
            for block_type in (block_types or [])
        )

    @staticmethod
    def _continuity_context(state_obj, contract):
        """Read already-measured dialogue continuity; never infer from keywords."""
        dialogue_state = state_obj.get("dialog_state", {})
        metadata = contract.get("metadata") if isinstance(contract.get("metadata"), dict) else {}
        space = contract.get("space_continuity") if isinstance(contract.get("space_continuity"), dict) else {}

        explicit_continuation = (
            metadata.get("continuation")
            if "continuation" in metadata
            else space.get("continuation")
        )
        explicit_dependency = (
            metadata.get("context_dependency")
            if "context_dependency" in metadata
            else space.get("context_dependency")
        )

        if explicit_continuation is not None:
            continuation = bool(explicit_continuation)
        else:
            continuation = bool(dialogue_state.get("continuation") or dialogue_state.get("reference_to_previous"))

        dependency = str(
            explicit_dependency
            or dialogue_state.get("context_dependency")
            or ""
        ).strip().lower()

        return {
            "continuation": continuation,
            "context_dependency": dependency,
            "new_topic": dependency in {"new_topic", "independent"} and not continuation,
        }

    # ---------- unified writes ----------

    def record_topic(self, state_obj, topic, slot="A", score=1.0):
        self.ensure_runtime(state_obj)
        slot = slot if slot in TOPIC_CLASSES else "C"
        state_obj["memory_timeline"]["day_0"][slot].append({
            "topic": safe_trim_text(topic, 400),
            "score": float(score or 0.0),
            "timestamp": time.time(),
        })
        state_obj["memory_timeline"]["day_0"]["topics"].append({
            "topic": safe_trim_text(topic, 400),
            "timestamp": time.time(),
        })
        self._trim_topic_memory(state_obj)

    def record_visual_scene(self, state_obj, scene_payload):
        """Promote one confirmed visual scene to active and archive it in 7-day memory.

        Active visual state is a one-scene hot pointer. The seven-day timeline is
        the durable dynamic memory. A new scene replaces the hot pointer; older
        scenes remain retrievable only while they are inside day_0..day_6 and
        are deleted when they cross the day_7 TTL boundary.
        """
        self.ensure_runtime(state_obj)
        if not isinstance(scene_payload, dict):
            return

        record = deepcopy(scene_payload)
        record.setdefault("timestamp", time.time())
        record.setdefault("memory_kind", "visual_scene")

        scene_id = str(record.get("scene_id") or "").strip()
        existing = state_obj["memory_timeline"]["day_0"]["visual_scenes"]

        if scene_id:
            existing[:] = [
                item for item in existing
                if not (
                    isinstance(item, dict)
                    and str(item.get("scene_id") or "").strip() == scene_id
                )
            ]

        existing.append(record)
        state_obj["memory_timeline"]["day_0"]["visual_scenes"] = existing[-TOPIC_MEMORY_LIMIT:]

        # The latest visual topic is the only hot visual pointer.
        visual_topic = (
            safe_trim_text(
                record.get("topic")
                or record.get("trajectory")
                or record.get("current_request")
                or record.get("summary"),
                500,
            )
            or None
        )
        state_obj["active_visual_topic"] = {
            "topic": visual_topic,
            "scene_id": scene_id,
            "timestamp": record.get("timestamp"),
            "source": "visual_scene",
        } if visual_topic else None

        state_obj["visual_topic_history"].append(deepcopy(state_obj["active_visual_topic"]))
        state_obj["visual_topic_history"] = state_obj["visual_topic_history"][-VISUAL_HISTORY_LIMIT:]

        state_obj["active_visual_scene"] = record
        state_obj["active_visual_scene_turn"] = deepcopy(record)
        state_obj["visual_scene_history"].append(record)
        state_obj["visual_scene_history"] = state_obj["visual_scene_history"][-VISUAL_HISTORY_LIMIT:]

    def record_intent(self, state_obj, signal):
        self.ensure_runtime(state_obj)
        if isinstance(signal, dict):
            signal = deepcopy(signal)
            signal.setdefault("timestamp", time.time())
            state_obj["memory_timeline"]["day_0"]["intent_signals"].append(signal)
            state_obj["memory_signals"] = signal

    def _trim_topic_memory(self, state_obj):
        for key in (
            "visual_topic_registry",
            "task_context_storage",
            "continuity_context_storage",
            "memory_anchor_storage",
        ):
            value = state_obj.get(key)
            if isinstance(value, list):
                state_obj[key] = value[-TOPIC_MEMORY_LIMIT:]

        day = state_obj["memory_timeline"]["day_0"]
        for slot in TOPIC_CLASSES:
            day[slot] = day[slot][-TOPIC_MEMORY_LIMIT:]
        day["topics"] = day["topics"][-TOPIC_MEMORY_LIMIT:]
        day["objects"] = day["objects"][-TOPIC_MEMORY_LIMIT:]
        day["intent_signals"] = day["intent_signals"][-TOPIC_MEMORY_LIMIT:]

    # ---------- unified scene ----------

    def refresh_scene(self, state_obj):
        self.ensure_runtime(state_obj)
        scene_state = state_obj.get("scene_state", {})
        focus = state_obj.get("focus_state", {})

        state_obj["active_scene"] = {
            "scene_state": deepcopy(scene_state),
            "focus_state": deepcopy(focus),
            "memory_timeline": deepcopy(state_obj.get("memory_timeline", {})),
            "memory_cycle": deepcopy(state_obj.get("memory_cycle", {})),
            "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
            "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
            "open_loops": deepcopy(state_obj.get("open_loops", [])),
            "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
            "active_flow": deepcopy(state_obj.get("active_flow")),
            "active_visual_scene": deepcopy(state_obj.get("active_visual_scene")),
            "active_visual_topic": deepcopy(state_obj.get("active_visual_topic")),
            "visual_topic_history": deepcopy(state_obj.get("visual_topic_history", [])),
            "visual_summary": deepcopy(state_obj.get("visual_summary", {})),
            "memory_cleanup": deepcopy(state_obj.get("memory_cleanup", {})),
            "today_visual_memory": deepcopy(
                state_obj["memory_timeline"]["day_0"].get("visual_scenes", [])
            ),
        }
        return state_obj["active_scene"]

    def build_executor_bridge(self, state_obj, query=""):
        self.ensure_runtime(state_obj)
        memory = self.query(state_obj, query) if query else {
            "engine": self.VERSION,
            "window_days": MEMORY_DAYS,
            "matches": [],
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }

        focus = state_obj.get("focus_state", {})
        return {
            "active_topic": focus.get("active_topic"),
            "active_goal": focus.get("active_goal"),
            "active_scene": focus.get("active_scene"),
            "active_object": focus.get("active_object"),
            "priority_score": focus.get("priority_score", 0.0),
            "intent_freshness": focus.get("intent_freshness", 0.0),
            "today": deepcopy(state_obj["memory_timeline"]["day_0"]),
            "yesterday": deepcopy(state_obj["memory_timeline"]["day_1"]),
            "open_loops": deepcopy(state_obj.get("open_loops", [])),
            "quantum_memory": memory,
            "memory_version": self.VERSION,
            "window_days": MEMORY_DAYS,
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }


QUANTUM_MEMORY_ENGINE = QuantumMemoryEngine()


# =====================================================
# CANONICAL STATE ACCESS
# =====================================================

state = {}
image_storage = {}


def get_state(user_id):
    key = str(user_id)

    with _state_lock:
        if key not in state:
            db_state = None
            try:
                if callable(load_memory):
                    db_state = load_memory(key)
            except Exception as exc:
                safe_state_log(f"STATE LOAD FAILED: {exc}")

            if isinstance(db_state, dict):
                state[key] = db_state
                safe_state_log(f"STATE RESTORED: {key}")
            else:
                state[key] = build_default_state()
                safe_state_log(f"NEW STATE: {key}")

        state[key]["user_id"] = key
        if not state[key].get("conversation_id"):
            state[key]["conversation_id"] = (
                f"april-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:24]}"
            )
        state[key]["memory_scope"] = {
            "user_id": key,
            "conversation_id": state[key]["conversation_id"],
            "scope_version": "USER_SCOPED_SCENE_V2",
        }
        QUANTUM_MEMORY_ENGINE.ensure(state[key])
        return state[key]


def _persistable_snapshot(value, _active=None):
    excluded = {
        "_machine_context",
        "_executor_context_packet",
        "_quantum_evidence_field",
        "_quantum_processor_context",
        "_semantic_encoder",
    }
    active = _active if _active is not None else set()

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    oid = id(value)
    if oid in active:
        return None

    if isinstance(value, dict):
        active.add(oid)
        try:
            result = {}
            for key, child in value.items():
                key = str(key)
                if key in excluded:
                    continue
                result[key] = _persistable_snapshot(child, active)
            return result
        finally:
            active.remove(oid)

    if isinstance(value, (list, tuple, set)):
        active.add(oid)
        try:
            return [_persistable_snapshot(child, active) for child in value]
        finally:
            active.remove(oid)

    return str(value)


def persist_state(user_id):
    try:
        state_obj = get_state(user_id)
        if callable(save_memory):
            save_memory(str(user_id), _persistable_snapshot(state_obj))
    except Exception as exc:
        safe_state_log(f"PERSIST ERROR: {exc}")


# =====================================================
# SCENE API
# =====================================================

def get_scene_state(user_id):
    return get_state(user_id).get("scene_state", {})


def update_scene_state(user_id, updates):
    if not isinstance(updates, dict):
        return

    state_obj = get_state(user_id)
    scene = state_obj.get("scene_state", {})
    allowed = {
        "mode", "type", "goal", "continuity_mode", "render_type",
        "renderer_active", "visual_active", "active_flow",
        "trajectory_locked", "anchor", "anchor_type", "confidence",
        "updated_at",
    }

    for key, value in updates.items():
        if key in allowed:
            scene[key] = value

    scene["updated_at"] = time.time()
    state_obj["scene_state"] = scene
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)


def clear_scene_state(user_id):
    state_obj = get_state(user_id)
    visual_scene = state_obj.get("active_visual_scene")
    new_scene = build_default_scene()

    if visual_scene:
        new_scene["visual_active"] = True
        new_scene["continuity_mode"] = "visual"

    state_obj["scene_state"] = new_scene
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)


# =====================================================
# IMAGE / FLOW / SIMPLE STATE API
# =====================================================

def set_image_context(user_id, ctx):
    image_storage[str(user_id)] = ctx
    state_obj = get_state(user_id)
    state_obj["image_context"] = ctx

    scene = state_obj.get("scene_state", {})
    scene["visual_active"] = True
    scene["continuity_mode"] = "visual"
    scene["updated_at"] = time.time()
    state_obj["scene_state"] = scene

    if isinstance(ctx, dict):
        QUANTUM_MEMORY_ENGINE.record_visual_scene(state_obj, ctx)

    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)


def get_image_context(user_id):
    return image_storage.get(str(user_id), get_state(user_id).get("image_context"))


def set_awaiting(user_id, value):
    get_state(user_id)["awaiting"] = bool(value)


def get_awaiting(user_id):
    return get_state(user_id).get("awaiting", False)


def set_last_prompt(user_id, prompt):
    get_state(user_id)["last_prompt"] = prompt


def get_last_prompt(user_id):
    return get_state(user_id).get("last_prompt")


# =====================================================
# DIALOG MEMORY
# =====================================================

def update_memory_summary(state_obj, user_text="", assistant_text=""):
    current = state_obj.get("memory_summary", "")
    entry = " | ".join(
        x for x in (
            safe_trim_text(user_text, 240),
            safe_trim_text(assistant_text, 240),
        ) if x
    )
    if entry:
        combined = (current + " | " + entry).strip()
        state_obj["memory_summary"] = combined[-SESSION_MEMORY_LIMIT:]
        state_obj["memory_summary_meta"] = {
            "created_at": time.time(),
            "expires_after_days": MEMORY_DAYS,
            "memory_kind": "summary",
        }


def build_visual_scene_summary(state_obj):
    scene = state_obj.get("active_visual_scene")
    if not isinstance(scene, dict):
        return {}

    return {
        "type": scene.get("scene_type"),
        "topic": scene.get("topic"),
        "goal": scene.get("goal"),
        "objects": safe_list(scene.get("objects"))[:5],
        "colors": safe_list(scene.get("colors"))[:5],
        "scene_id": scene.get("scene_id"),
    }


def _archive_dialog_pair(state_obj, user_id, user_msg, april_msg):
    """Persist one completed USER↔APRIL pair into today's rolling memory slot."""
    timeline = state_obj.get("memory_timeline") or build_memory_timeline()
    day0 = timeline.setdefault("day_0", build_memory_day())
    dialog_pairs = day0.setdefault("dialog_pairs", [])
    record = {
        "record_type": "dialog_pair",
        "user_id": str(user_id),
        "user_meaning": safe_trim_text(user_msg, 800),
        "april_meaning": safe_trim_text(april_msg, 1400),
        "answer_summary": safe_trim_text(april_msg, 1000),
        "visual_summary": safe_trim_text(
            build_visual_scene_summary(state_obj) or "",
            1000,
        ),
        "topic": safe_trim_text(
            state_obj.get("current_topic") or state_obj.get("active_topic_slot") or "",
            240,
        ),
        "continuation_hint": "available_for_reference",
        "created_at": time.time(),
        "expires_after_days": MEMORY_DAYS,
    }
    # Deduplicate the same completed pair if a compatibility caller invokes
    # compression more than once.
    fingerprint = (
        record["user_meaning"],
        record["april_meaning"],
    )
    if any(
        isinstance(item, dict)
        and (item.get("user_meaning"), item.get("april_meaning")) == fingerprint
        and item.get("user_id") == record["user_id"]
        for item in dialog_pairs[-HOT_DIALOG_LIMIT:]
    ):
        return
    dialog_pairs.append(record)
    day0["dialog_pairs"] = dialog_pairs[-HOT_DIALOG_LIMIT:]
    state_obj["memory_timeline"] = timeline


def compress_dialog_to_summary(state_obj):
    """
    Compatibility summary builder.

    The hot dialog is NEVER replaced by a [COMPRESSED_MEMORY] marker anymore.
    Completed pairs are archived by add_dialog() into day_0 and continue through
    the live day_0..day_6 window; day_7 is the deletion boundary.
    """
    dialog = safe_list(state_obj.get("dialog"))
    if not dialog:
        return

    recent = [
        {
            "role": msg.get("role"),
            "content": safe_trim_text(msg.get("content", ""), 180),
        }
        for msg in dialog[-8:]
        if isinstance(msg, dict)
    ]

    machine_summary = {
        "scene": {
            "type": state_obj.get("scene_state", {}).get("type"),
            "goal": state_obj.get("scene_state", {}).get("goal"),
            "flow": state_obj.get("scene_state", {}).get("active_flow"),
            "continuity": state_obj.get("scene_state", {}).get("continuity_mode"),
            "render": state_obj.get("scene_state", {}).get("render_type"),
        },
        "visual": build_visual_scene_summary(state_obj),
        "dialog": recent,
        "focus_state": deepcopy(state_obj.get("focus_state", {})),
        "hot_dialog_limit": HOT_DIALOG_LIMIT,
    }

    state_obj["memory_summary"] = str(machine_summary)[-SESSION_MEMORY_LIMIT:]
    state_obj["memory_summary_meta"] = {
        "created_at": time.time(),
        "expires_after_days": MEMORY_DAYS,
        "memory_kind": "summary",
    }

def trim_image_memory(state_obj):
    memory = safe_list(state_obj.get("image_memory"))
    state_obj["image_memory"] = memory[-IMAGE_MEMORY_LIMIT:]


def trim_visual_history(state_obj):
    history = safe_list(state_obj.get("visual_scene_history"))
    state_obj["visual_scene_history"] = history[-VISUAL_HISTORY_LIMIT:]


def add_dialog(user_id, role, content, metadata=None):
    state_obj = get_state(user_id)
    dialog = safe_list(state_obj.get("dialog"))
    message = compact_dialog_message(role, content)
    if isinstance(metadata, dict) and metadata:
        message["metadata"] = deepcopy(metadata)
    dialog.append(message)

    if role == "user":
        state_obj["last_user_turn"] = safe_trim_text(content, 320)
        state_obj["meta"]["last_user_message"] = safe_trim_text(content, 320)
    else:
        state_obj["last_april_turn"] = safe_trim_text(content, 320)
        state_obj["meta"]["last_bot_message"] = safe_trim_text(content, 320)

    # Canonical Free hot window: exactly 30 messages. Completed pairs leave the
    # hot window only as one semantic memory record and continue through day_0..day_6.
    while len(dialog) > HOT_DIALOG_LIMIT:
        if len(dialog) >= 2:
            first, second = dialog[0], dialog[1]
            first_role = str(first.get("role") or "").lower() if isinstance(first, dict) else ""
            second_role = str(second.get("role") or "").lower() if isinstance(second, dict) else ""
            if first_role == "user" and second_role in {"assistant", "april"}:
                _archive_dialog_pair(
                    state_obj,
                    user_id,
                    first.get("content", ""),
                    second.get("content", ""),
                )
                dialog = dialog[2:]
                continue
        # Preserve the current turn and avoid an infinite loop on malformed
        # legacy history. Archive the oldest unmatched item as a memory event.
        oldest = dialog.pop(0)
        day0 = state_obj["memory_timeline"]["day_0"]
        day0.setdefault("topics", []).append({
            "record_type": "dialog_turn",
            "user_id": str(user_id),
            "role": oldest.get("role") if isinstance(oldest, dict) else None,
            "content": safe_trim_text(oldest.get("content", "") if isinstance(oldest, dict) else oldest, 800),
            "created_at": time.time(),
            "expires_after_days": MEMORY_DAYS,
        })
        day0["topics"] = day0["topics"][-HOT_DIALOG_LIMIT:]

    state_obj["dialog"] = dialog
    state_obj["dialog_state"] = {
        "timeline": deepcopy(dialog),
        "hot_limit": HOT_DIALOG_LIMIT,
        "hot_user_target": HOT_DIALOG_LIMIT // 2,
        "hot_april_target": HOT_DIALOG_LIMIT // 2,
        "last_user_turn": state_obj.get("last_user_turn", ""),
        "last_april_turn": state_obj.get("last_april_turn", ""),
        "active_topic": state_obj.get("current_topic"),
        "focus": deepcopy(state_obj.get("focus_state", {})),
    }

    trim_image_memory(state_obj)
    trim_visual_history(state_obj)
    trim_topic_memory(state_obj)
    state_obj["active_scene"] = QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)



def get_dialog_state(user_id):
    return get_state(user_id).get("dialog_state", {})


def set_dialog_state(user_id, data):
    get_state(user_id)["dialog_state"] = data


# =====================================================
# FLOW / ENTITY API
# =====================================================

def set_active_flow(user_id, flow):
    state_obj = get_state(user_id)
    state_obj["active_flow"] = flow

    scene = state_obj.get("scene_state", {})
    if isinstance(flow, dict):
        flow_type = flow.get("type")
        scene["active_flow"] = flow_type
        scene["trajectory_locked"] = True
        scene["goal"] = safe_trim_text(flow.get("original"), 240)

        if flow_type in {"renderer_space", "graph", "formula", "diagram", "table"}:
            scene["renderer_active"] = True
            scene["render_type"] = flow_type
            scene["continuity_mode"] = "renderer"

        if flow_type in {"image", "image_generate", "image_edit"}:
            scene["visual_active"] = True
            scene["continuity_mode"] = "visual"

    scene["updated_at"] = time.time()
    state_obj["scene_state"] = scene
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)


def get_active_flow(user_id):
    return get_state(user_id).get("active_flow")


def clear_active_flow(user_id):
    state_obj = get_state(user_id)
    state_obj["active_flow"] = None

    scene = state_obj.get("scene_state", {})
    scene["active_flow"] = None
    scene["trajectory_locked"] = False

    if state_obj.get("active_visual_scene"):
        scene["visual_active"] = True
        scene["continuity_mode"] = "visual"

    scene["updated_at"] = time.time()
    state_obj["scene_state"] = scene
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)


def set_last_entity(user_id, entity):
    get_state(user_id)["meta"]["last_entity"] = entity


def get_last_entity(user_id):
    return get_state(user_id).get("meta", {}).get("last_entity")


# =====================================================
# COMPATIBILITY / MEMORY BRIDGES
# All bridges read the same Quantum Memory Engine state.
# =====================================================

def build_active_scene(user_id):
    state_obj = get_state(user_id)
    return {
        "dialog_summary": state_obj.get("memory_summary", ""),
        "visual_context": state_obj.get("visual_continuity_summary", {}),
        "active_visual_scene": state_obj.get("active_visual_scene"),
        "active_flow": state_obj.get("active_flow"),
        "scene_state": state_obj.get("scene_state", {}),
        "focus_snapshot": state_obj.get("focus_snapshot", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
    }


def refresh_active_scene(user_id):
    return QUANTUM_MEMORY_ENGINE.refresh_scene(get_state(user_id))


def get_active_focus(user_id):
    return get_state(user_id).get("dynamic_focus", {})


def build_memory_snapshot(user_id):
    state_obj = get_state(user_id)
    return {
        "memory_version": QUANTUM_MEMORY_ENGINE.VERSION,
        "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
        "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
        "open_loops": deepcopy(state_obj.get("open_loops", [])),
        "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
        "active_flow": deepcopy(state_obj.get("active_flow")),
        "scene_state": deepcopy(state_obj.get("scene_state", {})),
        "memory_timeline": deepcopy(state_obj.get("memory_timeline", {})),
        "memory_cycle": deepcopy(state_obj.get("memory_cycle", {})),
    }


def cleanup_closed_loops(user_id):
    state_obj = get_state(user_id)
    loops = safe_list(state_obj.get("open_loops"))
    state_obj["open_loops"] = [
        loop for loop in loops
        if not (isinstance(loop, dict) and loop.get("status") == "closed")
    ]
    persist_state(user_id)


def build_golden_memory_state():
    return {
        "dynamic_focus": {},
        "goal_hierarchy": {},
        "open_loops": [],
        "memory_signals": {},
    }


def update_dynamic_focus(user_id, focus_payload):
    get_state(user_id)["dynamic_focus"] = focus_payload or {}


def update_goal_hierarchy(user_id, goal_payload):
    get_state(user_id)["goal_hierarchy"] = goal_payload or {}


def update_open_loops(user_id, loops_payload):
    get_state(user_id)["open_loops"] = loops_payload or []


def update_memory_signals(user_id, signals_payload):
    state_obj = get_state(user_id)
    state_obj["memory_signals"] = signals_payload or {}
    if isinstance(signals_payload, dict):
        QUANTUM_MEMORY_ENGINE.record_intent(state_obj, signals_payload)


def build_memory_bridge(user_id):
    state_obj = get_state(user_id)
    return {
        "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
        "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
        "open_loops": deepcopy(state_obj.get("open_loops", [])),
        "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
    }


def update_focus_snapshot(user_id, abcde_payload):
    payload = abcde_payload if isinstance(abcde_payload, dict) else {}
    state_obj = get_state(user_id)
    state_obj["focus_snapshot"] = {
        "topic": payload.get("topic"),
        "scene": payload.get("scene"),
        "object": payload.get("object"),
        "focus": payload.get("focus"),
        "intent": payload.get("intent"),
    }
    return state_obj["focus_snapshot"]


def get_focus_snapshot(user_id):
    state_obj = get_state(user_id)
    focus_state = state_obj.get("focus_state")
    if isinstance(focus_state, dict) and focus_state:
        return {
            "topic": focus_state.get("active_topic"),
            "scene": focus_state.get("active_scene"),
            "object": focus_state.get("active_object"),
            "focus": focus_state.get("priority_score"),
            "intent": focus_state.get("intent_freshness"),
        }
    return state_obj.get("focus_snapshot", {})


def build_context_memory_bridge(user_id):
    state_obj = get_state(user_id)
    return {
        "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
        "focus_snapshot": deepcopy(state_obj.get("focus_snapshot", {})),
        "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
        "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
        "active_flow": deepcopy(state_obj.get("active_flow")),
    }


def trim_topic_memory(state_obj):
    QUANTUM_MEMORY_ENGINE.ensure_runtime(state_obj)
    QUANTUM_MEMORY_ENGINE._trim_topic_memory(state_obj)


def update_scene_relation(user_id, relation):
    get_state(user_id)["scene_relation"] = relation or {}


def push_scene_history(user_id, scene):
    state_obj = get_state(user_id)
    history = safe_list(state_obj.get("scene_history"))
    history.append(scene)
    state_obj["scene_history"] = history[-20:]


def refresh_unified_scene(user_id):
    return QUANTUM_MEMORY_ENGINE.refresh_scene(get_state(user_id))


# =====================================================
# SEVEN-DAY MEMORY API
# =====================================================

def build_memory_day():
    return {
        "A": [],
        "B": [],
        "C": [],
        "D": [],
        "E": [],
        "visual_scenes": [],
        "topics": [],
        "objects": [],
        "intent_signals": [],
        "created_at": time.time(),
    }


def build_memory_timeline():
    return {f"day_{i}": build_memory_day() for i in range(MEMORY_DAYS)}


def ensure_memory_engine(state_obj):
    return QUANTUM_MEMORY_ENGINE.ensure(state_obj)


def memory_rollover_if_needed(user_id):
    changed = QUANTUM_MEMORY_ENGINE.rollover(get_state(user_id))
    if changed:
        persist_state(user_id)
    return changed


def update_focus_state(user_id, payload):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    payload = payload if isinstance(payload, dict) else {}

    state_obj["focus_state"] = {
        "active_topic": payload.get("topic"),
        "active_scene": payload.get("scene"),
        "active_object": payload.get("object"),
        "active_goal": payload.get("goal"),
        "priority_score": payload.get("priority_score", 0.0),
        "intent_freshness": payload.get("intent_freshness", 0.0),
    }
    state_obj["focus_snapshot"] = {
        "topic": payload.get("topic"),
        "scene": payload.get("scene"),
        "object": payload.get("object"),
        "focus": payload.get("priority_score", 0.0),
        "intent": payload.get("intent_freshness", 0.0),
    }
    persist_state(user_id)


def register_topic(user_id, topic, slot="A", score=1.0):
    state_obj = get_state(user_id)
    QUANTUM_MEMORY_ENGINE.record_topic(state_obj, topic, slot, score)
    persist_state(user_id)


def bind_visual_scene_to_memory(user_id, scene_payload):
    state_obj = get_state(user_id)
    QUANTUM_MEMORY_ENGINE.record_visual_scene(state_obj, scene_payload)
    persist_state(user_id)


def build_memory_context(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    return {
        "focus_state": deepcopy(state_obj.get("focus_state", {})),
        "memory_timeline": deepcopy(state_obj.get("memory_timeline", {})),
        "memory_cycle": deepcopy(state_obj.get("memory_cycle", {})),
        "open_loops": deepcopy(state_obj.get("open_loops", [])),
        "active_flow": deepcopy(state_obj.get("active_flow")),
        "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
        "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
        "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
        "engine": QUANTUM_MEMORY_ENGINE.VERSION,
        "window_days": MEMORY_DAYS,
        "memory_cleanup": deepcopy(state_obj.get("memory_cleanup", {})),
        "memory_matrix": deepcopy(state_obj.get("memory_matrix", {})),
    }


def build_executor_memory_bridge(user_id, query=""):
    return QUANTUM_MEMORY_ENGINE.build_executor_bridge(get_state(user_id), query=query)


def ensure_memory_runtime(user_id):
    return QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))


def build_unified_memory_bridge(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    return {
        "focus_state": deepcopy(state_obj.get("focus_state", {})),
        "focus_snapshot": deepcopy(state_obj.get("focus_snapshot", {})),
        "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
        "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
        "open_loops": deepcopy(state_obj.get("open_loops", [])),
        "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
        "memory_timeline": deepcopy(state_obj.get("memory_timeline", {})),
        "memory_cycle": deepcopy(state_obj.get("memory_cycle", {})),
        "engine": QUANTUM_MEMORY_ENGINE.VERSION,
        "window_days": MEMORY_DAYS,
    }


def sync_focus_layers(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    focus = state_obj.get("focus_state", {})
    state_obj["focus_snapshot"] = {
        "topic": focus.get("active_topic"),
        "scene": focus.get("active_scene"),
        "object": focus.get("active_object"),
        "focus": focus.get("priority_score"),
        "intent": focus.get("intent_freshness"),
    }
    if not state_obj.get("dynamic_focus"):
        state_obj["dynamic_focus"] = deepcopy(state_obj["focus_snapshot"])


def prepare_visual_context_for_turn(user_id, current_request):
    """Expose the current user-scoped scene as memory evidence without deciding relevance.

    The current scene is already the compact USER↔APRIL dialogue state. The
    Quantum Processor/interpretation layer decides whether the turn continues
    it or starts a new topic. State Manager never resurrects an archived scene,
    never routes by words, and never scores a renderer.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    current = str(current_request or "").strip()

    scene = state_obj.get("active_visual_scene")
    if not isinstance(scene, dict) or not scene:
        state_obj["active_visual_scene_turn"] = None
        state_obj["stored_visual_scene_turn"] = None
        return {
            "active": False,
            "released": False,
            "overlap": 0.0,
            "semantic_relevance": 0.0,
            "continuation_score": 0.0,
            "decision_owner": "QUANTUM_PROCESSOR",
            "memory_role": "evidence_only",
            "user_id": str(user_id),
            "current_request": current,
        }

    # The persisted scene is durable evidence, not an automatic continuation.
    # Do not promote it into the turn-local context before the semantic matrix
    # has established a relation to the current request.
    state_obj["active_visual_scene_turn"] = None
    state_obj["stored_visual_scene_turn"] = None

    return {
        "active": False,
        "released": True,
        "overlap": 0.0,
        "semantic_relevance": 0.0,
        "continuation_score": 0.0,
        "decision_owner": "QUANTUM_PROCESSOR",
        "memory_role": "evidence_only",
        "user_id": str(user_id),
        "current_request": current,
        "scene_id": str(scene.get("scene_id") or ""),
    }

def restore_visual_context_after_turn(user_id, *, new_scene_active=False):
    """Finalize turn-local markers without resurrecting or erasing scene memory.

    The canonical USER↔APRIL scene is already committed by update_scene_context()
    inside the Executor. This compatibility hook must therefore be idempotent:
    it may finalize transient fields, but it must never promote an archived scene
    or clear the current scene after a text-only turn.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))

    current = state_obj.get("active_visual_scene_turn")
    if isinstance(current, dict) and current:
        state_obj["active_visual_scene"] = deepcopy(current)
        state_obj["current_visual_scene"] = deepcopy(current)
        state_obj["active_visual_topic"] = {
            "topic": safe_trim_text(
                current.get("topic")
                or current.get("current_request")
                or current.get("summary"),
                500,
            ),
            "scene_id": str(current.get("scene_id") or ""),
            "conversation_id": str(state_obj.get("conversation_id") or ""),
            "user_id": str(user_id),
            "turn_id": current.get("turn_id"),
            "source": "current_dialogue_scene",
        }

    # Do NOT resurrect stored_visual_scene_turn and do NOT clear active_visual_scene.
    # Archived scenes remain only inside day_0..day_6 until TTL cleanup removes them.
    state_obj["stored_visual_scene_turn"] = None
    state_obj["active_visual_scene_turn"] = None
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)

def bind_current_visual_scene(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    visual = state_obj.get("active_visual_scene_turn") or state_obj.get("active_visual_scene")
    if isinstance(visual, dict) and visual:
        state_obj["active_visual_scene"] = deepcopy(visual)
        state_obj["active_visual_topic"] = {
            "topic": safe_trim_text(
                visual.get("topic")
                or visual.get("trajectory")
                or visual.get("current_request")
                or visual.get("summary"),
                500,
            ),
            "scene_id": str(visual.get("scene_id") or ""),
            "timestamp": visual.get("timestamp", time.time()),
            "source": "bind_current_visual_scene",
        }
        persist_state(user_id)


def build_memory_snapshot_v3(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    return {
        "memory_version": QUANTUM_MEMORY_ENGINE.VERSION,
        "focus_state": deepcopy(state_obj.get("focus_state", {})),
        "dynamic_focus": deepcopy(state_obj.get("dynamic_focus", {})),
        "goal_hierarchy": deepcopy(state_obj.get("goal_hierarchy", {})),
        "open_loops": deepcopy(state_obj.get("open_loops", [])),
        "memory_signals": deepcopy(state_obj.get("memory_signals", {})),
        "memory_timeline": deepcopy(state_obj.get("memory_timeline", {})),
        "memory_cycle": deepcopy(state_obj.get("memory_cycle", {})),
        "active_flow": deepcopy(state_obj.get("active_flow")),
    }


# =====================================================
# VISUAL LEDGER / SCENE CONTRACT
# =====================================================

def update_visual_summary(user_id, visual_summary):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    visual_summary = visual_summary or {}
    state_obj["visual_summary"] = visual_summary

    scene = state_obj.get("active_visual_scene")
    last_event = visual_summary.get("last_event")
    event_type = ""
    payload_type = ""
    if isinstance(last_event, dict):
        event_type = str(last_event.get("event_type") or last_event.get("type") or "").strip().lower()
        payload = last_event.get("payload")
        if isinstance(payload, dict):
            payload_type = str(payload.get("type") or "").strip().lower()

    visual_signal = bool(
        visual_summary.get("visual_event")
        or visual_summary.get("scene_id")
        or visual_summary.get("scene_type")
        or visual_summary.get("render_block_types")
    )

    has_event = visual_signal and event_type not in {
        "user_message", "assistant_message", "text", "message",
    } and payload_type not in {
        "user_message", "assistant_message", "text", "message",
    }

    # An empty frontend visual summary is not a new scene. Keep the seven-day
    # memory untouched and do not rewrite the active scene with stale text.
    if not isinstance(scene, dict) or not scene:
        if not has_event:
            return {}
        scene = {}

    if has_event:
        scene["events_count"] = visual_summary.get("scene_events_count", scene.get("events_count", 0))
        scene["last_event"] = visual_summary.get("last_event", scene.get("last_event"))
        scene["package"] = visual_summary.get("package", scene.get("package", "free"))
        scene["session_started_utc"] = visual_summary.get("session_started_utc", scene.get("session_started_utc"))
        scene["timestamp"] = time.time()
        if visual_summary.get("current_request"):
            scene["current_request"] = str(visual_summary["current_request"]).strip()[:1200]

        if scene.get("scene_type") or scene.get("scene_id") or scene.get("summary"):
            QUANTUM_MEMORY_ENGINE.record_visual_scene(state_obj, scene)

    state_obj["active_scene"] = QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)
    return scene

def build_visual_memory_bridge(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    return {
        "user_visual_scene": deepcopy(state_obj.get("active_visual_scene", {})),
        "active_visual_topic": deepcopy(state_obj.get("active_visual_topic")),
        "visual_topic_history": deepcopy(state_obj.get("visual_topic_history", [])),
        "visual_summary": deepcopy(state_obj.get("visual_summary", {})),
        "today_visual_memory": deepcopy(
            state_obj["memory_timeline"]["day_0"].get("visual_scenes", [])
        ),
        "memory_engine": QUANTUM_MEMORY_ENGINE.VERSION,
        "window_days": MEMORY_DAYS,
    }


def _ensure_conversation_scope(state_obj, user_id):
    """Keep all memory under one authenticated user scope and one stable conversation."""
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(state_obj)
    user_scope = str(user_id or "").strip()
    if not user_scope:
        raise ValueError("Authenticated user_id is required for memory scope")

    conversation_id = str(state_obj.get("conversation_id") or "").strip()
    if not conversation_id:
        # Stable per-user conversation identity; not a routing identifier.
        conversation_id = f"april-{hashlib.sha256(user_scope.encode("utf-8")).hexdigest()[:24]}"
        state_obj["conversation_id"] = conversation_id

    state_obj["memory_scope"] = {
        "user_id": user_scope,
        "conversation_id": conversation_id,
        "scope_version": "USER_SCOPED_SCENE_V1",
    }
    return conversation_id


def _next_visual_topic_slot(state_obj):
    current = str(state_obj.get("active_topic_slot") or "A").upper()
    slots = TOPIC_CLASSES
    try:
        idx = slots.index(current)
    except ValueError:
        idx = 0
    return slots[(idx + 1) % len(slots)]


def _archive_current_visual_scene_to_dynamic(state_obj, user_id):
    """Move the current scene into live day_0..day_6 memory without making it hot."""
    current = state_obj.get("current_visual_scene") or state_obj.get("active_visual_scene")
    if not isinstance(current, dict) or not current:
        return

    slot = str(state_obj.get("active_topic_slot") or "A").upper()
    if slot not in TOPIC_CLASSES:
        slot = "A"

    archived = deepcopy(current)
    archived["memory_kind"] = "visual_dialogue_scene"
    archived["user_id"] = str(user_id)
    archived["conversation_id"] = str(state_obj.get("conversation_id") or "")
    archived["archived_from_active_visual"] = True
    archived["archived_at"] = time.time()

    day0 = state_obj["memory_timeline"]["day_0"]
    day0.setdefault(slot, []).append({
        "record_type": "visual_dialogue_scene",
        "user_id": str(user_id),
        "conversation_id": str(state_obj.get("conversation_id") or ""),
        "topic": safe_trim_text(
            archived.get("topic")
            or archived.get("current_request")
            or archived.get("summary"),
            500,
        ),
        "summary": safe_trim_text(
            archived.get("summary")
            or archived.get("april_answer")
            or archived.get("answer"),
            1000,
        ),
        "scene": deepcopy(archived),
        "timestamp": archived.get("archived_at", time.time()),
        "memory_kind": "visual_dialogue_scene",
    })
    day0[slot] = day0[slot][-TOPIC_MEMORY_LIMIT:]

    # Keep it in the visual-scene ledger as durable day_0..day_6 memory too.
    day0.setdefault("visual_scenes", []).append(archived)
    day0["visual_scenes"] = day0["visual_scenes"][-TOPIC_MEMORY_LIMIT:]
    state_obj.setdefault("visual_topic_history", []).append(archived)
    state_obj["visual_topic_history"] = state_obj["visual_topic_history"][-VISUAL_HISTORY_LIMIT:]


def update_scene_context(user_id, scene_contract, current_request="", answer=""):
    """
    One canonical dialogue-scene update.

    Every completed USER→APRIL turn becomes the current visual dialogue scene,
    regardless of whether it contains a graphic/table/formula. The scene stores
    the compact meaning of the user request + April answer + current rendering
    state. When the semantic dialogue contract says the turn is independent/new,
    the previous scene is archived into the existing A-E / 7-day memory and the
    new turn becomes the only active scene.

    No deletion, no trigger routing, no word rules and no renderer decisions.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    conversation_id = _ensure_conversation_scope(state_obj, user_id)

    contract = scene_contract if isinstance(scene_contract, dict) else {}
    if not contract and hasattr(scene_contract, "__dict__"):
        contract = dict(scene_contract.__dict__)

    render_blocks = contract.get("render_blocks") or contract.get("blocks") or []
    block_types = []
    presentation_types = []
    for block in render_blocks:
        if isinstance(block, dict):
            block_type = str(
                block.get("type")
                or block.get("artifact_type")
                or block.get("representation")
                or ""
            ).strip().lower()
            if block_type and block_type not in block_types:
                block_types.append(block_type)
            presentation = block.get("presentation")
            if isinstance(presentation, dict):
                pkind = safe_trim_text(
                    presentation.get("kind")
                    or presentation.get("mode")
                    or presentation.get("renderer")
                    or "",
                    80,
                ).lower()
                if pkind and pkind not in presentation_types:
                    presentation_types.append(pkind)

    current_request_text = str(current_request or "").strip()
    answer_text = str(answer or "").strip()[:4000]

    semantic_scene_state = {}
    metadata = contract.get("metadata") if isinstance(contract.get("metadata"), dict) else {}
    if isinstance(metadata.get("semantic_scene_state"), dict):
        semantic_scene_state = deepcopy(metadata["semantic_scene_state"])

    state_obj["active_scene_contract"] = {
        "scene_version": str(contract.get("scene_version") or ""),
        "active_scene": str(contract.get("active_scene") or ""),
        "space_continuity": deepcopy(contract.get("space_continuity") or {}),
        "metadata": deepcopy(contract.get("metadata") or {}),
        "supported_payloads": deepcopy(contract.get("supported_payloads") or []),
        "render_block_types": block_types,
        "presentation_types": presentation_types,
        "current_request": current_request_text,
        "answer": answer_text,
        "scene_id": str(contract.get("scene_id") or ""),
        "user_id": str(user_id),
        "conversation_id": conversation_id,
    }
    state_obj["current_scene_request"] = current_request_text
    state_obj["last_april_turn"] = answer_text

    continuity = QUANTUM_MEMORY_ENGINE._continuity_context(
        state_obj, state_obj["active_scene_contract"]
    )
    context_mode = str(continuity.get("context_dependency") or "").strip().lower()
    is_continuation = bool(
        continuity.get("continuation")
        or continuity.get("reference_to_previous")
        or context_mode in {"continuation", "same_topic", "reference"}
    )

    current_scene = state_obj.get("current_visual_scene")
    if not isinstance(current_scene, dict):
        current_scene = state_obj.get("active_visual_scene")
    current_scene = current_scene if isinstance(current_scene, dict) else None

    # If there is an existing scene and the semantic contract says the new turn
    # is independent/new, move the previous scene into A-E/7D before replacing it.
    if current_scene and not is_continuation:
        previous_topic = safe_trim_text(
            current_scene.get("topic")
            or current_scene.get("current_request")
            or current_scene.get("summary"),
            500,
        )
        if previous_topic or current_scene.get("scene_id"):
            _archive_current_visual_scene_to_dynamic(state_obj, user_id)
        state_obj["active_topic_slot"] = _next_visual_topic_slot(state_obj)

    previous_scene_id = (
        str(current_scene.get("scene_id") or "")
        if is_continuation and isinstance(current_scene, dict)
        else ""
    )

    state_obj["visual_scene_version"] = int(state_obj.get("visual_scene_version") or 0) + 1
    scene_id = str(
        contract.get("scene_id")
        or f"{conversation_id}:{state_obj['visual_scene_version']}"
    )

    # Canonical "visual dialogue scene": request + answer + semantic state +
    # render/presentation inventory. This is the active scene regardless of
    # whether the visible content is text, formula, table, graph or media.
    scene_record = {
        "scene_id": scene_id,
        "scene_type": str(contract.get("active_scene") or "dialogue"),
        "topic": safe_trim_text(
            (
                current_scene.get("topic")
                if is_continuation and isinstance(current_scene, dict)
                else (
                    contract.get("active_topic")
                    or contract.get("topic")
                    or state_obj.get("current_topic")
                    or state_obj.get("focus_state", {}).get("active_topic")
                    or current_request_text
                )
            ),
            500,
        ),
        "user_request": safe_trim_text(current_request_text, 1200),
        "april_answer": safe_trim_text(answer_text, 2200),
        "summary": safe_trim_text(
            contract.get("summary")
            or answer_text,
            1400,
        ),
        "continuation": is_continuation,
        "context_dependency": context_mode,
        "previous_scene_id": previous_scene_id,
        "render_block_types": block_types,
        "presentation_types": presentation_types,
        "renderer_state": deepcopy(contract.get("renderer_state") or {}),
        "supported_payloads": deepcopy(contract.get("supported_payloads") or []),
        "semantic_state": deepcopy(semantic_scene_state),
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "turn_id": state_obj.get("visual_scene_version"),
        "timestamp": time.time(),
        "memory_kind": "current_visual_dialogue",
    }

    state_obj["semantic_scene_state"] = deepcopy(semantic_scene_state)
    state_obj["current_visual_scene"] = deepcopy(scene_record)
    state_obj["active_visual_scene"] = deepcopy(scene_record)
    state_obj["active_visual_topic"] = {
        "topic": scene_record["topic"],
        "scene_id": scene_id,
        "conversation_id": conversation_id,
        "turn_id": scene_record["turn_id"],
        "user_id": str(user_id),
        "source": "current_dialogue_scene",
    }

    # Preserve every turn in the existing seven-day dialogue archive as one
    # compact USER↔APRIL unit. This is the durable fallback for semantic recall.
    day0 = state_obj["memory_timeline"]["day_0"]
    pairs = day0.setdefault("dialog_pairs", [])
    pair = {
        "record_type": "dialog_pair",
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "user_meaning": safe_trim_text(current_request_text, 800),
        "april_meaning": safe_trim_text(answer_text, 1400),
        "answer_summary": safe_trim_text(contract.get("summary") or answer_text, 1000),
        "semantic_state": deepcopy(semantic_scene_state),
        "visual_scene_id": scene_id,
        "continuation": is_continuation,
        "created_at": time.time(),
        "expires_after_days": MEMORY_DAYS,
    }
    if not any(
        isinstance(item, dict)
        and item.get("user_id") == str(user_id)
        and item.get("conversation_id") == conversation_id
        and item.get("user_meaning") == pair["user_meaning"]
        and item.get("april_meaning") == pair["april_meaning"]
        for item in pairs[-HOT_DIALOG_LIMIT:]
    ):
        pairs.append(pair)
    day0["dialog_pairs"] = pairs[-HOT_DIALOG_LIMIT:]

    # Keep the scene in durable visual history, without allowing old entries to
    # become active again merely because a new request is text-only.
    vs = day0.setdefault("visual_scenes", [])
    vs.append(deepcopy(scene_record))
    day0["visual_scenes"] = vs[-VISUAL_HISTORY_LIMIT:]

    state_obj.setdefault("visual_scene_history", []).append(deepcopy(scene_record))
    state_obj["visual_scene_history"] = state_obj["visual_scene_history"][-VISUAL_HISTORY_LIMIT:]

    # Ensure active scene is always the current turn; old scenes remain only in
    # dynamic memory/history and are recalled by semantic retrieval.
    state_obj["active_visual_scene_turn"] = deepcopy(scene_record)
    state_obj["stored_visual_scene_turn"] = None

    state_obj["active_scene"] = QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)
    return state_obj["active_scene_contract"]

def update_dialog_context(user_id, semantic_result):
    if not isinstance(semantic_result, dict):
        return

    state_obj = get_state(user_id)
    obj = semantic_result.get("current_object")
    topic = semantic_result.get("current_topic")
    contract = semantic_result.get("dialogue_contract") if isinstance(
        semantic_result.get("dialogue_contract"), dict
    ) else {}

    if obj:
        state_obj["current_object"] = obj
        state_obj["active_entity"] = obj
    if topic:
        state_obj["current_topic"] = topic

    # Store measured dialogue evidence in the existing dialog state so the
    # scene updater can consume the same decision without another semantic pass.
    dialogue_state = state_obj.get("dialog_state")
    if not isinstance(dialogue_state, dict):
        dialogue_state = {}

    dialogue_state.update({
        "current_request": semantic_result.get("normalized")
        or semantic_result.get("current_request")
        or "",
        "continuation": bool(
            contract.get("continuation", semantic_result.get("continuation", False))
        ),
        "reference_to_previous": bool(
            contract.get("reference_to_previous", False)
        ),
        "context_dependency": semantic_result.get("context_dependency"),
        "active_topic": topic or semantic_result.get("active_topic"),
        "active_goal": semantic_result.get("active_goal"),
        "dialog_act": contract.get("dialog_act") or semantic_result.get("dialog_act"),
    })
    state_obj["dialog_state"] = dialogue_state

    # Semantic result is evidence entering the same memory field; it is not a
    # second memory system.
    QUANTUM_MEMORY_ENGINE.record_intent(state_obj, {
        "topic": topic,
        "object": obj,
        "intent": semantic_result.get("intent"),
        "context_dependency": semantic_result.get("context_dependency"),
        "continuation": bool(contract.get("continuation", semantic_result.get("continuation", False))),
        "timestamp": time.time(),
    })
    persist_state(user_id)


# =====================================================
# DIRECT QUANTUM MEMORY QUERY API
# =====================================================

def query_dynamic_memory(user_id, query, limit=8, retrieval_mode="semantic"):
    """
    Return semantic memory evidence for the existing Quantum Processor.
    No route/renderer decision is made here.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    result = QUANTUM_MEMORY_ENGINE.query(state_obj, query, limit=limit, retrieval_mode=retrieval_mode)
    return result


def build_quantum_memory_matrix(user_id, query="", limit=8):
    """Return the live quantum-matrix memory evidence for the Quantum Processor."""
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    return QUANTUM_MEMORY_ENGINE.build_memory_matrix(state_obj, query=query, limit=limit)


def build_quantum_memory_signal(user_id, query="", limit=8):
    result = query_dynamic_memory(user_id, query, limit=limit)
    return {
        "engine": QUANTUM_MEMORY_ENGINE.VERSION,
        "window_days": MEMORY_DAYS,
        "signal": result,
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
    }


# =====================================================
# INITIALIZATION
# =====================================================

def initialize_state_engine():
    """
    Cheap initialization only. Heavy semantic model is intentionally not
    loaded here; it is part of the same engine and is activated on demand.
    """
    safe_state_log(
        f"QUANTUM MEMORY ENGINE READY: {QUANTUM_MEMORY_ENGINE.VERSION}, "
        f"window={MEMORY_DAYS}d"
    )
    return QUANTUM_MEMORY_ENGINE


initialize_state_engine()
