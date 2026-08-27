"""April Quantum Processor — balanced single-route executor.

This is a quantum-inspired processor, not a physical quantum computer.
It evaluates many independent evidence channels, fuses them multiplicatively,
then collapses them to ONE dialogue state, ONE request and ONE scene contract.
There is exactly one Provider call per user turn.
"""
from __future__ import annotations

import ast
import json
import re
import hashlib
import threading
from copy import deepcopy
from typing import Any

from blocks.context_system import build_deephub_context, build_executor_context_packet
from blocks.interpretation_layer import (
    interpret_request,
    build_processor_execution_context,
    QUANTUM_EVIDENCE_FUSION,
    QUANTUM_DIALOGUE_ENGINE,
)
from blocks.semantic_core import analyze as semantic_analyze
from blocks.reasoning_state import build_reasoning_state
from blocks.cognitive_core import analyze_cognition
from blocks.response_decision import build_response_decision
from blocks.visual_reference_system import build_visual_reference
from blocks.experience import build_experience_evidence
from blocks.experience_manager import get_experience
from blocks.goal_engine import build_goal_evidence
from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.intent_resolver import resolve_input, build_focus_intent_state
from blocks.router import route_request
from blocks.router_system import decide_action
from blocks.state_manager import get_state, update_dialog_context, update_scene_context, query_dynamic_memory, is_dialogue_visible_scene
from blocks.C_ARTIFACT_CONTRACT import MachineRequest, MachineResponse, build_machine_scene, build_scene_contract
from blocks.provider_router import generate_text
from blocks.energy_manager import (build_quantum_acceleration_profile, apply_quantum_acceleration, validate_quantum_acceleration)
from blocks.april_personality import APRIL_IDENTITY

PROCESSOR_VERSION = "april_quantum_processor_quantum64_v32_unified_quantum_memory_context_sync_v3"
SINGLE_ROUTE = True
PROVIDER_CALLS = 1
OUTPUT_MIN_TOKENS = 1
OUTPUT_MAX_TOKENS = 8000

# Canonical structural dimensions of the single processor matrix.
# These are fixed engine dimensions, not routing triggers or score thresholds.
QUANTUM_CORE_COUNT = 8
QUANTUM_LANE_COUNT = 8
QUANTUM_CORES = tuple(f"core_{i+1}" for i in range(QUANTUM_CORE_COUNT))
QUANTUM_LANES = tuple(f"lane_{i+1}" for i in range(QUANTUM_LANE_COUNT))

def _quantum_snapshot(value: Any, _active: set[int] | None = None) -> Any:
    """
    Convert runtime evidence into a detached, JSON-safe snapshot.

    Quantum evidence may contain shared references because multiple engines
    contribute the same dicts. Shared references are fine; live back-references
    are not. This helper detaches every branch so the persisted user state
    cannot become a self-referential object graph.
    """
    active = _active if _active is not None else set()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    oid = id(value)
    if oid in active:
        return {"__cycle__": True}
    if isinstance(value, dict):
        active.add(oid)
        try:
            result = {
                str(k): _quantum_snapshot(v, active)
                for k, v in value.items()
            }
        finally:
            active.remove(oid)
        return result
    if isinstance(value, (list, tuple, set)):
        active.add(oid)
        try:
            result = [_quantum_snapshot(v, active) for v in value]
        finally:
            active.remove(oid)
        return result
    # Runtime objects are not allowed into canonical state/evidence.
    return _s(value)

def _s(v: Any) -> str:
    return str(v or "").strip()

def _clip(v: Any, n: int = 900) -> str:
    s = _s(v)
    return s if len(s) <= n else s[-n:]

def _tokens(v: Any) -> set[str]:
    return set(re.findall(r"[\wА-Яа-яЁё]+", _s(v).lower()))

def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}

def _as_list(value: Any) -> list:
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []

def _unique_strings(values: Any) -> list[str]:
    result: list[str] = []
    for value in _as_list(values):
        value = _s(value).lower()
        if value and value not in result:
            result.append(value)
    return result


def _user_scope(state: dict, user_id: Any) -> dict:
    """Canonical identity scope carried through the one route and scene contract."""
    uid = _s(user_id)
    if not uid:
        raise RuntimeError("Quantum release blocked: authenticated user_id missing")

    conversation_id = _s(
        state.get("conversation_id")
        or state.get("memory_scope", {}).get("conversation_id")
        or ""
    )
    if not conversation_id:
        conversation_id = f"april-{hashlib.sha256(uid.encode("utf-8")).hexdigest()[:24]}"
        state["conversation_id"] = conversation_id

    scope = {
        "user_id": uid,
        "conversation_id": conversation_id,
        "identity_bound": True,
        "scope_version": "USER_SCOPED_SCENE_V1",
    }
    state["memory_scope"] = dict(scope)
    return scope

def _merge_evidence_fields(target: dict, sources: tuple[dict, ...]) -> dict:
    """
    Merge only machine evidence into the canonical semantic packet.

    Current request and authoritative semantic fields are never replaced.
    Multi-valued representation/capability evidence is unioned. Scalar
    signals are retained under quantum_evidence_sources so no room can
    overwrite another room's signal.
    """
    target = _as_dict(target)
    representations: list[str] = []
    domains: list[str] = []
    capabilities: list[str] = []
    candidates: list[dict] = []

    for source in sources:
        source = _as_dict(source)
        for key in (
            "required_representations", "candidate_representations",
            "requested_outputs", "required_outputs", "render_types",
            "artifact_types", "representations",
        ):
            for value in _as_list(source.get(key)):
                name = _s(value).lower()
                if name and name not in representations:
                    representations.append(name)
        for key in ("required_domains", "candidate_domains", "required_competencies"):
            for value in _as_list(source.get(key)):
                name = _s(value).lower()
                if name and name not in domains:
                    domains.append(name)
        for key in ("required_capabilities", "available_tools"):
            for value in _as_list(source.get(key)):
                name = _s(value).lower()
                if name and name not in capabilities:
                    capabilities.append(name)
        for item in _as_list(source.get("candidate_signals")):
            if isinstance(item, dict):
                candidates.append(dict(item))

    if representations:
        target["required_representations"] = _unique_strings(
            _as_list(target.get("required_representations")) + representations
        )
        target["candidate_representations"] = _unique_strings(
            _as_list(target.get("candidate_representations")) + representations
        )
    if domains:
        target["required_domains"] = _unique_strings(
            _as_list(target.get("required_domains")) + domains
        )
        target["candidate_domains"] = _unique_strings(
            _as_list(target.get("candidate_domains")) + domains
        )
    if capabilities:
        target["required_capabilities"] = _unique_strings(
            _as_list(target.get("required_capabilities")) + capabilities
        )

    target["quantum_candidate_signals"] = candidates
    return target

# ---------------------------------------------------------------------------
# INTEGRATED QUANTUM MEMORY UNDERSTANDING ENGINE
# ---------------------------------------------------------------------------


ORDINALS = {
    "первый": 1, "первая": 1, "первое": 1,
    "второй": 2, "вторая": 2, "второе": 2,
    "третий": 3, "третья": 3, "третье": 3,
    "четвертый": 4, "четвёртый": 4, "четвертая": 4, "четвёртая": 4,
    "пятый": 5, "пятая": 5, "пятое": 5,
    "шестой": 6, "шестая": 6, "шестое": 6,
    "седьмой": 7, "седьмая": 7, "седьмое": 7,
    "восьмой": 8, "восьмая": 8, "восьмое": 8,
    "девятый": 9, "девятая": 9, "девятое": 9,
    "десятый": 10, "десятая": 10, "десятое": 10,
    "первый пункт": 1, "второй пункт": 2, "третий пункт": 3,
    "четвертый пункт": 4, "четвёртый пункт": 4, "пятый пункт": 5,
    "шестой пункт": 6, "седьмой пункт": 7, "восьмой пункт": 8,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}

LAST_WORDS = {
    "последний": -1, "последняя": -1, "последнее": -1,
    "предпоследний": -2, "предпоследняя": -2, "предпоследнее": -2,
    "last": -1, "second-last": -2, "second-to-last": -2,
}

REFERENCE_RE = re.compile(
    r"(?:\b(?:этот|эта|это|этим|этого|эту|тот|та|то|тем|того|ту|он|она|они|его|её|ее|их|ему|ей|им|про него|про неё|про нее|по нему|по ней|по ним|выше|ниже|предыдущий|предыдущая|предыдущее|previous|this|that|above|below)\b)"
    r"|(?:\b(?:пункт|пункта|элемент|элемента|позиция|позицию|item|point|element|entry|block|блок|график|таблица|table|graph|chart)\b)"
    r"|(?:\b(?:первый|второй|третий|четвертый|четвёртый|пятый|шестой|седьмой|восьмой|девятый|десятый|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b)"
    r"|(?:\b\d{1,3}\s*[.)]\b)",
    re.I,
)

NUMBERED_RE = re.compile(r"^\s*(\d{1,3})\s*[.)]\s*(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*•]\s+(.+?)\s*$")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")


def _text(value: Any, limit: int = 1800) -> str:
    value = str(value or "").strip()
    return value[:limit]


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", str(value or "").lower()))


def _clip(value: Any, limit: int = 900) -> str:
    return _text(value, limit)


