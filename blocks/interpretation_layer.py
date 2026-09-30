"""
APRIL INTERPRETATION LAYER — QUANTUM MATRIX ENGINE

Coordinated semantic environment for:
input -> interpretation council -> cognitive workspace -> evidence packet -> QUANTUM_PROCESSOR
      -> existing provider/rooms -> C_ARTIFACT_CONTRACT -> April Web

The interpretation layer never owns routing, providers, renderers, room execution,
or final response generation. Public compatibility helpers remain available so
downstream imports can continue using the same single route.
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None
try:
    import stanza
    from stanza.pipeline.multilingual import MultilingualPipeline
    from spacy.language import Language
except Exception:  # pragma: no cover
    stanza = None
    MultilingualPipeline = Any
    Language = Any

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    from transformers import pipeline as hf_pipeline
except Exception:  # pragma: no cover
    hf_pipeline = None


# ---------------------------------------------------------------------------
# Canonical constants
# ---------------------------------------------------------------------------

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"

DECISION_OWNER = "QUANTUM_PROCESSOR"
TRANSPORT_NAME = "transport_state"

SEMANTIC_MODEL_NAME = os.getenv(
    "APRIL_SENTENCE_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
NLI_MODEL_NAME = os.getenv(
    "APRIL_ZERO_SHOT_MODEL",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
)
SPACY_MODEL_NAME = os.getenv("APRIL_SPACY_MODEL", "xx_ent_wiki_sm")

APRIL_FAST_SEMANTIC_MODE = (
    os.getenv("APRIL_FAST_SEMANTIC_MODE", "1").strip().lower()
    in {"1", "true", "yes", "on"}
)
APRIL_ENABLE_HEAVY_HOTPATH = (
    os.getenv("APRIL_ENABLE_HEAVY_HOTPATH", "0").strip().lower()
    in {"1", "true", "yes", "on"}
)

DIALOGUE_LABELS = (
    "identity", "greeting", "question", "request", "reformulation",
    "continuation", "correction", "reference", "affirmation",
    "rejection", "new_topic", "statement", "independent", "memory_query",
)

REPRESENTATION_HYPOTHESES = {
    "text": "the user wants a normal textual answer",
    "table": "the user wants the information represented as a table",
    "graph": "the user wants the information represented as a graph or chart",
    "diagram": "the user wants a schematic or diagram with connected elements",
    "formula": "the user wants a mathematical formula or mathematical notation",
    "image": "the user wants an image or generated picture",
    "gallery": "the user wants multiple images or a gallery",
    "code": "the user wants executable source code",
    "link": "the user wants a link or web resource",
}

SEMANTIC_TURN_PROTOTYPES = {
    "identity": "пользователь спрашивает кто ты как тебя зовут представься назови себя; the user asks who you are or what your name is",
    "greeting": "пользователь приветствует ассистента начинает непринужденный разговор; the user is greeting the assistant",
    "question": "пользователь задаёт вопрос просит ответ или разъяснение сколько равен вычисли посчитай значение; the user asks a question requiring an answer or calculation",
    "request": "пользователь просит выполнить задачу сделать действие создать результат; the user asks the assistant to perform a task",
    "continuation": "пользователь хочет продолжить предыдущую тему развить предыдущий ответ; the user wants to continue the preceding task",
    "reformulation": "пользователь просит переделать переформулировать переработать предыдущий результат; the user asks to rework previous content",
    "correction": "пользователь исправляет изменяет уточняет предыдущую инструкцию; the user corrects or modifies a previous instruction",
    "reference": "пользователь ссылается на ранее обсуждённое или созданное; the user refers back to previous material",
    "memory_query": "пользователь просит вспомнить что он ранее спрашивал, какой вопрос задавал, о чем говорили, какой был прошлый вопрос или тема; the user asks to recall what they previously asked or discussed",
    "affirmation": "пользователь подтверждает согласие принимает предыдущий результат; the user confirms the preceding result",
    "rejection": "пользователь отклоняет предыдущий результат или предлагает другой вариант; the user rejects the preceding result",
    "new_topic": "пользователь начинает новую тему не связанную с предыдущим обсуждением; the user starts a new topic",
    "statement": "пользователь сообщает утверждение факт или мысль; the user makes a statement",
    "independent": "самостоятельный запрос не зависящий от предыдущих сообщений; the request is self contained and independent",
}

REPRESENTATION_HYPOTHESES = {
    "text": "обычный текстовый ответ объяснение рассказ описание; the user wants a normal textual answer",
    "table": "таблица таблицу структурированные строки колонки сравнение параметров; information represented as a table",
    "graph": "график графика диаграмма данных визуализация числовых значений; information represented as a graph or chart",
    "diagram": "схема диаграмма связей блоков структура процесса; a schematic or diagram with connected elements",
    "formula": "формула уравнение математическое выражение математическая запись; a mathematical formula or notation",
    "image": "изображение картинка рисунок иллюстрация создать изображение; an image or generated picture",
    "gallery": "несколько изображений подборка галерея сравнение изображений; multiple images or a gallery",
    "code": "код программный код функция программа реализация python; executable source code or software implementation",
    "link": "ссылка адрес сайта веб ресурс открыть ресурс интернет источник; a link or web resource",
}


DOMAIN_HYPOTHESES = {
    "biology": "биология живые организмы клетки генетика животные растения; biology living organisms genetics",
    "chemistry": "химия вещества реакции молекулы атомы химические процессы; chemistry substances reactions molecules",
    "physics": "физика энергия сила движение скорость масса поля; physics energy forces motion",
    "engineering": "инженерия конструкции проектирование система устройство архитектура; engineering design construction",
    "it": "программирование компьютер software код алгоритм приложение система; computing programming software",
    "literature": "литература писатель поэзия роман стихотворение произведение; literature writing poetry authors",
    "politics": "политика государство правительство выборы закон; politics government",
    "news": "новости текущие события последние события; current events news",
    "social": "общество социальные темы люди отношения; society social topics",
    "web": "интернет сайт веб поиск онлайн ресурс страница; web search online resource",
}


CAPABILITY_HYPOTHESES = {
    "exploration": "анализ сравнение исследование изучение разбор выводы; analysis comparison investigation",
    "web": "поиск в интернете онлайн ресурс сайт веб информация; web search online resource",
    "code": "код программирование программная реализация функция python; programming code implementation",
    "information": "объяснение информация фактический ответ что означает разъяснение; explanation factual answer",
    "discussion": "обсуждение мнение рассуждение позиция аргументы; discussion opinion reasoning",
    "space": "пространство сцена композиция визуальная структура расположение элементов; spatial scene composition",
}


SCENE_MATRIX_LABELS = (
    "text", "table", "graph", "diagram", "formula", "image", "gallery", "code", "link",
)
SCENE_MATRIX_FEATURES = (
    "dialogue", "representation", "domain", "capability",
    "continuity", "context", "modality",
)

# One scene matrix: rows=scenes, columns=evidence families.
_SCENE_WEIGHTS = (
    (0.12, 0.55, 0.03, 0.20, 0.04, 0.03, 0.03),
    (0.08, 0.62, 0.03, 0.20, 0.02, 0.03, 0.02),
    (0.04, 0.68, 0.05, 0.16, 0.02, 0.03, 0.02),
    (0.04, 0.62, 0.06, 0.20, 0.02, 0.04, 0.02),
    (0.03, 0.70, 0.07, 0.16, 0.01, 0.02, 0.01),
    (0.03, 0.72, 0.03, 0.17, 0.01, 0.02, 0.02),
    (0.03, 0.74, 0.03, 0.16, 0.01, 0.02, 0.01),
    (0.02, 0.70, 0.03, 0.22, 0.01, 0.01, 0.01),
    (0.02, 0.66, 0.05, 0.22, 0.01, 0.03, 0.01),
)

SCENE_MATRIX_CAPABILITY = {
    "text": "information", "table": "information", "graph": "exploration",
    "diagram": "space", "formula": "information", "image": "space",
    "gallery": "space", "code": "code", "link": "web",
}
SCENE_MATRIX_DOMAIN_BIAS = {
    "biology": {"graph": .08, "table": .06, "diagram": .08},
    "chemistry": {"formula": .10, "table": .05, "diagram": .05},
    "physics": {"graph": .09, "formula": .09, "diagram": .05},
    "engineering": {"diagram": .10, "graph": .06, "table": .04},
    "it": {"code": .10, "diagram": .06, "table": .04},
    "literature": {"text": .08},
    "politics": {"table": .06, "graph": .06},
    "news": {"link": .05, "table": .05, "graph": .05},
    "social": {"table": .04, "graph": .04},
    "web": {"link": .10},
}


# ---------------------------------------------------------------------------
# Provider-context planning constants
# ---------------------------------------------------------------------------

PROVIDER_INPUT_HARD_BUDGET = 900
PROVIDER_INPUT_SOFT_TARGET_NEW = 850
PROVIDER_INPUT_SOFT_TARGET_CONTINUE = 820
PROVIDER_INPUT_SOFT_TARGET_RECALL = 800
PROVIDER_CONTEXT_PLAN_VERSION = "provider_context_plan_v2_dependency_first"


SEMANTIC_ANCHOR_VERSION = "semantic_anchor_v1_topic_entity_direction_development"
SEMANTIC_ENTITY_TYPES = (
    "USER_IDENTITY", "PERSON", "STORY_ELEMENT", "OBJECT", "DOCUMENT",
    "LOCATION", "PRODUCT", "VEHICLE", "CONCEPT", "RESULT", "ARTIFACT",
    "DIAGRAM_OBJECT", "IMAGE_OBJECT", "CODE_OBJECT", "TASK", "UNKNOWN",
)


# ---------------------------------------------------------------------------
# Dialogue obligations / commitments
# ---------------------------------------------------------------------------

OBLIGATION_SCHEMA_VERSION = "april_dialogue_obligation_v1"


def _obligation_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def extract_dialogue_obligations(text: str) -> list[dict[str, Any]]:
    """Extract explicit future commitments without routing or execution.

    This is intentionally narrow: it records only commitments explicitly stated
    in the user turn. It never invents an obligation from a generic request.
    """
    text = _obligation_text(text)
    low = text.lower()
    if not text or "если" not in low:
        return []

    obligations: list[dict[str, Any]] = []

    # Assistant promise on a correct answer, e.g.:
    # "если я угадаю, ты мне нарисуешь картинку с фейерверком"
    correct_match = re.search(
        r"если\s+я\s+(?:угадаю|отгадаю|решу|дам\s+правильн\w*\s+ответ|отвечу\s+правильно)"
        r".*?(?:ты\s+мне\s+)?(?:нарисуешь|покажешь|покажешь\s+мне|создашь|сделаешь|пришл[её]шь)"
        r".*?(?:картин\w*|изображен\w*|рисунок\w*).*?фейерверк", low, re.S
    )
    if correct_match:
        obligations.append({
            "id": "correct_answer_fireworks_image",
            "schema": OBLIGATION_SCHEMA_VERSION,
            "actor": "april",
            "trigger": "user_answer_correct",
            "action": "render",
            "representation": "image",
            "object": "фейерверк",
            "prompt": "Красивый реалистичный фейерверк в ночном небе, праздничная сцена, яркие разноцветные вспышки, высокая детализация.",
            "status": "pending",
            "source": "explicit_user_commitment",
            "source_text": text[:1600],
            "created_at": time.time(),
        })

    # Explicit negative branch. We keep it because it is part of the same
    # conditional promise and prevents the next turn from guessing what the
    # user expected April to say after an incorrect answer.
    negative_match = re.search(
        r"если\s+я\s+не\s+(?:угадаю|отгадаю|решу|дам\s+правильн\w*\s+ответ|отвечу\s+правильно)"
        r".*?(?:ты\s+(?:скажешь|напишешь|ответишь))\s*[«\"']?([^»\"']{10,180})",
        low, re.S
    )
    if negative_match:
        phrase = _obligation_text(negative_match.group(1))
        obligations.append({
            "id": "incorrect_answer_fireworks_text",
            "schema": OBLIGATION_SCHEMA_VERSION,
            "actor": "april",
            "trigger": "user_answer_incorrect",
            "action": "say",
            "representation": "text",
            "object": "",
            "text": phrase,
            "status": "pending",
            "source": "explicit_user_commitment",
            "source_text": text[:1600],
            "created_at": time.time(),
        })

    return obligations


def merge_dialogue_obligations(*sources: Any) -> list[dict[str, Any]]:
    """Merge obligations deterministically while preserving fulfillment state."""
    items: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, list):
            continue
        for raw in source:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            oid = _obligation_text(item.get("id"))
            if not oid:
                continue
            found = next((x for x in items if x.get("id") == oid), None)
            if found is None:
                items.append(item)
                continue
            # New wording may update the prompt, but terminal state wins.
            terminal = {"fulfilled", "cancelled"}
            if found.get("status") not in terminal:
                found.update({k: v for k, v in item.items() if v not in (None, "", [], {})})
    return items[-12:]


def _obligation_matches_request(obligation: dict[str, Any], text: str) -> bool:
    if not isinstance(obligation, dict):
        return False
    low = _obligation_text(text).lower()
    if not low:
        return False
    obj = _obligation_text(obligation.get("object")).lower()
    if obj and obj in low:
        return True
    return bool(
        obligation.get("representation") == "image"
        and any(x in low for x in ("картин", "изображ", "нарис", "покажи", "фейерверк"))
    )


def mark_obligation_status(obligations: Any, *, trigger: str, text: str = "") -> list[dict[str, Any]]:
    """Return an updated obligation list after a semantic trigger."""
    result = merge_dialogue_obligations([], obligations)
    for item in result:
        if item.get("status") in {"fulfilled", "cancelled"}:
            continue
        if item.get("trigger") == trigger:
            item["status"] = "ready"
            item["triggered_by"] = _obligation_text(text)[:1600]
            item["triggered_at"] = time.time()
    return result


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


class LiveSceneContinuityEngine:
    """
    Stateful semantic dialogue owner.

    The engine separates four concepts that were previously collapsed into one
    field:

        scene            = the conversational container
        task             = the currently open thing the user is acting on
        entity           = an object inside that task
        history          = evidence only

    The crucial invariant is:

        CURRENT OPEN TASK > STALE SEQUENCE ENTITY > HISTORICAL MEMORY

    A short answer to an open question/riddle is therefore resolved against
    the open task before topic-boundary logic is evaluated.  A request to
    change the task creates a new task revision inside the same conversation
    instead of inheriting the old entity.

    The engine does not execute providers or renderers.  It only produces and
    bridges semantic evidence/state for the existing pipeline.
    """

    VERSION = "live_scene_continuity_v2_task_ownership"
    ACTIVE_STATUSES = {"active", "open", "continuing", "resumable", "answer_received"}
    MAX_MEMORY_ITEMS = 8

    @staticmethod
    def _text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    @classmethod
    def _tokens(cls, value: Any) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", cls._text(value).lower())

    @classmethod
    def _scene_from_state(cls, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(state, dict):
            return {}

        candidates = [
            state.get("scene_state"),
            state.get("active_scene"),
            state.get("active_visual_scene"),
            state.get("current_visual_scene"),
            state.get("active_flow"),
        ]

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            nested = candidate.get("live_scene")
            if isinstance(nested, dict) and (
                nested.get("scene_id")
                or nested.get("status") in cls.ACTIVE_STATUSES
                or nested.get("open_task")
                or nested.get("task_state")
            ):
                return dict(nested)

            if (
                candidate.get("scene_id")
                or candidate.get("status") in cls.ACTIVE_STATUSES
                or candidate.get("open_task")
                or candidate.get("task_state")
            ):
                return dict(candidate)

        return {}

    @classmethod
    def _memory_projection(
        cls,
        state: dict[str, Any],
        scene_topic: str,
        active_scene_id: str,
    ) -> list[dict[str, Any]]:
        raw = state.get("memory_timeline", {}) if isinstance(state, dict) else {}
        items: list[dict[str, Any]] = []

        if isinstance(raw, dict):
            values: list[Any] = []
            for value in raw.values():
                values.extend(value if isinstance(value, list) else [value])
        elif isinstance(raw, list):
            values = raw
        else:
            values = []

        topic_tokens = set(cls._tokens(scene_topic))
        live_sequence = (
            state.get("active_dialogue_sequence")
            if isinstance(state.get("active_dialogue_sequence"), dict)
            else {}
        )
        live_sequence_id = cls._text(live_sequence.get("sequence_id"))
        user_id = cls._text(state.get("user_id"))
        conversation_id = cls._text(state.get("conversation_id"))

        for item in reversed(values):
            if not isinstance(item, dict):
                continue

            same_sequence = bool(
                live_sequence_id
                and cls._text(item.get("sequence_id")) == live_sequence_id
                and (not user_id or cls._text(item.get("user_id")) in {"", user_id})
                and (not conversation_id or cls._text(item.get("conversation_id")) in {"", conversation_id})
            )
            same_scene = cls._text(
                item.get("scene_id")
                or item.get("visual_scene_id")
                or item.get("source_scene_id")
            ) == cls._text(active_scene_id)

            # Live sequence/scene memory is useful only as evidence.  It does
            # not decide who owns the current task.
            if same_scene or same_sequence:
                items.append(dict(item))
                if len(items) >= cls.MAX_MEMORY_ITEMS:
                    break
                continue

            text = cls._text(
                item.get("summary")
                or item.get("content")
                or item.get("text")
                or item.get("answer")
                or item.get("user_request")
            )
            if not text:
                continue

            tokens = set(cls._tokens(text))
            if topic_tokens and len(topic_tokens & tokens) > 0:
                items.append(dict(item))
            if len(items) >= cls.MAX_MEMORY_ITEMS:
                break

        return items[-cls.MAX_MEMORY_ITEMS:]

    # ------------------------------ task model ------------------------------

    @classmethod
    def _history_turns(cls, history: Any) -> list[dict[str, Any]]:
        turns = history if isinstance(history, list) else []
        out: list[dict[str, Any]] = []

        for item in turns:
            if not isinstance(item, dict):
                continue

            user = ""
            assistant = ""

            if isinstance(item.get("user"), dict):
                user = cls._text(
                    item["user"].get("text")
                    or item["user"].get("content")
                    or item["user"].get("answer")
                )
            elif str(item.get("role") or "").lower() in {"user", "human"}:
                user = cls._text(item.get("content") or item.get("text"))

            if isinstance(item.get("april"), dict):
                assistant = cls._text(
                    item["april"].get("answer")
                    or item["april"].get("content")
                    or item["april"].get("summary")
                )
            elif str(item.get("role") or "").lower() in {"assistant", "april", "bot"}:
                assistant = cls._text(
                    item.get("answer") or item.get("content") or item.get("summary")
                )

            if user or assistant:
                out.append(
                    {
                        "user": user,
                        "assistant": assistant,
                        "turn_id": item.get("turn_id"),
                        "scene_id": cls._text(
                            item.get("scene_id") or item.get("visual_scene_id")
                        ),
                        "raw": item,
                    }
                )
        return out

    @classmethod
    def _latest_assistant(
        cls,
        history: list[dict[str, Any]],
        scene: dict[str, Any],
    ) -> str:
        direct = cls._text(
            scene.get("last_april_turn")
            or scene.get("april_answer")
            or scene.get("answer")
        )
        if direct:
            return direct

        for turn in reversed(history):
            value = cls._text(turn.get("assistant"))
            if value:
                return value
        return ""

    @classmethod
    def _latest_user(
        cls,
        history: list[dict[str, Any]],
        scene: dict[str, Any],
    ) -> str:
        direct = cls._text(
            scene.get("last_user_turn")
            or scene.get("user_request")
            or scene.get("current_request")
        )
        if direct:
            return direct

        for turn in reversed(history):
            value = cls._text(turn.get("user"))
            if value:
                return value
        return ""

    @classmethod
    def _task_mapping(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}

        # Normalize all known spellings into one stable shape.
        nested_candidates = [
            value.get("open_task"),
            value.get("task_state"),
            value.get("active_task"),
            value.get("dialogue_task"),
            value.get("pending_task"),
        ]
        for nested in nested_candidates:
            if isinstance(nested, dict) and nested:
                merged = dict(value)
                merged.update(nested)
                value = merged
                break

        status = cls._text(value.get("status")).lower()
        kind = cls._text(
            value.get("kind")
            or value.get("type")
            or value.get("task_type")
            or value.get("dialogue_type")
        ).lower()
        prompt = cls._text(
            value.get("prompt")
            or value.get("question")
            or value.get("task_prompt")
            or value.get("text")
        )
        target = cls._text(
            value.get("target")
            or value.get("target_entity")
            or value.get("active_entity")
            or value.get("entity")
        )

        # Terminal interactive tasks remain useful as historical evidence, but
        # they are no longer an open semantic owner of the next user turn.
        # Previously `kind == riddle/game/...` kept solved tasks active forever,
        # which let an old riddle leak into later image/table/diagram requests.
        terminal = status in {"solved", "completed", "closed", "cancelled", "canceled"}
        active = bool(
            not terminal
            and (
                value.get("pending_input")
                or value.get("open")
                or value.get("active")
                or status in cls.ACTIVE_STATUSES
                or kind in {"riddle", "question", "game", "choice"}
                or prompt
            )
        )

        if not active:
            return {}

        expected = cls._text(
            value.get("expected_input_type")
            or value.get("input_type")
            or "answer"
        )

        def _list(name: str) -> list[Any]:
            raw = value.get(name)
            if isinstance(raw, (list, tuple)):
                return [item for item in raw if item not in (None, "", {}, [])]
            return []

        qa_history = _list("qa_history")
        if not qa_history:
            qa_history = _list("turns")
        known_clues = _list("known_clues")
        obligations = [
            dict(item) for item in _list("obligations")
            if isinstance(item, dict) and item.get("id")
        ]
        return {
            "active": True,
            "status": status or "open",
            "kind": kind or "task",
            "role": cls._text(
                value.get("role")
                or value.get("game_role")
                or value.get("task_role")
                or ""
            ),
            "phase": cls._text(value.get("phase") or value.get("task_phase") or ""),
            "prompt": prompt,
            "last_question": cls._text(
                value.get("last_question")
                or value.get("question")
                or (value.get("prompt") if kind in {"question", "riddle"} else "")
            ),
            "expected_input_type": expected,
            "target": target,
            "secret_target": cls._text(
                value.get("secret_target")
                or value.get("hidden_target")
                or value.get("private_target")
            ),
            "candidate_answer": cls._text(
                value.get("candidate_answer") or value.get("answer_candidate")
            ),
            "last_user_answer": cls._text(
                value.get("last_user_answer")
                or value.get("user_answer")
                or value.get("candidate_answer")
            ),
            "known_clues": known_clues[-12:],
            "qa_history": qa_history[-12:],
            "turns": qa_history[-12:],
            "obligations": obligations[-12:],
            "task_outcome": cls._text(value.get("task_outcome") or value.get("outcome")),
            "awaiting_user": bool(
                value.get("awaiting_user")
                or value.get("awaiting_input")
                or expected in {"answer", "user_answer"}
            ),
            "completed": bool(value.get("completed")),
            "topic": cls._text(value.get("topic") or value.get("canonical_topic")),
            "goal": cls._text(value.get("goal") or value.get("task_goal")),
            "sequence_id": cls._text(value.get("sequence_id") or value.get("active_sequence_id")),
            "scene_id": cls._text(value.get("scene_id") or value.get("source_scene_id")),
            "task_revision": int(value.get("task_revision", 0) or 0),
            "source": cls._text(value.get("source") or "state"),
            "raw": dict(value),
        }

    @classmethod
    def _interactive_task_state(
        cls,
        state: dict[str, Any],
        scene: dict[str, Any],
        sequence: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the newest explicit interactive-task state without guessing ownership."""
        candidates: list[Any] = [
            state.get("interactive_task_state"),
            state.get("task_context_state"),
            state.get("open_task"),
            state.get("active_task"),
            scene.get("interactive_task_state"),
            scene.get("open_task"),
            scene.get("task_state"),
            sequence.get("interactive_task_state"),
            sequence.get("open_task"),
            sequence.get("task_state"),
        ]
        for value in candidates:
            mapped = cls._task_mapping(value)
            if mapped:
                return mapped
        return {}

    @classmethod
    def _is_interactive_start(cls, text: str) -> dict[str, Any]:
        """Understand conversational task shape (game/riddle), independent of routing."""
        low = cls._text(text).lower()
        words = cls._tokens(low)
        if not low:
            return {"active": False}

        user_holds_object = (
            ("я загадал" in low or "я загадала" in low or "моя очередь" in low)
            and any(x in low for x in ("задавай вопросы", "угадывай", "отгадывай", "вопрос"))
        )
        new_game = (
            "игр" in low
            and any(x in low for x in ("сыграем", "играем", "давай", "начн"))
        )
        riddle_request = (
            any(x in low for x in ("загадай", "загадку", "придумай загадку"))
            or ("задай" in low and "задач" in low)
            or ("придумай" in low and any(x in low for x in ("еще", "ещё", "друг", "нов", "слож")))
        )

        if user_holds_object:
            return {
                "active": True,
                "kind": "game",
                "role": "april_guesses_user_object",
                "phase": "asking_questions",
                "status": "assistant_turn",
                "expected_input_type": "assistant_question",
                "goal": "guess_user_object",
                "topic": "игра",
                "known_clues": [cls._text(text)],
                "qa_history": [],
                "source": "interactive_task_understanding",
            }
        if new_game:
            return {
                "active": True,
                "kind": "game",
                "role": "april_holds_secret",
                "phase": "generate_secret",
                "status": "pending_generation",
                "expected_input_type": "assistant_generation",
                "goal": "guess_secret",
                "topic": "игра",
                "known_clues": [],
                "qa_history": [],
                "source": "interactive_task_understanding",
            }
        if riddle_request:
            return {
                "active": True,
                "kind": "riddle",
                "role": "april_asks_riddle",
                "phase": "generate_riddle",
                "status": "pending_generation",
                "expected_input_type": "assistant_generation",
                "goal": "solve_riddle",
                "topic": "загадка",
                "known_clues": [],
                "qa_history": [],
                "source": "interactive_task_understanding",
            }
        return {"active": False}

    @classmethod
    def _task_action_of_open_task(
        cls,
        text: str,
        task: dict[str, Any],
        dialogue: dict[str, Any],
    ) -> dict[str, Any]:
        if not task.get("active"):
            return {"is_task_action": False, "confidence": 0.0, "reason": "no_open_task"}

        normalized = cls._text(text)
        low = normalized.lower()
        label = cls._text(dialogue.get("label")).lower()
        expected_input = cls._text(task.get("expected_input_type")).lower()
        awaiting_user_answer = bool(
            task.get("awaiting_user")
            or expected_input in {"answer", "user_answer"}
            or task.get("phase") == "awaiting_user_answer"
        )
        if not normalized:
            return {"is_task_action": False, "confidence": 0.0, "reason": "empty"}

        explicit_external = any(
            marker in low
            for marker in (
                "другая тема", "сменим тему", "перейдем к", "перейдём к",
                "давай про другое", "а теперь про", "отдельно поговорим"
            )
        )
        if explicit_external:
            return {"is_task_action": False, "confidence": 0.0, "reason": "external_topic"}

        # A task-control turn is a discourse move inside the active task:
        # continue, solve, guess, or ask for the accumulated result.
        control_semantics = (
            "угадывай", "угадай", "отгадывай", "отгадай",
            "решай", "реши", "продолжай", "дальше",
            "какой ответ", "правильный ответ", "что это",
            "мы же играем", "анализируй", "анализируйся",
        )
        control_score = sum(1 for cue in control_semantics if cue in low)
        if control_score > 0:
            return {
                "is_task_action": True,
                "confidence": min(0.99, 0.86 + 0.04 * control_score),
                "reason": "task_control_discourse",
            }

        if (
            not awaiting_user_answer
            and label in {"continuation", "reference", "affirmation", "rejection", "correction"}
        ):
            return {
                "is_task_action": True,
                "confidence": 0.88,
                "reason": "task_discourse_relation",
            }

        return {"is_task_action": False, "confidence": 0.0, "reason": "ordinary_task_turn"}

    @classmethod
    def _merge_assistant_task_update(
        cls,
        task: dict[str, Any],
        assistant_text: str,
    ) -> dict[str, Any]:
        """Advance the live task to the latest assistant question/interaction."""
        current = dict(task or {})
        text = cls._text(assistant_text)
        if not text:
            return current

        inferred = cls._infer_task_from_assistant(
            text,
            scene_id=cls._text(current.get("scene_id")),
            sequence_id=cls._text(current.get("sequence_id")),
        )
        if not inferred:
            return current

        merged = dict(current)
        # A newer assistant question supersedes the old prompt. It is the current
        # operand for the next user turn, while accumulated task memory survives.
        if inferred.get("kind") == "question":
            merged.update({
                "kind": current.get("kind") or "question",
                "role": current.get("role") or "april_questions_user",
                "phase": "awaiting_user_answer",
                "status": "open",
                "prompt": inferred.get("prompt") or text,
                "last_question": text,
                "expected_input_type": "answer",
                "awaiting_user": True,
            })
        elif inferred.get("kind") == "game":
            merged.update({
                "kind": "game",
                "role": current.get("role") or inferred.get("role") or "april_holds_secret",
                "phase": current.get("phase") or inferred.get("phase") or "awaiting_user_input",
                "status": "open",
                "prompt": text,
                "expected_input_type": "answer",
                "awaiting_user": True,
            })

        # The assistant's latest output is a new task boundary only when its
        # discourse form actually establishes a new task.
        merged["task_revision"] = max(
            int(current.get("task_revision", 0) or 0),
            int(inferred.get("task_revision", 1) or 1),
        ) + (1 if merged.get("last_question") and merged.get("last_question") != current.get("last_question") else 0)
        merged["source"] = "latest_assistant_task_update"
        return merged

    @classmethod
    def _assistant_question_is_task(cls, assistant_text: str) -> bool:
        text = cls._text(assistant_text)
        if not text:
            return False

        question_form = "?" in text or "？" in text
        lowered = text.lower()
        game_structure = any(
            marker in lowered
            for marker in (
                "я уже загадал",
                "я загадал",
                "я загадаю",
                "задавай вопросы",
                "угадай слово",
                "угадайте слово",
                "играем в",
            )
        )
        riddle_structure = (
            "что это" in lowered
            or "угадай" in lowered
            or "какое слово" in lowered
            or "отгада" in lowered
            or "как определить" in lowered
            or "как отличить" in lowered
            or "что получится" in lowered
        )
        words = cls._tokens(text)
        long_question = question_form and len(words) >= 5
        return bool(question_form and (riddle_structure or long_question) or game_structure)

    @classmethod
    def _infer_task_from_assistant(
        cls,
        assistant_text: str,
        *,
        scene_id: str = "",
        sequence_id: str = "",
    ) -> dict[str, Any]:
        text = cls._text(assistant_text)
        if not cls._assistant_question_is_task(text):
            return {}

        lowered = text.lower()
        game_structure = any(
            marker in lowered
            for marker in (
                "я уже загадал",
                "я загадал",
                "я загадаю",
                "задавай вопросы",
                "угадай слово",
                "играем в",
            )
        )
        if game_structure:
            return {
                "active": True,
                "status": "open",
                "kind": "game",
                "role": "april_holds_secret",
                "phase": "awaiting_user_input",
                "prompt": text,
                "last_question": text if ("?" in text or "？" in text) else "",
                "expected_input_type": "answer",
                "target": "",
                "secret_target": "",
                "candidate_answer": "",
                "last_user_answer": "",
                "known_clues": [],
                "qa_history": [],
                "turns": [],
                "awaiting_user": True,
                "completed": False,
                "topic": "игра",
                "goal": "guess_secret",
                "sequence_id": sequence_id,
                "scene_id": scene_id,
                "task_revision": 1,
                "source": "assistant_task_inference",
                "raw": {},
            }

        return {
            "active": True,
            "status": "open",
            "kind": "riddle" if any(
                marker in lowered for marker in (
                    "угадай", "что это", "какое слово", "отгада",
                    "как определить", "как отличить"
                )
            ) else "question",
            "role": "april_questions_user",
            "phase": "awaiting_user_answer",
            "prompt": text,
            "last_question": text,
            "expected_input_type": "answer",
            "target": "",
            "secret_target": "",
            "candidate_answer": "",
            "last_user_answer": "",
            "known_clues": [],
            "qa_history": [],
            "turns": [],
            "awaiting_user": True,
            "completed": False,
            "topic": "загадка" if "угадай" in lowered or "что это" in lowered else "вопрос",
            "goal": "solve_riddle" if "угадай" in lowered or "что это" in lowered else "answer_question",
            "sequence_id": sequence_id,
            "scene_id": scene_id,
            "task_revision": 1,
            "source": "assistant_task_inference",
            "raw": {},
        }

    @classmethod
    def _find_open_task(
        cls,
        state: dict[str, Any],
        history: list[dict[str, Any]],
        scene: dict[str, Any],
        previous_assistant: str,
    ) -> dict[str, Any]:
        sequence = state.get("active_dialogue_sequence")
        sequence = sequence if isinstance(sequence, dict) else {}

        explicit = cls._interactive_task_state(state, scene, sequence)
        inferred = cls._infer_task_from_assistant(
            previous_assistant,
            scene_id=cls._text(scene.get("scene_id")),
            sequence_id=cls._text(
                scene.get("sequence_id") or sequence.get("sequence_id")
            ),
        )

        if explicit:
            # The newest assistant question supersedes a stale persisted question.
            # Do not throw away private game state while refreshing the prompt.
            if inferred:
                explicit = cls._merge_assistant_task_update(explicit, previous_assistant)

            # A current explicit task is always more authoritative than a generic
            # historical active entity/topic.
            return explicit

        if inferred:
            return inferred

        # Recover an interactive task from recent history when state was partially
        # persisted by a legacy writer.
        for turn in reversed(history[-12:]):
            assistant = cls._text(turn.get("assistant"))
            if not assistant:
                continue
            candidate = cls._infer_task_from_assistant(
                assistant,
                scene_id=cls._text(turn.get("scene_id")),
                sequence_id=cls._text(sequence.get("sequence_id")),
            )
            if candidate:
                return candidate

        return {}

    @classmethod
    def _explicit_task_transition(
        cls,
        text: str,
        dialogue: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detect a discourse-level request to replace the current task.

        This is not topic routing by keyword.  It is a control relation:
        the user explicitly asks the assistant to produce/continue a different
        task, reset the current task, or discard its current target.
        """
        normalized = cls._text(text)
        low = normalized.lower()
        label = cls._text(dialogue.get("label")).lower()

        reset_markers = (
            "заново",
            "другое",
            "другую",
            "другое слово",
            "новую",
            "новое",
            "еще придумай",
            "ещё придумай",
            "загадай другое",
            "загадай ещё",
            "загадай еще",
            "посложней",
            "посложнее",
            "удали его из памяти",
            "забудь его",
            "не это",
        )

        riddle_creation_semantics = (
            ("загад" in low and any(x in low for x in ("друг", "нов", "ещ", "занов")))
            or ("придумай" in low and any(x in low for x in ("еще", "ещё", "друг", "нов")))
            or ("загадай" in low and any(x in low for x in ("друг", "нов", "ещ", "занов", "слож")))
            or ("задай" in low and "задач" in low)
            or ("если я" in low and any(x in low for x in ("угадаю", "отгадаю", "решу")) and "картин" in low)
        )

        explicit_control = any(marker in low for marker in reset_markers)
        correction_control = label in {"correction", "rejection"} and riddle_creation_semantics

        reset_memory = "памят" in low and any(
            x in low for x in ("удали", "забудь", "убери", "очист")
        )

        requested_new_task = bool(explicit_control or correction_control or riddle_creation_semantics)

        return {
            "requested": requested_new_task,
            "reset_memory": reset_memory,
            "replace_task": requested_new_task,
            "source": "discourse_task_transition",
        }

    @classmethod
    def _answer_of_open_task(
        cls,
        text: str,
        task: dict[str, Any],
        dialogue: dict[str, Any],
    ) -> dict[str, Any]:
        if not task.get("active"):
            return {
                "is_answer": False,
                "confidence": 0.0,
                "reason": "no_open_task",
            }

        normalized = cls._text(text)
        if not normalized:
            return {"is_answer": False, "is_task_action": False, "confidence": 0.0, "reason": "empty"}

        low = normalized.lower()
        words = cls._tokens(normalized)
        label = cls._text(dialogue.get("label")).lower()
        imperative_lexemes = {
            "включи", "выключи", "скажи", "расскажи", "покажи", "придумай",
            "загадай", "нарисуй", "напиши", "объясни", "сформулируй", "удали",
            "забудь", "убери", "сделай", "проверь", "посмотри", "построй",
            "создай", "выбери", "перейди", "добавь", "замени", "оставь",
        }
        imperative_form = any(
            token in imperative_lexemes
            or (
                len(token) >= 5
                and re.search(r"(?:ай|ей|уй|жи|ши|чи)$", token)
                and token not in {"первый", "второй", "третий", "правильный", "который"}
            )
            for token in words
        )

        # A request to replace the current task is a task-control move, not an
        # answer.  Keep it separate so the dialogue owner can replace the task
        # without destroying the surrounding conversation.
        transition = cls._explicit_task_transition(normalized, dialogue)
        if transition.get("requested"):
            return {
                "is_answer": False,
                "is_task_action": False,
                "confidence": 0.0,
                "reason": "task_transition_requested",
            }

        # A control/analysis request can be an interaction with the open task
        # even when it is grammatically imperative.  This is especially important
        # for turns such as "угадывай", "анализируй" and "мы же играем": they ask
        # the assistant to operate on the current task, not to start a new topic.
        task_action = cls._task_action_of_open_task(
            normalized,
            task,
            dialogue,
        )
        if task_action.get("is_task_action"):
            return {
                "is_answer": False,
                "is_task_action": True,
                "confidence": float(task_action.get("confidence", 0.0) or 0.0),
                "reason": task_action.get("reason") or "task_control_discourse",
            }

        # Once an active task exists, user turns are interpreted as task
        # interaction unless there is strong evidence of an external topic
        # boundary.  Riddle/game turns intentionally allow low lexical overlap.
        question_form = "?" in normalized or "？" in normalized
        explicit_external = any(
            marker in low
            for marker in (
                "другая тема",
                "отдельно",
                "поговорим о другом",
                "давай про другое",
                "сменим тему",
                "перейдем к",
                "перейдём к",
                "а теперь про",
            )
        )

        answer_shape = (
            len(words) <= 18
            and not explicit_external
            and (
                not question_form
                or label
                in {
                    "question",
                    "continuation",
                    "reference",
                    "affirmation",
                    "rejection",
                    "correction",
                }
            )
        )

        # Explicit references to the active task have very high authority.
        task_reference = any(
            marker in low
            for marker in (
                "твой ответ",
                "твоя загадка",
                "на твою загадку",
                "на вопрос",
                "правильный ответ",
                "мой ответ",
                "это оно",
                "это он",
                "это она",
            )
        )

        if explicit_external:
            return {
                "is_answer": False,
                "is_task_action": False,
                "confidence": 0.0,
                "reason": "explicit_external_topic",
            }

        # Imperative morphology usually addresses the assistant with a new
        # instruction ("Расскажи про Tesla", "Покажи ..."), not an answer to
        # the active riddle.  This is discourse-shape evidence, not routing.
        if imperative_form and len(words) >= 2:
            return {
                "is_answer": False,
                "is_task_action": False,
                "confidence": 0.0,
                "reason": "new_directive_shape",
            }

        if task_reference:
            return {
                "is_answer": True,
                "is_task_action": False,
                "confidence": 0.99,
                "reason": "explicit_task_reference",
            }

        if task.get("kind") in {"riddle", "game", "choice"} and answer_shape:
            return {
                "is_answer": True,
                "is_task_action": False,
                "confidence": 0.94 if not question_form else 0.88,
                "reason": "open_interactive_task",
            }

        if task.get("kind") == "question":
            if answer_shape:
                return {
                    "is_answer": True,
                    "is_task_action": False,
                    "confidence": 0.86,
                    "reason": "open_question",
                }

        # Generic open tasks still receive protection when the user asks a
        # short follow-up rather than introducing a distinct request.
        if len(words) <= 7 and label in {
            "continuation",
            "reference",
            "affirmation",
            "rejection",
            "correction",
        }:
            return {
                "is_answer": True,
                "is_task_action": False,
                "confidence": 0.82,
                "reason": "short_discourse_followup",
            }

        return {
            "is_answer": False,
            "is_task_action": False,
            "confidence": 0.0,
            "reason": "not_task_answer",
        }

    @classmethod
    def _explicit_topic_break(
        cls,
        text: str,
        profile: dict[str, Any],
        dialogue: dict[str, Any],
        active_topic: str,
    ) -> dict[str, Any]:
        normalized = cls._text(text)
        low = normalized.lower()
        words = cls._tokens(normalized)

        context = profile.get("context_scores", {}) or {}
        dialogue_scores = profile.get("dialogue_scores", {}) or {}

        topic_relation = float(context.get("active_topic", 0.0) or 0.0)
        goal_relation = float(context.get("active_goal", 0.0) or 0.0)
        explicit_new = float(dialogue_scores.get("new_topic", 0.0) or 0.0)
        independent = float(dialogue_scores.get("independent", 0.0) or 0.0)

        explicit_markers = (
            "другая тема",
            "сменим тему",
            "перейдем к",
            "перейдём к",
            "давай теперь про",
            "а теперь поговорим",
            "отдельно хочу",
            "новая тема",
        )
        explicit_boundary = any(marker in low for marker in explicit_markers)

        question_like = "?" in normalized or "？" in normalized
        short_turn = len(words) <= 7
        dialogue_label = cls._text(dialogue.get("label")).lower()
        discourse_continuation = dialogue_label in {
            "continuation",
            "reference",
            "affirmation",
            "rejection",
            "correction",
            "reformulation",
        }

        # Lightweight linguistic structure: imperative morphology is evidence
        # of a self-contained request even when the matrix prototype score is
        # weak for a single word such as "Придумай".  This is linguistic
        # understanding, not command routing.
        imperative_lexemes = {
            "включи", "выключи", "скажи", "расскажи", "покажи", "придумай",
            "загадай", "нарисуй", "напиши", "объясни", "сформулируй", "удали",
            "забудь", "убери", "сделай", "проверь", "посмотри", "построй",
            "создай", "выбери", "перейди", "добавь", "замени", "оставь",
        }
        imperative_form = any(
            token in imperative_lexemes
            or (
                len(token) >= 5
                and re.search(r"(?:ай|ей|уй|жи|ши|чи)$", token)
                and token not in {"первый", "второй", "третий", "правильный", "который"}
            )
            for token in words
        )
        collaborative_request = any(
            phrase in low
            for phrase in (
                "давай",
                "поиграем",
                "сыграем",
                "начнем",
                "начнём",
                "продолжим",
            )
        )

        # A self-contained request can legitimately open a new topic even while
        # another interactive task is open.  Task-transition requests are
        # handled separately and remain inside the same conversational scene.
        request_boundary = (
            (dialogue_label == "request" or imperative_form or collaborative_request)
            and topic_relation < 0.25
            and goal_relation < 0.25
            and not question_like
        )

        # Semantic novelty is considered only for a self-contained request.
        semantic_novelty = (
            explicit_new >= 0.58
            and independent >= 0.12
            and topic_relation < 0.14
            and goal_relation < 0.14
            and not discourse_continuation
            and not question_like
            and (not short_turn or dialogue_label == "request")
        )

        return {
            "explicit": explicit_boundary,
            "request_boundary": bool(request_boundary),
            "semantic": bool(semantic_novelty),
            "topic_relation": round(topic_relation, 6),
            "goal_relation": round(goal_relation, 6),
            "explicit_new_topic": round(explicit_new, 6),
            "independent": round(independent, 6),
            "active_topic": active_topic,
            "source": "semantic_topic_boundary",
        }

    @classmethod
    def _topic_change_evidence(
        cls,
        text: str,
        active_scene: dict[str, Any],
        profile: dict[str, Any],
        dialogue: dict[str, Any],
        active_topic: str,
        *,
        open_task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        boundary = cls._explicit_topic_break(
            text, profile, dialogue, active_topic
        )
        task_answer = cls._answer_of_open_task(
            text,
            open_task or {},
            dialogue,
        )

        task_transition = cls._explicit_task_transition(text, dialogue)

        # Open task ownership wins over weak novelty.  Both an actual answer and
        # a task-control/analysis turn belong to the active task.  They must not
        # be reclassified as a new topic merely because lexical overlap is low.
        protected_by_task = bool(
            (open_task or {}).get("active")
            and not task_transition.get("requested")
            and (
                task_answer.get("is_answer")
                or task_answer.get("is_task_action")
            )
        )

        strong_boundary = bool(
            boundary.get("explicit")
            or (
                (
                    boundary.get("semantic")
                    or boundary.get("request_boundary")
                )
                and not protected_by_task
            )
        )

        return {
            **boundary,
            "task_answer": task_answer,
            "task_transition": task_transition,
            "protected_by_open_task": protected_by_task,
            "new_topic": strong_boundary,
            "source": "semantic_scene_boundary_v2",
            "evidence_only": True,
        }

    @classmethod
    def _new_task_frame(
        cls,
        *,
        existing: dict[str, Any],
        transition: dict[str, Any],
        state: dict[str, Any],
        scene: dict[str, Any],
        text: str,
        sequence_id: str,
    ) -> dict[str, Any]:
        previous_target = cls._text(
            existing.get("target")
            or (
                state.get("active_dialogue_sequence", {}).get("active_entity")
                if isinstance(state.get("active_dialogue_sequence"), dict)
                else ""
            )
            or existing.get("candidate_answer")
        )
        revision = int(existing.get("task_revision", 0) or 0) + 1

        low = cls._text(text).lower()
        interactive = cls._is_interactive_start(text)
        riddle_request = bool(
            interactive.get("active")
            and interactive.get("kind") in {"riddle", "game"}
        )

        kind = (
            cls._text(interactive.get("kind"))
            or cls._text(existing.get("kind"))
            or "task"
        )

        prompt = ""
        status = (
            cls._text(interactive.get("status"))
            or ("pending_generation" if riddle_request else "open")
        )
        expected = (
            cls._text(interactive.get("expected_input_type"))
            or ("assistant_generation" if riddle_request else "answer")
        )

        avoid_entities = []
        if previous_target:
            avoid_entities.append(previous_target)

        # A reset request may explicitly demand memory removal.  The semantic
        # bridge records the old target as forbidden evidence for the next task.
        forbidden = list(
            dict.fromkeys(
                [
                    *(
                        state.get("interpretation_runtime", {})
                        .get("forbidden_entities", [])
                        if isinstance(state.get("interpretation_runtime"), dict)
                        else []
                    ),
                    *avoid_entities,
                ]
            )
        )

        topic = "загадка" if kind == "riddle" else "задача"
        goal = "generate_riddle" if status == "pending_generation" else "continue_task"

        return {
            "active": True,
            "status": status,
            "kind": kind,
            "role": cls._text(interactive.get("role"))
            or ("april_holds_secret" if kind == "game" else "april_asks_riddle" if kind == "riddle" else ""),
            "phase": cls._text(interactive.get("phase"))
            or ("generate_secret" if kind == "game" and status == "pending_generation" else "generate_riddle" if kind == "riddle" and status == "pending_generation" else "awaiting_user_answer"),
            "prompt": prompt,
            "last_question": "",
            "expected_input_type": expected,
            "target": "",
            "secret_target": "",
            "candidate_answer": "",
            "last_user_answer": "",
            "known_clues": list(interactive.get("known_clues") or []),
            "qa_history": [],
            "turns": [],
            "awaiting_user": expected in {"answer", "user_answer"},
            "completed": False,
            "topic": topic,
            "goal": goal,
            "sequence_id": sequence_id,
            "scene_id": cls._text(scene.get("scene_id")),
            "task_revision": revision,
            "source": "task_transition_engine",
            "replacement_requested": True,
            "avoid_entities": forbidden,
            "reset_memory": bool(transition.get("reset_memory")),
        }

    @classmethod
    def resolve(
        cls,
        *,
        text: str,
        state: dict[str, Any],
        history: list[dict[str, Any]],
        profile: dict[str, Any],
        dialogue: dict[str, Any],
        active_topic: str = "",
        active_goal: str = "",
        scene_type: str = "text",
    ) -> dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []

        current = cls._scene_from_state(state)
        current_scene_id = cls._text(current.get("scene_id"))
        sequence = (
            state.get("active_dialogue_sequence")
            if isinstance(state.get("active_dialogue_sequence"), dict)
            else {}
        )
        sequence_id = cls._text(sequence.get("sequence_id"))

        current_topic = cls._text(
            current.get("topic")
            or current.get("active_topic")
            or active_topic
        )
        current_goal = cls._text(
            current.get("goal")
            or current.get("active_goal")
            or active_goal
        )

        normalized_history = cls._history_turns(history)
        last_user = cls._latest_user(normalized_history, current)
        last_april = cls._latest_assistant(normalized_history, current)

        open_task = cls._find_open_task(
            state,
            normalized_history,
            current,
            last_april,
        )

        evidence = cls._topic_change_evidence(
            text,
            current,
            profile,
            dialogue,
            current_topic,
            open_task=open_task,
        )

        task_transition = evidence.get("task_transition", {})
        task_answer = evidence.get("task_answer", {})
        interactive_start = cls._is_interactive_start(text)
        if (
            interactive_start.get("active")
            and open_task.get("active")
            and (task_answer.get("is_answer") or task_answer.get("is_task_action"))
            and not task_transition.get("replace_task")
        ):
            # Phrases such as "я загадал" may appear while the user is talking
            # about the already-active game.  Current task ownership and the
            # resolved discourse move outrank surface self-reference.
            interactive_start = {"active": False, "reason": "existing_task_owns_turn"}

        # Task transition creates a new task frame.  The conversational scene may
        # stay continuous, but task ownership is replaced atomically.
        if task_transition.get("replace_task"):
            open_task = cls._new_task_frame(
                existing=open_task,
                transition=task_transition,
                state=state,
                scene=current,
                text=text,
                sequence_id=sequence_id,
            )

        # A self-contained interactive start is a real new task even when the
        # semantic topic scorer is weak.  The task frame is attached immediately,
        # before provider execution, so the provider can see what kind of state it
        # is operating on.
        elif interactive_start.get("active"):
            # An explicit interactive start creates a fresh task frame even when
            # another task is currently open. The conversation may remain in the
            # same scene, but task ownership changes atomically.
            open_task = cls._new_task_frame(
                existing=open_task,
                transition={"replace_task": True, "reset_memory": False},
                state=state,
                scene=current,
                text=text,
                sequence_id=sequence_id,
            )

        elif open_task.get("active") and task_answer.get("is_answer"):
            open_task = dict(open_task)
            qa_history = list(open_task.get("qa_history") or [])
            prompt = cls._text(
                open_task.get("last_question")
                or open_task.get("prompt")
            )
            qa_history.append({
                "user": cls._text(text),
                "assistant_prompt": prompt,
                "kind": "answer",
            })
            open_task["qa_history"] = qa_history[-12:]
            open_task["turns"] = list(open_task["qa_history"])
            open_task["status"] = "answer_received"
            open_task["phase"] = (
                "awaiting_assistant_action"
                if open_task.get("role") == "april_guesses_user_object"
                else open_task.get("phase") or "answer_received"
            )
            open_task["candidate_answer"] = cls._text(text)
            open_task["last_user_answer"] = cls._text(text)
            open_task["awaiting_user"] = False
            open_task["last_answer_confidence"] = float(
                task_answer.get("confidence", 0.0) or 0.0
            )
            open_task["source"] = "task_owner_answer"
            open_task["task_revision"] = int(open_task.get("task_revision", 0) or 0) + 1

        elif open_task.get("active") and task_answer.get("is_task_action"):
            open_task = dict(open_task)
            qa_history = list(open_task.get("qa_history") or [])
            qa_history.append({
                "user": cls._text(text),
                "assistant_prompt": cls._text(open_task.get("last_question") or open_task.get("prompt")),
                "kind": "task_action",
            })
            open_task["qa_history"] = qa_history[-12:]
            open_task["turns"] = list(open_task["qa_history"])
            open_task["last_user_action"] = cls._text(text)
            open_task["status"] = "open"
            open_task["phase"] = "awaiting_assistant_action"
            open_task["awaiting_user"] = False
            open_task["source"] = "task_owner_action"

        has_live_scene = bool(
            current_scene_id
            or current_topic
            or last_april
            or open_task.get("active")
        )

        # Memory recall is a retrieval mode, not a scene owner.
        memory_query = cls._text(dialogue.get("label")).lower() == "memory_query"

        # Explicit external boundary is the only direct escape from an active
        # open task.  Weak semantic novelty cannot steal ownership.
        topic_boundary = bool(evidence.get("new_topic"))
        if task_transition.get("replace_task") or interactive_start.get("active"):
            # Replacing/starting an interactive task changes task ownership, not
            # the user's conversational branch. The scene remains continuous.
            topic_boundary = False
        elif open_task.get("active"):
            topic_boundary = bool(
                (
                    evidence.get("explicit")
                    or evidence.get("request_boundary")
                    or evidence.get("semantic")
                )
                and not task_answer.get("is_answer")
                and not task_answer.get("is_task_action")
            )

        if topic_boundary:
            relation = "NEW_SCENE"
            next_scene_id = f"scene-{int(time.time() * 1000)}"
            continuity = False
        elif has_live_scene:
            relation = "MEMORY_RECALL" if memory_query and not open_task.get("active") else "CONTINUE_SCENE"
            next_scene_id = current_scene_id or f"scene-{int(time.time() * 1000)}"
            continuity = True
        else:
            relation = "OPEN_SCENE"
            next_scene_id = current_scene_id or f"scene-{int(time.time() * 1000)}"
            continuity = bool(current_scene_id)

        # The scene topic is task-owned, not entity-owned.  This prevents
        # "Ключ" from becoming the permanent canonical scene merely because it
        # was an old answer.
        if topic_boundary and not task_transition.get("replace_task"):
            # A genuine external subject change closes the old open task.
            open_task = {}
            resolved_topic = cls._text(text)
            resolved_goal = cls._text(text)
        elif open_task.get("active"):
            resolved_topic = cls._text(
                open_task.get("topic")
                or ("загадка" if open_task.get("kind") == "riddle" else "")
            )
            resolved_goal = cls._text(
                open_task.get("goal")
                or ("solve_riddle" if open_task.get("kind") == "riddle" else current_goal)
            )
        elif continuity:
            resolved_topic = current_topic
            resolved_goal = current_goal
        else:
            resolved_topic = cls._text(text)
            resolved_goal = cls._text(text)

        memory = cls._memory_projection(
            state,
            resolved_topic,
            next_scene_id,
        )

        task_entity = ""
        if open_task.get("active"):
            # The target is deliberately empty until it is established by the
            # active task itself.  Candidate user answers live separately.
            task_entity = cls._text(open_task.get("target"))

        forbidden_entities = list(
            dict.fromkeys(
                cls._text(x)
                for x in (
                    open_task.get("avoid_entities", [])
                    if isinstance(open_task.get("avoid_entities"), list)
                    else []
                )
                if cls._text(x)
            )
        )

        scene_turn_index = int(current.get("turn_index", 0) or 0) + 1

        scene = {
            "version": cls.VERSION,
            "scene_id": next_scene_id,
            "status": "active",
            "relation": relation,
            "continuity": continuity,
            "topic": resolved_topic,
            "goal": resolved_goal,
            "scene_type": scene_type,
            "focus": cls._text(text),
            "last_user_turn": cls._text(text),
            "last_april_turn": last_april,
            "previous_user_turn": last_user,
            "focus_history": list(current.get("focus_history") or [])[-7:] + [cls._text(text)],
            "turn_index": scene_turn_index,
            "sequence_id": sequence_id,
            "memory_projection": memory,
            "memory_role": "supporting_evidence",
            "resume_after_memory": bool(memory_query and continuity),
            "boundary": evidence,
            "open_task": open_task,
            "task_state": open_task,
            "interactive_task_state": open_task,
            "task_memory": {
                "role": open_task.get("role"),
                "phase": open_task.get("phase"),
                "last_question": open_task.get("last_question"),
                "known_clues": list(open_task.get("known_clues") or [])[-12:],
                "qa_history": list(open_task.get("qa_history") or [])[-12:],
                "candidate_answer": cls._text(open_task.get("candidate_answer")),
                "awaiting_user": bool(open_task.get("awaiting_user")),
            } if open_task.get("active") else {},
            "active_entity": task_entity,
            "candidate_answer": cls._text(open_task.get("candidate_answer")),
            "forbidden_entities": forbidden_entities,
            "single_active_scene": True,
            "trigger_free": True,
            "decision_owner": DECISION_OWNER,
        }

        # Same-turn bridge.  Persistence remains state-manager-owned.
        state["scene_state"] = scene
        state["active_scene"] = scene
        state["current_visual_scene"] = scene
        state["active_topic"] = resolved_topic
        state["current_topic"] = resolved_topic
        state["active_goal"] = resolved_goal
        state["open_task"] = dict(open_task)
        state["active_task"] = dict(open_task)
        state["interactive_task_state"] = dict(open_task)

        if open_task.get("active"):
            runtime = (
                state.get("interpretation_runtime")
                if isinstance(state.get("interpretation_runtime"), dict)
                else {}
            )
            runtime["active_task"] = dict(open_task)
            runtime["interactive_task_state"] = dict(open_task)
            runtime["forbidden_entities"] = forbidden_entities
            runtime["task_owner"] = "CURRENT_OPEN_TASK"
            runtime["historical_entities_are_evidence_only"] = True
            state["interpretation_runtime"] = runtime

            # Do not let the stale sequence topic keep owning the dialogue.
            if isinstance(sequence, dict):
                sequence["topic"] = resolved_topic
                sequence["active_topic"] = resolved_topic
                sequence["active_goal"] = resolved_goal
                sequence["open_task"] = dict(open_task)
                sequence["task_state"] = dict(open_task)
                sequence["active_entity"] = task_entity
                sequence["candidate_answer"] = cls._text(open_task.get("candidate_answer"))
                sequence["forbidden_entities"] = forbidden_entities
                if open_task.get("status") == "pending_generation":
                    sequence["task_revision"] = open_task.get("task_revision", 0)
        elif topic_boundary:
            # Close the old task/anchor when the user explicitly moves to a new
            # subject.  Leaving the old sequence entity here would allow the
            # next turn to resurrect the previous topic.
            if isinstance(sequence, dict):
                sequence["topic"] = resolved_topic
                sequence["active_topic"] = resolved_topic
                sequence["active_goal"] = resolved_goal
                sequence["open_task"] = {}
                sequence["task_state"] = {}
                sequence["active_entity"] = ""
                sequence["candidate_answer"] = ""
                sequence["forbidden_entities"] = []
            runtime = (
                state.get("interpretation_runtime")
                if isinstance(state.get("interpretation_runtime"), dict)
                else {}
            )
            runtime["active_task"] = {}
            runtime["forbidden_entities"] = []
            runtime["task_owner"] = "CURRENT_SCENE"
            runtime["historical_entities_are_evidence_only"] = True
            state["interpretation_runtime"] = runtime

        return {
            "scene": scene,
            "relation": relation,
            "continuation": bool(continuity),
            "new_scene": relation in {"OPEN_SCENE", "NEW_SCENE"},
            "topic_boundary": bool(topic_boundary),
            "memory_query": bool(memory_query),
            "memory_projection": memory,
            "memory_role": "supporting_evidence",
            "resume_after_memory": bool(memory_query and continuity),
            "open_task": open_task,
            "task_state": open_task,
            "interactive_task_state": open_task,
            "task_memory": {
                "role": open_task.get("role"),
                "phase": open_task.get("phase"),
                "last_question": open_task.get("last_question"),
                "known_clues": list(open_task.get("known_clues") or [])[-12:],
                "qa_history": list(open_task.get("qa_history") or [])[-12:],
                "candidate_answer": cls._text(open_task.get("candidate_answer")),
                "awaiting_user": bool(open_task.get("awaiting_user")),
            } if open_task.get("active") else {},
            "task_answer": task_answer,
            "task_transition": task_transition,
            "task_action": bool(task_answer.get("is_task_action")),
            "active_entity": task_entity,
            "candidate_answer": cls._text(open_task.get("candidate_answer")),
            "forbidden_entities": forbidden_entities,
            "scene_type": scene_type,
            "evidence": evidence,
            "decision_owner": DECISION_OWNER,
            "engine": cls.VERSION,
            "evidence_only": True,
        }


LIVE_SCENE_CONTINUITY_ENGINE = LiveSceneContinuityEngine()



class DialogueEnvironmentEngine:
    """Canonical preflight environment for one authenticated USER->APRIL turn.

    This engine does not route providers or renderers.  It resolves the semantic
    working environment *before* LiveSceneContinuityEngine/Processor decisions:

      1. authenticate the current conversation scope;
      2. recover the latest real USER<->APRIL antecedent in that same scope;
      3. classify the discourse move (new topic / continuation / recall / task);
      4. recover or create the live task frame when the turn is an interactive task;
      5. explicitly fence historical topics/entities from the current turn;
      6. build a compact continuation-content plan for Provider.

    The authenticated conversation is the long-lived container.  Topic branches
    inside it are independent semantic work items.  Historical 7-day memory is
    retrieval evidence only and never becomes the active owner by itself.
    """

    VERSION = "dialogue_environment_v3_semantic_sync"
    SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

    _CONFIRMATION = (
        "правильно", "верно", "точно", "ага", "именно", "да", "да,", "всё верно", "все верно",
        "совершенно верно", "угадал", "угадала", "угадано",
    )
    _REJECTION = (
        "неправильно", "не верно", "неверно", "нет", "не то", "неправильный ответ", "не угадал", "не угадала",
    )
    _MEMORY_RECALL = (
        "вспомни", "напомни", "что мы обсуждали", "о чем мы говорили", "о чём мы говорили",
        "что я спрашивал", "что я спрашивала", "мой прошлый вопрос", "помнишь", "из памяти",
        "вернись к теме", "вернемся к теме", "вернёмся к теме", "к той теме", "к прошлой теме",
    )
    _VISUAL_REFERENCE = (
        "как ты себя описала", "как ты описывала себя", "как ты себя видишь", "как ты себя представляешь",
        "как ты себя представляла", "как ты меня описывала", "по тому описанию", "по твоему описанию",
        "из нашего диалога", "из предыдущего диалога", "как мы описывали", "покажи ту картинку",
        "покажи эту картинку", "нарисуй как ты", "нарисуй то, как ты", "так как ты описала",
        "так, как ты описала", "так как ты себя описала",
    )
    _NEW_TOPIC = (
        "новая тема", "другая тема", "сменим тему", "перейдем к", "перейдём к",
        "давай про другое", "давай теперь про", "а теперь про", "отдельно поговорим",
    )
    _RIDDLE_SOLVE = (
        "отгадай загадку", "отгадай", "разгадай загадку", "разгадай", "реши загадку", "решить загадку",
    )
    _RIDDLE_CREATE = (
        "загадай мне", "загадай загадку", "придумай мне загадку", "придумай загадку",
        "задай мне загадку", "загадку мне",
    )
    _COMMAND_HEADS = (
        "расскажи", "объясни", "покажи", "нарисуй", "создай", "сделай", "напиши", "построй",
        "проверь", "опиши", "сравни", "найди", "выведи", "подскажи", "скажи", "дай",
        "предложи", "продолжи", "разработай", "дополни", "исправь", "выбери",
        "сформулируй", "составь", "перепиши", "переделай",
    )

    @staticmethod
    def _text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    @classmethod
    def _low(cls, value: Any) -> str:
        return cls._text(value).lower()

    @classmethod
    def _tokens(cls, value: Any) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", cls._low(value))

    @classmethod
    def _similarity(cls, a: Any, b: Any) -> float:
        left, right = set(cls._tokens(a)), set(cls._tokens(b))
        if not left or not right:
            return 0.0
        return len(left & right) / max(1.0, min(len(left), len(right)))

    @classmethod
    def _timestamp(cls, value: Any) -> float | None:
        if value in (None, "", 0, 0.0):
            return None
        if isinstance(value, (int, float)):
            return float(value) if float(value) > 0 else None
        text = cls._text(value)
        if not text:
            return None
        try:
            numeric = float(text)
            if numeric > 0:
                return numeric
        except Exception:
            pass
        try:
            raw = text.replace("Z", "+00:00")
            from datetime import datetime
            dt = datetime.fromisoformat(raw)
            return dt.timestamp()
        except Exception:
            return None

    @classmethod
    def _scope(cls, state: dict[str, Any]) -> dict[str, str]:
        sequence = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        return {
            "user_id": cls._text(state.get("user_id") or sequence.get("user_id")),
            "conversation_id": cls._text(state.get("conversation_id") or sequence.get("conversation_id")),
            "dialogue_sequence_id": cls._text(sequence.get("sequence_id") or state.get("dialogue_sequence_id")),
        }

    @classmethod
    def _scope_match(cls, item: Any, scope: dict[str, str], *, require_sequence: bool = False) -> bool:
        if not isinstance(item, dict):
            return False
        user_id = cls._text(item.get("user_id"))
        conversation_id = cls._text(item.get("conversation_id"))
        sequence_id = cls._text(item.get("sequence_id") or item.get("dialogue_sequence_id"))
        if scope.get("user_id") and user_id and user_id != scope["user_id"]:
            return False
        if scope.get("conversation_id") and conversation_id and conversation_id != scope["conversation_id"]:
            return False
        if require_sequence and scope.get("dialogue_sequence_id") and sequence_id and sequence_id != scope["dialogue_sequence_id"]:
            return False
        return True

    @classmethod
    def _pair_from_item(cls, item: Any, scope: dict[str, str]) -> dict[str, Any]:
        if not isinstance(item, dict) or not cls._scope_match(item, scope):
            return {}
        user = item.get("user")
        april = item.get("april") or item.get("assistant")
        if isinstance(user, dict):
            user = user.get("text") or user.get("content") or user.get("answer") or user.get("user_request")
        if isinstance(april, dict):
            april = april.get("answer") or april.get("content") or april.get("summary") or april.get("april_answer")
        user = cls._text(user or item.get("user_request") or item.get("last_user_request"))
        april = cls._text(april or item.get("april_answer") or item.get("last_april_answer"))
        if not user and not april:
            return {}
        visual_attachment = item.get("visual_attachment")
        if not isinstance(visual_attachment, dict):
            current_turn = item.get("current_turn") if isinstance(item.get("current_turn"), dict) else {}
            visual_attachment = current_turn.get("visual_attachment") if isinstance(current_turn.get("visual_attachment"), dict) else {}
        if not visual_attachment and isinstance(item.get("last_visual_attachment"), dict):
            visual_attachment = item.get("last_visual_attachment")
        return {
            "user": user,
            "april": april,
            "sequence_id": cls._text(item.get("sequence_id") or item.get("dialogue_sequence_id") or scope.get("dialogue_sequence_id")),
            "scene_id": cls._text(item.get("scene_id") or item.get("visual_scene_id") or item.get("last_visual_scene_id")),
            "conversation_id": cls._text(item.get("conversation_id") or scope.get("conversation_id")),
            "user_id": cls._text(item.get("user_id") or scope.get("user_id")),
            "timestamp": cls._timestamp(item.get("created_at") or item.get("timestamp") or item.get("updated_at")),
            "visual_attachment": deepcopy(visual_attachment) if isinstance(visual_attachment, dict) else {},
            "raw": item,
        }

    @classmethod
    def _candidate_pairs(cls, state: dict[str, Any], history: list[Any], scope: dict[str, str]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()

        def push(pair: dict[str, Any]) -> None:
            if not pair:
                return
            sig = (pair.get("user") or "") + "\n" + (pair.get("april") or "")
            sig = sig.strip().lower()
            if not sig:
                return
            if sig in seen:
                # Preserve the same semantic turn without discarding richer/newer
                # metadata from chronological history.
                for index, existing in enumerate(candidates):
                    existing_sig = ((existing.get("user") or "") + "\n" + (existing.get("april") or "")).strip().lower()
                    if existing_sig != sig:
                        continue
                    existing_ts = existing.get("timestamp")
                    incoming_ts = pair.get("timestamp")
                    existing_raw = existing.get("raw") if isinstance(existing.get("raw"), dict) else {}
                    incoming_raw = pair.get("raw") if isinstance(pair.get("raw"), dict) else {}
                    existing_anchor = existing_raw.get("semantic_anchor") if isinstance(existing_raw.get("semantic_anchor"), dict) else {}
                    incoming_anchor = incoming_raw.get("semantic_anchor") if isinstance(incoming_raw.get("semantic_anchor"), dict) else {}
                    if (
                        (incoming_ts is not None and (existing_ts is None or float(incoming_ts) > float(existing_ts)))
                        or (incoming_anchor and not existing_anchor)
                    ):
                        candidates[index] = pair
                    return
            seen.add(sig)
            candidates.append(pair)

        # The active authenticated sequence is the hot semantic carrier. Prefer it
        # before any stale visual scene because visual state can lag one or more
        # dialogue turns during artifact rendering.
        sequence = state.get("active_dialogue_sequence")
        if isinstance(sequence, dict):
            pair = cls._pair_from_item(sequence, scope)
            if pair:
                push(pair)

        # Chronological USER↔APRIL history is the next authority. This recovers the
        # real latest semantic turn even when scene_state/current_visual_scene was
        # not refreshed after the last response.
        if isinstance(history, list):
            for item in reversed(history):
                pair = cls._pair_from_item(item, scope)
                if pair:
                    push(pair)
                if len(candidates) >= 12:
                    break

        # Current visual scene is useful as an artifact carrier, but it must not
        # replace a newer semantic dialogue pair.
        for key in ("current_visual_scene", "active_visual_scene", "scene_state", "active_scene"):
            scene = state.get(key)
            if isinstance(scene, dict):
                pair = cls._pair_from_item(scene, scope)
                if pair:
                    push(pair)

        direct = cls._pair_from_item({
            "user": state.get("last_user_turn"),
            "april": state.get("last_april_turn"),
            "user_id": scope.get("user_id"),
            "conversation_id": scope.get("conversation_id"),
            "sequence_id": scope.get("dialogue_sequence_id"),
        }, scope)
        push(direct)
        return candidates

    @classmethod
    def _latest_pair(cls, state: dict[str, Any], history: list[Any], scope: dict[str, str]) -> dict[str, Any]:
        candidates = cls._candidate_pairs(state, history, scope)
        if not candidates:
            return {}

        # A transport/parser failure is not a semantic turn. Never let such a
        # placeholder become the active dialogue anchor when a real USER↔APRIL
        # pair is available behind it. This prevents a failed response from
        # poisoning short follow-ups such as "Почему?" or "А дальше?".
        def is_transport_failure(pair: dict[str, Any]) -> bool:
            answer = cls._low(pair.get("april"))
            return answer.startswith((
                "не удалось сформировать ответ на запрос",
                "не удалось сформировать ответ.",
                "не удалось сформировать ответ",
                "произошла ошибка при формировании ответа",
            ))

        semantic_candidates = [x for x in candidates if not is_transport_failure(x)]
        if semantic_candidates:
            candidates = semantic_candidates

        # Prefer explicit timestamps when available, otherwise preserve source order.
        dated = [x for x in candidates if x.get("timestamp") is not None]
        if dated:
            return max(dated, key=lambda x: float(x.get("timestamp") or 0.0))
        return candidates[0]

    @classmethod
    def _explicit_new_topic(cls, text: str) -> bool:
        low = cls._low(text)
        if any(x in low for x in cls._NEW_TOPIC):
            return True
        # Natural switch form: "а теперь расскажи про Гоголя".
        return bool(re.search(
            r"^(?:а\s+)?теперь\s+(?:давай\s+)?"
            r"(?:расскажи|объясни|обьясни|опиши|покажи|сделай|создай|нарисуй|"
            r"напиши|проверь|сравни|найди|скажи|дай|построй)\b"
            r"(?:\s+про\s+|\s+об\s+|\s+о\s+|\s+насч(?:ё|ё)т\s+)[^?!。！？]{2,}$",
            low,
            re.IGNORECASE,
        ))

    @classmethod
    def _subject_from_current(cls, text: str) -> str:
        """Extract the semantic object/subject, never the imperative command."""
        current = cls._text(text)
        if not current:
            return ""
        tokens = cls._tokens(current)
        if not tokens:
            return ""

        # Strip discourse wrappers before resolving a command object:
        # "а теперь покажи героя" -> "покажи героя".
        command_text = re.sub(
            r"^\s*(?:а\s+)?(?:теперь\s+|сейчас\s+)?",
            "",
            current,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        command_tokens = cls._tokens(command_text)

        # Explicit object introduction: "про Пушкина", "о Tesla", etc.
        match = re.search(
            r"\b(?:про|обо?|насч(?:ё|ё)т)\s+(.+?)(?:[?!.。！？]|$)",
            current,
            re.IGNORECASE,
        )
        if match:
            value = cls._text(match.group(1)).strip(" ,:;—-\t")
            if value and not cls._reference_led_subject(value):
                return value[:180]

        # Direct-object command: "нарисуй свинку", "покажи Tesla".
        if command_tokens and command_tokens[0] in cls._COMMAND_HEADS and len(command_tokens) >= 2:
            second = command_tokens[1]
            interrogative = {
                "как", "что", "почему", "зачем", "когда", "где", "кто",
                "какой", "какая", "какое", "какие", "сколько", "чем",
            }
            filler = {
                "подробнее", "подробно", "историю", "всё", "все", "мне",
                "пожалуйста", "еще", "ещё", "далее", "сейчас", "теперь",
            }
            if second not in interrogative and second not in filler:
                raw_head = re.split(r"\s+", command_text, maxsplit=1)[0]
                rest = cls._text(re.sub(
                    r"^\s*" + re.escape(raw_head) + r"\s+", "", command_text, count=1, flags=re.IGNORECASE
                ))
                if rest:
                    return rest[:180]
        return ""

    @classmethod
    def _reference_led_subject(cls, value: Any) -> bool:
        tokens = cls._tokens(value)
        return bool(tokens and tokens[0] in {
            "он", "она", "оно", "они", "его", "ее", "её", "ему", "ей",
            "этот", "эта", "это", "эту", "этой", "этим", "тот", "та", "те",
        })

    @classmethod
    def _stable_subject_from_pair(cls, previous_user: str, previous_april: str) -> str:
        subject = cls._subject_from_current(previous_user)
        if subject and not cls._reference_led_subject(subject):
            return subject
        answer = cls._text(previous_april)
        if answer:
            # Concrete answer patterns must outrank polite discourse words.
            # This fixes "Правильно! Это ёлка." -> entity="ёлка".
            answer_patterns = (
                r"(?:^|[.!?]\s*)это\s+([^.!?]+)",
                r"(?:правильн(?:ый|о)|верно)\s*!?\s*это\s+([^.!?]+)",
                r"(?:ответ|правильный ответ)\s*[:—-]\s*([^.!?]+)",
            )
            for pattern in answer_patterns:
                match = re.search(pattern, answer, flags=re.IGNORECASE)
                if match:
                    value = cls._text(match.group(1)).strip(" ,:;—-\t")
                    if value and not cls._reference_led_subject(value):
                        return value[:180]
            matches = re.findall(
                r"\b[А-ЯЁA-Z][\wЁёЇїІіЄєҐґ-]+(?:\s+[А-ЯЁA-Z][\wЁёЇїІіЄєҐґ-]+){0,3}\b",
                answer,
            )
            stop = {
                "Среди", "Он", "Она", "Оно", "Они", "Это", "Также", "Но", "В",
                "На", "По", "Из", "После", "Причиной", "Причина", "Русский",
                "Русская", "Русское", "Русские", "Этот", "Эта", "Эти",
                "Понял", "Поняла", "Хорошо", "Отлично", "Конечно", "Давайте",
                "Продолжаем", "Продолжим", "Развиваем", "Развиваемся", "Готово",
                "Готов", "Готова", "Ответ", "Ответь", "Смотри",
            }
            for candidate in matches:
                if candidate.split()[0] in stop:
                    continue
                return cls._text(candidate)[:180]
        return ""

    @classmethod
    def _identity_query(cls, text: str) -> bool:
        """Recognize authenticated user-name recall requests as memory queries."""
        low = cls._low(text).strip(" .,!?:;-—")
        return bool(re.search(
            r"(?:^|\b)(?:а\s+|и\s+|так\s+)?как\s+меня\s+(?:зовут|звать)(?:\b|$)|(?:как|так)\s+(?:мое|моё)\s+имя|(?:мое|моё)\s+имя",
            low,
            re.IGNORECASE,
        ))

    @classmethod
    def _memory_query(cls, text: str) -> bool:
        low = cls._low(text)
        history_query = bool(
            re.search(r"\b(?:последн\w*|недавн\w*)\b", low)
            and re.search(r"\b(?:диалог\w*|разговор\w*|обсуждени\w*)\b", low)
        )
        history_list_request = bool(
            re.search(r"(?:что|какие|какое|какую).*(?:мы|ты|я).*(?:обсуждал|говорил|спрашивал|делал)", low)
            and any(x in low for x in ("перечисли", "пронумеруй", "последн", "недавн", "диалог", "разговор"))
        )
        return bool(
            cls._identity_query(text)
            or any(x in low for x in cls._MEMORY_RECALL)
            or history_query
            or history_list_request
        )

    @classmethod
    def _visual_reference_query(cls, text: str) -> bool:
        low = cls._low(text)
        return any(marker in low for marker in cls._VISUAL_REFERENCE)

    @classmethod
    def _identity_unknown_answer(cls, text: str) -> bool:
        low = cls._low(text)
        return bool(
            ("имя" in low or "зовут" in low)
            and any(marker in low for marker in (
                "не говорил", "не говорили", "не указал", "не указали",
                "не сообщ", "не называл", "не называли", "не знаю",
            ))
        )

    @classmethod
    def _extract_identity_name(cls, text: str) -> str:
        """Extract an explicit personal-name disclosure only."""
        value = cls._text(text).strip(" .,!?:;-—")
        if not value:
            return ""

        match = re.search(
            r"\bменя\s+зовут\s+([A-Za-zА-Яа-яЁёЇїІіЄєҐґ][A-Za-zА-Яа-яЁёЇїІіЄєҐґ-]*(?:\s+[A-Za-zА-Яа-яЁёЇїІіЄєҐґ][A-Za-zА-Яа-яЁёЇїІіЄєҐґ-]*){0,2})\b",
            value,
            re.IGNORECASE,
        )
        if match:
            return cls._text(match.group(1))[:120]

        tokens = re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ][A-Za-zА-Яа-яЁёЇїІіЄєҐґ-]*", value)
        if len(tokens) not in {1, 2, 3}:
            return ""
        if any(cls._low(token) in {
            "да", "нет", "не", "здравствуйте", "привет", "почему", "как",
            "кто", "где", "зачем", "сколько", "дальше", "так", "хорошо",
        } for token in tokens):
            return ""
        if len(tokens) == 1 and len(tokens[0]) > 40:
            return ""
        return cls._text(" ".join(tokens))[:120]

    @classmethod
    def _identity_disclosure(cls, current_text: str, previous_user: str, previous_april: str) -> dict[str, Any]:
        """Detect the specific continuation: identity question/unknown answer -> user name."""
        if not (cls._identity_query(previous_user) or cls._identity_unknown_answer(previous_april)):
            return {}
        name = cls._extract_identity_name(current_text)
        if not name:
            return {}
        return {
            "name": name,
            "source": "explicit_user_disclosure_after_identity_query",
            "previous_user_turn": previous_user,
            "previous_april_turn": previous_april,
        }

    @classmethod
    def _riddle_solve_request(cls, text: str) -> bool:
        low = cls._low(text)
        return any(x in low for x in cls._RIDDLE_SOLVE) and "загад" in low

    @classmethod
    def _riddle_create_request(cls, text: str) -> bool:
        low = cls._low(text)
        return any(x in low for x in cls._RIDDLE_CREATE) or (
            "загад" in low and any(x in low for x in ("загадай", "придумай", "задай"))
        )

    @classmethod
    def _confirmation(cls, text: str) -> bool:
        low = cls._low(text).strip(" .,!?:;-")
        if not low:
            return False
        return low in cls._CONFIRMATION or any(low.startswith(x + " ") for x in cls._CONFIRMATION if x.strip())

    @classmethod
    def _rejection(cls, text: str) -> bool:
        low = cls._low(text).strip(" .,!?:;-")
        return low in cls._REJECTION or any(low.startswith(x + " ") for x in cls._REJECTION if x.strip())

    @classmethod
    def _riddle_answer_relation(cls, previous_user: str, previous_april: str) -> bool:
        pu = cls._low(previous_user)
        pa = cls._low(previous_april)
        return bool(
            cls._riddle_solve_request(previous_user)
            or ("загадк" in pu and "?" in pu)
            or ("что это" in pa or "что это" in pu)
        )

    @classmethod
    def _riddle_generation_relation(cls, previous_user: str, previous_april: str) -> bool:
        pu = cls._low(previous_user)
        pa = cls._low(previous_april)
        return bool(
            cls._riddle_create_request(previous_user)
            or ("загад" in pa and ("?" in pa or "что это" in pa))
        )

    @classmethod
    def _generic_task_from_pair(cls, previous_user: str, previous_april: str, scope: dict[str, str]) -> dict[str, Any]:
        if not previous_user and not previous_april:
            return {}

        # A generated riddle belongs to April's riddle task.  Check this branch
        # first because the generated question itself can contain "что это?",
        # which must not be mistaken for a user-owned riddle.
        if cls._riddle_generation_relation(previous_user, previous_april):
            return {
                "active": True,
                "status": "open",
                "kind": "riddle",
                "role": "april_asks_riddle",
                "phase": "awaiting_user_answer",
                "expected_input_type": "answer",
                "prompt": previous_april,
                "last_question": previous_april,
                "target": "",
                "candidate_answer": "",
                "last_user_answer": "",
                "known_clues": [],
                "qa_history": [{"user": previous_user, "assistant_prompt": previous_april, "kind": "riddle_prompt"}],
                "turns": [{"user": previous_user, "assistant_prompt": previous_april, "kind": "riddle_prompt"}],
                "awaiting_user": True,
                "completed": False,
                "topic": "загадка",
                "goal": "solve_riddle",
                "sequence_id": scope.get("dialogue_sequence_id", ""),
                "scene_id": "",
                "task_revision": 1,
                "source": "dialogue_environment_riddle_recovery",
            }

        if cls._riddle_answer_relation(previous_user, previous_april):
            return {
                "active": True,
                "status": "answer_received",
                "kind": "riddle",
                "role": "april_solves_user_riddle",
                "phase": "awaiting_user_followup",
                "expected_input_type": "followup",
                "prompt": previous_user,
                "last_question": previous_user,
                "target": "загадка",
                "candidate_answer": previous_april,
                "last_user_answer": "",
                "known_clues": [previous_user],
                "qa_history": [{"user": previous_user, "assistant_prompt": previous_user, "kind": "riddle_prompt", "assistant_answer": previous_april}],
                "turns": [{"user": previous_user, "assistant_prompt": previous_user, "kind": "riddle_prompt", "assistant_answer": previous_april}],
                "awaiting_user": True,
                "completed": False,
                "topic": "загадка",
                "goal": "solve_riddle",
                "sequence_id": scope.get("dialogue_sequence_id", ""),
                "scene_id": "",
                "task_revision": 1,
                "source": "dialogue_environment_riddle_recovery",
            }

        # A generic conversational prompt ("Чем займёмся?", "Как могу помочь?")
        # is not an answer-owning task. It should leave the semantic topic open so
        # the user's next substantive statement can create the first branch.
        generic_prompt = cls._low(previous_april).strip(" .,!?:;-—")
        if generic_prompt and any(
            phrase in generic_prompt
            for phrase in (
                "чем займёмся", "чем займемся", "что будем делать",
                "как могу помочь", "чем могу помочь", "что хотите обсудить",
                "что будем обсуждать", "что выберем",
            )
        ):
            return {}

        # A preceding assistant question opens a generic answer slot.
        if previous_april and ("?" in previous_april or "？" in previous_april):
            return {
                "active": True,
                "status": "open",
                "kind": "question",
                "role": "april_questions_user",
                "phase": "awaiting_user_answer",
                "expected_input_type": "answer",
                "prompt": previous_april,
                "last_question": previous_april,
                "target": "",
                "candidate_answer": "",
                "last_user_answer": "",
                "known_clues": [],
                "qa_history": [{"user": previous_user, "assistant_prompt": previous_april, "kind": "question"}],
                "turns": [{"user": previous_user, "assistant_prompt": previous_april, "kind": "question"}],
                "awaiting_user": True,
                "completed": False,
                "topic": "вопрос",
                "goal": "answer_question",
                "sequence_id": scope.get("dialogue_sequence_id", ""),
                "scene_id": "",
                "task_revision": 1,
                "source": "dialogue_environment_question_recovery",
            }
        return {}

    @classmethod
    def _current_task_start(cls, text: str, scope: dict[str, str]) -> dict[str, Any]:
        if cls._riddle_solve_request(text):
            return {
                "active": True,
                "status": "answer_received",
                "kind": "riddle",
                "role": "april_solves_user_riddle",
                "phase": "solve_user_riddle",
                "expected_input_type": "assistant_answer",
                "prompt": cls._text(text),
                "last_question": cls._text(text),
                "target": "загадка",
                "secret_target": "",
                "candidate_answer": "",
                "last_user_answer": cls._text(text),
                "known_clues": [cls._text(text)],
                "qa_history": [{"user": cls._text(text), "kind": "riddle_prompt"}],
                "turns": [{"user": cls._text(text), "kind": "riddle_prompt"}],
                "awaiting_user": False,
                "completed": False,
                "topic": "загадка",
                "goal": "solve_riddle",
                "sequence_id": scope.get("dialogue_sequence_id", ""),
                "scene_id": "",
                "task_revision": 1,
                "source": "dialogue_environment_current_task",
            }
        if cls._riddle_create_request(text):
            return {
                "active": True,
                "status": "pending_generation",
                "kind": "riddle",
                "role": "april_asks_riddle",
                "phase": "generate_riddle",
                "expected_input_type": "assistant_generation",
                "prompt": cls._text(text),
                "last_question": "",
                "target": "",
                "secret_target": "",
                "candidate_answer": "",
                "last_user_answer": "",
                "known_clues": [],
                "qa_history": [{"user": cls._text(text), "kind": "riddle_request"}],
                "turns": [{"user": cls._text(text), "kind": "riddle_request"}],
                "awaiting_user": False,
                "completed": False,
                "topic": "загадка",
                "goal": "generate_riddle",
                "sequence_id": scope.get("dialogue_sequence_id", ""),
                "scene_id": "",
                "task_revision": 1,
                "source": "dialogue_environment_current_task",
            }
        return {}

    @classmethod
    def _looks_like_command(cls, text: str) -> bool:
        words = cls._tokens(text)
        if not words:
            return False
        return words[0] in cls._COMMAND_HEADS

    @classmethod
    def _topic_from_current(cls, text: str, task: dict[str, Any] | None = None) -> str:
        task = task if isinstance(task, dict) else {}
        if task.get("topic"):
            return cls._text(task.get("topic"))
        if cls._riddle_solve_request(text) or cls._riddle_create_request(text):
            return "загадка"

        current = cls._text(text)
        low = current.lower().strip()
        # Greeting/meta-introduction is not a semantic topic.
        generic_meta = (
            r"^(?:привет|здравствуйте|добрый\s+(?:день|вечер)|доброе\s+утро)"
            r"(?:[!.;,\s]+(?:я|мне|хочу|нужно|давай|помоги|поможешь|хотел|хотела)\b.*)?$"
        )
        if re.fullmatch(generic_meta, low, flags=re.IGNORECASE):
            return ""

        declarative = cls._declarative_topic_candidate(current)
        if declarative:
            return declarative[:140]

        quoted = re.findall(r"[«\"]([^»\"]{2,100})[»\"]", current)
        if quoted:
            value = cls._text(quoted[0])
            if value and not cls._generic_dialogue_topic(value):
                return value[:140]

        subject = cls._subject_from_current(current)
        if subject and not cls._reference_led_subject(subject):
            return subject[:140]

        # Meta intent such as "Хочу развить тему" has direction but no topic.
        if re.search(
            r"\b(?:хочу|хотел|хотела|нужно|надо|помоги|поможешь|развить|обсудить|"
            r"продолжить|заняться|поговорить)\b",
            low,
        ) and not re.search(r"\b(?:про|об|о|насч(?:ё|ё)т)\b", low):
            return ""

        words = cls._tokens(current)
        if len(words) <= 2:
            candidate = cls._text(current)
            return "" if cls._generic_dialogue_topic(candidate) else candidate[:140]
        first_sentence = cls._text(re.split(r"(?<=[.!?。！？])\s+", current)[0])
        return "" if cls._generic_dialogue_topic(first_sentence) else first_sentence[:140]

    @classmethod
    def _new_topic_context(cls, text: str, scope: dict[str, str]) -> dict[str, Any]:
        task = cls._current_task_start(text, scope)
        topic = cls._declarative_topic_candidate(text) or cls._topic_from_current(text, task)
        representation = "text"
        low = cls._low(text)
        if any(x in low for x in ("картин", "изображ", "портрет", "нарисуй", "изобрази")):
            representation = "image"
        elif "схем" in low:
            representation = "diagram"
        elif "график" in low:
            representation = "graph"
        elif "таблиц" in low:
            representation = "table"
        elif "код" in low or "python" in low:
            representation = "code"
        if task.get("active"):
            goal = task.get("goal") or "answer"
            operation = "generate" if task.get("status") == "pending_generation" else "answer"
            relation = "NEW_TOPIC"
            return {
                "turn_relation": relation,
                "relation": "NEW",
                "conversation_continuation": bool(scope.get("conversation_id")),
                "topic_branch": "new",
                "context_dependency": "current_turn_only",
                "current_topic": topic,
                "active_entity": "загадка" if task.get("kind") == "riddle" else (cls._subject_from_current(text) if not cls._reference_led_subject(cls._subject_from_current(text)) else ""),
                "operation": operation,
                "goal": goal,
                "representation": representation,
                "active_task": task,
                "previous_user_turn": "",
                "previous_april_turn": "",
                "selected_memory": [],
                "historical_memory_allowed": False,
                "resolved_request": cls._text(text),
            }
        return {
            "turn_relation": relation if (relation := "NEW_TOPIC") else "NEW_TOPIC",
            "relation": "NEW",
            "conversation_continuation": bool(scope.get("conversation_id")),
            "topic_branch": "new",
            "context_dependency": "current_turn_only",
            "current_topic": topic,
            "active_entity": (cls._subject_from_current(text) if not cls._reference_led_subject(cls._subject_from_current(text)) else ""),
            "operation": "answer" if "?" in text or "？" in text else "build" if cls._looks_like_command(text) else "answer",
            "goal": "answer",
            "representation": representation,
            "active_task": {},
            "previous_user_turn": "",
            "previous_april_turn": "",
            "selected_memory": [],
            "historical_memory_allowed": False,
            "resolved_request": cls._text(text),
        }

    @classmethod
    def _recall_context(cls, text: str, state: dict[str, Any], history: list[Any], scope: dict[str, str]) -> dict[str, Any]:
        # Recall is deliberately isolated from active task ownership.  The actual
        # ranking is left to the existing semantic memory surface later in the route.
        return {
            "turn_relation": "REFERENCE_OLD_TOPIC",
            "relation": "RECALL",
            "conversation_continuation": bool(scope.get("conversation_id")),
            "topic_branch": "recalled",
            "context_dependency": "memory_reference",
            "current_topic": cls._topic_from_current(text),
            "active_entity": "",
            "operation": "retrieve" if any(x in cls._low(text) for x in ("вспомни", "напомни", "что мы обсуждали")) else "answer",
            "goal": "obtain",
            "representation": "text",
            "active_task": {},
            "previous_user_turn": "",
            "previous_april_turn": "",
            "selected_memory": [],
            "historical_memory_allowed": True,
            "resolved_request": cls._text(text),
        }

    @classmethod
    def _declarative_topic_candidate(cls, text: str) -> str:
        """Extract a concrete topic introduced by a declarative current turn."""
        current = cls._text(text)
        if not current:
            return ""
        patterns = (
            r"^(?:скорее|это|думаю|речь\s+(?:идет|идёт)|тема|идея(?:\s+вот)?)[,:]?\s+([^.!?]{3,140})",
            r"^(?:у\s+меня|есть\s+у\s+меня)\s+(?:идея|тема|сюжет|история)\s*[—:-]?\s*([^.!?]{3,140})",
        )
        for pattern in patterns:
            match = re.search(pattern, current, re.IGNORECASE)
            if match:
                value = cls._text(match.group(1)).strip(" ,:;—-\t")
                if value and not cls._reference_led_subject(value):
                    low = value.lower()
                    if low not in {"привет", "здравствуйте", "хорошо", "отлично", "вопрос", "ответ"}:
                        return value[:180]
        return ""

    @classmethod
    def _generic_dialogue_topic(cls, value: Any) -> bool:
        low = cls._low(value).strip(" .,!?:;-—")
        return low in {
            "", "привет", "здравствуйте", "доброе утро", "добрый вечер",
            "добрый день", "хорошо", "отлично", "вопрос", "ответ", "тема",
            "задача", "разговор", "игра",
        }

    @classmethod
    def _continuation_context(cls, text: str, previous: dict[str, Any], scope: dict[str, str], active_topic: str = "") -> dict[str, Any]:
        previous_user = cls._text(previous.get("user"))
        previous_april = cls._text(previous.get("april"))
        confirmation = cls._confirmation(text)
        rejection = cls._rejection(text)
        recovered = cls._generic_task_from_pair(previous_user, previous_april, scope)
        task = dict(recovered)

        # Confirmation/rejection are discourse moves, never new topics.
        if confirmation or rejection:
            if task:
                task["status"] = "answer_received"
                task["phase"] = "confirmed" if confirmation else "corrected"
                task["candidate_answer"] = previous_april
                task["last_user_answer"] = cls._text(text)
                task["awaiting_user"] = False
            return {
                "turn_relation": "TASK_CONFIRMATION" if confirmation else "TASK_CORRECTION",
                "relation": "CONTINUE",
                "conversation_continuation": bool(scope.get("conversation_id")),
                "topic_branch": "continue",
                "context_dependency": "active_dialogue_sequence" if task else "immediate_pair",
                "current_topic": cls._text(task.get("topic") or "вопрос"),
                "active_entity": cls._text(task.get("candidate_answer") or ""),
                "operation": "answer",
                "goal": cls._text(task.get("goal") or "continue"),
                "representation": "text",
                "active_task": task,
                "previous_user_turn": previous_user,
                "previous_april_turn": previous_april,
                "selected_memory": [],
                "historical_memory_allowed": False,
                "resolved_request": cls._text(text),
                "provider_instruction": (
                    "Acknowledge the user's confirmation of the immediately preceding answer and advance the conversation naturally. "
                    if confirmation else
                    "Handle the user's correction/rejection against the immediately preceding answer and continue the active task. "
                ) + f"Previous user: {previous_user}. Previous April: {previous_april}. Current user: {cls._text(text)}",
            }

        # Short/elliptical replies are attached to a real antecedent rather than
        # promoted to standalone topics.  Pronouns and follow-up words get a wide
        # semantic window; ordinary self-contained commands stay new.
        low = cls._low(text)
        tokens = cls._tokens(text)
        current_subject = cls._subject_from_current(text)
        deictic_tokens = {
            "это", "этот", "эта", "эту", "этой", "этим", "эти", "эту",
            "её", "ее", "его", "ему", "ей", "он", "она", "оно", "они",
            "тот", "та", "те", "там", "здесь", "теперь", "дальше",
        }
        deictic = bool(set(tokens) & deictic_tokens)
        short = len(tokens) <= 8
        followup_heads = {"кто", "где", "какой", "какая", "какое", "какие", "почему", "как", "когда", "зачем", "сколько", "чем"}
        question_followup = bool(tokens and tokens[0] in followup_heads) or (("?" in text or "？" in text) and any(x in tokens for x in followup_heads))

        # Explicit topic switch with an explicit object is NEW, even though it
        # contains the continuation word "теперь".
        if cls._explicit_new_topic(text) and current_subject and previous_user:
            return cls._new_topic_context(text, scope)
        prior_question = "?" in previous_april or "？" in previous_april
        semantic_overlap = max(cls._similarity(text, previous_user), cls._similarity(text, previous_april))

        # A concrete declarative topic introduction can occur inside the same
        # authenticated conversation. Conversation continuity does not imply topic
        # continuity. Open a new semantic branch when the old root is only a
        # greeting/generic prompt, or when the introduced topic is clearly distinct.
        declarative_topic = cls._declarative_topic_candidate(text)
        previous_topic = cls._text(
            active_topic
            or (previous.get("raw", {}).get("topic") if isinstance(previous.get("raw"), dict) else "")
            or (previous.get("raw", {}).get("sequence_topic") if isinstance(previous.get("raw"), dict) else "")
        )
        if declarative_topic and not deictic and not question_followup:
            topic_similarity = cls._similarity(declarative_topic, previous_topic) if previous_topic else 0.0
            if cls._generic_dialogue_topic(previous_topic) or (previous_topic and topic_similarity < 0.16):
                return cls._new_topic_context(text, scope)

        # A direct user-name disclosure belongs to the immediately preceding
        # identity exchange. Capture it before generic NEW-topic logic.
        identity_disclosure = cls._identity_disclosure(text, previous_user, previous_april)
        if identity_disclosure:
            name = cls._text(identity_disclosure.get("name"))
            task = {
                "active": True,
                "status": "answer_received",
                "kind": "identity",
                "role": "user_discloses_name",
                "phase": "awaiting_assistant_action",
                "expected_input_type": "assistant_answer",
                "prompt": previous_user or previous_april,
                "last_question": previous_user or previous_april,
                "target": "user_identity",
                "candidate_answer": name,
                "last_user_answer": name,
                "known_clues": [name],
                "qa_history": [{"user": previous_user, "assistant": previous_april, "user_identity": name}],
                "turns": [{"user": previous_user, "assistant_prompt": previous_april, "user_identity": name}],
                "awaiting_user": False,
                "completed": True,
                "topic": "user_identity",
                "goal": "remember_user_name",
                "sequence_id": scope.get("dialogue_sequence_id", ""),
                "scene_id": "",
                "task_revision": 1,
                "source": "dialogue_environment_identity_disclosure",
            }
            return {
                "turn_relation": "IDENTITY_PROVIDED",
                "relation": "CONTINUE",
                "conversation_continuation": bool(scope.get("conversation_id")),
                "topic_branch": "continue",
                "context_dependency": "active_dialogue_sequence",
                "current_topic": "user_identity",
                "active_entity": name,
                "operation": "answer",
                "goal": "remember_user_name",
                "representation": "text",
                "active_task": task,
                "identity_disclosure": identity_disclosure,
                "previous_user_turn": previous_user,
                "previous_april_turn": previous_april,
                "selected_memory": [],
                "historical_memory_allowed": False,
                "resolved_request": cls._text(text),
                "provider_instruction": (
                    "The user has just explicitly supplied their name. Acknowledge the name naturally and keep it as a persistent authenticated user fact. "
                    f"User name: {name}. Current user turn: {cls._text(text)}"
                ),
            }

        # A self-contained request/question is a new topic even when an older
        # interactive task is still present. Short replies and deictic references
        # remain eligible for continuation, but a concrete new command such as
        # "Расскажи про Tesla" must never be swallowed by the old task.
        explicit_object_topic = bool(
            re.search(r"\b(?:про|обо?|насч(?:ё|ё)т)\s+[^?!。！？]{2,}", low, re.IGNORECASE)
            or re.search(r'[«"][^»"]{3,}[»"]', text)
        )
        development_command = bool(
            active_topic
            and not cls._generic_dialogue_topic(active_topic)
            and tokens
            and tokens[0] in cls._COMMAND_HEADS
            and not explicit_object_topic
            and not cls._explicit_new_topic(text)
        )
        self_contained_new = bool(
            len(tokens) >= 3
            and not deictic
            and not confirmation
            and not rejection
            and semantic_overlap < 0.30
            and (
                not active_topic
                or cls._generic_dialogue_topic(active_topic)
                or declarative_topic
                or explicit_object_topic
            )
            and (current_subject or cls._looks_like_command(text) or "?" in text or "？" in text)
        )
        if self_contained_new:
            return cls._new_topic_context(text, scope)

        # When April has just asked the user a riddle/question, a short standalone
        # answer belongs to that task even with zero lexical overlap. Record the
        # answer in the task frame immediately so Provider receives the new fact.
        if task and short and not question_followup and not confirmation and not rejection:
            expected = cls._low(task.get("expected_input_type"))
            if expected in {"answer", "user_answer", "followup", ""} or task.get("phase") == "awaiting_user_answer":
                task["candidate_answer"] = cls._text(text)
                task["last_user_answer"] = cls._text(text)
                task["status"] = "answer_received"
                task["phase"] = "awaiting_assistant_action"
                task["awaiting_user"] = False
                task["task_revision"] = int(task.get("task_revision", 0) or 0) + 1
                return {
                    "turn_relation": "TASK_ANSWER",
                    "relation": "CONTINUE",
                    "conversation_continuation": bool(scope.get("conversation_id")),
                    "topic_branch": "continue",
                    "context_dependency": "active_dialogue_sequence",
                    "current_topic": cls._text(task.get("topic") or "вопрос"),
                    "active_entity": cls._text(text),
                    "operation": "answer",
                    "goal": cls._text(task.get("goal") or "answer"),
                    "representation": "text",
                    "active_task": task,
                    "previous_user_turn": previous_user,
                    "previous_april_turn": previous_april,
                    "selected_memory": [],
                    "historical_memory_allowed": False,
                    "resolved_request": cls._text(text),
                    "provider_instruction": (
                        "Evaluate the user's current answer against the immediately preceding active question/riddle. "
                        "Use the task state and respond naturally without repeating the prompt. "
                        f"Question/riddle: {previous_april}. Current user answer: {cls._text(text)}"
                    ),
                }

        continuation = bool(
            task
            or question_followup
            or prior_question and short
            or deictic and previous_april
            or semantic_overlap >= 0.22
            or development_command
            or low.startswith(("теперь ", "дальше ", "ещё ", "еще ", "а теперь ", "продолж"))
        )
        if continuation:
            stable_subject = cls._stable_subject_from_pair(previous_user, previous_april)
            topic = cls._text(
                task.get("topic")
                or stable_subject
                or previous.get("topic")
                or active_topic
                or ""
            )
            if not topic or topic in {"вопрос", "ответ", "тема"}:
                topic = (
                    active_topic
                    or stable_subject
                    or cls._topic_from_current(previous_user or previous_april, task)
                )
            active_entity = cls._text(
                task.get("candidate_answer")
                or stable_subject
            )
            provider_instruction = (
                "Continue the current dialogue using the immediately preceding USER↔APRIL pair. "
                "Do not repeat covered content; answer the current user turn and advance naturally. "
                f"Previous user: {previous_user}. Previous April: {previous_april}. Current user: {cls._text(text)}"
            )
            return {
                "turn_relation": "CONTINUE_TOPIC" if not task else "TASK_CONTINUE",
                "relation": "CONTINUE",
                "conversation_continuation": bool(scope.get("conversation_id")),
                "topic_branch": "continue",
                "context_dependency": "active_dialogue_sequence",
                "current_topic": topic or "",
                "active_entity": active_entity,
                "operation": "answer",
                "goal": cls._text(task.get("goal") or "continue"),
                "representation": "text",
                "active_task": task,
                "previous_user_turn": previous_user,
                "previous_april_turn": previous_april,
                "selected_memory": [],
                "historical_memory_allowed": False,
                "resolved_request": cls._text(text),
                "provider_instruction": provider_instruction,
            }

        return cls._new_topic_context(text, scope)

    @classmethod
    def _stale_entity_candidates(cls, state: dict[str, Any], previous: dict[str, Any], current_text: str, active_entity: str) -> list[str]:
        stale: list[str] = []
        seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        for value in (
            seq.get("active_entity"),
            state.get("april_active_entity"),
            (state.get("scene_state") or {}).get("active_entity") if isinstance(state.get("scene_state"), dict) else "",
        ):
            value = cls._text(value)
            if value and value != active_entity and cls._similarity(value, current_text) < 0.05 and cls._similarity(value, previous.get("user"),) < 0.05:
                stale.append(value)
        return list(dict.fromkeys(stale))

    @classmethod
    def build(cls, text: str, state: dict[str, Any], history: list[Any]) -> dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []
        scope = cls._scope(state)
        previous = cls._latest_pair(state, history, scope)

        # A visual reference is a dialogue dependency, not a fresh image topic.
        # Keep the authenticated sequence authoritative when the referenced turn
        # is immediately available; otherwise fall back to 7-day RECALL.
        visual_reference = cls._visual_reference_query(text)
        current_task = cls._current_task_start(text, scope)
        explicit_new = cls._explicit_new_topic(text)
        if explicit_new:
            env = cls._new_topic_context(text, scope)
        elif visual_reference and previous:
            sequence_state = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
            active_topic_context = cls._text(
                state.get("active_topic")
                or state.get("current_topic")
                or sequence_state.get("active_topic")
                or sequence_state.get("topic")
                or (state.get("semantic_anchor", {}).get("topic_root") if isinstance(state.get("semantic_anchor"), dict) else "")
            )
            env = cls._continuation_context(text, previous, scope, active_topic=active_topic_context)
            env["turn_relation"] = "VISUAL_REFERENCE"
            env["context_dependency"] = "active_dialogue_sequence"
            env["visual_reference"] = True
        elif visual_reference:
            env = cls._recall_context(text, state, history, scope)
            env["turn_relation"] = "REFERENCE_OLD_VISUAL"
            env["visual_reference"] = True
        elif current_task:
            env = cls._new_topic_context(text, scope)
        elif cls._memory_query(text):
            env = cls._recall_context(text, state, history, scope)
        elif previous:
            sequence_state = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
            active_topic_context = cls._text(
                state.get("active_topic")
                or state.get("current_topic")
                or sequence_state.get("active_topic")
                or sequence_state.get("topic")
                or (state.get("semantic_anchor", {}).get("topic_root") if isinstance(state.get("semantic_anchor"), dict) else "")
            )
            env = cls._continuation_context(text, previous, scope, active_topic=active_topic_context)
        else:
            env = cls._new_topic_context(text, scope)

        env["visual_reference"] = bool(visual_reference)
        env["previous_visual_attachment"] = deepcopy(previous.get("visual_attachment") or {}) if isinstance(previous, dict) else {}

        active_task = env.get("active_task") if isinstance(env.get("active_task"), dict) else {}
        active_entity = cls._text(env.get("active_entity"))
        stale_entities = cls._stale_entity_candidates(state, previous, text, active_entity)
        continuation_analysis = {
            "version": "dialogue_continuation_planner_v2",
            "mode": env.get("turn_relation"),
            "active": env.get("relation") in {"CONTINUE", "RECALL"},
            "new_information_required": env.get("relation") == "CONTINUE",
            "covered_content": [cls._text(previous.get("april"))[:360]] if previous.get("april") and env.get("relation") == "CONTINUE" else [],
            "avoid_repeat_content": [cls._text(previous.get("april"))[:360]] if previous.get("april") and env.get("relation") == "CONTINUE" else [],
            "novelty_target": "current_turn_answer" if env.get("relation") == "CONTINUE" else "current_topic",
            "next_direction": "answer_current_turn_and_advance" if env.get("relation") == "CONTINUE" else "recall_and_connect" if env.get("relation") == "RECALL" else "develop_new_topic",
            "answer_strategy": (
                "ACKNOWLEDGE_AND_ADVANCE" if env.get("turn_relation") == "TASK_CONFIRMATION"
                else "CORRECT_AND_ADVANCE" if env.get("turn_relation") == "TASK_CORRECTION"
                else "SOLVE_ACTIVE_TASK" if env.get("turn_relation") == "TASK_CONTINUE" and active_task.get("kind") in {"riddle", "game"}
                else "ANSWER_WITHOUT_REPEAT" if env.get("relation") == "CONTINUE"
                else "RECALL_AND_CONNECT" if env.get("relation") == "RECALL"
                else "START_FRESH"
            ),
            "recap_ratio_max": 0.20 if env.get("relation") == "CONTINUE" else 0.0,
        }

        diagnostics = {
            "source": cls.VERSION,
            "scope": scope,
            "previous_pair_found": bool(previous),
            "previous_pair_sequence_id": cls._text(previous.get("sequence_id")),
            "stale_entities_fenced": stale_entities,
            "historical_memory_policy": "recall_only" if env.get("historical_memory_allowed") else "excluded",
            "current_turn_authority": True,
            "active_branch_authority": env.get("relation") == "CONTINUE",
            "contradiction_count": len(stale_entities),
        }

        return {
            "version": cls.VERSION,
            "scope": scope,
            "current_turn": {"text": cls._text(text), "authoritative": True},
            "previous_pair": previous,
            "turn_relation": env.get("turn_relation"),
            "relation": env.get("relation"),
            "conversation_continuation": bool(env.get("conversation_continuation")),
            "topic_branch": env.get("topic_branch"),
            "context_dependency": env.get("context_dependency"),
            "current_topic": cls._text(env.get("current_topic")),
            "active_entity": active_entity,
            "operation": cls._text(env.get("operation") or "answer"),
            "goal": cls._text(env.get("goal") or "answer"),
            "representation": cls._text(env.get("representation") or "text"),
            "active_task": active_task,
            "previous_user_turn": cls._text(previous.get("user")),
            "previous_april_turn": cls._text(previous.get("april")),
            "previous_visual_attachment": deepcopy(previous.get("visual_attachment") or {}),
            "visual_reference": bool(env.get("visual_reference")),
            "selected_memory": list(env.get("selected_memory") or []),
            "historical_memory_allowed": bool(env.get("historical_memory_allowed")),
            "resolved_request": cls._text(text),
            "provider_instruction": cls._text(env.get("provider_instruction") or ""),
            "identity_disclosure": deepcopy(env.get("identity_disclosure") if isinstance(env.get("identity_disclosure"), dict) else {}),
            "continuation_content_analysis": continuation_analysis,
            "fenced_historical_entities": stale_entities,
            "diagnostics": diagnostics,
            "authority_chain": [
                "CURRENT_TURN",
                "AUTHENTICATED_USER_SCOPE",
                "IMMEDIATE_USER_APRIL_PAIR",
                "ACTIVE_TOPIC_BRANCH",
                "ACTIVE_TASK",
                "EXPLICIT_7D_MEMORY_RECALL",
                "HISTORICAL_MEMORY_EVIDENCE",
            ],
        }


DIALOGUE_ENVIRONMENT_ENGINE = DialogueEnvironmentEngine()
# ---------------------------------------------------------------------------
# Cognitive interpretation council
# ---------------------------------------------------------------------------
# These engines are deterministic semantic specialists. They do not call
# providers, select renderers, or execute tools. They enrich one shared
# workspace in a strict order. Each engine owns its own fields and returns
# evidence; arbitration and canonicalization decide the final handoff.
# ---------------------------------------------------------------------------

import hashlib


class InterpretationEngineBase:
    NAME = "interpretation_engine"
    VERSION = "1"

    @staticmethod
    def _text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    @classmethod
    def _low(cls, value: Any) -> str:
        return cls._text(value).lower()

    @classmethod
    def _tokens(cls, value: Any) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", cls._low(value))

    @classmethod
    def _sim(cls, a: Any, b: Any) -> float:
        left, right = set(cls._tokens(a)), set(cls._tokens(b))
        if not left or not right:
            return 0.0
        return float(len(left & right) / max(1, min(len(left), len(right))))

    @classmethod
    def _fingerprint(cls, value: Any) -> str:
        return hashlib.sha1(cls._low(value).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _scope(state: dict[str, Any]) -> dict[str, str]:
        seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        return {
            "user_id": str(state.get("user_id") or seq.get("user_id") or "").strip(),
            "conversation_id": str(state.get("conversation_id") or seq.get("conversation_id") or "").strip(),
            "dialogue_sequence_id": str(
                seq.get("sequence_id") or state.get("dialogue_sequence_id") or ""
            ).strip(),
        }

    @staticmethod
    def _modality_payloads(
        semantic: dict[str, Any],
        cognition: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        inputs = state.get("input_sources") if isinstance(state.get("input_sources"), dict) else {}
        return {
            "voice": semantic.get("voice_context") or cognition.get("voice_context") or inputs.get("voice"),
            "vision": semantic.get("vision_context") or cognition.get("vision_context") or inputs.get("images"),
            "gallery": semantic.get("gallery_context") or cognition.get("gallery_context") or inputs.get("gallery"),
            "files": semantic.get("file_context") or cognition.get("file_context") or inputs.get("files"),
            "links": semantic.get("link_context") or cognition.get("link_context") or inputs.get("links"),
        }


class IdentityScopeEngine(InterpretationEngineBase):
    NAME = "IdentityScopeEngine"
    VERSION = "identity_scope_v1"

    def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        scope = self._scope(state)
        complete = bool(scope["user_id"] and scope["conversation_id"])
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "scope": scope,
            "authenticated": bool(scope["user_id"]),
            "conversation_bound": bool(scope["conversation_id"]),
            "sequence_bound": bool(scope["dialogue_sequence_id"]),
            "scope_complete": complete,
            "authority": "CURRENT_AUTHENTICATED_SCOPE",
            "historical_cross_user_allowed": False,
            "confidence": 1.0 if complete else 0.60 if scope["user_id"] else 0.20,
        }


class CurrentTurnEngine(InterpretationEngineBase):
    NAME = "CurrentTurnEngine"
    VERSION = "current_turn_v1"

    def analyze(
        self,
        text: str,
        *,
        semantic: dict[str, Any],
        cognition: dict[str, Any],
        state: dict[str, Any],
        identity: dict[str, Any],
    ) -> dict[str, Any]:
        modalities = self._modality_payloads(semantic, cognition, state)
        available = [name for name, payload in modalities.items() if payload not in (None, "", {}, [])]
        raw = str(text or "")
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "raw_text": raw,
            "normalized_text": self._text(raw),
            "authoritative": True,
            "user_id": identity.get("scope", {}).get("user_id", ""),
            "conversation_id": identity.get("scope", {}).get("conversation_id", ""),
            "dialogue_sequence_id": identity.get("scope", {}).get("dialogue_sequence_id", ""),
            "modalities": modalities,
            "available_modalities": available,
            "text_present": bool(self._text(raw)),
            "current_request_fingerprint": self._fingerprint(raw),
            "must_preserve_exact_user_request": True,
        }


class DialogueBranchIndexEngine(InterpretationEngineBase):
    """Build a compact, user-bound index of dialogue branches.

    The index is derived from the durable seven-day dialogue records and the
    current hot sequence.  It is not a second memory store and it never becomes
    provider context by itself.  Its job is to answer one question before the
    rest of interpretation runs:

        "Which authenticated branch does this turn belong to, if any?"

    A branch is a stable semantic sequence identified by ``sequence_id``.  The
    current active sequence is only one candidate; an old branch can be resumed
    when the current turn explicitly points back to it ("вернёмся к схеме", "а
    что там с ёлкой", etc.) or when the turn is a strong semantic continuation of
    that branch.
    """

    NAME = "DialogueBranchIndexEngine"
    VERSION = "dialogue_branch_index_v1_user_bound"
    MAX_BRANCHES = 24
    MAX_RECORDS_PER_BRANCH = 48
    RESUME_MARKERS = (
        "вернись к", "вернемся к", "вернёмся к", "возвратимся к",
        "вернуться к", "вернёмся", "вернемся", "давай обратно к",
        "снова к", "опять к", "продолжим про", "продолжить про",
        "к той теме", "к прошлой теме", "по той теме", "про ту схему",
        "про ту машину", "про ту ёлку", "про ту картинку", "про ту тему",
    )
    LOOKBACK_MARKERS = (
        "там", "ту тему", "той теме", "тот разговор", "прошлый разговор",
        "раньше", "до этого", "мы обсуждали", "мы говорили", "я спрашивал",
        "я спрашивала", "ты говорила", "ты говорил", "как там",
    )
    # Lightweight morphology for branch routing. This is intentionally small:
    # it normalizes common Russian inflectional endings so "ёлка" and
    # "ёлкой/ёлку/ёлке" resolve to the same branch without adding a
    # heavyweight NLP dependency to the hot path.
    RU_SUFFIXES = (
        "иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими",
        "ов", "ев", "ей", "ой", "ах", "ях", "ам", "ям", "ом", "ем",
        "ым", "им", "ою", "ею", "ую", "юю", "ая", "яя", "ое",
        "ее", "ые", "ие", "ую", "юю", "ою", "ею", "ы", "и",
        "а", "я", "у", "ю", "о", "е", "ь",
    )

    @classmethod
    def _lexical_forms(cls, text: str) -> set[str]:
        forms: set[str] = set()
        for token in cls._tokens(text):
            token = token.replace("ё", "е")
            if len(token) < 3:
                continue
            forms.add(token)
            for suffix in cls.RU_SUFFIXES:
                if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                    forms.add(token[: -len(suffix)])
                    break
        return forms - {x.replace("ё", "е") for x in cls.STOPWORDS}

    STOPWORDS = {
        "а", "и", "но", "да", "нет", "это", "этот", "эта", "эту", "это", "тот", "та", "те",
        "там", "здесь", "теперь", "тогда", "сейчас", "дальше", "потом", "уже", "ещё", "еще",
        "про", "об", "о", "по", "к", "ко", "из", "от", "для", "на", "в", "во", "с", "со",
        "как", "что", "кто", "где", "когда", "почему", "зачем", "сколько", "какой", "какая",
        "какое", "какие", "чем", "можешь", "можно", "давай", "продолжим", "вернись", "вернемся",
        "вернёмся", "нарисуй", "покажи", "создай", "сделай", "напиши", "расскажи", "объясни",
        "опиши", "проверь", "сравни", "найди", "скажи", "дай", "построй", "помнишь", "вспомни",
        "напомни", "правильно", "неправильно", "верно", "точно",
    }
    INVALID_ANCHORS = STOPWORDS | {
        "подключите", "подключить", "подключи", "подключение", "напиши",
        "напишите", "скажи", "расскажи", "покажи", "сделай", "создай",
        "нарисуй", "объясни", "опиши", "не", "доброе", "утро",
    }

    @classmethod
    def _scope(cls, state: dict[str, Any]) -> dict[str, str]:
        seq = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        return {
            "user_id": cls._text(state.get("user_id") or seq.get("user_id")),
            "conversation_id": cls._text(state.get("conversation_id") or seq.get("conversation_id")),
            "dialogue_sequence_id": cls._text(seq.get("sequence_id") or state.get("dialogue_sequence_id")),
        }

    @classmethod
    def _source_items(cls, state: dict[str, Any], history: list[Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if isinstance(history, list):
            items.extend(x for x in history if isinstance(x, dict))

        seq = state.get("active_dialogue_sequence")
        if isinstance(seq, dict) and seq:
            items.append(seq)

        timeline = state.get("memory_timeline")
        if isinstance(timeline, dict):
            for key in sorted(timeline.keys(), reverse=True):
                day = timeline.get(key)
                if not isinstance(day, dict):
                    continue
                pairs = day.get("dialog_pairs")
                if isinstance(pairs, list):
                    items.extend(x for x in pairs if isinstance(x, dict))

        anchor = state.get("semantic_anchor")
        if isinstance(anchor, dict) and anchor:
            sequence = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
            items.append({
                "semantic_anchor": deepcopy(anchor),
                "sequence_id": anchor.get("sequence_id") or sequence.get("sequence_id"),
                "dialogue_sequence_id": anchor.get("sequence_id") or sequence.get("sequence_id"),
                "user_id": state.get("user_id") or sequence.get("user_id"),
                "conversation_id": state.get("conversation_id") or sequence.get("conversation_id"),
                "user_request": anchor.get("current_request"),
                "topic": anchor.get("topic_root"),
                "active_entity": anchor.get("primary_entity"),
                "goal": anchor.get("goal"),
            })

        for key in ("active_visual_scene", "current_visual_scene", "scene_state", "active_scene"):
            value = state.get(key)
            if isinstance(value, dict) and value:
                items.append(value)
        return items

    @classmethod
    def _pair(cls, item: dict[str, Any]) -> tuple[str, str]:
        user = item.get("user")
        april = item.get("april") or item.get("assistant")
        if isinstance(user, dict):
            user = user.get("text") or user.get("content") or user.get("answer") or user.get("user_request")
        if isinstance(april, dict):
            april = april.get("answer") or april.get("content") or april.get("summary") or april.get("april_answer")
        user = cls._text(user or item.get("user_request") or item.get("last_user_request"))
        april = cls._text(april or item.get("april_answer") or item.get("last_april_answer"))
        return user, april

    @classmethod
    def _subject_from_answer(cls, text: str) -> str:
        text = cls._text(text)
        if not text:
            return ""
        patterns = (
            r"(?:^|[.!?]\s*)это\s+([^.!?]+)",
            r"(?:правильн(?:ый|о)|верно)\s*!?\s*это\s+([^.!?]+)",
            r"ответ\s*[:—-]\s*([^.!?]+)",
            r"правильный ответ\s*[:—-]\s*([^.!?]+)",
        )
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                value = cls._text(m.group(1)).strip(" ,:;—-\t")
                if value and len(value) <= 180:
                    return value
        return ""

    @classmethod
    def _candidate_entity(cls, user: str, april: str, raw: dict[str, Any]) -> str:
        for key in ("canonical_entity", "active_entity", "entity", "current_entity", "object"):
            value = cls._text(raw.get(key))
            if value and value.lower() not in cls.INVALID_ANCHORS:
                return value[:180]

        # Direct topic/object in the user's command.
        subject = DialogueEnvironmentEngine._subject_from_current(user)
        if subject and not DialogueEnvironmentEngine._reference_led_subject(subject):
            return cls._text(subject)[:180]

        # Short answer/result subjects, e.g. "Ёлка" or "Да, это ёлка".
        answer_subject = cls._subject_from_answer(april)
        if answer_subject:
            return answer_subject[:180]

        # Single lexical noun-like user answers are useful branch anchors.
        tokens = cls._tokens(user)
        if 1 <= len(tokens) <= 3 and tokens:
            joined = cls._text(user)
            if not any(tok in cls.STOPWORDS for tok in tokens) and len(joined) <= 80:
                return joined[:180]
        return ""

    @classmethod
    def _topic(cls, user: str, april: str, raw: dict[str, Any]) -> str:
        for key in ("canonical_topic", "topic", "sequence_topic", "active_topic"):
            value = cls._text(raw.get(key))
            if value and value.lower() not in cls.INVALID_ANCHORS and value.lower() not in {"вопрос", "ответ", "тема"}:
                return value[:180]
        entity = cls._candidate_entity(user, april, raw)
        return entity or cls._text(user or april)[:180]

    @classmethod
    def _record(cls, item: dict[str, Any]) -> dict[str, Any]:
        user, april = cls._pair(item)
        anchor = item.get("semantic_anchor") if isinstance(item.get("semantic_anchor"), dict) else {}
        topic_from_anchor = cls._text(
            anchor.get("topic_root")
            or anchor.get("active_topic")
            or anchor.get("topic")
        )
        entity_from_anchor = cls._text(
            anchor.get("primary_entity")
            or anchor.get("active_entity")
            or anchor.get("entity")
        )
        goal_from_anchor = cls._text(anchor.get("goal") or anchor.get("active_goal"))
        return {
            "user": user,
            "april": april,
            "sequence_id": cls._text(item.get("sequence_id") or item.get("dialogue_sequence_id")),
            "scene_id": cls._text(item.get("scene_id") or item.get("visual_scene_id") or item.get("scene_contract_id")),
            "topic": topic_from_anchor or cls._topic(user, april, item),
            "entity": entity_from_anchor or cls._candidate_entity(user, april, item),
            "goal": goal_from_anchor or cls._text(item.get("goal") or item.get("active_goal"))[:160],
            "direction": cls._text(anchor.get("direction") or anchor.get("current_direction")),
            "focus": cls._text(anchor.get("active_focus") or anchor.get("focus")),
            "development": deepcopy(anchor.get("development") if isinstance(anchor.get("development"), dict) else {}),
            "semantic_anchor": deepcopy(anchor),
            "turn_index": item.get("sequence_turn_index") or item.get("turn_index") or item.get("turn_id"),
            "created_at": item.get("created_at") or item.get("timestamp") or item.get("updated_at"),
            "active_task": deepcopy(item.get("interactive_task_state") or item.get("active_task") or item.get("open_task") or {}),
        }

    @classmethod
    def _score(cls, query: str, branch: dict[str, Any]) -> float:
        low = cls._low(query)
        q_forms = cls._lexical_forms(query)
        q_tokens = set(cls._tokens(query)) - cls.STOPWORDS
        if not q_forms:
            return 0.0
        candidates = []
        for key in (
            "topic", "entity", "focus", "direction", "last_user_request",
            "last_april_answer", "goal",
        ):
            candidates.append(cls._text(branch.get(key)))
        for record in list(branch.get("records") or [])[-8:]:
            candidates.extend((
                cls._text(record.get("user")),
                cls._text(record.get("april")),
                cls._text(record.get("topic")),
                cls._text(record.get("entity")),
                cls._text(record.get("focus")),
                cls._text(record.get("direction")),
                cls._text(record.get("goal")),
            ))
            development = record.get("development")
            if isinstance(development, dict):
                candidates.extend((
                    cls._text(development.get("current_step")),
                    cls._text(development.get("next_step")),
                ))
        best = 0.0
        best_exact = False
        for value in candidates:
            if not value:
                continue
            v_forms = cls._lexical_forms(value)
            if not v_forms:
                continue
            overlap = len(q_forms & v_forms) / max(1, min(len(q_forms), len(v_forms)))
            phrase = 0.18 if any(form in cls._lexical_forms(cls._text(branch.get("canonical_entity"))) for form in q_forms if form) else 0.0
            best_exact = best_exact or bool(q_tokens & set(cls._tokens(value)))
            best = max(best, overlap + phrase)
        marker_boost = 0.25 if any(marker in low for marker in cls.RESUME_MARKERS) else 0.0
        lookback_boost = 0.14 if any(marker in low for marker in cls.LOOKBACK_MARKERS) else 0.0
        lexical_boost = 0.10 if best_exact else 0.0
        return min(1.0, best + marker_boost + lookback_boost + lexical_boost)

    @classmethod
    def _build_branches(cls, state: dict[str, Any], history: list[Any], scope: dict[str, str]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        active_seq = scope.get("dialogue_sequence_id")
        now = time.time()
        for raw in cls._source_items(state, history):
            user_id = cls._text(raw.get("user_id") or scope.get("user_id"))
            conversation_id = cls._text(raw.get("conversation_id") or scope.get("conversation_id"))
            if scope.get("user_id") and user_id and user_id != scope["user_id"]:
                continue
            if scope.get("conversation_id") and conversation_id and conversation_id != scope["conversation_id"]:
                continue
            rec = cls._record(raw)
            seq = rec["sequence_id"]
            if not seq:
                continue
            branch = grouped.setdefault(seq, {
                "branch_id": seq,
                "sequence_id": seq,
                "user_id": scope.get("user_id") or user_id,
                "conversation_id": scope.get("conversation_id") or conversation_id,
                "topic": rec["topic"],
                "canonical_entity": rec["entity"],
                "focus": rec.get("focus", ""),
                "direction": rec.get("direction", ""),
                "goal": rec["goal"],
                "development": deepcopy(rec.get("development") if isinstance(rec.get("development"), dict) else {}),
                "semantic_anchor": deepcopy(rec.get("semantic_anchor") if isinstance(rec.get("semantic_anchor"), dict) else {}),
                "records": [],
                "turn_count": 0,
                "last_turn_at": None,
                "last_user_request": "",
                "last_april_answer": "",
                "active": seq == active_seq,
                "status": "ACTIVE" if seq == active_seq else "DORMANT",
            })
            # A persisted semantic_anchor is stronger than compatibility fields
            # from stale scenes. Once an anchored record exists, an older non-anchor
            # scene must not overwrite the branch root/entity.
            rec_has_anchor = bool(rec.get("semantic_anchor"))
            branch_has_anchor = bool(branch.get("semantic_anchor"))
            if rec["topic"] and rec["topic"].lower() not in {"вопрос", "ответ", "тема", "правильно"}:
                if rec_has_anchor or not branch_has_anchor:
                    branch["topic"] = rec["topic"]
            if rec["entity"] and rec["entity"].lower() not in {"вопрос", "ответ", "правильно"}:
                if rec_has_anchor or not branch_has_anchor:
                    branch["canonical_entity"] = rec["entity"]
            if rec["goal"] and (rec_has_anchor or not branch_has_anchor):
                branch["goal"] = rec["goal"]
            if rec.get("focus"):
                branch["focus"] = rec["focus"]
            if rec.get("direction"):
                branch["direction"] = rec["direction"]
            if rec.get("development"):
                branch["development"] = deepcopy(rec["development"])
            if rec.get("semantic_anchor"):
                branch["semantic_anchor"] = deepcopy(rec["semantic_anchor"])
            branch["records"].append(rec)

        branches = []
        for branch in grouped.values():
            branch["records"] = branch["records"][-cls.MAX_RECORDS_PER_BRANCH:]
            branch["turn_count"] = len(branch["records"])
            last = branch["records"][-1] if branch["records"] else {}
            branch["last_user_request"] = cls._text(last.get("user"))
            branch["last_april_answer"] = cls._text(last.get("april"))
            branch["last_turn_at"] = last.get("created_at")
            stamp = last.get("created_at")
            try:
                age = max(0.0, now - float(stamp)) if stamp not in (None, "") else None
            except Exception:
                age = None
            branch["age_seconds"] = age
            # Prevent dead branches from winning indefinitely without a signal.
            branch["base_weight"] = 1.0 if branch["active"] else 0.82
            branches.append(branch)

        branches.sort(key=lambda x: (bool(x.get("active")), x.get("last_turn_at") or 0), reverse=True)
        return branches[: cls.MAX_BRANCHES]

    def analyze(self, text: str, *, state: dict[str, Any], history: list[Any], identity: dict[str, Any]) -> dict[str, Any]:
        state_scope = self._scope(state)
        identity_scope = identity.get("scope") if isinstance(identity, dict) else {}
        identity_scope = identity_scope if isinstance(identity_scope, dict) else {}
        # Identity scope is authoritative for user/conversation binding, while the
        # hot dialogue sequence may only exist in runtime state. Merge both instead
        # of letting an incomplete identity scope erase the active sequence id.
        scope = {
            "user_id": self._text(identity_scope.get("user_id") or state_scope.get("user_id")),
            "conversation_id": self._text(identity_scope.get("conversation_id") or state_scope.get("conversation_id")),
            "dialogue_sequence_id": self._text(identity_scope.get("dialogue_sequence_id") or state_scope.get("dialogue_sequence_id")),
        }
        branches = self._build_branches(state, history, scope)
        current_seq = self._text(scope.get("dialogue_sequence_id"))
        low = self._low(text)
        explicit_resume = any(marker in low for marker in self.RESUME_MARKERS)
        lookback = any(marker in low for marker in self.LOOKBACK_MARKERS)

        scored = []
        for branch in branches:
            score = self._score(text, branch)
            if branch.get("active"):
                score += 0.08
            branch_view = {
                "branch_id": branch.get("branch_id"),
                "sequence_id": branch.get("sequence_id"),
                "topic": branch.get("topic"),
                "canonical_entity": branch.get("canonical_entity"),
                "focus": branch.get("focus"),
                "direction": branch.get("direction"),
                "goal": branch.get("goal"),
                "development": deepcopy(branch.get("development") if isinstance(branch.get("development"), dict) else {}),
                "semantic_anchor": deepcopy(branch.get("semantic_anchor") if isinstance(branch.get("semantic_anchor"), dict) else {}),
                "turn_count": branch.get("turn_count"),
                "last_user_request": branch.get("last_user_request"),
                "last_april_answer": branch.get("last_april_answer"),
                "last_turn_at": branch.get("last_turn_at"),
                "active_task": deepcopy(branch.get("active_task") or {}),
                "active": bool(branch.get("active")),
                "status": branch.get("status"),
            }
            scored.append({"branch": branch_view, "score": round(min(1.0, score), 4)})
        scored.sort(key=lambda x: x["score"], reverse=True)

        selected = scored[0] if scored else None
        target = selected["branch"] if selected else {}
        # Pronoun/deictic turns such as "нарисуй её" may have no useful lexical
        # overlap. In that case the authenticated active branch remains the sole
        # candidate for entity inheritance, but it is never promoted to a branch
        # resume unless there is an explicit historical reference.
        deictic_turn = bool(re.search(r"\b(?:это|этот|эта|эту|этой|он|она|оно|они|его|ее|её|тот|та|там|этим|этой)\b", low))
        active_branch = next((item["branch"] for item in scored if item["branch"].get("active")), {})
        if (not target or (selected and selected["score"] < 0.30)) and active_branch and deictic_turn:
            target = active_branch
            selected = {"branch": active_branch, "score": 0.30}
        target_seq = self._text(target.get("sequence_id"))
        strong_target = bool(selected and selected["score"] >= (0.45 if explicit_resume else 0.62 if lookback else 0.72))
        resume_candidate = bool(
            strong_target
            and target_seq
            and target_seq != current_seq
            and (explicit_resume or lookback)
        )
        # A direct branch reference can also be expressed with a named entity
        # without a literal "вернись": "а что там с ёлкой?".
        entity_resume = bool(
            strong_target
            and target_seq
            and target_seq != current_seq
            and not explicit_resume
            and not current_seq == target_seq
            and self._text(target.get("canonical_entity"))
            and self._score(text, target) >= 0.88
        )
        resume = resume_candidate or entity_resume
        active_branch_view = next((
            item["branch"] for item in scored if item["branch"].get("active")
        ), {})

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "scope": scope,
            "index_size": len(branches),
            "active_sequence_id": current_seq,
            "branches": scored[:12],
            "selected_branch": target if strong_target else {},
            "active_branch": active_branch_view,
            "selected_score": float(selected["score"] if strong_target and selected else 0.0),
            "explicit_resume": explicit_resume,
            "lookback_signal": lookback,
            "resume_candidate": resume,
            "target_sequence_id": target_seq if resume else "",
            "target_branch_id": target.get("branch_id") if resume else "",
            "target_topic": target.get("topic") if resume else "",
            "target_entity": target.get("canonical_entity") if resume else "",
            "target_last_user_request": target.get("last_user_request") if resume else "",
            "target_last_april_answer": target.get("last_april_answer") if resume else "",
            "target_goal": target.get("goal") if resume else "",
            "resolution_mode": "RESUME_BRANCH" if resume else "ACTIVE_BRANCH" if target.get("active") else "NO_BRANCH_RESOLUTION",
            "historical_branch_as_evidence_only": not resume,
            "confidence": 0.98 if resume else 0.86 if strong_target else 0.70,
        }


class DialogueRelationEngine(InterpretationEngineBase):
    NAME = "DialogueRelationEngine"
    VERSION = "dialogue_relation_v4_synced"

    def analyze(
        self,
        text: str,
        *,
        state: dict[str, Any],
        history: list[Any],
        semantic: dict[str, Any],
        identity: dict[str, Any],
        branch_index: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        branch_index = branch_index if isinstance(branch_index, dict) else {}
        env = DIALOGUE_ENVIRONMENT_ENGINE.build(text, state, history)
        relation = str(env.get("relation") or "NEW").upper()
        turn_relation = str(env.get("turn_relation") or "").upper()
        previous_user = self._text(env.get("previous_user_turn"))
        previous_april = self._text(env.get("previous_april_turn"))
        task = env.get("active_task") if isinstance(env.get("active_task"), dict) else {}
        current = self._text(text)
        task_active = bool(task.get("active"))

        # A compact second pass catches discourse relations that are easier to
        # express directly than through prototype similarity.
        low = current.lower().strip(" .,!?:;-")
        confirmation = low in DialogueEnvironmentEngine._CONFIRMATION
        rejection = low in DialogueEnvironmentEngine._REJECTION
        visual_reference = bool(env.get("visual_reference")) or DIALOGUE_ENVIRONMENT_ENGINE._visual_reference_query(current)
        explicit_recall = (
            DIALOGUE_ENVIRONMENT_ENGINE._memory_query(current)
            or (
                any(marker in low for marker in ("вчера", "позавчера", "раньше", "на прошлой неделе"))
                and any(marker in low for marker in ("обсуждали", "говорили", "спрашивал", "спрашивала", "обсудили"))
            )
            or "помнишь" in low
        )
        explicit_new = DIALOGUE_ENVIRONMENT_ENGINE._explicit_new_topic(current)
        branch_resume = bool(branch_index.get("resume_candidate"))
        branch_target = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
        active_branch = branch_index.get("active_branch") if isinstance(branch_index.get("active_branch"), dict) else {}
        active_branch_deictic = bool(
            active_branch
            and re.search(
                r"\b(?:это|этот|эта|эту|этой|этим|он|она|оно|они|его|ее|её|тот|та|те|там|здесь)\b",
                low,
            )
        )

        if explicit_new:
            relation = "NEW"
            turn_relation = "NEW_TOPIC"
        elif explicit_recall and not branch_index.get("explicit_resume"):
            relation = "RECALL"
            turn_relation = "REFERENCE_OLD_TOPIC"
        elif branch_resume:
            relation = "CONTINUE"
            turn_relation = "RESUME_BRANCH"
            previous_user = self._text(branch_index.get("target_last_user_request")) or previous_user
            previous_april = self._text(branch_index.get("target_last_april_answer")) or previous_april
            env = dict(env)
            env.update({
                "relation": "CONTINUE",
                "turn_relation": "RESUME_BRANCH",
                "context_dependency": "branch_resume",
                "topic_branch": "resume",
                "active_entity": self._text(branch_index.get("target_entity")),
                "current_topic": self._text(branch_index.get("target_topic")) or self._text(env.get("current_topic")),
                "sequence_id": self._text(branch_index.get("target_sequence_id")),
                "target_sequence_id": self._text(branch_index.get("target_sequence_id")),
                "target_branch_id": self._text(branch_index.get("target_branch_id")),
                "target_branch": deepcopy(branch_target),
                "historical_memory_allowed": False,
            })
        elif active_branch_deictic:
            # A deictic follow-up ("нарисуй её", "покажи это", "объясни тот")
            # belongs to the authenticated active branch even when the hot scene
            # has incomplete previous-pair metadata. The branch index supplies the
            # last stable pair; no historical branch is activated.
            relation = "CONTINUE"
            turn_relation = "CONTINUE_TOPIC"
            previous_user = self._text(active_branch.get("last_user_request")) or previous_user
            previous_april = self._text(active_branch.get("last_april_answer")) or previous_april
            env = dict(env)
            env.update({
                "relation": "CONTINUE",
                "turn_relation": "CONTINUE_TOPIC",
                "context_dependency": "active_dialogue_sequence",
                "topic_branch": "active",
                "active_entity": self._text(active_branch.get("canonical_entity")),
                "current_topic": self._text(active_branch.get("topic")) or self._text(env.get("current_topic")),
                "sequence_id": self._text(active_branch.get("sequence_id")),
                "historical_memory_allowed": False,
            })
        elif visual_reference and previous_april:
            relation = "CONTINUE"
            turn_relation = "VISUAL_REFERENCE"
        elif explicit_recall:
            relation = "RECALL"
            turn_relation = "REFERENCE_OLD_TOPIC"
        elif confirmation and previous_april:
            relation = "CONTINUE"
            turn_relation = "TASK_CONFIRMATION" if task_active else "CONFIRMATION"
        elif rejection and previous_april:
            relation = "CONTINUE"
            turn_relation = "TASK_CORRECTION" if task_active else "CORRECTION"
        elif task_active and env.get("context_dependency") == "active_dialogue_sequence":
            relation = "CONTINUE"
        elif explicit_new and not task_active:
            relation = "NEW"
            turn_relation = "NEW_TOPIC"

        continuation_score = 0.0
        if relation == "CONTINUE":
            continuation_score = 0.94 if task_active else 0.82
        elif relation == "RECALL":
            continuation_score = 0.0
        else:
            continuation_score = 0.0

        confidence = 0.98 if turn_relation in {
            "TASK_ANSWER", "TASK_CONFIRMATION", "TASK_CORRECTION",
            "REFERENCE_OLD_TOPIC", "NEW_TOPIC"
        } else float(env.get("diagnostics", {}).get("current_turn_authority", False))

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "relation": relation,
            "turn_relation": turn_relation,
            "continuation": relation == "CONTINUE",
            "reference": relation == "RECALL",
            "previous_user_turn": previous_user,
            "previous_april_turn": previous_april,
            "previous_visual_attachment": deepcopy(env.get("previous_visual_attachment") or {}),
            "visual_reference": visual_reference,
            "active_task": task,
            "task_active": task_active,
            "context_dependency": env.get("context_dependency") or ("continuation" if relation == "CONTINUE" else "new_topic"),
            "environment": env,
            "branch_index": deepcopy(branch_index),
            "target_sequence_id": self._text(branch_index.get("target_sequence_id") if branch_resume else ""),
            "target_branch_id": self._text(branch_index.get("target_branch_id") if branch_resume else ""),
            "target_branch": deepcopy(branch_target) if branch_resume else {},
            "signals": {
                "confirmation": confirmation,
                "rejection": rejection,
                "explicit_recall": explicit_recall,
                "explicit_new_topic": explicit_new,
            },
            "confidence": max(0.20, confidence),
            "evidence": [
                "authenticated_scope",
                "immediate_user_april_pair",
                "active_task_state",
                "explicit_discourse_controls",
            ],
        }


class TopicDynamicsEngine(InterpretationEngineBase):
    NAME = "TopicDynamicsEngine"
    VERSION = "topic_dynamics_v3_subject_first"

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        semantic: dict[str, Any],
        state: dict[str, Any],
        branch_index: dict[str, Any] | None = None,
        entity: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        env = relation.get("environment") if isinstance(relation.get("environment"), dict) else {}
        branch_index = branch_index if isinstance(branch_index, dict) else {}
        task = relation.get("active_task") if isinstance(relation.get("active_task"), dict) else {}
        stored_anchor = state.get("semantic_anchor") if isinstance(state.get("semantic_anchor"), dict) else {}
        previous_topic = self._text(
            stored_anchor.get("topic_root")
            or env.get("current_topic")
            or state.get("active_topic")
            or state.get("current_topic")
        )
        task_topic = self._text(task.get("topic"))
        current = self._text(text)
        entity = entity if isinstance(entity, dict) else {}
        current_subject = DIALOGUE_ENVIRONMENT_ENGINE._subject_from_current(current)
        branch = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
        active_branch = branch_index.get("active_branch") if isinstance(branch_index.get("active_branch"), dict) else {}

        def topic_candidate(value: str) -> str:
            value = self._text(value)
            if not value or DIALOGUE_ENVIRONMENT_ENGINE._reference_led_subject(value):
                return ""
            low = value.lower()
            if low in {
                "привет", "здравствуйте", "доброе утро", "добрый вечер", "спасибо",
                "хорошо", "отлично", "вопрос", "ответ", "тема", "задача", "разговор", "игра",
            }:
                return ""
            return value[:180]

        # Declarative topic introductions deserve priority over the last hot topic.
        declarative_candidate = ""
        match = re.search(
            r"^(?:скорее|это|думаю|речь\s+(?:идет|идёт)|тема|идея(?:\s+вот)?)[,:]?\s+([^.!?]{3,120})",
            current,
            re.IGNORECASE,
        )
        if match:
            declarative_candidate = topic_candidate(match.group(1))

        explicit_topic_candidate = topic_candidate(current_subject)
        branch_anchor = branch.get("semantic_anchor") if isinstance(branch.get("semantic_anchor"), dict) else {}
        active_branch_anchor = active_branch.get("semantic_anchor") if isinstance(active_branch.get("semantic_anchor"), dict) else {}
        branch_topic = topic_candidate(
            branch_anchor.get("topic_root")
            or active_branch_anchor.get("topic_root")
            or branch.get("topic")
            or active_branch.get("topic")
            or env.get("current_topic")
        )

        if relation.get("turn_relation") == "RESUME_BRANCH" and branch_index.get("resume_candidate"):
            branch_action = "resume_branch"
            topic = topic_candidate(branch_index.get("target_topic")) or branch_topic or current
        elif relation.get("relation") == "RECALL":
            branch_action = "recall_branch"
            topic = topic_candidate(branch_index.get("target_topic")) or topic_candidate(task_topic) or branch_topic or current
        elif relation.get("relation") == "CONTINUE":
            branch_action = "continue_branch"
            # Keep a meaningful branch root stable. A generic placeholder root may
            # be replaced by the concrete topic introduced in the current turn.
            generic_root = not branch_topic
            if branch_topic:
                generic_root = self._low(branch_topic) in {
                    "вопрос", "ответ", "тема", "задача", "разговор", "игра", "привет", "отлично"
                }
            if generic_root and declarative_candidate:
                topic = declarative_candidate
            else:
                topic = topic_candidate(task_topic) or branch_topic or topic_candidate(previous_topic) or declarative_candidate or explicit_topic_candidate or current
        else:
            branch_action = "open_branch"
            # NEW uses only an actual semantic candidate. A greeting/meta request
            # therefore opens no topical root instead of storing "Привет!".
            topic = (
                topic_candidate(task_topic)
                or declarative_candidate
                or explicit_topic_candidate
                or ""
            )

        # Recover a usable root from the branch when the current text is merely
        # a development instruction such as "предложи начало".
        if relation.get("relation") == "CONTINUE" and topic in {"", "привет", "отлично"}:
            topic = branch_topic or topic_candidate(previous_topic) or current

        branch_key = self._fingerprint(topic)
        active_focus = topic_candidate(
            declarative_candidate
            or current_subject
            or (
                entity.get("active_entity")
                if self._low(entity.get("active_entity")) not in {
                    "привет", "здравствуйте", "хорошо", "отлично", "скорее",
                    "вопрос", "ответ", "тема", "разговор", "задача", "игра",
                }
                else ""
            )
            or (branch.get("focus") if relation.get("relation") == "CONTINUE" else "")
        )
        return {
            "engine": self.NAME,
            "version": "topic_dynamics_v4_root_focus",
            "topic": topic[:180],
            "topic_root": topic[:180],
            "active_focus": active_focus[:180],
            "previous_topic": previous_topic[:180],
            "topic_branch": branch_action,
            "topic_branch_key": f"topic:{branch_key}",
            "topic_changed": bool(previous_topic and topic and self._sim(previous_topic, topic) < 0.20),
            "old_topic_fenced": relation.get("relation") == "NEW",
            "topic_owner": "CURRENT_TURN" if relation.get("relation") == "NEW" else "ACTIVE_BRANCH",
            "confidence": 0.94 if topic else 0.40,
        }


class ActiveTaskEngine(InterpretationEngineBase):
    NAME = "ActiveTaskEngine"
    VERSION = "active_task_v3"

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        state: dict[str, Any],
        history: list[Any],
    ) -> dict[str, Any]:
        env_task = relation.get("active_task") if isinstance(relation.get("active_task"), dict) else {}
        task = dict(env_task)
        turn_relation = str(relation.get("turn_relation") or "").upper()

        if relation.get("relation") == "NEW" and not task.get("active"):
            current = DIALOGUE_ENVIRONMENT_ENGINE._current_task_start(text, self._scope(state))
            if current:
                task = dict(current)

        task_active = bool(task.get("active"))
        if task_active:
            phase = self._text(task.get("phase"))
            expected = self._text(task.get("expected_input_type"))
            ownership = "CURRENT_ACTIVE_TASK"
        else:
            phase = ""
            expected = ""
            ownership = "NONE"

        task_action = turn_relation in {
            "TASK_ANSWER", "TASK_CONFIRMATION", "TASK_CORRECTION",
            "TASK_CONTINUE", "TASK_RESPONSE",
        }

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "active": task_active,
            "task": task,
            "kind": self._text(task.get("kind")),
            "role": self._text(task.get("role")),
            "phase": phase,
            "expected_input_type": expected,
            "task_action": task_action,
            "ownership": ownership,
            "goal": self._text(task.get("goal")),
            "topic": self._text(task.get("topic")),
            "candidate_answer": self._text(task.get("candidate_answer")),
            "known_clues": list(task.get("known_clues") or [])[-12:],
            "qa_history": list(task.get("qa_history") or [])[-12:],
            "confidence": 0.96 if task_active else 0.50,
        }


class SemanticIntentEngine(InterpretationEngineBase):
    NAME = "SemanticIntentEngine"
    VERSION = "semantic_intent_v2"

    _OPERATIONS = (
        ("calculate", ("посчитай", "вычисли", "рассчитай", "сколько будет", "реши")),
        ("explain", ("объясни", "расскажи", "почему", "что означает", "разъясни")),
        ("compare", ("сравни", "сравнение", "чем отличается", "разница")),
        ("search", ("найди", "поищи", "где найти", "официальный сайт", "сайт")),
        ("create", ("создай", "сделай", "напиши", "придумай", "загадай", "загадай мне", "задай мне", "предложи", "сформулируй", "перепиши")),
        ("build", ("построй", "составь", "сформируй", "разработай", "дополни")),
        ("develop", ("развить", "развивай", "развивать", "доработай", "доработать", "проработай", "проработать", "расширь", "расширить")),
        ("analyze", ("проанализируй", "разбери", "проверь", "диагностируй")),
        ("retrieve", ("вспомни", "напомни", "вернись", "достань из памяти")),
        ("show", ("покажи", "представь", "изобрази", "нарисуй")),
    )

    def analyze(
        self,
        text: str,
        *,
        semantic_measurement: dict[str, Any],
        relation: dict[str, Any],
        task: dict[str, Any],
    ) -> dict[str, Any]:
        low = self._low(text)
        operation = ""
        for candidate, cues in self._OPERATIONS:
            if any(cue in low for cue in cues):
                operation = candidate
                break

        if relation.get("turn_relation") in {"TASK_CONFIRMATION", "CONFIRMATION"}:
            intent = "confirmation"
        elif relation.get("turn_relation") in {"TASK_CORRECTION", "CORRECTION"}:
            intent = "correction"
        elif relation.get("turn_relation") in {"TASK_ANSWER", "TASK_CONTINUE", "TASK_RESPONSE"}:
            intent = "task_response"
        elif relation.get("relation") == "RECALL":
            intent = "memory_recall"
        elif relation.get("relation") == "CONTINUE":
            intent = "follow_up"
        elif "?" in low or "？" in low:
            intent = "question"
        elif operation:
            intent = "request"
        else:
            intent = "statement"

        if not operation:
            operation = {
                "confirmation": "acknowledge",
                "correction": "correct",
                "task_response": "answer",
                "memory_recall": "retrieve",
                "follow_up": "answer",
                "question": "answer",
            }.get(intent, "answer")

        task_goal = self._text(task.get("goal"))
        goal = task_goal or {
            "calculate": "calculate",
            "explain": "understand",
            "compare": "compare",
            "search": "obtain_information",
            "create": "create_result",
            "build": "build_result",
            "develop": "develop_topic",
            "analyze": "diagnose_or_analyze",
            "retrieve": "obtain_memory",
            "show": "present",
        }.get(operation, "answer")

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "intent": intent,
            "operation": operation,
            "goal": goal,
            "current_request": self._text(text),
            "task_owned": bool(task.get("active")),
            "measurement": semantic_measurement,
            "confidence": 0.94 if operation or relation.get("relation") != "NEW" else 0.72,
        }


class DomainReasoningEngine(InterpretationEngineBase):
    NAME = "DomainReasoningEngine"
    VERSION = "domain_reasoning_v2"

    DOMAIN_CUES = {
        "mathematics": ("математ", "числ", "уравнен", "интеграл", "производн", "процент", "арифмет"),
        "geometry": ("геометр", "угол", "площад", "периметр", "треугольник", "круг", "радиус", "диаметр"),
        "physics": ("физик", "сила", "скорост", "масса", "энерг", "давлен", "ускорен", "ньютон"),
        "chemistry": ("хими", "реакци", "молекул", "атом", "элемент", "раствор"),
        "biology": ("биолог", "клетк", "ген", "организм", "растен", "животн"),
        "geography": ("географ", "страна", "город", "река", "горы", "континент", "карта"),
        "it": ("код", "python", "программ", "сервер", "api", "бот", "приложен", "алгоритм"),
        "web": ("сайт", "веб", "интернет", "страниц", "ссылка", "онлайн", "найди", "официальный сайт"),
        "automotive": ("автомоб", "машин", "двигател", "масл", "тормоз", "шина", "расход топлива", "tesla", "bmw", "geely", "toyota", "volkswagen"),
        "finance": ("банк", "деньги", "цена", "стоимость", "платеж", "paypal", "финанс", "крипт"),
        "literature": ("роман", "стих", "поэз", "писател", "литератур"),
        "politics": ("полит", "выбор", "правитель", "закон", "президент"),
        "news": ("новост", "сегодня", "последн", "событи"),
        "social": ("отношен", "общество", "человек", "семь"),
        "medicine": ("симптом", "лекар", "болит", "здоров", "медицин"),
        "travel": ("поездк", "отел", "билет", "турист", "маршрут"),
    }

    def analyze(
        self,
        text: str,
        *,
        semantic_measurement: dict[str, Any],
        relation: dict[str, Any] | None = None,
        intent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        low = self._low(text)
        relation = relation if isinstance(relation, dict) else {}
        intent = intent if isinstance(intent, dict) else {}

        if str(relation.get("turn_relation") or "").upper() in {
            "TASK_CONFIRMATION", "TASK_CORRECTION", "CONFIRMATION", "CORRECTION"
        }:
            return {
                "engine": self.NAME,
                "version": self.VERSION,
                "domain": "conversation",
                "domain_scores": {"conversation": 1.0},
                "candidate_domains": ["conversation"],
                "subdomain": "dialogue",
                "requires_domain_knowledge": False,
                "confidence": 0.98,
            }
        score_map: dict[str, float] = {}
        for domain, cues in self.DOMAIN_CUES.items():
            hits = sum(1 for cue in cues if cue in low)
            score_map[domain] = min(1.0, hits / max(1.0, min(4.0, len(cues) * 0.25)))

        # Existing matrix domain scores are supporting evidence only. Very small
        # prototype similarities must not turn an unrelated utterance into a
        # concrete domain (for example, a riddle becoming "biology").
        base = semantic_measurement.get("domain_scores") if isinstance(semantic_measurement, dict) else {}
        if isinstance(base, dict):
            for domain, value in base.items():
                value = float(value or 0.0)
                if value >= 0.20:
                    score_map[domain] = max(float(score_map.get(domain, 0.0)), value)

        ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        best = ranked[0][0] if ranked and ranked[0][1] > 0 else "general"
        best_score = ranked[0][1] if ranked else 0.0
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "domain": best,
            "domain_scores": {k: round(float(v), 4) for k, v in ranked[:12]},
            "candidate_domains": [k for k, v in ranked[:6] if v > 0.0],
            "subdomain": "",
            "requires_domain_knowledge": best not in {"general", "social"},
            "confidence": round(min(1.0, max(best_score, 0.35 if best != "general" else 0.20)), 4),
        }


class EntityResolutionEngine(InterpretationEngineBase):
    NAME = "EntityResolutionEngine"
    VERSION = "entity_resolution_v3_semantic_subject"

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        semantic: dict[str, Any],
        state: dict[str, Any],
        branch_index: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self._text(text)
        candidates: list[str] = []
        relation_value = self._text(relation.get("relation")).upper()
        env = relation.get("environment") if isinstance(relation.get("environment"), dict) else {}
        branch_index = branch_index if isinstance(branch_index, dict) else {}
        target_branch = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
        active_branch = branch_index.get("active_branch") if isinstance(branch_index.get("active_branch"), dict) else {}
        target_entity = self._text(
            branch_index.get("target_entity")
            or (target_branch.get("canonical_entity") if target_branch.get("active") else "")
            or (active_branch.get("canonical_entity") if relation_value == "CONTINUE" else "")
        )
        target_topic = self._text(
            branch_index.get("target_topic")
            or target_branch.get("topic")
            or (active_branch.get("topic") if relation_value == "CONTINUE" else "")
        )
        branch_resume = bool(branch_index.get("resume_candidate"))
        current_subject = DIALOGUE_ENVIRONMENT_ENGINE._subject_from_current(current)
        current_subject_is_reference = DIALOGUE_ENVIRONMENT_ENGINE._reference_led_subject(current_subject)
        command_heads = {
            "расскажи", "объясни", "покажи", "нарисуй", "создай", "сделай",
            "напиши", "построй", "проверь", "опиши", "сравни", "найди",
            "выведи", "подскажи", "скажи", "дай", "загадай", "отгадай",
            "разгадай", "реши", "придумай", "предложи", "продолжи", "разработай",
            "дополни", "исправь", "выбери", "сформулируй", "составь",
            "перепиши", "переделай",
        }

        def usable(value: Any) -> str:
            item = self._text(value)
            if not item:
                return ""
            first = self._tokens(item)[:1]
            non_entities = command_heads | {
                "почему", "как", "что", "кто", "где", "когда", "зачем",
                "сколько", "какой", "какая", "какое", "какие", "чем",
                "это", "теперь", "дальше", "привет", "здравствуйте",
                "доброе", "добрый", "хорошо", "отлично", "спасибо",
                "понял", "поняла", "конечно", "готово",
            }
            if first and first[0] in non_entities and len(self._tokens(item)) <= 3:
                return ""
            return item

        # Environment owns the stable subject; legacy semantic fields are only evidence.
        if branch_resume and target_entity:
            candidates.insert(0, target_entity)
        if relation_value == "CONTINUE":
            env_entity = usable(env.get("active_entity"))
            if env_entity and not DIALOGUE_ENVIRONMENT_ENGINE._reference_led_subject(env_entity):
                candidates.append(env_entity)
        if current_subject and not current_subject_is_reference:
            # Long multi-object directives are a focus/direction, not a single
            # canonical entity (e.g. "предложи начало, вступление, сюжет и развитие").
            subject_tokens = self._tokens(current_subject)
            explicit_object = bool(re.search(r"^\s*(?:про|обо?|о|насч(?:ё|ё)т)\s+", current, re.IGNORECASE))
            coordinated_focus = bool("," in current_subject or re.search(r"\s+и\s+", current_subject, re.IGNORECASE))
            if (len(subject_tokens) <= 5 and not coordinated_focus) or explicit_object:
                candidates.insert(0, current_subject)

        stored_anchor = state.get("semantic_anchor") if isinstance(state.get("semantic_anchor"), dict) else {}
        explicit_values = [
            semantic.get("active_entity"),
            semantic.get("entity"),
        ]
        if relation_value == "CONTINUE" and stored_anchor.get("primary_entity"):
            stored_entity = usable(stored_anchor.get("primary_entity"))
            if stored_entity:
                explicit_values.insert(0, stored_entity)
        # NEW must never inherit a legacy entity/current_object from the previous
        # branch. Only current-turn evidence is admissible here.

        for value in explicit_values:
            value = usable(value)
            if value and self._low(value).strip(" .,!?:;-—") not in {
                "привет", "здравствуйте", "хорошо", "отлично", "спасибо",
                "понял", "поняла", "конечно", "готово", "ответ",
            }:
                candidates.append(value)

        task_entity = self._text(task.get("task", {}).get("target") if isinstance(task.get("task"), dict) else "")
        if task_entity:
            candidates.append(task_entity)

        quoted = re.findall(r"[«\"]([^»\"]{2,120})[»\"]", current)
        candidates.extend(self._text(x) for x in quoted if self._text(x))

        # URLs/domains are first-class entities for web/site problems.
        candidates.extend(re.findall(r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}", current))

        # Capitalized phrases are useful entity evidence in mixed Russian/English input.
        proper = re.findall(
            r"\b(?:[А-ЯЁA-Z][\wЁёЇїІіЄєҐґ-]+(?:\s+[А-ЯЁA-Z][\wЁёЇїІіЄєҐґ-]+){0,3})\b",
            current,
        )
        candidates.extend(proper)

        # Do not mistake an imperative verb ("Отгадай", "Расскажи", "Покажи")
        # for an entity. Entity ownership comes from explicit entity evidence,
        # task state, or a real named object in the current turn.
        command_heads = {
            "расскажи", "объясни", "покажи", "нарисуй", "создай", "сделай",
            "напиши", "построй", "проверь", "опиши", "сравни", "найди",
            "выведи", "подскажи", "скажи", "дай", "загадай", "отгадай",
            "разгадай", "реши", "придумай", "предложи", "продолжи", "разработай",
            "дополни", "исправь", "выбери", "сформулируй", "составь",
            "перепиши", "переделай",
        }
        non_entity_heads = command_heads | {
            "теперь", "сейчас", "потом", "далее", "а", "и", "но", "давай",
            "пусть", "можешь", "можно", "скажи", "что", "как", "почему",
            "скорее", "это", "думаю", "есть", "вот", "тут", "здесь",
            "значит", "получается", "у", "меня", "нам", "мне",
            "хочу", "хотел", "хотела", "нужно", "надо", "помоги", "поможешь",
            "помочь", "развить", "обсудить", "поговорить", "заняться",
        }
        filtered = []
        for candidate in candidates:
            first = self._tokens(candidate)[:1]
            if first and first[0] in non_entity_heads and len(self._tokens(candidate)) <= 2:
                continue
            filtered.append(candidate)
        # Re-run the same semantic guard after all sources (quoted/proper/task)
        # have contributed candidates. This prevents question words such as
        # "Сколько" from returning through a later fallback path.
        candidates = list(dict.fromkeys(usable(x).strip() for x in filtered if usable(x)))

        inherited = ""
        if relation.get("relation") == "CONTINUE":
            if current_subject and not current_subject_is_reference:
                subject_tokens = self._tokens(current_subject)
                coordinated_focus = bool(
                    "," in current_subject
                    or re.search(r"\s+и\s+", current_subject, re.IGNORECASE)
                )
                if len(subject_tokens) <= 5 and not coordinated_focus:
                    inherited = current_subject
            if not inherited:
                inherited = usable(env.get("active_entity"))
            if not inherited:
                inherited = DIALOGUE_ENVIRONMENT_ENGINE._stable_subject_from_pair(
                    self._text(relation.get("previous_user_turn")),
                    self._text(relation.get("previous_april_turn")),
                )
            if not inherited:
                inherited = usable(task.get("target") or state.get("april_active_entity"))
            if inherited:
                candidates.insert(0, inherited)

        if task.get("active"):
            task_obj = task.get("task", {})
            task_kind = self._text(task_obj.get("kind")).lower()
            task_topic = self._text(task_obj.get("topic"))
            if task_kind == "riddle":
                candidates.insert(0, task_topic or "загадка")
            elif task_kind == "game":
                candidates.insert(0, task_topic or "игра")

        candidates = list(dict.fromkeys(x.strip() for x in candidates if self._text(x)))
        active_entity = self._text(candidates[0] if candidates else "")
        if relation.get("relation") == "NEW" and task.get("active"):
            task_obj = task.get("task", {})
            task_kind = self._text(task_obj.get("kind")).lower()
            if task_kind in {"riddle", "game"}:
                active_entity = self._text(task_obj.get("topic") or ("загадка" if task_kind == "riddle" else "игра"))

        if relation.get("relation") == "NEW":
            # A fresh topic cannot inherit an old entity. Prefer the explicit
            # semantic object extracted from this turn.
            if current_subject and not current_subject_is_reference:
                active_entity = self._text(current_subject)
            else:
                current_tokens = set(self._tokens(current))
                current_candidates = [
                    c for c in candidates
                    if set(self._tokens(c)) & current_tokens
                ]
                if current_candidates:
                    active_entity = self._text(current_candidates[0])
                elif task.get("active") and self._text(task.get("topic")):
                    active_entity = self._text(task.get("topic"))
                else:
                    active_entity = ""

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "active_entity": active_entity[:180],
            "candidate_entities": candidates[:16],
            "entity_source": "current_turn" if active_entity and self._sim(active_entity, current) > 0 else "contextual",
            "inherited_entity": inherited,
            "historical_entity_inheritance_blocked": relation.get("relation") == "NEW",
            "confidence": 0.90 if active_entity else 0.45,
        }


class ReferenceResolutionEngine(InterpretationEngineBase):
    NAME = "ReferenceResolutionEngine"
    VERSION = "reference_resolution_v2"

    DEICTIC = (
        "это", "этот", "эта", "эту", "этой", "этом", "этим",
        "он", "она", "оно", "они", "его", "ее", "её", "тот", "та", "там",
        "здесь", "выше", "ниже", "предыдущ", "дальше", "теперь",
    )

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        entity: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        branch_index: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        branch_index = branch_index if isinstance(branch_index, dict) else {}
        low = self._low(text)
        signals = [cue for cue in self.DEICTIC if cue in low]
        eligible = (
            relation.get("relation") != "NEW"
            and (
                bool(signals)
                or relation.get("turn_relation") in {
                    "TASK_ANSWER", "TASK_CONFIRMATION", "TASK_CORRECTION",
                    "CONFIRMATION", "CORRECTION",
                }
            )
        )

        target_branch = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
        branch_entity = self._text(branch_index.get("target_entity") or target_branch.get("canonical_entity"))
        branch_topic = self._text(branch_index.get("target_topic") or target_branch.get("topic"))
        candidates = [
            branch_entity,
            branch_topic,
            self._text(entity.get("active_entity")),
            self._text(task.get("candidate_answer")),
            self._text(task.get("topic")),
            self._text(topic.get("topic")),
            self._text(relation.get("previous_april_turn")),
            self._text(relation.get("previous_user_turn")),
        ]
        candidates = [x for x in dict.fromkeys(candidates) if x]

        resolved = candidates[0] if eligible and candidates else ""
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "reference_present": bool(signals),
            "reference_signals": signals,
            "eligible_for_resolution": eligible,
            "resolved_reference": resolved[:180],
            "candidate_antecedents": candidates[:10],
            "branch_target": {
                "branch_id": self._text(branch_index.get("target_branch_id")),
                "sequence_id": self._text(branch_index.get("target_sequence_id")),
                "topic": branch_topic,
                "entity": branch_entity,
            },
            "resolution_policy": (
                "active_task_then_current_topic_then_immediate_pair"
                if eligible else "no_reference_resolution"
            ),
            "confidence": 0.88 if resolved and signals else 0.72 if eligible and resolved else 0.35,
        }


class MemoryRelevanceEngine(InterpretationEngineBase):
    NAME = "MemoryRelevanceEngine"
    VERSION = "memory_relevance_v3"
    SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60
    MAX_ITEMS = 6

    def _timestamp(self, value: Any) -> float | None:
        if value in (None, "", 0, 0.0):
            return None
        try:
            if isinstance(value, (int, float)):
                return float(value)
            text = str(value).replace("Z", "+00:00")
            from datetime import datetime
            return datetime.fromisoformat(text).timestamp()
        except Exception:
            return None

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        topic: dict[str, Any],
        identity: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        now = time.time()
        scope = identity.get("scope", {})
        memory_raw = state.get("memory_timeline", {})
        values: list[Any] = []
        if isinstance(memory_raw, dict):
            for value in memory_raw.values():
                values.extend(value if isinstance(value, list) else [value])
        elif isinstance(memory_raw, list):
            values = list(memory_raw)

        relation_value = self._text(relation.get("relation")).upper()
        # Generic continuation is served by the immediate authenticated dialogue
        # pair; only explicit RECALL may pull 7-day historical memory.
        allowed = relation_value == "RECALL"

        selected: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        query = self._text(text)
        query_topic = self._text(topic.get("topic"))
        current_sequence_id = self._text(scope.get("dialogue_sequence_id"))
        current_scene = state.get("active_visual_scene") if isinstance(state.get("active_visual_scene"), dict) else (
            state.get("current_visual_scene") if isinstance(state.get("current_visual_scene"), dict) else {}
        )
        current_scene_id = self._text(current_scene.get("scene_id")) if isinstance(current_scene, dict) else ""
        for item in reversed(values):
            if not isinstance(item, dict):
                continue
            item_user = self._text(item.get("user_id"))
            item_conv = self._text(item.get("conversation_id"))
            if scope.get("user_id") and item_user and item_user != scope["user_id"]:
                continue
            if scope.get("conversation_id") and item_conv and item_conv != scope["conversation_id"]:
                continue

            stamp = self._timestamp(item.get("created_at") or item.get("timestamp") or item.get("updated_at"))
            if stamp is not None and now - stamp > self.SEVEN_DAYS_SECONDS:
                continue

            item_sequence_id = self._text(item.get("sequence_id") or item.get("dialogue_sequence_id"))
            item_scene_id = self._text(item.get("scene_id") or item.get("visual_scene_id"))
            same_sequence = bool(current_sequence_id and item_sequence_id and item_sequence_id == current_sequence_id)
            same_scene = bool(current_scene_id and item_scene_id and item_scene_id == current_scene_id)

            # Continuation must stay inside the authenticated active branch. A 7-day
            # record from the same user/conversation but another sequence is historical
            # evidence, not continuation context. Explicit RECALL may cross branches.
            if relation_value == "CONTINUE" and current_sequence_id and not (same_sequence or same_scene):
                continue

            content = self._text(
                item.get("summary")
                or item.get("content")
                or item.get("text")
                or item.get("answer")
                or item.get("user_request")
            )
            if not content:
                continue

            score = max(self._sim(query, content), self._sim(query_topic, content))
            if same_sequence:
                score += 0.18
            if same_scene:
                score += 0.10
            candidates.append({
                "item": dict(item),
                "score": round(float(min(1.0, score)), 4),
                "age_seconds": round(max(0.0, now - stamp), 2) if stamp is not None else None,
                "same_sequence": same_sequence,
                "same_scene": same_scene,
            })

        if relation_value == "NEW":
            selected = []
            allowed = False
        elif relation_value == "RECALL":
            ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)
            selected = [x["item"] for x in ranked if x["score"] >= 0.15][: self.MAX_ITEMS]
        else:
            # Continuation can use same-branch support only. Prefer active sequence
            # evidence and never promote another topic branch into the active owner.
            ranked = sorted(candidates, key=lambda x: (x["same_sequence"], x["same_scene"], x["score"]), reverse=True)
            selected = [
                x["item"] for x in ranked
                if (x["same_sequence"] or x["same_scene"]) and x["score"] >= 0.25
            ][: self.MAX_ITEMS]

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "seven_day_window_seconds": self.SEVEN_DAYS_SECONDS,
            "allowed": bool(allowed),
            "selection_mode": "explicit_recall" if relation_value == "RECALL" else "same_authenticated_branch" if allowed else "excluded",
            "selected": selected,
            "same_sequence_required_for_continuation": bool(relation_value == "CONTINUE" and current_sequence_id),
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "historical_memory_is_evidence_only": True,
            "cross_user_blocked": True,
            "confidence": 0.96 if relation.get("relation") == "RECALL" else 0.90 if selected else 0.78 if not allowed else 0.62,
        }


class DialogueHistorySearchEngine(InterpretationEngineBase):
    """Fast semantic retrieval over the authenticated dialogue branch.

    This is deliberately not another language model.  It builds a lightweight
    in-memory index from recent dialogue + same-sequence memory, then resolves
    multi-turn dependencies (especially "answer/result" references) before the
    provider receives its compact context plan.

    The important distinction is between the *latest assistant message* and the
    *latest result of the active task*.  A follow-up such as "Так сколько?"
    must retrieve the result of the preceding operation instead of treating the
    preceding scalar as a new operand.
    """

    NAME = "DialogueHistorySearchEngine"
    VERSION = "dialogue_history_search_v2_branch_fenced"
    MAX_INDEX_TURNS = 48
    MAX_SELECTED = 5
    MAX_MEMORY_SELECTED = 8

    _REFERENCE_MARKERS = (
        "ответ", "ответа", "ответу", "ответом", "результат", "результата",
        "получен", "полученного", "получилось", "получится", "полученого",
        "сумм", "от него", "от этого", "из этого", "это число", "тот ответ",
        "этот ответ", "как я просил", "я задавал", "спрашивал", "просил",
        "посмотри", "просмотри", "в истории", "раньше", "до этого",
        "как ты себя", "как ты описала", "как ты описывала", "по твоему описанию",
        "из нашего диалога", "из предыдущего диалога", "ту картинку", "эту картинку",
    )
    _FOLLOWUP_MARKERS = (
        "так сколько", "ну сколько", "и сколько", "сколько получилось",
        "сколько получится", "что получилось", "что получилось?", "какой ответ",
        "какой результат", "ну и сколько", "и что получилось", "сколько?",
    )
    _HISTORY_LOOKUP_MARKERS = (
        "я задавал", "я спрашивал", "какой вопрос", "какой был вопрос",
        "какой был ответ", "что я спрашивал", "что мы обсуждали", "что обсуждали",
        "вспомни", "напомни", "о чём мы говорили", "о чем мы говорили",
        "из памяти", "вернись к теме",
        "просмотри", "посмотри историю", "в истории", "раньше спрашивал",
    )
    _RECALL_STOPWORDS = {
        "вспомни", "напомни", "говорили", "обсуждали", "обсудили", "раньше",
        "прошлый", "прошлую", "прошлое", "диалог", "разговор", "тема",
        "том", "той", "тот", "это", "мы", "я", "ты", "про", "об", "о",
        "по", "к", "ко", "из", "от", "насчёт", "насчет", "что", "чем",
        "как", "где", "когда", "какой", "какая", "какое", "какие",
    }

    @classmethod
    def _recall_terms(cls, value: Any) -> set[str]:
        terms = set(cls._tokens(value))
        normalized = {token.replace("ё", "е") for token in terms}
        stop = {token.replace("ё", "е") for token in cls._RECALL_STOPWORDS}
        out = normalized - stop
        expanded = set(out)
        for token in list(out):
            for suffix in (
                "иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими",
                "ов", "ев", "ей", "ой", "ах", "ях", "ам", "ям", "ом", "ем",
                "ым", "им", "ою", "ею", "ую", "юю", "ая", "яя", "ое", "ее",
                "ые", "ие", "ы", "и", "а", "я", "у", "ю", "о", "е", "ь",
            ):
                if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                    expanded.add(token[:-len(suffix)])
                    break
        return expanded

    _OPERATION_PATTERNS = (
        ("subtract", ("вычти", "вычесть", "отними", "отнять", "минус")),
        ("add", ("прибавь", "прибавить", "добавь", "сложи", "плюс")),
        ("multiply", ("умножь", "умножить", "умножение", "на сколько")),
        ("divide", ("раздели", "разделить", "делением", "подели")),
    )

    @classmethod
    def _numbers(cls, value: Any) -> list[str]:
        text = cls._text(value).replace("−", "-").replace("–", "-")
        return re.findall(r"-?\d+(?:[.,]\d+)?", text)

    @classmethod
    def _arithmetic_expression(cls, value: Any) -> bool:
        text = cls._text(value).replace("−", "-")
        return bool(re.search(r"\d+\s*[+\-*/×x]\s*\d+", text))

    @classmethod
    def _result_value(cls, answer: Any, *, user_request: Any = "") -> str:
        text = cls._text(answer).replace("−", "-").replace("–", "-")
        if not text:
            return ""

        patterns = (
            r"(?:=|равн(?:о|яется)|получ(?:ается|ится)|итого|ответ(?:\s+равен)?)\s*([-+]?\d+(?:[.,]\d+)?)\s*\.?$",
            r"(?:=|равн(?:о|яется)|получ(?:ается|ится)|итого|ответ(?:\s+равен)?)\s*([-+]?\d+(?:[.,]\d+)?)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)

        # A scalar-only answer is safe to treat as the result when the user turn
        # itself is a calculation/operation request.
        if cls._arithmetic_expression(user_request) or any(
            needle in cls._low(user_request) for _, needles in cls._OPERATION_PATTERNS for needle in needles
        ):
            scalar = re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?\.?", text)
            if scalar:
                return scalar.group(0).rstrip(".")
            numbers = cls._numbers(text)
            if numbers:
                return numbers[-1]
        return ""

    @classmethod
    def _operation(cls, value: Any) -> dict[str, Any]:
        low = cls._low(value)
        for name, needles in cls._OPERATION_PATTERNS:
            matched = [x for x in needles if x in low]
            if matched:
                amount = ""
                nums = cls._numbers(value)
                if nums:
                    amount = nums[-1]
                return {"kind": name, "matched": matched[:3], "amount": amount}
        if cls._arithmetic_expression(value):
            return {"kind": "calculate", "matched": ["arithmetic_expression"], "amount": ""}
        return {"kind": "", "matched": [], "amount": ""}

    @classmethod
    def _reference_kind(cls, value: Any) -> str:
        low = cls._low(value)
        if any(marker in low for marker in cls._HISTORY_LOOKUP_MARKERS):
            return "history_lookup"

        # A concrete operation such as "вычти ... от ответа" is a new
        # dependent operation, not a pure request to repeat the last result.
        # Check the operation before generic "получилось/сколько" follow-up
        # markers so the searcher cannot accidentally re-apply or carry a
        # result while the user is explicitly asking for a new calculation.
        operation = cls._operation(low)
        if operation.get("kind"):
            if any(marker in low for marker in cls._REFERENCE_MARKERS):
                return "answer_reference"
            return "none"

        if any(marker in low for marker in cls._FOLLOWUP_MARKERS):
            return "result_followup"
        if any(marker in low for marker in cls._REFERENCE_MARKERS):
            return "answer_reference"
        return "none"

    @classmethod
    def _sequence_id(cls, item: dict[str, Any]) -> str:
        return cls._text(item.get("sequence_id") or item.get("dialogue_sequence_id"))

    @classmethod
    def _scene_id(cls, item: dict[str, Any]) -> str:
        return cls._text(item.get("scene_id") or item.get("visual_scene_id"))

    @classmethod
    def _normalize_history(cls, history: Any) -> list[dict[str, Any]]:
        """Normalize transport history into complete USER↔APRIL dialogue turns.

        The runtime hot history stores USER and APRIL as adjacent messages.  For
        recall/continuation we must reunite those two messages before semantic
        scoring so the assistant's answer (and its visual attachment) cannot be
        lost merely because transport is message-oriented.
        """
        turns = history if isinstance(history, list) else []
        out: list[dict[str, Any]] = []
        pending_user: dict[str, Any] | None = None

        def _visual_from_message(item: dict[str, Any]) -> dict[str, Any]:
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            value = item.get("visual_attachment")
            if not isinstance(value, dict):
                value = metadata.get("visual_attachment")
            return deepcopy(value) if isinstance(value, dict) else {}

        def _append_user_only(item: dict[str, Any]) -> None:
            nonlocal pending_user
            user_text = cls._text(item.get("content") or item.get("text") or item.get("user_request"))
            if not user_text:
                return
            pending_user = {
                "user": user_text,
                "assistant": "",
                "turn_id": item.get("turn_id"),
                "raw_user": item,
                "visual_attachment": _visual_from_message(item),
            }

        def _append_assistant_only(item: dict[str, Any]) -> None:
            assistant_text = cls._text(item.get("answer") or item.get("content") or item.get("summary") or item.get("text"))
            if not assistant_text:
                return
            out.append({
                "user": "",
                "assistant": assistant_text,
                "turn_id": item.get("turn_id"),
                "raw": item,
                "visual_attachment": _visual_from_message(item),
            })

        def _flush_pending() -> None:
            nonlocal pending_user
            if pending_user:
                out.append({
                    "user": pending_user.get("user", ""),
                    "assistant": pending_user.get("assistant", ""),
                    "turn_id": pending_user.get("turn_id"),
                    "raw": pending_user.get("raw_user") or {},
                    "visual_attachment": deepcopy(pending_user.get("visual_attachment") or {}),
                })
                pending_user = None

        for item in turns:
            if not isinstance(item, dict):
                continue

            # Explicit pair-shaped records are already complete turns.
            if item.get("user") not in (None, "") or item.get("april") not in (None, "") or item.get("assistant") not in (None, ""):
                explicit_user = item.get("user")
                explicit_april = item.get("april") or item.get("assistant")
                if isinstance(explicit_user, dict):
                    explicit_user = explicit_user.get("text") or explicit_user.get("content") or explicit_user.get("answer") or explicit_user.get("user_request")
                if isinstance(explicit_april, dict):
                    explicit_april = explicit_april.get("answer") or explicit_april.get("content") or explicit_april.get("summary") or explicit_april.get("april_answer")
                explicit_user = cls._text(explicit_user)
                explicit_april = cls._text(explicit_april)
                if explicit_user or explicit_april:
                    _flush_pending()
                    visual = item.get("visual_attachment") if isinstance(item.get("visual_attachment"), dict) else {}
                    out.append({
                        "user": explicit_user,
                        "assistant": explicit_april,
                        "turn_id": item.get("turn_id"),
                        "raw": item,
                        "visual_attachment": deepcopy(visual),
                    })
                    continue

            role = str(item.get("role") or "").lower().strip()
            if role in {"user", "human"}:
                if pending_user:
                    _flush_pending()
                _append_user_only(item)
                continue

            if role in {"assistant", "april", "bot"}:
                assistant_text = cls._text(item.get("answer") or item.get("content") or item.get("summary") or item.get("text"))
                if pending_user and assistant_text:
                    visual = _visual_from_message(item) or pending_user.get("visual_attachment") or {}
                    out.append({
                        "user": pending_user.get("user", ""),
                        "assistant": assistant_text,
                        "turn_id": item.get("turn_id") or pending_user.get("turn_id"),
                        "raw": item,
                        "visual_attachment": deepcopy(visual),
                    })
                    pending_user = None
                else:
                    _append_assistant_only(item)
                continue

            # Legacy shape: tolerate user_request/april_answer without a role.
            if item.get("user_request") not in (None, "") or item.get("april_answer") not in (None, ""):
                _flush_pending()
                out.append({
                    "user": cls._text(item.get("user_request")),
                    "assistant": cls._text(item.get("april_answer")),
                    "turn_id": item.get("turn_id"),
                    "raw": item,
                    "visual_attachment": deepcopy(item.get("visual_attachment") or {}) if isinstance(item.get("visual_attachment"), dict) else {},
                })

        _flush_pending()
        return out

    @classmethod
    def _record_from_pair(
        cls,
        pair: dict[str, Any],
        *,
        index: int,
        source: str,
        sequence_id: str = "",
        scene_id: str = "",
    ) -> dict[str, Any]:
        user = cls._text(pair.get("user"))
        assistant = cls._text(pair.get("assistant"))
        raw = pair.get("raw") if isinstance(pair.get("raw"), dict) else {}
        seq = cls._sequence_id(raw) or sequence_id
        scene = cls._scene_id(raw) or scene_id
        result = cls._result_value(assistant, user_request=user)
        visual_attachment = pair.get("visual_attachment") if isinstance(pair.get("visual_attachment"), dict) else {}
        if not visual_attachment and isinstance(raw.get("visual_attachment"), dict):
            visual_attachment = raw.get("visual_attachment")
        anchor = raw.get("semantic_anchor") if isinstance(raw.get("semantic_anchor"), dict) else {}
        return {
            "index": index,
            "source": source,
            "user": user,
            "assistant": assistant,
            "result": result,
            "visual_attachment": deepcopy(visual_attachment),
            "operation": cls._operation(user),
            "sequence_id": seq,
            "scene_id": scene,
            "turn_id": raw.get("turn_id") or pair.get("turn_id"),
            "semantic_anchor": deepcopy(anchor),
            "raw": deepcopy(raw),
            "topic": cls._text(
                anchor.get("topic_root")
                or raw.get("topic")
                or raw.get("sequence_topic")
            ),
            "entity": cls._text(
                anchor.get("primary_entity")
                or raw.get("active_entity")
                or raw.get("entity")
            ),
            "focus": cls._text(anchor.get("active_focus") or raw.get("focus")),
            "direction": cls._text(anchor.get("direction") or raw.get("direction")),
        }

    @classmethod
    def _timeline_records(
        cls,
        state: dict[str, Any],
        identity: dict[str, Any],
        history: list[Any],
        relation: str = "CONTINUE",
    ) -> list[dict[str, Any]]:
        scope = identity.get("scope", {}) if isinstance(identity, dict) else {}
        sequence = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        sequence_id = cls._text(sequence.get("sequence_id") or scope.get("dialogue_sequence_id"))
        scene = state.get("active_visual_scene") if isinstance(state.get("active_visual_scene"), dict) else (
            state.get("current_visual_scene") if isinstance(state.get("current_visual_scene"), dict) else {}
        )
        scene_id = cls._scene_id(scene)

        records: list[dict[str, Any]] = []
        normalized = cls._normalize_history(history)
        for idx, pair in enumerate(normalized[-cls.MAX_INDEX_TURNS:]):
            records.append(
                cls._record_from_pair(
                    pair, index=idx, source="dialogue_history", sequence_id=sequence_id, scene_id=scene_id
                )
            )

        # Same authenticated sequence records can exist in seven-day memory even
        # when the transport history contains only a short recent window. The
        # canonical state schema stores these records inside day_0..day_6 buckets,
        # so flatten the bucket lists explicitly instead of treating each day
        # dictionary as one dialogue record.
        memory_raw = state.get("memory_timeline", {})
        memory_records: list[dict[str, Any]] = []
        if isinstance(memory_raw, dict):
            day_items = []
            for day_index in range(7):
                day = memory_raw.get(f"day_{day_index}")
                if not isinstance(day, dict):
                    continue
                for field in ("dialog_pairs", "visual_scenes", "topics", "intent_signals", "objects", "A", "B", "C", "D", "E"):
                    values = day.get(field)
                    if not isinstance(values, list):
                        continue
                    for value in values:
                        if isinstance(value, dict):
                            item = dict(value)
                            item["_memory_day_index"] = day_index
                            item["_memory_field"] = field
                            day_items.append(item)
            memory_records = day_items
        elif isinstance(memory_raw, list):
            memory_records = [dict(x) for x in memory_raw if isinstance(x, dict)]

        base = len(records)
        # Preserve chronological order in the underlying timeline. Slider/recall
        # logic may request RECALL to see cross-branch records; normal CONTINUE
        # history remains branch-fenced by _branch_records below.
        memory_records.sort(
            key=lambda item: (
                float(item.get("created_at") or item.get("timestamp") or 0.0),
                int(item.get("sequence_turn_index") or 0),
                int(item.get("_memory_day_index") or 0),
            )
        )
        for offset, item in enumerate(memory_records[-cls.MAX_INDEX_TURNS:]):
            if scope.get("user_id") and item.get("user_id") and str(item.get("user_id")) != str(scope.get("user_id")):
                continue
            if scope.get("conversation_id") and item.get("conversation_id") and str(item.get("conversation_id")) != str(scope.get("conversation_id")):
                continue
            item_seq = cls._sequence_id(item)
            if relation != "RECALL" and sequence_id and item_seq and item_seq != sequence_id:
                continue
            user = cls._text(item.get("user_request") or item.get("user_meaning") or item.get("user") or item.get("text"))
            assistant = cls._text(
                item.get("april_answer")
                or item.get("april_meaning")
                or item.get("answer_summary")
                or item.get("answer")
                or item.get("assistant")
                or item.get("summary")
            )
            if not user and not assistant:
                continue
            pair = {
                "user": user,
                "assistant": assistant,
                "raw": item,
                "turn_id": item.get("turn_id"),
                "visual_attachment": deepcopy(item.get("visual_attachment") or {}),
            }
            records.append(
                cls._record_from_pair(
                    pair,
                    index=base + offset,
                    source="same_sequence_memory",
                    sequence_id=item_seq or sequence_id,
                    scene_id=cls._scene_id(item) or scene_id,
                )
            )


        # A compact active-sequence snapshot can contain the prior pair even if
        # neither history nor memory_timeline carries it verbatim.
        if sequence:
            user = cls._text(sequence.get("last_user_request"))
            assistant = cls._text(sequence.get("last_april_answer"))
            if user or assistant:
                records.append(
                    cls._record_from_pair(
                        {"user": user, "assistant": assistant, "raw": sequence},
                        index=len(records), source="active_sequence", sequence_id=sequence_id, scene_id=scene_id,
                    )
                )

        if scene:
            user = cls._text(scene.get("last_user_turn") or scene.get("user_request"))
            assistant = cls._text(scene.get("last_april_turn") or scene.get("april_answer") or scene.get("answer"))
            if user or assistant:
                records.append(
                    cls._record_from_pair(
                        {"user": user, "assistant": assistant, "raw": scene},
                        index=len(records), source="active_scene", sequence_id=sequence_id, scene_id=scene_id,
                    )
                )

        # De-duplicate repeated snapshots while retaining the newest source.
        # Some state snapshots do not carry turn_id, so content is part of the
        # identity. This prevents active_sequence/scene snapshots from creating
        # phantom duplicate operations in the result ledger.
        dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
        for record in records:
            user_key = cls._low(record.get("user"))
            assistant_key = cls._low(record.get("assistant"))
            turn_key = cls._text(record.get("turn_id"))
            if not user_key and not assistant_key:
                continue
            key = (user_key, assistant_key, turn_key)
            if turn_key:
                dedup[key] = record
                continue

            # Without a turn id, collapse identical user↔assistant pairs across
            # history/memory/active-scene snapshots. Prefer the newest appended
            # source, which is the most complete snapshot.
            fallback_key = (user_key, assistant_key, "")
            dedup[fallback_key] = record
        return list(dedup.values())[-cls.MAX_INDEX_TURNS:]

    @classmethod
    def _score_record(
        cls,
        query: str,
        record: dict[str, Any],
        *,
        scope: dict[str, Any],
        relation: str,
        query_reference: str,
        query_numbers: set[str],
        recency_rank: int,
    ) -> float:
        user = cls._text(record.get("user"))
        assistant = cls._text(record.get("assistant"))
        semantic_parts = [
            cls._text(record.get("topic")),
            cls._text(record.get("entity")),
            cls._text(record.get("focus")),
            cls._text(record.get("direction")),
        ]
        combined = " ".join(x for x in [user, assistant, *semantic_parts] if x)
        score = 0.0
        score += min(0.40, 0.40 * cls._sim(query, combined))
        score += min(0.22, 0.22 * cls._sim(query, user))
        if record.get("topic"):
            score += min(0.16, 0.16 * cls._sim(query, record.get("topic")))
        if record.get("entity"):
            score += min(0.08, 0.08 * cls._sim(query, record.get("entity")))

        if relation == "RECALL":
            q_terms = cls._recall_terms(query)
            topic_terms = cls._recall_terms(record.get("topic"))
            entity_terms = cls._recall_terms(record.get("entity"))
            exact_topic = bool(q_terms and topic_terms and q_terms & topic_terms)
            exact_entity = bool(q_terms and entity_terms and q_terms & entity_terms)
            if exact_topic:
                score += 0.38
            elif exact_entity:
                score += 0.28
            elif q_terms and record.get("topic"):
                score -= 0.06

        current_seq = cls._text(scope.get("dialogue_sequence_id"))
        record_seq = cls._text(record.get("sequence_id"))
        if relation == "CONTINUE" and current_seq and record_seq == current_seq:
            score += 0.24

        if query_reference in {"answer_reference", "result_followup"} and assistant:
            score += 0.12
        if query_reference == "history_lookup" and user:
            score += 0.14

        record_numbers = set(cls._numbers(combined))
        if query_numbers and record_numbers & query_numbers:
            score += 0.08
        if record.get("result") and query_reference in {"answer_reference", "result_followup"}:
            score += 0.12
        operation = record.get("operation") if isinstance(record.get("operation"), dict) else {}
        if operation.get("kind") and query_reference in {"answer_reference", "result_followup"}:
            score += 0.10

        score += max(0.0, 0.08 - recency_rank * 0.006)
        return float(min(1.0, score))

    @classmethod
    def _branch_records(
        cls,
        records: list[dict[str, Any]],
        *,
        scope: dict[str, Any],
        relation: str,
    ) -> list[dict[str, Any]]:
        current_seq = cls._text(scope.get("dialogue_sequence_id"))
        if relation == "CONTINUE" and current_seq:
            same = [r for r in records if cls._text(r.get("sequence_id")) == current_seq]
            if same:
                return same
        return records

    @classmethod
    def _result_chain(cls, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        chain: list[dict[str, Any]] = []
        previous_result = ""
        previous_record: dict[str, Any] | None = None
        for record in records:
            user = cls._text(record.get("user"))
            assistant = cls._text(record.get("assistant"))
            operation = record.get("operation") if isinstance(record.get("operation"), dict) else {}
            result = cls._text(record.get("result"))
            if operation.get("kind") or result or cls._arithmetic_expression(user):
                target = ""
                if operation.get("kind") and any(marker in cls._low(user) for marker in cls._REFERENCE_MARKERS):
                    target = previous_result
                chain.append({
                    "user_request": user,
                    "assistant_answer": assistant,
                    "operation": operation.get("kind") or "",
                    "operation_amount": operation.get("amount") or "",
                    "target_result": target,
                    "result": result,
                    "turn_id": record.get("turn_id"),
                })
            if result:
                previous_result = result
            if user or assistant:
                previous_record = record
        return chain[-10:]

    @classmethod
    def _latest_operation_result(cls, branch: list[dict[str, Any]]) -> dict[str, Any]:
        for record in reversed(branch):
            operation = record.get("operation") if isinstance(record.get("operation"), dict) else {}
            result = cls._text(record.get("result"))
            if (operation.get("kind") or cls._arithmetic_expression(record.get("user"))) and result:
                return {
                    "value": result,
                    "user_request": cls._text(record.get("user")),
                    "assistant_answer": cls._text(record.get("assistant")),
                    "operation": operation.get("kind") or "calculate",
                    "operation_amount": operation.get("amount") or "",
                    "turn_id": record.get("turn_id"),
                }
        return {}

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        topic: dict[str, Any],
        identity: dict[str, Any],
        state: dict[str, Any],
        history: list[Any],
        task: dict[str, Any] | None = None,
        reference: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relation_value = self._text(relation.get("relation") or "NEW").upper()
        scope = identity.get("scope", {}) if isinstance(identity, dict) else {}
        query = self._text(text)
        query_reference = self._reference_kind(query)
        query_numbers = set(self._numbers(query))

        records = self._timeline_records(state, identity, history, relation=relation_value)
        branch = self._branch_records(records, scope=scope, relation=relation_value)

        ranked = []
        total = len(branch)
        for recency_rank, record in enumerate(reversed(branch)):
            ranked.append({
                "record": record,
                "score": round(self._score_record(
                    query,
                    record,
                    scope=scope,
                    relation=relation_value,
                    query_reference=query_reference,
                    query_numbers=query_numbers,
                    recency_rank=recency_rank,
                ), 4),
            })
        ranked.sort(key=lambda x: x["score"], reverse=True)

        if relation_value == "NEW" and query_reference != "history_lookup":
            selected = []
        elif query_reference == "history_lookup":
            selected = [x for x in ranked if x["score"] >= 0.16][: self.MAX_SELECTED]
        elif relation_value == "RECALL":
            selected = [x for x in ranked if x["score"] >= 0.10][: self.MAX_SELECTED]
        elif query_reference in {"answer_reference", "result_followup"}:
            selected = [x for x in ranked if x["score"] >= 0.14][: self.MAX_SELECTED]
        else:
            selected = [x for x in ranked if x["score"] >= 0.28][:3]

        latest_operation_result = self._latest_operation_result(branch)
        carry_forward: dict[str, Any] = {}
        if relation_value == "CONTINUE" and query_reference == "result_followup" and latest_operation_result:
            carry_forward = {
                **latest_operation_result,
                "do_not_reapply_previous_operation": True,
                "reason": "pure_followup_requests_last_derived_result",
            }

        # For a new dependent operation, bind the referenced operand to the
        # previously obtained result, not blindly to the immediately prior scalar.
        operand_anchor: dict[str, Any] = {}
        operation = self._operation(query)
        if relation_value == "CONTINUE" and operation.get("kind") and any(
            marker in self._low(query) for marker in self._REFERENCE_MARKERS
        ):
            previous_result = ""
            previous_record = None
            for record in reversed(branch):
                result = self._text(record.get("result"))
                if result:
                    previous_result = result
                    previous_record = record
                    break
            if previous_result:
                operand_anchor = {
                    "value": previous_result,
                    "source_user_request": self._text((previous_record or {}).get("user")),
                    "source_assistant_answer": self._text((previous_record or {}).get("assistant")),
                    "operation": operation.get("kind"),
                    "operation_amount": operation.get("amount"),
                    "reference": "previous_result",
                    "reason": "current_operation_explicitly_references_prior_answer",
                }

        result_chain = self._result_chain(branch)
        selected_evidence = []
        for item in selected:
            record = item["record"]
            selected_evidence.append({
                "score": item["score"],
                "source": record.get("source"),
                "turn_id": record.get("turn_id"),
                "sequence_id": record.get("sequence_id"),
                "user": self._text(record.get("user")),
                "assistant": self._text(record.get("assistant")),
                "result": self._text(record.get("result")),
                "operation": record.get("operation") or {},
                "topic": self._text(record.get("topic")),
                "entity": self._text(record.get("entity")),
                "focus": self._text(record.get("focus")),
                "direction": self._text(record.get("direction")),
                "semantic_anchor": deepcopy(record.get("semantic_anchor") if isinstance(record.get("semantic_anchor"), dict) else {}),
                "visual_attachment": deepcopy(record.get("visual_attachment") or {}),
            })

        # A normal conversational continuation needs no result/history ledger.
        # Keeping it out prevents old arithmetic/result chains from contaminating
        # an unrelated semantic thread.
        if relation_value == "CONTINUE" and query_reference == "none" and not carry_forward and not operand_anchor:
            selected_evidence = []
            result_chain = []
            latest_operation_result = {}

        needs_history = (
            query_reference == "history_lookup"
            or relation_value in {"CONTINUE", "RECALL"} and bool(
                query_reference != "none" or carry_forward or operand_anchor or selected_evidence
            )
        )
        if relation_value == "CONTINUE" and latest_operation_result and query_reference == "result_followup":
            needs_history = True

        recommended = ""
        if carry_forward:
            recommended = "RESULT_FOLLOWUP"
        elif operand_anchor:
            recommended = "DEPENDENT_OPERATION"
        elif query_reference == "history_lookup":
            recommended = "HISTORY_LOOKUP"
        elif selected_evidence:
            recommended = "HISTORY_SUPPORTED_CONTINUATION"

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "relation": relation_value,
            "query": query,
            "query_kind": query_reference,
            "authenticated_scope": {
                "user_id": self._text(scope.get("user_id")),
                "conversation_id": self._text(scope.get("conversation_id")),
                "dialogue_sequence_id": self._text(scope.get("dialogue_sequence_id")),
            },
            "index_size": total,
            "selected_count": len(selected_evidence),
            "selected_evidence": selected_evidence,
            "result_chain": result_chain,
            "latest_operation_result": latest_operation_result,
            "operand_anchor": operand_anchor,
            "carry_forward_result": carry_forward,
            "history_context_required": needs_history,
            "same_authenticated_branch_first": relation_value == "CONTINUE",
            "seven_day_cross_branch_allowed": relation_value == "RECALL",
            "semantic_slider_cross_branch_allowed": relation_value in {"CONTINUE", "RECALL"},
            "memory_slider_enabled": relation_value in {"CONTINUE", "RECALL"},
            "historical_memory_is_evidence_only": True,
            "recommended_turn_relation": recommended,
            "provider_instruction": (
                "Use the carried result as the answer; do not reapply the preceding operation."
                if carry_forward else
                "Use the anchored prior result as the operand for the current operation."
                if operand_anchor else
                "Use only the selected dialogue-history evidence to resolve the current request."
                if needs_history else
                "No historical evidence is required for this turn."
            ),
            "confidence": round(
                0.97 if carry_forward or operand_anchor else
                0.92 if selected_evidence else
                0.80 if relation_value in {"CONTINUE", "RECALL"} else 0.98,
                4,
            ),
        }



class DialogueMemorySliderEngine(InterpretationEngineBase):
    """Sequential semantic slider over the authenticated seven-day dialogue.

    The slider is deliberately narrower than generic memory search:
      * NEW turns never invoke it.
      * CONTINUE/RECALL turns scan prior USER↔APRIL records chronologically.
      * Every candidate is measured by the same QuantumInterpretationEngine.
      * The first sufficiently related candidate becomes a semantic operand.
    """

    NAME = "DialogueMemorySliderEngine"
    VERSION = "dialogue_memory_slider_v1_sequential_semantic"
    MAX_SCAN = 48
    MAX_SELECTED = 4
    CONTINUE_THRESHOLD = 0.16
    RECALL_THRESHOLD = 0.12

    @staticmethod
    def _scope(identity: dict[str, Any], state: dict[str, Any]) -> dict[str, str]:
        scope = identity.get("scope") if isinstance(identity, dict) else {}
        scope = scope if isinstance(scope, dict) else {}
        user_id = str(scope.get("user_id") or state.get("user_id") or "").strip()
        conversation_id = str(
            scope.get("conversation_id") or state.get("conversation_id") or ""
        ).strip()
        sequence_id = str(
            scope.get("dialogue_sequence_id")
            or ((state.get("active_dialogue_sequence") or {}).get("sequence_id")
                if isinstance(state.get("active_dialogue_sequence"), dict) else "")
            or ""
        ).strip()
        return {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "dialogue_sequence_id": sequence_id,
        }

    @classmethod
    def _record_text(cls, record: dict[str, Any]) -> str:
        raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
        parts = (
            record.get("topic"),
            record.get("entity"),
            record.get("focus"),
            record.get("direction"),
            record.get("user"),
            record.get("assistant"),
            raw.get("sequence_topic"),
            raw.get("summary"),
            raw.get("user_meaning"),
            raw.get("april_meaning"),
            raw.get("answer_summary"),
        )
        return cls._text(" ".join(str(x) for x in parts if x))

    @staticmethod
    def _timestamp(record: dict[str, Any]) -> float:
        for key in ("created_at", "timestamp", "turn_timestamp", "updated_at"):
            try:
                value = float(record.get(key) or 0.0)
            except (TypeError, ValueError):
                continue
            if value:
                return value
        return 0.0

    @classmethod
    def _same_scope(cls, record: dict[str, Any], scope: dict[str, str]) -> bool:
        if scope.get("user_id") and record.get("user_id"):
            if str(record.get("user_id")) != scope["user_id"]:
                return False
        if scope.get("conversation_id") and record.get("conversation_id"):
            if str(record.get("conversation_id")) != scope["conversation_id"]:
                return False
        return True

    @classmethod
    def _operand(
        cls,
        record: dict[str, Any],
        *,
        score: float,
        position: int,
        semantic_relation: dict[str, Any],
        relation: str,
    ) -> dict[str, Any]:
        raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
        anchor = record.get("semantic_anchor") if isinstance(record.get("semantic_anchor"), dict) else {}
        obligations = (
            raw.get("dialogue_obligations")
            if isinstance(raw.get("dialogue_obligations"), list)
            else raw.get("obligations")
            if isinstance(raw.get("obligations"), list)
            else []
        )
        return {
            "source": "dialogue_memory_slider",
            "relation": relation,
            "memory_index": record.get("index", position),
            "slider_position": position,
            "score": round(float(score), 6),
            "sequence_id": cls._text(record.get("sequence_id") or raw.get("sequence_id")),
            "scene_id": cls._text(record.get("scene_id") or raw.get("scene_id")),
            "turn_id": record.get("turn_id") or raw.get("turn_id"),
            "topic": cls._text(anchor.get("topic_root") or record.get("topic") or raw.get("topic") or raw.get("sequence_topic")),
            "entity": cls._text(anchor.get("primary_entity") or record.get("entity") or raw.get("active_entity") or raw.get("entity")),
            "focus": cls._text(anchor.get("active_focus") or record.get("focus") or raw.get("active_focus") or raw.get("focus")),
            "direction": cls._text(anchor.get("direction") or record.get("direction") or raw.get("direction")),
            "goal": cls._text(anchor.get("goal") or raw.get("goal")),
            "user_request": cls._text(record.get("user") or raw.get("user_request") or raw.get("user")),
            "april_answer": cls._text(record.get("assistant") or raw.get("april_answer") or raw.get("assistant") or raw.get("answer") or raw.get("summary")),
            "summary": cls._text(raw.get("summary") or raw.get("answer_summary") or record.get("assistant")),
            "semantic_anchor": deepcopy(anchor),
            "dialogue_obligations": deepcopy(obligations[-8:]),
            "semantic_relation": deepcopy(semantic_relation),
            "created_at": cls._timestamp(record),
        }

    def scan(
        self,
        text: str,
        *,
        relation: str,
        identity: dict[str, Any],
        state: dict[str, Any],
        history: list[Any],
        active_topic: str = "",
        active_entity: str = "",
        active_goal: str = "",
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        relation_value = self._text(relation or "NEW").upper()
        query = self._text(text)
        result: dict[str, Any] = {
            "version": self.VERSION,
            "enabled": relation_value in {"CONTINUE", "RECALL"} and bool(query),
            "relation": relation_value,
            "query": query,
            "scanned": 0,
            "selected": [],
            "selected_memory_index": -1,
            "selected_memory_record": {},
            "selected_memory_operand": {},
            "reason": "new_vector" if relation_value == "NEW" else "no_match",
            "selection_mode": "disabled",
        }
        if relation_value not in {"CONTINUE", "RECALL"}:
            return result
        if not query:
            result["reason"] = "empty_request"
            return result

        scope = self._scope(identity, state)
        try:
            # RECALL mode exposes all seven-day dialogue records to the slider.
            # This is still authenticated/scope-filtered below. The slider itself
            # decides relevance; provider never searches the raw timeline.
            records = DialogueHistorySearchEngine._timeline_records(
                state,
                identity,
                history,
                relation="RECALL",
            )
        except Exception as exc:
            result["reason"] = "timeline_read_error"
            result["error"] = str(exc)
            return result

        # De-duplicate by concrete dialogue identity so the same pair from hot
        # history + day_0 memory does not count twice.
        deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
        for record in records:
            if not isinstance(record, dict) or not self._same_scope(record, scope):
                continue
            key = (
                record.get("turn_id"),
                record.get("sequence_id"),
                self._text(record.get("user")),
                self._text(record.get("assistant")),
                record.get("scene_id"),
            )
            if key in deduped:
                # Prefer the richer memory record.
                previous = deduped[key]
                if len(self._record_text(record)) > len(self._record_text(previous)):
                    deduped[key] = record
            else:
                deduped[key] = record
        ordered = list(deduped.values())
        ordered.sort(
            key=lambda r: (
                self._timestamp(r),
                int(r.get("sequence_turn_index") or 0),
                int(r.get("turn_id") or 0) if str(r.get("turn_id") or "").isdigit() else 0,
                int(r.get("index") or 0),
            )
        )
        ordered = ordered[-self.MAX_SCAN:]

        candidates: list[dict[str, Any]] = []
        for position, record in enumerate(ordered):
            candidate_text = self._record_text(record)
            if not candidate_text:
                continue

            user_text = self._text(record.get("user"))
            assistant_text = self._text(record.get("assistant"))
            # _timeline_records can expose the active scene snapshot. It is the
            # current turn, not historical evidence, and must never be selected by
            # the slider as the answer to the question currently being processed.
            if user_text and user_text == query and not assistant_text:
                continue
            candidate_topic = self._text(record.get("topic"))
            candidate_entity = self._text(record.get("entity"))
            candidate_anchor = record.get("semantic_anchor") if isinstance(record.get("semantic_anchor"), dict) else {}
            candidate_topic = self._text(candidate_anchor.get("topic_root") or candidate_topic)
            candidate_entity = self._text(candidate_anchor.get("primary_entity") or candidate_entity)

            try:
                direct = QUANTUM_INTERPRETATION_ENGINE.similarity(query, candidate_text)
                measurement = QUANTUM_INTERPRETATION_ENGINE.measure(
                    query,
                    previous_assistant=assistant_text,
                    previous_user=user_text,
                    active_topic=candidate_topic or active_topic,
                    active_goal=active_goal,
                )
                relation_probe = QUANTUM_INTERPRETATION_ENGINE.dialogue(
                    query,
                    previous_assistant=assistant_text,
                    previous_user=user_text,
                    active_topic=candidate_topic or active_topic,
                    active_goal=active_goal,
                    open_task=task if isinstance(task, dict) else None,
                )
                topic_probe = QUANTUM_INTERPRETATION_ENGINE.similarity(
                    query, candidate_topic or active_topic or candidate_text
                )
                entity_probe = QUANTUM_INTERPRETATION_ENGINE.similarity(
                    query, candidate_entity or active_entity or candidate_text
                )
            except Exception as exc:
                # A single candidate must never break the entire dialogue turn.
                continue

            semantic = float(direct.get("score", 0.0) or 0.0)
            context_scores = measurement.get("context_scores") if isinstance(measurement, dict) else {}
            dialogue_scores = relation_probe.get("dialogue") if isinstance(relation_probe, dict) else {}
            prev_assistant = float(context_scores.get("previous_assistant", 0.0) or 0.0)
            prev_user = float(context_scores.get("previous_user", 0.0) or 0.0)
            topic_context = float(context_scores.get("active_topic", 0.0) or 0.0)
            continuation_probe = float(dialogue_scores.get("continuation_score", 0.0) or 0.0)
            reference_probe = float(dialogue_scores.get("reference_score", 0.0) or 0.0)
            same_sequence = bool(
                scope.get("dialogue_sequence_id")
                and self._text(record.get("sequence_id")) == scope["dialogue_sequence_id"]
            )
            substance = min(
                1.0,
                len(self._text(user_text).split()) / 12.0
                + len(self._text(assistant_text).split()) / 20.0,
            )

            # Interpretation-first score: the candidate is related when the same
            # semantic engine sees it as a contextual antecedent, not merely when
            # it shares a keyword.
            score = (
                0.34 * semantic
                + 0.18 * max(prev_assistant, prev_user, topic_context)
                + 0.16 * max(continuation_probe, reference_probe)
                + 0.12 * float(topic_probe.get("score", 0.0) or 0.0)
                + 0.08 * float(entity_probe.get("score", 0.0) or 0.0)
                + 0.06 * (1.0 if same_sequence else 0.0)
                + 0.06 * substance
            )
            if relation_value == "RECALL":
                # Recall can resolve an older branch; chronological order remains
                # the tie-breaker after semantic evidence.
                score += min(0.08, 0.08 * ((position + 1) / max(1, len(ordered))))
            elif same_sequence:
                score += 0.06

            threshold = (
                self.RECALL_THRESHOLD
                if relation_value == "RECALL"
                else self.CONTINUE_THRESHOLD
            )
            if score < threshold:
                continue

            candidates.append({
                "score": round(min(1.0, score), 6),
                "position": position,
                "record": record,
                "semantic_relation": relation_probe,
            })

        # The slider is sequential, not a global top-k search: scan old dialogue
        # in chronological order and stop at the first candidate that the same
        # interpretation engine recognizes as a valid antecedent.
        if not candidates:
            result["reason"] = "no_semantic_match"
            result["scanned"] = len(ordered)
            result["selection_mode"] = "enabled_no_match"
            return result

        candidates.sort(
            key=lambda item: (
                int(item["position"]),
                self._timestamp(item["record"]),
                int(item["record"].get("index") or 0),
            )
        )
        primary = candidates[0]
        selected = candidates[: self.MAX_SELECTED]
        primary_record = primary["record"]
        primary_operand = self._operand(
            primary_record,
            score=primary["score"],
            position=primary["position"],
            semantic_relation=primary["semantic_relation"],
            relation=relation_value,
        )
        selected_records = []
        for item in selected:
            rec = item["record"]
            selected_records.append({
                "score": item["score"],
                "position": item["position"],
                "memory_index": rec.get("index", item["position"]),
                "sequence_id": self._text(rec.get("sequence_id")),
                "turn_id": rec.get("turn_id"),
                "topic": self._text(rec.get("topic")),
                "entity": self._text(rec.get("entity")),
                "user": self._text(rec.get("user")),
                "assistant": self._text(rec.get("assistant")),
            })

        result.update({
            "scanned": len(ordered),
            "selected": selected_records,
            "selected_memory_index": primary_record.get("index", primary["position"]),
            "selected_memory_record": deepcopy(primary_record),
            "selected_memory_operand": primary_operand,
            "reason": "semantic_match",
            "selection_mode": "dialogue_memory_slider",
            "scan_order": "chronological",
            "stop_position": primary["position"],
            "same_sequence": bool(
                scope.get("dialogue_sequence_id")
                and self._text(primary_record.get("sequence_id")) == scope["dialogue_sequence_id"]
            ),
        })
        return result


class ConversationContinuityEngine(InterpretationEngineBase):
    NAME = "ConversationContinuityEngine"
    VERSION = "conversation_continuity_v3"

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        entity: dict[str, Any],
        reference: dict[str, Any],
        history_search: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        previous_user = self._text(relation.get("previous_user_turn"))
        previous_april = self._text(relation.get("previous_april_turn"))
        current = self._text(text)
        rel = relation.get("relation")
        history_search = history_search if isinstance(history_search, dict) else {}
        carry_forward = history_search.get("carry_forward_result") if isinstance(history_search.get("carry_forward_result"), dict) else {}
        operand_anchor = history_search.get("operand_anchor") if isinstance(history_search.get("operand_anchor"), dict) else {}
        result_chain = list(history_search.get("result_chain") or [])[-6:]
        covered = [previous_april] if previous_april and rel == "CONTINUE" else []

        if rel == "CONTINUE":
            if carry_forward:
                next_step = "return_last_derived_result_without_reapplying_previous_operation"
            elif operand_anchor:
                next_step = "apply_current_operation_to_anchored_prior_result"
            elif task.get("active"):
                next_step = {
                    "TASK_ANSWER": "evaluate_current_user_answer",
                    "TASK_CONFIRMATION": "acknowledge_and_advance",
                    "TASK_CORRECTION": "correct_and_advance",
                }.get(str(relation.get("turn_relation")), "advance_active_task")
            else:
                next_step = "answer_current_turn_and_advance"
            avoid_repeat = covered
        elif rel == "RECALL":
            next_step = "retrieve_requested_historical_topic_and_connect"
            avoid_repeat = []
        else:
            next_step = "develop_current_topic_from_scratch"
            avoid_repeat = []

        novelty = self._sim(current, previous_april)
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "relation": rel,
            "same_conversational_branch": rel == "CONTINUE",
            "previous_pair": {
                "user": previous_user,
                "april": previous_april,
                "visual_attachment": deepcopy(relation.get("previous_visual_attachment") or {}),
            },
            "covered_content": covered,
            "avoid_repeat_content": avoid_repeat,
            "history_search": {
                "query_kind": history_search.get("query_kind"),
                "selected_evidence": list(history_search.get("selected_evidence") or [])[:4],
                "carry_forward_result": carry_forward,
                "operand_anchor": operand_anchor,
                "result_chain": result_chain,
                "history_context_required": bool(history_search.get("history_context_required")),
            },
            "novelty_score": round(float(1.0 - novelty), 4),
            "next_logical_step": next_step,
            "acknowledge_memory_when_recalled": rel == "RECALL",
            "do_not_reintroduce_old_topics_on_new": rel == "NEW",
            "confidence": 0.94 if previous_april or task.get("active") else 0.70,
        }


class DialogueDevelopmentEngine(InterpretationEngineBase):
    """Keep one semantic trajectory for the authenticated dialogue."""
    NAME = "DialogueDevelopmentEngine"
    VERSION = "dialogue_development_v1_single_route"

    @classmethod
    def _compact_loop(cls, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        out = {
            "id": cls._text(item.get("id") or item.get("loop_id")),
            "topic": cls._text(item.get("topic") or item.get("goal") or item.get("description")),
            "status": cls._text(item.get("status") or "open"),
            "next_step": cls._text(item.get("next_step") or item.get("next_action")),
        }
        return {k:v for k,v in out.items() if v not in (None,"",[],{})}

    def analyze(self, text: str, *, state: dict[str, Any], relation: dict[str, Any],
                topic: dict[str, Any], task: dict[str, Any], entity: dict[str, Any],
                history_search: dict[str, Any], continuity: dict[str, Any],
                obligations: dict[str, Any], visual_memory: dict[str, Any]) -> dict[str, Any]:
        rel=self._text(relation.get("relation") or "NEW").upper()
        env=relation.get("environment") if isinstance(relation.get("environment"),dict) else {}
        seq=env.get("active_sequence") if isinstance(env.get("active_sequence"),dict) else {}
        slider = history_search.get("memory_slider") if isinstance(history_search.get("memory_slider"), dict) else {}
        slider_operand = slider.get("selected_memory_operand") if isinstance(slider.get("selected_memory_operand"), dict) else {}
        slider_enabled = bool(slider.get("enabled") and slider_operand and rel in {"CONTINUE", "RECALL"})
        slider_topic = self._text(slider_operand.get("topic"))
        slider_entity = self._text(slider_operand.get("entity"))
        active_topic=self._text(seq.get("topic") or relation.get("active_topic") or topic.get("topic")
                                 or state.get("april_active_topic") or state.get("current_topic") or text)[:500]
        if slider_enabled and (rel == "RECALL" or active_topic.lower() in {"", "text", "вопрос", "ответ", "тема", "загадка"}):
            active_topic = slider_topic or active_topic
        task_frame=task.get("task") if isinstance(task.get("task"),dict) else {}
        active_goal=self._text(task_frame.get("goal") or task.get("goal") or slider_operand.get("goal")
                               or state.get("april_active_goal") or active_topic)[:500]
        active_entity=self._text(entity.get("active_entity") or state.get("april_active_entity"))
        if slider_enabled and (rel == "RECALL" or not active_entity or active_entity.lower() in {"text", "вопрос", "ответ", "ну"}):
            active_entity = slider_entity or active_entity
        last_result=history_search.get("latest_operation_result")
        if not isinstance(last_result,dict) or not last_result:
            last_result=history_search.get("carry_forward_result")
        if not isinstance(last_result,dict): last_result={}
        previous_result={k:v for k,v in {
            "value":self._text(last_result.get("value") or last_result.get("result")),
            "operation":self._text(last_result.get("operation")),
            "source_user_request":self._text(last_result.get("user_request") or last_result.get("source_user_request")),
            "source_assistant_answer":self._text(last_result.get("assistant_answer") or last_result.get("source_assistant_answer")),
            "scene_id":self._text(last_result.get("scene_id")),
            "turn_id":last_result.get("turn_id"),
        }.items() if v not in (None,"",[],{})}
        loops=[]
        for item in list(state.get("open_loops") or [])[-8:]:
            c=self._compact_loop(item)
            if c: loops.append(c)
        pending=[]; ready=[]
        for item in (list(obligations.get("obligations") or [])[-12:] if isinstance(obligations,dict) else []):
            if not isinstance(item,dict): continue
            status=self._text(item.get("status") or "pending").lower()
            c={k:v for k,v in {
                "id":self._text(item.get("id") or item.get("obligation_id")),
                "condition":self._text(item.get("condition")),
                "condition_type":self._text(item.get("condition_type")),
                "action":self._text(item.get("action")),
                "representation":self._text(item.get("representation") or "text"),
                "target":self._text(item.get("target")),
                "instruction":self._text(item.get("instruction")),
                "status":status,
            }.items() if v not in (None,"",[],{})}
            if status in {"pending","active"}: pending.append(c)
            elif status=="ready": ready.append(c)
        result_event=state.get("dialogue_result_event") if isinstance(state.get("dialogue_result_event"),dict) else {}
        result_event={k:v for k,v in result_event.items() if k in {"turn_id","scene_id","topic","goal","representation","summary","completed","created_at"} and v not in (None,"",[],{})}
        # Initiative is driven by semantic state, not trigger words.  A short turn by
        # itself is not enough to initiate anything; an open loop or an active task
        # without a resolved next question is the stronger signal.
        continuity_guidance = bool(continuity.get("user_needs_guidance"))
        task_stalled = bool(task_frame.get("active") and not task_frame.get("last_question") and not task_frame.get("last_user_answer"))
        user_needs_guidance = bool(rel == "CONTINUE" and (continuity_guidance or bool(loops) or task_stalled))
        if slider_enabled:
            next_step = (
                "answer_current_turn_using_recalled_dialogue_operand"
                if rel == "RECALL"
                else "continue_current_topic_using_selected_dialogue_operand"
            )
        elif ready: next_step="consider_ready_user_requested_follow_up_without_forcing_it"
        elif pending and rel=="CONTINUE": next_step="continue_current_topic_while_preserving_pending_obligations"
        elif user_needs_guidance: next_step="guide_user_with_one_small_next_step"
        elif rel=="NEW": next_step="establish_new_topic_and_keep_it_open_for_development"
        else: next_step=continuity.get("next_logical_step")
        return {
            "engine":self.NAME,"version":self.VERSION,"route_policy":"single_dialogue_route",
            "relation":rel,"same_dialogue":rel in {"CONTINUE","RECALL"},
            "sequence_id":self._text(seq.get("sequence_id") or relation.get("sequence_id")),
            "active_topic":active_topic,"active_goal":active_goal,"active_entity":active_entity,
            "current_request":self._text(text),"previous_result":previous_result,"latest_result_event":result_event,
            "memory_slider": {
                "enabled": slider_enabled,
                "selection_mode": self._text(slider.get("selection_mode")),
                "selected_memory_index": slider.get("selected_memory_index", -1),
                "stop_position": slider.get("stop_position"),
                "score": slider_operand.get("score") if slider_enabled else 0.0,
                "semantic_operand": deepcopy(slider_operand) if slider_enabled else {},
            },
            "selected_memory_index": slider.get("selected_memory_index", -1) if slider_enabled else -1,
            "selected_memory_record": deepcopy(slider.get("selected_memory_record") or {}) if slider_enabled else {},
            "selected_memory_operand": deepcopy(slider_operand) if slider_enabled else {},
            "open_loops":loops,"pending_obligations":pending,"ready_obligations":ready,
            "user_needs_guidance":user_needs_guidance,
            "initiative_policy":{
                "user_leads_topic":True,"assist_when_stalled":True,"offer_one_next_step":True,
                "use_semantic_state_not_keywords":True,"never_invent_goal":True,
                "never_repeat_covered_answer":True,"never_create_parallel_route":True,
                "never_force_question":True,"ready_obligation_requires_relevance":True,
            },
            "next_logical_step":next_step,
            "continuation_anchor":{
                "previous_user_turn":self._text(relation.get("previous_user_turn")),
                "previous_april_turn":self._text(relation.get("previous_april_turn")),
                "previous_visual_attachment":deepcopy(relation.get("previous_visual_attachment") or {}),
                "same_sequence":rel=="CONTINUE",
            },
            "visual_continuity":{
                "available":bool(visual_memory.get("available")),"for_renderer":bool(visual_memory.get("for_renderer")),
                "memory_refs":list(visual_memory.get("memory_refs") or [])[:4],"preserve_existing_visual":True,
            },
            "confidence":round(min(float(continuity.get("confidence",0.0) or 0.0),float(obligations.get("confidence",0.0) or 0.0),0.96),4),
        }


class KnowledgeSourceEngine(InterpretationEngineBase):
    NAME = "KnowledgeSourceEngine"
    VERSION = "knowledge_source_v2"

    def analyze(
        self,
        text: str,
        *,
        intent: dict[str, Any],
        domain: dict[str, Any],
        current_turn: dict[str, Any],
        memory: dict[str, Any],
        relation: dict[str, Any],
    ) -> dict[str, Any]:
        low = self._low(text)
        modalities = current_turn.get("modalities", {})
        sources: list[str] = []

        if memory.get("allowed") and relation.get("relation") == "RECALL":
            sources.append("memory")
        if any(modalities.get(k) not in (None, "", {}, []) for k in ("vision", "gallery")):
            sources.append("vision")
        if modalities.get("files") not in (None, "", {}, []):
            sources.append("file")
        if intent.get("operation") == "calculate" or any(
            cue in low for cue in ("посчитай", "вычисли", "сколько будет", "формула")
        ):
            sources.append("calculation")
        if domain.get("domain") == "web" or intent.get("operation") == "search" or any(
            cue in low for cue in ("сайт", "найди", "поищи", "ссылка", "сегодня", "сейчас", "последн")
        ):
            sources.append("web")
        if intent.get("operation") == "code" or domain.get("domain") == "it" and "код" in low:
            sources.append("code")
        if not sources:
            sources.append("internal_knowledge")

        sources = list(dict.fromkeys(sources))
        primary = sources[0]
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "candidate_sources": sources,
            "primary_source": primary,
            "freshness_required": "web" in sources and any(
                cue in low for cue in ("сейчас", "сегодня", "последн", "актуаль", "цена")
            ),
            "evidence_required": primary in {"web", "memory", "vision", "file"},
            "routing_owner": DECISION_OWNER,
            "confidence": 0.92,
        }


class RepresentationDecisionEngine(InterpretationEngineBase):
    NAME = "RepresentationDecisionEngine"
    VERSION = "representation_decision_v3_signal_gated"

    def analyze(
        self,
        text: str,
        *,
        semantic_measurement: dict[str, Any],
        intent: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> dict[str, Any]:
        low = self._low(text)
        explicit = ""
        cue_map = (
            ("graph", ("график", "графика", "plot", "chart")),
            ("table", ("таблиц", "таблица", "сводка в таблице")),
            ("diagram", ("схем", "диаграм", "блок-схем")),
            ("formula", ("формул", "уравнен", "математическ")),
            ("image", ("картин", "изображ", "рисунок", "нарисуй", "изобрази", "фото")),
            ("gallery", ("галере", "несколько изображен", "подборк")),
            ("code", ("код", "python", "функци", "программа")),
            ("link", ("ссылк", "официальный сайт", "адрес сайта")),
        )
        for representation, cues in cue_map:
            if any(cue in low for cue in cues):
                explicit = representation
                break

        profile = semantic_measurement.get("representation_scores", {}) if isinstance(semantic_measurement, dict) else {}
        best = explicit
        if not best and isinstance(profile, dict) and profile:
            ranked = sorted(profile.items(), key=lambda x: x[1], reverse=True)
            if ranked:
                top_rep, top_score = ranked[0]
                second_score = float(ranked[1][1]) if len(ranked) > 1 else 0.0
                # Prototype similarity is supporting evidence only. A weak
                # semantic resemblance must not silently request a gallery/image
                # for a plain text question. Explicit user modality cues above
                # remain authoritative.
                if (
                    top_rep != "text"
                    and float(top_score) >= 0.72
                    and float(top_score) - second_score >= 0.08
                ):
                    best = top_rep
        representation = best or "text"

        # Presentation is a semantic contract, not a renderer call.
        modalities = current_turn.get("available_modalities", [])
        if "vision" in modalities and representation == "text" and intent.get("operation") in {"analyze", "explain"}:
            representation = "text"

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "representation": representation,
            "explicit": bool(explicit),
            "candidate_representations": [explicit] if explicit else [],
            "scene_transform": representation != "text",
            "renderer_neutral": True,
            "confidence": 0.94 if explicit else 0.72,
        }


class ResponseStrategyEngine(InterpretationEngineBase):
    NAME = "ResponseStrategyEngine"
    VERSION = "response_strategy_v2"

    def analyze(
        self,
        text: str,
        *,
        relation: dict[str, Any],
        intent: dict[str, Any],
        task: dict[str, Any],
        continuity: dict[str, Any],
        representation: dict[str, Any],
        knowledge: dict[str, Any],
    ) -> dict[str, Any]:
        rel = relation.get("relation")
        turn = str(relation.get("turn_relation") or "").upper()

        if turn == "TASK_CONFIRMATION":
            mode = "acknowledge_and_advance"
        elif turn == "TASK_CORRECTION":
            mode = "correct_and_advance"
        elif turn in {"TASK_ANSWER", "TASK_RESPONSE"}:
            mode = "evaluate_and_advance_task"
        elif rel == "RECALL":
            mode = "recall_and_connect"
        elif rel == "CONTINUE":
            mode = "continue_dialogue"
        else:
            mode = "develop_new_topic"

        answer_shape = {
            "text": "textual",
            "table": "structured_table",
            "graph": "data_visualization",
            "diagram": "schematic",
            "formula": "mathematical",
            "image": "visual",
            "gallery": "multi_visual",
            "code": "executable_code",
            "link": "web_resource",
        }.get(representation.get("representation"), "textual")

        avoid_repeat = bool(continuity.get("avoid_repeat_content"))
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "mode": mode,
            "answer_shape": answer_shape,
            "natural_dialogue": True,
            "acknowledge_previous_turn": rel in {"CONTINUE", "RECALL"},
            "avoid_repetition": avoid_repeat,
            "recap_ratio_max": 0.20 if rel == "CONTINUE" else 0.0,
            "provider_should_follow_current_user_request": True,
            "provider_must_not_invent_missing_context": True,
            "knowledge_source": knowledge.get("primary_source"),
            "confidence": 0.92,
        }



class SemanticContextAnchorEngine(InterpretationEngineBase):
    """Unify topic, entity, focus, direction and dialogue development.

    This is the last semantic synthesis step before arbitration/provider planning.
    It never replaces the raw user request. It creates a compact, durable meaning
    object that the next turn can resolve without re-interpreting old dialogue text.
    """

    NAME = "SemanticContextAnchorEngine"
    VERSION = SEMANTIC_ANCHOR_VERSION

    @classmethod
    def _entity_type(cls, value: str, *, relation: str, representation: str, task: dict[str, Any]) -> str:
        low = cls._low(value)
        kind = cls._low(task.get("kind"))
        if not value:
            return "UNKNOWN"
        if kind in {"riddle", "game", "question", "choice"}:
            return "TASK"
        if low in {"загадка", "игра", "вопрос", "задача"}:
            return "TASK"
        if low in {"user_identity", "user", "пользователь"}:
            return "USER_IDENTITY"
        if re.search(r"https?://|www\.|[a-z0-9-]+\.[a-z]{2,}", low):
            return "DOCUMENT"
        if representation == "image":
            return "IMAGE_OBJECT"
        if representation == "diagram":
            return "DIAGRAM_OBJECT"
        if representation == "code":
            return "CODE_OBJECT"
        if representation in {"graph", "table", "formula"}:
            return "ARTIFACT"
        if "результат" in low or "ответ" in low or re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", low):
            return "RESULT"
        if any(token in low for token in ("герой", "героя", "героем", "персонаж", "персонажа", "персонажем", "актер", "актриса", "человек", "людей")):
            return "PERSON"
        if any(token in low for token in ("автомобиль", "машина", "авто", "машину", "машиной")):
            return "VEHICLE"
        if any(token in low for token in ("фильм", "сценарий", "история", "сюжет", "тема", "идея", "концепция")):
            return "STORY_ELEMENT" if any(token in low for token in ("герой", "сюжет", "сценарий", "история")) else "CONCEPT"
        return "OBJECT"

    @classmethod
    def _clean_text(cls, value: Any, limit: int = 220) -> str:
        text = cls._text(value)
        return text[:limit]

    @classmethod
    def _development_snapshot(
        cls,
        dialogue_development: dict[str, Any],
        continuity: dict[str, Any],
        current_request: str,
        relation: str,
        topic_root: str,
        active_focus: str,
        previous_anchor: dict[str, Any] | None = None,
        direction: str = "",
    ) -> dict[str, Any]:
        dd = dialogue_development if isinstance(dialogue_development, dict) else {}
        previous_anchor = previous_anchor if isinstance(previous_anchor, dict) else {}
        previous_development = previous_anchor.get("development") if isinstance(previous_anchor.get("development"), dict) else {}
        established: list[str] = []
        changed: list[str] = []

        # Carry forward semantic development only inside the same topic branch.
        # NEW creates a clean semantic history; RECALL resumes evidence only.
        if relation == "CONTINUE":
            for source in (
                previous_development.get("established"),
                previous_development.get("changed"),
            ):
                if isinstance(source, list):
                    established.extend(cls._clean_text(x, 180) for x in source if cls._clean_text(x, 180))

        # Existing development is trusted only as a compact semantic record.
        for source in (
            dd.get("established"),
            dd.get("known_facts"),
            dd.get("covered_content"),
        ):
            if isinstance(source, list):
                established.extend(cls._clean_text(x, 180) for x in source if cls._clean_text(x, 180))

        for source in (
            dd.get("new_information"),
            dd.get("delta"),
        ):
            if isinstance(source, list):
                changed.extend(cls._clean_text(x, 180) for x in source if cls._clean_text(x, 180))
            elif isinstance(source, dict):
                for key in ("new_information", "added", "changes", "updated", "delta"):
                    value = source.get(key)
                    if isinstance(value, list):
                        changed.extend(cls._clean_text(x, 180) for x in value if cls._clean_text(x, 180))

        current_step = cls._clean_text(
            active_focus
            or direction
            or dd.get("current_step")
            or continuity.get("next_logical_step")
            or current_request,
            220,
        )
        next_step = cls._clean_text(
            dd.get("next_step")
            or continuity.get("next_logical_step")
            or "continue_current_topic",
            220,
        )

        # Development records the semantic change of this turn, not a transcript.
        current_change = cls._clean_text(active_focus or direction, 220)
        if relation == "CONTINUE" and current_change:
            changed.append(current_change)
        elif relation == "NEW" and current_change and topic_root:
            changed.append(current_change)

        if relation == "NEW":
            status = "topic_opened"
        elif relation == "RECALL":
            status = "memory_recalled"
        else:
            status = "topic_developed"

        return {
            "status": status,
            "topic_root": topic_root,
            "active_focus": active_focus,
            "established": list(dict.fromkeys(established[-6:])),
            "changed": list(dict.fromkeys(changed[-6:])),
            "current_step": current_step,
            "next_step": next_step,
        }

    def build(
        self,
        *,
        current_turn: dict[str, Any],
        relation: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        intent: dict[str, Any],
        domain: dict[str, Any],
        entity: dict[str, Any],
        reference: dict[str, Any],
        continuity: dict[str, Any],
        branch_index: dict[str, Any],
        history_search: dict[str, Any],
        representation: dict[str, Any],
        dialogue_development: dict[str, Any],
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rel = self._text(relation.get("relation") or "NEW").upper()
        turn_rel = self._text(relation.get("turn_relation"))
        current_request = self._clean_text(current_turn.get("raw_text"), 1200)

        branch = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
        active_branch = branch_index.get("active_branch") if isinstance(branch_index.get("active_branch"), dict) else {}

        memory_slider = history_search.get("memory_slider") if isinstance(history_search.get("memory_slider"), dict) else {}
        slider_operand = memory_slider.get("selected_memory_operand") if isinstance(memory_slider.get("selected_memory_operand"), dict) else {}
        slider_enabled = bool(memory_slider.get("enabled") and slider_operand and rel in {"CONTINUE", "RECALL"})

        recalled_topic = self._clean_text(
            slider_operand.get("topic")
            if slider_enabled else ""
        )
        if not recalled_topic and rel == "RECALL":
            evidence_items = history_search.get("selected_evidence") if isinstance(history_search.get("selected_evidence"), list) else []
            for item in evidence_items:
                if not isinstance(item, dict):
                    continue
                recalled_anchor = item.get("semantic_anchor") if isinstance(item.get("semantic_anchor"), dict) else {}
                recalled_topic = self._clean_text(
                    recalled_anchor.get("topic_root")
                    or item.get("topic")
                    or ""
                )
                if recalled_topic:
                    break

        topic_root = self._clean_text(
            recalled_topic
            if slider_enabled and recalled_topic
            else topic.get("topic_root")
            or topic.get("topic")
            or branch.get("topic")
            or active_branch.get("topic")
            or (current_request if rel == "NEW" and topic.get("confidence", 0.0) >= 0.70 else "")
        )

        # Focus is a moving part of the branch. It may change without creating a new topic.
        focus_candidates = [
            topic.get("active_focus"),
            relation.get("environment", {}).get("active_entity"),
            entity.get("active_entity"),
            reference.get("resolved"),
            branch.get("focus"),
        ]
        focus_candidate = ""
        for candidate in focus_candidates:
            candidate_text = self._clean_text(candidate)
            if candidate_text and self._low(candidate_text) not in {
                "привет", "здравствуйте", "доброе утро", "добрый день", "добрый вечер",
                "хорошо", "отлично", "вопрос", "ответ", "тема", "разговор", "задача", "игра",
                "хочу", "хотел", "хотела", "нужно", "надо", "помоги", "поможешь",
                "помочь", "развить", "обсудить", "поговорить", "заняться",
            } and not re.search(
                r"^(?:привет|здравствуйте|добрый\s+(?:день|вечер)|доброе\s+утро)"
                r"(?:[!.;,\s]+(?:я|мне|хочу|нужно|давай|помоги|поможешь|хотел|хотела)\b.*)?$",
                self._low(candidate_text),
                flags=re.IGNORECASE,
            ):
                focus_candidate = candidate_text
                break
        if slider_enabled:
            slider_focus = self._clean_text(slider_operand.get("focus"))
            if slider_focus and (
                not focus_candidate
                or self._low(focus_candidate) in {"продолжим", "дальше", "вспомни", "ну", "теперь", "вопрос", "ответ"}
            ):
                focus_candidate = slider_focus

        if not focus_candidate and rel == "NEW":
            current_text = self._clean_text(current_request, 220)
            meta_only = bool(
                re.search(
                    r"^(?:привет|здравствуйте|добрый\\s+(?:день|вечер)|доброе\\s+утро)"
                    r"(?:[.!;,\\s]+(?:я|мне|хочу|нужно|давай|помоги|поможешь|хотел|хотела)\\b.*)?$",
                    self._low(current_text),
                    flags=re.IGNORECASE,
                )
                or (
                    re.search(
                        r"\\b(?:хочу|хотел|хотела|нужно|надо|помоги|поможешь|развить|обсудить|"
                        r"поговорить|заняться)\\b",
                        self._low(current_text),
                    )
                    and not re.search(r"\\b(?:про|об|о|насч(?:ё|ё)т)\\b", self._low(current_text))
                )
            )
            if current_text and not meta_only:
                focus_candidate = current_text
            elif not topic_root:
                focus_candidate = self._text(intent.get("goal") or "уточнение темы")

        task_frame = task.get("task") if isinstance(task.get("task"), dict) else {}
        task_target = self._text(task_frame.get("target"))
        recalled_entity = self._clean_text(
            slider_operand.get("entity")
            if slider_enabled else ""
        )
        if not recalled_entity and rel == "RECALL":
            evidence_items = history_search.get("selected_evidence") if isinstance(history_search.get("selected_evidence"), list) else []
            for item in evidence_items:
                if not isinstance(item, dict):
                    continue
                recalled_anchor = item.get("semantic_anchor") if isinstance(item.get("semantic_anchor"), dict) else {}
                recalled_entity = self._clean_text(
                    recalled_anchor.get("primary_entity")
                    or item.get("entity")
                    or ""
                )
                if recalled_entity:
                    break

        primary_entity = self._clean_text(
            recalled_entity
            if recalled_entity and slider_enabled
            else entity.get("active_entity")
            or reference.get("resolved")
            or task_target
        )
        if not primary_entity:
            if rel == "RESUME_BRANCH" or turn_rel == "RESUME_BRANCH":
                primary_entity = self._clean_text(branch_index.get("target_entity") or branch.get("canonical_entity"))
            elif rel == "CONTINUE":
                primary_entity = self._clean_text(
                    active_branch.get("canonical_entity")
                    or branch.get("canonical_entity")
                )

        # A conversational filler or identity fact is not a topical entity.
        if self._low(primary_entity) in {
            "привет", "здравствуйте", "хорошо", "отлично", "скорее",
            "пользователь", "user_identity", "вопрос", "ответ", "тема",
            "разговор", "задача", "игра",
        }:
            primary_entity = ""

        if rel == "NEW" and not topic_root and not primary_entity:
            # A meta/greeting turn has no topical object yet. The next
            # substantive turn establishes the first semantic root.
            focus_candidate = ""

        rep = self._text(representation.get("representation") or "text").lower()
        entity_type = self._entity_type(primary_entity, relation=rel, representation=rep, task=task.get("task") if isinstance(task.get("task"), dict) else {})

        goal = self._clean_text(
            (
                slider_operand.get("goal")
                if slider_enabled and slider_operand.get("goal")
                else intent.get("goal")
                or task.get("goal")
                or branch.get("goal")
                or continuity.get("next_logical_step")
                or "answer"
            )
        )
        operation = self._text(intent.get("operation") or "answer").lower()

        if rel == "NEW":
            direction = self._clean_text(
                f"{operation}: {goal}" if operation and goal else current_request
            )
        elif slider_enabled:
            direction = self._clean_text(
                f"{operation}: {goal}" if operation and goal
                else slider_operand.get("direction")
                or current_request
            )
        elif operation and goal:
            direction = f"{operation}: {goal}"
        else:
            direction = self._clean_text(current_request)

        reference_target = self._clean_text(
            reference.get("resolved")
            or recalled_entity
            or branch_index.get("target_entity")
            or ""
        )

        previous_anchor = state.get("semantic_anchor") if isinstance(state, dict) and isinstance(state.get("semantic_anchor"), dict) else {}
        dev = self._development_snapshot(
            dialogue_development,
            continuity,
            current_request,
            rel,
            topic_root,
            focus_candidate,
            previous_anchor=previous_anchor,
            direction=direction,
        )

        branch_id = self._text(
            relation.get("target_branch_id")
            or branch.get("branch_id")
            or active_branch.get("branch_id")
        )
        sequence_id = self._text(
            relation.get("target_sequence_id")
            or branch.get("sequence_id")
            or active_branch.get("sequence_id")
            or relation.get("environment", {}).get("sequence_id")
        )

        # The anchor is deliberately compact: it is designed to survive a memory
        # round trip and fit inside the provider's 900-token budget.
        anchor = {
            "version": self.VERSION,
            "branch_id": branch_id,
            "sequence_id": sequence_id,
            "relation": rel,
            "turn_relation": turn_rel,
            "topic_root": topic_root,
            "active_focus": focus_candidate,
            "primary_entity": primary_entity,
            "entity_type": entity_type,
            "reference_target": reference_target,
            "operation": operation,
            "goal": goal,
            "direction": self._clean_text(direction, 260),
            "representation": rep,
            "development": dev,
            "next_step": self._clean_text(
                (
                    "answer_current_turn_using_recalled_dialogue_operand"
                    if slider_enabled and rel == "RECALL"
                    else "continue_current_topic_using_selected_dialogue_operand"
                    if slider_enabled and rel == "CONTINUE"
                    else dev.get("next_step") or continuity.get("next_logical_step")
                )
            ),
            "memory_resolution": {
                "enabled": slider_enabled,
                "mode": self._text(memory_slider.get("selection_mode")),
                "memory_index": memory_slider.get("selected_memory_index", -1) if slider_enabled else -1,
                "score": float(slider_operand.get("score", 0.0) or 0.0) if slider_enabled else 0.0,
                "sequence_id": self._text(slider_operand.get("sequence_id")),
                "source": "dialogue_memory_slider" if slider_enabled else "",
            },
            "current_request": current_request,
            "source": "semantic_context_synthesis",
            "historical_memory_is_evidence_only": True,
        }

        meaningful_fields = sum(
            bool(anchor.get(key))
            for key in ("topic_root", "active_focus", "primary_entity", "goal", "direction")
        )
        return {
            **anchor,
            "anchor_id": self._fingerprint(
                "|".join(
                    self._text(anchor.get(k))
                    for k in ("branch_id", "topic_root", "active_focus", "primary_entity", "direction")
                )
            ),
            "confidence": round(
                min(
                    0.98,
                    0.45
                    + 0.08 * meaningful_fields
                    + (0.08 if rel in {"CONTINUE", "RECALL"} else 0.0)
                    + (0.06 if primary_entity else 0.0)
                    + (0.05 if branch_id or sequence_id else 0.0),
                ),
                4,
            ),
        }


class DecisionArbitrationEngine(InterpretationEngineBase):
    NAME = "DecisionArbitrationEngine"
    VERSION = "decision_arbitration_v2"

    def decide(
        self,
        *,
        current_turn: dict[str, Any],
        relation: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        intent: dict[str, Any],
        entity: dict[str, Any],
        reference: dict[str, Any],
        memory: dict[str, Any],
        continuity: dict[str, Any],
        knowledge: dict[str, Any],
        representation: dict[str, Any],
        history_search: dict[str, Any] | None = None,
        semantic_anchor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Deterministic priority:
        # current user turn > explicit discourse relation > active task > explicit recall
        # > current branch > semantic similarity > historical memory.
        rel = str(relation.get("relation") or "NEW").upper()
        turn = str(relation.get("turn_relation") or "").upper()
        signals = relation.get("signals") if isinstance(relation.get("signals"), dict) else {}
        hs = history_search if isinstance(history_search, dict) else {}
        hs_kind = self._text(hs.get("query_kind")).lower()

        if signals.get("explicit_recall") or hs_kind == "history_lookup":
            canonical = "RECALL"
            reason = "explicit_history_lookup" if hs_kind == "history_lookup" else "explicit_memory_request"
        elif signals.get("explicit_new_topic") and turn not in {"TASK_ANSWER", "TASK_CONTINUE", "TASK_CONFIRMATION", "TASK_CORRECTION"}:
            canonical = "NEW"
            reason = "explicit_topic_boundary"
        elif task.get("active") and (
            turn in {"TASK_ANSWER", "TASK_RESPONSE", "TASK_CONFIRMATION", "TASK_CORRECTION", "TASK_CONTINUE"}
            or task.get("task_action")
        ):
            canonical = "CONTINUE"
            reason = "active_task_owns_turn"
        elif rel == "CONTINUE":
            canonical = "CONTINUE"
            reason = "active_dialogue_relation"
        elif rel == "RECALL":
            canonical = "RECALL"
            reason = "memory_relation"
        else:
            canonical = "NEW"
            reason = "self_contained_current_turn"

        # An explicit branch resume is a higher-order discourse act than a
        # stale interactive task. The selected branch must own the turn, otherwise
        # an old question (for example a forgotten name prompt) can swallow the
        # resumed topic.
        if canonical == "CONTINUE" and (turn == "RESUME_BRANCH" or relation.get("target_branch_id") and relation.get("branch_index", {}).get("resume_candidate")):
            semantic_relation = "RESUME_BRANCH"
        # Active task answers always get task-level semantic ownership.
        elif canonical == "CONTINUE" and task.get("active"):
            if turn == "TASK_ANSWER":
                semantic_relation = "TASK_RESPONSE"
            elif turn == "TASK_CONFIRMATION":
                semantic_relation = "TASK_CONFIRMATION"
            elif turn == "TASK_CORRECTION":
                semantic_relation = "TASK_CORRECTION"
            else:
                semantic_relation = "TASK_CONTINUE"
        elif canonical == "RECALL":
            semantic_relation = "REFERENCE_OLD_TOPIC"
        elif canonical == "CONTINUE":
            # Let the fast history index refine the *kind* of continuation
            # without changing the canonical three-way relation. This keeps
            # dialogue semantics explicit: a result follow-up, a dependent
            # operation, a history lookup, and a generic branch continuation
            # are different discourse acts even though all remain CONTINUE.
            hs = history_search if isinstance(history_search, dict) else {}
            hs_relation = self._text(hs.get("recommended_turn_relation")).upper()
            semantic_relation = {
                "RESULT_FOLLOWUP": "RESULT_FOLLOWUP",
                "DEPENDENT_OPERATION": "DEPENDENT_OPERATION",
                "HISTORY_LOOKUP": "HISTORY_LOOKUP",
                "HISTORY_SUPPORTED_CONTINUATION": "HISTORY_SUPPORTED_CONTINUATION",
            }.get(hs_relation, "CONTINUE_TOPIC")
        else:
            semantic_relation = "NEW_TOPIC"

        # Historical entities never become active solely because memory exists.
        semantic_anchor = semantic_anchor if isinstance(semantic_anchor, dict) else {}
        active_entity = self._text(
            semantic_anchor.get("primary_entity")
            or entity.get("active_entity", "")
        )
        active_topic = self._text(
            semantic_anchor.get("topic_root")
            or topic.get("topic")
        )
        use_memory = bool(canonical == "RECALL" or (canonical == "CONTINUE" and memory.get("selected")))

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "relation": canonical,
            "turn_relation": semantic_relation,
            "reason": reason,
            "active_topic": active_topic,
            "active_entity": self._text(active_entity),
            "semantic_anchor": deepcopy(semantic_anchor),
            "active_task": task.get("task") if task.get("active") else {},
            "use_memory": use_memory,
            "memory_items": list(memory.get("selected") or []) if use_memory else [],
            "semantic_intent": intent.get("intent"),
            "operation": intent.get("operation"),
            "goal": intent.get("goal"),
            "representation": representation.get("representation") or "text",
            "current_request": current_turn.get("raw_text", ""),
            "provider_request_authority": "CURRENT_USER_TURN",
            "historical_memory_role": "evidence_only",
            "history_search_relation": self._text(
                (history_search or {}).get("recommended_turn_relation")
            ) if isinstance(history_search, dict) else "",
            "result_dependency": {
                "latest_operation_result": (history_search or {}).get("latest_operation_result", {})
                if isinstance(history_search, dict) else {},
                "carry_forward_result": (history_search or {}).get("carry_forward_result", {})
                if isinstance(history_search, dict) else {},
                "operand_anchor": (history_search or {}).get("operand_anchor", {})
                if isinstance(history_search, dict) else {},
            },
            "target_sequence_id": self._text(relation.get("target_sequence_id")),
            "target_branch_id": self._text(relation.get("target_branch_id")),
            "target_branch": deepcopy(relation.get("target_branch") if isinstance(relation.get("target_branch"), dict) else {}),
            "resume_branch": bool(turn == "RESUME_BRANCH"),
            "confidence": 0.97,
        }


class ConsistencyEngine(InterpretationEngineBase):
    NAME = "ConsistencyEngine"
    VERSION = "consistency_v3_semantic_sync"

    def validate(
        self,
        *,
        current_turn: dict[str, Any],
        identity: dict[str, Any],
        relation: dict[str, Any],
        arbitration: dict[str, Any],
        memory: dict[str, Any],
        entity: dict[str, Any],
        task: dict[str, Any],
        representation: dict[str, Any],
        semantic_anchor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []

        raw = current_turn.get("raw_text", "")
        checks.append({"name": "current_request_preserved", "ok": raw == current_turn.get("raw_text")})

        same_user = (
            not identity.get("scope", {}).get("user_id")
            or str(current_turn.get("user_id") or "") == str(identity.get("scope", {}).get("user_id") or "")
        )
        checks.append({"name": "authenticated_user_scope", "ok": same_user})

        mem_allowed = relation.get("relation") == "RECALL" or (
            relation.get("relation") == "CONTINUE" and bool(memory.get("selected"))
        )
        checks.append({
            "name": "memory_fenced_for_new_topic",
            "ok": relation.get("relation") != "NEW" or not mem_allowed,
        })

        stale_block = relation.get("relation") == "NEW" and bool(entity.get("inherited_entity"))
        checks.append({"name": "stale_entity_not_inherited", "ok": not stale_block})

        task_match = True
        if relation.get("relation") == "CONTINUE" and task.get("active"):
            task_match = True
        checks.append({"name": "task_relation_consistent", "ok": task_match})

        rep = representation.get("representation") or "text"
        supported = rep in {"text", "table", "graph", "diagram", "formula", "image", "gallery", "code", "link"}
        checks.append({"name": "representation_supported", "ok": supported})

        active_entity = self._text(arbitration.get("active_entity"))
        command_entity_leak = self._low(active_entity) in {
            "расскажи", "объясни", "покажи", "нарисуй", "создай", "сделай",
            "напиши", "построй", "проверь", "опиши", "сравни", "найди",
            "скажи", "дай", "почему", "как", "что",
        }
        checks.append({"name": "semantic_entity_not_command", "ok": not command_entity_leak})

        anchor = semantic_anchor if isinstance(semantic_anchor, dict) else {}
        allowed_entity_type = self._text(anchor.get("entity_type")) in SEMANTIC_ENTITY_TYPES if anchor.get("entity_type") else True
        checks.append({"name": "semantic_anchor_entity_type_valid", "ok": allowed_entity_type})

        anchor_request = self._text(anchor.get("current_request"))
        checks.append({
            "name": "semantic_anchor_current_request_synced",
            "ok": not anchor_request or anchor_request == self._text(current_turn.get("raw_text")),
        })

        stale_anchor_on_new = (
            arbitration.get("relation") == "NEW"
            and (
                self._text(anchor.get("reference_target"))
                or self._text(anchor.get("branch_id") or anchor.get("sequence_id"))
            )
            and not self._text(anchor.get("topic_root")) == self._text(current_turn.get("raw_text"))
            and not self._text(anchor.get("source")) == "semantic_context_synthesis"
        )
        checks.append({"name": "semantic_anchor_not_historical_on_new", "ok": not stale_anchor_on_new})

        errors = [x["name"] for x in checks if not x["ok"]]
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "valid": not errors,
            "checks": checks,
            "errors": errors,
            "repair_actions": (
                ["clear_historical_memory", "clear_inherited_entity"] if errors else []
            ),
            "confidence": 0.98 if not errors else 0.55,
        }


class CanonicalizationEngine(InterpretationEngineBase):
    NAME = "CanonicalizationEngine"
    VERSION = "canonical_packet_v3"

    def build(
        self,
        *,
        current_turn: dict[str, Any],
        identity: dict[str, Any],
        relation: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        intent: dict[str, Any],
        domain: dict[str, Any],
        entity: dict[str, Any],
        reference: dict[str, Any],
        memory: dict[str, Any],
        continuity: dict[str, Any],
        knowledge: dict[str, Any],
        representation: dict[str, Any],
        strategy: dict[str, Any],
        arbitration: dict[str, Any],
        consistency: dict[str, Any],
        semantic_anchor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        user_request = str(current_turn.get("raw_text") or "")
        normalized = self._text(user_request)
        relation_value = arbitration.get("relation") or relation.get("relation") or "NEW"

        active_task = task.get("task") if task.get("active") else {}
        semantic_anchor = semantic_anchor if isinstance(semantic_anchor, dict) else {}
        anchor_topic = self._text(semantic_anchor.get("topic_root")) if isinstance(semantic_anchor, dict) else ""
        if anchor_topic:
            active_topic = anchor_topic
        elif relation_value == "NEW":
            active_topic = self._text(
                arbitration.get("active_topic")
                or topic.get("topic")
                or ""
            )
        else:
            active_topic = self._text(
                arbitration.get("active_topic")
                or topic.get("topic")
                or normalized
            )
        active_entity = self._text(
            semantic_anchor.get("primary_entity")
            or arbitration.get("active_entity")
            or entity.get("active_entity")
        )

        provider_instruction_parts = [
            f"Current user request: {normalized}",
            f"Dialogue relation: {relation_value}",
            f"Topic: {active_topic}",
            f"Intent: {intent.get('intent')}",
            f"Operation: {intent.get('operation')}",
            f"Goal: {intent.get('goal')}",
            f"Domain: {domain.get('domain')}",
            f"Representation: {representation.get('representation') or 'text'}",
        ]
        if semantic_anchor:
            provider_instruction_parts.append(
                "Semantic anchor: "
                + self._text(
                    semantic_anchor.get("topic_root")
                    or active_topic
                )
                + " / focus="
                + self._text(semantic_anchor.get("active_focus"))
                + " / entity="
                + self._text(semantic_anchor.get("primary_entity"))
                + " / direction="
                + self._text(semantic_anchor.get("direction"))
            )
        if relation_value == "CONTINUE":
            provider_instruction_parts.append("Continue the current dialogue naturally; do not repeat content already covered.")
        elif relation_value == "RECALL":
            provider_instruction_parts.append("Use only the selected historical memory as evidence for the requested recall.")
        else:
            provider_instruction_parts.append("Treat the current user request as a fresh topic unless it explicitly depends on supplied current context.")

        if active_task:
            provider_instruction_parts.append(
                f"Active task state: {active_task.get('kind') or 'task'} / {active_task.get('phase') or 'active'}."
            )
        if continuity.get("avoid_repeat_content"):
            provider_instruction_parts.append(
                "Avoid repeating: " + " | ".join(
                    self._text(x) for x in continuity.get("avoid_repeat_content", []) if self._text(x)
                )
            )

        execution_instruction = "\n".join(provider_instruction_parts)

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            # The raw user request is immutable and independently addressable.
            "current_user_request": user_request,
            "canonical_user_request": user_request,
            "normalized_user_request": normalized,
            "authenticated_scope": identity.get("scope", {}),
            "dialogue": {
                "relation": relation_value,
                "turn_relation": arbitration.get("turn_relation") or relation.get("turn_relation"),
                "continuation": relation_value == "CONTINUE",
                "reference": relation_value == "RECALL",
                "sequence_id": self._text(
                    relation.get("target_sequence_id")
                    or (relation.get("environment", {}) or {}).get("target_sequence_id")
                    or identity.get("scope", {}).get("dialogue_sequence_id", "")
                ),
                "target_sequence_id": self._text(relation.get("target_sequence_id")),
                "target_branch_id": self._text(relation.get("target_branch_id")),
                "previous_user_turn": relation.get("previous_user_turn"),
                "previous_april_turn": relation.get("previous_april_turn"),
            },
            "topic": {
                "active": active_topic,
                "branch": topic.get("topic_branch"),
                "branch_key": topic.get("topic_branch_key"),
                "old_topic_fenced": relation_value == "NEW",
            },
            "task": active_task,
            "semantic": {
                "intent": intent.get("intent"),
                "operation": intent.get("operation"),
                "goal": intent.get("goal"),
                "domain": domain.get("domain"),
                "subdomain": domain.get("subdomain"),
                "active_entity": active_entity,
            },
            "semantic_anchor": deepcopy(semantic_anchor),
            "reference": reference,
            "memory": {
                "allowed": bool(arbitration.get("use_memory")),
                "selected": list(arbitration.get("memory_items") or []),
                "historical_memory_is_evidence_only": True,
                "seven_day_window_seconds": memory.get("seven_day_window_seconds"),
            },
            "knowledge_source": knowledge,
            "representation": representation,
            "response_strategy": strategy,
            "continuation_analysis": continuity,
            "branch": {
                "branch_id": self._text(relation.get("target_branch_id") or (relation.get("branch_index") or {}).get("target_branch_id")),
                "sequence_id": self._text(relation.get("target_sequence_id") or (relation.get("branch_index") or {}).get("target_sequence_id")),
                "topic": self._text((relation.get("branch_index") or {}).get("target_topic")),
                "entity": self._text((relation.get("branch_index") or {}).get("target_entity")),
                "resume": bool(relation.get("turn_relation") == "RESUME_BRANCH"),
            },
            "consistency": consistency,
            "execution_instruction": execution_instruction,
            "provider_input_policy": {
                "current_user_request_authoritative": True,
                "current_user_request_must_not_be_replaced_by_history": True,
                "historical_memory_is_evidence_only": True,
                "old_topics_are_excluded_on_new_topic": True,
                "derived_instruction_is_separate_from_user_text": True,
                "semantic_anchor_is_compact_state_not_raw_history": True,
                "topic_root_is_not_replaced_by_current_focus": True,
            },
            "decision_owner": DECISION_OWNER,
            "evidence_only_until_executor": True,
            "confidence": min(
                float(arbitration.get("confidence", 0.0) or 0.0),
                float(consistency.get("confidence", 0.0) or 0.0),
            ),
        }


class ProviderContextPlanEngine(InterpretationEngineBase):
    """Build the provider-facing context contract before the 900-token packer.

    This engine decides *which* semantic facts are relevant. Provider is only
    responsible for fitting those selected facts into the hard input envelope.
    The raw current user request is always retained separately.
    """

    NAME = "ProviderContextPlanEngine"
    VERSION = PROVIDER_CONTEXT_PLAN_VERSION

    @classmethod
    def _section(
        cls,
        key: str,
        value: Any,
        priority: float,
        reason: str,
        *,
        protected: bool = False,
        max_depth: int = 4,
        max_items: int = 8,
        max_keys: int = 12,
    ) -> dict[str, Any] | None:
        if value in (None, "", [], {}):
            return None
        if key == "CURRENT_REQUEST":
            compact = cls._text(value)
        else:
            # Keep this plan provider-friendly without copying arbitrary state.
            # Strings are bounded by _text; structured payloads are compacted.
            compact = value
            if isinstance(value, (dict, list, tuple, set)):
                compact = cls._compact(value, max_depth=max_depth, max_items=max_items, max_keys=max_keys)
        if compact in (None, "", [], {}):
            return None
        return {
            "key": key,
            "value": compact,
            "priority": round(max(0.0, min(1.0, float(priority))), 4),
            "reason": reason,
            "protected": bool(protected),
        }

    @classmethod
    def _compact(
        cls,
        value: Any,
        *,
        depth: int = 0,
        max_depth: int = 4,
        max_items: int = 8,
        max_keys: int = 12,
    ) -> Any:
        if depth > max_depth or value in (None, "", [], {}):
            return None
        if isinstance(value, (str, int, float, bool)):
            return value if not isinstance(value, str) else cls._text(value)
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for key, item in list(value.items())[:max_keys]:
                cleaned = cls._compact(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_items=max_items,
                    max_keys=max_keys,
                )
                if cleaned not in (None, "", [], {}):
                    out[str(key)] = cleaned
            return out
        if isinstance(value, (list, tuple, set)):
            out = []
            for item in list(value)[:max_items]:
                cleaned = cls._compact(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_items=max_items,
                    max_keys=max_keys,
                )
                if cleaned not in (None, "", [], {}):
                    out.append(cleaned)
            return out
        return cls._text(value)

    @classmethod
    def _memory_projection(cls, memory: dict[str, Any], *, recall: bool, continuation: bool) -> list[dict[str, Any]]:
        selected = list(memory.get("selected") or []) if isinstance(memory, dict) else []
        if not (recall or continuation):
            return []
        limit = 4 if recall else 2
        result = []
        for item in selected[:limit]:
            if not isinstance(item, dict):
                continue
            result.append(cls._compact(item, max_depth=3, max_items=4, max_keys=8))
        return [x for x in result if x not in (None, "", [], {})]

    def build(
        self,
        *,
        current_turn: dict[str, Any],
        relation: dict[str, Any],
        topic: dict[str, Any],
        task: dict[str, Any],
        intent: dict[str, Any],
        domain: dict[str, Any],
        entity: dict[str, Any],
        reference: dict[str, Any],
        memory: dict[str, Any],
        continuity: dict[str, Any],
        knowledge: dict[str, Any],
        representation: dict[str, Any],
        strategy: dict[str, Any],
        arbitration: dict[str, Any],
        consistency: dict[str, Any],
        history_search: dict[str, Any] | None = None,
        identity_memory: dict[str, Any] | None = None,
        dialogue_development: dict[str, Any] | None = None,
        semantic_anchor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        history_search = history_search if isinstance(history_search, dict) else {}
        rel = self._text(arbitration.get("relation") or relation.get("relation") or "NEW").upper()
        turn_rel = self._text(arbitration.get("turn_relation") or relation.get("turn_relation")).upper()
        raw_request = self._text(current_turn.get("raw_text"))
        active_task = task.get("task") if isinstance(task.get("task"), dict) and task.get("active") else {}
        active_topic = self._text(arbitration.get("active_topic") or topic.get("topic"))
        active_entity = self._text(arbitration.get("active_entity") or entity.get("active_entity"))
        slider = history_search.get("memory_slider") if isinstance(history_search.get("memory_slider"), dict) else {}
        slider_operand = slider.get("selected_memory_operand") if isinstance(slider.get("selected_memory_operand"), dict) else {}
        if slider.get("enabled") and slider_operand and rel in {"CONTINUE", "RECALL"}:
            active_topic = self._text(slider_operand.get("topic") or active_topic)
            if slider_operand.get("entity"):
                active_entity = self._text(slider_operand.get("entity"))
        rep = self._text(arbitration.get("representation") or representation.get("representation") or "text").lower()
        source = self._text(knowledge.get("primary_source") or "internal_knowledge").lower()
        identity_memory = identity_memory if isinstance(identity_memory, dict) else {}
        dialogue_development = dialogue_development if isinstance(dialogue_development, dict) else {}
        semantic_anchor = semantic_anchor if isinstance(semantic_anchor, dict) else {}

        required: list[dict[str, Any]] = []
        optional: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []

        def add(bucket, key, value, priority, reason, protected=False, **kwargs):
            item = self._section(key, value, priority, reason, protected=protected, **kwargs)
            if item:
                bucket.append(item)

        semantic_core = {
            "intent": intent.get("intent"),
            "operation": intent.get("operation"),
            "goal": intent.get("goal"),
            "domain": domain.get("domain"),
            "subdomain": domain.get("subdomain"),
            "topic": active_topic,
            "entity": active_entity,
            "representation": rep,
        }
        output_contract = {
            "representation": rep,
            "requested_outputs": (
                [rep] if rep != "text" else ["text"]
            ),
            "operation": intent.get("operation"),
            "render_authorized": bool(
                (reference.get("artifact_reference") if isinstance(reference, dict) else False)
            ) if rep in {"image", "gallery", "diagram", "graph", "table", "formula", "code", "link"} else False,
        }

        # The current request is immutable. Provider may compact it only when the
        # hard envelope requires it; it can never replace it with historical text.
        add(required, "CURRENT_REQUEST", raw_request, 1.0, "current_user_turn", True)

        # NEW topic turns are intentionally minimal: the provider already knows
        # how to produce MachineResponse JSON from its system contract. Do not ship
        # prior topic/entity/task state when there is no semantic dependency.
        # For CONTINUE/RECALL we keep the compact semantic core because the current
        # request may contain anaphora or omitted operands.
        if rel != "NEW":
            add(required, "SEMANTIC_CORE", semantic_core, 0.98, "interpretation_semantic_decision", True, max_depth=3, max_items=8, max_keys=10)
            if semantic_anchor:
                add(required, "SEMANTIC_ANCHOR", {
                    "topic_root": semantic_anchor.get("topic_root"),
                    "active_focus": semantic_anchor.get("active_focus"),
                    "primary_entity": semantic_anchor.get("primary_entity"),
                    "entity_type": semantic_anchor.get("entity_type"),
                    "direction": semantic_anchor.get("direction"),
                    "goal": semantic_anchor.get("goal"),
                    "operation": semantic_anchor.get("operation"),
                    "development": semantic_anchor.get("development"),
                    "next_step": semantic_anchor.get("next_step"),
                }, 0.995, "canonical_semantic_anchor_for_continuation", True, max_depth=4, max_items=6, max_keys=10)
            slider = history_search.get("memory_slider") if isinstance(history_search.get("memory_slider"), dict) else {}
            slider_operand = slider.get("selected_memory_operand") if isinstance(slider.get("selected_memory_operand"), dict) else {}
            if rel == "RECALL" and slider.get("enabled") and slider_operand:
                add(required, "MEMORY_SELECTION", {
                    "memory_index": slider.get("selected_memory_index", -1),
                    "sequence_id": slider_operand.get("sequence_id"),
                    "topic": slider_operand.get("topic"),
                    "entity": slider_operand.get("entity"),
                    "focus": slider_operand.get("focus"),
                    "direction": slider_operand.get("direction"),
                    "goal": slider_operand.get("goal"),
                    "previous_user_turn": slider_operand.get("user_request"),
                    "previous_april_turn": slider_operand.get("april_answer"),
                    "summary": slider_operand.get("summary"),
                    "semantic_relation": slider_operand.get("semantic_relation"),
                }, 0.998, "sequential_semantic_memory_slider", True, max_depth=4, max_items=6, max_keys=12)
            if rel == "RECALL":
                add(required, "DIALOGUE_DEVELOPMENT", dialogue_development, 0.965, "memory_recall_dialogue_connection", True, max_depth=4, max_items=8, max_keys=14)
            else:
                # CONTINUATION_INTEREST below is the single compact progression
                # contract. Keep the verbose development object out of the
                # provider-required set for CONTINUE.
                add(optional, "DIALOGUE_DEVELOPMENT", dialogue_development, 0.55, "debug_only_dialogue_trajectory", False, max_depth=3, max_items=5, max_keys=7)
            add(required, "OUTPUT_CONTRACT", output_contract, 0.96, "response_shape_contract", True, max_depth=3, max_items=5, max_keys=8)

        directives = current_turn.get("request_directives") or []
        if directives:
            add(required, "REQUEST_DIRECTIVES", list(directives)[:5], 0.95, "explicit_current_turn_constraints", True, max_depth=2, max_items=5, max_keys=6)

        # Tool/source decisions are useful only when the answer cannot be purely
        # generated from the semantic turn.
        if source not in {"internal_knowledge", "", "general"}:
            add(required, "KNOWLEDGE_SOURCE", {
                "primary": source,
                "freshness_required": bool(knowledge.get("freshness_required")),
                "evidence_required": bool(knowledge.get("evidence_required")),
            }, 0.90, "knowledge_source_requirement", True, max_depth=2, max_items=4, max_keys=6)

        # Interactive task ownership is stronger than generic topic continuity.
        if active_task:
            add(required, "ACTIVE_TASK", active_task, 0.97, "active_task_owner", True, max_depth=4, max_items=8, max_keys=12)

        if rel == "CONTINUE":
            branch_index = relation.get("branch_index") if isinstance(relation.get("branch_index"), dict) else {}
            target_branch = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
            active_branch = branch_index.get("active_branch") if isinstance(branch_index.get("active_branch"), dict) else {}
            target_sequence_id = self._text(
                relation.get("target_sequence_id")
                or (relation.get("environment", {}) or {}).get("target_sequence_id")
                or branch_index.get("target_sequence_id")
                or (target_branch.get("sequence_id") if turn_rel == "RESUME_BRANCH" else active_branch.get("sequence_id"))
            )
            anchor = {
                "branch_id": self._text(
                    relation.get("target_branch_id")
                    or branch_index.get("target_branch_id")
                    or target_branch.get("branch_id")
                    or active_branch.get("branch_id")
                ),
                "sequence_id": target_sequence_id,
                "previous_user_turn": relation.get("previous_user_turn"),
                "previous_april_turn": relation.get("previous_april_turn"),
                "topic": active_topic,
                "entity": active_entity,
                "turn_relation": turn_rel or history_search.get("recommended_turn_relation"),
            }
            add(required, "DIALOGUE_ANCHOR", anchor, 0.99, "selected_authenticated_branch_anchor", True, max_depth=3, max_items=6, max_keys=9)
            continuation_interest = {
                "mode": "RESUME_BRANCH" if turn_rel == "RESUME_BRANCH" else "CONTINUE_BRANCH",
                "what_user_continues": raw_request,
                "resolved_entity": active_entity,
                "active_topic": active_topic,
                "branch_id": self._text(anchor.get("branch_id") or active_branch.get("branch_id")),
                "sequence_id": target_sequence_id,
                "previous_result": self._text((history_search.get("latest_operation_result") or {}).get("value")),
                "next_step": self._text(continuity.get("next_logical_step")),
                "avoid_repeat": list(continuity.get("avoid_repeat_content") or [])[:2],
            }
            add(required, "CONTINUATION_INTEREST", continuation_interest, 0.988, "current_turn_progression_interest", True, max_depth=3, max_items=6, max_keys=10)

            # If the semantic slider found a historical branch/topic, that single
            # operand is the only cross-branch memory allowed into CONTINUE.
            slider = history_search.get("memory_slider") if isinstance(history_search.get("memory_slider"), dict) else {}
            slider_operand = slider.get("selected_memory_operand") if isinstance(slider.get("selected_memory_operand"), dict) else {}
            if slider.get("enabled") and slider_operand:
                add(required, "CONTINUATION_MEMORY_OPERAND", {
                    "memory_index": slider.get("selected_memory_index", -1),
                    "sequence_id": slider_operand.get("sequence_id"),
                    "scene_id": slider_operand.get("scene_id"),
                    "topic": slider_operand.get("topic"),
                    "entity": slider_operand.get("entity"),
                    "focus": slider_operand.get("focus"),
                    "direction": slider_operand.get("direction"),
                    "goal": slider_operand.get("goal"),
                    "previous_user_turn": slider_operand.get("user_request"),
                    "previous_april_turn": slider_operand.get("april_answer"),
                    "summary": slider_operand.get("summary"),
                    "dialogue_obligations": slider_operand.get("dialogue_obligations"),
                    "semantic_relation": slider_operand.get("semantic_relation"),
                    "instruction": (
                        "Resolve the current continuation against this selected "
                        "historical operand. The current user request stays authoritative."
                    ),
                }, 0.998, "sequential_semantic_memory_slider", True, max_depth=4, max_items=8, max_keys=14)
                add(optional, "MEMORY_SLIDER_TRACE", {
                    "enabled": True,
                    "selection_mode": slider.get("selection_mode"),
                    "selected_memory_index": slider.get("selected_memory_index", -1),
                    "stop_position": slider.get("stop_position"),
                    "same_sequence": slider.get("same_sequence"),
                    "score": slider_operand.get("score"),
                }, 0.70, "memory_slider_diagnostics", False, max_depth=3, max_items=4, max_keys=8)

            previous_visual = relation.get("previous_visual_attachment") or (relation.get("environment", {}) or {}).get("previous_visual_attachment")
            if isinstance(previous_visual, dict) and previous_visual:
                add(required, "DIALOGUE_VISUAL_ANCHOR", {
                    "reference_to_previous_visual": bool(relation.get("visual_reference")),
                    "attachment": previous_visual,
                    "same_dialogue_sequence": True,
                    "reuse_artifact_when_requested": True,
                }, 0.987, "visual_attachment_belongs_to_same_dialogue_turn", True, max_depth=4, max_items=5, max_keys=10)

            if history_search.get("history_context_required"):
                compact_history_evidence = {
                    "query_kind": history_search.get("query_kind"),
                    "selected_evidence": list(history_search.get("selected_evidence") or [])[:4],
                    "result_chain": list(history_search.get("result_chain") or [])[-6:],
                    "latest_operation_result": history_search.get("latest_operation_result") or {},
                    "recommended_turn_relation": history_search.get("recommended_turn_relation"),
                }
                add(required, "DIALOGUE_HISTORY_EVIDENCE", compact_history_evidence, 0.985, "fast_authenticated_history_search", True, max_depth=4, max_items=6, max_keys=10)

            carry_forward = history_search.get("carry_forward_result")
            if isinstance(carry_forward, dict) and carry_forward.get("value"):
                add(required, "RESULT_CARRY_FORWARD", {
                    "value": carry_forward.get("value"),
                    "source_user_request": carry_forward.get("user_request"),
                    "source_assistant_answer": carry_forward.get("assistant_answer"),
                    "operation": carry_forward.get("operation"),
                    "operation_amount": carry_forward.get("operation_amount"),
                    "do_not_reapply_previous_operation": True,
                }, 0.997, "latest_derived_result_is_current_answer", True, max_depth=3, max_items=5, max_keys=8)

            operand_anchor = history_search.get("operand_anchor")
            if isinstance(operand_anchor, dict) and operand_anchor.get("value"):
                add(required, "OPERAND_ANCHOR", operand_anchor, 0.996, "current_operation_references_prior_result", True, max_depth=3, max_items=6, max_keys=9)

            add(optional, "CONTINUATION_ANALYSIS", {
                "next_logical_step": continuity.get("next_logical_step"),
                "covered_content": continuity.get("covered_content") or [],
                "avoid_repeat_content": continuity.get("avoid_repeat_content") or [],
                "novelty_score": continuity.get("novelty_score"),
                "same_conversational_branch": True,
            }, 0.93, "advance_without_repetition", False, max_depth=3, max_items=6, max_keys=8)

            seq = (relation.get("environment") or {}).get("active_sequence") if isinstance(relation.get("environment"), dict) else None
            if isinstance(seq, dict) and seq:
                add(optional, "ACTIVE_SEQUENCE_DIGEST", {
                    "sequence_id": seq.get("sequence_id"),
                    "turn_count": seq.get("turn_count") or seq.get("turns_count"),
                    "last_user_request": seq.get("last_user_request"),
                    "last_april_answer": seq.get("last_april_answer"),
                }, 0.78, "same_authenticated_sequence", False, max_depth=2, max_items=5, max_keys=8)

            branch_memory = self._memory_projection(memory, recall=False, continuation=True)
            if branch_memory:
                add(optional, "BRANCH_MEMORY_EVIDENCE", branch_memory, 0.62, "same_sequence_support_only", False, max_depth=4, max_items=2, max_keys=7)

            excluded.extend([
                {"key": "UNRELATED_7D_MEMORY", "reason": "continuation_uses_live_branch_first"},
                {"key": "OTHER_TOPIC_BRANCHES", "reason": "current_branch_is_authoritative"},
                {"key": "STALE_GLOBAL_ENTITY", "reason": "entity must resolve from current branch"},
                {"key": "FULL_HISTORY", "reason": "history_search_selects_relevant_evidence_only"},
            ])

        elif rel == "RECALL":
            if identity_memory.get("name"):
                add(required, "USER_IDENTITY", {
                    "name": self._text(identity_memory.get("name")),
                    "source": self._text(identity_memory.get("name_source") or "authenticated_user_dialogue"),
                    "updated_at": identity_memory.get("updated_at"),
                    "scope": "current_authenticated_user",
                }, 0.995, "authenticated_user_identity_fact", True, max_depth=2, max_items=4, max_keys=6)

            memory_items = self._memory_projection(memory, recall=True, continuation=False)
            history_items = list(history_search.get("selected_evidence") or [])[:5]
            recall_packet = {
                "memory_items": memory_items,
                "dialogue_history_items": history_items,
                "result_chain": list(history_search.get("result_chain") or [])[-6:],
                "query_kind": history_search.get("query_kind"),
                "authenticated_scope": history_search.get("authenticated_scope") or {},
            }
            add(required, "MEMORY_RECALL", recall_packet, 0.99, "explicit_history_or_7d_recall", True, max_depth=4, max_items=6, max_keys=10)
            add(optional, "RECALL_RESPONSE_GUIDANCE", {
                "use_memory_as_evidence": True,
                "state_only_what_is_recalled": True,
                "do_not_invent_missing_details": True,
                "invite_user_to_restate_missing_context": True,
            }, 0.90, "safe_memory_recall_behavior", False, max_depth=2, max_items=4, max_keys=6)

            # Old branch context can be useful only insofar as the memory engine
            # selected it for this explicit recall.
            excluded.extend([
                {"key": "UNSELECTED_7D_MEMORY", "reason": "not_relevant_to_explicit_recall"},
                {"key": "FULL_HISTORY", "reason": "memory_engine_selected_evidence_only"},
                {"key": "CURRENT_UNRELATED_TASK", "reason": "recall_requested"},
            ])
        else:
            # NEW/INDEPENDENT: no old conversational content crosses the boundary.
            excluded.extend([
                {"key": "PREVIOUS_USER_TURN", "reason": "new_topic"},
                {"key": "PREVIOUS_APRIL_TURN", "reason": "new_topic"},
                {"key": "ACTIVE_SEQUENCE_DIGEST", "reason": "new_topic"},
                {"key": "RELEVANT_MEMORY", "reason": "new_topic_memory_fence"},
                {"key": "SEVEN_DAY_MEMORY", "reason": "new_topic_memory_fence"},
                {"key": "HISTORICAL_MEMORY", "reason": "new_topic_memory_fence"},
                {"key": "STALE_VISUAL_STATE", "reason": "no_artifact_dependency"},
                {"key": "STALE_ENTITY", "reason": "current_turn_entity_only"},
            ])

        # Current-turn multimodal presence is relevant when it can materially change
        # the answer. Actual payload bytes remain outside the semantic plan.
        modalities = current_turn.get("available_modalities") or []
        if modalities:
            add(optional, "CURRENT_MODALITIES", list(modalities)[:5], 0.86, "current_turn_multimodal_evidence", False, max_depth=2, max_items=5, max_keys=5)

        # Keep only the selected representation; Provider must not manufacture another.
        if rep != "text":
            add(optional, "REPRESENTATION_DECISION", {
                "representation": rep,
                "renderer_neutral": True,
                "structured_output_required": True,
            }, 0.88, "representation_decision", False, max_depth=2, max_items=4, max_keys=6)

        # A tool/search/calculation source is not the answer itself; it is the source
        # requirement that Executor/Provider must honor.
        if source == "web":
            add(required, "WEB_REQUIREMENT", {
                "search_required": True,
                "freshness_required": bool(knowledge.get("freshness_required")),
                "evidence_required": True,
            }, 0.91, "current_turn_requires_web_evidence", True, max_depth=2, max_items=4, max_keys=6)
        elif source == "calculation":
            add(optional, "CALCULATION_REQUIREMENT", {
                "calculation_required": True,
                "use_current_request_operands_only": True,
            }, 0.86, "current_turn_computation", False, max_depth=2, max_items=4, max_keys=5)

        if source in {"vision", "file"}:
            add(required, "MODALITY_REQUIREMENT", {
                "source": source,
                "current_turn_only": True,
            }, 0.90, "current_turn_external_input", True, max_depth=2, max_items=3, max_keys=5)

        # Stable semantic order: high priority first, current turn protected first.
        required.sort(key=lambda x: (-float(x.get("priority", 0.0)), x.get("key", "")))
        optional.sort(key=lambda x: (-float(x.get("priority", 0.0)), x.get("key", "")))

        if rel == "NEW":
            soft_target = PROVIDER_INPUT_SOFT_TARGET_NEW
        elif rel == "RECALL":
            soft_target = PROVIDER_INPUT_SOFT_TARGET_RECALL
        else:
            soft_target = PROVIDER_INPUT_SOFT_TARGET_CONTINUE

        provider_sections = [
            {
                "name": item["key"],
                "value": item["value"],
                "priority": item["priority"],
                "protected": item["protected"],
                "reason": item["reason"],
            }
            for item in required + optional
        ]

        return {
            "version": self.VERSION,
            "mode": "dependency_first",
            "relation": rel,
            "turn_relation": turn_rel,
            "hard_budget_tokens": PROVIDER_INPUT_HARD_BUDGET,
            "soft_target_tokens": soft_target,
            "current_user_request": raw_request,
            "current_request_authoritative": True,
            "current_request_may_be_compacted_only_for_budget": True,
            "context_selection_done_before_provider": True,
            "provider_must_not_reselect_context": True,
            "memory_policy": (
                "explicit_recall_with_semantic_slider" if rel == "RECALL" and history_search.get("memory_slider", {}).get("selected_memory_operand")
                else "selected_authenticated_branch_plus_semantic_slider" if rel == "CONTINUE" and history_search.get("memory_slider", {}).get("selected_memory_operand")
                else "explicit_recall_only" if rel == "RECALL"
                else "selected_authenticated_branch_only" if rel == "CONTINUE"
                else "disabled"
            ),
            "branch_index": {
                "version": self._text((relation.get("branch_index") or {}).get("version") or "dialogue_branch_index_v1_user_bound"),
                "active_sequence_id": self._text((relation.get("branch_index") or {}).get("active_sequence_id")),
                "target_sequence_id": self._text((relation.get("branch_index") or {}).get("target_sequence_id")),
                "target_branch_id": self._text((relation.get("branch_index") or {}).get("target_branch_id")),
                "active_branch_id": self._text(((relation.get("branch_index") or {}).get("active_branch") or {}).get("branch_id")),
                "resolution_mode": self._text((relation.get("branch_index") or {}).get("resolution_mode")),
                "selected_score": float((relation.get("branch_index") or {}).get("selected_score") or 0.0),
            },
            "required_context": required,
            "optional_context": optional,
            "excluded_context": excluded,
            "provider_sections": provider_sections,
            "active_topic": active_topic,
            "active_entity": active_entity,
            "active_task": bool(active_task),
            "knowledge_source": source,
            "continuation_analysis": continuity if rel == "CONTINUE" else {},
            "history_search": history_search if rel in {"CONTINUE", "RECALL"} else {},
            "result_dependency": {
                "carry_forward": history_search.get("carry_forward_result") or {},
                "operand_anchor": history_search.get("operand_anchor") or {},
            },
            "selection_basis": [
                "current_user_request",
                "authenticated_scope",
                "dialogue_relation",
                "active_task",
                "semantic_intent",
                "domain",
                "entity/reference",
                "memory_relevance",
                "dialogue_history_search",
                "semantic_memory_slider",
                "knowledge_source",
                "representation",
                "response_strategy",
                "dialogue_development",
            ],
            "budget_policy": "relevance_first_then_progressive_compression",
            "provider_role": "consume_plan_and_answer_current_request",
            "new_topic_minimal_context": bool(rel == "NEW"),
            "continuation_interest": (
                {
                    "mode": "RESUME_BRANCH" if turn_rel == "RESUME_BRANCH" else "CONTINUE_BRANCH",
                    "branch_id": self._text(
                        relation.get("target_branch_id")
                        or (relation.get("branch_index") or {}).get("target_branch_id")
                        or ((relation.get("branch_index") or {}).get("active_branch") or {}).get("branch_id")
                    ),
                    "sequence_id": self._text(
                        relation.get("target_sequence_id")
                        or (relation.get("branch_index") or {}).get("target_sequence_id")
                        or ((relation.get("branch_index") or {}).get("active_branch") or {}).get("sequence_id")
                    ),
                    "topic": active_topic,
                    "entity": active_entity,
                    "current_request": raw_request,
                    "next_step": self._text(continuity.get("next_logical_step")),
                }
                if rel == "CONTINUE" else {}
            ),
            "dialogue_development": {
                "version": self._text(dialogue_development.get("version") or "dialogue_development_v1_single_route"),
                "authoritative": True,
                "route": "single_dialogue_route",
            },
            "exclusions_are_authoritative": True,
            "confidence": 0.97 if consistency.get("valid") else 0.72,
        }


class ObligationEngine(InterpretationEngineBase):
    """Extract and carry user-visible commitments without hard-coding one reward.

    An obligation is a dialogue fact, not a renderer command.  It becomes an
    executable trigger only when its condition is satisfied by the current turn.
    """
    NAME = "ObligationEngine"
    VERSION = "obligations_v2_generic"

    _IF_PATTERNS = (
        re.compile(r"если\s+(.+?)\s*[,—-]\s*(?:то\s+)?(.+)$", re.I),
        re.compile(r"если\s+(.+?)\s+то\s+(.+)$", re.I),
        re.compile(r"if\s+(.+?)\s*,?\s*then\s+(.+)$", re.I),
        re.compile(r"после\s+того\s+как\s+(.+?)\s*[,—-]\s*(.+)$", re.I),
        re.compile(r"когда\s+(?:будет\s+)?(?:получен|получим|получишь|достигнут|достигнем)\s+(.+?)\s*[,—-]\s*(.+)$", re.I),
        re.compile(r"после\s+(?:достижения|получения|достижении)\s+(.+?)\s*[,—-]\s*(.+)$", re.I),
    )

    @classmethod
    def _normalize_condition(cls, value: str) -> str:
        value = cls._text(value).lower()
        if any(x in value for x in ("правильн", "угад", "решишь", "решит", "correct", "solve")):
            return "user_answer_correct"
        if any(x in value for x in ("ошиб", "не угада", "неправиль", "incorrect", "wrong")):
            return "user_answer_incorrect"
        if any(x in value for x in ("ответ", "ответишь", "ответит", "answer")):
            return "user_answer_received"
        if any(x in value for x in ("результат", "результата", "результат готов", "получим", "получен", "получишь", "достигнем", "достигнут", "итог", "цель достиг")):
            return "after_result"
        return "condition:" + value[:180]

    @classmethod
    def _action_payload(cls, action: str) -> dict[str, Any]:
        low = cls._low(action)
        representation = "text"
        if any(x in low for x in ("картин", "изображ", "нарис", "рисунок", "фото")):
            representation = "image"
        elif any(x in low for x in ("галере", "несколько изображ")):
            representation = "gallery"
        elif any(x in low for x in ("таблиц",)):
            representation = "table"
        elif any(x in low for x in ("схем", "диаграм")):
            representation = "diagram"
        elif any(x in low for x in ("график", "графика")):
            representation = "graph"
        elif "код" in low or "python" in low:
            representation = "code"

        target = ""
        if representation == "image":
            for cue in ("картинку", "изображение", "картинка", "рисунок", "фото"):
                if cue in low:
                    tail = low.split(cue, 1)[1].strip(" .,:;—-")
                    target = tail[:180]
                    break
        return {
            "action": "render" if representation != "text" else "answer",
            "representation": representation,
            "target": target,
            "instruction": cls._text(action),
        }

    @classmethod
    def _existing(cls, state: dict[str, Any], task: dict[str, Any], history: list[Any]) -> list[dict[str, Any]]:
        candidates: list[Any] = []
        for owner in (state, task):
            if isinstance(owner, dict):
                for key in ("obligations", "dialogue_obligations", "commitments", "promises", "pending_obligations"):
                    value = owner.get(key)
                    if isinstance(value, list):
                        candidates.extend(value)
        out = []
        seen = set()
        for item in candidates:
            if not isinstance(item, dict):
                continue
            oid = cls._text(item.get("id") or item.get("obligation_id"))
            if not oid:
                oid = cls._fingerprint(item.get("source") or item.get("instruction") or repr(item))
            if oid in seen:
                continue
            seen.add(oid)
            normalized = dict(item)
            normalized["id"] = oid
            normalized.setdefault("status", "pending")
            normalized.setdefault("source", "state")
            out.append(normalized)
        return out[-24:]

    def analyze(self, text: str, *, state: dict[str, Any], task: dict[str, Any], history: list[Any]) -> dict[str, Any]:
        existing = self._existing(state, task.get("task") if task.get("active") else {}, history)
        found: list[dict[str, Any]] = []
        for pattern in self._IF_PATTERNS:
            match = pattern.search(self._text(text))
            if not match:
                continue
            condition, action = match.group(1), match.group(2)
            payload = self._action_payload(action)
            found.append({
                "id": self._fingerprint(text),
                "condition": self._normalize_condition(condition),
                "condition_type": self._normalize_condition(condition),
                "condition_text": self._text(condition),
                "action": payload["action"],
                "trigger_mode": "semantic_milestone" if self._normalize_condition(condition) == "after_result" else "semantic_condition",
                "created_turn_id": int(state.get("april_turn_id") or 0),
                "representation": payload["representation"],
                "target": payload["target"],
                "instruction": payload["instruction"],
                "status": "pending",
                "source": "current_user_turn",
                "created_from": self._text(text),
            })
            break

        merged = existing[:]
        known = {item.get("id") for item in merged}
        for item in found:
            if item["id"] not in known:
                merged.append(item)
                known.add(item["id"])

        low = self._low(text)
        triggers: list[dict[str, Any]] = []
        correctness = None
        if any(x in low for x in ("правильный ответ", "угадал", "решил", "верный ответ", "correct answer")):
            correctness = True
        elif any(x in low for x in ("не угадал", "ошибся", "неправильный ответ", "wrong answer")):
            correctness = False

        for item in merged:
            if item.get("status") not in {"pending", "active", "ready"}:
                continue
            condition = self._text(item.get("condition"))
            matched = (
                condition == "user_answer_correct" and correctness is True
            ) or (
                condition == "user_answer_incorrect" and correctness is False
            ) or (
                condition == "user_answer_received" and bool(text)
            )
            if matched:
                triggers.append({**item, "triggered": True, "trigger_turn": self._text(text)})
            elif condition == "after_result":
                result_event = state.get("dialogue_result_event") if isinstance(state.get("dialogue_result_event"), dict) else {}
                try:
                    created_turn = int(item.get("created_turn_id") or 0)
                    result_turn = int(result_event.get("turn_id") or 0)
                except (TypeError, ValueError):
                    created_turn, result_turn = 0, 0
                if bool(result_event.get("completed")) and result_turn > created_turn:
                    item["status"] = "ready"
                    item["ready_reason"] = "result_milestone_reached"

        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "obligations": merged,
            "new_obligations": found,
            "triggered": triggers,
            "pending_count": sum(1 for x in merged if x.get("status") in {"pending", "active", "ready"}),
            "confidence": 0.96 if (found or triggers) else 0.84,
        }


class VisualMemoryEngine(InterpretationEngineBase):
    """Build a renderer-neutral visual projection from explicit stored facts.

    It never invents appearance.  Only facts already present in state/memory
    under visual/Nia/profile namespaces are forwarded to visual renderers.
    """
    NAME = "VisualMemoryEngine"
    VERSION = "visual_memory_v2_renderer_neutral"

    VISUAL_KEYS = (
        "visual_memory", "visual_facts", "visual_profile", "render_memory",
        "nia_visual_memory", "nia_profile", "character_profile", "appearance",
    )

    def analyze(self, *, state: dict[str, Any], memory: dict[str, Any], entity: dict[str, Any], text: str) -> dict[str, Any]:
        source_items: list[dict[str, Any]] = []
        for key in self.VISUAL_KEYS:
            value = state.get(key)
            if isinstance(value, dict):
                source_items.append({"source": key, "data": value})
            elif isinstance(value, list):
                source_items.append({"source": key, "data": value})

        active_sequence = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        last_visual_attachment = active_sequence.get("last_visual_attachment") if isinstance(active_sequence.get("last_visual_attachment"), dict) else {}
        if last_visual_attachment:
            source_items.append({
                "source": "active_dialogue_sequence.visual_attachment",
                "data": deepcopy(last_visual_attachment),
            })

        selected: list[dict[str, Any]] = []
        for item in source_items:
            selected.append(item)

        active_entity = self._text(entity.get("active_entity"))
        is_visual_request = any(x in self._low(text) for x in (
            "картин", "изображ", "нарис", "покажи", "визуал", "галере", "схем", "диаграм"
        ))
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "active_entity": active_entity,
            "available": bool(selected),
            "explicit_only": True,
            "visual_memory": selected,
            "memory_refs": list(memory.get("selected") or []) if is_visual_request else [],
            "for_renderer": is_visual_request,
            "do_not_invent_visual_facts": True,
            "confidence": 0.95 if selected else 0.72,
        }


class SemanticSynchronizationEngine(InterpretationEngineBase):
    """Final internal contract: one synchronized semantic state for downstream engines."""
    NAME = "SemanticSynchronizationEngine"
    VERSION = "semantic_sync_v3"

    def build(self, *, current_turn: dict[str, Any], arbitration: dict[str, Any], topic: dict[str, Any],
              task: dict[str, Any], entity: dict[str, Any], reference: dict[str, Any],
              representation: dict[str, Any], obligations: dict[str, Any], visual_memory: dict[str, Any],
              memory: dict[str, Any], continuity: dict[str, Any], dialogue_development: dict[str, Any] | None = None) -> dict[str, Any]:
        relation = self._text(arbitration.get("relation") or "NEW")
        return {
            "engine": self.NAME,
            "version": self.VERSION,
            "authoritative": True,
            "current_user_request": self._text(current_turn.get("raw_text")),
            "relation": relation,
            "topic": self._text(arbitration.get("active_topic") or topic.get("topic")),
            "active_entity": self._text(arbitration.get("active_entity") or entity.get("active_entity")),
            "task": task.get("task") if task.get("active") else {},
            "reference": reference,
            "representation": self._text(representation.get("representation") or "text"),
            "obligations": obligations.get("obligations", []),
            "triggered_obligations": obligations.get("triggered", []),
            "dialogue_development": dialogue_development or {},
            "visual_memory": visual_memory,
            "memory": memory,
            "continuity": continuity,
            "authority_order": [
                "current_user_turn", "explicit_discourse", "active_task",
                "active_topic", "resolved_reference", "selected_memory", "semantic_similarity",
            ],
            "no_renderer_owns_semantics": True,
            "no_history_replaces_current_turn": True,
            "confidence": min(
                float(arbitration.get("confidence", 0.0) or 0.0),
                float(obligations.get("confidence", 0.0) or 0.0),
                float(visual_memory.get("confidence", 0.0) or 0.0),
            ),
        }


class InterpretationOrchestrator(InterpretationEngineBase):
    NAME = "InterpretationOrchestrator"
    VERSION = "cognitive_interpretation_environment_v1"

    def __init__(self):
        self.identity = IdentityScopeEngine()
        self.current_turn = CurrentTurnEngine()
        self.branch_index = DialogueBranchIndexEngine()
        self.dialogue = DialogueRelationEngine()
        self.task = ActiveTaskEngine()
        self.entity = EntityResolutionEngine()
        self.topic = TopicDynamicsEngine()
        self.intent = SemanticIntentEngine()
        self.domain = DomainReasoningEngine()
        self.reference = ReferenceResolutionEngine()
        self.memory = MemoryRelevanceEngine()
        self.history_search = DialogueHistorySearchEngine()
        self.memory_slider = DialogueMemorySliderEngine()
        self.continuity = ConversationContinuityEngine()
        self.knowledge = KnowledgeSourceEngine()
        self.representation = RepresentationDecisionEngine()
        self.strategy = ResponseStrategyEngine()
        self.arbitration = DecisionArbitrationEngine()
        self.consistency = ConsistencyEngine()
        self.canonical = CanonicalizationEngine()
        self.provider_context = ProviderContextPlanEngine()
        self.obligations = ObligationEngine()
        self.visual_memory = VisualMemoryEngine()
        self.dialogue_development = DialogueDevelopmentEngine()
        self.semantic_anchor = SemanticContextAnchorEngine()
        self.semantic_sync = SemanticSynchronizationEngine()

    def run(
        self,
        text: str,
        *,
        state: dict[str, Any],
        history: list[Any],
        semantic: dict[str, Any],
        cognition: dict[str, Any],
    ) -> dict[str, Any]:
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []
        semantic = semantic if isinstance(semantic, dict) else {}
        cognition = cognition if isinstance(cognition, dict) else {}

        identity = self.identity.analyze(state)
        current_turn = self.current_turn.analyze(
            text, semantic=semantic, cognition=cognition, state=state, identity=identity
        )

        branch_index = self.branch_index.analyze(
            text, state=state, history=history, identity=identity
        )

        # The existing environment is a specialized dialogue/task engine. It is
        # consulted here as evidence, then its result is reconciled by arbitration.
        relation = self.dialogue.analyze(
            text, state=state, history=history, semantic=semantic, identity=identity,
            branch_index=branch_index,
        )

        identity_disclosure = relation.get("environment", {}).get("identity_disclosure") if isinstance(relation.get("environment"), dict) else {}
        if isinstance(identity_disclosure, dict) and identity_disclosure.get("name"):
            profile = state.get("user_profile")
            if not isinstance(profile, dict):
                profile = {}
            profile.update({
                "name": self._text(identity_disclosure.get("name")),
                "name_source": self._text(identity_disclosure.get("source") or "dialogue"),
                "updated_at": time.time(),
            })
            state["user_profile"] = profile

        task = self.task.analyze(text, relation=relation, state=state, history=history)

        # Resolve the current semantic object before topic dynamics.  Topic root and
        # moving focus are related but not identical; this prevents stale topic state
        # from winning simply because topic was computed first.
        entity = self.entity.analyze(
            text, relation=relation, topic={}, task=task, semantic=semantic, state=state,
            branch_index=branch_index,
        )

        # Topic dynamics consumes the task and entity evidence instead of re-deriving
        # ownership from the raw request alone.
        relation_with_task = dict(relation)
        relation_with_task["active_task_engine"] = task
        if task.get("active") and isinstance(task.get("task"), dict):
            relation_with_task["active_task"] = task.get("task")
        topic = self.topic.analyze(
            text, relation=relation_with_task, semantic=semantic, state=state,
            branch_index=branch_index, entity=entity,
        )

        # Quantum matrix measurement is an evidence engine. This call is safe:
        # during normal execution QUANTUM_INTERPRETATION_ENGINE already exists.
        try:
            measurement = QUANTUM_INTERPRETATION_ENGINE.measure(
                self._text(text),
                previous_assistant=self._text(relation.get("previous_april_turn")),
                previous_user=self._text(relation.get("previous_user_turn")),
                active_topic=self._text(topic.get("topic")),
                active_goal=self._text(task.get("goal")),
                modalities=current_turn.get("modalities", {}),
            )
        except Exception as exc:
            measurement = {
                "dialogue_scores": {},
                "representation_scores": {"text": 1.0},
                "domain_scores": {},
                "capability_scores": {},
                "context_scores": {},
                "scene_matrix": {},
                "engine_error": str(exc),
            }

        intent = self.intent.analyze(
            text, semantic_measurement=measurement, relation=relation, task=task
        )
        domain = self.domain.analyze(
            text, semantic_measurement=measurement, relation=relation, intent=intent
        )
        reference = self.reference.analyze(
            text, relation=relation, entity=entity, topic=topic, task=task,
            branch_index=branch_index,
        )
        memory = self.memory.analyze(
            text, relation=relation, topic=topic, identity=identity, state=state
        )
        history_search = self.history_search.analyze(
            text, relation=relation, topic=topic, identity=identity, state=state,
            history=history, task=task, reference=reference,
        )

        # Semantic memory slider: only CONTINUE/RECALL turns may scan the seven-day
        # dialogue. NEW vectors deliberately bypass this mechanism.
        current_relation_value = self._text(relation.get("relation") or "NEW").upper()
        memory_slider = self.memory_slider.scan(
            text,
            relation=current_relation_value,
            identity=identity,
            state=state,
            history=history,
            active_topic=self._text(topic.get("topic") or topic.get("topic_root")),
            active_entity=self._text(entity.get("active_entity")),
            active_goal=self._text(task.get("goal")),
            task=task,
        )
        history_search = deepcopy(history_search)
        history_search["memory_slider"] = memory_slider

        if memory_slider.get("enabled") and memory_slider.get("selected_memory_operand"):
            selected_operand = deepcopy(memory_slider.get("selected_memory_operand") or {})
            selected_record = deepcopy(memory_slider.get("selected_memory_record") or {})
            history_search["selected_memory_index"] = int(memory_slider.get("selected_memory_index", -1)) if str(memory_slider.get("selected_memory_index", -1)).strip() not in {"", "None"} else -1
            history_search["selected_memory_record"] = selected_record
            history_search["selected_memory_operand"] = selected_operand
            history_search["history_context_required"] = True
            history_search["recommended_turn_relation"] = (
                "HISTORY_SUPPORTED_CONTINUATION"
                if current_relation_value == "CONTINUE"
                else "HISTORY_LOOKUP"
            )
            history_search["provider_instruction"] = (
                "Use the selected chronological seven-day dialogue operand to resolve "
                "the current continuation before answering. Keep the current user "
                "request authoritative and do not invent missing historical details."
            )
            history_search["selection_mode"] = "dialogue_memory_slider"

            selected_evidence = list(history_search.get("selected_evidence") or [])
            if selected_record:
                primary_key = (
                    selected_record.get("turn_id"),
                    selected_record.get("sequence_id"),
                    self._text(selected_record.get("user")),
                    self._text(selected_record.get("assistant")),
                )
                filtered = []
                for item in selected_evidence:
                    if not isinstance(item, dict):
                        continue
                    item_key = (
                        item.get("turn_id"),
                        item.get("sequence_id"),
                        self._text(item.get("user")),
                        self._text(item.get("assistant")),
                    )
                    if item_key != primary_key:
                        filtered.append(item)
                history_search["selected_evidence"] = [selected_operand] + filtered

            memory = deepcopy(memory)
            selected_memory = list(memory.get("selected") or []) if isinstance(memory, dict) else []
            memory["selected"] = [selected_operand] + [
                item for item in selected_memory if isinstance(item, dict) and (
                    item.get("sequence_id") != selected_operand.get("sequence_id")
                    or item.get("turn_id") != selected_operand.get("turn_id")
                )
            ]
            memory["allowed"] = True
            memory["selection_mode"] = "dialogue_memory_slider"
            memory["slider_enabled"] = True
        else:
            history_search["selected_memory_index"] = -1
            history_search["selected_memory_record"] = {}
            history_search["selected_memory_operand"] = {}

        continuity = self.continuity.analyze(
            text, relation=relation, topic=topic, task=task, entity=entity, reference=reference,
            history_search=history_search,
        )
        knowledge = self.knowledge.analyze(
            text, intent=intent, domain=domain, current_turn=current_turn,
            memory=memory, relation=relation
        )
        representation = self.representation.analyze(
            text, semantic_measurement=measurement, intent=intent,
            current_turn=current_turn
        )
        obligations = self.obligations.analyze(
            text, state=state, task=task, history=history
        )
        visual_memory = self.visual_memory.analyze(
            state=state, memory=memory, entity=entity, text=text
        )
        dialogue_development = self.dialogue_development.analyze(
            text, state=state, relation=relation, topic=topic, task=task, entity=entity,
            history_search=history_search, continuity=continuity, obligations=obligations,
            visual_memory=visual_memory,
        )

        # Synthesize the durable semantic anchor before arbitration/provider planning.
        # This is where topic root, current focus, entity, direction and development
        # become one coherent object instead of five competing state fields.
        semantic_anchor = self.semantic_anchor.build(
            current_turn=current_turn,
            relation=relation,
            topic=topic,
            task=task,
            intent=intent,
            domain=domain,
            entity=entity,
            reference=reference,
            continuity=continuity,
            branch_index=branch_index,
            history_search=history_search,
            representation=representation,
            dialogue_development=dialogue_development,
            state=state,
        )
        # The synthesized anchor is the semantic authority for topic/focus/entity.
        # Align the development packet to it so Provider never receives a recalled
        # topic mixed with the current active branch (e.g. Tesla + сценарий).
        if isinstance(dialogue_development, dict):
            dialogue_development = deepcopy(dialogue_development)
            dialogue_development["relation"] = semantic_anchor.get("relation")
            dialogue_development["topic_root"] = semantic_anchor.get("topic_root")
            dialogue_development["active_focus"] = semantic_anchor.get("active_focus")
            dialogue_development["active_entity"] = semantic_anchor.get("primary_entity")
            dialogue_development["current_step"] = (
                semantic_anchor.get("development", {}).get("current_step")
                if isinstance(semantic_anchor.get("development"), dict)
                else semantic_anchor.get("active_focus")
            )
            dialogue_development["next_step"] = semantic_anchor.get("next_step")
            if semantic_anchor.get("relation") == "RECALL":
                dialogue_development["status"] = "memory_recalled"
        state["semantic_anchor"] = deepcopy(semantic_anchor)
        state["dialogue_development"] = deepcopy(dialogue_development)
        semantic_anchor["development"] = deepcopy(dialogue_development) if semantic_anchor.get("relation") == "RECALL" else semantic_anchor.get("development")
        state["active_topic_root"] = self._text(semantic_anchor.get("topic_root"))
        state["active_dialogue_focus"] = self._text(semantic_anchor.get("active_focus"))
        state["active_entity"] = self._text(semantic_anchor.get("primary_entity"))
        state["current_object"] = self._text(semantic_anchor.get("primary_entity"))
        state["dialogue_direction"] = self._text(semantic_anchor.get("direction"))
        state["dialogue_development"] = deepcopy(semantic_anchor.get("development") or dialogue_development)

        # An obligation can explicitly request a representation after its trigger.
        # This is a semantic override, not a hard-coded fireworks/image rule.
        triggered = obligations.get("triggered") or []
        if triggered and any(item.get("representation") for item in triggered):
            representation = dict(representation)
            representation["representation"] = triggered[0].get("representation") or representation.get("representation")
            representation["explicit"] = True
            representation["source"] = "triggered_obligation"
            representation["obligation_id"] = triggered[0].get("id")
        strategy = self.strategy.analyze(
            text, relation=relation, intent=intent, task=task,
            continuity=continuity, representation=representation, knowledge=knowledge
        )

        arbitration = self.arbitration.decide(
            current_turn=current_turn,
            relation=relation,
            topic=topic,
            task=task,
            intent=intent,
            entity=entity,
            reference=reference,
            memory=memory,
            continuity=continuity,
            knowledge=knowledge,
            representation=representation,
            history_search=history_search,
            semantic_anchor=semantic_anchor,
        )
        semantic_sync = self.semantic_sync.build(
            current_turn=current_turn, arbitration=arbitration, topic=topic, task=task,
            entity=entity, reference=reference, representation=representation,
            obligations=obligations, visual_memory=visual_memory, memory=memory, continuity=continuity,
            dialogue_development=dialogue_development
        )
        semantic_sync["semantic_anchor"] = deepcopy(semantic_anchor)
        consistency = self.consistency.validate(
            current_turn=current_turn,
            identity=identity,
            relation=arbitration,
            arbitration=arbitration,
            memory=memory,
            entity=entity,
            task=task,
            representation=representation,
            semantic_anchor=semantic_anchor,
        )
        canonical = self.canonical.build(
            current_turn=current_turn,
            identity=identity,
            relation=relation,
            topic=topic,
            task=task,
            intent=intent,
            domain=domain,
            entity=entity,
            reference=reference,
            memory=memory,
            continuity=continuity,
            knowledge=knowledge,
            representation=representation,
            strategy=strategy,
            arbitration=arbitration,
            consistency=consistency,
            semantic_anchor=semantic_anchor,
        )

        provider_context_plan = self.provider_context.build(
            current_turn=current_turn,
            relation=relation,
            topic=topic,
            task=task,
            intent=intent,
            domain=domain,
            entity=entity,
            reference=reference,
            memory=memory,
            continuity=continuity,
            knowledge=knowledge,
            representation=representation,
            strategy=strategy,
            arbitration=arbitration,
            consistency=consistency,
            history_search=history_search,
            identity_memory=state.get("user_profile") if isinstance(state.get("user_profile"), dict) else {},
            dialogue_development=dialogue_development,
            semantic_anchor=semantic_anchor,
        )
        canonical["provider_context_plan"] = provider_context_plan
        canonical["dialogue_development"] = dialogue_development
        canonical["semantic_anchor"] = deepcopy(semantic_anchor)
        canonical["obligations"] = obligations
        canonical["visual_memory"] = visual_memory
        canonical["semantic_synchronization"] = semantic_sync

        workspace = {
            "version": self.VERSION,
            "current_request": current_turn["raw_text"],
            "current_request_raw": current_turn["raw_text"],
            "current_user_request": current_turn["raw_text"],
            "current_turn": current_turn,
            "dialogue_branch_index": branch_index,
            "authenticated_scope": identity["scope"],
            "identity_scope": identity,
            "user_profile": deepcopy(state.get("user_profile") if isinstance(state.get("user_profile"), dict) else {}),
            "dialogue_relation": relation,
            "topic_dynamics": topic,
            "active_task": task,
            "semantic_intent": intent,
            "domain_reasoning": domain,
            "entity_resolution": entity,
            "reference_resolution": reference,
            "memory_relevance": memory,
            "dialogue_history_search": history_search,
            "memory_slider": deepcopy(memory_slider),
            "selected_memory_index": (
                int(memory_slider.get("selected_memory_index", -1))
                if str(memory_slider.get("selected_memory_index", -1)).strip() not in {"", "None"}
                and memory_slider.get("selected_memory_operand") else -1
            ),
            "selected_memory_operand": deepcopy(memory_slider.get("selected_memory_operand") or {}),
            "selected_memory_record": deepcopy(memory_slider.get("selected_memory_record") or {}),
            "conversation_continuity": continuity,
            "knowledge_source": knowledge,
            "representation_decision": representation,
            "response_strategy": strategy,
            "obligations": obligations,
            "dialogue_development": dialogue_development,
            "visual_memory": visual_memory,
            "semantic_synchronization": semantic_sync,
            "arbitration": arbitration,
            "consistency": consistency,
            "canonical": canonical,
            "provider_context_plan": provider_context_plan,
            "provider_context_authority": "INTERPRETATION",
            "provider_context_plan_version": provider_context_plan.get("version"),
            "provider_hard_input_budget": provider_context_plan.get("hard_budget_tokens", PROVIDER_INPUT_HARD_BUDGET),
            "provider_soft_input_target": provider_context_plan.get("soft_target_tokens"),
            "provider_context_required": provider_context_plan.get("required_context", []),
            "provider_context_optional": provider_context_plan.get("optional_context", []),
            "provider_context_excluded": provider_context_plan.get("excluded_context", []),
            # Flat authoritative fields for downstream adapters.
            "relation": arbitration["relation"],
            "turn_relation": arbitration["turn_relation"],
            "continuation": arbitration["relation"] == "CONTINUE",
            "reference": arbitration["relation"] == "RECALL",
            "conversation_continuation": bool(identity["scope"].get("conversation_id")),
            "sequence_id": self._text(
                arbitration.get("target_sequence_id")
                or relation.get("target_sequence_id")
                or identity["scope"].get("dialogue_sequence_id", "")
            ),
            "target_sequence_id": self._text(arbitration.get("target_sequence_id") or relation.get("target_sequence_id")),
            "target_branch_id": self._text(arbitration.get("target_branch_id") or relation.get("target_branch_id")),
            "active_topic": canonical["topic"]["active"],
            "active_topic_root": self._text(semantic_anchor.get("topic_root")),
            "active_focus": self._text(semantic_anchor.get("active_focus")),
            "active_entity": canonical["semantic"]["active_entity"],
            "entity_type": self._text(semantic_anchor.get("entity_type")),
            "dialogue_direction": self._text(semantic_anchor.get("direction")),
            "dialogue_development": deepcopy(semantic_anchor.get("development") or dialogue_development),
            "semantic_anchor": deepcopy(semantic_anchor),
            "operation": canonical["semantic"]["operation"],
            "goal": canonical["semantic"]["goal"],
            "representation": canonical["representation"]["representation"],
            "current_user_request": canonical["current_user_request"],
            "canonical_user_request": canonical["canonical_user_request"],
            "provider_instruction": canonical["execution_instruction"],
            "selected_memory": canonical["memory"]["selected"],
            "historical_memory_allowed": canonical["memory"]["allowed"],
            "active_task_context": canonical["task"],
            "continuation_content_analysis": continuity,
            "dialogue_history_search": history_search,
            "result_dependency": {
                "latest_operation_result": history_search.get("latest_operation_result", {}),
                "carry_forward_result": history_search.get("carry_forward_result", {}),
                "operand_anchor": history_search.get("operand_anchor", {}),
            },
            "avoid_repeat_content": continuity.get("avoid_repeat_content", []),
            "provider_request_authority": "CURRENT_USER_TURN",
            "historical_topics_are_evidence_only": True,
            "engine_order": [
                self.identity.NAME,
                self.current_turn.NAME,
                self.branch_index.NAME,
                self.dialogue.NAME,
                self.task.NAME,
                self.intent.NAME,
                self.domain.NAME,
                self.entity.NAME,
                self.topic.NAME,
                self.reference.NAME,
                self.memory.NAME,
                self.history_search.NAME,
                self.memory_slider.NAME,
                self.continuity.NAME,
                self.knowledge.NAME,
                self.representation.NAME,
                self.strategy.NAME,
                self.semantic_anchor.NAME,
                self.arbitration.NAME,
                self.consistency.NAME,
                self.canonical.NAME,
                self.provider_context.NAME,
            ],
            "provider_context_authority": "INTERPRETATION",
            "provider_must_not_reselect_context": True,
        }

        return {
            "workspace": workspace,
            "canonical": canonical,
            "engines": {
                "identity": identity,
                "current_turn": current_turn,
                "branch_index": branch_index,
                "dialogue": relation,
                "topic": topic,
                "task": task,
                "intent": intent,
                "domain": domain,
                "entity": entity,
                "reference": reference,
                "memory": memory,
                "continuity": continuity,
                "knowledge": knowledge,
                "representation": representation,
                "strategy": strategy,
                "arbitration": arbitration,
                "consistency": consistency,
                "canonicalization": canonical,
                "provider_context": provider_context_plan,
            },
        }


INTERPRETATION_ORCHESTRATOR = InterpretationOrchestrator()


class QuantumInterpretationEngine:
    """One engine: linguistic evidence + semantic matrix + context fusion."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache: dict[tuple, dict[str, Any]] = {}
        self._cache_limit = 256
        self._vectorizer = None
        self._prototype_matrix = None
        self._prototype_index: dict[str, list[int]] = {}
        self._semantic_encoder = None
        self._nli = None
        self._runtime_ready = True
        self._heavy_ready = False
        self._compile_matrix()

    @staticmethod
    def _text(value: Any) -> str:
        """Compatibility normalization used by all semantic adapters."""
        return QuantumInterpretationEngine.normalize(value)

    # ----------------------------- primitives -----------------------------

    @staticmethod
    def normalize(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", text.lower())

    def _compile_matrix(self) -> None:
        docs: list[str] = []
        families = (
            ("dialogue", SEMANTIC_TURN_PROTOTYPES),
            ("representation", REPRESENTATION_HYPOTHESES),
            ("domain", DOMAIN_HYPOTHESES),
            ("capability", CAPABILITY_HYPOTHESES),
        )
        self._prototype_index = {}
        for family, vocab in families:
            for label, description in vocab.items():
                self._prototype_index.setdefault(f"{family}:{label}", []).append(len(docs))
                docs.append(description)

        if TfidfVectorizer is not None and docs:
            self._vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5),
                lowercase=True, sublinear_tf=True,
            )
            self._prototype_matrix = self._vectorizer.fit_transform(docs)

    def _tfidf_scores(self, text: str) -> dict[str, dict[str, float]]:
        families = {
            "dialogue": SEMANTIC_TURN_PROTOTYPES,
            "representation": REPRESENTATION_HYPOTHESES,
            "domain": DOMAIN_HYPOTHESES,
            "capability": CAPABILITY_HYPOTHESES,
        }
        if not text:
            return {name: {key: 0.0 for key in values} for name, values in families.items()}

        if self._vectorizer is None or self._prototype_matrix is None or cosine_similarity is None:
            # Tiny deterministic semantic sketch for environments without sklearn.
            token_set = set(self._tokens(text))
            out: dict[str, dict[str, float]] = {}
            for family, vocab in families.items():
                out[family] = {}
                for label, description in vocab.items():
                    words = set(self._tokens(description))
                    overlap = len(token_set & words)
                    out[family][label] = min(1.0, overlap / max(2.0, len(words) * 0.20))
            return out

        q = self._vectorizer.transform([text])
        sim = cosine_similarity(q, self._prototype_matrix)[0]
        out = {}
        offset = 0
        for family, vocab in families.items():
            fam = {}
            for label in vocab:
                # prototypes are inserted contiguously by family
                fam[label] = max(0.0, min(1.0, float(sim[offset])))
                offset += 1
            out[family] = fam
        return out

    def _context_scores(
        self, text: str, previous_assistant: str, previous_user: str, active_topic: str, active_goal: str
    ) -> dict[str, float]:
        if not text:
            return {"previous_assistant": 0.0, "previous_user": 0.0, "active_topic": 0.0, "active_goal": 0.0}
        scores = {"previous_assistant": 0.0, "previous_user": 0.0, "active_topic": 0.0, "active_goal": 0.0}
        query = set(self._tokens(text))
        for key, value in (
            ("previous_assistant", previous_assistant),
            ("previous_user", previous_user),
            ("active_topic", active_topic),
            ("active_goal", active_goal),
        ):
            words = set(self._tokens(self.normalize(value)))
            scores[key] = (
                len(query & words) / max(1.0, min(len(query), len(words)))
                if query and words else 0.0
            )
        return scores

    def _linguistic(self, text: str) -> dict[str, Any]:
        tokens = self._tokens(text)
        return {
            "language": None,
            "tokens": tokens,
            "lemmas": tokens,
            "pos": [],
            "dependencies": [],
            "entities": [],
            "sentences": [text] if text else [],
            "source": "quantum_matrix_lightweight",
            "engine": "quantum_interpretation_engine",
        }

    # ----------------------------- matrix core ----------------------------

    def _feature_vector(
        self,
        dialogue: dict[str, float],
        representation: dict[str, float],
        domain: dict[str, float],
        capability: dict[str, float],
        context: dict[str, float],
        modalities: dict[str, Any],
    ) -> list[float]:
        dialogue_v = max(
            [dialogue.get(x, 0.0) for x in ("continuation", "reference", "question", "request")]
            or [0.0]
        )
        representation_v = max(representation.values(), default=0.0)
        domain_v = max(domain.values(), default=0.0)
        capability_v = max(capability.values(), default=0.0)
        continuity_v = max(context.values(), default=0.0)
        context_v = max(
            context.get("active_topic", 0.0),
            context.get("active_goal", 0.0),
            0.0,
        )
        modality_count = sum(
            v not in (None, "", {}, []) for v in (modalities or {}).values()
        )
        modality_v = min(1.0, modality_count / 3.0)
        return [
            float(dialogue_v), float(representation_v), float(domain_v),
            float(capability_v), float(continuity_v), float(context_v),
            float(modality_v),
        ]

    def scene_matrix(
        self,
        *,
        dialogue: dict[str, float],
        representation: dict[str, float],
        domain: dict[str, float],
        capability: dict[str, float],
        context: dict[str, float],
        modalities: dict[str, Any] | None = None,
        explicit_representations: Sequence[str] = (),
    ) -> dict[str, Any]:
        vector = self._feature_vector(
            dialogue, representation, domain, capability, context, modalities or {}
        )

        raw = []
        for row in _SCENE_WEIGHTS:
            raw.append(sum(a * b for a, b in zip(row, vector)))

        for scene in SCENE_MATRIX_LABELS:
            raw[SCENE_MATRIX_LABELS.index(scene)] += (
                0.34 * float(representation.get(scene, 0.0))
            )
            raw[SCENE_MATRIX_LABELS.index(scene)] += (
                0.10 * float(capability.get(SCENE_MATRIX_CAPABILITY[scene], 0.0))
            )

        for domain_name, bias_map in SCENE_MATRIX_DOMAIN_BIAS.items():
            ds = float(domain.get(domain_name, 0.0))
            for scene, bias in bias_map.items():
                raw[SCENE_MATRIX_LABELS.index(scene)] += ds * bias

        for scene in explicit_representations:
            if scene in SCENE_MATRIX_LABELS:
                raw[SCENE_MATRIX_LABELS.index(scene)] += 0.45

        maximum = max(raw, default=0.0)
        scores = [x / maximum if maximum > 0 else 0.0 for x in raw]
        ranked = sorted(
            zip(SCENE_MATRIX_LABELS, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        best, best_score = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        return {
            "labels": [x[0] for x in ranked],
            "scores": [round(float(x[1]), 6) for x in ranked],
            "best_scene": best,
            "best_score": round(float(best_score), 6),
            "margin": round(float(best_score - second), 6),
            "feature_order": list(SCENE_MATRIX_FEATURES),
            "feature_vector": [round(x, 6) for x in vector],
            "matrix_shape": [len(_SCENE_WEIGHTS), len(SCENE_MATRIX_FEATURES)],
            "explicit_representations": list(explicit_representations),
            "engine": "quantum_matrix",
            "mode": "vectorized_evidence_fusion",
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
        }

    # ------------------------------ measurement ---------------------------

    def measure(
        self,
        text: str,
        *,
        previous_assistant: str = "",
        previous_user: str = "",
        active_topic: str = "",
        active_goal: str = "",
        modalities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = self.normalize(text)
        key = (
            text, self.normalize(previous_assistant), self.normalize(previous_user),
            self.normalize(active_topic), self.normalize(active_goal),
            tuple(sorted((modalities or {}).keys())),
        )
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        families = self._tfidf_scores(text)
        context = self._context_scores(
            text, previous_assistant, previous_user, active_topic, active_goal
        )

        dialogue = families["dialogue"]
        representation = families["representation"]
        domain = families["domain"]
        capability = families["capability"]

        dialogue_ranked = sorted(dialogue.items(), key=lambda x: x[1], reverse=True)
        best_dialogue, dialogue_score = dialogue_ranked[0]
        margin = dialogue_score - (dialogue_ranked[1][1] if len(dialogue_ranked) > 1 else 0.0)

        rep_ranked = sorted(representation.items(), key=lambda x: x[1], reverse=True)
        best_representation, rep_score = rep_ranked[0]
        rep_margin = rep_score - (rep_ranked[1][1] if len(rep_ranked) > 1 else 0.0)

        # Representation is selected from a compatibility matrix rather than
        # lexical triggers. A representation must have enough semantic mass
        # AND a compatible dialogue/domain/capability signal. This prevents a
        # weak gallery/table prototype from winning an ordinary numeric or
        # memory question.
        text_rep_score = float(representation.get("text", 0.0) or 0.0)
        domain_scores = domain
        capability_scores = capability
        best_dialogue = str(best_dialogue or "")

        def compatible(name: str) -> bool:
            if name == "formula":
                return (float(domain_scores.get("physics", 0.0)) >= 0.005
                        or float(domain_scores.get("chemistry", 0.0)) >= 0.005
                        or float(capability_scores.get("information", 0.0)) >= 0.04)
            if name == "link":
                return (best_dialogue == "reference"
                        or float(capability_scores.get("web", 0.0)) >= 0.02)
            if name == "table":
                return (float(capability_scores.get("information", 0.0)) >= 0.04
                        or float(capability_scores.get("exploration", 0.0)) >= 0.03
                        or float(domain_scores.get("politics", 0.0)) >= 0.01
                        or float(domain_scores.get("news", 0.0)) >= 0.01)
            if name == "graph":
                return (float(capability_scores.get("exploration", 0.0)) >= 0.03
                        or float(domain_scores.get("physics", 0.0)) >= 0.02
                        or float(domain_scores.get("biology", 0.0)) >= 0.02)
            if name in {"diagram", "gallery", "image"}:
                return float(capability_scores.get("space", 0.0)) >= 0.03
            if name == "code":
                return float(capability_scores.get("code", 0.0)) >= 0.03
            return False

        effective = {}
        for name, score in representation.items():
            if name == "text":
                continue
            value = float(score or 0.0)
            if compatible(name):
                value += 0.10
            effective[name] = value

        explicit_representations = [
            name for name, score in effective.items()
            if score >= 0.20
            and score - text_rep_score >= 0.08
        ]
        explicit_representations.sort(
            key=lambda name: effective.get(name, 0.0), reverse=True
        )

        identity_request = (
            dialogue.get("identity", 0.0) >= 0.12
            and dialogue.get("identity", 0.0) >= dialogue.get("continuation", 0.0) + 0.03
            and dialogue.get("identity", 0.0) >= dialogue.get("reference", 0.0) + 0.03
        )
        fast_social = (
            best_dialogue in {"identity", "greeting"}
            and dialogue_score >= 0.12
            and margin >= 0.035
            and len(text.split()) <= 24
        )

        scene = self.scene_matrix(
            dialogue=dialogue,
            representation=representation,
            domain=domain,
            capability=capability,
            context=context,
            modalities=modalities,
            explicit_representations=explicit_representations,
        )

        profile = {
            "dialogue_scores": dict(dialogue),
            "dialogue_best": best_dialogue,
            "dialogue_confidence": float(dialogue_score),
            "dialogue_margin": float(margin),
            "representation_scores": dict(representation),
            "domain_scores": dict(domain),
            "capability_scores": dict(capability),
            "context_scores": dict(context),
            "best_representation": best_representation,
            "best_representation_score": float(rep_score),
            "representation_margin": float(rep_margin),
            "explicit_representations": explicit_representations,
            "identity_request": bool(identity_request),
            "fast_social": bool(fast_social or identity_request),
            "scene_matrix": scene,
            "source": "quantum_matrix_semantic_measurement",
        }

        with self._lock:
            self._cache[key] = profile
            if len(self._cache) > self._cache_limit:
                self._cache.pop(next(iter(self._cache)))
        return profile

    # ------------------------------ contracts -----------------------------

    def _history(self, history: Any) -> tuple[str, str, Any]:
        turns = history if isinstance(history, list) else []
        last_assistant = ""
        last_user = ""
        reply_to = None
        for item in reversed(turns):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").lower()
            if not last_assistant:
                if isinstance(item.get("april"), dict):
                    obj = item["april"]
                    last_assistant = self.normalize(
                        obj.get("answer") or obj.get("content") or obj.get("summary")
                    )
                    reply_to = item.get("turn_id")
                elif role in {"assistant", "april", "bot"}:
                    last_assistant = self.normalize(
                        item.get("answer") or item.get("content") or item.get("summary")
                    )
                    reply_to = item.get("turn_id")
            if not last_user:
                if isinstance(item.get("user"), dict):
                    obj = item["user"]
                    last_user = self.normalize(
                        obj.get("text") or obj.get("content") or obj.get("answer")
                    )
                elif role in {"user", "human"}:
                    last_user = self.normalize(item.get("content") or item.get("text"))
            if last_assistant and last_user:
                break
        return last_assistant, last_user, reply_to

    def fast_semantic_profile(
        self, text: str, previous_assistant: str = "",
        previous_user: str = "",
        active_topic: str = "", active_goal: str = ""
    ) -> dict[str, Any]:
        return self.measure(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_topic=active_topic,
            active_goal=active_goal,
        )

    def turn_measurement(
        self, text: str, previous_assistant: str = "",
        previous_user: str = "", active_goal: str = "", active_topic: str = ""
    ) -> dict[str, Any]:
        profile = self.measure(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_topic=active_topic,
            active_goal=active_goal,
        )
        return {
            "linguistic": self._linguistic(self.normalize(text)),
            "dialogue_nli": {
                "labels": list(profile["dialogue_scores"]),
                "scores": list(profile["dialogue_scores"].values()),
                "source": "quantum_matrix",
            },
            "representation_nli": {
                "labels": [REPRESENTATION_HYPOTHESES[x] for x in profile["representation_scores"]],
                "scores": list(profile["representation_scores"].values()),
                "source": "quantum_matrix",
            },
            "domain_nli": {
                "labels": [DOMAIN_HYPOTHESES[x] for x in profile["domain_scores"]],
                "scores": list(profile["domain_scores"].values()),
                "source": "quantum_matrix",
            },
            "capability_nli": {
                "labels": [CAPABILITY_HYPOTHESES[x] for x in profile["capability_scores"]],
                "scores": list(profile["capability_scores"].values()),
                "source": "quantum_matrix",
            },
            "embeddings": dict(profile["context_scores"]),
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_interpretation_turn_engine",
        }

    def classify(self, text: str, hypotheses: Sequence[str]) -> dict[str, Any]:
        profile = self.measure(text)
        labels = list(hypotheses)
        family_map = {
            "dialogue": profile["dialogue_scores"],
            "representation": profile["representation_scores"],
            "domain": profile["domain_scores"],
            "capability": profile["capability_scores"],
        }
        scores: dict[str, float] = {}
        for family in family_map.values():
            scores.update({str(k): float(v) for k, v in family.items()})
        ranked = sorted(
            ((label, scores.get(label, 0.0)) for label in labels),
            key=lambda x: x[1], reverse=True,
        )
        return {
            "labels": [x[0] for x in ranked],
            "scores": [x[1] for x in ranked],
            "source": "quantum_matrix",
        }

    def similarity(self, text_a: str, text_b: str) -> dict[str, Any]:
        a, b = set(self._tokens(self.normalize(text_a))), set(self._tokens(self.normalize(text_b)))
        score = len(a & b) / max(1.0, min(len(a), len(b))) if a and b else 0.0
        return {"score": float(score), "source": "quantum_matrix", "measured": bool(a and b), "cached": False}

    def similarities(self, text: str, candidates: Sequence[str]) -> dict[str, float]:
        return {self.normalize(c): self.similarity(text, c)["score"] for c in candidates if self.normalize(c)}

    def prewarm_static(self, candidates: Sequence[str]) -> int:
        return len({self.normalize(x) for x in candidates if self.normalize(x)})

    def _resolve_scene_context(
        self,
        text: str,
        state: dict[str, Any],
        *,
        continuation: bool,
        reference: bool,
        active_topic: str = "",
    ) -> dict[str, Any]:
        """Resolve the semantic scene that the current turn refers to.

        This is interpretation evidence only.  It does not execute routing,
        use keyword triggers, or create a second memory.  The current scene is
        preferred for a true continuation; a historical scene may be selected
        by semantic similarity when the turn is a reference rather than a
        direct continuation.
        """
        if not isinstance(state, dict) or (not continuation and not reference):
            return {}

        current = state.get("current_visual_scene") or state.get("active_visual_scene")
        candidates: list[dict[str, Any]] = []
        if isinstance(current, dict) and current.get("scene_id"):
            candidates.append(current)

        history = state.get("visual_scene_history")
        if isinstance(history, list):
            for scene in reversed(history):
                if not isinstance(scene, dict) or not scene.get("scene_id"):
                    continue
                if any(scene.get("scene_id") == x.get("scene_id") for x in candidates):
                    continue
                candidates.append(scene)
                if len(candidates) >= 8:
                    break

        if not candidates:
            return {}

        def scene_text(scene: dict[str, Any]) -> str:
            return self.normalize(" ".join(
                str(scene.get(key) or "")
                for key in ("topic", "user_request", "summary", "april_answer")
            ))

        # A continuation means the immediately active scene is the semantic
        # referent.  No lexical trigger is used here.
        if continuation and isinstance(current, dict) and current.get("scene_id"):
            selected = current
            relation = "current_scene"
            confidence = 1.0
        else:
            scored: list[tuple[float, int, dict[str, Any]]] = []
            for index, scene in enumerate(candidates):
                candidate_text = scene_text(scene)
                score = self.similarity(text, candidate_text)["score"] if candidate_text else 0.0
                if active_topic and candidate_text:
                    score = max(score, self.similarity(active_topic, candidate_text)["score"])
                scored.append((float(score), -index, scene))
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            confidence, _, selected = scored[0]
            relation = "historical_scene" if selected.get("scene_id") != (current or {}).get("scene_id") else "current_scene"

        answer = self.normalize(
            selected.get("april_answer") or selected.get("answer") or selected.get("content")
        )
        summary = self.normalize(selected.get("summary") or "")
        return {
            "relation": relation,
            "confidence": round(float(confidence), 6),
            "scene_id": str(selected.get("scene_id") or ""),
            "turn_id": selected.get("turn_id"),
            "topic": self.normalize(selected.get("topic") or ""),
            "user_request": self.normalize(selected.get("user_request") or selected.get("current_request") or ""),
            "answer": answer,
            "summary": summary,
            "render_block_types": list(selected.get("render_block_types") or []),
            "presentation_types": list(selected.get("presentation_types") or []),
            "renderer_state": selected.get("renderer_state") if isinstance(selected.get("renderer_state"), dict) else {},
            "semantic_source": "interpretation_scene_resolution",
            "evidence_only": True,
        }

    def dialogue(
        self,
        text: str,
        previous_assistant: str = "",
        previous_user: str = "",
        active_goal: str = "",
        active_topic: str = "",
        open_task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile = self.measure(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_topic=active_topic,
            active_goal=active_goal,
        )
        dialogue = profile["dialogue_scores"]
        best = profile["dialogue_best"]

        assistant_relation = profile["context_scores"].get("previous_assistant", 0.0)
        user_relation = profile["context_scores"].get("previous_user", 0.0)
        topic_relation = profile["context_scores"].get("active_topic", 0.0)

        continuation_score = max(
            dialogue.get("continuation", 0.0),
            0.72 * assistant_relation,
            0.58 * user_relation,
            0.64 * topic_relation,
        )

        reference_score = max(
            dialogue.get("reference", 0.0),
            0.86 * assistant_relation,
            0.62 * user_relation,
            0.70 * topic_relation,
        )

        has_dialogue_context = bool(
            previous_assistant or previous_user or active_topic or active_goal
        )

        memory_query_score = (
            float(dialogue.get("memory_query", 0.0) or 0.0)
            if has_dialogue_context
            else 0.0
        )

        if memory_query_score >= 0.10:
            reference_score = max(reference_score, memory_query_score)

        if previous_assistant or previous_user:
            if profile.get("dialogue_best") == "identity" or dialogue.get("identity", 0.0) >= 0.12:
                reference_score = max(reference_score, 0.72)
                continuation_score = max(continuation_score, 0.62)

        task_frame = open_task if isinstance(open_task, dict) else {}
        task_relation = LIVE_SCENE_CONTINUITY_ENGINE._answer_of_open_task(
            text,
            task_frame,
            {"label": best},
        )
        task_transition = LIVE_SCENE_CONTINUITY_ENGINE._explicit_task_transition(
            text,
            {"label": best},
        )

        # The current open task is stronger evidence than lexical similarity.
        # This is the key semantic rule for interactive dialogue.
        if task_relation.get("is_answer") or task_relation.get("is_task_action"):
            continuation_score = max(
                continuation_score,
                float(task_relation.get("confidence", 0.0) or 0.0),
            )
            reference_score = max(reference_score, 0.90)

        if task_transition.get("replace_task"):
            continuation_score = max(continuation_score, 0.93)
            reference_score = max(reference_score, 0.90)

        continuation = bool(
            previous_assistant
            and (
                task_relation.get("is_answer")
                or task_relation.get("is_task_action")
                or task_transition.get("replace_task")
                or best
                in {
                    "continuation",
                    "reformulation",
                    "correction",
                    "reference",
                    "affirmation",
                    "rejection",
                }
                or continuation_score >= 0.72
            )
        )

        return {
            "dialogue": {
                "label": best,
                "confidence": float(profile["dialogue_confidence"]),
                "continuation_score": float(continuation_score),
                "reference_score": float(reference_score),
                "topic_score": float(
                    profile["context_scores"].get("active_topic", 0.0)
                ),
                "goal_score": float(
                    profile["context_scores"].get("active_goal", 0.0)
                ),
                "task_relation": task_relation,
                "task_transition": task_transition,
            },
            "linguistic": self._linguistic(self.normalize(text)),
            "continuation": continuation,
            "reference_to_previous": bool(
                previous_assistant and reference_score >= 0.60
            ),
            "identity_request": bool(profile["identity_request"]),
            "nli": {
                "labels": list(profile["dialogue_scores"]),
                "scores": list(profile["dialogue_scores"].values()),
                "source": "quantum_matrix",
            },
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_dialogue_matrix_view_v2_task_aware",
        }

    def representations(self, text: str, context: str = "") -> dict[str, Any]:
        profile = self.measure(text, active_topic=context)
        return {
            "nli": {
                "labels": [REPRESENTATION_HYPOTHESES[x] for x in profile["representation_scores"]],
                "scores": list(profile["representation_scores"].values()),
                "source": "quantum_matrix",
            },
            "measurements": [
                {"type": k, "score": float(v), "source": "quantum_matrix"}
                for k, v in sorted(profile["representation_scores"].items(), key=lambda x: x[1], reverse=True)
            ],
            "context_similarity": {
                "score": float(profile["context_scores"].get("active_topic", 0.0)),
                "source": "quantum_matrix",
            },
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_representation_matrix_view",
        }

    def domains(self, text: str) -> dict[str, Any]:
        profile = self.measure(text)
        return {
            "measurements": [
                {"domain": k, "score": float(v)}
                for k, v in sorted(profile["domain_scores"].items(), key=lambda x: x[1], reverse=True)
            ],
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "engine": "quantum_domain_matrix_view",
        }

    @classmethod
    def _artifact_reference_evidence(
        cls,
        text: str,
        previous_user: str,
        previous_assistant: str,
        active_scene: dict[str, Any],
        representation: str,
    ) -> dict[str, Any]:
        """Resolve whether a structured request operates on the current dialogue artifact.

        This is semantic relation evidence, not a renderer trigger.  It combines
        grammatical deixis, a structured representation request, and the existence
        of a live conversational operand.  The result only authorizes context; the
        provider and Web still receive the canonical SceneContract.
        """
        rep = cls.normalize(representation).lower()
        if rep not in {"image", "gallery", "diagram", "graph", "table", "formula", "code", "link"}:
            return {"score": 0.0, "artifact_reference": False, "reason": "non_structured"}

        low = cls.normalize(text).lower()
        if not low:
            return {"score": 0.0, "artifact_reference": False, "reason": "empty"}

        live = isinstance(active_scene, dict) and bool(
            active_scene.get("scene_id") or active_scene.get("topic") or
            active_scene.get("render_blocks") or active_scene.get("blocks")
        )
        if not live and not previous_user and not previous_assistant:
            return {"score": 0.0, "artifact_reference": False, "reason": "no_operand"}

        deictic = (
            "это", "этот", "эта", "эту", "этой", "этом", "этим",
            "здесь", "выше", "ниже", "получивш", "предыдущ",
        )
        transformation = (
            "покажи", "представь", "сделай", "нарисуй", "изобрази",
            "добавь", "измени", "переделай", "в таблице", "в виде",
            "в схеме", "на графике", "формул",
        )
        deictic_score = 0.72 if any(x in low for x in deictic) else 0.0
        transform_score = 0.20 if any(x in low for x in transformation) else 0.0
        scene_score = 0.08 if live else 0.0
        previous_score = 0.08 if (previous_user or previous_assistant) else 0.0
        score = min(1.0, deictic_score + transform_score + scene_score + previous_score)

        return {
            "score": round(score, 6),
            "artifact_reference": bool(score >= 0.70),
            "reason": "dialogue_artifact_dependency" if score >= 0.70 else "structured_new_operand",
            "deictic": bool(deictic_score),
            "transformation": bool(transform_score),
            "live_scene": live,
        }

    @classmethod
    def _build_interpretation_control(
        cls,
        *,
        text: str,
        representation: str,
        operation: str,
        relation: str,
        previous_user: str,
        previous_assistant: str,
        live_scene: dict[str, Any],
        explicit_boundary: bool,
    ) -> dict[str, Any]:
        """Produce the one semantic control packet consumed downstream.

        Renderer selection is not decided here.  This packet only states whether
        the current semantic result is authorized to produce a structured artifact
        and whether that artifact depends on the previous dialogue operand.
        """
        rep = cls.normalize(representation).lower()
        structured = rep in {"image", "gallery", "diagram", "graph", "table", "formula", "code", "link"}
        artifact = cls._artifact_reference_evidence(
            text, previous_user, previous_assistant, live_scene, rep
        )
        authorized = bool(structured and not explicit_boundary)
        mode = "TEXT_ONLY"
        if authorized:
            mode = "ARTIFACT_CONTINUATION" if artifact.get("artifact_reference") else "STRUCTURED_OUTPUT"

        return {
            "version": "interpretation_control_v1",
            "relation": relation,
            "render_authorized": authorized,
            "render_mode": mode,
            "render_representations": [rep] if authorized else [],
            "artifact_reference": bool(artifact.get("artifact_reference")),
            "artifact_reference_score": float(artifact.get("score", 0.0) or 0.0),
            "artifact_reference_reason": artifact.get("reason", ""),
            "context_policy": "active_dialogue_operand" if artifact.get("artifact_reference") else "current_semantic_request",
            "memory_policy": "same_dialogue_sequence",
            "payload_contract": "scene_contract",
            "operation": cls.normalize(operation),
            "representation": rep,
        }

    def interpret(
        self,
        text: str,
        cognition: dict | None = None,
        semantic: dict | None = None,
        history: list | None = None,
        state: dict | None = None,
    ) -> dict[str, Any] | None:
        text = self.normalize(text)
        if not text:
            return None

        cognition = cognition if isinstance(cognition, dict) else {}
        semantic = semantic if isinstance(semantic, dict) else {}
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []

        # Explicit future commitments are semantic state, not renderer state.
        # Keep them outside the current topic/task so a task replacement cannot
        # accidentally erase a promise that must be fulfilled later.
        detected_obligations = extract_dialogue_obligations(text)
        if detected_obligations:
            state["dialogue_obligations"] = merge_dialogue_obligations(
                state.get("dialogue_obligations"), detected_obligations
            )

        started = time.perf_counter()

        # ------------------------------------------------------------------
        # Cognitive Interpretation Environment: all specialist engines work
        # in one authenticated workspace before the legacy scene bridge runs.
        # The raw current user request remains immutable and separate from the
        # derived provider instruction.
        # ------------------------------------------------------------------
        interpretation_council = INTERPRETATION_ORCHESTRATOR.run(
            text,
            state=state,
            history=history,
            semantic=semantic,
            cognition=cognition,
        )
        cognitive_environment = interpretation_council.get("workspace", {})
        canonical_cognitive = interpretation_council.get("canonical", {})

        # The cognitive orchestrator already performed the fast authenticated
        # dialogue-history search. Recover that result here before the legacy
        # compatibility bridge consumes it. Without this handoff the bridge
        # raises NameError and silently falls back to the legacy/weak route.
        history_search = cognitive_environment.get("dialogue_history_search")
        if not isinstance(history_search, dict):
            history_search = interpretation_council.get("dialogue_history_search")
        if not isinstance(history_search, dict):
            history_search = {}
        state["interpretation_workspace"] = cognitive_environment
        state["interpretation_canonical"] = canonical_cognitive

        # Seed only ownership facts into the existing scene bridge. The bridge
        # still owns scene state; the council owns semantic interpretation.
        council_relation = str(cognitive_environment.get("relation") or "NEW").upper()
        council_task = cognitive_environment.get("active_task_context")
        if council_relation == "NEW" and not council_task:
            state["open_task"] = {}
            state["active_task"] = {}
            state["interactive_task_state"] = {}
            state["active_topic"] = self.normalize(cognitive_environment.get("active_topic"))
            state["current_topic"] = self.normalize(cognitive_environment.get("active_topic"))
            state["active_goal"] = self.normalize(cognitive_environment.get("goal"))
            state["current_goal"] = self.normalize(cognitive_environment.get("goal"))
            state["april_active_entity"] = ""
        elif council_task:
            state["open_task"] = dict(council_task)
            state["active_task"] = dict(council_task)
            state["interactive_task_state"] = dict(council_task)
            state["active_topic"] = self.normalize(cognitive_environment.get("active_topic"))
            state["current_topic"] = self.normalize(cognitive_environment.get("active_topic"))
            state["active_goal"] = self.normalize(cognitive_environment.get("goal"))
            state["current_goal"] = self.normalize(cognitive_environment.get("goal"))

        # Build the dialogue environment BEFORE any task/scene resolution.  The
        # environment is scoped to the authenticated USER↔conversation and picks
        # the freshest real antecedent instead of trusting a stale sequence topic.
        dialogue_environment = DIALOGUE_ENVIRONMENT_ENGINE.build(text, state, history)

        # Reconcile the compatibility environment with the specialist council.
        # The council owns semantic relation; the legacy environment stays available
        # for scene/state compatibility.
        council_env = cognitive_environment if isinstance(cognitive_environment, dict) else {}
        council_rel = str(council_env.get("relation") or "").upper()
        if council_rel in {"NEW", "CONTINUE", "RECALL"}:
            dialogue_environment = dict(dialogue_environment)
            dialogue_environment["relation"] = council_rel
            dialogue_environment["turn_relation"] = council_env.get("turn_relation") or dialogue_environment.get("turn_relation")
            dialogue_environment["conversation_continuation"] = bool(council_env.get("conversation_continuation"))
            dialogue_environment["context_dependency"] = (
                "memory_reference" if council_rel == "RECALL"
                else "active_dialogue_sequence" if council_rel == "CONTINUE"
                else "current_turn_only"
            )
            dialogue_environment["current_topic"] = self.normalize(
                council_env.get("active_topic") or dialogue_environment.get("current_topic") or text
            )
            dialogue_environment["active_entity"] = self.normalize(
                council_env.get("active_entity") or dialogue_environment.get("active_entity") or ""
            )
            dialogue_environment["operation"] = self.normalize(
                council_env.get("operation") or dialogue_environment.get("operation") or "answer"
            )
            dialogue_environment["goal"] = self.normalize(
                council_env.get("goal") or dialogue_environment.get("goal") or "answer"
            )
            dialogue_environment["representation"] = self.normalize(
                council_env.get("representation") or dialogue_environment.get("representation") or "text"
            )
            dialogue_environment["historical_memory_allowed"] = council_rel == "RECALL"
            dialogue_environment["selected_memory"] = list(council_env.get("selected_memory") or [])
            if isinstance(council_env.get("active_task_context"), dict) and council_env.get("active_task_context"):
                dialogue_environment["active_task"] = dict(council_env["active_task_context"])
            dialogue_environment["continuation_content_analysis"] = (
                council_env.get("continuation_content_analysis")
                or dialogue_environment.get("continuation_content_analysis")
                or {}
            )

        environment_previous = dialogue_environment.get("previous_pair") if isinstance(dialogue_environment.get("previous_pair"), dict) else {}
        last_assistant = self.normalize(
            dialogue_environment.get("previous_april_turn") or environment_previous.get("april")
        )
        last_user = self.normalize(
            dialogue_environment.get("previous_user_turn") or environment_previous.get("user")
        )
        reply_to = ""

        # The environment, not stale sequence/entity fields, is the first semantic
        # authority for the current turn.  Older state remains available as evidence
        # but cannot silently become the active owner.
        raw_scene = LIVE_SCENE_CONTINUITY_ENGINE._scene_from_state(state)
        preflight_relation = self.normalize(dialogue_environment.get("relation")).upper()
        preflight_task = dialogue_environment.get("active_task") if isinstance(dialogue_environment.get("active_task"), dict) else {}

        if preflight_relation == "NEW" and not preflight_task:
            # Fence the previous task/topic before the live-scene resolver runs.
            state["open_task"] = {}
            state["active_task"] = {}
            state["interactive_task_state"] = {}
            state["april_active_task"] = {}
            state["april_pending_task"] = {} if isinstance(state.get("april_pending_task"), dict) else state.get("april_pending_task")
            state["active_topic"] = self.normalize(dialogue_environment.get("current_topic"))
            state["current_topic"] = self.normalize(dialogue_environment.get("current_topic"))
            state["active_goal"] = self.normalize(dialogue_environment.get("goal"))
            state["current_goal"] = self.normalize(dialogue_environment.get("goal"))
        elif preflight_task:
            # Recover/create only the task that belongs to this current authenticated
            # branch.  This is especially important for riddle confirmation turns.
            state["open_task"] = dict(preflight_task)
            state["active_task"] = dict(preflight_task)
            state["interactive_task_state"] = dict(preflight_task)
            state["april_active_task"] = dict(preflight_task)
            state["active_topic"] = self.normalize(dialogue_environment.get("current_topic"))
            state["current_topic"] = self.normalize(dialogue_environment.get("current_topic"))
            state["active_goal"] = self.normalize(dialogue_environment.get("goal"))
            state["current_goal"] = self.normalize(dialogue_environment.get("goal"))

        inferred_open_task = dict(preflight_task) if preflight_task else LIVE_SCENE_CONTINUITY_ENGINE._find_open_task(
            state,
            LIVE_SCENE_CONTINUITY_ENGINE._history_turns(history),
            raw_scene,
            last_assistant,
        )

        transition_preview = LIVE_SCENE_CONTINUITY_ENGINE._explicit_task_transition(
            text,
            {"label": ""},
        )

        owner_topic = self.normalize(dialogue_environment.get("current_topic"))
        if not owner_topic and inferred_open_task.get("active"):
            owner_topic = self.normalize(
                inferred_open_task.get("topic")
                or ("загадка" if inferred_open_task.get("kind") == "riddle" else "вопрос")
            )

        active_topic = self.normalize(
            owner_topic
            or state.get("active_topic")
            or state.get("current_topic")
            or semantic.get("active_topic")
            or semantic.get("current_topic")
            or cognition.get("active_topic")
            or cognition.get("current_topic")
        )

        active_goal = self.normalize(
            dialogue_environment.get("goal")
            or inferred_open_task.get("goal")
            or state.get("active_goal")
            or state.get("current_goal")
            or semantic.get("active_goal")
            or cognition.get("active_goal")
            or cognition.get("current_goal")
        )

        profile = self.measure(
            text,
            previous_assistant=last_assistant,
            previous_user=last_user,
            active_topic=active_topic,
            active_goal=active_goal,
            modalities={
                "voice": semantic.get("voice_context") or cognition.get("voice_context"),
                "vision": semantic.get("vision_context") or cognition.get("vision_context"),
                "gallery": semantic.get("gallery_context") or cognition.get("gallery_context"),
                "files": semantic.get("file_context") or cognition.get("file_context"),
            },
        )
        matrix = profile["scene_matrix"]

        measured_dialogue = self.dialogue(
            text,
            previous_assistant=last_assistant,
            previous_user=last_user,
            active_goal=active_goal,
            active_topic=active_topic,
            open_task=inferred_open_task,
        )["dialogue"]

        # The preflight environment is the discourse authority. Matrix scores remain
        # evidence, but they may not relabel a known interaction such as
        # `Правильно`, `Ключ`, or `Отгадай загадку ...`.
        measured_dialogue = dict(measured_dialogue)
        preflight_turn_relation = self.normalize(dialogue_environment.get("turn_relation")).upper()
        if preflight_relation == "NEW":
            measured_dialogue.update({
                "label": "request",
                "continuation_score": 0.0,
                "reference_score": 0.0,
                "topic_score": 0.0,
                "goal_score": 0.0,
                "task_relation": {
                    "is_answer": False,
                    "is_task_action": False,
                    "confidence": 0.0,
                    "reason": "current_topic_authority",
                },
                "task_transition": {"requested": False, "replace_task": False, "reset_memory": False, "source": "dialogue_environment"},
                "confidence": max(float(measured_dialogue.get("confidence", 0.0) or 0.0), 0.90),
            })
        elif preflight_relation == "RECALL":
            measured_dialogue.update({
                "label": "memory_query",
                "continuation_score": 0.0,
                "reference_score": 0.95,
                "reference_to_previous": True,
                "topic_score": 0.0,
                "goal_score": 0.0,
            })
        elif preflight_relation == "CONTINUE":
            measured_dialogue.update({
                "label": (
                    "affirmation" if preflight_turn_relation == "TASK_CONFIRMATION"
                    else "correction" if preflight_turn_relation == "TASK_CORRECTION"
                    else "continuation"
                ),
                "continuation_score": max(float(measured_dialogue.get("continuation_score", 0.0) or 0.0), 0.94),
                "reference_score": max(float(measured_dialogue.get("reference_score", 0.0) or 0.0), 0.90),
                "topic_score": max(float(measured_dialogue.get("topic_score", 0.0) or 0.0), 0.50),
                "goal_score": max(float(measured_dialogue.get("goal_score", 0.0) or 0.0), 0.50),
                "task_relation": (
                    {
                        "is_answer": False,
                        "is_task_action": True,
                        "confidence": 0.99,
                        "reason": "confirmed_active_task",
                    } if preflight_turn_relation in {"TASK_CONFIRMATION", "TASK_CORRECTION"} and preflight_task else measured_dialogue.get("task_relation", {})
                ),
                "confidence": max(float(measured_dialogue.get("confidence", 0.0) or 0.0), 0.92),
            })

        # For an explicitly new topic, erase stale semantic context from the matrix
        # profile before LiveSceneContinuityEngine sees it.
        if preflight_relation == "NEW":
            profile = dict(profile)
            profile["context_scores"] = dict(profile.get("context_scores") or {})
            for key in ("previous_assistant", "previous_user", "active_topic", "active_goal"):
                profile["context_scores"][key] = 0.0
            profile["dialogue_scores"] = dict(profile.get("dialogue_scores") or {})
            profile["dialogue_scores"]["new_topic"] = max(float(profile["dialogue_scores"].get("new_topic", 0.0) or 0.0), 0.95)
            profile["dialogue_scores"]["independent"] = max(float(profile["dialogue_scores"].get("independent", 0.0) or 0.0), 0.90)

        # First-turn guard remains, but it does not override a real live task.
        has_live_context = bool(
            last_assistant
            or last_user
            or active_topic
            or active_goal
            or raw_scene.get("scene_id")
            or inferred_open_task.get("active")
        )
        if not has_live_context and measured_dialogue["label"] == "memory_query":
            measured_dialogue = dict(measured_dialogue)
            measured_dialogue["label"] = "request"
            measured_dialogue["reference_score"] = 0.0

        required_representations = list(
            dict.fromkeys(
                [
                    *[
                        str(x).lower()
                        for x in (semantic.get("required_representations", []) or [])
                        + (cognition.get("required_representations", []) or [])
                        if str(x).strip()
                    ],
                    *profile["explicit_representations"],
                ]
            )
        )

        candidate_domains = [
            k
            for k, v in profile["domain_scores"].items()
            if float(v) >= 0.45
        ]
        required_domains = list(
            semantic.get("required_domains", []) or candidate_domains
        )

        provisional_scene_type = (
            required_representations[0]
            if required_representations
            else "text"
        )

        # One canonical owner decides scene/task continuity.
        live_scene = LIVE_SCENE_CONTINUITY_ENGINE.resolve(
            text=text,
            state=state,
            history=history,
            profile=profile,
            dialogue=measured_dialogue,
            active_topic=active_topic,
            active_goal=active_goal,
            scene_type=provisional_scene_type,
        )

        # Reconcile the low-level scene resolver with the preflight environment.
        # This is intentionally a narrow semantic fence: it does not touch routing
        # or rendering, only the ownership/continuity facts used by those layers.
        if preflight_relation == "NEW":
            live_scene["topic_boundary"] = True
            live_scene["new_scene"] = True
            live_scene["continuation"] = False
            live_scene["relation"] = "NEW_SCENE"
            if preflight_task:
                live_scene["open_task"] = dict(preflight_task)
                live_scene["task_state"] = dict(preflight_task)
                live_scene["interactive_task_state"] = dict(preflight_task)
                live_scene["active_entity"] = self.normalize(dialogue_environment.get("active_entity"))
                state["open_task"] = dict(preflight_task)
                state["active_task"] = dict(preflight_task)
                state["interactive_task_state"] = dict(preflight_task)
        elif preflight_relation == "CONTINUE":
            live_scene["topic_boundary"] = False
            live_scene["new_scene"] = False
            live_scene["continuation"] = True
            live_scene["relation"] = "CONTINUE_SCENE"
            if preflight_task:
                live_scene["open_task"] = dict(preflight_task)
                live_scene["task_state"] = dict(preflight_task)
                live_scene["interactive_task_state"] = dict(preflight_task)
        elif preflight_relation == "RECALL":
            live_scene["memory_query"] = True
            live_scene["relation"] = "MEMORY_RECALL"
            live_scene["continuation"] = False

        # Historical entity values from an older branch are evidence only.  Never
        # let them survive as the active entity when the preflight environment has
        # established a fresh topic.
        if preflight_relation == "NEW":
            state["april_active_entity"] = self.normalize(dialogue_environment.get("active_entity"))
        elif preflight_relation == "CONTINUE" and dialogue_environment.get("active_entity"):
            state["april_active_entity"] = self.normalize(dialogue_environment.get("active_entity"))

        live_scene_record = (
            live_scene.get("scene", {})
            if isinstance(live_scene.get("scene"), dict)
            else {}
        )

        # A structured representation request is still a turn in the same
        # conversation even when its topic vector changes.  The old resolver
        # treated a modality change (e.g. text -> table) as NEW and therefore
        # withheld the active sequence from Provider.  Keep topic-boundary evidence
        # separate from conversation continuity.
        requested_representation = (
            required_representations[0]
            if required_representations
            else (profile["explicit_representations"][0] if profile.get("explicit_representations") else "")
        )
        if not requested_representation:
            best_rep = str(profile.get("best_representation") or "").lower()
            best_score = float(profile.get("best_representation_score", 0.0) or 0.0)
            rep_margin = float(profile.get("representation_margin", 0.0) or 0.0)
            if best_rep and best_rep != "text" and best_score >= 0.20 and rep_margin >= 0.04:
                requested_representation = best_rep

        explicit_boundary = bool(live_scene.get("topic_boundary"))
        structured_request = requested_representation in {
            "image", "gallery", "diagram", "graph", "table", "formula", "code", "link"
        }
        artifact_evidence = self._artifact_reference_evidence(
            text, last_user, last_assistant, live_scene_record or raw_scene, requested_representation
        )
        if artifact_evidence.get("artifact_reference") and raw_scene.get("scene_id"):
            # A representation transform of the current operand is a continuation
            # even when the generic topic scorer calls it a new scene. Topic-vector
            # change remains available separately as evidence.
            explicit_boundary = False
        if (
            structured_request
            and raw_scene.get("scene_id")
            and not explicit_boundary
            and not transition_preview.get("replace_task")
        ):
            live_scene["continuation"] = True
            live_scene["new_scene"] = False
            live_scene["topic_boundary"] = False
            live_scene["relation"] = "CONTINUE_SCENE"

        three_way_relation = "CONTINUE" if live_scene.get("continuation") else (
            "NEW" if live_scene.get("new_scene") else "RECALL"
            if live_scene.get("memory_query")
            else "NEW"
        )

        continuation = three_way_relation == "CONTINUE"
        reference = three_way_relation == "RECALL"

        resolved_scene = self._resolve_scene_context(
            text,
            state,
            continuation=continuation,
            reference=reference,
            active_topic=live_scene_record.get("topic") or active_topic,
        )

        representation_scores = profile["representation_scores"]
        capability = profile["capability_scores"]

        representation_evidence = [
            SemanticEvidence(k, float(v), "quantum_matrix").as_dict()
            for k, v in sorted(
                representation_scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if float(v) >= 0.20
        ]

        open_task = live_scene.get("open_task", {})
        task_active = bool(isinstance(open_task, dict) and open_task.get("active"))

        effective_topic = self.normalize(
            live_scene_record.get("topic")
            or (
                open_task.get("topic")
                if task_active
                else active_topic
            )
            or (active_topic if continuation else text)
        )

        effective_goal = self.normalize(
            live_scene_record.get("goal")
            or (
                open_task.get("goal")
                if task_active
                else active_goal
            )
            or (active_goal if continuation else text)
        )

        interpretation_control = self._build_interpretation_control(
            text=text,
            representation=requested_representation or "text",
            operation=(
                semantic.get("operation")
                or semantic.get("semantic_task", {}).get("operation")
                if isinstance(semantic.get("semantic_task"), dict)
                else semantic.get("operation")
                or ""
            ),
            relation=three_way_relation,
            previous_user=last_user,
            previous_assistant=last_assistant,
            live_scene=live_scene_record or raw_scene,
            explicit_boundary=bool(live_scene.get("topic_boundary")) and not bool(artifact_evidence.get("artifact_reference")),
        )

        canonical_context_dependency = (
            "continuation"
            if continuation
            else "recall"
            if reference
            else "new_topic"
            if live_scene.get("topic_boundary")
            else "independent"
        )

        active_entity = ""
        candidate_answer = self.normalize(
            open_task.get("candidate_answer") if task_active and isinstance(open_task, dict) else ""
        )
        if task_active and not active_entity:
            active_entity = self.normalize(open_task.get("target") if isinstance(open_task, dict) else "")

        semantic_anchor = (
            cognitive_environment.get("semantic_anchor")
            if isinstance(cognitive_environment.get("semantic_anchor"), dict)
            else {}
        )
        if not semantic_anchor:
            semantic_anchor = (
                canonical_cognitive.get("semantic_anchor")
                if isinstance(canonical_cognitive.get("semantic_anchor"), dict)
                else {}
            )

        task_answer = live_scene.get("task_answer", {})
        if not isinstance(task_answer, dict):
            task_answer = {}
        task_relation = task_answer
        task_transition = live_scene.get("task_transition", {})
        if not isinstance(task_transition, dict):
            task_transition = {}
        forbidden_entities = list(
            live_scene.get("forbidden_entities", [])
            if isinstance(live_scene.get("forbidden_entities"), list)
            else []
        )

        # Do not expose an inherited sequence entity as the active entity.
        # Candidates belong to the task and are not facts until confirmed.
        if task_active and candidate_answer and not active_entity:
            active_entity = ""

        resolved_request = text
        # The cognitive workspace is the current-turn authority and will replace
        # this provisional request below. The legacy task frame is deliberately
        # not allowed to rewrite the request before that decision is made.

        active_task_contract = {
            "operation": "answer"
            if open_task.get("status") in {"open", "answer_received"}
            else "generate"
            if open_task.get("status") == "pending_generation"
            else "answer",
            "object": active_entity or open_task.get("kind") or "conversation",
            "representation": "text",
            "goal": effective_goal,
            "topic": effective_topic,
            "kind": open_task.get("kind") if task_active else "",
            "role": open_task.get("role") if task_active else "",
            "phase": open_task.get("phase") if task_active else "",
            "status": open_task.get("status") if task_active else "",
            "prompt": open_task.get("prompt") if task_active else "",
            "last_question": open_task.get("last_question") if task_active else "",
            "candidate_answer": candidate_answer,
            "last_user_answer": open_task.get("last_user_answer") if task_active else "",
            "expected_input_type": open_task.get("expected_input_type") if task_active else "",
            "known_clues": list(open_task.get("known_clues") or [])[-12:] if task_active else [],
            "qa_history": list(open_task.get("qa_history") or [])[-12:] if task_active else [],
            "task_revision": open_task.get("task_revision", 0) if task_active else 0,
            "avoid_entities": forbidden_entities if task_active else [],
        }

        dialogue_contract = {
            "relation": three_way_relation,
            "three_way_relation": three_way_relation,
            "scene_relation": str(
                live_scene.get("relation") or ""
            ).upper(),
            "dialog_act": measured_dialogue["label"],
            "current_request": text,
            "resolved_request": resolved_request,
            "continuation": continuation,
            "reference_to_previous": reference,
            "previous_april_turn": last_assistant,
            "previous_user_turn": last_user,
            "reply_to": reply_to,
            "active_goal": effective_goal,
            "active_topic": effective_topic,
            "current_topic": effective_topic,
            "canonical_topic": effective_topic,
            "active_topic_root": self._text(semantic_anchor.get("topic_root")),
            "active_focus": self._text(semantic_anchor.get("active_focus")),
            "active_entity": active_entity,
            "entity_type": self._text(semantic_anchor.get("entity_type")),
            "direction": self._text(semantic_anchor.get("direction")),
            "development_state": deepcopy(semantic_anchor.get("development") or {}),
            "candidate_answer": candidate_answer,
            "open_task": open_task,
            "active_task": active_task_contract,
            "interactive_task_state": open_task,
            "task_memory": {
                "last_question": open_task.get("last_question"),
                "known_clues": list(open_task.get("known_clues") or [])[-12:],
                "qa_history": list(open_task.get("qa_history") or [])[-12:],
            } if task_active else {},
            "task_relation": task_relation,
            "task_transition": task_transition,
            "task_action": bool(task_answer.get("is_task_action")),
            "topic_shift": bool(live_scene.get("topic_boundary")),
            "memory_query": bool(live_scene.get("memory_query")),
            "memory_projection": live_scene.get("memory_projection", []),
            "memory_role": live_scene.get("memory_role", "supporting_evidence"),
            "resume_after_memory": bool(live_scene.get("resume_after_memory")),
            "context_dependency": canonical_context_dependency,
            "confidence": measured_dialogue["confidence"],
            "canonical": True,
            "version": "live_scene_dialogue_v3_task_ownership",
        }

        domain_evidence = [
            {"domain": k, "score": float(v)}
            for k, v in sorted(
                profile["domain_scores"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if float(v) >= 0.20
        ]

        result = build_result(text)
        result.update(
            {
                "type": measured_dialogue["label"],
                "subtype": provisional_scene_type,
                "scene_type": provisional_scene_type,
                "candidate_domains": candidate_domains,
                "required_domains": required_domains,
                "domain_confidence": {
                    k: round(float(v), 4)
                    for k, v in profile["domain_scores"].items()
                },
                "candidate_representations": profile["explicit_representations"],
                "required_representations": required_representations,
                "resolved_scene": resolved_scene,
                "live_scene": live_scene_record,
                "scene_continuity": live_scene,
                "scene_relation": live_scene.get("relation"),
                "three_way_relation": three_way_relation,
                "memory_query": bool(live_scene.get("memory_query")),
                "representation_evidence": representation_evidence,
                "semantic_profile": {
                    "active_topic": effective_topic,
                    "active_goal": effective_goal,
                    "active_entity": active_entity,
                    "candidate_answer": candidate_answer,
                    "previous_april_turn": last_assistant,
                    "resolved_scene": resolved_scene,
                    "live_scene": live_scene_record,
                    "open_task": open_task,
                    "task_relation": task_relation,
                    "task_transition": task_transition,
                    "forbidden_entities": forbidden_entities,
                    "scene_relation": live_scene.get("relation"),
                    "dialogue_history": history[-8:],
                    "representation_scores": dict(representation_scores),
                    "domain_scores": dict(profile["domain_scores"]),
                    "capability_scores": dict(capability),
                    "context_scores": dict(profile["context_scores"]),
                    "scene_matrix": matrix,
                    "engine": "quantum_interpretation_engine",
                },
                "scene_profile": {
                    "scene_type": provisional_scene_type,
                    "dialogue_mode": "semantic_unified",
                    "matrix_confidence": matrix["best_score"],
                    "matrix_margin": matrix["margin"],
                    "live_scene": live_scene_record,
                    "scene_relation": live_scene.get("relation"),
                    "scene_continuation": bool(live_scene.get("continuation")),
                    "topic_boundary": bool(live_scene.get("topic_boundary")),
                    "memory_role": live_scene.get("memory_role"),
                    "open_task": open_task,
                    "decision_owner": DECISION_OWNER,
                },
                "artifact_contract": {
                    "contract": "scene_artifact",
                    "transport": TRANSPORT_NAME,
                    "scene_type": provisional_scene_type,
                    "representation": required_representations or [provisional_scene_type],
                    "semantic_profile_ref": "semantic_profile",
                    "decision_owner": DECISION_OWNER,
                },
                "dialogue_contract": dialogue_contract,
                "semantic_anchor": deepcopy(semantic_anchor),
                "dialog_act": measured_dialogue["label"],
                "continuation": float(measured_dialogue["continuation_score"]),
                "continuation_target": (
                    f"task:{open_task.get('kind')}"
                    if task_active
                    else last_assistant or effective_topic
                ),
                "active_goal": effective_goal,
                "active_topic": effective_topic,
                "current_topic": effective_topic,
                "canonical_topic": effective_topic,
                "active_entity": active_entity,
                "candidate_answer": candidate_answer,
                "semantic_request": resolved_request,
                "context_dependency": canonical_context_dependency,
                "context_resolution": {
                    "depends_on_previous_dialogue": bool(continuation or reference),
                    "previous_user_turn": last_user,
                    "previous_assistant_turn": last_assistant,
                    "resolved_scene": resolved_scene,
                    "live_scene": live_scene_record,
                    "active_topic": active_topic,
                    "active_goal": active_goal,
                    "active_entity": active_entity,
                    "candidate_answer": candidate_answer,
                    "open_task": open_task,
                    "task_relation": task_relation,
                    "task_transition": task_transition,
                    "forbidden_entities": forbidden_entities,
                    "relation": three_way_relation,
                    "scene_relation": live_scene.get("relation"),
                    "memory_query": bool(live_scene.get("memory_query")),
                },
                "reply_to": reply_to,
                "required_capabilities": [
                    "semantic_interpretation",
                    "dialogue_context",
                    *(
                        ["memory_retrieval"]
                        if live_scene.get("memory_query")
                        else []
                    ),
                    *(
                        ["open_task_reasoning"]
                        if task_active
                        else []
                    ),
                    *(
                        ["representation_evidence"]
                        if required_representations
                        else []
                    ),
                ],
                "dialogue_relation": {
                    "relation": three_way_relation,
                    "three_way_relation": three_way_relation,
                    "same_scene": three_way_relation == "CONTINUE",
                    "continuation": continuation,
                    "reference_to_previous": reference,
                    "topic_boundary": bool(live_scene.get("topic_boundary")),
                    "scene_id": live_scene_record.get("scene_id"),
                    "canonical_topic": effective_topic,
                    "active_entity": active_entity,
                    "candidate_answer": candidate_answer,
                    "open_task": open_task,
                    "task_relation": task_relation,
                    "task_transition": task_transition,
                    "confidence": float(measured_dialogue.get("confidence", 0.0) or 0.0),
                    "source": "live_scene_continuity_engine_v2",
                },
                "dialogue_vector": {
                    "version": "live_scene_dialogue_vector_v3_task_ownership",
                    "relation": three_way_relation,
                    "three_way_relation": three_way_relation,
                    "scene_relation": live_scene.get("relation"),
                    "continuation": continuation,
                    "reference_to_previous": reference,
                    "memory_query": bool(live_scene.get("memory_query")),
                    "canonical_topic": effective_topic,
                    "active_topic": effective_topic,
                    "active_goal": effective_goal,
                    "active_entity": active_entity,
                    "candidate_answer": candidate_answer,
                    "open_task": open_task,
                    "task_relation": task_relation,
                    "task_transition": task_transition,
                    "forbidden_entities": forbidden_entities,
                    "sequence_id": self.normalize(
                        live_scene_record.get("sequence_id")
                        or (
                            state.get("active_dialogue_sequence", {}).get("sequence_id")
                            if isinstance(state.get("active_dialogue_sequence"), dict)
                            else ""
                        )
                    ),
                    "target_sequence_id": self.normalize(
                        live_scene_record.get("sequence_id")
                        or (
                            state.get("active_dialogue_sequence", {}).get("sequence_id")
                            if isinstance(state.get("active_dialogue_sequence"), dict)
                            else ""
                        )
                    ),
                    "topic_boundary": bool(live_scene.get("topic_boundary")),
                    "previous_user_turn": last_user,
                    "previous_april_turn": last_assistant,
                    "resolved_request": resolved_request,
                    "selected_memory_index": -1,
                    "selected_memory_operand": {},
                    "trajectory": {
                        "scene_id": live_scene_record.get("scene_id"),
                        "topic": effective_topic,
                        "goal": effective_goal,
                        "turn_index": live_scene_record.get("turn_index", 0),
                        "status": live_scene_record.get("status", "active"),
                    },
                    "sequence_continuation_authorized": continuation,
                    "historical_memory_is_evidence_only": True,
                    "current_task_is_authoritative": task_active,
                    "semantic_anchor": deepcopy(semantic_anchor),
                    "source": "live_scene_continuity_engine_v2",
                },
                "context_policy": {
                    "current_request": True,
                    "dialogue_vector": True,
                    "active_scene": bool(
                        live_scene_record.get("scene_id")
                    ),
                    "previous_turn": bool(reply_to),
                    "memory_retrieval": bool(live_scene.get("memory_query")),
                    "active_goal": bool(effective_goal),
                    "full_history": True,
                    "semantic_similarity": True,
                    "nli_intent": "refinement_only",
                    "linguistic_structure": True,
                    "scene_resolution": bool(resolved_scene),
                    "open_task_priority": task_active,
                },
                "quantum_interpretation_field": {
                    "linguistic": self._linguistic(text),
                    "dialogue": dialogue_contract,
                    "live_scene": live_scene_record,
                    "dialogue_vector": {
                        "relation": three_way_relation,
                        "scene_id": live_scene_record.get("scene_id"),
                        "canonical_topic": effective_topic,
                        "sequence_id": live_scene_record.get("sequence_id"),
                        "active_entity": active_entity,
                        "candidate_answer": candidate_answer,
                        "open_task": open_task,
                        "task_relation": task_relation,
                    },
                    "representation": representation_evidence,
                    "domain": domain_evidence,
                    "context_vectors": profile["context_scores"],
                    "profile": profile,
                    "scene_matrix": matrix,
                    "decision_owner": DECISION_OWNER,
                    "evidence_only": True,
                    "engine": "quantum_interpretation_engine",
                },
                "quantum_representation_measurement": {
                    "measurements": representation_evidence,
                    "scene_matrix": matrix,
                },
                "evidence": {
                    "domain": domain_evidence,
                    "representation": representation_evidence,
                    "math": float(
                        representation_scores.get("formula", 0.0)
                    ),
                    "code": float(
                        representation_scores.get("code", 0.0)
                    ),
                    "web": float(capability.get("web", 0.0)),
                    "image": float(representation_scores.get("image", 0.0)),
                    "continuation": float(
                        measured_dialogue["continuation_score"]
                    ),
                    "exploration": float(
                        capability.get("exploration", 0.0)
                    ),
                    "information": float(
                        capability.get("information", 0.0)
                    ),
                    "linguistic": self._linguistic(text),
                    "dialogue": dialogue_contract,
                    "context_vectors": profile["context_scores"],
                    "cognition": dict(cognition),
                    "semantic": dict(semantic),
                },
                "quantum_matrix": matrix,
                "matrix_scene": matrix["best_scene"],
                "matrix_confidence": matrix["best_score"],
                "decision_owner": DECISION_OWNER,
                "routing_owner": DECISION_OWNER,
                "renderer_owner": DECISION_OWNER,
                "provider_calls": 0,
                "canonical_transport": TRANSPORT_NAME,
                "semantic_authority": True,
                "semantic_decision_source": "task_aware_quantum_matrix",
                "representation_resolution": "processor_selection",
                "legacy_keyword_matching": False,
                "avoid_trigger_execution": True,
                "machine_only": True,
                "single_route": True,
                "measurement_ms": round(
                    (time.perf_counter() - started) * 1000.0,
                    3,
                ),
            }
        )

        result["memory_query"] = bool(live_scene.get("memory_query"))
        result["discussion_mode"] = float(capability.get("discussion", 0.0)) >= 0.60
        result["space_discussion"] = float(capability.get("space", 0.0)) >= 0.60
        result["exploration"] = float(capability.get("exploration", 0.0))
        result["web_context"] = float(capability.get("web", 0.0))
        result["explicit_image_generation"] = float(
            representation_scores.get("image", 0.0)
        )
        result["lightweight_visual"] = max(
            float(representation_scores.get("graph", 0.0)),
            float(representation_scores.get("diagram", 0.0)),
            float(representation_scores.get("image", 0.0)),
        ) >= 0.72
        result["contains_object"] = bool(text)
        result["contains_explanation"] = (
            float(capability.get("information", 0.0)) >= 0.60
        )
        result["contains_analysis"] = (
            float(capability.get("exploration", 0.0)) >= 0.60
        )
        result["content_role"] = (
            "explanation"
            if result["contains_explanation"]
            else "analysis"
            if result["contains_analysis"]
            else None
        )

        # Machine-facing state is explicitly task-aware so that the next layer
        # cannot accidentally resurrect a stale entity.
        dialogue_obligations = merge_dialogue_obligations(
            state.get("dialogue_obligations"),
            open_task.get("obligations") if isinstance(open_task, dict) else [],
        )
        if dialogue_obligations:
            state["dialogue_obligations"] = dialogue_obligations
            if isinstance(open_task, dict) and open_task.get("active"):
                open_task = dict(open_task)
                open_task["obligations"] = dialogue_obligations
                active_task_contract["obligations"] = dialogue_obligations

        result["active_task"] = active_task_contract
        result["open_task"] = open_task
        result["interactive_task_state"] = open_task
        result["dialogue_obligations"] = dialogue_obligations
        result["task_memory"] = {
            "last_question": open_task.get("last_question"),
            "known_clues": list(open_task.get("known_clues") or [])[-12:],
            "qa_history": list(open_task.get("qa_history") or [])[-12:],
            "candidate_answer": candidate_answer,
            "awaiting_user": bool(open_task.get("awaiting_user")),
        } if task_active else {}
        result["task_relation"] = task_relation
        result["task_transition"] = task_transition
        result["task_action"] = bool(task_answer.get("is_task_action"))
        result["active_entity"] = active_entity
        result["semantic_request"] = (
            result.get("resolved_request")
            or dialogue_contract.get("resolved_request")
            or text
        )
        result["interpretation_control"] = interpretation_control
        result["artifact_reference"] = bool(interpretation_control.get("artifact_reference"))
        result["artifact_reference_score"] = float(interpretation_control.get("artifact_reference_score", 0.0) or 0.0)
        result["candidate_answer"] = candidate_answer
        result["forbidden_entities"] = forbidden_entities

        # Canonical semantic frame: one compact identity shared by downstream engines.
        result["semantic_frame"] = {
            "intent": measured_dialogue.get("label") or "request",
            "relation": three_way_relation,
            "topic": effective_topic,
            "entity": active_entity,
            "operation": self.normalize(
                semantic.get("operation")
                or (semantic.get("semantic_task") or {}).get("operation")
                or active_task_contract.get("operation")
                or "answer"
            ),
            "goal": effective_goal,
            "representation": requested_representation or "text",
            "reference": bool(artifact_evidence.get("artifact_reference") or reference),
            "task_phase": active_task_contract.get("phase") if task_active else "",
            "sequence_id": self.normalize(dialogue_contract.get("sequence_id")),
            "scene_id": self.normalize(live_scene_record.get("scene_id")),
        }

        result["cognitive_workspace"] = DIALOG_COGNITIVE_WORKSPACE.build(
            text=text,
            semantic_result=result,
            state=state,
            history=history,
        )

        # Attach the real interpretation council to the existing workspace.
        # This is additive: legacy workspace fields remain available, while the
        # council becomes the explicit source of semantic provenance.
        result["cognitive_workspace"]["interpretation_council"] = interpretation_council
        result["cognitive_workspace"]["provider_context_plan"] = interpretation_council.get("provider_context_plan", {})
        result["cognitive_workspace"]["dialogue_history_search"] = history_search
        result["cognitive_workspace"]["history_search_ready"] = bool(history_search)
        result["cognitive_workspace"]["current_user_request"] = text
        result["cognitive_workspace"]["current_request_raw"] = text
        result["cognitive_workspace"]["canonical_user_request"] = text
        result["cognitive_workspace"]["provider_instruction"] = canonical_cognitive.get("execution_instruction", "")
        result["cognitive_workspace"]["engine_order"] = cognitive_environment.get("engine_order", [])
        result["cognitive_workspace"]["provider_request_authority"] = "CURRENT_USER_TURN"
        result["cognitive_workspace"]["historical_topics_are_evidence_only"] = True
        result["interpretation_council"] = interpretation_council
        result["canonical_interpretation"] = canonical_cognitive
        result["current_user_request"] = text
        result["canonical_user_request"] = text
        result["provider_instruction"] = canonical_cognitive.get("execution_instruction", "")
        result["provider_context_plan"] = cognitive_environment.get("provider_context_plan", {})
        result["dialogue_history_search"] = history_search
        result["memory_slider"] = deepcopy(history_search.get("memory_slider") or {})
        result["selected_memory_index"] = (
            int(history_search.get("selected_memory_index", -1)) if str(history_search.get("selected_memory_index", -1)).strip() not in {"", "None"} else -1
            if isinstance(history_search.get("memory_slider"), dict)
            and history_search.get("memory_slider", {}).get("selected_memory_operand")
            else result.get("selected_memory_index", -1)
        )
        if result.get("memory_slider", {}).get("selected_memory_operand"):
            result["selected_memory_operand"] = deepcopy(
                history_search.get("selected_memory_operand") or {}
            )
            result["selected_memory_record"] = deepcopy(
                history_search.get("selected_memory_record") or {}
            )
        result["result_dependency"] = {
            "carry_forward": history_search.get("carry_forward_result") or {},
            "operand_anchor": history_search.get("operand_anchor") or {},
            "latest_operation_result": history_search.get("latest_operation_result") or {},
            "result_chain": list(history_search.get("result_chain") or [])[-8:],
        }
        result["interpretation_engine_order"] = cognitive_environment.get("engine_order", [])
        result["interpretation_authority"] = "COGNITIVE_INTERPRETATION_COUNCIL"
        result["current_request_authority"] = "CURRENT_USER_TURN"
        result["historical_memory_is_evidence_only"] = True
        result["context_plan"] = result["cognitive_workspace"]

        # Promote the workspace decision into the canonical semantic surface used
        # by Processor/Executor. This prevents downstream adapters from falling
        # back to weaker legacy fields after the workspace has already resolved
        # the current turn.
        workspace = result["cognitive_workspace"]

        # Final canonicalization: the workspace is now the single semantic handoff
        # object.  It must reflect the preflight environment exactly, otherwise a
        # late legacy field can silently resurrect an older topic/task.
        env_task = dialogue_environment.get("active_task") if isinstance(dialogue_environment.get("active_task"), dict) else {}
        resolved_live_task = live_scene.get("open_task") if isinstance(live_scene.get("open_task"), dict) else {}
        effective_env_task = (
            resolved_live_task if resolved_live_task.get("active")
            else env_task
        )

        # The cognitive council can author a new task while the legacy dialogue
        # environment still exposes the previous active task. Reconcile that
        # split before the final canonical handoff. Obligations live outside the
        # task lifecycle, so they survive task replacement and continue to be
        # available to Executor/Provider until explicitly fulfilled.
        task_transition_final = result.get("task_transition") if isinstance(result.get("task_transition"), dict) else {}
        council_task_final = cognitive_environment.get("active_task_context") if isinstance(cognitive_environment.get("active_task_context"), dict) else {}
        if task_transition_final.get("replace_task") and council_task_final:
            effective_env_task = dict(council_task_final)
        final_obligations = merge_dialogue_obligations(
            state.get("dialogue_obligations"),
            result.get("dialogue_obligations"),
            effective_env_task.get("obligations") if isinstance(effective_env_task, dict) else [],
        )
        if final_obligations:
            effective_env_task = dict(effective_env_task or {})
            effective_env_task["obligations"] = final_obligations
            state["dialogue_obligations"] = final_obligations

        if dialogue_environment.get("relation") in {"NEW", "CONTINUE", "RECALL"}:
            workspace["turn_relation"] = dialogue_environment.get("turn_relation")
            workspace["relation"] = dialogue_environment.get("relation")
            workspace["conversation_continuation"] = bool(dialogue_environment.get("conversation_continuation"))
            workspace["semantic_continuation"] = dialogue_environment.get("relation") == "CONTINUE"
            workspace["task_continuation"] = bool(effective_env_task and dialogue_environment.get("relation") == "CONTINUE")
            workspace["reference"] = dialogue_environment.get("relation") == "RECALL"
            workspace["context_dependency"] = dialogue_environment.get("context_dependency")
            workspace["active_topic"] = self.normalize(dialogue_environment.get("current_topic"))
            workspace["active_entity"] = self.normalize(
                dialogue_environment.get("active_entity")
                or effective_env_task.get("candidate_answer")
                or effective_env_task.get("target")
            )

            # For an explicitly replaced task, never let a stale entity/topic
            # from the previous branch overwrite the new task frame.
            if task_transition_final.get("replace_task") and effective_env_task:
                workspace["active_topic"] = self.normalize(
                    effective_env_task.get("topic")
                    or effective_env_task.get("canonical_topic")
                    or workspace.get("active_topic")
                    or "задание"
                )
                workspace["active_entity"] = self.normalize(
                    effective_env_task.get("target")
                    or effective_env_task.get("candidate_answer")
                    or ""
                )
            workspace["operation"] = self.normalize(dialogue_environment.get("operation") or workspace.get("operation") or "answer")
            workspace["goal"] = self.normalize(dialogue_environment.get("goal") or workspace.get("goal") or "answer")
            workspace["representation"] = self.normalize(dialogue_environment.get("representation") or workspace.get("representation") or "text")
            workspace["active_task_context"] = effective_env_task
            workspace["dialogue_obligations"] = final_obligations
            workspace["previous_user_turn"] = self.normalize(dialogue_environment.get("previous_user_turn"))
            workspace["previous_april_turn"] = self.normalize(dialogue_environment.get("previous_april_turn"))
            workspace["resolved_request"] = self.normalize(dialogue_environment.get("resolved_request") or text)
            workspace["historical_memory_allowed"] = bool(dialogue_environment.get("historical_memory_allowed"))
            workspace["selected_memory"] = list(dialogue_environment.get("selected_memory") or [])
            workspace["continuation_content_analysis"] = dialogue_environment.get("continuation_content_analysis") or {}

            # The semantic memory slider is the only mechanism that may cross an
            # active-branch boundary during CONTINUE/RECALL. Its decision is made
            # before ProviderContextPlanEngine and must survive the legacy workspace
            # reconciliation below.
            slider = history_search.get("memory_slider") if isinstance(history_search.get("memory_slider"), dict) else {}
            slider_operand = slider.get("selected_memory_operand") if isinstance(slider.get("selected_memory_operand"), dict) else {}
            slider_enabled = bool(
                slider.get("enabled")
                and slider_operand
                and str(workspace.get("relation") or dialogue_environment.get("relation") or "").upper() in {"CONTINUE", "RECALL"}
            )
            workspace["memory_slider"] = deepcopy(slider)
            workspace["memory_slider_enabled"] = slider_enabled
            workspace["selected_memory_index"] = (
                int(slider.get("selected_memory_index", -1)) if str(slider.get("selected_memory_index", -1)).strip() not in {"", "None"} else -1
                if slider_enabled else -1
            )
            workspace["selected_memory_record"] = (
                deepcopy(slider.get("selected_memory_record") or {})
                if slider_enabled else {}
            )
            workspace["selected_memory_operand"] = (
                deepcopy(slider_operand) if slider_enabled else {}
            )
            if slider_enabled:
                workspace["historical_memory_allowed"] = True
                workspace["selected_memory"] = [{
                    "text": self.normalize(
                        " ".join(
                            x for x in (
                                slider_operand.get("user_request"),
                                slider_operand.get("april_answer"),
                                slider_operand.get("summary"),
                            ) if x
                        )
                    )[:700],
                    "sequence_id": slider_operand.get("sequence_id"),
                    "scene_id": slider_operand.get("scene_id"),
                    "score": slider_operand.get("score", 0.0),
                    "memory_index": slider_operand.get("memory_index", -1),
                    "source": "dialogue_memory_slider",
                }]
            workspace["fenced_historical_entities"] = list(dialogue_environment.get("fenced_historical_entities") or [])
            workspace["authority_chain"] = list(dialogue_environment.get("authority_chain") or workspace.get("authority_chain") or [])

            # New/continuing turns must not inherit semantically unrelated 7-day
            # memory. Recall is the only mode that is allowed to rank historical
            # topics into provider context.
            optional_context = list(workspace.get("optional_context") or [])
            slider_memory_allowed = bool(workspace.get("memory_slider_enabled"))
            if not workspace["historical_memory_allowed"] and not slider_memory_allowed:
                optional_context = [
                    entry for entry in optional_context
                    if not isinstance(entry, dict) or entry.get("key") not in {"RELEVANT_MEMORY", "SEVEN_DAY_DIALOGUE_MEMORY", "HISTORICAL_MEMORY", "CONTINUATION_MEMORY_OPERAND"}
                ]
                excluded_context = list(workspace.get("excluded_context") or [])
                excluded_context.append({
                    "key": "HISTORICAL_MEMORY",
                    "reason": "current_turn_or_active_sequence_has_priority",
                })
                workspace["excluded_context"] = excluded_context
            elif slider_memory_allowed:
                # Remove competing generic memory entries. The selected slider
                # operand is already a protected, semantically resolved dependency.
                optional_context = [
                    entry for entry in optional_context
                    if not isinstance(entry, dict) or entry.get("key") not in {"RELEVANT_MEMORY", "SEVEN_DAY_DIALOGUE_MEMORY", "HISTORICAL_MEMORY"}
                ]
            workspace["optional_context"] = optional_context
            workspace["selected_memory"] = (
                list(workspace.get("selected_memory") or [])
                if workspace["historical_memory_allowed"] or slider_memory_allowed else []
            )

            # Rebuild the provider section index after the memory fence without
            # changing the provider or renderer route.
            provider_sections = list(workspace.get("provider_sections") or [])
            if not workspace["historical_memory_allowed"] and not slider_memory_allowed:
                provider_sections = [
                    entry for entry in provider_sections
                    if not isinstance(entry, dict) or entry.get("name") not in {"RELEVANT_MEMORY", "SEVEN_DAY_DIALOGUE_MEMORY", "HISTORICAL_MEMORY", "CONTINUATION_MEMORY_OPERAND"}
                ]
            elif slider_memory_allowed:
                provider_sections = [
                    entry for entry in provider_sections
                    if not isinstance(entry, dict) or entry.get("name") not in {"RELEVANT_MEMORY", "SEVEN_DAY_DIALOGUE_MEMORY", "HISTORICAL_MEMORY"}
                ]
            workspace["provider_sections"] = provider_sections

        # Dedicated provider-context planner is the final relevance authority.
        provider_plan = interpretation_council.get("provider_context_plan")
        if isinstance(provider_plan, dict) and provider_plan:
            workspace["provider_context_plan"] = provider_plan
            workspace["required_context"] = list(provider_plan.get("required_context") or [])
            workspace["optional_context"] = list(provider_plan.get("optional_context") or [])
            workspace["excluded_context"] = list(provider_plan.get("excluded_context") or [])
            workspace["provider_sections"] = list(provider_plan.get("provider_sections") or [])
            workspace["context_selection_done_before_provider"] = True
            workspace["provider_must_not_reselect_context"] = True
            workspace["provider_hard_budget_tokens"] = int(provider_plan.get("hard_budget_tokens") or PROVIDER_INPUT_HARD_BUDGET)
            workspace["provider_soft_target_tokens"] = int(provider_plan.get("soft_target_tokens") or PROVIDER_INPUT_SOFT_TARGET_NEW)
            workspace["current_request_raw"] = text

        workspace_frame = workspace.get("semantic_frame") if isinstance(workspace.get("semantic_frame"), dict) else {}
        if workspace_frame:
            result["semantic_frame"] = dict(workspace_frame)
            workspace_relation = str(workspace.get("relation") or "").upper()
            promoted_intent = workspace_frame.get("intent") or result.get("type")
            if workspace_relation == "NEW_TOPIC" and promoted_intent in {"identity", "statement"}:
                promoted_intent = "request"
            result["type"] = promoted_intent
            result["operation"] = workspace.get("operation") or result.get("operation")
            result["goal"] = workspace.get("goal") or result.get("goal")
            result["representation"] = workspace.get("representation") or result.get("representation")
            result["canonical_topic"] = workspace.get("active_topic") if "active_topic" in workspace else result.get("canonical_topic")
            result["active_topic"] = workspace.get("active_topic") if "active_topic" in workspace else result.get("active_topic")
            result["active_entity"] = (cognitive_environment.get("active_entity") or (workspace.get("active_entity") if "active_entity" in workspace else result.get("active_entity")))
            result["continuation"] = bool(workspace.get("continuation"))
            result["reference_to_previous"] = bool(workspace.get("reference"))
            result["resolved_request"] = workspace.get("resolved_request") or result.get("resolved_request")
            result["semantic_request"] = workspace.get("resolved_request") or result.get("semantic_request")
            result["history_dependent_task"] = bool(workspace.get("task_continuation"))
            result["current_turn_authority"] = True
            result["historical_memory_is_evidence_only"] = True
            result["dialogue_branch_index"] = deepcopy(workspace.get("dialogue_branch_index") or {})
            if workspace.get("memory_slider_enabled") and workspace.get("selected_memory_operand"):
                result["continuation_authority"] = "semantic_memory_slider"
                result["selected_memory_index"] = int(workspace.get("selected_memory_index", -1)) if str(workspace.get("selected_memory_index", -1)).strip() not in {"", "None"} else -1
                result["selected_memory_operand"] = deepcopy(workspace.get("selected_memory_operand") or {})
                result["selected_memory_record"] = deepcopy(workspace.get("selected_memory_record") or {})
                result["memory_slider"] = deepcopy(workspace.get("memory_slider") or {})
            elif workspace.get("conversation_continuation") and (workspace.get("continuation") or workspace.get("reference")):
                result["continuation_authority"] = (
                    "resumed_dialogue_branch" if workspace.get("target_sequence_id")
                    else "active_dialogue_sequence"
                )
                result["selected_memory_index"] = -1
                branch_index = workspace.get("dialogue_branch_index") if isinstance(workspace.get("dialogue_branch_index"), dict) else {}
                selected_branch = branch_index.get("selected_branch") if isinstance(branch_index.get("selected_branch"), dict) else {}
                result["selected_memory_operand"] = {
                    "source": "dialogue_branch_index" if workspace.get("target_sequence_id") else "active_dialogue_sequence",
                    "sequence_id": workspace.get("target_sequence_id") or workspace.get("sequence_id"),
                    "branch_id": workspace.get("target_branch_id") or selected_branch.get("branch_id"),
                    "topic": selected_branch.get("topic") or workspace.get("active_topic"),
                    "entity": selected_branch.get("canonical_entity") or workspace.get("active_entity"),
                    "user_request": workspace.get("previous_user_turn"),
                    "april_answer": workspace.get("previous_april_turn"),
                    "user_id": (workspace.get("authenticated_scope") or {}).get("user_id", ""),
                    "conversation_id": (workspace.get("authenticated_scope") or {}).get("conversation_id", ""),
                }
                result["selected_memory_record"] = {}
            else:
                result["continuation_authority"] = "current_turn"
                result["selected_memory_index"] = -1
                result["selected_memory_operand"] = {}
                result["selected_memory_record"] = {}
                result["memory_slider"] = {}

            # Keep the immediately preceding authenticated USER↔APRIL pair on the
            # top-level result too. Older consumers may still read these fields
            # directly instead of entering dialogue_contract/dialogue_vector.
            result["previous_user_turn"] = (
                workspace.get("previous_user_turn") or result.get("previous_user_turn")
            )
            result["previous_april_turn"] = (
                workspace.get("previous_april_turn") or result.get("previous_april_turn")
            )

            control = result.get("interpretation_control") if isinstance(result.get("interpretation_control"), dict) else {}
            control = dict(control)
            control.update({
                "relation": workspace.get("relation") or control.get("relation"),
                "context_policy": (
                    "active_sequence_compact" if workspace.get("continuation") or workspace.get("reference")
                    else "current_turn_only"
                ),
                "memory_policy": (
                    "semantic_memory_slider_selected_operand"
                    if workspace.get("memory_slider_enabled")
                    else "selected_live_sequence_only"
                    if workspace.get("continuation") or workspace.get("reference")
                    else "no_historical_content"
                ),
                "current_turn_authority": True,
                "historical_memory_is_evidence_only": True,
                "provider_must_follow_plan": True,
            })
            result["interpretation_control"] = control

            # Make the new semantic bridge visible through the existing canonical
            # dialogue contract so older adapters cannot resurrect the stale task.
            contract = result.get("dialogue_contract") if isinstance(result.get("dialogue_contract"), dict) else {}
            contract = dict(contract)
            contract.update({
                "relation": workspace.get("relation") or contract.get("relation"),
                "three_way_relation": workspace.get("relation") or contract.get("three_way_relation"),
                "continuation": bool(workspace.get("continuation")),
                "reference_to_previous": bool(workspace.get("reference")),
                "context_dependency": workspace.get("context_dependency") or contract.get("context_dependency"),
                "resolved_request": workspace.get("resolved_request") or contract.get("resolved_request"),
                "previous_user_turn": workspace.get("previous_user_turn") or contract.get("previous_user_turn"),
                "previous_april_turn": workspace.get("previous_april_turn") or contract.get("previous_april_turn"),
                "canonical_topic": workspace.get("active_topic") or contract.get("canonical_topic"),
                "active_topic": workspace.get("active_topic") or contract.get("active_topic"),
                "current_topic": workspace.get("active_topic") or contract.get("current_topic"),
                "active_entity": workspace.get("active_entity") or "",
                "active_task": workspace.get("active_task_context") or {},
                "open_task": workspace.get("active_task_context") or {},
                "interactive_task_state": workspace.get("active_task_context") or {},
                "task_relation": workspace.get("task_relation") or {
                    "owned": bool(workspace.get("task_continuation")),
                    "reason": "cognitive_workspace",
                },
                "sequence_id": workspace.get("sequence_id") or contract.get("sequence_id"),
                "target_sequence_id": workspace.get("sequence_id") or contract.get("target_sequence_id"),
                "conversation_continuation": bool(workspace.get("conversation_continuation")),
                "semantic_continuation": bool(workspace.get("semantic_continuation")),
                "task_continuation": bool(workspace.get("task_continuation")),
                "continuation_content_analysis": workspace.get("continuation_content_analysis") or {},
                "continuation_authority": result.get("continuation_authority"),
                "memory_slider": deepcopy(workspace.get("memory_slider") or {}),
                "selected_memory_operand": result.get("selected_memory_operand") or {},
                "selected_memory_record": result.get("selected_memory_record") or {},
                "selected_memory_index": result.get("selected_memory_index", -1),
                "target_sequence_id": workspace.get("target_sequence_id") or contract.get("target_sequence_id") or "",
                "target_branch_id": workspace.get("target_branch_id") or contract.get("target_branch_id") or "",
                "target_branch": deepcopy((workspace.get("dialogue_branch_index") or {}).get("selected_branch") or contract.get("target_branch") or {}),
            })
            contract["dialogue_obligations"] = final_obligations
            result["dialogue_contract"] = contract
            result["interactive_task_state"] = workspace.get("active_task_context") or {}
            result["open_task"] = workspace.get("active_task_context") or {}
            result["dialogue_obligations"] = final_obligations
            result["task_active"] = bool(workspace.get("task_continuation"))

            vector = result.get("dialogue_vector") if isinstance(result.get("dialogue_vector"), dict) else {}
            vector = dict(vector)
            vector.update({
                "relation": workspace.get("relation") or vector.get("relation"),
                "three_way_relation": workspace.get("relation") or vector.get("three_way_relation"),
                "continuation": bool(workspace.get("continuation")),
                "reference_to_previous": bool(workspace.get("reference")),
                "conversation_continuation": bool(workspace.get("conversation_continuation")),
                "semantic_continuation": bool(workspace.get("semantic_continuation")),
                "task_continuation": bool(workspace.get("task_continuation")),
                "canonical_topic": workspace.get("active_topic"),
                "active_topic": workspace.get("active_topic"),
                "active_entity": workspace.get("active_entity"),
                "previous_user_turn": workspace.get("previous_user_turn"),
                "previous_april_turn": workspace.get("previous_april_turn"),
                "resolved_request": workspace.get("resolved_request"),
                "sequence_id": workspace.get("sequence_id"),
                "target_sequence_id": workspace.get("target_sequence_id") or "",
                "target_branch_id": workspace.get("target_branch_id") or "",
                "target_branch": deepcopy((workspace.get("dialogue_branch_index") or {}).get("selected_branch") or {}),
                "branch_index": deepcopy(workspace.get("dialogue_branch_index") or {}),
                "turn_relation": workspace.get("turn_relation") or "",
                "continuation_authority": result.get("continuation_authority"),
                "memory_slider": deepcopy(workspace.get("memory_slider") or {}),
                "selected_memory_index": result.get("selected_memory_index", -1),
                "selected_memory_operand": result.get("selected_memory_operand") or {},
                "selected_memory_record": result.get("selected_memory_record") or {},
                "continuation_content_analysis": workspace.get("continuation_content_analysis") or {},
            })
            result["dialogue_vector"] = vector

            qif = result.get("quantum_interpretation_field") if isinstance(result.get("quantum_interpretation_field"), dict) else {}
            if qif:
                qif = dict(qif)
                qif["dialogue"] = contract
                qif["dialogue_vector"] = vector
                result["quantum_interpretation_field"] = qif
            evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
            if evidence:
                evidence = dict(evidence)
                evidence["dialogue"] = contract
                result["evidence"] = evidence

        # Final council authority surface.
        result["current_user_request"] = text
        result["canonical_user_request"] = text
        result["interpretation_council"] = interpretation_council
        result["canonical_interpretation"] = canonical_cognitive
        result["provider_instruction"] = canonical_cognitive.get("execution_instruction", "")
        result["interpretation_engine_order"] = cognitive_environment.get("engine_order", [])
        result["current_request_authority"] = "CURRENT_USER_TURN"
        result["interpretation_authority"] = "COGNITIVE_INTERPRETATION_COUNCIL"
        result["interpretation_consistency_valid"] = bool(
            (cognitive_environment.get("consistency") or {}).get("valid")
        )

        result["estimated_action_count"] = estimate_action_count(result)
        result["response_complexity"] = determine_response_complexity(result)
        result["factory_order"] = build_factory_order(result)
        result["scene_strategy"] = build_scene_strategy(result)
        result["interpretation_state"] = synchronize_interpretation_context(
            build_interpretation_state(),
            result,
        )
        result["transport_state"] = export_transport_state(
            result["interpretation_state"],
            result,
        )
        result["interpretation_state"]["diagnostics"]["matrix"] = matrix
        result["transport_diagnostics"] = build_transport_diagnostics(result)

        result["interpretation_council_diagnostics"] = {
            "engine": INTERPRETATION_ORCHESTRATOR.NAME,
            "version": INTERPRETATION_ORCHESTRATOR.VERSION,
            "engine_count": len(cognitive_environment.get("engine_order", [])),
            "engine_order": cognitive_environment.get("engine_order", []),
            "canonical_relation": cognitive_environment.get("relation"),
            "canonical_turn_relation": cognitive_environment.get("turn_relation"),
            "current_user_request_preserved": cognitive_environment.get("current_user_request") == text,
            "provider_instruction_separate": bool(cognitive_environment.get("provider_instruction")) and cognitive_environment.get("provider_instruction") != text,
            "memory_selected": len(cognitive_environment.get("selected_memory") or []),
            "historical_topics_fenced": bool(cognitive_environment.get("historical_topics_are_evidence_only")),
            "consistency_valid": bool((cognitive_environment.get("consistency") or {}).get("valid")),
            "provider_context_plan": {
                "version": (cognitive_environment.get("provider_context_plan") or {}).get("version"),
                "hard_budget_tokens": (cognitive_environment.get("provider_context_plan") or {}).get("hard_budget_tokens"),
                "soft_target_tokens": (cognitive_environment.get("provider_context_plan") or {}).get("soft_target_tokens"),
                "required_context": [
                    x.get("key") for x in (cognitive_environment.get("provider_context_plan") or {}).get("required_context", [])
                    if isinstance(x, dict)
                ],
                "optional_context": [
                    x.get("key") for x in (cognitive_environment.get("provider_context_plan") or {}).get("optional_context", [])
                    if isinstance(x, dict)
                ],
                "excluded_context": [
                    x.get("key") for x in (cognitive_environment.get("provider_context_plan") or {}).get("excluded_context", [])
                    if isinstance(x, dict)
                ],
                "provider_must_not_reselect_context": bool(
                    (cognitive_environment.get("provider_context_plan") or {}).get("provider_must_not_reselect_context")
                ),
            },
            "decision_owner": DECISION_OWNER,
        }

        result["semantic_engine_diagnostics"] = {
            "engine": "quantum_interpretation_engine",
            "version": "task_ownership_v2",
            "matrix_shape": matrix["matrix_shape"],
            "matrix_features": matrix["feature_order"],
            "single_measurement": True,
            "single_route": True,
            "fallback_mode": False,
            "substring_routing": False,
            "renderer_selection_owner": DECISION_OWNER,
            "provider_calls": 0,
            "open_task_priority": task_active,
            "task_transition": task_transition,
            "task_relation": task_relation,
            "active_entity": active_entity,
            "candidate_answer": candidate_answer,
            "forbidden_entities": forbidden_entities,
            "historical_memory_is_evidence_only": True,
        }

        propagate_canonical_response(result, result["transport_state"])
        bridge_machine_response(result, result["transport_state"])
        validate_response_complexity(result)
        return result

# Canonical result / transport helpers
# ---------------------------------------------------------------------------

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
    dialogue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a renderer-neutral scene blueprint for Semantic Core.

    This helper contains no routing and no renderer selection. It preserves the
    Interpretation decision as a compact semantic scene description.
    """
    reps: list[str] = []
    for value in list(requested_outputs or ()) + list(scene_composition or ()) + [production_representation]:
        if isinstance(value, dict):
            value = value.get("type") or value.get("representation") or value.get("kind")
        value = str(value or "").strip().lower()
        if value and value not in reps:
            reps.append(value)
    if not reps:
        reps = ["text"]

    preferred = str(production_representation or "text").strip().lower() or reps[0]
    if preferred not in reps:
        reps.insert(0, preferred)

    dialogue = dialogue if isinstance(dialogue, dict) else {}
    live_scene = dialogue.get("live_scene") if isinstance(dialogue.get("live_scene"), dict) else {}

    return {
        "version": "live_scene_blueprint_v1",
        "scene_kind": "composite" if len(reps) > 1 else reps[0],
        "representations": reps,
        "preferred_representation": preferred,
        "active_topic": str(active_topic or live_scene.get("topic") or "").strip(),
        "active_goal": str(active_goal or live_scene.get("goal") or "").strip(),
        "subject": str(subject or "").strip(),
        "semantic_summary": str(semantic_summary or text or "").strip()[:1800],
        "dialogue": {
            "relation": str(
                dialogue.get("three_way_relation")
                or dialogue.get("relation")
                or "NEW"
            ).strip().upper(),
            "continuation": bool(dialogue.get("continuation")),
            "reference_to_previous": bool(dialogue.get("reference_to_previous")),
            "scene_id": str(
                dialogue.get("scene_id")
                or live_scene.get("scene_id")
                or ""
            ).strip(),
            "canonical_topic": str(
                dialogue.get("canonical_topic")
                or active_topic
                or live_scene.get("topic")
                or ""
            ).strip(),
        },
        "composition": [dict(x) if isinstance(x, dict) else str(x) for x in list(scene_composition or ())[:16]],
        "ownership": {
            "interpretation_owner": "INTERPRETATION_LAYER",
            "semantic_owner": "SEMANTIC_CORE",
            "renderer_owner": "PROCESSOR_SELECTED",
        },
        "renderer_neutral": True,
    }


@dataclass
class SemanticEvidence:
    label: str
    score: float
    source: str
    positive: bool = True
    details: Dict[str, Any] | None = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "score": max(0.0, min(1.0, float(self.score))),
            "source": self.source,
            "positive": bool(self.positive),
            "details": self.details or {},
        }



class DialogCognitiveWorkspace:
    """Pre-provider semantic workspace for context selection.

    This is a deterministic working memory layer, not a second language model.
    It combines the existing Interpretation/continuity evidence into a ranked
    context plan before the 900-token provider packer runs.
    """

    VERSION = "dialog_cognitive_workspace_v1"
    MAX_MEMORY_CANDIDATES = 24

    def __init__(self) -> None:
        self._lock = threading.RLock()

    @staticmethod
    def _text(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    @classmethod
    def _tokens(cls, value: Any) -> set[str]:
        return set(re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", cls._text(value).lower()))

    @classmethod
    def _similarity(cls, a: Any, b: Any) -> float:
        left, right = cls._tokens(a), cls._tokens(b)
        if not left or not right:
            return 0.0
        return len(left & right) / max(1.0, min(len(left), len(right)))

    @classmethod
    def _excerpt(cls, value: Any, limit: int = 360) -> str:
        text = cls._text(value)
        if len(text) <= limit:
            return text
        parts = [x.strip() for x in re.split(r"(?<=[.!?。！？])\s+", text) if x.strip()]
        key_lines = [
            x.strip(" -\t") for x in text.splitlines()
            if x.strip().startswith(("-", "•", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))
        ]
        selected: list[str] = []
        selected.extend(parts[:1])
        selected.extend(key_lines[:4])
        if parts:
            selected.append(parts[-1])
        compact = " | ".join(dict.fromkeys(x for x in selected if x))
        if compact and len(compact) <= limit:
            return compact
        head = max(180, int(limit * 0.60))
        tail = max(80, limit - head - 5)
        return text[:head].rstrip() + " … " + text[-tail:].lstrip()

    @classmethod
    def _instruction_signals(cls, text: str) -> dict[str, Any]:
        low = cls._text(text).lower()
        terms = {
            "must": ("нужно", "должен", "должна", "обязательно", "важно", "must", "required"),
            "forbidden": ("не пиши", "не создавай", "не меняй", "не трогай", "не выдумывай", "не используй", "do not", "don't"),
            "continuation": ("продолж", "теперь", "дальше", "ещё", "еще", "а теперь", "continue", "next"),
            "architecture": ("архитект", "контракт", "слой", "движок", "engine", "pipeline", "маршрут", "processor", "provider"),
            "code": ("python", "код", "класс", "функц", "module", "class", "function"),
            "visual": ("картин", "изображ", "схем", "график", "диаграм", "render", "artifact"),
        }
        return {
            key: [needle for needle in needles if needle in low][:6]
            for key, needles in terms.items()
        }

    @classmethod
    def _request_directives(cls, text: str) -> list[str]:
        """Extract short, high-signal instruction clauses from the current turn."""
        directives: list[str] = []
        for raw in str(text or "").splitlines():
            line = cls._text(raw).strip(" -•\t")
            low = line.lower()
            if not line:
                continue
            if any(marker in low for marker in (
                "не ", "нельзя", "обязательно", "важно", "нужно", "должен", "должна",
                "только", "without", "must ", "required", "do not", "don't", "only ",
            )):
                directives.append(cls._excerpt(line, 220))
            elif re.match(r"^(?:\d+\.|[a-z]\))\s+", low):
                directives.append(cls._excerpt(line, 180))
            if len(directives) >= 8:
                break
        return list(dict.fromkeys(directives))

    @classmethod
    def _request_identifiers(cls, text: str) -> list[str]:
        values = re.findall(r"`([^`]{2,80})`", str(text or ""))
        if not values:
            values = re.findall(r"\b[A-Z][A-Za-z0-9_]{2,}(?:\s+[A-Z][A-Za-z0-9_]{2,})*\b", str(text or ""))
        return list(dict.fromkeys(cls._text(v) for v in values if cls._text(v)))[:12]

    @classmethod
    def _safe_topic(cls, candidates: list[Any], text: str) -> str:
        current = cls._text(text)
        current_low = current.lower()
        generic = {"вопрос", "ответ", "запрос", "тема", "опрос", "question", "request", "answer"}
        scored: list[tuple[float, str]] = []
        for candidate in candidates:
            value = cls._text(candidate)
            if not value or len(value) > 140 or value.lower() in generic:
                continue
            low = value.lower()
            overlap = cls._similarity(value, current)
            explicit = 1.0 if low in current_low else 0.0
            scored.append((explicit + overlap, value))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return cls._excerpt(scored[0][1], 140)
        identifiers = cls._request_identifiers(text)
        if identifiers:
            return identifiers[0]
        first = cls._text(re.split(r"(?<=[.!?。！？])\s+", current)[0] if current else "")
        return cls._excerpt(first, 140)

    @classmethod
    def _safe_operation(cls, value: Any, representation: str, directives: list[str]) -> str:
        known = {"answer", "build", "modify", "retrieve", "calculate", "analyze", "explain", "summarize", "list", "present"}
        op = cls._text(value).lower()
        joined = (cls._text(" ".join(directives)) + " " + cls._text(representation)).lower()
        # A generic legacy `answer` operation is too weak for explicit
        # construction/specification requests. Prefer the current-turn action
        # semantics when the request clearly asks to define/create/design/build.
        explicit_build = any(x in joined for x in (
            "создай", "создать", "определи", "определить", "спроектируй",
            "спроектировать", "зафиксируй", "структур", "контракт",
            "реализуй", "реализац", "покажи", "выведи", "опиши в коде",
            "build", "design", "specify", "implement",
        ))
        if op == "answer" and explicit_build and representation in {
            "code", "diagram", "image", "graph", "table", "formula", "gallery", "text"
        }:
            return "build"
        if op in known and len(op) < 32:
            return op
        if any(x in joined for x in ("исправ", "измени", "передел", "добавь", "убери", "modify", "change")):
            return "modify"
        if representation in {"code", "image", "diagram", "graph", "table", "formula", "gallery", "link"}:
            return "build"
        if any(x in joined for x in ("объясни", "почему", "что такое", "explain")):
            return "explain"
        return "answer"

    @classmethod
    def _safe_goal(cls, value: Any, operation: str, representation: str, text: str) -> str:
        goal = cls._text(value)
        if operation == "build" and goal.lower() in {"answer", "reply", "question"}:
            return "present" if representation in {"image", "diagram", "graph", "table", "formula", "code", "gallery"} else "obtain"
        if goal and len(goal) <= 80 and goal.lower() not in cls._text(text).lower():
            return goal
        return {
            "retrieve": "obtain",
            "explain": "understand",
            "analyze": "understand",
            "build": "present" if representation in {"image", "diagram", "graph", "table", "formula", "code", "gallery"} else "answer",
            "modify": "transform",
            "summarize": "understand",
            "list": "answer",
        }.get(operation, "answer")

    @classmethod
    def _explicit_artifact_dependency(cls, text: str, control: dict[str, Any], semantic_result: dict[str, Any]) -> bool:
        low = cls._text(text).lower()
        explicit_ref = any(x in low for x in (
            "этот график", "этот рисунок", "эту картинку", "на картинке", "этот файл",
            "на схеме", "эту схему", "предыдущий рисунок", "предыдущую картинку",
            "этот артефакт", "this image", "this diagram", "this file",
        ))
        explicit_transform = any(x in low for x in (
            "измени эту", "переделай эту", "добавь на", "убери с", "нарисуй на",
            "вставь в эту", "modify this", "edit this",
        ))
        return bool(
            explicit_ref
            or explicit_transform
            or (bool(control.get("artifact_reference")) and explicit_ref)
            or (bool(semantic_result.get("target_artifact")) and explicit_ref)
        )

    @classmethod
    def _compact_value(cls, value: Any, depth: int = 0, max_depth: int = 4, max_items: int = 8, max_keys: int = 12) -> Any:
        if depth > max_depth or value in (None, "", [], {}):
            return None
        if isinstance(value, (str, int, float, bool)):
            return cls._excerpt(value, 360) if isinstance(value, str) else value
        if isinstance(value, dict):
            out = {}
            for key, item in list(value.items())[:max_keys]:
                compact = cls._compact_value(item, depth + 1, max_depth, max_items, max_keys)
                if compact not in (None, "", [], {}):
                    out[str(key)] = compact
            return out
        if isinstance(value, (list, tuple, set)):
            out = []
            for item in list(value)[:max_items]:
                compact = cls._compact_value(item, depth + 1, max_depth, max_items, max_keys)
                if compact not in (None, "", [], {}):
                    out.append(compact)
            return out
        return cls._text(value)

    @classmethod
    def _turn_text(cls, item: Any) -> str:
        if not isinstance(item, dict):
            return cls._text(item)
        user = item.get("user")
        april = item.get("april") or item.get("assistant")
        if isinstance(user, dict):
            user = user.get("text") or user.get("content") or user.get("answer")
        if isinstance(april, dict):
            april = april.get("answer") or april.get("content") or april.get("summary")
        direct = cls._text(item.get("text") or item.get("content") or item.get("summary"))
        return cls._excerpt(" ".join(x for x in (user, april, direct) if x), 420)

    @classmethod
    def _task_digest(cls, task: dict[str, Any]) -> dict[str, Any]:
        task = task if isinstance(task, dict) else {}
        return {
            "active": bool(task.get("active") or task.get("status") in {"open", "active", "continuing"}),
            "kind": cls._text(task.get("kind") or task.get("type")),
            "phase": cls._text(task.get("phase") or task.get("task_phase")),
            "goal": cls._excerpt(task.get("goal") or task.get("task_goal"), 160),
            "target": cls._excerpt(task.get("target") or task.get("target_entity") or task.get("entity"), 160),
            "prompt": cls._excerpt(task.get("prompt") or task.get("question") or task.get("last_question"), 260),
            "expected_input_type": cls._text(task.get("expected_input_type") or task.get("input_type")),
            "candidate_answer": cls._excerpt(task.get("candidate_answer") or task.get("answer_candidate"), 120),
            "known_clues": [cls._excerpt(x, 120) for x in list(task.get("known_clues") or [])[-4:] if cls._text(x)],
            "qa_history": [
                cls._compact_value(x, depth=0, max_depth=2, max_items=4, max_keys=5)
                for x in list(task.get("qa_history") or task.get("turns") or [])[-2:]
            ],
        }

    def _memory_candidates(self, state: dict[str, Any], history: list[Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        raw = state.get("memory_timeline") if isinstance(state, dict) else None
        if isinstance(raw, dict):
            values: list[Any] = []
            for value in raw.values():
                values.extend(value if isinstance(value, list) else [value])
        elif isinstance(raw, list):
            values = list(raw)
        else:
            values = []

        for key in ("active_sequence_turns", "relevant_7d_turns", "seven_day_memory_turns"):
            value = state.get(key) if isinstance(state, dict) else None
            if isinstance(value, list):
                values.extend(value)
        values.extend(history[-8:])

        now = time.time()
        cutoff = now - DialogueEnvironmentEngine.SEVEN_DAYS_SECONDS
        seen: set[str] = set()
        for item in reversed(values[-self.MAX_MEMORY_CANDIDATES * 2:]):
            if isinstance(item, dict):
                stamp = DialogueEnvironmentEngine._timestamp(
                    item.get("created_at") or item.get("timestamp") or item.get("updated_at")
                )
                # The 7-day memory contract is enforced when a source exposes a
                # timestamp. Entries without a timestamp are treated as transient
                # active-history evidence, not as historical memory.
                is_historical_store = bool(item.get("sequence_id") or item.get("memory_kind") or item.get("created_at"))
                if stamp is not None and stamp < cutoff:
                    continue
                if stamp is None and is_historical_store:
                    continue
            text = self._turn_text(item)
            if not text:
                continue
            sig = text.lower()
            if sig in seen:
                continue
            seen.add(sig)
            candidates.append({
                "text": text,
                "sequence_id": self._text(item.get("sequence_id")) if isinstance(item, dict) else "",
                "scene_id": self._text(item.get("scene_id") or item.get("visual_scene_id")) if isinstance(item, dict) else "",
                "raw": item if isinstance(item, dict) else {},
            })
        return candidates[:self.MAX_MEMORY_CANDIDATES]

    @classmethod
    def _reference_signals(cls, text: str) -> dict[str, Any]:
        low = cls._text(text).lower()
        words = cls._tokens(text)
        markers = (
            "её", "ее", "этот", "эта", "это", "эту", "эти", "его", "ему", "ей",
            "она", "он", "оно", "они", "там", "туда", "сюда", "отсюда",
            "теперь", "дальше", "слева", "справа", "снова", "ещё", "еще",
            "а теперь", "а слева", "а справа", "кто её", "кто ее", "про неё", "про нее",
            "what is it", "who sings it", "this", "that", "it", "then", "next", "left", "right",
        )
        def present(marker: str) -> bool:
            marker_low = marker.lower()
            if " " in marker_low:
                return marker_low in low
            return marker_low in words

        matched = [x for x in markers if present(x)]
        return {
            "markers": matched[:10],
            "deictic": bool(matched),
            "short_followup": len(words) <= 8,
            "explicit_reference": any(x in low for x in ("эту", "этот", "эта", "эти", "её", "ее", "кто её", "кто ее", "this ", "it ")),
        }

    @classmethod
    def _extract_quoted_reference(cls, text: str) -> str:
        value = str(text or "")
        patterns = (
            r"«([^»]{3,140})»",
            r"“([^”]{3,140})”",
            r'"([^\"]{3,140})"',
            r"'([^']{3,140})'",
        )
        for pattern in patterns:
            for match in re.findall(pattern, value):
                candidate = cls._text(match)
                if candidate and len(candidate.split()) <= 18:
                    return candidate
        return ""

    @classmethod
    def _build_continuation_bridge(
        cls,
        *,
        text: str,
        dialogue: dict[str, Any],
        frame: dict[str, Any],
        task: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        dialogue = dialogue if isinstance(dialogue, dict) else {}
        frame = frame if isinstance(frame, dict) else {}
        task = task if isinstance(task, dict) else {}
        state = state if isinstance(state, dict) else {}

        previous_user = cls._text(
            dialogue.get("previous_user_turn")
            or state.get("last_user_turn")
        )
        previous_april = cls._text(
            dialogue.get("previous_april_turn")
            or state.get("last_april_turn")
        )
        previous_pair_present = bool(previous_user or previous_april)

        sequence = state.get("active_dialogue_sequence") if isinstance(state.get("active_dialogue_sequence"), dict) else {}
        sequence_id = cls._text(
            dialogue.get("sequence_id")
            or sequence.get("sequence_id")
            or state.get("dialogue_sequence_id")
        )
        authenticated_scope = {
            "user_id": cls._text(state.get("user_id")),
            "conversation_id": cls._text(state.get("conversation_id")),
            "dialogue_sequence_id": sequence_id,
        }
        same_authenticated_dialogue = bool(
            authenticated_scope["user_id"]
            and authenticated_scope["conversation_id"]
            and sequence_id
            and previous_pair_present
        )

        refs = cls._reference_signals(text)
        words = cls._tokens(text)
        previous_user_similarity = cls._similarity(text, previous_user)
        previous_april_similarity = cls._similarity(text, previous_april)
        recent_similarity = max(previous_user_similarity, previous_april_similarity)

        task_text = " ".join(
            cls._text(x) for x in (
                task.get("kind"), task.get("topic"), task.get("target"), task.get("prompt"),
                task.get("last_question"), task.get("goal"),
                frame.get("entity"), dialogue.get("active_entity"),
            ) if cls._text(x)
        )
        task_similarity = cls._similarity(text, task_text)
        recent_task_similarity = max(
            cls._similarity(previous_user, task_text),
            cls._similarity(previous_april, task_text),
        )

        raw_task_active = bool(
            task.get("active")
            or task.get("status") in {"open", "active", "continuing", "resumable", "answer_received"}
        )
        task_relation = dialogue.get("task_relation")
        if not isinstance(task_relation, dict):
            task_relation = {}
        task_answer = bool(task_relation.get("is_answer") or task_relation.get("is_task_action"))

        # A task owns the current turn only when the current turn actually fits
        # the task or is a discourse follow-up to a recent turn that belongs to it.
        # Merely having a persisted open task is never enough.
        task_answer_signal = bool(
            task_answer
            and (
                task_similarity >= 0.08
                or (
                    refs["short_followup"]
                    and len(words) <= 2
                    and recent_task_similarity >= 0.08
                )
            )
        )
        task_continuation = bool(
            raw_task_active
            and (
                task_similarity >= 0.18
                or (refs["deictic"] and recent_task_similarity >= 0.10)
                or task_answer_signal
            )
        )

        quoted_entity = cls._extract_quoted_reference(previous_april)
        reference = bool(
            previous_pair_present
            and (
                refs["explicit_reference"]
                or (refs["deictic"] and recent_similarity >= 0.03)
                or bool(quoted_entity and recent_similarity >= 0.02)
            )
        )

        semantic_continuation = bool(
            previous_pair_present
            and (
                task_continuation
                or reference
                or (refs["deictic"] and recent_similarity >= 0.02)
                or recent_similarity >= 0.22
            )
        )

        # A self-contained request can start a new topic while remaining inside
        # the same authenticated dialogue sequence. This is the distinction the
        # old task owner collapsed into one CONTINUE flag.
        topic_relation = "CONTINUE" if semantic_continuation else "NEW_TOPIC" if previous_pair_present else "NEW"
        conversation_continuation = same_authenticated_dialogue

        resolved_entity = ""
        if reference and quoted_entity:
            resolved_entity = quoted_entity
        elif task_continuation:
            resolved_entity = cls._text(
                task.get("target")
                or dialogue.get("active_entity")
                or frame.get("entity")
            )
        elif semantic_continuation and recent_similarity >= 0.10:
            candidate = cls._text(frame.get("entity") or dialogue.get("active_entity"))
            if candidate and cls._similarity(candidate, text) >= 0.05:
                resolved_entity = candidate

        current_identifiers = cls._request_identifiers(text)
        resolved_topic = ""
        if task_continuation:
            resolved_topic = cls._text(task.get("topic") or frame.get("topic") or dialogue.get("canonical_topic"))
        elif reference and quoted_entity:
            resolved_topic = quoted_entity
        elif current_identifiers:
            resolved_topic = current_identifiers[0]
        elif semantic_continuation and previous_user:
            # Keep a real semantic subject from the latest conversational pair;
            # never inherit a generic task label such as "вопрос".
            candidates = [
                frame.get("topic"),
                dialogue.get("canonical_topic"),
                dialogue.get("active_topic"),
            ]
            resolved_topic = cls._safe_topic(candidates, previous_user)
        else:
            resolved_topic = cls._excerpt(re.split(r"(?<=[.!?。！？])\s+", cls._text(text))[0] if cls._text(text) else "", 140)

        if resolved_entity and not resolved_topic:
            resolved_topic = resolved_entity

        context_dependency = (
            "task_continuation" if task_continuation
            else "dialogue_reference" if reference
            else "dialogue_continuation" if semantic_continuation
            else "new_topic"
            if previous_pair_present else "independent"
        )

        if task_continuation:
            resolved_request = (
                "Continue the active task using the current user turn.\n"
                f"Task topic: {resolved_topic}\n"
                f"Current user turn: {cls._text(text)}\n"
                f"Previous user turn: {previous_user}\n"
                f"Previous April turn: {previous_april}"
            )
        elif semantic_continuation or reference:
            resolved_request = (
                "Continue the current conversational thread using only the supplied recent context.\n"
                f"Previous user turn: {previous_user}\n"
                f"Previous April turn: {previous_april}\n"
                f"Resolved reference: {resolved_entity or resolved_topic}\n"
                f"Current user instruction: {cls._text(text)}"
            )
        else:
            resolved_request = cls._text(text)

        return {
            "authenticated_scope": authenticated_scope,
            "conversation_continuation": conversation_continuation,
            "topic_relation": topic_relation,
            "semantic_continuation": semantic_continuation,
            "task_continuation": task_continuation,
            "reference": reference,
            "reference_signals": refs,
            "sequence_id": sequence_id,
            "previous_user_turn": previous_user,
            "previous_april_turn": previous_april,
            "previous_user_similarity": round(previous_user_similarity, 4),
            "previous_april_similarity": round(previous_april_similarity, 4),
            "task_similarity": round(task_similarity, 4),
            "recent_task_similarity": round(recent_task_similarity, 4),
            "active_entity": resolved_entity,
            "topic": resolved_topic,
            "context_dependency": context_dependency,
            "resolved_request": resolved_request,
            "active_task_context": cls._task_digest(task) if task_continuation else {},
            "parked_task_context": cls._task_digest(task) if raw_task_active and not task_continuation else {},
            "reasoning": {
                "identity_continuity": "authenticated_sequence + previous_turn",
                "task_ownership": "current_turn_fit_required",
                "topic_change": "allowed_inside_same_authenticated_sequence",
                "reference_resolution": "recent_user_assistant_pair",
                "history_role": "semantic_evidence",
            },
        }

    def build(
        self,
        *,
        text: str,
        semantic_result: dict[str, Any],
        state: dict[str, Any],
        history: list[Any],
    ) -> dict[str, Any]:
        semantic_result = semantic_result if isinstance(semantic_result, dict) else {}
        state = state if isinstance(state, dict) else {}
        history = history if isinstance(history, list) else []
        dialogue = semantic_result.get("dialogue_contract") if isinstance(semantic_result.get("dialogue_contract"), dict) else {}
        frame = semantic_result.get("semantic_frame") if isinstance(semantic_result.get("semantic_frame"), dict) else {}
        control = semantic_result.get("interpretation_control") if isinstance(semantic_result.get("interpretation_control"), dict) else {}
        relation = self._text(dialogue.get("relation") or semantic_result.get("three_way_relation") or "NEW").upper()
        memory_slider = semantic_result.get("dialogue_history_search", {}).get("memory_slider") if isinstance(semantic_result.get("dialogue_history_search"), dict) else {}
        memory_slider = memory_slider if isinstance(memory_slider, dict) else {}
        slider_operand = memory_slider.get("selected_memory_operand") if isinstance(memory_slider.get("selected_memory_operand"), dict) else {}
        slider_enabled = bool(
            memory_slider.get("enabled")
            and slider_operand
            and relation in {"CONTINUE", "RECALL"}
        )
        representation = self._text(frame.get("representation") or control.get("representation") or semantic_result.get("subtype") or "text").lower()
        directives = self._request_directives(text)
        operation = self._safe_operation(frame.get("operation") or control.get("operation"), representation, directives)
        goal = self._safe_goal(frame.get("goal") or dialogue.get("active_goal"), operation, representation, text)
        raw_task = semantic_result.get("interactive_task_state") if isinstance(semantic_result.get("interactive_task_state"), dict) else dialogue.get("active_task") if isinstance(dialogue.get("active_task"), dict) else {}
        continuation_bridge = self._build_continuation_bridge(
            text=text, dialogue=dialogue, frame=frame, task=raw_task, state=state,
        )
        continuation = bool(continuation_bridge.get("semantic_continuation"))
        reference = bool(continuation_bridge.get("reference"))
        task_active = bool(continuation_bridge.get("task_continuation"))
        active_entity = self._text(continuation_bridge.get("active_entity"))
        artifact_reference = self._explicit_artifact_dependency(text, control, semantic_result)
        topic = self._safe_topic(
            [continuation_bridge.get("topic"),
             active_entity,
             dialogue.get("canonical_topic") if task_active else "",
             frame.get("topic") if task_active else "",
             "Algorithm Engine" if "algorithm engine" in self._text(text).lower() else "",
             "Interpretation Layer" if "interpretation layer" in self._text(text).lower() else ""],
            text,
        )
        bridge_topic = self._text(continuation_bridge.get("topic"))
        if bridge_topic and bridge_topic.lower() not in {
            "вопрос", "ответ", "запрос", "тема", "опрос", "question", "request", "answer"
        }:
            topic = bridge_topic
        if slider_enabled:
            slider_topic = self._text(slider_operand.get("topic"))
            if slider_topic and (relation == "RECALL" or topic.lower() in {"", "text", "вопрос", "ответ", "тема"}):
                topic = slider_topic
        relation = self._text(continuation_bridge.get("topic_relation") or relation).upper()
        if slider_enabled:
            # A selected semantic memory operand keeps the original relation alive
            # even if the legacy bridge could not infer it from the short turn.
            relation = "RECALL" if relation == "RECALL" else "CONTINUE"

        signals = self._instruction_signals(text)
        output_modes = list(semantic_result.get("requested_outputs") or semantic_result.get("candidate_representations") or [])
        if representation and representation != "text" and representation not in output_modes:
            output_modes.append(representation)

        base_intent = self._text(frame.get("intent") or "")
        if base_intent not in DIALOGUE_LABELS:
            base_intent = "request" if directives or representation != "text" else (relation.lower() or "request")
        if base_intent in {"independent", "statement"} and (directives or representation != "text"):
            base_intent = "request"

        canonical_frame = {
            "intent": base_intent,
            "relation": relation,
            "topic": topic,
            "entity": active_entity,
            "operation": operation,
            "goal": goal,
            "representation": representation,
            "reference": bool(reference or artifact_reference),
            "task_active": bool(task_active),
            "sequence_id": self._text(
                dialogue.get("sequence_id")
                or (state.get("active_dialogue_sequence", {}) or {}).get("sequence_id")
                if isinstance(state.get("active_dialogue_sequence"), dict) else ""
            ),
        }

        output_contract = {
            "representation": representation,
            "operation": operation,
            "goal": goal,
            "requested_outputs": output_modes[:6],
            "render_authorized": bool(control.get("render_authorized")),
            "render_mode": self._text(control.get("render_mode") or "TEXT_ONLY"),
            "artifact_reference": artifact_reference,
        }

        required: list[dict[str, Any]] = []
        optional: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        protected: list[str] = []

        def add(bucket: list[dict[str, Any]], key: str, value: Any, score: float, reason: str, protected_flag: bool = False) -> None:
            compact = self._compact_value(value, depth=0, max_depth=4, max_items=8, max_keys=12)
            if compact in (None, "", [], {}):
                return
            entry = {
                "key": key,
                "value": compact,
                "priority": round(max(0.0, min(1.0, float(score))), 4),
                "reason": reason,
                "protected": bool(protected_flag),
            }
            bucket.append(entry)
            if protected_flag and key not in protected:
                protected.append(key)

        # These four elements define the current computational task and survive
        # all budget optimization unless the request itself is pathologically larger
        # than the hard provider envelope.
        add(required, "CURRENT_REQUEST", self._excerpt(text, 1600), 1.0, "current_user_turn", True)
        add(required, "SEMANTIC_FRAME", canonical_frame, 0.99, "workspace_normalized_semantics", True)
        add(required, "OUTPUT_CONTRACT", output_contract, 1.0, "render_and_response_shape", True)
        if directives:
            add(required, "REQUEST_DIRECTIVES", directives[:8], 0.98, "explicit_user_constraints", True)
        identifiers = self._request_identifiers(text)
        if identifiers and (representation == "code" or signals.get("architecture") or signals.get("code")):
            add(required, "REQUEST_IDENTIFIERS", identifiers[:12], 0.96, "named_contract_entities", True)
        if task_active:
            add(required, "ACTIVE_TASK", self._task_digest(raw_task), 0.97, "active_task_owner", True)

        obligations = merge_dialogue_obligations(
            state.get("dialogue_obligations"),
            raw_task.get("obligations") if isinstance(raw_task, dict) else [],
        )
        if obligations:
            relevant = [
                item for item in obligations
                if item.get("status") not in {"fulfilled", "cancelled"}
            ][-6:]
            if relevant:
                add(required if task_active else optional, "ACTIVE_OBLIGATIONS", relevant, 0.965, "explicit_future_commitment", task_active)

        if continuation or reference or task_active:
            add(required if (continuation or reference) else optional, "DIALOGUE_ANCHOR", {
                # Keep the actual USER↔APRIL antecedent first so even a hard
                # protected compaction preserves the pair that resolves pronouns.
                "previous_user_turn": continuation_bridge.get("previous_user_turn"),
                "previous_april_turn": continuation_bridge.get("previous_april_turn"),
                "resolved_reference": active_entity or topic,
                "active_entity": active_entity,
                "canonical_topic": topic,
                "relation": relation,
                "sequence_id": continuation_bridge.get("sequence_id"),
            }, 0.99 if (continuation or reference) else 0.92, "continuation_anchor", bool(continuation or reference))

        if continuation or reference:
            seq = dialogue.get("active_dialogue_sequence") or state.get("active_dialogue_sequence")
            if isinstance(seq, dict) and seq:
                add(optional, "ACTIVE_SEQUENCE", {
                    "sequence_id": seq.get("sequence_id"),
                    "turn_count": seq.get("turn_count") or seq.get("turns_count"),
                    "last_user_request": seq.get("last_user_request"),
                    "last_april_answer": seq.get("last_april_answer"),
                }, 0.9, "same_authenticated_sequence")

        if task_active:
            task_memory = semantic_result.get("task_memory") if isinstance(semantic_result.get("task_memory"), dict) else dialogue.get("task_memory")
            if isinstance(task_memory, dict):
                add(optional, "TASK_MEMORY", self._task_digest(task_memory), 0.88, "active_task_evidence")

        if artifact_reference:
            visual = semantic_result.get("target_artifact") if isinstance(semantic_result.get("target_artifact"), dict) else {}
            if not visual:
                visual = state.get("selected_artifact") if isinstance(state.get("selected_artifact"), dict) else {}
            if visual:
                add(optional, "ACTIVE_ARTIFACT", {
                    "type": visual.get("type") or visual.get("artifact_type"),
                    "id": visual.get("block_id") or visual.get("render_id") or visual.get("id"),
                    "title": visual.get("title"),
                }, 0.96, "explicit_artifact_dependency")

        # Rank memory semantically instead of blindly taking the newest records.
        memory_items = self._memory_candidates(state, history)
        memory_ranked: list[dict[str, Any]] = []
        for item in memory_items:
            text_value = item["text"]
            lexical = self._similarity(text, text_value)
            topic_match = self._similarity(dialogue.get("canonical_topic") or frame.get("topic"), text_value)
            entity_match = self._similarity(active_entity, text_value) if active_entity else 0.0
            sequence_match = 1.0 if dialogue.get("sequence_id") and item.get("sequence_id") == dialogue.get("sequence_id") else 0.0
            score = (0.46 * lexical) + (0.24 * topic_match) + (0.16 * entity_match) + (0.14 * sequence_match)
            if continuation and sequence_match:
                score += 0.18
            if reference and (topic_match > 0 or entity_match > 0):
                score += 0.12
            if artifact_reference and item.get("scene_id") and dialogue.get("scene_id") == item.get("scene_id"):
                score += 0.15
            memory_ranked.append((min(1.0, score), text_value, item))
        memory_ranked.sort(key=lambda x: x[0], reverse=True)

        selected_memory = []
        for score, text_value, item in memory_ranked[:4]:
            if score < 0.16:
                continue
            selected_memory.append({
                "text": self._excerpt(text_value, 320),
                "sequence_id": item.get("sequence_id"),
                "scene_id": item.get("scene_id"),
                "score": round(score, 4),
            })
        if slider_enabled:
            slider_memory = {
                "text": self._excerpt(
                    " ".join(
                        x for x in (
                            slider_operand.get("user_request"),
                            slider_operand.get("april_answer"),
                            slider_operand.get("summary"),
                        ) if x
                    ),
                    700,
                ),
                "sequence_id": slider_operand.get("sequence_id"),
                "scene_id": slider_operand.get("scene_id"),
                "memory_index": slider_operand.get("memory_index", -1),
                "topic": slider_operand.get("topic"),
                "entity": slider_operand.get("entity"),
                "focus": slider_operand.get("focus"),
                "direction": slider_operand.get("direction"),
                "score": slider_operand.get("score", 0.0),
                "source": "dialogue_memory_slider",
            }
            add(required, "CONTINUATION_MEMORY_OPERAND", {
                **slider_memory,
                "previous_user_turn": slider_operand.get("user_request"),
                "previous_april_turn": slider_operand.get("april_answer"),
                "goal": slider_operand.get("goal"),
                "dialogue_obligations": slider_operand.get("dialogue_obligations"),
                "semantic_relation": slider_operand.get("semantic_relation"),
                "instruction": "Resolve the current user request against this selected historical dialogue operand; current request remains authoritative.",
            }, 0.998, "sequential_semantic_memory_slider", True)
            selected_memory = [slider_memory] + [
                item for item in selected_memory
                if isinstance(item, dict)
                and not (
                    item.get("sequence_id") == slider_memory.get("sequence_id")
                    and item.get("scene_id") == slider_memory.get("scene_id")
                )
            ]
        elif selected_memory:
            add(optional, "RELEVANT_MEMORY", selected_memory, 0.76 if continuation or reference else 0.48, "semantic_memory_selection")

        # Visual state is explicitly excluded unless the current task depends on
        # a prior artifact. This prevents old graph/image state from contaminating
        # unrelated text/code/architecture requests.
        if not artifact_reference:
            live_visual = state.get("active_visual_scene") or state.get("current_visual_scene")
            if isinstance(live_visual, dict) and live_visual.get("scene_id"):
                excluded.append({
                    "key": "STALE_VISUAL_STATE",
                    "reason": "no_current_artifact_dependency",
                    "scene_id": live_visual.get("scene_id"),
                })

        if continuation_bridge.get("parked_task_context"):
            excluded.append({
                "key": "STALE_ACTIVE_TASK",
                "reason": "current_turn_not_owned_by_persisted_task",
                "task": continuation_bridge.get("parked_task_context"),
            })

        # A replaced task explicitly forbids the previous entity/task from becoming
        # an implicit provider dependency.
        transition = semantic_result.get("task_transition") if isinstance(semantic_result.get("task_transition"), dict) else dialogue.get("task_transition") if isinstance(dialogue.get("task_transition"), dict) else {}
        if transition.get("replace_task"):
            excluded.append({
                "key": "PREVIOUS_TASK",
                "reason": "task_replaced",
                "forbidden_entities": list(semantic_result.get("forbidden_entities") or []),
            })

        # Current request instruction signals are part of the reasoning basis,
        # never a routing trigger.
        confidence_components = [
            1.0,
            float(bool(frame)),
            float(bool(output_contract["requested_outputs"] or representation == "text")),
            float(1.0 if task_active else 0.75 if continuation or reference else 0.60),
        ]
        confidence = sum(confidence_components) / len(confidence_components)

        # Provider sections are already ordered by semantic priority. The provider
        # packer only performs size fitting; it does not decide relevance.
        provider_sections: list[dict[str, Any]] = []
        for entry in required + sorted(optional, key=lambda x: x.get("priority", 0.0), reverse=True):
            provider_sections.append({
                "name": entry["key"],
                "value": entry["value"],
                "priority": entry["priority"],
                "protected": entry["protected"],
                "reason": entry["reason"],
            })

        return {
            "version": self.VERSION,
            "mode": "semantic_pre_provider_workspace",
            "current_request": self._text(text),
            "current_request_raw": self._text(text),
            "current_request_excerpt": self._excerpt(text, 1200),
            "current_request_raw_preserved": True,
            "active_task": bool(task_active),
            "task_continuation": bool(continuation_bridge.get("task_continuation")),
            "conversation_continuation": bool(continuation_bridge.get("conversation_continuation")),
            "semantic_continuation": bool(continuation_bridge.get("semantic_continuation")),
            "relation": relation,
            "continuation": continuation,
            "reference": reference,
            "artifact_reference": artifact_reference,
            "sequence_id": continuation_bridge.get("sequence_id"),
            "authenticated_scope": continuation_bridge.get("authenticated_scope") or {},
            "previous_user_turn": continuation_bridge.get("previous_user_turn"),
            "previous_april_turn": continuation_bridge.get("previous_april_turn"),
            "continuation_bridge": continuation_bridge,
            "resolved_request": continuation_bridge.get("resolved_request") or self._text(text),
            "active_topic": topic,
            "active_entity": active_entity,
            "operation": operation,
            "goal": goal,
            "representation": representation,
            "semantic_frame": canonical_frame,
            "instruction_signals": signals,
            "request_directives": directives,
            "request_identifiers": self._request_identifiers(text),
            "required_context": required,
            "optional_context": sorted(optional, key=lambda x: x.get("priority", 0.0), reverse=True),
            "protected_context": protected,
            "excluded_context": excluded,
            "selected_memory": selected_memory,
            "memory_slider": memory_slider if isinstance(memory_slider, dict) else {},
            "selected_memory_index": memory_slider.get("selected_memory_index", -1) if slider_enabled else -1,
            "selected_memory_record": deepcopy(memory_slider.get("selected_memory_record") or {}) if slider_enabled else {},
            "selected_memory_operand": deepcopy(slider_operand) if slider_enabled else {},
            "historical_memory_allowed": bool(slider_enabled or reference),
            "context_dependency": continuation_bridge.get("context_dependency") or ("continuation" if slider_enabled and relation == "CONTINUE" else "recall" if slider_enabled else "independent"),
            "task_relation": {
                "owned": bool(continuation_bridge.get("task_continuation")),
                "current_turn_fit": bool(continuation_bridge.get("task_continuation")),
                "task_similarity": continuation_bridge.get("task_similarity", 0.0),
                "recent_task_similarity": continuation_bridge.get("recent_task_similarity", 0.0),
            },
            "continuation_content_analysis": {
                "version": "dialog_cognitive_continuation_v1",
                "active": bool(continuation or reference),
                "mode": "REFERENCE" if reference else "CONTINUE" if continuation else "NONE",
                "conversation_continuation": bool(continuation_bridge.get("conversation_continuation")),
                "semantic_continuation": bool(continuation_bridge.get("semantic_continuation")),
                "task_continuation": bool(continuation_bridge.get("task_continuation")),
                "previous_user_turn": continuation_bridge.get("previous_user_turn"),
                "previous_answer": continuation_bridge.get("previous_april_turn"),
                "active_entity": active_entity,
                "next_direction": "answer_current_request_using_resolved_context" if (continuation or reference) else "start_current_turn",
            },
            "context_dependencies": [
                x for x in (
                    "current_request",
                    "output_contract",
                    "semantic_frame",
                    "active_task" if task_active else "",
                    "dialogue_anchor" if continuation or reference or task_active else "",
                    "continuation_memory_operand" if slider_enabled else "",
                    "active_artifact" if artifact_reference else "",
                ) if x
            ],
            "requested_outputs": output_modes[:6],
            "output_contract": output_contract,
            "provider_sections": provider_sections,
            "reasoning_basis": {
                "selection": "dependency + semantic similarity + authenticated sequence continuity + task ownership + recency + entity continuity",
                "decision_order": "authenticate -> detect conversation continuity -> separate topic/task ownership -> resolve references -> rank context -> protect mandatory -> budget pack",
                "budget_policy": "relevance_before_budget",
                "provider_role": "consume_selected_context; do_not_reinterpret_or_reselect",
                "stale_visual_state": "excluded_without_artifact_dependency",
                "historical_memory": "selected_slider_operand_only" if slider_enabled else "evidence_only",
                "current_request_policy": "preserve_semantically; compact only when provider envelope requires it",
                "memory_slider": "scan chronologically; compare each candidate with the same interpretation engine; stop on the strongest related operand",
                "output_contract_policy": "protected",
            },
            "confidence": round(min(1.0, confidence), 4),
        }


DIALOG_COGNITIVE_WORKSPACE = DialogCognitiveWorkspace()

def build_result(text: str) -> dict[str, Any]:
    return {
        "type": "text",
        "subtype": None,
        "scene_type": None,
        "normalized": text,
        "content_role": None,
        "contains_object": bool(text),
        "contains_explanation": False,
        "contains_analysis": False,
        "contains_legend": False,
        "scene_composition_ready": True,
        "renderer_intent": False,
        "discussion_mode": False,
        "space_discussion": False,
        "lightweight_visual": False,
        "exploration": False,
        "continuation": False,
        "web_context": False,
        "explicit_image_generation": False,
        "cognition_assisted": True,
        "continuity_aware": True,
        "scene_aware": True,
        "supports_executor": True,
        "prefer_renderer": False,
        "prefer_guidance": False,
        "prefer_execution": False,
        "prefer_continuation": False,
        "active_topic_slot": None,
        "topic_continuity": False,
        "avoid_force_generation": True,
        "avoid_hidden_escalation": True,
        "avoid_telegram_behavior": True,
        "avoid_trigger_execution": True,
        "provider_safe": True,
        "renderer_first": False,
        "machine_only": True,
        "semantic_bridge": True,
        "orchestration_safe": True,
        "continuity_preserved": True,
        "required_domains": [],
        "candidate_domains": [],
        "required_representations": [],
        "candidate_representations": [],
        "domain_confidence": {},
        "response_complexity": None,
        "estimated_action_count": 0,
        "decision_owner": DECISION_OWNER,
        "routing_owner": DECISION_OWNER,
        "renderer_owner": DECISION_OWNER,
        "provider_calls": 0,
        "single_route": True,
    }


def estimate_action_count(result: dict[str, Any]) -> int:
    reps = set(result.get("required_representations", []) or [])
    domains = set(result.get("required_domains", []) or [])
    count = len(reps) + len(domains)
    count += int(bool(result.get("contains_analysis") or result.get("contains_explanation")))
    count += 2 if result.get("explicit_image_generation") else 0
    return max(1, count)


def determine_response_complexity(result: dict[str, Any]) -> str:
    actions = estimate_action_count(result)
    if actions <= 1:
        return RESPONSE_COMPLEXITY_LOW
    if actions <= 3:
        return RESPONSE_COMPLEXITY_MEDIUM
    return RESPONSE_COMPLEXITY_HIGH


def build_factory_order(result: dict[str, Any]) -> dict[str, Any]:
    domains = list(result.get("required_domains", []) or [])
    return {
        "intent": result.get("type"),
        "goal": result.get("subtype"),
        "required_domains": domains,
        "required_rooms": list(domains),
        "required_artifacts": list(result.get("required_representations", []) or []),
        "quality_target": 0.95,
        "owner": DECISION_OWNER,
        "status": "evidence_only",
    }


def build_scene_strategy(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_strategy": "evidence_only",
        "preferred_blocks": list(result.get("required_representations", []) or []),
        "content_role": result.get("content_role"),
        "scene_priority": "normal",
        "scene_contribution_mode": True,
        "scene_builder_profile": "processor_selected",
        "decision_owner": DECISION_OWNER,
    }


def build_interpretation_state() -> dict[str, dict[str, Any]]:
    return {
        "dialogue": {},
        "evidence": {},
        "cognition": {},
        "scene": {},
        "artifacts": {},
        "executor": {},
        "diagnostics": {},
    }


INTERPRETATION_TRANSPORT_FIELDS = {
    "dialogue_profile": ("dialogue", "profile"),
    "semantic_evidence_engine": ("evidence", "engine"),
    "dialogue_cognition_matrix": ("cognition", "matrix"),
    "semantic_dialogue_graph": ("dialogue", "graph"),
    "scene_profile": ("scene", "profile"),
    "artifact_contract": ("artifacts", "contract"),
    "executor_preparation_contract": ("executor", "contract"),
}
INTERPRETATION_ROUTE = tuple(INTERPRETATION_TRANSPORT_FIELDS)
INTERPRETATION_ENTRYPOINT = TRANSPORT_NAME
INTERPRETATION_STATE_TEMPLATE = build_interpretation_state()


def safe_result_get(result: Any, key: str, default: Any = None) -> Any:
    if not isinstance(result, dict):
        return default
    value = result.get(key, default)
    return default if value is None else value


def ensure_transport_defaults(state: dict[str, Any] | None) -> dict[str, Any]:
    state = state or {}
    for key in ("dialogue", "scene", "executor", "artifacts", "diagnostics"):
        state.setdefault(key, {})
    return state


def synchronize_interpretation_context(
    state: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    state["dialogue"]["profile"] = result.get("semantic_profile")
    state["dialogue"]["contract"] = result.get("dialogue_contract")
    state["evidence"]["engine"] = result.get("quantum_interpretation_field")
    state["scene"]["profile"] = result.get("scene_profile")
    state["scene"]["matrix"] = result.get("quantum_matrix")
    state["artifacts"]["contract"] = result.get("artifact_contract")
    state["executor"]["contract"] = result.get("executor_preparation_contract")
    return state


def export_transport_state(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    for field, (section, key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state[section][key] = result[field]
    state["diagnostics"]["route"] = [
        {"node": node, "status": "evidence", "payload": result.get(node)}
        for node in INTERPRETATION_ROUTE
    ]
    return state


def resolve_interpretation_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result.get(TRANSPORT_NAME, {}) if isinstance(result, dict) else {}


def propagate_canonical_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    transport = state.setdefault("transport", {})
    response = transport.setdefault("response", {})
    response["content"] = (
        safe_result_get(result, "assistant_response")
        or safe_result_get(result, "answer")
        or safe_result_get(result, "response")
        or safe_result_get(result, "content")
        or ""
    )
    return result


def bridge_machine_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    machine = state.setdefault("machine_response", {})
    scene = state.setdefault("scene_contract", {})
    content = (
        machine.get("content")
        or result.get("assistant_response")
        or result.get("answer")
        or result.get("response")
        or result.get("content")
        or ""
    )
    machine["content"] = content
    scene.update({"content": content, "answer": content, "summary": content})
    result["machine_response"] = machine
    result["scene_contract"] = scene
    return result


def validate_response_complexity(result: dict[str, Any]) -> dict[str, Any]:
    complexity = result.get("response_complexity") or RESPONSE_COMPLEXITY_LOW
    result["response_complexity"] = complexity
    result["estimated_action_count"] = result.get("estimated_action_count") or 0
    result["semantic_response_complexity"] = complexity
    result["machine_response_complexity"] = complexity
    return result


def export_response_complexity(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result.get(key)
        for key in (
            "response_complexity",
            "estimated_action_count",
            "semantic_response_complexity",
            "machine_response_complexity",
        )
    }


def build_transport_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "has_transport": bool(result.get(TRANSPORT_NAME)),
        "has_machine_response": bool(result.get("machine_response")),
        "has_scene_contract": bool(result.get("scene_contract")),
        "normalized": bool(result.get("normalized")),
        "decision_owner": result.get("decision_owner"),
        "provider_calls": result.get("provider_calls", 0),
    }


def build_interpretation_route(state: dict[str, Any], result: dict[str, Any]):
    state = export_transport_state(state, result)
    return state["diagnostics"]["route"]


# ---------------------------------------------------------------------------
# Compatibility helpers: all point into the one engine.
# ---------------------------------------------------------------------------

QUANTUM_INTERPRETATION_ENGINE = QuantumInterpretationEngine()

# Compatibility singleton names intentionally reference the same engine object.
QUANTUM_FAST_SEMANTIC = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_LINGUISTIC_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EMBEDDING_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_INTENT_ENGINE = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_EVIDENCE_FUSION = QUANTUM_INTERPRETATION_ENGINE
QUANTUM_DIALOGUE_ENGINE = QUANTUM_INTERPRETATION_ENGINE

# Public class aliases preserve import names without reinstating parallel engines.
QuantumFastSemanticEngine = QuantumInterpretationEngine
QuantumLinguisticEngine = QuantumInterpretationEngine
QuantumEmbeddingEngine = QuantumInterpretationEngine
QuantumIntentEngine = QuantumInterpretationEngine
QuantumEvidenceFusionEngine = QuantumInterpretationEngine
QuantumDialogueEngine = QuantumInterpretationEngine
QuantumSceneInterpretationMatrix = QuantumInterpretationEngine


def normalize_text(text: Any) -> str:
    return QUANTUM_INTERPRETATION_ENGINE.normalize(text)


def normalize_lower(text: Any) -> str:
    return normalize_text(text).lower()


def contains_any(text: str, words: Sequence[str]) -> bool:
    tokens = set(QUANTUM_INTERPRETATION_ENGINE._tokens(normalize_text(text)))
    return bool(tokens & {normalize_lower(x) for x in words})


def _semantic_evidence_stub(kind: str, text: str) -> bool:
    return contains_any(text, (kind,))


def detect_domain_candidates(text: str):
    return [
        x["domain"] for x in QUANTUM_INTERPRETATION_ENGINE.domains(text)["measurements"]
        if float(x["score"]) >= 0.45
    ]


def build_domain_confidence(text: str):
    return {
        x["domain"]: round(float(x["score"]), 4)
        for x in QUANTUM_INTERPRETATION_ENGINE.domains(text)["measurements"]
        if float(x["score"]) >= 0.20
    }


def _capability_scores(text: str) -> dict[str, float]:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)["capability_scores"]


def measure_representation_evidence(text: str) -> list[dict[str, Any]]:
    return [
        SemanticEvidence(x["type"], float(x["score"]), "quantum_matrix").as_dict()
        for x in QUANTUM_INTERPRETATION_ENGINE.representations(text)["measurements"]
    ]


def detect_representation_candidates(text: str):
    return [
        x["label"] for x in measure_representation_evidence(text)
        if float(x["score"]) >= 0.45
    ]


def semantic_evidence_math(text: str) -> float:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"].get("formula", 0.0)


def semantic_evidence_renderer(text: str) -> float:
    return max(
        QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"].values(),
        default=0.0,
    )


def semantic_evidence_image(text: str) -> float:
    return QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"].get("image", 0.0)


def semantic_evidence_exploration(text: str) -> float:
    return _capability_scores(text).get("exploration", 0.0)


def semantic_evidence_continuation(text: str, previous_assistant: str = "") -> float:
    return QUANTUM_INTERPRETATION_ENGINE.dialogue(
        text, previous_assistant=previous_assistant
    )["dialogue"]["continuation_score"]


def semantic_evidence_web(text: str) -> float:
    return _capability_scores(text).get("web", 0.0)


def semantic_evidence_code(text: str) -> float:
    return _capability_scores(text).get("code", 0.0)


def semantic_evidence_information(text: str) -> float:
    return _capability_scores(text).get("information", 0.0)


def detect_discussion_mode(text: str) -> float:
    return _capability_scores(text).get("discussion", 0.0)


def detect_space_discussion(text: str) -> float:
    return _capability_scores(text).get("space", 0.0)


def detect_lightweight_visual(text: str) -> float:
    scores = QUANTUM_INTERPRETATION_ENGINE.measure(text)["representation_scores"]
    return max(scores.get("image", 0.0), scores.get("diagram", 0.0), scores.get("graph", 0.0))


def detect_scene_type(text: str, cognition=None):
    cognition = cognition if isinstance(cognition, dict) else {}
    required = [str(x).lower() for x in cognition.get("required_representations", ()) or ()]
    return required[0] if required else QUANTUM_INTERPRETATION_ENGINE.measure(text)["scene_matrix"]["best_scene"]


def _is_micro_social_turn(text: Any) -> bool:
    p = QUANTUM_INTERPRETATION_ENGINE.measure(normalize_text(text))
    return bool(p["fast_social"] and len(normalize_text(text).split()) <= 24)


def _semantic_identity_request(text: Any) -> bool:
    return bool(QUANTUM_INTERPRETATION_ENGINE.measure(normalize_text(text))["identity_request"])


def _dialogue_signal_contract(
    text: str, history: list, state: dict, semantic: dict, cognition: dict | None = None,
    precomputed_profile: dict[str, Any] | None = None,
):
    cognition = cognition if isinstance(cognition, dict) else {}
    state = state if isinstance(state, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    previous_assistant, previous_user, reply_to = QUANTUM_INTERPRETATION_ENGINE._history(history)
    active_goal = normalize_text(
        state.get("active_goal") or state.get("current_goal")
        or semantic.get("active_goal") or cognition.get("active_goal")
    )
    active_topic = normalize_text(
        state.get("active_topic") or state.get("current_topic")
        or semantic.get("current_topic") or cognition.get("active_topic")
    )
    measured = QUANTUM_INTERPRETATION_ENGINE.dialogue(
        text, previous_assistant=previous_assistant, previous_user=previous_user,
        active_goal=active_goal, active_topic=active_topic,
    )
    d = measured["dialogue"]
    continuation = bool(
        previous_assistant and (
            d["label"] in {"continuation", "reformulation", "correction", "reference", "affirmation", "rejection"}
            or d["continuation_score"] >= 0.72
        )
    )
    return {
        "dialog_act": d["label"],
        "current_request": text,
        "continuation": continuation,
        "reference_to_previous": bool(previous_assistant and d["reference_score"] >= 0.60),
        "previous_april_turn": previous_assistant,
        "previous_user_turn": previous_user,
        "reply_to": reply_to,
        "active_goal": active_goal,
        "active_topic": active_topic,
        "topic_score": d["topic_score"],
        "goal_score": d["goal_score"],
        "continuation_score": d["continuation_score"],
        "reference_score": d["reference_score"],
        "topic_shift": bool(active_topic and not continuation and d["topic_score"] < 0.35),
        "history_available": bool(history),
        "turn_count": len(history),
        "semantic_measurement": measured,
        "confidence": d["confidence"],
        "decision_owner": DECISION_OWNER,
        "evidence_only": True,
        "canonical": True,
    }


def _semantic_context_packet(
    text: str, history: list, state: dict, semantic: dict, cognition: dict
) -> dict[str, Any]:
    result = QUANTUM_INTERPRETATION_ENGINE.interpret(
        text, cognition=cognition, semantic=semantic, history=history, state=state
    )
    return result.get("quantum_interpretation_field", {})


def _base_interpret_request(
    text, cognition=None, semantic=None, history=None, state=None
):
    return interpret_request(text, cognition, semantic, history, state)


# ---------------------------------------------------------------------------
# Canonical interpretation entrypoint
# ---------------------------------------------------------------------------

def interpret_request(
    text, cognition=None, semantic=None, history=None, state=None
):
    return QUANTUM_INTERPRETATION_ENGINE.interpret(
        text,
        cognition=cognition,
        semantic=semantic,
        history=history,
        state=state,
    )


# ---------------------------------------------------------------------------
# Compatibility builders retained as thin views, not separate engines.
# ---------------------------------------------------------------------------

def build_semantic_dialog_profile(
    text, cognition=None, semantic=None, assistant_response=None,
    dialogue_history=None, vision_context=None
):
    cognition = cognition or {}
    semantic = semantic or {}
    return {
        "input_text": text,
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "vision_context": vision_context or {},
        "active_goal": cognition.get("active_goal") or semantic.get("active_goal"),
        "active_topic": cognition.get("active_topic_slot") or semantic.get("current_topic"),
        "semantic_state": semantic,
        "requires_scene_builder": False,
        "profile_version": "quantum_matrix_v1",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "quantum_matrix",
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v1",
    }


def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {
        "contract": "scene_artifact",
        "transport": TRANSPORT_NAME,
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "representation": "processor_decides",
        "profile_version": "quantum_matrix_v1",
    }


def build_unified_scene_context(
    semantic_profile, scene_profile, artifact_contract,
    voice_context=None, vision_context=None, gallery_context=None, file_context=None,
    assistant_response=None, dialogue_history=None, memory_state=None
):
    return {
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "artifact_contract": artifact_contract or {},
        "voice_context": voice_context or {},
        "vision_context": vision_context or {},
        "gallery_context": gallery_context or {},
        "file_context": file_context or {},
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "active_goal": (semantic_profile or {}).get("active_goal"),
        "active_scene": (scene_profile or {}).get("scene_type", "dialogue"),
        "memory_state": memory_state or {},
        "continuity_state": {
            "single_route": True,
            "transport": TRANSPORT_NAME,
            "scene_contract": "canonical",
        },
        "profile_version": "quantum_matrix_v1",
    }


def build_scene_execution_plan(
    semantic_profile, scene_profile, artifact_contract, unified_scene_context=None
):
    context = unified_scene_context or build_unified_scene_context(
        semantic_profile, scene_profile, artifact_contract
    )
    return {
        "transport": TRANSPORT_NAME,
        "scene_contract": "canonical",
        "scene_context": context,
        "scene_type": (scene_profile or {}).get("scene_type", "dialogue"),
        "representation": "processor_decides",
        "execution_mode": "single_quantum_matrix_pipeline",
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v1",
    }


def build_unified_interpretation_state(scene_context, processor_state=None):
    return {
        "transport": TRANSPORT_NAME,
        "scene_context": scene_context or {},
        "processor_state": processor_state or {},
        "dialogue_vector": (scene_context or {}).get("dialogue_history", []),
        "assistant_response": (scene_context or {}).get("assistant_response"),
        "voice_context": (scene_context or {}).get("voice_context", {}),
        "vision_context": (scene_context or {}).get("vision_context", {}),
        "gallery_context": (scene_context or {}).get("gallery_context", {}),
        "file_context": (scene_context or {}).get("file_context", {}),
        "active_goal": (scene_context or {}).get("active_goal"),
        "active_scene": (scene_context or {}).get("active_scene"),
        "executor_mode": "single_scene_contract",
        "profile_version": "quantum_matrix_v1",
    }


def build_semantic_processor_state(interpretation_state, execution_plan=None):
    state = interpretation_state or {}
    return {
        "transport": TRANSPORT_NAME,
        "processor_contract": "canonical",
        "interpretation_state": state,
        "execution_plan": execution_plan or {},
        "semantic_inputs": {
            "text": state.get("scene_context", {}).get("semantic_profile", {}).get("input_text"),
            "voice": state.get("voice_context", {}),
            "images": state.get("vision_context", {}),
            "gallery": state.get("gallery_context", {}),
            "files": state.get("file_context", {}),
            "assistant": state.get("assistant_response"),
            "history": state.get("dialogue_vector", []),
        },
        "scene_understanding": {
            "active_scene": state.get("active_scene"),
            "active_goal": state.get("active_goal"),
            "continuity": True,
            "single_route": True,
        },
        "profile_version": "quantum_matrix_v1",
    }


def build_dialogue_understanding_core(processor_state, executor_state=None):
    inputs = (processor_state or {}).get("semantic_inputs", {})
    return {
        "transport": TRANSPORT_NAME,
        "dialogue_understanding": {
            "user_text": inputs.get("text"),
            "voice": inputs.get("voice"),
            "images": inputs.get("images"),
            "gallery": inputs.get("gallery"),
            "files": inputs.get("files"),
            "assistant_response": inputs.get("assistant"),
            "dialogue_history": inputs.get("history", []),
            "scene_understanding": (processor_state or {}).get("scene_understanding", {}),
        },
        "processor_reasoning": {
            "single_scene": True,
            "history_aware": True,
            "response_context": True,
            "executor_shared_context": executor_state or {},
        },
        "profile_version": "quantum_matrix_v1",
    }


def optimize_dialogue_understanding(dialogue_core):
    return {
        "transport": TRANSPORT_NAME,
        "dialogue_understanding": (dialogue_core or {}).get("dialogue_understanding", {}),
        "optimization": {
            "semantic_priority": ["current_request", "active_goal", "dialogue_history", "multimodal_context"],
            "multi_evidence": True,
            "response_continuity": True,
            "scene_consistency": True,
            "executor_alignment": True,
        },
        "canonical_reasoning": {
            "single_scene": True, "single_contract": True, "single_transport": True,
            "preserve_dialogue_vector": True,
        },
        "profile_version": "quantum_matrix_v1",
    }


def build_semantic_interpretation_contract(dialogue_optimization):
    return {
        "transport": TRANSPORT_NAME,
        "semantic_contract": {
            "mode": "canonical_semantic",
            "single_scene": True,
            "single_dialogue": True,
            "single_processor": True,
            "single_executor": True,
        },
        "dialogue_optimization": dialogue_optimization or {},
        "reasoning_policy": {
            "current_request_authoritative": True,
            "multimodal_fusion": True,
            "multi_evidence": True,
            "trigger_independent": True,
            "scene_continuity": True,
        },
        "profile_version": "quantum_matrix_v1",
    }


def build_canonical_semantic_runtime(semantic_contract, processor_state, dialogue_core):
    dialogue = (dialogue_core or {}).get("dialogue_understanding", {})
    return {
        "transport": TRANSPORT_NAME,
        "scene": dialogue.get("scene_understanding", {}),
        "dialogue": dialogue,
        "processor": processor_state or {},
        "reasoning_policy": (semantic_contract or {}).get("reasoning_policy", {}),
        "continuity_vector": {
            "history": dialogue.get("dialogue_history", []),
            "assistant": dialogue.get("assistant_response"),
            "goal": dialogue.get("scene_understanding", {}).get("active_goal"),
        },
        "compatibility": {
            "enabled": False,
            "trigger_execution": False,
            "keyword_matching": False,
        },
        "profile_version": "quantum_matrix_v1",
    }


def fuse_semantic_inputs(runtime_state):
    runtime_state = runtime_state or {}
    inputs = dict(runtime_state.get("input_sources", {}))
    continuity = runtime_state.get("continuity_vector", {})
    return {
        "transport": TRANSPORT_NAME,
        "scene": runtime_state.get("scene", {}),
        "goal": continuity.get("goal"),
        "history": continuity.get("history", []),
        "assistant_response": continuity.get("assistant"),
        "modalities": {k: inputs.get(k) for k in ("text", "voice", "images", "gallery", "files")},
        "semantic_state": {
            "single_route": True,
            "multimodal_fusion": True,
            "legacy_trigger_enabled": False,
            "context_complete": True,
        },
        "available_modalities": [k for k, v in inputs.items() if v not in (None, {}, [], "")],
        "profile_version": "quantum_matrix_v1",
    }


def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {
        "transport": TRANSPORT_NAME,
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v1",
    }


SEMANTIC_EVIDENCE_PRIORITY = (
    "current_request", "active_goal", "dialogue_history",
    "voice_context", "vision_context", "gallery_context",
    "file_context", "semantic_profile",
)
LEGACY_TRIGGER_FLAGS = ()
CANONICAL_SEMANTIC_RUNTIME = {
    "transport": TRANSPORT_NAME,
    "reasoning": "quantum_matrix",
    "legacy_trigger_execution": False,
    "single_scene": True,
    "single_processor": True,
    "single_executor": True,
}
SEMANTIC_INTERPRETATION_CORE = {
    "decision_source": DECISION_OWNER,
    "routing": "processor_owned",
    "legacy_mode": "isolated",
    "scene_contract": "artifact_first",
    "executor_contract": "advisory_only",
    "history_model": "evidence_based",
    "confidence_policy": "multi_evidence",
}
SEMANTIC_PIPELINE = INTERPRETATION_ROUTE


# ---------------------------------------------------------------------------
# Shared semantic encoder compatibility
# ---------------------------------------------------------------------------

_SHARED_SEMANTIC_ENCODER = None
_SHARED_SEMANTIC_ENCODER_LOCK = threading.RLock()

def get_shared_semantic_encoder():
    """Return the optional shared SentenceTransformer instance.

    Heavy model loading remains opt-in. State Manager can safely link to this
    function without creating a second semantic runtime.
    """
    global _SHARED_SEMANTIC_ENCODER
    if _SHARED_SEMANTIC_ENCODER is not None:
        return _SHARED_SEMANTIC_ENCODER
    if SentenceTransformer is None or not APRIL_ENABLE_HEAVY_HOTPATH:
        return None
    with _SHARED_SEMANTIC_ENCODER_LOCK:
        if _SHARED_SEMANTIC_ENCODER is not None:
            return _SHARED_SEMANTIC_ENCODER
        try:
            _SHARED_SEMANTIC_ENCODER = SentenceTransformer(SEMANTIC_MODEL_NAME)
        except Exception as exc:
            _SHARED_SEMANTIC_ENCODER = None
            safe_semantic_log = globals().get("safe_patch_log")
            if callable(safe_semantic_log):
                safe_semantic_log(f"SHARED ENCODER UNAVAILABLE: {exc}")
    return _SHARED_SEMANTIC_ENCODER


# ---------------------------------------------------------------------------
# Deep-model API compatibility
# ---------------------------------------------------------------------------

def _runtime_ready_guard() -> None:
    return None


def _ensure_semantic_runtime() -> None:
    return None


def preload_semantic_runtime() -> None:
    return None


def start_semantic_accelerator() -> None:
    return None


def _ensure_nli_runtime() -> None:
    return None


def _lightweight_linguistic(text: str) -> Dict[str, Any]:
    return QUANTUM_INTERPRETATION_ENGINE._linguistic(normalize_text(text))


def _stanza_lang_ready(lang: str) -> bool:
    return False


def _stanza_resources_ready() -> bool:
    return False


def _provision_stanza_resources() -> None:
    return None
