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

from storage import get_user_plan

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

        print(
            "STATE:",
            msg
        )

        STATE_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass

safe_state_log(
    "STATE MANAGER INITIALIZED"
)

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

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "machine_runtime": True,

        "renderer_safe": True,

        "continuity_alive": True,

        "web_safe": True
    }

# =====================================================
# 🔥 GET STATE
# =====================================================

def get_state(user_id):

    if user_id not in state:

        state[user_id] = (

            build_default_state()
        )

        safe_state_log(
            f"NEW STATE: {user_id}"
        )

    state_obj = state[user_id]

    # =================================================
    # 🔥 SAFE BACKFILL
    # =====================================================

    defaults = build_default_state()

    for key, value in defaults.items():

        if key not in state_obj:

            state_obj[key] = value

    if "scene_state" not in state_obj:

        state_obj[
            "scene_state"
        ] = build_default_scene()

    return state_obj

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

    dialog.append(

        compact_dialog_message(
            role,
            content
        )
    )

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

    trim_image_memory(
        state_obj
    )

    trim_visual_history(
        state_obj
    )
    
    trim_topic_memory(
        state_obj
    )

    state_obj["active_scene"] = build_active_scene(user_id) 

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
# 🔥 PERSISTENT MEMORY BRIDGE
# =====================================================

from storage import (
    load_memory,
    save_memory
)

def persist_state(user_id):
    try:
        state_obj = get_state(user_id)
        save_memory(user_id, state_obj)
    except Exception as e:
        safe_state_log(f"PERSIST ERROR: {e}")


# =====================================================
# 🔥 DB-AWARE STATE LOADER
# =====================================================

_original_get_state = get_state

def get_state(user_id):

    if user_id not in state:

        db_state = load_memory(user_id)

        if isinstance(db_state, dict):

            state[user_id] = db_state

            safe_state_log(
                f"STATE RESTORED: {user_id}"
            )

        else:

            state[user_id] = (
                build_default_state()
            )

            safe_state_log(
                f"NEW STATE: {user_id}"
            )

    state_obj = state[user_id]

    defaults = build_default_state()

    for key, value in defaults.items():

        if key not in state_obj:
            state_obj[key] = value

    if "scene_state" not in state_obj:

        state_obj["scene_state"] = (
            build_default_scene()
        )

    return state_obj

# Call persist_state(user_id) after:
# add_dialog()
# set_image_context()
# update_scene_state()
# clear_scene_state()
# set_active_flow()
# clear_active_flow()




# =====================================================
# 🧠 ACTIVE SCENE ENGINE
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
# 🧠 MEMORY ENGINE HELPERS
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

def update_goal_hierarchy(user_id, goal_payload):
    state_obj = get_state(user_id)
    state_obj["goal_hierarchy"] = goal_payload or {}

def update_open_loops(user_id, loops_payload):
    state_obj = get_state(user_id)
    state_obj["open_loops"] = loops_payload or []

def update_memory_signals(user_id, signals_payload):
    state_obj = get_state(user_id)
    state_obj["memory_signals"] = signals_payload or {}

def build_memory_bridge(user_id):
    state_obj = get_state(user_id)
    return {
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {})
    }


# =====================================================
# 🧠 DYNAMIC MEMORY FOCUS UPGRADE
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

    return get_state(user_id).get(
        "focus_snapshot",
        {}
    )


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
        "dynamic_focus": state_obj.get("dynamic_focus", {}),
        "goal_hierarchy": state_obj.get("goal_hierarchy", {}),
        "open_loops": state_obj.get("open_loops", []),
        "memory_signals": state_obj.get("memory_signals", {}),
        "active_flow": state_obj.get("active_flow")
    }

    return state_obj["active_scene"]
