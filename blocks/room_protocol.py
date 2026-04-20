class Room:
    name = "base"

    def can_handle(self, text, context):
        return False

    async def handle(self, user_id, text, context, run):
        return None
