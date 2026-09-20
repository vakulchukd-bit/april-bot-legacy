"""April — canonical scene presentation layer.

This module owns presentation formatting only.

Architecture law
----------------
Quantum Processor -> Scene Blueprint -> C_ARTIFACT_CONTRACT ->
this formatter -> one SceneSignal -> April Web.

It MUST NOT:
* call the Provider;
* inspect or decide dialogue intent;
* select a renderer from user keywords;
* create a second response;
* create fallback render routes;
* duplicate a scene block already present in the canonical scene.

Renderer identity is an input from the semantic scene / artifact contract.
This module only makes that already-decided block display-safe and preserves
relationships, order and scene continuity.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Iterable


APRIL_FILE_ID = "APRIL_PRESENTATION_FORMATTER_SCENE_V3"
PRESENTATION_ENGINE_VERSION = "april_scene_presentation_v3"
PRESENTATION_SIGNAL_VERSION = "scene_presentation_signal_v3"
MATH_ENGINE = "KaTeX"
MARKDOWN_ENGINE = "McDowell"

RENDERER_ALIASES = {
    "text": "MessageTextBlock",
    "markdown": "MessageTextBlock",
    "message": "MessageTextBlock",
    "message_text": "MessageTextBlock",
    "graph": "GraphBlock",
    "chart": "GraphBlock",
    "plot": "GraphBlock",
    "table": "TableBlock",
    "diagram": "GalleryBlock",
    "schematic": "GalleryBlock",
    "image": "GalleryBlock",
    "gallery": "GalleryBlock",
    "code": "CodeBlock",
    "link": "LinkCard",
    "formula": "MessageTextBlock",
    "math": "MessageTextBlock",
}

TYPE_ALIASES = {
    "markdown": "text",
    "chart": "graph",
    "plot": "graph",
    "schematic": "diagram",
    "math": "formula",
}

TEXT_TYPES = {"text", "markdown", "formula"}


def _s(value: Any) -> str:
    return str(value or "").strip()


def _d(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _l(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def normalize_type(value: Any) -> str:
    key = _s(value).lower()
    return TYPE_ALIASES.get(key, key or "text")


def normalize_renderer(value: Any, block_type: str) -> str:
    requested = _s(value).lower()
    if requested in RENDERER_ALIASES:
        return RENDERER_ALIASES[requested]
    if requested:
        return requested
    return RENDERER_ALIASES.get(normalize_type(block_type), "MessageTextBlock")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return _s(value)


def _fingerprint(value: Any) -> str:
    raw = json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def stable_block_id(scene_id: str, block: dict[str, Any], index: int) -> str:
    existing = _s(block.get("block_id") or block.get("id"))
    if existing:
        return existing
    material = {
        "scene_id": scene_id,
        "type": normalize_type(block.get("type") or block.get("artifact_type") or block.get("representation")),
        "role": _s(block.get("role") or block.get("text_role")),
        "index": index,
        "payload": block.get("payload"),
        "content": block.get("content") or block.get("text") or "",
    }
    return f"block_{_fingerprint(material)}"


def stable_render_id(scene_id: str, block_id: str, renderer: str) -> str:
    return f"render_{_fingerprint({'scene_id': scene_id, 'block_id': block_id, 'renderer': renderer})}"


def _blueprint_indexes(blueprint: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    nodes = {}
    for raw in _l(blueprint.get("nodes")):
        if not isinstance(raw, dict):
            continue
        node_id = _s(raw.get("block_id") or raw.get("id"))
        if node_id:
            nodes[node_id] = dict(raw)
    order = {}
    for idx, raw in enumerate(_l(blueprint.get("order"))):
        key = _s(raw)
        if key:
            order[key] = idx
    return nodes, order


def _relation_map(blueprint: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for raw in _l(blueprint.get("relations")):
        if not isinstance(raw, dict):
            continue
        source = _s(raw.get("from") or raw.get("source"))
        target = _s(raw.get("to") or raw.get("target"))
        if not source or not target:
            continue
        result.setdefault(source, []).append(target)
        result.setdefault(target, [])
    return result


def _content(block: dict[str, Any]) -> str:
    for key in ("content", "text", "answer", "summary", "display_text"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _semantic_visual_key(block: dict[str, Any]) -> str:
    """Return a stable key for transport duplicates of the same visual node."""
    block_type = normalize_type(block.get("type") or block.get("artifact_type") or block.get("representation"))
    payload = _d(block.get("payload"))

    if block_type in {"link", "file"}:
        url = _s(block.get("url") or block.get("href") or payload.get("url") or payload.get("href"))
        if url:
            return f"link:{url.split('#', 1)[0].rstrip('/').lower()}"

    # graph_data is an internal data carrier for graph artifacts, not a second
    # human-visible scene node.
    if block_type == "graph_data":
        name = _s(block.get("name") or payload.get("name"))
        return f"internal:graph_data:{name or _fingerprint(payload)}"

    return ""


def _prefer_block(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    existing_renderer = _s(existing.get("renderer")).lower()
    candidate_renderer = _s(candidate.get("renderer")).lower()
    if "linkcard" in candidate_renderer and "message" in existing_renderer:
        return candidate
    if "linkcard" in existing_renderer and "message" in candidate_renderer:
        return existing
    return existing

def canonicalize_scene_blocks(
    blocks: Iterable[Any] | None,
    *,
    scene_id: str = "",
    turn_id: str = "",
    flow_id: str = "",
    blueprint: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Normalize and deduplicate blocks without changing their semantics.

    The deduplication key is block identity first and exact canonical payload
    second. This prevents old repair layers from creating repeated visible
    nodes while keeping legitimately different renderers of the same scene.
    """
    blueprint = _d(blueprint)
    bp_nodes, bp_order = _blueprint_indexes(blueprint)
    relation_targets = _relation_map(blueprint)

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_signatures: set[str] = set()
    semantic_index: dict[str, int] = {}

    raw_blocks = [b for b in blocks or [] if isinstance(b, dict)]
    for index, raw in enumerate(raw_blocks):
        block = deepcopy(raw)
        block_type = normalize_type(block.get("type") or block.get("artifact_type") or block.get("representation"))
        block["type"] = block_type
        block.setdefault("artifact_type", block_type)

        if block_type == "graph_data":
            # Preserve structured graph data inside its owning graph payload,
            # but do not expose it as a second visible Web block.
            continue

        block_id = stable_block_id(scene_id, block, index)
        bp_node = bp_nodes.get(block_id, {})
        # Blueprint metadata can enrich presentation but never overwrite a
        # concrete payload already produced by a room.
        for key in ("role", "purpose", "parent_block_id", "text_role"):
            if key not in block and bp_node.get(key) is not None:
                block[key] = deepcopy(bp_node[key])

        renderer = normalize_renderer(block.get("renderer") or block.get("viewer"), block_type)
        block["renderer"] = renderer
        block["viewer"] = _s(block.get("viewer")) or renderer
        block["block_id"] = block_id
        block["render_id"] = _s(block.get("render_id")) or stable_render_id(scene_id, block_id, renderer)
        block["scene_id"] = _s(block.get("scene_id")) or scene_id
        block["turn_id"] = _s(block.get("turn_id")) or turn_id
        block["flow_id"] = _s(block.get("flow_id")) or flow_id
        block["topic_group"] = _s(block.get("topic_group")) or _s(blueprint.get("topic_group"))
        block["continuation"] = bool(block.get("continuation", blueprint.get("continuation", False)))
        block["sequence_index"] = bp_order.get(block_id, index)
        block["scene_contract"] = True

        related = []
        for value in _l(block.get("related_block_ids")):
            key = _s(value)
            if key and key not in related:
                related.append(key)
        for value in relation_targets.get(block_id, []):
            if value and value not in related:
                related.append(value)
        block["related_block_ids"] = related

        signature = _fingerprint({
            "type": block_type,
            "renderer": renderer,
            "content": _content(block),
            "payload": block.get("payload", {}),
        })
        semantic_key = _semantic_visual_key(block)
        if semantic_key and semantic_key in semantic_index:
            previous_index = semantic_index[semantic_key]
            preferred = _prefer_block(normalized[previous_index], block)
            if preferred is not normalized[previous_index]:
                normalized[previous_index] = preferred
            continue
        if block_id in seen_ids or signature in seen_signatures:
            continue
        seen_ids.add(block_id)
        seen_signatures.add(signature)
        if semantic_key:
            semantic_index[semantic_key] = len(normalized)
        normalized.append(block)

    normalized.sort(key=lambda item: int(item.get("sequence_index", 0)))
    for index, block in enumerate(normalized):
        block["sequence_index"] = index
    return normalized


