# =====================================================
# 🧠 APRIL IMAGE ROOM
# =====================================================

"""
APRIL IMAGE ROOM

APRIL_FILE_ID:
APRIL_IMAGE_ROOM_COORDINATOR

ROLE:
VISUAL_ROOM_ORCHESTRATION_LAYER

INPUT:
USER_VISUAL_REQUEST
SEMANTIC_CONTEXT
VISUAL_STATE
IMAGE_CONTEXT

OUTPUT:
IMAGE_TASK
VISUAL_ANALYSIS
EDIT_TRAJECTORY
RENDERER_SAFE_VISUAL_RESPONSE

Главная задача:
- semantic visual routing;
- visual continuity;
- image orchestration;
- renderer-safe image coordination;
- Web Space compatible visual execution.

Этот файл НЕ:
- renderer authority;
- frontend renderer;
- Telegram-only image pipeline;
- cognition authority;
- hidden orchestration engine.
"""

# ===============================
# 🔥 SAFE PATCH MODE (IMAGE ROOM)
# ===============================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "IMAGE PATCH:",
            msg
        )

        PATCH_LOG.append(msg)

    except:
        pass

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_IMAGE_ROOM_COORDINATOR"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

IMAGE_ROOM_TASK_CHANNEL = {

    "channel":
        "image_room_machine_task_channel",

    "isolated":
        True
}

IMAGE_ROOM_RESPONSE_CHANNEL = {

    "channel":
        "image_room_machine_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

IMAGE_ROOM_LOGS = []

MAX_IMAGE_ROOM_LOGS = 60


def log_image_room_event(
    event,
    payload=None
):

    try:

        IMAGE_ROOM_LOGS.append({

            "file_id":
                APRIL_FILE_ID,

            "event":
                event,

            "payload":
                payload or {},

            "machine_only":
                True
        })

        if len(IMAGE_ROOM_LOGS) > MAX_IMAGE_ROOM_LOGS:

            IMAGE_ROOM_LOGS.pop(0)

    except:
        pass

# =====================================================
# 🧠 SEMANTIC IMAGE SIGNALS
# =====================================================

SEMANTIC_IMAGE_SIGNALS = {

    "generate": [

        "image_generate",
        "visual_generate",
        "scene_generate",
        "art_generate"
    ],

    "edit": [

        "image_edit",
        "visual_edit",
        "scene_edit"
    ],

    "analyze": [

        "visual_analysis",
        "image_analysis",
        "screenshot_analysis",
        "ocr_analysis"
    ]
}

# =====================================================
# 🔥 PATCH: SEMANTIC ENTRY
# =====================================================

def patch_image_enter(
    text,
    semantic=None
):

    semantic = semantic or {}

    safe_patch_log(

        f"IMAGE ENTER: "
        f"{str(text)[:50]}"
    )

    room = semantic.get(
        "room"
    )

    intent = semantic.get(
        "intent"
    )

    if room in [

        "image_generate",
        "image_edit",
        "image_analysis"
    ]:

        log_image_room_event(

            "semantic_room_detected",

            {
                "room":
                    room,

                "intent":
                    intent
            }
        )

        return {

            "semantic_room":
                room,

            "semantic_intent":
                intent,

            "semantic_detected":
                True,

            "machine_channel":
                IMAGE_ROOM_RESPONSE_CHANNEL
        }

    return {

        "semantic_detected":
            False
    }

# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def patch_image_future(
    *args,
    **kwargs
):

    return None

# =====================================================
# 🔥 IMAGE LOCKS
# =====================================================

def is_image_locked(
    state
):

    return (

        state.get(
            "image_locked"
        )

        is True
    )


def lock_image(
    state
):

    state[
        "image_locked"
    ] = True

    log_image_room_event(
        "image_locked"
    )


def unlock_image(
    state
):

    state[
        "image_locked"
    ] = False

    log_image_room_event(
        "image_unlocked"
    )

