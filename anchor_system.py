# =====================================================
# ⚓ APRIL SEMANTIC ANCHOR SYSTEM
# =====================================================

"""
APRIL CONTINUITY ANCHOR SYSTEM

Это больше НЕ:
- simple object storage;
- passive legacy anchor;
- telegram-era memory helper.

Теперь это:
- semantic continuity anchor system;
- scene persistence layer;
- trajectory-aware object memory;
- renderer-aware continuity bridge;
- multimodal anchor space.

Главная задача:
НЕ давать сцене разваливаться.

Anchor system помогает April:

- понимать что сцена продолжается;
- понимать что объект тот же;
- сохранять visual continuity;
- сохранять trajectory;
- предотвращать day-surka resets;
- связывать renderer-space с continuity;
- сохранять semantic object evolution.

Это foundation для:
- scene-space;
- multimodal continuity;
- persistent visual memory;
- semantic UI continuity.
"""

# =====================================================
# ⚓ STORAGE
# =====================================================

anchors = {}

# =====================================================
# ⚓ HELPERS
# =====================================================

def safe_text(
    value,
    limit=240
):

    value = str(
        value or ""
    ).strip()

    if len(value) <= limit:
        return value

    return value[:limit]


def safe_list(value):

    if isinstance(value, list):
        return value

    return []


# =====================================================
# ⚓ DEFAULT ANCHOR
# =====================================================

def build_anchor(
    type_,
    base
):

    return {

        # =================================================
        # 🔥 CORE
        # =================================================

        "type": type_,

        "base": base,

        "current": base,

        # =================================================
        # 🔥 CONTINUITY
        # =================================================

        "continuity_active": True,

        "continuity_weight": 0.85,

        "scene_continuation": True,

        "prevent_scene_reset": True,

        # =================================================
        # 🔥 SEMANTIC
        # =================================================

        "semantic_role":
            "primary_scene_object",

        "semantic_state":
            "active",

        "trajectory_state":
            "continuing",

        "anchor_priority": 1.0,

        # =================================================
        # 🔥 RENDERER
        # =================================================

        "renderer_bound": True,

        "renderer_space_active": True,

        "render_sync_required": True,

        # =================================================
        # 🔥 VISUAL
        # =================================================

        "visual_continuity": (
            type_ in [

                "image",
                "visual",
                "scene"
            ]
        ),

        "visual_scene_active": (
            type_ in [

                "image",
                "visual",
                "scene"
            ]
        ),

        # =================================================
        # 🔥 SCENE
        # =================================================

        "scene_id": None,

        "scene_type": None,

        "scene_state": "active",

        # =================================================
        # 🔥 HISTORY
        # =================================================

        "history": [],

        "semantic_history": [],

        "evolution": [],

        # =================================================
        # 🔥 META
        # =================================================

        "created_by": "anchor_system",

        "machine_space": True,

        "supports_multimodal": True,

        "supports_renderer_space": True
    }


# =====================================================
# ⚓ GET
# =====================================================

def get_anchor(
    user_id
):

    return anchors.get(
        user_id
    )


# =====================================================
# ⚓ CREATE
# =====================================================

def create_anchor(
    user_id,
    type_,
    base
):

    anchor = build_anchor(
        type_,
        base
    )

    # =================================================
    # 🔥 AUTO SCENE TYPE
    # =====================================================

    if type_ in [

        "image",
        "visual"
    ]:

        anchor[
            "scene_type"
        ] = "visual_scene"

    elif type_ == "voice":

        anchor[
            "scene_type"
        ] = "voice_scene"

    else:

        anchor[
            "scene_type"
        ] = "dialog_scene"

    # =================================================
    # 🔥 SAFE BASE
    # =====================================================

    if isinstance(
        base,
        dict
    ):

        anchor[
            "scene_id"
        ] = base.get(
            "scene_id"
        )

    anchors[user_id] = anchor

    return anchor


# =====================================================
# ⚓ UPDATE
# =====================================================