def ensure_scene_text_block(
    blocks: Iterable[Any] | None,
    answer: Any,
    *,
    scene_id: str = "",
    turn_id: str = "",
    flow_id: str = "",
    blueprint: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Add the scene's single human text node only when it is genuinely absent.

    This is scene composition, not a renderer fallback: a text node is a normal
    peer of graph/table/image/etc. and is never used to replace those nodes.
    """
    result = canonicalize_scene_blocks(
        blocks,
        scene_id=scene_id,
        turn_id=turn_id,
        flow_id=flow_id,
        blueprint=blueprint,
    )
    text = _s(answer)
    if not text:
        return result
    if any(normalize_type(b.get("type")) in TEXT_TYPES and _content(b) for b in result):
        return result

    node = {
        "type": "text",
        "artifact_type": "text",
        "renderer": "MessageTextBlock",
        "viewer": "MessageTextBlock",
        "content": text,
        "text": text,
        "role": "answer",
        "scene_id": scene_id,
        "turn_id": turn_id,
        "flow_id": flow_id,
        "topic_group": _s(_d(blueprint).get("topic_group")),
        "continuation": bool(_d(blueprint).get("continuation", False)),
        "scene_contract": True,
    }
    # Text is first in the scene only when the blueprint does not explicitly
    # place another node before it.
    result.insert(0, node)
    for index, block in enumerate(result):
        block["sequence_index"] = index
        block["block_id"] = stable_block_id(scene_id, block, index)
        block["render_id"] = stable_render_id(scene_id, block["block_id"], _s(block.get("renderer")) or "MessageTextBlock")
    return result


def build_presentation_contract(
    *,
    scene_id: str = "",
    turn_id: str = "",
    flow_id: str = "",
    topic_group: str = "",
    continuation: bool = False,
    layout_mode: str = "flow",
) -> dict[str, Any]:
    """Describe how Web should lay out the already-decided scene.

    There are no card/fallback routes here. The layout is intentionally
    adaptive and full-width so a graph, table or image is not squeezed into
    the dimensions of a text card.
    """
    return {
        "version": PRESENTATION_ENGINE_VERSION,
        "signal_version": PRESENTATION_SIGNAL_VERSION,
        "engine": MARKDOWN_ENGINE,
        "math_engine": MATH_ENGINE,
        "scene_id": scene_id,
        "turn_id": turn_id,
        "flow_id": flow_id,
        "topic_group": topic_group,
        "continuation": bool(continuation),
        "single_response": True,
        "single_signal": True,
        "layout": {
            "mode": layout_mode or "flow",
            "container": "adaptive_full_width",
            "frames": False,
            "cards": False,
            "allow_wide_visuals": True,
            "allow_inline_text": True,
            "preserve_order": True,
            "preserve_relationships": True,
        },
        "markdown": {
            "engine": MARKDOWN_ENGINE,
            "gfm": True,
            "math_parser": "remark-math",
            "math_renderer": "rehype-katex",
            "payload_preserved": True,
        },
        "answer_render_policy": "render_from_scene_blocks_only",
        "renderer_selection_owner": "QUANTUM_PROCESSOR",
    }


def _presentation_for_block(block: dict[str, Any], scene_presentation: dict[str, Any]) -> dict[str, Any]:
    block_type = normalize_type(block.get("type"))
    renderer = normalize_renderer(block.get("renderer"), block_type)
    return {
        "version": PRESENTATION_SIGNAL_VERSION,
        "engine": MARKDOWN_ENGINE,
        "math_engine": MATH_ENGINE,
        "kind": block_type,
        "renderer": renderer,
        "renderer_authority": "SCENE_CONTRACT",
        "scene_id": _s(block.get("scene_id")) or _s(scene_presentation.get("scene_id")),
        "block_id": _s(block.get("block_id")),
        "render_id": _s(block.get("render_id")),
        "payload_unchanged": True,
        "layout_mode": _d(scene_presentation.get("layout")).get("mode", "flow"),
        "container": "adaptive_full_width",
    }


def attach_presentation_signals(
    blocks: Iterable[Any] | None,
    *,
    scene_presentation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Attach presentation metadata once per canonical block."""
    result = []
    for raw in blocks or []:
        if not isinstance(raw, dict):
            continue
        block = deepcopy(raw)
        block["presentation"] = _presentation_for_block(block, scene_presentation)
        result.append(block)
    return result


def build_scene_presentation(
    scene: dict[str, Any] | Any,
    *,
    blocks: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build the Web-facing presentation view of one canonical scene."""
    scene_map = scene if isinstance(scene, dict) else getattr(scene, "__dict__", {})
    scene_map = _d(scene_map)
    blueprint = _d(scene_map.get("scene_blueprint") or scene_map.get("blueprint"))
    metadata = _d(scene_map.get("metadata"))

    scene_id = _s(scene_map.get("scene_id") or metadata.get("scene_id"))
    turn_id = _s(scene_map.get("turn_id") or metadata.get("turn_id"))
    flow_id = _s(scene_map.get("flow_id") or metadata.get("flow_id"))
    topic_group = _s(scene_map.get("topic_group") or blueprint.get("topic_group") or metadata.get("topic_group"))
    continuation = bool(scene_map.get("continuation", blueprint.get("continuation", metadata.get("continuation", False))))
    answer = _s(scene_map.get("answer") or metadata.get("answer"))

    source_blocks = blocks if blocks is not None else scene_map.get("render_blocks") or scene_map.get("blocks") or []
    canonical_blocks = ensure_scene_text_block(
        source_blocks,
        answer,
        scene_id=scene_id,
        turn_id=turn_id,
        flow_id=flow_id,
        blueprint=blueprint,
    )
    presentation = build_presentation_contract(
        scene_id=scene_id,
        turn_id=turn_id,
        flow_id=flow_id,
        topic_group=topic_group,
        continuation=continuation,
        layout_mode=_s(_d(metadata.get("presentation")).get("layout_mode")) or "flow",
    )
    presented_blocks = attach_presentation_signals(canonical_blocks, scene_presentation=presentation)

    relations = []
    for raw in _l(blueprint.get("relations")):
        if not isinstance(raw, dict):
            continue
        source = _s(raw.get("from") or raw.get("source"))
        target = _s(raw.get("to") or raw.get("target"))
        relation = _s(raw.get("relation") or raw.get("type") or "related")
        if source and target:
            relations.append({"from": source, "to": target, "relation": relation})
    if not relations:
        for block in presented_blocks:
            for target in _l(block.get("related_block_ids")):
                if _s(target):
                    relations.append({"from": _s(block.get("block_id")), "to": _s(target), "relation": "related"})

    order = [_s(block.get("block_id")) for block in presented_blocks if _s(block.get("block_id"))]

    return {
        "signal_type": "scene",
        "signal_version": PRESENTATION_SIGNAL_VERSION,
        "scene_id": scene_id,
        "turn_id": turn_id,
        "flow_id": flow_id,
        "topic_group": topic_group,
        "continuation": continuation,
        "single_response": True,
        "single_signal": True,
        "answer_render_policy": "render_from_scene_blocks_only",
        "answer": answer,
        "blocks": presented_blocks,
        "render_blocks": presented_blocks,
        "relations": relations,
        "order": order,
        "presentation": presentation,
    }


def build_scene_signal(scene: dict[str, Any] | Any, *, blocks: Iterable[Any] | None = None) -> dict[str, Any]:
    """Compatibility alias used by the canonical artifact boundary."""
    return build_scene_presentation(scene, blocks=blocks)


# ---------------------------------------------------------------------------
# Math / Markdown formatting helpers. They preserve source text; they do not
# decide whether a formula is semantically required.
# ---------------------------------------------------------------------------

_MATH_SPAN_RE = re.compile(r"(?<!\\)(\\\\\(|\\\\\[|\$\$?|\\begin\{[^}]+\}).*?(?<!\\)(?:\\\\\)|\\\\\]|\$\$?|\\end\{[^}]+\})", re.S)


def normalize_markdown_math(value: Any) -> str:
    """Preserve TeX delimiters while removing transport-only wrappers."""
    text = _s(value)
    if not text:
        return ""
    return text.replace("\\r\\n", "\\n").replace("\\x00", "")


def split_markdown_segments(value: Any) -> list[dict[str, Any]]:
    """Return text/math segments for MessageTextBlock without rewriting TeX."""
    text = normalize_markdown_math(value)
    if not text:
        return []
    segments = []
    last = 0
    for match in _MATH_SPAN_RE.finditer(text):
        if match.start() > last:
            segments.append({"kind": "text", "value": text[last:match.start()]})
        segments.append({"kind": "math", "value": match.group(0)})
        last = match.end()
    if last < len(text):
        segments.append({"kind": "text", "value": text[last:]})
    return segments or [{"kind": "text", "value": text}]


__all__ = [
    "APRIL_FILE_ID",
    "PRESENTATION_ENGINE_VERSION",
    "PRESENTATION_SIGNAL_VERSION",
    "canonicalize_scene_blocks",
    "ensure_scene_text_block",
    "build_presentation_contract",
    "attach_presentation_signals",
    "build_scene_presentation",
    "build_scene_signal",
    "normalize_markdown_math",
    "split_markdown_segments",
    "stable_block_id",
    "stable_render_id",
]
