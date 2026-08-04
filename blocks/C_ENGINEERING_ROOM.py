# =====================================================
# APRIL C_ENGINEERING_ROOM
# =====================================================

from __future__ import annotations

from typing import Any, Dict, Optional

from blocks.room_protocol import Room
from blocks.C_ARTIFACT_CONTRACT import create_artifact


class EngineeringRoom(Room):
    name = "engineering"
    room_type = "professional"
    ROOM_ID = "ENGINEERING_ROOM"
    ARTIFACT_TYPE = "function"

    quality_score = 1.0
    confidence_score = 1.0
    completeness_score = 1.0

    ENGINEERING_KEYWORDS = (
        "engineering",
        "engineer",
        "инженер",
        "инженерия",
        "техника",
        "техничес",
        "project",
        "проект",
        "architecture",
        "архитект",
        "mechanical",
        "electrical",
        "civil",
        "process",
        "diagnostic",
        "optimization",
        "разработка",
        "конструкт",
    )

    # =================================================
    # INTERNAL HELPERS
    # =================================================

    def _get_context_mapping(self, context: Any) -> Dict[str, Any]:
        if isinstance(context, dict):
            return context
        mapping: Dict[str, Any] = {}
        try:
            mapping.update(
                {k: v for k, v in vars(context).items() if not k.startswith("_")}
            )
        except Exception:
            pass
        return mapping

    def _is_engineering_request(self, text: str, context: Any) -> bool:
        haystack_parts = [text or ""]
        ctx = self._get_context_mapping(context)

        for key in ("goal", "topic", "intent", "domain", "room", "active_topic"):
            value = ctx.get(key)
            if isinstance(value, str):
                haystack_parts.append(value)

        semantic = ctx.get("semantic")
        if isinstance(semantic, dict):
            for key in ("domain", "topic", "intent", "room", "preferred_room"):
                value = semantic.get(key)
                if isinstance(value, str):
                    haystack_parts.append(value)

            domains = semantic.get("domains") or semantic.get("required_domains") or []
            if isinstance(domains, (list, tuple, set)):
                haystack_parts.extend([str(item) for item in domains if item])

            room = semantic.get("room")
            if isinstance(room, str):
                haystack_parts.append(room)

        chat_text = " ".join(haystack_parts).lower()
        if "engineering_room" in chat_text or "engineer" in chat_text:
            return True

        return any(keyword in chat_text for keyword in self.ENGINEERING_KEYWORDS)

    def _build_internal_signal_text(self, topic: str) -> str:
        topic = (topic or "").strip()
        if topic:
            return f"Engineering room internal signal for: {topic}"
        return "Engineering room internal signal"

    def _build_payload(self, topic: str) -> Dict[str, Any]:
        structured = {
            "domain": "engineering",
            "topic": topic,
            "analysis": {},
            "capabilities": [
                "system_design",
                "architecture",
                "mechanical_engineering",
                "electrical_engineering",
                "civil_engineering",
                "process_engineering",
                "technical_analysis",
                "optimization",
                "diagnostics",
                "project_planning",
            ],
        }

        signal_text = self._build_internal_signal_text(topic)

        return {
            "answer": signal_text,
            "content": signal_text,
            "summary": signal_text,
            "text": signal_text,
            "display_text": signal_text,
            "signal": structured,
            "payload": structured,
            "analysis": {},
            "capabilities": list(structured["capabilities"]),
            "machine_only": True,
            "human_visible": False,
            "presentation": {
                "payload_type": "function",
                "scene_block": "function",
                "renderer": "FunctionBlock",
                "viewer": "FunctionBlock",
                "priority": 100,
                "complexity": "internal",
                "layout": "single",
            },
            "render_blocks": [],
        }

    # =================================================
    # ROOM EXECUTION
    # =================================================

    async def handle(
        self,
        user_id,
        text,
        context,
        run,
    ):
        print("ENGINEERING ROOM HANDLE START")

        if not self._is_engineering_request(text, context):
            return None

        artifact = self.process({"topic": text})

        return {
            "type": "artifact",
            "artifact": artifact,
        }

    # =================================================
    # ARTIFACT FACTORY
    # =================================================

    def process(self, task: Dict[str, Any]):
        topic = task.get("topic", "")
        artifact = create_artifact(
            artifact_type=self.ARTIFACT_TYPE,
            room_source=self.ROOM_ID,
            data=self._build_payload(topic),
        )

        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0

        # Keep the artifact explicitly internal so downstream scene builders
        # can preserve the canonical provider answer instead of rendering this
        # room payload as the visible user response.
        try:
            artifact.render.machine_only = True
            artifact.render.human_visible = False
            artifact.render.web_block = "FunctionBlock"
            artifact.render.viewer = "FunctionBlock"
            artifact.render.renderer = "FunctionBlock"
        except Exception:
            pass

        return artifact


ROOM = EngineeringRoom()
