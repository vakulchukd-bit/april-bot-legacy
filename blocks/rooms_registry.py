from blocks.room_protocol import Room

# === IMAGE GENERATE ===
from blocks.image_module import process as image_generate

class ImageGenerateRoom(Room):
    name = "image_generate"

    def can_handle(self, text, context):
        # 🔥 теперь опираемся НЕ только на текст, а на intent
        if context.get("intent") == "generate_image":
            return True

        t = text.lower()
        return any(w in t for w in [
            "сгенерируй", "создай", "нарисуй",
            "картин", "изображен",
            "generate", "draw"
        ])

    async def handle(self, user_id, text, context, run):
        result = await run(
            context["chat_id"],
            image_generate(user_id, text, context["state"])
        )

        if result and result.get("type") == "image":
            # 🔥 очищаем pending_action после выполнения
            context["state"]["pending_action"] = None
            return result

        return None


# === IMAGE EDIT ===
from blocks.image_edit_module import process as image_edit
from blocks.image_system import analyze_image

class ImageEditRoom(Room):
    name = "image_edit"

    def can_handle(self, text, context):
        ctx = context.get("image")
        if not ctx or not ctx.get("path"):
            return False

        # 🔥 приоритет через intent
        if context.get("intent") == "edit_image":
            return True

        t = text.lower()

        return any(v in t for v in [
            "измени", "добавь", "убери",
            "замени", "поменяй",
            "осветли", "затемни", "улучши"
        ])

    async def handle(self, user_id, text, context, run):
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
            # 🔥 очищаем pending_action
            context["state"]["pending_action"] = None
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
