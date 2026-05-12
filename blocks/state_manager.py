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

        "last_update": None
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

    # 🔥 SAFETY BACKFILL
    if "scene_state" not in state_obj:

        state_obj["scene_state"] = (
            build_default_scene()
        )

    if "meta" not in state_obj:

        state_obj["meta"] = {}

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

    get_state(user_id)[
        "scene_state"
    ] = build_default_scene()


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

    if isinstance(ctx, dict):

        hint = (
            ctx.get("hint")
            or ctx.get("prompt")
        )

        if hint:

            scene["visual_target"] = (
                hint[:120]
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
    if len(updated) > 700:

        updated = updated[-700:]

    state_obj[
        "memory_summary"
    ] = updated


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

    last_messages = dialog[-6:]

    summary_parts = []

    for m in last_messages:

        content = (
            m.get("content", "")
            [:120]
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

    if len(combined) > 1000:

        combined = combined[-1000:]

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

    if scene.get("goal"):

        protected_context.append(
            f"GOAL:{scene['goal']}"
        )

    if scene.get("trajectory"):

        protected_context.append(
            f"FLOW:{scene['trajectory']}"
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


# =====================================================
# 🔥 IMAGE MEMORY CLEAN
# =====================================================

def trim_image_memory(
    state_obj
):

    memory = state_obj.get(
        "image_memory",
        []
    )

    if not memory:
        return

    if len(memory) > 3:

        state_obj[
            "image_memory"
        ] = memory[-3:]

        print(
            "🧹 IMAGE MEMORY TRIMMED"
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
            flow.get("original")
        )

        scene["continuity"] = True

    state_obj["scene_state"] = scene


def get_active_flow(user_id):

    return get_state(user_id).get(
        "active_flow"
    )


def clear_active_flow(user_id):

    state_obj = get_state(user_id)

    state_obj["active_flow"] = None

    scene = state_obj.get(
        "scene_state",
        {}
    )

    scene["trajectory"] = None

    scene["execution_mode"] = False

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
