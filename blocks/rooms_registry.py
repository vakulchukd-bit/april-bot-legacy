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
# 🎨 IMAGE GENERATE
# =====================================================

class ImageGenerateRoom(Room):

    name = "image_generate"

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

        semantic = context.get(
            "semantic",
            {}
        )

        reasoning = context.get(
            "reasoning",
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
                    "сделай"
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
        # 🔥 EXECUTION AUTHORITY
        # =================================================

        if not semantic.get(
            "should_execute",
            False
        ):

            return {
                "type": "text",
                "data":
                    "⚠️ Выполнение не подтверждено"
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

        semantic = context.get(
            "semantic",
            {}
        )

        reasoning = context.get(
            "reasoning",
            {}
        )

        # =================================================
        # 🔥 EXECUTION PRIORITY
        # =================================================

        if semantic.get(
            "should_execute"
        ):

            return 0.01

        # =================================================
        # 🔥 DIALOG FATIGUE
        # =================================================

        if reasoning.get(
            "dialog_overextended"
        ):

            return 0.05

        return 0.1

    async def handle(self, user_id, text, context, run):

        from blocks.text_module import (
            process as text_process
        )

        reasoning = context.get(
            "reasoning",
            {}
        )

        semantic = context.get(
            "semantic",
            {}
        )

        # =================================================
        # 🔥 RESPONSE ECONOMY
        # =================================================

        text_input = text

        if reasoning.get(
            "response_economy"
        ) == "minimal":

            text_input = (
                "Коротко и по делу:\n\n"
                + text
            )

        # =================================================
        # 🔥 EXECUTION AVOIDANCE
        # =================================================

        if semantic.get(
            "should_execute"
        ):

            return {
                "type": "text",
                "data":
                    "⚠️ Требуется execution room"
            }

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

    # 🔥 IMAGE FIRST
    ImageEditRoom(),
    ImageGenerateRoom(),

    # 🔥 SCIENCE
    SafeScienceRoom(),

    # 🔥 LAST FALLBACK
    TextRoom(),
]
