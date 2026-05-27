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

        return {

            "semantic_room":
                room,

            "semantic_intent":
                intent,

            "semantic_detected":
                True
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
        ) is True
    )


def lock_image(
    state
):

    state[
        "image_locked"
    ] = True


def unlock_image(
    state
):

    state[
        "image_locked"
    ] = False


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

        except:
            pass

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

            return {

                "type": "text",

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

                result = await analyze_image(

                    path,

                    state
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

                    result = await image_edit(

                        user_id,

                        path,

                        text,

                        state
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

            return {

                "type": "image_task",

                "prompt": text,

                "semantic": {

                    "intent":
                        "image_generate",

                    "renderer_expected":
                        False,

                    "continuity_safe":
                        True
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

            return {

                "type": "image_task",

                "prompt": text,

                "semantic": {

                    "legacy_routed":
                        True,

                    "continuity_safe":
                        True
                }
            }

        # =============================================
        # 🔥 SAFE FALLBACK
        # =============================================

        return {

            "type": "text",

            "data":
                "⚠️ Visual request detected, "
                "but trajectory is unclear."
        }
