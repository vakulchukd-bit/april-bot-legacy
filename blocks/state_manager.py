# blocks/state_manager.py

# =====================================================
# 🧠 APRIL STATE MANAGER
# =====================================================

"""
APRIL STATE MANAGER

ROLE:
- continuity-safe runtime storage
- lightweight dialog memory
- visual scene persistence
- renderer continuity support
- active flow stabilization
- dynamic memory hierarchy
- focus persistence
- open-loop tracking
- trajectory memory core

SYSTEM DOES NOT:
- perform orchestration
- mutate cognition
- own routing authority
- generate renderer payloads
- execute provider logic
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

import time
import math
from datetime import datetime, timezone

from sentence_transformers import SentenceTransformer, util

try:
    from storage import get_user_plan, load_memory, save_memory
    _STORAGE_IMPORT_ERROR = None
except Exception as exc:
    get_user_plan = None
    load_memory = None
    save_memory = None
    _STORAGE_IMPORT_ERROR = exc

# =====================================================
# 🔥 MACHINE IDENTITY
# =====================================================

APRIL_FILE_ID = "APRIL_STATE_MANAGER"

STATE_MACHINE_CHANNEL = {

    "type": "state_runtime",

    "mode": "machine_memory",

    "isolated": True,

    "renderer_safe": True,

    "web_safe": True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

STATE_PATCH_LOG = []

def safe_state_log(msg):
    try:
        print("STATE:", msg)
    except Exception:
        pass

safe_state_log("STATE MANAGER INITIALIZED")

# =====================================================
# 🔥 RUNTIME STATE
# =====================================================

state = {}

# =====================================================
# 🔥 STABLE IMAGE STORAGE
# =====================================================

image_storage = {}

# =====================================================
# 🔥 ADMIN
# =====================================================

ADMIN_ID = 2016592532

# =====================================================
# 🔥 LIMITS
# =====================================================

SESSION_MEMORY_LIMIT = 1600

VISUAL_HISTORY_LIMIT = 8

IMAGE_MEMORY_LIMIT = 5

TOPIC_MEMORY_LIMIT = 5

# =====================================================
# 🔥 DIALOG LIMITS
# =====================================================

def get_dialog_limit(
    user_id,
    plan
):

    if user_id == ADMIN_ID:

        return 50

    return {

        "free": 10,

        "lite": 20,

        "premium": 30

    }.get(plan, 10)

# =====================================================
# 🔥 SAFE HELPERS
# =====================================================

def safe_trim_text(
    text,
    limit=120
):

    text = str(
        text or ""
    ).strip()

    if len(text) <= limit:

        return text

    return text[:limit]


def safe_list(value):

    if isinstance(
        value,
        list
    ):

        return value

    return []


def compact_dialog_message(
    role,
    content
):

    return {

        "role": role,

        "content":

            safe_trim_text(
                content,
                320
            )
    }


# =====================================================
# 🧠 QUANTUM MEMORY ENGINE V1
# =====================================================

# The memory room owns memory measurement only.
# It does not orchestrate, route, render or call providers.
# Seven days are a fixed rolling window: day_0 ... day_6.
# Older state is discarded on rollover instead of creating day_7/day_8.

MEMORY_DAYS = 7
MEMORY_DAY_KEYS = tuple(f"day_{i}" for i in range(MEMORY_DAYS))
MEMORY_VECTOR_MODEL_NAME = os.getenv(
    "APRIL_MEMORY_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

class QuantumMemoryEngine:
    """
    Dynamic semantic memory engine.

    Measurements:
      recency + semantic similarity + topic/goal/scene continuity +
      visual relationship + memory-type relevance.

    The result is an evidence packet for Quantum Processor.
    """

    def __init__(self, model_name=MEMORY_VECTOR_MODEL_NAME):
        self.model_name = model_name
        self._encoder = None
        self._cache = {}

    def _model(self):
        if self._encoder is None:
            self._encoder = SentenceTransformer(self.model_name)
        return self._encoder

    def _embed(self, text):
        value = safe_trim_text(text, 4000)
        if not value:
            return None
        key = value
        if key not in self._cache:
            self._cache[key] = self._model().encode(
                value,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        return self._cache[key]

    @staticmethod
    def _cosine(a, b):
        if a is None or b is None:
            return 0.0
        score = float(util.cos_sim(a, b).item())
        return max(0.0, min(1.0, (score + 1.0) / 2.0))

    @staticmethod
    def _recency(timestamp, now=None):
        if not timestamp:
            return 0.0
        now = now or time.time()
        age_days = max(0.0, (now - float(timestamp)) / 86400.0)
        return math.exp(-0.55 * age_days)

    def score_record(self, query, record, current_topic="", current_goal="", current_scene=""):
        record_text = record.get("text") or record.get("summary") or record.get("topic") or ""
        semantic = self._cosine(self._embed(query), self._embed(record_text))

        topic = self._cosine(
            self._embed(current_topic),
            self._embed(record.get("topic", "")),
        ) if current_topic and record.get("topic") else 0.0

        goal = self._cosine(
            self._embed(current_goal),
            self._embed(record.get("goal", "")),
        ) if current_goal and record.get("goal") else 0.0

        scene = self._cosine(
            self._embed(current_scene),
            self._embed(
                record.get("scene_type", "")
                or record.get("scene", "")
                or record.get("summary", "")
            ),
        ) if current_scene and (
            record.get("scene_type") or record.get("scene") or record.get("summary")
        ) else 0.0

        visual = 1.0 if (
            record.get("visual")
            or record.get("visual_scene")
            or record.get("visual_summary")
        ) else 0.0

        recency = self._recency(record.get("timestamp"))

        total = (
            0.45 * semantic +
            0.18 * topic +
            0.12 * goal +
            0.12 * scene +
            0.05 * visual +
            0.08 * recency
        )

        return {
            "score": round(max(0.0, min(1.0, total)), 6),
            "semantic": round(semantic, 6),
            "topic": round(topic, 6),
            "goal": round(goal, 6),
            "scene": round(scene, 6),
            "visual": round(visual, 6),
            "recency": round(recency, 6),
        }

    def retrieve(self, query, timeline, current_topic="", current_goal="", current_scene="", top_k=6):
        records = []
        for day_index in range(MEMORY_DAYS):
            day = timeline.get(f"day_{day_index}", {})
            if not isinstance(day, dict):
                continue

            for slot in ("A", "B", "C", "D", "E"):
                for item in day.get(slot, []) if isinstance(day.get(slot, []), list) else []:
                    if isinstance(item, dict):
                        record = dict(item)
                        record["memory_day"] = day_index
                        record["memory_slot"] = slot
                        records.append(record)

            for item in day.get("visual_scenes", []) if isinstance(day.get("visual_scenes", []), list) else []:
                if isinstance(item, dict):
                    record = dict(item)
                    record["memory_day"] = day_index
                    record["memory_slot"] = "visual"
                    record["visual"] = True
                    records.append(record)

        ranked = []
        for record in records:
            metrics = self.score_record(
                query,
                record,
                current_topic=current_topic,
                current_goal=current_goal,
                current_scene=current_scene,
            )
            ranked.append({**record, "quantum_memory_score": metrics})

        ranked.sort(
            key=lambda item: item["quantum_memory_score"]["score"],
            reverse=True,
        )

        return ranked[:max(1, int(top_k))]

    def build_signal(self, query, timeline, current_topic="", current_goal="", current_scene="", top_k=6):
        matches = self.retrieve(
            query,
            timeline,
            current_topic=current_topic,
            current_goal=current_goal,
            current_scene=current_scene,
            top_k=top_k,
        )

        strongest = matches[0] if matches else {}
        strongest_score = (
            strongest.get("quantum_memory_score", {}).get("score", 0.0)
            if strongest else 0.0
        )

        return {
            "engine": "quantum_memory_engine_v1",
            "window_days": MEMORY_DAYS,
            "day_keys": list(MEMORY_DAY_KEYS),
            "query": safe_trim_text(query, 1000),
            "matches": matches,
            "strongest_match": strongest,
            "strongest_score": strongest_score,
            "continuation_candidate": bool(strongest and strongest_score >= 0.60),
            "historical_reference_candidate": bool(strongest and strongest_score >= 0.72),
            "visual_continuation_candidate": bool(
                strongest and
                strongest_score >= 0.65 and
                strongest.get("visual")
            ),
            "decision_owner": "QUANTUM_PROCESSOR",
            "evidence_only": True,
        }

    def clear_runtime_cache(self):
        self._cache.clear()


QUANTUM_MEMORY_ENGINE = QuantumMemoryEngine()


# =====================================================
# 🔥 DEFAULT SCENE
# =====================================================

def build_default_scene():

    return {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "mode": "idle",

        "type": None,

        "goal": None,

        "continuity_mode": None,

        # =================================================
        # 🔥 RENDER
        # =====================================================

        "render_type": None,

        "renderer_active": False,

        "visual_active": False,

        # =================================================
        # 🔥 FLOW
        # =====================================================

        "active_flow": None,

        "trajectory_locked": False,

        # =================================================
        # 🔥 ANCHOR
        # =====================================================

        "anchor": None,

        "anchor_type": None,

        # =================================================
        # 🔥 STATE
        # =====================================================

        "confidence": 0.0,

        "updated_at": time.time()
    }

# =====================================================
# 🔥 DEFAULT STATE
# =====================================================

def build_default_state():

    return {

        # =================================================
        # 🔥 DIALOG
        # =====================================================

        "dialog": [],

        "memory_summary": "",

        "active_scene": {},
        "scene_history": [],
        "scene_stack": [],
        "scene_relation": {},

        # =================================================
        # 🔥 GOLDEN MEMORY
        # =====================================================

        "dynamic_focus": {},

        "goal_hierarchy": {},

        "open_loops": [],

        "memory_signals": {},

        # =================================================
        # 🔥 IMAGE
        # =====================================================

        "image_context": None,

        "image_memory": [],

        # =================================================
        # 🔥 VISUAL
        # =====================================================

        "active_visual_scene": None,

        "visual_scene_history": [],
        
        "visual_topic_registry": [],
        
        "task_context_storage": [],
        
        "continuity_context_storage": [],
        
        "memory_anchor_storage": [],
        
        "active_topic_slot": "A",

        # =================================================
        # 🔥 FLOW
        # =====================================================

        "active_flow": None,

        # =================================================
        # 🔥 EXECUTION
        # =====================================================

        "awaiting": False,

        "last_prompt": None,

        "task_type": None,

        # =================================================
        # 🔥 SCENE
        # =====================================================

        "scene_state":
            build_default_scene(),

        # =================================================
        # 🔥 CACHE
        # =====================================================

        "image_analysis": None,

        "image_analysis_path": None,

        # =================================================
        # 🔥 META
        # =====================================================

        "meta": {

            "last_user_message": None,

            "last_bot_message": None,

            "last_entity": None,

            "last_intent": None
        },

        "current_object": None,
        "current_topic": None,
        "active_entity": None,

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "machine_runtime": True,

        "renderer_safe": True,

        "continuity_alive": True,

        "web_safe": True
    }

# =====================================================
# 🔥 SCENE STATE
# =====================================================

def get_scene_state(user_id):

    return get_state(user_id).get(
        "scene_state",
        {}
    )


def update_scene_state(
    user_id,
    updates
):

    if not isinstance(
        updates,
        dict
    ):

        return

    state_obj = get_state(user_id)

    scene = state_obj.get(
        "scene_state",
        {}
    )

    allowed_keys = [

        "mode",
        "type",
        "goal",
        "continuity_mode",
        "render_type",
        "renderer_active",
        "visual_active",
        "active_flow",
        "trajectory_locked",
        "anchor",
        "anchor_type",
        "confidence",
        "updated_at"
    ]

    for key, value in updates.items():

        if key in allowed_keys:

            scene[key] = value

    scene["updated_at"] = time.time()

    state_obj[
        "scene_state"
    ] = scene

    safe_state_log(
        f"SCENE UPDATED: {user_id}"
    )

    persist_state(user_id)


def clear_scene_state(user_id):

    state_obj = get_state(user_id)

    visual_scene = state_obj.get(
        "active_visual_scene"
    )

    new_scene = build_default_scene()

    # =================================================
    # 🔥 VISUAL CONTINUITY
    # =====================================================

    if visual_scene:

        new_scene[
            "visual_active"
        ] = True

        new_scene[
            "continuity_mode"
        ] = "visual"

    state_obj[
        "scene_state"
    ] = new_scene

    safe_state_log(
        f"SCENE CLEARED: {user_id}"
    )

    persist_state(user_id)

# =====================================================
# 🔥 IMAGE CONTEXT
# =====================================================

def set_image_context(
    user_id,
    ctx
):

    image_storage[user_id] = ctx

    state_obj = get_state(user_id)

    state_obj[
        "image_context"
    ] = ctx

    # =================================================
    # 🔥 SCENE SYNC
    # =====================================================

    scene = state_obj.get(
        "scene_state",
        {}
    )

    scene[
        "visual_active"
    ] = True

    scene[
        "continuity_mode"
    ] = "visual"

    scene[
        "updated_at"
    ] = time.time()

    state_obj[
        "scene_state"
    ] = scene

    safe_state_log(
        f"IMAGE CONTEXT: {user_id}"
    )

    persist_state(user_id)


def get_image_context(user_id):

    ctx = image_storage.get(
        user_id
    )

    if ctx:

        return ctx

    return get_state(user_id).get(
        "image_context"
    )

# =====================================================
# 🔥 AWAITING
# =====================================================

def set_awaiting(
    user_id,
    value
):

    get_state(user_id)[
        "awaiting"
    ] = value


def get_awaiting(user_id):

    return get_state(user_id).get(
        "awaiting",
        False
    )

# =====================================================
# 🔥 LAST PROMPT
# =====================================================

def set_last_prompt(
    user_id,
    prompt
):

    get_state(user_id)[
        "last_prompt"
    ] = prompt


def get_last_prompt(user_id):

    return get_state(user_id).get(
        "last_prompt"
    )

# =====================================================
# 🔥 MEMORY SUMMARY
# =====================================================

def update_memory_summary(
    state_obj,
    user_text="",
    assistant_text=""
):

    try:

        current = state_obj.get(
            "memory_summary",
            ""
        )

        entry = " | ".join(

            x for x in [

                safe_trim_text(
                    user_text,
                    240
                ),

                safe_trim_text(
                    assistant_text,
                    240
                )

            ]

            if x
        )

        combined = (
            current + " | " + entry
        ).strip()

        if len(combined) > SESSION_MEMORY_LIMIT:

            combined = combined[
                -SESSION_MEMORY_LIMIT:
            ]

        state_obj[
            "memory_summary"
        ] = combined

    except Exception as e:

        safe_state_log(
            f"MEMORY ERROR: {e}"
        )

# =====================================================
# 🔥 VISUAL SUMMARY
# =====================================================

def build_visual_scene_summary(
    state_obj
):

    scene = state_obj.get(
        "active_visual_scene"
    )

    if not scene:

        return {}

    return {

        "type":

            scene.get(
                "scene_type"
            ),

        "objects":

            safe_list(

                scene.get(
                    "objects",
                    []
                )
            )[:5],

        "colors":

            safe_list(

                scene.get(
                    "colors",
                    []
                )
            )[:5]
    }

# =====================================================
# 🔥 DIALOG COMPRESSION
# =====================================================

def compress_dialog_to_summary(
    state_obj
):

    dialog = state_obj.get(
        "dialog",
        []
    )

    if not dialog:

        return

    recent = dialog[-8:]

    compact_dialog = []

    for msg in recent:

        compact_dialog.append({

            "role":
                msg.get("role"),

            "content":

                safe_trim_text(
                    msg.get(
                        "content",
                        ""
                    ),
                    180
                )
        })

    scene = state_obj.get(
        "scene_state",
        {}
    )

    visual = build_visual_scene_summary(
        state_obj
    )

    # =================================================
    # 🔥 MACHINE SUMMARY
    # =====================================================

    machine_summary = {

        "scene": {

            "type":
                scene.get("type"),

            "goal":
                scene.get("goal"),

            "flow":
                scene.get(
                    "active_flow"
                ),

            "continuity":
                scene.get(
                    "continuity_mode"
                ),

            "render":
                scene.get(
                    "render_type"
                )
        },

        "visual":
            visual,

        "dialog":
            compact_dialog
    }

    state_obj[
        "memory_summary"
    ] = str(
        machine_summary
    )[
        -SESSION_MEMORY_LIMIT:
    ]

    # =================================================
    # 🔥 SAFE DIALOG RESET
    # =====================================================

    state_obj["dialog"] = [{

        "role": "system",

        "content": "[COMPRESSED_MEMORY]"
    }]

    safe_state_log(
        "DIALOG COMPRESSED"
    )

# =====================================================
# 🔥 IMAGE MEMORY
# =====================================================

def trim_image_memory(
    state_obj
):

    memory = safe_list(

        state_obj.get(
            "image_memory",
            []
        )
    )

    if len(memory) > IMAGE_MEMORY_LIMIT:

        state_obj[
            "image_memory"
        ] = memory[
            -IMAGE_MEMORY_LIMIT:
        ]

# =====================================================
# 🔥 VISUAL HISTORY
# =====================================================

def trim_visual_history(
    state_obj
):

    history = safe_list(

        state_obj.get(
            "visual_scene_history",
            []
        )
    )

    if len(history) > VISUAL_HISTORY_LIMIT:

        state_obj[
            "visual_scene_history"
        ] = history[
            -VISUAL_HISTORY_LIMIT:
        ]

# =====================================================
# 🔥 DIALOG
# =====================================================

def add_dialog(
    user_id,
    role,
    content
):

    state_obj = get_state(user_id)

    dialog = state_obj.get(
        "dialog",
        []
    )

    message = compact_dialog_message(
        role,
        content
    )
    dialog.append(message)

    # Keep canonical dialog continuity mirrors available to the executor.
    state_obj["dialog"] = dialog
    state_obj["last_user_turn"] = (
        safe_trim_text(content, 320) if role == "user" else state_obj.get("last_user_turn", "")
    )
    state_obj["last_april_turn"] = (
        safe_trim_text(content, 320) if role != "user" else state_obj.get("last_april_turn", "")
    )
    state_obj["dialog_state"] = {
        "timeline": dialog,
        "last_user_turn": state_obj.get("last_user_turn", ""),
        "last_april_turn": state_obj.get("last_april_turn", ""),
        "active_topic": state_obj.get("active_topic", ""),
        "focus": state_obj.get("focus_state", state_obj.get("dynamic_focus", {})),
    }

    # =================================================
    # 🔥 META
    # =====================================================

    meta = state_obj.get(
        "meta",
        {}
    )

    if role == "user":

        meta[
            "last_user_message"
        ] = safe_trim_text(
            content,
            320
        )

    else:

        meta[
            "last_bot_message"
        ] = safe_trim_text(
            content,
            320
        )

    state_obj["meta"] = meta

    # =================================================
    # 🔥 LIMIT
    # =====================================================

    plan = get_user_plan(
        user_id
    )

    limit = get_dialog_limit(
        user_id,
        plan
    )

    if len(dialog) > limit:

        compress_dialog_to_summary(
            state_obj
        )

        # Compression is a memory operation, not a loss of canonical
        # continuity. Keep the compacted timeline mirrored in dialog_state so
        # the next Executor pass can still recover the conversation.
        state_obj["dialog_state"] = {
            "timeline": state_obj.get("dialog", []),
            "last_user_turn": state_obj.get("last_user_turn", ""),
            "last_april_turn": state_obj.get("last_april_turn", ""),
            "active_topic": state_obj.get("active_topic", ""),
            "focus": state_obj.get(
                "focus_state",
                state_obj.get("dynamic_focus", {}),
            ),
        }

    trim_image_memory(
        state_obj
    )

    trim_visual_history(
        state_obj
    )
    
    trim_topic_memory(
        state_obj
    )

    state_obj["active_scene"] = refresh_unified_scene(user_id)

    persist_state(user_id) 

# =====================================================
# 🔥 DIALOG STATE
# =====================================================

def get_dialog_state(user_id):

    return get_state(user_id).get(
        "dialog_state",
        {}
    )


def set_dialog_state(
    user_id,
    data
):

    get_state(user_id)[
        "dialog_state"
    ] = data

# =====================================================
# 🔥 ACTIVE FLOW
# =====================================================

def set_active_flow(
    user_id,
    flow
):

    state_obj = get_state(user_id)

    state_obj[
        "active_flow"
    ] = flow

    scene = state_obj.get(
        "scene_state",
        {}
    )

    if isinstance(flow, dict):

        flow_type = flow.get(
            "type"
        )

        scene[
            "active_flow"
        ] = flow_type

        scene[
            "trajectory_locked"
        ] = True

        scene[
            "goal"
        ] = safe_trim_text(

            flow.get(
                "original"
            ),

            240
        )

        # =================================================
        # 🔥 RENDER MODE
        # =====================================================

        if flow_type in [

            "renderer_space",
            "graph",
            "formula",
            "diagram",
            "table"
        ]:

            scene[
                "renderer_active"
            ] = True

            scene[
                "render_type"
            ] = flow_type

            scene[
                "continuity_mode"
            ] = "renderer"

        # =================================================
        # 🔥 VISUAL MODE
        # =====================================================

        if flow_type in [

            "image",
            "image_generate",
            "image_edit"
        ]:

            scene[
                "visual_active"
            ] = True

            scene[
                "continuity_mode"
            ] = "visual"

    scene["updated_at"] = time.time()

    state_obj[
        "scene_state"
    ] = scene

    safe_state_log(
        f"FLOW SET: {user_id}"
    )

    persist_state(user_id)


def get_active_flow(user_id):

    return get_state(user_id).get(
        "active_flow"
    )


def clear_active_flow(user_id):

    state_obj = get_state(user_id)

    visual = state_obj.get(
        "active_visual_scene"
    )

    state_obj[
        "active_flow"
    ] = None

    scene = state_obj.get(
        "scene_state",
        {}
    )

    scene[
        "active_flow"
    ] = None

    scene[
        "trajectory_locked"
    ] = False

    # =================================================
    # 🔥 SAFE VISUAL
    # =====================================================

    if visual:

        scene[
            "visual_active"
        ] = True

        scene[
            "continuity_mode"
        ] = "visual"

    scene["updated_at"] = time.time()

    state_obj[
        "scene_state"
    ] = scene

    safe_state_log(
        f"FLOW CLEARED: {user_id}"
    )

    persist_state(user_id)

# =====================================================
# 🔥 ENTITY
# =====================================================

def set_last_entity(
    user_id,
    entity
):

    state_obj = get_state(user_id)

    meta = state_obj.get(
        "meta",
        {}
    )

    meta[
        "last_entity"
    ] = entity

    state_obj[
        "meta"
    ] = meta


def get_last_entity(user_id):

    return get_state(user_id).get(
        "meta",
        {}
    ).get(
        "last_entity"
    )


# =====================================================
# 🔥 GET STATE — CANONICAL SINGLE DEFINITION
# =====================================================

def get_state(user_id):
    """Return one canonical per-user runtime state."""
    key = str(user_id)

    if key not in state:
        db_state = None
        try:
            if callable(load_memory):
                db_state = load_memory(key)
        except Exception as exc:
            safe_state_log(f"STATE LOAD SKIPPED: {exc}")

        if isinstance(db_state, dict):
            state[key] = db_state
            safe_state_log(f"STATE RESTORED: {key}")
        else:
            state[key] = build_default_state()
            safe_state_log(f"NEW STATE: {key}")

    state_obj = state[key]
    defaults = build_default_state()
    for name, value in defaults.items():
        if name not in state_obj:
            if isinstance(value, dict):
                state_obj[name] = value.copy()
            elif isinstance(value, list):
                state_obj[name] = list(value)
            else:
                state_obj[name] = value

    if not isinstance(state_obj.get("scene_state"), dict):
        state_obj["scene_state"] = build_default_scene()

    return state_obj

# =====================================================
# 🔥 PERSISTENT MEMORY BRIDGE
# =====================================================


_PERSISTENCE_EXCLUDED_KEYS = {
    "_machine_context",
    "_executor_context_packet",
    "_quantum_evidence_field",
    "_quantum_processor_context",
}


def _persistable_snapshot(value, _active=None):
    """Detach runtime graphs and remove ephemeral Quantum Processor objects."""
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
                if key in _PERSISTENCE_EXCLUDED_KEYS:
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

    # Runtime objects do not belong in durable user memory.
    return str(value)


def persist_state(user_id):
    try:
        state_obj = get_state(user_id)
        persistable = _persistable_snapshot(state_obj)
        if callable(save_memory):
            save_memory(user_id, persistable)
    except Exception as e:
        safe_state_log(f"PERSIST ERROR: {e}")


# Call persist_state(user_id) after:
# add_dialog()
# set_image_context()
# update_scene_state()
# clear_scene_state()
# set_active_flow()
# clear_active_flow()




# =====================================================
# 🧠 ACTIVE SCENE ENGINE (LEGACY - DeepHub Pass)
# =====================================================

def build_active_scene(user_id):

    state_obj = get_state(user_id)

    return {

        "dialog_summary":
            state_obj.get("memory_summary", ""),

        "visual_context":
            state_obj.get("visual_continuity_summary", {}),

        "active_visual_scene":
            state_obj.get("active_visual_scene"),

        "active_flow":
            state_obj.get("active_flow"),

        "scene_state":
            state_obj.get("scene_state", {}),

        "focus_snapshot":
            state_obj.get("focus_snapshot", {}),

        "goal_hierarchy":
            state_obj.get("goal_hierarchy", {}),

        "dynamic_focus":
            state_obj.get("dynamic_focus", {})
    }

def refresh_active_scene(user_id):

    state_obj = get_state(user_id)

    state_obj["active_scene"] = (
        build_active_scene(user_id)
    )

    return state_obj["active_scene"]


# =====================================================
# 🧠 MEMORY ENGINE HELPERS (LEGACY - DeepHub Pass)
# =====================================================

MEMORY_ENGINE_VERSION = "2.0"

def get_active_focus(user_id):
    state_obj = get_state(user_id)
    focus = state_obj.get("dynamic_focus", {})

    if not isinstance(focus, dict):
        return {}

    return focus

def build_memory_snapshot(user_id):
    state_obj = get_state(user_id)

    return {
        "memory_version": MEMORY_ENGINE_VERSION,
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {}),
        "active_flow": state_obj.get("active_flow"),
        "scene_state": state_obj.get("scene_state", {})
    }

def cleanup_closed_loops(user_id):
    state_obj = get_state(user_id)

    loops = state_obj.get("open_loops", [])

    if not isinstance(loops, list):
        loops = []

    state_obj["open_loops"] = [
        loop for loop in loops
        if not (
            isinstance(loop, dict)
            and loop.get("status") == "closed"
        )
    ]
    

# =====================================================
# 🧠 GOLDEN MEMORY LAYER
# =====================================================

def build_golden_memory_state():
    return {
        "dynamic_focus": {},
        "goal_hierarchy": {},
        "open_loops": [],
        "memory_signals": {}
    }

def update_dynamic_focus(user_id, focus_payload):
    state_obj = get_state(user_id)
    state_obj["dynamic_focus"] = focus_payload or {}
    persist_state(user_id)

def update_goal_hierarchy(user_id, goal_payload):
    state_obj = get_state(user_id)
    state_obj["goal_hierarchy"] = goal_payload or {}
    persist_state(user_id)

def update_open_loops(user_id, loops_payload):
    state_obj = get_state(user_id)
    state_obj["open_loops"] = loops_payload or []
    persist_state(user_id)

def update_memory_signals(user_id, signals_payload):
    state_obj = get_state(user_id)
    state_obj["memory_signals"] = signals_payload or {}
    persist_state(user_id)

def build_memory_bridge(user_id):
    state_obj = get_state(user_id)
    return {
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {})
    }


# =====================================================
# 🧠 DYNAMIC MEMORY FOCUS UPGRADE (COMPATIBILITY LAYER)
# =====================================================

def update_focus_snapshot(
    user_id,
    abcde_payload
):

    state_obj = get_state(user_id)

    state_obj["focus_snapshot"] = {

        "topic":
            abcde_payload.get("topic"),

        "scene":
            abcde_payload.get("scene"),

        "object":
            abcde_payload.get("object"),

        "focus":
            abcde_payload.get("focus"),

        "intent":
            abcde_payload.get("intent")
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
            "intent": focus_state.get("intent_freshness")
        }

    return state_obj.get("focus_snapshot", {})


def build_context_memory_bridge(user_id):

    state_obj = get_state(user_id)

    return {

        "dynamic_focus":
            state_obj.get("dynamic_focus", {}),

        "focus_snapshot":
            state_obj.get("focus_snapshot", {}),

        "goal_hierarchy":
            state_obj.get("goal_hierarchy", {}),

        "memory_signals":
            state_obj.get("memory_signals", {}),

        "active_flow":
            state_obj.get("active_flow")
    }
    
# =====================================================
# 🧠 TOPIC MEMORY TRIMMER
# =====================================================

def trim_topic_memory(state_obj):

    for key in [

        "visual_topic_registry",

        "task_context_storage",

        "continuity_context_storage",

        "memory_anchor_storage"

    ]:

        value = state_obj.get(
            key,
            []
        )

        if isinstance(
            value,
            list
        ):

            state_obj[key] = value[
                -TOPIC_MEMORY_LIMIT:
            ]


# =====================================================
# 🧠 SCENE MEMORY API
# =====================================================

def update_scene_relation(user_id, relation):
    get_state(user_id)["scene_relation"] = relation or {}

def push_scene_history(user_id, scene):
    state_obj = get_state(user_id)
    history = state_obj.get("scene_history", [])
    history.append(scene)
    state_obj["scene_history"] = history[-20:]


# =====================================================
# 🧠 UNIFIED SCENE STORAGE
# =====================================================

def refresh_unified_scene(user_id):
    state_obj = get_state(user_id)

    state_obj["active_scene"] = {
        "scene_state": state_obj.get("scene_state", {}),
        "focus_state": state_obj.get("focus_state", {}),
        "memory_timeline": state_obj.get("memory_timeline", {}),
        "memory_cycle": state_obj.get("memory_cycle", {}),
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {}),
        "active_flow": state_obj.get("active_flow"),
        "active_visual_scene": state_obj.get("active_visual_scene", {}),
        "visual_summary": state_obj.get("visual_summary", {}),
        "today_visual_memory": state_obj.get(
            "memory_timeline", {}
        ).get("day_0", {}).get("visual_scenes", [])
    }

    return state_obj["active_scene"]



# =====================================================
# 🧠 APRIL MEMORY ENGINE V4
# =====================================================

TOPIC_CLASSES = ["A", "B", "C", "D", "E"]

def utc_day_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        "created_at": time.time()
    }

def build_memory_timeline():
    return {key: build_memory_day() for key in MEMORY_DAY_KEYS}

def ensure_memory_engine(state_obj):

    if "memory_timeline" not in state_obj:
        state_obj["memory_timeline"] = build_memory_timeline()
    else:
        timeline = state_obj["memory_timeline"]
        for key in MEMORY_DAY_KEYS:
            if key not in timeline or not isinstance(timeline[key], dict):
                timeline[key] = build_memory_day()
        # Hard-delete any accidental day_7+ keys so the seven-day contract
        # remains canonical.
        for key in list(timeline):
            if key not in MEMORY_DAY_KEYS:
                del timeline[key]

    if "memory_cycle" not in state_obj:
        state_obj["memory_cycle"] = {
            "last_day_key": utc_day_key(),
            "last_rollover": time.time()
        }

    if "focus_state" not in state_obj:
        state_obj["focus_state"] = {
            "active_topic": None,
            "active_scene": None,
            "active_object": None,
            "active_goal": None,
            "priority_score": 0.0,
            "intent_freshness": 0.0
        }

def memory_rollover_if_needed(user_id):

    state_obj = get_state(user_id)
    ensure_memory_engine(state_obj)

    today = utc_day_key()
    cycle = state_obj["memory_cycle"]
    last_day = cycle.get("last_day_key") or today

    if last_day == today:
        return False

    # Rotate exactly once per elapsed UTC day, capped to the seven-day window.
    try:
        last_date = datetime.strptime(last_day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        today_date = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        elapsed_days = max(1, (today_date - last_date).days)
    except Exception:
        elapsed_days = 1

    elapsed_days = min(elapsed_days, MEMORY_DAYS)

    timeline = state_obj["memory_timeline"]
    for _ in range(elapsed_days):
        for i in range(MEMORY_DAYS - 1, 0, -1):
            timeline[f"day_{i}"] = timeline.get(f"day_{i-1}", build_memory_day())
        timeline["day_0"] = build_memory_day()

    for key in list(timeline):
        if key not in MEMORY_DAY_KEYS:
            del timeline[key]

    state_obj["memory_cycle"] = {
        "last_day_key": today,
        "last_rollover": time.time()
    }

    safe_state_log(f"MEMORY_DAY_SHIFT: {user_id} elapsed={elapsed_days}")
    persist_state(user_id)
    return True

def update_focus_state(user_id, payload):

    state_obj = get_state(user_id)
    ensure_memory_engine(state_obj)
    payload = payload if isinstance(payload, dict) else {}

    state_obj["focus_state"] = {
        "active_topic": payload.get("topic"),
        "active_scene": payload.get("scene"),
        "active_object": payload.get("object"),
        "active_goal": payload.get("goal"),
        "priority_score": payload.get("priority_score", 0.0),
        "intent_freshness": payload.get("intent_freshness", 0.0)
    }
    persist_state(user_id)

def register_topic(user_id, topic, slot="A", score=1.0, goal=None, scene=None):

    state_obj = get_state(user_id)
    ensure_memory_engine(state_obj)

    slot = slot if slot in TOPIC_CLASSES else "C"

    timeline = state_obj["memory_timeline"]
    today = timeline["day_0"]

    topic_text = safe_trim_text(topic, 1000)
    today[slot].append({
        "topic": topic_text,
        "text": topic_text,
        "score": float(score),
        "goal": safe_trim_text(goal, 600),
        "scene": safe_trim_text(scene, 600),
        "timestamp": time.time(),
    })
    today[slot] = today[slot][-TOPIC_MEMORY_LIMIT:]

def bind_visual_scene_to_memory(user_id, scene_payload):

    state_obj = get_state(user_id)
    ensure_memory_engine(state_obj)

    payload = scene_payload if isinstance(scene_payload, dict) else {}
    record = dict(payload)
    record.setdefault(
        "text",
        safe_trim_text(
            record.get("summary")
            or record.get("scene_type")
            or record.get("topic")
            or "",
            2000,
        ),
    )
    record.setdefault("timestamp", time.time())
    record["visual"] = True

    today = state_obj["memory_timeline"]["day_0"]["visual_scenes"]
    today.append(record)
    state_obj["memory_timeline"]["day_0"]["visual_scenes"] = today[-VISUAL_HISTORY_LIMIT:]

def build_memory_context(user_id, query=None):

    state_obj = ensure_memory_runtime(user_id)

    context = {
        "focus_state": state_obj.get("focus_state", {}),
        "memory_timeline": state_obj.get("memory_timeline", {}),
        "memory_cycle": state_obj.get("memory_cycle", {}),
        "open_loops": state_obj.get("open_loops", []),
        "active_flow": state_obj.get("active_flow"),
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "memory_signals": state_obj.get("memory_signals", {}),
        "window_days": MEMORY_DAYS,
        "day_keys": list(MEMORY_DAY_KEYS),
    }

    if query:
        focus = state_obj.get("focus_state", {})
        context["quantum_memory_signal"] = QUANTUM_MEMORY_ENGINE.build_signal(
            query=query,
            timeline=state_obj.get("memory_timeline", {}),
            current_topic=focus.get("active_topic") or state_obj.get("current_topic") or "",
            current_goal=focus.get("active_goal") or "",
            current_scene=focus.get("active_scene") or "",
        )

    return context

def build_executor_memory_bridge(user_id, query=None):

    memory = build_memory_context(user_id, query=query)
    focus = memory.get("focus_state", {})
    signal = memory.get("quantum_memory_signal", {})

    return {
        "active_topic": focus.get("active_topic"),
        "active_goal": focus.get("active_goal"),
        "priority_score": focus.get("priority_score"),
        "intent_freshness": focus.get("intent_freshness"),
        "today": memory.get("memory_timeline", {}).get("day_0", {}),
        "yesterday": memory.get("memory_timeline", {}).get("day_1", {}),
        "open_loops": memory.get("open_loops", []),
        "quantum_memory": signal,
        "memory_window_days": MEMORY_DAYS,
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
    }


# =====================================================
# 🧠 QUANTUM MEMORY QUERY / SCENE RESOLUTION
# =====================================================

def query_dynamic_memory(user_id, query, top_k=6):
    state_obj = ensure_memory_runtime(user_id)
    focus = state_obj.get("focus_state", {})

    return QUANTUM_MEMORY_ENGINE.build_signal(
        query=query,
        timeline=state_obj.get("memory_timeline", {}),
        current_topic=focus.get("active_topic") or state_obj.get("current_topic") or "",
        current_goal=focus.get("active_goal") or "",
        current_scene=focus.get("active_scene") or "",
        top_k=top_k,
    )


def resolve_memory_scene(user_id, current_request, similarity_threshold=0.65):
    """
    Resolve whether the current request continues the live visual scene,
    references a prior seven-day scene, or is an independent topic.

    No renderer is selected here.
    """
    state_obj = ensure_memory_runtime(user_id)
    focus = state_obj.get("focus_state", {})
    active_visual = state_obj.get("active_visual_scene") or {}

    active_record = dict(active_visual) if isinstance(active_visual, dict) else {}
    if active_record:
        active_record.setdefault(
            "text",
            active_record.get("summary")
            or active_record.get("scene_type")
            or state_obj.get("current_topic")
            or "",
        )
        active_record["visual"] = True
        active_record.setdefault("timestamp", time.time())

    candidates = []
    if active_record.get("text"):
        metrics = QUANTUM_MEMORY_ENGINE.score_record(
            current_request,
            active_record,
            current_topic=focus.get("active_topic") or state_obj.get("current_topic") or "",
            current_goal=focus.get("active_goal") or "",
            current_scene=focus.get("active_scene") or "",
        )
        candidates.append({
            **active_record,
            "source": "active_scene",
            "quantum_memory_score": metrics,
        })

    signal = query_dynamic_memory(user_id, current_request, top_k=6)
    candidates.extend(signal.get("matches", []))

    ranked = sorted(
        candidates,
        key=lambda item: item.get("quantum_memory_score", {}).get("score", 0.0),
        reverse=True,
    )

    best = ranked[0] if ranked else {}
    best_score = best.get("quantum_memory_score", {}).get("score", 0.0) if best else 0.0

    if not best:
        relation = "independent"
    elif best.get("source") == "active_scene" and best_score >= similarity_threshold:
        relation = "continue_active_scene"
    elif best_score >= 0.72:
        relation = "historical_scene_reference"
    else:
        relation = "independent"

    return {
        "engine": "quantum_memory_engine_v1",
        "relation": relation,
        "score": round(float(best_score), 6),
        "active_scene_match": bool(
            best.get("source") == "active_scene"
            and best_score >= similarity_threshold
        ),
        "historical_match": bool(
            best.get("source") != "active_scene"
            and best_score >= 0.72
        ),
        "best_match": best,
        "memory_signal": signal,
        "window_days": MEMORY_DAYS,
        "decision_owner": "QUANTUM_PROCESSOR",
        "evidence_only": True,
    }


# =====================================================
# 🧠 APRIL MEMORY ENGINE V5 INTEGRATION
# =====================================================

def ensure_memory_runtime(user_id):
    state_obj = get_state(user_id)
    ensure_memory_engine(state_obj)
    memory_rollover_if_needed(user_id)
    return state_obj

def build_unified_memory_bridge(user_id):

    state_obj = ensure_memory_runtime(user_id)

    return {
        "focus_state": state_obj.get("focus_state", {}),
        "focus_snapshot": state_obj.get("focus_snapshot", {}),
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {}),
        "memory_timeline": state_obj.get("memory_timeline", {}),
        "memory_cycle": state_obj.get("memory_cycle", {})
    }

def sync_focus_layers(user_id):

    state_obj = ensure_memory_runtime(user_id)

    focus_state = state_obj.get("focus_state", {})

    state_obj["focus_snapshot"] = {
        "topic": focus_state.get("active_topic"),
        "scene": focus_state.get("active_scene"),
        "object": focus_state.get("active_object"),
        "focus": focus_state.get("priority_score"),
        "intent": focus_state.get("intent_freshness")
    }

    if not state_obj.get("dynamic_focus"):
        state_obj["dynamic_focus"] = state_obj["focus_snapshot"]

def bind_current_visual_scene(user_id):

    state_obj = ensure_memory_runtime(user_id)

    visual = state_obj.get("active_visual_scene")

    if visual:
        bind_visual_scene_to_memory(user_id, visual)

def build_memory_snapshot_v3(user_id):

    state_obj = ensure_memory_runtime(user_id)

    return {
        "memory_version": "3.0",
        "focus_state": state_obj.get("focus_state", {}),
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {}),
        "memory_timeline": state_obj.get("memory_timeline", {}),
        "memory_cycle": state_obj.get("memory_cycle", {}),
        "active_flow": state_obj.get("active_flow"),
        "memory_engine": {
            "version": "quantum_memory_engine_v1",
            "window_days": MEMORY_DAYS,
            "day_keys": list(MEMORY_DAY_KEYS),
            "decision_owner": "QUANTUM_PROCESSOR",
        },
    }



# =====================================================
# 🧠 VISUAL LEDGER MEMORY BRIDGE
# =====================================================

def update_visual_summary(
    user_id,
    visual_summary
):

    state_obj = ensure_memory_runtime(
        user_id
    )

    state_obj["visual_summary"] = (
        visual_summary or {}
    )

    scene = state_obj.get(
        "active_visual_scene"
    ) or {}

    scene["events_count"] = (
        visual_summary.get(
            "scene_events_count",
            0
        )
    )

    scene["last_event"] = (
        visual_summary.get(
            "last_event"
        )
    )

    scene["package"] = (
        visual_summary.get(
            "package",
            "free"
        )
    )

    scene["session_started_utc"] = (
        visual_summary.get(
            "session_started_utc"
        )
    )

    state_obj["active_visual_scene"] = scene

    bind_visual_scene_to_memory(
        user_id,
        scene
    )

    state_obj["active_scene"] = refresh_unified_scene(
        user_id
    )

    persist_state(user_id)

    return scene


def build_visual_memory_bridge(
    user_id
):

    state_obj = ensure_memory_runtime(
        user_id
    )

    return {

        "user_visual_scene":
            state_obj.get(
                "active_visual_scene",
                {}
            ),

        "visual_summary":
            state_obj.get(
                "visual_summary",
                {}
            ),

        "today_visual_memory":
            state_obj.get(
                "memory_timeline",
                {}
            ).get(
                "day_0",
                {}
            ).get(
                "visual_scenes",
                []
            )
    }



# =====================================================
# 🧠 DIALOG CONTEXT MEMORY
# =====================================================


def update_scene_context(
    user_id,
    scene_contract,
    current_request="",
    answer="",
):
    """
    Persist the canonical scene produced by the existing route so the next
    turn can compare against the scene that actually reached the Web.
    """
    state_obj = ensure_memory_runtime(user_id)
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
        "space_continuity": contract.get("space_continuity") or {},
        "metadata": contract.get("metadata") or {},
        "supported_payloads": contract.get("supported_payloads") or [],
        "render_block_types": block_types,
        "current_request": str(current_request or "").strip(),
        "answer": str(answer or "").strip()[:4000],
        "scene_id": str(contract.get("scene_id") or ""),
    }
    state_obj["current_scene_request"] = str(current_request or "").strip()
    state_obj["last_april_turn"] = str(answer or "").strip()[:4000]
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
    persist_state(user_id)
