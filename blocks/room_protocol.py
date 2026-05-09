class Room:

    name = "base"

    # =====================================================
    # 🔥 LEGACY SUPPORT
    # =====================================================

    def can_handle(self, text, context):
        return False

    # =====================================================
    # 🔥 SEMANTIC EVALUATION
    # =====================================================

    def evaluate(self, text, context):

        semantic = context.get("semantic", {})

        room = semantic.get("room")

        if room == self.name:

            return semantic.get(
                "confidence",
                0.5
            )

        return 0.0

    # =====================================================
    # 🔥 EXECUTION
    # =====================================================

    async def handle(
        self,
        user_id,
        text,
        context,
        run
    ):
        return None
