# blocks/state_manager.py

state = {}

# 🔥 STABLE IMAGE STORAGE
image_storage = {}

ADMIN_ID = 2016592532


# =====================================================
# 🔥 DIALOG LIMITS
# =====================================================

def get_dialog_limit(user_id, plan):

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

    if isinstance(value, list):
        return value

    return []


# =====================================================
# 🔥 DEFAULT SCENE STATE
# =====================================================

def build_default_scene():

    return {

        # =================================================
        # 🔥 CORE SCENE
        # =================================================

        "type": None,

        "goal": None,

        "trajectory": None,

        "continuity": True,

        "status": "active",

        # =================================================
        # 🔥 PRIMARY CONTINUITY
        # =================================================

        "primary_anchor": None,

        "anchor_type": None,

        "anchor_priority": 0.0,

        "anchor_updated_at": None,

        # =================================================
        # 🔥 USER
        # =================================================

        "user_intent": None,

        "user_direction": None,

        "user_expectation": None,

        # =================================================
        # 🔥 VISUAL
        # =================================================

        "visual_mode": False,

        "visual_target": None,

        "visual_continuity": False,

        # =================================================
        # 🔥 EXECUTION
        # =================================================

        "execution_mode": False,

        "execution_target": None,

        # =================================================
        # 🔥 FLOW
        # =================================================

        "active_room": None,

        "confirmed_direction": None,

        "last_completed_step": None,

        # =================================================
        # 🔥 STABILITY
        # =================================================

        "confidence": 0.0,

        "last_update": None,

        # =================================================
        # 🔥 APRIL CONTINUITY
        # =================================================

        "semantic_continuity": True,

        "continuity_window_active": True,

        "trajectory_locked": False,

        "visual_scene_active": False,

        "scene_identity": "stable",

        "orchestration_mode": "stable",

        "preserve_visual_space": True
    }


# =====================================================
# 🔥 DEFAULT STATE
# =====================================================

def build_default_state():

    return {

        # =================================================
        # 🔥 DIALOG
        # =================================================

        "dialog": [],

        "memory_summary": "",

        "dialog_state": {},

        # =================================================
        # 🔥 IMAGE
        # =================================================

        "image_context": None,

        "image_memory": [],

        # =================================================
        # 🔥 VISUAL SCENE MEMORY
        # =================================================

        "active_visual_scene": None,

        "visual_scene_history": [],

        # =================================================
        # 🔥 FLOW
        # =================================================

        "active_flow": None,

        "passive_memory": [],

        # =================================================
        # 🔥 REQUEST STATE
        # =================================================

        "awaiting": False,

        "last_prompt": None,

        "task_type": None,

        # =================================================
        # 🔥 UNIFIED SCENE
        # =================================================

        "scene_state": build_default_scene(),

        # =================================================
        # 🔥 CACHE
        # =================================================

        "image_analysis": None,

        "image_analysis_path": None,

        "last_scene_object": None,

        # =================================================
        # 🔥 META
        # =================================================

        "meta": {

            "last_intent": None,

            "last_action": None,

            "last_entity": None,

            "last_user_message": None,

            "last_bot_message": None,

            "identity_initialized": False,

            "identity_name": "April",

            "identity_mode": "integrated"
        }
    }


# =====================================================
# 🔥 GET STATE
# =====================================================

def get_state(user_id):

    if user_id not in state:

        state[user_id] = (
            build_default_state()
        )

    state_obj = state[user_id]

    # =================================================
    # 🔥 SAFETY BACKFILL
    # =================================================

    if "scene_state" not in state_obj:

        state_obj["scene_state"] = (
            build_default_scene()
        )

    if "meta" not in state_obj:

        state_obj["meta"] = {}

    if "active_visual_scene" not in state_obj:

        state_obj[
            "active_visual_scene"
        ] = None

    if "visual_scene_history" not in state_obj:

        state_obj[
            "visual_scene_history"
        ] = []

    if "image_memory" not in state_obj:

        state_obj[
            "image_memory"
        ] = []

    if "dialog" not in state_obj:

        state_obj[
            "dialog"
        ] = []

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
    updates: dict
):

    if not isinstance(updates, dict):
        return

    state_obj = get_state(user_id)

    scene = state_obj.get(
        "scene_state",
        {}
    )

    for key, value in updates.items():

        scene[key] = value

    state_obj["scene_state"] = scene