def update_anchor(
    user_id,
    new_data
):

    anchor = anchors.get(
        user_id
    )

    if not anchor:
        return

    previous = anchor.get(
        "current"
    )

    # =================================================
    # 🔥 HISTORY
    # =====================================================

    anchor[
        "history"
    ].append(previous)

    # =================================================
    # 🔥 SEMANTIC HISTORY
    # =====================================================

    anchor[
        "semantic_history"
    ].append({

        "state":
            anchor.get(
                "semantic_state"
            ),

        "trajectory":
            anchor.get(
                "trajectory_state"
            ),

        "continuity":
            anchor.get(
                "continuity_active"
            )
    })

    # =================================================
    # 🔥 EVOLUTION
    # =====================================================

    evolution_entry = {

        "previous":
            previous,

        "current":
            new_data,

        "continuity":
            True
    }

    anchor[
        "evolution"
    ].append(
        evolution_entry
    )

    # =================================================
    # 🔥 CURRENT
    # =====================================================

    anchor[
        "current"
    ] = new_data

    # =================================================
    # 🔥 CONTINUITY STABILIZATION
    # =====================================================

    anchor[
        "continuity_active"
    ] = True

    anchor[
        "scene_continuation"
    ] = True

    anchor[
        "prevent_scene_reset"
    ] = True

    anchor[
        "trajectory_state"
    ] = "continuing"

    anchor[
        "semantic_state"
    ] = "updated"

    # =================================================
    # 🔥 VISUAL STABILIZATION
    # =====================================================

    if anchor.get(
        "visual_scene_active"
    ):

        anchor[
            "visual_continuity"
        ] = True

        anchor[
            "renderer_bound"
        ] = True

        anchor[
            "renderer_space_active"
        ] = True

    # =================================================
    # 🔥 LIMITS
    # =====================================================

    if len(anchor["history"]) > 12:

        anchor["history"] = (
            anchor["history"][-12:]
        )

    if len(
        anchor["semantic_history"]
    ) > 12:

        anchor[
            "semantic_history"
        ] = (

            anchor[
                "semantic_history"
            ][-12:]
        )

    if len(anchor["evolution"]) > 12:

        anchor["evolution"] = (
            anchor["evolution"][-12:]
        )


# =====================================================
# ⚓ PATCH
# =====================================================

def patch_anchor(
    user_id,
    updates: dict
):

    anchor = anchors.get(
        user_id
    )

    if not anchor:
        return

    if not isinstance(
        updates,
        dict
    ):

        return

    for key, value in updates.items():

        anchor[key] = value

    # =================================================
    # 🔥 SAFETY
    # =====================================================

    anchor[
        "continuity_active"
    ] = True

    anchor[
        "prevent_scene_reset"
    ] = True


# =====================================================
# ⚓ CONTINUITY CHECK
# =====================================================

def anchor_continuity_active(
    user_id
):

    anchor = anchors.get(
        user_id
    )

    if not anchor:
        return False

    return anchor.get(
        "continuity_active",
        False
    )


# =====================================================
# ⚓ VISUAL CHECK
# =====================================================

def anchor_visual_active(
    user_id
):

    anchor = anchors.get(
        user_id
    )

    if not anchor:
        return False

    return anchor.get(
        "visual_scene_active",
        False
    )


# =====================================================
# ⚓ SCENE CHECK
# =====================================================

def anchor_scene_active(
    user_id
):

    anchor = anchors.get(
        user_id
    )

    if not anchor:
        return False

    return anchor.get(
        "scene_state"
    ) == "active"


# =====================================================
# ⚓ SUMMARY
# =====================================================

def build_anchor_summary(
    user_id
):

    anchor = anchors.get(
        user_id
    )

    if not anchor:
        return ""

    parts = []

    anchor_type = anchor.get(
        "type"
    )

    if anchor_type:

        parts.append(
            f"ANCHOR:{anchor_type}"
        )

    semantic_role = anchor.get(
        "semantic_role"
    )

    if semantic_role:

        parts.append(
            f"ROLE:{semantic_role}"
        )

    trajectory = anchor.get(
        "trajectory_state"
    )

    if trajectory:

        parts.append(
            f"FLOW:{trajectory}"
        )

    if anchor.get(
        "visual_continuity"
    ):

        parts.append(
            "VISUAL_CONTINUITY"
        )

    return " | ".join(parts)


# =====================================================
# ⚓ CLEAR
# =====================================================

def clear_anchor(
    user_id
):

    if user_id not in anchors:
        return

    anchor = anchors.get(
        user_id
    )

    # =================================================
    # 🔥 SOFT SHUTDOWN
    # =====================================================

    if anchor:

        anchor[
            "continuity_active"
        ] = False

        anchor[
            "scene_state"
        ] = "closed"

    del anchors[user_id]
