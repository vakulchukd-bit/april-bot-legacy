from blocks.room_protocol import Room

# === IMAGE GENERATE ===
from blocks.image_module import process as image_generate

class ImageGenerateRoom(Room):
    name = "image_generate"

    def can_handle(self, text, context):
        if context.get("intent") != "generate_image":
            return False

        if not context["state"].get("pending_action"):
            return False

        return True

    async def handle(self, user_id, text, context, run):
        # 🔥 ВАЖНО: УБРАЛИ run_with_typing
        result = await image_generate(user_id, text, context["state"])

        if result and result.get("type") == "image":
            context["state"]["pending_action"] = None
            return result

        return result  # 🔥 возвращаем даже если ошибка


# === IMAGE EDIT ===
from blocks.image_edit_module import process as image_edit
from blocks.image_system import analyze_image

class ImageEditRoom(Room):
    name = "image_edit"

    def can_handle(self, text, context):
        ctx = context.get("image")

        if not ctx or not ctx.get("path"):
            return False

        if context.get("intent") != "edit_image":
            return False

        if not context["state"].get("pending_action"):
            return False

        return True

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

        # 🔥 УБРАЛИ run_with_typing
        result = await image_edit(user_id, ctx["path"], new_prompt)

        if result and result.get("type") == "image":
            context["state"]["pending_action"] = None
            return result

        return result


# === TEXT ===
from blocks.text_module import process as text_process

class TextRoom(Room):
    name = "text"

    def can_handle(self, text, context):
        if context["state"].get("pending_action"):
            return False
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
