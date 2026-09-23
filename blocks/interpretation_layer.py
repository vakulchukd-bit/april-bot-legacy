"""
APRIL INTERPRETATION LAYER — QUANTUM MATRIX ENGINE

Single semantic engine for:
input -> matrix interpretation -> evidence packet -> QUANTUM_PROCESSOR
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

        active = bool(
            value.get("pending_input")
            or value.get("open")
            or value.get("active")
            or status in cls.ACTIVE_STATUSES
            or kind in {"riddle", "question", "game", "choice"}
            or prompt
        )

        if not active:
            return {}

        expected = cls._text(
            value.get("expected_input_type")
            or value.get("input_type")
            or "answer"
        )

        return {
            "active": True,
            "status": status or "open",
            "kind": kind or "task",
            "prompt": prompt,
            "expected_input_type": expected,
            "target": target,
            "candidate_answer": cls._text(
                value.get("candidate_answer") or value.get("answer_candidate")
            ),
            "topic": cls._text(value.get("topic") or value.get("canonical_topic")),
            "goal": cls._text(value.get("goal") or value.get("task_goal")),
            "sequence_id": cls._text(value.get("sequence_id") or value.get("active_sequence_id")),
            "scene_id": cls._text(value.get("scene_id") or value.get("source_scene_id")),
            "task_revision": int(value.get("task_revision", 0) or 0),
            "source": cls._text(value.get("source") or "state"),
            "raw": dict(value),
        }

    @classmethod
    def _assistant_question_is_task(cls, assistant_text: str) -> bool:
        text = cls._text(assistant_text)
        if not text:
            return False

        # Structural question detection first.
        question_form = "?" in text or "？" in text

        lowered = text.lower()
        riddle_structure = (
            "что это" in lowered
            or "угадай" in lowered
            or "какое слово" in lowered
            or "я загадал" in lowered
            or "отгада" in lowered
            or "как определить" in lowered
            or "как отличить" in lowered
            or "что получится" in lowered
        )

        # A sufficiently long question-like assistant reply can itself be
        # an active task even without a riddle marker.
        words = cls._tokens(text)
        long_question = question_form and len(words) >= 5

        return bool(question_form and (riddle_structure or long_question))

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
        if any(
            marker in lowered
            for marker in ("угадай", "я загадал", "что это", "какое слово", "отгада", "как определить", "как отличить")
        ):
            kind = "riddle"
            goal = "solve_riddle"
        else:
            kind = "question"
            goal = "answer_question"

        # The answer is deliberately unknown.  We do NOT turn nouns mentioned
        # in the question into the active entity.
        return {
            "active": True,
            "status": "open",
            "kind": kind,
            "prompt": text,
            "expected_input_type": "answer",
            "target": "",
            "candidate_answer": "",
            "topic": "загадка" if kind == "riddle" else "вопрос",
            "goal": goal,
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
        candidates: list[tuple[str, Any]] = [
            ("state.open_task", state.get("open_task")),
            ("state.active_task", state.get("active_task")),
            ("state.dialogue_task", state.get("dialogue_task")),
            ("state.pending_task", state.get("pending_task")),
            ("scene.open_task", scene.get("open_task")),
            ("scene.task_state", scene.get("task_state")),
            ("scene.active_task", scene.get("active_task")),
        ]

        sequence = state.get("active_dialogue_sequence")
        if isinstance(sequence, dict):
            candidates.extend(
                [
                    ("sequence.open_task", sequence.get("open_task")),
                    ("sequence.task_state", sequence.get("task_state")),
                    ("sequence.active_task", sequence.get("active_task")),
                ]
            )

        # A previous dialogue vector may carry the task state.
        vector = (
            scene.get("dialogue_vector")
            if isinstance(scene.get("dialogue_vector"), dict)
            else {}
        )
        candidates.extend(
            [
                ("scene.dialogue_vector.open_task", vector.get("open_task")),
                ("scene.dialogue_vector.task_state", vector.get("task_state")),
            ]
        )

        for source, value in candidates:
            frame = cls._task_mapping(value)
            if frame:
                frame["source"] = source
                return frame

        inferred = cls._infer_task_from_assistant(
            previous_assistant,
            scene_id=cls._text(scene.get("scene_id")),
            sequence_id=cls._text(
                scene.get("sequence_id")
                or (
                    sequence.get("sequence_id")
                    if isinstance(sequence, dict)
                    else ""
                )
            ),
        )
        if inferred:
            return inferred

        # Last history assistant may be newer than state.
        if previous_assistant:
            for turn in reversed(history):
                assistant = cls._text(turn.get("assistant"))
                if assistant != previous_assistant:
                    continue
                inferred = cls._infer_task_from_assistant(
                    assistant,
                    scene_id=cls._text(turn.get("scene_id")),
                    sequence_id=cls._text(
                        sequence.get("sequence_id")
                        if isinstance(sequence, dict)
                        else ""
                    ),
                )
                if inferred:
                    return inferred

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
            return {"is_answer": False, "confidence": 0.0, "reason": "empty"}

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

        # A request to replace the current task is never treated as an answer
        # to the previous task.
        transition = cls._explicit_task_transition(normalized, dialogue)
        if transition.get("requested"):
            return {
                "is_answer": False,
                "confidence": 0.0,
                "reason": "task_transition_requested",
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
                "confidence": 0.0,
                "reason": "explicit_external_topic",
            }

        # Imperative morphology usually addresses the assistant with a new
        # instruction ("Расскажи про Tesla", "Покажи ..."), not an answer to
        # the active riddle.  This is discourse-shape evidence, not routing.
        if imperative_form and len(words) >= 2:
            return {
                "is_answer": False,
                "confidence": 0.0,
                "reason": "new_directive_shape",
            }

        if task_reference:
            return {
                "is_answer": True,
                "confidence": 0.99,
                "reason": "explicit_task_reference",
            }

        if task.get("kind") in {"riddle", "game", "choice"} and answer_shape:
            return {
                "is_answer": True,
                "confidence": 0.94 if not question_form else 0.88,
                "reason": "open_interactive_task",
            }

        if task.get("kind") == "question":
            if answer_shape:
                return {
                    "is_answer": True,
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
                "confidence": 0.82,
                "reason": "short_discourse_followup",
            }

        return {
            "is_answer": False,
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

        # Open task ownership wins over weak novelty.  Only an explicit topic
        # boundary is allowed to break out of an active task.
        protected_by_task = bool(
            (open_task or {}).get("active")
            and not task_transition.get("requested")
            and task_answer.get("is_answer")
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
        riddle_request = "загад" in low and any(
            x in low for x in ("загадай", "придумай", "друг", "нов", "ещ", "слож")
        )
        if "придумай" in low and not riddle_request:
            riddle_request = any(x in low for x in ("еще", "ещё", "друг", "нов"))

        kind = "riddle" if riddle_request else cls._text(existing.get("kind")) or "task"

        prompt = ""
        status = "pending_generation" if riddle_request else "open"
        expected = "assistant_generation" if riddle_request else "answer"

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
            "prompt": prompt,
            "expected_input_type": expected,
            "target": "",
            "candidate_answer": "",
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

        # Task transition creates a new task frame.  The conversation itself
        # remains the same scene unless the user explicitly changed topics.
        if task_transition.get("replace_task"):
            open_task = cls._new_task_frame(
                existing=open_task,
                transition=task_transition,
                state=state,
                scene=current,
                text=text,
                sequence_id=sequence_id,
            )

        elif open_task.get("active") and task_answer.get("is_answer"):
            open_task = dict(open_task)
            open_task["status"] = "answer_received"
            open_task["candidate_answer"] = cls._text(text)
            open_task["last_answer_confidence"] = float(
                task_answer.get("confidence", 0.0) or 0.0
            )
            open_task["source"] = open_task.get("source") or "task_owner"

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
        if task_transition.get("replace_task"):
            # Replacing the current task is still continuation of the same
            # conversational scene; only an explicit external subject change
            # may create a new scene.
            topic_boundary = False
        elif open_task.get("active"):
            topic_boundary = bool(
                (
                    evidence.get("explicit")
                    or evidence.get("request_boundary")
                    or evidence.get("semantic")
                )
                and not task_answer.get("is_answer")
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
        state["open_task"] = open_task
        state["active_task"] = open_task

        if open_task.get("active"):
            runtime = (
                state.get("interpretation_runtime")
                if isinstance(state.get("interpretation_runtime"), dict)
                else {}
            )
            runtime["active_task"] = dict(open_task)
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
            "task_answer": task_answer,
            "task_transition": task_transition,
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
        if task_relation.get("is_answer"):
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

        started = time.perf_counter()

        last_assistant, last_user, reply_to = self._history(history)

        # The old sequence topic is evidence only.  Current task ownership is
        # resolved from the live state/scene/history before we choose the
        # canonical topic.
        raw_scene = LIVE_SCENE_CONTINUITY_ENGINE._scene_from_state(state)
        inferred_open_task = LIVE_SCENE_CONTINUITY_ENGINE._find_open_task(
            state,
            LIVE_SCENE_CONTINUITY_ENGINE._history_turns(history),
            raw_scene,
            last_assistant,
        )

        transition_preview = LIVE_SCENE_CONTINUITY_ENGINE._explicit_task_transition(
            text,
            {"label": ""},
        )

        if inferred_open_task.get("active") and not transition_preview.get("replace_task"):
            owner_topic = self.normalize(
                inferred_open_task.get("topic")
                or ("загадка" if inferred_open_task.get("kind") == "riddle" else "вопрос")
            )
        else:
            owner_topic = ""

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
            inferred_open_task.get("goal")
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

        live_scene_record = (
            live_scene.get("scene", {})
            if isinstance(live_scene.get("scene"), dict)
            else {}
        )

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

        canonical_context_dependency = (
            "continuation"
            if continuation
            else "recall"
            if reference
            else "new_topic"
            if live_scene.get("topic_boundary")
            else "independent"
        )

        candidate_answer = self.normalize(
            open_task.get("candidate_answer") if task_active else ""
        )
        active_entity = self.normalize(
            open_task.get("target") if task_active else ""
        )

        task_relation = live_scene.get("task_answer", {})
        task_transition = live_scene.get("task_transition", {})
        forbidden_entities = list(
            live_scene.get("forbidden_entities", [])
            if isinstance(live_scene.get("forbidden_entities"), list)
            else []
        )

        # Do not expose an inherited sequence entity as the active entity.
        # Candidates belong to the task and are not facts until confirmed.
        if task_active and candidate_answer and not active_entity:
            active_entity = ""

        if task_active:
            resolved_request = (
                "Continue the current active task.\n"
                f"Task type: {open_task.get('kind')}\n"
                f"Task goal: {effective_goal}\n"
                f"Open task prompt: {open_task.get('prompt')}\n"
                f"Current user turn: {text}\n"
                f"Candidate answer: {candidate_answer}\n"
                "Treat the current user turn as an interaction with this task "
                "unless the user explicitly changes the subject."
            )
            if task_transition.get("replace_task"):
                resolved_request = (
                    "Replace the previous task with a new task requested by the user.\n"
                    f"Current user instruction: {text}\n"
                    f"Previous task target is forbidden from reuse: {forbidden_entities}\n"
                    "Do not continue the previous target. Create the requested new task."
                )
        elif continuation:
            resolved_request = (
                "Continue the active conversation naturally.\n"
                f"Active scene topic: {effective_topic}\n"
                f"Previous user turn: {last_user}\n"
                f"Previous April turn: {last_assistant}\n"
                f"Current user instruction: {text}"
            )
        else:
            resolved_request = text

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
            "status": open_task.get("status") if task_active else "",
            "prompt": open_task.get("prompt") if task_active else "",
            "candidate_answer": candidate_answer,
            "expected_input_type": open_task.get("expected_input_type") if task_active else "",
            "task_revision": open_task.get("task_revision", 0) if task_active else 0,
            "avoid_entities": forbidden_entities,
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
            "active_entity": active_entity,
            "candidate_answer": candidate_answer,
            "open_task": open_task,
            "active_task": active_task_contract,
            "task_relation": task_relation,
            "task_transition": task_transition,
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
        result["active_task"] = active_task_contract
        result["open_task"] = open_task
        result["task_relation"] = task_relation
        result["task_transition"] = task_transition
        result["active_entity"] = active_entity
        result["candidate_answer"] = candidate_answer
        result["forbidden_entities"] = forbidden_entities

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
