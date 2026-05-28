# =====================================================
# 🧠 APRIL BASE ROOM
# =====================================================
#
# APRIL_FILE_ID:
# APRIL_BASE_ROOM
#
# ROLE:
# ABSTRACT_ROOM_INTERFACE
#
# INPUT:
# USER_TEXT
# SEMANTIC_CONTEXT
# EXECUTION_CONTEXT
# RUN_INTERFACE
#
# OUTPUT:
# ROOM_CONFIDENCE
# ROOM_EXECUTION_RESULT
# ROOM_ROUTING_SIGNAL
#
# DEPENDENCIES:
# excrouter
# semantic_core
# cognition
# response_decision
# room_registry
#
# =====================================================
#
# APRIL BASE ROOM
#
# Этот слой является:
#
# - abstract room interface;
# - orchestration-safe contract;
# - semantic-compatible execution node;
# - continuity-aware room adapter.
#
# =====================================================
# 🔥 IMPORTANT
# =====================================================
#
# Этот слой НЕ:
#
# - Telegram room;
# - dispatcher authority;
# - routing override;
# - execution controller.
#
# =====================================================
# 🌐 WEB-FIRST ARCHITECTURE
# =====================================================
#
# Room system подготовлен под:
#
# - Web April;
# - multimodal orchestration;
# - renderer-safe routing;
# - future room scaling;
# - cognition-first execution.
#
# =====================================================

print(
    "🧠 APRIL BASE ROOM LOADED"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "excrouter",

    "target":
        "room",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "source":
        "room",

    "target":
        "executor",

    "isolated":
        True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

ROOM_PATCH_LOG = []

def safe_room_log(*args):

    try:

        print(
            "APRIL ROOM:",
            *args
        )

        ROOM_PATCH_LOG.append(
            " ".join(
                [str(x) for x in args]
            )
        )

    except:
        pass


# =====================================================
# 🧠 BASE ROOM
# =====================================================

class Room:

    # =====================================================
    # 🔥 CORE
    # =====================================================

    name = "base"

    room_type = "abstract"

    web_space_ready = True

    renderer_safe = True

    continuity_safe = True

    orchestration_safe = True

    # =====================================================
    # 🔥 LEGACY SUPPORT
    # =====================================================

    def can_handle(
        self,
        text,
        context
    ):

        """
        Legacy compatibility layer.

        НЕ используется
        как primary routing authority.
        """

        safe_room_log(
            f"{self.name} LEGACY CHECK"
        )

        return False

    # =====================================================
    # 🔥 SEMANTIC EVALUATION
    # =====================================================

    def evaluate(
        self,
        text,
        context
    ):

        """
        Lightweight room evaluation.

        Room НЕ принимает
        финальное routing decision.

        Room только:
        - оценивает relevance;
        - помогает orchestration;
        - stabilizes routing.
        """

        safe_room_log(
            f"{self.name} EVALUATE START"
        )

        semantic = context.get(
            "semantic",
            {}
        )

        room = semantic.get(
            "room"
        )

        if room == self.name:

            confidence = semantic.get(
                "confidence",
                0.5
            )

            safe_room_log(

                f"{self.name} MATCH:",
                confidence
            )

            return confidence

        safe_room_log(
            f"{self.name} NO MATCH"
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

        """
        Room execution bridge.

        Room:
        - получает stabilized context;
        - работает через orchestration;
        - возвращает machine-safe result.
        """

        safe_room_log(
            f"{self.name} HANDLE START"
        )

        return None

    # =====================================================
    # 🔥 FUTURE SAFE API
    # =====================================================

    def build_room_state(
        self,
        context=None
    ):

        context = context or {}

        return {

            "room":
                self.name,

            "room_type":
                self.room_type,

            "renderer_safe":
                self.renderer_safe,

            "continuity_safe":
                self.continuity_safe,

            "web_space_ready":
                self.web_space_ready,

            "machine_isolated":
                True
        }

    # =====================================================
    # 🔥 ROOM METADATA
    # =====================================================

    def get_room_metadata(self):

        return {

            "name":
                self.name,

            "type":
                self.room_type,

            "web_ready":
                True,

            "renderer_safe":
                True,

            "continuity_safe":
                True,

            "telegram_bound":
                False,

            "machine_role":
                "execution_node"
        }
