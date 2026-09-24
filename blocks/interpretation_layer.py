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
            "active_entity": active_entity,
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
        result["interactive_task_state"] = open_task
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
        result["context_plan"] = result["cognitive_workspace"]

        # Promote the workspace decision into the canonical semantic surface used
        # by Processor/Executor. This prevents downstream adapters from falling
        # back to weaker legacy fields after the workspace has already resolved
        # the current turn.
        workspace = result["cognitive_workspace"]
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
            result["active_entity"] = workspace.get("active_entity") if "active_entity" in workspace else result.get("active_entity")
            result["continuation"] = bool(workspace.get("continuation"))
            result["reference_to_previous"] = bool(workspace.get("reference"))
            result["resolved_request"] = workspace.get("resolved_request") or result.get("resolved_request")
            result["semantic_request"] = workspace.get("resolved_request") or result.get("semantic_request")
            result["history_dependent_task"] = bool(workspace.get("task_continuation"))
            result["current_turn_authority"] = True
            result["historical_memory_is_evidence_only"] = True
            if workspace.get("conversation_continuation") and (workspace.get("continuation") or workspace.get("reference")):
                result["continuation_authority"] = "active_dialogue_sequence"
                result["selected_memory_index"] = -1
                result["selected_memory_operand"] = {
                    "source": "active_dialogue_sequence",
                    "sequence_id": workspace.get("sequence_id"),
                    "user_request": workspace.get("previous_user_turn"),
                    "april_answer": workspace.get("previous_april_turn"),
                    "user_id": (workspace.get("authenticated_scope") or {}).get("user_id", ""),
                    "conversation_id": (workspace.get("authenticated_scope") or {}).get("conversation_id", ""),
                }
            else:
                result["continuation_authority"] = "current_turn"
                result["selected_memory_index"] = -1
                result["selected_memory_operand"] = {}

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
                    "selected_live_sequence_only" if workspace.get("continuation") or workspace.get("reference")
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
                "selected_memory_operand": result.get("selected_memory_operand") or {},
                "selected_memory_index": result.get("selected_memory_index", -1),
            })
            result["dialogue_contract"] = contract
            result["interactive_task_state"] = workspace.get("active_task_context") or {}
            result["open_task"] = workspace.get("active_task_context") or {}
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
                "target_sequence_id": workspace.get("sequence_id"),
                "continuation_authority": result.get("continuation_authority"),
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

        seen: set[str] = set()
        for item in reversed(values[-self.MAX_MEMORY_CANDIDATES:]):
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
        relation = self._text(continuation_bridge.get("topic_relation") or relation).upper()

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
        if selected_memory:
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
            "current_request": self._excerpt(text, 1200),
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
            "context_dependency": continuation_bridge.get("context_dependency") or "independent",
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
                "historical_memory": "evidence_only",
                "current_request_policy": "preserve_semantically; compact only when provider envelope requires it",
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
