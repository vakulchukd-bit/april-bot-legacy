from blocks.room_protocol import Room

# =====================================================
# 🔥 IMAGE
# =====================================================

from blocks.image_engine import (
    generate as image_generate
)

from blocks.image_engine import (
    edit as image_edit_engine
)

from blocks.image_system import (
    analyze_image
)

# =====================================================
# 🔥 SCIENCE
# =====================================================

from blocks.science_room import (
    ScienceRoom
)

import time
import re


# =====================================================
# 🔥 SAFE IMAGE LOCK
# =====================================================

def is_repeat_generation_blocked(state):

    ts = state.get(
        "last_image_time"
    )

    if not ts:
        return False

    return (
        time.time() - ts
    ) < 8


def mark_generation_time(state):

    state[
        "last_image_time"
    ] = time.time()


def is_image_locked(state):

    return (
        state.get(
            "image_locked"
        ) is True
    )


def unlock_image(state):

    state[
        "image_locked"
    ] = False


# =====================================================
# 🔥 APRIL MODALITY UNDERSTANDING
# =====================================================

def normalize_text(text):

    return (
        text or ""
    ).lower().strip()


def detect_visual_math_signal(text):

    t = normalize_text(text)

    patterns = [

        "график",
        "функция",
        "построй",
        "парабола",
        "синус",
        "косинус",
        "sin(",
        "cos(",
        "tan(",
        "y=",
        "y =",
        "f(x)",
        "f(x) =",
        "x**",
        "^2",
        "^3"
    ]

    if any(
        x in t
        for x in patterns
    ):

        return True

    equation = re.search(

        r"[a-z0-9]+\s*=\s*.+",

        t
    )

    if equation:
        return True

    return False


def detect_code_signal(text):

    t = text or ""

    code_patterns = [

        "import ",
        "from ",
        "export default",
        "const ",
        "let ",
        "var ",
        "function(",
        "=>",
        "return (",
        "className=",
        "</",
        "/>",
        "```",
        "async def",
        "await ",
        "use client",
        "props",
        "typescript",
        "javascript",
        "python",
        ".map(",
        "if (",
        "{",
        "};"
    ]

    hits = 0

    for p in code_patterns:

        if p in t:
            hits += 1

    return hits >= 2


def detect_link_signal(text):

    t = normalize_text(text)

    patterns = [

        "ссылка",
        "url",
        "линк",
        "website",
        "http://",
        "https://"
    ]

    return any(
        x in t
        for x in patterns
    )


def detect_image_signal(text):

    t = normalize_text(text)

    patterns = [

        "нарисуй",
        "создай изображение",
        "сгенерируй",
        "арт",
        "draw",
        "generate image"
    ]

    return any(
        x in t
        for x in patterns
    )


# =====================================================
# 🔥 IMAGE GENERATE
# =====================================================

class ImageGenerateRoom(Room):

    name = "image_generate"

    def can_handle(
        self,
        text,
        context
    ):

        return detect_image_signal(
            text
        )

    def evaluate(
        self,
        text,
        context
    ):

        if detect_image_signal(
            text
        ):

            return 0.92

        return 0.0

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        state = context.get(
            "state",
            {}
        )

        if is_image_locked(
            state
        ):

            return {

                "type": "text",

                "data":
                    "⏳ Уже генерирую изображение..."
            }

        state[
            "image_locked"
        ] = True

        try:

            result = await run(

                context["chat_id"],

                image_generate(

                    user_id,
                    text,
                    state
                )
            )

            if (
                result
                and result.get(
                    "type"
                ) == "image"
            ):

                state[
                    "last_image_prompt"
                ] = text

                mark_generation_time(
                    state
                )

                return result

            return {

                "type": "error",

                "data":
                    "🎨 Ошибка генерации"
            }

        finally:

            unlock_image(
                state
            )


# =====================================================
# 🔥 IMAGE EDIT
# =====================================================

class ImageEditRoom(Room):

    name = "image_edit"

    def can_handle(
        self,
        text,
        context
    ):

        semantic = context.get(
            "semantic",
            {}
        )

        return semantic.get(
            "room"
        ) == self.name

    def evaluate(
        self,
        text,
        context
    ):

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get(
            "room"
        ) == self.name:

            return 0.8

        return 0.0

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        state = context.get(
            "state",
            {}
        )

        ctx = state.get(
            "image_context"
        )

        if (
            not ctx
            or not ctx.get("path")
        ):

            return {

                "type": "text",

                "data":
                    "⚠️ Нет изображения"
            }

        try:

            hint = await analyze_image(

                ctx["path"],
                state
            )

        except:

            hint = "изображение"

        prompt = (

            hint
            + ". "
            + text
        )

        image_bytes = state.get(
            "image_current"
        )

        result = await run(

            context["chat_id"],

            image_edit_engine(

                user_id,
                image_bytes,
                prompt,
                state
            )
        )

        return result


# =====================================================
# 🔥 SCIENCE
# =====================================================

class SafeScienceRoom(ScienceRoom):

    name = "science"

    # =================================================
    # 🔥 APRIL CAPABILITY DETECTION
    # =====================================================

    def can_handle(
        self,
        text,
        context
    ):

        # =============================================
        # 🔥 CODE PROTECTION
        # =============================================

        if detect_code_signal(
            text
        ):

            return False

        return detect_visual_math_signal(
            text
        )

    # =================================================
    # 🔥 CALM EVALUATION
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        # =============================================
        # 🔥 CODE PROTECTION
        # =============================================

        if detect_code_signal(
            text
        ):

            return 0.0

        score = 0.0

        t = normalize_text(
            text
        )

        # =============================================
        # 🔥 DIRECT GRAPH SIGNAL
        # =============================================

        if detect_visual_math_signal(
            text
        ):

            score += 0.9

        # =============================================
        # 🔥 EXPLICIT GRAPH REQUEST
        # =============================================

        graph_words = [

            "построй",
            "покажи график",
            "нарисуй график"
        ]

        if any(
            x in t
            for x in graph_words
        ):

            score += 0.3

        return score


# =====================================================
# 🔥 TEXT
# =====================================================

class TextRoom(Room):

    name = "text"

    def can_handle(
        self,
        text,
        context
    ):

        return True

    # =================================================
    # 🔥 CALM FALLBACK
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        # =============================================
        # 🔥 CODE PRIORITY
        # =============================================

        if detect_code_signal(
            text
        ):

            return 1.0

        # =============================================
        # 🔥 LINK PRIORITY
        # =============================================

        if detect_link_signal(
            text
        ):

            return 0.9

        # =============================================
        # 🔥 MATH / GRAPH
        # =============================================

        if detect_visual_math_signal(
            text
        ):

            return 0.25

        return 0.55

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):

        from blocks.text_module import (
            process as text_process
        )

        cognition = context.get(
            "cognition",
            {}
        )

        text_input = text

        if cognition.get(
            "reduce_talking"
        ):

            text_input = (

                "Ответь коротко и по делу.\n\n"

                + text
            )

        result = await run(

            context["chat_id"],

            text_process(

                user_id,
                text_input,
                context.get("state"),
                context.get("energy")
            )
        )

        return {

            "type": "text",

            "data":

                result.get(
                    "content",
                    "⚠️ Пустой ответ"
                )
        }


# =====================================================
# 🚀 ROOMS
# =====================================================

ROOMS = [

    SafeScienceRoom(),

    ImageEditRoom(),

    ImageGenerateRoom(),

    TextRoom(),
]
