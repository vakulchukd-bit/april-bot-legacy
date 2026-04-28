from blocks.room_protocol import Room

# === TRIG ROOM 🔥 ===
from blocks.trig_room import TrigRoom

# === SCIENCE ROOM 🔥 ===
from blocks.science_room import ScienceRoom

# === IMAGE GENERATE ===
from blocks.image_module import process as image_generate


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

        if text.lower().strip() in ["да", "ага", "ок", "окей", "давай", "согласен", "подходит"]:
            text = state.get("last_image_prompt", text)

        result = await run(
            context["chat_id"],
            image_generate(user_id, text, state)
        )

        if result and result.get("type") == "image":
            state["last_image_prompt"] = text
            return result

        return {"type": "error", "data": "🎨 Ошибка генерации"}


# === IMAGE EDIT ===
from blocks.image_edit_module import process as image_edit
from blocks.image_system import analyze_image


class ImageEditRoom(Room):
    name = "image_edit"

    def can_handle(self, text, context):
        ctx = context.get("image")
        if not ctx or not ctx.get("path"):
            return False

        t = text.lower()

        return any(v in t for v in [
            "измени", "добавь", "убери",
            "сделай", "замени", "поменяй"
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

        if not ctx or not ctx.get("path"):
            return {"type": "error", "data": "⚠️ Нет изображения"}

        new_prompt = (ctx.get("hint") or "изображение") + ", " + text

        result = await run(
            context["chat_id"],
            image_edit(user_id, ctx["path"], new_prompt)
        )

        return result


# === TEXT (ФИКС) ===
class TextRoom(Room):
    name = "text"

    def can_handle(self, text, context):
        return False  # 🔥 КЛЮЧЕВОЙ ФИКС

    def evaluate(self, text, context):
        return 0.0


# === РЕЕСТР ===
ROOMS = [
    TrigRoom(),
    ScienceRoom(),
    ImageEditRoom(),
    ImageGenerateRoom(),
    # TextRoom убран из активного перехвата
]