def clear_scene_state(user_id):

    state_obj = get_state(user_id)

    old_scene = state_obj.get(
        "scene_state",
        {}
    )

    preserved_visual_scene = state_obj.get(
        "active_visual_scene"
    )

    new_scene = build_default_scene()

    # =================================================
    # 🔥 VISUAL CONTINUITY PRESERVE
    # =================================================

    if preserved_visual_scene:

        new_scene[
            "visual_continuity"
        ] = True

        new_scene[
            "visual_scene_active"
        ] = True

    if old_scene.get(
        "primary_anchor"
    ):

        new_scene[
            "primary_anchor"
        ] = old_scene.get(
            "primary_anchor"
        )

        new_scene[
            "anchor_type"
        ] = old_scene.get(
            "anchor_type"
        )

    state_obj[
        "scene_state"
    ] = new_scene


# =====================================================
# 🔥 IMAGE CONTEXT
# =====================================================

def set_image_context(
    user_id,
    ctx
):

    image_storage[user_id] = ctx

    state_obj = get_state(user_id)

    state_obj["image_context"] = ctx

    # 🔥 SCENE LINK
    scene = state_obj.get(
        "scene_state",
        {}
    )

    scene["visual_mode"] = True

    scene["visual_continuity"] = True

    scene["visual_scene_active"] = True

    if isinstance(ctx, dict):

        hint = (
            ctx.get("hint")
            or ctx.get("prompt")
        )

        if hint:

            scene["visual_target"] = (
                safe_trim_text(
                    hint,
                    120
                )
            )

    state_obj["scene_state"] = scene


def get_image_context(user_id):

    ctx = image_storage.get(user_id)

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
    value: bool
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
    user_id,
    new_text
):

    state_obj = get_state(user_id)

    current = state_obj.get(
        "memory_summary",
        ""
    )

    updated = (
        current
        + " "
        + str(new_text)
    ).strip()

    # 🔥 LIMIT
    if len(updated) > 1200:

        updated = updated[-1200:]

    state_obj[
        "memory_summary"
    ] = updated


# =====================================================
# 🔥 VISUAL CONTINUITY SUMMARY
# =====================================================

def build_visual_scene_summary(
    state_obj
):

    visual_scene = state_obj.get(
        "active_visual_scene"
    )

    if not visual_scene:
        return ""

    objects = visual_scene.get(
        "objects",
        []
    )

    scene_type = visual_scene.get(
        "scene_type"
    )

    colors = visual_scene.get(
        "colors",
        []
    )

    parts = []

    if scene_type:

        parts.append(
            f"SCENE:{scene_type}"
        )

    if objects:

        parts.append(
            "OBJECTS:"
            + ",".join(objects[:5])
        )

    if colors:

        parts.append(
            "COLORS:"
            + ",".join(colors[:5])
        )

    return " | ".join(parts)


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

    # =================================================
    # 🔥 LAST IMPORTANT
    # =================================================

    last_messages = dialog[-8:]

    summary_parts = []

    for m in last_messages:

        content = safe_trim_text(
            m.get("content", ""),
            160
        )

        if content:

            summary_parts.append(
                content
            )

    short_summary = " | ".join(
        summary_parts
    )

    # =================================================
    # 🔥 MEMORY SUMMARY
    # =================================================

    existing = state_obj.get(
        "memory_summary",
        ""
    )

    combined = (
        existing
        + " | "
        + short_summary
    ).strip()

    if len(combined) > 1600:

        combined = combined[-1600:]

    state_obj[
        "memory_summary"
    ] = combined

    # =================================================
    # 🔥 SCENE PROTECTION
    # =================================================

    scene = state_obj.get(
        "scene_state",
        {}
    )

    protected_context = []

    # =================================================
    # 🔥 PRIMARY ANCHOR PROTECTION
    # =================================================

    primary_anchor = scene.get(
        "primary_anchor"
    )

    anchor_type = scene.get(
        "anchor_type"
    )

    if primary_anchor:

        protected_context.append(

            f"ANCHOR:{anchor_type}:{primary_anchor}"
        )

    if scene.get("goal"):

        protected_context.append(
            f"GOAL:{scene['goal']}"
        )

    if scene.get("trajectory"):

        protected_context.append(
            f"FLOW:{scene['trajectory']}"
        )

    # =================================================
    # 🔥 VISUAL CONTINUITY PROTECTION
    # =================================================

    visual_summary = (
        build_visual_scene_summary(
            state_obj
        )
    )

    if visual_summary:

        protected_context.append(
            visual_summary
        )

    protected_text = " | ".join(
        protected_context
    )

    # =================================================
    # 🔥 NEW DIALOG
    # =================================================

    compressed_content = (
        protected_text
        + "\n"
        + short_summary
    ).strip()

    state_obj["dialog"] = [{

        "role": "system",

        "content": compressed_content
    }]

    print(
        "🧹 DIALOG COMPRESSED"
    )

    print(
        "🧠 CONTINUITY PRESERVED"
    )


# =====================================================
# 🔥 IMAGE MEMORY CLEAN
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

    if not memory:
        return

    if len(memory) > 5:

        state_obj[
            "image_memory"
        ] = memory[-5:]

        print(
            "🧹 IMAGE MEMORY TRIMMED"
        )


