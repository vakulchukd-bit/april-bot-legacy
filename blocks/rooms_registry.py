# =====================================================
# 🧠 APRIL ROOMS REGISTRY
# =====================================================
#
# APRIL_FILE_ID:
# APRIL_ROOMS_REGISTRY
#
# ROLE:
# ROOM_EXECUTION_REGISTRY
#
# INPUT:
# USER_TEXT
# SEMANTIC_CONTEXT
# COGNITION_CONTEXT
# ROOM_CONTEXT
# EXECUTION_CONTEXT
#
# OUTPUT:
# ROOM_SELECTION
# ROOM_EXECUTION_RESULT
# MULTIMODAL_ROUTING
#
# DEPENDENCIES:
# room_protocol
# image_engine
# image_system
# science_room
# text_module
# excrouter
#
# =====================================================
#
# APRIL ROOMS REGISTRY
#
# Этот слой:
# - room registry;
# - execution-safe orchestration layer;
# - continuity-safe room collection;
# - multimodal routing bridge.
#
# Этот слой НЕ:
# - Telegram dispatcher;
# - routing authority;
# - semantic core;
# - renderer authority.
#
# =====================================================

print(
    "🧠 APRIL ROOMS REGISTRY LOADED"
)

# =====================================================
# 🔥 IMPORTS
# =====================================================

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
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "excrouter",

    "target":
        "rooms_registry",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "source":
        "rooms_registry",

    "target":
        "executor",

    "isolated":
        True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

ROOMS_PATCH_LOG = []

def safe_rooms_log(*args):

    try:

        print(
            "APRIL ROOMS:",
            *args
        )

        ROOMS_PATCH_LOG.append(
            " ".join(
                [str(x) for x in args]
            )
        )

    except:
        pass


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
# 🔥 SAFE EXECUTOR CONTEXT
# =====================================================

def get_executor_context(context):

    if not isinstance(context, dict):

        return {}

    return context.get(
        "context",
        context
    )


def get_chat_id(context):

    executor_context = get_executor_context(
        context
    )

    return executor_context.get(
        "chat_id"
    )


def get_state(context):

    executor_context = get_executor_context(
        context
    )

    return executor_context.get(
        "state",
        {}
    )


def get_cognition(context):

    executor_context = get_executor_context(
        context
    )

    return executor_context.get(
        "cognition",
        {}
    )



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

    room_type = "visual_generation"

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

        safe_rooms_log(
            "IMAGE GENERATE START"
        )

        state = get_state(
            context
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

                get_chat_id(
    context
),

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

                safe_rooms_log(
                    "IMAGE GENERATE SUCCESS"
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

    room_type = "visual_edit"

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

        safe_rooms_log(
            "IMAGE EDIT START"
        )

        state = get_state(
            context
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

            get_chat_id(
    context
),

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

    room_type = "science_renderer"

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

    room_type = "dialog"

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

        safe_rooms_log(
            "TEXT ROOM START"
        )

        from blocks.text_module import (
            process as text_process
        )

        cognition = get_cognition(
            context
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

            get_chat_id(
    context
),

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
# 🧠 GUIDANCE ROOM
# =====================================================

class GuidanceRoom(Room):

    name = "guidance"
    room_type = "assistant_guidance"

    def evaluate(self, text, context):

        cognition = get_cognition(context)

        if cognition.get("assistant_next_step"):
            return 0.95

        return 0.0

    async def handle(self, user_id, text, context, run):

        cognition = get_cognition(context)

        return {
            "type": "text",
            "data": f"Следующий шаг: {cognition.get('assistant_next_step','уточнение данных')}"
        }


class GraphRoom(Room):

    name = "graph"
    room_type = "graph_renderer"

    def evaluate(self, text, context):

        if "график" in normalize_text(text):
            return 0.96

        return 0.0

    async def handle(self, user_id, text, context, run):

        return {
            "type": "graph",
            "data": {
                "source": text
            }
        }


class FormulaRoom(Room):

    name = "formula"
    room_type = "formula_renderer"

    def evaluate(self, text, context):

        t = normalize_text(text)

        if "формул" in t:
            return 0.94

        return 0.0

    async def handle(self, user_id, text, context, run):

        return {
            "type": "formula",
            "data": text
        }


class FunctionRoom(Room):

    name = "function"
    room_type = "function_renderer"

    def evaluate(self, text, context):

        t = normalize_text(text)

        if "функц" in t or "f(x)" in t:
            return 0.93

        return 0.0

    async def handle(self, user_id, text, context, run):

        return {
            "type": "function",
            "data": text
        }


class TableRoom(Room):

    name = "table"
    room_type = "table_renderer"

    def evaluate(self, text, context):

        if "таблиц" in normalize_text(text):
            return 0.92

        return 0.0

    async def handle(self, user_id, text, context, run):

        return {
            "type": "table",
            "data": text
        }


class LinkRoom(Room):

    name = "link"
    room_type = "link_renderer"

    def evaluate(self, text, context):

        if detect_link_signal(text):
            return 0.91

        return 0.0

    async def handle(self, user_id, text, context, run):

        return {
            "type": "link",
            "data": text
        }

# =====================================================
# 🚀 ROOMS
# =====================================================

ROOMS = [

    GuidanceRoom(),

    GraphRoom(),

    FormulaRoom(),

    FunctionRoom(),

    TableRoom(),

    LinkRoom(),

    SafeScienceRoom(),

    ImageEditRoom(),

    ImageGenerateRoom(),

    TextRoom(),
]

# =====================================================
# 🔥 REGISTRY METADATA
# =====================================================

ROOM_REGISTRY_STATE = {

    "registry_ready":
        True,

    "web_space_ready":
        True,

    "renderer_safe":
        True,

    "continuity_safe":
        True,

    "telegram_bound":
        False,

    "machine_isolated":
        True
}