# =====================================================
# 🔥 SAFE UNLOCK
# =====================================================

def ensure_unlock(
    state
):

    if (

        state.get(
            "image_locked"
        )

        and not state.get(
            "image_current"
        )

    ):

        print(
            "⚠️ FORCE UNLOCK "
            "(no image result)"
        )

        state[
            "image_locked"
        ] = False

        log_image_room_event(
            "force_unlock"
        )

# =====================================================
# 🔥 IMPORTS
# =====================================================

from blocks.image_module import (
    process as image_generate
)

from blocks.image_edit_module import (
    process as image_edit
)

from blocks.image_system import (
    analyze_image
)

from blocks.state_manager import (

    get_image_context,

    get_state
)

# =====================================================
# 🧠 IMAGE ROOM
# =====================================================

class ImageRoom:

    name = "image"

    ROOM_ID = (
        "APRIL_IMAGE_ROOM"
    )

    # =================================================
    # 🔥 SEMANTIC ROUTING
    # =====================================================

    def semantic_can_handle(
        self,
        semantic
    ):

        semantic = semantic or {}

        room = semantic.get(
            "room"
        )

        intent = semantic.get(
            "intent"
        )

        if room in [

            "image_generate",
            "image_edit",
            "image_analysis"
        ]:

            return True

        if intent in [

            "image_generate",
            "image_edit",
            "image_analysis",
            "visual_analysis"
        ]:

            return True

        return False

    # =================================================
    # 🔥 LEGACY FALLBACK
    # =====================================================

    def legacy_can_handle(
        self,
        text
    ):

        t = (
            text or ""
        ).lower()

        if any(

            w in t

            for w in [

                "создай",
                "сгенерируй",
                "нарисуй",
                "сделай"
            ]
        ):

            return True

        if any(

            w in t

            for w in [

                "убери",
                "добавь",
                "измени",
                "замени"
            ]
        ):

            return True

        if any(

            w in t

            for w in [

                "что на картинке",
                "что это",
                "что изображено"
            ]
        ):

            return True

        return False

    # =================================================
    # 🔥 MAIN HANDLE DETECTION
    # =====================================================

    def can_handle(
        self,
        text,
        context
    ):

        semantic = (

            context.get(
                "semantic"
            )

            or {}
        )

        if self.semantic_can_handle(
            semantic
        ):

            return True

        return self.legacy_can_handle(
            text
        )

    # =================================================
    # 🔥 EVALUATION
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        semantic = (

            context.get(
                "semantic"
            )

            or {}
        )

        score = 0.0

        # =============================================
        # 🧠 SEMANTIC PRIORITY
        # =============================================

        room = semantic.get(
            "room"
        )

        intent = semantic.get(
            "intent"
        )

        if room in [

            "image_generate",
            "image_edit",
            "image_analysis"
        ]:

            score += 0.92

        if intent in [

            "image_generate",
            "image_edit",
            "image_analysis",
            "visual_analysis"
        ]:

            score += 0.82

        # =============================================
        # 🔥 LEGACY SUPPORT
        # =============================================

        try:

            if self.legacy_can_handle(
                text
            ):

                score += 0.25

        except Exception as e:

            log_image_room_event(

                "legacy_evaluation_error",

                {
                    "error":
                        str(e)
                }
            )

        return min(
            score,
            1.0
        )

    # =================================================
    # 🔥 HANDLE
    # =====================================================

    async def handle(
        self,
        user_id,
        text,
        context,
        run_with_typing
    ):

        log_image_room_event(

            "handle_started",

            {
                "user_id":
                    str(user_id)
            }
        )

        ctx = get_image_context(
            user_id
        )

        state = get_state(
            user_id
        )

        semantic = (

            context.get(
                "semantic"
            )

            or {}
        )

        semantic_room = semantic.get(
            "room"
        )

        semantic_intent = semantic.get(
            "intent"
        )

        t = (
            text or ""
        ).lower()

        # =============================================
        # 🔥 AUTO UNLOCK
        # =============================================

        ensure_unlock(
            state
        )

        # =============================================
        # 🔥 DUPLICATE PROTECTION
        # =============================================

        if is_image_locked(
            state
        ):

            print(
                "⛔ IMAGE LOCKED "
                "→ skip duplicate"
            )

            log_image_room_event(
                "duplicate_blocked"
            )

            return {

                "type":
                    "text",

                "data":
                    "⏳ Уже обрабатываю изображение..."
            }

        # =============================================
        # 🧠 SEMANTIC ANALYSIS
        # =============================================

        semantic_analysis = (

            semantic_room
            == "image_analysis"

            or

            semantic_intent in [

                "visual_analysis",
                "image_analysis",
                "screenshot_analysis"
            ]
        )

        # =============================================
        # 🧠 SEMANTIC EDIT
        # =============================================

        semantic_edit = (

            semantic_room
            == "image_edit"

            or

            semantic_intent
            == "image_edit"
        )

        # =============================================
        # 🧠 SEMANTIC GENERATE
        # =============================================

        semantic_generate = (

            semantic_room
            == "image_generate"

            or

            semantic_intent
            == "image_generate"
        )

        # =============================================
        # 🔥 LEGACY ANALYSIS
        # =============================================

        legacy_analysis = any(

            w in t

            for w in [

                "что на картинке",
                "что это",
                "что изображено"
            ]
        )

        # =============================================
        # 🔥 LEGACY EDIT
        # =============================================

        legacy_edit = any(

            w in t

            for w in [

                "убери",
                "добавь",
                "измени",
                "замени"
            ]
        )

        # =============================================
        # 🔥 ANALYZE
        # =============================================

        if ctx and (

            semantic_analysis
            or legacy_analysis
        ):

            path = ctx.get(
                "path"
            )

            if path:

                log_image_room_event(
                    "analysis_started"
                )

                result = await analyze_image(

                    path,

                    state
                )

                log_image_room_event(
                    "analysis_completed"
                )

                return result

        # =============================================
        # 🔥 EDIT
        # =============================================

        if ctx and (

            semantic_edit
            or legacy_edit
        ):

            path = ctx.get(
                "path"
            )

            if path:

                lock_image(
                    state
                )

                try:

                    log_image_room_event(
                        "edit_started"
                    )

                    result = await image_edit(

                        user_id,

                        path,

                        text,

                        state
                    )

                    log_image_room_event(
                        "edit_completed"
                    )

                    return result

                finally:

                    unlock_image(
                        state
                    )

        # =============================================
        # 🔥 GENERATE
        # =============================================

        if semantic_generate:

            lock_image(
                state
            )

            log_image_room_event(
                "generation_task_created"
            )

            return {

                "type":
                    "image_task",

                "prompt":
                    text,

                "semantic": {

                    "intent":
                        "image_generate",

                    "renderer_expected":
                        False,

                    "continuity_safe":
                        True,

                    "machine_channel":
                        IMAGE_ROOM_RESPONSE_CHANNEL
                }
            }

        # =============================================
        # 🔥 LEGACY GENERATE
        # =============================================

        if self.legacy_can_handle(
            text
        ):

            lock_image(
                state
            )

            log_image_room_event(
                "legacy_generation_task_created"
            )

            return {

                "type":
                    "image_task",

                "prompt":
                    text,

                "semantic": {

                    "legacy_routed":
                        True,

                    "continuity_safe":
                        True,

                    "machine_channel":
                        IMAGE_ROOM_RESPONSE_CHANNEL
                }
            }

        # =============================================
        # 🔥 SAFE FALLBACK
        # =============================================

        log_image_room_event(
            "safe_fallback"
        )

        return {

            "type":
                "text",

            "data":
                "⚠️ Visual request detected, "
                "but trajectory is unclear."
        }
