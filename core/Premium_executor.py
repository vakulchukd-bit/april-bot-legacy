"""APRIL Premium canonical Exkrutor processor.

Processor responsibilities:
1. accept one normalized request from bot.ru;
2. bind authenticated user/turn identity;
3. synchronize the 24h dialogue state from PostgreSQL through state_manager;
4. run the state-manager search/rerank engine;
5. build the single Interpretation structure;
6. ask C_ARTIFACT_CONTRACT for the rooms/renderers required by that interpretation;
7. make one structured Provider/Luna call;
8. optionally hand an image generation spec to the existing C_APRIL_IMAGES_GENERATOR;
9. build one SceneContract and verify identity before Web delivery;
10. persist the final USER↔APRIL pair.

No alternate route, room register or second memory store is created here.
"""
from __future__ import annotations

from typing import Any
import base64
import hashlib
import json
import os
import re
import time
import uuid

from blocks.Premium_C_ARTIFACT_CONTRACT import (
    MachineRequest,
    MachineResponse,
    MachineScene,
    build_scene_contract,
    prepare_render_blocks_for_room_dispatch,
    get_web_renderer_registration,
    list_registered_rooms,
)
from blocks.dialog_identity import resolve_dialog_identity, assert_identity_match
from blocks.Premium_interpretation_identity import (
    build_interpretation_identity,
    build_interpretation,
    build_question_sequence,
    interpret_request_semantics,
    _has_explicit_topic_introduction,
    _detect_image_modification,
    _detect_contextual_image_edit,
)
from blocks.Premium_provider_router import generate_text
from blocks.text_module import package_provider_response
from blocks.premium_asset_store import save_asset as _save_premium_asset, load_message_assets as _load_premium_assets, decode_data_uri as _decode_asset_data_uri
from blocks.Premium_state_manager import (
    init_db,
    is_authenticated_user,
    save_dialogue_pair,
    prepare_dialogue_context,
    build_active_work_branch_record,
)


PROCESSOR_VERSION = "april_premium_exkrutor_single_route_v6_hot_work_branch_priority"
CANONICAL_ROUTE = "/api/v1/chat"


def _apr_timing_log(stage: str, started: float | None = None, **fields: Any) -> None:
    """Low-overhead diagnostic timing; logging must never affect the request path."""
    try:
        payload = {"component": "premium_executor", "stage": stage}
        if started is not None:
            payload["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        payload.update(fields)
        print("[APRIL_TIMING] " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), flush=True)
    except Exception:
        pass

def _apr_diag_ref(value: Any) -> str:
    """One-way short reference for joining logs without exposing raw user IDs."""
    try:
        raw = str(value or "").strip()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10] if raw else ""
    except Exception:
        return ""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _stable_scene_id(identity: dict[str, str]) -> str:
    """Return one deterministic scene ID for the progressive and final turn payloads.

    The Web receives the text-ready scene before a slow image render and the final
    SceneContract afterwards. Those are two states of one assistant turn, not two
    messages, so both payloads must share the same scene identity.
    """
    parts = (
        _text(identity.get("user_id")),
        _text(identity.get("conversation_id") or identity.get("dialog_id")),
        _text(identity.get("message_id")),
        _text(identity.get("flow_id")),
    )
    source = "|".join(parts).strip("|") or "missing-turn-identity"
    return "scene_" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def _is_structured_3d_graph_block(block: Any) -> bool:
    if not isinstance(block, dict):
        return False
    block_type = _text(block.get("type") or block.get("artifact_type")).lower()
    if block_type not in {"graph", "chart", "plot"}:
        return False
    payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
    if not payload and isinstance(block.get("artifact"), dict):
        candidate = block["artifact"].get("payload")
        payload = candidate if isinstance(candidate, dict) else {}
    representation = _text(payload.get("representation") or payload.get("graph_type") or payload.get("chart_type")).lower()
    return bool(
        "3d" in representation
        or payload.get("three_d") is True
        or payload.get("dimensions") == 3
        or payload.get("objects_3d")
        or payload.get("spheres")
        or payload.get("surface_grid")
        or payload.get("z_values")
        or any(
            isinstance(point, dict) and ("z" in point or "value_z" in point)
            for series in (payload.get("series") or []) if isinstance(series, dict)
            for point in (series.get("points") or series.get("data") or [])
        )
    )


def _compact_question_search(
    context: dict[str, Any],
    query: str = "",
    semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bounded per-question retrieval context for the existing Provider sequence."""
    if not isinstance(context, dict):
        return {"status": "unavailable", "relation": "NEW", "context": []}

    def compact_pair(item: Any) -> dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        # Keep per-question retrieval semantic and bounded. Carry the selected
        # source's lossless structure as an internal hand-off to Provider's
        # _select_protected_structured_data(). Provider extracts it into the single
        # top-level PROTECTED_STRUCTURED_DATA lane before prompt compaction; the
        # REQUEST_SEQUENCE serializer later removes this sidecar, so it is not
        # duplicated into every model-facing subtask.
        sections = []
        for section in (item.get("sections") or [])[:4]:
            if not isinstance(section, dict):
                continue
            sections.append({
                "heading": _text(section.get("heading"))[:160],
                "summary": _text(section.get("summary"))[:300],
                "order": section.get("order"),
                "message_id": _text(section.get("message_id"))[:120],
                "source_message_id": _text(section.get("source_message_id") or section.get("message_id"))[:120],
                "topic_id": _text(section.get("topic_id") or item.get("topic_id"))[:100],
                "topic_origin_message_id": _text(section.get("topic_origin_message_id") or item.get("origin_message_id"))[:120],
            })
        compact = {
            "topic": _text(item.get("topic"))[:200],
            "user": _text(item.get("user"))[:360],
            "april": _text(item.get("april"))[:480],
            "sections": sections,
            "message_id": _text(item.get("message_id"))[:120],
            "topic_id": _text(item.get("topic_id"))[:100],
            "origin_message_id": _text(item.get("origin_message_id") or item.get("topic_origin_message_id"))[:120],
            "origin_turn": item.get("origin_turn"),
            "first_at": item.get("first_at") or item.get("topic_origin_at"),
            "last_at": item.get("last_at") or item.get("topic_last_at"),
            "same_dialog": bool(item.get("same_dialog")),
        }
        # Optional exact source text is forwarded only when State Manager has
        # selected a verified matching DB pair. It is never reconstructed from a summary.
        if item.get("preserve_source_text") is True:
            compact.update({
                "preserve_source_text": True,
                "source_user_text": _text(item.get("source_user_text"))[:1800],
                "source_april_text": _text(item.get("source_april_text"))[:5200],
                "source_user_text_chars": item.get("source_user_text_chars"),
                "source_april_text_chars": item.get("source_april_text_chars"),
                "source_user_text_complete": bool(item.get("source_user_text_complete")),
                "source_april_text_complete": bool(item.get("source_april_text_complete")),
                "source_content_complete": bool(item.get("source_content_complete")),
                "source_text_origin": _text(item.get("source_text_origin") or "dialogue_memory")[:40],
            })
        # Do not reconstruct structured data from clipped text. Preserve the exact
        # source payload (including its source_message_id/checksum) only when it is
        # a real, value-bearing structure; Provider will validate/route it by source.
        protected = item.get("protected_structured_data")
        if (
            isinstance(protected, dict)
            and isinstance(protected.get("items"), list)
            and protected.get("items")
            and _text(protected.get("source_answer"))
        ):
            compact["protected_structured_data"] = protected
        return compact

    anchor = context.get("anchor") if isinstance(context.get("anchor"), dict) else {}
    section = context.get("selected_section") if isinstance(context.get("selected_section"), dict) else {}
    # Preserve the five evidence pairs selected by Premium history search. The
    # previous two-pair cap discarded valid temporal/topic matches before the model.
    pairs = [compact_pair(item) for item in (context.get("selected_pairs") or [])[:5]]
    pairs = [item for item in pairs if item]
    pending = context.get("pending_clarification") if isinstance(context.get("pending_clarification"), dict) else {}
    options = []
    for item in (pending.get("options") or [])[:3]:
        if not isinstance(item, dict):
            continue
        options.append({
            "topic": _text(item.get("topic"))[:180],
            "heading": _text(item.get("heading"))[:180],
            "summary": _text(item.get("summary"))[:280],
            "message_id": _text(item.get("message_id"))[:120],
        })
    semantics = dict(semantics or {})
    repair_features = semantics.get("pragmatic_features") if isinstance(semantics.get("pragmatic_features"), dict) else {}
    state_search = context.get("search") if isinstance(context.get("search"), dict) else {}
    active_repair = bool(
        semantics.get("active_branch_repair")
        or repair_features.get("active_branch_repair")
        or context.get("active_branch_repair")
        or state_search.get("active_branch_repair")
    )
    anchor_message_id = _text(anchor.get("message_id"))
    if active_repair and anchor_message_id:
        # Provider compaction has stricter pair limits than State Manager. Put the
        # exact challenged USER↔APRIL source first so the wrong answer is not lost
        # when the prompt is reduced to one evidence pair.
        anchor_pair_index = next((i for i, pair in enumerate(pairs)
                                  if _text(pair.get("message_id")) == anchor_message_id), -1)
        if anchor_pair_index > 0:
            pairs = [pairs[anchor_pair_index]] + pairs[:anchor_pair_index] + pairs[anchor_pair_index + 1:]
    history_request = bool(context.get("history_request") or semantics.get("history_request"))
    topic_index = []
    requested_topic_count = max(1, min(10, int(
        semantics.get("requested_topic_count") or context.get("requested_topic_count") or 10
    )))
    minimum_topic_count = max(1, min(requested_topic_count, int(
        semantics.get("minimum_topic_count") or context.get("minimum_topic_count") or min(5, requested_topic_count)
    )))
    if history_request:
        topic_index = [
            {
                "number": item.get("number"),
                "topic": _text(item.get("topic"))[:200],
                "summary": _text(item.get("summary"))[:320],
                "last_question": _text(item.get("last_question"))[:200],
                "message_id": _text(item.get("message_id"))[:120],
                "topic_id": _text(item.get("topic_id"))[:100],
                "origin_message_id": _text(item.get("origin_message_id"))[:120],
                "origin_turn": item.get("origin_turn"),
                "first_at": item.get("first_at"),
                "last_at": item.get("last_at"),
                "pair_count": item.get("pair_count") or item.get("turns"),
                "sections": [
                    {
                        "heading": _text(sec.get("heading"))[:100],
                        "summary": _text(sec.get("summary"))[:160],
                        "order": sec.get("order"),
                        "message_id": _text(sec.get("message_id"))[:120],
                        "source_message_id": _text(sec.get("source_message_id") or sec.get("message_id"))[:120],
                        "topic_id": _text(sec.get("topic_id") or item.get("topic_id"))[:100],
                        "topic_origin_message_id": _text(sec.get("topic_origin_message_id") or item.get("origin_message_id"))[:120],
                    }
                    for sec in (item.get("sections") or [])[:4] if isinstance(sec, dict)
                ],
            }
            for item in (context.get("topic_index") or [])[:requested_topic_count] if isinstance(item, dict)
        ]
    history_topics = [
        {
            "number": item.get("number"),
            "topic": _text(item.get("topic"))[:200],
            "summary": _text(item.get("summary"))[:320],
            "last_question": _text(item.get("last_question"))[:200],
            "message_id": _text(item.get("message_id"))[:120],
            "topic_id": _text(item.get("topic_id"))[:100],
            "origin_message_id": _text(item.get("origin_message_id"))[:120],
            "origin_turn": item.get("origin_turn"),
            "first_at": item.get("first_at"),
            "last_at": item.get("last_at"),
            "pair_count": item.get("pair_count") or item.get("turns"),
        }
        for item in (context.get("history_topics") or [])[:requested_topic_count] if isinstance(item, dict)
    ] if history_request else []
    return {
        "status": "ready",
        "relation": _text(context.get("relation") or "NEW").upper(),
        "history_request": history_request,
        "requested_topic_count": requested_topic_count if history_request else 0,
        "minimum_topic_count": minimum_topic_count if history_request else 0,
        "time_window": context.get("time_window") if isinstance(context.get("time_window"), dict) else {},
        "time_filter": context.get("time_filter") if isinstance(context.get("time_filter"), dict) else {},
        "semantic_intent": _text(semantics.get("primary_intent") or ("HISTORY_RECALL" if history_request else "NEW_INFORMATION")),
        "search_direction": _text(semantics.get("direction") or ("SEARCH_DIALOGUE_HISTORY" if history_request else "ANSWER_NEW_REQUEST")),
        "time_scope": _text(semantics.get("time_scope") or "UNSPECIFIED"),
        "speech_act": _text(semantics.get("speech_act") or "STATEMENT_OR_REQUEST"),
        "communicative_act": _text(semantics.get("communicative_act") or "NEW_OR_STANDALONE"),
        "active_branch_repair": bool(active_repair),
        "active_branch": dict(context.get("active_branch") or state_search.get("active_branch") or {}),
        "active_work_branch": dict(context.get("active_work_branch") or state_search.get("active_work_branch") or {}),
        "hot_work_followup": bool(context.get("hot_work_followup") or state_search.get("hot_work_followup")),
        "hot_work_match_reason": _text(context.get("hot_work_match_reason") or state_search.get("hot_work_match_reason"))[:80],
        "user_operation": dict(context.get("user_operation") or state_search.get("user_operation") or {}),
        "source_retrieval": dict(context.get("source_retrieval") or state_search.get("source_retrieval") or {}),
        "previous_answer_reference": bool(
            semantics.get("previous_answer_reference")
            or (semantics.get("pragmatic_features") or {}).get("previous_answer_reference")
            or context.get("previous_answer_reference")
            or state_search.get("previous_answer_reference")
        ),
        "factual_verification_request": bool(
            semantics.get("factual_verification_request")
            or (semantics.get("pragmatic_features") or {}).get("factual_verification_request")
            or context.get("factual_verification_request")
            or state_search.get("factual_verification_request")
        ),
        "explicit_topic_switch": bool(
            semantics.get("explicit_topic_switch")
            or context.get("explicit_topic_switch")
            or state_search.get("explicit_topic_switch")
        ),
        "tone": _text(semantics.get("tone") or "NEUTRAL"),
        "recommended_response_action": _text(semantics.get("recommended_response_action") or "ANSWER_NORMALLY"),
        "pragmatic_features": dict(semantics.get("pragmatic_features") or {}),
        "history_topics": history_topics,
        "topic_index": topic_index,
        "confidence": round(float(context.get("relation_confidence") or 0.0), 4),
        "reason": _text(context.get("reason"))[:160],
        "topic": (_text(context.get("active_topic")) or _text(query))[:240],
        "anchor": {
            "topic": _text(anchor.get("topic"))[:200],
            "user": _text(anchor.get("user"))[:360],
            "april": _text(anchor.get("april"))[:480],
            "message_id": _text(anchor.get("message_id"))[:120],
        } if anchor else {},
        "selected_section": {
            "topic": _text(section.get("topic"))[:200],
            "heading": _text(section.get("heading"))[:180],
            "summary": _text(section.get("summary"))[:360],
            "order": section.get("order"),
            "message_id": _text(section.get("message_id"))[:120],
            "source_message_id": _text(section.get("source_message_id") or section.get("message_id"))[:120],
            "topic_id": _text(section.get("topic_id"))[:100],
            "topic_origin_message_id": _text(section.get("topic_origin_message_id"))[:120],
        } if section else {},
        "selected_pairs": pairs,
        "clarification_needed": bool(context.get("clarification_needed")),
        "clarification_prompt": _text(context.get("clarification_prompt"))[:560],
        "clarification_options": options,
    }


def _identity_tuple(identity: dict[str, Any]) -> dict[str, str]:
    return {
        "user_id": _text(identity.get("user_id")),
        "conversation_id": _text(identity.get("conversation_id")),
        "dialog_id": _text(identity.get("dialog_id")),
        "message_id": _text(identity.get("message_id")),
        "flow_id": _text(identity.get("flow_id")),
        "interpretation_id": _text(identity.get("interpretation_id")),
    }


def _select_rooms(interpretation: dict[str, Any]) -> list[dict[str, Any]]:
    """Select registered rooms/engines only from C_ARTIFACT_CONTRACT."""
    intent = interpretation.get("intent") or {}
    input_data = interpretation.get("input") or {}
    selected: list[dict[str, Any]] = []

    required_capabilities: list[str] = []
    if intent.get("wants_image"):
        required_capabilities.extend(["image_generation", "png", "gallery"])
    if intent.get("wants_links"):
        required_capabilities.extend(["link", "url", "preview", "web"])
    if intent.get("wants_code"):
        required_capabilities.extend(["software", "code", "analysis"])
    if intent.get("wants_formula"):
        required_capabilities.extend(["formula", "latex", "math"])
    if intent.get("wants_diagram"):
        required_capabilities.extend(["diagram", "geometry"])
    if intent.get("wants_table"):
        required_capabilities.extend(["table", "structured_data", "tabular"])
    if intent.get("wants_graph"):
        required_capabilities.extend(["graph", "series", "data_visualization"])

    # Domain hints from the current request are additive, never authoritative over
    # the Interpretation decision.
    required_capabilities.extend(
        str(x) for x in interpretation.get("routing_capabilities", []) if str(x)
    )

    seen: set[str] = set()
    for room in list_registered_rooms():
        if not room.enabled or room.room_id in seen:
            continue
        caps = set(room.capabilities)
        if caps.intersection(required_capabilities):
            selected.append(
                {
                    "room": room.room_id,
                    "module": room.module,
                    "capabilities": list(room.capabilities),
                    "artifact_type": room.artifact_type,
                    "room_type": room.room_type,
                    "is_engine": room.is_engine,
                }
            )
            seen.add(room.room_id)

    # Text is always a legal primary output. C-ARTIFACT remains the renderer
    # authority even when no specialized room was selected.
    if not selected:
        selected = [
            {
                "room": room.room_id,
                "module": room.module,
                "capabilities": list(room.capabilities),
                "artifact_type": room.artifact_type,
                "room_type": room.room_type,
                "is_engine": room.is_engine,
            }
            for room in list_registered_rooms(include_engines=False)
            if room.room_id in {"it", "WEB_ROOM"}
        ][:1]

    # For image generation, keep the generator first and gallery renderer second.
    if intent.get("wants_image"):
        ordered: list[dict[str, Any]] = []
        for preferred in ("APRIL_IMAGES_GENERATION", "GALLERY_ROOM"):
            for item in selected:
                if item["room"] == preferred and item not in ordered:
                    ordered.append(item)
        selected = ordered + [
            item for item in selected if item not in ordered
        ]

    return selected


def _renderer_plan(
    interpretation: dict[str, Any],
    selected_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ask C-ARTIFACT for concrete Web renderers; no local renderer map."""
    outputs = list((interpretation.get("intent") or {}).get("requested_outputs") or ["text"])
    plan: list[dict[str, Any]] = []
    seen: set[str] = set()

    for output in outputs:
        key = str(output or "text").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        reg = get_web_renderer_registration(key)
        plan.append(
            {
                "output": key,
                "renderer": reg.get("renderer", ""),
                "viewer": reg.get("viewer", ""),
                "payload_keys": list(reg.get("payload_keys") or []),
                "presentation_engine": "McDowell",
                "source_rooms": [
                    item["room"]
                    for item in selected_rooms
                    if item.get("artifact_type") in {key, "gallery" if key == "image" else key}
                    or key in set(item.get("capabilities") or [])
                ],
            }
        )
    return plan


def _final_portrait_prompt(request_text: str) -> str:
    """Return a portrait-only prompt when the user explicitly reserved an image for last."""
    source = _text(request_text)
    low = source.lower().replace("ё", "е")
    final_image_cue = bool(re.search(
        r"(?:в\s+(?:самом\s+)?конце|напоследок|в\s+завершени\w*|at\s+the\s+end|finally)"
        r"[\s\S]{0,140}?(?:покаж\w*|изобраз\w*|представ\w*|show|display|present)"
        r"[\s\S]{0,90}?(?:изображени\w*|картинк\w*|портрет\w*|фото\b|image\w*|picture\w*|portrait\w*)",
        low, re.IGNORECASE,
    ))
    if not final_image_cue:
        return ""
    subject_match = re.search(
        r"(?:про|об|о|about)\s+([A-ZА-ЯЁ][A-Za-zА-Яа-яЁё.'’-]*(?:\s+[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё.'’-]*){0,3}?)"
        r"(?=\s+(?:все|всю|всё|его|ее|её|их|формул\w*|истори\w*|кратк\w*|and|all|his|her|their|formul\w*|biograph\w*)|[,.;!?]|$)",
        source,
        re.IGNORECASE,
    )
    subject = _text(subject_match.group(1) if subject_match else "").strip(" .,!?:;")
    if not subject:
        return ""
    return (
        f"Create one standalone, historically grounded portrait of {subject}. "
        "This is the final portrait in a factual educational answer. Show only the subject; "
        "do not create an infographic, poster, collage, formula sheet, diagrams, panels, labels, captions, "
        "or any text. Use a clear composition, natural proportions, coherent lighting, and a neutral background."
    )


def _apply_presentation_sequence(
    render_blocks: Any,
    answer: str,
    presentation_sequence: Any,
) -> list[dict[str, Any]]:
    """Assign renderer steps and keep each narrative section in a compact block.

    Providers usually return one complete text block. Splitting it at every Markdown
    heading made the Web render dozens of separate blocks; more importantly, cloned
    blocks inherited the original full text from ``payload.content`` and could repeat
    the answer while an image was still generating. This adapter now synchronizes text
    aliases/payloads per clone and merges adjacent pieces from the same source text and
    presentation step back into one block.
    """
    blocks = [dict(block) for block in (render_blocks or []) if isinstance(block, dict)] if isinstance(render_blocks, list) else []
    sequence = [dict(item) for item in (presentation_sequence or []) if isinstance(item, dict)] if isinstance(presentation_sequence, list) else []
    if not sequence:
        for index, block in enumerate(blocks):
            block.setdefault("step_index", 1)
            block["sequence_index"] = index
        return blocks

    by_section = {str(item.get("section") or ""): item for item in sequence}
    by_step = {int(item.get("step_index") or index + 1): item for index, item in enumerate(sequence)}
    text_keys = ("content", "text", "markdown", "display_text")

    def set_text_content(block: dict[str, Any], value: str) -> None:
        present_keys = [key for key in text_keys if isinstance(block.get(key), str)]
        for key in (present_keys or ["content"]):
            block[key] = value
        payload = block.get("payload")
        if isinstance(payload, dict):
            payload_keys = [key for key in text_keys if isinstance(payload.get(key), str)]
            for key in (payload_keys or ["content"]):
                # Text-block payloads mirror the visible text; never leave the
                # original full answer inside every heading-derived clone.
                payload[key] = value

    def section_for_text(value: str, fallback_step: int = 1) -> dict[str, Any]:
        low = _text(value).lower().replace("ё", "е")
        patterns = {
            "formulas": r"(?:формул\w*|уравнен\w*|formula\w*|equation\w*|математическ\w+ запись)",
            "biography": r"(?:биограф\w*|истори\w* жизни|ранн\w+ годы|жизн\w* и работ\w*|life story|biography|early life)",
            "experiments": r"(?:опыт\w*|эксперимент\w*|фотоэффект|маякельсон|микельсон|мерли|experiment\w*)",
            "resources": r"(?:ресурс\w*|ссылк\w*|источник\w*|полезн\w+ ресурс\w*|resource\w*|source\w*|reference\w*)",
        }
        for section, pattern in patterns.items():
            if re.search(pattern, low, re.IGNORECASE) and section in by_section:
                return by_section[section]
        return by_step.get(max(1, fallback_step), sequence[0])

    expanded: list[dict[str, Any]] = []
    for source_index, block in enumerate(blocks):
        block_type = str(block.get("type") or block.get("artifact_type") or "text").strip().lower()
        content = str(block.get("content") or block.get("text") or "")
        is_text = block_type in {"text", "message", "answer", "markdown", "message_text"}
        if is_text and len(sequence) > 1 and content.strip():
            heading_matches = list(re.finditer(r"(?m)^#{1,4}\s+[^\n]+\s*$", content))
            if len(heading_matches) >= 2:
                starts = sorted(set([0] + [match.start() for match in heading_matches]))
                ends = starts[1:] + [len(content)]
                chunks = [content[a:b] for a, b in zip(starts, ends) if content[a:b].strip()]
                if len(chunks) >= 2:
                    for chunk in chunks:
                        heading_match = re.search(r"(?m)^#{1,4}\s+([^\n]+)", chunk)
                        heading = heading_match.group(1) if heading_match else chunk[:180]
                        step = section_for_text(heading + "\n" + chunk[:350])
                        clone = dict(block)
                        if isinstance(block.get("payload"), dict):
                            # A shallow block clone otherwise shares the nested payload
                            # with every sibling heading and leaks the same full answer.
                            clone["payload"] = dict(block["payload"])
                        clone["_april_text_source_index"] = source_index
                        set_text_content(clone, chunk.strip())
                        try:
                            clone["step_index"] = max(1, int(step.get("step_index") or 1))
                        except (TypeError, ValueError, OverflowError):
                            clone["step_index"] = 1
                        clone["step_title"] = _text(step.get("title") or step.get("section") or "Answer section")[:100]
                        expanded.append(clone)
                    continue
        clone = dict(block)
        if is_text:
            if isinstance(block.get("payload"), dict):
                clone["payload"] = dict(block["payload"])
            clone["_april_text_source_index"] = source_index
            set_text_content(clone, content)
        expanded.append(clone)

    for original_order, block in enumerate(expanded):
        kind = str(block.get("type") or block.get("artifact_type") or "text").strip().lower()
        try:
            current_step = max(1, int(block.get("step_index") or 1))
        except (TypeError, ValueError, OverflowError):
            current_step = 1
        if kind in {"image", "gallery"}:
            match = next((item for item in sequence if item.get("final_output") and "image" in (item.get("output_types") or [])), None)
            if match is None:
                image_items = [item for item in sequence if "image" in (item.get("output_types") or [])]
                match = image_items[-1] if image_items else None
        elif kind in {"formula", "diagram", "graph", "table", "link", "code", "file"}:
            match = next((item for item in sequence if kind in (item.get("output_types") or [])), None)
            if kind == "diagram" and "experiments" in by_section:
                match = by_section["experiments"]
        else:
            text_payload = _text(block.get("content") or block.get("text") or block.get("title") or "")
            match = section_for_text(text_payload, current_step)
        if isinstance(match, dict):
            try:
                block["step_index"] = max(1, int(match.get("step_index") or 1))
            except (TypeError, ValueError, OverflowError):
                block["step_index"] = current_step
            block["step_title"] = _text(match.get("title") or match.get("section") or "Answer section")[:100]
        else:
            block.setdefault("step_index", current_step)
        block["_april_original_order"] = original_order

    def safe_step_index(block: dict[str, Any]) -> int:
        try:
            return max(1, int(block.get("step_index") or 1))
        except (TypeError, ValueError, OverflowError):
            return 1

    expanded.sort(key=lambda block: (safe_step_index(block), int(block.get("_april_original_order") or 0)))

    # Merge heading chunks back into one text block per step. Visual blocks retain
    # their own renderers and sit between the appropriate narrative steps.
    compact: list[dict[str, Any]] = []
    for block in expanded:
        source_index = block.get("_april_text_source_index")
        kind = str(block.get("type") or block.get("artifact_type") or "text").strip().lower()
        is_text = kind in {"text", "message", "answer", "markdown", "message_text"}
        current_step = safe_step_index(block)
        current_title = _text(block.get("step_title") or "Answer section")
        current_content = str(block.get("content") or block.get("text") or "").strip()
        previous = compact[-1] if compact else None
        can_merge = bool(
            is_text and previous is not None
            and str(previous.get("type") or previous.get("artifact_type") or "text").strip().lower() in {"text", "message", "answer", "markdown", "message_text"}
            and previous.get("_april_text_source_index") == source_index
            and safe_step_index(previous) == current_step
            and _text(previous.get("step_title") or "Answer section") == current_title
        )
        if can_merge:
            previous_content = str(previous.get("content") or previous.get("text") or "").strip()
            combined = "\n\n".join(value for value in (previous_content, current_content) if value)
            set_text_content(previous, combined)
        else:
            compact.append(dict(block))

    for index, block in enumerate(compact):
        block.pop("_april_text_source_index", None)
        block.pop("_april_original_order", None)
        block["sequence_index"] = index
    return compact

def _build_image_spec(
    raw: dict[str, Any],
    interpretation: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any] | None:
    """Build the canonical image-generation spec without losing a visual plan.

    Models may put the same scene brief in an image artifact spec, an image
    render-block payload, or one of the explicit top-level image prompt fields.
    All of these are accepted only after Interpretation has authorized raster
    generation. Generic answer text is never treated as the image prompt.
    """
    if not bool((interpretation.get("intent") or {}).get("wants_image")):
        return None

    request_text = _text((interpretation.get("input") or {}).get("original_request"))
    prompt_keys = (
        "openai_structured_visual_plan_semantic", "visual_generation_prompt",
        "image_prompt", "visual_prompt", "image_description", "visual_description",
        "scene_prompt", "prompt", "description",
    )

    def _first_prompt(value: Any, *, allow_description: bool = True) -> str:
        if not isinstance(value, dict):
            return ""
        keys = prompt_keys if allow_description else prompt_keys[:-1]
        for key in keys:
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _canonicalize(candidate: Any, *, raw_plan: Any = None) -> dict[str, Any] | None:
        if not isinstance(candidate, dict):
            return None
        clean = dict(candidate)
        # Specs sometimes arrive wrapped in a render-block's payload/data envelope.
        for nested_key in ("spec", "render_spec", "image_spec"):
            nested = clean.get(nested_key)
            if isinstance(nested, dict):
                merged = dict(clean)
                merged.update(nested)
                clean = merged
                break
        semantic = _first_prompt(clean)
        if not semantic:
            semantic = _first_prompt(clean.get("payload")) if isinstance(clean.get("payload"), dict) else ""
        final_portrait_prompt = _final_portrait_prompt(request_text)
        if final_portrait_prompt:
            # The requested image is a final portrait, not a poster that replaces
            # the separate biography/formula/experiment/resource deliverables.
            semantic = final_portrait_prompt
            subject = _text(re.search(r"portrait of (.+?)\.", final_portrait_prompt, re.IGNORECASE).group(1)) if re.search(r"portrait of (.+?)\.", final_portrait_prompt, re.IGNORECASE) else ""
            clean["image_subject_only"] = True
            # Replace any conflicting infographic plan returned for the same
            # compound prompt. The other sections remain in the text/SceneContract.
            clean["openai_structured_visual_plan_raw"] = {
                "rendering_type": "single_portrait",
                "subject": subject,
                "exclude": ["infographic", "poster", "collage", "formulas", "diagrams", "panels", "labels", "text"],
            }
        # Do not downgrade an empty artifact/spec to the original user request
        # here: callers may have a richer candidate later in the same response.
        # The request fallback is applied only after every explicit visual-plan
        # location has been inspected.
        if not semantic:
            return None
        clean["schema"] = "april_image_spec_v1"
        clean["generator_signal"] = "C_APRIL_IMAGES_GENERATOR"
        clean["request_anchor"] = _text(clean.get("request_anchor") or request_text)
        clean["prompt"] = final_portrait_prompt or _text(clean.get("prompt") or semantic)
        clean["openai_structured_visual_plan_semantic"] = semantic
        if isinstance(raw_plan, dict) and not final_portrait_prompt:
            clean.setdefault("openai_structured_visual_plan_raw", raw_plan)
        clean.setdefault("width", 512)
        clean.setdefault("height", 512)
        clean.setdefault("quality", "low")
        clean.setdefault("visual_context", {})
        clean.setdefault("flow_id", identity["flow_id"])
        clean.setdefault("turn_id", identity["message_id"])
        clean.setdefault("user_id", identity["user_id"])
        clean.setdefault("conversation_id", identity["conversation_id"])
        clean.setdefault("dialogue_sequence_id", identity["dialog_id"])
        clean.setdefault("dialogue_development", interpretation.get("dialogue") or {})
        return clean

    # Canonical form requested by the Provider contract.
    artifacts = raw.get("artifacts")
    if isinstance(artifacts, list):
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or item.get("artifact_type") or "").strip().lower() not in {"image", "generated_image"}:
                continue
            for candidate in (item.get("spec"), item.get("render_spec"), item.get("payload"), item.get("data"), item):
                result = _canonicalize(candidate, raw_plan=raw)
                if result:
                    return result

    # Compatibility: an image render block may carry the visual plan instead of
    # duplicating it under artifacts[].spec. Do not treat a source URL alone as a
    # prompt; the exact current request is used only by the final safe fallback.
    blocks = raw.get("render_blocks")
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if str(block.get("type") or block.get("artifact_type") or "").strip().lower() not in {"image", "gallery"}:
                continue
            payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
            for candidate in (payload.get("spec"), payload.get("render_spec"), payload, block):
                result = _canonicalize(candidate, raw_plan=raw)
                if result:
                    return result

    direct = raw.get("image_spec")
    if isinstance(direct, dict):
        result = _canonicalize(direct, raw_plan=raw)
        if result:
            return result

    # Some model responses correctly describe the scene but omit the wrapper.
    # Only named image-prompt fields qualify; never use answer/content/summary.
    direct_prompt = _first_prompt(raw, allow_description=False)
    if direct_prompt and request_text:
        return _canonicalize({
            "prompt": direct_prompt,
            "openai_structured_visual_plan_semantic": direct_prompt,
        }, raw_plan=raw)

    # Safe fallback: the explicit user request remains the semantic authority.
    if not request_text:
        return None
    return _canonicalize({
        "prompt": request_text,
        "openai_structured_visual_plan_semantic": request_text,
    }, raw_plan=raw)


