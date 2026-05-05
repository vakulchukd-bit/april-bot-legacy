from blocks.room_protocol import Room

# === SCIENCE ROOM 🔥 ===
from blocks.science_room import ScienceRoom

# === IMAGE ENGINE (НОВОЕ) ===
from blocks.image_engine import generate as image_generate
from blocks.image_engine import edit as image_edit_engine
from blocks.image_system import analyze_image


# 🔥 ДОБАВЛЕНО: защита от повторной генерации
import time

def is_repeat_generation_blocked(state):
    ts = state.get("last_image_time")
    if not ts:
        return False
    return (time.time() - ts) < 8  # 8 секунд защита

def mark_generation_time(state):
    state["last_image_time"] = time.time()


class ImageGenerateRoom(Room):
    name = "image_generate"

    def can_handle(self, text, context):
        t = text.lower().strip()

        if any(w in t for w in [
            "сгенерируй", "создай изображение", "создай картинку",
            "нарисуй", "generate image", "draw image"
        ]):
            return True

        state = context.get("state", {})
        if state.get("last_image_prompt"):
            if t in ["да", "ага", "ок", "окей", "давай", "согласен", "подходит"]:
                return True

        return False

    def evaluate(self, text, context):
        t = text.lower()
        score = 0.0

        if context.get("task_type") == "image_generate":
            score += 1.0

        if self.can_handle(text, context):
            score += 0.6

        if any(w in t for w in ["картин", "изображ", "арт", "рисунок"]):
            score += 0.5

        if any(w in t for w in ["сделай", "создай", "нарисуй"]):
            score += 0.4

        return score

    async def handle(self, user_id, text, context, run):
        state = context.get("state", {})

        t = text.lower().strip()

        # 🔥 PATCH: защита от повторного запуска
        if t in ["да", "ага", "ок", "окей", "давай", "согласен", "подходит"]:
            if is_repeat_generation_blocked(state):
                return {
                    "type": "text",
                    "data": "⏳ Уже сделал недавно, не дублирую"
                }

        if t in ["да", "ага", "ок", "окей", "давай", "согласен", "подходит"]:
            text = state.get("last_image_prompt", text)

        result = await run(
            context["chat_id"],
            image_generate(user_id, text, state)
        )

        if result and result.get("type") == "image":
            state["last_image_prompt"] = text

            # 🔥 PATCH: фиксируем время генерации
            mark_generation_time(state)

            return result

        return {"type": "error", "data": "🎨 Ошибка генерации"}


# === IMAGE EDIT ===
class ImageEditRoom(Room):
    name = "image_edit"

    def can_handle(self, text, context):
        ctx = context.get("image")
        if not ctx or not ctx.get("path"):
            return False

        t = text.lower()

        return any(v in t for v in [
            "измени", "добавь", "убери",
            "сделай", "замени", "поменяй",
            "осветли", "затемни", "улучши"
        ])

    def evaluate(self, text, context):
        t = text.lower()
        score = 0.0

        if context.get("task_type") == "image_edit":
            score += 1.0

        if self.can_handle(text, context):
            score += 0.7

        return score

    async def handle(self, user_id, text, context, run):
        ctx = context["image"]
        state = context.get("state", {})

        if not ctx or not ctx.get("path"):
            return {
                "type": "error",
                "data": "⚠️ Нет изображения для редактирования"
            }

        if not ctx.get("hint"):
            try:
                ctx["hint"] = await analyze_image(ctx["path"])
            except:
                ctx["hint"] = "изображение"

        new_prompt = ctx["hint"] + ", IMPORTANT: " + text

        image_bytes = state.get("image_current")

        result = await run(
            context["chat_id"],
            image_edit_engine(user_id, image_bytes, new_prompt, state)
        )

        return result


# === TEXT (ВОССТАНОВЛЕН КАК FALLBACK) ===
class TextRoom(Room):
    name = "text"

    def can_handle(self, text, context):
        return True

    def evaluate(self, text, context):
        return 0.1

    async def handle(self, user_id, text, context, run):
        from blocks.text_module import process as text_process

        result = await run(
            context["chat_id"],
            text_process(user_id, text, context.get("state"), context.get("energy"))
        )

        return {
            "type": "text",
            "data": result.get("content", "⚠️ Пустой ответ")
        }


# === РЕЕСТР ===
ROOMS = [
    ScienceRoom(),
    ImageEditRoom(),
    ImageGenerateRoom(),
    TextRoom(),
]
