from C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    UniversalArtifactContract,
    create_artifact,
)

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
    # 🔥 PROFESSIONAL ROOM CONTRACT
    # =====================================================

    artifact_type = None
    artifact_version = "1.0"

    quality_score = 0.0
    confidence_score = 0.0
    completeness_score = 0.0


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

        confidence = semantic.get(
            "confidence",
            0.5
        )

        required_domains = semantic.get(
            "required_domains",
            []
        )

        candidate_domains = semantic.get(
            "candidate_domains",
            []
        )

        if self.name in required_domains:

            safe_room_log(
                f"{self.name} DOMAIN MATCH:",
                confidence
            )

            return confidence

        if self.name in candidate_domains:

            safe_room_log(
                f"{self.name} CANDIDATE MATCH:",
                confidence
            )

            return max(
                confidence * 0.8,
                0.4
            )

        room = semantic.get(
            "room"
        )

        if room == self.name:

            safe_room_log(
                f"{self.name} LEGACY MATCH:",
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
    # 🔥 PROFESSIONAL ENGINES
    # =====================================================

    def build_work_order(self, context=None):
        context = context or {}
        return {
            "goal": context.get("goal"),
            "purpose": context.get("purpose"),
            "role": context.get("role"),
            "dependencies": context.get("dependencies", []),
            "expected_artifact": context.get("expected_artifact"),
            "quality_target": context.get("quality_target", 0.95),
            "active_scene": context.get("active_scene")
        }

    def build_context_contract(self, context=None):
        context = context or {}
        return {
            "memory": context.get("memory"),
            "history": context.get("history"),
            "goals": context.get("goals"),
            "focus": context.get("focus"),
            "active_scene": context.get("active_scene"),
            "visual_context": context.get("visual_context"),
            "vision_context": context.get("vision_context"),
            "user_context": context.get("user_context"),
            "state_context": context.get("state_context")
        }

    def knowledge_engine(self, context):
        return context

    def generation_engine(self, context):
        return None

    def validation_engine(self, artifact):
        return True

    def quality_engine(self, artifact):
        return {
            "quality_score": self.quality_score,
            "confidence_score": self.confidence_score,
            "completeness_score": self.completeness_score
        }

    def artifact_builder(self, artifact):
        return artifact

    def room_start(self):
        safe_room_log(f"{self.name} ROOM_START")

    def room_task(self, task):
        safe_room_log(f"{self.name} ROOM_TASK", task)

    def room_generation(self):
        safe_room_log(f"{self.name} ROOM_GENERATION")

    def room_validation(self):
        safe_room_log(f"{self.name} ROOM_VALIDATION")

    def room_score(self):
        safe_room_log(f"{self.name} ROOM_SCORE")

    def room_artifact(self):
        safe_room_log(f"{self.name} ROOM_ARTIFACT")

    def room_end(self):
        safe_room_log(f"{self.name} ROOM_END")


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


# =====================================================
# APRIL FIBER CHANNEL ADAPTER
# =====================================================

class FiberRoom(Room):
    """Universal room adapter for April fiber channel."""

    def accept_request(self, request: MachineRequest):
        self.room_start()
        return request

    def build_machine_response(self, artifact_type: str, payload: dict):
        artifact = create_artifact(
            artifact_type=artifact_type,
            room_source=self.name,
            data=payload,
        )
        response = MachineResponse()
        response.artifacts.append(artifact)
        return response

    def export_contract(self, response: MachineResponse):
        contract = UniversalArtifactContract()
        if response.artifacts:
            contract.artifact = response.artifacts[0]
            contract.payload.artifacts = [
                a.data for a in response.artifacts
            ]
        contract.transport.origin = self.name
        contract.transport.destination = "executor"
        contract.transport.pipeline_stage = "room_output"
        return contract
