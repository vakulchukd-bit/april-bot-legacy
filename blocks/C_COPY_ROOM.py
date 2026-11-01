"""Shared Copy Room: emits a plain-text copy artifact for both Free and Premium.

The room does not interpret user language or apply plan limits. The active
Free/Premium Interpretation branch selects it and enforces its own budget.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict
import uuid

from blocks.C_ARTIFACT_CONTRACT import create_artifact

ROOM_ID = "C_COPY_ROOM"
ARTIFACT_TYPE = "copy"
RENDERER = "CopyBlock"


def _object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _identity(task: Dict[str, Any]) -> Dict[str, Any]:
    scene = _object(task.get("scene"))
    scene_id = str(task.get("scene_id") or scene.get("scene_id") or f"scene_{uuid.uuid4().hex[:12]}")
    turn_id = str(task.get("turn_id") or scene.get("turn_id") or f"turn_{uuid.uuid4().hex[:12]}")
    block_id = str(task.get("block_id") or scene.get("block_id") or f"copy_{uuid.uuid4().hex[:12]}")
    return {"scene_id": scene_id, "turn_id": turn_id, "flow_id": str(task.get("flow_id") or scene.get("flow_id") or ""),
            "block_id": block_id, "render_id": str(task.get("render_id") or scene.get("render_id") or f"{block_id}:render")}


class CopyRoom:
    name = ROOM_ID
    room_type = "text_renderer"
    artifact_type = ARTIFACT_TYPE
    artifact_version = "1.0"
    web_space_ready = True
    renderer_safe = True
    continuity_safe = True
    orchestration_safe = True

    def can_handle(self, text: Any, context: Any) -> bool:
        return self.evaluate(text, context) > 0

    def evaluate(self, text: Any, context: Any) -> float:
        ctx = _object(context)
        semantic = _object(ctx.get("semantic"))
        requested = semantic.get("requested_outputs") or ctx.get("requested_outputs") or []
        return 1.0 if "copy" in {str(item).lower() for item in requested if item} else 0.0

    def build_work_order(self, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ctx = dict(context or {})
        return {"scene_id": ctx.get("scene_id"), "turn_id": ctx.get("turn_id"), "flow_id": ctx.get("flow_id"),
                "block_id": ctx.get("block_id"), "render_id": ctx.get("render_id"),
                "payload": deepcopy(ctx.get("copy_payload") or ctx.get("payload") or {}),
                "title": ctx.get("title"), "content": ctx.get("content") or ctx.get("text")}

    def process(self, task: Dict[str, Any]):
        source = dict(task or {})
        payload = _object(source.get("payload") or source.get("copy_payload"))
        content = source.get("content") or source.get("text") or payload.get("content") or payload.get("text")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("C_COPY_ROOM requires non-empty plain text")
        identity = _identity(source)
        normalized = {"title": str(payload.get("title") or source.get("title") or ""),
                      "content": content, "text": content,
                      "copy_action": "clipboard", "scene": identity,
                      "room": ROOM_ID, "payload_version": "april.copy.v1"}
        artifact = create_artifact(artifact_type=ARTIFACT_TYPE, room_source=ROOM_ID,
            data={"title": normalized["title"], "content": content, "payload": normalized,
                  "renderer": RENDERER, "viewer": RENDERER, "scene_id": identity["scene_id"],
                  "turn_id": identity["turn_id"], "flow_id": identity["flow_id"],
                  "block_id": identity["block_id"], "render_id": identity["render_id"],
                  "text_companion_required": False})
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = artifact.quality.confidence_score = artifact.quality.completeness_score = 1.0
        return artifact

    def execute(self, machine_request: Any):
        return self.process(machine_request) if isinstance(machine_request, dict) else None

    async def handle(self, user_id, text, context, run):
        task = self.build_work_order(dict(context or {}))
        task.setdefault("content", text)
        return self.process(task)


ROOM = CopyRoom()



def attach_copy_block(render_blocks: Any, requested_outputs: Any, answer: Any = "") -> list[dict[str, Any]]:
    """Add one plain-text copy renderer from the text already generated this turn.

    The helper avoids asking the model to repeat the same answer in a second block.
    A provider-authored copy block always wins and is preserved unchanged.
    """
    blocks = [deepcopy(item) for item in (render_blocks or []) if isinstance(item, dict)]
    requested = {str(item).strip().lower() for item in (requested_outputs or []) if str(item).strip()}
    if "copy" not in requested:
        return blocks
    for block in blocks:
        if str(block.get("type") or block.get("artifact_type") or "").strip().lower() in {"copy", "copy_block", "copyable_text", "text_copy_block"}:
            block["type"] = "copy"
            block["artifact_type"] = "copy"
            block["renderer"] = RENDERER
            block["viewer"] = RENDERER
            return blocks
    text = str(answer or "")
    if not text.strip():
        fragments = []
        for block in blocks:
            if str(block.get("type") or block.get("artifact_type") or "").strip().lower() in {"text", "markdown", "message", "message_text", "answer"}:
                payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
                fragment = str(payload.get("content") or payload.get("text") or block.get("content") or block.get("text") or "")
                if fragment.strip():
                    fragments.append(fragment)
        text = "\n\n".join(fragments)
    if not text.strip():
        return blocks
    blocks.append({
        "type": "copy", "artifact_type": "copy", "renderer": RENDERER, "viewer": RENDERER,
        "payload": {"title": "", "content": text, "text": text, "copy_action": "clipboard"},
        "source_room": ROOM_ID,
    })
    return blocks
