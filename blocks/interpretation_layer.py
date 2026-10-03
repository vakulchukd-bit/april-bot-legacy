"""
APRIL — TEST ONLY: Unified Interpretation Layer v1
===================================================

This file is intentionally independent from the currently installed
interpretation_layer.py. Keep the production file untouched.

Purpose
-------
Replace trigger/keyword-driven dialogue handling with one semantic cycle:

    CURRENT USER REQUEST
            |
            v
    SEMANTIC MEANING ENGINE
            |
            v
    DIALOGUE RELATION ENGINE
       NEW / CONTINUE / RECALL
            |
            v
    STRUCTURED CONTEXT ENGINE
       subject + goal + data + artifact + history
            |
            v
    CANONICAL PROVIDER HANDOFF
            |
            v
    OpenAI / provider_router
            |
            v
    STRUCTURED RESPONSE
            |
            v
    CANONICAL DIALOGUE MEMORY
            |
            v
       next user turn

Design rules
------------
1. No trigger dictionaries for dialogue understanding.
2. No "его/её/он/оно/это" routing rules.
3. No arbitrary entity-bag memory.
4. Structured OpenAI responses are stored as first-class dialogue records.
5. Data is preserved independently of representation.
6. Representation changes do not change the semantic subject.
7. A week/month/year/custom range can contain any number of points.
8. Parent 12h dialogue sequence and topic/task branches remain separate.
9. Provider receives the canonical interpretation; provider does not re-select context.
10. Renderer remains outside this file and can be upgraded independently.

Canonical integration points
-----------------------------
Current project route uses these modules around this layer:

    blocks.executor
    blocks.provider_router
    blocks.state_manager
    blocks.C_ARTIFACT_CONTRACT
    blocks.presentation_formatter
    blocks.context_system

The production Executor currently imports:
    interpret_request
    build_processor_execution_context
    QUANTUM_EVIDENCE_FUSION
    QUANTUM_DIALOGUE_ENGINE

Those compatibility symbols are provided at the bottom of this file.

IMPORTANT
---------
This is a test replacement. It is deliberately not a drop-in replacement for
every historical helper in the 4k-line production file. The old file remains
your rollback point.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover
    fuzz = None


ENGINE_VERSION = "APRIL-UNIFIED-INTERPRETATION-V1"
TRANSPORT_NAME = "transport_state"
DECISION_OWNER = "INTERPRETATION_LAYER"
DIALOGUE_WINDOW_HOURS = 12
DIALOGUE_TTL_SECONDS = DIALOGUE_WINDOW_HOURS * 3600

PROVIDER_INPUT_HARD_BUDGET = 900
PROVIDER_OUTPUT_HARD_BUDGET = 8000

SINGLE_ROUTE = True
PROVIDER_CALLS_PER_TURN = 1
LEGACY_TRIGGER_EXECUTION = False
KEYWORD_ROUTING = False


# ---------------------------------------------------------------------------
# Renderer-independent representation schema.
# These are data types, not trigger words.
# ---------------------------------------------------------------------------

REPRESENTATIONS = (
    "text",
    "table",
    "graph",
    "diagram",
    "formula",
    "image",
    "gallery",
    "code",
    "link",
)

STRUCTURED_KINDS = {
    "table",
    "graph",
    "diagram",
    "formula",
    "image",
    "gallery",
    "code",
    "link",
}


# ---------------------------------------------------------------------------
# Compatibility result constants.
# ---------------------------------------------------------------------------

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _text(value: Any, limit: Optional[int] = None) -> str:
    value = "" if value is None else str(value)
    value = " ".join(value.strip().split())
    if limit is not None:
        return value[:limit]
    return value


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _safe_json(value: Any) -> Any:
    """
    Make runtime objects persistable without flattening structured data.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Mapping):
        return {
            str(k): _safe_json(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_safe_json(v) for v in value]

    if hasattr(value, "__dict__"):
        return _safe_json(vars(value))

    return str(value)


def _semantic_similarity(a: str, b: str) -> float:
    """
    Similarity is evidence, not a route trigger.

    Primary path:
        existing April semantic memory engine, if available.

    Secondary path:
        fuzzy similarity only as a degraded mathematical similarity measure,
        never as a hard-coded language trigger.

    There are NO word dictionaries here.
    """
    a = _text(a)
    b = _text(b)
    if not a or not b:
        return 0.0

    # Reuse the project's existing semantic-memory encoder when present.
    try:
        from blocks.state_manager import QUANTUM_MEMORY_ENGINE

        scorer = getattr(QUANTUM_MEMORY_ENGINE, "semantic_score", None)
        if callable(scorer):
            value = float(scorer(a, b))
            return max(0.0, min(1.0, value))
    except Exception:
        pass

    if fuzz is not None:
        try:
            token_set = fuzz.token_set_ratio(a, b) / 100.0
            ratio = fuzz.ratio(a, b) / 100.0
            return max(0.0, min(1.0, token_set * 0.70 + ratio * 0.30))
        except Exception:
            pass

    return 0.0


def _semantic_canvas(
    *,
    user_text: str,
    interpretation: Optional[Mapping[str, Any]] = None,
    assistant_text: str = "",
    structured: Any = None,
    artifact: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    Build semantic evidence from the meaning-bearing fields of a turn.

    Structured data are represented by a compact schema summary here; the full
    data remain in the turn/artifact and are never replaced by this text.
    """
    interpretation = interpretation or {}
    artifact = artifact or {}

    values: List[str] = [
        _text(user_text, 1600),
        _text(interpretation.get("topic"), 400),
        _text(interpretation.get("goal"), 400),
        _text(interpretation.get("operation"), 400),
        _text(interpretation.get("representation"), 120),
        _text(interpretation.get("active_subject_description"), 500),
        _text(assistant_text, 1800),
        _text(artifact.get("title"), 300),
        _text(artifact.get("kind"), 100),
        _text(artifact.get("representation"), 100),
    ]

    temporal = interpretation.get("temporal_scope")
    if isinstance(temporal, Mapping):
        values.extend(
            _text(temporal.get(k), 100)
            for k in ("kind", "from", "to", "granularity")
        )

    if isinstance(structured, Mapping):
        values.extend(
            _text(structured.get(k), 300)
            for k in ("kind", "title", "representation")
        )

    return " | ".join(x for x in values if x)


@dataclass
class StructuredArtifact:
    artifact_id: str
    kind: str
    representation: str
    title: str = ""
    data: Any = None
    columns: List[Any] = field(default_factory=list)
    rows: List[Any] = field(default_factory=list)
    series: List[Any] = field(default_factory=list)
    x_axis: Dict[str, Any] = field(default_factory=dict)
    y_axis: Dict[str, Any] = field(default_factory=dict)
    temporal_scope: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _safe_json({
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "representation": self.representation,
            "title": self.title,
            "data": self.data,
            "columns": self.columns,
            "rows": self.rows,
            "series": self.series,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "temporal_scope": self.temporal_scope,
            "metadata": self.metadata,
        })


@dataclass
class DialogueTurn:
    turn_id: str
    sequence_id: str
    created_at: float
    user_text: str

    # Canonical interpretation for the turn.
    interpretation: Dict[str, Any]

    # Exact structured result from Provider/OpenAI.
    assistant_structured: Any = None

    # Human-readable answer.
    assistant_text: str = ""

    # Extracted structured artifacts. Full values/data stay here.
    artifacts: List[Dict[str, Any]] = field(default_factory=list)

    # Provider usage/cost/transport metadata.
    provider_meta: Dict[str, Any] = field(default_factory=dict)

    def semantic_canvas(self) -> str:
        artifact = self.artifacts[0] if self.artifacts else {}
        return _semantic_canvas(
            user_text=self.user_text,
            interpretation=self.interpretation,
            assistant_text=self.assistant_text,
            structured=self.assistant_structured,
            artifact=artifact,
        )

    def to_dict(self) -> Dict[str, Any]:
        return _safe_json({
            "turn_id": self.turn_id,
            "sequence_id": self.sequence_id,
            "created_at": self.created_at,
            "user_text": self.user_text,
            "interpretation": self.interpretation,
            "assistant_structured": self.assistant_structured,
            "assistant_text": self.assistant_text,
            "artifacts": self.artifacts,
            "provider_meta": self.provider_meta,
        })


@dataclass
class DialogueMemory:
    user_id: str
    conversation_id: str
    sequence_id: str
    ttl_seconds: int = DIALOGUE_TTL_SECONDS
    turns: List[DialogueTurn] = field(default_factory=list)

    def prune(self, now: Optional[float] = None) -> None:
        now = _now() if now is None else float(now)
        cutoff = now - float(self.ttl_seconds)

        self.turns = [
            t for t in self.turns
            if float(t.created_at or 0.0) >= cutoff
        ]

    def append(self, turn: DialogueTurn, now: Optional[float] = None) -> None:
        self.prune(now)
        self.turns.append(turn)
        self.prune(now)

    def latest(self) -> Optional[DialogueTurn]:
        self.prune()
        return self.turns[-1] if self.turns else None

    def recent(self, limit: int = 12) -> List[DialogueTurn]:
        self.prune()
        return self.turns[-max(1, int(limit)):]

    def to_dict(self) -> Dict[str, Any]:
        self.prune()
        return _safe_json({
            "engine": ENGINE_VERSION,
            "window": "12h",
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "sequence_id": self.sequence_id,
            "ttl_seconds": self.ttl_seconds,
            "turns": [t.to_dict() for t in self.turns],
        })


@dataclass
class InterpretationDecision:
    relation: str = "NEW"
    topic: str = ""
    goal: str = ""
    operation: str = "answer"

    active_subject: Dict[str, Any] = field(default_factory=dict)
    source_turn_ids: List[str] = field(default_factory=list)

    # Requested representation is separate from semantic topic.
    representation: str = "text"

    # Reused structured data, when current request depends on it.
    data: Any = None

    # Natural language time scope remains first-class semantic data.
    temporal_scope: Dict[str, Any] = field(default_factory=dict)

    # Provider needs more data only when the data are not already available.
    data_required: bool = False

    # Semantic summary sent into the response-generation stage.
    openai_objective: str = ""

    confidence: float = 0.0
    rationale: str = ""

    # Evidence used by the semantic engine, useful for diagnostics.
    semantic_evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _safe_json({
            "relation": self.relation,
            "topic": self.topic,
            "goal": self.goal,
            "operation": self.operation,
            "active_subject": self.active_subject,
            "active_subject_description": _text(
                self.active_subject.get("description")
            ),
            "source_turn_ids": self.source_turn_ids,
            "representation": self.representation,
            "data": self.data,
            "temporal_scope": self.temporal_scope,
            "data_required": self.data_required,
            "openai_objective": self.openai_objective,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "semantic_evidence": self.semantic_evidence,
        })


# ---------------------------------------------------------------------------
# Semantic dialogue engine
# ---------------------------------------------------------------------------

class UnifiedDialogueSemanticEngine:
    """
    One semantic engine.

    It does not contain vocabulary-trigger routing.

    Its job is to compare:
        current request
        against
        complete meaning-bearing previous turns / artifacts.

    Relation is decided from evidence fusion:
        recency
        semantic similarity
        active branch similarity
        artifact similarity
        structural continuity
        explicit branch identity from stored state

    It does not manufacture entities.
    """

    VERSION = ENGINE_VERSION

    CONTINUE_THRESHOLD = 0.60
    STRONG_CONTINUE_THRESHOLD = 0.74
    RECALL_THRESHOLD = 0.66
    NEW_DISTANCE_THRESHOLD = 0.42

    def _stored_turns_from_state(
        self,
        history: Sequence[Any],
        state: Mapping[str, Any],
    ) -> List[DialogueTurn]:
        """
        Prefer canonical structured memory.

        Legacy dialog rows are accepted as read-only evidence but are never
        rewritten into the new entity-based representation.
        """
        turns: List[DialogueTurn] = []

        raw_memory = state.get("dialogue_memory")
        if isinstance(raw_memory, Mapping):
            raw_turns = raw_memory.get("turns")
            if isinstance(raw_turns, list):
                for item in raw_turns:
                    if not isinstance(item, Mapping):
                        continue

                    turns.append(
                        DialogueTurn(
                            turn_id=_text(item.get("turn_id")) or uuid.uuid4().hex,
                            sequence_id=_text(
                                item.get("sequence_id")
                                or raw_memory.get("sequence_id")
                            ),
                            created_at=float(
                                item.get("created_at") or _now()
                            ),
                            user_text=_text(
                                item.get("user_text")
                            ),
                            interpretation=_copy(
                                item.get("interpretation") or {}
                            ),
                            assistant_structured=_copy(
                                item.get("assistant_structured")
                            ),
                            assistant_text=_text(
                                item.get("assistant_text")
                            ),
                            artifacts=_copy(
                                item.get("artifacts") or []
                            ),
                            provider_meta=_copy(
                                item.get("provider_meta") or {}
                            ),
                        )
                    )

        # Canonical current turn is useful even if persistence has not yet been
        # written. It must not be treated as an entity bag.
        canonical = state.get("canonical_dialogue_turn")
        if isinstance(canonical, Mapping):
            user_text = _text(
                canonical.get("user_request")
                or canonical.get("user_text")
            )
            if user_text:
                turn_id = _text(
                    canonical.get("turn_id")
                ) or uuid.uuid4().hex

                if not any(t.turn_id == turn_id for t in turns):
                    turns.append(
                        DialogueTurn(
                            turn_id=turn_id,
                            sequence_id=_text(
                                canonical.get("sequence_id")
                                or state.get(
                                    "active_dialogue_sequence",
                                    {},
                                ).get("sequence_id")
                            ),
                            created_at=float(
                                canonical.get("created_at") or _now()
                            ),
                            user_text=user_text,
                            interpretation=_copy(
                                canonical.get("interpretation")
                                or canonical
                            ),
                            assistant_structured=_copy(
                                canonical.get("assistant_structured")
                                or canonical.get("last_result")
                            ),
                            assistant_text=_text(
                                canonical.get("april_answer")
                                or canonical.get("assistant_text")
                            ),
                            artifacts=_copy(
                                canonical.get("artifacts") or []
                            ),
                            provider_meta=_copy(
                                canonical.get("provider_meta") or {}
                            ),
                        )
                    )

        if turns:
            turns.sort(key=lambda x: (x.created_at, x.turn_id))
            return turns

        # Legacy history is evidence only.
        for item in history if isinstance(history, list) else []:
            if not isinstance(item, Mapping):
                continue

            user = item.get("user")
            april = item.get("april")

            if isinstance(user, Mapping):
                user_text = _text(
                    user.get("text")
                    or user.get("content")
                )
            else:
                user_text = _text(
                    item.get("user_request")
                    or item.get("content")
                )

            if isinstance(april, Mapping):
                assistant_text = _text(
                    april.get("answer")
                    or april.get("content")
                )
            else:
                assistant_text = _text(
                    item.get("answer")
                    or item.get("april_answer")
                )

            if not user_text and not assistant_text:
                continue

            turns.append(
                DialogueTurn(
                    turn_id=_text(
                        item.get("turn_id")
                    ) or uuid.uuid4().hex,
                    sequence_id=_text(
                        item.get("sequence_id")
                        or item.get("dialogue_sequence_id")
                    ),
                    created_at=float(
                        item.get("created_at") or _now()
                    ),
                    user_text=user_text,
                    interpretation=_copy(
                        item.get("interpretation")
                        or item.get("semantic_state")
                        or {}
                    ),
                    assistant_structured=_copy(
                        item.get("assistant_structured")
                        or item.get("last_result")
                    ),
                    assistant_text=assistant_text,
                    artifacts=_copy(
                        item.get("artifacts") or []
                    ),
                    provider_meta={},
                )
            )

        turns.sort(key=lambda x: (x.created_at, x.turn_id))
        return turns

    def _branch_state(
        self,
        state: Mapping[str, Any],
        turns: Sequence[DialogueTurn],
    ) -> Dict[str, Any]:
        active = state.get("active_dialogue_sequence")

        if isinstance(active, Mapping):
            return {
                "sequence_id": _text(active.get("sequence_id")),
                "task_id": _text(active.get("task_id")),
                "topic": _text(
                    active.get("topic")
                    or active.get("current_topic")
                ),
                "goal": _text(active.get("goal")),
                "active_subject": _text(
                    active.get("active_entity")
                    or active.get("current_object")
                ),
            }

        latest = turns[-1] if turns else None
        return {
            "sequence_id": latest.sequence_id if latest else "",
            "task_id": "",
            "topic": _text(
                latest.interpretation.get("topic")
                if latest else ""
            ),
            "goal": _text(
                latest.interpretation.get("goal")
                if latest else ""
            ),
            "active_subject": _text(
                latest.interpretation.get(
                    "active_subject_description"
                )
                if latest else ""
            ),
        }

    def _turn_score(
        self,
        current: str,
        candidate: DialogueTurn,
        *,
        branch: Mapping[str, Any],
        rank_from_latest: int,
    ) -> float:
        semantic = _semantic_similarity(
            current,
            candidate.semantic_canvas(),
        )

        branch_text = " | ".join(
            _text(branch.get(k))
            for k in (
                "topic",
                "goal",
                "active_subject",
            )
        )

        branch_similarity = _semantic_similarity(
            current,
            branch_text,
        )

        # Structured artifact relevance is independent from topic text.
        artifact_similarity = 0.0
        for artifact in candidate.artifacts:
            artifact_canvas = _semantic_canvas(
                user_text=candidate.user_text,
                interpretation=candidate.interpretation,
                assistant_text=candidate.assistant_text,
                structured=candidate.assistant_structured,
                artifact=artifact,
            )
            artifact_similarity = max(
                artifact_similarity,
                _semantic_similarity(current, artifact_canvas),
            )

        # Mild recency evidence. It never creates continuity on its own.
        recency = 1.0 / max(1, rank_from_latest)

        score = (
            semantic * 0.50
            + branch_similarity * 0.20
            + artifact_similarity * 0.25
            + recency * 0.05
        )

        return max(0.0, min(1.0, score))

    def resolve(
        self,
        *,
        current_request: str,
        history: Sequence[Any],
        state: Mapping[str, Any],
    ) -> Dict[str, Any]:
        current = _text(current_request)

        turns = self._stored_turns_from_state(
            history,
            state,
        )
        turns = [
            t for t in turns
            if t.user_text or t.assistant_text or t.artifacts
        ]

        branch = self._branch_state(
            state,
            turns,
        )

        if not turns:
            return {
                "relation": "NEW",
                "reason": "no_live_dialogue_evidence",
                "confidence": 1.0,
                "selected_turn_id": "",
                "selected_artifact": {},
                "scores": [],
            }

        scores: List[Dict[str, Any]] = []
        for reverse_index, turn in enumerate(
            reversed(turns),
            start=1,
        ):
            score = self._turn_score(
                current,
                turn,
                branch=branch,
                rank_from_latest=reverse_index,
            )

            scores.append({
                "turn_id": turn.turn_id,
                "score": round(score, 6),
                "age_rank": reverse_index,
                "sequence_id": turn.sequence_id,
                "topic": _text(
                    turn.interpretation.get("topic")
                ),
                "representation": _text(
                    turn.interpretation.get("representation")
                ),
            })

        scores.sort(
            key=lambda x: (
                float(x["score"]),
                -int(x["age_rank"]),
            ),
            reverse=True,
        )

        best = scores[0]
        best_score = float(best["score"])

        selected_turn = next(
            (
                t for t in turns
                if t.turn_id == best["turn_id"]
            ),
            None,
        )

        # A stored branch can be explicitly recalled through a semantic match.
        # The current request remains authoritative.
        if (
            selected_turn is not None
            and selected_turn.sequence_id
            and (
                selected_turn.sequence_id
                != _text(branch.get("sequence_id"))
            )
            and best_score >= self.RECALL_THRESHOLD
        ):
            relation = "RECALL"
            reason = "semantic_match_to_live_memory_branch"
        elif best_score >= self.STRONG_CONTINUE_THRESHOLD:
            relation = "CONTINUE"
            reason = "strong_semantic_continuity"
        elif best_score >= self.CONTINUE_THRESHOLD:
            relation = "CONTINUE"
            reason = "semantic_branch_affinity"
        elif best_score <= self.NEW_DISTANCE_THRESHOLD:
            relation = "NEW"
            reason = "semantic_distance_from_live_context"
        else:
            # Ambiguous middle ground stays in dialogue context rather than
            # inventing a new subject.
            relation = "CONTINUE"
            reason = "ambiguous_but_live_context_retained"

        selected_artifact: Dict[str, Any] = {}
        if selected_turn is not None:
            for artifact in selected_turn.artifacts:
                canvas = _semantic_canvas(
                    user_text=selected_turn.user_text,
                    interpretation=selected_turn.interpretation,
                    assistant_text=selected_turn.assistant_text,
                    structured=selected_turn.assistant_structured,
                    artifact=artifact,
                )

                artifact_score = _semantic_similarity(
                    current,
                    canvas,
                )

                if (
                    not selected_artifact
                    or artifact_score
                    > float(
                        selected_artifact.get(
                            "_score",
                            0.0,
                        )
                    )
                ):
                    selected_artifact = _copy(artifact)
                    selected_artifact["_score"] = round(
                        artifact_score,
                        6,
                    )

        return {
            "relation": relation,
            "reason": reason,
            "confidence": round(best_score, 6),
            "selected_turn_id": selected_turn.turn_id
            if selected_turn
            else "",
            "selected_artifact": selected_artifact,
            "scores": scores[:12],
            "branch": branch,
        }

    def dialogue(
        self,
        text: str,
        *,
        previous_assistant: str = "",
        previous_user: str = "",
        active_goal: str = "",
        active_topic: str = "",
        open_task: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compatibility method used by older Executor paths.

        It still performs semantic comparison and does not use word triggers.
        """
        candidate = {
            "user_request": previous_user,
            "april_answer": previous_assistant,
            "topic": active_topic,
            "goal": active_goal,
            "task": open_task or {},
        }

        score = _semantic_similarity(
            text,
            _semantic_canvas(
                user_text=previous_user,
                interpretation={
                    "topic": active_topic,
                    "goal": active_goal,
                },
                assistant_text=previous_assistant,
            ),
        )

        continuation = bool(
            previous_assistant
            or previous_user
            or active_topic
            or active_goal
        ) and score >= self.CONTINUE_THRESHOLD

        return {
            "dialogue": {
                "label": "continuation"
                if continuation
                else "independent",
                "confidence": score,
                "continuation_score": score,
                "reference_score": score,
                "topic_score": _semantic_similarity(
                    text,
                    active_topic,
                ),
                "goal_score": _semantic_similarity(
                    text,
                    active_goal,
                ),
            },
            "continuation": continuation,
            "reference_to_previous": continuation and score >= 0.66,
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": ENGINE_VERSION,
            "candidate": candidate,
        }

    def similarities(
        self,
        text: str,
        candidates: Sequence[str],
    ) -> Dict[str, float]:
        return {
            _text(candidate): _semantic_similarity(
                text,
                _text(candidate),
            )
            for candidate in candidates
            if _text(candidate)
        }

    def semantic_profile(
        self,
        text: str,
        *,
        previous_assistant: str = "",
        previous_user: str = "",
        active_topic: str = "",
        active_goal: str = "",
    ) -> Dict[str, Any]:
        canvas = _semantic_canvas(
            user_text=text,
            interpretation={
                "topic": active_topic,
                "goal": active_goal,
            },
            assistant_text=previous_assistant,
        )

        return {
            "engine": ENGINE_VERSION,
            "source": "semantic_context_fusion",
            "context_similarity": {
                "previous_turn": _semantic_similarity(
                    text,
                    canvas,
                ),
                "active_topic": _semantic_similarity(
                    text,
                    active_topic,
                ),
                "active_goal": _semantic_similarity(
                    text,
                    active_goal,
                ),
            },
            "evidence_only": True,
        }

    def measure(self, text: str, **context: Any) -> Dict[str, Any]:
        return self.semantic_profile(
            text,
            previous_assistant=_text(
                context.get("previous_assistant")
            ),
            previous_user=_text(
                context.get("previous_user")
            ),
            active_topic=_text(
                context.get("active_topic")
            ),
            active_goal=_text(
                context.get("active_goal")
            ),
        )


QUANTUM_DIALOGUE_ENGINE = UnifiedDialogueSemanticEngine()
QUANTUM_EVIDENCE_FUSION = QUANTUM_DIALOGUE_ENGINE
QUANTUM_INTERPRETATION_ENGINE = QUANTUM_DIALOGUE_ENGINE
QUANTUM_FAST_SEMANTIC = QUANTUM_DIALOGUE_ENGINE
QuantumInterpretationEngine = UnifiedDialogueSemanticEngine


# ---------------------------------------------------------------------------
# Representation understanding.
# ---------------------------------------------------------------------------

def _extract_representation_from_state(
    current_request: str,
    *,
    state: Mapping[str, Any],
    selected_turn: Optional[DialogueTurn] = None,
) -> str:
    """
    Do not parse the user's vocabulary into route decisions.

    Preference order:
        1. canonical structured request already stored in state;
        2. selected prior artifact when current operation transforms it;
        3. processor/semantic evidence supplied by previous stages;
        4. 'text' only as a neutral absence-of-structure value.

    The actual natural-language representation interpretation is expected to be
    provided by the existing semantic processor before/after this layer.
    """
    canonical = state.get("canonical_dialogue_turn")
    if isinstance(canonical, Mapping):
        representation = _text(
            canonical.get("representation")
            or canonical.get("production_representation")
        )
        if representation in REPRESENTATIONS:
            return representation

    active_context = state.get(
        "active_dialogue_context"
    )
    if isinstance(active_context, Mapping):
        representation = _text(
            active_context.get("representation")
        )
        if representation in REPRESENTATIONS:
            return representation

    if selected_turn is not None:
        representation = _text(
            selected_turn.interpretation.get(
                "representation"
            )
        )
        if representation in REPRESENTATIONS:
            return representation

        if selected_turn.artifacts:
            candidate = _text(
                selected_turn.artifacts[-1].get(
                    "representation"
                )
            )
            if candidate in REPRESENTATIONS:
                return candidate

    # No semantic representation has been established yet.
    return "text"


def _extract_data_from_artifact(
    artifact: Mapping[str, Any]
) -> Any:
    """
    Preserve data exactly. No 5/7/12/30-point reduction.
    """
    if not isinstance(artifact, Mapping):
        return None

    if artifact.get("data") is not None:
        return _copy(artifact["data"])

    if artifact.get("rows"):
        return _copy(artifact["rows"])

    if artifact.get("series"):
        return _copy(artifact["series"])

    return None


def _build_active_subject(
    *,
    decision_relation: str,
    current_request: str,
    selected_turn: Optional[DialogueTurn],
    selected_artifact: Optional[Mapping[str, Any]],
    state: Mapping[str, Any],
) -> Dict[str, Any]:
    subject: Dict[str, Any] = {}

    if decision_relation in {"CONTINUE", "RECALL"} and selected_turn:
        subject = {
            "kind": "dialogue_object",
            "turn_id": selected_turn.turn_id,
            "artifact_id": _text(
                (selected_artifact or {}).get(
                    "artifact_id"
                )
            ),
            "description": _text(
                selected_turn.interpretation.get(
                    "active_subject_description"
                )
                or selected_turn.interpretation.get(
                    "topic"
                )
                or selected_turn.user_text
            ),
        }

    if not subject:
        canonical = state.get("canonical_dialogue_turn")
        if isinstance(canonical, Mapping):
            description = _text(
                canonical.get("active_entity")
                or canonical.get("topic")
            )
            if description:
                subject = {
                    "kind": "canonical_dialogue_object",
                    "turn_id": _text(
                        canonical.get("turn_id")
                    ),
                    "artifact_id": "",
                    "description": description,
                }

    if not subject and current_request:
        # Current request is the authoritative subject source for a NEW turn.
        subject = {
            "kind": "current_request",
            "turn_id": "",
            "artifact_id": "",
            "description": _text(
                current_request,
                1000,
            ),
        }

    return subject


# ---------------------------------------------------------------------------
# Canonical interpretation.
# ---------------------------------------------------------------------------

def interpret_request(
    text: str,
    cognition: Optional[Dict[str, Any]] = None,
    semantic: Optional[Dict[str, Any]] = None,
    history: Optional[List[Any]] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    THE ONLY public interpretation entrypoint.

    It creates one canonical interpretation object.

    Important:
        this function never runs a keyword-trigger routing table.

    The current semantic processors can add evidence under:
        cognition
        semantic

    but they cannot replace the canonical structured dialogue record.
    """
    current = _text(text)
    if not current:
        return None

    cognition = cognition if isinstance(cognition, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    history = history if isinstance(history, list) else []
    state = state if isinstance(state, dict) else {}

    relation_measurement = QUANTUM_DIALOGUE_ENGINE.resolve(
        current_request=current,
        history=history,
        state=state,
    )

    relation = _text(
        relation_measurement.get("relation")
    ).upper()

    if relation not in {"NEW", "CONTINUE", "RECALL"}:
        relation = "NEW"

    selected_turn_id = _text(
        relation_measurement.get(
            "selected_turn_id"
        )
    )

    semantic_turns = QUANTUM_DIALOGUE_ENGINE._stored_turns_from_state(
        history,
        state,
    )

    selected_turn = next(
        (
            t for t in semantic_turns
            if t.turn_id == selected_turn_id
        ),
        None,
    )

    selected_artifact = relation_measurement.get(
        "selected_artifact"
    )
    if not isinstance(selected_artifact, dict):
        selected_artifact = {}

    # Remove diagnostic score from persisted artifact identity.
    selected_artifact = {
        k: _copy(v)
        for k, v in selected_artifact.items()
        if k != "_score"
    }

    active_subject = _build_active_subject(
        decision_relation=relation,
        current_request=current,
        selected_turn=selected_turn,
        selected_artifact=selected_artifact,
        state=state,
    )

    # Prefer semantic evidence supplied by the existing processor if present.
    inferred_topic = _text(
        semantic.get("topic")
        or cognition.get("topic")
        or (
            selected_turn.interpretation.get("topic")
            if selected_turn
            else ""
        )
    )

    inferred_goal = _text(
        semantic.get("goal")
        or cognition.get("goal")
        or (
            selected_turn.interpretation.get("goal")
            if selected_turn
            else ""
        )
    )

    inferred_operation = _text(
        semantic.get("operation")
        or cognition.get("operation")
        or (
            selected_turn.interpretation.get(
                "operation"
            )
            if selected_turn
            else ""
        )
        or "answer"
    )

    representation = (
        _text(
            semantic.get("representation")
            or semantic.get(
                "production_representation"
            )
            or cognition.get("representation")
        )
        or _extract_representation_from_state(
            current,
            state=state,
            selected_turn=selected_turn,
        )
    )

    if representation not in REPRESENTATIONS:
        representation = "text"

    data = _copy(
        semantic.get("data")
    )

    if data is None and selected_artifact:
        data = _extract_data_from_artifact(
            selected_artifact
        )

    # For continuation of a structured object, preserve its representation/data
    # unless the upstream semantic processor has already supplied a new one.
    if (
        relation in {"CONTINUE", "RECALL"}
        and selected_artifact
    ):
        if data is None:
            data = _extract_data_from_artifact(
                selected_artifact
            )

        if (
            representation == "text"
            and _text(
                selected_artifact.get(
                    "representation"
                )
            ) in REPRESENTATIONS
        ):
            representation = _text(
                selected_artifact.get(
                    "representation"
                )
            )

    # Temporal scope is deliberately structured rather than hard-coded.
    temporal_scope = _copy(
        semantic.get("temporal_scope")
        or cognition.get("temporal_scope")
        or (
            selected_turn.interpretation.get(
                "temporal_scope"
            )
            if selected_turn
            else {}
        )
        or {}
    )

    source_turn_ids = []
    if selected_turn is not None:
        source_turn_ids.append(
            selected_turn.turn_id
        )

    # When an existing structured object is referenced, its full data remain
    # attached to the canonical interpretation.
    data_required = bool(
        semantic.get("data_required")
        or (
            relation in {"CONTINUE", "RECALL"}
            and selected_artifact == {}
            and selected_turn is not None
            and representation in STRUCTURED_KINDS
        )
    )

    objective = _text(
        semantic.get("openai_objective")
        or cognition.get("openai_objective")
    )

    if not objective:
        objective = _text(
            current,
            1800,
        )

    confidence = float(
        relation_measurement.get(
            "confidence"
        )
        or semantic.get("confidence")
        or cognition.get("confidence")
        or 0.0
    )
    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    decision = InterpretationDecision(
        relation=relation,
        topic=inferred_topic,
        goal=inferred_goal,
        operation=inferred_operation,
        active_subject=active_subject,
        source_turn_ids=source_turn_ids,
        representation=representation,
        data=data,
        temporal_scope=temporal_scope
        if isinstance(temporal_scope, dict)
        else {},
        data_required=data_required,
        openai_objective=objective,
        confidence=confidence,
        rationale=_text(
            relation_measurement.get(
                "reason"
            ),
            300,
        ),
        semantic_evidence=_copy(
            relation_measurement
        ),
    )

    result = decision.to_dict()

    # ------------------------------------------------------------------
    # Canonical transport fields expected downstream.
    # ------------------------------------------------------------------
    result["transport"] = TRANSPORT_NAME
    result["decision_owner"] = DECISION_OWNER
    result["engine_version"] = ENGINE_VERSION

    result["canonical"] = True
    result["single_route"] = True
    result["provider_must_not_reselect_context"] = True
    result["legacy_trigger_execution"] = False
    result["keyword_routing"] = False

    result["current_request"] = current

    result["dialogue_vector"] = {
        "relation": relation,
        "continuation": relation == "CONTINUE",
        "reference_to_previous": relation == "RECALL",
        "context_dependency": (
            "current_dialogue"
            if relation == "CONTINUE"
            else "memory_reference"
            if relation == "RECALL"
            else "independent"
        ),
        "selected_turn_id": selected_turn_id,
        "source_turn_ids": source_turn_ids,
        "confidence": confidence,
    }

    # Keep the full structured data in a dedicated field. This is not an
    # entity-derived reconstruction.
    result["structured_data"] = _copy(data)

    result["active_subject"] = _copy(
        active_subject
    )

    result["data_contract"] = {
        "preserve_all_points": True,
        "dynamic_point_count": True,
        "no_fixed_series_length": True,
        "reuse_previous_data_on_representation_change": (
            relation in {"CONTINUE", "RECALL"}
            and data is not None
        ),
        "temporal_scope": _copy(
            decision.temporal_scope
        ),
    }

    result["render_contract"] = {
        "representation": representation,
        "structured": representation in STRUCTURED_KINDS,
        "renderer_selection_owner": "PROCESSOR",
        "renderer_layer": "SCENE_CONTRACT",
        "allowed_representations": list(
            REPRESENTATIONS
        ),
        "renderer_neutral": True,
    }

    # Full 12h context is available to the provider builder.
    result["memory_contract"] = {
        "window_hours": DIALOGUE_WINDOW_HOURS,
        "authenticated_scope": True,
        "structured_turn_memory": True,
        "entity_bag_is_not_authoritative": True,
        "history_is_semantic_evidence": True,
    }

    return result


# ---------------------------------------------------------------------------
# Structured provider context.
# ---------------------------------------------------------------------------

def _compact_artifact_for_provider(
    artifact: Mapping[str, Any]
) -> Dict[str, Any]:
    """
    Compact envelope, complete data preserved.

    We do not slice series to a fixed number of points.
    """
    artifact = artifact if isinstance(
        artifact,
        Mapping,
    ) else {}

    payload = {
        "artifact_id": _text(
            artifact.get("artifact_id")
        ),
        "kind": _text(
            artifact.get("kind")
        ),
        "representation": _text(
            artifact.get("representation")
        ),
        "title": _text(
            artifact.get("title"),
            240,
        ),
        "data": _copy(
            artifact.get("data")
        ),
        "columns": _copy(
            artifact.get("columns") or []
        ),
        "rows": _copy(
            artifact.get("rows") or []
        ),
        "series": _copy(
            artifact.get("series") or []
        ),
        "x_axis": _copy(
            artifact.get("x_axis") or {}
        ),
        "y_axis": _copy(
            artifact.get("y_axis") or {}
        ),
        "temporal_scope": _copy(
            artifact.get("temporal_scope") or {}
        ),
        "metadata": _copy(
            artifact.get("metadata") or {}
        ),
    }

    return _safe_json(payload)


def _compact_turn_for_provider(
    turn: DialogueTurn,
) -> Dict[str, Any]:
    return {
        "turn_id": turn.turn_id,
        "user": turn.user_text,
        "interpretation": {
            "relation": _text(
                turn.interpretation.get(
                    "relation"
                )
            ),
            "topic": _text(
                turn.interpretation.get(
                    "topic"
                ),
                300,
            ),
            "goal": _text(
                turn.interpretation.get(
                    "goal"
                ),
                300,
            ),
            "operation": _text(
                turn.interpretation.get(
                    "operation"
                ),
                200,
            ),
            "representation": _text(
                turn.interpretation.get(
                    "representation"
                ),
                100,
            ),
            "temporal_scope": _copy(
                turn.interpretation.get(
                    "temporal_scope"
                )
                or {}
            ),
        },
        "assistant_text": turn.assistant_text,
        "assistant_structured": _copy(
            turn.assistant_structured
        ),
        "artifacts": [
            _compact_artifact_for_provider(
                a
            )
            for a in turn.artifacts
        ],
    }


def build_dialogue_context(
    *,
    current_request: str,
    decision: Mapping[str, Any],
    memory: DialogueMemory,
    context_limit: int = 12,
) -> Dict[str, Any]:
    memory.prune()

    recent_turns = memory.recent(
        context_limit
    )

    selected_turn_ids = {
        str(x)
        for x in (
            decision.get(
                "source_turn_ids"
            )
            or []
        )
    }

    # Always include source turns for a CONTINUE/RECALL decision.
    selected = [
        t for t in recent_turns
        if t.turn_id in selected_turn_ids
    ]

    # Add recent context around the selected source, not an arbitrary entity list.
    for turn in reversed(recent_turns):
        if turn not in selected:
            selected.append(turn)
        if len(selected) >= context_limit:
            break

    selected.reverse()

    structured_sources: List[Dict[str, Any]] = []
    for turn in selected:
        for artifact in turn.artifacts:
            structured_sources.append(
                _compact_artifact_for_provider(
                    artifact
                )
            )

    return _safe_json({
        "engine": ENGINE_VERSION,
        "window": "12h",
        "conversation_id": memory.conversation_id,
        "sequence_id": memory.sequence_id,
        "current_request": current_request,
        "canonical_interpretation": _copy(
            decision
        ),
        "source_turns": [
            _compact_turn_for_provider(
                t
            )
            for t in selected
        ],
        "structured_sources": structured_sources,
        "rules": {
            "current_request_is_authoritative": True,
            "reuse_structured_data": True,
            "preserve_all_data_points": True,
            "representation_is_independent_of_topic": True,
            "do_not_invent_missing_data": True,
            "provider_does_not_reselect_context": True,
        },
    })


def build_provider_request(
    *,
    current_request: str,
    interpretation: Mapping[str, Any],
    memory: DialogueMemory,
    context_limit: int = 12,
) -> Dict[str, Any]:
    """
    Single canonical provider handoff.

    The existing provider_router remains the API owner.
    """
    context = build_dialogue_context(
        current_request=current_request,
        decision=interpretation,
        memory=memory,
        context_limit=context_limit,
    )

    return {
        "version": "april_unified_provider_handoff_v1",
        "transport": TRANSPORT_NAME,
        "single_route": True,
        "provider_must_not_reselect_context": True,
        "input_budget_tokens": PROVIDER_INPUT_HARD_BUDGET,
        "current_request": current_request,
        "interpretation": _copy(interpretation),
        "dialogue_context": context,
        "structured_output_required": True,
        "preserve_all_data_points": True,
    }


def build_openai_messages(
    *,
    current_request: str,
    interpretation: Mapping[str, Any],
    memory: DialogueMemory,
) -> List[Dict[str, str]]:
    """
    Provider-ready messages.

    The production provider prompt can wrap this packet inside its existing
    MachineResponse contract.
    """
    system_prompt = (
        "April canonical response stage. "
        "Use the supplied canonical interpretation and structured dialogue context. "
        "Do not re-select the topic or dialogue branch. "
        "Preserve complete structured datasets. "
        "When changing representation, reuse the same underlying data. "
        "Return one structured MachineResponse JSON object with answer/content, "
        "structured response data, artifacts/render_blocks and metadata. "
        "Never invent missing values."
    )

    packet = build_provider_request(
        current_request=current_request,
        interpretation=interpretation,
        memory=memory,
    )

    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(
                packet,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        },
    ]


# ---------------------------------------------------------------------------
# OpenAI response -> canonical dialogue memory.
# ---------------------------------------------------------------------------

def extract_structured_artifacts(
    structured: Any,
) -> List[Dict[str, Any]]:
    """
    Extract renderer-neutral artifacts without discarding their payloads.
    """
    if not isinstance(structured, Mapping):
        return []

    artifacts: List[Dict[str, Any]] = []

    def append_artifact(
        value: Mapping[str, Any]
    ) -> None:
        kind = _text(
            value.get("kind")
            or value.get("type")
            or value.get("artifact_type")
        )

        representation = _text(
            value.get("representation")
            or value.get("renderer")
            or kind
        )

        if not kind and not representation:
            return

        artifact_id = (
            _text(
                value.get("artifact_id")
            )
            or f"artifact-{_sha(value)}"
        )

        artifacts.append({
            "artifact_id": artifact_id,
            "kind": kind or representation,
            "representation": representation,
            "title": _text(
                value.get("title")
            ),
            "data": _copy(
                value.get("data")
            ),
            "columns": _copy(
                value.get("columns") or []
            ),
            "rows": _copy(
                value.get("rows") or []
            ),
            "series": _copy(
                value.get("series") or []
            ),
            "x_axis": _copy(
                value.get("x_axis") or {}
            ),
            "y_axis": _copy(
                value.get("y_axis") or {}
            ),
            "temporal_scope": _copy(
                value.get("temporal_scope") or {}
            ),
            "metadata": _copy(
                value.get("metadata") or {}
            ),
        })

    append_artifact(
        structured
    )

    raw_artifacts = structured.get(
        "artifacts"
    )

    if isinstance(
        raw_artifacts,
        list,
    ):
        for item in raw_artifacts:
            if isinstance(item, Mapping):
                append_artifact(
                    item
                )

    render_blocks = structured.get(
        "render_blocks"
    )

    if isinstance(
        render_blocks,
        list,
    ):
        for block in render_blocks:
            if isinstance(
                block,
                Mapping,
            ):
                payload = block.get(
                    "payload"
                )

                if isinstance(
                    payload,
                    Mapping,
                ):
                    append_artifact(
                        {
                            **block,
                            **payload,
                        }
                    )
                else:
                    append_artifact(
                        block
                    )

    # Deduplicate by stable artifact_id.
    unique: Dict[str, Dict[str, Any]] = {}
    for artifact in artifacts:
        unique[
            _text(
                artifact.get(
                    "artifact_id"
                )
            )
        ] = artifact

    return list(unique.values())


def record_openai_response(
    *,
    memory: DialogueMemory,
    user_text: str,
    interpretation: Mapping[str, Any],
    provider_result: Mapping[str, Any],
    now: Optional[float] = None,
) -> DialogueTurn:
    """
    Preserve the OpenAI/provider result as the next semantic turn.

    This is the crucial memory rule:
        DO NOT reconstruct this from entities.
    """
    now = _now() if now is None else float(now)

    provider_result = (
        provider_result
        if isinstance(provider_result, Mapping)
        else {
            "text": _text(provider_result)
        }
    )

    structured = _copy(
        provider_result.get(
            "structured"
        )
    )

    # Existing provider contract may carry the structured response under
    # MachineResponse-level fields.
    if structured is None:
        structured = _copy(
            provider_result.get(
                "scene"
            )
        )

    artifacts = extract_structured_artifacts(
        structured
    )

    assistant_text = _text(
        provider_result.get(
            "answer"
        )
        or provider_result.get(
            "content"
        )
        or provider_result.get(
            "text"
        )
    )

    turn = DialogueTurn(
        turn_id=(
            _text(
                provider_result.get(
                    "turn_id"
                )
            )
            or uuid.uuid4().hex
        ),
        sequence_id=memory.sequence_id,
        created_at=now,
        user_text=_text(user_text),
        interpretation=_copy(
            interpretation
        ),
        assistant_structured=structured,
        assistant_text=assistant_text,
        artifacts=artifacts,
        provider_meta={
            "model": _copy(
                provider_result.get(
                    "model"
                )
            ),
            "usage": _copy(
                provider_result.get(
                    "usage"
                )
            ),
            "cost": _copy(
                provider_result.get(
                    "cost"
                )
                or provider_result.get(
                    "metadata",
                    {},
                ).get(
                    "cost"
                )
                if isinstance(
                    provider_result.get(
                        "metadata"
                    ),
                    Mapping,
                )
                else provider_result.get(
                    "cost"
                )
            ),
            "provider_version": _copy(
                provider_result.get(
                    "provider_version"
                )
            ),
        },
    )

    memory.append(
        turn,
        now,
    )

    return turn


# ---------------------------------------------------------------------------
# StateManager integration.
# ---------------------------------------------------------------------------

def memory_from_state(
    *,
    user_id: str,
    conversation_id: str,
    state: Optional[Mapping[str, Any]],
) -> DialogueMemory:
    state = state if isinstance(
        state,
        Mapping,
    ) else {}

    active = state.get(
        "active_dialogue_sequence"
    )
    active = (
        active
        if isinstance(active, Mapping)
        else {}
    )

    raw = state.get(
        "dialogue_memory"
    )

    if not isinstance(
        raw,
        Mapping,
    ):
        raw = active.get(
            "dialogue_memory"
        )

    sequence_id = (
        _text(
            raw.get("sequence_id")
        )
        if isinstance(
            raw,
            Mapping,
        )
        else ""
    )

    if not sequence_id:
        sequence_id = _text(
            active.get(
                "sequence_id"
            )
        )

    if not sequence_id:
        bucket = int(
            _now() // DIALOGUE_TTL_SECONDS
        )
        sequence_id = (
            "seq-"
            + hashlib.sha256(
                (
                    f"{user_id}|"
                    f"{conversation_id}|"
                    f"{bucket}"
                ).encode("utf-8")
            ).hexdigest()[:20]
        )

    memory = DialogueMemory(
        user_id=_text(user_id),
        conversation_id=_text(
            conversation_id
        ),
        sequence_id=sequence_id,
    )

    if isinstance(
        raw,
        Mapping,
    ):
        for item in (
            raw.get(
                "turns"
            )
            or []
        ):
            if not isinstance(
                item,
                Mapping,
            ):
                continue

            memory.turns.append(
                DialogueTurn(
                    turn_id=_text(
                        item.get(
                            "turn_id"
                        )
                    ) or uuid.uuid4().hex,
                    sequence_id=_text(
                        item.get(
                            "sequence_id"
                        )
                    ) or sequence_id,
                    created_at=float(
                        item.get(
                            "created_at"
                        )
                        or _now()
                    ),
                    user_text=_text(
                        item.get(
                            "user_text"
                        )
                    ),
                    interpretation=_copy(
                        item.get(
                            "interpretation"
                        )
                        or {}
                    ),
                    assistant_structured=_copy(
                        item.get(
                            "assistant_structured"
                        )
                    ),
                    assistant_text=_text(
                        item.get(
                            "assistant_text"
                        )
                    ),
                    artifacts=_copy(
                        item.get(
                            "artifacts"
                        )
                        or []
                    ),
                    provider_meta=_copy(
                        item.get(
                            "provider_meta"
                        )
                        or {}
                    ),
                )
            )

    memory.prune()
    return memory


def write_memory_to_state(
    *,
    state: Dict[str, Any],
    memory: DialogueMemory,
    latest_turn: Optional[DialogueTurn] = None,
) -> Dict[str, Any]:
    """
    Canonical in-memory write.

    StateManager remains responsible for durable persistence.
    This layer prepares the canonical record and never writes entity bags.
    """
    state["dialogue_memory"] = memory.to_dict()
    state["dialogue_memory_engine"] = ENGINE_VERSION
    state["dialogue_memory_window_hours"] = DIALOGUE_WINDOW_HOURS

    if latest_turn is not None:
        state["canonical_dialogue_turn"] = {
            "engine": ENGINE_VERSION,
            "turn_id": latest_turn.turn_id,
            "sequence_id": latest_turn.sequence_id,
            "created_at": latest_turn.created_at,
            "user_request": latest_turn.user_text,
            "april_answer": latest_turn.assistant_text,
            "interpretation": _copy(
                latest_turn.interpretation
            ),
            "assistant_structured": _copy(
                latest_turn.assistant_structured
            ),
            "artifacts": _copy(
                latest_turn.artifacts
            ),
            "provider_meta": _copy(
                latest_turn.provider_meta
            ),
            "structured_data": _copy(
                latest_turn.interpretation.get(
                    "structured_data"
                )
            ),
            "representation": _text(
                latest_turn.interpretation.get(
                    "representation"
                )
            ),
            "topic": _text(
                latest_turn.interpretation.get(
                    "topic"
                )
            ),
            "goal": _text(
                latest_turn.interpretation.get(
                    "goal"
                )
            ),
        }

    active = state.get(
        "active_dialogue_sequence"
    )
    if isinstance(active, dict):
        active["sequence_id"] = memory.sequence_id
        active["dialogue_memory"] = _copy(
            state["dialogue_memory"]
        )

        if latest_turn is not None:
            active["last_user_request"] = latest_turn.user_text
            active["last_april_answer"] = latest_turn.assistant_text
            active["topic"] = _text(
                latest_turn.interpretation.get(
                    "topic"
                )
            )
            active["goal"] = _text(
                latest_turn.interpretation.get(
                    "goal"
                )
            )
            active["representation"] = _text(
                latest_turn.interpretation.get(
                    "representation"
                )
            )
            active["last_result"] = _copy(
                latest_turn.assistant_structured
            )

        state["active_dialogue_sequence"] = active

    return state


def persist_with_state_manager(
    *,
    user_id: str,
    state: Dict[str, Any],
    latest_turn: Optional[DialogueTurn] = None,
) -> Dict[str, Any]:
    """
    Adapter for the project's existing StateManager.

    The production module owns actual persistence.
    """
    try:
        from blocks.state_manager import persist_state

        persist_state(
            user_id
        )
    except Exception as exc:
        state.setdefault(
            "diagnostics",
            {},
        )[
            "state_manager_persist_error"
        ] = _text(exc, 800)

    return state


# ---------------------------------------------------------------------------
# Canonical single-turn orchestration helper for tests.
# ---------------------------------------------------------------------------

async def process_turn(
    *,
    user_id: str,
    conversation_id: str,
    current_request: str,
    state: Optional[Dict[str, Any]],
    provider_call,
) -> Dict[str, Any]:
    """
    Test harness for the complete semantic cycle.

    provider_call(messages) must be an async callable compatible with the
    project's provider_router.generate_text contract.

    The test harness does not call a renderer.
    """
    state = state if isinstance(
        state,
        dict,
    ) else {}

    memory = memory_from_state(
        user_id=user_id,
        conversation_id=conversation_id,
        state=state,
    )

    history = state.get(
        "dialog",
        [],
    )
    history = history if isinstance(
        history,
        list,
    ) else []

    interpretation = interpret_request(
        current_request,
        cognition=state.get(
            "cognition",
            {},
        ),
        semantic=state.get(
            "semantic",
            {},
        ),
        history=history,
        state=state,
    )

    if interpretation is None:
        raise ValueError(
            "empty current request"
        )

    messages = build_openai_messages(
        current_request=current_request,
        interpretation=interpretation,
        memory=memory,
    )

    provider_result = await provider_call(
        messages
    )

    if not isinstance(
        provider_result,
        Mapping,
    ):
        provider_result = {
            "text": _text(
                provider_result
            )
        }

    latest_turn = record_openai_response(
        memory=memory,
        user_text=current_request,
        interpretation=interpretation,
        provider_result=provider_result,
    )

    write_memory_to_state(
        state=state,
        memory=memory,
        latest_turn=latest_turn,
    )

    persist_with_state_manager(
        user_id=user_id,
        state=state,
        latest_turn=latest_turn,
    )

    return {
        "engine": ENGINE_VERSION,
        "interpretation": interpretation,
        "provider_result": _copy(
            provider_result
        ),
        "canonical_turn": latest_turn.to_dict(),
        "dialogue_memory": memory.to_dict(),
        "provider_messages": messages,
        "single_route": True,
        "provider_calls": 1,
    }


# ---------------------------------------------------------------------------
# Executor compatibility bridge.
# ---------------------------------------------------------------------------

def build_processor_execution_context(
    runtime_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Existing Executor compatibility entrypoint.

    It exposes the canonical interpretation context without creating another
    route.
    """
    runtime_state = (
        runtime_state
        if isinstance(
            runtime_state,
            dict,
        )
        else {}
    )

    return {
        "transport": TRANSPORT_NAME,
        "engine": ENGINE_VERSION,
        "single_route": True,
        "legacy_trigger_execution": False,
        "keyword_routing": False,
        "interpretation": _copy(
            runtime_state.get(
                "_canonical_interpretation_dialogue"
            )
            or runtime_state.get(
                "canonical_interpretation"
            )
            or {}
        ),
        "dialogue_memory": _copy(
            runtime_state.get(
                "dialogue_memory"
            )
            or {}
        ),
        "active_dialogue_sequence": _copy(
            runtime_state.get(
                "active_dialogue_sequence"
            )
            or {}
        ),
        "provider_authority": "INTERPRETATION",
        "provider_must_not_reselect_context": True,
        "scene_contract": "canonical",
    }


def build_semantic_profile(
    text: str,
    *,
    history: Optional[List[Any]] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = state if isinstance(
        state,
        dict,
    ) else {}

    history = history if isinstance(
        history,
        list,
    ) else []

    latest = QUANTUM_DIALOGUE_ENGINE._stored_turns_from_state(
        history,
        state,
    )
    previous = latest[-1] if latest else None

    return {
        "engine": ENGINE_VERSION,
        "input_text": _text(text),
        "previous_turn_id": (
            previous.turn_id
            if previous
            else ""
        ),
        "context_similarity": (
            _semantic_similarity(
                text,
                previous.semantic_canvas(),
            )
            if previous
            else 0.0
        ),
        "history_available": bool(
            latest
        ),
        "structured_memory_available": any(
            bool(t.artifacts)
            or t.assistant_structured is not None
            for t in latest
        ),
        "legacy_trigger_execution": False,
    }


def build_scene_blueprint(
    *,
    text: str,
    requested_outputs: Sequence[str] = (),
    scene_composition: Sequence[Any] = (),
    production_representation: str = "text",
    active_topic: str = "",
    active_goal: str = "",
    subject: str = "",
    semantic_summary: str = "",
    dialogue: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Renderer-neutral blueprint.

    The processor may choose the actual renderer later.
    """
    reps: List[str] = []

    for value in list(
        requested_outputs or []
    ) + list(
        scene_composition or []
    ):
        if isinstance(
            value,
            Mapping,
        ):
            value = (
                value.get(
                    "representation"
                )
                or value.get(
                    "kind"
                )
                or value.get(
                    "type"
                )
            )

        candidate = _text(
            value
        )

        if (
            candidate
            and candidate in REPRESENTATIONS
            and candidate not in reps
        ):
            reps.append(candidate)

    preferred = _text(
        production_representation
    )

    if (
        preferred in REPRESENTATIONS
        and preferred not in reps
    ):
        reps.insert(
            0,
            preferred,
        )

    if not reps:
        reps = [
            "text"
        ]

    dialogue = (
        dialogue
        if isinstance(
            dialogue,
            dict,
        )
        else {}
    )

    return {
        "version": "unified_scene_blueprint_v1",
        "scene_kind": (
            "composite"
            if len(reps) > 1
            else reps[0]
        ),
        "representations": reps,
        "preferred_representation": (
            preferred
            if preferred in REPRESENTATIONS
            else reps[0]
        ),
        "active_topic": _text(
            active_topic,
            400,
        ),
        "active_goal": _text(
            active_goal,
            400,
        ),
        "subject": _text(
            subject,
            800,
        ),
        "semantic_summary": _text(
            semantic_summary
            or text,
            1800,
        ),
        "dialogue": {
            "relation": _text(
                dialogue.get(
                    "relation"
                )
                or "NEW"
            ).upper(),
            "continuation": bool(
                dialogue.get(
                    "continuation"
                )
            ),
            "reference_to_previous": bool(
                dialogue.get(
                    "reference_to_previous"
                )
            ),
            "scene_id": _text(
                dialogue.get(
                    "scene_id"
                )
            ),
        },
        "ownership": {
            "interpretation_owner": "INTERPRETATION_LAYER",
            "semantic_owner": "INTERPRETATION_LAYER",
            "renderer_owner": "PROCESSOR",
        },
        "renderer_neutral": True,
    }


# ---------------------------------------------------------------------------
# Integration metadata.
# ---------------------------------------------------------------------------

def integration_contract() -> Dict[str, Any]:
    """
    Explicitly documents the intended single route.

    No secondary route is created by this test file.
    """
    return {
        "interpretation_layer": "blocks.interpretation_layer",
        "executor": "blocks.executor",
        "provider": "blocks.provider_router.generate_text",
        "state_manager": {
            "get_state": "blocks.state_manager.get_state",
            "build_dialogue_memory_bridge":
                "blocks.state_manager.build_dialogue_memory_bridge",
            "update_dialog_context":
                "blocks.state_manager.update_dialog_context",
            "update_scene_context":
                "blocks.state_manager.update_scene_context",
            "persist_state":
                "blocks.state_manager.persist_state",
        },
        "artifact_contract":
            "blocks.C_ARTIFACT_CONTRACT",
        "presentation_formatter":
            "blocks.presentation_formatter",
        "context_system":
            "blocks.context_system",
        "route": [
            "INGEST",
            "INTERPRETATION",
            "DIALOGUE_RELATION",
            "STRUCTURED_CONTEXT",
            "PROVIDER",
            "STRUCTURED_RESPONSE",
            "CANONICAL_DIALOGUE_MEMORY",
            "SCENE_CONTRACT",
            "WEB",
        ],
        "single_route": True,
        "one_provider_call_per_turn": True,
        "renderer_independent": True,
        "legacy_triggers_enabled": False,
    }


# ---------------------------------------------------------------------------
# Test helpers.
# ---------------------------------------------------------------------------

def build_test_state(
    *,
    user_id: str = "test-user",
    conversation_id: str = "test-conversation",
) -> Dict[str, Any]:
    """
    Small in-memory fixture for local tests.
    """
    bucket = int(
        _now() // DIALOGUE_TTL_SECONDS
    )

    sequence_id = (
        "seq-"
        + hashlib.sha256(
            (
                f"{user_id}|"
                f"{conversation_id}|"
                f"{bucket}"
            ).encode("utf-8")
        ).hexdigest()[:20]
    )

    return {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "active_dialogue_sequence": {
            "sequence_id": sequence_id,
            "task_id": "",
        },
        "dialog": [],
        "dialogue_memory": {
            "engine": ENGINE_VERSION,
            "window": "12h",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "sequence_id": sequence_id,
            "ttl_seconds": DIALOGUE_TTL_SECONDS,
            "turns": [],
        },
        "cognition": {},
        "semantic": {},
    }


async def fake_provider(
    messages: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Provider fixture for a pure local contract test.

    It demonstrates that the provider may return a full structured dataset
    without the interpretation layer truncating it.
    """
    packet = json.loads(
        messages[-1]["content"]
    )

    interpretation = packet[
        "interpretation"
    ]

    existing_data = (
        interpretation.get(
            "structured_data"
        )
    )

    if existing_data is None:
        existing_data = {
            "x": list(range(1, 31)),
            "y": list(range(10, 40)),
        }

    representation = (
        interpretation.get(
            "representation"
        )
        or "line"
    )

    return {
        "model": "test-provider",
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
        },
        "answer": "Структурированный тестовый ответ.",
        "structured": {
            "kind": "graph",
            "title": "Тестовые данные",
            "representation": representation,
            "data": existing_data,
            "series": [
                {
                    "name": "series-1",
                    "data": existing_data,
                }
            ],
            "temporal_scope": {
                "kind": "month",
                "granularity": "day",
            },
            "metadata": {
                "point_count": len(
                    existing_data.get(
                        "x",
                        []
                    )
                )
            },
        },
    }


__all__ = [
    "ENGINE_VERSION",
    "TRANSPORT_NAME",
    "DECISION_OWNER",
    "DIALOGUE_WINDOW_HOURS",
    "PROVIDER_INPUT_HARD_BUDGET",
    "PROVIDER_OUTPUT_HARD_BUDGET",
    "REPRESENTATIONS",
    "STRUCTURED_KINDS",
    "DialogueTurn",
    "DialogueMemory",
    "InterpretationDecision",
    "StructuredArtifact",
    "UnifiedDialogueSemanticEngine",
    "QUANTUM_DIALOGUE_ENGINE",
    "QUANTUM_EVIDENCE_FUSION",
    "QUANTUM_INTERPRETATION_ENGINE",
    "QUANTUM_FAST_SEMANTIC",
    "QuantumInterpretationEngine",
    "interpret_request",
    "build_dialogue_context",
    "build_provider_request",
    "build_openai_messages",
    "extract_structured_artifacts",
    "record_openai_response",
    "memory_from_state",
    "write_memory_to_state",
    "persist_with_state_manager",
    "process_turn",
    "build_processor_execution_context",
    "build_semantic_profile",
    "build_scene_blueprint",
    "integration_contract",
    "build_test_state",
    "fake_provider",
]