class QuantumMemoryUnderstandingEngine:
    VERSION = "quantum_memory_understanding_v2"

    def __init__(self) -> None:
        self._lock = threading.RLock()

    @staticmethod
    def _extract_ordinals(text: str) -> list[int]:
        source = str(text or "").lower()
        found: list[tuple[int, int]] = []
        # Longer phrases first so "третий пункт" is represented once.
        for phrase, value in sorted(ORDINALS.items(), key=lambda x: len(x[0]), reverse=True):
            pos = source.find(phrase)
            if pos >= 0:
                found.append((pos, int(value)))
        found.sort(key=lambda x: x[0])
        result: list[int] = []
        for _, value in found:
            if value not in result:
                result.append(value)
        return result

    @staticmethod
    def _extract_last_reference(text: str) -> int | None:
        source = str(text or "").lower()
        for phrase, value in LAST_WORDS.items():
            if re.search(rf"\b{re.escape(phrase)}\b", source):
                return value
        return None

    @staticmethod
    def _structural_items(previous_assistant: str) -> list[dict[str, Any]]:
        """Extract generic document structure while attaching continuation lines to list items."""
        source_text = str(previous_assistant or "").strip()
        # History normalization can collapse line breaks. Recover numbered
        # structure directly from the text when several ordinal markers remain.
        numbered_segments = list(re.finditer(
            r"(?:^|\s)(\d{1,3})\s*[.)]\s+(.+?)(?=(?:\s+\d{1,3}\s*[.)]\s+)|$)",
            source_text,
            flags=re.S,
        ))
        if len(numbered_segments) >= 2:
            compact_items = []
            for match in numbered_segments[:80]:
                idx = int(match.group(1))
                content = re.sub(r"\s+", " ", match.group(2)).strip()
                title = re.split(r"[—:–]", content, maxsplit=1)[0].strip()
                compact_items.append({
                    "kind": "numbered_item",
                    "index": idx,
                    "title": title[:240],
                    "content": content[:1800],
                    "source": "previous_assistant_text_compact",
                })
            return compact_items

        lines = [line.rstrip() for line in source_text.splitlines()]
        items: list[dict[str, Any]] = []
        paragraph: list[str] = []
        current_item: dict[str, Any] | None = None
        next_auto_index = 0

        def flush_paragraph() -> None:
            nonlocal paragraph, next_auto_index
            if not paragraph:
                return
            text = " ".join(x.strip() for x in paragraph if x.strip()).strip()
            if text:
                next_auto_index += 1
                items.append({
                    "kind": "paragraph",
                    "index": next_auto_index,
                    "title": text[:180],
                    "content": text,
                    "source": "previous_assistant_text",
                })
            paragraph = []

        def flush_item() -> None:
            nonlocal current_item, next_auto_index
            if current_item is None:
                return
            current_item["content"] = _clip(current_item.get("content", ""), 1800)
            items.append(current_item)
            next_auto_index = max(next_auto_index, int(current_item.get("index") or 0))
            current_item = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # A blank line inside a numbered/bullet item is only a visual
                # separator; keep the item alive so its explanatory prose remains
                # attached to the same structural object.
                if current_item is not None:
                    continue
                flush_paragraph()
                continue

            match = NUMBERED_RE.match(line)
            if match:
                flush_item()
                flush_paragraph()
                idx = int(match.group(1))
                content = match.group(2).strip()
                title = re.split(r"[—:–]", content, maxsplit=1)[0].strip()
                current_item = {
                    "kind": "numbered_item",
                    "index": idx,
                    "title": title[:240],
                    "content": content,
                    "source": "previous_assistant_text",
                }
                continue

            match = BULLET_RE.match(line)
            if match:
                flush_item()
                flush_paragraph()
                next_auto_index += 1
                content = match.group(1).strip()
                current_item = {
                    "kind": "bullet_item",
                    "index": next_auto_index,
                    "title": content[:240],
                    "content": content,
                    "source": "previous_assistant_text",
                }
                continue

            match = HEADING_RE.match(line)
            if match:
                flush_item()
                flush_paragraph()
                next_auto_index += 1
                content = match.group(1).strip()
                items.append({
                    "kind": "heading",
                    "index": next_auto_index,
                    "title": content[:240],
                    "content": content,
                    "source": "previous_assistant_text",
                })
                continue

            if current_item is not None:
                current_item["content"] = f"{current_item.get('content', '')} {stripped}".strip()
            else:
                paragraph.append(stripped)

        flush_item()
        flush_paragraph()
        return items[:80]

    @staticmethod
    def _visual_blocks(scene: dict[str, Any]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        raw_blocks = scene.get("render_blocks") if isinstance(scene, dict) else None
        if isinstance(raw_blocks, list):
            for idx, block in enumerate(raw_blocks):
                if not isinstance(block, dict):
                    continue
                payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
                content_parts = [
                    block.get("type"), block.get("renderer"), block.get("title"),
                    block.get("label"), block.get("text"), block.get("content"),
                    payload.get("title"), payload.get("label"), payload.get("x_label"),
                    payload.get("y_label"), payload.get("series"), payload.get("name"),
                ]
                blocks.append({
                    "kind": "render_block",
                    "index": idx + 1,
                    "block_id": block.get("block_id") or block.get("id") or "",
                    "type": block.get("type") or block.get("block_type") or "",
                    "renderer": block.get("renderer") or "",
                    "content": _clip(" ".join(str(x) for x in content_parts if x), 1200),
                    "payload": deepcopy(payload),
                    "source": "visual_scene",
                })
        return blocks[:24]

    @staticmethod
    def _scene_text(scene: dict[str, Any]) -> str:
        if not isinstance(scene, dict):
            return ""
        parts = [
            scene.get("topic"), scene.get("summary"), scene.get("user_request"),
            scene.get("current_request"), scene.get("april_answer"), scene.get("answer"),
        ]
        for block in QuantumMemoryUnderstandingEngine._visual_blocks(scene):
            parts.extend([block.get("type"), block.get("renderer"), block.get("content")])
        return _clip(" ".join(str(x) for x in parts if x), 3200)

    @staticmethod
    def _lexical_score(left: str, right: str) -> float:
        a, b = _tokens(left), _tokens(right)
        if not a or not b:
            return 0.0
        return len(a & b) / max(1, len(a | b))

    def _semantic_score(self, query: str, candidates: list[str]) -> tuple[dict[str, float], str]:
        if not query or not candidates:
            return {}, "none"
        try:
            # Lazy import avoids a circular import: interpretation_layer owns the
            # shared encoder/cache, while this engine only consumes its measurement.
            from blocks.interpretation_layer import QUANTUM_EMBEDDING_ENGINE
            values = QUANTUM_EMBEDDING_ENGINE.similarities(query, candidates)
            return values, "shared_quantum_embedding"
        except Exception:
            return {c: self._lexical_score(query, c) for c in candidates}, "lexical_fallback"

    @staticmethod
    def _visual_reference_kind(text: str) -> str:
        """Infer a generic referenced renderer type from representation language."""
        source = str(text or "").lower()
        mapping = (
            ("graph", ("график", "графика", "графику", "графиком", "chart", "plot")),
            ("table", ("таблица", "таблицу", "таблице", "table")),
            ("formula", ("формула", "формулу", "уравнение", "equation", "formula")),
            ("link", ("ссылк", "link", "url")),
            ("gallery", ("галере", "gallery")),
            ("image", ("изображен", "картин", "image", "picture")),
            ("diagram", ("схем", "диаграм", "diagram")),
        )
        for kind, lexemes in mapping:
            if any(lexeme in source for lexeme in lexemes):
                return kind
        return ""

    @staticmethod
    def _previous_numeric_result(previous_assistant: str) -> str:
        """Recover a compact numeric result from a prior answer."""
        source = str(previous_assistant or "")
        patterns = (
            r"(?:=|равно|получается|получится|result)\s*(-?\d+(?:[.,]\d+)?)",
            r"(-?\d+(?:[.,]\d+)?)\s*$",
        )
        for pattern in patterns:
            matches = re.findall(pattern, source, flags=re.I)
            if matches:
                return matches[-1]
        return ""

    def _need_memory(self, current: str, previous_user: str, previous_assistant: str, scene: dict[str, Any]) -> dict[str, Any]:
        """
        Decide whether the dedicated memory engine must participate in this turn.

        This gate is evidence-driven rather than topic/word triggered:
          * explicit discourse references (pronoun/deictic/ordinal/relative target);
          * meaningful semantic overlap with the previous substantive answer/scene;
          * a structurally incomplete follow-up whose missing operand/target is
            represented by the previous answer (e.g. "теперь вычти 1");
          * never activate merely because a previous turn exists or because the
            current request is short.

        A new topic therefore remains a true independent turn even when memory
        contains many prior scenes.
        """
        source = str(current or "")
        structural = bool(REFERENCE_RE.search(source))
        ordinals = self._extract_ordinals(source)
        last_ref = self._extract_last_reference(source)
        pronoun = bool(re.search(
            r"\b(?:он|она|они|его|её|ее|их|ему|ей|им|этот|эта|это|этим|этом|тот|та|то|"
            r"this|that|he|she|they|him|her|it|them)\b",
            source,
            flags=re.I,
        ))
        operation_followup = bool(re.search(
            r"(?<!\w)(?:теперь|затем|потом|дальше|ещ[её]|then|next)\b",
            source,
            flags=re.I,
        )) and bool(re.search(
            r"(?:[+\-−*/=]|\b(?:вычти|прибавь|умножь|раздели|посчитай|получи|"
            r"subtract|add|multiply|divide|calculate|result|получится)\b)",
            source,
            flags=re.I,
        ))
        short = len(_tokens(source)) <= 12

        lexical_prev = self._lexical_score(source, previous_assistant)
        lexical_scene = self._lexical_score(source, self._scene_text(scene)) if scene else 0.0

        # Structural/visual relations are stronger than loose lexical overlap.
        # The engine may participate for an operation follow-up when the previous
        # answer itself contains a compact numeric/structured result.
        previous_numeric = bool(re.search(r"\d", previous_assistant or ""))
        operation_dependency = bool(operation_followup and previous_numeric)
        visual_reference_kind = self._visual_reference_kind(source)

        active = bool(previous_user or previous_assistant or scene)
        explicit_reference = bool(
            structural or pronoun or ordinals or last_ref is not None or visual_reference_kind
        )

        # A semantic overlap is meaningful only when it exceeds noise. The same
        # gate is deliberately conservative for unrelated new-topic turns.
        semantic_relation = bool(lexical_prev >= 0.12 or lexical_scene >= 0.16)

        needed = active and bool(
            explicit_reference
            or semantic_relation
            or operation_dependency
        )

        return {
            "needed": bool(needed),
            "explicit_reference": explicit_reference,
            "structural_reference": structural,
            "pronoun_reference": pronoun,
            "ordinal_targets": ordinals,
            "relative_target": last_ref,
            "short_followup": short,
            "operation_followup": operation_followup,
            "operation_dependency": operation_dependency,
            "previous_numeric": previous_numeric,
            "visual_reference_kind": visual_reference_kind,
            "semantic_relation": semantic_relation,
            "lexical_previous_assistant": round(lexical_prev, 6),
            "lexical_visual_scene": round(lexical_scene, 6),
        }

    def _candidate_scores(self, current: str, candidates: list[dict[str, Any]], ordinal: int | None, relative: int | None) -> list[dict[str, Any]]:
        texts = [f"{c.get('title','')} {c.get('content','')}" for c in candidates]
        semantic, semantic_source = self._semantic_score(current, texts)
        ranked: list[dict[str, Any]] = []
        for idx, candidate in enumerate(candidates):
            text = texts[idx]
            sem = float(semantic.get(text, 0.0))
            lex = self._lexical_score(current, text)
            structural = 0.0
            if ordinal is not None and int(candidate.get("index") or -999) == ordinal:
                structural = 1.0
            if relative is not None:
                target_index = relative if relative > 0 else len(candidates) + relative + 1
                if int(candidate.get("index") or -999) == target_index:
                    structural = max(structural, 1.0)
            score = min(1.0, 0.62 * structural + 0.24 * sem + 0.14 * lex)
            ranked.append({
                "candidate": candidate,
                "score": round(score, 6),
                "semantic": round(sem, 6),
                "lexical": round(lex, 6),
                "structural": round(structural, 6),
                "semantic_source": semantic_source,
            })
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    @staticmethod
    def _entity_candidates(*texts: str) -> list[str]:
        """Extract generic name-like spans without topic-specific vocabulary."""
        out: list[str] = []
        seen: set[str] = set()
        for source in texts:
            source = str(source or "")
            patterns = (
                r"\b(?:[А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+){1,4})\b",
                r"\b[А-ЯЁA-Z][а-яёa-z]{2,}\b",
            )
            for pattern in patterns:
                for match in re.finditer(pattern, source):
                    value = re.sub(r"\s+", " ", match.group(0)).strip()
                    if not value:
                        continue
                    # Sentence starts are weak entity candidates; retain them only
                    # when they look like a multi-token proper name.
                    if len(value.split()) == 1 and match.start() > 0:
                        prefix = source[max(0, match.start() - 2):match.start()]
                        if prefix not in {"", ". ", "! ", "? ", "\n ", "\r "}:
                            continue
                    key = value.lower()
                    if key not in seen:
                        seen.add(key)
                        out.append(value)
        return out[:24]

    @staticmethod
    def _pair_quality(user_text: str, assistant_text: str) -> float:
        """Score whether a prior USER↔APRIL pair is substantive enough to anchor reference resolution."""
        user = str(user_text or "").strip()
        answer = str(assistant_text or "").strip()
        if not user or not answer:
            return 0.0
        tokens = _tokens(answer)
        paragraphs = max(1, len(re.split(r"\n\s*\n", answer)))
        sentences = max(1, len(re.findall(r"[^.!?]+[.!?]", answer)))
        questions = len(re.findall(r"[?!]", answer))
        numbered = len(re.findall(r"(?:^|\s)\d{1,3}\s*[.)]\s+", answer))
        entities = len(QuantumMemoryUnderstandingEngine._entity_candidates(user, answer))
        length_score = min(1.0, len(answer) / 900.0)
        lexical_richness = min(1.0, len(tokens) / 140.0)
        structure = min(1.0, numbered / 3.0 + max(0, paragraphs - 1) * 0.10)
        declarative = 1.0 - min(1.0, questions / max(1, sentences))
        entity_score = min(1.0, entities / 3.0)
        score = (
            0.40 * length_score
            + 0.20 * lexical_richness
            + 0.15 * structure
            + 0.15 * declarative
            + 0.10 * entity_score
        )
        # Very short one-line clarifications should not outrank a substantive
        # answer simply because they are the immediately preceding turn.
        if len(answer) < 320 and numbered == 0 and paragraphs == 1 and questions:
            score *= 0.45
        return max(0.0, min(1.0, score))

    @classmethod
    def _historical_pairs(cls, dialog_history: list[dict[str, Any]] | None,
                          memory_timeline: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        history = dialog_history if isinstance(dialog_history, list) else []
        for index in range(len(history) - 1):
            left = history[index]
            right = history[index + 1]
            if not isinstance(left, dict) or not isinstance(right, dict):
                continue
            left_role = str(left.get("role") or "").lower()
            right_role = str(right.get("role") or "").lower()
            if left_role in {"user", "human"} and right_role in {"assistant", "april", "bot"}:
                pairs.append({
                    "user": str(left.get("content") or left.get("text") or ""),
                    "assistant": str(right.get("content") or right.get("text") or right.get("answer") or ""),
                    "source": "dialog_history",
                })
        timeline = memory_timeline if isinstance(memory_timeline, dict) else {}
        for day in timeline.values():
            if not isinstance(day, dict):
                continue
            for item in day.get("dialog_pairs", []) or []:
                if not isinstance(item, dict):
                    continue
                user = str(item.get("user_meaning") or item.get("user") or "")
                assistant = str(item.get("april_meaning") or item.get("answer_summary") or item.get("assistant") or "")
                if user and assistant:
                    pairs.append({"user": user, "assistant": assistant, "source": "dialog_pair_memory"})
        # De-duplicate by exact USER/ASSISTANT content while keeping original order.
        result: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for pair in reversed(pairs):
            key = (pair["user"].strip(), pair["assistant"].strip())
            if key in seen:
                continue
            seen.add(key)
            result.append(pair)
        return list(reversed(result))

    @classmethod
    def _select_reference_pair(cls, current: str, previous_user: str, previous_assistant: str,
                               dialog_history: list[dict[str, Any]] | None,
                               memory_timeline: dict[str, Any] | None = None) -> tuple[str, str, str, float]:
        """Choose the best substantive prior pair for a short contextual reference."""
        pairs = cls._historical_pairs(dialog_history, memory_timeline)
        if previous_user and previous_assistant:
            pairs.append({
                "user": previous_user,
                "assistant": previous_assistant,
                "source": "state_previous_pair",
            })
        if not pairs:
            return previous_user, previous_assistant, "none", 0.0

        current_tokens = _tokens(current)
        ranked: list[tuple[float, dict[str, Any]]] = []
        total = len(pairs)
        for pos, pair in enumerate(pairs):
            user = pair["user"]
            assistant = pair["assistant"]
            quality = cls._pair_quality(user, assistant)
            overlap = cls._lexical_score(current, f"{user} {assistant}")
            recency = (pos + 1) / max(1, total)
            # For pronoun/deictic follow-ups, a substantive recent pair is the
            # strongest anchor; lexical overlap is secondary because "он/это"
            # deliberately shares few tokens with its antecedent.
            score = 0.62 * quality + 0.23 * recency + 0.15 * overlap
            ranked.append((score, pair))
        ranked.sort(key=lambda x: x[0], reverse=True)
        score, best = ranked[-1] if False else ranked[0]
        return best["user"], best["assistant"], str(best.get("source") or "history"), float(score)

    @staticmethod
    def _active_scene_from_history(memory_timeline: dict[str, Any] | None, state_scene: dict[str, Any] | None) -> dict[str, Any]:
        if isinstance(state_scene, dict) and state_scene:
            return deepcopy(state_scene)
        timeline = memory_timeline if isinstance(memory_timeline, dict) else {}
        candidates: list[dict[str, Any]] = []
        for day in timeline.values():
            if not isinstance(day, dict):
                continue
            for scene in day.get("visual_scenes", []) or []:
                if isinstance(scene, dict):
                    candidates.append(scene)
        return deepcopy(candidates[-1]) if candidates else {}

    @staticmethod
    def _build_memory_matrix(
        *,
        relation: str,
        reference_resolved: bool,
        continuation: bool,
        visual_present: bool,
        structural_reference: bool,
        semantic_relation: bool,
        history_present: bool,
        context_dependency: bool,
        confidence: float,
        scene_similarity: float,
        topic_similarity: float,
        target: str,
    ) -> dict[str, Any]:
        """Build a deterministic 8x8 quantum-inspired memory evidence matrix."""
        cores = [
            ("dialogue", bool(continuation or relation in {"CONTINUE_TOPIC", "ARTIFACT_REFERENCE"}), confidence),
            ("reference", reference_resolved, confidence if reference_resolved else 0.0),
            ("visual", bool(visual_present and relation != "INDEPENDENT"), scene_similarity),
            ("structure", structural_reference, 1.0 if structural_reference else 0.0),
            ("semantic", semantic_relation, topic_similarity),
            ("history", history_present, 1.0 if history_present else 0.0),
            ("dependency", context_dependency, confidence if context_dependency else 0.0),
            ("release", relation != "INDEPENDENT", confidence if relation != "INDEPENDENT" else 1.0),
        ]
        lanes = ("present","relevance","continuity","reference","visual","structure","context","release")
        matrix = []
        for core_index,(core_name,core_active,core_conf) in enumerate(cores,1):
            row=[]
            for lane_index,lane_name in enumerate(lanes,1):
                states = {
                    "present": core_active or history_present,
                    "relevance": scene_similarity >= 0.16 or topic_similarity >= 0.12 or semantic_relation,
                    "continuity": continuation,
                    "reference": reference_resolved,
                    "visual": visual_present,
                    "structure": structural_reference,
                    "context": context_dependency,
                    "release": relation != "INDEPENDENT",
                }
                active = bool(states[lane_name])
                conf = float(core_conf or 0.0)
                if lane_name == "visual":
                    conf = max(conf, float(scene_similarity or 0.0))
                elif lane_name == "relevance":
                    conf = max(conf, float(scene_similarity or 0.0), float(topic_similarity or 0.0))
                elif lane_name == "reference":
                    conf = confidence if reference_resolved else 0.0
                elif lane_name == "structure":
                    conf = 1.0 if structural_reference else 0.0
                row.append({
                    "core": core_index,
                    "core_name": core_name,
                    "lane": lane_index,
                    "lane_name": lane_name,
                    "state": 1 if active else 0,
                    "confidence": round(min(1.0,max(0.0,conf)),6),
                    "evidence": target if reference_resolved and lane_name in {"reference","structure","visual"} else "",
                })
            matrix.append(row)
        return {
            "version":"QUANTUM-MEMORY-MATRIX-8X8-V3",
            "model":"quantum_inspired_qubit_state",
            "physical_quantum":False,
            "cores":8,"lanes":8,"signals":64,
            "matrix":matrix,
            "active_cells":sum(cell["state"] for row in matrix for cell in row),
            "collapsed_relation":relation,
            "collapsed_target":target,
            "collapsed_confidence":round(float(confidence or 0.0),6),
            "single_collapse":True,
            "decision_owner":"QUANTUM_PROCESSOR",
        }

    def analyze(
        self,
        current_request: str,
        *,
        previous_user: str = "",
        previous_assistant: str = "",
        active_topic: str = "",
        active_goal: str = "",
        visual_scene: dict[str, Any] | None = None,
        dialog_history: list[dict[str, Any]] | None = None,
        dynamic_memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = _text(current_request, 2200)
        previous_user = _text(previous_user, 1800)
        previous_assistant = _text(previous_assistant, 5000)
        scene = deepcopy(visual_scene) if isinstance(visual_scene, dict) else {}

        # The immediate previous turn may be a clarification/error response.
        # For a contextual follow-up, prefer the latest substantive USER↔APRIL
        # pair from the same canonical dialogue/memory window.
        selected_user, selected_assistant, selected_source, pair_score = self._select_reference_pair(
            current,
            previous_user,
            previous_assistant,
            dialog_history,
            (dynamic_memory or {}).get("memory_timeline") if isinstance(dynamic_memory, dict) else None,
        )
        if selected_user and selected_assistant:
            previous_user, previous_assistant = selected_user, selected_assistant

        gate = self._need_memory(current, previous_user, previous_assistant, scene)

        base = {
            "version": self.VERSION,
            "engine": "QUANTUM_MEMORY_UNDERSTANDING_ENGINE",
            "decision_owner": "QUANTUM_PROCESSOR",
            "active": False,
            "needed": bool(gate["needed"]),
            "relation": "INDEPENDENT",
            "reference": {"resolved": False, "target": "", "confidence": 0.0},
            "visual_context": {},
            "dialogue_context": {
                "previous_user": previous_user,
                "previous_assistant": previous_assistant,
                "active_topic": _text(active_topic, 500),
                "active_goal": _text(active_goal, 700),
            },
            "gate": gate,
            "memory_sources": {
                "dialogue": bool(previous_user or previous_assistant),
                "visual_scene": bool(scene),
                "dynamic_memory": bool(dynamic_memory and dynamic_memory.get("matches")),
                "history": bool(dialog_history),
                "selected_pair_source": selected_source,
                "selected_pair_score": round(pair_score, 6),
            },
            "evidence": [],
            "provider_hint": {},
            "generation_strategy": "independent_request",
            "independent_safe": bool(not gate["needed"]),
            "lexical_triggers": False,
            "renderer_control": False,
            "render_signal_mutation": False,
        }
        if not current or not gate["needed"]:
            return base

        structural_items = self._structural_items(previous_assistant)
        visual_blocks = self._visual_blocks(scene)
        all_candidates = structural_items + visual_blocks

        # Pronoun/deictic references need a semantic antecedent even when the
        # previous answer contains no numbered/list structure. The candidate is
        # built from the same substantive pair, not from hard-coded topic names.
        antecedents = self._entity_candidates(previous_user, previous_assistant)
        if antecedents and (gate["structural_reference"] or gate["short_followup"]):
            for idx, name in enumerate(antecedents[:8], start=1):
                all_candidates.append({
                    "kind": "entity_reference",
                    "index": idx,
                    "title": name,
                    "content": _clip(f"{previous_user} {previous_assistant}", 1800),
                    "source": "substantive_dialogue_pair",
                })
        ordinal_targets = gate["ordinal_targets"]
        ordinal = ordinal_targets[0] if ordinal_targets else None
        relative = gate["relative_target"]

        ranked = self._candidate_scores(current, all_candidates, ordinal, relative) if all_candidates else []
        best = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        best_score = float(best["score"]) if best else 0.0
        margin = best_score - float(second["score"]) if second else best_score

        visual_text = self._scene_text(scene)
        semantic_scene, scene_source = self._semantic_score(current, [visual_text]) if visual_text else ({}, "none")
        scene_similarity = float(next(iter(semantic_scene.values()), 0.0)) if semantic_scene else 0.0
        topic_similarity = self._lexical_score(current, active_topic)

        # A structurally explicit ordinal/relative reference is stronger than
        # semantic similarity. If the previous answer contains the requested
        # ordinal item, that exact structural match is the target even when the
        # surrounding prose has many semantically similar candidates.
        structural_target = None
        if ordinal is not None:
            structural_target = next(
                (c for c in structural_items if int(c.get("index") or -999) == int(ordinal)),
                None,
            )
        if structural_target is None and relative is not None and structural_items:
            target_index = relative if relative > 0 else len(structural_items) + relative + 1
            structural_target = next(
                (c for c in structural_items if int(c.get("index") or -999) == int(target_index)),
                None,
            )

        # Explicit pronoun/deictic references ("он", "это", "этот", etc.) are
        # structural discourse links. When there is no ordinal/list target, the
        # most salient name-like entity in the selected substantive pair is the
        # antecedent; no topic-specific vocabulary is needed.
        pronoun_reference = bool(re.search(
            r"\b(?:он|она|они|его|её|ее|их|ему|ей|им|этот|эта|это|этим|этом|тот|та|то|them|he|she|they|him|her|this|that)\b",
            current,
            flags=re.I,
        ))
        visual_kind = str(gate.get("visual_reference_kind") or "")
        if structural_target is None and visual_kind and visual_blocks:
            structural_target = next(
                (
                    c for c in visual_blocks
                    if str(c.get("type") or "").lower() == visual_kind
                ),
                None,
            )

        if structural_target is None and pronoun_reference and antecedents:
            salient = sorted(
                antecedents,
                key=lambda value: (len(value.split()), len(value)),
                reverse=True,
            )[0]
            structural_target = next(
                (c for c in all_candidates if c.get("kind") == "entity_reference" and c.get("title") == salient),
                None,
            )
        numeric_result = self._previous_numeric_result(previous_assistant) if gate.get("operation_dependency") else ""
        if structural_target is None and numeric_result:
            structural_target = {
                "kind": "numeric_result",
                "index": None,
                "title": f"previous_result={numeric_result}",
                "content": f"Previous answer's numeric result: {numeric_result}",
                "source": "previous_assistant_numeric_structure",
            }

        target = deepcopy(structural_target or (best["candidate"] if best and best_score >= 0.55 else {}))
        target_kind = str(target.get("kind") or "")
        explicit_reference = bool(
            gate.get("structural_reference")
            or gate.get("pronoun_reference")
            or ordinal is not None
            or relative is not None
        )

        # Structural references are authoritative only when the referenced object
        # actually exists. Loose semantic similarity may support continuation but
        # must never fabricate a target.
        reference_resolved = bool(
            target
            and (
                structural_target is not None
                or (explicit_reference and best_score >= 0.68)
            )
        )

        # Explicitly unrelated requests must collapse to INDEPENDENT even when
        # an old scene happens to be present in state.
        semantic_continuation = bool(
            gate.get("semantic_relation")
            or gate.get("operation_dependency")
            or scene_similarity >= 0.48
            or topic_similarity >= 0.18
        )
        continuation = bool(reference_resolved or semantic_continuation)

        relation = "CONTINUE_TOPIC" if continuation else "INDEPENDENT"
        if reference_resolved:
            relation = "ARTIFACT_REFERENCE" if target_kind == "render_block" else "CONTINUE_TOPIC"

        confidence = min(1.0, max(
            best_score if reference_resolved else 0.0,
            0.58 * scene_similarity + 0.42 * topic_similarity,
        ))
        if structural_target is not None:
            confidence = max(confidence, 0.96)
        elif reference_resolved:
            confidence = max(confidence, min(1.0, 0.72 + 0.22 * best_score))
        elif gate.get("operation_dependency"):
            confidence = max(confidence, 0.84)

        # The engine itself owns the release decision. This keeps a weak
        # continuation measurement from silently contaminating the canonical
        # route. An active memory result with no resolved target is evidence only.
        authorization = bool(
            relation in {"CONTINUE_TOPIC", "ARTIFACT_REFERENCE"}
            and (
                reference_resolved
                or gate.get("semantic_relation")
                or gate.get("operation_dependency")
                or scene_similarity >= 0.48
            )
            and (
                confidence >= 0.50
                or gate.get("operation_dependency")
                or reference_resolved
            )
        )

        previous_scene_id = str(scene.get("scene_id") or "")
        visual_context = {
            "scene_id": previous_scene_id,
            "topic": _text(scene.get("topic") or active_topic, 500),
            "summary": _clip(scene.get("summary") or scene.get("april_answer") or scene.get("answer"), 1000),
            "render_block_types": list(scene.get("render_block_types") or []),
            "render_blocks": visual_blocks,
            "scene_similarity": round(scene_similarity, 6),
            "source": scene_source,
        }

        target_title = _text(target.get("title") or target.get("type") or target.get("block_id"), 300)
        resolved_request = current
        if reference_resolved:
            target_content = _clip(target.get("content") or "", 1800)
            resolved_request = (
                f"{current}\n\n"
                f"Memory understanding resolved the current reference to the previous response object.\n"
                f"Target kind: {target_kind}. Target index: {target.get('index')}. Target title: {target_title}.\n"
                f"Target content: {target_content}\n"
                f"Use this resolved context to answer the current request directly; do not ask the user to repeat the referenced item."
            )

        memory_matrix = self._build_memory_matrix(
            relation=relation if authorization else "INDEPENDENT",
            reference_resolved=reference_resolved,
            continuation=authorization,
            visual_present=bool(scene or visual_blocks),
            structural_reference=bool(ordinal is not None or relative is not None or gate.get("structural_reference") or visual_kind),
            semantic_relation=bool(gate.get("semantic_relation") or gate.get("operation_dependency")),
            history_present=bool(selected_source not in {"none", ""}),
            context_dependency=bool(authorization),
            confidence=confidence if authorization else 0.0,
            scene_similarity=scene_similarity,
            topic_similarity=topic_similarity,
            target=target_title if reference_resolved else "",
        )

        base.update({
            "active": True,
            "relation": relation,
            "continuation": bool(authorization),
            "reference": {
                "resolved": reference_resolved,
                "target": target_title if reference_resolved else "",
                "target_kind": target_kind if reference_resolved else "",
                "target_index": (
                    target.get("index")
                    if reference_resolved and target_kind not in {"entity_reference", "numeric_result"}
                    else None
                ),
                "target_id": target.get("block_id") if reference_resolved else "",
                "confidence": round(confidence, 6),
                "candidate_count": len(all_candidates),
            },
            "visual_context": visual_context,
            "dialogue_context": {
                **base["dialogue_context"],
                "scene_similarity": round(scene_similarity, 6),
                "topic_similarity": round(topic_similarity, 6),
            },
            "selected_evidence": ranked[:5],
            "resolved_request": resolved_request,
            "generation_strategy": (
                "create_new_artifact_with_continued_meaning"
                if authorization
                else "independent_request"
            ),
            "independent_safe": bool(not authorization and not semantic_continuation),
            "authorization": {
                "memory_context_authorized": authorization,
                "reason": (
                    "resolved_reference"
                    if reference_resolved
                    else "semantic_or_structural_continuation"
                    if authorization
                    else "no_reliable_relation"
                ),
            },
            "quantum_memory_matrix": memory_matrix,
            "provider_hint": {
                "context_dependency": authorization,
                "resolved_scene_id": previous_scene_id if authorization else "",
                "reference_target": target_title if reference_resolved else "",
                "reference_content": _clip(target.get("content") if reference_resolved else "", 1600),
                "resolved_request": resolved_request,
            },
            "evidence": [
                {"channel": "structure", "score": round(float(best.get("structural", 0.0)) if best else 0.0, 6)},
                {"channel": "semantic", "score": round(float(best.get("semantic", 0.0)) if best else 0.0, 6)},
                {"channel": "lexical", "score": round(float(best.get("lexical", 0.0)) if best else 0.0, 6)},
                {"channel": "visual_scene", "score": round(scene_similarity, 6)},
                {"channel": "topic", "score": round(topic_similarity, 6)},
                {"channel": "reference", "score": round(confidence if reference_resolved else 0.0, 6)},
            ],
            "collapse": {
                "relation": relation if authorization else "INDEPENDENT",
                "confidence": round(confidence, 6),
                "margin": round(margin, 6),
                "authorized": authorization,
                "target": target_title if reference_resolved else "",
                "target_kind": target_kind if reference_resolved else "",
                "scene_id": previous_scene_id if authorization else "",
            },
        })
        return base


QUANTUM_MEMORY_UNDERSTANDING_ENGINE = QuantumMemoryUnderstandingEngine()

def _build_quantum_field(
    *,
    user_id: Any,
    text: str,
    state: dict,
    context: dict,
    interpretation: dict,
    semantic: dict,
    cognition: dict,
    intent: dict,
    intent_ai: dict,
    resolver: dict,
    router: dict,
    router_system: dict,
    decision: dict,
    experience: dict,
    experience_manager: dict,
    goal: dict,
    visual_reference: dict,
    memory_understanding: dict | None = None,
) -> dict:
    """Build the one canonical evidence field for Quantum collapse."""
    return {
        "version": PROCESSOR_VERSION,
        "user_id": _s(user_id),
        "current_request": _s(text),
        "current_request_authoritative": True,
        "decision_owner": "QUANTUM_PROCESSOR",
        "identity_scope": _quantum_snapshot(state.get("memory_scope", {})),
        "single_route": True,
        "provider_calls": 0,
        "parallel_route": False,
        "sources": {
            "context_system": _quantum_snapshot(_as_dict(context)),
            "interpretation_layer": _quantum_snapshot(_as_dict(interpretation)),
            "semantic_core": _quantum_snapshot(_as_dict(semantic)),
            "cognitive_core": _quantum_snapshot(_as_dict(cognition)),
            "intent_system": _quantum_snapshot(_as_dict(intent)),
            "intent_ai": _quantum_snapshot(_as_dict(intent_ai)),
            "intent_resolver": _quantum_snapshot(_as_dict(resolver)),
            "router": _quantum_snapshot(_as_dict(router)),
            "router_system": _quantum_snapshot(_as_dict(router_system)),
            "response_decision": _quantum_snapshot(_as_dict(decision)),
            "experience": _quantum_snapshot(_as_dict(experience)),
            "experience_manager": _quantum_snapshot(_as_dict(experience_manager)),
            "goal_engine": _quantum_snapshot(_as_dict(goal)),
            "visual_reference_system": _quantum_snapshot(_as_dict(visual_reference)),
            "quantum_memory_understanding": _quantum_snapshot(_as_dict(memory_understanding)),
        },
        "evidence_channels": 15,
        "representations": _unique_strings(
            _as_list(semantic.get("required_representations"))
            + _as_list(interpretation.get("required_representations"))
            + _as_list(intent.get("renderer_subtype"))
            + _as_list(decision.get("required_representations"))
        ),
        "candidate_signals": _quantum_snapshot(
            _as_list(intent.get("candidate_signals"))
            + _as_list(intent_ai.get("quantum_evidence", {}).get("candidates"))
            + _as_list(router.get("quantum_evidence", {}).get("signals"))
            + _as_list(router_system.get("candidate_signals"))
        ),
        "semantic_engines": {
            "dialogue": _quantum_snapshot(
                semantic.get("quantum_dialogue_measurement", {})
            ),
            "representation": _quantum_snapshot(
                semantic.get("quantum_representation_measurement", {})
            ),
            "representation_candidates": _quantum_snapshot(
                semantic.get("quantum_representation_candidates", [])
            ),
            "decision_owner": "QUANTUM_PROCESSOR",
            "word_trigger_routing": False,
            "fallback_semantics": False,
        },
        "trajectory": _quantum_snapshot({
            "resolver": _as_dict(resolver),
            "active_flow": _as_dict(state.get("active_flow")),
            "context": _as_dict(context.get("quantum_evidence")),
        }),
        "arbitration": {
            "dialogue": "processor",
            "representation": "processor",
            "room": "delegated",
            "renderer": "delegated",
            "execution": "delegated",
        },
    }

def _field(sources: tuple[dict, ...], names: tuple[str, ...]) -> Any:
    for src in sources:
        if not isinstance(src, dict):
            continue
        for name in names:
            if src.get(name) not in (None, "", [], {}):
                return src[name]
    return ""



def _scene_continuity_engine(
    *,
    text: str,
    state: dict,
    history: list,
) -> dict:
    """
    Canonical immediate-scene interpretation engine.

    It does not inspect words or maintain a trigger list. It feeds the existing
    QUANTUM_DIALOGUE_ENGINE with the most recent canonical USER↔APRIL scene
    when the hot dialog list is empty or incomplete. The engine's own semantic
    dialogue label remains the sole authority for continuation/reference state.

    This repairs the exact failure where current_visual_scene existed, but the
    Executor discarded it because state["dialog"] was empty.
    """
    current_scene = {}
    if isinstance(state, dict):
        candidate = (
            state.get("current_visual_scene")
            or state.get("active_visual_scene")
            or state.get("active_scene_contract")
        )
        if isinstance(candidate, dict) and is_dialogue_visible_scene(candidate):
            current_scene = candidate

    previous_user = ""
    previous_april = ""
    active_topic = ""
    active_goal = ""
    scene_id = ""

    # Human dialogue is the primary continuity anchor. Visual scene state is
    # evidence, not a replacement for the last human USER↔APRIL pair.
    if isinstance(history, list):
        for item in reversed(history):
            if not isinstance(item, dict):
                continue
            role = _s(item.get("role")).lower()
            if not previous_april and role in {"assistant", "april"}:
                previous_april = _s(item.get("content") or item.get("answer") or item.get("summary"))
            if not previous_user and role == "user":
                previous_user = _s(item.get("content"))
            if previous_user and previous_april:
                break

    if current_scene:
        if not previous_user:
            previous_user = _s(
                current_scene.get("user_request")
                or current_scene.get("current_request")
                or current_scene.get("user")
            )
        if not previous_april:
            previous_april = _s(
                current_scene.get("april_answer")
                or current_scene.get("answer")
                or current_scene.get("content")
                or current_scene.get("summary")
            )
        active_topic = _s(
            current_scene.get("topic")
            or current_scene.get("active_topic")
            or previous_user
        )
        active_goal = _s(
            current_scene.get("active_goal")
            or current_scene.get("goal")
            or current_scene.get("resolved_request")
        )
        scene_id = _s(current_scene.get("scene_id") or current_scene.get("id"))

    measured: dict[str, Any] = {}
    if previous_april:
        try:
            measured = QUANTUM_DIALOGUE_ENGINE.dialogue(
                text,
                previous_assistant=previous_april,
                previous_user=previous_user,
                active_goal=active_goal,
                active_topic=active_topic,
            ) or {}
        except Exception:
            measured = {}

    dialogue = _as_dict(measured.get("dialogue"))
    label = _s(dialogue.get("label")).lower()

    # Only the existing dialogue engine label is interpreted here.
    # No lexical triggers, local thresholds, or word maps are introduced.
    label_to_state = {
        "continuation": ("CONTINUATION", True, True),
        "reformulation": ("CONTINUATION", True, True),
        "correction": ("CONTINUATION", True, True),
        "reference": ("ARTIFACT_REFERENCE", True, True),
        "affirmation": ("SAME_TOPIC", True, False),
        "rejection": ("SAME_TOPIC", True, False),
        "memory_query": ("MEMORY_QUERY", True, False),
        "new_topic": ("NEW_TOPIC", False, False),
        "independent": ("INDEPENDENT", False, False),
    }
    mode, continuation, reference = label_to_state.get(
        label, ("INDEPENDENT", False, False)
    )

    return {
        "engine": "quantum_scene_continuity_engine",
        "decision_owner": "QUANTUM_PROCESSOR",
        "canonical": True,
        "scene_id": scene_id,
        "previous_user": previous_user,
        "previous_april": previous_april,
        "active_topic": active_topic,
        "active_goal": active_goal,
        "dialogue_measurement": _quantum_snapshot(measured),
        "dialogue_label": label,
        "mode": mode,
        "continuation": continuation,
        "reference_to_previous": reference,
        "history_available": bool(history),
        "hot_scene_available": bool(current_scene),
        "source": "QUANTUM_DIALOGUE_ENGINE",
        "lexical_triggers": False,
        "score_routing": False,
    }


def _dialogue_evidence(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    state: dict,
) -> dict:
    """Collapse dialogue evidence to one state using the existing dialogue engine.

    The Executor does not use lexical triggers or local thresholds. The canonical
    immediate-scene continuity measurement is produced by QUANTUM_DIALOGUE_ENGINE
    and merged with the Interpretation dialogue contract.
    """
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    previous_user = ""
    previous_april = ""
    last_turn_id = None

    for item in reversed(dialog):
        if not isinstance(item, dict):
            continue
        role = _s(item.get("role")).lower()
        if not previous_april:
            if role in {"assistant", "april"}:
                previous_april = _s(item.get("content") or item.get("answer"))
                last_turn_id = item.get("turn_id")
            elif isinstance(item.get("april"), dict):
                previous_april = _s(
                    item["april"].get("answer")
                    or item["april"].get("content")
                )
                last_turn_id = item.get("turn_id")
        if not previous_user:
            if role == "user":
                previous_user = _s(item.get("content"))
            elif item.get("user"):
                previous_user = _s(item.get("user"))
        if previous_user and previous_april:
            break

    scene_continuity = _as_dict(
        semantic.get("quantum_scene_continuity")
    )
    if not scene_continuity:
        scene_continuity = _scene_continuity_engine(
            text=text,
            state=state,
            history=dialog,
        )

    if not previous_user:
        previous_user = _s(scene_continuity.get("previous_user"))
    if not previous_april:
        previous_april = _s(scene_continuity.get("previous_april"))
    if not last_turn_id:
        last_turn_id = _as_dict(state.get("current_visual_scene")).get("turn_id")

    interpretation_packet = _as_dict(semantic.get("quantum_interpretation_evidence"))
    dialogue_contract = _as_dict(interpretation_packet.get("dialogue_contract"))
    if not dialogue_contract:
        dialogue_contract = _as_dict(semantic.get("dialogue_context_field"))

    # Continuity engine is an evidence source. If Interpretation already emitted
    # an explicit dialogue state, that explicit structured state remains primary.
    mode = _s(
        dialogue_contract.get("context_mode")
        or dialogue_contract.get("dialogue_state")
        or semantic.get("dialogue_state")
        or decision.get("dialogue_state")
    ).upper()

    if mode not in {
        "INDEPENDENT",
        "NEW_TOPIC",
        "SAME_TOPIC",
        "CONTINUATION",
        "ARTIFACT_REFERENCE",
        "MEMORY_QUERY",
    }:
        mode = ""

    if not mode:
        mode = _s(scene_continuity.get("mode")).upper() or "INDEPENDENT"

    active_topic = _s(
        dialogue_contract.get("active_topic")
        or semantic.get("active_topic")
        or decision.get("active_topic")
        or scene_continuity.get("active_topic")
        or state.get("active_topic")
        or state.get("topic")
        or previous_user
    )
    active_goal = _s(
        dialogue_contract.get("active_goal")
        or semantic.get("active_goal")
        or cognition.get("active_goal")
        or decision.get("active_goal")
        or scene_continuity.get("active_goal")
        or state.get("active_goal")
    )

    explicit_dependency = _s(dialogue_contract.get("context_dependency")).lower()
    context_dependency = explicit_dependency not in {"", "independent", "none", "false", "0"}
    continuation = bool(
        dialogue_contract.get("continuation")
        if dialogue_contract.get("continuation") is not None
        else scene_continuity.get("continuation")
    )
    reference_to_previous = bool(
        dialogue_contract.get("reference_to_previous")
        if dialogue_contract.get("reference_to_previous") is not None
        else scene_continuity.get("reference_to_previous")
    )

    # Structured continuity evidence can promote the state when the canonical
    # Interpretation packet did not emit a full contract.
    if not explicit_dependency:
        context_dependency = bool(
            continuation
            or reference_to_previous
            or mode in {"CONTINUATION", "ARTIFACT_REFERENCE", "SAME_TOPIC", "MEMORY_QUERY"}
        )

    resolved_scene = _as_dict(dialogue_contract.get("resolved_scene"))
    if not resolved_scene and scene_continuity.get("scene_id"):
        resolved_scene = {
            "scene_id": _s(scene_continuity.get("scene_id")),
            "relation": (
                "current_scene"
                if continuation or reference_to_previous
                else "same_topic"
                if mode == "SAME_TOPIC"
                else "new_topic"
                if mode == "NEW_TOPIC"
                else "independent"
            ),
            "source": "quantum_scene_continuity_engine",
        }

    dialog_act = _s(
        dialogue_contract.get("dialog_act")
        or scene_continuity.get("dialogue_label")
        or semantic.get("dialog_act")
        or decision.get("dialog_act")
        or "statement"
    )

    return {
        "mode": mode,
        "previous_user": previous_user,
        "previous_april": previous_april,
        "last_turn_id": last_turn_id,
        "active_topic": active_topic,
        "active_goal": active_goal,
        "context_dependency": context_dependency,
        "continuation": continuation,
        "reference_to_previous": reference_to_previous,
        "dialog_act": dialog_act,
        "reply_to": _s(
            dialogue_contract.get("reply_to")
            or dialogue_contract.get("previous_turn_id")
        ),
        "scene_continuity": scene_continuity,
        "source": "QUANTUM_DIALOGUE_ENGINE",
    }


def _collapse_dialogue(e: dict[str, Any]) -> tuple[str, dict[str, float], float]:
    """Compatibility bridge: no local score collapse; semantic engines own the state."""
    mode = _s(e.get("mode")).upper() or "INDEPENDENT"
    states = {
        "INDEPENDENT": 1.0 if mode == "INDEPENDENT" else 0.0,
        "NEW_TOPIC": 1.0 if mode == "NEW_TOPIC" else 0.0,
        "SAME_TOPIC": 1.0 if mode == "SAME_TOPIC" else 0.0,
        "CONTINUATION": 1.0 if mode == "CONTINUATION" else 0.0,
        "ARTIFACT_REFERENCE": 1.0 if mode == "ARTIFACT_REFERENCE" else 0.0,
        "MEMORY_QUERY": 1.0 if mode == "MEMORY_QUERY" else 0.0,
    }
    return mode, states, 1.0


def _representation_constraints(*sources: dict) -> dict:
    """Merge explicit representation constraints without local scoring or triggers."""
    positive: list[str] = []
    negative: list[str] = []

    for src in sources:
        if not isinstance(src, dict):
            continue
        constraints = src.get("representation_constraints")
        if isinstance(constraints, dict):
            for key, target in (("positive", positive), ("negative", negative)):
                values = constraints.get(key) or []
                if isinstance(values, str):
                    values = [values]
                for value in values:
                    name = _s(value).lower()
                    if name and name not in target:
                        target.append(name)

        preferred = _s(src.get("preferred_representation")).lower()
        if preferred and preferred not in positive:
            positive.append(preferred)

        authority = _s(src.get("representation_authority")).lower()
        if authority and authority not in {"", "adaptive"} and authority not in positive:
            positive.append(authority)

    blocked = set(negative)
    positive = [item for item in positive if item not in blocked]

    return {
        "positive": positive,
        "negative": negative,
        "blocked": sorted(blocked),
        "current_request_authoritative": True,
    }

def _representation_audit(
    requested_outputs: list[str],
    measured_output: str,
    constraints: dict,
) -> dict:
    requested = list(dict.fromkeys(requested_outputs or []))
    blocked = set(constraints.get("negative", []) or [])
    return {
        "requested_outputs": requested,
        "preferred_representation": measured_output,
        "blocked_outputs": sorted(blocked),
        "multi_output": len(requested) > 1,
        "table_requested": "table" in requested,
        "graph_requested": "graph" in requested,
        "code_requested": "code" in requested,
        "representation_gap": bool(requested and not set(requested).issubset(blocked | set(requested))),
        "canonical": True,
    }


def _structural_request_signals(text: str) -> dict:
    """Measure syntax-level representation evidence; no lexical trigger map."""
    source = _s(text)
    urls = re.findall(r"https?://[^\s)\]}>,]+", source, flags=re.I)
    markdown_links = re.findall(r"\[[^\]]+\]\(https?://[^)]+\)", source, flags=re.I)
    code_fences = bool(re.search(r"```[\s\S]*?```", source))
    table_rows = len(re.findall(r"(?m)^\s*\|.+\|\s*$", source))
    return {
        "url_count": len(urls),
        "markdown_link_count": len(markdown_links),
        "code_fence": code_fences,
        "table_row_count": table_rows,
        "link_signal": bool(urls or markdown_links),
        "code_signal": code_fences,
        "table_signal": table_rows >= 2,
    }

def _requested_outputs(text: str, semantic: dict, cognition: dict, decision: dict, *, independent_turn: bool = False) -> list[str]:
    """Collapse explicit semantic and structural evidence into one output plan."""
    constraints = _representation_constraints(semantic, cognition, decision)
    blocked = set(constraints["negative"])
    names: list[str] = []
    aliases = {"markdown": "text", "renderer_scene": "diagram", "visual": "graph", "image_generate": "image", "plot": "graph", "chart": "graph"}

    def add(value: Any) -> None:
        values = [value] if isinstance(value, str) else list(value) if isinstance(value, (list, tuple, set)) else []
        for raw in values:
            name = aliases.get(_s(raw).lower(), _s(raw).lower())
            if name and name not in blocked and name not in names:
                names.append(name)

    for src in (decision, semantic):
        if isinstance(src, dict):
            add(src.get("requested_outputs"))
            add(src.get("required_outputs"))
    add(constraints["positive"])
    if not names:
        for src in (semantic, cognition, decision):
            if not isinstance(src, dict):
                continue
            for key in ("required_representations", "requested_representations", "candidate_representations", "artifact_types", "render_types", "representations", "renderer_subtype"):
                add(src.get(key))
            add(src.get("preferred_representation"))

    structural = _structural_request_signals(text)
    if structural["link_signal"] and "link" not in blocked and "link" not in names:
        names.append("link")
    if structural["code_signal"] and "code" not in blocked and "code" not in names:
        names.append("code")
    if structural["table_signal"] and "table" not in blocked and "table" not in names:
        names.append("table")
    return names or ["text"]


def _representation_consensus(outputs: list[str], semantic: dict, decision: dict) -> tuple[str, dict[str, Any]]:
    plan = list(dict.fromkeys(outputs or ["text"]))
    preferred = _s(decision.get("preferred_representation") or semantic.get("preferred_representation") or (plan[0] if plan else "text")).lower()
    if preferred not in plan:
        preferred = plan[0] if plan else "text"
    return preferred, {"outputs": plan, "preferred": preferred, "selection_method": "declared_plus_structural_measurement", "scoring": False, "triggers": False}

def _representation_consensus(
    outputs: list[str],
    semantic: dict,
    decision: dict,
) -> tuple[str, dict[str, Any]]:
    """Select the declared preferred representation without local scoring."""
    plan = list(dict.fromkeys(outputs or ["text"]))
    preferred = _s(
        decision.get("preferred_representation")
        or semantic.get("preferred_representation")
        or (plan[0] if plan else "text")
    ).lower()
    if preferred not in plan:
        preferred = plan[0] if plan else "text"

    return preferred, {
        "outputs": plan,
        "preferred": preferred,
        "selection_method": "declared_semantic_plan",
        "scoring": False,
        "triggers": False,
    }


def _complexity(
    semantic: dict,
    cognition: dict,
    decision: dict,
    text: str,
) -> str:
    """Carry the semantic complexity declaration without local score tiers."""
    explicit = _s(
        semantic.get("response_complexity")
        or cognition.get("response_complexity")
        or decision.get("response_complexity")
    ).upper()
    return explicit if explicit in {"LOW", "MEDIUM", "HIGH"} else "ADAPTIVE"

def _quantum_64_field(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
) -> dict:
    """Build a 64-lane structural measurement field without score weighting or triggers."""
    outputs = list(dict.fromkeys(
        _as_list(
            semantic.get("requested_outputs")
            or semantic.get("required_outputs")
            or decision.get("requested_outputs")
        )
    ))
    artifacts = _as_list(
        semantic.get("required_artifacts")
        or decision.get("required_artifacts")
    )
    domains = _as_list(
        semantic.get("required_domains")
        or semantic.get("required_competencies")
        or cognition.get("required_domains")
    )
    parts = max(1, len(
        semantic.get("task_parts")
        or semantic.get("subtasks")
        or semantic.get("requested_tasks")
        or []
    ))
    word_count = len(_tokens(text))

    field = {
        "meaning": {
            "request_length": word_count,
            "has_context": bool(semantic.get("active_topic") or semantic.get("context")),
            "has_goal": bool(semantic.get("active_goal") or decision.get("active_goal")),
            "semantic_state": _s(semantic.get("dialogue_state") or semantic.get("dialog_act")),
            "declared_complexity": _complexity(semantic, cognition, decision, text),
            "measured": True,
            "source": "semantic_engines",
            "scoring": False,
            "triggering": False,
        },
        "intent": {
            "intent": _s(semantic.get("intent") or decision.get("intent")),
            "dialogue_state": _s(semantic.get("dialogue_state")),
            "dialog_act": _s(semantic.get("dialog_act") or decision.get("dialog_act")),
            "goal_present": bool(decision.get("active_goal") or semantic.get("active_goal")),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "context": {
            "history_present": bool(semantic.get("history_present")),
            "continuation": bool(semantic.get("continuation")),
            "reference_to_previous": bool(semantic.get("reference_to_previous")),
            "context_dependency": bool(semantic.get("context_dependency")),
            "topic": _s(semantic.get("active_topic") or decision.get("active_topic")),
            "goal": _s(semantic.get("active_goal") or decision.get("active_goal")),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "structure": {
            "requested_outputs": outputs,
            "artifact_types": list(dict.fromkeys(map(_s, artifacts))),
            "domains": list(dict.fromkeys(map(_s, domains))),
            "task_parts": parts,
            "word_count": word_count,
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "evidence": {
            "semantic_evidence_present": bool(semantic),
            "cognition_evidence_present": bool(cognition),
            "decision_evidence_present": bool(decision),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "representation": {
            "requested_outputs": outputs or ["text"],
            "preferred": _s(
                decision.get("preferred_representation")
                or semantic.get("preferred_representation")
                or "text"
            ),
            "constraints": _representation_constraints(semantic, cognition, decision),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "economy": {
            "input_text_chars": len(text),
            "word_count": word_count,
            "requested_output_count": len(outputs),
            "artifact_count": len(artifacts),
            "domain_count": len(domains),
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
        "completion": {
            "requested_output_count": len(outputs),
            "artifact_count": len(artifacts),
            "task_parts": parts,
            "measured": True,
            "scoring": False,
            "triggering": False,
        },
    }

    return {
        "cores": field,
        "core_count": QUANTUM_CORE_COUNT,
        "lane_count": QUANTUM_LANE_COUNT,
        "signal_count": QUANTUM_CORE_COUNT * QUANTUM_LANE_COUNT,
        "measurement_mode": "structural_no_trigger_no_score",
        "request_word_count": word_count,
        "requested_output_count": len(outputs),
        "artifact_count": len(artifacts),
        "domain_count": len(domains),
        "task_parts": parts,
        "scoring": False,
        "triggering": False,
    }


def _representation_budget_profile(kind: str) -> dict:
    """Canonical output-shape budget for every Web-facing representation."""
    profiles = {
        "text": {"base": 420, "block": 320, "payload": 0},
        "formula": {"base": 980, "block": 620, "payload": 900},
        "table": {"base": 900, "block": 760, "payload": 1100},
        "graph": {"base": 1200, "block": 900, "payload": 1500},
        "diagram": {"base": 1500, "block": 980, "payload": 1900},
        "link": {"base": 700, "block": 520, "payload": 700},
        "code": {"base": 1100, "block": 700, "payload": 1300},
        "gallery": {"base": 1200, "block": 720, "payload": 1600},
        "image": {"base": 1200, "block": 720, "payload": 1600},
        "audio": {"base": 900, "block": 620, "payload": 1100},
        "video": {"base": 1100, "block": 700, "payload": 1300},
        "file": {"base": 900, "block": 620, "payload": 1100},
        "action": {"base": 900, "block": 620, "payload": 1100},
        "memory": {"base": 800, "block": 540, "payload": 900},
        "scene": {"base": 1500, "block": 980, "payload": 1900},
    }
    return profiles.get(kind, profiles["text"])


def _quantum_budget_from_64(field: dict, *, minimum: int = OUTPUT_MIN_TOKENS, maximum: int = OUTPUT_MAX_TOKENS) -> int:
    """Representation-aware Provider capacity. Never budgets structured output as plain text."""
    cores = field.get("cores", {}) if isinstance(field, dict) else {}
    economy = cores.get("economy", {}) if isinstance(cores, dict) else {}
    structure = cores.get("structure", {}) if isinstance(cores, dict) else {}
    word_count = max(1, int(economy.get("word_count", field.get("request_word_count", 1)) or 1))
    output_count = max(1, int(economy.get("requested_output_count", field.get("requested_output_count", 1)) or 1))
    artifact_count = max(0, int(economy.get("artifact_count", field.get("artifact_count", 0)) or 0))
    domain_count = max(0, int(economy.get("domain_count", field.get("domain_count", 0)) or 0))
    parts = max(1, int(structure.get("task_parts", field.get("task_parts", 1)) or 1))
    outputs = [_s(x).lower() for x in _as_list(structure.get("requested_outputs")) if _s(x)] or ["text"]
    answer_capacity = 160 + min(1500, word_count * 8) + min(1600, parts * 220)
    structural_capacity = 0
    for kind in dict.fromkeys(outputs):
        profile = _representation_budget_profile(kind)
        structural_capacity += profile["base"] + profile["block"] + profile["payload"]
    envelope = 950 + output_count * 180 + artifact_count * 260 + domain_count * 90
    reserve = 420
    return int(max(minimum, min(maximum, answer_capacity + structural_capacity + envelope + reserve)))


def _adaptive_output_budget(text: str, semantic: dict, cognition: dict, decision: dict) -> int:
    """Continuous structural capacity with representation-specific envelopes."""
    return _quantum_budget_from_64(_quantum_64_field(text, semantic, cognition, decision))

def _compact_context(text: str, state: dict, mode: str, topic: str, goal: str) -> dict:
    dialog = state.get("dialog", []) if isinstance(state, dict) else []
    recent = []
    for turn in dialog[-8:]:
        if not isinstance(turn, dict):
            continue
        role = _s(turn.get("role")).lower()
        if role == "user":
            recent.append({
                "user": _clip(turn.get("content"), 450),
                "april": "",
            })
        elif role in {"assistant", "april"}:
            recent.append({
                "user": "",
                "april": _clip(
                    turn.get("content")
                    or turn.get("answer")
                    or turn.get("summary"),
                    700,
                ),
            })
        else:
            recent.append({
                "user": _clip(turn.get("user"), 450),
                "april": _clip(
                    (turn.get("april") or {}).get("answer")
                    if isinstance(turn.get("april"), dict)
                    else turn.get("april") or turn.get("content", ""),
                    700,
                ),
            })
    data = {"current_request": text, "context_mode": mode}
    if mode != "INDEPENDENT":
        if topic: data["active_topic"] = _clip(topic, 300)
        if goal: data["active_goal"] = _clip(goal, 500)
        data["recent_dialogue"] = recent
    if mode == "ARTIFACT_REFERENCE":
        visual = None
        if isinstance(state.get("active_scene_contract"), dict):
            visual = state.get("active_scene_contract")
        if not visual:
            visual = state.get("active_visual_scene") or state.get("visual_summary")
        if visual:
            data["visual_context"] = _clip(visual, 900)
    return data



def _build_processor_control_plane(
    *,
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    state: dict,
    dynamic_memory: dict | None = None,
    memory_understanding: dict | None = None,
) -> dict:
    """
    Build ONE authoritative post-interpretation control plane.

    Authority:
      dialogue/context -> canonical Interpretation dialogue_contract
      representation   -> current semantic/decision plan
      capabilities     -> semantic/cognition union
      memory           -> already queried dynamic memory
      presentation     -> produced only after Provider response

    Other engines contribute evidence; this function collapses their compatible
    signals into one executable state. It does not invent a second route,
    trigger map, or score-based arbitration.
    """
    evidence = _dialogue_evidence(text, semantic, cognition, decision, state)
    interpretation_packet = _as_dict(semantic.get("quantum_interpretation_evidence"))

    # Quantum memory-understanding is the authoritative post-interpretation
    # reference layer. It may override a stale legacy dialogue classification,
    # but it never changes the representation/rendering route.
    memory_packet = _as_dict(memory_understanding)
    memory_reference = _as_dict(memory_packet.get("reference"))
    memory_dialogue = _as_dict(memory_packet.get("dialogue_context"))
    memory_scene = _as_dict(memory_packet.get("visual_context"))
    memory_resolved_request = _s(memory_packet.get("resolved_request"))
    memory_active = bool(memory_packet.get("active"))
    memory_continuation = bool(memory_packet.get("continuation"))
    memory_resolved = bool(memory_reference.get("resolved"))
    canonical_dialogue = _as_dict(
        interpretation_packet.get("dialogue_contract")
        or semantic.get("dialogue_context_field")
    )

    mode = _s(evidence.get("mode")).upper() or "INDEPENDENT"
    continuation = bool(evidence.get("continuation"))
    reference_to_previous = bool(evidence.get("reference_to_previous"))
    context_dependency = bool(evidence.get("context_dependency"))

    memory_authorized = bool(
        _as_dict(memory_packet.get("authorization")).get("memory_context_authorized")
        or _as_dict(memory_packet.get("collapse")).get("authorized")
    )

    if memory_active and memory_authorized:
        continuation = True
        reference_to_previous = bool(memory_resolved)
        context_dependency = True
        mode = "ARTIFACT_REFERENCE" if str(memory_reference.get("target_kind") or "") == "render_block" else "CONTINUATION"
        evidence = {
            **evidence,
            "mode": mode,
            "continuation": True,
            "reference_to_previous": reference_to_previous,
            "context_dependency": True,
            "previous_user": _s(memory_dialogue.get("previous_user")) or _s(evidence.get("previous_user")),
            "previous_april": _s(memory_dialogue.get("previous_assistant")) or _s(evidence.get("previous_april")),
        }
    elif memory_active and not memory_authorized:
        # Explicitly prevent a weak/irrelevant memory result from overriding
        # the canonical dialogue measurement.
        memory_relation = _s(memory_packet.get("relation")).upper()
        if memory_relation in {"INDEPENDENT", "NEW_TOPIC"}:
            continuation = False
            reference_to_previous = False
            context_dependency = False
            mode = "INDEPENDENT" if memory_relation == "INDEPENDENT" else "NEW_TOPIC"
    elif not bool(memory_packet.get("needed")):
        # The memory engine has positively determined that this turn has no
        # reliable dependency on prior dialogue/visual state. This blocks a
        # stale legacy CONTINUE_TOPIC classification from crossing the collapse.
        continuation = False
        reference_to_previous = False
        context_dependency = False
        mode = "INDEPENDENT"

    resolved_scene = _as_dict(canonical_dialogue.get("resolved_scene"))
    if memory_active and memory_scene.get("scene_id"):
        resolved_scene = {
            **resolved_scene,
            "scene_id": _s(memory_scene.get("scene_id")),
            "relation": "current_scene" if continuation else "independent",
            "source": "QUANTUM_MEMORY_UNDERSTANDING_ENGINE",
        }
    relation = _s(resolved_scene.get("relation"))
    if not relation:
        relation = (
            "current_scene"
            if continuation or reference_to_previous
            else "new_topic"
            if mode == "NEW_TOPIC"
            else "independent"
        )

    outputs = _requested_outputs(
        text,
        semantic,
        cognition,
        decision,
        independent_turn=(mode == "INDEPENDENT"),
    )
    preferred, representation_state = _representation_consensus(
        outputs, semantic, decision
    )
    constraints = _representation_constraints(semantic, cognition, decision)

    topic = _s(
        memory_reference.get("target")
        or memory_dialogue.get("active_topic")
        or canonical_dialogue.get("active_topic")
        or _field((semantic, decision, state), ("active_topic", "topic", "current_topic"))
    )
    goal = _s(
        memory_resolved_request
        or memory_dialogue.get("active_goal")
        or canonical_dialogue.get("active_goal")
        or _field((decision, cognition, semantic), ("active_goal", "resolved_request", "goal"))
    ) or text

    capabilities: list[str] = []
    for source in (semantic, cognition):
        for key in ("required_capabilities", "required_domains", "available_tools"):
            values = source.get(key, []) if isinstance(source, dict) else []
            for value in _as_list(values):
                value = _s(value)
                if value and value not in capabilities:
                    capabilities.append(value)

    control = {
        "version": "QUANTUM_CONTROL_PLANE_V1",
        "authority": {
            "dialogue": "interpretation",
            "representation": "semantic_decision",
            "capabilities": "semantic_cognition",
            "memory": "state_manager",
            "production": "executor_specialized_engines",
            "presentation": "executor_presentation_matrix",
            "rendering": "april_web",
        },
        "mode": mode,
        "relation": relation,
        "continuation": continuation,
        "reference_to_previous": reference_to_previous,
        "context_dependency": context_dependency,
        "resolved_scene": resolved_scene,
        "active_topic": topic,
        "active_goal": goal,
        "dialogue_evidence": evidence,
        "requested_outputs": outputs,
        "preferred_representation": preferred,
        "representation_state": representation_state,
        "representation_constraints": constraints,
        "capabilities": capabilities[:12],
        "dynamic_memory": dynamic_memory if isinstance(dynamic_memory, dict) else {},
        "memory_understanding": _quantum_snapshot(memory_understanding or {}),
        "resolved_request": memory_resolved_request,
        "resolved_reference": _quantum_snapshot(memory_reference),
        "single_route": True,
        "provider_calls": 1,
        "triggers": False,
        "score_routing": False,
    }

    state["_quantum_control_plane"] = _quantum_snapshot(control)
    semantic["quantum_control_plane"] = _quantum_snapshot(control)
    return control


def _make_request(
    text: str,
    semantic: dict,
    cognition: dict,
    decision: dict,
    state: dict,
    visual: dict,
    control: dict | None = None,
) -> MachineRequest:
    """Create the single canonical MachineRequest from the processor control plane."""
    scope = _user_scope(state, state.get("_request_user_id") or state.get("user_id"))
    control = control or _build_processor_control_plane(
        text=text,
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        dynamic_memory=_as_dict(semantic.get("quantum_dynamic_memory_evidence")),
    )

    evidence = _as_dict(control.get("dialogue_evidence"))
    mode = _s(control.get("mode")).upper() or "INDEPENDENT"
    dialogue_state = {
        name: 1.0 if mode == name else 0.0
        for name in (
            "INDEPENDENT",
            "NEW_TOPIC",
            "SAME_TOPIC",
            "CONTINUATION",
            "ARTIFACT_REFERENCE",
            "MEMORY_QUERY",
        )
    }
    coherence = 1.0

    dialogue_contract_source = _as_dict(
        _as_dict(semantic.get("quantum_interpretation_evidence")).get("dialogue_contract")
    )
    dialogue_contract = {
        "dialog_act": _s(
            dialogue_contract_source.get("dialog_act")
            or _field((semantic, decision, cognition), ("dialog_act", "dialogue_act"))
        ) or "statement",
        "continuation": bool(control.get("continuation")),
        "reference_to_previous": bool(control.get("reference_to_previous")),
        "context_dependency": (
            _s(dialogue_contract_source.get("context_dependency"))
            or ("continuation" if mode == "CONTINUATION"
                else "reference" if mode == "ARTIFACT_REFERENCE"
                else "independent" if mode == "INDEPENDENT"
                else "topic")
        ),
        "reply_to": _s(
            _field((dialogue_contract_source, semantic, decision), ("reply_to", "previous_turn_id"))
        ),
        "previous_user_turn": _s(
            dialogue_contract_source.get("previous_user_turn")
            or dialogue_evidence.get("previous_user")
        ),
        "previous_april_turn": _s(
            dialogue_contract_source.get("previous_april_turn")
            or dialogue_evidence.get("previous_april")
        ),
        "active_goal": _s(dialogue_contract_source.get("active_goal"))
            or _s(control.get("active_goal")),
        "active_topic": _s(dialogue_contract_source.get("active_topic"))
            or _s(control.get("active_topic")),
        "resolved_scene": _as_dict(dialogue_contract_source.get("resolved_scene")),
        "current_request": _s(text),
    }

    memory_packet = _as_dict(control.get("memory_understanding"))
    memory_reference = _as_dict(memory_packet.get("reference"))
    memory_dialogue = _as_dict(memory_packet.get("dialogue_context"))
    memory_resolved_request = _s(control.get("resolved_request") or memory_packet.get("resolved_request"))
    if bool(memory_packet.get("active")) and (bool(memory_packet.get("continuation")) or bool(memory_reference.get("resolved"))):
        dialogue_contract.update({
            "continuation": True,
            "reference_to_previous": bool(memory_reference.get("resolved")),
            "context_dependency": "continuation" if not memory_reference.get("resolved") else "reference",
            "previous_user_turn": _s(memory_dialogue.get("previous_user")) or _s(dialogue_contract.get("previous_user_turn")),
            "previous_april_turn": _s(memory_dialogue.get("previous_assistant")) or _s(dialogue_contract.get("previous_april_turn")),
            "active_topic": _s(memory_reference.get("target")) or _s(dialogue_contract.get("active_topic")),
            "resolved_request": memory_resolved_request or _s(dialogue_contract.get("current_request")),
            "resolved_scene": _as_dict(control.get("resolved_scene")) or _as_dict(dialogue_contract.get("resolved_scene")),
        })

    context = _compact_context(
        text,
        state,
        mode,
        _s(control.get("active_topic")),
        _s(control.get("active_goal")),
    )

    # The immediate canonical scene is part of the same dialogue state. When
    # hot history is absent, carry the measured previous scene through the
    # existing conversation contract instead of creating a second memory path.
    dialogue_evidence = _as_dict(control.get("dialogue_evidence"))
    previous_scene_user = _s(dialogue_evidence.get("previous_user"))
    previous_scene_april = _s(dialogue_evidence.get("previous_april"))
    if mode in {"CONTINUATION", "SAME_TOPIC", "ARTIFACT_REFERENCE", "MEMORY_QUERY"}:
        recent = list(context.get("recent_dialogue", []) or [])
        if previous_scene_user or previous_scene_april:
            recent.insert(0, {
                "user": _clip(previous_scene_user, 700),
                "april": _clip(previous_scene_april, 1000),
                "source": "current_visual_scene",
            })
        context["recent_dialogue"] = recent[-8:]

    dynamic_memory_evidence = _as_dict(control.get("dynamic_memory"))
    complexity = _complexity(semantic, cognition, decision, text)
    quantum_budget_field = _quantum_64_field(text, semantic, cognition, decision)
    response_budget = _quantum_budget_from_64(quantum_budget_field)

    representation_constraints = _as_dict(control.get("representation_constraints"))
    requested_outputs = list(control.get("requested_outputs") or ["text"])
    measured_output = _s(control.get("preferred_representation")) or "text"

    representation_audit = _representation_audit(
        requested_outputs=requested_outputs,
        measured_output=measured_output,
        constraints=representation_constraints,
    )

    # Explicit mathematical turns get a structured presentation policy. This is
    # not a routing trigger; it is a downstream rendering contract for the
    # Quantum Math Engine.
    presentation_plan = {
        "version": "quantum_presentation_plan_v2",
        "math_mode": (
            "explicit_math"
            if measured_output in {"formula", "math"} or "formula" in requested_outputs or "math" in requested_outputs
            else "structural"
        ),
        "promote_math_numbers": bool(
            measured_output in {"formula", "math"}
            or "formula" in requested_outputs
            or "math" in requested_outputs
        ),
        "promote_variable_labels": bool(
            measured_output in {"formula", "math"}
            or "formula" in requested_outputs
            or "math" in requested_outputs
        ),
        "source": "QUANTUM_PROCESSOR",
    }

    request_metadata = {
        "processor_version": PROCESSOR_VERSION,
        "assistant_identity": deepcopy(APRIL_IDENTITY),
        "assistant_identity_name": APRIL_IDENTITY.get("name", "April"),
        "identity_request": bool(semantic.get("identity_request")),
        "single_route": True,
        "provider_calls_per_request": 1,
        "context_mode": mode,
        "dialogue_coherence": round(coherence, 4),
        "identity_scope": deepcopy(scope),
        "control_plane_version": control.get("version"),
    }

    if isinstance(state, dict):
        active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
        flow_id = state.get("flow_id") or active_flow.get("flow_id")
        if flow_id:
            request_metadata["flow_id"] = flow_id

    request = MachineRequest(
        goal=_s(control.get("active_goal")) or text,
        intent={
            "type": _s(semantic.get("intent")) or (
                "self_identification" if semantic.get("identity_request") else "dialogue"
            ),
            "normalized_text": _s(text),
            "dialogue_state": mode,
            "coherence": round(coherence, 4),
            "dialog_act": dialogue_contract["dialog_act"],
        },
        conversation={
            "current_request": _s(text),
            "dialogue_contract": dialogue_contract,
            "dialogue_vector": deepcopy(semantic.get("dialogue_vector") or {}),
            "dialogue_delta": deepcopy(semantic.get("dialogue_delta") or {}),
            "render_continuity": deepcopy(semantic.get("render_continuity") or {}),
            "visual_schema": _s(semantic.get("visual_schema")),
            "visual_schema_confidence": float(semantic.get("visual_schema_confidence") or 0.0),
            "context_mode": mode,
            "context_dependency": bool(control.get("context_dependency")),
            "resolved_request": _s(
                dialogue_contract.get("resolved_request")
                or dialogue_contract_source.get("resolved_request")
                or text
            ),
            "previous_user_turn": _s(
                dialogue_contract_source.get("previous_user_turn")
                or dialogue_evidence.get("previous_user")
            ),
            "previous_april_turn": _s(
                dialogue_contract_source.get("previous_april_turn")
                or dialogue_evidence.get("previous_april")
            ),
            "resolved_scene": _as_dict(
                dialogue_contract.get("resolved_scene")
                or dialogue_contract_source.get("resolved_scene")
                or control.get("resolved_scene")
            ),
            **(
                {
                    "active_topic": _clip(_s(control.get("active_topic")), 300),
                    "active_goal": _clip(_s(control.get("active_goal")), 500),
                }
                if mode != "INDEPENDENT"
                else {}
            ),
            **(
                {"recent_dialogue": context.get("recent_dialogue", [])}
                if mode in {
                    "CONTINUATION",
                    "SAME_TOPIC",
                    "ARTIFACT_REFERENCE",
                    "MEMORY_QUERY",
                } or bool(control.get("context_dependency"))
                else {}
            ),
        },
        memory=(
            {
                "active_topic": _clip(_s(control.get("active_topic")), 300),
                "active_goal": _clip(_s(control.get("active_goal")), 500),
                "active_scene_id": _s(
                    _as_dict(dialogue_evidence.get("scene_continuity")).get("scene_id")
                    or _as_dict(state.get("current_visual_scene")).get("scene_id")
                ),
                "retrieval_mode": "memory_query" if mode == "MEMORY_QUERY" else "semantic",
                "dynamic_memory": (
                    dynamic_memory_evidence
                    if mode in {
                        "CONTINUATION",
                        "SAME_TOPIC",
                        "ARTIFACT_REFERENCE",
                        "MEMORY_QUERY",
                    } or bool(control.get("reference_to_previous"))
                    else {"available": bool(dynamic_memory_evidence.get("matches"))}
                ),
            }
            if mode != "INDEPENDENT"
            else {
                "active_scene_id": _s(
                    _as_dict(state.get("current_visual_scene")).get("scene_id")
                )
            }
        ),
        visual_context=(
            visual if mode == "ARTIFACT_REFERENCE" and isinstance(visual, dict)
            else {}
        ),
        available_tools=list(control.get("capabilities") or []),
        requested_outputs=requested_outputs,
        required_competencies=list(control.get("capabilities") or []),
        required_artifacts=requested_outputs,
        routing={
            "single_route": True,
            "processor": PROCESSOR_VERSION,
            "measured_state": mode,
            "identity_scope": deepcopy(scope),
        },
        constraints={
            "one_provider_call": True,
            "one_visible_answer": True,
            "canonical_scene": True,
            "dialogue_coherence": round(coherence, 4),
            "quantum_state": {
                "dialogue": dialogue_state,
                "representation": control.get("representation_state", {}),
                "measured_output": measured_output,
            },
            "provider_input_token_budget": 900,
            "provider_context_strategy": "provider_router_semantic_field_selection",
            "current_request_must_remain_intact": True,
            "identity_scope": deepcopy(scope),
            "presentation_plan": presentation_plan,
            "representation_plan": {
                "requested_outputs": requested_outputs,
                "preferred_representation": measured_output,
                "visual_schema": _s(semantic.get("visual_schema")),
                "visual_schema_confidence": float(semantic.get("visual_schema_confidence") or 0.0),
                "dialogue_relation": _s(semantic.get("dialogue_relation")) or "NEW_TOPIC",
                "dialogue_subtype": _s(semantic.get("dialogue_subtype")) or "NEW_TOPIC",
                "avoid_repeat": True,
                "constraints": representation_constraints,
                "audit": representation_audit,
                "current_request_authoritative": True,
            },
            "metadata": request_metadata,
        },
    )

    request.response_complexity = complexity
    request.response_output_tokens = response_budget
    request.max_output_tokens = response_budget
    request.quantum_state = {
        "dialogue": dialogue_state,
        "representation": control.get("representation_state", {}),
        "measured_output": measured_output,
        "context_dependency": bool(control.get("context_dependency")),
        "reference_to_previous": bool(control.get("reference_to_previous")),
        "continuation": bool(control.get("continuation")),
        "scene_continuity": _quantum_snapshot(
            control.get("dialogue_evidence", {}).get("scene_continuity", {})
        ),
        "evidence_channels": len(evidence),
        "coherence": round(coherence, 4),
        "response_budget": response_budget,
        "response_budget_min": OUTPUT_MIN_TOKENS,
        "response_budget_max": OUTPUT_MAX_TOKENS,
        "response_budget_mode": "continuous_64_signal_scale",
        "quantum_cores": QUANTUM_CORE_COUNT,
        "quantum_lanes": QUANTUM_LANE_COUNT,
        "quantum_signal_count": QUANTUM_CORE_COUNT * QUANTUM_LANE_COUNT,
        "quantum_budget_field": quantum_budget_field,
        "response_budget_logical": True,
        "response_budget_compression_ceiling": OUTPUT_MAX_TOKENS,
        "control_plane": _quantum_snapshot(control),
    }
    request.dialogue_contract = dialogue_contract
    request.response_decision = decision
    request.single_route = True
    request.provider_calls_allowed = 1

    request.constraints["metadata"].update({
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "context_mode": mode,
        "dialogue_coherence": round(coherence, 4),
        "response_budget": response_budget,
        "response_budget_min": OUTPUT_MIN_TOKENS,
        "response_budget_max": OUTPUT_MAX_TOKENS,
        "response_budget_mode": "continuous_64_signal_scale",
        "quantum_cores": QUANTUM_CORE_COUNT,
        "quantum_lanes": QUANTUM_LANE_COUNT,
        "quantum_signal_count": QUANTUM_CORE_COUNT * QUANTUM_LANE_COUNT,
        "quantum_budget_field": quantum_budget_field,
        "requested_outputs": requested_outputs,
        "identity_scope": deepcopy(scope),
        "control_plane": _quantum_snapshot(control),
        "presentation_plan": _quantum_snapshot(request.constraints.get("presentation_plan", {})),
        "representation_plan": _quantum_snapshot(
            request.constraints.get("representation_plan", {})
        ),
    })
    return request


def _request_metadata(request: MachineRequest) -> dict:
    constraints = getattr(request, "constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    metadata = constraints.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata


def _repair_machine_json_escapes(text: str) -> str:
    """Repair only invalid JSON backslashes while preserving real JSON escapes.

    Provider responses sometimes contain JSON-shaped envelopes with LaTeX such
    as ``\\( ... \\sqrt{...} \\)``. Those backslashes are valid payload text but
    are not valid JSON escapes unless doubled for the JSON parser. This engine
    normalizes the transport encoding only; it does not alter the decoded human
    answer.
    """
    # JSON permits only these one-character escapes plus \\uXXXX. Any other
    # backslash is payload text and must be escaped before json.loads().
    return re.sub(r'\\\\(?!["\\\\/bfnrtu])', r'\\\\\\\\', text)


def _decode_json_envelope(value: Any, *, max_depth: int = 5) -> Any:
    """Recursively unwrap serialized machine envelopes without creating a route.

    The decoder accepts:
      * normal JSON,
      * JSON-shaped Provider payloads containing LaTeX backslashes,
      * Python-literal style dicts using single quotes.

    The repair is transport-level only. It never rewrites the decoded answer.
    """
    current = value
    for _ in range(max_depth):
        if isinstance(current, MachineResponse):
            current = {
                name: getattr(current, name)
                for name in current.__dataclass_fields__
            }
            continue
        if not isinstance(current, str):
            break

        text = current.strip()
        if not (text.startswith("{") and text.endswith("}")):
            break

        parsed = None

        # 1. Canonical JSON first.
        try:
            candidate = json.loads(text)
            if isinstance(candidate, dict):
                parsed = candidate
        except Exception:
            pass

        # 2. Relaxed transport JSON: preserve LaTeX backslashes as payload.
        if parsed is None:
            repaired = _repair_machine_json_escapes(text)
            try:
                candidate = json.loads(repaired)
                if isinstance(candidate, dict):
                    parsed = candidate
            except Exception:
                pass

            # 3. Legacy Python-literal envelopes. Parse the repaired form so
            # invalid LaTeX escapes cannot emit SyntaxWarning during eval.
            if parsed is None:
                try:
                    candidate = ast.literal_eval(repaired)
                    if isinstance(candidate, dict):
                        parsed = candidate
                except Exception:
                    pass

        if parsed is None:
            break
        current = parsed

    return current


def _clean_text_value(value: Any) -> str:
    """Return only the final human-readable text from a Provider field."""
    current = _decode_json_envelope(value)

    if isinstance(current, dict):
        for key in ("answer", "content", "response", "text", "message", "final_text"):
            if current.get(key) not in (None, "", [], {}):
                nested = _decode_json_envelope(current.get(key))
                if isinstance(nested, str):
                    return nested.strip()
                if isinstance(nested, dict):
                    resolved = _clean_text_value(nested)
                    if resolved:
                        return resolved
        return ""

    return _s(current)


def _clean_render_blocks(blocks: Any) -> list[dict]:
    """Decode nested machine envelopes and retain every embedded artifact block."""
    result: list[dict] = []
    queue = list(blocks or []) if isinstance(blocks, (list, tuple)) else []
    while queue:
        block = queue.pop(0)
        if not isinstance(block, dict):
            continue
        btype = _s(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
        content = block.get("content")
        decoded_content = _decode_json_envelope(content)
        if isinstance(decoded_content, dict) and any(k in decoded_content for k in ("answer", "content", "summary", "render_blocks", "blocks", "artifacts", "artifacts_payload")):
            nested_answer = _clean_text_value(decoded_content.get("answer") or decoded_content.get("content"))
            if nested_answer:
                clean_block = dict(block)
                clean_block["content"] = nested_answer
                clean_block["text"] = nested_answer
                clean_block.setdefault("type", "text")
                result.append(clean_block)
            nested = []
            nested.extend(_as_list(decoded_content.get("render_blocks")))
            nested.extend(_as_list(decoded_content.get("blocks")))
            nested.extend(_as_list(decoded_content.get("artifacts")))
            nested.extend(_as_list(decoded_content.get("artifacts_payload")))
            if nested:
                queue = nested + queue
            continue
        clean_block = dict(block)
        if btype in {"text", "markdown"}:
            clean_text = _clean_text_value(block.get("content") or block.get("text") or block.get("value"))
            if clean_text:
                clean_block["content"] = clean_text
                clean_block["text"] = clean_text
        result.append(clean_block)
    return result


def _promote_embedded_structured_blocks(blocks: list[dict]) -> list[dict]:
    """Turn structurally explicit URLs into link blocks without keyword routing."""
    result: list[dict] = []
    url_re = re.compile(r"https?://[^\s)\]}>,]+", flags=re.I)
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = _s(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
        if kind not in {"text", "markdown"}:
            result.append(block)
            continue
        text = _s(block.get("content") or block.get("text") or block.get("value"))
        urls = url_re.findall(text)
        if not urls:
            result.append(block)
            continue
        remaining = text
        first = True
        for url in urls:
            before, sep, after = remaining.partition(url)
            if before.strip():
                tb = dict(block)
                tb["content"] = before.strip()
                tb["text"] = tb["content"]
                if not first:
                    tb.pop("block_id", None)
                result.append(tb)
            lb = {
                "type": "link",
                "renderer": "link",
                "viewer": "link_card",
                "payload": {"url": url, "href": url},
                "scene_contract": True,
            }
            result.append(lb)
            remaining = after
            first = False
        if remaining.strip():
            tb = dict(block)
            tb["content"] = remaining.strip()
            tb["text"] = tb["content"]
            tb.pop("block_id", None)
            result.append(tb)
    return result

def _decode_provider_payload(value: Any) -> dict:
    """Fully decode the Provider envelope while preserving every structured field.

    The Provider may return:
      1) a dict,
      2) a MachineResponse dataclass,
      3) a JSON string containing either,
      4) an answer/content field that itself contains another JSON envelope.

    Nested canonical fields must WIN over the outer serialized wrapper.  We
    therefore merge metadata first and canonical inner fields second, instead
    of letting the raw outer ``answer`` overwrite the decoded answer.
    """
    decoded = _decode_json_envelope(value)
    if isinstance(decoded, MachineResponse):
        decoded = {
            name: getattr(decoded, name)
            for name in decoded.__dataclass_fields__
        }

    if not isinstance(decoded, dict):
        return {"answer": _clean_text_value(decoded)}

    def merge_nested(base: dict, nested: dict, source_key: str) -> dict:
        # Preserve every unrelated outer field, but let decoded inner fields
        # own answer/content/summary/render/artifact semantics.
        outer = {k: v for k, v in base.items() if k != source_key}
        merged = {**outer, **nested}

        # When the inner envelope omitted a machine field, retain the outer one.
        for key in (
            "render_blocks", "blocks", "artifacts", "artifacts_payload",
            "scene", "scene_plan", "renderer_state", "metadata",
            "active_scene", "supported_payloads", "links", "graph", "formula",
            "table", "gallery", "layout", "visual",
        ):
            if key not in nested and key in base:
                merged[key] = base[key]
        return merged

    payload = dict(decoded)

    # First unwrap explicit nested machine_response envelopes.
    embedded = _decode_json_envelope(payload.get("machine_response"))
    if isinstance(embedded, dict):
        payload = merge_nested(payload, embedded, "machine_response")

    # Repeatedly unwrap a canonical answer/content/response envelope until the
    # visible fields are no longer machine JSON.  Inner canonical fields win.
    for _ in range(4):
        changed = False
        for key in ("answer", "content", "response", "payload", "data"):
            nested = _decode_json_envelope(payload.get(key))
            if isinstance(nested, dict) and any(
                k in nested
                for k in (
                    "answer", "content", "response", "summary",
                    "render_blocks", "artifacts", "machine_response"
                )
            ):
                payload = merge_nested(payload, nested, key)
                changed = True
                break
        if not changed:
            break

    payload["render_blocks"] = _clean_render_blocks(
        payload.get("render_blocks") or payload.get("blocks") or []
    )
    if isinstance(payload.get("summary"), str):
        payload["summary"] = _clean_text_value(payload.get("summary"))

    # Canonical human fields are always flattened to plain text here.
    answer = (
        _clean_text_value(payload.get("answer"))
        or _clean_text_value(payload.get("content"))
        or _clean_text_value(payload.get("response"))
    )
    if answer:
        payload["answer"] = answer
        payload["content"] = answer

    return payload




def _math_structure_profile(value: Any) -> dict:
    """Measure mathematical notation structurally for the unified presentation engine.

    Ordinary prose numbers are not promoted to math. Ordered-list markers,
    dates, counters and other plain numeric prose remain text unless they are
    part of an explicit/structural mathematical expression.
    """
    source = _s(value)
    if not source:
        return {
            "present": False,
            "confidence": 0.0,
            "ranges": [],
            "notation": [],
            "operator_density": 0.0,
            "measurement_mode": "structural_notation_matrix",
            "lexical_triggers": False,
        }

    ranges: list[dict] = []
    notation: list[str] = []
    occupied: list[tuple[int, int]] = []

    def add_range(start: int, end: int, source_name: str, *, display: bool = False) -> None:
        start = max(0, int(start))
        end = min(len(source), int(end))
        while end > start and source[end - 1].isspace():
            end -= 1
        while start < end and source[start].isspace():
            start += 1
        if end <= start:
            return
        if any(start < b and end > a for a, b in occupied):
            return
        occupied.append((start, end))
        ranges.append({
            "start": start,
            "end": end,
            "kind": "formula",
            "renderer": "mcdowell",
            "engine": "katex",
            "source": source_name,
            "display": bool(display),
        })
        notation.append(source_name)

    # Explicit delimiters are authoritative.
    delimiter_patterns = (
        (r"\\\((.+?)\\\)", "inline_latex", False),
        (r"\\\[(.+?)\\\]", "display_latex", True),
        (r"\$\$(.+?)\$\$", "display_dollar", True),
        (r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", "inline_dollar", False),
    )
    for pattern, label, display in delimiter_patterns:
        for match in re.finditer(pattern, source, flags=re.DOTALL):
            add_range(*match.span(), label, display=display)

    # Structural atoms.
    frac_atom = r"\\(?:frac|dfrac|tfrac)\s*\{[^{}\n]{1,120}\}\s*\{[^{}\n]{1,120}\}"
    sqrt_atom = r"\\sqrt\s*(?:\[[^\]\n]{1,24}\])?\s*\{[^{}\n]{1,120}\}"
    command_atom = r"\\(?:operatorname|mathrm|text)\s*\{[^{}\n]{1,80}\}"
    radical_value = r"[A-Za-zА-Яа-яЁёΑ-Ωα-ω0-9_]+(?:[.,]\d+)?"
    unicode_sqrt_atom = rf"√\s*(?:\([^()\n]{{1,120}}\)|{radical_value})"
    unicode_cbrt_atom = rf"∛\s*(?:\([^()\n]{{1,120}}\)|{radical_value})"
    unicode_qrtrt_atom = rf"∜\s*(?:\([^()\n]{{1,120}}\)|{radical_value})"
    numeric_atom = r"[-+−]?\d+(?:[.,]\d+)?(?:[eE][-+−]?\d+)?"
    symbol_atom = r"[A-Za-zΑ-Ωα-ω]\w*(?:\^[-+]?\d+|[²³⁴⁵⁶⁷⁸⁹])?"
    paren_atom = r"\([^()\n]{1,120}\)"
    atom = (
        rf"(?:{numeric_atom}|{symbol_atom}|{frac_atom}|{sqrt_atom}|"
        rf"{unicode_sqrt_atom}|{unicode_cbrt_atom}|{unicode_qrtrt_atom}|"
        rf"{command_atom}|{paren_atom})"
    )
    operator = (
        r"(?:\\(?:cdot|times|div|pm|mp|approx|leq|geq|neq|sim|cong|simeq|"
        r"equiv|to)|[+\-−*/=<>×÷≈≤≥≠±·])"
    )

    # Operator-connected chains.
    chain_re = re.compile(rf"(?P<expr>{atom}(?:\s*{operator}\s*{atom})+)")
    for match in chain_re.finditer(source):
        add_range(*match.span("expr"), "raw_math_structure", display=False)

    # Standalone radicals/fractions are formulas even without an operator.
    standalone_re = re.compile(
        rf"(?:{frac_atom}|{sqrt_atom}|{unicode_sqrt_atom}|{unicode_cbrt_atom}|"
        rf"{unicode_qrtrt_atom})(?:\s*{operator}\s*"
        rf"(?:{frac_atom}|{sqrt_atom}|{unicode_sqrt_atom}|{unicode_cbrt_atom}|"
        rf"{unicode_qrtrt_atom}|{numeric_atom}|{symbol_atom}|{paren_atom}))*"
    )
    for match in standalone_re.finditer(source):
        add_range(*match.span(), "radical_structure", display=False)

    # Relations need full operands; this also captures Provider output that
    # uses Unicode operators rather than TeX.
    relation_re = re.compile(
        rf"(?P<expr>{atom}\s*(?:=|≈|≃|≅|≤|≥|≠)\s*{atom}"
        rf"(?:\s*{operator}\s*{atom})*)"
    )
    for match in relation_re.finditer(source):
        add_range(*match.span("expr"), "relation_structure", display=False)

    # NEVER classify list numbering itself as math:
    # "1. ..." / "2) ..." are layout structure, not formulas.
    list_prefixes: list[tuple[int, int]] = []
    offset = 0
    for raw_line in source.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        m = re.match(r"^\s*\d+[.)]\s+", line)
        if m:
            list_prefixes.append((offset + m.start(), offset + m.end()))
        offset += len(raw_line)

    # A number already inside an occupied structural expression is part of it.
    # Standalone numeric values are intentionally not promoted by themselves.
    # This preserves clean prose and list numbering while formulas stay unified.

    ranges.sort(key=lambda item: (item["start"], item["end"]))
    merged: list[dict] = []
    for item in ranges:
        if not merged or item["start"] >= merged[-1]["end"]:
            merged.append(dict(item))
        elif item["end"] > merged[-1]["end"]:
            merged[-1]["end"] = item["end"]
            merged[-1]["display"] = bool(
                merged[-1].get("display") or item.get("display")
            )
            if item.get("source") not in notation:
                notation.append(item.get("source", "structural"))

    operator_count = len(re.findall(r"[=≈≃≅≤≥±·×÷/*^_√∛∜]", source))
    numeric_count = len(re.findall(r"\d", source))
    density = (operator_count + min(numeric_count, 12)) / max(len(source), 1)

    structural_strength = 0.0
    if merged:
        structural_strength = min(
            1.0,
            0.55 + 0.12 * min(len(merged), 3) + min(0.20, density * 6.0),
        )

    return {
        "present": bool(merged),
        "confidence": round(structural_strength, 6),
        "ranges": merged,
        "notation": sorted(set(x for x in notation if x)),
        "operator_density": round(density, 6),
        "measurement_mode": "structural_notation_matrix",
        "lexical_triggers": False,
        "numeric_policy": "structural_only",
        "list_numbering_protected": True,
    }


def _math_presentation_policy(request: MachineRequest | None = None) -> dict:
    """Return one canonical math-display policy for the current turn.

    The policy is derived from the already-collapsed request contract. It never
    performs lexical routing. In explicit mathematical turns, numbers/units
    that belong to mathematical expressions are promoted to KaTeX, while
    ordinary prose remains Markdown.
    """
    if request is None:
        return {
            "version": "math_presentation_policy_v2",
            "mode": "structural",
            "promote_math_numbers": False,
            "promote_variable_labels": False,
            "source": "QUANTUM_PROCESSOR",
        }

    qstate = getattr(request, "quantum_state", {}) or {}
    rep = qstate.get("representation", {}) if isinstance(qstate, dict) else {}
    measured = _s(qstate.get("measured_output")) if isinstance(qstate, dict) else ""
    outputs = list(getattr(request, "requested_outputs", []) or [])

    explicit_formula = (
        measured in {"formula", "math"}
        or "formula" in outputs
        or "math" in outputs
    )
    plan = getattr(request, "constraints", {}) or {}
    presentation_plan = plan.get("presentation_plan", {}) if isinstance(plan, dict) else {}
    explicit_numbers = bool(
        presentation_plan.get("promote_math_numbers")
        or presentation_plan.get("all_math_numbers")
    )

    mode = "explicit_math" if explicit_formula or explicit_numbers else "structural"

    return {
        "version": "math_presentation_policy_v2",
        "mode": mode,
        "promote_math_numbers": bool(explicit_numbers or explicit_formula),
        "promote_variable_labels": bool(explicit_numbers or explicit_formula),
        "source": "QUANTUM_PROCESSOR",
    }


def _math_structure_profile_v2(value: Any, *, policy: dict | None = None) -> dict:
    """Extended structural math parser for Provider output.

    This is intentionally structure-driven:
      * explicit TeX delimiters remain authoritative;
      * relation/assignment/operator chains form one expression;
      * units attached to numeric expressions remain part of that expression;
      * explicit math turns can additionally promote standalone numbers and
        variable labels that are clearly part of assignment/list notation;
      * ordinary prose is never globally converted to math.
    """
    source = _s(value)
    policy = policy if isinstance(policy, dict) else {}
    promote_numbers = bool(policy.get("promote_math_numbers"))
    promote_variables = bool(policy.get("promote_variable_labels"))

    if not source:
        return {
            "present": False,
            "confidence": 0.0,
            "ranges": [],
            "notation": [],
            "operator_density": 0.0,
            "measurement_mode": "structural_notation_matrix_v2",
            "lexical_triggers": False,
            "numeric_policy": "explicit_math_only",
            "math_policy": policy,
        }

    ranges: list[dict] = []
    occupied: list[tuple[int, int]] = []
    notation: list[str] = []

    def overlaps(start: int, end: int) -> bool:
        return any(start < b and end > a for a, b in occupied)

    def add_range(start: int, end: int, source_name: str, *, display: bool = False) -> None:
        start = max(0, int(start))
        end = min(len(source), int(end))
        while end > start and source[end - 1].isspace():
            end -= 1
        while start < end and source[start].isspace():
            start += 1
        if end <= start or overlaps(start, end):
            return
        occupied.append((start, end))
        ranges.append({
            "start": start,
            "end": end,
            "kind": "formula",
            "renderer": "mcdowell",
            "engine": "katex",
            "source": source_name,
            "display": bool(display),
        })
        notation.append(source_name)

    # 1. Explicit TeX delimiters.
    delimiter_patterns = (
        (r"\\\((.+?)\\\)", "inline_latex", False),
        (r"\\\[(.+?)\\\]", "display_latex", True),
        (r"\$\$(.+?)\$\$", "display_dollar", True),
        (r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", "inline_dollar", False),
    )
    for pattern, label, display in delimiter_patterns:
        for match in re.finditer(pattern, source, flags=re.DOTALL):
            add_range(*match.span(), label, display=display)

    # 2. Canonical TeX/Unicode atoms.
    frac_atom = r"\\(?:frac|dfrac|tfrac)\s*\{[^{}\n]{1,160}\}\s*\{[^{}\n]{1,160}\}"
    sqrt_atom = r"\\sqrt\s*(?:\[[^\]\n]{1,24}\])?\s*\{[^{}\n]{1,160}\}"
    command_atom = r"\\(?:operatorname|mathrm|text)\s*\{[^{}\n]{1,100}\}"
    radical_value = r"[A-Za-zА-Яа-яЁёΑ-Ωα-ω0-9_]+(?:[.,]\d+)?"
    unicode_sqrt_atom = rf"√\s*(?:\([^()\n]{{1,160}}\)|{radical_value})"
    unicode_cbrt_atom = rf"∛\s*(?:\([^()\n]{{1,160}}\)|{radical_value})"
    unicode_qrtrt_atom = rf"∜\s*(?:\([^()\n]{{1,160}}\)|{radical_value})"
    numeric_atom = r"[-+−]?\d+(?:[.,]\d+)?(?:[eE][-+−]?\d+)?(?:\s*(?:[A-Za-zА-Яа-яЁё]{1,6}|%|°))?"
    symbol_atom = r"[A-Za-zΑ-Ωα-ω]\w*(?:\^[-+]?\d+|[²³⁴⁵⁶⁷⁸⁹])?"
    paren_atom = r"\([^()\n]{1,160}\)"
    atom = (
        rf"(?:{numeric_atom}|{symbol_atom}|{frac_atom}|{sqrt_atom}|"
        rf"{unicode_sqrt_atom}|{unicode_cbrt_atom}|{unicode_qrtrt_atom}|"
        rf"{command_atom}|{paren_atom})"
    )
    operator = (
        r"(?:\\(?:cdot|times|div|pm|mp|approx|leq|geq|neq|sim|cong|simeq|"
        r"equiv|to)|[+\-−*/=<>×÷≈≤≥≠±·])"
    )

    # 3. Operator-connected chains and relations.
    chain_re = re.compile(rf"(?P<expr>{atom}(?:\s*{operator}\s*{atom})+)")
    for match in chain_re.finditer(source):
        add_range(*match.span("expr"), "raw_math_structure", display=False)

    relation_re = re.compile(
        rf"(?P<expr>{atom}\s*(?:=|≈|≃|≅|≤|≥|≠)\s*{atom}"
        rf"(?:\s*{operator}\s*{atom})*)"
    )
    for match in relation_re.finditer(source):
        add_range(*match.span("expr"), "relation_structure", display=False)

    # 4. Standalone radical/fraction structures.
    standalone_re = re.compile(
        rf"(?:{frac_atom}|{sqrt_atom}|{unicode_sqrt_atom}|{unicode_cbrt_atom}|"
        rf"{unicode_qrtrt_atom})(?:\s*{operator}\s*"
        rf"(?:{frac_atom}|{sqrt_atom}|{unicode_sqrt_atom}|{unicode_cbrt_atom}|"
        rf"{unicode_qrtrt_atom}|{numeric_atom}|{symbol_atom}|{paren_atom}))*"
    )
    for match in standalone_re.finditer(source):
        add_range(*match.span(), "radical_structure", display=False)

    # 5. Explicit math mode: promote numbers/units and variable labels only
    # when the local line itself has mathematical structure.
    if promote_numbers or promote_variables:
        line_offset = 0
        for raw_line in source.splitlines(keepends=True):
            line = raw_line.rstrip("\r\n")
            stripped = line.strip()
            line_start = line_offset
            line_end = line_start + len(line)
            line_offset += len(raw_line)

            if not stripped:
                continue

            line_math = bool(
                re.search(r"(?:=|≈|≃|≅|≤|≥|≠|×|÷|\*|/|\^|²|³|√|∛|∜|\\(?:frac|sqrt|cdot|times|div))", line)
                or re.match(r"^\s*(?:[A-Za-zΑ-Ωα-ω]\w*|[A-Za-zА-Яа-яЁё]\w*)\s*=", line)
            )
            if not line_math:
                # Still support explanatory list labels like "- **E** — энергия".
                line_math = bool(
                    promote_variables
                    and re.match(r"^\s*[-*+]\s+\*\*[A-Za-zΑ-Ωα-ωА-Яа-яЁё]\w*(?:\^[-+]?\d+|[²³⁴⁵⁶⁷⁸⁹])?\*\*\s*[—-]", line)
                )
            if not line_math:
                continue

            # Bold variable labels: **E**, **m**, **c²**
            if promote_variables:
                for match in re.finditer(
                    r"\*\*(?P<var>[A-Za-zΑ-Ωα-ωА-Яа-яЁё]\w*(?:\^[-+]?\d+|[²³⁴⁵⁶⁷⁸⁹])?)\*\*",
                    line,
                ):
                    start = line_start + match.start("var")
                    end = line_start + match.end("var")
                    add_range(start, end, "math_variable_label", display=False)

            # Standalone numeric values in an explicitly mathematical line.
            if promote_numbers:
                for match in re.finditer(
                    r"(?<![\wА-Яа-яЁё])[-+]?\d+(?:[.,]\d+)?(?:\s*(?:[A-Za-zА-Яа-яЁё]{1,8}|%|°))?(?![\wА-Яа-яЁё])",
                    line,
                ):
                    start = line_start + match.start()
                    end = line_start + match.end()
                    # Do not split numbers that are already inside a larger
                    # expression span; the full expression is the better unit.
                    if not overlaps(start, end):
                        add_range(start, end, "explicit_math_number", display=False)

    # 6. Protect Markdown list numbering from accidental math promotion.
    list_prefixes: list[tuple[int, int]] = []
    offset = 0
    for raw_line in source.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        m = re.match(r"^\s*\d+[.)]\s+", line)
        if m:
            list_prefixes.append((offset + m.start(), offset + m.end()))
        offset += len(raw_line)

    # 7. Merge only truly overlapping ranges.
    ranges.sort(key=lambda item: (item["start"], item["end"]))
    merged: list[dict] = []
    for item in ranges:
        if any(
            item["start"] >= a and item["end"] <= b
            for a, b in list_prefixes
        ):
            continue
        if not merged or item["start"] >= merged[-1]["end"]:
            merged.append(dict(item))
        elif item["end"] > merged[-1]["end"]:
            merged[-1]["end"] = item["end"]
            merged[-1]["display"] = bool(
                merged[-1].get("display") or item.get("display")
            )
            if item.get("source") not in notation:
                notation.append(item.get("source", "structural"))

    operator_count = len(re.findall(r"[=≈≃≅≤≥±·×÷/*^_√∛∜]", source))
    numeric_count = len(re.findall(r"\d", source))
    density = (operator_count + min(numeric_count, 16)) / max(len(source), 1)

    structural_strength = 0.0
    if merged:
        structural_strength = min(
            1.0,
            0.55 + 0.11 * min(len(merged), 4) + min(0.24, density * 6.0),
        )

    return {
        "present": bool(merged),
        "confidence": round(structural_strength, 6),
        "ranges": merged,
        "notation": sorted(set(x for x in notation if x)),
        "operator_density": round(density, 6),
        "measurement_mode": "structural_notation_matrix_v2",
        "lexical_triggers": False,
        "numeric_policy": "explicit_math_and_structural",
        "math_policy": policy,
        "list_numbering_protected": True,
    }


def _math_normalize_provider_fragment(fragment: str) -> str:
    """Normalize common Provider TeX fragments into stable KaTeX source."""
    value = _presentation_latex(fragment)
    value = value.replace(r"\text{кг}", r"\mathrm{кг}")
    value = value.replace(r"\text{г}", r"\mathrm{г}")
    value = value.replace(r"\text{м}", r"\mathrm{м}")
    value = value.replace(r"\text{с}", r"\mathrm{с}")
    value = re.sub(r"\\text\{([^{}]{1,40})\}", r"\\mathrm{\1}", value)
    value = value.replace(r"\cdot", r"\times")
    return value


def _canonical_semantic_block_key(block: dict) -> str:
    """Semantic identity used only to collapse true transport duplicates."""
    source = _as_dict(block)
    btype = _s(
        source.get("type")
        or source.get("artifact_type")
        or source.get("representation")
        or "text"
    ).lower()

    parts = []
    for key in ("content", "text", "value", "title", "description"):
        val = source.get(key)
        if isinstance(val, (str, int, float)):
            normalized = re.sub(r"\s+", " ", _s(val)).strip().lower()
            if normalized:
                parts.append(f"{key}:{normalized}")

    payload = _canonical_block_payload(source)
    if payload:
        try:
            parts.append(
                "payload:"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
            )
        except Exception:
            parts.append("payload:" + repr(payload))

    return hashlib.sha256(
        (btype + "|" + "|".join(parts)).encode("utf-8")
    ).hexdigest()


def _canonical_answer_composer(blocks: Any, answer: str = "") -> list[dict]:
    """Compose one logical visible stream from Provider's heterogeneous blocks.

    The composer removes only true duplicates. Distinct blocks are preserved in
    Provider order and linked under one answer stream.
    """
    canonical = _canonicalize_render_stream(blocks)
    if not canonical and answer:
        canonical = [{
            "type": "text",
            "artifact_type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "source": "quantum_processor",
        }]

    result: list[dict] = []
    seen: dict[str, dict] = {}
    stream_id = hashlib.sha256(
        _s(answer).encode("utf-8")
    ).hexdigest()[:20] if answer else "stream"

    for raw in canonical:
        if not isinstance(raw, dict):
            continue
        block = dict(raw)
        semantic_key = _canonical_semantic_block_key(block)

        # Same logical text/content appearing twice is a transport duplicate.
        # Do not collapse distinct renderer types with different structured payloads.
        existing = seen.get(semantic_key)
        if existing is not None:
            existing.setdefault("duplicate_block_ids", [])
            if block.get("block_id") not in existing["duplicate_block_ids"]:
                existing["duplicate_block_ids"].append(block.get("block_id"))
            continue

        seen[semantic_key] = block
        result.append(block)

    stream_ids = []
    for idx, block in enumerate(result):
        old_id = _s(block.get("block_id"))
        if not old_id:
            old_id = f"quantum-block-{idx}"
        block["block_id"] = old_id
        block["sequence_index"] = idx
        stream_ids.append(old_id)

    for idx, block in enumerate(result):
        related = list(block.get("related_block_ids") or [])
        prev_id = stream_ids[idx - 1] if idx > 0 else ""
        next_id = stream_ids[idx + 1] if idx + 1 < len(stream_ids) else ""
        for rid in (prev_id, next_id):
            if rid and rid not in related:
                related.append(rid)
        block["related_block_ids"] = related
        block["presentation_stream"] = {
            "version": "quantum_presentation_stream_v2",
            "answer_stream_id": stream_id,
            "stream_ids": stream_ids,
            "source_block_id": block.get("block_id"),
            "sequence_index": idx,
            "single_visible_stream": True,
            "duplicate_blocks_collapsed": bool(block.get("duplicate_block_ids")),
        }

    return result


def _quantum_visible_render_policy(
    blocks: Any,
    answer: str = "",
    request: MachineRequest | None = None,
) -> list[dict]:
    """Collapse provider output into one semantic visible stream.

    The processor is the release authority. It does not invent renderers and it
    does not classify natural language here. It only uses the canonical request
    output plan plus the typed provider payload already present in render_blocks.

    Invariants:
      * one human answer text block at most;
      * internal production/transport signals never become visible renderers;
      * one logical block per structured renderer kind;
      * multiple different structured renderers are preserved only when the
        canonical request explicitly asked for them;
      * duplicate payload wrappers are merged without changing payload content.
    """
    source = _canonicalize_render_stream(blocks)
    if not source:
        if answer:
            source = [{
                "type": "text",
                "artifact_type": "text",
                "content": answer,
                "text": answer,
                "renderer": "TextBlock",
                "viewer": "TextBlock",
                "source": "quantum_processor",
            }]
        else:
            return []

    requested: list[str] = []
    if request is not None:
        requested.extend(
            _s(value).lower()
            for value in list(getattr(request, "requested_outputs", []) or [])
            if _s(value)
        )
        constraints = _as_dict(getattr(request, "constraints", {}) or {})
        plan = _as_dict(constraints.get("representation_plan"))
        requested.extend(
            _s(value).lower()
            for value in list(plan.get("requested_outputs", []) or [])
            if _s(value)
        )
        for key in ("preferred_representation", "measured_output", "production_representation"):
            value = _s(plan.get(key)).lower()
            if value:
                requested.append(value)

    aliases = {
        "markdown": "text",
        "line_chart": "graph",
        "function_plot": "graph",
        "function": "graph",
        "chart": "graph",
        "data_table": "table",
        "galleryblock": "gallery",
        "imageblock": "image",
    }
    requested_set = {aliases.get(item, item) for item in requested if item}
    internal_kinds = {"production_signal", "signal", "quantum_signal", "transport"}

    def kind_of(block: dict) -> str:
        presentation = _as_dict(block.get("presentation"))
        raw = _s(
            block.get("type")
            or block.get("artifact_type")
            or block.get("representation")
            or presentation.get("kind")
            or "text"
        ).lower()
        return aliases.get(raw, raw)

    visible: list[dict] = []
    internal: list[dict] = []
    for raw in source:
        if not isinstance(raw, dict):
            continue
        block = dict(raw)
        kind = kind_of(block)
        block["type"] = kind or "text"
        if kind in internal_kinds:
            internal.append(block)
        else:
            visible.append(block)

    # Keep the actual processor answer as the sole authoritative human text.
    final: list[dict] = []
    answer_norm = re.sub(r"\s+", " ", _clean_text_value(answer)).strip()
    seen_text: set[str] = set()
    for block in visible:
        if kind_of(block) not in {"text", "markdown"}:
            continue
        text = re.sub(r"\s+", " ", _clean_text_value(
            block.get("content") or block.get("text") or block.get("value")
        )).strip()
        if not text or text in seen_text:
            continue
        if answer_norm and text != answer_norm:
            # Provider text fragments are evidence/supporting prose. The
            # canonical answer remains the only top-level human text block.
            continue
        seen_text.add(text)
        final.append(block)

    if answer_norm and answer_norm not in seen_text:
        final.insert(0, {
            "type": "text",
            "artifact_type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
            "source": "quantum_processor",
        })

    structured = [b for b in visible if kind_of(b) not in {"text", "markdown"}]
    requested_structured = {
        item for item in requested_set
        if item not in {"text", "production_signal", "signal"}
    }

    # If the request explicitly names structured outputs, those are the only
    # structured renderers allowed onto the visible stream. Otherwise preserve
    # the single canonical structured representation already emitted by the
    # provider/processor.
    authorized = requested_structured or ({kind_of(structured[0])} if structured else set())

    chosen: dict[str, dict] = {}
    order: list[str] = []
    for block in structured:
        kind = kind_of(block)
        if kind not in authorized:
            continue
        if kind not in chosen:
            chosen[kind] = block
            order.append(kind)
            continue
        existing = chosen[kind]
        for key, value in block.items():
            if key in {"presentation", "presentation_stream", "related_block_ids", "sequence_index"}:
                continue
            if key not in existing or existing.get(key) in (None, "", [], {}):
                existing[key] = value
        existing.setdefault("duplicate_block_ids", [])
        block_id = _s(block.get("block_id"))
        if block_id and block_id not in existing["duplicate_block_ids"]:
            existing["duplicate_block_ids"].append(block_id)

    final.extend(chosen[kind] for kind in order)

    return _canonical_answer_composer(final, answer="")


def _finalize_quantum_visible_stream(
    blocks: Any,
    answer: str = "",
    request: MachineRequest | None = None,
) -> list[dict]:
    """Final canonical visible stream before SceneContract/Web."""
    collapsed = _quantum_visible_render_policy(blocks, answer=answer, request=request)
    return _ensure_presentation_signals(collapsed, request=request)

def _presentation_latex(fragment: str) -> str:
    """Convert recognized notation to KaTeX source without changing payload text."""
    text = _s(fragment)
    if not text:
        return ""

    if text.startswith(r"\(") and text.endswith(r"\)"):
        return text[2:-2].strip()
    if text.startswith(r"\[") and text.endswith(r"\]"):
        return text[2:-2].strip()
    if text.startswith("$$") and text.endswith("$$"):
        return text[2:-2].strip()
    if text.startswith("$") and text.endswith("$"):
        return text[1:-1].strip()

    value = text
    value = re.sub(r"\\begin\{(?:equation|align|gather)\*?\}", "", value)
    value = re.sub(r"\\end\{(?:equation|align|gather)\*?\}", "", value)

    value = value.replace("≈", r"\approx")
    value = value.replace("≃", r"\simeq")
    value = value.replace("≅", r"\cong")
    value = value.replace("≤", r"\leq")
    value = value.replace("≥", r"\geq")
    value = value.replace("±", r"\pm")
    value = value.replace("×", r"\times")
    value = value.replace("÷", r"\div")
    value = value.replace("−", "-")

    value = re.sub(
        r"√\s*\(([^()]{1,96})\)",
        lambda m: r"\sqrt{" + m.group(1).strip() + "}",
        value,
    )
    value = re.sub(
        r"√\s*([A-Za-zА-Яа-яЁёΑ-Ωα-ω0-9_]+(?:[.]\d+)?)",
        lambda m: r"\sqrt{" + m.group(1).strip() + "}",
        value,
    )
    value = re.sub(
        r"∛\s*\(([^()]{1,96})\)",
        lambda m: r"\sqrt[3]{" + m.group(1).strip() + "}",
        value,
    )
    value = re.sub(
        r"∛\s*([A-Za-zА-Яа-яЁёΑ-Ωα-ω0-9_]+(?:[.]\d+)?)",
        lambda m: r"\sqrt[3]{" + m.group(1).strip() + "}",
        value,
    )
    value = re.sub(
        r"∜\s*\(([^()]{1,96})\)",
        lambda m: r"\sqrt[4]{" + m.group(1).strip() + "}",
        value,
    )
    value = re.sub(
        r"∜\s*([A-Za-zА-Яа-яЁёΑ-Ωα-ω0-9_]+(?:[.]\d+)?)",
        lambda m: r"\sqrt[4]{" + m.group(1).strip() + "}",
        value,
    )
    return value


def _markdown_line_kind(line: str) -> tuple[str, str]:
    """Classify existing Markdown structure only; never infer from words."""
    stripped = line.strip()
    if not stripped:
        return "blank", ""
    if re.match(r"^#{1,6}\s+", stripped):
        return "heading", stripped
    if re.match(r"^(?:[-*+])\s+", stripped):
        return "list_item", stripped
    if re.match(r"^\d+[.)]\s+", stripped):
        return "list_item", stripped
    if stripped.startswith(">"):
        return "quote", stripped[1:].lstrip()
    if re.match(r"^(?:---+|\*\*\*+|___+)\s*$", stripped):
        return "divider", stripped
    return "paragraph", line


def _presentation_segments(content: Any, *, math_policy: dict | None = None) -> dict:
    """Build the canonical McDowell layout while preserving the exact payload.

    McDowell owns text layout. KaTeX owns mathematical spans inside that layout.
    The function exposes paragraphs/headings/lists/quotes as structural segments
    and formulas as delegated spans. No second route or rewritten answer is made.
    """
    source = _s(content)
    profile = _math_structure_profile_v2(source, policy=math_policy)
    ranges = list(profile.get("ranges", []) if isinstance(profile, dict) else [])

    if not source:
        return {
            "mode": "text",
            "layout": "mcdowell_document",
            "spans": [],
            "segments": [],
            "blocks": [],
            "analysis": profile,
            "renderer": "mcdowell",
            "text_engine": "mcdowell",
            "math_engine": "katex",
            "payload_preserved": True,
        }

    # First create structural line blocks from the existing Markdown surface.
    line_blocks: list[dict] = []
    offset = 0
    for raw_line in source.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        start = offset
        end = start + len(line)
        offset += len(raw_line)
        kind, value = _markdown_line_kind(line)
        line_blocks.append({
            "kind": kind,
            "start": start,
            "end": end,
            "value": value,
        })

    if not line_blocks:
        line_blocks = [{"kind": "paragraph", "start": 0, "end": len(source), "value": source}]

    spans: list[dict] = []
    segments: list[dict] = []
    layout_blocks: list[dict] = []

    def append_text(start: int, end: int, *, kind: str = "text", role: str = "text") -> None:
        if end <= start:
            return
        segments.append({
            "kind": kind,
            "start": start,
            "end": end,
            "role": role,
            "renderer": "mcdowell",
            "engine": "markdown",
            "value": source[start:end],
            "preserve_payload": True,
        })

    # Math ranges are nested into the structural text blocks.
    for block in line_blocks:
        kind = block["kind"]
        start = block["start"]
        end = block["end"]

        if kind == "blank":
            layout_blocks.append({
                "kind": "spacer",
                "start": start,
                "end": end,
                "renderer": "mcdowell",
                "engine": "layout",
            })
            continue

        if kind in {"heading", "list_item", "quote", "divider"}:
            layout_blocks.append({
                "kind": kind,
                "start": start,
                "end": end,
                "renderer": "mcdowell",
                "engine": "markdown",
                "value": source[start:end],
                "preserve_payload": True,
            })
        else:
            layout_blocks.append({
                "kind": "paragraph",
                "start": start,
                "end": end,
                "renderer": "mcdowell",
                "engine": "markdown",
                "value": source[start:end],
                "preserve_payload": True,
            })

        local_ranges = [
            item for item in ranges
            if int(item["start"]) < end and int(item["end"]) > start
        ]

        cursor = start
        for item in sorted(local_ranges, key=lambda x: (x["start"], x["end"])):
            item_start = max(start, int(item["start"]))
            item_end = min(end, int(item["end"]))
            if item_end <= item_start:
                continue
            if item_start > cursor:
                append_text(
                    cursor,
                    item_start,
                    kind="text",
                    role=kind,
                )

            original = source[item_start:item_end]
            latex = _math_normalize_provider_fragment(original)
            display = bool(item.get("display"))
            # A formula occupying the meaningful body of a line is visually
            # stronger as display math; inline formulas remain inline.
            line_body = source[start:end].strip()
            formula_body = original.strip()
            if line_body == formula_body and kind in {"paragraph", "list_item"}:
                display = True

            span = {
                "start": item_start,
                "end": item_end,
                "role": "formula",
                "renderer": "mcdowell",
                "engine": "katex",
                "latex": latex,
                "value": original,
                "display": display,
                "preserve_payload": True,
            }
            spans.append(span)
            segments.append({
                "kind": "formula",
                "start": item_start,
                "end": item_end,
                "role": "formula",
                "renderer": "mcdowell",
                "engine": "katex",
                "latex": latex,
                "value": original,
                "display": display,
                "preserve_payload": True,
            })
            cursor = max(cursor, item_end)

        if cursor < end:
            append_text(
                cursor,
                end,
                kind="text",
                role=kind,
            )

    # A provider may return content without line endings. Ensure the whole
    # payload is represented exactly once.
    if not segments:
        append_text(0, len(source))

    # Do not allow overlapping ranges to duplicate payload positions.
    segments.sort(key=lambda x: (int(x.get("start", 0)), int(x.get("end", 0)), x.get("kind", "")))

    has_formula = bool(spans)
    has_structured_layout = any(
        block.get("kind") in {"heading", "list_item", "quote", "divider", "spacer"}
        for block in layout_blocks
    )

    return {
        "mode": "mixed" if has_formula else "structured" if has_structured_layout else "text",
        "layout": "mcdowell_document",
        "spans": spans,
        "segments": segments,
        "blocks": layout_blocks,
        "analysis": profile,
        "renderer": "mcdowell",
        "text_engine": "mcdowell",
        "math_engine": "katex",
        "payload_preserved": True,
    }


def _mcdowell_block_contract(source: dict, segmented: dict) -> dict:
    """Expose stable presentation metadata for McDowell without a new route."""
    return {
        "renderer": "mcdowell",
        "engine": "presentation_matrix",
        "layout": segmented.get("layout", "mcdowell_document"),
        "text_engine": "mcdowell",
        "math_engine": "katex",
        "payload_preserved": True,
        "segments": segmented.get("segments", []),
        "spans": segmented.get("spans", []),
        "blocks": segmented.get("blocks", []),
        "source_type": _s(
            source.get("type")
            or source.get("artifact_type")
            or source.get("representation")
            or "text"
        ).lower(),
    }



def _presentation_payload_contract(source: dict, kind: str) -> dict:
    """Expose the complete structured payload; never whitelist away renderer data."""
    raw = _canonical_block_payload(source)
    payload = _quantum_snapshot(raw) if isinstance(raw, dict) else {}
    passthrough = {
        "title", "label", "caption", "description", "url", "href", "x", "y", "x_axis", "y_axis", "axes",
        "series", "data", "columns", "headers", "rows", "cells", "values", "nodes", "edges", "elements", "items",
        "target", "alt", "alt_text", "language", "source", "file", "steps", "expression", "equation", "formula",
        "math", "content", "text", "mime", "duration", "thumbnail", "actions", "parameters", "path", "size", "domain", "icon",
    }
    for key, value in source.items():
        if key in {"payload", "presentation", "metadata"} or value in (None, "", [], {}):
            continue
        if key in passthrough and key not in payload:
            payload[key] = _quantum_snapshot(value)
    return {"kind": kind, "payload": payload, "payload_preserved": True}


def _canonical_block_payload(block: dict) -> dict:
    """Return the full canonical structured payload."""
    source = _as_dict(block)
    payload = source.get("payload")
    if isinstance(payload, dict):
        return payload
    artifact = source.get("artifact")
    if isinstance(artifact, dict):
        nested = artifact.get("payload")
        if isinstance(nested, dict):
            return nested
        return artifact
    return {}

def _canonical_block_payload(block: dict) -> dict:
    """Return the block's canonical structured payload without changing it."""
    source = _as_dict(block)
    payload = source.get("payload")
    if isinstance(payload, dict):
        return payload
    artifact = source.get("artifact")
    if isinstance(artifact, dict):
        nested = artifact.get("payload")
        if isinstance(nested, dict):
            return nested
        return artifact
    return {}


def _canonical_block_id(block: dict, index: int) -> str:
    """Stable identity for one logical renderer block in the single stream."""
    source = _as_dict(block)
    payload = _canonical_block_payload(source)
    explicit = _s(source.get("block_id") or source.get("render_id") or payload.get("block_id"))
    if explicit:
        return explicit
    btype = _s(source.get("type") or source.get("artifact_type") or source.get("representation") or "text").lower()
    # Structured fallback identity is deterministic for this turn's stream.
    return f"quantum-{btype}-{index}"


def _payload_fingerprint(block: dict) -> str:
    """Fingerprint logical payload to prevent artifact/block double rendering."""
    source = _as_dict(block)
    payload = _canonical_block_payload(source)
    btype = _s(source.get("type") or source.get("artifact_type") or source.get("representation") or "text").lower()
    normalized = {"type": btype, "payload": payload}
    try:
        return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    except Exception:
        return hashlib.sha256(repr(normalized).encode("utf-8")).hexdigest()


def _materialize_provider_blocks(payload: dict) -> list[dict]:
    """Merge Provider render_blocks and artifact collections into one block stream."""
    candidates: list[dict] = []
    for block in _as_list(payload.get("render_blocks") or payload.get("blocks")):
        if isinstance(block, dict):
            candidates.append(dict(block))
    for key in ("artifacts", "artifacts_payload"):
        for artifact in _as_list(payload.get(key)):
            if not isinstance(artifact, dict):
                continue
            item = dict(artifact)
            if not item.get("type"):
                item["type"] = item.get("artifact_type") or item.get("representation") or "text"
            candidates.append(item)
    return candidates


def _canonicalize_render_stream(blocks: Any) -> list[dict]:
    """Create one canonical visible stream while preserving structured payloads."""
    if not isinstance(blocks, list):
        return []
    result: list[dict] = []
    by_id: dict[str, dict] = {}
    by_fp: dict[str, dict] = {}
    for index, raw in enumerate(blocks):
        if not isinstance(raw, dict):
            continue
        block = dict(raw)
        block_id = _canonical_block_id(block, index)
        block["block_id"] = block_id
        block["sequence_index"] = index
        fp = _payload_fingerprint(block)
        existing = by_id.get(block_id) or by_fp.get(fp)
        if existing is not None:
            if not _canonical_block_payload(existing) and _canonical_block_payload(block):
                existing["payload"] = deepcopy(_canonical_block_payload(block))
            for key in ("title", "description", "caption", "renderer", "viewer", "language"):
                if not existing.get(key) and block.get(key):
                    existing[key] = block[key]
            continue
        result.append(block)
        by_id[block_id] = block
        by_fp[fp] = block
    stream_ids = [b.get("block_id") for b in result]
    for pos, block in enumerate(result):
        related = list(block.get("related_block_ids") or [])
        for idx in (pos - 1, pos + 1):
            if 0 <= idx < len(result):
                rid = result[idx].get("block_id")
                if rid and rid not in related:
                    related.append(rid)
        block["related_block_ids"] = related
        block["presentation_stream"] = {"version": "quantum_presentation_stream_v2", "stream_ids": stream_ids, "source_block_id": block.get("block_id"), "sequence_index": pos, "single_visible_stream": True}
    return result

def _formula_values_from_payload(payload: dict) -> list[dict]:
    """Build KaTeX formula entries from a formula payload, including step arrays."""
    values: list[dict] = []
    steps = payload.get("steps") if isinstance(payload, dict) else None
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            expression = _s(step.get("expression") or step.get("latex") or step.get("formula") or step.get("value"))
            if expression:
                values.append({"label": _s(step.get("label") or step.get("title")), "value": expression, "latex": _math_normalize_provider_fragment(expression), "display": True})
    else:
        expression = _s(payload.get("formula") or payload.get("equation") or payload.get("expression") or payload.get("math") or payload.get("content")) if isinstance(payload, dict) else ""
        if expression:
            values.append({"label": "", "value": expression, "latex": _math_normalize_provider_fragment(expression), "display": True})
    return values


def _presentation_signal_for_block(block: dict, request: MachineRequest | None = None) -> dict:
    """Build one canonical signal that tells April Web exactly which engine to use."""
    source = dict(block or {})
    payload = _canonical_block_payload(source)
    kind = _s(source.get("type") or source.get("artifact_type") or source.get("representation") or "text").lower()
    kind = {"markdown": "text", "plot": "graph", "chart": "graph", "scene": "diagram", "layout": "diagram", "visual": "diagram", "image": "gallery", "media": "gallery"}.get(kind, kind)
    math_policy = _math_presentation_policy(request)
    signal = {
        "version": "presentation_signal_v4", "kind": kind, "renderer": "", "engine": "", "producer": "QUANTUM_PROCESSOR", "route": "canonical",
        "preserve_payload": True, "payload_unchanged": True, "payload_contract": _presentation_payload_contract(source, kind),
        "block_id": _canonical_block_id(source, int(source.get("sequence_index") or 0)), "sequence_index": int(source.get("sequence_index") or 0),
        "related_block_ids": list(source.get("related_block_ids") or []), "presentation_stream": _quantum_snapshot(source.get("presentation_stream") or {}),
    }
    meta = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    for name in ("continuation", "topic_group", "flow_id", "render_id", "scene_id", "turn_id"):
        value = source.get(name) or meta.get(name)
        if value not in (None, ""):
            signal[name] = _quantum_snapshot(value)
    if kind == "text":
        content = source.get("content") or source.get("text") or source.get("value") or ""
        segmented = _presentation_segments(content, math_policy=math_policy)
        signal.update({"kind": "mixed" if segmented.get("mode") == "mixed" else "structured" if segmented.get("mode") == "structured" else "text", "renderer": "mcdowell", "engine": "presentation_matrix", "text_engine": "mcdowell", "formula_engine": "katex", "presentation": _mcdowell_block_contract(source, segmented), "spans": segmented.get("spans", []), "segments": segmented.get("segments", []), "blocks": segmented.get("blocks", []), "analysis": segmented.get("analysis", {}), "layout": segmented.get("layout", "mcdowell_document"), "delegated_segments": bool(segmented.get("spans") or segmented.get("blocks")), "math_policy": _quantum_snapshot(math_policy)})
    elif kind == "formula":
        formulas = _formula_values_from_payload(payload)
        value = _s(source.get("content") or source.get("text") or source.get("value"))
        if not formulas and value:
            formulas = [{"label": "", "value": value, "latex": _math_normalize_provider_fragment(value), "display": True}]
        signal.update({"kind": "formula", "renderer": "mcdowell", "engine": "katex", "text_engine": "mcdowell", "formula_engine": "katex", "layout": "mcdowell_document", "presentation": {"enabled": bool(formulas), "mode": "formula", "renderer": "mcdowell", "math_engine": "katex", "layout": "mcdowell_document", "formulas": formulas, "payload_preserved": True}, "spans": [{"start": 0, "end": len(f["value"]), "role": "formula", "renderer": "mcdowell", "engine": "katex", "latex": f["latex"], "value": f["value"], "display": bool(f.get("display"))} for f in formulas]})
    elif kind == "table":
        signal.update({"kind": "table", "renderer": "table", "engine": "table", "layout": "table_document", "cell_text_engine": "mcdowell", "cell_math_engine": "katex", "caption_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, "table")})
    elif kind == "graph":
        signal.update({"kind": "graph", "renderer": "graph", "engine": "graph", "layout": "graph_document", "label_text_engine": "mcdowell", "label_math_engine": "katex", "caption_text_engine": "mcdowell", "description_text_engine": "mcdowell", "axis_text_engine": "mcdowell", "axis_math_engine": "katex", "artifact_payload": _presentation_payload_contract(source, "graph")})
    elif kind == "diagram":
        signal.update({"kind": "diagram", "renderer": "graph", "engine": "diagram", "layout": "diagram_document", "label_text_engine": "mcdowell", "label_math_engine": "katex", "caption_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, "diagram")})
    elif kind == "link":
        signal.update({"kind": "link", "renderer": "link", "engine": "link_card", "layout": "link_card_document", "title_text_engine": "mcdowell", "description_text_engine": "mcdowell", "inline_math_engine": "katex", "href_preserved": True, "artifact_payload": _presentation_payload_contract(source, "link")})
    elif kind == "code":
        signal.update({"kind": "code", "renderer": "code", "engine": "syntax", "layout": "code_document", "caption_text_engine": "mcdowell", "description_text_engine": "mcdowell", "language": _s(source.get("language") or payload.get("language"))})
    elif kind == "gallery":
        signal.update({"kind": "gallery", "renderer": "gallery", "engine": "media", "layout": "gallery_document", "caption_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, "gallery")})
    elif kind in {"audio", "video"}:
        signal.update({"kind": kind, "renderer": kind, "engine": "media", "layout": f"{kind}_document", "caption_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, kind)})
    elif kind == "file":
        signal.update({"kind": "file", "renderer": "file", "engine": "file_card", "layout": "file_card_document", "title_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, "file")})
    elif kind == "action":
        signal.update({"kind": "action", "renderer": "action", "engine": "action", "layout": "action_document", "label_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, "action")})
    elif kind == "memory":
        signal.update({"kind": "memory", "renderer": "memory", "engine": "memory", "layout": "memory_document", "label_text_engine": "mcdowell", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, "memory")})
    else:
        signal.update({"kind": kind, "renderer": "mcdowell", "engine": "markdown", "layout": "mcdowell_document", "inline_math_engine": "katex", "description_text_engine": "mcdowell", "artifact_payload": _presentation_payload_contract(source, kind)})
    signal["math_policy"] = _quantum_snapshot(math_policy)
    return signal

def _attach_presentation_signals(blocks: Any, request: MachineRequest | None = None) -> list[dict]:
    enriched: list[dict] = []
    canonical_blocks = _canonicalize_render_stream(blocks)
    for block in canonical_blocks if isinstance(canonical_blocks, list) else []:
        if not isinstance(block, dict):
            continue
        clean = dict(block)
        presentation = _presentation_signal_for_block(clean, request=request)
        clean["presentation"] = presentation
        enriched.append(clean)
    return enriched


def _ensure_presentation_signals(blocks: Any, request: MachineRequest | None = None) -> list[dict]:
    """Recompute the canonical signal from the current block payload.

    An existing presentation_signal_v3 is metadata, not an authority. Rebuilding
    it here prevents stale/partial Provider or persisted signals from bypassing
    the Quantum Processor's current McDowell/KaTeX and artifact render contract.
    """
    result: list[dict] = []
    canonical_blocks = _canonicalize_render_stream(blocks)
    for block in canonical_blocks if isinstance(canonical_blocks, list) else []:
        if not isinstance(block, dict):
            continue
        clean = dict(block)
        clean["presentation"] = _presentation_signal_for_block(clean, request=request)
        result.append(clean)
    return result

def _response(value: Any, request: MachineRequest | None = None) -> MachineResponse:
    """Decode Provider output and materialize all structured artifacts into one stream."""
    payload = _decode_provider_payload(value)
    fields = MachineResponse.__dataclass_fields__
    allowed = {k: v for k, v in payload.items() if k in fields}
    answer = _clean_text_value(payload.get("answer") or payload.get("content") or payload.get("response"))
    blocks = _materialize_provider_blocks(payload)
    blocks = _promote_embedded_structured_blocks(blocks)
    if answer and not any(isinstance(b, dict) and _s(b.get("type") or b.get("artifact_type")).lower() in {"text", "markdown"} for b in blocks):
        blocks.insert(0, {"type": "text", "content": answer, "text": answer, "renderer": "TextBlock", "viewer": "TextBlock", "scene_contract": True})
    blocks = _finalize_quantum_visible_stream(
        _clean_render_blocks(blocks),
        answer=answer,
        request=request,
    )
    allowed["render_blocks"] = blocks
    if answer:
        allowed["answer"] = answer
        allowed["content"] = answer
    metadata = dict(allowed.get("metadata") or {}) if isinstance(allowed.get("metadata"), dict) else {}
    metadata["quantum_matrix"] = {"owner": "QUANTUM_PROCESSOR", "version": PROCESSOR_VERSION, "block_types": [_s(b.get("type") or b.get("artifact_type")).lower() for b in blocks if isinstance(b, dict)], "render_block_count": len(blocks), "composer_engine": "quantum_canonical_answer_composer_v2", "information_preserved": True, "machine_fields_transport_only": True, "scoring": False, "triggers": False}
    allowed["metadata"] = metadata
    return MachineResponse(**allowed)

def _canonicalize(
    user_id: str,
    response: MachineResponse,
    state: dict,
    semantic: dict,
    cognition: dict,
    decision: dict,
    request: MachineRequest,
    internal_context: bool = False,
) -> dict:
    answer = _clean_text_value(
        response.answer
    ) or _clean_text_value(
        response.content
    ) or _clean_text_value(
        response.response
    )

    if not answer:
        raise RuntimeError("Quantum canonicalization blocked: empty MachineResponse answer")

    # Final human-field invariant: SceneContract.answer/content can only contain
    # plain human text, never the serialized MachineResponse envelope.
    decoded_answer = _decode_json_envelope(answer)
    if isinstance(decoded_answer, dict):
        answer = _clean_text_value(decoded_answer)
    answer = _s(answer)
    if not answer:
        raise RuntimeError("Quantum canonicalization blocked: decoded answer is empty")

    response.answer = answer
    response.content = answer

    # Summary remains a memory/context field supplied by the Provider or an
    # upstream semantic engine. The Executor never fabricates a summary from
    # the visible answer.
    response.summary = _clean_text_value(response.summary)

    response.render_blocks = _finalize_quantum_visible_stream(
        _clean_render_blocks(list(getattr(response, "render_blocks", []) or [])),
        answer=answer,
        request=request,
    )

    scope = _user_scope(state, user_id)
    response.metadata = dict(response.metadata or {})
    response.metadata.update({
        "processor_version": PROCESSOR_VERSION,
        "single_route": True,
        "provider_calls_per_request": 1,
        "visible_answer_guaranteed": True,
        "artifact_preservation": True,
        "trigger_routing": False,
        "score_routing": False,
        "identity_scope": deepcopy(scope),
    })
    response.quantum_state = request.quantum_state
    response.conversation_space = {
        "identity_scope": deepcopy(scope),
        "current_turn": {
            "user": _s(request.conversation.get("current_request")),
            "april": {
                "answer": answer,
                "render_blocks": response.render_blocks,
                "artifacts": list(getattr(response, "artifacts", []) or []),
                "summary": response.summary,
            },
        }
    }
    response.executor_semantic = semantic
    response.executor_cognition = cognition
    response.executor_response_decision = decision

    if not any(
        isinstance(block, dict)
        and _s(block.get("type") or block.get("artifact_type")).lower() in {"text", "markdown"}
        and bool(_clean_text_value(block.get("content") or block.get("text") or block.get("value")))
        for block in response.render_blocks
    ):
        response.render_blocks.insert(0, {
            "type": "text",
            "artifact_type": "text",
            "content": answer,
            "text": answer,
            "renderer": "TextBlock",
            "viewer": "TextBlock",
            "scene_contract": True,
            "source": "quantum_processor",
        })
        response.render_blocks = _finalize_quantum_visible_stream(
            response.render_blocks,
            answer=answer,
            request=request,
        )

    scene = build_machine_scene(response)
    provider_blocks = _finalize_quantum_visible_stream(
        list(getattr(response, "render_blocks", []) or []),
        answer=answer,
        request=request,
    )
    response.render_blocks = provider_blocks

    try:
        scene.blocks = provider_blocks
        scene.contract.blocks = provider_blocks
        scene.contract.render_blocks = list(provider_blocks)
        scene.contract.metadata = dict(scene.contract.metadata or {})
        scene.contract.metadata["identity_scope"] = deepcopy(scope)
        scene.contract.metadata["renderer_state"] = {
            "active_scene": scene.contract.active_scene,
            "block_types": [
                _s(
                    block.get("type")
                    or block.get("artifact_type")
                    or block.get("representation")
                ).lower()
                for block in provider_blocks
                if isinstance(block, dict)
            ],
            "continuation": bool(request.quantum_state.get("continuation")),
            "decision_owner": "QUANTUM_PROCESSOR",
            "single_route": True,
        }

        if hasattr(scene.contract, "supported_payloads"):
            supported = list(getattr(scene.contract, "supported_payloads", []) or [])
            for artifact in list(getattr(response, "artifacts", []) or []):
                if artifact not in supported:
                    supported.append(artifact)
            scene.contract.supported_payloads = supported
    except Exception:
        pass

    contract = build_scene_contract(scene)

    # SceneContract is the release boundary: force the canonical human answer
    # into answer/content, keep summary isolated, and keep every renderer block.
    try:
        contract.answer = answer
        contract.content = answer
        contract.summary = response.summary
        contract.render_blocks = list(provider_blocks)
        contract.blocks = list(provider_blocks)
    except Exception:
        pass

    render_blocks = list(getattr(contract, "render_blocks", []) or [])
    if not render_blocks:
        render_blocks = provider_blocks
        try:
            contract.render_blocks = render_blocks
        except Exception:
            pass

    if not internal_context:
        update_dialog_context(user_id, semantic)
    update_scene_context(
        user_id,
        contract,
        current_request=_s(request.conversation.get("current_request")),
        answer=answer,
        internal_context=internal_context,
    )
    request_meta = _request_metadata(request)

    # One canonical visible presentation stream is released to Web.
    stream = [
        {
            "block_id": _s(block.get("block_id")),
            "type": _s(block.get("type") or block.get("artifact_type") or "text").lower(),
            "sequence_index": int(block.get("sequence_index") or i),
            "related_block_ids": list(block.get("related_block_ids") or []),
        }
        for i, block in enumerate(render_blocks)
        if isinstance(block, dict)
    ]
    try:
        contract.metadata = dict(contract.metadata or {})
        contract.metadata["presentation_stream"] = {
            "version": "quantum_presentation_stream_v1",
            "nodes": stream,
            "single_visible_stream": True,
            "answer_is_fallback": True,
        }
    except Exception:
        pass

    try:
        contract.metadata = dict(contract.metadata or {})
        contract.metadata["quantum_visible_stream_policy"] = {
            "version": "quantum_visible_stream_v3",
            "single_logical_answer": True,
            "visible_block_count": len(render_blocks),
            "visible_block_types": [
                _s(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
                for block in render_blocks if isinstance(block, dict)
            ],
            "internal_signals_hidden": True,
            "structured_outputs_authorized_by_request": True,
            "duplicate_renderer_instances_collapsed": True,
        }
    except Exception:
        pass

    return {
        "transport_contract": "scene_first",
        "provider_contract": "fiber_v3_quantum",
        "machine_request": request,
        "machine_response": response,
        "machine_scene": scene,
        "scene_contract": contract,
        "answer": answer,
        "content": answer,
        "summary": response.summary,
        "render_blocks": render_blocks,
        "artifacts": list(getattr(response, "artifacts", []) or []),
        "single_route": True,
        "provider_calls_per_request": 1,
        "quantum_state": request.quantum_state,
        "energy_acceleration": request_meta.get("energy_acceleration", {}),
        "visible_answer_guaranteed": True,
        "artifact_preservation": True,
        "identity_scope": deepcopy(scope),
    }

def _validate_quantum_release(request: MachineRequest) -> None:
    constraints = getattr(request, "constraints", {})
    if not isinstance(constraints, dict):
        raise RuntimeError("Quantum release blocked: constraints missing")

    if constraints.get("one_provider_call") is not True:
        raise RuntimeError("Quantum release blocked: one_provider_call invariant failed")

    if constraints.get("provider_input_token_budget") != 900:
        raise RuntimeError("Quantum release blocked: provider input budget invariant failed")

    response_budget = getattr(request, "response_output_tokens", 0)
    if not isinstance(response_budget, int) or not (OUTPUT_MIN_TOKENS <= response_budget <= OUTPUT_MAX_TOKENS):
        raise RuntimeError("Quantum release blocked: adaptive response budget invariant failed")

    if getattr(request, "provider_calls_allowed", 1) != 1:
        raise RuntimeError("Quantum release blocked: provider call count invariant failed")

    if getattr(request, "single_route", True) is not True:
        raise RuntimeError("Quantum release blocked: single_route invariant failed")

    metadata = constraints.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("Quantum release blocked: metadata bridge missing")
    identity_scope = metadata.get("identity_scope")
    if not isinstance(identity_scope, dict) or not identity_scope.get("user_id"):
        raise RuntimeError("Quantum release blocked: identity scope missing")

async def execute(user_id, chat_id=None, text="", run_with_activity=None, **kwargs):
    """
    ONE ROUTE / UNIFIED MATRIX PROCESSOR / ONE COLLAPSE / ONE PROVIDER CALL.

    The ten quantumized modules are not ten routes. They are ten independent
    evidence lenses feeding one processor field. The processor arbitrates the
    combined field, creates one MachineRequest, then uses the existing Provider
    path once and the existing C-Artifact/SceneContract path once.
    """
    state = get_state(user_id)
    state = state if isinstance(state, dict) else {}
    state["user_id"] = _s(user_id)
    internal_context = bool(
        kwargs.get("internal_context")
        or kwargs.get("internal_turn")
        or str(kwargs.get("request_source") or "").strip().lower()
        in {"internal_visual", "internal_visual_analysis", "passive_visual_helper"}
    )
    scope = _user_scope(state, user_id)
    state["_request_user_id"] = _s(user_id)
    history = state.get("dialog", []) if isinstance(state.get("dialog"), list) else []
    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    dialog_state = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}

    build_deephub_context(user_id, text, state)
    context_packet = state.get("_executor_context_packet")
    if not isinstance(context_packet, dict):
        context_packet = build_executor_context_packet(state)
    context_evidence = state.get("_machine_context", {}).get("quantum_evidence", {})
    if not isinstance(context_evidence, dict):
        context_evidence = {}

    active_flow = state.get("active_flow") if isinstance(state.get("active_flow"), dict) else {}
    dialog_state = state.get("scene_state") if isinstance(state.get("scene_state"), dict) else {}
    history = state.get("dialog", []) if isinstance(state.get("dialog"), list) else []

    # One canonical heavy Interpretation pass per turn. Semantic Core reuses
    # the same evidence packet instead of re-running Stanza/NLI.
    interpretation = interpret_request(
        text,
        cognition=state.get("cognition", {}) if isinstance(state.get("cognition"), dict) else {},
        semantic={},
        history=history,
        state=state,
    ) or {}

    # Canonical immediate-scene continuity measurement. This uses the existing
    # QUANTUM_DIALOGUE_ENGINE and feeds its structured evidence into Semantic
    # Core and the processor control plane. No local word triggers are used.
    scene_continuity = _scene_continuity_engine(
        text=text,
        state=state,
        history=history,
    )
    interpretation["quantum_scene_continuity"] = _quantum_snapshot(scene_continuity)
    # Canonical dialogue-vector bridge: relation is resolved before routing.
    # Downstream engines receive the same decision; no second topic router exists.
    if isinstance(interpretation.get("dialogue_vector"), dict):
        interpretation["quantum_dialogue_vector"] = _quantum_snapshot(
            interpretation["dialogue_vector"]
        )
        state["_quantum_dialogue_vector"] = _quantum_snapshot(
            interpretation["dialogue_vector"]
        )

    # Freeze canonical interpretation measurements for downstream engines.
    field = interpretation.get("quantum_interpretation_field", {})
    if isinstance(field, dict):
        dialogue_field = field.get("dialogue")
        representation_field = field.get("representation")
        if isinstance(dialogue_field, dict) and isinstance(
            dialogue_field.get("semantic_measurement"), dict
        ):
            interpretation["quantum_dialogue_measurement"] = dialogue_field["semantic_measurement"]
        if isinstance(representation_field, dict):
            interpretation["quantum_representation_measurement"] = representation_field

    semantic = semantic_analyze(
        text=text,
        state=state,
        history=history,
        active_flow=active_flow,
        dialog_state=dialog_state,
        interpreted=interpretation,
    ) or {}

    reasoning = build_reasoning_state(text=text, semantic=semantic, state=state)
    cognition = analyze_cognition(
        text=text, semantic=semantic, reasoning=reasoning, state=state
    ) or {}

    interpretation["cognition"] = _quantum_snapshot(cognition)

    _merge_evidence_fields(semantic, (interpretation,))
    semantic["quantum_interpretation_evidence"] = interpretation
    if isinstance(interpretation.get("quantum_representation_measurement"), dict):
        semantic["quantum_representation_measurement"] = _quantum_snapshot(
            interpretation["quantum_representation_measurement"]
        )
    if isinstance(interpretation.get("quantum_dialogue_measurement"), dict):
        semantic["quantum_dialogue_measurement"] = _quantum_snapshot(
            interpretation["quantum_dialogue_measurement"]
        )

    intent = detect_intent(text, state) or {}
    intent_ai = await detect_intent_ai(text, state)
    intent_ai = intent_ai if isinstance(intent_ai, dict) else {}
    resolver = resolve_input(history, state) or {}
    focus_intent = build_focus_intent_state(text, state) or {}

    intent_ai["provider_calls"] = 0
    intent_ai["decision_owner"] = "QUANTUM_PROCESSOR"

    _merge_evidence_fields(semantic, (intent, intent_ai, resolver))
    semantic["quantum_intent_evidence"] = {
        "intent_system": intent,
        "intent_ai": intent_ai,
        "intent_resolver": resolver,
        "focus": focus_intent,
    }

    router_context = {
        "semantic": semantic,
        "cognition": cognition,
        "reasoning": reasoning,
        "response_decision": {},
        "visual_reference": {},
        "state": state,
        "quantum_evidence": {
            "context": context_evidence,
            "interpretation": interpretation,
            "intent": intent,
            "intent_ai": intent_ai,
            "resolver": resolver,
        },
    }
    router_hint = await route_request(text, router_context)
    router_evidence = semantic.get("quantum_router_evidence", {})
    if not isinstance(router_evidence, dict):
        router_evidence = {}

    router_system = decide_action(text, history) or {}

    _merge_evidence_fields(semantic, (router_evidence, router_system))
    semantic["quantum_router_evidence"] = {
        "router": router_evidence,
        "router_system": router_system,
        "compatibility_hint": router_hint,
    }

    visual = build_visual_reference(
        semantic=semantic, cognition=cognition, text=text, state=state
    ) or {}

    # -------------------------------------------------------------
    # FOUR NEW QUANTUM EVIDENCE LENSES
    # These do not own routing or memory. They only contribute compact,
    # JSON-safe evidence to the single processor field.
    # -------------------------------------------------------------
    experience = build_experience_evidence(
        text=text,
        state=state,
    ) or {}

    experience_manager_state = get_experience(
        user_id
    ) or {}

    # The experience manager is a short-lived per-user signal source.
    # Only the latest compact state is admitted to the quantum field.
    experience_manager_evidence = {
        "user_id": _s(experience_manager_state.get("user_id") or user_id),
        "latest": _quantum_snapshot(
            experience_manager_state.get("latest", {})
        ),
        "has_experience": bool(experience_manager_state.get("events")),
        "temporary": True,
        "machine_only": True,
        "decision_owner": "QUANTUM_PROCESSOR",
        "provider_calls": 0,
    }

    goal_evidence = build_goal_evidence(
        text=text,
        state=state,
        semantic=semantic,
    ) or {}

    decision = build_response_decision(
        semantic=semantic,
        cognition=cognition,
        state=state,
        visual_reference=visual,
    ) or {}

    # Canonical dynamic-memory evidence is resolved exactly once for this turn,
    # after interpretation/semantic measurement and before the Quantum Control
    # Plane is collapsed. It remains evidence only; it does not create a route
    # or independently decide dialogue state.
    retrieval_mode = (
        "memory_query"
        if _s(interpretation.get("dialog_act")).lower() == "memory_query"
        else "semantic"
    )
    dynamic_memory = query_dynamic_memory(
        user_id,
        text,
        limit=8,
        retrieval_mode=retrieval_mode,
    )
    if not isinstance(dynamic_memory, dict):
        dynamic_memory = {}

    semantic["quantum_dynamic_memory_evidence"] = _quantum_snapshot(dynamic_memory)
    semantic["dynamic_memory_available"] = bool(dynamic_memory.get("matches"))

    # ONE authoritative memory-understanding pass lives inside the Quantum
    # Processor. Never accept a stale/legacy memory packet from Interpretation
    # as the final result: that was the source of the context-loss regression.
    previous_pair_evidence = _dialogue_evidence(text, semantic, cognition, decision, state)
    previous_user = _s(previous_pair_evidence.get("previous_user") or state.get("last_user_turn"))
    previous_april = _s(previous_pair_evidence.get("previous_april") or state.get("last_april_turn"))
    visual_scene = _as_dict(
        state.get("current_visual_scene")
        or state.get("active_visual_scene")
        or state.get("active_scene_contract")
    )
    legacy_dialogue_relation_before_memory = _s(
        _as_dict(interpretation.get("dialogue_vector")).get("relation")
    ).upper()

    memory_understanding = QUANTUM_MEMORY_UNDERSTANDING_ENGINE.analyze(
        text,
        previous_user=previous_user,
        previous_assistant=previous_april,
        active_topic=_s(state.get("active_topic") or state.get("current_topic")),
        active_goal=_s(state.get("active_goal")),
        visual_scene=visual_scene,
        dialog_history=history,
        dynamic_memory={
            **dynamic_memory,
            "memory_timeline": state.get("memory_timeline", {}),
        },
    ) or {}
    semantic["memory_understanding"] = _quantum_snapshot(memory_understanding)
    semantic["quantum_memory_understanding"] = _quantum_snapshot(memory_understanding)
    print("🧠 QMEM GATE:", {
        "needed": bool(memory_understanding.get("needed")),
        "active": bool(memory_understanding.get("active")),
        "relation": _s(memory_understanding.get("relation")),
        "independent_safe": bool(memory_understanding.get("independent_safe", False)),
        "structural_reference": bool(_as_dict(memory_understanding.get("gate")).get("structural_reference")),
        "visual_reference_kind": _s(_as_dict(memory_understanding.get("gate")).get("visual_reference_kind")),
        "operation_dependency": bool(_as_dict(memory_understanding.get("gate")).get("operation_dependency")),
    })
    state["_quantum_memory_understanding"] = _quantum_snapshot(memory_understanding)

    # Promote the memory engine's resolved discourse back into the canonical
    # Interpretation contract so the existing provider/router/render pipeline
    # receives the same context without creating a second route.
    if isinstance(memory_understanding, dict) and memory_understanding.get("active"):
        resolved_request = _s(memory_understanding.get("resolved_request"))
        memory_ref = _as_dict(memory_understanding.get("reference"))
        memory_ctx = _as_dict(memory_understanding.get("dialogue_context"))
        memory_vctx = _as_dict(memory_understanding.get("visual_context"))
        packet = _as_dict(semantic.get("quantum_interpretation_evidence"))
        contract = _as_dict(packet.get("dialogue_contract"))
        vector = _as_dict(interpretation.get("dialogue_vector"))
        if memory_understanding.get("continuation") or memory_ref.get("resolved"):
            vector.update({
                "relation": "CONTINUE_TOPIC",
                "subtype": "REFERENCE_OR_DEVELOPMENT" if memory_ref.get("resolved") else "MEMORY_CONTEXT_DEVELOPMENT",
                "continuation": True,
                "delta_mode": "extend",
                "avoid_repeat": True,
                "reference_resolution": {
                    "resolved": bool(memory_ref.get("resolved")),
                    "target": _s(memory_ref.get("target")),
                    "confidence": float(memory_ref.get("confidence", 0.0) or 0.0),
                    "source": "QUANTUM_MEMORY_UNDERSTANDING_ENGINE",
                },
                "resolved_request": resolved_request,
                "previous_user_turn": _s(memory_ctx.get("previous_user")),
                "previous_april_turn": _s(memory_ctx.get("previous_assistant")),
            })
            interpretation["dialogue_vector"] = _quantum_snapshot(vector)
            interpretation["resolved_request"] = resolved_request
            contract.update({
                "continuation": True,
                "reference_to_previous": bool(memory_ref.get("resolved")),
                "context_dependency": "reference" if memory_ref.get("resolved") else "continuation",
                "previous_user_turn": _s(memory_ctx.get("previous_user")),
                "previous_april_turn": _s(memory_ctx.get("previous_assistant")),
                "active_topic": _s(memory_ref.get("target") or memory_ctx.get("active_topic")),
                "resolved_request": resolved_request,
            })
            if memory_vctx.get("scene_id"):
                contract["resolved_scene"] = {
                    "scene_id": _s(memory_vctx.get("scene_id")),
                    "relation": "current_scene",
                    "source": "QUANTUM_MEMORY_UNDERSTANDING_ENGINE",
                }
            packet["dialogue_contract"] = contract
            packet["dialogue_vector"] = vector
            semantic["quantum_interpretation_evidence"] = _quantum_snapshot(packet)
        memory_ref_log = _as_dict(memory_understanding.get("reference"))
        memory_collapse_log = _as_dict(memory_understanding.get("collapse"))
        memory_auth_log = _as_dict(memory_understanding.get("authorization"))
        print("🧠 QUANTUM MEMORY UNDERSTANDING:", {
            "active": bool(memory_understanding.get("active")),
            "needed": bool(memory_understanding.get("needed")),
            "relation": _s(memory_understanding.get("relation")),
            "target": _s(memory_ref_log.get("target")),
            "target_kind": _s(memory_ref_log.get("target_kind")),
            "target_index": memory_ref_log.get("target_index"),
            "confidence": float(memory_ref_log.get("confidence", 0.0) or 0.0),
            "authorized": bool(memory_auth_log.get("memory_context_authorized") or memory_collapse_log.get("authorized")),
            "scene_id": _s(_as_dict(memory_understanding.get("visual_context")).get("scene_id")),
            "selected_pair_source": _s(_as_dict(memory_understanding.get("memory_sources")).get("selected_pair_source")),
            "matrix": {
                "version": _s(_as_dict(memory_understanding.get("quantum_memory_matrix")).get("version")),
                "active_cells": int(_as_dict(memory_understanding.get("quantum_memory_matrix")).get("active_cells") or 0),
                "signals": int(_as_dict(memory_understanding.get("quantum_memory_matrix")).get("signals") or 0),
            },
        })

        # Explicitly expose cross-engine disagreement so the next test tells us
        # whether the discrepancy is in interpretation, memory understanding,
        # or the final control-plane collapse.
        legacy_relation = legacy_dialogue_relation_before_memory
        memory_relation = _s(memory_understanding.get("relation")).upper()
        control_preview = _s(memory_collapse_log.get("relation")).upper()
        if legacy_relation and memory_relation and legacy_relation != memory_relation:
            print("⚠️ QUANTUM CONTEXT MISMATCH:", {
                "legacy_dialogue_relation": legacy_relation,
                "memory_relation": memory_relation,
                "memory_collapse_relation": control_preview,
                "memory_authorized": bool(memory_auth_log.get("memory_context_authorized") or memory_collapse_log.get("authorized")),
                "resolution_owner": "QUANTUM_PROCESSOR",
            })
        print("🧭 QUANTUM MEMORY ROUTE SYNC:", {
            "order": [
                "INTERPRETATION",
                "SEMANTIC",
                "DYNAMIC_MEMORY",
                "QUANTUM_MEMORY_UNDERSTANDING",
                "CONTROL_PLANE_COLLAPSE",
                "MACHINE_REQUEST",
                "PROVIDER",
                "SCENE_CONTRACT",
                "WEB",
            ],
            "single_route": True,
            "provider_calls": 0,
            "render_signals_mutated": False,
        })

    # One authoritative control plane for dialogue, representation, memory relation,
    # capability delegation, and single-route ownership. Individual engines remain
    # evidence sources; downstream code consumes this collapsed state.
    control_plane = _build_processor_control_plane(
        text=text,
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        dynamic_memory=dynamic_memory,
        memory_understanding=memory_understanding,
    )
    print("🧠 QUANTUM MEMORY MATRIX:", {
        "window": dynamic_memory.get("window_days"),
        "matches": len(dynamic_memory.get("matches", []) or []),
        "matrix_version": dynamic_memory.get("matrix_version"),
        "decision_owner": "QUANTUM_PROCESSOR",
        "memory_role": "evidence_only",
    })
    state["_quantum_memory_sequence"] = {
        "version": "QMEM-SEQUENCE-V3",
        "stages": [
            "INTERPRETATION","SEMANTIC","DYNAMIC_MEMORY",
            "QUANTUM_MEMORY_UNDERSTANDING","CONTROL_PLANE_COLLAPSE",
            "MACHINE_REQUEST","PROVIDER","SCENE_CONTRACT","WEB",
        ],
        "memory_relation": _s(memory_understanding.get("relation")),
        "canonical_mode": _s(control_plane.get("mode")),
        "memory_authorized": bool(
            _as_dict(memory_understanding.get("authorization")).get("memory_context_authorized")
        ),
        "single_route": True,
        "render_signals_mutated": False,
    }
    state["_turn_dialogue_relation"] = {
        "relation": _s(control_plane.get("relation")),
        "scene_id": _s(_as_dict(control_plane.get("resolved_scene")).get("scene_id")),
        "continuation": bool(control_plane.get("continuation")),
        "reference_to_previous": bool(control_plane.get("reference_to_previous")),
        "same_scene": bool(
            control_plane.get("relation") == "current_scene"
            and _as_dict(control_plane.get("resolved_scene")).get("scene_id")
        ),
        "context_dependency": bool(control_plane.get("context_dependency")),
    }

    processor_context = build_processor_execution_context({
        "state": state,
        "context": context_evidence,
        "semantic": semantic,
        "cognition": cognition,
        "interpretation": interpretation,
        "intent": intent,
        "intent_ai": intent_ai,
        "resolver": resolver,
        "router": router_evidence,
        "router_system": router_system,
        "decision": decision,
        "experience": experience,
        "experience_manager": experience_manager_evidence,
        "goal": goal_evidence,
        "visual_reference": visual,
        "dynamic_memory": dynamic_memory,
        "memory_understanding": memory_understanding,
        "control_plane": control_plane,
    })

    quantum_field = _build_quantum_field(
        user_id=user_id,
        text=text,
        state=state,
        context=context_evidence,
        interpretation=interpretation,
        semantic=semantic,
        cognition=cognition,
        intent=intent,
        intent_ai=intent_ai,
        resolver={**resolver, "focus": focus_intent},
        router=router_evidence,
        router_system=router_system,
        decision=decision,
        experience=experience,
        experience_manager=experience_manager_evidence,
        goal=goal_evidence,
        visual_reference=visual,
        memory_understanding=memory_understanding,
    )

    detached_quantum_field = _quantum_snapshot(quantum_field)
    state["_quantum_evidence_field"] = detached_quantum_field
    state["_quantum_processor_context"] = _quantum_snapshot(processor_context)
    semantic["quantum_evidence_field"] = _quantum_snapshot(quantum_field)
    semantic["processor_context"] = _quantum_snapshot(processor_context)
    semantic["decision_owner"] = "QUANTUM_PROCESSOR"
    semantic["provider_calls"] = 0
    semantic["parallel_route"] = False
    semantic["quantum_processor_version"] = PROCESSOR_VERSION
    semantic["semantic_decision_owner"] = "QUANTUM_PROCESSOR"

    request = _make_request(text, semantic, cognition, decision, state, visual, control=control_plane)
    request.quantum_state["evidence_channels"] = 15
    request.quantum_state["evidence_field"] = quantum_field
    request_meta = _request_metadata(request)
    request_meta.update({
        "dynamic_memory_available": bool(dynamic_memory.get("matches")),
        "dynamic_memory_match_count": len(dynamic_memory.get("matches") or []),
        "quantum_evidence_channels": 15,
        "quantum_evidence_field_version": PROCESSOR_VERSION,
        "provider_calls_per_request": 1,
        "single_route": True,
        "requested_outputs": list(request.requested_outputs),
        "dialogue_vector": _quantum_snapshot(
            interpretation.get("dialogue_vector", {})
        ),
        "dialogue_delta": _quantum_snapshot(
            interpretation.get("dialogue_delta", {})
        ),
        "render_continuity": _quantum_snapshot(
            interpretation.get("render_continuity", {})
        ),
        "representation_plan": _quantum_snapshot(
            request.constraints.get("representation_plan", {})
        ),
        "representation_audit": _quantum_snapshot(
            request.constraints.get("representation_plan", {}).get("audit", {})
        ),
        "processor_context": processor_context,
        "memory_understanding": _quantum_snapshot(memory_understanding),
    })
    request.constraints["metadata"] = request_meta

    energy_profile = build_quantum_acceleration_profile(
        user_id,
        flow_id=(state.get("flow_id") if isinstance(state, dict) else "") or "",
        semantic=semantic,
        cognition=cognition,
        decision=decision,
        state=state,
        outputs=request.requested_outputs,
        visual=visual,
    )
    request = apply_quantum_acceleration(request, energy_profile)
    acceleration_check = validate_quantum_acceleration(request, energy_profile)
    if not acceleration_check.get("ok"):
        raise RuntimeError("Quantum energy acceleration invariant failed")

    _validate_quantum_release(request)

    representation_plan = request.constraints.get("representation_plan", {})
    requested_outputs = list(getattr(request, "requested_outputs", []) or [])
    if representation_plan.get("current_request_authoritative") is not True:
        raise RuntimeError("Quantum release blocked: representation authority invariant failed")
    blocked_outputs = set(
        (representation_plan.get("constraints") or {}).get("negative", []) or []
    )
    if any(output in blocked_outputs for output in requested_outputs):
        raise RuntimeError("Quantum release blocked: contradictory representation plan")

    # Final quantum release audit: 15 evidence lenses, one request, one provider.
    #
    # IMPORTANT:
    # The 64-signal budget field is owned by the MachineRequest created by
    # _make_request(). It must never be read from execute()'s local scope,
    # because that would make the processor depend on a variable that only
    # exists inside _make_request(). Reading the canonical field from the
    # request keeps the budget calculation single-source and preserves the
    # single-route processor invariant.
    quantum_budget_field = (
        getattr(request, "quantum_state", {}) or {}
    ).get("quantum_budget_field", {})
    if not isinstance(quantum_budget_field, dict):
        raise RuntimeError("Quantum release blocked: canonical 64-signal budget field missing")

    # Final quantum release audit: 15 evidence lenses, one request, one provider.
    request.constraints.setdefault("metadata", {})["quantum_release_audit"] = {
        "evidence_channels": 15,
        "decision_owner": "QUANTUM_PROCESSOR",
        "single_route": True,
        "provider_calls": 1,
        "response_budget": getattr(request, "response_output_tokens", 0),
        "response_budget_range": [OUTPUT_MIN_TOKENS, OUTPUT_MAX_TOKENS],
        "response_budget_canonical": True,
        "quantum_cores": 8,
        "quantum_lanes_per_core": 8,
        "quantum_signal_count": 64,
        "response_budget_mode": "continuous_64_signal_scale",
        "input_budget": 900,
        "input_budget_mode": "logical_compaction",
        "quantum_semantic_engines": [
            "spacy_linguistic",
            "sentence_transformers_embedding",
            "transformers_nli",
            "context_vector_fusion",
        ],
        "word_trigger_routing": False,
        "fallback_semantics": False,
        "quantum_budget_field": quantum_budget_field,
        "experience": True,
        "experience_manager": True,
        "goal_engine": True,
        "visual_reference_system": True,
        "control_plane_version": control_plane.get("version"),
        "control_plane_single_route": bool(control_plane.get("single_route")),
    }

    provider_result = await generate_text(
        request,
        max_output_tokens=request.response_output_tokens,
    )
    response = _response(provider_result, request)

    # Canonical presentation audit: proves the processor actually emitted
    # renderer signals before the SceneContract release boundary.
    presentation_blocks = []
    for block in list(getattr(response, "render_blocks", []) or []):
        if isinstance(block, dict):
            presentation = block.get("presentation")
            if isinstance(presentation, dict):
                presentation_blocks.append({
                    "type": _s(block.get("type") or block.get("artifact_type") or "text"),
                    "kind": _s(presentation.get("kind")),
                    "renderer": _s(presentation.get("renderer")),
                    "engine": _s(presentation.get("engine")),
                    "spans": len(presentation.get("spans") or []),
                    "segments": len(presentation.get("segments") or []),
                    "math_engine": _s(presentation.get("math_engine") or presentation.get("formula_engine")),
                    "payload_unchanged": bool(presentation.get("payload_unchanged", False)),
                })
    request.constraints.setdefault("metadata", {})["presentation_matrix_audit"] = {
        "version": "presentation_signal_v3",
        "decision_owner": "QUANTUM_PROCESSOR",
        "math_engine_version": "quantum_math_structure_engine_v2",
        "composer_engine_version": "quantum_canonical_answer_composer_v1",
        "blocks": presentation_blocks,
        "signal_count": len(presentation_blocks),
        "payload_preserved": True,
    }

    request.constraints.setdefault("metadata", {})["visible_answer_audit"] = {
        "answer_present": bool(_s(response.answer) or _s(response.content) or _s(response.response)),
        "render_blocks_before_canonicalize": len(getattr(response, "render_blocks", []) or []),
        "artifacts_preserved": len(getattr(response, "artifacts", []) or []),
        "text_block_guaranteed": any(
            isinstance(block, dict)
            and _s(block.get("type") or block.get("artifact_type")).lower() in {"text", "markdown"}
            for block in getattr(response, "render_blocks", []) or []
        ),
    }

    return _canonicalize(
        user_id, response, state, semantic, cognition, decision, request,
        internal_context=internal_context,
    )
