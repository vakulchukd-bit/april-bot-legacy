from blocks.room_protocol import Room

# === IMAGE GENERATE ===
from blocks.image_module import process as image_generate

class ImageGenerateRoom(Room):
    name = "image_generate"

    def can_handle(self, text, context):
        t = text.lower()
        return any(w in t for w in [
            "сгенерируй", "создай", "нарисуй", "сделай",
            "generate", "draw"
        ])

    def decide(self, text):
        t = text.lower()
        words = t.split()

        # ❌ вопросы
        if any(q in t for q in ["что", "как", "почему", "зачем", "можешь", "?"]):
            return "ask"

        # ❌ нет конкретики
        if len(words) <= 2:
            return "ask"

        # ❌ "сделай картинку"
        if "картинку" in words:
            idx = words.index("картинку")
            if idx == len(words) - 1:
                return "ask"

        if "изображение" in words:
            idx = words.index("изображение")
            if idx == len(words) - 1:
                return "ask"

        return "generate"

    async def handle(self, user_id, text, context, run):
        decision = self.decide(text)

        if decision == "ask":
            return {
                "type": "text",
                "data": "🎨 Что именно нужно создать?\nНапример: лес, город, человек 🙂"
            }

        if decision == "generate":
            result = await run(
                context["chat_id"],
                image_generate(user_id, text, context["state"])
            )

            if result and result.get("type") == "image":
                return result

        return None


# === IMAGE EDIT ===
from blocks.image_edit_module import process as image_edit
from blocks.image_system import analyze_image

class ImageEditRoom(Room):
    name = "image_edit"

    def can_handle(self, text, context):
        ctx = context.get("image")
        return ctx is not None and ctx.get("path") is not None

    def decide(self, text):
        t = text.lower()

        # ❌ вопросы
        if any(q in t for q in ["что", "как", "почему", "?", "думаешь"]):
            return "ignore"

        # ✅ команды
        if any(v in t for v in [
            "измени", "добавь", "убери", "осветли",
            "затемни", "замени", "поменяй", "улучши"
        ]):
            return "edit"

        return "ignore"

    async def handle(self, user_id, text, context, run):
        decision = self.decide(text)

        if decision != "edit":
            return None

        ctx = context["image"]

        if not ctx or not ctx.get("path"):
            return None

        if not ctx.get("hint"):
            try:
                ctx["hint"] = await analyze_image(ctx["path"])
            except:
                ctx["hint"] = "изображение"

        new_prompt = ctx["hint"] + ", IMPORTANT: " + text

        result = await run(
            context["chat_id"],
            image_edit(user_id, ctx["path"], new_prompt)
        )

        if result and result.get("type") == "image":
            return result

        return None


# === TEXT ===
from blocks.text_module import process as text_process

class TextRoom(Room):
    name = "text"

    def can_handle(self, text, context):
        return True

    async def handle(self, user_id, text, context, run):
        result = await run(
            context["chat_id"],
            text_process(user_id, text, context["state"])
        )

        return {
            "type": "text",
            "data": result["content"]
        }


# === РЕЕСТР ===
ROOMS = [
    ImageEditRoom(),
    ImageGenerateRoom(),
    TextRoom()
]
