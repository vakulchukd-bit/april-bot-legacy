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
MEMORY_DAYS = 7
TOPIC_CLASSES = ["A", "B", "C", "D", "E"]

SESSION_MEMORY_LIMIT = 1600
VISUAL_HISTORY_LIMIT = 8
IMAGE_MEMORY_LIMIT = 5
TOPIC_MEMORY_LIMIT = 5

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


def get_dialog_limit(user_id, plan):
    if user_id == ADMIN_ID:
        return 50
    return {"free": 10, "lite": 20, "premium": 30}.get(plan, 10)


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
        "memory_version": "QUANTUM-7D-V1",
        "active_scene_contract": {},
        "current_scene_request": "",
        "visual_summary": {},
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

    VERSION = "QUANTUM-MEMORY-7D-V1"

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

    # ---------- seven-day cycle ----------

    def rollover(self, state_obj):
        self.ensure(state_obj)
        today = utc_day_key()
        cycle = state_obj["memory_cycle"]
        previous = cycle.get("last_day_key")

        if previous == today:
            return False

        # Preserve a maximum seven-day window. If the process was offline for
        # several days, advance only as many slots as elapsed, capped at 7.
        shift = 1
        try:
            old_date = datetime.strptime(str(previous), "%Y-%m-%d").date()
            new_date = datetime.strptime(today, "%Y-%m-%d").date()
            shift = max(1, min(MEMORY_DAYS, (new_date - old_date).days))
        except Exception:
            shift = 1

        timeline = state_obj["memory_timeline"]
        for _ in range(shift):
            for i in range(MEMORY_DAYS - 1, 0, -1):
                timeline[f"day_{i}"] = timeline[f"day_{i-1}"]
            timeline["day_0"] = build_memory_day()

        state_obj["memory_cycle"] = {
            "last_day_key": today,
            "last_rollover": time.time(),
        }
        safe_state_log("MEMORY_WINDOW_ROLLED: 7D")
        return True

    def ensure_runtime(self, state_obj):
        self.ensure(state_obj)
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
        q = safe_trim_text(query, 1600)
        c = safe_trim_text(candidate, 1600)
        if not q or not c:
            return 0.0

        encoder = self._get_encoder()
        vectors = encoder.encode([q, c], normalize_embeddings=True)
        return max(0.0, min(1.0, (self._cosine(vectors[0], vectors[1]) + 1.0) / 2.0))

    def semantic_scores(self, query, candidates):
        """Batch semantic comparison through the shared interpretation encoder."""
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
            record.get("goal"),
            record.get("object"),
        ]
        scene = record.get("scene")
        if isinstance(scene, dict):
            parts.extend([
                scene.get("scene_type"),
                scene.get("topic"),
                scene.get("goal"),
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

            for item in day.get("intent_signals", []):
                if isinstance(item, dict):
                    yield {
                        **item,
                        "memory_kind": "intent",
                        "day_index": age,
                    }

    def query(self, state_obj, query, *, limit=8):
        """
        Produce memory evidence. It never selects a route or renderer.
        """
        self.ensure_runtime(state_obj)
        query = str(query or "").strip()

        if not query:
            return {
                "engine": self.VERSION,
                "window_days": MEMORY_DAYS,
                "matches": [],
                "active_scene": state_obj.get("active_scene", {}),
                "active_visual_scene": state_obj.get("active_visual_scene"),
                "decision_owner": "QUANTUM_PROCESSOR",
                "evidence_only": True,
            }

        focus = state_obj.get("focus_state", {})
        active_topic = focus.get("active_topic") or state_obj.get("current_topic")
        active_scene = focus.get("active_scene") or state_obj.get("active_visual_scene")
        current_visual = state_obj.get("active_visual_scene")

        candidates = list(self.iter_memory_records(state_obj))
        ranked = []

        candidate_texts = []
        candidate_records = []
        for record in candidates:
            candidate_text = self._record_text(record)
            if candidate_text:
                candidate_texts.append(candidate_text)
                candidate_records.append(record)

        semantic_map = self.semantic_scores(query, candidate_texts)

        for record, candidate_text in zip(candidate_records, candidate_texts):
            semantic = float(semantic_map.get(candidate_text, 0.0))
            recency = max(0.0, 1.0 - (record.get("day_index", 0) / MEMORY_DAYS))

            relation = 0.0
            if active_topic and str(active_topic).lower() in candidate_text.lower():
                relation += 0.15

            if active_scene:
                scene_text = self._record_text(
                    active_scene if isinstance(active_scene, dict) else {"text": active_scene}
                )
                if scene_text:
                    relation += 0.20 * self.semantic_score(query, scene_text)

            score = min(1.0, (semantic * 0.65) + (recency * 0.20) + relation)
            if score >= 0.30:
                ranked.append((score, record))

        ranked.sort(key=lambda x: x[0], reverse=True)
        matches = []
        for score, record in ranked[: max(1, int(limit))]:
            matches.append({
                "score": round(score, 6),
                "day_index": record.get("day_index", 0),
                "memory_kind": record.get("memory_kind"),
                "slot": record.get("slot"),
                "topic": record.get("topic"),
                "summary": safe_trim_text(
                    record.get("summary") or record.get("text") or self._record_text(record),
                    600,
                ),
                "scene": record.get("scene"),
                "visual": record.get("scene") if record.get("memory_kind") == "visual_scene" else None,
                "timestamp": record.get("timestamp"),
            })

        # Explicit active scene evidence is kept separate from historical
        # matches so the processor can distinguish "continue" from "recall".
        active_scene_text = self._record_text(
            active_scene if isinstance(active_scene, dict) else {"text": active_scene}
        )
        active_similarity = (
            self.semantic_score(query, active_scene_text)
            if active_scene_text
            else 0.0
        )

        return {
            "engine": self.VERSION,
            "window_days": MEMORY_DAYS,
            "matches": matches,
            "active_scene_similarity": round(active_similarity, 6),
            "active_visual_scene": current_visual,
            "focus_state": deepcopy(focus),
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
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
        self.ensure_runtime(state_obj)
        if not isinstance(scene_payload, dict):
            return

        record = deepcopy(scene_payload)
        record.setdefault("timestamp", time.time())
        record.setdefault("memory_kind", "visual_scene")

        state_obj["memory_timeline"]["day_0"]["visual_scenes"].append(record)
        state_obj["active_visual_scene"] = record
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
            "visual_summary": deepcopy(state_obj.get("visual_summary", {})),
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


def compress_dialog_to_summary(state_obj):
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
    }

    state_obj["memory_summary"] = str(machine_summary)[-SESSION_MEMORY_LIMIT:]
    state_obj["dialog"] = [{"role": "system", "content": "[COMPRESSED_MEMORY]"}]


def trim_image_memory(state_obj):
    memory = safe_list(state_obj.get("image_memory"))
    state_obj["image_memory"] = memory[-IMAGE_MEMORY_LIMIT:]


def trim_visual_history(state_obj):
    history = safe_list(state_obj.get("visual_scene_history"))
    state_obj["visual_scene_history"] = history[-VISUAL_HISTORY_LIMIT:]


def add_dialog(user_id, role, content):
    state_obj = get_state(user_id)
    dialog = safe_list(state_obj.get("dialog"))

    dialog.append(compact_dialog_message(role, content))
    state_obj["dialog"] = dialog

    if role == "user":
        state_obj["last_user_turn"] = safe_trim_text(content, 320)
        state_obj["meta"]["last_user_message"] = safe_trim_text(content, 320)
    else:
        state_obj["last_april_turn"] = safe_trim_text(content, 320)
        state_obj["meta"]["last_bot_message"] = safe_trim_text(content, 320)

    state_obj["dialog_state"] = {
        "timeline": deepcopy(dialog),
        "last_user_turn": state_obj.get("last_user_turn", ""),
        "last_april_turn": state_obj.get("last_april_turn", ""),
        "active_topic": state_obj.get("current_topic"),
        "focus": deepcopy(state_obj.get("focus_state", {})),
    }

    plan = get_user_plan(user_id) if callable(get_user_plan) else "free"
    limit = get_dialog_limit(user_id, plan)
    if len(dialog) > limit:
        compress_dialog_to_summary(state_obj)
        state_obj["dialog_state"]["timeline"] = deepcopy(state_obj["dialog"])

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


def bind_current_visual_scene(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    visual = state_obj.get("active_visual_scene")
    if visual:
        QUANTUM_MEMORY_ENGINE.record_visual_scene(state_obj, visual)
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

    scene = state_obj.get("active_visual_scene") or {}
    scene["events_count"] = visual_summary.get("scene_events_count", 0)
    scene["last_event"] = visual_summary.get("last_event")
    scene["package"] = visual_summary.get("package", "free")
    scene["session_started_utc"] = visual_summary.get("session_started_utc")
    QUANTUM_MEMORY_ENGINE.record_visual_scene(state_obj, scene)

    state_obj["active_scene"] = QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)
    return scene


def build_visual_memory_bridge(user_id):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    return {
        "user_visual_scene": deepcopy(state_obj.get("active_visual_scene", {})),
        "visual_summary": deepcopy(state_obj.get("visual_summary", {})),
        "today_visual_memory": deepcopy(
            state_obj["memory_timeline"]["day_0"].get("visual_scenes", [])
        ),
        "memory_engine": QUANTUM_MEMORY_ENGINE.VERSION,
        "window_days": MEMORY_DAYS,
    }


def update_scene_context(user_id, scene_contract, current_request="", answer=""):
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    contract = scene_contract if isinstance(scene_contract, dict) else {}

    if not contract and hasattr(scene_contract, "__dict__"):
        contract = dict(scene_contract.__dict__)

    render_blocks = contract.get("render_blocks") or contract.get("blocks") or []
    block_types = []
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

    state_obj["active_scene_contract"] = {
        "scene_version": str(contract.get("scene_version") or ""),
        "active_scene": str(contract.get("active_scene") or ""),
        "space_continuity": deepcopy(contract.get("space_continuity") or {}),
        "metadata": deepcopy(contract.get("metadata") or {}),
        "supported_payloads": deepcopy(contract.get("supported_payloads") or []),
        "render_block_types": block_types,
        "current_request": str(current_request or "").strip(),
        "answer": str(answer or "").strip()[:4000],
        "scene_id": str(contract.get("scene_id") or ""),
    }
    state_obj["current_scene_request"] = str(current_request or "").strip()
    state_obj["last_april_turn"] = str(answer or "").strip()[:4000]

    # A scene contract is itself a memory record. This keeps the actual
    # rendered scene and the remembered scene in the same memory field.
    scene_record = {
        "scene_id": state_obj["active_scene_contract"]["scene_id"],
        "scene_type": state_obj["active_scene_contract"]["active_scene"],
        "summary": state_obj["active_scene_contract"]["answer"],
        "current_request": state_obj["active_scene_contract"]["current_request"],
        "render_block_types": block_types,
        "timestamp": time.time(),
    }
    QUANTUM_MEMORY_ENGINE.record_visual_scene(state_obj, scene_record)
    QUANTUM_MEMORY_ENGINE.refresh_scene(state_obj)
    persist_state(user_id)
    return state_obj["active_scene_contract"]


def update_dialog_context(user_id, semantic_result):
    if not isinstance(semantic_result, dict):
        return

    state_obj = get_state(user_id)
    obj = semantic_result.get("current_object")
    topic = semantic_result.get("current_topic")

    if obj:
        state_obj["current_object"] = obj
        state_obj["active_entity"] = obj
    if topic:
        state_obj["current_topic"] = topic

    # Semantic result is evidence entering the same memory field; it is not a
    # second memory system.
    QUANTUM_MEMORY_ENGINE.record_intent(state_obj, {
        "topic": topic,
        "object": obj,
        "intent": semantic_result.get("intent"),
        "timestamp": time.time(),
    })
    persist_state(user_id)


# =====================================================
# DIRECT QUANTUM MEMORY QUERY API
# =====================================================

def query_dynamic_memory(user_id, query, limit=8):
    """
    Return semantic memory evidence for the existing Quantum Processor.
    No route/renderer decision is made here.
    """
    state_obj = QUANTUM_MEMORY_ENGINE.ensure_runtime(get_state(user_id))
    result = QUANTUM_MEMORY_ENGINE.query(state_obj, query, limit=limit)
    return result


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
