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

        t = text.lower().strip()

        triggers = [
            "сгенерируй",
            "создай изображение",
            "создай картинку",
            "нарисуй",
            "generate image",
            "draw image"
        ]

        if any(w in t for w in triggers):
            return True

        state = context.get("state", {})

        if state.get("last_image_prompt"):

            if t in [
                "да",
                "ага",
                "ок",
                "окей",
                "давай",
                "подходит"
            ]:
                return True

        return False

    def evaluate(self, text, context):

        score = 0.0

        if context.get("task_type") == "image_generate":
            score += 1.0

        if self.can_handle(text, context):
            score += 0.6

        return score

    async def handle(self, user_id, text, context, run):

        state = context.get("state", {})

        t = text.lower().strip()

        if is_image_locked(state):

            return {
                "type": "text",
                "data":
                    "⏳ Уже генерирую изображение..."
            }

        if t in [
            "да",
            "ага",
            "ок",
            "окей",
            "давай",
            "подходит"
        ]:

            if is_repeat_generation_blocked(state):

                return {
                    "type": "text",
                    "data":
                        "⏳ Не дублирую генерацию"
                }

            text = state.get(
                "last_image_prompt",
                text
            )

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

        state = context.get("state", {})

        ctx = state.get("image_context")

        if not ctx or not ctx.get("path"):
            return False

        t = text.lower()

        triggers = [
            "измени",
            "добавь",
            "убери",
            "замени",
            "сделай",
            "улучши",
            "осветли",
            "затемни"
        ]

        return any(v in t for v in triggers)

    def evaluate(self, text, context):

        score = 0.0

        if context.get("task_type") == "image_edit":
            score += 1.0

        if self.can_handle(text, context):
            score += 0.7

        return score

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

        # =================================================
        # 🔥 SEMANTIC AUTHORITY
        # =================================================

        if semantic.get("room") == self.name:

            confidence = semantic.get(
                "confidence",
                0.0
            )

            if confidence >= 0.6:
                return True

        # =================================================
        # 🔥 LEGACY FALLBACK
        # =================================================

        state = context.get(
            "state",
            {}
        )

        dialog = (
            state.get(
                "dialog_state",
                {}
            ) or {}
        )

        # 🔥 IMAGE PRIORITY
        if dialog.get("intent") == "image":
            return False

        t = text.lower()

        math_words = [
            "график",
            "уравнение",
            "функция",
            "sin(",
            "cos(",
            "tan(",
            "y="
        ]

        if any(w in t for w in math_words):
            return True

        if "=" in t:

            has_digits = any(
                ch.isdigit()
                for ch in t
            )

            if has_digits:
                return True

        return False


# =====================================================
# 💬 TEXT
# =====================================================

class TextRoom(Room):

    name = "text"

    def can_handle(self, text, context):
        return True

    def evaluate(self, text, context):
        return 0.1

    async def handle(self, user_id, text, context, run):

        from blocks.text_module import (
            process as text_process
        )

        result = await run(
            context["chat_id"],
            text_process(
                user_id,
                text,
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

    # 🔥 SCIENCE ONLY AFTER IMAGE
    SafeScienceRoom(),

    # 🔥 LAST FALLBACK
    TextRoom(),
]
