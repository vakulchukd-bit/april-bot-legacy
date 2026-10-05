# blocks/state_manager.py
# =====================================================
# APRIL QUANTUM STATE / MEMORY ENGINE
# =====================================================
"""
Canonical State Manager for April.

Design:
- one unified Quantum Memory Engine owns state evolution;
- the authenticated dialogue window is a rolling 12-hour UTC window;
- visual, dialog, focus, goals, loops and scene continuity are one authenticated live-memory field;
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
from typing import Any

try:
    from storage import (
        get_user_plan,
        is_authenticated_user,
        load_dialogue_pairs,
        save_dialogue_pair,
        search_dialogue_memory,
        cleanup_dialogue_memory_utc,
        dialogue_window_bounds,
        utc_cycle_start,
    )
    _STORAGE_IMPORT_ERROR = None
except Exception as exc:
    get_user_plan = None
    is_authenticated_user = None
    load_dialogue_pairs = None
    save_dialogue_pair = None
    search_dialogue_memory = None
    cleanup_dialogue_memory_utc = None
    dialogue_window_bounds = None
    utc_cycle_start = None
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

# Canonical authenticated dialogue memory: a per-user rolling 12h UTC window.
# Each user has an independent cycle anchored to the start of that dialogue; at each
# 12h rollover only the immediately preceding hour is retained as the continuity seed.
DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_SEED_HOURS = 1
DIALOGUE_WINDOW_SECONDS = DIALOGUE_WINDOW_HOURS * 60 * 60
ACTIVE_DIALOGUE_WINDOW_PAIRS = 15
DIALOGUE_SEED_SECONDS = DIALOGUE_SEED_HOURS * 60 * 60
MEMORY_TTL_SECONDS = DIALOGUE_WINDOW_SECONDS
USER_CONTENT_RETENTION_SECONDS = DIALOGUE_WINDOW_SECONDS
MEMORY_SLOTS = 1

SESSION_MEMORY_LIMIT = 1600  # legacy compatibility for summaries/limits outside canonical hot dialogue
HOT_DIALOG_LIMIT = 3
CANONICAL_DIALOG_HOT_LIMIT = 3
RECALL_INDEX_LIMIT = 512
MEMORY_HOURLY_CLEANUP_SECONDS = 3600.0
TOPIC_CLASSES = ["A", "B", "C", "D", "E"]

_INTERNAL_BRANCH_ALPHABET_RU = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _internal_branch_label(tasks: dict, task_id: str = "") -> str:
    rows = []
    for tid, task in (tasks or {}).items():
        if not isinstance(task, dict):
            continue
        rows.append((
            float(task.get("created_at") or task.get("started_at") or 0.0),
            str(task.get("task_id") or tid),
            task,
        ))
    rows.sort(key=lambda x: (x[0], x[1]))
    for idx, (_ts, tid, task) in enumerate(rows):
        if str(tid) == str(task_id) and str(task.get("branch_label") or ""):
            return str(task.get("branch_label"))[:4]
    for idx, (_ts, tid, _task) in enumerate(rows):
        if str(tid) == str(task_id):
            return _INTERNAL_BRANCH_ALPHABET_RU[min(idx, len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)]
    return _INTERNAL_BRANCH_ALPHABET_RU[min(len(rows), len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)]


def _internal_response_path(branch_label: str, response_number: int) -> str:
    label = str(branch_label or "А").strip().upper()[:4] or "А"
    idx = max(0, int(response_number or 0) - 1)
    mark = _INTERNAL_BRANCH_ALPHABET_RU[min(idx, len(_INTERNAL_BRANCH_ALPHABET_RU) - 1)]
    return f"{label}.{mark}"

HOT_DIALOG_LIMIT = 30  # canonical active dialogue hot window
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
SEMANTIC_MODEL_NAME = "rapidfuzz-arc-light"  # compatibility metadata; runtime is the shared lightweight interpretation engine

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

def _dict(value: Any):
    """Return a mapping safely; used by canonical scene-memory builders."""
    return value if isinstance(value, dict) else {}


def safe_trim_text(text, limit=120):
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit]


def safe_list(value):
    return value if isinstance(value, list) else []


# ---------------------------------------------------------------------------
# POST-PROVIDER DIALOGUE MEMORY
# Pair memory is persisted directly from USER↔APRIL turns. Entity extraction is removed.

def _derive_post_provider_memory_semantics(
    current_request,
    answer,
    provisional=None,
    previous_anchor=None,
    relation="NEW",
    render_types=None,
):
    """Build canonical semantic metadata for one authenticated USER↔APRIL pair.

    The stored pair always keeps the exact USER request and APRIL answer. Optional
    interpretation metadata (resolved request/topic/reference/context) is stored
    beside them so a later turn can understand pronouns without inventing text.
    """
    provisional = provisional if isinstance(provisional, dict) else {}
    relation = str(relation or "NEW").strip().upper()
    if relation == "RECALL" or relation not in {"CONTINUE", "NEW"}:
        relation = "NEW"
    request_text = str(current_request or "").strip()[:1200]
    answer_text = str(answer or "").strip()[:4000]
    rtypes = [str(x or "").strip().lower() for x in (render_types or []) if str(x or "").strip()]
    subtopic = next((label for label in ("image","gallery","formula","diagram","graph","table","code","link","audio","video","file") if label in rtypes), "")
    topic = str(
        provisional.get("canonical_topic")
        or provisional.get("active_topic")
        or provisional.get("topic")
        or ""
    ).strip()[:220]
    if not topic:
        topic = request_text[:220]
    active_entity = str(
        provisional.get("resolved_reference_entity")
        or provisional.get("active_entity")
        or provisional.get("resolved_entity")
        or ""
    ).strip()[:220]
    resolved_request = str(provisional.get("resolved_request") or request_text).strip()[:1200]
    context_mode = str(provisional.get("context_mode") or ("LIVE_CONTINUATION" if relation == "CONTINUE" else "NEW_TOPIC_ISOLATED"))
    return {
        "version": "post_provider_pair_memory_v4_live_context",
        "source_of_truth": "USER_REQUEST_PLUS_PROVIDER_RESPONSE",
        "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        "topic": topic,
        "canonical_topic": topic,
        "subtopic": subtopic,
        "entities": [],
        "active_entity": active_entity,
        "resolved_reference_entity": active_entity,
        "resolved_request": resolved_request,
        "subject_source": "INTERPRETATION_PAIR_CONTEXT",
        "subject_confidence": 0.98 if active_entity else 0.55 if topic else 0.0,
        "reference_policy": "AUTHENTICATED_12H_PAIR_CONTEXT",
        "relation": relation,
        "context_mode": context_mode,
        "context_dependency": (
            "continuation" if relation == "CONTINUE"
            else "new_with_context" if context_mode in {"NEW_TOPIC_WITH_CONTEXT", "HISTORY_LOOKUP"}
            else "independent"
        ),
        "user_request": request_text,
        "april_answer": answer_text,
        "created_at": time.time(),
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
    }

def compact_dialog_message(role, content):
    now = time.time()
    return {
        "role": role,
        "content": safe_trim_text(content, 320),
        "created_at": now,
        "expires_at": now + USER_CONTENT_RETENTION_SECONDS,
    }


def get_dialog_limit(user_id, plan=None):
    """One active Free hot-dialog window; future plans remain reserved."""
    return HOT_DIALOG_LIMIT


def utc_day_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def utc_window_start(timestamp=None):
    """Compatibility helper for legacy visual records only. New dialogue memory uses a per-user anchor."""
    dt = datetime.fromtimestamp(
        float(timestamp if timestamp is not None else time.time()),
        tz=timezone.utc,
    )
    hour = 0 if dt.hour < 12 else 12
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0)


def utc_window_key(timestamp=None):
    return utc_window_start(timestamp).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "dialog_pairs": [],
        "created_at": time.time(),
    }


def build_memory_timeline():
    return {"day_0": build_memory_day()}


def build_default_active_dialogue_sequence():
    return {
        "version": "april_dialogue_sequence_v4_12h_dynamic_branches",
        # sequence_id identifies the authenticated conversation sequence.
        # task_id identifies the currently active task inside that sequence.
        "sequence_id": None, "branch_id": None, "task_id": None,
        "topic": None, "status": "inactive",
        "user_id": None, "conversation_id": None, "turn_count": 0,
        "response_count": 0, "task_response_count": 0,
        "started_at": None, "last_turn_at": None,
        "last_user_request": "", "last_april_answer": "",
        "last_task_result": {}, "last_answer_basis": {},
        "dialogue_rules": {},
        "task_registry": {},
        "last_visual_attachment": {}, "last_visual_scene_id": "",
        "last_visual_turn_index": 0, "visual_turn_count": 0, "relation": "NEW",
    }


def build_default_active_dialogue_context():
    return {
        "version": "active_dialogue_context_v3_12h_task_scoped",
        "scope": {"user_id": None, "conversation_id": None},
        "sequence_id": None,
        "task_id": None,
        "objective": "",
        "task": {},
        "intent": "",
        "goal": "",
        "topic": "",
        "active_entity": "",
        "dialogue_rules": {},
        "response_sequence": {},
        "completed_results": [],
        "last_completed_result": {},
        "updated_at": None,
    }


def build_default_state():
    now = time.time()
    return {
        "dialog": [],
        "memory_summary": "",
        "memory_summary_meta": {
            "created_at": None,
            "expires_after_hours": DIALOGUE_WINDOW_HOURS,
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
        "dialogue_obligations": [],
        "dialogue_development": {},
        "result_chain": [],
        "turn_progression": [],
        "dialogue_result_event": {},
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
            "last_user_message_at": None,
            "last_bot_message": None,
            "last_bot_message_at": None,
            "last_entity": None,
            "last_intent": None,
        },
        "current_object": None,
        "current_topic": None,
        "active_entity": None,
        "user_profile": {
            "name": "",
            "name_source": "",
            "updated_at": None,
        },
        # Canonical interactive task owner, separate from generic topic/entity state.
        "interactive_task_state": {},
        "open_task": {},
        "active_task": {},
        "continuity_resolution": {
            "version": "continuity_resolution_v1",
            "final_relation": "NEW",
            "live_supported": False,
            "recovery_attempted": False,
            "escalation_result": "",
            "historical_memory_policy": "BLOCKED_UNTIL_LIVE_MISS",
            "selected_sequence_id": "",
            "updated_at": None,
        },
        "machine_runtime": True,
        "renderer_safe": True,
        "continuity_alive": True,
        "web_safe": True,
        "last_user_turn": "",
        "last_user_turn_at": None,
        "last_april_turn": "",
        "last_april_turn_at": None,
        "dialog_state": {},
        "dialogue_resolution": {
            "relation": "NEW",
            "selected_memory_index": -1,
            "selected_memory_operand": {},
            "selected_memory_record": {},
            "memory_slider": {},
            "previous_result": {},
            "development_state": {},
            "source_scene_id": "",
            "resolved_request": "",
            "confidence": 0.0,
            "authoritative": False,
            "updated_at": None,
        },
        "active_dialogue_sequence": build_default_active_dialogue_sequence(),
        "active_dialogue_context": build_default_active_dialogue_context(),
        "dialogue_task_registry": {},
        "active_dialogue_task_id": "",
        "dialogue_sequence_version": "APRIL-DIALOGUE-SEQUENCE-12H-V3-TASK-SCOPED",
        "dialogue_branch_index": {
            "version": "dialogue_branch_index_v1_user_bound",
            "active_sequence_id": "",
            "target_sequence_id": "",
            "target_branch_id": "",
            "resolution_mode": "NO_BRANCH_RESOLUTION",
            "branches": [],
        },
        "active_dialogue_branch_id": "",
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
            "anchor_mode": "USER_DIALOGUE_START_12H_V1",
            "session_start_utc": now,
            "window_key": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window_start_utc": now,
            "seed_cutoff_utc": now - DIALOGUE_SEED_SECONDS,
            "last_rollover": now,
        },
        "memory_version": "QUANTUM-MEMORY-12H-V2",
        "active_scene_contract": {},
        "current_scene_request": "",
        "dialogue_memory_anchor": {},
        "canonical_dialogue_turn": {},
        "visual_summary": {},
        "semantic_scene_state": {},
        "last_successful_visual_scene": None,
        "last_successful_visual_scene_id": None,
        "last_successful_visual_scene_turn": None,
        "visual_memory_integrity": {
            "active_artifact_source": "last_successful_visual_scene",
            "preserve_on_nonvisual_turn": True,
        },
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

    VERSION = "QUANTUM-MEMORY-12H-V2"
    MATRIX_VERSION = "QUANTUM-MEMORY-MATRIX-12H-V2"

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
        if not isinstance(state_obj.get("dialogue_task_registry"), dict):
            state_obj["dialogue_task_registry"] = {}
        if not isinstance(state_obj.get("active_dialogue_task_id"), str):
            state_obj["active_dialogue_task_id"] = str(state_obj.get("active_dialogue_task_id") or "")

        self.normalize_timeline(state_obj)
        if not isinstance(state_obj.get("memory_summary_meta"), dict):
            state_obj["memory_summary_meta"] = {
                "created_at": None,
                "expires_after_hours": DIALOGUE_WINDOW_HOURS,
                "memory_kind": "summary",
            }
        if not isinstance(state_obj.get("memory_matrix"), dict):
            state_obj["memory_matrix"] = {}
        if not isinstance(state_obj.get("dialogue_resolution"), dict):
            state_obj["dialogue_resolution"] = {
                "relation": "NEW",
                "selected_memory_index": -1,
                "selected_memory_operand": {},
                "selected_memory_record": {},
                "previous_result": {},
                "development_state": {},
                "source_scene_id": "",
                "resolved_request": "",
                "confidence": 0.0,
                "authoritative": False,
                "updated_at": None,
            }
        self._ensure_active_dialogue_sequence(state_obj)
        return state_obj

    def normalize_timeline(self, state_obj):
        timeline = state_obj.get("memory_timeline")
        if not isinstance(timeline, dict):
            timeline = {}

        canonical = {}
        key = "day_0"
        day = timeline.get(key)
        canonical[key] = day if isinstance(day, dict) else build_memory_day()
        for slot in TOPIC_CLASSES:
            if not isinstance(canonical[key].get(slot), list):
                canonical[key][slot] = []
        for field in ("visual_scenes", "topics", "objects", "intent_signals", "dialog_pairs"):
            if not isinstance(canonical[key].get(field), list):
                canonical[key][field] = []

        state_obj["memory_timeline"] = canonical
        return canonical

    # ---------- rolling 12-hour UTC lifecycle ----------

    @staticmethod
    def _record_timestamp(record):
        if not isinstance(record, dict):
            return 0.0
        for key in (
            "created_at", "created_at_utc", "timestamp", "archived_at", "updated_at",
            "turn_timestamp", "task_definition_at", "expires_at", "last_turn_at",
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
    def _memory_age_hours(timestamp, now=None):
        try:
            created = float(timestamp or 0.0)
        except (TypeError, ValueError):
            return None
        if created <= 0.0:
            return None
        current = float(now if now is not None else time.time())
        return max(0.0, (current - created) / 3600.0)

    def _purge_sequence(self, value, *, now=None):
        if not isinstance(value, list):
            return value, 0
        kept, removed = [], 0
        for item in value:
            ts = self._record_timestamp(item)
            if ts <= 0.0 or self._is_expired(ts, now=now):
                removed += 1
                continue
            kept.append(item)
        return kept, removed

    @staticmethod
    def _in_interval(record, start_ts, end_ts):
        ts = QuantumMemoryEngine._record_timestamp(record)
        return bool(ts and float(start_ts) <= ts < float(end_ts))

    def _seed_container(self, container, seed_start, seed_end):
        if not isinstance(container, dict):
            return build_memory_day()
        result = build_memory_day()
        for field in tuple(TOPIC_CLASSES) + ("visual_scenes", "topics", "objects", "intent_signals", "dialog_pairs"):
            values = container.get(field) if isinstance(container.get(field), list) else []
            result[field] = [deepcopy(x) for x in values if self._in_interval(x, seed_start, seed_end)]
        return result

    def _clear_dialogue_runtime_except_seed(self, state_obj, seed_start, seed_end):
        """Keep only the last pre-boundary hour of dialogue state."""
        timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
        source_day = timeline.get("day_0") if isinstance(timeline.get("day_0"), dict) else {}
        hot_day = self._seed_container(source_day, seed_start, seed_end)
        # At the 12-hour boundary retain only the immediately preceding hour as
        # continuity seed. The fresh window then grows again with new turns.
        hot_day["dialog_pairs"] = [
            deepcopy(x) for x in (source_day.get("dialog_pairs") or [])
            if self._in_interval(x, seed_start, seed_end)
        ][-SESSION_MEMORY_LIMIT:]
        state_obj["memory_timeline"] = {"day_0": hot_day}

        def keep_record(record):
            return isinstance(record, dict) and self._in_interval(record, seed_start, seed_end)

        for key in ("result_chain", "turn_progression", "visual_scene_history", "visual_topic_history", "visual_topic_registry",
                    "task_context_storage", "continuity_context_storage", "memory_anchor_storage", "internal_dialog_events"):
            values = state_obj.get(key)
            if isinstance(values, list):
                state_obj[key] = [deepcopy(x) for x in values if keep_record(x)][-HOT_DIALOG_LIMIT:]

        # Keep only USER/APRIL pairs in the retained seed hour.
        dialog = state_obj.get("dialog") if isinstance(state_obj.get("dialog"), list) else []
        state_obj["dialog"] = [deepcopy(x) for x in dialog if keep_record(x)][-HOT_DIALOG_LIMIT:]

        # Task state is durable for the full 12-hour authenticated window. The
        # one-hour seed is only the HOT conversational cache and must never delete
        # an unfinished task that may be recalled later in the same 12h window.
        def ttl_fresh(key, timestamp_keys=("updated_at", "last_turn_at", "created_at")):
            value = state_obj.get(key)
            if not isinstance(value, dict) or not value:
                return False
            ts = self._record_timestamp(value)
            if not ts:
                for tk in timestamp_keys:
                    try:
                        ts = float(value.get(tk) or 0.0)
                    except Exception:
                        ts = 0.0
                    if ts:
                        break
            return bool(ts and not self._is_expired(ts))

        now = time.time()
        registry = state_obj.get("dialogue_task_registry") if isinstance(state_obj.get("dialogue_task_registry"), dict) else {}
        cleaned_registry = {}
        for task_id, task in registry.items():
            if not isinstance(task, dict):
                continue
            task_copy = deepcopy(task)
            has_seed_history = False
            for history_key in ("qa_history", "turns", "result_history", "completed_results"):
                values = task_copy.get(history_key)
                if not isinstance(values, list):
                    continue
                kept_values = [deepcopy(x) for x in values if self._in_interval(x, seed_start, seed_end)]
                has_seed_history = has_seed_history or bool(kept_values)
                task_copy[history_key] = kept_values[-HOT_DIALOG_LIMIT:]
            if has_seed_history or self._in_interval(task_copy, seed_start, seed_end):
                cleaned_registry[str(task_id)] = task_copy
        state_obj["dialogue_task_registry"] = cleaned_registry

        seq = state_obj.get("active_dialogue_sequence")
        if isinstance(seq, dict) and seq:
            seq = deepcopy(seq)
            # A sequence may be older than one 12h cycle while still having a
            # valid one-hour continuity seed. Use the latest activity timestamp
            # for the rollover decision; the sequence start remains only the
            # authenticated cycle anchor.
            try:
                seq_ts = float(
                    seq.get("last_turn_at")
                    or seq.get("updated_at")
                    or seq.get("last_user_turn_at")
                    or seq.get("last_april_turn_at")
                    or seq.get("created_at")
                    or 0.0
                )
            except (TypeError, ValueError):
                seq_ts = 0.0
            if seq_ts and not self._is_expired(seq_ts, now=now):
                seq_registry = {
                    str(k): deepcopy(v) for k, v in (seq.get("task_registry") or {}).items()
                    if isinstance(v, dict) and (not self._record_timestamp(v) or not self._is_expired(self._record_timestamp(v), now=now))
                }
                seq_registry.update(cleaned_registry)
                seq["task_registry"] = seq_registry
                task_id = str(seq.get("task_id") or state_obj.get("active_dialogue_task_id") or "")
                if task_id and isinstance(seq_registry.get(task_id), dict):
                    active_task = deepcopy(seq_registry[task_id])
                    seq["active_task"] = active_task
                    seq["interactive_task_state"] = deepcopy(active_task)
                    seq["open_task"] = deepcopy(active_task)
                    seq["task_state"] = deepcopy(active_task)
                    seq["dialogue_rules"] = deepcopy(active_task.get("dialogue_rules") or seq.get("dialogue_rules") or {})
                    state_obj["active_dialogue_task_id"] = task_id
                state_obj["active_dialogue_sequence"] = seq
            else:
                state_obj["active_dialogue_sequence"] = build_default_active_dialogue_sequence()
                state_obj["active_dialogue_task_id"] = ""

        active_ctx = state_obj.get("active_dialogue_context") if isinstance(state_obj.get("active_dialogue_context"), dict) else {}
        if active_ctx:
            ctx_ts = self._record_timestamp(active_ctx)
            active_task_id = str(active_ctx.get("task_id") or state_obj.get("active_dialogue_task_id") or "")
            durable_task = cleaned_registry.get(active_task_id) if active_task_id else None
            if durable_task:
                active_ctx["task_id"] = active_task_id
                active_ctx["task"] = deepcopy(durable_task)
                active_ctx["sequence_id"] = str(durable_task.get("sequence_id") or active_ctx.get("sequence_id") or "")
                active_ctx["objective"] = str(durable_task.get("objective") or active_ctx.get("objective") or "")
                active_ctx["topic"] = str(durable_task.get("topic") or active_ctx.get("topic") or "")
                active_ctx["goal"] = str(durable_task.get("goal") or active_ctx.get("goal") or "")
                active_ctx["active_entity"] = str(durable_task.get("entity") or active_ctx.get("active_entity") or "")
                active_ctx["dialogue_rules"] = deepcopy(durable_task.get("dialogue_rules") or active_ctx.get("dialogue_rules") or {})
                active_ctx["response_sequence"] = {
                    "sequence_turn_index": int((state_obj.get("active_dialogue_sequence") or {}).get("turn_count") or 0),
                    "task_response_number": int(durable_task.get("response_count") or 0),
                    "next_task_response_number": int(durable_task.get("response_count") or 0) + 1,
                    "branch_label": str(durable_task.get("branch_label") or _internal_branch_label(cleaned_registry, active_task_id))[:4],
                    "internal_response_path": str(durable_task.get("next_internal_response_path") or ""),
                }
                active_ctx["last_completed_result"] = deepcopy(durable_task.get("last_result") or {})
                active_ctx["completed_results"] = list(durable_task.get("result_history") or [])[-HOT_DIALOG_LIMIT:]
                active_ctx["updated_at"] = ctx_ts or now
                state_obj["active_dialogue_context"] = active_ctx
            elif not ctx_ts or self._is_expired(ctx_ts, now=now):
                state_obj["active_dialogue_context"] = build_default_active_dialogue_context()

        # Canonical dialogue anchors follow the same seed lifecycle.
        for key in ("dialogue_memory_anchor", "canonical_dialogue_turn"):
            value = state_obj.get(key)
            if not (isinstance(value, dict) and self._in_interval(value, seed_start, seed_end)):
                state_obj[key] = {}

        # Top-level task mirrors survive only when their task survived the seed.
        for key in ("interactive_task_state", "open_task", "active_task", "april_active_task"):
            value = state_obj.get(key)
            if not isinstance(value, dict) or not value:
                continue
            task_id = str(value.get("task_id") or "")
            if task_id and task_id in cleaned_registry:
                state_obj[key] = deepcopy(cleaned_registry[task_id])
            elif not ttl_fresh(key):
                state_obj[key] = {}

        # Rebuild branch index from all unexpired task states in this authenticated
        # sequence. No old task is allowed to leak from another sequence/user.
        active_seq = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
        seq_id = str(active_seq.get("sequence_id") or "")
        branches = []
        for task_id, task in cleaned_registry.items():
            if str(task.get("sequence_id") or seq_id) != seq_id:
                continue
            branches.append({
                "branch_id": f"{seq_id}:{task_id}",
                "sequence_id": seq_id,
                "task_id": task_id,
                "topic": task.get("topic"),
                "canonical_entity": task.get("entity") or task.get("active_entity") or "",
                "goal": task.get("goal") or "answer",
                "turn_count": task.get("response_count") or task.get("turn_count") or 0,
                "started_at": task.get("created_at") or task.get("started_at"),
                "last_turn_at": task.get("last_turn_at") or task.get("updated_at"),
                "last_user_request": task.get("last_user_request") or "",
                "last_april_answer": task.get("last_april_answer") or task.get("last_answer") or "",
                "last_result": deepcopy(task.get("last_result") or {}),
                "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
                "dialogue_rules": deepcopy(task.get("dialogue_rules") or active_seq.get("dialogue_rules") or {}),
                "branch_label": str(task.get("branch_label") or _internal_branch_label(cleaned_registry, task_id))[:4],
                "branch_type": str(task.get("branch_type") or "topic")[:40],
                "linked_branch_ids": deepcopy(task.get("linked_branch_ids") or [])[:8],
                "linked_branches": deepcopy(task.get("linked_branches") or [])[:4],
                "internal_only": True,
                "active_task": deepcopy(task),
                "active": task_id == str(active_seq.get("task_id") or state_obj.get("active_dialogue_task_id") or ""),
            })
        state_obj["dialogue_branch_index"] = {
            "version": "dialogue_branch_index_v4_dynamic_branches",
            "active_sequence_id": seq_id,
            "target_sequence_id": seq_id,
            "target_task_id": str(active_seq.get("task_id") or state_obj.get("active_dialogue_task_id") or ""),
            "target_branch_id": f"{seq_id}:{active_seq.get('task_id')}" if active_seq.get("task_id") else seq_id,
            "resolution_mode": "DURABLE_12H_TASKS" if seq_id else "NO_BRANCH_RESOLUTION",
            "branches": branches[-32:],
        }
        state_obj["active_dialogue_branch_id"] = str(
            state_obj["dialogue_branch_index"].get("target_branch_id") or ""
        )

        # Visual hot pointer is also bounded by the seed hour; it does not erase user/profile data.
        hot = state_obj.get("last_successful_visual_scene")
        hot_ts = self._record_timestamp(hot)
        if not (isinstance(hot, dict) and seed_start <= hot_ts < seed_end):
            state_obj["last_successful_visual_scene"] = None
            state_obj["last_successful_visual_scene_id"] = None
            state_obj["last_successful_visual_scene_turn"] = None
            state_obj["active_visual_scene"] = None
            state_obj["current_visual_scene"] = None
            state_obj["active_visual_scene_turn"] = None
            state_obj["stored_visual_scene_turn"] = None
            state_obj["active_visual_topic"] = None

        # Generic current-message pointers follow the same seed rule.
        for value_key, stamp_key in (("last_user_turn", "last_user_turn_at"), ("last_april_turn", "last_april_turn_at"), ("current_scene_request", "current_scene_request_at")):
            try:
                ts = float(state_obj.get(stamp_key) or 0.0)
            except Exception:
                ts = 0.0
            if not (ts and seed_start <= ts < seed_end):
                state_obj[value_key] = ""
                state_obj[stamp_key] = None

    def _cleanup_top_level_memory(self, state_obj, now=None):
        now = float(now if now is not None else time.time())
        removed = 0
        by_field = {}
        # Never touch user/profile/auth/subscription records here. This is dialogue/derived memory only.
        for field in (
            "visual_scene_history", "visual_topic_history", "visual_topic_registry",
            "task_context_storage", "continuity_context_storage", "memory_anchor_storage",
            "scene_history", "internal_dialog_events", "result_chain", "turn_progression",
        ):
            cleaned, count = self._purge_sequence(state_obj.get(field), now=now)
            if isinstance(state_obj.get(field), list):
                state_obj[field] = cleaned
            if count:
                by_field[field] = count
                removed += count

        # Apply the same TTL to the canonical day_0 bucket even when we are
        # inside the current per-user 12-hour window. This also removes legacy
        # records that may have survived in day_0 after migration.
        timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
        day0 = timeline.get("day_0") if isinstance(timeline.get("day_0"), dict) else {}
        if day0:
            for field in tuple(TOPIC_CLASSES) + ("visual_scenes", "topics", "objects", "intent_signals", "dialog_pairs"):
                values = day0.get(field) if isinstance(day0.get(field), list) else []
                cleaned, count = self._purge_sequence(values, now=now)
                day0[field] = cleaned
                if count:
                    by_field[f"memory_timeline.day_0.{field}"] = count
                    removed += count
            timeline["day_0"] = day0
            state_obj["memory_timeline"] = timeline

        active_ctx = state_obj.get("active_dialogue_context") if isinstance(state_obj.get("active_dialogue_context"), dict) else None
        if isinstance(active_ctx, dict):
            results = active_ctx.get("completed_results") if isinstance(active_ctx.get("completed_results"), list) else []
            kept_results = [x for x in results if isinstance(x, dict) and self._record_timestamp(x) > 0.0 and not self._is_expired(self._record_timestamp(x), now=now)]
            active_ctx["completed_results"] = kept_results[-HOT_DIALOG_LIMIT:]
            last = active_ctx.get("last_completed_result") if isinstance(active_ctx.get("last_completed_result"), dict) else {}
            if last:
                last_ts = self._record_timestamp(last)
                if not last_ts or self._is_expired(last_ts, now=now):
                    active_ctx["last_completed_result"] = {}
                    active_ctx["objective"] = ""
                    active_ctx["task"] = {}
                    active_ctx["intent"] = ""
                    active_ctx["goal"] = ""
                    active_ctx["topic"] = ""
                    active_ctx["active_entity"] = ""
                    active_ctx["sequence_id"] = None
                    active_ctx["updated_at"] = None
            state_obj["active_dialogue_context"] = active_ctx

        meta = state_obj.get("memory_summary_meta")
        if not isinstance(meta, dict):
            meta = {}
            state_obj["memory_summary_meta"] = meta
        summary_ts = self._record_timestamp(meta)
        if state_obj.get("memory_summary") and (not summary_ts or self._is_expired(summary_ts, now=now)):
            state_obj["memory_summary"] = ""
            state_obj["memory_summary_meta"] = {
                "created_at": None,
                "expires_after_hours": DIALOGUE_WINDOW_HOURS,
                "memory_kind": "rolling_dialogue_summary",
            }
            removed += 1
            by_field["memory_summary"] = 1

        state_obj["memory_cleanup"] = {
            "last_cleanup_at": now,
            "last_cleanup_utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "removed_count": removed,
            "removed_by_field": by_field,
            "window": "12h_rolling",
            "seed_hours": DIALOGUE_SEED_HOURS,
            "ttl_seconds": MEMORY_TTL_SECONDS,
        }
        return removed

    def rollover(self, state_obj):
        # `ensure()` may reconstruct legacy active dialogue/task state. Rollover
        # is the destructive boundary and must never revive a task immediately
        # before deciding what belongs to the new UTC window. Callers already
        # normalize the state before entering this method.
        if not isinstance(state_obj, dict):
            return False
        now = time.time()
        cycle = state_obj.get("memory_cycle") if isinstance(state_obj.get("memory_cycle"), dict) else {}
        anchor = float(cycle.get("session_start_utc") or cycle.get("window_start_utc") or now)
        if anchor > now:
            anchor = now
        elapsed = max(0.0, now - anchor)
        cycle_index = int(elapsed // DIALOGUE_WINDOW_SECONDS)
        current_start = anchor + cycle_index * DIALOGUE_WINDOW_SECONDS
        current_key = datetime.fromtimestamp(current_start, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        previous_key = cycle.get("window_key") or cycle.get("last_window_key")
        changed = bool(previous_key and previous_key != current_key)

        if changed:
            seed_start = current_start - DIALOGUE_SEED_SECONDS
            seed_end = current_start
            self._clear_dialogue_runtime_except_seed(state_obj, seed_start, seed_end)
            # Rebuild the live sequence/task mirrors from the retained one-hour
            # authenticated seed. This keeps dialogue continuation alive without
            # resurrecting any of the preceding 11 hours.
            self._ensure_active_dialogue_sequence(state_obj)

        state_obj["memory_cycle"] = {
            "anchor_mode": "USER_DIALOGUE_START_12H_V1",
            "session_start_utc": anchor,
            "window_key": current_key,
            "window_start_utc": current_start,
            "seed_cutoff_utc": current_start - DIALOGUE_SEED_SECONDS,
            "last_rollover": now,
        }
        self._cleanup_top_level_memory(state_obj, now=now)
        if changed:
            state_obj["memory_summary"] = ""
            state_obj["memory_summary_meta"] = {
                "created_at": None,
                "expires_after_hours": DIALOGUE_WINDOW_HOURS,
                "memory_kind": "summary",
            }
            safe_state_log(
                f"MEMORY_12H_ROLLOVER: utc_window={current_key}; retained_seed=1h;"
            )
        return changed

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
        """Migrate legacy visual hot pointers into live day_0 (12h) memory.

        Old deployments stored rendered tables/images as active_visual_scene without
        the canonical USER↔APRIL scene fields. The migrated record stays live only
        within the 12-hour memory window and can no longer remain the hot pointer.
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

        # Never re-stamp legacy content with `time.time()`. That turns an old
        # visual scene into a fresh 12-hour record. Only a record whose original
        # timestamp is already inside the authenticated current user window may
        # be migrated, and its original timestamp is preserved.
        now = time.time()
        scene_ts = self._record_timestamp(scene)
        cycle = state_obj.get("memory_cycle") if isinstance(state_obj.get("memory_cycle"), dict) else {}
        anchor = float(cycle.get("session_start_utc") or cycle.get("window_start_utc") or now)
        if anchor > now:
            anchor = now
        elapsed = max(0.0, now - anchor)
        cycle_index = int(elapsed // DIALOGUE_WINDOW_SECONDS)
        window_start = anchor + cycle_index * DIALOGUE_WINDOW_SECONDS
        if not scene_ts or scene_ts < window_start or scene_ts >= window_start + DIALOGUE_WINDOW_SECONDS or scene_ts > now:
            state_obj["active_visual_scene"] = None
            state_obj["current_visual_scene"] = None
            state_obj["active_visual_scene_turn"] = None
            state_obj["stored_visual_scene_turn"] = None
            state_obj["active_visual_topic"] = None
            return

        archived = deepcopy(scene)
        archived["memory_kind"] = "visual_dialogue_archive"
        archived["legacy_hot_pointer_migrated"] = True
        archived["user_id"] = user_id
        archived["conversation_id"] = str(
            state_obj.get("memory_scope", {}).get("conversation_id")
            or state_obj.get("conversation_id")
            or ""
        )
        archived["archived_at"] = scene_ts

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

    @staticmethod
    def _rebuild_task_registry_from_pairs(state_obj, sequence_id, user_id, conversation_id):
        """Migrate legacy sequence-only pairs into task-scoped records without losing data."""
        timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
        pairs = []
        for day in timeline.values():
            if not isinstance(day, dict):
                continue
            for item in day.get("dialog_pairs", []):
                if not isinstance(item, dict):
                    continue
                if str(item.get("sequence_id") or "") != str(sequence_id):
                    continue
                if user_id and str(item.get("user_id") or "") != str(user_id):
                    continue
                if conversation_id and str(item.get("conversation_id") or "") not in {"", str(conversation_id)}:
                    continue
                pairs.append(item)
        pairs.sort(key=lambda x: float(x.get("created_at") or x.get("timestamp") or 0.0))
        registry = {}
        current_task_id = ""
        previous_topic = ""
        for item in pairs:
            topic = str(item.get("sequence_topic") or item.get("topic") or item.get("canonical_topic") or "").strip()[:220]
            relation = str(item.get("dialogue_relation") or item.get("relation") or "CONTINUE").upper()
            explicit_tid = str(item.get("task_id") or "").strip()
            topic_changed = bool(topic and previous_topic and topic.lower() != previous_topic.lower())
            if explicit_tid:
                current_task_id = explicit_tid
            elif not current_task_id or relation == "NEW" or topic_changed:
                raw = f"{sequence_id}|{topic or 'task'}|{len(registry)}"
                current_task_id = "task-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
            task = registry.get(current_task_id)
            if not isinstance(task, dict):
                task = {
                    "task_id": current_task_id,
                    "sequence_id": str(sequence_id),
                    "topic": topic or None,
                    "canonical_topic": topic or None,
                    "goal": str(item.get("goal") or "answer"),
                    "status": "open",
                    "active": True,
                    "kind": "topic_task",
                    "objective": str(item.get("objective") or item.get("user_request") or ""),
                    "instruction": str(item.get("instruction") or item.get("user_request") or ""),
                    "created_at": float(item.get("created_at") or item.get("timestamp") or time.time()),
                    "response_count": 0,
                    "task_response_count": 0,
                    "qa_history": [],
                    "result_history": [],
                    "dialogue_rules": deepcopy(item.get("dialogue_rules") or {}),
                }
            result = {
                "task_id": current_task_id,
                "sequence_id": str(sequence_id),
                "sequence_turn_index": int(item.get("sequence_turn_index") or 0),
                "task_response_number": int(item.get("task_response_number") or (task.get("response_count") or 0) + 1),
                "user_request": str(item.get("user_request") or item.get("user_meaning") or "")[:1200],
                "april_answer": str(item.get("april_answer") or item.get("april_meaning") or item.get("answer") or "")[:2200],
                "summary": str(item.get("answer_summary") or item.get("april_answer") or "")[:900],
                "relation": relation,
                "topic": topic or task.get("topic"),
                "created_at": float(item.get("created_at") or item.get("timestamp") or time.time()),
            }
            task["qa_history"] = list(task.get("qa_history") or []) + [{
                "task_id": current_task_id,
                "sequence_id": str(sequence_id),
                "task_response_number": result["task_response_number"],
                "sequence_turn_index": result["sequence_turn_index"],
                "user": result["user_request"],
                "april": result["april_answer"],
                "kind": "turn",
                "relation": relation,
                "created_at": result["created_at"],
            }]
            task["qa_history"] = task["qa_history"][-HOT_DIALOG_LIMIT:]
            task["turns"] = deepcopy(task["qa_history"])
            task["result_history"] = list(task.get("result_history") or []) + [deepcopy(result)]
            task["result_history"] = task["result_history"][-HOT_DIALOG_LIMIT:]
            task["completed_results"] = deepcopy(task["result_history"])[-12:]
            task["response_count"] = max(int(task.get("response_count") or 0), result["task_response_number"])
            task["task_response_count"] = task["response_count"]
            task["last_result"] = deepcopy(result)
            task["last_user_request"] = result["user_request"]
            task["last_april_answer"] = result["april_answer"]
            task["last_answer"] = result["april_answer"]
            task["last_turn_at"] = result["created_at"]
            task["updated_at"] = result["created_at"]
            registry[current_task_id] = task
            previous_topic = topic or previous_topic
        return registry

    @staticmethod
    def _ensure_active_dialogue_sequence(state_obj):
        """Recover/normalize the authenticated user's active 12-hour vector."""
        if not isinstance(state_obj, dict):
            return {}

        scope = state_obj.get("memory_scope") if isinstance(state_obj.get("memory_scope"), dict) else {}
        user_id = str(scope.get("user_id") or state_obj.get("user_id") or "").strip()
        conversation_id = str(
            scope.get("conversation_id")
            or state_obj.get("conversation_id")
            or ""
        ).strip()

        current = state_obj.get("active_dialogue_sequence")
        if not isinstance(current, dict):
            current = {}

        sequence_id = str(current.get("sequence_id") or "").strip()
        current_user = str(current.get("user_id") or "").strip()
        current_conversation = str(current.get("conversation_id") or "").strip()

        try:
            current_last_turn = float(current.get("last_turn_at") or 0.0)
        except (TypeError, ValueError):
            current_last_turn = 0.0
        sequence_expired = bool(
            current_last_turn
            and (time.time() - current_last_turn) >= USER_CONTENT_RETENTION_SECONDS
        )

        if sequence_id and not sequence_expired and (
            (not current_user or current_user == user_id)
            and (not current_conversation or current_conversation == conversation_id)
        ):
            current.update({
                "version": "april_dialogue_sequence_v4_12h_dynamic_branches",
                "sequence_id": sequence_id,
                "user_id": user_id or current_user,
                "conversation_id": conversation_id or current_conversation,
                "status": "active",
                "relation": str(current.get("relation") or "CONTINUE").upper(),
            })
            registry = state_obj.get("dialogue_task_registry") if isinstance(state_obj.get("dialogue_task_registry"), dict) else {}
            if not registry or not any(isinstance(v, dict) and str(v.get("sequence_id") or sequence_id) == sequence_id for v in registry.values()):
                registry.update(QuantumMemoryEngine._rebuild_task_registry_from_pairs(state_obj, sequence_id, user_id, conversation_id))
            else:
                registry = {str(k): deepcopy(v) for k, v in registry.items() if isinstance(v, dict) and str(v.get("sequence_id") or sequence_id) == sequence_id}
            current["task_registry"] = registry
            active_tid = str(current.get("task_id") or state_obj.get("active_dialogue_task_id") or "").strip()
            if not active_tid:
                # Prefer the latest task observed in the durable registry.
                candidates = sorted(registry.items(), key=lambda kv: float(kv[1].get("updated_at") or kv[1].get("last_turn_at") or kv[1].get("created_at") or 0.0))
                if candidates:
                    active_tid = str(candidates[-1][0])
            if active_tid and isinstance(registry.get(active_tid), dict):
                current["task_id"] = active_tid
                current["active_task"] = deepcopy(registry[active_tid])
                current["interactive_task_state"] = deepcopy(registry[active_tid])
                current["open_task"] = deepcopy(registry[active_tid])
                current["task_state"] = deepcopy(registry[active_tid])
                current["task_response_count"] = int(registry[active_tid].get("response_count") or 0)
                current["response_count"] = int(current.get("turn_count") or 0)
                current["last_task_result"] = deepcopy(registry[active_tid].get("last_result") or {})
                current["last_answer_basis"] = deepcopy(registry[active_tid].get("last_answer_basis") or {})
                current["dialogue_rules"] = deepcopy(registry[active_tid].get("dialogue_rules") or current.get("dialogue_rules") or {})
                state_obj["dialogue_task_registry"] = deepcopy(registry)
                state_obj["active_dialogue_task_id"] = active_tid
            # Backfill visual continuity from the durable 12-hour turn archive
            # when an older persisted sequence predates the visual attachment fields.
            if not isinstance(current.get("last_visual_attachment"), dict) or not current.get("last_visual_attachment"):
                latest_visual_pair = None
                timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
                for day_index in range(MEMORY_SLOTS):
                    day = timeline.get(f"day_{day_index}")
                    if not isinstance(day, dict):
                        continue
                    for item in day.get("dialog_pairs", []):
                        if not isinstance(item, dict):
                            continue
                        if str(item.get("sequence_id") or "") != sequence_id:
                            continue
                        if str(item.get("user_id") or "") != user_id:
                            continue
                        attachment = item.get("visual_attachment")
                        if isinstance(attachment, dict) and attachment:
                            latest_visual_pair = item
                if latest_visual_pair:
                    current["last_visual_attachment"] = deepcopy(latest_visual_pair.get("visual_attachment") or {})
                    current["last_visual_scene_id"] = str(latest_visual_pair.get("visual_scene_id") or latest_visual_pair.get("scene_contract_id") or "")
                    current["last_visual_turn_index"] = int(latest_visual_pair.get("sequence_turn_index") or 0)
                    current["visual_turn_count"] = sum(
                        1 for day_index in range(MEMORY_SLOTS)
                        for item in ((timeline.get(f"day_{day_index}") or {}).get("dialog_pairs", []) if isinstance(timeline.get(f"day_{day_index}"), dict) else [])
                        if isinstance(item, dict)
                        and str(item.get("sequence_id") or "") == sequence_id
                        and isinstance(item.get("visual_attachment"), dict)
                        and item.get("visual_attachment")
                    )
            state_obj["active_dialogue_sequence"] = current
            return current

        # Restore from the newest authenticated dialog pair in the 12-hour window.
        pairs = []
        timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
        now = time.time()
        for day_index in range(MEMORY_SLOTS):
            day = timeline.get(f"day_{day_index}")
            if not isinstance(day, dict):
                continue
            for item in day.get("dialog_pairs", []):
                if not isinstance(item, dict):
                    continue
                if user_id and str(item.get("user_id") or "") != user_id:
                    continue
                if conversation_id and str(item.get("conversation_id") or "") not in {"", conversation_id}:
                    continue
                try:
                    created = float(item.get("created_at") or item.get("timestamp") or 0.0)
                except Exception:
                    created = 0.0
                if created and now - created >= USER_CONTENT_RETENTION_SECONDS:
                    continue
                if item.get("sequence_id"):
                    pairs.append(item)

        pairs.sort(key=lambda item: float(item.get("created_at") or item.get("timestamp") or 0.0))
        if pairs:
            last = pairs[-1]
            sequence_id = str(last.get("sequence_id") or "").strip()
            registry = state_obj.get("dialogue_task_registry") if isinstance(state_obj.get("dialogue_task_registry"), dict) else {}
            rebuilt = QuantumMemoryEngine._rebuild_task_registry_from_pairs(state_obj, sequence_id, user_id, conversation_id)
            if rebuilt:
                registry = {**{str(k): deepcopy(v) for k, v in registry.items() if isinstance(v, dict) and str(v.get("sequence_id") or sequence_id) == sequence_id}, **rebuilt}
            last_task_id = str(last.get("task_id") or "").strip()
            if not last_task_id and registry:
                candidates = sorted(registry.items(), key=lambda kv: float(kv[1].get("updated_at") or kv[1].get("created_at") or 0.0))
                last_task_id = str(candidates[-1][0])
            task = deepcopy(registry.get(last_task_id) or {})
            topic = str(task.get("topic") or last.get("topic") or last.get("canonical_topic") or "").strip()
            sequence_pairs = [p for p in pairs if str(p.get("sequence_id") or "") == sequence_id]
            turn_count = max([int(p.get("sequence_turn_index") or 0) for p in sequence_pairs] or [len(sequence_pairs)])
            restored = {
                **build_default_active_dialogue_sequence(),
                "version": "april_dialogue_sequence_v4_12h_dynamic_branches",
                "sequence_id": sequence_id,
                "branch_id": sequence_id,
                "task_id": last_task_id or None,
                "topic": topic or None,
                "status": "active",
                "user_id": user_id or str(last.get("user_id") or ""),
                "conversation_id": conversation_id or str(last.get("conversation_id") or ""),
                "turn_count": turn_count,
                "response_count": turn_count,
                "task_response_count": int(task.get("response_count") or 0),
                "started_at": sequence_pairs[0].get("created_at") if sequence_pairs else None,
                "last_turn_at": last.get("created_at") or last.get("timestamp"),
                "last_user_request": str(last.get("user_request") or last.get("user_meaning") or ""),
                "last_april_answer": str(last.get("april_answer") or last.get("april_meaning") or ""),
                "last_task_result": deepcopy(task.get("last_result") or {}),
                "last_answer_basis": deepcopy(task.get("last_answer_basis") or {}),
                "dialogue_rules": deepcopy(task.get("dialogue_rules") or last.get("dialogue_rules") or {}),
                "task_registry": deepcopy(registry),
                "active_task": deepcopy(task),
                "interactive_task_state": deepcopy(task),
                "open_task": deepcopy(task),
                "task_state": deepcopy(task),
                "last_visual_attachment": deepcopy(last.get("visual_attachment") or {}),
                "last_visual_scene_id": str(last.get("visual_scene_id") or last.get("scene_contract_id") or ""),
                "last_visual_turn_index": int(last.get("sequence_turn_index") or 0),
                "visual_turn_count": sum(1 for p in sequence_pairs if isinstance(p.get("visual_attachment"), dict) and p.get("visual_attachment")),
                "relation": str(last.get("dialogue_relation") or "CONTINUE").upper(),
                "restored": True,
            }
            state_obj["active_dialogue_sequence"] = restored
            state_obj["dialogue_task_registry"] = deepcopy(registry)
            state_obj["active_dialogue_task_id"] = last_task_id
            return restored

        # No pair means no live sequence. Do not manufacture one yet.
        empty = {
            "version": "april_dialogue_sequence_v1",
            "sequence_id": None,
            "topic": None,
            "status": "inactive",
            "user_id": user_id or None,
            "conversation_id": conversation_id or None,
            "turn_count": 0,
            "started_at": None,
            "last_turn_at": None,
            "last_user_request": "",
            "last_april_answer": "",
            "relation": "NEW",
        }
        state_obj["active_dialogue_sequence"] = empty
        return empty

    @staticmethod
    def _task_belongs_to_sequence(task, sequence, *, now=None):
        """Validate a task against the authenticated conversation sequence.

        Tasks are scoped by task_id; sequence_id alone identifies the parent
        conversation and therefore must never be used as the task identity.
        """
        if not isinstance(task, dict) or not task:
            return {}
        sequence = sequence if isinstance(sequence, dict) else {}
        seq_id = str(sequence.get("sequence_id") or "").strip()
        task_seq = str(task.get("sequence_id") or task.get("active_sequence_id") or "").strip()
        if seq_id and task_seq and task_seq != seq_id:
            return {}

        current = float(now if now is not None else time.time())
        task_ts = QuantumMemoryEngine._record_timestamp(task)
        if task_ts and QuantumMemoryEngine._is_expired(task_ts, now=current):
            return {}
        if not task_ts:
            seq_ts = 0.0
            try:
                seq_ts = float(sequence.get("last_turn_at") or 0.0)
            except (TypeError, ValueError):
                seq_ts = 0.0
            if not seq_ts or QuantumMemoryEngine._is_expired(seq_ts, now=current):
                return {}

        # Legacy records may not have active=True. A task is still valid when it
        # has a stable task_id and a status/result history.
        task_id = str(task.get("task_id") or "").strip()
        active_signal = bool(
            task.get("active")
            or task.get("status") in {"open", "active", "suspended", "completed", "paused"}
            or task_id
        )
        if not active_signal:
            return {}
        return deepcopy(task)

    @staticmethod
    def _advance_active_dialogue_sequence(
        state_obj, user_id, relation, current_request, answer,
        dialogue_vector=None, selected_operand=None, canonical_semantics=None
    ):
        """Advance one authenticated dialogue sequence without mixing tasks.

        NEW creates a *task*, not a second conversation sequence. CONTINUE keeps
        the active task. RECALL switches to a previously stored task in the same
        authenticated sequence. Every completed answer is committed as the next
        task result only after the Provider has produced the actual visible text.
        """
        if not isinstance(state_obj, dict):
            raise TypeError("state_obj must be dict")
        dv = dialogue_vector if isinstance(dialogue_vector, dict) else {}
        canonical_turn = state_obj.get("canonical_dialogue_turn") if isinstance(state_obj.get("canonical_dialogue_turn"), dict) else {}
        current_canonical = canonical_semantics if isinstance(canonical_semantics, dict) else {}
        previous_canonical = canonical_turn.get("memory_semantics") if isinstance(canonical_turn.get("memory_semantics"), dict) else canonical_turn
        canonical_semantics = current_canonical or previous_canonical
        relation = str(relation or "NEW").strip().upper()
        if relation == "RECALL" or relation not in {"NEW", "CONTINUE"}:
            relation = "NEW"
        selected_operand = selected_operand if isinstance(selected_operand, dict) else {}
        presentation_only = bool(dv.get("presentation_only"))

        scope = state_obj.get("memory_scope") if isinstance(state_obj.get("memory_scope"), dict) else {}
        conversation_id = str(scope.get("conversation_id") or state_obj.get("conversation_id") or "")
        user_key = str(user_id or scope.get("user_id") or state_obj.get("user_id") or "")
        now = time.time()

        current = deepcopy(state_obj.get("active_dialogue_sequence")) if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
        if not current:
            current = build_default_active_dialogue_sequence()

        current_id = str(current.get("sequence_id") or dv.get("sequence_id") or "").strip()
        if not current_id:
            raw = f"{user_key}|{conversation_id}|dialogue-sequence-v3|{int(now // DIALOGUE_WINDOW_SECONDS)}"
            current_id = "seq-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

        # One conversation sequence owns multiple task records.
        task_registry = state_obj.get("dialogue_task_registry")
        if not isinstance(task_registry, dict):
            task_registry = {}
        sequence_tasks = current.get("task_registry") if isinstance(current.get("task_registry"), dict) else {}
        # Merge the persisted top-level registry only for this authenticated sequence.
        for tid, tval in task_registry.items():
            if not isinstance(tval, dict):
                continue
            if str(tval.get("sequence_id") or current_id) != current_id:
                continue
            sequence_tasks[str(tid)] = deepcopy(tval)

        active_task_id = str(
            dv.get("task_id")
            or dv.get("active_task_id")
            or current.get("task_id")
            or state_obj.get("active_dialogue_task_id")
            or ""
        ).strip()
        target_task = {}

        if relation == "RECALL":
            target_task_id = str(
                dv.get("target_task_id")
                or selected_operand.get("task_id")
                or selected_operand.get("active_task", {}).get("task_id")
                or active_task_id
                or ""
            ).strip()
            if target_task_id and isinstance(sequence_tasks.get(target_task_id), dict):
                target_task = deepcopy(sequence_tasks[target_task_id])
            elif isinstance(selected_operand.get("active_task"), dict):
                target_task = deepcopy(selected_operand.get("active_task"))
                target_task_id = str(target_task.get("task_id") or target_task_id).strip()
            elif isinstance(selected_operand, dict) and selected_operand.get("task_id"):
                target_task = deepcopy(selected_operand)
                target_task_id = str(target_task.get("task_id") or target_task_id).strip()
            if not target_task_id:
                relation = "NEW"
            else:
                active_task_id = target_task_id

        if relation == "CONTINUE":
            if active_task_id and isinstance(sequence_tasks.get(active_task_id), dict):
                target_task = deepcopy(sequence_tasks[active_task_id])
            elif isinstance(current.get("active_task"), dict) and current.get("active_task"):
                target_task = deepcopy(current.get("active_task"))
                active_task_id = str(target_task.get("task_id") or active_task_id).strip()
            # If the interpreter supplied a task frame with the same sequence,
            # prefer it, but never clear a persisted task merely because the turn
            # itself is not a procedural action.
            supplied = dv.get("interactive_task_state") or dv.get("open_task") or dv.get("task_state")
            if isinstance(supplied, dict) and supplied:
                supplied_id = str(supplied.get("task_id") or active_task_id).strip()
                if not supplied_id or not active_task_id or supplied_id == active_task_id:
                    target_task = {**target_task, **deepcopy(supplied)}
                    active_task_id = str(target_task.get("task_id") or active_task_id).strip()
            # Canonical completed-turn identity outranks every pre-provider task mirror.
            if canonical_semantics:
                if canonical_semantics.get("topic"):
                    target_task["topic"] = str(canonical_semantics.get("topic"))[:220]
                    target_task["canonical_topic"] = target_task["topic"]
                if canonical_semantics.get("entities"):
                    target_task["entities"] = deepcopy(canonical_semantics.get("entities") or [])[:6]
                if canonical_semantics.get("active_entity"):
                    target_task["entity"] = str(canonical_semantics.get("active_entity"))[:220]
                    target_task["active_entity"] = target_task["entity"]
                if canonical_semantics.get("subtopic"):
                    target_task["subtopic"] = str(canonical_semantics.get("subtopic"))[:80]

        if relation == "NEW":
            # A NEW topic is a child task of the SAME authenticated 12h dialogue
            # sequence. Interpretation has already assigned the canonical task_id;
            # StateManager must persist that exact id instead of minting another one.
            seed_topic = str(
                dv.get("canonical_topic")
                or dv.get("active_topic")
                or dv.get("topic")
                or ""
            ).strip()[:220]
            interpreted_task_id = str(
                dv.get("task_id")
                or dv.get("target_task_id")
                or dv.get("active_task_id")
                or ""
            ).strip()
            if interpreted_task_id:
                active_task_id = interpreted_task_id
            else:
                raw = f"{user_key}|{conversation_id}|{current_id}|{seed_topic}|{now:.9f}"
                active_task_id = "task-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
            target_task = deepcopy(
                dv.get("interactive_task_state")
                or dv.get("open_task")
                or dv.get("task_state")
                or {}
            )
            target_task.setdefault("active", True)
            target_task.setdefault("status", "open")
            target_task.setdefault("phase", "active")
            target_task.setdefault("kind", "topic_task")
            target_task["task_id"] = active_task_id
            target_task["sequence_id"] = current_id
            target_task["topic"] = str(canonical_semantics.get("topic") or seed_topic or target_task.get("topic") or "")[:220] or None
            target_task["canonical_topic"] = target_task.get("topic")
            if canonical_semantics.get("entities"):
                target_task["entities"] = deepcopy(canonical_semantics.get("entities") or [])[:6]
            if canonical_semantics.get("active_entity"):
                target_task["entity"] = str(canonical_semantics.get("active_entity"))[:220]
                target_task["active_entity"] = target_task["entity"]
            if canonical_semantics.get("subtopic"):
                target_task["subtopic"] = str(canonical_semantics.get("subtopic"))[:80]
            target_task["created_at"] = target_task.get("created_at") or now
            target_task["task_revision"] = int(target_task.get("task_revision") or 0) + 1

        # Make sure a recalled/continued task has an id and belongs to this sequence.
        if target_task and not active_task_id:
            raw = f"{user_key}|{conversation_id}|{current_id}|{target_task.get('topic') or 'task'}|legacy"
            active_task_id = "task-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        if target_task:
            target_task["task_id"] = active_task_id
            target_task["sequence_id"] = current_id

        # Presentation rules belong to the dialogue sequence, never to task state.
        # Legacy task-local copies are ignored so they cannot drive visible numbering.
        rules = deepcopy(
            dv.get("dialogue_rules")
            or current.get("dialogue_rules")
            or {}
        )
        if rules.get("enabled") is False:
            rules = {}
        if target_task and "dialogue_rules" in target_task:
            target_task.pop("dialogue_rules", None)

        previous_task_result = deepcopy(target_task.get("last_result") or current.get("last_task_result") or {})
        previous_basis = deepcopy(target_task.get("last_answer_basis") or current.get("last_answer_basis") or {})
        task_response_count = int(target_task.get("response_count") or target_task.get("task_response_count") or 0)
        task_response_number = task_response_count + 1 if target_task else 0
        sequence_turn_index = int(current.get("turn_count") or current.get("response_count") or 0) + 1

        # Branch identity is semantic state. It never controls visible formatting.
        branch_label = str(target_task.get("branch_label") or dv.get("branch_label") or "").strip() if target_task else ""
        if target_task and not branch_label:
            branch_label = _internal_branch_label(sequence_tasks, active_task_id)
            target_task["branch_label"] = branch_label
        if target_task:
            target_task["internal_only"] = True
            target_task["internal_response_path"] = _internal_response_path(branch_label, task_response_number or 1)
            target_task["next_internal_response_path"] = _internal_response_path(branch_label, (task_response_number or 0) + 1)
            branch_type = str(target_task.get("branch_type") or dv.get("branch_type") or "topic")
            if branch_type:
                target_task["branch_type"] = branch_type
            links = target_task.get("linked_branch_ids") or dv.get("linked_branch_ids") or []
            if isinstance(links, list):
                target_task["linked_branch_ids"] = [str(x)[:120] for x in links if str(x).strip()][:8]
            linked = target_task.get("linked_branches") or dv.get("linked_branches") or []
            if isinstance(linked, list):
                target_task["linked_branches"] = deepcopy(linked)[:4]

        if target_task and not presentation_only:
            # Actual answer/result is the canonical state transition.
            # Presentation-only dialogue-rule turns intentionally do not mutate
            # task history or task-local counters.
            answer_text = str(answer or "").strip()[:2200]
            request_text = str(current_request or "").strip()[:1200]
            result_record = {
                "task_id": active_task_id,
                "sequence_id": current_id,
                "task_response_number": task_response_number,
                "sequence_turn_index": sequence_turn_index,
                "branch_label": branch_label,
                "internal_response_path": target_task.get("internal_response_path") if target_task else "",
                "branch_type": target_task.get("branch_type") if target_task else "topic",
                "linked_branch_ids": deepcopy(target_task.get("linked_branch_ids") or []) if target_task else [],
                "linked_branches": deepcopy(target_task.get("linked_branches") or []) if target_task else [],
                "user_request": request_text,
                "april_answer": answer_text,
                "summary": answer_text[:900],
                "relation": relation,
                "topic": target_task.get("topic"),
                "goal": target_task.get("goal") or dv.get("goal") or "answer",
                "operation": dv.get("operation") or "answer",
                "created_at": now,
                "answer_basis": {
                    "task_id": active_task_id,
                    "task_objective": target_task.get("objective") or "",
                    "current_request": request_text,
                    "previous_result": previous_task_result,
                    "relation": relation,
                    "next_logical_step": "continue_task",
                },
            }
            history = list(target_task.get("result_history") or target_task.get("completed_results") or [])
            history.append(deepcopy(result_record))
            target_task["result_history"] = history[-HOT_DIALOG_LIMIT:]
            target_task["completed_results"] = deepcopy(target_task["result_history"])[-12:]
            target_task["last_result"] = deepcopy(result_record)
            target_task["last_answer"] = answer_text
            target_task["last_april_answer"] = answer_text
            target_task["last_user_request"] = request_text
            target_task["last_turn_at"] = now
            target_task["updated_at"] = now
            target_task["response_count"] = task_response_number
            target_task["task_response_count"] = task_response_number
            target_task["answer_basis"] = deepcopy(result_record["answer_basis"])
            target_task["last_answer_basis"] = deepcopy(result_record["answer_basis"])
            target_task["turn_count"] = int(target_task.get("turn_count") or 0) + 1

            # Store actual USER↔APRIL pair in task history. No assistant_prompt placeholder.
            qa = list(target_task.get("qa_history") or target_task.get("turns") or [])
            qa.append({
                "task_id": active_task_id,
                "sequence_id": current_id,
                "task_response_number": task_response_number,
                "sequence_turn_index": sequence_turn_index,
                "branch_label": branch_label,
                "internal_response_path": target_task.get("internal_response_path") if target_task else "",
                "user": request_text,
                "april": answer_text,
                "kind": "turn",
                "relation": relation,
                "created_at": now,
            })
            target_task["qa_history"] = qa[-HOT_DIALOG_LIMIT:]
            target_task["turns"] = deepcopy(target_task["qa_history"])

            sequence_tasks[active_task_id] = deepcopy(target_task)
            task_registry[active_task_id] = deepcopy(target_task)

        current.update({
            "version": "april_dialogue_sequence_v4_12h_dynamic_branches",
            "sequence_id": current_id,
            "branch_id": current.get("branch_id") or current_id,
            "task_id": active_task_id or None,
            "topic": (str(canonical_semantics.get("topic"))[:220] if canonical_semantics.get("topic") else (target_task.get("topic") if target_task else (current.get("topic") or dv.get("canonical_topic") or None))),
            "entities": deepcopy(canonical_semantics.get("entities") or current.get("entities") or [])[:6],
            "status": "active",
            "user_id": user_key,
            "conversation_id": conversation_id,
            "turn_count": sequence_turn_index,
            "response_count": sequence_turn_index,
            "task_response_count": int(current.get("task_response_count") or 0) if presentation_only else task_response_number,
            "started_at": current.get("started_at") or now,
            "last_turn_at": now,
            "last_user_request": str(current_request or "").strip()[:1200],
            "last_april_answer": str(answer or "").strip()[:2200],
            "last_task_result": deepcopy(current.get("last_task_result") if presentation_only else (target_task.get("last_result") if target_task else previous_task_result)),
            "last_answer_basis": deepcopy(current.get("last_answer_basis") if presentation_only else (target_task.get("last_answer_basis") if target_task else previous_basis)),
            "dialogue_rules": deepcopy(rules),
            "task_registry": deepcopy(sequence_tasks),
            "relation": relation,
            "restored": False,
            "active_entity": str(canonical_semantics.get("active_entity") or dv.get("active_entity") or current.get("active_entity") or "")[:220],
            "branch_label": branch_label,
            "branch_type": str(dv.get("branch_type") or target_task.get("branch_type") or "topic") if target_task else str(dv.get("branch_type") or "topic"),
            "linked_branch_ids": deepcopy(target_task.get("linked_branch_ids") or dv.get("linked_branch_ids") or []) if target_task else deepcopy(dv.get("linked_branch_ids") or []),
            "linked_branches": deepcopy(target_task.get("linked_branches") or dv.get("linked_branches") or []) if target_task else deepcopy(dv.get("linked_branches") or []),
            "internal_response_path": target_task.get("internal_response_path") if target_task else "",
            "goal": str(dv.get("goal") or (target_task.get("goal") if target_task else current.get("goal") or "answer"))[:120],
            "active_task": deepcopy(target_task),
            "interactive_task_state": deepcopy(target_task),
            "open_task": deepcopy(target_task),
            "task_state": deepcopy(target_task),
        })

        state_obj["active_dialogue_sequence"] = deepcopy(current)
        state_obj["dialogue_task_registry"] = deepcopy(task_registry)
        state_obj["active_dialogue_task_id"] = active_task_id
        state_obj["active_dialogue_branch_id"] = (
            f"{current_id}:{active_task_id}" if active_task_id
            else str(current.get("branch_id") or current_id)
        )
        state_obj["interactive_task_state"] = deepcopy(target_task)
        state_obj["open_task"] = deepcopy(target_task)
        state_obj["active_task"] = deepcopy(target_task)

        # One branch entry per task; tasks share the conversation sequence_id.
        branches = [
            deepcopy(b) for b in ((state_obj.get("dialogue_branch_index") or {}).get("branches") or [])
            if isinstance(b, dict) and str(b.get("sequence_id") or "") == current_id
        ]
        for tid, task in sequence_tasks.items():
            if not isinstance(task, dict):
                continue
            branches = [b for b in branches if str(b.get("task_id") or "") != str(tid)]
            branches.append({
                "branch_id": f"{current_id}:{tid}",
                "sequence_id": current_id,
                "task_id": tid,
                "topic": task.get("topic"),
                "canonical_entity": task.get("active_entity") or task.get("entity") or "",
                "goal": task.get("goal") or "answer",
                "turn_count": task.get("response_count") or task.get("turn_count") or 0,
                "started_at": task.get("created_at") or task.get("started_at"),
                "last_turn_at": task.get("last_turn_at") or task.get("updated_at"),
                "last_user_request": task.get("last_user_request") or "",
                "last_april_answer": task.get("last_april_answer") or task.get("last_answer") or "",
                "last_result": deepcopy(task.get("last_result") or {}),
                "answer_basis": deepcopy(task.get("last_answer_basis") or task.get("answer_basis") or {}),
                "dialogue_rules": deepcopy(task.get("dialogue_rules") or rules),
                "branch_label": str(task.get("branch_label") or _internal_branch_label(sequence_tasks, str(tid)))[:4],
                "branch_type": str(task.get("branch_type") or "topic")[:40],
                "linked_branch_ids": deepcopy(task.get("linked_branch_ids") or [])[:8],
                "linked_branches": deepcopy(task.get("linked_branches") or [])[:4],
                "internal_only": True,
                "active_task": deepcopy(task),
                "active": str(tid) == active_task_id,
            })
        state_obj["dialogue_branch_index"] = {
            "version": "dialogue_branch_index_v4_dynamic_branches",
            "active_sequence_id": current_id,
            "target_sequence_id": current_id,
            "target_task_id": active_task_id,
            "target_branch_label": branch_label,
            "target_branch_id": f"{current_id}:{active_task_id}" if active_task_id else str(current.get("branch_id") or current_id),
            "resolution_mode": "RECALL_TASK" if relation == "RECALL" else "NEW_TASK" if relation == "NEW" else "ACTIVE_TASK",
            "branches": branches[-32:],
        }
        return current

    def ensure_runtime(self, state_obj):
        self.ensure(state_obj)
        # Normalize legacy hot visual pointers exactly once. Nothing is deleted;
        # the old scene is preserved in dynamic/12-hour memory.
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
            # and Memory. No second semantic engine instance is created here.
            from blocks.interpretation_layer import get_shared_semantic_encoder
            self._encoder = get_shared_semantic_encoder()
            self._encoder_ready = True
            safe_state_log("SEMANTIC MEMORY ENGINE LINKED: SHARED_ARC_LIGHT_INTERPRETATION")
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
        """Batch comparison through the one shared lightweight interpretation engine."""
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
        # The interpretation engine owns the similarity/cache. State Manager only
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

        for day_index in range(MEMORY_SLOTS):
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
        """Build one quantum-matrix evidence field over live day_0 (12h) memory."""
        self.ensure_runtime(state_obj)
        query = str(query or "").strip()
        now = time.time()
        records = list(self.iter_memory_records(state_obj))
        texts = [self._record_text(r) for r in records]
        semantic_map = self.semantic_scores(query, texts) if query else {}

        rows = []
        for record, text in zip(records, texts):
            ts = self._record_timestamp(record)
            age_hours = self._memory_age_hours(ts, now=now)
            base_age = age_hours if age_hours is not None else 0.0
            age_ratio = min(1.0, max(0.0, base_age / DIALOGUE_WINDOW_HOURS))
            semantic = float(semantic_map.get(text, 0.0)) if query and text else 0.0
            rows.append({
                "day_index": int(record.get("day_index", 0)),
                "memory_kind": record.get("memory_kind"),
                "age_hours": round(age_hours, 6) if age_hours is not None else None,
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
            "window": "12h_rolling",
            "expired_boundary": "next_authenticated_12h_boundary",
            "ttl_seconds": MEMORY_TTL_SECONDS,
            "query": query,
            "rows": rows[: max(1, int(limit))],
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }

    def query(self, state_obj, query, *, limit=8, retrieval_mode="semantic"):

        """
        Produce memory evidence. Stored visual scenes remain in the 12-hour
        memory, but the current active visual context is exposed only when its
        semantic relevance survives the current-turn measurement.
        """
        self.ensure_runtime(state_obj)
        query = str(query or "").strip()
        retrieval_mode = str(retrieval_mode or "semantic").strip().lower()
        continuity_policy = state_obj.get("continuity_resolution") if isinstance(state_obj.get("continuity_resolution"), dict) else {}
        active_sequence_id = str(
            (state_obj.get("active_dialogue_sequence") or {}).get("sequence_id")
            if isinstance(state_obj.get("active_dialogue_sequence"), dict) else ""
        ).strip()

        if not query:
            return {
                "engine": self.VERSION,
                "window_hours": DIALOGUE_WINDOW_HOURS,
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

        if retrieval_mode == "continuation_live":
            # Live continuation is sequence-local. It must never search another
            # 12-hour branch merely because the text is semantically similar.
            if not active_sequence_id:
                candidates = []
            else:
                candidates = [
                    record for record in candidates
                    if str(record.get("sequence_id") or "") == active_sequence_id
                ]

        elif retrieval_mode == "continuation_recovery":
            # 12-hour recovery is an explicit Interpretation decision, not a
            # default memory query. Without the gate, return no historical evidence.
            recovery_allowed = bool(
                continuity_policy.get("recovery_attempted")
                and str(continuity_policy.get("historical_memory_policy") or "") == "BLOCKED_OUTSIDE_LIVE_WINDOW"
            )
            if not recovery_allowed:
                candidates = []

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
            day_recency = max(0.0, 1.0 - (record.get("day_index", 0) / MEMORY_SLOTS))
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
            "window_hours": DIALOGUE_WINDOW_HOURS,
            "matches": matches,
            "memory_matrix": matrix,
            "memory_cleanup": deepcopy(state_obj.get("memory_cleanup", {})),
            "active_scene_similarity": round(active_scene_similarity, 6),
            "active_visual_scene": current_visual if active_visual_context_relevant else None,
            "stored_visual_scene": current_visual,
            "active_visual_context_relevant": active_visual_context_relevant,
            "active_topic_similarity": round(active_topic_score, 6),
            "retrieval_mode": retrieval_mode,
            "continuity_resolution": deepcopy(continuity_policy),
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
            # Never reuse the previous turn's continuation bit as a new-turn
            # decision.  Missing current-turn relation means independent until
            # the Interpretation Engine explicitly resolves continuity.
            continuation = False

        turn_relation = state_obj.get("_turn_dialogue_relation")
        turn_dependency = (
            turn_relation.get("context_dependency")
            if isinstance(turn_relation, dict)
            else ""
        )
        resolution = state_obj.get("dialogue_resolution")
        authoritative_relation = ""
        if isinstance(resolution, dict) and resolution.get("authoritative"):
            authoritative_relation = str(resolution.get("relation") or "").strip().upper()

        dependency = str(
            explicit_dependency
            if explicit_dependency is not None
            else turn_dependency
            or ("continuation" if authoritative_relation == "CONTINUE" else "recall" if authoritative_relation == "RECALL" else "independent" if authoritative_relation == "NEW" else "")
        ).strip().lower()

        if authoritative_relation == "RECALL":
            authoritative_relation = "NEW"
            if dependency == "recall":
                dependency = "history_lookup"
        if authoritative_relation == "CONTINUE":
            continuation = True

        return {
            "continuation": continuation,
            "context_dependency": dependency,
            "relation": authoritative_relation or ("CONTINUE" if continuation else "NEW"),
            "new_topic": authoritative_relation == "NEW",
            "recall": False,
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
        """Promote one confirmed visual scene to active and archive it in 12-hour memory.

        Active visual state is a one-scene hot pointer. The 12-hour timeline is
        the durable dynamic memory. A new scene replaces the hot pointer; older
        scenes remain retrievable only while they are inside day_0 (12h) and
        are deleted when they cross the next authenticated 12h cycle boundary.
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
            "dialogue_window_memory": deepcopy(state_obj["memory_timeline"]["day_0"]),
        }
        return state_obj["active_scene"]

    def build_executor_bridge(self, state_obj, query=""):
        self.ensure_runtime(state_obj)
        memory = self.query(state_obj, query) if query else {
            "engine": self.VERSION,
            "window_hours": DIALOGUE_WINDOW_HOURS,
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
            "dialogue_window": deepcopy(state_obj["memory_timeline"]["day_0"]),
            "active_dialogue_context": deepcopy(state_obj.get("active_dialogue_context", {})),
            "open_loops": deepcopy(state_obj.get("open_loops", [])),
            "quantum_memory": memory,
            "memory_version": self.VERSION,
            "window_hours": DIALOGUE_WINDOW_HOURS,
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }


QUANTUM_MEMORY_ENGINE = QuantumMemoryEngine()


# =====================================================
# CANONICAL STATE ACCESS
# =====================================================

state = {}
image_storage = {}



def _sanitize_persisted_dialog(state_obj):
    """Keep only genuine USER/APRIL dialogue in the semantic hot history.

    Internal visual/tool protocol messages are retained separately so legacy
    state cannot poison previous_user/previous_april or the dialogue vector.
    """
    dialog = safe_list(state_obj.get("dialog"))
    clean = []
    internal = safe_list(state_obj.get("internal_dialog_events"))
    for item in dialog:
        if _is_human_dialog_item(item):
            clean.append(item)
        else:
            internal.append({
                "role": str(item.get("role") or "") if isinstance(item, dict) else "",
                "content": safe_trim_text(
                    item.get("content", "") if isinstance(item, dict) else item,
                    1200,
                ),
                "metadata": deepcopy(item.get("metadata", {})) if isinstance(item, dict) else {},
                "created_at": time.time(),
            })
    state_obj["dialog"] = clean[-HOT_DIALOG_LIMIT:]
    state_obj["internal_dialog_events"] = internal[-VISUAL_HISTORY_LIMIT:]


def _repair_canonical_dialogue_memory(state_obj):
    """Repair legacy semantic fields from the existing USER↔APRIL archive.

    Old deployments stored correct USER/APRIL text together with incorrect topic/entity
    values such as a leading command word. The repair walks the live authenticated 12h
    archive chronologically and rebuilds semantic identity from each completed pair.
    """
    if not isinstance(state_obj, dict):
        return False
    timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
    day0 = timeline.get("day_0") if isinstance(timeline.get("day_0"), dict) else {}
    pairs = day0.get("dialog_pairs") if isinstance(day0.get("dialog_pairs"), list) else []
    if not pairs:
        return False
    user_id = str(state_obj.get("user_id") or (state_obj.get("memory_scope") or {}).get("user_id") or "").strip()
    conversation_id = str(state_obj.get("conversation_id") or (state_obj.get("memory_scope") or {}).get("conversation_id") or "").strip()
    now = time.time()
    ordered = sorted(
        [p for p in pairs if isinstance(p, dict)],
        key=lambda p: float(p.get("created_at") or p.get("timestamp") or 0.0),
    )
    previous_anchor = {}
    changed = False
    latest_pair = None
    for pair in ordered:
        if user_id and str(pair.get("user_id") or "") not in {"", user_id}:
            continue
        if conversation_id and str(pair.get("conversation_id") or "") not in {"", conversation_id}:
            continue
        try:
            ts = float(pair.get("created_at") or pair.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            ts = 0.0
        if ts and (now - ts) >= USER_CONTENT_RETENTION_SECONDS:
            continue
        req = str(pair.get("user_request") or pair.get("user_meaning") or "").strip()
        ans = str(pair.get("april_answer") or pair.get("april_meaning") or pair.get("answer") or "").strip()
        relation = str(pair.get("dialogue_relation") or pair.get("relation") or "NEW").upper()
        semantics = _derive_post_provider_memory_semantics(
            req,
            ans,
            provisional={},
            previous_anchor=previous_anchor,
            relation=relation,
            render_types=pair.get("render_block_types") or pair.get("presentation_types") or [],
        )
        for key, value in {
            "topic": semantics.get("topic") or "",
            "sequence_topic": semantics.get("topic") or "",
            "subtopic": semantics.get("subtopic") or "",
            "entities": deepcopy(semantics.get("entities") or []),
            "active_entity": semantics.get("active_entity") or "",
            "memory_semantics": deepcopy(semantics),
            "source_of_truth": "USER_REQUEST_PLUS_PROVIDER_RESPONSE",
            "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        }.items():
            if pair.get(key) != value:
                pair[key] = value
                changed = True
        semantic_state = pair.get("semantic_state") if isinstance(pair.get("semantic_state"), dict) else {}
        semantic_state.update({
            "topic": semantics.get("topic") or "",
            "subtopic": semantics.get("subtopic") or "",
            "entity": semantics.get("active_entity") or "",
            "active_entity": semantics.get("active_entity") or "",
            "entities": deepcopy(semantics.get("entities") or []),
            "relation": relation,
            "memory_truth": deepcopy(semantics),
            "source_of_truth": "USER_REQUEST_PLUS_PROVIDER_RESPONSE",
            "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        })
        if pair.get("semantic_state") != semantic_state:
            pair["semantic_state"] = semantic_state
            changed = True
        previous_anchor = deepcopy(semantics)
        latest_pair = pair

    day0["dialog_pairs"] = ordered[-SESSION_MEMORY_LIMIT:]
    timeline["day_0"] = day0
    state_obj["memory_timeline"] = timeline

    if latest_pair:
        canonical = deepcopy(latest_pair.get("memory_semantics") or {})
        canonical.update({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "sequence_id": str(latest_pair.get("sequence_id") or ""),
            "task_id": str(latest_pair.get("task_id") or ""),
            "sequence_turn_index": int(latest_pair.get("sequence_turn_index") or 0),
            "created_at": float(latest_pair.get("created_at") or now),
            "expires_after_hours": DIALOGUE_WINDOW_HOURS,
        })
        if state_obj.get("dialogue_memory_anchor") != canonical:
            state_obj["dialogue_memory_anchor"] = deepcopy(canonical)
            changed = True
        turn = deepcopy(canonical)
        turn["record_type"] = "canonical_dialogue_turn"
        turn["source_of_truth"] = "USER_REQUEST_PLUS_PROVIDER_RESPONSE"
        if state_obj.get("canonical_dialogue_turn") != turn:
            state_obj["canonical_dialogue_turn"] = turn
            changed = True

        # Rehydrate active sequence/topic/task mirrors strictly from the repaired pair archive.
        sequence_id = str(latest_pair.get("sequence_id") or "").strip()
        if sequence_id:
            registry = QuantumMemoryEngine._rebuild_task_registry_from_pairs(
                state_obj, sequence_id, user_id, conversation_id
            )
            if registry:
                # Rebuild every task's semantic identity from its latest canonical pair.
                # Legacy task mirrors such as entity="Нарисуй" are never authoritative.
                for task_id, task in list(registry.items()):
                    if not isinstance(task, dict):
                        continue
                    matching = [
                        pair for pair in ordered
                        if isinstance(pair, dict)
                        and str(pair.get("sequence_id") or "") == sequence_id
                        and str(pair.get("task_id") or "") == str(task_id)
                    ]
                    if matching:
                        matching.sort(key=lambda item: float(item.get("created_at") or item.get("timestamp") or 0.0))
                        latest_task_pair = matching[-1]
                        latest_sem = latest_task_pair.get("memory_semantics") if isinstance(latest_task_pair.get("memory_semantics"), dict) else {}
                        if latest_sem:
                            task["topic"] = latest_sem.get("topic") or task.get("topic")
                            task["canonical_topic"] = latest_sem.get("topic") or task.get("canonical_topic")
                            task["entities"] = deepcopy(latest_sem.get("entities") or [])
                            task["entity"] = latest_sem.get("active_entity") or task.get("entity") or ""
                            task["active_entity"] = latest_sem.get("active_entity") or task.get("active_entity") or ""
                            task["subtopic"] = latest_sem.get("subtopic") or task.get("subtopic") or ""
                        task["last_user_request"] = str(latest_task_pair.get("user_request") or task.get("last_user_request") or "")[:1200]
                        task["last_april_answer"] = str(latest_task_pair.get("april_answer") or task.get("last_april_answer") or "")[:2200]
                        task["last_answer"] = task["last_april_answer"]
                        task["last_turn_at"] = float(latest_task_pair.get("created_at") or task.get("last_turn_at") or time.time())
                        task["updated_at"] = task["last_turn_at"]
                        registry[str(task_id)] = task
                state_obj["dialogue_task_registry"] = deepcopy(registry)
                active_task_id = str(latest_pair.get("task_id") or "").strip()
                task = deepcopy(registry.get(active_task_id) or {})
                seq = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else build_default_active_dialogue_sequence()
                seq.update({
                    "sequence_id": sequence_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "status": "active",
                    "topic": canonical.get("topic") or "",
                    "entities": deepcopy(canonical.get("entities") or []),
                    "active_entity": canonical.get("active_entity") or "",
                    "last_user_request": req if (req := str(latest_pair.get("user_request") or "").strip()) else "",
                    "last_april_answer": str(latest_pair.get("april_answer") or "").strip(),
                    "last_turn_at": float(latest_pair.get("created_at") or now),
                    "turn_count": int(latest_pair.get("sequence_turn_index") or 0),
                    "response_count": int(latest_pair.get("sequence_turn_index") or 0),
                    "task_id": active_task_id or seq.get("task_id"),
                    "task_response_count": int(task.get("response_count") or 0),
                    "task_registry": deepcopy(registry),
                    "active_task": deepcopy(task),
                    "interactive_task_state": deepcopy(task),
                    "open_task": deepcopy(task),
                    "task_state": deepcopy(task),
                    "restored": True,
                })
                state_obj["active_dialogue_sequence"] = seq
                state_obj["active_dialogue_task_id"] = str(seq.get("task_id") or "")
                for key in ("active_task", "interactive_task_state", "open_task", "april_active_task"):
                    if task:
                        state_obj[key] = deepcopy(task)
                state_obj["april_active_topic"] = canonical.get("topic") or ""
                state_obj["april_active_entity"] = canonical.get("active_entity") or ""
                state_obj["current_topic"] = canonical.get("topic") or state_obj.get("current_topic")
                state_obj["current_object"] = canonical.get("active_entity") or state_obj.get("current_object")
                focus = state_obj.get("focus_state") if isinstance(state_obj.get("focus_state"), dict) else {}
                focus.update({
                    "active_topic": canonical.get("topic") or focus.get("active_topic"),
                    "active_object": canonical.get("active_entity") or focus.get("active_object"),
                    "intent_freshness": 1.0,
                })
                state_obj["focus_state"] = focus

    return changed

def get_state(user_id):
    """Fast authenticated state access.

    The request hot path deliberately does NOT rebuild the 12h archive, task registry,
    embeddings, or canonical history. Those operations belong to Provider completion
    and/or the hourly maintenance worker. Historical 12h data is recall-only evidence.
    """
    key = str(user_id)
    maintenance_due = False

    with _state_lock:
        needs_full_normalization = False
        if key not in state:
            state[key] = build_default_state()
            safe_state_log(f"NEW EPHEMERAL STATE: {key}")
            needs_full_normalization = True

        obj = state[key]
        obj["user_id"] = key
        profile = obj.get("user_profile")
        if not isinstance(profile, dict):
            profile = {}
        profile.setdefault("name", "")
        profile.setdefault("name_source", "")
        profile.setdefault("updated_at", None)
        obj["user_profile"] = profile
        if not obj.get("conversation_id"):
            obj["conversation_id"] = (
                f"april-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:24]}"
            )
        obj["memory_scope"] = {
            "user_id": key,
            "conversation_id": obj["conversation_id"],
            "scope_version": "USER_SCOPED_SCENE_V2",
        }

        # Full normalization is a one-time load/migration operation. Re-running
        # QuantumMemoryEngine.ensure() on every message would rebuild task/sequence
        # state and scan the 12h archive, defeating the fast hot path.
        if needs_full_normalization or obj.get("_state_manager_normalized_version") != 3:
            QUANTUM_MEMORY_ENGINE.ensure(obj)
            _sanitize_persisted_dialog(obj)
            obj["_state_manager_normalized_version"] = 3
        else:
            # The live dialog is already capped; this is intentionally O(3).
            dialog = obj.get("dialog")
            if isinstance(dialog, list) and len(dialog) > CANONICAL_DIALOG_HOT_LIMIT:
                obj["dialog"] = dialog[-CANONICAL_DIALOG_HOT_LIMIT:]

        cleanup = obj.get("memory_cleanup") if isinstance(obj.get("memory_cleanup"), dict) else {}
        try:
            last_cleanup = float(cleanup.get("last_cleanup_at") or 0.0)
        except (TypeError, ValueError):
            last_cleanup = 0.0
        maintenance_due = (not last_cleanup) or (time.time() - last_cleanup >= MEMORY_HOURLY_CLEANUP_SECONDS)

        result = obj

    if maintenance_due:
        _schedule_hourly_memory_maintenance(key)
    return result


def _append_recall_index(state_obj, pair):
    """Compatibility no-op: live dialogue uses the authenticated pair window directly."""
    if isinstance(state_obj, dict):
        state_obj["dialogue_recall_index"] = []
        state_obj["dialogue_recall_policy"] = {
            "enabled": False,
            "reason": "TWO_STATE_LIVE_DIALOGUE",
            "window_hours": DIALOGUE_WINDOW_HOURS,
        }

def _repair_latest_canonical_dialogue_memory(state_obj):
    """Cheap maintenance: repair only the last 3 completed turns and current task mirrors."""
    if not isinstance(state_obj, dict):
        return False
    timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
    day0 = timeline.get("day_0") if isinstance(timeline.get("day_0"), dict) else {}
    pairs = [p for p in day0.get("dialog_pairs", []) if isinstance(p, dict)][-CANONICAL_DIALOG_HOT_LIMIT:]
    if not pairs:
        return False
    changed = False
    latest = pairs[-1]
    # Provider-produced memory_semantics is authoritative; never re-infer it from a command word.
    sem = latest.get("memory_semantics") if isinstance(latest.get("memory_semantics"), dict) else {}
    if sem:
        canonical = deepcopy(sem)
        canonical.update({
            "user_id": str(state_obj.get("user_id") or ""),
            "conversation_id": str(state_obj.get("conversation_id") or ""),
            "sequence_id": str(latest.get("sequence_id") or ""),
            "task_id": str(latest.get("task_id") or ""),
            "sequence_turn_index": int(latest.get("sequence_turn_index") or 0),
            "created_at": float(latest.get("created_at") or time.time()),
            "expires_after_hours": DIALOGUE_WINDOW_HOURS,
            "source_of_truth": "USER_REQUEST_PLUS_PROVIDER_RESPONSE",
        })
        if state_obj.get("dialogue_memory_anchor") != canonical:
            state_obj["dialogue_memory_anchor"] = deepcopy(canonical)
            turn = deepcopy(canonical)
            turn["record_type"] = "canonical_dialogue_turn"
            state_obj["canonical_dialogue_turn"] = turn
            changed = True
        # Replace stale active entity/topic mirrors from the latest Provider semantics only.
        seq = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
        for k, v in (("topic", canonical.get("topic") or ""), ("active_entity", canonical.get("active_entity") or ""), ("entities", deepcopy(canonical.get("entities") or []))):
            if seq.get(k) != v:
                seq[k] = v
                changed = True
        state_obj["active_dialogue_sequence"] = seq
    return changed


def _schedule_hourly_memory_maintenance(user_id):
    uid = str(user_id)
    with _MEMORY_MAINTENANCE_LOCK:
        if uid in _MEMORY_MAINTENANCE_WORKERS:
            return
        _MEMORY_MAINTENANCE_WORKERS.add(uid)

    def _worker():
        try:
            with _state_lock:
                obj = state.get(uid)
                if not isinstance(obj, dict):
                    return
                cleanup = obj.get("memory_cleanup") if isinstance(obj.get("memory_cleanup"), dict) else {}
                try:
                    last = float(cleanup.get("last_cleanup_at") or 0.0)
                except (TypeError, ValueError):
                    last = 0.0
                if last and time.time() - last < MEMORY_HOURLY_CLEANUP_SECONDS:
                    return
                removed = _cleanup_hot_content(obj)
                repaired = _repair_latest_canonical_dialogue_memory(obj)
                if removed or repaired:
                    QUANTUM_MEMORY_ENGINE.refresh_scene(obj)
                snapshot = _persistable_snapshot(obj)
            safe_state_log(f"HOURLY MEMORY CLEANUP: user={uid} removed={removed} pair_turns={CANONICAL_DIALOG_HOT_LIMIT}")
        except Exception as exc:
            safe_state_log(f"HOURLY MEMORY CLEANUP ERROR: {exc}")
        finally:
            with _MEMORY_MAINTENANCE_LOCK:
                _MEMORY_MAINTENANCE_WORKERS.discard(uid)

    threading.Thread(target=_worker, name="april-memory-hourly-cleanup", daemon=True).start()


def _cleanup_hot_content(state_obj, now=None):
    """Enforce the same 12-hour rolling TTL on all conversational/visual hot content."""
    now = float(now if now is not None else time.time())
    removed = 0

    dialog = safe_list(state_obj.get("dialog"))
    kept_dialog = []
    for item in dialog:
        if isinstance(item, dict):
            created = item.get("created_at") or item.get("timestamp") or 0.0
            expires = item.get("expires_at")
            try:
                expired = (
                    not created
                    or bool(expires and float(expires) <= now)
                    or (now - float(created)) >= USER_CONTENT_RETENTION_SECONDS
                )
            except Exception:
                expired = True
            if expired:
                removed += 1
                continue
        else:
            removed += 1
            continue
        kept_dialog.append(item)
    state_obj["dialog"] = kept_dialog[-CANONICAL_DIALOG_HOT_LIMIT:]

    internal_events = safe_list(state_obj.get("internal_dialog_events"))
    kept_internal = []
    for item in internal_events:
        created = item.get("created_at") if isinstance(item, dict) else 0.0
        try:
            expired = not created or (now - float(created)) >= USER_CONTENT_RETENTION_SECONDS
        except Exception:
            expired = True
        if expired:
            removed += 1
            continue
        kept_internal.append(item)
    state_obj["internal_dialog_events"] = kept_internal[-CANONICAL_DIALOG_HOT_LIMIT:]

    for content_key, timestamp_key in (("last_user_turn", "last_user_turn_at"), ("last_april_turn", "last_april_turn_at"), ("current_scene_request", "current_scene_request_at")):
        value = state_obj.get(content_key)
        stamp = state_obj.get(timestamp_key)
        try:
            expired = bool(value) and (not stamp or (now - float(stamp)) >= USER_CONTENT_RETENTION_SECONDS)
        except Exception:
            expired = bool(value)
        if expired:
            state_obj[content_key] = ""
            state_obj[timestamp_key] = None
            removed += 1

    meta = state_obj.get("meta") if isinstance(state_obj.get("meta"), dict) else {}
    for key, stamp_key in (("last_user_message", "last_user_message_at"), ("last_bot_message", "last_bot_message_at")):
        value = meta.get(key)
        stamp = meta.get(stamp_key)
        try:
            expired = bool(value) and (not stamp or (now - float(stamp)) >= USER_CONTENT_RETENTION_SECONDS)
        except Exception:
            expired = bool(value)
        if expired:
            meta[key] = ""
            meta[stamp_key] = None
            removed += 1
    state_obj["meta"] = meta

    # Generated/uploaded image bytes and temporary paths are not persistent user memory.
    image_context = state_obj.get("image_context")
    if isinstance(image_context, dict):
        created = image_context.get("created_at")
        try:
            if not created or (now - float(created)) >= USER_CONTENT_RETENTION_SECONDS:
                state_obj["image_context"] = None
                removed += 1
        except Exception:
            state_obj["image_context"] = None
            removed += 1

    memory = safe_list(state_obj.get("image_memory"))
    kept_memory = []
    for item in memory:
        if isinstance(item, dict):
            created = item.get("created_at") or item.get("timestamp") or 0.0
            try:
                if not created or (now - float(created)) >= USER_CONTENT_RETENTION_SECONDS:
                    removed += 1
                    continue
            except Exception:
                removed += 1
                continue
        kept_memory.append(item)
    state_obj["image_memory"] = kept_memory[-3:]

    prompt = state_obj.get("last_prompt")
    prompt_stamp = state_obj.get("last_prompt_at")
    try:
        prompt_expired = bool(prompt) and (not prompt_stamp or (now - float(prompt_stamp)) >= USER_CONTENT_RETENTION_SECONDS)
    except Exception:
        prompt_expired = bool(prompt)
    if prompt_expired:
        state_obj["last_prompt"] = None
        state_obj["last_prompt_at"] = None
        state_obj["last_prompt_expires_at"] = None
        removed += 1

    meta = state_obj.get("meta") if isinstance(state_obj.get("meta"), dict) else {}
    entity = meta.get("last_entity")
    entity_stamp = meta.get("last_entity_at")
    try:
        entity_expired = bool(entity) and (not entity_stamp or (now - float(entity_stamp)) >= USER_CONTENT_RETENTION_SECONDS)
    except Exception:
        entity_expired = bool(entity)
    if entity_expired:
        meta["last_entity"] = None
        meta["last_entity_at"] = None
        meta["last_entity_expires_at"] = None
        removed += 1
    state_obj["meta"] = meta

    # The pair archive is the authenticated 12h semantic source. Do NOT prune it
    # to 3 or 15 here. The active window of 15 pairs is a sliding read view used by
    # Interpretation; retention/deletion remains exclusively time-based (12h).
    timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
    day0 = timeline.get("day_0") if isinstance(timeline.get("day_0"), dict) else {}
    if day0:
        pairs = [x for x in day0.get("dialog_pairs", []) if isinstance(x, dict)]
        state_obj["dialogue_recall_index"] = []
        # Keep all unexpired USER↔APRIL pairs in the 12h archive. Interpretation
        # selects the latest 15 as its dynamic working window; nothing older is
        # deleted merely because it left that window.
        day0["dialog_pairs"] = pairs
        # Visual history is also capped; the active/current scene pointers are untouched.
        for field, limit in (("visual_scenes", 3), ("topics", 3), ("objects", 3), ("intent_signals", 3)):
            values = day0.get(field) if isinstance(day0.get(field), list) else []
            if len(values) > limit:
                removed += len(values) - limit
                day0[field] = values[-limit:]
        timeline["day_0"] = day0
        state_obj["memory_timeline"] = timeline

    recall_index = state_obj.get("dialogue_recall_index") if isinstance(state_obj.get("dialogue_recall_index"), list) else []
    cutoff = now - DIALOGUE_WINDOW_SECONDS
    state_obj["dialogue_recall_index"] = [
        x for x in recall_index
        if isinstance(x, dict) and float(x.get("created_at") or 0.0) >= cutoff
    ][-RECALL_INDEX_LIMIT:]

    state_obj["user_content_retention"] = {
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "ttl_seconds": USER_CONTENT_RETENTION_SECONDS,
        "hourly_cleanup_seconds": MEMORY_HOURLY_CLEANUP_SECONDS,
        "full_dialog_turns": CANONICAL_DIALOG_HOT_LIMIT,
        "policy": "hourly_hot_ui_plus_12h_full_dialogue_archive",
        "last_cleanup_at": now,
    }
    state_obj["memory_cleanup"] = {
        "last_cleanup_at": now,
        "last_cleanup_utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "removed_count": removed,
        "window": "15_pair_sliding_active_view_plus_12h_archive",
        "full_dialog_turns": CANONICAL_DIALOG_HOT_LIMIT,
        "recall_index_hours": DIALOGUE_WINDOW_HOURS,
    }
    return removed


def _persistable_snapshot(value, _active=None):
    excluded = {
        "_machine_context",
        "_executor_context_packet",
        "_quantum_evidence_field",
        "_quantum_processor_context",
        "_semantic_encoder",
        "image_current",
        "image_context",
        "image_storage",
        "last_prompt",
        "last_prompt_at",
        "last_prompt_expires_at",
        "last_entity",
        "last_entity_at",
        "last_entity_expires_at",
        "last_user_message",
        "last_user_message_at",
        "last_bot_message",
        "last_bot_message_at",
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
    # Legacy name retained only for callers; no full-state persistence exists.
    try:
        get_state(user_id)
    except Exception as exc:
        safe_state_log(f"PERSIST STATE READ ERROR: {exc}")
    return None


# The Web chat path must not wait on PostgreSQL after the canonical SceneContract
# is already complete. Keep one latest snapshot per user and serialize background
# writes so a later turn replaces, rather than races, an older queued snapshot.
_PERSIST_BACKGROUND_LOCK = threading.RLock()
_PERSIST_BACKGROUND_QUEUES = {}
_PERSIST_BACKGROUND_WORKERS = set()
_MEMORY_MAINTENANCE_LOCK = threading.RLock()
_MEMORY_MAINTENANCE_WORKERS = set()

def persist_state_background(user_id):
    """Queue a persistence marker; serialization and DB I/O happen only in the worker."""
    uid = str(user_id)
    with _PERSIST_BACKGROUND_LOCK:
        _PERSIST_BACKGROUND_QUEUES[uid] = True
        if uid in _PERSIST_BACKGROUND_WORKERS:
            return
        _PERSIST_BACKGROUND_WORKERS.add(uid)

    def _worker():
        while True:
            with _PERSIST_BACKGROUND_LOCK:
                pending = _PERSIST_BACKGROUND_QUEUES.pop(uid, None)
            if pending is None:
                with _PERSIST_BACKGROUND_LOCK:
                    _PERSIST_BACKGROUND_WORKERS.discard(uid)
                return
            try:
                with _state_lock:
                    obj = state.get(uid)
                    if not isinstance(obj, dict):
                        continue
            except Exception as exc:
                safe_state_log(f"BACKGROUND PERSIST ERROR: {exc}")

    threading.Thread(target=_worker, name="april-state-persist", daemon=True).start()


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
    now = time.time()
    if isinstance(ctx, dict):
        ctx = deepcopy(ctx)
        ctx.setdefault("created_at", now)
        ctx.setdefault("expires_at", now + USER_CONTENT_RETENTION_SECONDS)
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
    state_obj = get_state(user_id)
    now = time.time()
    state_obj["last_prompt"] = safe_trim_text(prompt, 1200)
    state_obj["last_prompt_at"] = now
    state_obj["last_prompt_expires_at"] = now + USER_CONTENT_RETENTION_SECONDS


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
            "expires_after_hours": DIALOGUE_WINDOW_HOURS,
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
    sequence = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
    record = {
        "record_type": "dialog_pair",
        "user_id": str(user_id),
        "conversation_id": str(state_obj.get("conversation_id") or ""),
        "sequence_id": str(sequence.get("sequence_id") or ""),
        "sequence_turn_index": int(sequence.get("turn_count") or 0),
        "sequence_topic": safe_trim_text(sequence.get("topic") or "", 240),
        "user_meaning": safe_trim_text(user_msg, 800),
        "april_meaning": safe_trim_text(april_msg, 1400),
        "answer_summary": safe_trim_text(april_msg, 1000),
        "visual_summary": safe_trim_text(
            build_visual_scene_summary(state_obj) or "",
            1000,
        ),
        "topic": safe_trim_text(
            state_obj.get("current_topic")
            or state_obj.get("dialogue_resolution", {}).get("development_state", {}).get("active_topic")
            or state_obj.get("active_topic_slot")
            or "",
            240,
        ),
        "dialogue_relation": str(
            state_obj.get("dialogue_resolution", {}).get("relation") or "NEW"
        ).upper(),
        "development_state": deepcopy(
            state_obj.get("dialogue_resolution", {}).get("development_state") or {}
        ),
        "selected_memory_operand": deepcopy(
            state_obj.get("dialogue_resolution", {}).get("selected_memory_operand") or {}
        ),
        "selected_memory_index": int(
            state_obj.get("dialogue_resolution", {}).get("selected_memory_index", -1) or -1
        ),
        "selected_memory_record": deepcopy(
            state_obj.get("dialogue_resolution", {}).get("selected_memory_record") or {}
        ),
        "memory_slider": deepcopy(
            state_obj.get("dialogue_resolution", {}).get("memory_slider") or {}
        ),
        "semantic_anchor": deepcopy(
            state_obj.get("semantic_anchor")
            or _dict(state_obj.get("dialogue_resolution")).get("development_state", {}).get("semantic_anchor")
            or {}
        ),
        "continuation_hint": "available_for_reference",
        "created_at": time.time(),
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
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
    # Retention is time-based. HOT_DIALOG_LIMIT is only the hot/UI cache and
    # SESSION_MEMORY_LIMIT is not allowed to truncate the live 12-hour semantic
    # dialogue window. Expired pairs are removed; unexpired pairs stay searchable.
    now = time.time()
    day0["dialog_pairs"] = [
        item
        for item in dialog_pairs
        if isinstance(item, dict)
        and (
            not item.get("created_at")
            or (now - float(item.get("created_at"))) < USER_CONTENT_RETENTION_SECONDS
        )
    ]
    state_obj["memory_timeline"] = timeline
    _append_recall_index(state_obj, record)


def compress_dialog_to_summary(state_obj):
    """
    Compatibility summary builder.

    The hot dialog is NEVER replaced by a [COMPRESSED_MEMORY] marker anymore.
    Completed pairs are archived by add_dialog() into day_0 and continue through
    the live day_0 (12h) window; the next authenticated 12h cycle boundary is the deletion boundary.
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
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
        "memory_kind": "summary",
    }

def trim_image_memory(state_obj):
    memory = safe_list(state_obj.get("image_memory"))
    state_obj["image_memory"] = memory[-IMAGE_MEMORY_LIMIT:]


def trim_visual_history(state_obj):
    history = safe_list(state_obj.get("visual_scene_history"))
    state_obj["visual_scene_history"] = history[-VISUAL_HISTORY_LIMIT:]


def _is_internal_dialog_metadata(metadata):
    """Return True only for protocol-level internal turns, never user topics."""
    if not isinstance(metadata, dict):
        return False
    return bool(
        metadata.get("internal_context")
        or metadata.get("internal_turn")
        or str(metadata.get("source") or "").strip().lower() in {
            "internal_visual", "internal_visual_analysis", "passive_visual_helper"
        }
    )


def is_dialogue_visible_scene(scene):
    """Structural visibility check for scenes entering human dialogue continuity."""
    if not isinstance(scene, dict) or not scene:
        return False
    if scene.get("internal_context") is True or scene.get("internal_turn") is True:
        return False
    metadata = scene.get("metadata") if isinstance(scene.get("metadata"), dict) else {}
    if _is_internal_dialog_metadata(metadata):
        return False
    source = str(scene.get("source") or "").strip().lower()
    if source in {"internal_visual", "internal_visual_analysis", "passive_visual_helper"}:
        return False
    # Migration guard for already-persisted protocol scenes from older builds.
    topic = str(scene.get("topic") or scene.get("user_request") or "").strip()
    if topic.startswith("VISUAL_ANALYSIS:"):
        return False
    return True




def _is_human_dialog_item(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    content = str(item.get("content") or item.get("text") or item.get("answer") or "").strip()
    if (metadata.get("internal_context") or metadata.get("internal_turn")
            or metadata.get("source") in {"internal_visual", "internal_visual_analysis", "passive_visual_helper"}
            or content.startswith("VISUAL_ANALYSIS:")):
        return False
    return str(item.get("role") or "").lower() in {"user", "human", "assistant", "april", "bot"}

def add_dialog(user_id, role, content, metadata=None, *, persist=True):
    state_obj = get_state(user_id)
    # Internal visual/tool turns are not human dialogue and must never become
    # previous_user/previous_april evidence for the dialogue vector.
    role_name = str(role or "").strip().lower()
    if _is_internal_dialog_metadata(metadata) or role_name not in {"user", "human", "assistant", "april", "bot"}:
        state_obj.setdefault("internal_dialog_events", []).append({
            "role": str(role or ""),
            "content": safe_trim_text(content, 1200),
            "metadata": deepcopy(metadata),
            "created_at": time.time(),
        })
        state_obj["internal_dialog_events"] = state_obj["internal_dialog_events"][-VISUAL_HISTORY_LIMIT:]
        if persist:
            persist_state(user_id)
        return
    dialog = safe_list(state_obj.get("dialog"))
    message = compact_dialog_message(role, content)
    if isinstance(metadata, dict) and metadata:
        message["metadata"] = deepcopy(metadata)
    dialog.append(message)

    if role == "user":
        now = time.time()
        state_obj["last_user_turn"] = safe_trim_text(content, 320)
        state_obj["last_user_turn_at"] = now
        state_obj["meta"]["last_user_message"] = safe_trim_text(content, 320)
        state_obj["meta"]["last_user_message_at"] = now
    else:
        now = time.time()
        state_obj["last_april_turn"] = safe_trim_text(content, 320)
        state_obj["last_april_turn_at"] = now
        state_obj["meta"]["last_bot_message"] = safe_trim_text(content, 320)
        state_obj["meta"]["last_bot_message_at"] = now

    # Canonical Free hot window: exactly 30 messages. Completed pairs leave the
    # hot window only as one semantic memory record and continue inside the current 12-hour window.
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
            "expires_after_hours": DIALOGUE_WINDOW_HOURS,
        })
        day0["topics"] = day0["topics"][-HOT_DIALOG_LIMIT:]

    state_obj["dialog"] = dialog
    human_dialog = [item for item in dialog if _is_human_dialog_item(item)]
    state_obj["dialog_state"] = {
        "timeline": deepcopy(human_dialog),
        "hot_limit": HOT_DIALOG_LIMIT,
        "hot_user_target": HOT_DIALOG_LIMIT // 2,
        "hot_april_target": HOT_DIALOG_LIMIT // 2,
        "last_user_turn": state_obj.get("last_user_turn", ""),
        "last_april_turn": state_obj.get("last_april_turn", ""),
        "active_topic": state_obj.get("current_topic"),
        "focus": deepcopy(state_obj.get("focus_state", {})),
        "dialogue_vector": deepcopy(state_obj.get("dialogue_vector", {})),
        "turn_progression": deepcopy(state_obj.get("turn_progression", {})),
    }

    trim_image_memory(state_obj)
    trim_visual_history(state_obj)
    trim_topic_memory(state_obj)
    state_obj["active_scene"] = QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    if persist:
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
    state_obj = get_state(user_id)
    now = time.time()
    state_obj["meta"]["last_entity"] = deepcopy(entity)
    state_obj["meta"]["last_entity_at"] = now
    state_obj["meta"]["last_entity_expires_at"] = now + USER_CONTENT_RETENTION_SECONDS


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
        "dialogue_vector": deepcopy(state_obj.get("dialogue_vector", {})),
        "turn_progression": deepcopy(state_obj.get("turn_progression", {})),
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
# ROLLING 12-HOUR MEMORY API
# =====================================================

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
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "memory_cleanup": deepcopy(state_obj.get("memory_cleanup", {})),
        "memory_matrix": deepcopy(state_obj.get("memory_matrix", {})),
        "active_dialogue_sequence": deepcopy(state_obj.get("active_dialogue_sequence", {})),
    }


def build_executor_memory_bridge(user_id, query=""):
    return QUANTUM_MEMORY_ENGINE.build_executor_bridge(get_state(user_id), query=query)


def build_dialogue_memory_bridge(
    user_id,
    query="",
    limit=ACTIVE_DIALOGUE_WINDOW_PAIRS,
    *,
    relation="AUTO",
    target_sequence_id="",
    target_task_id="",
):
    """
    Build the authenticated 12-hour dialogue memory packet after Interpretation
    has resolved the current relation.

    Important separation:
      * the parent sequence is the complete live 12-hour dialogue scope;
      * the active task is a child branch inside that sequence;
      * task-local history is exposed separately and never replaces the parent
        sequence trajectory;
      * RECALL may retrieve an older branch from the same authenticated
        12-hour conversation without changing the current request.

    This function does not decide whether a turn is NEW/CONTINUE/RECALL. It only
    materializes the memory already owned by StateManager for the interpreter and
    downstream Provider/Executor chain.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    user_key = str(user_id)
    conversation_id = str(state_obj.get("conversation_id") or "")
    active = deepcopy(state_obj.get("active_dialogue_sequence") or {})

    mode = str(relation or "AUTO").strip().upper()
    if mode == "AUTO":
        resolution = (
            state_obj.get("dialogue_resolution")
            if isinstance(state_obj.get("dialogue_resolution"), dict)
            else {}
        )
        mode = str(resolution.get("relation") or "NEW").strip().upper()
    if mode not in {"NEW", "CONTINUE", "RECALL"}:
        mode = "NEW"

    active_id = str(active.get("sequence_id") or "").strip()
    selected_sequence_id = str(target_sequence_id or active_id).strip()
    selected_task_id = str(
        target_task_id
        or active.get("task_id")
        or state_obj.get("active_dialogue_task_id")
        or ""
    ).strip()

    now = time.time()
    timeline = (
        state_obj.get("memory_timeline")
        if isinstance(state_obj.get("memory_timeline"), dict)
        else {}
    )

    # ------------------------------------------------------------------
    # Materialize ALL authenticated USER↔APRIL pairs in the 12-hour window.
    # Do not filter by task here: tasks are branches of the parent sequence.
    # ------------------------------------------------------------------
    records: list[dict[str, Any]] = []
    for day_index in range(MEMORY_SLOTS):
        day = timeline.get(f"day_{day_index}")
        if not isinstance(day, dict):
            continue
        for item in day.get("dialog_pairs", []):
            if not isinstance(item, dict):
                continue
            if str(item.get("user_id") or "") != user_key:
                continue
            item_conversation = str(item.get("conversation_id") or "")
            if item_conversation and conversation_id and item_conversation != conversation_id:
                continue
            try:
                created = float(item.get("created_at") or item.get("timestamp") or 0.0)
            except (TypeError, ValueError):
                created = 0.0
            if not created or (now - created) >= USER_CONTENT_RETENTION_SECONDS:
                continue

            records.append({
                "sequence_id": str(item.get("sequence_id") or ""),
                "task_id": str(item.get("task_id") or ""),
                "sequence_turn_index": int(item.get("sequence_turn_index") or 0),
                "task_response_number": int(item.get("task_response_number") or item.get("response_count") or 0),
                "sequence_topic": (
                    item.get("sequence_topic")
                    or item.get("topic")
                    or item.get("canonical_topic")
                    or ""
                ),
                "user_request": (
                    item.get("user_request")
                    or item.get("user_meaning")
                    or item.get("text")
                    or ""
                ),
                "april_answer": (
                    item.get("april_answer")
                    or item.get("april_meaning")
                    or item.get("answer")
                    or ""
                ),
                "answer_summary": (
                    item.get("answer_summary")
                    or item.get("april_meaning")
                    or item.get("april_answer")
                    or ""
                ),
                "dialogue_relation": item.get("dialogue_relation") or item.get("relation") or "",
                "visual_scene_id": item.get("visual_scene_id") or item.get("scene_id") or "",
                "visual_attachment": deepcopy(item.get("visual_attachment") or {}),
                "dialogue_development": deepcopy(item.get("dialogue_development") or {}),
                "created_at": created,
            })

    records.sort(
        key=lambda item: (
            int(item.get("sequence_turn_index") or 0),
            float(item.get("created_at") or 0.0),
        )
    )

    # The sequence window is the parent context. A task is only a child slice.
    sequence_records = [
        item for item in records
        if selected_sequence_id
        and str(item.get("sequence_id") or "") == selected_sequence_id
    ]
    task_records = [
        item for item in sequence_records
        if selected_task_id
        and str(item.get("task_id") or "") == selected_task_id
    ]

    # ------------------------------------------------------------------
    # Resolve the metadata of the selected sequence/branch.
    # ------------------------------------------------------------------
    selected_sequence_meta = (
        deepcopy(active)
        if selected_sequence_id and selected_sequence_id == active_id
        else {}
    )

    if mode == "RECALL" and selected_sequence_id != active_id:
        branch_index = (
            state_obj.get("dialogue_branch_index")
            if isinstance(state_obj.get("dialogue_branch_index"), dict)
            else {}
        )
        for branch in branch_index.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            branch_id = str(branch.get("sequence_id") or branch.get("branch_id") or "")
            if branch_id == selected_sequence_id:
                selected_sequence_meta = deepcopy(branch)
                break

    if not selected_sequence_meta and sequence_records:
        first_record = sequence_records[0]
        last_record = sequence_records[-1]
        selected_sequence_meta = {
            "sequence_id": selected_sequence_id,
            "topic": first_record.get("sequence_topic") or last_record.get("sequence_topic") or "",
            "turn_count": int(last_record.get("sequence_turn_index") or len(sequence_records)),
            "last_user_request": last_record.get("user_request") or "",
            "last_april_answer": last_record.get("april_answer") or "",
            "active": mode == "CONTINUE",
        }

    # Legacy states can contain only a sequence head even when pair archival did
    # not run. Keep one synthetic turn so the current active turn remains usable.
    if selected_sequence_id and not sequence_records and selected_sequence_id == active_id:
        sequence_records = [{
            "sequence_id": selected_sequence_id,
            "task_id": selected_task_id,
            "sequence_turn_index": int(active.get("turn_count") or 0),
            "task_response_number": int(active.get("task_response_count") or 0),
            "sequence_topic": active.get("topic") or "",
            "user_request": active.get("last_user_request") or "",
            "april_answer": active.get("last_april_answer") or "",
            "answer_summary": active.get("last_april_answer") or "",
            "dialogue_relation": active.get("relation") or "",
            "created_at": float(active.get("last_turn_at") or 0.0),
        }]
        task_records = [
            item for item in sequence_records
            if selected_task_id and str(item.get("task_id") or "") == selected_task_id
        ]

    max_turns = max(1, min(int(limit or ACTIVE_DIALOGUE_WINDOW_PAIRS), ACTIVE_DIALOGUE_WINDOW_PAIRS))

    def compact_turn(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "turn": int(item.get("sequence_turn_index") or 0),
            "task_response_number": int(item.get("task_response_number") or 0),
            "task_id": str(item.get("task_id") or ""),
            "user": safe_trim_text(item.get("user_request") or "", 220),
            "april": safe_trim_text(item.get("april_answer") or item.get("answer_summary") or "", 320),
            "topic": safe_trim_text(item.get("sequence_topic") or "", 180),
            "relation": str(item.get("dialogue_relation") or "").upper(),
        }

    recent_sequence_records = sequence_records[-max_turns:]
    recent_task_records = task_records[-max_turns:]
    recent_sequence_trajectory = [
        compact_turn(item)
        for item in recent_sequence_records
        if item.get("user_request") or item.get("april_answer")
    ]
    recent_task_trajectory = [
        compact_turn(item)
        for item in recent_task_records
        if item.get("user_request") or item.get("april_answer")
    ]

    first_turn = compact_turn(sequence_records[0]) if sequence_records else {}
    last_turn = compact_turn(sequence_records[-1]) if sequence_records else {}
    previous_turn = compact_turn(sequence_records[-2]) if len(sequence_records) >= 2 else {}

    topic_path: list[str] = []
    for item in sequence_records:
        topic = str(item.get("sequence_topic") or "").strip()
        if topic and topic not in topic_path:
            topic_path.append(topic)

    task_registry = (
        active.get("task_registry")
        if isinstance(active.get("task_registry"), dict)
        else {}
    )
    top_registry = (
        state_obj.get("dialogue_task_registry")
        if isinstance(state_obj.get("dialogue_task_registry"), dict)
        else {}
    )
    merged_registry = dict(top_registry)
    merged_registry.update(task_registry)
    task_summaries = []
    for tid, task in sorted(
        merged_registry.items(),
        key=lambda pair: (
            float(pair[1].get("created_at") or pair[1].get("started_at") or 0.0)
            if isinstance(pair[1], dict) else 0.0,
            str(pair[0]),
        ),
    ):
        if not isinstance(task, dict):
            continue
        if str(task.get("sequence_id") or selected_sequence_id) != selected_sequence_id:
            continue
        task_summaries.append({
            "task_id": str(task.get("task_id") or tid),
            "topic": safe_trim_text(task.get("topic") or "", 180),
            "entity": safe_trim_text(task.get("entity") or task.get("active_entity") or "", 140),
            "status": str(task.get("status") or "open"),
            "turn_count": int(task.get("turn_count") or task.get("response_count") or 0),
            "last_user_request": safe_trim_text(task.get("last_user_request") or "", 180),
            "last_april_answer": safe_trim_text(task.get("last_april_answer") or task.get("last_answer") or "", 220),
        })

    active_task_meta = {}
    if selected_task_id:
        active_task_meta = deepcopy(merged_registry.get(selected_task_id) or {})
    if not active_task_meta and isinstance(selected_sequence_meta, dict):
        for candidate in (
            selected_sequence_meta.get("active_task"),
            selected_sequence_meta.get("interactive_task_state"),
            selected_sequence_meta.get("open_task"),
            selected_sequence_meta.get("task_state"),
        ):
            if isinstance(candidate, dict) and candidate:
                if not selected_task_id or str(candidate.get("task_id") or "") == selected_task_id:
                    active_task_meta = deepcopy(candidate)
                    break

    # RECALL searches the complete authenticated 12-hour conversation rather
    # than only the current task. The selected branch is still authoritative;
    # these are recovery candidates, not a second route.
    relevant: list[dict[str, Any]] = []
    if mode == "RECALL" and str(query or "").strip():
        candidates = []
        for item in records:
            text_parts = (
                item.get("sequence_topic"),
                item.get("user_request"),
                item.get("april_answer"),
                item.get("answer_summary"),
            )
            source = " ".join(str(x or "") for x in text_parts).strip()
            if source:
                candidates.append((item, source))
        if candidates:
            scores = QUANTUM_MEMORY_ENGINE.semantic_scores(
                str(query),
                [source for _, source in candidates],
            )
            ranked = sorted(
                ((float(scores.get(source, 0.0)), item) for item, source in candidates),
                key=lambda pair: (
                    pair[0],
                    int(pair[1].get("sequence_turn_index") or 0),
                    float(pair[1].get("created_at") or 0.0),
                ),
                reverse=True,
            )
            relevant = [
                {**item, "relevance": round(score, 6)}
                for score, item in ranked[:6]
                if score >= 0.08
            ]

    active_meta = {
        "sequence_id": selected_sequence_meta.get("sequence_id") or selected_sequence_id,
        "task_id": selected_task_id,
        "branch_id": selected_sequence_meta.get("branch_id"),
        "topic": selected_sequence_meta.get("topic") or (topic_path[-1] if topic_path else ""),
        "turn_count": max(
            int(selected_sequence_meta.get("turn_count") or 0),
            int(last_turn.get("turn") or 0),
        ),
        "window_record_count": len(sequence_records),
        "last_user_request": (
            selected_sequence_meta.get("last_user_request")
            or last_turn.get("user")
            or ""
        ),
        "last_april_answer": (
            selected_sequence_meta.get("last_april_answer")
            or last_turn.get("april")
            or ""
        ),
        "last_task_result": deepcopy(active_task_meta.get("last_result") or {}),
        "answer_basis": deepcopy(active_task_meta.get("last_answer_basis") or active_task_meta.get("answer_basis") or {}),
        "dialogue_rules": deepcopy(
            selected_sequence_meta.get("dialogue_rules")
            or active_task_meta.get("dialogue_rules")
            or active.get("dialogue_rules")
            or {}
        ),
        "next_task_response_number": int(active_task_meta.get("response_count") or active_task_meta.get("task_response_count") or 0) + 1 if active_task_meta else 1,
    }

    active_sequence_digest = {
        "version": "active_sequence_digest_v5_12h_sequence_window",
        "source": (
            "authenticated_active_sequence"
            if mode == "CONTINUE"
            else "authenticated_recalled_sequence"
            if mode == "RECALL"
            else "current_turn"
        ),
        "sequence_id": selected_sequence_id,
        "conversation_id": conversation_id,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "history_scope": "authenticated_12h_dialogue_sequence",
        "root_topic": safe_trim_text(
            (topic_path[0] if topic_path else "")
            or selected_sequence_meta.get("topic")
            or "",
            220,
        ),
        "current_topic": safe_trim_text(
            selected_sequence_meta.get("topic")
            or (topic_path[-1] if topic_path else ""),
            220,
        ),
        "current_task_id": selected_task_id,
        "current_task_topic": safe_trim_text(active_task_meta.get("topic") or "", 180),
        "sequence_turn_count": max(
            int(selected_sequence_meta.get("turn_count") or 0),
            int(last_turn.get("turn") or 0),
        ),
        "window_record_count": len(sequence_records),
        "task_turn_count": len(task_records),
        "task_response_count": int(active_task_meta.get("response_count") or active_task_meta.get("task_response_count") or 0),
        "current_focus": safe_trim_text(
            active_task_meta.get("entity")
            or active_task_meta.get("active_entity")
            or (last_turn.get("user") if last_turn else "")
            or "",
            220,
        ),
        "first_turn": first_turn,
        "previous_turn": previous_turn,
        "recent_trajectory": recent_sequence_trajectory,
        "task_trajectory": recent_task_trajectory,
        "last_turn": last_turn,
        "topic_path": [safe_trim_text(x, 180) for x in topic_path[-12:]],
        "task_summaries": task_summaries[-12:],
        "coverage": "authenticated_sequence_window",
        "window_complete": True,
        "provider_compaction_required": True,
        "other_authenticated_branches_available": len(task_summaries) > 1,
        "full_history_included": False,
    }

    interactive_task_state = deepcopy(active_task_meta)
    if (
        not interactive_task_state
        and isinstance(selected_sequence_meta, dict)
        and isinstance(selected_sequence_meta.get("active_task"), dict)
    ):
        interactive_task_state = deepcopy(selected_sequence_meta.get("active_task") or {})

    return {
        "version": "april_dialogue_memory_bridge_v4_12h_sequence_window",
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "history_scope": "authenticated_12h_dialogue_sequence",
        "user_id": user_key,
        "conversation_id": conversation_id,
        "retrieval_mode": mode,
        "target_sequence_id": selected_sequence_id,
        "target_task_id": selected_task_id,
        "active_sequence": active_meta,
        "active_sequence_turns": (
            recent_sequence_records
            if mode in {"CONTINUE", "RECALL"}
            else []
        ),
        "active_sequence_trajectory": recent_sequence_trajectory,
        "active_task_turns": recent_task_records if mode in {"CONTINUE", "RECALL"} else [],
        "active_task_trajectory": recent_task_trajectory,
        "active_sequence_turn_count": len(sequence_records),
        "active_task_turn_count": len(task_records),
        "active_dialogue_context": (
            deepcopy(state_obj.get("active_dialogue_context") or {})
            if mode in {"CONTINUE", "RECALL"}
            else {}
        ),
        "active_sequence_digest": (
            deepcopy(active_sequence_digest)
            if mode in {"CONTINUE", "RECALL"}
            else {}
        ),
        "interactive_task_state": interactive_task_state,
        "task_id": selected_task_id,
        "task_memory": {
            "role": interactive_task_state.get("role"),
            "phase": interactive_task_state.get("phase"),
            "last_question": interactive_task_state.get("last_question"),
            "known_clues": list(interactive_task_state.get("known_clues") or [])[-12:],
            "qa_history": list(
                interactive_task_state.get("qa_history")
                or interactive_task_state.get("turns")
                or []
            )[-12:],
            "candidate_answer": interactive_task_state.get("candidate_answer"),
            "awaiting_user": bool(interactive_task_state.get("awaiting_user")),
        } if interactive_task_state else {},
        "relevant_window_turns": relevant,
        "turn_count_window": len(records),
        "decision_owner": "INTERPRETATION",
        "interpretation_first": True,
        "active_branch_first": True,
        "evidence_only": True,
    }


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
        "window_hours": DIALOGUE_WINDOW_HOURS,
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


def prepare_visual_context_for_turn(user_id, current_request, *, persist=True):
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
    # Keep the complete canonical visual evidence available to the next semantic
    # stage.  Releasing evidence here does not grant continuation authority;
    # Interpretation/Quantum Processor still decides whether this turn actually
    # depends on the previous scene.
    evidence_scene = deepcopy(scene)
    render_blocks = evidence_scene.get("render_blocks")
    if not isinstance(render_blocks, list):
        render_blocks = []

    block_types = []
    presentation_types = []
    for block in render_blocks:
        if not isinstance(block, dict):
            continue
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
            ptype = str(
                presentation.get("kind")
                or presentation.get("mode")
                or presentation.get("renderer")
                or ""
            ).strip().lower()
            if ptype and ptype not in presentation_types:
                presentation_types.append(ptype)

    # Turn-local signal: this is an evidence packet only.  It deliberately does
    # not change relation/continuation and therefore cannot override a fresh
    # representation request.
    state_obj["active_visual_scene_turn"] = deepcopy(evidence_scene)
    state_obj["stored_visual_scene_turn"] = deepcopy(evidence_scene)

    visual_context = {
        "scene_id": str(evidence_scene.get("scene_id") or ""),
        "scene_type": str(evidence_scene.get("scene_type") or ""),
        "topic": safe_trim_text(
            evidence_scene.get("topic")
            or evidence_scene.get("current_request")
            or evidence_scene.get("summary"),
            500,
        ),
        "user_request": safe_trim_text(evidence_scene.get("user_request"), 1200),
        "april_answer": safe_trim_text(evidence_scene.get("april_answer"), 2200),
        "render_block_types": block_types,
        "presentation_types": presentation_types,
        "render_blocks": deepcopy(render_blocks),
        "presentation_signals": deepcopy(
            evidence_scene.get("presentation_signals") or []
        ),
        "semantic_state": deepcopy(
            evidence_scene.get("semantic_state") or {}
        ),
        "render_continuity": deepcopy(
            evidence_scene.get("render_continuity") or {}
        ),
        "source": "active_visual_scene",
        "evidence_only": True,
    }

    # Canonical bridge consumed by runtime adapters.  Keep the old compact keys
    # for compatibility and expose the structured packet without creating a
    # second memory system.
    state_obj["visual_context_bridge"] = {
        "active": True,
        "released": True,
        "overlap": 0.0,
        "semantic_relevance": 0.0,
        "continuation_score": 0.0,
        "decision_owner": "QUANTUM_PROCESSOR",
        "memory_role": "evidence_only",
        "user_id": str(user_id),
        "current_request": current,
        "scene_id": visual_context["scene_id"],
        "visual_context": deepcopy(visual_context),
        "active_visual_scene": deepcopy(evidence_scene),
    }

    if persist:
        persist_state(user_id)
    return deepcopy(state_obj["visual_context_bridge"])

def restore_visual_context_after_turn(user_id, *, new_scene_active=False, persist=True):
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
    # Archived scenes remain only inside day_0 (12h) until TTL cleanup removes them.
    state_obj["stored_visual_scene_turn"] = None
    state_obj["active_visual_scene_turn"] = None
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    if persist:
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

    # An empty frontend visual summary is not a new scene. Keep the 12-hour
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
        "window_hours": DIALOGUE_WINDOW_HOURS,
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
    """Move the current scene into live day_0 (12h) memory without making it hot."""
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

    # Keep it in the visual-scene ledger as durable day_0 (12h) memory too.
    day0.setdefault("visual_scenes", []).append(archived)
    day0["visual_scenes"] = day0["visual_scenes"][-TOPIC_MEMORY_LIMIT:]
    state_obj.setdefault("visual_topic_history", []).append(archived)
    state_obj["visual_topic_history"] = state_obj["visual_topic_history"][-VISUAL_HISTORY_LIMIT:]



def _visual_block_has_payload(block):
    """Return True when a canonical structured block carries real render data.

    The predicate is deliberately renderer-agnostic. It recognizes the complete
    payload families used by the canonical SceneContract, including arithmetic
    diagrams and calculation-result processor blocks. A placeholder
    ``quantum_processor`` status block still does not become visual memory.
    """
    if not isinstance(block, dict):
        return False

    btype = str(
        block.get("type")
        or block.get("artifact_type")
        or block.get("representation")
        or ""
    ).strip().lower()
    renderer = str(block.get("renderer") or "").strip().lower()

    if btype in {"", "text", "markdown"}:
        return False

    payload = block.get("payload")
    if not isinstance(payload, dict):
        artifact = block.get("artifact")
        payload = artifact.get("payload") if isinstance(artifact, dict) else None
    if not isinstance(payload, dict):
        return False

    status = str(payload.get("status") or block.get("status") or "").strip().lower()
    if status in {"unavailable", "pending_data", "incomplete", "error"}:
        return False

    # Canonical structured payload families currently produced by the
    # Quantum Processor/Web contract.
    structural_keys = (
        # Generic data/visual families
        "categories", "labels", "x", "x_values", "points", "data",
        "series", "rows", "items", "nodes", "edges", "url", "src",
        # Geometry / drawing
        "vertices", "segments", "shapes", "coordinates",
        # Arithmetic diagram / number-line families
        "left_group", "right_group", "operator", "equals", "result",
        "expression", "groups", "value", "operands", "operation",
        # Media / artifact identity
        "image", "images", "svg", "drawing_elements", "artifact",
    )

    has_structured_data = any(
        payload.get(key) not in (None, [], {}, "")
        for key in structural_keys
    )
    if has_structured_data:
        return True

    # ``quantum_processor`` is also used for lightweight status blocks. Only
    # promote it to visual memory when it contains a concrete calculation
    # result, not merely ``status=ready/processed`` metadata.
    if btype == "quantum_processor":
        return bool(
            renderer in {"calculation_result", "arithmetic_result", "result"}
            or any(
                payload.get(key) not in (None, [], {}, "")
                for key in ("operation", "operands", "result", "expression", "value")
            )
        )

    return False


def _scene_has_successful_visual(scene):
    if not isinstance(scene, dict):
        return False
    blocks = scene.get("render_blocks")
    if not isinstance(blocks, list):
        return False
    return any(_visual_block_has_payload(block) for block in blocks)


def _build_dialogue_visual_attachment(render_blocks, scene_id="", turn_id="", *, created_at=None):
    """Build a small renderer-neutral visual attachment for the owning dialogue turn.

    The dialogue memory keeps visual identity/metadata, never PNG/base64 payloads.
    This makes a visual artifact part of the same USER↔APRIL turn without
    inflating the 12-hour dialogue memory or changing renderer ownership.
    """
    blocks = render_blocks if isinstance(render_blocks, list) else []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = str(block.get("type") or block.get("artifact_type") or block.get("representation") or "").strip().lower()
        if kind not in VISUAL_SCENE_BLOCK_TYPES:
            continue

        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        artifact = block.get("artifact") if isinstance(block.get("artifact"), dict) else {}
        artifact_payload = artifact.get("payload") if isinstance(artifact.get("payload"), dict) else {}
        presentation = block.get("presentation") if isinstance(block.get("presentation"), dict) else {}

        candidates = [
            block.get("src"), block.get("url"), block.get("asset_url"),
            block.get("image_url"), payload.get("src"), payload.get("url"),
            payload.get("asset_url"), payload.get("image_url"),
            artifact.get("src"), artifact.get("url"), artifact_payload.get("src"),
            artifact_payload.get("url"),
        ]
        src = next((str(value).strip() for value in candidates if isinstance(value, str) and value.strip()), "")

        images = payload.get("images") if isinstance(payload.get("images"), list) else []
        if not src and images:
            for item in images[:8]:
                if isinstance(item, dict):
                    src = next((str(item.get(key)).strip() for key in ("src", "url", "asset_url", "image_url", "asset_path") if item.get(key)), "")
                    if src:
                        break
                elif isinstance(item, str) and item.strip():
                    src = item.strip()
                    break

        # A visual turn is useful for dialogue recall even when its src is absent
        # (e.g. a structured diagram), so preserve its stable semantic identity.
        attachment = {
            "present": True,
            "kind": kind,
            "artifact_id": str(block.get("block_id") or block.get("artifact_id") or artifact.get("artifact_id") or "").strip(),
            "block_id": str(block.get("block_id") or "").strip(),
            "scene_id": str(scene_id or block.get("scene_id") or "").strip(),
            "turn_id": str(turn_id or block.get("turn_id") or "").strip(),
            "renderer": str(
                presentation.get("renderer")
                or block.get("renderer")
                or block.get("viewer")
                or ""
            ).strip(),
            "src": src,
            "caption": str(block.get("caption") or payload.get("caption") or "").strip()[:800],
            "description": str(block.get("description") or payload.get("description") or "").strip()[:1200],
            "alt": str(block.get("alt") or payload.get("alt") or "").strip()[:800],
            "prompt": str(payload.get("prompt") or block.get("prompt") or "").strip()[:1600],
            "mime_type": str(block.get("mime_type") or payload.get("mime_type") or artifact.get("mime_type") or "").strip(),
            "width": payload.get("width") or block.get("width") or artifact.get("width"),
            "height": payload.get("height") or block.get("height") or artifact.get("height"),
            "generation_model": str(
                payload.get("generation_model")
                or block.get("generation_model")
                or artifact.get("generation_model")
                or ""
            ).strip(),
            "generation_quality": str(
                payload.get("generation_quality")
                or block.get("generation_quality")
                or artifact.get("generation_quality")
                or ""
            ).strip(),
            "created_at": created_at if created_at is not None else time.time(),
        }
        return {k: v for k, v in attachment.items() if v not in (None, "", [], {})}
    return {}


def update_scene_context(
    user_id,
    scene_contract,
    current_request="",
    answer="",
    *,
    provider_result=None,
    visual_generation_memory=None,
    internal_context=False,
    persist=True,
):
    """
    One canonical dialogue-scene update.

    Every completed USER→APRIL turn becomes the current visual dialogue scene,
    regardless of whether it contains a graphic/table/formula. The scene stores
    the compact meaning of the user request + April answer + current rendering
    state. When the semantic dialogue contract says the turn is independent/new,
    the previous scene is archived into the existing A-E / 12-hour memory and the
    new turn becomes the only active scene.

    No deletion, no trigger routing, no word rules and no renderer decisions.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    conversation_id = _ensure_conversation_scope(state_obj, user_id)

    # Optional machine-only visual-generation evidence. The authenticated
    # conversation/sequence IDs are canonicalized here rather than trusted from
    # the renderer, so the large prompt can live only inside the existing 12-hour
    # USER↔APRIL memory pair.
    visual_generation_memory_record = (
        deepcopy(visual_generation_memory)
        if isinstance(visual_generation_memory, dict)
        and str(visual_generation_memory.get("generation_prompt") or "").strip()
        else {}
    )
    if visual_generation_memory_record:
        visual_generation_memory_record["version"] = str(
            visual_generation_memory_record.get("version")
            or "visual_generation_dialogue_memory_v1"
        )
        visual_generation_memory_record["memory_kind"] = "visual_generation_prompt"
        visual_generation_memory_record["source"] = "C_APRIL_IMAGES_GENERATOR"
        visual_generation_memory_record["user_id"] = str(user_id)
        visual_generation_memory_record["conversation_id"] = conversation_id
        visual_generation_memory_record["dialogue_sequence_id"] = str(
            visual_generation_memory_record.get("dialogue_sequence_id") or ""
        )
        visual_generation_memory_record["created_at"] = float(
            visual_generation_memory_record.get("created_at") or time.time()
        )
        visual_generation_memory_record["expires_after_hours"] = DIALOGUE_WINDOW_HOURS
        visual_generation_memory_record["history_scope"] = "authenticated_dialogue_12h"

    contract = scene_contract if isinstance(scene_contract, dict) else {}
    if internal_context:
        # Internal multimodal helper turns may inform the current response, but
        # they are never allowed to replace the human dialogue anchor.
        state_obj["last_internal_visual_context"] = {
            "user_id": str(user_id),
            "conversation_id": conversation_id,
            "current_request": safe_trim_text(current_request, 1200),
            "answer": safe_trim_text(answer, 2200),
            "created_at": time.time(),
            "internal_context": True,
        }
        if persist:
            persist_state(user_id)
        return state_obj.get("active_scene_contract")
    if not contract and hasattr(scene_contract, "__dict__"):
        contract = dict(scene_contract.__dict__)

    render_blocks = contract.get("render_blocks") or contract.get("blocks") or []
    block_types = []
    presentation_types = []
    render_signal_inventory = []
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
            signal = block.get("presentation") if isinstance(block.get("presentation"), dict) else block.get("signal")
            if isinstance(signal, dict):
                render_signal_inventory.append({
                    "block_id": safe_trim_text(
                        block.get("block_id") or block.get("render_id") or "",
                        120,
                    ),
                    "type": block_type,
                    "renderer": safe_trim_text(
                        signal.get("web_renderer")
                        or signal.get("renderer")
                        or block.get("renderer")
                        or "",
                        120,
                    ),
                    "fallback_renderer": safe_trim_text(
                        signal.get("fallback_renderer") or "MessageTextBlock",
                        120,
                    ),
                    "sequence_index": block.get("sequence_index"),
                    "signal_channel": safe_trim_text(
                        signal.get("signal_channel") or "canonical_web_render_signal_v2",
                        120,
                    ),
                })

    current_request_text = str(current_request or "").strip()
    answer_text = str(answer or "").strip()[:4000]

    # The completed Provider envelope is the only authoritative completed-turn source.
    provider_payload = provider_result if isinstance(provider_result, dict) else {}
    provider_machine = provider_payload.get("machine_response") if isinstance(provider_payload.get("machine_response"), dict) else provider_payload
    provider_metadata = provider_machine.get("metadata") if isinstance(provider_machine.get("metadata"), dict) else {}
    provider_answer = str(
        provider_machine.get("answer")
        or provider_machine.get("content")
        or provider_machine.get("response")
        or answer_text
    ).strip()[:4000]
    if provider_answer:
        answer_text = provider_answer

    semantic_scene_state = {}
    metadata = contract.get("metadata") if isinstance(contract.get("metadata"), dict) else {}
    if isinstance(metadata.get("semantic_scene_state"), dict):
        semantic_scene_state = deepcopy(metadata["semantic_scene_state"])

    identity_scope = _dict(contract.get("authenticated_scope") or _dict(contract.get("metadata")).get("identity_scope"))
    active_sequence = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
    contract_selected_memory_index = contract.get("selected_memory_index")
    try:
        contract_selected_memory_index = int(contract_selected_memory_index)
    except (TypeError, ValueError):
        contract_selected_memory_index = int(
            _dict(state_obj.get("dialogue_resolution")).get("selected_memory_index", -1) or -1
        )
    if not str(identity_scope.get("dialogue_sequence_id") or "").strip():
        sequence_id = str(active_sequence.get("sequence_id") or contract.get("dialogue_sequence_id") or "").strip()
        if sequence_id:
            identity_scope = deepcopy(identity_scope)
            identity_scope["dialogue_sequence_id"] = sequence_id
    state_obj["active_scene_contract"] = {
        "scene_version": str(contract.get("scene_version") or ""),
        "scene_id": str(contract.get("scene_id") or ""),
        "turn_id": str(contract.get("turn_id") or ""),
        "flow_id": str(contract.get("flow_id") or ""),
        "topic_group": str(contract.get("topic_group") or ""),
        "continuation": bool(contract.get("continuation")),
        "user_id": str(contract.get("user_id") or identity_scope.get("user_id") or user_id),
        "conversation_id": str(contract.get("conversation_id") or identity_scope.get("conversation_id") or conversation_id),
        "dialogue_sequence_id": str(contract.get("dialogue_sequence_id") or identity_scope.get("dialogue_sequence_id") or ""),
        "task_id": str(contract.get("task_id") or _dict(contract.get("active_task")).get("task_id") or ""),
        "sequence_turn_index": int(contract.get("sequence_turn_index") or 0),
        "task_response_number": int(contract.get("task_response_number") or _dict(contract.get("active_task")).get("response_count") or 0),
        "active_task": deepcopy(contract.get("active_task") or {}),
        "dialogue_obligations": deepcopy(
            contract.get("dialogue_obligations")
            or _dict(contract.get("dialogue_state")).get("dialogue_obligations")
            or state_obj.get("dialogue_obligations")
            or []
        ),
        "dialogue_development": deepcopy(
            contract.get("dialogue_development")
            or _dict(contract.get("metadata")).get("dialogue_development")
            or state_obj.get("dialogue_development")
            or {}
        ),
        "memory_slider": deepcopy(
            contract.get("memory_slider")
            or _dict(contract.get("dialogue_state")).get("memory_slider")
            or _dict(state_obj.get("dialogue_resolution")).get("memory_slider")
            or {}
        ),
        "semantic_anchor": deepcopy(
            contract.get("semantic_anchor")
            or _dict(contract.get("metadata")).get("semantic_anchor")
            or state_obj.get("semantic_anchor")
            or {}
        ),
        "selected_memory_index": contract_selected_memory_index,
        "selected_memory_operand": deepcopy(
            contract.get("selected_memory_operand")
            or _dict(state_obj.get("dialogue_resolution")).get("selected_memory_operand")
            or {}
        ),
        "selected_memory_record": deepcopy(
            contract.get("selected_memory_record")
            or _dict(state_obj.get("dialogue_resolution")).get("selected_memory_record")
            or {}
        ),
        "dialogue_state": deepcopy(contract.get("dialogue_state") or {}),
        "authenticated_scope": deepcopy(identity_scope or {"user_id": str(user_id), "conversation_id": conversation_id}),
        "active_scene": str(contract.get("active_scene") or ""),
        "space_continuity": deepcopy(contract.get("space_continuity") or {}),
        "scene_blueprint": deepcopy(contract.get("scene_blueprint") or {}),
        "relations": deepcopy(contract.get("relations") or []),
        "order": deepcopy(contract.get("order") or []),
        "signal": deepcopy(contract.get("signal") or {}),
        "metadata": deepcopy(contract.get("metadata") or {}),
        "supported_payloads": deepcopy(contract.get("supported_payloads") or []),
        "render_block_types": block_types,
        "presentation_types": presentation_types,
        "render_blocks": deepcopy(render_blocks) if isinstance(render_blocks, list) else [],
        "presentation_signals": [
            deepcopy(block.get("presentation"))
            for block in render_blocks
            if isinstance(block, dict) and isinstance(block.get("presentation"), dict)
        ],
        "render_signal_inventory": deepcopy(render_signal_inventory),
        "current_request": current_request_text,
        "answer": answer_text,
        "scene_id": str(contract.get("scene_id") or ""),
        "user_id": str(user_id),
        "conversation_id": conversation_id,
    }
    now = time.time()
    state_obj["current_scene_request"] = current_request_text
    state_obj["current_scene_request_at"] = now
    state_obj["last_april_turn"] = answer_text
    state_obj["last_april_turn_at"] = now

    continuity = QUANTUM_MEMORY_ENGINE._continuity_context(
        state_obj, state_obj["active_scene_contract"]
    )
    dialogue_resolution = state_obj.get("dialogue_resolution")
    resolved_relation = str(
        dialogue_resolution.get("relation")
        if isinstance(dialogue_resolution, dict) and dialogue_resolution.get("authoritative")
        else continuity.get("relation") or ""
    ).strip().upper()
    if resolved_relation == "RECALL":
        # Migrate stale pre-v4 state. RECALL is no longer a dialogue relation.
        # Historical requests are NEW turns with context_mode=HISTORY_LOOKUP.
        resolved_relation = "NEW"
    elif resolved_relation not in {"CONTINUE", "NEW"}:
        resolved_relation = "CONTINUE" if continuity.get("continuation") else "NEW"
    context_mode = str(
        (dialogue_resolution.get("context_mode") if isinstance(dialogue_resolution, dict) else "")
        or continuity.get("context_dependency")
        or ""
    ).strip().lower()
    is_continuation = resolved_relation == "CONTINUE"
    is_recall = False

    current_scene = state_obj.get("current_visual_scene")
    if not isinstance(current_scene, dict):
        current_scene = state_obj.get("active_visual_scene")
    current_scene = current_scene if isinstance(current_scene, dict) else None

    # Only NEW closes the current active topic. CONTINUE develops it; RECALL
    # switches the semantic operand to an older authenticated dialogue record.
    if current_scene and resolved_relation == "NEW":
        previous_topic = safe_trim_text(
            current_scene.get("topic")
            or current_scene.get("current_request")
            or current_scene.get("summary"),
            500,
        )
        if previous_topic or current_scene.get("scene_id"):
            _archive_current_visual_scene_to_dynamic(state_obj, user_id)
        state_obj["active_topic_slot"] = _next_visual_topic_slot(state_obj)

    selected_operand = {}
    selected_index = -1
    if isinstance(dialogue_resolution, dict):
        selected_operand = deepcopy(dialogue_resolution.get("selected_memory_operand") or {})
        try:
            selected_index = int(dialogue_resolution.get("selected_memory_index", -1))
        except (TypeError, ValueError):
            selected_index = -1

    provisional_dialogue_vector = (
        state_obj.get("dialogue_vector")
        if isinstance(state_obj.get("dialogue_vector"), dict)
        else {}
    )
    previous_anchor = state_obj.get("dialogue_memory_anchor") if isinstance(state_obj.get("dialogue_memory_anchor"), dict) else {}
    if not previous_anchor:
        previous_seq = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
        previous_anchor = {
            "topic": previous_seq.get("topic") or "",
            "entities": previous_seq.get("entities") or [],
            "active_entity": previous_seq.get("active_entity") or "",
            "user_request": previous_seq.get("last_user_request") or "",
            "april_answer": previous_seq.get("last_april_answer") or "",
        }

    # Canonical semantic memory is built only after Provider/OpenAI has returned
    # the completed USER request + APRIL answer. Pre-provider interpretation is audit only.
    post_provider_semantics = _derive_post_provider_memory_semantics(
        current_request_text,
        answer_text,
        provisional=dialogue_vector,
        previous_anchor=previous_anchor,
        relation=resolved_relation,
        render_types=block_types or presentation_types,
    )
    post_provider_semantics["provider_contract"] = {
        "present": bool(provider_payload),
        "structured": bool(provider_machine),
        "image_generation_spec": deepcopy(provider_metadata.get("image_generation_spec") or {}),
        "render_blocks_count": len(provider_machine.get("render_blocks") or []) if isinstance(provider_machine.get("render_blocks"), list) else 0,
    }

    dialogue_vector = deepcopy(provisional_dialogue_vector)
    dialogue_vector["canonical_topic"] = post_provider_semantics.get("topic") or current_request_text[:220]
    dialogue_vector["active_topic"] = post_provider_semantics.get("topic") or dialogue_vector.get("active_topic") or current_request_text[:220]
    dialogue_vector["topic"] = dialogue_vector["canonical_topic"]
    dialogue_vector["active_entity"] = post_provider_semantics.get("active_entity") or ""
    dialogue_vector["entities"] = deepcopy(post_provider_semantics.get("entities") or [])
    dialogue_vector["subtopic"] = post_provider_semantics.get("subtopic") or dialogue_vector.get("subtopic") or ""
    dialogue_vector["memory_semantics"] = deepcopy(post_provider_semantics)

    supplied_task = (
        dialogue_vector.get("interactive_task_state")
        or dialogue_vector.get("open_task")
        or dialogue_vector.get("task_state")
    )
    if isinstance(supplied_task, dict) and supplied_task:
        supplied_task = deepcopy(supplied_task)
        supplied_task["topic"] = post_provider_semantics.get("topic") or supplied_task.get("topic")
        supplied_task["canonical_topic"] = post_provider_semantics.get("topic") or supplied_task.get("canonical_topic")
        supplied_task["entity"] = post_provider_semantics.get("active_entity") or supplied_task.get("entity")
        supplied_task["active_entity"] = post_provider_semantics.get("active_entity") or supplied_task.get("active_entity")
        supplied_task["subtopic"] = post_provider_semantics.get("subtopic") or supplied_task.get("subtopic")
        dialogue_vector["interactive_task_state"] = supplied_task
        dialogue_vector["open_task"] = deepcopy(supplied_task)
        dialogue_vector["task_state"] = deepcopy(supplied_task)

    # The dialogue vector, not the visual-artifact pointer, owns sequence
    # continuity. A new vector is the only transition that creates a sequence.
    active_sequence = QUANTUM_MEMORY_ENGINE._advance_active_dialogue_sequence(
        state_obj,
        user_id,
        resolved_relation,
        current_request_text,
        answer_text,
        dialogue_vector=dialogue_vector,
        selected_operand=selected_operand,
        canonical_semantics=post_provider_semantics,
    )

    # Refresh the scene-level task mirror from the canonical sequence state. The
    # contract arriving from Interpretation is the decision input; StateManager
    # has now committed the actual result and therefore owns the authoritative
    # task response number/result for this completed turn.
    state_obj["active_scene_contract"]["dialogue_sequence_id"] = str(active_sequence.get("sequence_id") or state_obj["active_scene_contract"].get("dialogue_sequence_id") or "")
    state_obj["active_scene_contract"]["task_id"] = str(active_sequence.get("task_id") or state_obj["active_scene_contract"].get("task_id") or "")
    state_obj["active_scene_contract"]["sequence_turn_index"] = int(active_sequence.get("turn_count") or state_obj["active_scene_contract"].get("sequence_turn_index") or 0)
    state_obj["active_scene_contract"]["task_response_number"] = int(active_sequence.get("task_response_count") or state_obj["active_scene_contract"].get("task_response_number") or 0)
    state_obj["active_scene_contract"]["active_task"] = deepcopy(active_sequence.get("active_task") or state_obj["active_scene_contract"].get("active_task") or {})
    state_obj["active_scene_contract"]["dialogue_rules"] = deepcopy(active_sequence.get("dialogue_rules") or state_obj["active_scene_contract"].get("dialogue_rules") or {})

    previous_scene_id = ""
    if resolved_relation == "CONTINUE" and isinstance(current_scene, dict):
        previous_scene_id = str(current_scene.get("scene_id") or "")
    elif resolved_relation == "RECALL" and isinstance(selected_operand, dict):
        previous_scene_id = str(
            selected_operand.get("scene_id")
            or selected_operand.get("visual_scene_id")
            or selected_operand.get("source_scene_id")
            or ""
        )

    state_obj["visual_scene_version"] = int(state_obj.get("visual_scene_version") or 0) + 1
    scene_id = str(
        contract.get("scene_id")
        or f"{conversation_id}:{state_obj['visual_scene_version']}"
    )

    # Canonical "visual dialogue scene": request + answer + semantic state +
    # render/presentation inventory. This is the active scene regardless of
    # whether the visible content is text, formula, table, graph or media.
    dialogue_development = deepcopy(
        contract.get("dialogue_development")
        or _dict(contract.get("metadata")).get("dialogue_development")
        or state_obj.get("dialogue_development")
        or {}
    )
    if not isinstance(dialogue_development, dict):
        dialogue_development = {}
    state_obj["dialogue_development"] = deepcopy(dialogue_development)

    scene_record = {
        "scene_id": scene_id,
        "scene_version": str(contract.get("scene_version") or ""),
        "turn_id": str(contract.get("turn_id") or state_obj.get("visual_scene_version")),
        "flow_id": str(contract.get("flow_id") or ""),
        "user_id": str(contract.get("user_id") or user_id),
        "conversation_id": str(contract.get("conversation_id") or conversation_id),
        "dialogue_sequence_id": str(contract.get("dialogue_sequence_id") or active_sequence.get("sequence_id") or ""),
        "task_id": str(contract.get("task_id") or active_sequence.get("task_id") or ""),
        "sequence_turn_index": int(contract.get("sequence_turn_index") or active_sequence.get("turn_count") or 0),
        "task_response_number": int(contract.get("task_response_number") or active_sequence.get("task_response_count") or 0),
        "authenticated_scope": deepcopy(
            identity_scope
            or {"user_id": str(user_id), "conversation_id": conversation_id}
        ),
        "active_task": deepcopy(
            active_sequence.get("active_task")
            or contract.get("active_task")
            or state_obj.get("interactive_task_state")
            or {}
        ),
        "dialogue_obligations": deepcopy(
            contract.get("dialogue_obligations")
            or _dict(contract.get("metadata")).get("dialogue_obligations")
            or state_obj.get("dialogue_obligations")
            or []
        ),
        "scene_type": str(contract.get("active_scene") or "dialogue"),
        "topic": safe_trim_text(
            post_provider_semantics.get("topic")
            or (
                active_sequence.get("topic")
                if is_continuation
                else (
                    selected_operand.get("topic")
                    if is_recall and isinstance(selected_operand, dict) and selected_operand.get("topic")
                    else (
                        contract.get("active_topic")
                        or contract.get("topic")
                        or active_sequence.get("topic")
                        or state_obj.get("current_topic")
                        or state_obj.get("focus_state", {}).get("active_topic")
                        or current_request_text
                    )
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
        "context_dependency": ("continuation" if resolved_relation == "CONTINUE" else "recall" if resolved_relation == "RECALL" else "independent"),
        "dialogue_relation": resolved_relation,
        "selected_memory_index": selected_index,
        "selected_memory_operand": deepcopy(selected_operand),
        "selected_memory_record": deepcopy(
            _dict(dialogue_resolution).get("selected_memory_record") or {}
            if isinstance(dialogue_resolution, dict) else {}
        ),
        "memory_slider": deepcopy(
            _dict(dialogue_resolution).get("memory_slider") or {}
            if isinstance(dialogue_resolution, dict) else {}
        ),
        "semantic_anchor": deepcopy(
            contract.get("semantic_anchor")
            or _dict(contract.get("metadata")).get("semantic_anchor")
            or state_obj.get("semantic_anchor")
            or {}
        ),
        "interactive_task_state": deepcopy(
            state_obj.get("interactive_task_state")
            or active_sequence.get("interactive_task_state")
            or {}
        ),
        "development_state": deepcopy(
            dialogue_development
            or (dialogue_resolution.get("development_state") if isinstance(dialogue_resolution, dict) else {})
        ),
        "previous_scene_id": previous_scene_id,
        "dialogue_development": deepcopy(dialogue_development),
        "render_block_types": block_types,
        "presentation_types": presentation_types,
        "renderer_state": deepcopy(contract.get("renderer_state") or {}),
        "supported_payloads": deepcopy(contract.get("supported_payloads") or []),
        "render_blocks": deepcopy(render_blocks) if isinstance(render_blocks, list) else [],
        "presentation_signals": [
            deepcopy(block.get("presentation"))
            for block in render_blocks
            if isinstance(block, dict) and isinstance(block.get("presentation"), dict)
        ],
        "render_signal_inventory": deepcopy(render_signal_inventory),
        "semantic_state": deepcopy(semantic_scene_state),
        "memory_semantics": deepcopy(post_provider_semantics),
        "pre_provider_interpretation": deepcopy(metadata.get("semantic_scene_state") or {}),
        "provider_structured_result": {
            "answer": answer_text,
            "render_block_types": list(block_types),
            "metadata": {
                "provider_version": str(provider_metadata.get("provider_version") or ""),
                "image_generation_spec_present": bool(provider_metadata.get("image_generation_spec")),
            },
        },
        "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        "source_of_truth": "USER_REQUEST_PLUS_APRIL_ANSWER",
        "subtopic": post_provider_semantics.get("subtopic") or "",
        "entities": deepcopy(post_provider_semantics.get("entities") or []),
        "active_entity": post_provider_semantics.get("active_entity") or "",
        "dialogue_vector": deepcopy(state_obj.get("dialogue_vector", {})),
        "turn_progression": deepcopy(state_obj.get("turn_progression", {})),
        "interactive_task_state": deepcopy(
            state_obj.get("interactive_task_state")
            or active_sequence.get("interactive_task_state")
            or active_sequence.get("open_task")
            or {}
        ),
        "sequence_id": active_sequence.get("sequence_id"),
        "task_id": active_sequence.get("task_id"),
        "sequence_turn_index": active_sequence.get("turn_count", 0),
        "task_response_number": active_sequence.get("task_response_count", 0),
        "dialogue_rules": deepcopy(active_sequence.get("dialogue_rules") or {}),
        "sequence_topic": post_provider_semantics.get("topic") or active_sequence.get("topic"),
        "render_continuity": {
            "relation": resolved_relation,
            "reuse_existing_scene": bool(resolved_relation == "CONTINUE" and previous_scene_id),
            "reuse_recalled_memory": bool(resolved_relation == "RECALL" and selected_operand),
            "selected_memory_index": selected_index,
            "previous_scene_id": previous_scene_id,
            "previous_render_types": list(current_scene.get("render_block_types") or []) if is_continuation and isinstance(current_scene, dict) else [],
            "avoid_repeat": True,
        },
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "turn_id": state_obj.get("visual_scene_version"),
        "timestamp": time.time(),
        "memory_kind": "current_visual_dialogue",
        "dialogue_visible": True,
        "internal_context": False,
    }

    # Attach only compact visual identity/metadata to this same dialogue turn.
    # The binary image remains owned by C_ARTIFACT_CONTRACT / GalleryBlock.
    visual_attachment = _build_dialogue_visual_attachment(
        render_blocks,
        scene_id=scene_id,
        turn_id=str(state_obj.get("visual_scene_version")),
        created_at=time.time(),
    )
    if visual_attachment:
        scene_record["visual_attachment"] = deepcopy(visual_attachment)

        # The active dialogue sequence remains the single continuity owner while
        # remembering the last successful visual attached to that sequence.
        active_sequence["last_visual_attachment"] = deepcopy(visual_attachment)
        active_sequence["last_visual_scene_id"] = scene_id
        active_sequence["last_visual_turn_index"] = int(active_sequence.get("turn_count") or 0)
        active_sequence["visual_turn_count"] = int(active_sequence.get("visual_turn_count") or 0) + 1
        state_obj["active_dialogue_sequence"] = deepcopy(active_sequence)

    # Provider result is the canonical semantic source for the completed turn.
    # Preserve the earlier interpretation only as an audit trail.
    semantic_scene_state = {
        **deepcopy(semantic_scene_state),
        "topic": post_provider_semantics.get("topic") or scene_record.get("topic") or active_sequence.get("topic"),
        "subtopic": post_provider_semantics.get("subtopic") or semantic_scene_state.get("subtopic") or "",
        "entity": post_provider_semantics.get("active_entity") or semantic_scene_state.get("entity") or "",
        "active_entity": post_provider_semantics.get("active_entity") or semantic_scene_state.get("active_entity") or "",
        "entities": deepcopy(post_provider_semantics.get("entities") or []),
        "relation": resolved_relation,
        "memory_truth": deepcopy(post_provider_semantics),
        "source_of_truth": "USER_REQUEST_PLUS_APRIL_ANSWER",
        "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        "pre_provider_interpretation": deepcopy(metadata.get("semantic_scene_state") or {}),
    }
    state_obj["semantic_scene_state"] = deepcopy(semantic_scene_state)
    scene_record["semantic_state"] = deepcopy(semantic_scene_state)

    # SINGLE MEMORY AUTHORITY: this is the completed USER↔APRIL turn leaving Provider.
    canonical_turn = deepcopy(post_provider_semantics)
    canonical_turn.update({
        "record_type": "canonical_dialogue_turn",
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "sequence_id": str(active_sequence.get("sequence_id") or ""),
        "task_id": str(active_sequence.get("task_id") or ""),
        "sequence_turn_index": int(active_sequence.get("turn_count") or 0),
        "created_at": now,
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
    })
    state_obj["canonical_dialogue_turn"] = deepcopy(canonical_turn)
    state_obj["dialogue_memory_anchor"] = deepcopy(canonical_turn)

    # Compatibility mirrors are derived from canonical memory, never used as its source.
    state_obj["april_active_topic"] = canonical_turn.get("topic") or ""
    state_obj["april_active_entity"] = canonical_turn.get("active_entity") or ""
    state_obj["current_topic"] = canonical_turn.get("topic") or state_obj.get("current_topic")
    state_obj["current_object"] = canonical_turn.get("active_entity") or state_obj.get("current_object")
    focus = state_obj.get("focus_state") if isinstance(state_obj.get("focus_state"), dict) else {}
    focus.update({
        "active_topic": canonical_turn.get("topic") or focus.get("active_topic"),
        "active_object": canonical_turn.get("active_entity") or focus.get("active_object"),
        "intent_freshness": 1.0,
    })
    state_obj["focus_state"] = focus
    # Keep the same post-Provider semantic truth on the scene contract returned
    # to WEB; render blocks/signals are untouched.
    active_contract = state_obj.get("active_scene_contract") if isinstance(state_obj.get("active_scene_contract"), dict) else {}
    active_metadata = active_contract.get("metadata") if isinstance(active_contract.get("metadata"), dict) else {}
    active_metadata = deepcopy(active_metadata)
    active_metadata["semantic_scene_state"] = deepcopy(semantic_scene_state)
    active_metadata["memory_semantics"] = deepcopy(post_provider_semantics)
    active_metadata["memory_source"] = "POST_PROVIDER_OPENAI_RESPONSE"
    active_metadata["source_of_truth"] = "USER_REQUEST_PLUS_APRIL_ANSWER"
    active_contract["metadata"] = active_metadata
    active_contract["topic_group"] = scene_record.get("topic") or active_contract.get("topic_group") or ""
    active_contract["continuation"] = bool(is_continuation)
    active_contract["dialogue_sequence_id"] = str(active_sequence.get("sequence_id") or active_contract.get("dialogue_sequence_id") or "")
    active_contract["task_id"] = str(active_sequence.get("task_id") or active_contract.get("task_id") or "")
    active_contract["sequence_turn_index"] = int(active_sequence.get("turn_count") or active_contract.get("sequence_turn_index") or 0)
    active_contract["task_response_number"] = int(active_sequence.get("task_response_count") or active_contract.get("task_response_number") or 0)
    active_contract["active_task"] = deepcopy(active_sequence.get("active_task") or active_contract.get("active_task") or {})
    state_obj["active_scene_contract"] = active_contract
    state_obj["current_topic"] = scene_record.get("topic") or active_sequence.get("topic") or state_obj.get("current_topic")
    state_obj["april_active_topic"] = state_obj["current_topic"]
    state_obj["active_entity"] = post_provider_semantics.get("active_entity") or state_obj.get("active_entity")
    state_obj["april_active_entity"] = post_provider_semantics.get("active_entity") or state_obj.get("april_active_entity")

    # One canonical post-Provider memory anchor feeds the next interpretation
    # turn. It contains the authenticated USER↔APRIL pair plus semantic
    # continuation data; preliminary Interpretation is retained only as audit.
    memory_cycle = state_obj.get("memory_cycle") if isinstance(state_obj.get("memory_cycle"), dict) else {}
    canonical_anchor = {
        "version": "dialogue_memory_anchor_v2_post_provider",
        "source_of_truth": "USER_REQUEST_PLUS_APRIL_ANSWER",
        "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "dialogue_sequence_id": str(active_sequence.get("sequence_id") or ""),
        "task_id": str(active_sequence.get("task_id") or ""),
        "sequence_turn_index": int(active_sequence.get("turn_count") or 0),
        "task_response_number": int(active_sequence.get("task_response_count") or 0),
        "topic": post_provider_semantics.get("topic") or "",
        "subtopic": post_provider_semantics.get("subtopic") or "",
        "entities": deepcopy(post_provider_semantics.get("entities") or []),
        "active_entity": post_provider_semantics.get("active_entity") or "",
        "relation": resolved_relation,
        "user_request": safe_trim_text(current_request_text, 1200),
        "april_answer": safe_trim_text(answer_text, 2200),
        "created_at": now,
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
        "memory_window_key": memory_cycle.get("window_key") or "",
        "memory_window_start_utc": memory_cycle.get("window_start_utc") or 0.0,
        "seed_cutoff_utc": memory_cycle.get("seed_cutoff_utc") or 0.0,
        "authenticated_scope": deepcopy(
            identity_scope
            or {"user_id": str(user_id), "conversation_id": conversation_id,
                "dialogue_sequence_id": str(active_sequence.get("sequence_id") or "")}
        ),
        "pre_provider_interpretation": deepcopy(metadata.get("semantic_scene_state") or {}),
    }
    state_obj["dialogue_memory_anchor"] = canonical_anchor
    state_obj["canonical_dialogue_turn"] = {
        "version": "canonical_dialogue_turn_v2_post_provider",
        "source": "POST_PROVIDER_OPENAI_RESPONSE",
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "dialogue_sequence_id": str(active_sequence.get("sequence_id") or ""),
        "task_id": str(active_sequence.get("task_id") or ""),
        "sequence_turn_index": int(active_sequence.get("turn_count") or 0),
        "task_response_number": int(active_sequence.get("task_response_count") or 0),
        "user_request": safe_trim_text(current_request_text, 1200),
        "april_answer": safe_trim_text(answer_text, 2200),
        "semantic": deepcopy(post_provider_semantics),
        "created_at": now,
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
        "memory_window_key": memory_cycle.get("window_key") or "",
    }
    state_obj["current_visual_scene"] = deepcopy(scene_record)
    state_obj["dialogue_development"] = deepcopy(dialogue_development)
    state_obj["dialogue_obligations"] = deepcopy(scene_record.get("dialogue_obligations") or state_obj.get("dialogue_obligations") or [])

    result_record = {
        "turn_id": scene_record.get("turn_id"),
        "task_id": str(active_sequence.get("task_id") or state_obj.get("active_dialogue_task_id") or ""),
        "task_response_number": int(active_sequence.get("task_response_count") or 0),
        "scene_id": scene_id,
        "flow_id": scene_record.get("flow_id"),
        "conversation_id": conversation_id,
        "sequence_id": active_sequence.get("sequence_id"),
        "topic": scene_record.get("topic"),
        "goal": state_obj.get("april_active_goal") or active_sequence.get("topic"),
        "user_request": safe_trim_text(current_request_text, 700),
        "assistant_answer": safe_trim_text(answer_text, 1200),
        "representation": block_types[0] if block_types else "text",
        "render_block_types": list(block_types),
        "result_available": bool(answer_text),
        "created_at": time.time(),
        "answer_basis": deepcopy(
            active_sequence.get("last_answer_basis")
            or _dict(active_sequence.get("active_task")).get("last_answer_basis")
            or {}
        ),
        "task_result": deepcopy(active_sequence.get("last_task_result") or {}),
    }
    # Canonical task/result ledger consumed by the next interpretation turn.
    active_ctx = state_obj.get("active_dialogue_context") if isinstance(state_obj.get("active_dialogue_context"), dict) else build_default_active_dialogue_context()
    active_task = deepcopy(
        active_sequence.get("active_task")
        or state_obj.get("active_task")
        or scene_record.get("active_task")
        or {}
    )
    task_semantic = deepcopy(semantic_scene_state if isinstance(semantic_scene_state, dict) else {})
    previous_results = list(active_ctx.get("completed_results") or [])
    if resolved_relation == "NEW":
        previous_results = []
    previous_results.append(deepcopy(result_record))
    previous_results = previous_results[-HOT_DIALOG_LIMIT:]
    state_obj["active_dialogue_context"] = {
        "version": "active_dialogue_context_v2_12h",
        "scope": {"user_id": str(user_id), "conversation_id": conversation_id},
        "sequence_id": str(active_sequence.get("sequence_id") or ""),
        "task_id": str(active_sequence.get("task_id") or active_task.get("task_id") or ""),
        "dialogue_rules": deepcopy(active_sequence.get("dialogue_rules") or active_task.get("dialogue_rules") or {}),
        "response_sequence": {
            "sequence_turn_index": int(active_sequence.get("turn_count") or 0),
            "task_response_number": int(active_task.get("response_count") or 0),
            "next_task_response_number": int(active_task.get("response_count") or 0) + 1,
        },
        "objective": safe_trim_text(
            task_semantic.get("objective")
            or active_task.get("objective")
            or (active_task.get("prompt") if active_task else "")
            or (current_request_text if resolved_relation == "NEW" else state_obj.get("active_dialogue_context", {}).get("objective", "")),
            1200,
        ),
        "task": active_task,
        "intent": safe_trim_text(task_semantic.get("intent") or task_semantic.get("operation") or "", 220),
        "goal": safe_trim_text(task_semantic.get("goal") or active_task.get("goal") or "", 320),
        "topic": safe_trim_text(scene_record.get("topic") or "", 500),
        "active_entity": safe_trim_text(task_semantic.get("entity") or contract.get("active_entity") or state_obj.get("active_entity") or "", 320),
        "completed_results": previous_results,
        "last_completed_result": deepcopy(result_record),
        "updated_at": now,
    }

    result_chain = list(state_obj.get("result_chain") or [])
    result_chain.append(result_record)
    state_obj["result_chain"] = result_chain[-12:]

    progression = list(state_obj.get("turn_progression") or [])
    progression.append({
        "turn_id": scene_record.get("turn_id"),
        "sequence_id": active_sequence.get("sequence_id"),
        "relation": resolved_relation,
        "topic": scene_record.get("topic"),
        "goal": state_obj.get("april_active_goal") or active_sequence.get("topic"),
        "result_available": bool(answer_text),
        "dialogue_development": deepcopy(dialogue_development),
    })
    state_obj["turn_progression"] = progression[-12:]

    # Canonical live dialogue scene. This is the hot conversational context and
    # exists independently of whether the turn produced a visual artifact.
    state_obj["scene_state"] = {
        **(deepcopy(state_obj.get("scene_state")) if isinstance(state_obj.get("scene_state"), dict) else {}),
        "version": "live_scene_dialogue_v2",
        "scene_id": scene_id,
        "status": "active",
        "continuity": bool(is_continuation),
        "relation": resolved_relation,
        "trajectory": scene_record.get("topic"),
        "active_topic": scene_record.get("topic"),
        "goal": active_sequence.get("topic") or scene_record.get("topic"),
        "active_goal": active_sequence.get("topic") or scene_record.get("topic"),
        "focus": current_request_text,
        "last_user_turn": current_request_text,
        "last_april_turn": answer_text,
        "previous_scene_id": previous_scene_id,
        "sequence_id": active_sequence.get("sequence_id"),
        "turn_index": active_sequence.get("turn_count", 0),
        "interactive_task_state": deepcopy(
            state_obj.get("interactive_task_state")
            or active_sequence.get("interactive_task_state")
            or {}
        ),
        "dialogue_obligations": deepcopy(state_obj.get("dialogue_obligations") or []),
        "dialogue_development": deepcopy(state_obj.get("dialogue_development") or {}),
        "updated_at": time.time(),
        "live_scene": {
            "scene_id": scene_id,
            "status": "active",
            "relation": resolved_relation,
            "topic": scene_record.get("topic"),
            "goal": active_sequence.get("topic") or scene_record.get("topic"),
            "focus": current_request_text,
            "last_user_turn": current_request_text,
            "last_april_turn": answer_text,
            "sequence_id": active_sequence.get("sequence_id"),
            "turn_index": active_sequence.get("turn_count", 0),
            "interactive_task_state": deepcopy(
                state_obj.get("interactive_task_state")
                or active_sequence.get("interactive_task_state")
                or {}
            ),
            "dialogue_development": deepcopy(state_obj.get("dialogue_development") or {}),
        },
    }
    state_obj["live_dialogue_scene"] = deepcopy(state_obj["scene_state"]["live_scene"])

    # Separate the latest dialogue turn from the latest successful visual
    # artifact. A clarification/error turn must never erase the last usable
    # graph/table/formula from the active visual memory.
    successful_visual = _scene_has_successful_visual(scene_record)
    previous_successful_visual = state_obj.get("last_successful_visual_scene")
    if successful_visual:
        state_obj["last_successful_visual_scene"] = deepcopy(scene_record)
        state_obj["last_successful_visual_scene_id"] = scene_id
        state_obj["last_successful_visual_scene_turn"] = scene_record.get("turn_id")
        state_obj["active_visual_scene"] = deepcopy(scene_record)
        active_visual_source = "current_dialogue_successful_visual"
    elif isinstance(previous_successful_visual, dict) and previous_successful_visual:
        state_obj["active_visual_scene"] = deepcopy(previous_successful_visual)
        active_visual_source = "last_successful_visual_preserved"
    else:
        # Plain dialogue is NOT a visual scene. Keep the live dialogue scene in
        # `scene_state`, and keep the visual pointer empty until a real structured
        # visual artifact exists.
        state_obj["active_visual_scene"] = None
        active_visual_source = "no_visual_scene"

    active_visual = state_obj.get("active_visual_scene")
    if isinstance(active_visual, dict) and active_visual:
        state_obj["active_visual_topic"] = {
            "topic": active_visual.get("topic") or scene_record["topic"],
            "scene_id": active_visual.get("scene_id") or scene_id,
            "conversation_id": conversation_id,
            "turn_id": active_visual.get("turn_id") or scene_record["turn_id"],
            "user_id": str(user_id),
            "source": active_visual_source,
        }
    else:
        state_obj["active_visual_topic"] = None
    state_obj["visual_memory_integrity"] = {
        "active_artifact_source": active_visual_source,
        "last_successful_scene_id": state_obj.get("last_successful_visual_scene_id"),
        "current_turn_scene_id": scene_id,
        "current_turn_has_successful_visual": bool(successful_visual),
        "preserve_on_nonvisual_turn": True,
        "updated_at": time.time(),
    }
    safe_state_log(
        "VISUAL MEMORY INTEGRITY: "
        f"active={active_visual_source} "
        f"last_successful={state_obj.get('last_successful_visual_scene_id')} "
        f"current={scene_id} "
        f"usable={bool(successful_visual)}"
    )

    # Persist every completed USER↔APRIL turn in the current 12-hour dialogue archive as one
    # compact USER↔APRIL unit. This is the durable fallback for semantic recall.
    day0 = state_obj["memory_timeline"]["day_0"]
    pairs = day0.setdefault("dialog_pairs", [])
    turn_key = f"{conversation_id}:{state_obj['visual_scene_version']}"
    if visual_generation_memory_record:
        visual_generation_memory_record["dialogue_sequence_id"] = str(
            contract.get("dialogue_sequence_id")
            or active_sequence.get("sequence_id")
            or visual_generation_memory_record.get("dialogue_sequence_id")
            or ""
        )
        visual_generation_memory_record["scene_id"] = scene_id
        visual_generation_memory_record["turn_id"] = str(
            contract.get("turn_id") or scene_id or ""
        )

    pair = {
        "record_type": "dialog_pair",
        "turn_key": turn_key,
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "user_request": safe_trim_text(current_request_text, 1200),
        "april_answer": safe_trim_text(answer_text, 2200),
        "user_meaning": safe_trim_text(current_request_text, 800),
        "april_meaning": safe_trim_text(answer_text, 1400),
        "answer_summary": safe_trim_text(contract.get("summary") or answer_text, 1000),
        "semantic_state": deepcopy(semantic_scene_state),
        "memory_semantics": deepcopy(post_provider_semantics),
        "pre_provider_interpretation": deepcopy(metadata.get("semantic_scene_state") or {}),
        "memory_source": "POST_PROVIDER_OPENAI_RESPONSE",
        "source_of_truth": "USER_REQUEST_PLUS_APRIL_ANSWER",
        "topic": post_provider_semantics.get("topic") or scene_record.get("topic") or "",
        "subtopic": post_provider_semantics.get("subtopic") or "",
        "entities": deepcopy(post_provider_semantics.get("entities") or []),
        "active_entity": post_provider_semantics.get("active_entity") or "",
        "memory_window_key": memory_cycle.get("window_key") or "",
        "memory_window_start_utc": memory_cycle.get("window_start_utc") or 0.0,
        "seed_cutoff_utc": memory_cycle.get("seed_cutoff_utc") or 0.0,
        "authenticated_scope": deepcopy(
            identity_scope
            or {"user_id": str(user_id), "conversation_id": conversation_id,
                "dialogue_sequence_id": str(active_sequence.get("sequence_id") or "")}
        ),
        "interpretation_summary": {
            "relation": resolved_relation,
            "topic": active_sequence.get("topic"),
            "operation": semantic_scene_state.get("operation") or semantic_scene_state.get("best_operation"),
            "goal": semantic_scene_state.get("goal") or semantic_scene_state.get("best_goal"),
            "representation": semantic_scene_state.get("representation") or (block_types[0] if block_types else "text"),
            "requested_outputs": deepcopy(semantic_scene_state.get("requested_outputs") or block_types),
            "render_authorized": bool(semantic_scene_state.get("render_authorized")),
            "render_mode": semantic_scene_state.get("render_mode") or "TEXT_ONLY",
            "historical_memory_is_evidence_only": True,
        },
        "dialogue_relation": resolved_relation,
        "sequence_id": active_sequence.get("sequence_id"),
        "task_id": active_sequence.get("task_id"),
        "task_response_number": int(active_sequence.get("task_response_count") or 0),
        "sequence_turn_index": active_sequence.get("turn_count", 0),
        "sequence_topic": active_sequence.get("topic"),
        "dialogue_rules": deepcopy(active_sequence.get("dialogue_rules") or {}),
        "answer_basis": deepcopy(active_sequence.get("last_answer_basis") or {}),
        "task_result": deepcopy(active_sequence.get("last_task_result") or {}),
        "selected_memory_index": selected_index,
        "selected_memory_operand": deepcopy(selected_operand),
        "development_state": deepcopy(
            state_obj.get("dialogue_development")
            or (dialogue_resolution.get("development_state") if isinstance(dialogue_resolution, dict) else {})
        ),
        "dialogue_development": deepcopy(state_obj.get("dialogue_development") or {}),
        "dialogue_obligations": deepcopy(state_obj.get("dialogue_obligations") or []),
        "visual_scene_id": scene_id,
        "scene_contract_id": scene_id,
        "visual_attachment": deepcopy(visual_attachment),
        "visual_generation_memory": deepcopy(visual_generation_memory_record)
        if visual_generation_memory_record
        else {},
        "dialogue_sequence_id": str(contract.get("dialogue_sequence_id") or active_sequence.get("sequence_id") or ""),
        "continuation": is_continuation,
        "render_block_types": list(block_types),
        "presentation_types": list(presentation_types),
        "render_signal_inventory": deepcopy(render_signal_inventory),
        "current_turn": {
            "user": safe_trim_text(current_request_text, 1200),
            "april": safe_trim_text(answer_text, 2200),
            "scene_id": scene_id,
            "relation": resolved_relation,
            "renderer_signals": deepcopy(render_signal_inventory),
            "visual_attachment": deepcopy(visual_attachment),
        },
        "created_at": now,
        "expires_after_hours": DIALOGUE_WINDOW_HOURS,
    }
    if not any(
        isinstance(item, dict)
        and item.get("user_id") == str(user_id)
        and item.get("conversation_id") == conversation_id
        and item.get("task_id") == pair.get("task_id")
        and item.get("sequence_turn_index") == pair.get("sequence_turn_index")
        and item.get("user_meaning") == pair["user_meaning"]
        and item.get("april_meaning") == pair["april_meaning"]
        for item in pairs[-HOT_DIALOG_LIMIT:]
    ):
        pairs.append(pair)
    day0["dialog_pairs"] = [
        item for item in pairs
        if isinstance(item, dict)
        and (
            not item.get("created_at")
            or (time.time() - float(item.get("created_at"))) < USER_CONTENT_RETENTION_SECONDS
        )
    ]
    _append_recall_index(state_obj, pair)

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
    if persist:
        persist_state(user_id)
    return state_obj["active_scene_contract"]

def update_dialog_context(user_id, semantic_result):
    if not isinstance(semantic_result, dict):
        return

    state_obj = get_state(user_id)
    obj = semantic_result.get("current_object")
    contract = semantic_result.get("dialogue_contract") if isinstance(
        semantic_result.get("dialogue_contract"), dict
    ) else {}
    dialogue_vector = (
        semantic_result.get("dialogue_vector")
        if isinstance(semantic_result.get("dialogue_vector"), dict)
        else {}
    )
    interactive_task_state = deepcopy(
        semantic_result.get("interactive_task_state")
        or semantic_result.get("open_task")
        or dialogue_vector.get("interactive_task_state")
        or contract.get("interactive_task_state")
        or contract.get("open_task")
        or {}
    )
    if not isinstance(interactive_task_state, dict):
        interactive_task_state = {}
    topic = (
        semantic_result.get("current_topic")
        or semantic_result.get("active_topic")
        or semantic_result.get("canonical_topic")
        or contract.get("canonical_topic")
        or contract.get("active_topic")
        or dialogue_vector.get("canonical_topic")
        or dialogue_vector.get("active_topic")
    )
    if obj:
        state_obj["current_object"] = obj
        state_obj["active_entity"] = obj
    if topic:
        state_obj["current_topic"] = topic
        state_obj["active_topic"] = topic

    raw_relation = (
        dialogue_vector.get("three_way_relation")
        or dialogue_vector.get("relation")
        or semantic_result.get("three_way_relation")
        or contract.get("three_way_relation")
        or contract.get("relation")
        or semantic_result.get("dialogue_relation")
    )
    relation = str(raw_relation or "").strip().upper()
    if relation == "RECALL":
        relation = "NEW"
    if relation not in {"CONTINUE", "NEW"}:
        # Compatibility inputs from older semantic contracts.
        if bool(contract.get("continuation", semantic_result.get("continuation", False))):
            relation = "CONTINUE"
        elif bool(contract.get("reference_to_previous", False)):
            relation = "CONTINUE"
        else:
            relation = "NEW"

    # Canonical task ownership comes from Interpretation (task_id + sequence_id),
    # not from the presence of a procedural keyword in the current sentence.
    # This compatibility path must never clear an existing task merely because
    # this turn is ordinary dialogue. The canonical result writer is the
    # StateManager sequence advance after the Provider answer.
    active_sequence = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
    validation_sequence = deepcopy(active_sequence)
    # RECALL is a retired compatibility value. It never owns routing.
    if relation == "RECALL":
        relation = "NEW"
    if relation == "NEW" and str(
        dialogue_vector.get("context_mode") or contract.get("context_mode") or semantic_result.get("context_mode") or ""
    ).upper() == "HISTORY_LOOKUP":
        state_obj["dialogue_history_lookup"] = True
    target_sequence_id = ""
    if relation == "CONTINUE":
        target_sequence_id = str(
            dialogue_vector.get("target_sequence_id")
            or contract.get("target_sequence_id")
            or semantic_result.get("target_sequence_id")
            or active_sequence.get("sequence_id")
            or ""
        ).strip()
        if target_sequence_id:
            validation_sequence["sequence_id"] = target_sequence_id

    registry = state_obj.get("dialogue_task_registry") if isinstance(state_obj.get("dialogue_task_registry"), dict) else {}
    provided_task_id = str(
        dialogue_vector.get("target_task_id")
        or dialogue_vector.get("task_id")
        or contract.get("target_task_id")
        or contract.get("task_id")
        or semantic_result.get("target_task_id")
        or semantic_result.get("task_id")
        or ""
    ).strip()

    # Prefer an explicitly selected task from Interpretation, otherwise resolve
    # the current authenticated task from the registry. Never merge tasks merely
    # because they are in the same 12-hour window.
    if not interactive_task_state and provided_task_id and isinstance(registry.get(provided_task_id), dict):
        interactive_task_state = deepcopy(registry[provided_task_id])

    if interactive_task_state:
        if provided_task_id:
            interactive_task_state["task_id"] = provided_task_id
        validated_task = QUANTUM_MEMORY_ENGINE._task_belongs_to_sequence(
            interactive_task_state, validation_sequence, now=time.time()
        )
        if validated_task:
            interactive_task_state = validated_task
            state_obj["active_dialogue_task_id"] = str(validated_task.get("task_id") or provided_task_id or "")
            state_obj["interactive_task_state"] = deepcopy(validated_task)
            state_obj["open_task"] = deepcopy(validated_task)
            state_obj["active_task"] = deepcopy(validated_task)
            if isinstance(active_sequence, dict) and active_sequence.get("sequence_id"):
                active_sequence["task_id"] = str(validated_task.get("task_id") or provided_task_id or "")
                active_sequence["active_task"] = deepcopy(validated_task)
                active_sequence["interactive_task_state"] = deepcopy(validated_task)
                active_sequence["open_task"] = deepcopy(validated_task)
                active_sequence["task_state"] = deepcopy(validated_task)
                active_sequence["task_response_count"] = int(validated_task.get("response_count") or 0)
                active_sequence["dialogue_rules"] = deepcopy(validated_task.get("dialogue_rules") or active_sequence.get("dialogue_rules") or {})
                state_obj["active_dialogue_sequence"] = active_sequence
        else:
            # Invalid/mismatched task references are ignored rather than deleting
            # the authenticated user's existing task registry.
            interactive_task_state = {}

    # If Interpretation has already resolved a NEW task but the compatibility
    # caller did not carry the full task object, preserve its task_id/sequence_id
    # as a lightweight pointer. The canonical StateManager advance will populate
    # the actual result and counters after the Provider returns.
    if relation == "NEW" and provided_task_id and not interactive_task_state:
        pointer = registry.get(provided_task_id) if isinstance(registry.get(provided_task_id), dict) else {}
        if pointer:
            interactive_task_state = deepcopy(pointer)

    memory_slider = deepcopy(
        dialogue_vector.get("memory_slider")
        or contract.get("memory_slider")
        or semantic_result.get("memory_slider")
        or {}
    )
    if not isinstance(memory_slider, dict):
        memory_slider = {}

    selected_operand = deepcopy(
        dialogue_vector.get("selected_memory_operand")
        or contract.get("selected_memory_operand")
        or semantic_result.get("selected_memory_operand")
        or memory_slider.get("selected_memory_operand")
        or {}
    )
    try:
        selected_index = int(
            dialogue_vector.get(
                "selected_memory_index",
                contract.get("selected_memory_index", semantic_result.get("selected_memory_index", -1)),
            )
        )
    except (TypeError, ValueError):
        selected_index = -1

    selected_record = deepcopy(
        semantic_result.get("selected_memory_record")
        or contract.get("selected_memory_record")
        or {}
    )
    resolved_request = str(
        contract.get("resolved_request")
        or semantic_result.get("resolved_request")
        or dialogue_vector.get("resolved_request")
        or ""
    ).strip()

    history_context = (
        contract.get("history_task_context")
        if isinstance(contract.get("history_task_context"), dict)
        else semantic_result.get("history_task_context")
        if isinstance(semantic_result.get("history_task_context"), dict)
        else {}
    )

    semantic_scene_state = semantic_result.get("semantic_scene_state")
    if not isinstance(semantic_scene_state, dict):
        semantic_scene_state = (
            contract.get("semantic_scene_state")
            if isinstance(contract.get("semantic_scene_state"), dict)
            else {}
        )

    # The development state is a persisted operand/result description. It does
    # not decide routing; it records what the semantic processor already chose.
    development_state = {
        "relation": relation,
        "active_topic": topic or semantic_result.get("active_topic"),
        "active_goal": semantic_result.get("active_goal"),
        "current_request": semantic_result.get("normalized")
        or semantic_result.get("current_request")
        or contract.get("current_request")
        or "",
        "resolved_request": resolved_request,
        "delta": deepcopy(semantic_result.get("dialogue_delta") or {}),
        "semantic_state": deepcopy(semantic_scene_state),
        "history_task_context": deepcopy(history_context),
        "previous_result": deepcopy(
            selected_operand.get("result")
            or selected_operand.get("april")
            or selected_operand.get("assistant")
            or selected_operand.get("answer")
            or ""
        ) if isinstance(selected_operand, dict) else "",
        "source_scene_id": str(
            selected_operand.get("scene_id")
            or selected_operand.get("visual_scene_id")
            or selected_operand.get("source_scene_id")
            or ""
        ) if isinstance(selected_operand, dict) else "",
        "updated_at": time.time(),
    }

    now = time.time()
    resolution = {
        "relation": relation,
        "selected_memory_index": selected_index,
        "selected_memory_operand": selected_operand,
        "selected_memory_record": selected_record,
        "memory_slider": memory_slider,
        "previous_result": {
            "user": (
                selected_operand.get("user")
                or selected_operand.get("user_meaning")
                or ""
            ) if isinstance(selected_operand, dict) else "",
            "result": (
                selected_operand.get("result")
                or selected_operand.get("april")
                or selected_operand.get("assistant")
                or selected_operand.get("answer")
                or ""
            ) if isinstance(selected_operand, dict) else "",
            "scene_id": development_state["source_scene_id"],
        },
        "development_state": development_state,
        "source_scene_id": development_state["source_scene_id"],
        "resolved_request": resolved_request,
        "context_mode": str(dialogue_vector.get("context_mode") or "NEW_TOPIC_ISOLATED"),
        "context_dependency": str(
            dialogue_vector.get("context_dependency")
            or ("continuation" if relation == "CONTINUE" else "independent")
        ),
        "history_lookup": bool(dialogue_vector.get("history_lookup")),
        "resolved_reference_entity": str(dialogue_vector.get("resolved_reference_entity") or ""),
        "confidence": float(
            dialogue_vector.get("three_way_confidence")
            or contract.get("three_way_confidence")
            or semantic_result.get("confidence")
            or 0.0
        ),
        "authoritative": True,
        "updated_at": now,
    }
    state_obj["dialogue_resolution"] = resolution
    branch_index_state = semantic_result.get("dialogue_branch_index") or dialogue_vector.get("branch_index")
    if isinstance(branch_index_state, dict) and branch_index_state:
        state_obj["dialogue_branch_index"] = {
            "version": str(branch_index_state.get("version") or "dialogue_branch_index_v1_user_bound"),
            "active_sequence_id": str(branch_index_state.get("active_sequence_id") or ""),
            "target_sequence_id": str(branch_index_state.get("target_sequence_id") or ""),
            "target_branch_id": str(branch_index_state.get("target_branch_id") or ""),
            "active_branch_id": str(state_obj.get("active_dialogue_branch_id") or ""),
            "resolution_mode": str(branch_index_state.get("resolution_mode") or "NO_BRANCH_RESOLUTION"),
            "selected_score": float(branch_index_state.get("selected_score") or 0.0),
            "branches": deepcopy(branch_index_state.get("branches") or [])[:12],
            "updated_at": now,
        }

    dialogue_state = state_obj.get("dialog_state")
    if not isinstance(dialogue_state, dict):
        dialogue_state = {}

    dialogue_state.update({
        "current_request": semantic_result.get("normalized")
        or semantic_result.get("current_request")
        or "",
        "continuation": relation == "CONTINUE",
        "reference_to_previous": relation == "CONTINUE" and selected_index >= 0,
        "context_dependency": (
            "continuation" if relation == "CONTINUE"
            else "new_with_context" if str(dialogue_vector.get("context_mode") or "") in {"NEW_TOPIC_WITH_CONTEXT", "HISTORY_LOOKUP"}
            else "independent"
        ),
        "active_topic": topic or semantic_result.get("active_topic"),
        "active_goal": semantic_result.get("active_goal"),
        "dialog_act": contract.get("dialog_act") or semantic_result.get("dialog_act"),
        "relation": relation,
        "three_way_relation": relation,
        "subtype": contract.get("subtype") or semantic_result.get("dialogue_subtype") or relation,
        "avoid_repeat": True,
        "delta": deepcopy(semantic_result.get("dialogue_delta") or {}),
        "selected_memory_index": selected_index,
        "selected_memory_operand": deepcopy(selected_operand),
        "selected_memory_record": deepcopy(selected_record),
        "memory_slider": deepcopy(memory_slider),
        "development_state": deepcopy(development_state),
        "resolved_request": resolved_request,
        "context_mode": str(dialogue_vector.get("context_mode") or "NEW_TOPIC_ISOLATED"),
        "history_lookup": bool(dialogue_vector.get("history_lookup")),
        "resolved_reference_entity": str(dialogue_vector.get("resolved_reference_entity") or ""),
        "context_pairs": deepcopy(dialogue_vector.get("selected_context_pairs") or dialogue_vector.get("context_pairs") or []),
        "interactive_task_state": deepcopy(interactive_task_state),
    })

    state_obj["dialogue_vector"] = deepcopy(dialogue_vector)
    state_obj["dialogue_vector"]["branch_index"] = deepcopy(
        semantic_result.get("dialogue_branch_index")
        or dialogue_vector.get("branch_index")
        or {}
    )
    state_obj["dialogue_vector"]["target_sequence_id"] = str(
        dialogue_vector.get("target_sequence_id")
        or contract.get("target_sequence_id")
        or ""
    )
    state_obj["dialogue_vector"]["target_branch_id"] = str(
        dialogue_vector.get("target_branch_id")
        or contract.get("target_branch_id")
        or ""
    )
    state_obj["dialogue_vector"]["target_branch"] = deepcopy(
        dialogue_vector.get("target_branch")
        or contract.get("target_branch")
        or {}
    )
    state_obj["dialogue_vector"]["turn_relation"] = str(
        dialogue_vector.get("turn_relation")
        or contract.get("turn_relation")
        or semantic_result.get("dialogue_subtype")
        or ""
    )
    state_obj["dialogue_vector"]["interactive_task_state"] = deepcopy(interactive_task_state)
    state_obj["dialogue_vector"]["open_task"] = deepcopy(interactive_task_state)
    state_obj["turn_progression"] = {
        "relation": relation,
        "subtype": dialogue_state.get("subtype"),
        "active_topic": dialogue_state.get("active_topic"),
        "active_goal": dialogue_state.get("active_goal"),
        "delta": deepcopy(dialogue_state.get("delta") or {}),
        "selected_memory_index": selected_index,
        "selected_memory_operand": deepcopy(selected_operand),
        "development_state": deepcopy(development_state),
        "interactive_task_state": deepcopy(interactive_task_state),
        "task_memory": {
            "role": interactive_task_state.get("role"),
            "phase": interactive_task_state.get("phase"),
            "last_question": interactive_task_state.get("last_question"),
            "known_clues": list(interactive_task_state.get("known_clues") or [])[-12:],
            "qa_history": list(
                interactive_task_state.get("qa_history")
                or interactive_task_state.get("turns")
                or []
            )[-12:],
            "candidate_answer": interactive_task_state.get("candidate_answer"),
        } if interactive_task_state else {},
        "avoid_repeat": True,
        "updated_at": now,
    }
    state_obj["dialog_state"] = dialogue_state

    # Semantic result is evidence entering the same memory field; the selected
    # operand is now durably anchored for the next executor/provider stage.
    QUANTUM_MEMORY_ENGINE.record_intent(state_obj, {
        "topic": topic,
        "object": obj,
        "intent": semantic_result.get("intent"),
        "context_dependency": dialogue_state["context_dependency"],
        "continuation": relation == "CONTINUE",
        "three_way_relation": relation,
        "selected_memory_index": selected_index,
        "selected_memory_operand": deepcopy(selected_operand),
        "timestamp": now,
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
        "window_hours": DIALOGUE_WINDOW_HOURS,
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
        f"window={DIALOGUE_WINDOW_HOURS}h"
    )
    return QUANTUM_MEMORY_ENGINE


initialize_state_engine()


# ============================================================================
# CANONICAL PAIR-ONLY PERSISTENCE OVERRIDE — 2026-10-04
# ============================================================================
# The historical QuantumMemoryEngine above is retained only for compatibility
# with callers that import its old helper names. Production persistence is
# deliberately narrowed here to one source of truth:
#     authenticated user -> USER↔APRIL pairs -> fixed UTC 12h window.
# No entity/topic/task/scene index is written to PostgreSQL.

CLEAN_DIALOGUE_MEMORY_VERSION = "dialogue_pairs_utc12h_v3"
CLEAN_DIALOGUE_SEQUENCE_VERSION = "utc12h_pair_sequence_v1"
CLEAN_DIALOGUE_WINDOW_PAIRS = 15


def _clean_uid(user_id: Any) -> str:
    return str(user_id or "").strip()


def _clean_pair_from_row(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    user = str(row.get("user_text") or row.get("user_request") or row.get("user_meaning") or row.get("user") or "").strip()
    april = str(row.get("april_text") or row.get("april_answer") or row.get("april_meaning") or row.get("answer") or "").strip()
    if not user or not april:
        return None
    try:
        created = float(row.get("created_at") or row.get("timestamp") or 0.0)
    except (TypeError, ValueError):
        created = 0.0
    try:
        turn = int(row.get("turn_index") or row.get("sequence_turn_index") or row.get("turn") or 0)
    except (TypeError, ValueError):
        turn = 0
    return {
        "user_text": user,
        "april_text": april,
        "created_at": created,
        "turn_index": turn,
    }


def _clean_pairs_from_state(state_obj: dict[str, Any]) -> list[dict[str, Any]]:
    timeline = state_obj.get("memory_timeline") if isinstance(state_obj.get("memory_timeline"), dict) else {}
    day = timeline.get("day_0") if isinstance(timeline.get("day_0"), dict) else {}
    source = day.get("dialog_pairs") if isinstance(day.get("dialog_pairs"), list) else []
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in source:
        pair = _clean_pair_from_row(item)
        if not pair:
            continue
        sig = (pair["turn_index"], pair["created_at"], pair["user_text"], pair["april_text"])
        if sig in seen:
            continue
        seen.add(sig)
        result.append(pair)
    result.sort(key=lambda x: (x["created_at"], x["turn_index"]))
    return result


def _clean_sequence_id(user_id: str, cycle_start_ts: float) -> str:
    raw = f"{user_id}|{int(cycle_start_ts)}|{CLEAN_DIALOGUE_SEQUENCE_VERSION}"
    return "seq-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _clean_conversation_id(user_id: str, cycle_start_ts: float) -> str:
    raw = f"{user_id}|{int(cycle_start_ts)}|conversation-v1"
    return "conv-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _clean_runtime_memory_scope(state_obj: dict[str, Any], user_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Synchronize only the pair memory view into the existing runtime state."""
    if not isinstance(state_obj, dict):
        state_obj = build_default_state()

    current_ts = time.time()
    try:
        cycle = utc_cycle_start(current_ts)
        cycle_ts = cycle.timestamp()
        seed_start, _ = dialogue_window_bounds(current_ts)
        seed_ts = seed_start.timestamp()
    except Exception:
        cycle_ts = current_ts - (current_ts % DIALOGUE_WINDOW_SECONDS)
        seed_ts = cycle_ts - DIALOGUE_SEED_SECONDS
        cycle = datetime.fromtimestamp(cycle_ts, tz=timezone.utc)

    sequence_id = _clean_sequence_id(user_id, cycle_ts)
    conversation_id = _clean_conversation_id(user_id, cycle_ts)

    timeline = state_obj.setdefault("memory_timeline", {})
    day = timeline.setdefault("day_0", build_memory_day())
    day["dialog_pairs"] = deepcopy(rows)
    # Entity/topic/intent archives are no longer memory sources.
    day["topics"] = []
    day["objects"] = []
    day["intent_signals"] = []
    for slot in TOPIC_CLASSES:
        day[slot] = []

    state_obj["memory_timeline"] = {"day_0": day}
    state_obj["user_id"] = user_id
    state_obj["conversation_id"] = conversation_id
    state_obj["current_topic"] = None
    state_obj["current_object"] = None
    state_obj["active_entity"] = None
    state_obj["april_active_topic"] = None
    state_obj["april_active_entity"] = None
    state_obj["last_entity"] = None

    last = rows[-1] if rows else None
    first_created = rows[0]["created_at"] if rows else None
    last_created = rows[-1]["created_at"] if rows else None

    # Keep one lightweight runtime sequence object. It contains no subject/entity
    # memory; the conversation meaning is reconstructed from the pair archive.
    seq = state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"), dict) else {}
    seq.update({
        "version": CLEAN_DIALOGUE_SEQUENCE_VERSION,
        "sequence_id": sequence_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "branch_id": None,
        "task_id": None,
        "topic": None,
        "entity": None,
        "active_entity": None,
        "turn_count": len(rows),
        "response_count": len(rows),
        "task_response_count": 0,
        "started_at": first_created,
        "last_turn_at": last_created,
        "last_user_request": last["user_text"] if last else "",
        "last_april_answer": last["april_text"] if last else "",
        "last_task_result": {},
        "last_answer_basis": {},
        "task_registry": {},
        "relation": "CONTINUE" if rows else "NEW",
        "dialogue_rules": deepcopy(seq.get("dialogue_rules") or {}),
    })
    state_obj["active_dialogue_sequence"] = seq

    ctx = state_obj.get("active_dialogue_context") if isinstance(state_obj.get("active_dialogue_context"), dict) else {}
    ctx.update({
        "version": "active_dialogue_context_pair_first_v1",
        "scope": {"user_id": user_id, "conversation_id": conversation_id},
        "sequence_id": sequence_id,
        "task_id": None,
        "objective": "",
        "task": {},
        "intent": "",
        "goal": "",
        "topic": "",
        "active_entity": "",
        "response_sequence": {"sequence_id": sequence_id, "sequence_turn_index": len(rows)},
        "completed_results": [],
        "last_completed_result": {},
        "updated_at": current_ts,
    })
    state_obj["active_dialogue_context"] = ctx

    state_obj["dialogue_branch_index"] = {
        "version": "dialogue_pair_history_only_v1",
        "active_sequence_id": sequence_id,
        "target_sequence_id": sequence_id,
        "target_branch_id": "",
        "resolution_mode": "PAIR_HISTORY_ONLY",
        "branches": [],
    }
    state_obj["active_dialogue_branch_id"] = ""

    state_obj["canonical_dialogue_turn"] = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "dialogue_sequence_id": sequence_id,
        "sequence_turn_index": int(last["turn_index"] if last else 0),
        "user_request": last["user_text"] if last else "",
        "april_answer": last["april_text"] if last else "",
        "created_at": last["created_at"] if last else None,
    }
    state_obj["dialogue_memory_anchor"] = {
        "version": "dialogue_pair_anchor_v1",
        "user_id": user_id,
        "conversation_id": conversation_id,
        "sequence_id": sequence_id,
        "previous_user_turn": last["user_text"] if last else "",
        "previous_april_turn": last["april_text"] if last else "",
        "turn_index": int(last["turn_index"] if last else 0),
        "created_at": last["created_at"] if last else None,
    }
    state_obj["memory_cycle"] = {
        "anchor_mode": "FIXED_UTC_12H",
        "session_start_utc": cycle_ts,
        "window_key": cycle.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_start_utc": cycle_ts,
        "seed_cutoff_utc": seed_ts,
        "last_rollover": cycle_ts,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "seed_hours": DIALOGUE_SEED_HOURS,
        "authenticated_only": True,
        "source": "dialogue_memory",
    }
    state_obj["memory_version"] = CLEAN_DIALOGUE_MEMORY_VERSION
    state_obj["memory_summary"] = ""
    state_obj["memory_matrix"] = {}
    state_obj["dialogue_resolution"] = {
        "relation": "CONTINUE" if rows else "NEW",
        "selected_memory_index": -1,
        "selected_memory_operand": {},
        "selected_memory_record": {},
        "previous_result": {},
        "development_state": {},
        "source_scene_id": "",
        "resolved_request": "",
        "confidence": 0.0,
        "authoritative": True,
        "memory_source": "USER_APRIL_PAIRS",
        "updated_at": current_ts,
    }
    state_obj["last_user_turn"] = last["user_text"] if last else ""
    state_obj["last_user_turn_at"] = last["created_at"] if last else None
    state_obj["last_april_turn"] = last["april_text"] if last else ""
    state_obj["last_april_turn_at"] = last["created_at"] if last else None
    return state_obj


def _clean_load_authenticated_state(user_id: Any) -> dict[str, Any]:
    uid = _clean_uid(user_id)
    base = state.get(uid) if uid else None
    if not isinstance(base, dict):
        base = build_default_state()

    auth_ok = bool(is_authenticated_user(uid)) if callable(is_authenticated_user) and uid else False
    if not auth_ok:
        # Anonymous/unregistered state is explicitly ephemeral and contains no DB
        # dialogue memory.
        base = _clean_runtime_memory_scope(base, uid, [])
        base["memory_scope"] = {
            "user_id": uid,
            "authenticated": False,
            "persistence": "disabled",
            "source": "auth_required",
        }
        state[uid] = base
        return base

    try:
        cleanup_dialogue_memory_utc(uid)
    except Exception as exc:
        safe_state_log(f"UTC PAIR CLEANUP READ ERROR: {exc}")

    try:
        rows = load_dialogue_pairs(uid, limit=0)
    except Exception as exc:
        safe_state_log(f"PAIR LOAD ERROR: {exc}")
        rows = []
    rows = [p for p in (_clean_pair_from_row(x) for x in rows) if p]
    base = _clean_runtime_memory_scope(base, uid, rows)
    base["memory_scope"] = {
        "user_id": uid,
        "authenticated": True,
        "persistence": "dialogue_memory",
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "seed_hours": DIALOGUE_SEED_HOURS,
        "source": "POSTGRES_DIALOGUE_MEMORY_PAIRS",
    }
    state[uid] = base
    return base


# Replace the old DB-backed full-state loader.
def get_state(user_id):
    with _state_lock:
        return _clean_load_authenticated_state(user_id)


# The old state snapshot writer is intentionally disabled. Pair writes are made
# only at the completed USER↔APRIL commit point in update_scene_context().
def persist_state(user_id):
    try:
        cleanup_dialogue_memory_utc(str(user_id))
    except Exception as exc:
        safe_state_log(f"PERSIST CLEANUP ERROR: {exc}")
    return None


def persist_state_background(user_id):
    """Compatibility API: persist only the canonical pair store, never the state JSON."""
    try:
        cleanup_dialogue_memory_utc(str(user_id))
    except Exception as exc:
        safe_state_log(f"BACKGROUND PAIR CLEANUP ERROR: {exc}")
    return None


def invalidate_user_memory_cache(user_id):
    """Invalidate only the in-process authenticated memory snapshot.

    PostgreSQL ``dialogue_memory`` is the durable source of truth. This helper
    exists for the user-registry route so account creation/login cannot leave a
    stale anonymous runtime snapshot attached to the same public April ID. It
    never deletes dialogue rows and never changes the 12h UTC retention policy.
    """
    uid = _clean_uid(user_id)
    if not uid:
        return False
    with _state_lock:
        removed = state.pop(uid, None)
    safe_state_log(f"MEMORY CACHE INVALIDATED user={uid} removed={bool(removed)}")
    return bool(removed)


def add_dialog(user_id, role, content, metadata=None, *, persist=True):
    """Runtime conversation buffer only. Database writes happen once per completed pair."""
    uid = _clean_uid(user_id)
    state_obj = get_state(uid)
    role_name = str(role or "").strip().lower()
    text = str(content or "").strip()
    if text:
        item = {
            "role": role_name,
            "content": text,
            "timestamp": time.time(),
            "metadata": deepcopy(metadata or {}),
        }
        dialog = state_obj.setdefault("dialog", [])
        dialog.append(item)
        state_obj["dialog"] = dialog[-60:]
        state_obj["meta"] = state_obj.get("meta") if isinstance(state_obj.get("meta"), dict) else {}
        if role_name in {"user", "human"}:
            state_obj["last_user_turn"] = text
            state_obj["last_user_turn_at"] = item["timestamp"]
        elif role_name in {"assistant", "april", "bot"}:
            state_obj["last_april_turn"] = text
            state_obj["last_april_turn_at"] = item["timestamp"]
    return state_obj


_ORIGINAL_UPDATE_SCENE_CONTEXT_PAIR_MEMORY = update_scene_context


def update_scene_context(
    user_id,
    contract,
    *,
    current_request=None,
    answer=None,
    provider_result=None,
    visual_generation_memory=None,
    internal_context=False,
    persist=True,
):
    """Preserve the existing scene pipeline but commit only a compact pair to DB."""
    result = _ORIGINAL_UPDATE_SCENE_CONTEXT_PAIR_MEMORY(
        user_id,
        contract,
        current_request=current_request,
        answer=answer,
        provider_result=provider_result,
        visual_generation_memory=visual_generation_memory,
        internal_context=bool(internal_context),
        persist=False,
    )
    if not internal_context:
        uid = _clean_uid(user_id)
        request_text = str(current_request or "").strip()
        answer_text = str(answer or "").strip()
        auth_ok = bool(is_authenticated_user(uid)) if callable(is_authenticated_user) and uid else False
        if auth_ok and request_text and answer_text:
            current_rows = []
            try:
                current_rows = load_dialogue_pairs(uid, limit=0)
            except Exception:
                current_rows = []
            clean_rows = [p for p in (_clean_pair_from_row(x) for x in current_rows) if p]
            turn_index = (max((int(p.get("turn_index") or 0) for p in clean_rows), default=0) + 1)
            try:
                save_dialogue_pair(
                    uid,
                    request_text,
                    answer_text,
                    created_at=time.time(),
                    turn_index=turn_index,
                )
                clean_rows = [p for p in (_clean_pair_from_row(x) for x in load_dialogue_pairs(uid, limit=0)) if p]
                with _state_lock:
                    _clean_runtime_memory_scope(state.get(uid) if isinstance(state.get(uid), dict) else build_default_state(), uid, clean_rows)
                    state[uid]["dialog"] = state[uid].get("dialog", [])[-60:]
            except Exception as exc:
                safe_state_log(f"PAIR PERSIST ERROR: {exc}")
    if persist:
        persist_state(user_id)
    return result


def _clean_sequence_pairs_from_runtime(state_obj: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _clean_pairs_from_state(state_obj)
    rows.sort(key=lambda x: (float(x.get("created_at") or 0.0), int(x.get("turn_index") or 0)))
    return rows


# Pair-only replacement for the old rich memory query engine.
def _clean_engine_ensure_runtime(self, state_obj):
    uid = _clean_uid((state_obj or {}).get("user_id")) if isinstance(state_obj, dict) else ""
    if uid and callable(is_authenticated_user) and is_authenticated_user(uid):
        try:
            cleanup_dialogue_memory_utc(uid)
            rows = load_dialogue_pairs(uid, limit=0)
        except Exception:
            rows = []
        rows = [p for p in (_clean_pair_from_row(x) for x in rows) if p]
        return _clean_runtime_memory_scope(state_obj if isinstance(state_obj, dict) else build_default_state(), uid, rows)
    return _clean_runtime_memory_scope(state_obj if isinstance(state_obj, dict) else build_default_state(), uid, [])


QuantumMemoryEngine.ensure_runtime = _clean_engine_ensure_runtime


def _clean_engine_iter_memory_records(self, state_obj):
    for row in _clean_sequence_pairs_from_runtime(state_obj):
        yield {
            "record_type": "dialog_pair",
            "user": row["user_text"],
            "april": row["april_text"],
            "created_at": row["created_at"],
            "turn_index": row["turn_index"],
        }


def _clean_engine_query(self, state_obj, query, *, limit=8, retrieval_mode="semantic"):
    pairs = _clean_sequence_pairs_from_runtime(state_obj)
    q = str(query or "").strip().lower()
    if not q:
        selected = pairs[-max(1, int(limit or 8)):]
    else:
        scored = []
        for row in pairs:
            hay = f"{row['user_text']} {row['april_text']}".lower()
            exact = fuzz.token_set_ratio(q, hay) / 100.0 if q else 0.0
            partial = fuzz.partial_ratio(q, hay) / 100.0 if q else 0.0
            recency = max(0.0, 1.0 - max(0.0, time.time() - float(row['created_at'] or 0.0)) / DIALOGUE_WINDOW_SECONDS)
            score = exact * 0.68 + partial * 0.22 + recency * 0.10
            scored.append((score, row))
        scored.sort(key=lambda x: (x[0], float(x[1].get("created_at") or 0.0)), reverse=True)
        selected = [r for _s, r in scored[:max(1, int(limit or 8))]]
    return {
        "engine": "dialogue_pairs_v1",
        "mode": "pair_search",
        "query": query,
        "total_pairs": len(pairs),
        "records": [
            {
                "score": 1.0,
                "turn_index": int(r["turn_index"]),
                "created_at": float(r["created_at"]),
                "user": r["user_text"],
                "april": r["april_text"],
            }
            for r in selected
        ],
        "topic_index": [],
        "entity_index": [],
        "authenticated_only": True,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "seed_hours": DIALOGUE_SEED_HOURS,
    }


def _clean_engine_build_memory_matrix(self, state_obj, query="", limit=8):
    result = _clean_engine_query(self, state_obj, query, limit=limit, retrieval_mode="semantic")
    return {
        "engine": "dialogue_pairs_v1",
        "query": query,
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "records": result.get("records", []),
        "labels": [],
        "entities": [],
        "topics": [],
        "mode": "pair_history_only",
        "evidence_only": True,
    }


QuantumMemoryEngine.iter_memory_records = _clean_engine_iter_memory_records
QuantumMemoryEngine.query = _clean_engine_query
QuantumMemoryEngine.build_memory_matrix = _clean_engine_build_memory_matrix


# ============================================================================
# PAIR-ONLY DIALOGUE BRIDGE / HISTORY SEARCH API
# ============================================================================

def build_dialogue_memory_bridge(
    user_id,
    query="",
    limit=CLEAN_DIALOGUE_WINDOW_PAIRS,
    *,
    relation="AUTO",
    target_sequence_id="",
    target_task_id="",
):
    """Return only the authenticated 12h USER↔APRIL pair window.

    Interpretation decides NEW/CONTINUE/RECALL. This bridge never performs a
    second fuzzy selector and never builds entity/topic indexes.
    """
    uid=_clean_uid(user_id)
    state_obj=get_state(uid)
    scope=state_obj.get("memory_scope") if isinstance(state_obj,dict) and isinstance(state_obj.get("memory_scope"),dict) else {}
    authenticated=bool(scope.get("authenticated") or scope.get("user_id"))
    if not authenticated:
        return {"version":"dialogue_pairs_v2","authenticated":False,"relation":"NEW","window_hours":DIALOGUE_WINDOW_HOURS,"selected_records":[],"dialogue_pairs":[],"memory_search":[]}
    rows=_clean_sequence_pairs_from_runtime(state_obj)
    rows=rows[-max(1,int(limit or CLEAN_DIALOGUE_WINDOW_PAIRS)):]
    def compact(row):
        return {"turn":int(row.get("turn_index") or 0),"created_at":float(row.get("created_at") or 0.0),"user":str(row.get("user_text") or ""),"april":str(row.get("april_text") or "")}
    records=[compact(x) for x in rows]
    seq=state_obj.get("active_dialogue_sequence") if isinstance(state_obj.get("active_dialogue_sequence"),dict) else {}
    mode=str(relation or "AUTO").upper()
    if mode=="AUTO": mode=str((state_obj.get("dialogue_resolution") or {}).get("relation") or ("CONTINUE" if records else "NEW")).upper()
    if mode == "RECALL": mode="NEW"
    if mode not in {"NEW","CONTINUE"}: mode="NEW"
    return {
        "version":"dialogue_pairs_v2",
        "authenticated":True,
        "relation":mode,
        "window_hours":DIALOGUE_WINDOW_HOURS,
        "seed_hours":DIALOGUE_SEED_HOURS,
        "sequence_id":_clean_text_bridge(target_sequence_id or seq.get("sequence_id"),100),
        "selected_sequence_id":_clean_text_bridge(target_sequence_id or seq.get("sequence_id"),100),
        "current_turn_count":len(records),
        "active_sequence_turns":records,
        "relevant_window_turns":records,
        "dialogue_pairs":records,
        "selected_records":records,
        "memory_search":[],
        "history_source":"USER_APRIL_PAIRS",
        "authenticated_only":True,
        "pair_interpretation_authority":"INTERPRETATION",
    }

def _clean_text_bridge(value: Any, limit: int = 120) -> str:
    value = str(value or "").strip()
    return value[:limit]


# ============================================================================
# UTC ROLLOVER — fixed half-day boundary, retain one-hour seed
# ============================================================================

def memory_rollover_if_needed(user_id):
    uid = _clean_uid(user_id)
    try:
        removed = cleanup_dialogue_memory_utc(uid) if callable(cleanup_dialogue_memory_utc) else 0
        if removed:
            safe_state_log(f"UTC ROLLOVER CLEANUP user={uid} removed={removed}")
    except Exception as exc:
        safe_state_log(f"UTC ROLLOVER ERROR: {exc}")
    get_state(uid)
    return state.get(uid, {})


def ensure_memory_engine(state_obj):
    return _clean_engine_ensure_runtime(QUANTUM_MEMORY_ENGINE, state_obj)


def query_dynamic_memory(user_id, query, limit=8, retrieval_mode="semantic"):
    uid = _clean_uid(user_id)
    if not callable(is_authenticated_user) or not is_authenticated_user(uid):
        return {
            "engine": "dialogue_pairs_v1",
            "authenticated": False,
            "query": query,
            "records": [],
            "matches": [],
            "topic_index": [],
            "entity_index": [],
        }
    return search_dialogue_memory(uid, query, limit=limit)


def build_quantum_memory_matrix(user_id, query="", limit=8):
    result = query_dynamic_memory(user_id, query, limit=limit)
    return {
        "engine": "dialogue_pairs_v1",
        "query": query,
        "records": result.get("matches") or result.get("records") or [],
        "topics": [],
        "entities": [],
        "labels": [],
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "mode": "pair_history_only",
        "evidence_only": True,
    }


def build_quantum_memory_signal(user_id, query="", limit=8):
    result = query_dynamic_memory(user_id, query, limit=limit)
    return {
        "engine": "dialogue_pairs_v1",
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "seed_hours": DIALOGUE_SEED_HOURS,
        "signal": result,
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
        "memory_source": "USER_APRIL_PAIRS",
    }


# ============================================================================
# CANONICAL 12H PAIR MEMORY / ENTITY ROUTING REMOVAL
# ============================================================================

def _purge_entity_routing_fields(obj):
    """Remove legacy fuzzy routing indexes without deleting semantic pair metadata.

    active_entity/entities/resolved_entity are useful semantic evidence inside an
    authenticated USER↔APRIL pair (for pronoun resolution). The deprecated entity
    index/engine is disabled, but the pair's resolved subject remains durable.
    """
    if not isinstance(obj, dict):
        return obj
    for key in list(obj.keys()):
        low = str(key).lower()
        if low in {"entity_index"}:
            obj.pop(key, None)
            continue
        value = obj.get(key)
        if isinstance(value, dict):
            _purge_entity_routing_fields(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _purge_entity_routing_fields(item)
    return obj

_STATE_GET_STATE_ORIGINAL = get_state

def get_state(user_id):
    obj=_STATE_GET_STATE_ORIGINAL(user_id)
    uid=str(user_id or "")
    scope=obj.get("memory_scope") if isinstance(obj,dict) and isinstance(obj.get("memory_scope"),dict) else {}
    authenticated=bool(scope.get("authenticated") or scope.get("user_id"))
    if authenticated and uid:
        timeline=obj.get("memory_timeline") if isinstance(obj.get("memory_timeline"),dict) else {}
        pair_count=sum(len(day.get("dialog_pairs") or []) for day in timeline.values() if isinstance(day,dict) and isinstance(day.get("dialog_pairs"),list))
        if pair_count == 0:
            try:
                rows=load_dialogue_pairs(uid, limit=0)
            except Exception:
                rows=[]
            if rows:
                try:
                    clean=[p for p in (_clean_pair_from_row(x) for x in rows) if p]
                    obj=_clean_runtime_memory_scope(obj, uid, clean)
                except Exception:
                    pass
    _purge_entity_routing_fields(obj)
    return obj

# Replace public pair bridge with a pure 12h pair window: no fuzzy entity/topic index.
_BUILD_DIALOGUE_MEMORY_BRIDGE_ORIGINAL = build_dialogue_memory_bridge

def build_dialogue_memory_bridge(*args, **kwargs):
    result=_BUILD_DIALOGUE_MEMORY_BRIDGE_ORIGINAL(*args, **kwargs)
    if not isinstance(result,dict): return result
    if str(result.get("relation") or "").upper() == "RECALL":
        result["relation"] = "NEW"
    result.pop("entity_index",None)
    result.pop("topic_index",None)
    result.pop("task_index",None)
    result["history_source"]="USER_APRIL_PAIRS"
    result["window_hours"]=DIALOGUE_WINDOW_HOURS
    result["authenticated_only"]=True
    # CONTINUE/NEW are interpreted from the supplied full pair window; the bridge
    # never selects a historical branch and exposes only live authenticated pairs.
    rows=result.get("dialogue_pairs") or result.get("active_sequence_turns") or result.get("relevant_window_turns") or []
    result["dialogue_pairs"]=rows[-ACTIVE_DIALOGUE_WINDOW_PAIRS:]
    result["selected_records"]=result["dialogue_pairs"]
    result["memory_search"]=[]
    result["pair_interpretation_authority"]="INTERPRETATION"
    return result