async def _generate_image_artifact(
    interpretation: dict[str, Any],
    raw: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any] | None:
    spec = _build_image_spec(raw, interpretation, identity)
    if spec is None:
        return None

    from blocks.C_APRIL_IMAGES_GENERATOR import generate_from_spec

    return await generate_from_spec(spec, variant="processor_route")


async def _edit_image_artifact(
    interpretation: dict[str, Any],
    visual_context: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Edit the selected source image through the existing GPT Image edit route."""
    selected = _select_image_edit_source(visual_context or [])
    if not selected:
        return None
    source_bytes, source_mime, source_item = selected
    intent = interpretation.get("intent") if isinstance(interpretation.get("intent"), dict) else {}
    input_data = interpretation.get("input") if isinstance(interpretation.get("input"), dict) else {}
    request_text = _text(input_data.get("original_request") or input_data.get("normalized_request"))
    if not request_text:
        request_text = _text(intent.get("image_edit_instruction"))
    if not request_text:
        return None
    edit_prompt = (
        "Edit the supplied source image according to this exact user instruction: "
        + request_text
        + ". Preserve the original photograph and every unaffected detail, including composition, "
          "background, perspective, lighting, and existing text. Apply only the requested changes. "
          "Do not replace the source with a new scene or add unrequested objects."
    )
    from blocks.C_APRIL_IMAGES_GENERATOR import edit_image_result
    result = await edit_image_result(source_bytes, edit_prompt, quality="low")
    if not isinstance(result, dict) or not result.get("success") or not result.get("image_bytes"):
        return None
    result["operation"] = "edit"
    result["source_asset_message_id"] = _text(source_item.get("asset_message_id"))
    result["source_asset_role"] = _text(source_item.get("asset_role") or "user_input")
    result["source_asset_filename"] = _text(source_item.get("filename"))[:200]
    result["source_asset_mime_type"] = source_mime
    return result


def _image_edit_message(interpretation: dict[str, Any], state: str) -> str:
    """Use a truthful, stable message for edit lifecycle states, in the user's language."""
    input_data = interpretation.get("input") if isinstance(interpretation.get("input"), dict) else {}
    language = _text(input_data.get("display_language") or "").lower()
    request = _text(input_data.get("original_request") or input_data.get("normalized_request")).lower().replace("ё", "е")
    if language in {"uk", "ua", "uk-ua"}:
        if state == "missing_source":
            return "Щоб змінити саме твою фотографію, прикріпи вихідне зображення. Зараз його немає, тому я не створюватиму окрему картинку замість редагування."
        if state == "processing":
            return "Обробляю вихідне зображення та вношу лише запитану зміну."
        if state == "success":
            if "галоч" in request:
                return "Готово — додала зелену позначку до вихідного зображення. Нижче — відредагований результат."
            return "Готово — внесла запитану зміну у вихідне зображення. Нижче — результат."
        return "Не вдалося обробити зображення цього разу. Вихідне зображення не змінене; спробуй повторити запит."
    if language in {"en", "en-us", "en-gb"}:
        if state == "missing_source":
            return "Please attach the original photo so I can edit that image. It is not available in this turn, so I will not generate a separate picture as a substitute."
        if state == "processing":
            return "I’m editing the source image and applying only the requested change."
        if state == "success":
            if "галоч" in request or "check mark" in request or "tick" in request:
                return "Done — I added the green check mark to the source image. The edited result is below."
            return "Done — I applied the requested change to the source image. The edited result is below."
        return "I couldn’t process the image this time. The source image was not changed; please try again."
    # Russian is the default for auto-language requests written in Cyrillic.
    if state == "missing_source":
        return "Чтобы изменить именно твою фотографию, прикрепи исходное изображение. Сейчас его нет, поэтому я не буду создавать отдельную картинку вместо редактирования."
    if state == "processing":
        return "Обрабатываю исходное изображение и вношу только запрошенное изменение."
    if state == "success":
        if "галоч" in request:
            return "Готово — добавила зелёную галочку на исходное изображение. Ниже — результат редактирования."
        if "хаски" in request or "собак" in request:
            return "Готово — добавила хаски на исходную фотографию. Ниже — результат редактирования."
        return "Готово — внесла запрошенное изменение в исходное изображение. Ниже — результат редактирования."
    return "Не удалось обработать изображение в этот раз. Исходное изображение не изменено; попробуй повторить запрос."


def _build_scene(
    response: MachineResponse,
    identity: dict[str, str],
    interpretation: dict[str, Any],
    turn_index: int,
    route_meta: dict[str, Any],
) -> dict[str, Any]:
    scene = MachineScene(
        scene_id=_stable_scene_id(identity),
        turn_id=identity["message_id"],
        flow_id=identity["flow_id"],
        topic_group=_text(
            (interpretation.get("dialogue") or {}).get("continuation_context", {}).get("active_topic")
        ),
        continuation=(
            _text((interpretation.get("dialogue") or {}).get("relation")).upper()
            == "CONTINUE"
        ),
        user_id=identity["user_id"],
        conversation_id=identity["conversation_id"],
        dialogue_sequence_id=identity["dialog_id"],
        sequence_turn_index=turn_index,
        active_task=dict((interpretation.get("intent") or {})),
        dialogue_state=dict((interpretation.get("dialogue") or {})),
        dialogue_development={
            "interpretation_id": identity["interpretation_id"],
            "memory_search_engine": "state_manager_topic_section_search_v10_active_branch_repair_evidence",
        },
        result_event={
            "status": "complete",
            "provider_calls": 0 if bool((response.metadata or {}).get("local_clarification")) else 1 + int((response.metadata or {}).get("provider_retries", 0)),
            "provider_retries": int((response.metadata or {}).get("provider_retries", 0)),
            "provider_output_limit": str((response.metadata or {}).get("provider_output_limit") or 12000),
            "canonical_route": CANONICAL_ROUTE,
        },
        blocks=list(response.render_blocks or []),
        metadata={
            **dict(response.metadata or {}),
            "identity": identity,
            "canonical_route": CANONICAL_ROUTE,
            "route": route_meta,
        },
    )
    contract = build_scene_contract(scene)
    contract.authenticated_scope = {
        "user_id": identity["user_id"],
        "conversation_id": identity["conversation_id"],
        "dialogue_sequence_id": identity["dialog_id"],
    }
    return {
        "answer": response.answer,
        "content": response.content or response.answer,
        "summary": response.summary,
        "render_blocks": contract.render_blocks,
        "scene_contract": contract.__dict__,
        "artifacts": list(response.artifacts or []),
    }


def _mime_data_uri(raw: bytes, mime_type: str) -> str:
    import base64
    return f"data:{mime_type or 'application/octet-stream'};base64," + base64.b64encode(raw).decode("ascii")


def _decode_saved_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _looks_like_image_edit_request(value: Any) -> bool:
    text = _text(value)
    return bool(_detect_image_modification(text) or _detect_contextual_image_edit(text))


def _looks_like_referential_image_edit(value: Any) -> bool:
    """Only enable the latest-image fallback when the request points to a prior object."""
    low = _text(value).lower().replace("ё", "е")
    if not _looks_like_image_edit_request(low):
        return False
    return bool(re.search(
        r"(?:\b(?:на|в|по|с)\s+(?:этом|этой|этих|этот|эта|эти)\s+(?:фото\b|фотограф\w*|картинк\w*|"
        r"изображени\w*|иллюстрац\w*|рисунк\w*|снимк\w*|канистр\w*|этикетк\w*)|"
        r"\bк\s+(?:этой|той|такой)\s+иллюстрац\w*|"
        r"\b(?:ту|эту|предыдущую|прошлую)\s+(?:иллюстрац\w*|картинк\w*|изображени\w*)\b|"
        r"\b(?:на|в)\s+(?:ней|нем|н[её]м|них|этом|этой)\b|"
        r"\b(?:this|that)\s+(?:photo|image|picture|illustration|drawing|canister|label)\b|\b(?:on it|in it|on this one)\b)",
        low, re.IGNORECASE,
    ))


def _decode_image_source_item(item: dict[str, Any]) -> tuple[bytes, str] | None:
    """Decode image bytes from a current or restored visual-context item."""
    for key in ("image_url", "data_uri", "src", "image_data_uri"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith("data:image/"):
            decoded = _decode_asset_data_uri(value)
            if decoded and decoded[0]:
                return decoded
    return None


def _select_image_edit_source(visual_context: list[dict[str, Any]]) -> tuple[bytes, str, dict[str, Any]] | None:
    """Prefer a current upload, then April's latest output, then a recalled user image."""
    candidates = [item for item in (visual_context or []) if isinstance(item, dict)]
    ranked = sorted(candidates, key=lambda item: (
        0 if not item.get("recalled_from_memory") else 1,
        0 if _text(item.get("asset_role")).lower() in {"april_output", "assistant_output", "generated"} else 1,
    ))
    for item in ranked:
        decoded = _decode_image_source_item(item)
        if decoded:
            raw, mime = decoded
            return raw, mime or _text(item.get("mime_type") or "image/png"), item
    return None


def _explicit_prior_asset_reference(value: Any) -> bool:
    low = _text(value).lower().replace("ё", "е")
    markers = (
        "предыдущее фото", "предыдущую картинку", "предыдущем фото", "прошлое фото",
        "раньше присылал", "которое я присылал", "который я присылал", "которую я присылал",
        "то фото", "та картинка", "тот файл", "предыдущий файл", "предыдущий код",
        "сравни с", "сравни это", "сравни с предыдущ", "вернись к фото", "вернись к файлу",
        "на той картинке", "на предыдущей картинке", "на старой картинке",
        "на этой канистре", "на этом фото", "на этой фотографии", "на этой картинке",
        "на этом изображении", "к этой иллюстрации", "к этой картинке", "к этому изображению",
        "ту иллюстрацию, которую ты нарисовала", "ту иллюстрацию, которую ты нарисовал",
        "ту картинку, которую ты нарисовала", "ту картинку, которую ты нарисовал",
        "которую ты мне нарисовала", "которую ты мне нарисовал", "которую ты создала",
        "на ней", "на нем", "на нём", "эту канистру",
        "this canister", "this photo", "this image", "this illustration", "that illustration", "on it",
        "that image", "previous image", "previous photo", "the earlier file",
        "the file i sent", "the image i sent", "compare with", "compare to previous",
    )
    return any(marker.replace("ё", "е") in low for marker in markers)


def _requires_original_asset(value: Any, kind: str, cached_summary: str) -> bool:
    """Decide whether a follow-up needs original bytes rather than its sidecar.

    A cached summary is the default continuity representation. Original bytes are
    reattached only when the user explicitly references an earlier asset or asks
    for exact extraction/verification/editing that a summary cannot safely supply.
    This gate does not decide whether to generate an image; Interpretation owns
    that decision independently.
    """
    text = _text(value).lower().replace("ё", "е")
    is_image_asset = str(kind or "").lower() in {"image", "image/png", "image/jpeg"}
    if is_image_asset and _detect_image_modification(text) and not _looks_like_referential_image_edit(text):
        # "Draw on a photo" without an attachment does not identify which old
        # image is intended. Do not silently borrow a historical picture.
        return False
    if is_image_asset and (
        _looks_like_referential_image_edit(text)
        or (_detect_contextual_image_edit(text) and not _detect_image_modification(text))
    ):
        return True
    if not cached_summary or _explicit_prior_asset_reference(text):
        return True

    exact_read_markers = (
        "что написано", "что там написано", "прочитай текст", "прочти текст",
        "прочитай номер", "какой номер", "номер документа", "текст на фото",
        "текст на изображении", "перепиши текст", "проверь данные на",
        "приблизь", "увеличь фрагмент", "разбери мелкий текст",
        "read the text", "what does it say", "extract the text", "read the number",
        "zoom in", "verify the details", "transcribe the image", "ocr this",
        "по этому фото", "по этой фотографии", "по этой картинке", "на основе фото",
        "на основе этой картинки", "используй фото как референс", "используй картинку как референс",
        "сделай вариант по фото", "как на этой фотографии", "отредактируй изображение",
    )
    if any(marker in text for marker in exact_read_markers):
        return True

    if str(kind or "").lower() in {"file", "text_file"}:
        source_edit_markers = (
            "исправь код", "исправь файл", "измени файл", "обнови код",
            "улучши код", "оптимизируй код", "перепиши код", "улучши файл",
            "найди ошибку в", "покажи полный код", "разбери строку",
            "исправь этот скрипт", "refactor the code", "fix the code",
            "improve the code", "optimize the code", "rewrite the code",
            "edit the file", "patch the source", "show the full source",
            "trace the bug in",
        )
        if any(marker in text for marker in source_edit_markers):
            return True

    return False


def _source_code_from_block(block: dict[str, Any]) -> tuple[str, str, str] | None:
    language = _text(block.get("language") or block.get("lang") or "text").lower()
    filename = _text(block.get("filename") or "")
    code = _text(block.get("code") or block.get("content") or block.get("text"))
    if not code:
        return None
    # Accept a single fenced block while preserving internal source lines.
    match = re.fullmatch(r"```[\w.+-]*\s*\n(.*?)\n```", code, flags=re.S)
    if match:
        code = match.group(1)
    extensions = {
        "python": "py", "py": "py", "javascript": "js", "js": "js",
        "typescript": "ts", "ts": "ts", "tsx": "tsx", "jsx": "jsx",
        "json": "json", "sql": "sql", "bash": "sh", "shell": "sh",
        "html": "html", "css": "css", "yaml": "yml", "toml": "toml",
        "markdown": "md", "md": "md", "text": "txt",
    }
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else extensions.get(language, "txt")
    allowed_exts = {"py", "js", "ts", "tsx", "jsx", "json", "sql", "sh", "html", "css", "yml", "toml", "md", "txt"}
    if ext not in allowed_exts:
        ext = extensions.get(language, "txt")
    return code, language, ext


def _persist_asset_analysis_summaries(
    uid: str,
    identity: dict[str, str],
    attachment_index: list[dict[str, Any]],
    memory_record: Any,
) -> int:
    """Keep provider-grounded attachment summaries in the canonical memory record."""
    if not isinstance(memory_record, dict):
        return 0

    allowed: list[dict[str, str]] = []
    for item in attachment_index:
        if not isinstance(item, dict):
            continue
        role = _text(item.get("asset_role") or "user_input")
        kind = _text(item.get("kind")).lower()
        if role != "user_input" or kind not in {"image", "text_file", "file"}:
            continue
        if not bool(item.get("source_bytes_attached", True)):
            continue
        filename = os.path.basename(_text(item.get("filename")))[:240]
        message_id = _text(item.get("asset_message_id") or identity.get("message_id"))
        if filename and message_id:
            allowed.append({"filename": filename, "kind": kind, "message_id": message_id, "role": role})

    # De-duplicate index entries contributed by both metadata and content readers.
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in allowed:
        key = (item["message_id"], item["filename"], item["kind"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    allowed = deduped
    if not allowed:
        return 0

    raw_summaries = memory_record.get("attachment_summaries")
    summaries = [dict(item) for item in raw_summaries if isinstance(item, dict)] if isinstance(raw_summaries, list) else []

    # Compatibility with providers that return the established memory fields but
    # omit per-asset records: only use a fallback when one-to-one attribution is
    # unambiguous. Never copy a composite answer onto every attached file.
    if not summaries:
        images = [item for item in allowed if item["kind"] == "image"]
        files = [item for item in allowed if item["kind"] in {"file", "text_file"}]
        observations = memory_record.get("visual_observations")
        if len(images) == 1 and isinstance(observations, list) and observations:
            summaries.append({
                **images[0],
                "asset_message_id": images[0]["message_id"],
                "summary": "; ".join(_text(item) for item in observations if _text(item))[:1200],
            })
        file_purpose = _text(memory_record.get("file_purpose"))
        if len(files) == 1 and file_purpose:
            symbols = memory_record.get("code_symbols")
            symbol_text = ", ".join(_text(item) for item in symbols[:8] if _text(item)) if isinstance(symbols, list) else ""
            summaries.append({
                **files[0],
                "asset_message_id": files[0]["message_id"],
                "summary": (file_purpose + (f" Key elements: {symbol_text}" if symbol_text else ""))[:1200],
            })

    changed = 0
    for summary_item in summaries[:12]:
        filename = os.path.basename(_text(summary_item.get("filename")))[:240]
        kind = _text(summary_item.get("kind")).lower()
        summary_text = _text(summary_item.get("summary"))[:1200]
        details = summary_item.get("key_details")
        if not isinstance(details, list):
            details = []
        requested_message_id = _text(summary_item.get("asset_message_id") or summary_item.get("message_id"))
        if requested_message_id in {"current", "this_message"}:
            requested_message_id = _text(identity.get("message_id"))
        candidates = [
            item for item in allowed
            if item["filename"] == filename
            and (not kind or item["kind"] == kind)
            and (not requested_message_id or item["message_id"] == requested_message_id)
        ]
        if not candidates and not requested_message_id and filename:
            candidates = [item for item in allowed if item["filename"] == filename and (not kind or item["kind"] == kind)]
        if len(candidates) != 1:
            continue
        target = candidates[0]
        if target["role"] != "user_input" or not summary_text:
            continue
        index_matches = [
            item for item in attachment_index
            if isinstance(item, dict)
            and os.path.basename(_text(item.get("filename")))[:240] == target["filename"]
            and _text(item.get("kind")).lower() == target["kind"]
            and _text(item.get("asset_message_id") or identity.get("message_id")) == target["message_id"]
            and _text(item.get("asset_role") or "user_input") == "user_input"
        ]
        if len(index_matches) != 1:
            continue
        # These bounded semantic fields are saved as part of structured_request
        # inside dialogue_memory; no sidecar-table update is required.
        index_matches[0]["analysis_summary"] = summary_text
        index_matches[0]["analysis_key_details"] = [
            _text(item)[:220] for item in details if _text(item)
        ][:8]
        changed += 1

    if changed:
        print(
            "STATE: DIALOGUE MEMORY ATTACHMENT SUMMARIES INDEXED "
            + json.dumps({"count": changed, "source": "provider_attachment_summaries"}, ensure_ascii=False),
            flush=True,
        )
    return changed


def _restore_selected_assets(
    uid: str,
    identity: dict[str, str],
    dialogue_context: dict[str, Any],
    visual_context: list[dict[str, Any]],
    attachments: list[dict[str, Any]],
    file_inputs: list[dict[str, Any]],
    file_contents: list[dict[str, Any]],
    current_request: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Restore sidecars for the selected authenticated turn and original bytes on demand.

    Current uploads take precedence. A known older asset is represented by its
    semantic sidecar for ordinary continuity; original bytes are reattached only
    when precise inspection, editing, comparison, or an uncached first analysis is
    required.
    """
    has_current_asset = bool(visual_context or file_inputs or file_contents)
    if has_current_asset and not _explicit_prior_asset_reference(current_request):
        return visual_context, attachments, file_inputs, file_contents, []

    selected = dialogue_context.get("selected_pairs") or []
    anchor = dialogue_context.get("anchor") or {}
    message_ids: list[str] = []
    if isinstance(anchor, dict) and _text(anchor.get("message_id")):
        message_ids.append(_text(anchor.get("message_id")))
    for item in selected:
        if isinstance(item, dict) and _text(item.get("message_id")):
            message_ids.append(_text(item.get("message_id")))
    message_ids = list(dict.fromkeys(message_ids))[:8]

    relation = _text(dialogue_context.get("relation")).upper()
    # Semantic search can label a referential edit as NEW when the user's current
    # sentence names a visible object (e.g. "на этой канистре") but the previous
    # turn's user text was only "Что здесь?". In that narrow case, restore the most
    # recent same-dialog image candidate within Premium's 24-hour retention window.
    # A generic "draw on a photo" request must never silently borrow an older image:
    # when no source is attached, the Premium Interpreter decides whether the user
    # wants a new image or explicitly refers to a particular existing source.
    referential_edit = _looks_like_referential_image_edit(current_request)
    fallback_used = False
    if relation != "CONTINUE" and not (not has_current_asset and referential_edit):
        return visual_context, attachments, file_inputs, file_contents, []
    if not has_current_asset and referential_edit and (relation != "CONTINUE" or not message_ids):
        candidates = [item for item in (dialogue_context.get("candidates") or []) if isinstance(item, dict)]
        now_ts = time.time()
        recent_images = []
        request_low = _text(current_request).lower().replace("ё", "е")
        subject_terms = [term for term in ("канистр", "этикетк", "масл", "собак", "хаски", "автомобил", "машин", "кот", "собак") if term in request_low]
        for candidate in candidates:
            if not bool(candidate.get("same_dialog")):
                continue
            if "image" not in set(candidate.get("row_modalities") or []):
                continue
            try:
                age = now_ts - float(candidate.get("created_at") or 0)
            except (TypeError, ValueError, OverflowError):
                continue
            if age < -60 or age > 24 * 60 * 60:
                continue
            candidate_id = _text(candidate.get("message_id"))
            if not candidate_id:
                continue
            evidence = " ".join(_text(candidate.get(key)) for key in ("topic", "user", "april", "attachment_evidence")).lower().replace("ё", "е")
            if subject_terms and not any(term in evidence for term in subject_terms):
                continue
            recent_images.append((float(candidate.get("created_at") or 0), candidate_id))
        if recent_images:
            recent_images.sort(reverse=True)
            message_ids = [recent_images[0][1]]
            fallback_used = True
        elif relation != "CONTINUE":
            return visual_context, attachments, file_inputs, file_contents, []
    if not message_ids:
        return visual_context, attachments, file_inputs, file_contents, []
    # Binary sidecars are scoped to the same message row as dialogue_memory.
    # Only the selected topic/turn IDs are read; no global asset scan is performed.
    rows = _load_premium_assets(uid, message_ids)
    # PostgreSQL is the durable source for generated output bytes. File sidecars
    # remain a fast path, but a container restart must not make a saved image
    # disappear from a continued scene.
    try:
        from storage import load_dialogue_asset_payloads
        database_rows = load_dialogue_asset_payloads(uid, message_ids)
    except Exception:
        database_rows = []
    import base64
    import json as _json
    existing_asset_keys = set()
    for asset in rows:
        raw_existing = bytes(asset.get("content") or b"")
        existing_asset_keys.add((_text(asset.get("message_id")), hashlib.sha256(raw_existing).hexdigest()))
    for database_row in database_rows:
        payloads = database_row.get("asset_payloads") if isinstance(database_row, dict) else []
        if isinstance(payloads, str):
            try:
                payloads = _json.loads(payloads)
            except (TypeError, ValueError):
                payloads = []
        if not isinstance(payloads, list):
            continue
        for payload in payloads:
            if not isinstance(payload, dict) or _text(payload.get("kind")).lower() != "image":
                continue
            encoded = _text(payload.get("content_base64"))
            if not encoded:
                continue
            try:
                content = base64.b64decode(encoded, validate=True)
            except Exception:
                continue
            if not content:
                continue
            message_key = _text(payload.get("message_id") or database_row.get("message_id"))
            digest = _text(payload.get("sha256")) or hashlib.sha256(content).hexdigest()
            asset_key = (message_key, digest)
            if asset_key in existing_asset_keys:
                continue
            existing_asset_keys.add(asset_key)
            rows.append({
                "message_id": message_key,
                "filename": _text(payload.get("filename") or "april-generated-image.png"),
                "kind": "image",
                "mime_type": _text(payload.get("mime_type") or "image/png"),
                "content": content,
                "size_bytes": len(content),
                "asset_role": _text(payload.get("asset_role") or "april_output"),
                "metadata": {
                    "source_type": "april_generated",
                    "asset_role": "april_output",
                    "output_type": "image",
                    "prompt": _text(payload.get("prompt"))[:1200],
                    "width": int(payload.get("width") or 0),
                    "height": int(payload.get("height") or 0),
                    "operation": _text(payload.get("operation") or "generate"),
                    "derived_from_message_id": _text(payload.get("derived_from_message_id")),
                    "source_asset_role": _text(payload.get("source_asset_role")),
                },
            })
    def _asset_sequence_index(asset: dict[str, Any]) -> int:
        metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
        try:
            return int(metadata.get("sequence_index")) if metadata.get("sequence_index") is not None else 9999
        except (TypeError, ValueError, OverflowError):
            return 9999

    rows.sort(key=_asset_sequence_index)
    restored_meta: list[dict[str, Any]] = []
    for asset in rows:
        raw = bytes(asset.get("content") or b"")
        if not raw:
            continue
        kind = _text(asset.get("kind")).lower()
        filename = _text(asset.get("filename") or "attachment")
        mime_type = _text(asset.get("mime_type") or "application/octet-stream")
        asset_metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
        source_type = _text(asset_metadata.get("source_type") or kind)
        asset_role = _text(
            asset.get("asset_role")
            or asset_metadata.get("asset_role")
            or ("april_output" if source_type in {"april_generated", "generated_image", "april_output", "generated_file"} else "user_input")
        )
        analysis_summary = _text(asset_metadata.get("analysis_summary"))[:1200]
        try:
            sequence_index = int(asset_metadata.get("sequence_index")) if asset_metadata.get("sequence_index") is not None else 9999
        except (TypeError, ValueError, OverflowError):
            sequence_index = 9999
        analysis_key_details = asset_metadata.get("analysis_key_details")
        if not isinstance(analysis_key_details, list):
            analysis_key_details = []
        analysis_key_details = [_text(item)[:220] for item in analysis_key_details if _text(item)][:8]
        restore_original = _requires_original_asset(current_request, kind, analysis_summary)
        common = {
            "filename": filename,
            "content_type": mime_type,
            "mime_type": mime_type,
            "sequence_index": sequence_index,
            "kind": kind,
            "size_bytes": int(asset.get("size_bytes") or len(raw)),
            "source_type": source_type,
            "asset_role": asset_role,
            "output_type": _text(asset_metadata.get("output_type")),
            "provider_readable": True,
            "recalled_from_memory": True,
            "asset_message_id": _text(asset.get("message_id")),
            "analysis_summary": analysis_summary,
            "analysis_key_details": analysis_key_details,
            "requires_original_analysis": restore_original,
        }
        metadata_item = {k: common[k] for k in ("filename", "mime_type", "kind", "sequence_index", "asset_role", "output_type", "asset_message_id", "analysis_summary", "analysis_key_details")}
        if asset_role.lower() in {"april_output", "assistant_output", "generated"} and (kind == "image" or mime_type.startswith("image/")):
            # This is an answer artifact, not a user-uploaded picture. Keep its
            # bytes available for the Gallery renderer, but never feed it back as
            # an input image that would cause analyze_image to swallow the output.
            metadata_item["_content_data_uri"] = _mime_data_uri(raw, mime_type if mime_type.startswith("image/") else "image/png")
            metadata_item["width"] = int(asset_metadata.get("width") or 0)
            metadata_item["height"] = int(asset_metadata.get("height") or 0)
            metadata_item["prompt"] = _text(asset_metadata.get("prompt"))[:1200]
            # Generated images are not input images during ordinary follow-ups.
            # For an explicit edit, however, the latest April output is often the
            # correct source (e.g. "make it brighter" after a generated picture).
            relation_for_asset = _text(dialogue_context.get("relation")).upper()
            should_use_saved_output_as_edit_source = bool(
                _looks_like_referential_image_edit(current_request)
                or (
                    relation_for_asset == "CONTINUE"
                    and _detect_contextual_image_edit(current_request)
                    and not _detect_image_modification(current_request)
                )
            )
            if should_use_saved_output_as_edit_source:
                visual_context.append({
                    "type": "input_image",
                    "image_url": metadata_item["_content_data_uri"],
                    "filename": filename,
                    "source_type": source_type,
                    "mime_type": mime_type,
                    "sequence_index": sequence_index,
                    "recalled_from_memory": True,
                    "asset_message_id": common["asset_message_id"],
                    "asset_role": asset_role,
                    "output_type": common["output_type"],
                    "analysis_summary": analysis_summary,
                    "analysis_key_details": analysis_key_details,
                    "requires_original_analysis": True,
                })
            restored_meta.append(metadata_item)
            continue

        attachments.append(common)
        restored_meta.append(metadata_item)

        # Recalled assets with a valid sidecar normally enter the dialogue as
        # semantic context only. Reattach the original bytes for precise reads,
        # explicit references, modifications, or when no sidecar exists yet.
        if not restore_original:
            continue

        if kind == "image" or mime_type.startswith("image/"):
            data_uri = _mime_data_uri(raw, mime_type if mime_type.startswith("image/") else "image/png")
            visual_context.append({
                "type": "input_image",
                "image_url": data_uri,
                "filename": filename,
                "source_type": common["source_type"],
                "mime_type": mime_type,
                "sequence_index": sequence_index,
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
                "asset_role": asset_role,
                "output_type": common["output_type"],
                "analysis_summary": analysis_summary,
                "analysis_key_details": analysis_key_details,
                "requires_original_analysis": True,
            })
        elif kind == "text_file":
            # Re-decode the preserved original bytes instead of trusting the
            # text_content sidecar: older versions stored only the first 18k
            # characters there, so preferring it would keep old assets clipped
            # even after the input-reader limit is raised.
            decoded_source = _decode_saved_text(raw)
            text_value = decoded_source or _text(asset.get("text_content"))
            source_chars = len(text_value)
            reader_truncated = source_chars > 48000
            file_contents.append({
                "filename": filename,
                "mime_type": mime_type or "text/plain",
                "sequence_index": sequence_index,
                "content": text_value[:48000],
                "size_bytes": len(raw),
                "reader_truncated": reader_truncated,
                "source_chars": source_chars,
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
                "asset_role": asset_role,
                "output_type": common["output_type"],
                "analysis_summary": analysis_summary,
                "analysis_key_details": analysis_key_details,
                "requires_original_analysis": True,
            })
        else:
            file_inputs.append({
                "type": "input_file",
                "filename": filename,
                "sequence_index": sequence_index,
                "file_data": _mime_data_uri(raw, mime_type),
                "mime_type": mime_type,
                "size_bytes": len(raw),
                "recalled_from_memory": True,
                "asset_message_id": common["asset_message_id"],
                "asset_role": asset_role,
                "output_type": common["output_type"],
                "analysis_summary": analysis_summary,
                "analysis_key_details": analysis_key_details,
                "requires_original_analysis": True,
            })
    if file_contents:
        restored_text_budget = min(48_000, max(12_000, 120_000 // max(1, len(file_contents))))
        for file_item in file_contents:
            original_text = _text(file_item.get("content"))
            file_item.setdefault("persistence_content", original_text)
            if len(original_text) > restored_text_budget:
                file_item["content"] = original_text[:restored_text_budget]
                file_item["reader_truncated"] = True

    if restored_meta:
        # Do not place OCR or semantic details from documents into operational
        # logs. The returned metadata still carries the sidecar into Provider.
        log_assets = [
            {
                "filename": item.get("filename"),
                "kind": item.get("kind"),
                "asset_role": item.get("asset_role"),
                "asset_message_id": item.get("asset_message_id"),
                "analysis_cached": bool(item.get("analysis_summary")),
            }
            for item in restored_meta
        ]
        print(
            "STATE: DIALOGUE ASSETS RESTORED "
            + json.dumps({"count": len(restored_meta), "assets": log_assets}, ensure_ascii=False),
            flush=True,
        )
    return visual_context, attachments, file_inputs, file_contents, restored_meta


def _image_payload_bytes(value: Any) -> tuple[bytes, str] | None:
    """Extract generated image bytes for binary asset persistence, if present."""
    import base64
    visited = 0
    stack = [value]
    while stack and visited < 500:
        visited += 1
        item = stack.pop()
        if isinstance(item, dict):
            for key in ("image_data_uri", "data_uri", "src", "url", "image"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.startswith("data:image/") and ";base64," in candidate:
                    header, encoded = candidate.split(",", 1)
                    mime = header[5:].split(";", 1)[0] or "image/png"
                    try:
                        raw = base64.b64decode(encoded, validate=True)
                        if raw:
                            return raw, mime
                    except Exception:
                        pass
            for key in ("image_base64", "base64", "b64_json"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate:
                    try:
                        raw = base64.b64decode(candidate, validate=True)
                        if raw and raw.startswith(b"\x89PNG\r\n\x1a\n"):
                            return raw, "image/png"
                    except Exception:
                        pass
            stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
        elif isinstance(item, list):
            stack.extend(v for v in item if isinstance(v, (dict, list)))
    return None


def _strip_inline_binary(value: Any) -> Any:
    """Keep canonical dialogue-memory JSON compact by stripping inline binary payloads."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            low = str(key).lower()
            if low in {"image_base64", "image_data_uri", "data_uri", "file_data", "b64_json"}:
                continue
            if (
                low in {"image_url", "src", "url", "image"}
                and isinstance(item, str)
                and item.startswith("data:")
                and ";base64," in item
            ):
                continue
            cleaned[key] = _strip_inline_binary(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_inline_binary(item) for item in value]
    if isinstance(value, str):
        # Also catch a data URI embedded in a larger JSON/text field, not only
        # values that consist solely of the URI.
        if value.startswith("data:") and ";base64," in value:
            return "[binary payload omitted from persistent dialogue memory]"
        return re.sub(
            r"data:[^,\s;]+(?:;[^,\s;]+)*;base64,[A-Za-z0-9+/=_-]+",
            "[binary payload omitted from persistent dialogue memory]",
            value,
        )
    return value


async def execute(
    user_id: str,
    chat_id: Any = None,
    text: str = "",
    *,
    internal_text: str = "",
    display_language: str = "auto",
    flow_id: str = "",
    conversation_id: str = "",
    dialog_id: str = "",
    message_id: str = "",
    resume_message_id: str = "",
    interpretation_id: str = "",
    visual_context: list[dict[str, Any]] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    file_inputs: list[dict[str, Any]] | None = None,
    file_contents: list[dict[str, Any]] | None = None,
    translation: dict[str, Any] | None = None,
    message_created_at: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    pipeline_started = time.perf_counter()
    progress_sink = kwargs.get("progress_sink") if callable(kwargs.get("progress_sink")) else None
    uid = _text(user_id)
    original = _text(text)
    current_text = _text(internal_text or original)
    if not uid:
        raise ValueError("USER_ID_REQUIRED")
    file_inputs = [
        dict(item)
        for item in (file_inputs or [])
        if isinstance(item, dict)
        and _text(item.get("file_data"))
    ]
    file_contents = [
        dict(item)
        for item in (file_contents or [])
        if isinstance(item, dict) and _text(item.get("content"))
    ]
    visual_context = [dict(item) for item in (visual_context or []) if isinstance(item, dict)]
    attachments = [dict(item) for item in (attachments or []) if isinstance(item, dict)]
    if not current_text and not visual_context and not file_inputs and not file_contents:
        raise ValueError("EMPTY_REQUEST")

    # Processor owns DB bootstrap; harmless and idempotent after the first call.
    db_started = time.perf_counter()
    init_db()
    _apr_timing_log("db_bootstrap", db_started, user_key=_apr_diag_ref(uid))

    require_auth = str(os.getenv("APRIL_REQUIRE_AUTH", "1")).lower() not in {"0", "false", "no"}
    auth_started = time.perf_counter()
    if require_auth and not is_authenticated_user(uid):
        raise ValueError("AUTHENTICATED_USER_REQUIRED")
    _apr_timing_log("auth_check", auth_started, user_key=_apr_diag_ref(uid), required=require_auth)

    identity_started = time.perf_counter()
    payload_identity = {
        "dialog_id": dialog_id or conversation_id,
        "conversation_id": conversation_id or dialog_id,
        "message_id": message_id,
        "flow_id": flow_id,
        "interpretation_id": interpretation_id,
    }
    identity = resolve_dialog_identity(
        payload_identity,
        user_id=uid,
        flow_id=flow_id,
    )
    identity["interpretation_id"] = (
        _text(interpretation_id)
        or build_interpretation_identity(
            april_id=identity["user_id"],
            conversation_id=identity["conversation_id"],
            dialog_id=identity["dialog_id"],
            message_id=identity["message_id"],
            flow_id=identity["flow_id"],
        )["interpretation_id"]
    )
    _apr_timing_log(
        "identity_bind", identity_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        flow_key=_apr_diag_ref(identity.get("flow_id")),
    )

    # First infer the overall semantic direction, intent, time scope and memory
    # need; only then split the request into ordered questions. The classifier is
    # local/deterministic and does not add an API call or replace the existing splitter.
    memory_started = time.perf_counter()
    semantic_started = time.perf_counter()
    semantic_interpretation = interpret_request_semantics(original or current_text)
    _apr_timing_log(
        "semantic_preinterpretation", semantic_started,
        user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        semantic_intent=semantic_interpretation.get("primary_intent"),
        search_direction=semantic_interpretation.get("direction"),
        time_scope=semantic_interpretation.get("time_scope"),
        topic_reference=semantic_interpretation.get("topic_reference"),
        requires_memory=bool(semantic_interpretation.get("requires_memory")),
        history_request=bool(semantic_interpretation.get("history_request")),
        intent_score=semantic_interpretation.get("intent_score"),
        intent_features=semantic_interpretation.get("features"),
        reason=semantic_interpretation.get("reason"),
    )
    question_sequence = build_question_sequence(
        original or current_text, parent_interpretation=semantic_interpretation
    )
    normalized_semantics = interpret_request_semantics(current_text)
    normalized_sequence = build_question_sequence(
        current_text, parent_interpretation=normalized_semantics
    )
    _apr_timing_log(
        "question_decomposition_result",
        user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        question_count=len(question_sequence),
        questions=[{
            "step_index": item.get("step_index"),
            "request_key": _apr_diag_ref(item.get("request")),
            "semantic_intent": item.get("semantic_intent"),
            "output_types": item.get("output_types", ["text"]),
            "search_direction": item.get("search_direction"),
            "time_scope": item.get("time_scope"),
            "history_request": bool(item.get("history_request")),
            "reason": item.get("semantic_reason"),
        } for item in question_sequence],
    )
    has_voice_input = any(_text(item.get("kind")).lower() == "voice" for item in attachments)
    search_kwargs = {
        "dialog_id": identity["dialog_id"],
        "conversation_id": identity["conversation_id"],
        # Only set by a deliberate History-card click; this is a one-turn anchor.
        "resume_message_id": _text(resume_message_id),
        "limit": 12,
        "has_image": bool(visual_context),
        "has_file": bool(file_inputs or file_contents),
        "has_voice": has_voice_input,
    }
    question_contexts: list[dict[str, Any]] = []

    if len(question_sequence) <= 1:
        single_semantics = {
            "schema": "april_request_semantics_v1",
            "primary_intent": semantic_interpretation.get("primary_intent"),
            "direction": semantic_interpretation.get("direction"),
            "time_scope": semantic_interpretation.get("time_scope"),
            "topic_reference": semantic_interpretation.get("topic_reference"),
            "requires_memory": semantic_interpretation.get("requires_memory"),
            "history_request": semantic_interpretation.get("history_request"),
            "history_inventory_request": semantic_interpretation.get("history_inventory_request"),
            "has_explicit_time_window": semantic_interpretation.get("has_explicit_time_window"),
            "time_window": semantic_interpretation.get("time_window") or {},
            "requested_topic_count": semantic_interpretation.get("requested_topic_count"),
            "minimum_topic_count": semantic_interpretation.get("minimum_topic_count"),
            "search_scope": semantic_interpretation.get("search_scope"),
            "relation_hint": semantic_interpretation.get("relation_hint"),
            "explicit_topic_switch": bool(semantic_interpretation.get("explicit_topic_switch")),
            "reason": semantic_interpretation.get("reason"),
            "speech_act": semantic_interpretation.get("speech_act"),
            "communicative_act": semantic_interpretation.get("communicative_act"),
            "pragmatic_intent": semantic_interpretation.get("pragmatic_intent"),
            "message_function": semantic_interpretation.get("message_function"),
            "pragmatic_features": semantic_interpretation.get("pragmatic_features", {}),
            "tone": semantic_interpretation.get("tone", "NEUTRAL"),
            "recommended_response_action": semantic_interpretation.get("recommended_response_action", "ANSWER_NORMALLY"),
            "features": semantic_interpretation.get("features", {}),
            "context_signature": semantic_interpretation.get("context_signature", {}),
        }
        # When Interpretation says that this is independent new information and
        # does not require memory, do not hydrate/rank every Premium dialogue row
        # merely to answer a normal message. That full pass can take tens of seconds
        # on a busy database and may incorrectly pull an unrelated hot-work branch
        # into a casual exchange. Keep all explicit history, continuation, repair,
        # reference, temporal and resume signals on the canonical State Manager path.
        _single_features = single_semantics.get("features") if isinstance(single_semantics.get("features"), dict) else {}
        _single_pragmatic = single_semantics.get("pragmatic_features") if isinstance(single_semantics.get("pragmatic_features"), dict) else {}
        _single_topic_reference = _text(single_semantics.get("topic_reference")).upper()
        _single_direction = _text(single_semantics.get("direction")).upper()
        _single_relation_hint = _text(single_semantics.get("relation_hint")).upper()
        _explicit_context_signal = bool(
            single_semantics.get("history_request")
            or single_semantics.get("history_inventory_request")
            or single_semantics.get("has_explicit_time_window")
            or single_semantics.get("explicit_topic_switch")
            or single_semantics.get("active_branch_repair")
            or single_semantics.get("previous_answer_reference")
            or single_semantics.get("factual_verification_request")
            or _single_topic_reference in {"PREVIOUS_OR_ACTIVE_TOPIC", "PREVIOUS_ASSISTANT_ANSWER", "TOPIC_FRAGMENT"}
            or _single_direction in {"RESUME_OR_RETRIEVE_ACTIVE_TOPIC", "SEARCH_ACTIVE_OR_REFERENCED_TOPIC"}
            or _single_relation_hint in {"CONTINUE", "HISTORY_LOOKUP"}
            or any(bool(_single_features.get(key)) for key in (
                "context_dependent_question", "context_dependent_reaction", "topic_reference_fragment",
                "previous_answer_reference", "active_branch_repair", "selection_followup_candidate",
                "explicit_previous_answer_correction", "factual_verification_request",
                "recall_action", "continuation_action", "answer_followup",
            ))
            or any(bool(_single_pragmatic.get(key)) for key in (
                "previous_answer_reference", "active_branch_repair", "deictic_reference",
                "topic_reference_fragment", "clarification_request", "continuation_request",
                "revision_request", "factual_verification_request",
            ))
        )
        skip_memory_search = bool(
            single_semantics.get("primary_intent") == "NEW_INFORMATION"
            and not single_semantics.get("requires_memory")
            and not single_semantics.get("history_request")
            and not _text(resume_message_id)
            and not _explicit_context_signal
        )
        if skip_memory_search:
            dialogue_context = {
                "window_hours": 24,
                "relation": "NEW",
                "relation_confidence": 1.0,
                "active_branch_repair": False,
                "active_branch": {},
                "active_work_branch": {},
                "hot_work_followup": False,
                "hot_work_match_reason": "",
                "user_operation": {},
                "source_retrieval": {},
                "previous_answer_reference": False,
                "factual_verification_request": False,
                "explicit_topic_switch": False,
                "reason": "self_contained_new_topic_fast_path",
                "active_topic": _text(original or current_text)[:140],
                "selected_pairs": [],
                "candidates": [],
                "matches": [],
                "history_topics": [],
                "topic_index": [],
                "known_topic_count": 0,
                "history_request": False,
                "contextual_history_match": False,
                "matched_topic_count": 0,
                "requested_topic_count": 10,
                "minimum_topic_count": 0,
                "time_window": {},
                "time_filter": {},
                "topic_table_markdown": "",
                "anchor": {},
                "selected_section": {},
                "clarification_needed": False,
                "clarification_prompt": "",
                "pending_clarification": {},
                "clarification_resolution": {},
                "search": {"relation": "NEW", "total_pairs": 0, "candidate_count": 0},
            }
        else:
            dialogue_context = prepare_dialogue_context(
                uid, current_text, query_interpretation=single_semantics, **search_kwargs
            )
        if question_sequence:
            question_sequence[0]["dialogue_search"] = _compact_question_search(
                dialogue_context, current_text, single_semantics
            )
        _apr_timing_log(
            "request_question_search", memory_started,
            user_key=_apr_diag_ref(uid),
            dialog_key=_apr_diag_ref(identity.get("dialog_id")),
            message_key=_apr_diag_ref(identity.get("message_id")),
            step_index=question_sequence[0].get("step_index") if question_sequence else 1,
            query_key=_apr_diag_ref(current_text),
            semantic_intent=single_semantics.get("primary_intent"),
            search_direction=single_semantics.get("direction"),
            history_request=bool(dialogue_context.get("history_request")),
            relation=dialogue_context.get("relation"),
            candidates=len(dialogue_context.get("candidates") or []),
            selected_pairs=len(dialogue_context.get("selected_pairs") or []),
            topic_index_count=len(dialogue_context.get("topic_index") or []),
            status="self_contained_new_topic_fast_path" if skip_memory_search else "ok",
        )
    else:
        current_request_subject_context: dict[str, Any] | None = None
        parent_repair_turn = bool(
            semantic_interpretation.get("active_branch_repair")
            or (semantic_interpretation.get("pragmatic_features") or {}).get("active_branch_repair")
            or (semantic_interpretation.get("features") or {}).get("active_branch_repair")
        )
        # A self-contained NEW turn whose clauses do not request prior context should
        # not run a full cross-history ranking once per clause. Any continuation,
        # explicit history request, attachment, resume anchor, correction or choice
        # candidate still uses State Manager and must pass its normal confirmation.
        compound_turn_is_new = bool(
            semantic_interpretation.get("primary_intent") == "NEW_INFORMATION"
            and not semantic_interpretation.get("requires_memory")
            and not semantic_interpretation.get("history_request")
            and not _text(resume_message_id)
            and not visual_context and not file_inputs and not file_contents and not attachments
            and not any(
                item.get("requires_memory") or item.get("history_request")
                or item.get("active_branch_repair")
                or (item.get("features") or {}).get("selection_followup_candidate")
                for item in question_sequence if isinstance(item, dict)
            )
        )
        # Use the same original-language clause that was classified. Equal list lengths
        # do not guarantee that separately split normalized text is aligned item by item.
        for index, question_item in enumerate(question_sequence):
            search_query = _text(question_item.get("request")) or (
                _text(normalized_sequence[index].get("request"))
                if index < len(normalized_sequence) else _text(current_text)
            )
            try:
                inherits_subject = bool(question_item.get("inherits_current_request_subject"))
                task_semantics = {
                    "schema": "april_request_semantics_v1",
                    "primary_intent": question_item.get("semantic_intent", "NEW_INFORMATION"),
                    "direction": question_item.get("search_direction", "ANSWER_NEW_REQUEST"),
                    "time_scope": question_item.get("time_scope", "UNSPECIFIED"),
                    "topic_reference": question_item.get("topic_reference", "UNSPECIFIED"),
                    "requires_memory": False if inherits_subject else question_item.get("requires_memory", False),
                    "history_request": False if inherits_subject else question_item.get("history_request", False),
                    "history_inventory_request": False if inherits_subject else question_item.get("history_request", False),
                    "has_explicit_time_window": bool(question_item.get("has_explicit_time_window")),
                    "time_window": question_item.get("time_window") if isinstance(question_item.get("time_window"), dict) else {},
                    "requested_topic_count": question_item.get("requested_topic_count"),
                    "minimum_topic_count": question_item.get("minimum_topic_count"),
                    "search_scope": "CURRENT_REQUEST_SUBJECT" if inherits_subject else ("ALL_DIALOGUE_HISTORY" if question_item.get("history_request") else (
                        "TOPIC_OR_ACTIVE_CONTEXT" if question_item.get("requires_memory") else "CURRENT_DIALOGUE"
                    )),
                    "relation_hint": "NEW" if inherits_subject else ("HISTORY_LOOKUP" if question_item.get("history_request") else "CONTINUE" if question_item.get("requires_memory") else "NEW"),
                    "reason": "pronoun_inherits_subject_from_current_request" if inherits_subject else question_item.get("semantic_reason", ""),
                    "explicit_topic_switch": bool(question_item.get("explicit_topic_switch")),
                    "active_branch_repair": bool(question_item.get("active_branch_repair")),
                    "previous_answer_reference": bool(question_item.get("previous_answer_reference")),
                    "factual_verification_request": bool(question_item.get("factual_verification_request")),
                    "speech_act": question_item.get("speech_act") or (semantic_interpretation.get("speech_act") if index == 0 else ""),
                    "communicative_act": question_item.get("communicative_act") or (semantic_interpretation.get("communicative_act") if index == 0 else ""),
                    "pragmatic_intent": question_item.get("pragmatic_intent") or (semantic_interpretation.get("pragmatic_intent") if index == 0 else ""),
                    "message_function": question_item.get("message_function") or (semantic_interpretation.get("message_function") if index == 0 else ""),
                    "pragmatic_features": question_item.get("pragmatic_features") or (semantic_interpretation.get("pragmatic_features", {}) if index == 0 else {}),
                    "tone": question_item.get("tone") or (semantic_interpretation.get("tone", "NEUTRAL") if index == 0 else "NEUTRAL"),
                    "recommended_response_action": question_item.get("recommended_response_action") or (semantic_interpretation.get("recommended_response_action", "ANSWER_NORMALLY") if index == 0 else "ANSWER_NORMALLY"),
                    "features": question_item.get("features", {}),
                    "context_signature": question_item.get("context_signature", {}),
                    "parent_context_dependency": bool(question_item.get("parent_context_dependency")),
                    "parent_intent": question_item.get("parent_intent", ""),
                    "inherits_current_request_subject": inherits_subject,
                }
                reuse_parent_branch_context = bool(
                    index > 0
                    and parent_repair_turn
                    and current_request_subject_context
                    and _text(current_request_subject_context.get("relation")).upper() == "CONTINUE"
                    and bool(task_semantics.get("active_branch_repair") or (task_semantics.get("pragmatic_features") or {}).get("active_branch_repair"))
                    and not task_semantics.get("explicit_topic_switch")
                )
                use_current_turn_context = bool(inherits_subject and current_request_subject_context)
                use_new_root_fast_path = bool(index == 0 and compound_turn_is_new)
                if reuse_parent_branch_context:
                    # Once the first correction clause selected the active branch,
                    # dependent correction clauses should share its exact anchor and
                    # evidence instead of rehydrating/reranking the whole history.
                    task_context = dict(current_request_subject_context)
                    task_search = _compact_question_search(task_context, search_query, task_semantics)
                    task_search["reused_parent_branch_context"] = True
                    task_search["reason"] = "parent_active_branch_context_reuse"
                elif use_current_turn_context or use_new_root_fast_path:
                    active_subject = _text((current_request_subject_context or {}).get("active_topic") or search_query)[:140]
                    task_context = {
                        "window_hours": 24,
                        "relation": "NEW",
                        "relation_confidence": 1.0 if use_new_root_fast_path else 0.0,
                        "active_branch_repair": False,
                        "active_branch": {},
                        "active_work_branch": {},
                        "hot_work_followup": False,
                        "hot_work_match_reason": "",
                        "user_operation": {},
                        "source_retrieval": {},
                        "previous_answer_reference": False,
                        "factual_verification_request": False,
                        "explicit_topic_switch": False,
                        "reason": "self_contained_new_topic_fast_path" if use_new_root_fast_path else "current_request_subject_inheritance",
                        "active_topic": active_subject,
                        "selected_pairs": [],
                        "candidates": [],
                        "matches": [],
                        "history_topics": [],
                        "topic_index": [],
                        "known_topic_count": 0,
                        "history_request": False,
                        "contextual_history_match": False,
                        "matched_topic_count": 0,
                        "requested_topic_count": 10,
                        "minimum_topic_count": 0,
                        "time_window": {},
                        "time_filter": {},
                        "topic_table_markdown": "",
                        "anchor": {},
                        "selected_section": {},
                        "clarification_needed": False,
                        "clarification_prompt": "",
                        "pending_clarification": {},
                        "clarification_resolution": {},
                        "search": {"relation": "NEW", "total_pairs": 0, "candidate_count": 0},
                    }
                    task_search = _compact_question_search(task_context, search_query, task_semantics)
                    if use_current_turn_context:
                        task_search["inherits_current_request_subject"] = True
                        task_search["reason"] = "current_request_subject_inheritance"
                    else:
                        task_search["reason"] = "self_contained_new_topic_fast_path"
                        current_request_subject_context = task_context
                else:
                    task_context = prepare_dialogue_context(
                        uid, search_query, query_interpretation=task_semantics, **search_kwargs
                    )
                    if index == 0 and parent_repair_turn and _text(task_context.get("relation")).upper() == "CONTINUE":
                        current_request_subject_context = task_context
                    if question_item.get("introduces_current_request_subject"):
                        # Bind dependent substeps to the first subject clause; do not
                        # search independently for anaphoric or evaluative fragments.
                        if _text(task_context.get("relation")).upper() == "NEW":
                            task_context["active_topic"] = search_query[:140]
                        current_request_subject_context = task_context
                    task_search = _compact_question_search(task_context, search_query, task_semantics)
                    if inherits_subject:
                        task_search["inherits_current_request_subject"] = True
            except Exception as exc:
                # A task-search failure must not discard the whole user request.
                # Keep order/identity and allow other tasks to proceed independently.
                task_context = {}
                task_search = {
                    "status": "search_error",
                    "relation": "NEW",
                    "confidence": 0.0,
                    "reason": type(exc).__name__,
                    "topic": "",
                    "anchor": {},
                    "selected_section": {},
                    "selected_pairs": [],
                    "clarification_needed": False,
                    "clarification_prompt": "",
                    "clarification_options": [],
                }
            question_item["dialogue_search"] = task_search
            question_item["search_query"] = search_query[:500]
            question_contexts.append(task_context)
            _apr_timing_log(
                "request_question_search", memory_started,
                user_key=_apr_diag_ref(uid),
                dialog_key=_apr_diag_ref(identity.get("dialog_id")),
                message_key=_apr_diag_ref(identity.get("message_id")),
                step_index=question_item.get("step_index"),
                query_key=_apr_diag_ref(search_query),
                relation=task_search.get("relation"),
                candidates=len(task_context.get("candidates") or []) if isinstance(task_context, dict) else 0,
                selected_pairs=len(task_context.get("selected_pairs") or []) if isinstance(task_context, dict) else 0,
                clarification_needed=bool(task_search.get("clarification_needed")),
                status=task_search.get("status"),
                context_source=(
                    "parent_active_branch" if task_search.get("reused_parent_branch_context")
                    else "current_request_subject" if question_item.get("inherits_current_request_subject")
                    else "dialogue_memory"
                ),
                semantic_intent=task_semantics.get("primary_intent"),
                search_direction=task_semantics.get("direction"),
                active_branch_repair=bool(task_semantics.get("active_branch_repair") or (task_semantics.get("pragmatic_features") or {}).get("active_branch_repair")),
                previous_answer_reference=bool(task_semantics.get("previous_answer_reference") or (task_semantics.get("pragmatic_features") or {}).get("previous_answer_reference")),
                history_request=bool(task_context.get("history_request")) if isinstance(task_context, dict) else False,
                topic_index_count=len(task_context.get("topic_index") or []) if isinstance(task_context, dict) else 0,
            )

        # Preserve the established top-level route contract by using the first
        # ordered task as the legacy turn anchor. All other per-task relation and
        # history results travel in REQUEST_SEQUENCE; no second dialogue is made.
        dialogue_context = dict(question_contexts[0] if question_contexts else {})
        # Keep the legacy first-question anchor, but do not lose history topics when
        # a history-recall item appears later in a compound request.
        history_context = next((ctx for ctx in question_contexts if isinstance(ctx, dict) and ctx.get("history_request")), None)
        if history_context:
            dialogue_context["history_available_for_request"] = True
            dialogue_context["history_request"] = True
            dialogue_context["history_topics"] = list(history_context.get("history_topics") or [])
            dialogue_context["topic_index"] = list(history_context.get("topic_index") or dialogue_context.get("topic_index") or [])
            dialogue_context["known_topic_count"] = max(
                int(dialogue_context.get("known_topic_count") or 0),
                int(history_context.get("known_topic_count") or 0),
            )
            dialogue_context["requested_topic_count"] = int(history_context.get("requested_topic_count") or 10)
            dialogue_context["minimum_topic_count"] = int(history_context.get("minimum_topic_count") or 5)
            dialogue_context["time_window"] = dict(history_context.get("time_window") or {})
            dialogue_context["time_filter"] = dict(history_context.get("time_filter") or {})
            dialogue_context["topic_table_markdown"] = _text(history_context.get("topic_table_markdown") or dialogue_context.get("topic_table_markdown"))
        if not dialogue_context:
            # Do not fall back to a whole-message retrieval if one per-question
            # search failed. That could accidentally replace the first task's
            # relation with a mixed CONTINUE/NEW decision. Keep the canonical
            # request alive with an empty, correctly-shaped memory context.
            dialogue_context = {
                "window_hours": 24,
                "relation": "NEW",
                "relation_confidence": 0.0,
                "reason": "per_question_search_unavailable",
                "active_topic": _text(question_sequence[0].get("request")) if question_sequence else current_text,
                "selected_pairs": [],
                "candidates": [],
                "history_topics": [],
                "topic_index": [],
                "known_topic_count": 0,
                "history_request": False,
                "requested_topic_count": 10,
                "minimum_topic_count": 5,
                "time_window": {},
                "time_filter": {},
                "topic_table_markdown": "",
                "anchor": {},
                "selected_section": {},
                "clarification_needed": False,
                "clarification_prompt": "",
                "pending_clarification": {},
                "clarification_resolution": {},
                "search": {"relation": "NEW", "total_pairs": 0, "candidate_count": 0},
            }
        # A local stop for one ambiguous subtask would hide every other task. In a
        # compound request, pass the ambiguity within its task entry so Provider can
        # answer the clear tasks and ask only about the unresolved part.
        dialogue_context["clarification_needed"] = False
        dialogue_context["clarification_prompt"] = ""
        dialogue_context["pending_clarification"] = {}
        dialogue_context["request_sequence_count"] = len(question_sequence)

    search_result = dialogue_context.get("search") if isinstance(dialogue_context.get("search"), dict) else {}
    anchor = dialogue_context.get("anchor") if isinstance(dialogue_context.get("anchor"), dict) else {}
    selected_pairs = dialogue_context.get("selected_pairs") or []
    _apr_timing_log(
        "dialogue_context_ready", memory_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")),
        message_key=_apr_diag_ref(identity.get("message_id")),
        relation=dialogue_context.get("relation"), reason=dialogue_context.get("reason"),
        question_count=len(question_sequence),
        total_pairs=search_result.get("total_pairs"), candidates=search_result.get("candidate_count", len(dialogue_context.get("candidates") or [])),
        selected_pairs=len(selected_pairs), selected_message_keys=[_apr_diag_ref(x.get("message_id")) for x in selected_pairs if isinstance(x, dict) and x.get("message_id")],
        anchor_message_key=_apr_diag_ref(anchor.get("message_id")), topic_index_count=len(dialogue_context.get("topic_index") or []),
    )

    # A follow-up may refer to an image/file from earlier in this conversation.
    # Rehydrate only the assets attached to State Manager's selected anchor/pairs;
    # do not mix older files into NEW requests or when a fresh attachment exists.
    restore_started = time.perf_counter()
    if bool(dialogue_context.get("clarification_needed")):
        # Clarification must be quick and must not restore/load unrelated assets.
        restored_assets = []
    else:
        asset_context = dialogue_context
        if len(question_sequence) > 1:
            for question_item, task_context in zip(question_sequence, question_contexts):
                if (
                    isinstance(task_context, dict)
                    and _text(task_context.get("relation")).upper() == "CONTINUE"
                    and _explicit_prior_asset_reference(question_item.get("request"))
                ):
                    asset_context = task_context
                    break
        visual_context, attachments, file_inputs, file_contents, restored_assets = _restore_selected_assets(
            uid, identity, asset_context, visual_context, attachments, file_inputs, file_contents,
            current_request=current_text,
        )
    _apr_timing_log(
        "selected_asset_restore", restore_started, user_key=_apr_diag_ref(uid),
        restored_assets=len(restored_assets or []), visual_items=len(visual_context or []),
        file_inputs=len(file_inputs or []), file_contents=len(file_contents or []),
    )

    interpretation_started = time.perf_counter()
    interpretation_memory = dict(dialogue_context)
    # The inline data URI is private to the renderer/reuse branch and must never
    # enter the model prompt, structured card, or response metadata.
    interpretation_memory["restored_assets"] = [
        {key: value for key, value in item.items() if not str(key).startswith("_")}
        for item in restored_assets if isinstance(item, dict)
    ]
    interpretation = build_interpretation(
        current_request=current_text,
        original_request=original,
        display_language=display_language,
        memory=interpretation_memory,
        attachments=attachments or [],
        visual_context=visual_context or [],
        identity=identity,
        semantic_interpretation=semantic_interpretation,
    )
    # Bind the user's preferred display name to the already-authenticated ID.
    # This is prompt metadata only: it does not alter stored message text,
    # dialogue identity, history, or the canonical chat route.
    user_display_name = _text(kwargs.get("user_display_name"))[:80]
    if user_display_name:
        identity_context = interpretation.setdefault("identity", {})
        if isinstance(identity_context, dict):
            identity_context["display_name"] = user_display_name

    request_structure = interpretation.setdefault("request_structure", {})
    request_structure["question_sequence"] = question_sequence
    request_structure["answer_sequence_in_order"] = True
    request_structure["question_search_engine"] = "state_manager_per_question_semantic_v3_active_repair"
    request_structure["semantic_interpretation"] = semantic_interpretation
    request_structure["semantic_interpretation_version"] = "april_request_semantics_v4_active_branch_repair"
    request_structure["question_search_count"] = len(question_sequence)
    request_structure["question_relations"] = [
        {
            "step_index": item.get("step_index"),
            "relation": (item.get("dialogue_search") or {}).get("relation", "NEW"),
            "topic": (item.get("dialogue_search") or {}).get("topic", ""),
            "confidence": (item.get("dialogue_search") or {}).get("confidence", 0.0),
        }
        for item in question_sequence
    ]
    _apr_timing_log(
        "interpretation_ready", interpretation_started,
        relation=(interpretation.get("dialogue") or {}).get("relation"),
        task=(interpretation.get("intent") or {}).get("task"),
        requested_outputs=(interpretation.get("intent") or {}).get("requested_outputs"),
        question_sequence_count=len(((interpretation.get("request_structure") or {}).get("question_sequence") or [])),
        semantic_intent=semantic_interpretation.get("primary_intent"),
        search_direction=semantic_interpretation.get("direction"),
        active_branch_repair=bool(semantic_interpretation.get("active_branch_repair")),
        previous_answer_reference=bool(semantic_interpretation.get("previous_answer_reference")),
        factual_verification_request=bool(semantic_interpretation.get("factual_verification_request")),
        history_request=bool(semantic_interpretation.get("history_request")),
    )

    selected_rooms = _select_rooms(interpretation)
    render_plan = _renderer_plan(interpretation, selected_rooms)

    identity["flow_id"] = _text(identity["flow_id"])
    request_build_started = time.perf_counter()
    request = MachineRequest(
        request_id=identity["flow_id"] or str(uuid.uuid4()),
        goal="answer_user_request",
        intent={
            **interpretation,
            "interpretation_id": identity["interpretation_id"],
        },
        conversation={
            "conversation_id": identity["conversation_id"],
            "dialog_id": identity["dialog_id"],
            "message_id": identity["message_id"],
            "current_request": original,
            "resolved_request": current_text,
            "display_language": display_language,
        },
        memory={
            "window_hours": int(dialogue_context.get("window_hours") or 24),
            "relation": dialogue_context["relation"],
            "relation_confidence": dialogue_context["relation_confidence"],
            "active_branch": dict(dialogue_context.get("active_branch") or {}),
            "active_work_branch": (
                dict(dialogue_context.get("active_work_branch") or {})
                if dialogue_context.get("hot_work_followup") else {}
            ),
            "hot_work_followup": bool(dialogue_context.get("hot_work_followup")),
            "hot_work_match_reason": _text(dialogue_context.get("hot_work_match_reason"))[:80],
            "user_operation": dict(dialogue_context.get("user_operation") or {}),
            "source_retrieval": dict(dialogue_context.get("source_retrieval") or {}),
            "selected_pairs": (
                dialogue_context.get("selected_pairs") or []
                if (dialogue_context.get("relation") == "CONTINUE" or dialogue_context.get("history_request") or dialogue_context.get("contextual_history_match"))
                else []
            ),
            # Search candidates/full trace stay internal. Pass only the ranked
            # relevant topic index on a semantic hit, or the broader index for explicit history overview.
            "selected_section": (
                dialogue_context.get("selected_section") or {}
                if (dialogue_context.get("relation") == "CONTINUE" or dialogue_context.get("history_request") or dialogue_context.get("contextual_history_match"))
                else {}
            ),
            "clarification_needed": bool(dialogue_context.get("clarification_needed")),
            "pending_clarification": dialogue_context.get("pending_clarification") or {},
            "clarification_resolution": dialogue_context.get("clarification_resolution") or {},
            "history_topics": (dialogue_context.get("history_topics") or []) if dialogue_context.get("history_request") else [],
            "topic_index": (dialogue_context.get("topic_index") or []) if (dialogue_context.get("history_request") or dialogue_context.get("contextual_history_match") or dialogue_context.get("relation") == "CONTINUE") else [],
            "known_topic_count": int(dialogue_context.get("known_topic_count") or 0) if (dialogue_context.get("history_request") or dialogue_context.get("contextual_history_match")) else 0,
            "contextual_history_match": bool(dialogue_context.get("contextual_history_match")),
            "history_request": bool(dialogue_context.get("history_request")),
            "requested_topic_count": int(dialogue_context.get("requested_topic_count") or 10) if dialogue_context.get("history_request") else 0,
            "minimum_topic_count": int(dialogue_context.get("minimum_topic_count") or 5) if dialogue_context.get("history_request") else 0,
            "time_window": dict(dialogue_context.get("time_window") or {}),
            "time_filter": dict(dialogue_context.get("time_filter") or {}),
            "topic_table_markdown": (dialogue_context.get("topic_table_markdown") or "") if dialogue_context.get("history_request") else "",
            "anchor": (
                dialogue_context.get("anchor") or {}
                if (dialogue_context.get("relation") == "CONTINUE" or dialogue_context.get("history_request"))
                else {}
            ),
            "restored_assets": restored_assets,
        },
        visual_context={
            "items": visual_context or [],
            "has_input_images": bool(visual_context),
        },
        available_tools=[r.room_id for r in list_registered_rooms()],
        requested_outputs=list(
            (interpretation.get("intent") or {}).get("requested_outputs") or ["text"]
        ),
        required_competencies=[
            cap
            for room in selected_rooms
            for cap in room.get("capabilities", [])
        ],
        required_artifacts=list(
            (interpretation.get("intent") or {}).get("requested_outputs") or ["text"]
        ),
        routing={
            "single_route": True,
            "canonical_route": CANONICAL_ROUTE,
            "processor_version": PROCESSOR_VERSION,
            "flow_id": identity["flow_id"],
            "dialog_id": identity["dialog_id"],
            "conversation_id": identity["conversation_id"],
            "message_id": identity["message_id"],
            "interpretation_id": identity["interpretation_id"],
            "selected_rooms": selected_rooms,
            "render_plan": render_plan,
            "provider_context_plan": {
                "relation": dialogue_context["relation"],
                "current_request": current_text,
                "active_branch": dict(dialogue_context.get("active_branch") or {}),
                "active_work_branch": (
                    dict(dialogue_context.get("active_work_branch") or {})
                    if dialogue_context.get("hot_work_followup") else {}
                ),
                "hot_work_followup": bool(dialogue_context.get("hot_work_followup")),
                "hot_work_match_reason": _text(dialogue_context.get("hot_work_match_reason"))[:80],
                "user_operation": dict(dialogue_context.get("user_operation") or {}),
                "source_retrieval": dict(dialogue_context.get("source_retrieval") or {}),
                "selected_dialogue_chain": (
                    dialogue_context.get("selected_pairs") or []
                    if (dialogue_context.get("relation") == "CONTINUE" or dialogue_context.get("history_request"))
                    else []
                ),
                "selected_section": (
                    dialogue_context.get("selected_section") or {}
                    if (dialogue_context.get("relation") == "CONTINUE" or dialogue_context.get("history_request"))
                    else {}
                ),
                "clarification_needed": bool(dialogue_context.get("clarification_needed")),
                "pending_clarification": dialogue_context.get("pending_clarification") or {},
                "clarification_resolution": dialogue_context.get("clarification_resolution") or {},
                "history_topics": (dialogue_context.get("history_topics") or []) if dialogue_context.get("history_request") else [],
                "topic_index": (dialogue_context.get("topic_index") or []) if dialogue_context.get("history_request") else [],
                "known_topic_count": int(dialogue_context.get("known_topic_count") or 0) if dialogue_context.get("history_request") else 0,
                "history_request": bool(dialogue_context.get("history_request")),
                "requested_topic_count": int(dialogue_context.get("requested_topic_count") or 10) if dialogue_context.get("history_request") else 0,
                "minimum_topic_count": int(dialogue_context.get("minimum_topic_count") or 5) if dialogue_context.get("history_request") else 0,
                "time_window": dict(dialogue_context.get("time_window") or {}),
                "time_filter": dict(dialogue_context.get("time_filter") or {}),
                "topic_table_markdown": (dialogue_context.get("topic_table_markdown") or "") if dialogue_context.get("history_request") else "",
                "anchor": (
                    dialogue_context.get("anchor") or {}
                    if (dialogue_context.get("relation") == "CONTINUE" or dialogue_context.get("history_request"))
                    else {}
                ),
                "restored_assets": restored_assets,
                # Always carry the literal current request in the structured chain.
                # This field is active as a topic switch only for NEW dialogue.
                "new_dialogue_request": original or current_text,
                "new_dialogue_active": (
                    dialogue_context["relation"] == "NEW"
                    and not dialogue_context.get("history_request")
                ),
                "context": {
                    "active_topic": dialogue_context["active_topic"],
                    "reason": dialogue_context["reason"],
                    "confidence": dialogue_context["relation_confidence"],
                    "anchor_topic": (dialogue_context.get("anchor") or {}).get("topic", ""),
                    "active_branch": dict(dialogue_context.get("active_branch") or {}),
                    "active_work_branch": (
                        dict(dialogue_context.get("active_work_branch") or {})
                        if dialogue_context.get("hot_work_followup") else {}
                    ),
                    "hot_work_followup": bool(dialogue_context.get("hot_work_followup")),
                    "user_operation": dict(dialogue_context.get("user_operation") or {}),
                    "source_retrieval": dict(dialogue_context.get("source_retrieval") or {}),
                },
                "mcdowell": {
                    "always": True,
                    "required": True,
                    "role": "presentation_and_render_layout",
                },
                "katex": {
                    "required_for_math": True,
                    "renderer": "FormulaRenderer",
                },
                "provider_policy": {
                    "output_limit": "model_native_no_application_cap",
                    "provider_calls_per_turn": 0 if dialogue_context.get("clarification_needed") else 1,
                    "local_clarification_allowed": True,
                    "retry_count": 0,
                    "question_sequence_required": True,
                },
            },
        },
        constraints={
            "display_language": display_language,
            "provider_output_language": display_language,
            "internal_language": "en",
            "single_route": True,
            "no_legacy_route": True,
            "structured_response": True,
            "context_always_present": True,
            "mcdowell_always_present": True,
            "katex_required_for_math": True,
            "provider_calls_per_turn": 0 if dialogue_context.get("clarification_needed") else 1,
            "provider_retry_count": 0,
            "local_clarification_allowed": True,
            "input_modalities": (interpretation.get("input") or {}).get("modalities", []),
        },
    )
    _apr_timing_log("machine_request_build", request_build_started,
        relation=dialogue_context.get("relation"), selected_pairs=len(dialogue_context.get("selected_pairs") or []),
        candidates=len(dialogue_context.get("candidates") or []), input_chars=len(current_text),
        request_id_key=_apr_diag_ref(getattr(request, "request_id", "")))
    request.fiber.identity.user_id = uid
    # Search index is deliberately separate from binary storage. It contains a
    # bounded source preview, exact filenames/roles and the message ID used to
    # restore original bytes. Historical binary sidecars are no longer persisted.
    request_metadata_started = time.perf_counter()
    attachment_index: list[dict[str, Any]] = []
    for item in (attachments or []):
        if not isinstance(item, dict):
            continue
        attachment_index.append({
            "filename": _text(item.get("filename"))[:200],
            "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
            "kind": _text(item.get("kind") or "file"),
            "mime_type": _text(item.get("mime_type") or item.get("content_type"))[:100],
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "source_type": _text(item.get("source_type"))[:100],
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            "recalled_from_memory": bool(item.get("recalled_from_memory")),
            "requires_original_analysis": bool(item.get("requires_original_analysis")),
            "source_bytes_attached": (
                bool(item.get("requires_original_analysis"))
                if item.get("recalled_from_memory")
                else (_text(item.get("kind")).lower() in {"image", "text_file"} or bool(item.get("provider_readable", True)))
            ),
        })
    for item in (file_contents or []):
        if not isinstance(item, dict):
            continue
        attachment_index.append({
            "filename": _text(item.get("filename") or "file")[:200],
            "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
            "kind": "text_file",
            "mime_type": _text(item.get("mime_type") or "text/plain")[:100],
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "content_preview": _text(item.get("content"))[:4500],
            "reader_truncated": bool(item.get("reader_truncated", False)),
            "source_chars": int(item.get("source_chars") or len(_text(item.get("content")))),
            "summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            "recalled_from_memory": bool(item.get("recalled_from_memory")),
            "requires_original_analysis": bool(item.get("requires_original_analysis", True)),
            "source_bytes_attached": True,
        })
    for item in (visual_context or []):
        if not isinstance(item, dict):
            continue
        attachment_index.append({
            "filename": _text(item.get("filename") or "image")[:200],
            "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
            "kind": "image",
            "mime_type": _text(item.get("mime_type") or "image/*")[:100],
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "source_type": _text(item.get("source_type") or "image")[:100],
            "analysis_summary": _text(item.get("analysis_summary"))[:1200],
            "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            "recalled_from_memory": bool(item.get("recalled_from_memory")),
            "requires_original_analysis": bool(item.get("requires_original_analysis")),
            "source_bytes_attached": not bool(item.get("recalled_from_memory")) or bool(item.get("requires_original_analysis")),
        })
    def _attachment_index_order(item: dict[str, Any]) -> int:
        try:
            return int(item.get("sequence_index", 9999))
        except (TypeError, ValueError, OverflowError):
            return 9999

    attachment_index.sort(key=_attachment_index_order)
    unique_index: list[dict[str, Any]] = []
    index_by_asset_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for item in attachment_index:
        asset_key = (
            _text(item.get("asset_message_id")),
            _text(item.get("filename")),
            _text(item.get("asset_role")),
            _text(item.get("kind")),
            str(_attachment_index_order(item)),
        )
        existing = index_by_asset_key.get(asset_key)
        if existing is None:
            existing = dict(item)
            index_by_asset_key[asset_key] = existing
            unique_index.append(existing)
        else:
            # Merge rather than discard the richer text-file entry: attachment
            # metadata is appended before the decoded text preview by design.
            for key, value in item.items():
                if value not in (None, "", [], {}):
                    existing[key] = value
    attachment_index = unique_index[:12]
    attachment_refs = [
        {key: item.get(key) for key in ("filename", "kind", "mime_type", "asset_role", "asset_message_id", "source_type", "size_bytes", "sequence_index") if item.get(key) is not None}
        for item in attachment_index
    ]

    request.metadata = {
        "identity": identity,
        "interpretation": interpretation,
        "attachments": attachments or [],
        "attachment_index": attachment_index,
        # Raw file_data is request-scoped only. It is consumed by Provider and
        # is deliberately excluded from structured_request/DB persistence below.
        "file_inputs": [
            {
                "filename": _text(item.get("filename") or "file"),
                "mime_type": _text(item.get("mime_type") or "application/octet-stream"),
                "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
                "size_bytes": int(item.get("size_bytes") or 0),
                "file_data": _text(item.get("file_data")),
                "asset_role": _text(item.get("asset_role") or "user_input"),
                "asset_message_id": _text(item.get("asset_message_id")),
                "analysis_summary": _text(item.get("analysis_summary"))[:1200],
                "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            }
            for item in file_inputs
        ],
        "file_contents": [
            {
                "filename": _text(item.get("filename") or "file"),
                "mime_type": _text(item.get("mime_type") or "text/plain"),
                "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
                "size_bytes": int(item.get("size_bytes") or 0),
                "content": _text(item.get("content")),
                "reader_truncated": bool(item.get("reader_truncated", False)),
                "source_chars": int(item.get("source_chars") or len(_text(item.get("content")))),
                "asset_role": _text(item.get("asset_role") or "user_input"),
                "asset_message_id": _text(item.get("asset_message_id")),
                "analysis_summary": _text(item.get("analysis_summary"))[:1200],
                "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else [],
            }
            for item in file_contents
        ],
        "translation": translation or {},
    }
    _apr_timing_log("request_metadata_ready", request_metadata_started,
        attachment_index_count=len(attachment_index), visual_items=len(visual_context or []),
        file_inputs_count=len(file_inputs or []), file_contents_count=len(file_contents or []),
        file_content_chars=sum(len(_text(x.get("content"))) for x in (file_contents or []) if isinstance(x, dict)))

    provider_started = time.perf_counter()
    time_filter = dialogue_context.get("time_filter") if isinstance(dialogue_context.get("time_filter"), dict) else {}
    time_window = dialogue_context.get("time_window") if isinstance(dialogue_context.get("time_window"), dict) else {}
    temporal_history_lookup = bool(
        dialogue_context.get("history_request")
        or semantic_interpretation.get("history_request")
        or semantic_interpretation.get("history_inventory_request")
    )
    temporal_gap = bool(
        temporal_history_lookup
        and time_filter.get("applied")
        and not time_filter.get("empty")
        and int(time_filter.get("matched_rows") or 0) == 0
    )
    temporal_empty_window = bool(temporal_history_lookup and time_filter.get("applied") and time_filter.get("empty"))
    temporal_outside_retention = bool(temporal_empty_window and time_filter.get("empty_reason") == "outside_retention")
    temporal_future_period = bool(temporal_empty_window and time_filter.get("empty_reason") == "future_period")
    if bool(dialogue_context.get("clarification_needed")):
        # This is a deterministic UI-facing clarification, not a provider fallback.
        # The original request and options are persisted in dialogue_memory_record,
        # so the user's next reply resolves this exact question without losing intent.
        clarification_answer = _text(dialogue_context.get("clarification_prompt"))
        pending = dict(dialogue_context.get("pending_clarification") or {})
        if not clarification_answer:
            clarification_answer = "Уточните, пожалуйста, какой именно раздел продолжить. Исходный запрос сохранён."
        topic_name = _text(pending.get("active_topic") or dialogue_context.get("active_topic")) or "Тема диалога"
        memory_record = {
            "topic": topic_name[:140],
            "summary": "Ожидается уточнение выбранного раздела; исходный запрос сохранён без потери намерения пользователя.",
            "sections": [],
            "entities": [],
            "pending_clarification": pending,
        }
        provider_packet = {"machine_response": {
            "answer": clarification_answer,
            "content": clarification_answer,
            "summary": "Уточнение раздела для продолжения диалога.",
            "render_blocks": [{
                "type": "text",
                "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                "content": clarification_answer,
            }],
            "artifacts": [],
            "metadata": {
                "identity": identity,
                "dialogue_memory_record": memory_record,
                "local_clarification": True,
                "provider_calls": 0,
            },
            "internal_answer_en": clarification_answer,
        }}
        provider_ms = 0.0
        _apr_timing_log("local_clarification_ready", provider_started,
            options=len(pending.get("options") or []), active_topic=topic_name,
            original_request_chars=len(_text(pending.get("original_request"))))
    elif temporal_gap or temporal_empty_window:
        # Window labels originate from the parsed Kyiv-local interval. Show the
        # exact empty interval first; adjacent records are explicitly marked as outside.
        raw_label = _text(time_filter.get("label") or time_window.get("label"))
        if " — " in raw_label:
            left, right = raw_label.split(" — ", 1)
            def _pretty_clock(value: str) -> str:
                try:
                    from datetime import datetime
                    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M").strftime("%d.%m.%Y %H:%M")
                except (TypeError, ValueError):
                    return value.strip()
            raw_label = f"{_pretty_clock(left)} — {_pretty_clock(right)}"
        if temporal_outside_retention:
            fallback_answer = (
                f"Указанный период ({raw_label or 'запрошенное время'}) не пересекается с доступным "
                "24-часовым окном Premium. Поэтому я не могу подтвердить, какие диалоги были именно в это время."
            )
            memory_topic = "Поиск истории вне 24-часового окна"
            memory_summary = "Запрошенный период не пересекается с доступным 24-часовым окном Premium."
        elif temporal_future_period:
            fallback_answer = (
                f"Период ({raw_label or 'указанное время'}) ещё не наступил по Киеву. "
                "В сохранённой истории пока нет диалогов за это время."
            )
            memory_topic = "Поиск истории за будущий период"
            memory_summary = "Запрошенный период ещё не наступил; исторических записей за него пока быть не может."
        elif temporal_empty_window:
            fallback_answer = (
                f"Период ({raw_label or 'указанное время'}) не пересекается с прошедшими записями "
                "в доступном 24-часовом окне Premium."
            )
            memory_topic = "Поиск истории по времени"
            memory_summary = fallback_answer
        else:
            fallback_answer = (
                f"Проверила сохранённую историю за {raw_label or 'указанный период'} по Киеву: "
                "внутри этого интервала записей не нашлось."
            )
            neighbors = time_filter.get("neighbors") if isinstance(time_filter.get("neighbors"), dict) else {}
            neighbor_lines = []
            for side, title in (("before", "Ближайшая запись до интервала"), ("after", "Ближайшая запись после интервала")):
                item = neighbors.get(side) if isinstance(neighbors.get(side), dict) else None
                if not item:
                    continue
                topic = _text(item.get("topic")) or "Тема без названия"
                at_label = _text(item.get("time_label")) or "время неизвестно"
                summary = _text(item.get("summary")) or _text(item.get("user"))
                line = f"**{title} — {at_label}:** {topic}."
                if summary and summary.casefold() != topic.casefold():
                    line += f" {summary[:240]}"
                neighbor_lines.append(line)
            if neighbor_lines:
                fallback_answer += "\n\nРядом по времени сохранились такие записи:\n\n" + "\n\n".join(neighbor_lines)
                fallback_answer += "\n\nЭто записи рядом с указанным временем, а не диалоги внутри самого интервала."
            else:
                fallback_answer += " В доступной 24-часовой истории нет и соседних записей до или после него."
            memory_topic = "Поиск истории по времени"
            memory_summary = fallback_answer[:500]

        # Show nearby retained evidence for every empty temporal window, including
        # old/future ranges. These are never presented as matches within the range.
        neighbors = time_filter.get("neighbors") if isinstance(time_filter.get("neighbors"), dict) else {}
        neighbor_lines = []
        if temporal_outside_retention:
            neighbor_titles = {
                "before": "Ближайшая доступная запись до указанного периода (в пределах последних 24 часов)",
                "after": "Ближайшая доступная запись после указанного периода (в пределах последних 24 часов)",
            }
        elif temporal_future_period:
            neighbor_titles = {
                "before": "Последняя доступная запись перед будущим периодом",
                "after": "Ближайшая доступная запись после будущего периода",
            }
        else:
            neighbor_titles = {
                "before": "Ближайшая запись до интервала",
                "after": "Ближайшая запись после интервала",
            }
        for side in ("before", "after"):
            item = neighbors.get(side) if isinstance(neighbors.get(side), dict) else None
            if not item:
                continue
            topic = _text(item.get("topic")) or "Тема без названия"
            at_label = _text(item.get("time_label")) or "время неизвестно"
            summary = _text(item.get("summary")) or _text(item.get("user"))
            line = f"**{neighbor_titles[side]} — {at_label}:** {topic}."
            if summary and summary.casefold() != topic.casefold():
                line += f" {summary[:240]}"
            neighbor_lines.append(line)
        if neighbor_lines:
            if temporal_outside_retention or temporal_future_period:
                fallback_answer += "\n\nБлижайшие записи, которые доступны в сохранённой истории:\n\n" + "\n\n".join(neighbor_lines)
                fallback_answer += "\n\nЭти записи приведены только как ориентир и не подтверждают наличие диалога внутри указанного периода."
            elif temporal_empty_window:
                fallback_answer += "\n\nБлижайшие доступные записи:\n\n" + "\n\n".join(neighbor_lines)
                fallback_answer += "\n\nЭто записи за пределами указанного интервала, а не диалоги внутри него."
        elif temporal_empty_window:
            fallback_answer += "\n\nВ доступной истории Premium за последние 24 часа нет соседних записей, которые можно было бы показать для сравнения."

        provider_packet = {"machine_response": {
            "answer": fallback_answer,
            "content": fallback_answer,
            "summary": fallback_answer[:180],
            "render_blocks": [{
                "type": "text",
                "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                "content": fallback_answer,
            }],
            "artifacts": [],
            "metadata": {
                "identity": identity,
                "dialogue_memory_record": {
                    "topic": memory_topic,
                    "summary": memory_summary,
                    "sections": [],
                    "entities": [],
                },
                "local_temporal_history_fallback": True,
                "provider_calls": 0,
            },
            "internal_answer_en": fallback_answer,
        }}
        provider_ms = 0.0
        _apr_timing_log(
            "temporal_gap_response_ready", provider_started,
            matched_rows=int(time_filter.get("matched_rows") or 0),
            neighbor_sides=sum(1 for side in (time_filter.get("neighbors") or {}).values() if isinstance(side, dict)),
            outside_retention=temporal_outside_retention,
            answer_chars=len(fallback_answer), provider_calls=0,
        )
    else:
        try:
            provider_packet = await generate_text(request)
        except Exception as exc:
            # A history search already has authenticated, database-backed evidence.
            # If only the Provider/compaction layer fails, show that evidence locally
            # rather than returning HTTP 500 and an empty chat bubble. Ordinary NEW
            # questions still raise normally; this is not a generic model fallback.
            history_fallback_allowed = bool(
                dialogue_context.get("history_request")
                or dialogue_context.get("contextual_history_match")
            )
            if not history_fallback_allowed:
                raise

            found_topics = [dict(item) for item in (
                dialogue_context.get("history_topics") or dialogue_context.get("topic_index") or []
            ) if isinstance(item, dict)]
            found_pairs = [dict(item) for item in (dialogue_context.get("selected_pairs") or []) if isinstance(item, dict)]
            topic_count = int(dialogue_context.get("known_topic_count") or len(found_topics) or 0)
            explicit_window = dialogue_context.get("time_window") or {}
            time_filter = dialogue_context.get("time_filter") or {}
            overview_request = str(semantic_interpretation.get("primary_intent") or "").upper() == "HISTORY_SUMMARY"
            overview_request = overview_request or bool(semantic_interpretation.get("history_inventory_request"))

            if not found_topics and not found_pairs:
                if topic_count > 0:
                    fallback_answer = (
                        f"В сохранённой истории не нашёл однозначного совпадения по запросу «{current_text[:160]}». "
                        "Не буду подменять тему случайными записями. Уточни, пожалуйста, одну-две детали темы."
                    )
                    memory_topic = "Поиск темы в истории"
                    memory_summary = "В сохранённой истории есть записи, но поиск не подтвердил тематическое совпадение."
                elif bool(time_filter.get("applied")) or bool(explicit_window.get("has_constraint")):
                    fallback_answer = "В сохранённой истории за указанный период записей не найдено."
                    memory_topic = "Проверка истории по времени"
                    memory_summary = "Поиск по сохранённой истории за указанный период выполнен; записей не найдено."
                else:
                    fallback_answer = "В сохранённой истории за доступный период записей нет."
                    memory_topic = "Проверка истории диалога"
                    memory_summary = "Поиск по сохранённой истории выполнен; записей не найдено."
            elif overview_request:
                visible_topics = found_topics[:max(1, min(10, int(dialogue_context.get("requested_topic_count") or 10)))]
                lines = [f"В доступной истории найдено тем: {len(visible_topics)}."]
                for index, item in enumerate(visible_topics, 1):
                    name = str(item.get("topic") or item.get("last_question") or "Тема без названия").strip()
                    summary = str(item.get("summary") or "").strip()
                    lines.append(f"{index}. **{name}**" + (f" — {summary}" if summary else ""))
                if topic_count > len(visible_topics):
                    lines.append(f"Показано {len(visible_topics)} наиболее релевантных/свежих тем из {topic_count} найденных.")
                fallback_answer = "\n\n".join(lines)
                memory_topic = "Обзор сохранённой истории"
                memory_summary = f"Локально сформирован обзор {len(visible_topics)} тем из сохранённой истории."
            else:
                anchor_topic = ""
                anchor_summary = ""
                if found_topics:
                    anchor_topic = str(found_topics[0].get("topic") or found_topics[0].get("last_question") or "").strip()
                    anchor_summary = str(found_topics[0].get("summary") or "").strip()
                if found_pairs:
                    pair = found_pairs[0]
                    anchor_topic = str(pair.get("topic") or anchor_topic or "Найденная тема").strip()
                    pair_summary = str(pair.get("memory_summary") or pair.get("summary") or "").strip()
                    anchor_summary = anchor_summary or pair_summary
                    user_line = str(pair.get("user") or pair.get("user_text") or "").strip()
                    april_line = str(pair.get("april") or pair.get("april_text") or "").strip()
                    body_parts = [f"Нашёл запись в истории по теме **{anchor_topic}**."]
                    if user_line:
                        body_parts.append(f"**Твой запрос:** {user_line}")
                    if april_line:
                        body_parts.append(f"**Ответ April:** {april_line}")
                    elif anchor_summary:
                        body_parts.append(anchor_summary)
                    fallback_answer = "\n\n".join(body_parts)
                else:
                    fallback_answer = f"Нашёл связанную тему в истории: **{anchor_topic or 'тема без названия'}**."
                    if anchor_summary:
                        fallback_answer += f"\n\n{anchor_summary}"
                memory_topic = (anchor_topic or "Найденная запись истории")[:180]
                memory_summary = (anchor_summary or fallback_answer)[:500]

            provider_packet = {"machine_response": {
                "answer": fallback_answer,
                "content": fallback_answer,
                "summary": fallback_answer[:180],
                "render_blocks": [{
                    "type": "text",
                    "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                    "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                    "content": fallback_answer,
                }],
                "artifacts": [],
                "metadata": {
                    "identity": identity,
                    "dialogue_memory_record": {
                        "topic": memory_topic,
                        "summary": memory_summary,
                        "sections": [],
                        "entities": [],
                    },
                    "local_history_fallback": True,
                    "provider_calls": 0,
                    "fallback_reason": type(exc).__name__,
                },
                "internal_answer_en": fallback_answer,
            }}
            _apr_timing_log(
                "history_fallback_ready", provider_started,
                fallback_reason=type(exc).__name__, history_topics=len(found_topics),
                selected_pairs=len(found_pairs), answer_chars=len(fallback_answer),
            )
        provider_ms = round((time.perf_counter() - provider_started) * 1000, 1)
    provider_machine = provider_packet.get("machine_response") if isinstance(provider_packet, dict) else {}
    provider_machine = provider_machine if isinstance(provider_machine, dict) else {}
    provider_meta_for_log = provider_machine.get("metadata") if isinstance(provider_machine.get("metadata"), dict) else {}
    _apr_timing_log("provider_wait_complete", provider_started,
        request_id_key=_apr_diag_ref(getattr(request, "request_id", "")), provider_ms=provider_ms,
        answer_chars=len(_text(provider_machine.get("answer") or provider_machine.get("content"))),
        render_blocks=len(provider_machine.get("render_blocks") or []), artifacts=len(provider_machine.get("artifacts") or []),
        input_tokens=(provider_meta_for_log.get("usage") or {}).get("input_tokens"),
        output_tokens=(provider_meta_for_log.get("usage") or {}).get("output_tokens"),
        provider_fallback=bool(provider_meta_for_log.get("provider_fallback")),
        provider_retries=provider_meta_for_log.get("provider_retries", 0),
        provider_output_limit=provider_meta_for_log.get("provider_output_limit", 12000),
        local_clarification=bool(provider_meta_for_log.get("local_clarification")))

    raw = provider_packet.get("machine_response") if isinstance(provider_packet, dict) else None
    if not isinstance(raw, dict):
        raise RuntimeError("PROVIDER_CONTRACT_MISSING")

    provider_metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    asset_summary_started = time.perf_counter()
    _persist_asset_analysis_summaries(
        uid,
        identity,
        attachment_index,
        provider_metadata.get("dialogue_memory_record"),
    )
    _apr_timing_log("asset_summary_persist", asset_summary_started, attachment_index_count=len(attachment_index))

    response_package_started = time.perf_counter()
    answer = _text(raw.get("answer") or raw.get("content"))
    if not answer:
        raise RuntimeError("CANONICAL_ANSWER_MISSING")

    image_intent_for_answer = interpretation.get("intent") if isinstance(interpretation.get("intent"), dict) else {}
    image_task = _text(image_intent_for_answer.get("task"))
    if image_task == "request_source_image":
        answer = _image_edit_message(interpretation, "missing_source")
        raw["answer"] = answer
        raw["content"] = answer
        raw["summary"] = "Редактирование ожидает исходное изображение."
        raw["render_blocks"] = [{
            "type": "text",
            "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
            "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
            "content": answer,
        }]
        raw["artifacts"] = []
    elif image_task == "edit_image":
        # The model can incorrectly claim editing is unavailable. The executor owns
        # the actual edit operation, so show truthful processing text until it returns.
        answer = _image_edit_message(interpretation, "processing")
        raw["answer"] = answer
        raw["content"] = answer
        raw["summary"] = "Редактирование исходного изображения."
        raw["render_blocks"] = [{
            "type": "text",
            "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
            "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
            "content": answer,
        }]
        raw["artifacts"] = []

    # The existing TextModule participates only as the canonical response
    # packaging/sanitization layer; it never creates a second Provider call.
    raw_blocks = [dict(x) for x in (raw.get("render_blocks") or []) if isinstance(x, dict)]
    raw_artifacts = [dict(x) for x in (raw.get("artifacts") or []) if isinstance(x, dict)]
    wants_image = bool((interpretation.get("intent") or {}).get("wants_image"))
    if not wants_image:
        raw_blocks = [
            block for block in raw_blocks
            if str(block.get("type") or "").lower() not in {"image", "gallery"}
        ]
        raw_artifacts = [
            artifact for artifact in raw_artifacts
            if str(artifact.get("type") or artifact.get("artifact_type") or "").lower() not in {"image", "generated_image"}
        ]


    packaged = package_provider_response(
        answer=answer,
        content=_text(raw.get("content") or answer),
        summary=_text(raw.get("summary") or answer[:180]),
        render_blocks=raw_blocks,
        artifacts=raw_artifacts,
    )
    _apr_timing_log("response_package_ready", response_package_started, answer_chars=len(answer),
        raw_render_blocks=len(raw_blocks), raw_artifacts=len(raw_artifacts),
        packaged_blocks=len(packaged.get("render_blocks") or []), packaged_artifacts=len(packaged.get("artifacts") or []))

    request_structure = interpretation.get("request_structure") if isinstance(interpretation.get("request_structure"), dict) else {}
    presentation_sequence = request_structure.get("presentation_sequence") if isinstance(request_structure.get("presentation_sequence"), list) else []
    graph_policy = (interpretation.get("intent") or {}).get("graph_policy") if isinstance((interpretation.get("intent") or {}).get("graph_policy"), dict) else {}
    image_pending = bool((interpretation.get("intent") or {}).get("wants_image"))

    # First publish all text and non-image typed renderers. The Web replaces this
    # provisional SceneContract with the final one, while the image generator keeps
    # running and the existing visual typing indicator remains active.
    if progress_sink:
        try:
            progressive_blocks = prepare_render_blocks_for_room_dispatch(
                packaged.get("render_blocks") or [],
                answer=answer,
                requested_outputs=(interpretation.get("intent") or {}).get("requested_outputs") or [],
                graph_policy=graph_policy,
            )
            progressive_blocks = [block for block in progressive_blocks if str(block.get("type") or "").lower() not in {"image", "gallery"}]
            progressive_blocks = _apply_presentation_sequence(progressive_blocks, answer, presentation_sequence)
            stable_scene_id = _stable_scene_id(identity)
            partial_scene = {
                "scene_id": stable_scene_id,
                "turn_id": identity["message_id"],
                "flow_id": identity["flow_id"],
                "answer": answer,
                "content": answer,
                "render_blocks": progressive_blocks,
                "partial": True,
                "status": "rendering" if image_pending else "text_ready",
            }
            progress_sink({
                "type": "partial_answer",
                "stage": "text_ready",
                "data": {
                    "success": True,
                    "answer": answer,
                    "content": answer,
                    "summary": packaged.get("summary") or answer[:180],
                    "render_blocks": progressive_blocks,
                    "scene_contract": partial_scene,
                    "message_id": identity["message_id"],
                    "flow_id": identity["flow_id"],
                    "scene_id": stable_scene_id,
                    "partial": True,
                },
            })
            _apr_timing_log(
                "progressive_text_ready",
                None,
                message_key=_apr_diag_ref(identity.get("message_id")),
                scene_id=stable_scene_id,
                render_blocks=len(progressive_blocks),
                text_blocks=sum(1 for block in progressive_blocks if str(block.get("type") or "").lower() in {"text", "message", "answer", "markdown", "message_text"}),
                image_pending=image_pending,
            )
            if image_pending:
                image_step = next((item for item in presentation_sequence if item.get("final_output") and "image" in (item.get("output_types") or [])), None)
                if image_step is None:
                    image_steps = [item for item in presentation_sequence if "image" in (item.get("output_types") or [])]
                    image_step = image_steps[-1] if image_steps else None
                progress_sink({
                    "type": "render_pending",
                    "stage": "rendering",
                    "render_type": "image",
                    "step_index": int((image_step or {}).get("step_index") or 1),
                    "title": _text((image_step or {}).get("title") or "Image generation"),
                    "message_id": identity["message_id"],
                    "flow_id": identity["flow_id"],
                    "scene_id": stable_scene_id,
                    "partial": True,
                })
        except Exception as progress_error:
            _apr_timing_log("progressive_handoff_skipped", None, error=type(progress_error).__name__)

    image_result = None
    image_intent = interpretation.get("intent") if isinstance(interpretation.get("intent"), dict) else {}
    if image_intent.get("wants_image") and (
        not bool(provider_metadata.get("provider_fallback"))
        or image_intent.get("image_operation") == "edit"
    ):
        image_started = time.perf_counter()
        if image_intent.get("image_operation") == "edit" or _text(image_intent.get("task")) == "edit_image":
            try:
                image_result = await _edit_image_artifact(interpretation, visual_context or [])
            except Exception as image_edit_error:
                _apr_timing_log(
                    "image_edit_failed", None,
                    error=type(image_edit_error).__name__,
                    source_available=bool((interpretation.get("intent") or {}).get("source_image_available")),
                )
                image_result = None
        elif image_intent.get("reuse_saved_image"):
            saved_output = next((
                item for item in restored_assets
                if isinstance(item, dict)
                and _text(item.get("kind")).lower() == "image"
                and _text(item.get("asset_role")).lower() in {"april_output", "assistant_output", "generated"}
                and _text(item.get("_content_data_uri")).startswith("data:image/")
            ), None)
            decoded_saved = _decode_asset_data_uri(saved_output.get("_content_data_uri")) if saved_output else None
            if decoded_saved:
                saved_bytes, saved_mime = decoded_saved
                saved_width = int((saved_output or {}).get("width") or 0)
                saved_height = int((saved_output or {}).get("height") or 0)
                if len(saved_bytes) >= 24 and saved_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                    import struct as _struct
                    saved_width = saved_width or int(_struct.unpack(">I", saved_bytes[16:20])[0])
                    saved_height = saved_height or int(_struct.unpack(">I", saved_bytes[20:24])[0])
                saved_image_item = {
                    "src": _mime_data_uri(saved_bytes, saved_mime or "image/png"),
                    "mime_type": saved_mime or "image/png",
                    "width": saved_width,
                    "height": saved_height,
                    "alt": _text((saved_output or {}).get("prompt") or "Сохранённое изображение предыдущей сцены")[:180],
                    "caption": "Изображение восстановлено из сохранённой сцены",
                }
                reused_artifact = {
                    "artifact_type": "image",
                    "type": "image",
                    "mime_type": saved_mime or "image/png",
                    "width": saved_width,
                    "height": saved_height,
                    "payload": {
                        "kind": "generated_image",
                        "artifact_type": "image",
                        "mime_type": saved_mime or "image/png",
                        "width": saved_width,
                        "height": saved_height,
                        "images": [saved_image_item],
                    },
                }
                image_result = {
                    "success": True,
                    "image_bytes": saved_bytes,
                    "mime_type": saved_mime or "image/png",
                    "width": saved_width,
                    "height": saved_height,
                    "prompt": _text((saved_output or {}).get("prompt"))[:1200],
                    "artifact": reused_artifact,
                    "reused": True,
                }
                _apr_timing_log("saved_image_reuse", None, reused=True, image_bytes=len(saved_bytes), message_key=_apr_diag_ref((saved_output or {}).get("asset_message_id")))
        if image_result is None:
            image_result = await _generate_image_artifact(
                interpretation,
                raw,
                identity,
            )
        _apr_timing_log(
            "image_edit" if image_intent.get("image_operation") == "edit" else "image_generation",
            image_started,
            succeeded=bool(image_result),
            reused=bool((image_result or {}).get("reused")),
            source_message_key=_apr_diag_ref((image_result or {}).get("source_asset_message_id")),
        )
        if image_result:
            source_artifact = image_result.get("artifact") if isinstance(image_result.get("artifact"), dict) else image_result
            artifact_payload = source_artifact.get("payload") if isinstance(source_artifact.get("payload"), dict) else {}
            source_items = source_artifact.get("images") if isinstance(source_artifact.get("images"), list) else artifact_payload.get("images", [])
            source_items = source_items if isinstance(source_items, list) else []
            raw_image_bytes = image_result.get("image_bytes")
            image_mime = _text(image_result.get("mime_type") or source_artifact.get("mime_type") or "image/png")
            image_data_uri = _mime_data_uri(bytes(raw_image_bytes), image_mime) if isinstance(raw_image_bytes, (bytes, bytearray)) and raw_image_bytes else ""
            source_item = next((item for item in source_items if isinstance(item, dict) and _text(item.get("src") or item.get("image_data_uri") or item.get("url")).startswith("data:image/")), {})
            if not image_data_uri:
                image_data_uri = _text(source_item.get("src") or source_item.get("image_data_uri") or source_item.get("url"))
            image_width = int(image_result.get("width") or source_artifact.get("width") or source_item.get("width") or 0)
            image_height = int(image_result.get("height") or source_artifact.get("height") or source_item.get("height") or 0)
            visible_image = {
                "src": image_data_uri,
                "mime_type": image_mime,
                "width": image_width,
                "height": image_height,
                "alt": _text(source_item.get("alt") or source_item.get("title") or "Иллюстрация к ответу")[:180],
                "caption": _text(source_item.get("caption") or source_item.get("title"))[:220],
            }
            # Keep the image bytes exactly once in the response: GalleryBlock reads
            # payload.images. The previous block duplicated the same ~400 KB PNG
            # through payload, block.artifact, block.images and artifacts, raising
            # peak JSON/React memory use and the risk of the Web render crashing.
            compact_artifact = {
                "artifact_type": "image",
                "type": "image",
                "mime_type": image_mime,
                "width": image_width,
                "height": image_height,
                "generated": not bool((image_result or {}).get("reused")),
                "reused": bool((image_result or {}).get("reused")),
            }
            packaged["artifacts"].append(compact_artifact)
            visible_image_payload = {
                "kind": "generated_image",
                "artifact_type": "image",
                "mime_type": image_mime,
                "width": image_width,
                "height": image_height,
                "images": [visible_image] if image_data_uri else [],
            }
            image_step_index = 1
            image_step_title = "Illustration"
            image_sequence_items = [item for item in presentation_sequence if isinstance(item, dict) and "image" in (item.get("output_types") or [])]
            image_sequence_item = next((item for item in image_sequence_items if item.get("final_output")), None)
            if image_sequence_item is None and image_sequence_items:
                image_sequence_item = image_sequence_items[-1]
            if isinstance(image_sequence_item, dict):
                image_step_index = max(1, int(image_sequence_item.get("step_index") or 1))
                image_step_title = _text(image_sequence_item.get("title") or "Final portrait")[:100]
            else:
                question_sequence = request_structure.get("question_sequence") if isinstance(request_structure.get("question_sequence"), list) else []
                image_questions = []
                for question in question_sequence:
                    if not isinstance(question, dict):
                        continue
                    question_outputs = question.get("output_types") or question.get("outputs") or []
                    if isinstance(question_outputs, str):
                        question_outputs = [question_outputs]
                    if any(str(value).lower() == "image" for value in question_outputs):
                        image_questions.append(question)
                if image_questions:
                    last_image_question = image_questions[-1]
                    image_step_index = max(1, int(last_image_question.get("step_index") or 1))
                    image_step_title = _text(last_image_question.get("title") or last_image_question.get("request") or "Illustration")[:100]
            image_block = {
                "type": "image",
                "step_index": image_step_index,
                "step_title": image_step_title,
                "renderer": get_web_renderer_registration("image").get("renderer", "GalleryBlock"),
                "viewer": get_web_renderer_registration("image").get("viewer", "GalleryBlock"),
                "content": "",
                "payload": visible_image_payload,
            }
            packaged["render_blocks"].append(image_block)

    if _text(image_intent.get("task")) == "edit_image":
        edit_state = "success" if image_result and image_result.get("success") else "failed"
        answer = _image_edit_message(interpretation, edit_state)
        packaged["answer"] = answer
        packaged["content"] = answer
        packaged["summary"] = "Изображение отредактировано." if edit_state == "success" else "Не удалось завершить редактирование изображения."
        text_blocks = [
            block for block in (packaged.get("render_blocks") or [])
            if isinstance(block, dict) and _text(block.get("type") or block.get("artifact_type")).lower() in {"text", "message", "answer", "markdown", "message_text"}
        ]
        if text_blocks:
            text_blocks[0]["content"] = answer
            text_blocks[0]["text"] = answer
            packaged["render_blocks"] = [block for block in (packaged.get("render_blocks") or []) if not (
                isinstance(block, dict) and _text(block.get("type") or block.get("artifact_type")).lower() in {"text", "message", "answer", "markdown", "message_text"}
            )] + [text_blocks[0]]
        else:
            packaged.setdefault("render_blocks", []).insert(0, {
                "type": "text",
                "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                "content": answer,
            })

    normalized_blocks = _apply_presentation_sequence(
        packaged["render_blocks"] or [], answer, presentation_sequence
    )
    # Preserve stable model ordering within each request step while ensuring that
    # a generated image is placed beside its matching explanation, not appended to
    # the end of a multi-question scene regardless of its semantic step.
    def _safe_block_step_index(block: Any) -> int:
        try:
            return max(1, int(block.get("step_index") or 1)) if isinstance(block, dict) else 1
        except (TypeError, ValueError, OverflowError):
            return 1

    indexed_blocks = list(enumerate(normalized_blocks))
    indexed_blocks.sort(key=lambda pair: (_safe_block_step_index(pair[1]), pair[0]))
    normalized_blocks = [block for _, block in indexed_blocks]
    for scene_index, block in enumerate(normalized_blocks):
        if isinstance(block, dict):
            block.setdefault("step_index", 1)
            block["sequence_index"] = scene_index
    if not normalized_blocks:
        normalized_blocks = [
            {
                "type": "text",
                "renderer": get_web_renderer_registration("text").get("renderer", "MessageTextBlock"),
                "viewer": get_web_renderer_registration("text").get("viewer", "MessageTextBlock"),
                "content": packaged["answer"],
            }
        ]

    response = MachineResponse(
        answer=packaged["answer"],
        content=packaged["content"],
        summary=packaged["summary"],
        render_blocks=normalized_blocks,
        artifacts=list(packaged["artifacts"]),
        metadata={
            "provider_ms": provider_ms,
            "identity": identity,
            "interpretation": interpretation,
            "selected_rooms": selected_rooms,
            "render_plan": render_plan,
            "image_generated": bool(image_result and not image_result.get("reused")),
            "image_reused": bool(image_result and image_result.get("reused")),
            "local_clarification": bool(provider_metadata.get("local_clarification")),
            "dialogue_memory_record": (
                raw.get("metadata", {}).get("dialogue_memory_record", {})
                if isinstance(raw.get("metadata"), dict) else {}
            ),
            "provider_fallback": bool(provider_metadata.get("provider_fallback")),
            "provider_error_code": _text(provider_metadata.get("provider_error_code")),
            "provider_retries": int(provider_metadata.get("provider_retries") or 0),
            "provider_output_limit": provider_metadata.get("provider_output_limit") or 12000,
        },
    )

    # Provider responses do not get to change the authenticated identity.
    response_identity = {
        **identity,
        **dict(response.metadata.get("identity") or {}),
    }
    assert_identity_match(identity, response_identity)

    rows_for_turn = dialogue_context.get("candidates") or []
    turn_index = (
        max(
            [int(item.get("turn_index") or 0) for item in rows_for_turn],
            default=-1,
        )
        + 1
    )
    if _text(dialogue_context.get("relation")).upper() == "NEW":
        turn_index = 0

    scene_started = time.perf_counter()
    result = _build_scene(
        response,
        identity,
        interpretation,
        turn_index,
        {
            "canonical_route": CANONICAL_ROUTE,
            "processor_version": PROCESSOR_VERSION,
            "stages": [
                "bot.ru",
                "input_reader",
                "premium_state_manager_search",
                "premium_interpretation_identity",
                "Premium_C_ARTIFACT_CONTRACT",
                "provider_luna",
                "C_APRIL_IMAGES_GENERATOR" if image_result and not image_result.get("reused") else "",
                "SceneContract",
                "RenderMessage",
                "bot.ru",
                "Web",
            ],
        },
    )
    _apr_timing_log("scene_contract_build", scene_started,
        render_blocks=len(response.render_blocks or []), answer_chars=len(response.answer or ""))

    # Persist the complete structured turn after Provider/SceneContract.
    # PostgreSQL remains storage only; State Manager will search these fields
    # on the next request.
    safe_visual_context = dict(request.visual_context)
    safe_visual_items: list[dict[str, Any]] = []
    for item in (request.visual_context.get("items") or []) if isinstance(request.visual_context, dict) else []:
        if not isinstance(item, dict):
            continue
        safe_visual_items.append({
            "type": _text(item.get("type") or "input_image"),
            "filename": _text(item.get("filename") or "image"),
            "source_type": _text(item.get("source_type") or "image"),
            "mime_type": _text(item.get("mime_type") or "image/*"),
            "sequence_index": int(item.get("sequence_index", 9999) or 0),
            "asset_role": _text(item.get("asset_role") or "user_input"),
            "asset_message_id": _text(item.get("asset_message_id") or identity["message_id"]),
            "output_type": _text(item.get("output_type")),
        })
    safe_visual_context["items"] = safe_visual_items
    safe_visual_context["has_input_images"] = bool(safe_visual_items)

    # Save original user inputs under the exact turn where they were uploaded.
    # The file bytes stay on disk; only small references enter dialogue_memory.
    persisted_input_refs: list[dict[str, Any]] = []
    seen_input_keys: set[tuple[str, str, str]] = set()
    for item in (visual_context or []):
        if not isinstance(item, dict) or item.get("recalled_from_memory"):
            continue
        decoded = _decode_asset_data_uri(item.get("image_url") or item.get("data_uri"))
        if not decoded:
            continue
        raw_bytes, mime = decoded
        filename = _text(item.get("filename") or f"uploaded-image-{identity['message_id'][-8:]}.png")
        dedupe = (filename, hashlib.sha256(raw_bytes).hexdigest(), "user_input")
        if dedupe in seen_input_keys:
            continue
        seen_input_keys.add(dedupe)
        ref = _save_premium_asset(uid, identity["message_id"], filename=filename, content=raw_bytes,
            mime_type=_text(item.get("mime_type") or mime), kind="image", asset_role="user_input",
            metadata={"source_type": _text(item.get("source_type") or "user_upload"),
                      "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
                      "analysis_summary": _text(item.get("analysis_summary"))[:1200],
                      "analysis_key_details": item.get("analysis_key_details") if isinstance(item.get("analysis_key_details"), list) else []})
        if ref:
            persisted_input_refs.append(ref)
    for item in (file_inputs or []):
        if not isinstance(item, dict) or item.get("recalled_from_memory"):
            continue
        decoded = _decode_asset_data_uri(item.get("file_data") or item.get("data_uri"))
        if not decoded:
            continue
        raw_bytes, mime = decoded
        filename = _text(item.get("filename") or f"uploaded-file-{identity['message_id'][-8:]}.bin")
        dedupe = (filename, hashlib.sha256(raw_bytes).hexdigest(), "user_input")
        if dedupe in seen_input_keys:
            continue
        seen_input_keys.add(dedupe)
        ref = _save_premium_asset(uid, identity["message_id"], filename=filename, content=raw_bytes,
            mime_type=_text(item.get("mime_type") or mime), kind="file", asset_role="user_input",
            metadata={"source_type": "user_upload", "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999), "analysis_summary": _text(item.get("analysis_summary"))[:1200]})
        if ref:
            persisted_input_refs.append(ref)
    for item in (file_contents or []):
        if not isinstance(item, dict) or item.get("recalled_from_memory"):
            continue
        body = _text(item.get("persistence_content") or item.get("content"))
        if not body:
            continue
        filename = _text(item.get("filename") or f"uploaded-text-{identity['message_id'][-8:]}.txt")
        raw_bytes = body.encode("utf-8")
        dedupe = (filename, hashlib.sha256(raw_bytes).hexdigest(), "user_input")
        if dedupe in seen_input_keys:
            continue
        seen_input_keys.add(dedupe)
        ref = _save_premium_asset(uid, identity["message_id"], filename=filename, content=raw_bytes,
            mime_type=_text(item.get("mime_type") or "text/plain"), kind="text_file", asset_role="user_input",
            metadata={"source_type": "user_upload_text", "sequence_index": int(item.get("sequence_index", 9999) if item.get("sequence_index") is not None else 9999),
                      "analysis_summary": _text(item.get("analysis_summary"))[:1200],
                      "reader_truncated": bool(item.get("reader_truncated")), "source_chars": int(item.get("source_chars") or len(body))})
        if ref:
            persisted_input_refs.append(ref)
    for ref in persisted_input_refs:
        attachment_refs.append({key: ref.get(key) for key in ("asset_id", "filename", "kind", "mime_type", "asset_role", "output_type", "message_id", "storage_key", "size_bytes", "sha256", "metadata") if ref.get(key) is not None})

    output_asset_persist_started = time.perf_counter()
    generated_asset_saved = False
    output_asset_refs: list[dict[str, Any]] = []
    durable_asset_payloads: list[dict[str, Any]] = []
    if image_result:
        # The generator returns validated raw bytes as well as a scene artifact.
        # Persist raw bytes first; artifact fields are the compatibility fallback.
        direct_image_bytes = image_result.get("image_bytes")
        direct_mime = _text(image_result.get("mime_type") or "image/png")
        if isinstance(direct_image_bytes, (bytes, bytearray)) and direct_image_bytes:
            generated_image = (bytes(direct_image_bytes), direct_mime)
        else:
            generated_image = _image_payload_bytes(image_result.get("artifact") or image_result)
        if generated_image:
            generated_bytes, generated_mime = generated_image
            generated_width = int(image_result.get("width") or 0)
            generated_height = int(image_result.get("height") or 0)
            if len(generated_bytes) >= 24 and generated_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                import struct as _struct
                generated_width = generated_width or int(_struct.unpack(">I", generated_bytes[16:20])[0])
                generated_height = generated_height or int(_struct.unpack(">I", generated_bytes[20:24])[0])
            durable_asset_payloads.append({
                "kind": "image",
                "mime_type": generated_mime or "image/png",
                "asset_role": "april_output",
                "output_type": "image",
                "filename": f"april-generated-{identity['message_id'][-10:]}.png",
                "message_id": identity["message_id"],
                "size_bytes": len(generated_bytes),
                "sha256": hashlib.sha256(generated_bytes).hexdigest(),
                "width": generated_width,
                "height": generated_height,
                "prompt": _text((image_result or {}).get("prompt"))[:1200],
                "operation": _text((image_result or {}).get("operation") or image_intent.get("image_operation") or "generate"),
                "derived_from_message_id": _text((image_result or {}).get("source_asset_message_id")),
                "source_asset_role": _text((image_result or {}).get("source_asset_role")),
                "content_base64": base64.b64encode(generated_bytes).decode("ascii"),
            })
            generated_ref = _save_premium_asset(
                uid, identity["message_id"],
                filename=f"april-generated-{identity['message_id'][-10:]}.png",
                content=generated_bytes, mime_type=generated_mime, kind="image",
                asset_role="april_output", output_type="image",
                metadata={
                    "source_type": "april_generated", "asset_role": "april_output", "output_type": "image",
                    "width": generated_width, "height": generated_height,
                    "prompt": _text((image_result or {}).get("prompt"))[:1200],
                    "operation": _text((image_result or {}).get("operation") or image_intent.get("image_operation") or "generate"),
                    "derived_from_message_id": _text((image_result or {}).get("source_asset_message_id")),
                    "source_asset_role": _text((image_result or {}).get("source_asset_role")),
                },
            )
            if generated_ref:
                generated_asset_saved = True
                output_asset_refs.append(generated_ref)

    # Save code/file output as a separately versioned asset paired to this turn.
    # A visible CodeBlock remains in SceneContract; this binary/text asset lets
    # later CONTINUE requests retrieve the exact source rather than its summary.
    requested_outputs = set(str(x).lower() for x in (interpretation.get("intent") or {}).get("requested_outputs", []))
    should_persist_code = bool((interpretation.get("intent") or {}).get("wants_code") or (interpretation.get("intent") or {}).get("wants_file"))
    if should_persist_code:
        code_blocks = [block for block in normalized_blocks if isinstance(block, dict) and str(block.get("type") or "").lower() == "code"]
        seen_source_hashes: set[str] = set()
        for block_index, block in enumerate(code_blocks[:4], 1):
            extracted = _source_code_from_block(block)
            if not extracted:
                continue
            code_text, language, extension = extracted
            code_bytes = code_text.encode("utf-8")
            source_hash = hashlib.sha256(code_bytes).hexdigest()
            if source_hash in seen_source_hashes:
                continue
            seen_source_hashes.add(source_hash)
            filename = _text(block.get("filename")) or f"april-output-{identity['message_id'][-10:]}-{block_index}.{extension}"
            saved_ref = _save_premium_asset(uid, identity["message_id"], filename=filename, content=code_bytes,
                mime_type="text/plain", kind="text_file", asset_role="april_output", output_type="code",
                metadata={"source_type": "april_generated", "language": language})
            if saved_ref:
                saved_ref["metadata"] = {**(saved_ref.get("metadata") or {}), "language": language}
                output_asset_refs.append(saved_ref)

        # Persist explicit file artifacts as actual bytes/text, not only as a
        # caption in JSONB. Do not duplicate an already-saved CodeBlock.
        for artifact_index, artifact in enumerate((raw_artifacts or [])[:6], 1):
            if not isinstance(artifact, dict):
                continue
            artifact_type = _text(artifact.get("type") or artifact.get("artifact_type")).lower()
            if artifact_type not in {"file", "document", "text_file", "code_file"}:
                continue
            filename = _text(artifact.get("filename") or artifact.get("name") or f"april-output-{identity['message_id'][-10:]}-{artifact_index}.txt")
            mime = _text(artifact.get("mime_type") or artifact.get("content_type") or "text/plain")
            body_value = artifact.get("content") or artifact.get("text") or artifact.get("code")
            file_bytes = b""
            text_content = ""
            if isinstance(body_value, str) and body_value.strip():
                text_content = body_value
                file_bytes = body_value.encode("utf-8")
            encoded = artifact.get("file_base64") or artifact.get("base64") or artifact.get("b64_json")
            data_uri = artifact.get("data_uri") or artifact.get("file_data_uri")
            try:
                if isinstance(data_uri, str) and data_uri.startswith("data:") and ";base64," in data_uri:
                    header, b64 = data_uri.split(",", 1)
                    file_bytes = base64.b64decode(b64, validate=True)
                    mime = header[5:].split(";", 1)[0] or mime
                    if mime.startswith("text/"):
                        text_content = file_bytes.decode("utf-8", errors="replace")
                elif isinstance(encoded, str) and encoded:
                    file_bytes = base64.b64decode(encoded, validate=True)
                    if mime.startswith("text/"):
                        text_content = file_bytes.decode("utf-8", errors="replace")
            except Exception:
                file_bytes = b""
            if not file_bytes or len(file_bytes) > 10 * 1024 * 1024:
                continue
            source_hash = hashlib.sha256(file_bytes).hexdigest()
            if source_hash in seen_source_hashes:
                continue
            saved_ref = _save_premium_asset(uid, identity["message_id"], filename=filename, content=file_bytes,
                mime_type=mime, kind="text_file" if (mime.startswith("text/") or text_content) else "file",
                asset_role="april_output", output_type="file",
                metadata={"source_type": "april_generated"})
            if saved_ref:
                output_asset_refs.append(saved_ref)

    _apr_timing_log("output_asset_persist", output_asset_persist_started,
        generated_asset_saved=generated_asset_saved, output_asset_refs=len(output_asset_refs),
        durable_asset_payloads=len(durable_asset_payloads),
        durable_asset_bytes=sum(int(item.get("size_bytes") or 0) for item in durable_asset_payloads))

    # Make the current Scene carry asset pointers and retrieval evidence as well
    # as the renderer blocks; no data URI or private file bytes enter the Scene.
    scene_contract = result.get("scene_contract") if isinstance(result.get("scene_contract"), dict) else {}
    scene_meta = scene_contract.get("metadata") if isinstance(scene_contract.get("metadata"), dict) else {}
    scene_meta["dialogue_assets"] = {
        "user_inputs": attachment_refs,
        "april_outputs": output_asset_refs,
        "pairing": {"user_id": uid, "dialog_id": identity["dialog_id"], "conversation_id": identity["conversation_id"], "message_id": identity["message_id"], "interpretation_id": identity["interpretation_id"]},
    }
    scene_contract["metadata"] = scene_meta
    result["scene_contract"] = scene_contract

    response_memory_record = (
        raw.get("dialogue_memory_record") if isinstance(raw.get("dialogue_memory_record"), dict)
        else ((raw.get("metadata") or {}).get("dialogue_memory_record") if isinstance(raw.get("metadata"), dict) else {})
    )
    if not isinstance(response_memory_record, dict):
        response_memory_record = {}
    inherited_work_branch = (
        dialogue_context.get("active_work_branch")
        if dialogue_context.get("hot_work_followup") and isinstance(dialogue_context.get("active_work_branch"), dict)
        else {}
    )
    active_work_record = build_active_work_branch_record(
        user_text=original or current_text,
        april_text=answer,
        summary=_text(response_memory_record.get("summary") or raw.get("summary") or answer[:180]),
        topic=_text(response_memory_record.get("topic") or response_memory_record.get("title")),
        message_id=identity["message_id"],
        dialog_id=identity["dialog_id"],
        conversation_id=identity["conversation_id"],
        relation=_text(dialogue_context.get("relation") or "NEW"),
        inherited_branch=inherited_work_branch,
        intent=interpretation,
        requested_outputs=list(request.requested_outputs),
        render_blocks=list(response.render_blocks or []),
        artifacts=list(response.artifacts or []),
    )
    structured_request = _strip_inline_binary({
        "request_id": request.request_id,
        "goal": request.goal,
        "intent": dict(request.intent),
        "conversation": dict(request.conversation),
        "memory": dict(request.memory),
        "visual_context": safe_visual_context,
        "attachments": list(attachments or []),
        "attachment_index": attachment_index,
        "available_tools": list(request.available_tools),
        "requested_outputs": list(request.requested_outputs),
        "required_competencies": list(request.required_competencies),
        "required_artifacts": list(request.required_artifacts),
        "routing": dict(request.routing),
        "constraints": dict(request.constraints),
    })
    structured_response = _strip_inline_binary({
        "answer": response.answer,
        "content": response.content,
        "summary": response.summary,
        "render_blocks": list(response.render_blocks or []),
        "artifacts": list(response.artifacts or []),
        "metadata": dict(response.metadata or {}),
        "scene_contract": result.get("scene_contract") or {},
        "generated_asset_saved": generated_asset_saved,
        "asset_refs": {
            "source_inputs": attachment_refs,
            "april_outputs": output_asset_refs,
        },
        "dialogue_memory_record": response_memory_record,
        **({"active_work_branch": active_work_record} if active_work_record else {}),
    })

    pair_save_started = time.perf_counter()
    saved = save_dialogue_pair(
        uid,
        original or current_text,
        answer,
        created_at=message_created_at,
        turn_index=turn_index,
        user_en=current_text,
        april_en=_text(raw.get("internal_answer_en")) or answer,
        language=display_language,
        relation=_text(dialogue_context.get("relation") or "NEW"),
        dialog_id=identity["dialog_id"],
        conversation_id=identity["conversation_id"],
        message_id=identity["message_id"],
        interpretation_id=identity["interpretation_id"],
        structured_request=structured_request,
        structured_response=structured_response,
        asset_payloads=durable_asset_payloads,
    )
    pair_save_ms = round((time.perf_counter() - pair_save_started) * 1000, 1)
    _apr_timing_log("dialogue_pair_persist", saved=bool(saved), elapsed_ms=pair_save_ms,
        answer_chars=len(answer), structured_request_fields=len(structured_request),
        structured_response_fields=len(structured_response), render_blocks=len(response.render_blocks or []),
        artifacts=len(response.artifacts or []), durable_asset_payloads=len(durable_asset_payloads))

    result.update(
        {
            "april_id": uid,
            "conversation_id": identity["conversation_id"],
            "dialog_id": identity["dialog_id"],
            "message_id": identity["message_id"],
            "interpretation_id": identity["interpretation_id"],
            "flow_id": identity["flow_id"],
            "processor_version": PROCESSOR_VERSION,
            "display_language": display_language,
            "internal_language": "en",
            "translation": translation or {},
            "memory_window_hours": 24,
            "memory_relation": dialogue_context.get("relation"),
            "memory_pair_count": int(dialogue_context.get("search", {}).get("total_pairs") or 0),
            "memory_selected_count": len(dialogue_context.get("selected_pairs") or []),
            "memory_saved": saved,
            "dialogue_assets_restored": [
                {key: value for key, value in item.items() if not str(key).startswith("_")}
                for item in restored_assets if isinstance(item, dict)
            ],
            "generated_asset_saved": generated_asset_saved,
            "dialogue_asset_refs": {"source_inputs": attachment_refs, "april_outputs": output_asset_refs},
            "interpretation": interpretation,
            "route": result.get("scene_contract", {}).get("metadata", {}).get("route", {}),
        }
    )
    _apr_timing_log("execute_total", pipeline_started, user_key=_apr_diag_ref(uid),
        dialog_key=_apr_diag_ref(identity.get("dialog_id")), message_key=_apr_diag_ref(identity.get("message_id")),
        relation=dialogue_context.get("relation"), answer_chars=len(answer), saved=bool(saved),
        provider_ms=provider_ms, restored_assets=len(restored_assets or []))
    return result


__all__ = ["execute", "PROCESSOR_VERSION", "CANONICAL_ROUTE"]
