from blocks.room_protocol import Room

# === IMAGE FIRST 🔥 ===
from blocks.image_engine import generate as image_generate
from blocks.image_engine import edit as image_edit_engine
from blocks.image_system import analyze_image

# === SCIENCE ===
from blocks.science_room import ScienceRoom

import time


# =====================================================
# 🔥 SAFE IMAGE LOCK
# =====================================================

def is_repeat_generation_blocked(state):

    ts = state.get("last_image_time")

    if not ts:
        return False

    return (time.time() - ts) < 8


def mark_generation_time(state):

    state["last_image_time"] = time.time()


def is_image_locked(state):

    return state.get("image_locked") is True


def unlock_image(state):

    state["image_locked"] = False


# =====================================================
# 🔥 COGNITIVE HELPERS
# =====================================================

def wants_visual_support(context):

    cognition = context.get(
        "cognition",
        {}
    )

    if cognition.get(
        "prefer_visual"
    ):
        return True

    if cognition.get(
        "needs_examples"
    ):
        return True

    return False


def wants_execution(context):

    cognition = context.get(
        "cognition",
        {}
    )

    semantic = context.get(
        "semantic",
        {}
    )

    if cognition.get(
        "prefer_execution"
    ):
        return True

    if semantic.get(
        "should_execute"
    ):
        return True

    return False


def dialog_overextended(context):

    cognition = context.get(
        "cognition",
        {}
    )

    if cognition.get(
        "dialog_fatigue",
        0.0
    ) >= 0.7:
        return True

    return False


# =====================================================
# 🎨 IMAGE GENERATE
# =====================================================

class ImageGenerateRoom(Room):

    name = "image_generate"

    def can_handle(self, text, context):

        semantic = context.get(
            "semantic",
            {}
        )

        cognition = context.get(
            "cognition",
            {}
        )

        if semantic.get("room") == self.name:

            confidence = semantic.get(
                "confidence",
                0.0
            )

            if confidence >= 0.6:
                return True

        # =================================================
        # 🔥 APRIL VISUAL AUTHORITY
        # =================================================

        if cognition.get(
            "prefer_visual"
        ):

            return True

        if cognition.get(
            "wants_visual",
            0.0
        ) >= 0.55:

            return True

        if cognition.get(
            "wants_result",
            0.0
        ) >= 0.72:

            return True

        if semantic.get(
            "visual_obligation"
        ):

            return True

        # =================================================
        # 🔥 DIALOG IMAGE UNDERSTANDING
        # =================================================

        t = text.lower()

        visual_context_words = [

            "самолет",
            "самолёт",
            "корабль",
            "море",
            "небо",
            "космос",
            "машина",
            "человек",
            "девушка",
            "город",
            "лес",
            "кот",
            "собака",
            "картинка",
            "изображение",
            "нарисуй",
            "создай",
            "сделай"
        ]

        if any(
            w in t
            for w in visual_context_words
        ):

            return True

        return False

    def evaluate(self, text, context):

        score = super().evaluate(
            text,
            context
        )

        cognition = context.get(
            "cognition",
            {}
        )

        semantic = context.get(
            "semantic",
            {}
        )

        if cognition.get(
            "prefer_visual"
        ):

            score += 0.3

        if cognition.get(
            "wants_visual",
            0.0
        ) >= 0.55:

            score += 0.5

        if semantic.get(
            "visual_obligation"
        ):

            score += 1.0

        return score

    async def handle(self, user_id, text, context, run):

        state = context.get("state", {})

        semantic = context.get(
            "semantic",
            {}
        )

        reasoning = context.get(
            "reasoning",
            {}
        )

        cognition = context.get(
            "cognition",
            {}
        )

        t = text.lower().strip()

        if is_image_locked(state):

            return {
                "type": "text",
                "data":
                    "⏳ Уже генерирую изображение..."
            }

        # =================================================
        # 🔥 CONTINUATION SUPPORT
        # =================================================

        if (
            reasoning.get(
                "continuation_target"
            ) == "image"
            and len(t) <= 50
        ):

            last_prompt = state.get(
                "last_image_prompt"
            )

            if last_prompt:

                continuation_words = [
                    "да",
                    "ага",
                    "ок",
                    "окей",
                    "давай",
                    "подходит",
                    "ещё",
                    "продолжай",
                    "сделай",
                    "создай",
                    "жду"
                ]

                if any(
                    w in t
                    for w in continuation_words
                ):

                    if is_repeat_generation_blocked(
                        state
                    ):

                        return {
                            "type": "text",
                            "data":
                                "⏳ Не дублирую генерацию"
                        }

                    text = last_prompt

        # =================================================
        # 🔥 APRIL EXECUTION AUTHORITY
        # =================================================

        should_execute = False

        if semantic.get(
            "should_execute"
        ):

            should_execute = True

        if cognition.get(
            "prefer_visual"
        ):

            should_execute = True

        if cognition.get(
            "wants_visual",
            0.0
        ) >= 0.55:

            should_execute = True

        if cognition.get(
            "wants_result",
            0.0
        ) >= 0.7:

            should_execute = True

        if semantic.get(
            "visual_obligation"
        ):

            should_execute = True

        if reasoning.get(
            "continuation_target"
        ) == "image":

            should_execute = True

        if not should_execute:

            return {
                "type": "text",
                "data":
                    "⚠️ Недостаточно execution intent"
            }

        state["image_locked"] = True

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
                and result.get("type") == "image"
            ):

                state["last_image_prompt"] = text

                mark_generation_time(state)

                return result

            return {
                "type": "error",
                "data":
                    "🎨 Ошибка генерации"
            }

        finally:

            unlock_image(state)


