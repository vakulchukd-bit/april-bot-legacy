from blocks.room_protocol import Room

# === IMAGE GENERATE ===
from blocks.image_module import process as image_generate

class ImageGenerateRoom(Room):
    name = "image_generate"

    def can_handle(self, text, context):
        t = text.lower()

        triggers = [
            "сгенерируй", "создай", "нарисуй",
            "сделай картинку", "сделай изображение",
            "generate image", "draw"
        ]

        return any(word in t for word in triggers)

    async def handle(self, user_id, text, context, run):
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
        return context.get("image") is not None

    async def handle(self, user_id, text, context, run):
        ctx = context["image"]

        if not ctx or not ctx.get("path"):
            return None

        if not ctx.get("hint"):
            try:
                ctx["hint"] = await analyze_image(ctx["path"])
            except:
                ctx["hint"] = "изображение"

        base = ctx["hint"]
        new_prompt = base + ", IMPORTANT: " + text

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