# =====================================================
# 🔥 VISUAL HISTORY CLEAN
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

    if len(history) > 8:

        state_obj[
            "visual_scene_history"
        ] = history[-8:]

        print(
            "🧹 VISUAL HISTORY TRIMMED"
        )


# =====================================================
# 🔥 DIALOG
# =====================================================

from storage import get_user_plan


def add_dialog(
    user_id,
    role,
    content
):

    state_obj = get_state(user_id)

    dialog = state_obj["dialog"]

    dialog.append({

        "role": role,

        "content": content
    })

    # =================================================
    # 🔥 META UPDATE
    # =================================================

    meta = state_obj.get(
        "meta",
        {}
    )

    if role == "user":

        meta[
            "last_user_message"
        ] = content

    else:

        meta[
            "last_bot_message"
        ] = content

    state_obj["meta"] = meta

    # =================================================
    # 🔥 SCENE UPDATE
    # =================================================

    scene = state_obj.get(
        "scene_state",
        {}
    )

    if role == "user":

        scene["last_update"] = (
            "user"
        )

    else:

        scene["last_update"] = (
            "assistant"
        )

    state_obj[
        "scene_state"
    ] = scene

    # =================================================
    # 🔥 LIMITS
    # =================================================

    plan = get_user_plan(user_id)

    limit = get_dialog_limit(
        user_id,
        plan
    )

    # =================================================
    # 🔥 COMPRESSION
    # =================================================

    if len(dialog) > limit:

        compress_dialog_to_summary(
            state_obj
        )

    # =================================================
    # 🔥 IMAGE MEMORY
    # =================================================

    trim_image_memory(
        state_obj
    )

    trim_visual_history(
        state_obj
    )


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
    flow: dict
):

    state_obj = get_state(user_id)

    state_obj["active_flow"] = flow

    # 🔥 SCENE SYNC
    scene = state_obj.get(
        "scene_state",
        {}
    )

    if isinstance(flow, dict):

        scene["trajectory"] = (
            flow.get("type")
        )

        scene["goal"] = (
            safe_trim_text(
                flow.get("original"),
                240
            )
        )

        scene["trajectory_locked"] = True

        # =================================================
        # 🔥 PRIMARY ANCHOR SYNC
        # =================================================

        primary_anchor = flow.get(
            "primary_anchor"
        )

        anchor_type = flow.get(
            "anchor_type"
        )

        if primary_anchor:

            scene["primary_anchor"] = (
                primary_anchor
            )

            scene["anchor_type"] = (
                anchor_type
            )

            scene["anchor_priority"] = (
                flow.get(
                    "anchor_priority",
                    1.0
                )
            )

            scene["anchor_updated_at"] = (
                flow.get(
                    "timestamp"
                )
            )

        scene["continuity"] = True

        if flow.get("type") in [

            "image_generate",
            "image_edit",
            "image"
        ]:

            scene["visual_mode"] = True

            scene["visual_continuity"] = True

            scene["visual_scene_active"] = True

    state_obj["scene_state"] = scene


def get_active_flow(user_id):

    return get_state(user_id).get(
        "active_flow"
    )


def clear_active_flow(user_id):

    state_obj = get_state(user_id)

    active_visual_scene = state_obj.get(
        "active_visual_scene"
    )

    state_obj["active_flow"] = None

    scene = state_obj.get(
        "scene_state",
        {}
    )

    scene["trajectory"] = None

    scene["execution_mode"] = False

    scene["trajectory_locked"] = False

    # =================================================
    # 🔥 VISUAL CONTINUITY SAFE
    # =================================================

    if active_visual_scene:

        scene["visual_continuity"] = True

        scene["visual_scene_active"] = True

    state_obj["scene_state"] = scene


# =====================================================
# 🔥 META HELPERS
# =====================================================

def set_last_entity(
    user_id,
    entity: dict
):

    state_obj = get_state(user_id)

    meta = state_obj.get(
        "meta",
        {}
    )

    meta["last_entity"] = entity

    state_obj["meta"] = meta

    # 🔥 SCENE ENTITY LINK
    scene = state_obj.get(
        "scene_state",
        {}
    )

    if isinstance(entity, dict):

        entity_type = entity.get(
            "type"
        )

        if entity_type:

            scene[
                "confirmed_direction"
            ] = entity_type

            if entity_type == "image":

                scene[
                    "visual_mode"
                ] = True

                scene[
                    "visual_scene_active"
                ] = True

    state_obj["scene_state"] = scene

    print(
        "🧠 META UPDATED:",
        meta
    )


def get_last_entity(user_id):

    return get_state(user_id).get(
        "meta",
        {}
    ).get(
        "last_entity"
    )