# =====================================================
# 🖼 IMAGE EDIT
# =====================================================

class ImageEditRoom(Room):

    name = "image_edit"

    def can_handle(self, text, context):

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get("room") == self.name:

            confidence = semantic.get(
                "confidence",
                0.0
            )

            if confidence >= 0.6:
                return True

        return False

    def evaluate(self, text, context):

        return super().evaluate(
            text,
            context
        )

    async def handle(self, user_id, text, context, run):

        state = context.get("state", {})

        ctx = state.get("image_context")

        if not ctx or not ctx.get("path"):

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
# 🧠 SCIENCE
# =====================================================

class SafeScienceRoom(ScienceRoom):

    name = "science"

    def can_handle(self, text, context):

        semantic = context.get(
            "semantic",
            {}
        )

        if semantic.get("room") == self.name:

            confidence = semantic.get(
                "confidence",
                0.0
            )

            if confidence >= 0.6:
                return True

        return False

    def evaluate(self, text, context):

        return super().evaluate(
            text,
            context
        )


# =====================================================
# 💬 TEXT
# =====================================================

class TextRoom(Room):

    name = "text"

    def can_handle(self, text, context):
        return True

    def evaluate(self, text, context):

        score = 0.1

        cognition = context.get(
            "cognition",
            {}
        )

        if cognition.get(
            "prefer_execution"
        ):

            score -= 0.08

        if cognition.get(
            "prefer_visual"
        ):

            score -= 0.05

        if cognition.get(
            "dialog_fatigue",
            0.0
        ) >= 0.7:

            score -= 0.03

        return max(score, 0.01)

    async def handle(self, user_id, text, context, run):

        from blocks.text_module import (
            process as text_process
        )

        cognition = context.get(
            "cognition",
            {}
        )

        if (
            cognition.get("prefer_visual")
            and cognition.get("wants_result", 0.0) >= 0.6
        ):

            return {
                "type": "image_task",
                "prompt": text
            }

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
# 🚀 ROOMS ORDER
# =====================================================

ROOMS = [

    ImageEditRoom(),
    ImageGenerateRoom(),
    SafeScienceRoom(),
    TextRoom(),
]
