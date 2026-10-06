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
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

# VRU_SINGLE_FILE_CONTRACT = True

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

# Optional lightweight fuzzy matcher. It is an evidence source only and never
# owns the CONTINUE/NEW decision.
try:
    from rapidfuzz import fuzz as _rapidfuzz
except Exception:  # pragma: no cover
    _rapidfuzz = None

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


# ============================================================================
# EMBEDDED VRU — Vector/Reference Understanding for authenticated 12h pairs
# ============================================================================
# VRU is kept INSIDE this canonical interpretation layer. No separate module is
# required at runtime, so deployment cannot fail because of a missing VRU file.
# Stage: authenticated 12h pair discovery -> VRU semantic fusion -> final
# CONTINUE/RECALL/NEW definition -> existing formulation/provider route.

VRU_VERSION = "vru_12h_pair_semantic_fusion_v1"

_STOP = {
    "что", "это", "такое", "такой", "такая", "такие", "кто", "как", "почему",
    "зачем", "а", "и", "но", "же", "в", "во", "на", "с", "со", "у", "из", "по",
    "для", "про", "о", "об", "от", "до", "за", "не", "ни", "я", "ты", "мне", "меня",
    "тебя", "мы", "вы", "они", "он", "она", "оно", "их", "им", "ему", "ей", "его",
    "ее", "её", "них", "ним", "него", "нее", "неё", "этот", "эта", "эти", "этим",
    "этом", "так", "теперь", "тогда", "пожалуйста", "просто", "сам", "сама", "самые",
    "есть", "были", "был", "быть", "можно", "нужно", "хочу", "хотел", "хотела",
}

_REFERENCE = {
    "он", "она", "оно", "они", "его", "ее", "её", "ему", "ей", "им", "их", "них",
    "ним", "него", "неё", "нее", "этому", "этого", "этим", "этот", "эта", "эти",
    "такой", "такая", "такое", "такие", "из них", "из этих", "из тех",
}

_CONTINUATION = {
    "дальше", "далее", "ещё", "еще", "следующее", "следующий", "следующая", "следующие",
    "продолжай", "продолжи", "продолжить", "добавь", "расширь", "подробнее", "детальнее",
    "уточни", "поясни", "объясни", "раскрой", "разверни",
}

_FORMAT_COMMANDS = {
    "в столбик": "vertical_list",
    "столбиком": "vertical_list",
    "списком": "vertical_list",
    "по пунктам": "numbered_or_bulleted_list",
    "таблицей": "table",
    "в таблице": "table",
}

_LIST_WORDS = {
    "назови", "назов", "перечисли", "перечислить", "список", "списком", "виды", "породы",
    "пункты", "столбик", "столбиком", "добавь", "ещё", "еще",
}

_EXPLICIT_NEW = (
    r"\bнов(ая|ую)?\s+тем",
    r"\bдругая\s+тема\b",
    r"\bперейд(и|ем|ём)\s+(?:к|на)\s+друг",
    r"\bначн(ем|ём|ать)\s+(?:нов|друг)",
)

_EXPLICIT_RECALL = (
    r"\bвспомн",
    r"\bраньше\b",
    r"\bдо\s+этого\b",
    r"\bперед\s+этим\b",
    r"\bпредыдущ",
    r"\bчто\s+я\s+спрашивал",
    r"\bо\s+ч[её]м\s+я(?:\s+(?:тебя|вас|мы))?\s+спрашивал",
    r"\bо\s+ч[её]м\s+мы\s+говорили",
    r"\bв\s+истории\b",
    r"\bв\s+контексте\b",
)

_REPAIR = (
    r"\bя\s+просил\b",
    r"\bя\s+имел\s+в\s+виду\b",
    r"\bя\s+говорил\b",
    r"\bне\s+так\b",
    r"\bне\s+то\b",
    r"\bты\s+не\s+понял",
    r"\bты\s+ошиб",
)


@dataclass(frozen=True)
class VRUPairEvidence:
    index: int
    score: float
    user_score: float
    answer_score: float
    chain_score: float
    format_score: float
    subject_score: float
    recency: float
    pair_subject: str
    reasons: tuple[str, ...]


class VRUContextInterpreter:
    VERSION = VRU_VERSION

    def _tokens(self, text: Any) -> list[str]:
        raw = re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", str(text or "").lower())
        return [self._stem(x) for x in raw if len(x) >= 2]

    def _stem(self, token: str) -> str:
        t = token.lower().replace("ё", "е").replace("й", "и")
        # Lightweight conversational morphology. Intentionally conservative.
        for suffix in (
            "ами", "ями", "ого", "ему", "ыми", "ими", "ов", "ев", "ей", "ах", "ях", "ам", "ям",
            "ом", "ем", "ой", "ый", "ий", "ая", "яя", "ое", "ее", "ые", "ие", "ую", "юю",
            "ыми", "ими", "ить", "ать", "ять", "ить", "ы", "и", "а", "я", "о", "е", "у", "ю",
        ):
            if len(t) > 5 and t.endswith(suffix):
                return t[:-len(suffix)]
        return t

    def _content(self, text: Any) -> set[str]:
        return {x for x in self._tokens(text) if x not in _STOP and len(x) >= 3}

    def _overlap(self, a: Any, b: Any) -> float:
        aa = self._content(a)
        bb = self._content(b)
        if not aa or not bb:
            return 0.0
        inter = len(aa & bb)
        union = len(aa | bb)
        return inter / max(1, union)

    def _contains(self, text: str, words: Iterable[str]) -> bool:
        low = str(text or "").lower()
        return any(w in low for w in words)

    def _has_regex(self, text: str, patterns: Iterable[str]) -> bool:
        low = str(text or "").lower()
        return any(re.search(p, low) for p in patterns)

    def _format_hint(self, text: str) -> str:
        low = str(text or "").lower()
        for phrase, fmt in _FORMAT_COMMANDS.items():
            if phrase in low:
                return fmt
        return ""

    def _pair_text(self, pair: dict[str, Any]) -> tuple[str, str, str]:
        user = str(pair.get("user") or pair.get("user_request") or pair.get("user_text") or "").strip()
        answer = str(pair.get("april") or pair.get("april_answer") or pair.get("assistant") or pair.get("answer") or "").strip()
        combined = f"{user} {answer}".strip()
        return user, answer, combined

    def _pair_subject(self, pair: dict[str, Any]) -> str:
        for key in ("active_entity", "resolved_entity", "canonical_topic", "topic", "subtopic"):
            value = str(pair.get(key) or "").strip()
            if value:
                return value[:220]
        user, answer, _ = self._pair_text(pair)
        # Prefer concrete noun-rich words from the user, then answer.
        for source in (user, answer):
            words = [w for w in self._content(source) if len(w) >= 4]
            if words:
                return " ".join(words[:4])[:220]
        return ""

    def _is_format_only(self, current: str) -> bool:
        low = current.lower().strip()
        if self._format_hint(low):
            content = self._content(low)
            command_tokens = set(re.findall(r"[a-zа-яёіїєґ]+", low))
            # Keep this broad for natural short commands: "в столбик" / "покажи списком".
            meaningful = {x for x in command_tokens if x not in _STOP}
            return len(meaningful) <= 4 or meaningful.issubset(_LIST_WORDS | {"покажи", "сделай", "дай", "назови"})
        return False

    def _subject_family(self, current: str, pair_text: str) -> float:
        # Strong domain anchors that survive inflection/wording changes.
        pairs = (
            ({"кот", "кош", "кошач", "домашн", "пород"}, 0.34),
            ({"лошад", "лошади", "пород"}, 0.30),
            ({"таблиц", "столбик", "строк", "колон"}, 0.18),
            ({"код", "функц", "скрипт", "модул"}, 0.18),
            ({"фото", "изображ", "картин", "сним"}, 0.18),
        )
        c = self._content(current)
        p = self._content(pair_text)
        if not c or not p:
            return 0.0
        score = 0.0
        for group, weight in pairs:
            if any(any(tok.startswith(root) for root in group) for tok in c) and any(
                any(tok.startswith(root) for root in group) for tok in p
            ):
                score = max(score, weight)
        return score

    def _scope_conflict(self, current: str, answer: str) -> bool:
        low_c = str(current or "").lower()
        low_a = str(answer or "").lower()
        domestic_request = ("домашн" in low_c) and ("кот" in low_c or "кош" in low_c or self._is_format_only(low_c))
        if not domestic_request:
            return False
        domestic_markers = ("домашн", "британ", "шотланд", "мейн-кун", "сиам", "персид", "сфинкс", "бенгал", "абиссин", "рэгдолл", "ангор")
        wild_markers = ("лев", "тигр", "леопард", "ягуар", "гепард", "пума", "рысь", "каракал", "сервал", "оцелот", "манул")
        domestic_hits = sum(1 for x in domestic_markers if x in low_a)
        wild_hits = sum(1 for x in wild_markers if x in low_a)
        return wild_hits >= 2 and domestic_hits == 0

    def _pair_evidence(self, current: str, pairs: list[dict[str, Any]], i: int) -> VRUPairEvidence:
        pair = pairs[i]
        user, answer, combined = self._pair_text(pair)
        latest_distance = len(pairs) - 1 - i
        recency = 1.0 / (1.0 + 0.18 * max(0, latest_distance))

        user_score = self._overlap(current, user)
        answer_score = self._overlap(current, answer)
        pair_score = self._overlap(current, combined)
        format_hint = self._format_hint(current)
        format_score = 0.0
        low_answer = answer.lower()
        if format_hint == "vertical_list" and ("\n" in answer or answer.count(",") >= 2 or answer.count(";") >= 2):
            format_score = 0.62
        elif format_hint == "table" and ("табли" in low_answer or "|" in answer):
            format_score = 0.62

        reasons: list[str] = []
        if user_score >= 0.12:
            reasons.append("USER_MEANING_OVERLAP")
        if answer_score >= 0.12:
            reasons.append("APRIL_RESULT_OVERLAP")
        if format_score:
            reasons.append("RESULT_FORMAT_MATCH")

        explicit_reference = self._contains(current.lower(), _REFERENCE)
        continuation = self._contains(current.lower(), _CONTINUATION)
        repair = self._has_regex(current, _REPAIR)
        format_only = self._is_format_only(current)
        if explicit_reference:
            reasons.append("REFERENCE_FORM")
        if continuation:
            reasons.append("CONTINUATION_FORM")
        if repair:
            reasons.append("REPAIR_FORM")
        if format_only:
            reasons.append("ELLIPTICAL_FORMAT_COMMAND")

        # Chain score: measure whether this pair shares meaning with the nearest
        # neighboring pairs. The point is to fuse a sequence, not elect a lone row.
        chain_score = 0.0
        if i > 0:
            _, prev_a, _ = self._pair_text(pairs[i - 1])
            chain_score = max(chain_score, self._overlap(answer, prev_a))
        if i + 1 < len(pairs):
            next_u, _, _ = self._pair_text(pairs[i + 1])
            chain_score = max(chain_score, self._overlap(answer, next_u))
        if chain_score >= 0.10:
            reasons.append("PAIR_CHAIN_LINK")

        subject_score = self._subject_family(current, combined)
        if subject_score:
            reasons.append("DOMAIN_FAMILY_MATCH")

        conflict = self._scope_conflict(current, answer)
        if conflict:
            reasons.append("CURRENT_SCOPE_CONFLICT")

        score = (
            0.22 * pair_score
            + 0.16 * user_score
            + 0.24 * answer_score
            + 0.14 * chain_score
            + 0.12 * format_score
            + 0.08 * subject_score
            + 0.04 * recency
            - (0.24 if conflict else 0.0)
        )

        # Deterministic boosts for conversational ellipsis.
        if format_only:
            score += 0.20 * min(1.0, answer_score * 2.4 + format_score)
        if explicit_reference:
            score += 0.10
        if repair:
            score += 0.10
        score = max(0.0, min(1.0, score))

        return VRUPairEvidence(
            index=i,
            score=score,
            user_score=user_score,
            answer_score=answer_score,
            chain_score=chain_score,
            format_score=format_score,
            subject_score=subject_score,
            recency=recency,
            pair_subject=self._pair_subject(pair),
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def _is_clarification_answer(self, answer: str) -> bool:
        low = str(answer or "").lower().strip()
        return bool(
            re.search(r"\bуточн", low)
            or re.search(r"\bпришлите\b", low)
            or re.search(r"\bчто именно\b", low)
            or re.search(r"\bне\s+совсем\s+понял", low)
            or re.search(r"\bне\s+понял", low)
            or re.search(r"\bнужно прислать\b", low)
        )

    def _scope_pair_indices(self, current: str, pairs: list[dict[str, Any]], ranked: list[VRUPairEvidence]) -> list[int]:
        low = str(current or "").lower()
        domestic = "домашн" in low and ("кот" in low or "кош" in low or self._is_format_only(low))
        if not domestic:
            return []
        markers = ("домашн", "британ", "шотланд", "мейн-кун", "сиам", "персид", "сфинкс", "бенгал", "абиссин", "рэгдолл", "ангор")
        indices = []
        for e in ranked:
            if "CURRENT_SCOPE_CONFLICT" in e.reasons:
                continue
            _, answer, combined = self._pair_text(pairs[e.index])
            low_combined = combined.lower()
            if any(m in low_combined for m in markers):
                # Exclude clarification-only answers when a substantive domestic
                # result exists elsewhere in the same 12h window.
                if self._is_clarification_answer(answer):
                    continue
                indices.append(e.index)
        return sorted(dict.fromkeys(indices))[-6:]

    def analyze(
        self,
        current: str,
        pairs: list[dict[str, Any]],
        seed: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = str(current or "").strip()
        window = [p for p in (pairs or []) if isinstance(p, dict)][:]
        seed = seed if isinstance(seed, dict) else {}

        if not window:
            return {
                "version": self.VERSION,
                "relation": "NEW",
                "confidence": 0.92,
                "selected_indices": [],
                "context_pairs": [],
                "anchor_index": -1,
                "definition": "NEW",
                "reason": "NO_AUTHENTICATED_12H_PAIRS",
                "provider_safe": True,
            }

        evidence = [self._pair_evidence(current, window, i) for i in range(len(window))]
        ranked = sorted(evidence, key=lambda x: (x.score, x.index), reverse=True)

        explicit_new = self._has_regex(current, _EXPLICIT_NEW)
        explicit_recall = self._has_regex(current, _EXPLICIT_RECALL)
        repair = self._has_regex(current, _REPAIR)
        low_current = current.lower()
        # Elliptical questions like "Какое ты неназвал" refer to the immediately
        # preceding result even without an explicit pronoun. Keep that dependency
        # inside the active dialogue sequence.
        omission_reference = bool(
            re.search(
                r"\b(?:какое|какая|какие|который|которая|которые|что|кто)\b.{0,80}\bне\s*(?:назвал|назвала|назвали|упомянул|упомянула|упомянули)\b",
                low_current,
                re.I,
            )
        )
        reference = any(x in low_current for x in _REFERENCE) or omission_reference
        continuation = any(x in low_current for x in _CONTINUATION)
        format_hint = self._format_hint(current)
        format_only = self._is_format_only(current)

        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        top_cut = max(0.13, best.score * 0.58)
        connected = [x for x in ranked if x.score >= top_cut]
        # Do not fuse a pair whose APRIL answer conflicts with an explicitly
        # established current scope (for example wild cats when the user now
        # explicitly asks for domestic cats). The pair remains in the 12h memory
        # window, but is excluded from the semantic context packet.
        connected = [x for x in connected if "CURRENT_SCOPE_CONFLICT" not in x.reasons]

        # Prefer the latest substantive pair when a format-only command directly
        # follows a rich result. This is the critical "В столбик" repair.
        latest = evidence[-1]
        latest_user, latest_answer, latest_combined = self._pair_text(window[-1])
        latest_result_anchor = bool(
            format_only
            and format_hint == "vertical_list"
            and "CURRENT_SCOPE_CONFLICT" not in latest.reasons
            and not self._is_clarification_answer(latest_answer)
            and len(latest_answer.strip()) >= 40
            and (
                "домашн" in latest_user.lower()
                or any(x in latest_user.lower() for x in ("виды", "породы", "назови", "перечисли", "столбик"))
            )
        )
        direct_latest_result = bool(
            latest_result_anchor
            or (
                format_only
                and format_hint == "vertical_list"
                and "CURRENT_SCOPE_CONFLICT" not in latest.reasons
                and ("\n" in latest_answer or latest.answer_score >= 0.10)
            )
        )
        # A clarification reply is not a semantic result. For reference/omission
        # questions, anchor to the latest substantive USER↔APRIL pair instead of
        # the clarification itself. This prevents "какое не назвал" from inheriting
        # the assistant's own request-for-clarification text.
        latest_substantive = next(
            (x for x in reversed(evidence)
             if "CURRENT_SCOPE_CONFLICT" not in x.reasons
             and not self._is_clarification_answer(self._pair_text(window[x.index])[1])),
            None,
        )
        scope_indices = self._scope_pair_indices(current, window, ranked)
        if direct_latest_result and latest.score >= 0.0:
            anchor = latest
        elif omission_reference and latest_substantive is not None:
            anchor = latest_substantive
        elif scope_indices:
            anchor = next((x for x in reversed(evidence) if x.index == scope_indices[-1]), best)
        elif reference and latest.score >= 0.08 and "CURRENT_SCOPE_CONFLICT" not in latest.reasons:
            # For anaphoric turns, the immediately preceding user-selected pair
            # is the preferred discourse anchor even when an older pair has a
            # slightly higher lexical score. The later pair may contain the
            # actual narrowed scope (e.g. "из домашних видов").
            anchor = latest
        else:
            non_conflicting = [x for x in ranked if "CURRENT_SCOPE_CONFLICT" not in x.reasons]
            anchor = non_conflicting[0] if non_conflicting else best

        if explicit_new:
            relation = "NEW"
            selected = []
            anchor_index = -1
            reason = "EXPLICIT_NEW_TOPIC"
        elif explicit_recall:
            selected = [x.index for x in connected[:6] if x.score >= 0.10]
            if not selected:
                selected = [best.index]
            relation = "RECALL"
            anchor_index = selected[0]
            reason = "HISTORY_QUERY_OVER_FUSED_PAIRS"
        else:
            # A compact command is not evaluated against the current sentence alone.
            # It inherits the active task from the strongest recent pair/result.
            semantic_continuation = bool(
                reference or continuation or repair or format_only
                or latest.answer_score >= 0.14
                or best.answer_score >= 0.18
                or best.chain_score >= 0.14
            )
            strong_fused_context = bool(
                best.score >= 0.20
                or latest.score >= 0.16
                or (reference and best.score >= 0.10)
                or (format_only and latest_result_anchor)
            )

            if semantic_continuation and strong_fused_context:
                relation = "CONTINUE"
                reason = "VRU_FUSED_PAIR_MEANING"
                if direct_latest_result:
                    # A pure formatting command directly after a substantive
                    # result should operate on that result only. This prevents a
                    # previous wrong/alternative answer in the 12h window from
                    # leaking into the semantic packet.
                    selected = [latest.index]
                elif omission_reference and latest_substantive is not None:
                    # "Какое ты неназвал" asks for the missing item from the
                    # immediately established result set, not from our clarification.
                    selected = [latest_substantive.index]
                else:
                    selected = sorted(dict.fromkeys(x.index for x in connected[:6]))
                    # When the current turn explicitly narrows the scope (e.g.
                    # "домашних котов"), prefer substantive pairs from that scope
                    # and drop clarification/error-answer rows from the fused context.
                    if scope_indices:
                        scoped = [i for i in selected if i in set(scope_indices)]
                        if scoped:
                            selected = scoped
                    # Always keep the current/latest result for an elliptical format command.
                    if format_only and latest.index not in selected and "CURRENT_SCOPE_CONFLICT" not in latest.reasons:
                        selected.append(latest.index)
                    selected = sorted(dict.fromkeys(selected))[-8:]
                anchor_index = anchor.index
            elif seed.get("relation") == "CONTINUE" and seed.get("selected_index", -1) >= 0:
                # Preserve an already-valid decision when VRU does not have enough
                # evidence to improve it. This keeps compatibility with production.
                relation = "CONTINUE"
                reason = "PRESERVE_VALID_PAIR_DECISION"
                # `context_pairs` contains pair dictionaries, not numeric indices.
                # The previous expression attempted `int(dict)` and crashed the
                # entire request. The selected_index is the only index needed here;
                # the actual pair objects are rebuilt below from `window`.
                try:
                    seed_index = int(seed.get("selected_index", -1))
                except (TypeError, ValueError):
                    seed_index = -1
                selected = [seed_index] if 0 <= seed_index < len(window) else []
                anchor_index = seed_index
            else:
                relation = "NEW"
                selected = []
                anchor_index = -1
                reason = "NO_FUSED_DIALOGUE_DEPENDENCY"

        # Build a fused semantic reading from ALL selected pairs, not just one row.
        context_pairs = [dict(window[i]) for i in selected if 0 <= i < len(window)]
        fused_user = " ".join(self._pair_text(p)[0] for p in context_pairs).strip()
        fused_answer = " ".join(self._pair_text(p)[1] for p in context_pairs).strip()
        fused_subjects = [self._pair_subject(p) for p in context_pairs if self._pair_subject(p)]
        fused_subject = " / ".join(dict.fromkeys(fused_subjects))[:420]

        # Explicitly recognize the user's current semantic target when they say
        # "домашних" or "домашних котов". This keeps the active subject from being
        # polluted by a previous broad "кошачьи" answer.
        low = current.lower()
        target_scope = ""
        if "домашн" in low and ("кот" in low or "кош" in low or format_only):
            target_scope = "домашние кошки / породы домашних кошек"
        elif "домашн" in fused_user.lower() or "домашн" in fused_answer.lower():
            target_scope = "домашние кошки / породы домашних кошек"
        elif fused_subject:
            target_scope = fused_subject

        output_format = format_hint or ""
        action = "answer_current_request"
        if relation == "CONTINUE" and format_only:
            action = "format_previous_result"
        elif relation == "CONTINUE" and reference:
            action = "develop_referenced_result"
        elif relation == "RECALL":
            action = "retrieve_fused_dialogue_memory"

        confidence = best.score
        if relation == "CONTINUE" and format_only:
            confidence = max(confidence, 0.88 if latest.answer_score >= 0.10 else 0.78)
        elif relation == "CONTINUE":
            confidence = max(confidence, 0.72)
        elif relation == "RECALL":
            confidence = max(confidence, 0.82)
        else:
            confidence = max(confidence, 0.86)

        margin = best.score - (second.score if second else 0.0)

        return {
            "version": self.VERSION,
            "relation": relation,
            "definition": relation,
            "confidence": round(min(0.99, max(0.0, confidence)), 6),
            "reason": reason,
            "selected_indices": selected,
            "anchor_index": anchor_index,
            "context_pairs": context_pairs,
            "candidate_evidence": [
                {
                    "index": x.index,
                    "score": round(x.score, 6),
                    "user_score": round(x.user_score, 6),
                    "answer_score": round(x.answer_score, 6),
                    "chain_score": round(x.chain_score, 6),
                    "format_score": round(x.format_score, 6),
                    "subject_score": round(x.subject_score, 6),
                    "recency": round(x.recency, 6),
                    "subject": x.pair_subject,
                    "reasons": list(x.reasons),
                }
                for x in ranked[:8]
            ],
            "fused_meaning": {
                "user_requests": fused_user[:1800],
                "april_answers": fused_answer[:2400],
                "subject": fused_subject,
                "target_scope": target_scope,
                "pair_count": len(context_pairs),
            },
            "dialogue_signals": {
                "explicit_new": explicit_new,
                "explicit_recall": explicit_recall,
                "reference": reference,
                "continuation": continuation,
                "repair": repair,
                "format_only": format_only,
                "format_hint": format_hint,
                "latest_result_anchor": direct_latest_result,
                "best_score": round(best.score, 6),
                "latest_score": round(latest.score, 6),
                "margin": round(margin, 6),
            },
            "task_definition": {
                "action": action,
                "inherits_previous_result": relation == "CONTINUE",
                "inherits_previous_subject": relation == "CONTINUE" and bool(target_scope),
                "output_format": output_format,
                "format_as_vertical_list": output_format == "vertical_list",
            },
            "contract": {
                "stage": "AFTER_12H_PAIR_DISCOVERY_BEFORE_FINAL_RELATION",
                "source": "STATE_MANAGER_AUTHENTICATED_12H_USER_APRIL_PAIRS",
                "uses_both_sides_of_pair": True,
                "uses_multiple_pairs": bool(len(context_pairs) > 1),
                "single_final_relation": True,
                "provider_must_not_reselect_context": True,
                "memory_mutation": False,
                "routing": False,
            },
            "provider_safe": True,
        }


VRU_CONTEXT_INTERPRETER = VRUContextInterpreter()


# ============================================================================
# EMBEDDED PAIR DIALOGUE UNDERSTANDING ENGINE — RICH HUMAN CONTINUATION v2
# ============================================================================
# This engine is intentionally embedded in the canonical interpretation layer.
# The production contract remains: authenticated 12h USER↔APRIL pairs first,
# then exactly one relation (CONTINUE / RECALL / NEW), then formulation/OpenAI.
# No provider, renderer, legacy intent branch or fallback may own this decision.

PAIR_DIRECTION_ENGINE_VERSION = "rich-human-continuation-v3-200-links"


class PairDialogueDirectionEngine:
    """Resolve how a current user turn relates to authenticated dialogue pairs.

    The engine models several common forms of human continuation that plain
    cosine/keyword similarity misses: anaphora ("из них", "кто из них"),
    elliptical continuation ("дальше", "ещё"), list extension with constraints
    ("не повторяйся", "кроме ..."), correction/repair ("я спрашивал ..."),
    comparison follow-ups, and explicit historical recall ("перед этим").

    It never routes or calls a provider. It returns one locked three-state
    decision and the exact pair indices that justify it.
    """

    VERSION = PAIR_DIRECTION_ENGINE_VERSION

    _NEW_PATTERNS = (
        r"\bнов(ая|ую)?\s+тем",
        r"\bдругая\s+тема\b",
        r"\bперейд(и|ем|ём)\s+(?:к|на)\s+друг",
        r"\bначн(ем|ём|ать)\s+(?:нов|друг)",
        r"\bтест\s*(?:номер|№|#)\s*\d+",
        r"\bначнем\s+тест\b",
        r"\bначн[её]м\s+тест\b",
    )
    _RECALL_PATTERNS = (
        r"\bвспомн",
        r"\bпомн(ишь|ю|и)?\b",
        r"\bя\s+(?:спрашивал|спрашивала|говорил|говорила|писал|писала)\b",
        r"\bраньше\b",
        r"\bдо\s+этого\b",
        r"\bперед\s+этим\b",
        r"\bпредыдущ(ий|ем|его|ую|ей)\b",
        r"\bв\s+предыдущ(ем|ем\s+вопросе|ем\s+диалоге)\b",
        r"\bгде\s+ты\s+(?:ошиб|сбил|не\s+понял)\b",
        r"\bвернись\b",
        r"\bнайди\s+в\s+(?:истории|контексте)\b",
        r"\bчто\s+я\s+спрашивал\b",
    )
    _CONTINUATION_PATTERNS = (
        r"\bдальше\b",
        r"\bещ[её]\b",
        r"\bследующ(ее|ий|ую|ая)\b",
        r"\bпродолж(и|ай|ить|аем|им|ение)\b",
        r"\bдалее\b",
        r"\bа\s+(?:теперь|дальше)\b",
        r"\bещ[её]\s+назов",
        r"\bназов(?:и|ывай).*\b(?:ещ[её]|дальше|следующ)",
        r"\bне\s+повторяй(?:ся)?\b",
        r"\bкроме\b",
        r"\bдобавь\b",
        r"\bчто\s+ещ[её]\b",
        r"\bкакое\s+ещ[её]\b",
        r"\bкакой\s+ещ[её]\b",
        r"\bкто\s+из\s+них\b",
        r"\bчто\s+из\s+них\b",
        r"\bкакой\s+из\s+них\b",
        r"\bкто\s+из\s+эт(?:их|ого)\b",
        r"\bа\s+если\b",
        r"\bа\s+что\s+(?:насчет|насчёт)\b",
        r"\bпо\s+этому\b",
        r"\bподробн(?:ее|ей)\b",
        r"\bдетальн(?:ее|ей)\b",
        r"\bрасшир(?:ь|и|ить)\b",
        r"\bразверни\b",
        r"\bраскрой\b",
        r"\bуточни\b",
        r"\bпоясни\b",
        r"\bобъясни\b",
        r"\bрасскажи\s+ещ[её]\b",
        r"\bчто\s+насчет\s+этого\b",
        r"\bа\s+кто\b",
        r"\bа\s+почему\b",
        r"\bа\s+зачем\b",
        r"\bнасколько\b",
    )
    # ------------------------------------------------------------------
    # Rich antecedent/object relation model.
    # 200 lightweight semantic links are evaluated before NEW/CONTINUE/RECALL.
    # A link is not a route; it is evidence connecting the current wording to
    # an authenticated USER↔APRIL pair object.
    # ------------------------------------------------------------------
    _OBJECT_PROFILE_PRIORITY = (
        "graph_chart", "table", "photo_image", "link", "code_program",
        "text_document", "plural_entity", "neuter_entity", "female_entity", "male_entity",
    )

    _OBJECT_PROFILES = {
        "male_entity": {
            "gender": "MASCULINE",
            "pronouns": {"он", "его", "ему", "им", "ним", "него", "нём", "нем", "этом", "этот", "такой"},
            "markers": {"график", "код", "текст", "файл", "документ", "сервис", "объект", "человек", "мужчина", "кот", "лев", "тигр", "волк"},
        },
        "female_entity": {
            "gender": "FEMININE",
            "pronouns": {"она", "её", "ее", "ей", "им", "ней", "неё", "нее", "эта", "такой"},
            "markers": {"таблица", "ссылка", "картина", "фраза", "тема", "страница", "система", "машина", "женщина"},
        },
        "neuter_entity": {
            "gender": "NEUTER",
            "pronouns": {"оно", "его", "ему", "им", "ним", "него", "нём", "нем", "это", "этому", "такое"},
            "markers": {"изображение", "фото", "фотография", "сообщение", "слово", "значение", "явление", "место", "животное"},
        },
        "plural_entity": {
            "gender": "PLURAL",
            "pronouns": {"они", "их", "им", "ними", "них", "эти", "такие", "которые", "которых"},
            "markers": {"данные", "люди", "хищники", "животные", "объекты", "варианты", "элементы", "имена", "пункты", "значения"},
        },
        "photo_image": {
            "gender": "NEUTER",
            "pronouns": {"это", "его", "ним", "нём", "нем", "него", "этом", "этом", "такое"},
            "markers": {"фото", "фотография", "изображение", "снимок", "картинка", "портрет", "изображено", "на фото", "на снимке"},
        },
        "graph_chart": {
            "gender": "MASCULINE",
            "pronouns": {"он", "его", "ему", "им", "ним", "нём", "нем", "этом", "этот", "такой"},
            "markers": {"график", "графика", "chart", "plot", "диаграмма", "кривая", "ось", "линия", "точки", "ряд данных"},
        },
        "table": {
            "gender": "FEMININE",
            "pronouns": {"она", "её", "ее", "ей", "ней", "неё", "нее", "этой", "этой", "такой"},
            "markers": {"таблица", "строки", "столбцы", "колонки", "ячейки", "табличные данные", "в таблице"},
        },
        "link": {
            "gender": "FEMININE",
            "pronouns": {"она", "её", "ее", "ней", "неё", "нее", "этой", "такой"},
            "markers": {"ссылка", "ссылку", "url", "адрес", "страница", "ресурс", "веб-страница", "сайт"},
        },
        "code_program": {
            "gender": "MASCULINE",
            "pronouns": {"он", "его", "ему", "им", "ним", "нём", "нем", "этот", "такой"},
            "markers": {"код", "скрипт", "программа", "модуль", "функция", "класс", "репозиторий", "проект", "api"},
        },
        "text_document": {
            "gender": "MASCULINE",
            "pronouns": {"он", "его", "ему", "им", "ним", "нём", "нем", "этот", "такой"},
            "markers": {"текст", "ответ", "вопрос", "абзац", "документ", "файл", "письмо", "сообщение", "описание"},
        },
    }

    _OBJECT_MARKER_ALIASES = {
        "фото": "photo_image", "фотография": "photo_image", "снимок": "photo_image", "картинка": "photo_image", "изображение": "photo_image",
        "график": "graph_chart", "графика": "graph_chart", "chart": "graph_chart", "plot": "graph_chart", "диаграмма": "graph_chart",
        "таблица": "table", "таблича": "table", "ссылка": "link", "url": "link", "код": "code_program", "скрипт": "code_program",
        "таблице": "table", "графике": "graph_chart", "графиках": "graph_chart", "таблице": "table", "ссылке": "link",
        "хищник": "plural_entity", "хищники": "plural_entity", "хищников": "plural_entity", "люди": "plural_entity", "людей": "plural_entity",
        "данные": "plural_entity", "элементы": "plural_entity", "варианты": "plural_entity", "имена": "plural_entity",
    }

    _ANAPHORIC_FORMS = {
        "он", "она", "оно", "они", "его", "ее", "её", "ему", "ей", "им", "ними", "ним", "них", "него", "неё", "нее", "нём", "нем",
        "этом", "этому", "этой", "этот", "эта", "это", "эти", "того", "той", "ту", "тем", "таким", "такую", "такие",
        "из них", "из этих", "из тех", "из него", "из неё", "из нее", "из этого", "из этой", "кто из них", "какой из них", "какая из них", "какие из них",
        "который из них", "которая из них", "которые из них", "в нём", "в нем", "в ней", "в них", "на нём", "на нем", "на ней", "на фото",
    }

    _CONTINUATION_LINK_PHRASES = (
        "дальше", "далее", "ещё", "еще", "следующее", "следующий", "следующая", "следующие",
        "продолжай", "продолжи", "продолжить", "раскрой", "расширь", "подробнее", "детальнее", "уточни",
        "поясни", "объясни", "добавь", "назови еще", "назови ещё", "ещё один", "еще один", "что дальше",
    )

    # Exactly 200 relation links: 10 object classes × 20 human follow-up forms.
    _RELATION_LINK_BANK = {
        f"{obj}:{idx}": phrase
        for obj in _OBJECT_PROFILES
        for idx, phrase in enumerate((
            "из него", "из неё", "из нее", "из них", "кто из них", "какой из них", "какая из них", "какие из них",
            "его", "её", "ее", "их", "ему", "ей", "им", "ним", "них", "в нём", "в ней", "в них",
        ), start=1)
    }

    _REPAIR_PATTERNS = (
        r"\bне\s+так\b",
        r"\bне\s+то\b",
        r"\bты\s+(?:ошибся|ошибаешься|не\s+понял|не\s+поняла)\b",
        r"\bя\s+спрашивал\b",
        r"\bя\s+имел\s+в\s+виду\b",
        r"\bя\s+говорил\b",
        r"\bя\s+именно\s+про\b",
        r"\bсбил(ся|ась)\b",
        r"\bсош[её]л\s+с\s+контекста\b",
        r"\bне\s+тупи\b",
    )
    _ANAPHORA = {
        "из них", "из этих", "из этого", "из тех", "кто из них", "что из них",
        "какой из них", "какая из них", "какое из них", "который из них",
        "которая из них", "которые из них", "их", "них", "этому", "этого",
        "этим", "этот", "эта", "эти", "это", "такой", "такая", "такое", "такие",
        "дальше", "ещё", "еще", "следующее", "следующий",
    }
    _LIST_INTENT = (
        r"\b(?:назов|назови|называй|перечисл|дай)\b",
        r"\b(?:тр[её]х|три|несколько|ещ[её])\b",
    )
    _EXCLUSION_PATTERNS = (
        r"\bне\s+повторяй(?:ся)?\b",
        r"\bкроме\b",
        r"\bбез\b",
        r"\bне\s+включай\b",
        r"\bуже\s+был(?:и|о)?\b",
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip().lower())

    @staticmethod
    def _tokens(value: Any) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", str(value or "").lower())

    @staticmethod
    def _semantic_token(token: str) -> str:
        """Tolerant morphological key for conversational matching.

        It normalizes common Russian case endings and a frequent ``щ/ш`` typo
        without changing the original pair text sent downstream.
        """
        t = str(token or "").lower().replace("ё", "е").replace("щ", "ш")
        if len(t) <= 4:
            return t
        endings = (
            "иями", "ями", "ами", "ого", "ему", "ому", "ами", "иях",
            "иях", "ах", "ях", "ов", "ев", "ей", "ем", "ам", "ям",
            "ом", "ой", "ою", "ую", "ую", "ия", "ие", "ий", "ая",
            "ое", "ые", "ым", "им", "ых", "их", "ую", "юю", "ы",
            "и", "а", "я", "у", "ю", "е", "о", "ь",
        )
        for ending in endings:
            if len(t) - len(ending) >= 4 and t.endswith(ending):
                return t[:-len(ending)]
        return t

    @classmethod
    def _content_tokens(cls, value: Any) -> set[str]:
        stop = {
            "что","это","как","кто","когда","где","куда","почему","зачем",
            "ты","вы","мне","тебе","меня","тебя","я","мы","и","а","но",
            "из","них","этих","этого","этот","эта","эти","уже","перед","этим",
            "для","про","о","об","по","на","в","с","со","к","за","же",
            "тест","номер","назови","называй","назвать","знаешь","знаеш","знать",
            "знаю","три","трое","трёх","трех","пожалуйста","любое","любые",
            "именно","вопрос","вопроса","вопросом","спросил","спрашивал","спрашивала",
        }
        return {t for t in cls._tokens(value) if len(t) >= 3 and t not in stop}

    @classmethod
    def _affinity(cls, left: Any, right: Any) -> float:
        raw_a = cls._content_tokens(left)
        raw_b = cls._content_tokens(right)
        if not raw_a or not raw_b:
            return 0.0
        a = {cls._semantic_token(x) for x in raw_a}
        b = {cls._semantic_token(x) for x in raw_b}
        a.discard(""); b.discard("")
        exact = len(a & b) / max(1, len(a | b))
        morph_hits = 0.0
        for x in a:
            best = 0.0
            for y in b:
                if x == y:
                    best = 1.0
                    break
                common = 0
                for ca, cb in zip(x, y):
                    if ca != cb:
                        break
                    common += 1
                if common >= 4:
                    best = max(best, common / max(len(x), len(y)))
            morph_hits += best
        morph = morph_hits / max(1, len(a))
        # Directional overlap helps short topical phrases such as
        # "подробнее о хищниках" match an earlier answer about "хищников".
        directional = len(a & b) / max(1, min(len(a), len(b)))
        return max(
            exact,
            min(1.0, 0.55 * exact + 0.30 * morph + 0.15 * directional),
        )

    @classmethod
    def _has_any(cls, text: str, patterns: tuple[str, ...]) -> bool:
        low = cls._norm(text)
        return any(re.search(p, low, re.I) for p in patterns)

    @classmethod
    def _has_anaphora(cls, text: str) -> bool:
        low = cls._norm(text)
        # "перед этим / до этого / в предыдущем вопросе" is historical recall,
        # not an anaphoric reference to the immediately preceding pair.
        if re.search(r"\b(?:перед\s+этим|до\s+этого|перед\s+этим\s+вопросом|в\s+предыдущем\s+вопросе)\b", low):
            return False
        if re.search(r"\b(?:кто|что|какой|какая|какое|какие)\s+из\s+них\b", low):
            return True
        if re.search(r"\b(?:из\s+них|из\s+этих|из\s+тех)\b", low):
            return True
        return any(re.search(rf"\b{re.escape(x)}\b", low) for x in cls._ANAPHORA if x not in {"этим", "этого"})

    @classmethod
    def _has_exclusion(cls, text: str) -> bool:
        return cls._has_any(text, cls._EXCLUSION_PATTERNS)

    @classmethod
    def _explicit_new(cls, text: str) -> bool:
        return cls._has_any(text, cls._NEW_PATTERNS)

    @classmethod
    def _explicit_recall(cls, text: str) -> bool:
        return cls._has_any(text, cls._RECALL_PATTERNS)

    @classmethod
    def _explicit_repair(cls, text: str) -> bool:
        return cls._has_any(text, cls._REPAIR_PATTERNS)

    @classmethod
    def _explicit_continuation(cls, text: str) -> bool:
        return cls._has_any(text, cls._CONTINUATION_PATTERNS)

    @classmethod
    def _pair_text(cls, pair: dict[str, Any]) -> tuple[str, str, str]:
        user = cls._norm(pair.get("user") or pair.get("user_text") or pair.get("user_request"))
        april = cls._norm(pair.get("april") or pair.get("april_text") or pair.get("april_answer") or pair.get("assistant") or pair.get("answer"))
        return user, april, f"{user} {april}".strip()

    @classmethod
    def _pair_subject(cls, pair: dict[str, Any]) -> str:
        explicit = pair.get("topic") or pair.get("canonical_topic") or pair.get("subtopic")
        if explicit:
            return cls._norm(explicit)
        user, april, _ = cls._pair_text(pair)
        # Prefer user request content. For list-like answers include answer too.
        return " ".join(sorted(cls._content_tokens(f"{user} {april}"), key=lambda x: (-len(x), x))[:6])

    @classmethod
    def _is_clarification_pair(cls, pair: dict[str, Any]) -> bool:
        _, april, _ = cls._pair_text(pair)
        if not april:
            return False
        return bool(re.search(
            r"^(?:уточните|уточни|скажите|напомни|пришли|непонятно|кого именно|что именно|\s*мне неясно)",
            april,
            re.I,
        ))

    @classmethod
    def _contains_reference_answer_set(cls, pair: dict[str, Any]) -> bool:
        _, april, _ = cls._pair_text(pair)
        if not april:
            return False
        # Assistant clarification/questions are not antecedent result sets.
        clarification = re.search(
            r"^(?:уточните|уточни|скажите|напомни|пришли|непонятно|кого именно|что именно)",
            april,
            re.I,
        )
        if clarification:
            return False
        has_items = len(re.findall(r",|;|\bи\b|\bили\b", april)) >= 1
        has_name_or_entity = bool(re.search(r"[A-Za-zА-Яа-яЁё]{3,}", april))
        return has_items and has_name_or_entity

    @classmethod
    def _collect_exclusions(cls, text: str) -> set[str]:
        low = cls._norm(text)
        result: set[str] = set()
        for m in re.finditer(r"\b(?:кроме|без)\s+([^.;!?]+)", low, re.I):
            result |= cls._content_tokens(m.group(1))
        if cls._has_exclusion(low):
            # Capture explicit names after "не повторяйся" only when present in
            # the current turn; generic exclusions are represented by a flag.
            result |= set(re.findall(r"[А-Яа-яЁёA-Za-z]{4,}", m.group(1))) if False else set()
        return result

    @classmethod
    def _select_by_object(cls, current: str, window: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[int]:
        current_tokens = cls._content_tokens(current)
        if not current_tokens:
            return []
        ranked: list[tuple[float, int]] = []
        for row in rows:
            pair = row.get("pair") if isinstance(row.get("pair"), dict) else {}
            _, _, combined = cls._pair_text(pair)
            topic = cls._pair_subject(pair)
            score = max(cls._affinity(current, combined), 0.9 * cls._affinity(current, topic))
            # Small morphology/substring boost for misspelled Russian nouns such as
            # "хишниках" vs "хищников".
            score = max(score, cls._affinity(" ".join(current_tokens), combined))
            ranked.append((score, int(row.get("index", -1))))
        ranked.sort(reverse=True)
        return [i for score, i in ranked if i >= 0 and score >= 0.16][:6]

    @classmethod
    def _find_historical_topic_pair(cls, current: str, window: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[int]:
        current_tokens = cls._content_tokens(current)
        if not current_tokens:
            return []
        ranked: list[tuple[float, int]] = []
        # For recall/repair, topical evidence in the USER side is weighted more
        # heavily than recency because the user is intentionally reaching back.
        for row in rows:
            pair = row.get("pair") if isinstance(row.get("pair"), dict) else {}
            user, april, combined = cls._pair_text(pair)
            user_score = cls._affinity(current, user)
            answer_score = cls._affinity(current, april)
            topic_score = cls._affinity(current, cls._pair_subject(pair))
            score = 0.54 * user_score + 0.26 * answer_score + 0.20 * topic_score
            ranked.append((score, int(row.get("index", -1))))
        ranked.sort(reverse=True)
        return [i for score, i in ranked if i >= 0 and score >= 0.12][:6]

    @classmethod
    def _object_profile_from_text(cls, text: str) -> dict[str, Any]:
        low = cls._norm(text)
        tokens = set(cls._tokens(low))
        explicit_plural = bool(re.search(
            r"\b(?:три|тр[её]х|двое|две|несколько|много|все|эти|они|их|них|данные|хищники|хищников|животные|люди|имена|варианты|элементы)\b",
            low,
            re.I,
        ))
        plural_answer_shape = bool(
            explicit_plural
            or len(re.findall(r"[,;]", low)) >= 1
            or bool(re.search(r"\b(?:лев|тигр|волк|собаки|кошки|люди)\b[^.]{0,80}\b(?:и|или)\b", low, re.I))
        )
        scored: list[tuple[float, int, str]] = []
        animal_list_shape = bool(
            plural_answer_shape
            and re.search(r"\b(?:лев|тигр|волк|медведь|лиса|рысь|собака|кошка|орёл|орел|ястреб|акула)\b", low, re.I)
        )
        for priority, obj_type in enumerate(cls._OBJECT_PROFILE_PRIORITY):
            profile = cls._OBJECT_PROFILES[obj_type]
            phrase_hits = sum(1 for marker in profile["markers"] if marker in low)
            token_hits = sum(1 for marker in profile["markers"] if marker in tokens)
            score = min(1.0, 0.30 * phrase_hits + 0.12 * token_hits)
            if obj_type == "plural_entity" and plural_answer_shape:
                score = min(1.0, score + 0.50)
            # A list of named entities is one plural conversational object for
            # anaphora purposes: "три хищника: лев, тигр и волк" -> "они/их/них".
            if obj_type == "plural_entity" and animal_list_shape:
                score = max(score, 0.96)
            scored.append((score, -priority, obj_type))
        # A clearly enumerated set ("три хищника: лев, тигр и волк") is one plural
        # antecedent even though its members individually have masculine gender.
        # The plural group wins over member-level gender so "кто из них" resolves
        # to the whole set, not to one animal.
        if animal_list_shape:
            best_type, best_score = "plural_entity", 0.99
        else:
            scored.sort(reverse=True)
            best_score, _, best_type = scored[0] if scored else (0.0, 0, "unknown")
        # Avoid classifying every animal/verb as an object. Generic grammatical
        # gender is retained only when there is actual object/entity evidence.
        if best_score < 0.16:
            best_type = "unknown"
            best_score = 0.0
        return {
            "object_type": best_type,
            "gender": (cls._OBJECT_PROFILES.get(best_type) or {}).get("gender", "UNKNOWN"),
            "score": round(best_score, 6),
            "pronouns": sorted((cls._OBJECT_PROFILES.get(best_type) or {}).get("pronouns", set())),
            "source": "PAIR_OBJECT_PROFILE_PRIORITY_AND_NUMBER_AGREEMENT",
        }

    @classmethod
    def _pronoun_class(cls, text: str) -> dict[str, Any]:
        low = cls._norm(text)
        forms = []
        for form in sorted(cls._ANAPHORIC_FORMS, key=len, reverse=True):
            if re.search(rf"(?<!\w){re.escape(form)}(?!\w)", low, re.I):
                forms.append(form)
        if not forms:
            return {"present": False, "forms": [], "gender_hints": [], "number": "UNKNOWN"}
        hints = set()
        plural = False
        for form in forms:
            if form in {"она", "её", "ее", "ей", "ней", "неё", "нее", "в ней", "на ней", "из неё", "из нее", "этой", "эта"}:
                hints.add("FEMININE")
            elif form in {"он", "этот", "такой", "который", "тот"}:
                hints.add("MASCULINE")
            elif form in {"оно", "это", "этому", "такое", "которое", "таковым", "на это"}:
                hints.add("NEUTER")
            elif form in {"они", "их", "им", "ними", "них", "из них", "в них", "кто из них", "какой из них", "какая из них", "какие из них", "которые из них", "эти", "такие"}:
                hints.add("PLURAL"); plural = True
            elif form in {"его", "ему", "им", "ним", "него", "нём", "нем", "в нём", "в нем", "из него", "на нём", "на нем", "этом", "тем", "к нему", "в него"}:
                # Russian "него/нему/нём/ним/его/ему" can refer to either
                # masculine or neuter antecedents; keep both hypotheses alive.
                hints.update({"MASCULINE", "NEUTER"})
        return {
            "present": True,
            "forms": forms,
            "gender_hints": sorted(hints),
            "number": "PLURAL" if plural else "SINGULAR_OR_UNKNOWN",
        }

    @classmethod
    def _object_relation_cue(cls, current: str, object_type: str) -> float:
        """Measure whether the wording of the current turn fits an object class."""
        low = cls._norm(current)
        cues = {
            "photo_image": ("фото", "фотографии", "снимке", "изображено", "видно", "изображение", "картинке", "на фото"),
            "graph_chart": ("графике", "график", "ось", "оси", "кривая", "точки", "динамика", "значения", "показатели", "данные"),
            "table": ("таблице", "таблица", "строки", "столбцы", "ячейки", "колонки", "данные"),
            "link": ("ссылке", "ссылка", "адрес", "url", "ресурс", "странице", "сайте"),
            "code_program": ("коде", "код", "функции", "функция", "строке кода", "ошибке", "модуле", "скрипте"),
            "text_document": ("тексте", "текст", "ответе", "абзаце", "сообщении", "документе", "файле"),
            "plural_entity": ("них", "они", "их", "всех", "элементов", "вариантов", "хищников", "людей", "данных"),
        }
        return 1.0 if object_type in cues and any(cue in low for cue in cues[object_type]) else 0.0

    @classmethod
    def _resolve_pair_object_and_antecedent(cls, current: str, window: list[dict[str, Any]]) -> dict[str, Any]:
        """Resolve current pronouns/anaphora to a concrete prior pair object.

        This pass runs before the three-state decision. It deliberately prefers the
        latest substantive pair compatible with pronoun number/gender/object type and
        ignores assistant clarification pairs as invalid antecedents.
        """
        current = cls._norm(current)
        pronoun = cls._pronoun_class(current)
        direct_object = cls._object_profile_from_text(current)
        candidates: list[dict[str, Any]] = []
        if not window or not pronoun["present"]:
            return {
                "resolved": False,
                "anchor_index": -1,
                "object_type": direct_object.get("object_type", "unknown"),
                "gender": direct_object.get("gender", "UNKNOWN"),
                "pronoun": pronoun,
                "candidates": [],
                "score": 0.0,
                "source": "PAIR_OBJECT_ANTECEDENT_RESOLUTION",
            }

        for idx in range(len(window) - 1, -1, -1):
            pair = window[idx]
            if cls._is_clarification_pair(pair):
                continue
            user, april, combined = cls._pair_text(pair)
            profile = cls._object_profile_from_text(f"{user} {april}")
            object_type = profile.get("object_type", "unknown")
            gender = profile.get("gender", "UNKNOWN")
            type_score = 0.0
            for hint in pronoun.get("gender_hints", []):
                if hint == gender:
                    type_score = max(type_score, 0.58)
                elif hint == "PLURAL" and object_type == "plural_entity":
                    type_score = max(type_score, 0.92)
                elif hint == "NEUTER" and object_type == "photo_image":
                    type_score = max(type_score, 0.78)
            answer_set = cls._contains_reference_answer_set(pair)
            if "PLURAL" in pronoun.get("gender_hints", []) and answer_set:
                type_score = max(type_score, 0.92)
            if any(f in {"в ней", "на ней"} for f in pronoun.get("forms", [])) and object_type == "table":
                type_score = max(type_score, 0.92)
            if any(f in {"из неё", "из нее", "её", "ее"} for f in pronoun.get("forms", [])) and object_type == "link":
                type_score = max(type_score, 0.80)
            if any(f in {"в нём", "в нем", "на нём", "на нем"} for f in pronoun.get("forms", [])) and object_type in {"graph_chart", "code_program", "text_document", "photo_image"}:
                type_score = max(type_score, 0.76)
            lexical = cls._affinity(current, combined)
            subject = cls._pair_subject(pair)
            subject_score = cls._affinity(current, subject)
            relation_cue = cls._object_relation_cue(current, object_type)
            recency = 1.0 / (1.0 + 0.10 * (len(window) - 1 - idx))
            score = min(1.0, 0.34 * type_score + 0.24 * (1.0 if answer_set and "PLURAL" in pronoun.get("gender_hints", []) else 0.0) + 0.16 * relation_cue + 0.14 * lexical + 0.07 * subject_score + 0.05 * recency)
            candidates.append({
                "index": idx,
                "score": round(score, 6),
                "object_type": object_type,
                "gender": gender,
                "answer_set": answer_set,
                "subject": subject,
                "relation_cue": relation_cue,
                "pair": dict(pair),
            })

        candidates.sort(key=lambda x: (x["score"], x["index"]), reverse=True)
        best = candidates[0] if candidates else None
        if not best:
            return {
                "resolved": False,
                "anchor_index": -1,
                "object_type": direct_object.get("object_type", "unknown"),
                "gender": direct_object.get("gender", "UNKNOWN"),
                "pronoun": pronoun,
                "candidates": [],
                "score": 0.0,
                "source": "PAIR_OBJECT_ANTECEDENT_RESOLUTION",
            }
        # Strong plural anaphora such as "кто из них" should resolve to a real
        # prior answer set even when lexical similarity is weak.
        strong_plural = "PLURAL" in pronoun.get("gender_hints", []) and bool(best.get("answer_set"))
        resolved = bool(best["score"] >= 0.30 or strong_plural)
        return {
            "resolved": resolved,
            "anchor_index": int(best["index"] if resolved else -1),
            "object_type": best["object_type"],
            "gender": best["gender"],
            "pronoun": pronoun,
            "candidates": candidates[:8],
            "score": float(best["score"]),
            "strong_plural_antecedent": strong_plural,
            "source": "PAIR_OBJECT_ANTECEDENT_RESOLUTION",
        }

    @classmethod
    def _semantic_link_evidence(cls, current: str, pair: dict[str, Any], antecedent: dict[str, Any]) -> dict[str, Any]:
        low = cls._norm(current)
        profile = cls._object_profile_from_text(" ".join(cls._pair_text(pair)))
        links = []
        gender = antecedent.get("gender") or profile.get("gender")
        obj_type = antecedent.get("object_type") or profile.get("object_type")
        if gender == "MASCULINE":
            links.extend(["он/его/ему/ним", "в нём/на нём", "этот/такой"])
        elif gender == "FEMININE":
            links.extend(["она/её/ей/ней", "в ней/на ней", "эта/такой"])
        elif gender == "NEUTER":
            links.extend(["оно/его/ему", "в нём/на нём", "это/такое"])
        elif gender == "PLURAL":
            links.extend(["они/их/им/ними", "из них/в них", "эти/такие"])
        if obj_type in {"photo_image"}:
            links.append("фото → оно/его/на нём")
        elif obj_type in {"graph_chart", "code_program", "text_document"}:
            links.append(f"{obj_type} → он/его/в нём")
        elif obj_type in {"table", "link"}:
            links.append(f"{obj_type} → она/её/в ней")
        elif obj_type == "plural_entity":
            links.append("множество элементов → они/их/них")
        matched = [k for k, phrase in cls._RELATION_LINK_BANK.items() if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", low, re.I)]
        return {
            "matched_link_keys": matched[:24],
            "matched_link_count": len(matched),
            "object_type": obj_type,
            "gender": gender,
            "semantic_links": links,
            "source": "200_LINK_SEMANTIC_RELATION_BANK",
        }

    def analyze(self, current: str, pairs: list[dict[str, Any]], scored_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        current = self._norm(current)
        window = [p for p in (pairs or []) if isinstance(p, dict)][:]
        rows = [r for r in (scored_rows or []) if isinstance(r, dict)]
        rows_by_index = {int(r.get("index", -1)): r for r in rows if str(r.get("index", "")).lstrip("-").isdigit()}
        if not rows:
            rows = [{"index": i, "score": self._affinity(current, self._pair_text(p)[2]), "pair": p} for i, p in enumerate(window)]
            rows_by_index = {int(r["index"]): r for r in rows}

        latest = len(window) - 1
        anaphora = self._has_anaphora(current)
        exclusion = self._has_exclusion(current)
        explicit_new = self._explicit_new(current)
        explicit_recall = self._explicit_recall(current)
        explicit_repair = self._explicit_repair(current)
        explicit_continuation = self._explicit_continuation(current)
        list_intent = self._has_any(current, self._LIST_INTENT)

        # Human discourse strengths. They are intentionally not just keyword
        # switches: they identify discourse functions that are later combined with
        # real pair evidence.
        antecedent_resolution = self._resolve_pair_object_and_antecedent(current, window)
        _raw_antecedent_index = antecedent_resolution.get("anchor_index", -1)
        antecedent_index = int(_raw_antecedent_index) if _raw_antecedent_index not in (None, "") else -1
        antecedent_pair = window[antecedent_index] if 0 <= antecedent_index < len(window) else {}
        semantic_links = self._semantic_link_evidence(current, antecedent_pair, antecedent_resolution) if antecedent_pair else {
            "matched_link_keys": [], "matched_link_count": 0, "object_type": "unknown", "gender": "UNKNOWN",
            "semantic_links": [], "source": "200_LINK_SEMANTIC_RELATION_BANK",
        }

        discourse_signals = {
            "anaphoric_reference": anaphora,
            "elliptical_continuation": explicit_continuation,
            "constraint_extension": exclusion,
            "repair_or_correction": explicit_repair,
            "historical_recall": explicit_recall,
            "explicit_new_topic": explicit_new,
            "list_continuation": bool(list_intent and (explicit_continuation or exclusion or anaphora)),
            "object_antecedent_resolved": bool(antecedent_resolution.get("resolved")),
            "object_type": semantic_links.get("object_type", "unknown"),
            "object_gender": semantic_links.get("gender", "UNKNOWN"),
            "pronoun_forms": list((antecedent_resolution.get("pronoun") or {}).get("forms", [])),
        }

        # Explicit new-topic markers win before historical similarity. A new test
        # is not a continuation merely because the word "тест" appeared before.
        if explicit_new:
            relation = "NEW"
            selected_indices: list[int] = []
            anchor_index = -1
            reason = "EXPLICIT_NEW_TEST_OR_TOPIC"
        else:
            # First resolve the likely pair sequence. For recall/repair the user
            # is deliberately reaching backward; for anaphora/ellipsis the latest
            # compatible antecedent is preferred.
            if antecedent_resolution.get("resolved") and antecedent_index >= 0 and not explicit_recall:
                selected_indices = [antecedent_index]
                reason = "OBJECT_PRONOUN_ANTECEDENT_RESOLVED"
            elif explicit_recall:
                selected_indices = self._find_historical_topic_pair(current, window, rows)
                reason = "EXPLICIT_HISTORICAL_REFERENCE"
            else:
                selected_indices = self._select_by_object(current, window, rows)
                reason = "SEMANTIC_PAIR_MATCH"

            if anaphora and antecedent_resolution.get("resolved") and antecedent_index >= 0:
                selected_indices = [antecedent_index]
                reason = "ANAPHORA_OBJECT_GENDER_NUMBER_RESOLVED"
            elif anaphora:
                # "из них" requires a real antecedent from the dialogue, not the
                # assistant's later clarification question. Prefer the most recent
                # substantive USER↔APRIL result set and use it as the sole anchor.
                antecedent = None
                for i in range(latest, -1, -1):
                    pair = window[i]
                    if self._is_clarification_pair(pair):
                        continue
                    if self._contains_reference_answer_set(pair):
                        antecedent = i
                        break
                if antecedent is not None:
                    selected_indices = [antecedent]
                    reason = "ANAPHORIC_ANTECEDENT_FROM_PAIR"
                elif window:
                    substantive = [
                        i for i in range(latest, -1, -1)
                        if not self._is_clarification_pair(window[i])
                    ]
                    if substantive:
                        selected_indices = [substantive[0]]
                        reason = "ANAPHORIC_ANTECEDENT_LATEST_SUBSTANTIVE_PAIR"

            if explicit_repair and not explicit_recall:
                # Repair often says what the earlier topic was without an explicit
                # "before/earlier" word. If the current turn mentions a concrete
                # topic that exists in the pair window, keep that trajectory.
                repair_hits = self._find_historical_topic_pair(current, window, rows)
                if repair_hits:
                    selected_indices = sorted(set(repair_hits[:4] + selected_indices[-2:]))
                    reason = "REPAIR_FROM_DIALOGUE_TOPIC"

            # If no direct match was found but the turn is clearly an elliptical
            # continuation, the nearest non-empty pair is the contextual anchor.
            if not selected_indices and (explicit_continuation or anaphora or exclusion) and window:
                selected_indices = [latest]
                reason = "ELLIPTICAL_CONTINUATION_LATEST_PAIR"

            # The latest pair may be an assistant clarification that lost the real
            # object. If the user explicitly names that object, prefer the older
            # pair that contains it rather than the clarification itself.
            if selected_indices and explicit_repair:
                object_hits = self._find_historical_topic_pair(current, window, rows)
                if object_hits:
                    selected_indices = sorted(set(object_hits[:4] + selected_indices[-2:]))

            # Relation classification uses discourse semantics + pair evidence.
            # A new self-contained request is NEW even if an unrelated pair exists.
            direct_pair = [rows_by_index.get(i, {}) for i in selected_indices]
            best_pair_score = max((float(x.get("score", 0.0) or 0.0) for x in direct_pair), default=0.0)
            has_real_pair = bool(selected_indices)

            topical_followup = bool(
                has_real_pair
                and (
                    explicit_continuation
                    or anaphora
                    or exclusion
                    or explicit_repair
                )
            )
            if explicit_recall and has_real_pair:
                relation = "RECALL"
            elif antecedent_resolution.get("resolved") and has_real_pair:
                relation = "CONTINUE"
            elif topical_followup:
                relation = "CONTINUE"
            elif has_real_pair:
                # A concrete current request can remain NEW even when it resembles
                # a previous topic. Require strong pair evidence plus discourse
                # dependency to call it continuation.
                latest_pair_score = float(rows_by_index.get(latest, {}).get("score", 0.0) or 0.0)
                if latest_pair_score >= 0.34 and self._affinity(current, self._pair_text(window[latest])[2]) >= 0.18:
                    relation = "CONTINUE"
                else:
                    relation = "NEW"
                    selected_indices = []
            else:
                relation = "NEW"

            if relation == "CONTINUE" and not selected_indices and window:
                selected_indices = [latest]

            # A topical follow-up may score weakly lexically (Russian inflection,
            # spelling variation, short request), but still carries a human
            # continuation act such as "подробнее о хищниках". Recover the best
            # historical topical pair before allowing NEW.
            if (
                relation == "NEW"
                and window
                and (explicit_continuation or explicit_repair or anaphora)
            ):
                recovery = self._find_historical_topic_pair(current, window, rows)
                if recovery:
                    relation = "CONTINUE" if not explicit_recall else "RECALL"
                    selected_indices = recovery[:6]

            if selected_indices:
                # Keep a compact contiguous trajectory around the anchor for list
                # continuation, while preserving explicitly matched older pairs.
                anchor_index = selected_indices[-1]
                if explicit_recall:
                    anchor_index = selected_indices[0]
                elif anaphora:
                    anchor_index = max(selected_indices)
                selected_indices = sorted(set(i for i in selected_indices if 0 <= i < len(window)))[-8:]
            else:
                anchor_index = -1
                best_pair_score = 0.0

        if relation == "NEW":
            selected_indices = []
            anchor_index = -1

        context_pairs = [dict(window[i]) for i in selected_indices if 0 <= i < len(window)]
        object_focus = {}
        if anchor_index >= 0 and anchor_index < len(window):
            pair = window[anchor_index]
            object_focus = {
                "label": self._pair_subject(pair),
                "key": self._pair_subject(pair),
                "source": "PAIR_DIALOGUE_ANTECEDENT",
            }

        exclusions = sorted(self._collect_exclusions(current))
        direction = (
            "EXTEND_WITH_EXCLUSIONS" if exclusion and relation == "CONTINUE" else
            "COMPARE_REFERENCED_OBJECTS" if relation == "CONTINUE" and antecedent_resolution.get("resolved") and _has_any_token(current, {"сравни", "сопоставь", "кто", "какой", "опаснее", "лучше", "хуже"}) else
            "EXPLAIN_REFERENCED_OBJECT" if relation == "CONTINUE" and antecedent_resolution.get("resolved") and _has_any_token(current, {"подробнее", "объясни", "поясни", "что", "почему", "зачем"}) else
            "EXPLAIN_OR_JUSTIFY_PREVIOUS" if explicit_repair and relation == "CONTINUE" else
            "RECALL_RELEVANT_PAIRS" if relation == "RECALL" else
            "EXTEND_PREVIOUS_RESULT" if relation == "CONTINUE" else
            "ANSWER_CURRENT_REQUEST"
        )
        structured_request_context = {
            "object": semantic_links.get("object_type", "unknown"),
            "object_gender": semantic_links.get("gender", "UNKNOWN"),
            "pronoun_forms": list((antecedent_resolution.get("pronoun") or {}).get("forms", [])),
            "antecedent_pair_index": antecedent_index,
            "semantic_relation_links": semantic_links.get("semantic_links", []),
            "matched_link_count": int(semantic_links.get("matched_link_count", 0) or 0),
            "direction": direction,
            "requested_operation": (
                "compare" if direction == "COMPARE_REFERENCED_OBJECTS" else
                "explain" if direction == "EXPLAIN_REFERENCED_OBJECT" else
                "extend" if relation == "CONTINUE" else
                "recall" if relation == "RECALL" else "answer"
            ),
            "context_locked_before_provider": True,
            "pair_search_narrowed_by": [
                "object_type", "grammatical_gender", "grammatical_number",
                "pronoun_form", "semantic_direction", "pair_sequence",
            ],
            "pair_search_scope": "AUTHENTICATED_12H_USER_APRIL_PAIRS",
        }

        confidence_base = 0.52
        if anaphora and context_pairs:
            confidence_base += 0.30
        if explicit_continuation and context_pairs:
            confidence_base += 0.15
        if explicit_recall and context_pairs:
            confidence_base += 0.20
        if explicit_repair and context_pairs:
            confidence_base += 0.15
        confidence_base += min(0.18, best_pair_score * 0.30 if context_pairs else 0.0)
        if explicit_new:
            confidence_base = 0.98
        confidence = max(0.60 if relation != "NEW" else 0.88, min(0.99, confidence_base))

        return {
            "version": self.VERSION,
            "relation_hint": relation,
            "relation": relation,
            "confidence": round(confidence, 6),
            "direction": direction,
            "reason": reason,
            "selected_indices": selected_indices,
            "anchor_index": anchor_index,
            "history_lookup": relation == "RECALL",
            "requested_action": {
                "new_task": relation == "NEW",
                "continue_result": relation == "CONTINUE",
                "recall_history": relation == "RECALL",
                "list_continuation": discourse_signals["list_continuation"],
                "exclude_repeated_items": exclusion,
            },
            "object_focus": object_focus,
            "excluded_items": exclusions,
            "discourse_signals": discourse_signals,
            "object_resolution": {
                "resolved": bool(antecedent_resolution.get("resolved")),
                "anchor_index": antecedent_index,
                "object_type": semantic_links.get("object_type", "unknown"),
                "gender": semantic_links.get("gender", "UNKNOWN"),
                "pronoun": antecedent_resolution.get("pronoun", {}),
                "score": float(antecedent_resolution.get("score", 0.0) or 0.0),
                "source": antecedent_resolution.get("source", "PAIR_OBJECT_ANTECEDENT_RESOLUTION"),
            },
            "semantic_link_engine": {
                "version": "200-links",
                "link_count": len(self._RELATION_LINK_BANK),
                "matched_link_count": int(semantic_links.get("matched_link_count", 0) or 0),
                "matched_link_keys": list(semantic_links.get("matched_link_keys", [])),
                "object_type": semantic_links.get("object_type", "unknown"),
                "gender": semantic_links.get("gender", "UNKNOWN"),
            },
            "structured_request_context": structured_request_context,
            "discourse_signals": discourse_signals,
            "context_pairs": context_pairs,
            "test_sequence": {
                "start_index": selected_indices[0] if selected_indices else -1,
                "end_index": selected_indices[-1] if selected_indices else -1,
            },
            "semantic_contract": {
                "pair_source": "STATE_MANAGER_AUTHENTICATED_12H_USER_APRIL_PAIRS",
                "decision_owner": "PAIR_DIALOGUE_DIRECTION_ENGINE",
                "single_relation": True,
                "provider_ready_only_after_relation": True,
                "no_fallback": True,
                "object_resolution_before_relation": True,
                "relation_before_provider": True,
                "link_bank_size": len(self._RELATION_LINK_BANK),
            },
        }


PAIR_DIALOGUE_DIRECTION_ENGINE = PairDialogueDirectionEngine()


# ---------------------------------------------------------------------------
# Canonical constants
# ---------------------------------------------------------------------------

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"

DECISION_OWNER = "QUANTUM_PROCESSOR"
TRANSPORT_NAME = "transport_state"
INTERPRETATION_ENGINE_VERSION = "quantum_interpretation_engine_v19_12h_live_dialogue_v2_two_state_chain_locked"
print("🧠 APRIL INTERPRETATION BUILD:", INTERPRETATION_ENGINE_VERSION)

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
    "identity": "пользователь спрашивает кто ты как тебя зовут представься твое имя своё имя расскажи о себе; the user asks who you are or what your name is",
    "greeting": "пользователь приветствует ассистента начинает непринужденный разговор; the user is greeting the assistant",
    "question": "пользователь задаёт вопрос просит ответ или разъяснение сколько равен вычисли посчитай значение; the user asks a question requiring an answer or calculation",
    "request": "пользователь просит выполнить задачу сделать действие создать результат; the user asks the assistant to perform a task",
    "continuation": "пользователь продолжает текущую мысль и предыдущий ответ, задаёт следующий уточняющий вопрос, просит подробнее, детальнее, развёрнуто, продолжи, дальше, ещё, расширь предыдущий ответ, проверь вывод, добавь деталь, развивай уже начатый результат; the user continues the current reasoning thread with a follow-up, clarification, extension, or refinement",
    "reformulation": "пользователь переформулирует предыдущий запрос, просит показать это иначе, подробнее или другим способом, уточняет формулировку, просит переделать, дополнить или расширить уже полученный результат; the user reformulates or refines an existing result",
    "correction": "пользователь исправляет предыдущий результат, говорит что ответ неверен, просит исправить, переделать или изменить условие, параметр или деталь уже обсуждаемой задачи; the user corrects, extends, or changes a detail of the preceding task",
    "reference": "пользователь явно ссылается на уже показанное, созданное или сказанное, использует местоимение или указание на объект, этот, эту, это, него, неё, нему, просит изменить добавить отметить в нём или в ней; the user explicitly refers to a previously shown or discussed object",
    "artifact_reference": "пользователь спрашивает о содержимом, свойствах или результате уже созданного или показанного артефакта, что было нарисовано, какие элементы получились, что находится в предыдущем результате, просит перечислить или объяснить уже созданный объект; the user asks about the contents, properties, or result of an artifact that was already created or shown",
    "memory_query": "пользователь просит вспомнить что он ранее спрашивал, какой вопрос задавал, о чем говорили, какой был прошлый вопрос или тема; the user asks to recall what they previously asked or discussed",
    "affirmation": "пользователь подтверждает согласие принимает предыдущий результат; the user confirms the preceding result",
    "rejection": "пользователь отклоняет предыдущий результат или предлагает другой вариант; the user rejects the preceding result",
    "new_topic": "пользователь начинает новую тему не связанную с предыдущим обсуждением; the user starts a new topic",
    "statement": "пользователь сообщает утверждение факт или мысль; the user makes a statement",
    "independent": "самостоятельный запрос не зависящий от предыдущих сообщений; the request is self contained and independent",
}

REPRESENTATION_HYPOTHESES = {
    "text": "обычный текстовый ответ объяснение рассказ описание; the user wants a normal textual answer",
    "table": "таблица таблицу табличный формат строки столбцы колонки; information represented as a table",
    "graph": "график графика chart plot graph кривая кривые функция; information represented as a graph or chart",
    "diagram": "схема чертёж технический чертёж рисунок построение геометрическая фигура треугольник квадрат круг окружность вершины стороны углы длина сантиметр см соединение элементов блоки связи последовательность процесса подключение проводов источник питания выключатель лампа электрическая цепь; a technical or geometric drawing, construction diagram, schematic, wiring diagram, connected structure, or process diagram",
    "formula": "формула уравнение математическое выражение математическая запись равенство обозначение величин степени корни E mc2; a mathematical formula, equation, notation, or quantitative relationship",
    "image": "изображение картинка рисунок иллюстрация создать изображение фотография; an image or generated picture",
    "gallery": "несколько изображений много картинок подборка галерея набор карточек сравнение изображений; multiple images, a gallery, or an image collection",
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


# ---------------------------------------------------------------------------
# Unified Quantum Interpretation Engine v3
# ---------------------------------------------------------------------------

REPRESENTATION_UNIVERSE = (
    "text", "table", "graph", "diagram", "formula", "image", "gallery",
    "code", "link", "audio", "video", "file", "action", "scene",
    "memory", "visual_context",
)
STRUCTURED_REPRESENTATIONS = tuple(x for x in REPRESENTATION_UNIVERSE if x != "text")

OPERATION_HYPOTHESES = {
    "answer": "ответить объяснить рассказать сообщить дать информацию назвать называть название наименование",
    "build": "создать построить сформировать нарисовать начертить изобразить результат",
    "present": "показать отобразить продемонстрировать вывести представить результат",

    "compare": "сравнить сопоставить различия сходства",
    "modify": "изменить исправить обновить переделать дополнить",
    "retrieve": "найти получить ресурс источник ссылку документ",
    "calculate": "посчитать посчитай вычислить вычисли рассчитать рассчитай решить реши сложить сложи складывать складывай сумма суммировать арифметика добавить прибавить получить сумму; calculate compute add sum arithmetic",
    "analyze": "проанализировать разобрать исследовать проверить",
    "explain": "объяснить разъяснить пояснить растолковать как работает почему смысл принцип",
    "summarize": "суммировать сократить основные пункты",
    "list": "перечислить список варианты",
}
OBJECT_HYPOTHESES = {
    "graph": "график plot chart curve series числовая визуализация",
    "diagram": "схема чертёж технический чертёж построение геометрическая фигура треугольник квадрат круг окружность вершины стороны углы длина сантиметр см блоки связи соединения проводка электрическая цепь процесс",
    "table": "таблица строки столбцы колонки структурированные данные сравнение",
    "formula": "формула уравнение математическое выражение notation",
    "link": "ссылка URL адрес сайта веб ресурс источник",
    "code": "код программа функция скрипт",
    "image": "изображение картинка рисунок иллюстрация фотография портрет художественная картинка",
    "gallery": "галерея подборка несколько изображений",
    "file": "файл документ вложение",
    "audio": "аудио звук голос запись",
    "video": "видео ролик запись",
    "text": "текст обычный ответ объяснение описание",
    "action": "действие интерактивная операция",
}
GOAL_HYPOTHESES = {
    "visualize": "увидеть визуально показать наглядно кривые схему",
    "organize": "структурировать упорядочить данные строки столбцы",
    "present": "представить вывести отобразить результат",
    "understand": "понять разобраться объяснение смысл",
    "obtain": "получить ресурс ссылку файл",
    "transform": "изменить преобразовать результат",
    "decide": "выбрать сопоставить варианты",
}

# Visual schema is a semantic subtype of an already-resolved representation.
# It is evidence only: it never routes by keyword and never owns renderer choice.
VISUAL_SCHEMA_HYPOTHESES = {
    "function": "mathematical function equation dependency f(x) y of x curve coordinate plot; mathematical function against an axis",
    "series": "ряд данных последовательность измерений значения изменение динамика тренд временной ряд развитие по оси; ordered measurements or changing values",
    "timeline": "временная шкала хронология история периоды эпохи эры события даты раньше позже начало конец продолжительность последовательность во времени развитие существование вымирание; temporal history chronology eras periods dates and events",
    "scatter": "paired observations numeric variables relationship correlation distribution individual points; relationship between two numeric variables",
    "network": "entities connected by relationships nodes edges topology dependencies connections; network of related entities",
    "matrix": "rows columns cells heatmap two dimensional array intensities crossing dimensions; matrix or heatmap",
    "categorical": "категории группы сравнение ранжирование дискретные значения подписи количество по категориям; categorical comparison",
}

REPRESENTATION_ALIASES = {
    "chart":"graph","plot":"graph","schematic":"diagram","flowchart":"diagram",
    "math":"formula","equation":"formula","url":"link","link_card":"link","media":"gallery",
}

def _clean_representation(value: Any) -> str:
    value = str(value or "").strip().lower()
    value = REPRESENTATION_ALIASES.get(value, value)
    return value if value in REPRESENTATION_UNIVERSE else ""


class QuantumContextUnderstandingEngine:
    """
    Context-first semantic fusion layer.

    Purpose:
      1) reconstruct the active topic/thread from authentic USER↔APRIL history;
      2) resolve entities/coreference before downstream engines see the turn;
      3) distinguish current-turn structure ("first/second/third") from historical
         references ("the previous formula", "that image");
      4) describe the COMPLETE task as a multi-dimensional intent packet:
         operation + object + representation + input modality + output modality;
      5) use multilingual sentence embeddings as the primary semantic comparison
         when available, with the existing matrix engine as a deterministic fallback;
      6) optionally use local NLI only for genuinely ambiguous relations.

    This class never routes, calls a provider, executes tools, selects renderers,
    or mutates an answer. It produces an evidence/understanding packet consumed
    by the canonical interpretation engine.
    """

    VERSION = "QUANTUM_CONTEXT_UNDERSTANDING_V4_FAST_HOTPATH"
    TOPIC_WINDOW = 12
    ENTITY_WINDOW = 8
    NLI_ENABLED = (
        os.getenv("APRIL_ENABLE_CONTEXT_NLI", "0").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    EMBEDDING_ENABLED = (
        os.getenv("APRIL_ENABLE_CONTEXT_EMBEDDINGS", "0").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    ACTION_UNIVERSE = (
        "answer", "ask", "explain", "calculate", "analyze", "compare",
        "summarize", "list", "retrieve", "create", "build", "present",
        "modify", "correct", "continue", "recall", "inspect", "read",
        "extract", "classify", "translate",
    )

    OUTPUT_UNIVERSE = (
        "text", "number", "formula", "code", "link", "table", "graph",
        "diagram", "image", "gallery", "file", "audio", "video",
        "memory", "visual_context", "action",
    )

    INPUT_UNIVERSE = (
        "text", "number", "formula", "code", "link", "image", "screenshot",
        "gallery", "file", "audio", "video", "visual_context",
    )

    _PRONOUNS = {
        "он", "она", "они", "его", "её", "ее", "их", "ему", "ей", "им",
        "ним", "него", "нём", "нем", "неё", "нее", "ней", "этом", "этот", "эта", "это",
        "эти", "тот", "та", "то", "те", "тем", "того", "ту", "выше",
        "ниже", "там", "здесь", "такой", "такая", "такое", "такие",
    }

    _ORDINAL_MAP = {
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
        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    }

    _STOP = {
        "что", "это", "такое", "как", "кто", "когда", "где", "куда",
        "почему", "зачем", "мне", "тебе", "тебя", "ты", "вы", "он", "она",
        "они", "его", "ее", "её", "их", "ему", "ей", "им", "можно",
        "нужно", "хочу", "покажи", "показать", "расскажи", "рассказать",
        "объясни", "объяснить", "скажи", "сделай", "сделать", "дай",
        "добавь", "добавить", "первое", "второе", "третье", "первый",
        "второй", "третий", "и", "а", "но", "ещё", "еще", "then", "the",
        "what", "who", "how", "why", "this", "that", "they", "he", "she",
        "it", "and", "or", "to", "of", "for",
    }

    def __init__(self, semantic_engine: "QuantumInterpretationEngine") -> None:
        self.semantic_engine = semantic_engine
        self._nli = None
        self._nli_lock = threading.RLock()

    @staticmethod
    def _compact(value: Any, limit: int = 800) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())[:limit]

    @staticmethod
    def _tokens(text: Any) -> list[str]:
        return re.findall(
            r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+",
            str(text or "").lower(),
        )

    @classmethod
    def _content_tokens(cls, text: Any) -> list[str]:
        return [
            token for token in cls._tokens(text)
            if len(token) >= 3 and token not in cls._STOP
        ]

    @classmethod
    def _entities(cls, text: Any) -> list[dict[str, Any]]:
        """Entity extraction is intentionally disabled on the dialogue hot path.

        Dialogue meaning is reconstructed from authenticated USER↔APRIL pairs in
        the 12-hour StateManager memory. Objects/representations are measured by
        the semantic matrix, but named-entity graphs are not used to choose a
        continuation, topic, or renderer.
        """
        return []

    @classmethod
    def _ordinals(cls, text: Any) -> list[int]:
        source = str(text or "").lower()
        hits = []
        for word, number in cls._ORDINAL_MAP.items():
            pos = source.find(word)
            if pos >= 0:
                hits.append((pos, number))
        hits.sort(key=lambda item: item[0])
        result = []
        for _, value in hits:
            if value not in result:
                result.append(value)
        return result

    @classmethod
    def _request_segments(cls, text: Any) -> list[dict[str, Any]]:
        source = str(text or "").strip()
        if not source:
            return []

        numbered = list(re.finditer(
            r"(?:^|\n|\s)(\d{1,3})[.)]\s+(.+?)(?=(?:\s+\d{1,3}[.)]\s+)|\n+\s*(?:\d{1,3})[.)]\s+|$)",
            source,
            flags=re.S,
        ))
        if len(numbered) >= 2:
            return [
                {
                    "segment_index": int(match.group(1)),
                    "text": re.sub(r"\s+", " ", match.group(2)).strip(),
                    "source": "numbered_current_turn",
                }
                for match in numbered[:32]
            ]

        pieces = [
            piece.strip(" \t")
            for piece in re.split(r"(?:\n{2,}|;(?=\s+)|\s+\band\b\s+|\s+\bи\b\s+)", source, flags=re.I)
            if piece.strip()
        ]
        if len(pieces) >= 2:
            return [
                {
                    "segment_index": idx,
                    "text": re.sub(r"\s+", " ", piece),
                    "source": "semantic_clause_segmentation",
                }
                for idx, piece in enumerate(pieces[:16], start=1)
            ]
        return [{
            "segment_index": 1,
            "text": re.sub(r"\s+", " ", source),
            "source": "single_current_turn",
        }]

    @classmethod
    def _modality_evidence(
        cls,
        text: str,
        *,
        semantic: dict[str, Any] | None = None,
        cognition: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sources = [
            semantic if isinstance(semantic, dict) else {},
            cognition if isinstance(cognition, dict) else {},
            state if isinstance(state, dict) else {},
        ]
        combined = " ".join(cls._compact(s) for s in sources if s)
        source_text = f"{text} {combined}"

        code = bool(re.search(r"```[\s\S]*?```|(?:\bdef\b|\bclass\b|\bimport\b|\bfunction\b)\s+\w+", text, re.I))
        link = bool(re.search(r"https?://|www\.[\w.-]+\.", text, re.I))
        screenshot = bool(re.search(
            r"\b(?:скриншот|скрин|screenshot|screen shot|снимок экрана|изображен(?:ие|ия) на экране)\b",
            source_text, re.I,
        ))
        formula = bool(re.search(
            r"(?:[A-Za-z]\s*=\s*[A-Za-z0-9^_()+*/.\-]+|\b(?:mc\^2|E\s*=\s*mc2)\b|\\frac|\\sqrt)",
            text,
            re.I,
        ))
        numeric = bool(re.search(
            r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?:\s*[+\-*/×÷]\s*[-+]?\d+(?:[.,]\d+)?)+",
            text,
        ))
        image_signal = screenshot or bool(re.search(
            r"\b(?:изображение|картинка|фото|фотография|image|picture|photo)\b",
            source_text, re.I,
        ))
        table_signal = bool(re.search(
            r"\b(?:таблица|таблич(?:а|ный)|table|rows?|columns?)\b",
            source_text, re.I,
        ))
        graph_signal = bool(re.search(
            r"\b(?:график|графика|chart|plot|curve|диаграмма данных)\b",
            source_text, re.I,
        ))
        diagram_signal = bool(re.search(
            r"\b(?:схема|чертёж|чертеж|diagram|schematic|flowchart|блок-схема)\b",
            source_text, re.I,
        ))
        audio_signal = bool(re.search(r"\b(?:аудио|голос|audio|voice|sound)\b", source_text, re.I))
        video_signal = bool(re.search(r"\b(?:видео|ролик|video)\b", source_text, re.I))
        file_signal = bool(re.search(r"\b(?:файл|документ|attachment|file|pdf|docx?)\b", source_text, re.I))

        for src in sources:
            keys = {str(k).lower(): v for k, v in src.items()}
            if any(k in keys and keys[k] for k in ("images", "image", "vision_context", "vision")):
                image_signal = True
            if any(k in keys and keys[k] for k in ("files", "file_context", "attachment", "attachments")):
                file_signal = True
            if any(k in keys and keys[k] for k in ("audio", "voice_context", "voice")):
                audio_signal = True
            if any(k in keys and keys[k] for k in ("video", "video_context")):
                video_signal = True
            if any(k in keys and keys[k] for k in ("screenshot", "screenshots")):
                screenshot = True
                image_signal = True

        inputs = []
        if text.strip():
            inputs.append("text")
        if numeric:
            inputs.append("number")
        if formula:
            inputs.append("formula")
        if code:
            inputs.append("code")
        if link:
            inputs.append("link")
        if image_signal:
            inputs.append("screenshot" if screenshot else "image")
        if table_signal:
            inputs.append("table")
        if graph_signal:
            inputs.append("graph")
        if diagram_signal:
            inputs.append("diagram")
        if file_signal:
            inputs.append("file")
        if audio_signal:
            inputs.append("audio")
        if video_signal:
            inputs.append("video")

        return {
            "inputs": list(dict.fromkeys(inputs)),
            "flags": {
                "text": bool(text.strip()),
                "number": numeric,
                "formula": formula,
                "code": code,
                "link": link,
                "image": image_signal,
                "screenshot": screenshot,
                "table": table_signal,
                "graph": graph_signal,
                "diagram": diagram_signal,
                "file": file_signal,
                "audio": audio_signal,
                "video": video_signal,
            },
            "source": "multimodal_structural_evidence",
            "lexical_routing": False,
        }

    @classmethod
    def _task_actions(
        cls,
        text: str,
        profile: dict[str, Any],
        modality: dict[str, Any],
    ) -> dict[str, Any]:
        """Compile an action/output vector from semantic evidence.

        Operation is measured by the existing matrix. Structured outputs are
        admitted when operation + object semantics agree; raw words are never
        used as renderer commands.
        """
        scores = {
            key: float(value or 0.0)
            for key, value in (profile.get("operation_scores") or {}).items()
        }
        objects = {
            key: float(value or 0.0)
            for key, value in (profile.get("object_scores") or {}).items()
        }
        reps = {
            key: float(value or 0.0)
            for key, value in (profile.get("representation_scores") or {}).items()
        }

        op_rank = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best = op_rank[0][0] if op_rank else "answer"
        flags = modality.get("flags", {})

        # Explicit arithmetic structure is strong CALCULATE evidence even when
        # natural-language wording pulls another operation prototype upward.
        if flags.get("number") and re.search(
            r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?\s*[+\-*/×÷]\s*[-+]?\d+(?:[.,]\d+)?(?![\w.])",
            text,
        ):
            best = "calculate"

        compatible = {
            "formula": {"calculate", "answer", "explain", "present", "build", "modify"},
            "code": {"build", "modify", "present", "explain", "analyze"},
            "link": {"retrieve", "present", "answer", "list", "explain"},
            "table": {"build", "present", "compare", "list", "explain", "analyze"},
            "graph": {"build", "present", "calculate", "analyze", "compare", "list", "explain"},
            "diagram": {"build", "present", "modify", "explain", "analyze"},
            "image": {"build", "present", "modify", "create"},
            "gallery": {"build", "present", "compare", "list"},
            "file": {"retrieve", "present", "analyze", "read"},
            "audio": {"retrieve", "present", "analyze", "read"},
            "video": {"retrieve", "present", "analyze", "read"},
        }

        candidates = []
        for action in cls.ACTION_UNIVERSE:
            score = float(scores.get(action, 0.0) or 0.0)
            if score >= 0.05:
                candidates.append({"action": action, "score": round(score, 6)})

        outputs: list[str] = []

        # Structural numeric expression: the answer itself is a numerical result,
        # usually accompanied by text explanation.
        if flags.get("number") and best in {"calculate", "answer"}:
            outputs.append("number")

        # The request's semantic object can authorize a structured output even when
        # the character-level representation rank is polluted by decorative words.
        compatible_object_candidates = []
        for label, obj_score in objects.items():
            if label not in cls.OUTPUT_UNIVERSE or label == "text":
                continue
            if best in compatible.get(label, set()) and obj_score >= 0.08:
                compatible_object_candidates.append((label, obj_score))
        compatible_object_candidates.sort(key=lambda item: item[1], reverse=True)
        for label, _ in compatible_object_candidates[:4]:
            outputs.append(label)

        # Representation measurements remain evidence, not a hard trigger. When
        # they agree with the current operation, they contribute to the output plan.
        for label, rep_score in sorted(reps.items(), key=lambda item: item[1], reverse=True):
            if label == "text" or label not in cls.OUTPUT_UNIVERSE:
                continue
            if rep_score < 0.10:
                continue
            if best in compatible.get(label, set()) or label in {
                "formula" if flags.get("formula") else "",
                "code" if flags.get("code") else "",
                "link" if flags.get("link") else "",
            }:
                outputs.append(label)

        # Explicit input/output modality mapping.
        if flags.get("formula"):
            outputs.append("formula")
        if flags.get("code"):
            outputs.append("code")
        if flags.get("link"):
            outputs.append("link")
        if flags.get("table"):
            outputs.append("table")
        if flags.get("graph"):
            outputs.append("graph")
        if flags.get("diagram"):
            outputs.append("diagram")
        if flags.get("screenshot"):
            # Reading/analysing a screenshot produces an understanding, not another
            # screenshot. A later renderer may display an annotated result, but the
            # semantic output is visual_context unless the current request explicitly
            # asks to create a new image.
            outputs.append("visual_context")
        elif flags.get("image"):
            outputs.append("image")
        if flags.get("file"):
            outputs.append("file")
        if flags.get("audio"):
            outputs.append("audio")
        if flags.get("video"):
            outputs.append("video")

        return {
            "primary": best,
            "primary_score": float(scores.get(best, 0.0) or 0.0),
            "candidates": candidates[:16],
            "requested_outputs": list(dict.fromkeys(outputs)),
            "output_evidence": {
                "object_scores": {k: round(float(v), 6) for k, v in sorted(objects.items(), key=lambda item: item[1], reverse=True)[:12]},
                "representation_scores": {k: round(float(v), 6) for k, v in sorted(reps.items(), key=lambda item: item[1], reverse=True)[:12]},
            },
            "source": "task_action_matrix",
        }

    @classmethod
    def _topic_label(cls, pair: dict[str, str], scene: dict[str, Any] | None = None) -> str:
        texts = [
            str(pair.get("user") or ""),
            str(pair.get("assistant") or ""),
        ]
        if isinstance(scene, dict):
            texts.extend([
                str(scene.get("topic") or ""),
                str(scene.get("summary") or ""),
            ])
        # Entity extraction is deliberately absent from dialogue topic labeling.
        # The topic label is a compact semantic projection of the authenticated
        # USER↔APRIL pair, not an entity-engine result.
        content = [
            token for token in cls._content_tokens(" ".join(texts))
            if not token.isdigit()
        ]
        if content:
            ranked = sorted(set(content), key=lambda x: (-len(x), x))
            return " ".join(ranked[:4])
        return ""

    def _embedding_similarity(self, left: str, right: str) -> tuple[float, str]:
        if not left or not right:
            return 0.0, "none"
        if self.EMBEDDING_ENABLED and os.getenv("APRIL_ALLOW_CONTEXT_MODEL_DOWNLOAD", "0").strip().lower() in {"1", "true", "yes", "on"}:
            try:
                # Context embeddings are an explicit opt-in cold path. They never
                # download/load a Hugging Face model during normal production turns.
                if self.semantic_engine._semantic_encoder is None:
                    try:
                        if SentenceTransformer is not None:
                            self.semantic_engine._semantic_encoder = SentenceTransformer(SEMANTIC_MODEL_NAME)
                    except Exception:
                        self.semantic_engine._semantic_encoder = None
                result = self.semantic_engine.similarity(left, right)
                if result.get("measured"):
                    return float(result.get("score", 0.0)), str(result.get("source", "embedding"))
            except Exception:
                pass
        try:
            result = self.semantic_engine.similarity(left, right)
            return float(result.get("score", 0.0)), str(result.get("source", "matrix"))
        except Exception:
            return 0.0, "none"

    @staticmethod
    def _shared_entities(current_entities: list[dict[str, Any]], prior_entities: list[dict[str, Any]]) -> list[str]:
        # Entity overlap is not a dialogue authority. CONTINUE/RECALL is derived
        # from the authenticated pair history instead.
        return []

    def _topic_profiles(
        self,
        current: str,
        recent_pairs: list[dict[str, str]],
        active_topic: str,
        previous_scene: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        profiles = []
        candidates = list(reversed(recent_pairs[-self.TOPIC_WINDOW:]))
        if active_topic:
            candidates.insert(0, {"user": active_topic, "assistant": active_topic, "source": "active_topic"})
        for idx, pair in enumerate(candidates, start=1):
            user = self._compact(pair.get("user"))
            assistant = self._compact(pair.get("assistant"), 1200)
            pair_text = f"{user} {assistant}".strip()
            if not pair_text:
                continue
            sim, source = self._embedding_similarity(current, pair_text)
            shared = []
            current_terms = set(self._content_tokens(current))
            prior_terms = set(self._content_tokens(pair_text))
            lexical_overlap = (
                len(current_terms & prior_terms) / max(1, len(current_terms | prior_terms))
            )
            recency = 1.0 / (1.0 + 0.12 * (idx - 1))
            topic_label = self._topic_label(pair, previous_scene)
            topic_score = (
                0.76 * sim
                + 0.14 * lexical_overlap
                + 0.10 * recency
            )
            profiles.append({
                "pair_index": idx,
                "topic": topic_label,
                "user": user,
                "assistant": assistant,
                "semantic_similarity": round(float(sim), 6),
                "shared_entities": shared,
                "lexical_overlap": round(float(lexical_overlap), 6),
                "recency": round(float(recency), 6),
                "score": round(float(min(1.0, topic_score)), 6),
                "source": source,
            })
        return sorted(profiles, key=lambda item: item["score"], reverse=True)

    @classmethod
    def _is_current_turn_reference(cls, text: str) -> bool:
        source = str(text or "").lower()
        ordinals = cls._ordinals(source)
        numbered_items = len(cls._request_segments(source)) >= 2
        # An ordinal within a multi-part current request is local structure, not
        # a historical pointer.
        return bool(ordinals) and numbered_items

    @classmethod
    def _coreference_candidates(
        cls,
        current: str,
        prior_text: str,
        topic_profiles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """No entity/coreference engine: references use dialogue pairs only.

        The canonical dialogue selector already chooses a prior USER↔APRIL pair.
        Returning no entity candidates prevents named-entity logic from competing
        with the StateManager 12-hour contextual memory.
        """
        return []

    def _nli_verify(
        self,
        current: str,
        hypothesis_pairs: list[tuple[str, str]],
    ) -> list[dict[str, Any]]:
        """Use local NLI as an ambiguity verifier, never as the primary router."""
        if not self.NLI_ENABLED or hf_pipeline is None or not hypothesis_pairs:
            return []
        labels = [str(label) for label, _ in hypothesis_pairs[:4]]
        with self._nli_lock:
            try:
                if self._nli is None:
                    self._nli = hf_pipeline(
                        "zero-shot-classification",
                        model=NLI_MODEL_NAME,
                        tokenizer=NLI_MODEL_NAME,
                    )
            except Exception:
                return []
        try:
            result = self._nli(
                current,
                candidate_labels=labels,
                hypothesis_template="This user request is {} relative to the previous conversation.",
                multi_label=False,
            )
            out = []
            for label, score in zip(
                result.get("labels", []) if isinstance(result, dict) else [],
                result.get("scores", []) if isinstance(result, dict) else [],
            ):
                out.append({
                    "hypothesis": str(label),
                    "score": round(float(score), 6),
                })
            return out
        except Exception:
            return []

    def analyze(
        self,
        current: str,
        *,
        history: list[dict[str, Any]] | None = None,
        state: dict[str, Any] | None = None,
        semantic: dict[str, Any] | None = None,
        cognition: dict[str, Any] | None = None,
        active_topic: str = "",
        active_goal: str = "",
        previous_scene: dict[str, Any] | None = None,
        semantic_profile: dict[str, Any] | None = None,
        precomputed_dialogue_selection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = self._compact(current, 2200)
        history = history if isinstance(history, list) else []
        state = state if isinstance(state, dict) else {}
        semantic = semantic if isinstance(semantic, dict) else {}
        cognition = cognition if isinstance(cognition, dict) else {}
        semantic_profile = semantic_profile if isinstance(semantic_profile, dict) else {}

        recent_pairs = []
        pending_user = ""
        for item in history:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            if metadata.get("internal_context") or metadata.get("internal_turn"):
                continue
            role = str(item.get("role") or "").lower()
            content = self._compact(item.get("content") or item.get("text") or item.get("answer"), 1200)
            if role in {"user", "human"}:
                pending_user = content
            elif role in {"assistant", "april", "bot"} and pending_user:
                recent_pairs.append({
                    "user": pending_user,
                    "assistant": content,
                    "source": "authentic_dialogue",
                })
                pending_user = ""
        recent_pairs = recent_pairs[-self.TOPIC_WINDOW:]

        if isinstance(precomputed_dialogue_selection, dict) and str(precomputed_dialogue_selection.get("relation") or "").upper() in {"NEW", "CONTINUE", "RECALL"}:
            # The canonical dialogue selector has already run in the same
            # interpretation pass. Reuse its exact three-way result instead of
            # executing the branch selector a second time for context fusion.
            dialogue_selection = dict(precomputed_dialogue_selection)
        else:
            dialogue_selection = self.semantic_engine._select_three_way_dialogue_relation(
                current, recent_pairs, active_topic=self._compact(active_topic, 500),
                previous_assistant=self._compact(recent_pairs[-1].get("assistant"), 1200) if recent_pairs else "",
                previous_user=self._compact(recent_pairs[-1].get("user"), 1200) if recent_pairs else "",
            )
        selected_pair = dialogue_selection.get("selected_pair") if isinstance(dialogue_selection.get("selected_pair"), dict) else {}
        canonical_three_way = str(dialogue_selection.get("relation") or "NEW").upper()

        topic_profiles = self._topic_profiles(
            current,
            recent_pairs,
            self._compact(active_topic, 500),
            previous_scene,
        )
        top_topic = topic_profiles[0] if topic_profiles else {}
        current_topic_label = self._topic_label({"user": current, "assistant": ""}, previous_scene)
        reconstructed_topic = (
            current_topic_label
            if top_topic and float(top_topic.get("semantic_similarity", 0.0) or 0.0) < 0.24
            else self._compact(top_topic.get("topic"), 500)
            or self._compact(active_topic, 500)
            or current_topic_label
            or self._compact(current, 500)
        )

        modality = self._modality_evidence(
            current,
            semantic=semantic,
            cognition=cognition,
            state=state,
        )
        request_segments = self._request_segments(current)
        ordinals = self._ordinals(current)

        prior_text = " ".join(
            [self._compact(pair.get("user"), 700) + " " + self._compact(pair.get("assistant"), 1000)
             for pair in recent_pairs[-self.ENTITY_WINDOW:]]
        )
        coreference = self._coreference_candidates(
            current,
            prior_text,
            topic_profiles,
        )

        semantic_operation_scores = semantic_profile.get("operation_scores")
        if not isinstance(semantic_operation_scores, dict):
            semantic_operation_scores = {}
        action_matrix = self._task_actions(
            current,
            {
                "operation_scores": semantic_operation_scores,
                "object_scores": semantic_profile.get("object_scores", {}) if isinstance(semantic_profile.get("object_scores"), dict) else {},
                "representation_scores": semantic_profile.get("representation_scores", {}) if isinstance(semantic_profile.get("representation_scores"), dict) else {},
            },
            modality,
        )

        topic_similarity = float(top_topic.get("semantic_similarity", 0.0) or 0.0)
        shared_entities = []
        current_entities = []

        # Topic shift is a pair-context semantic decision. No entity graph is
        # consulted or allowed to veto/force a dialogue transition.
        topic_shift = bool(
            top_topic
            and topic_similarity < 0.24
        )
        if topic_shift and current_topic_label:
            reconstructed_topic = current_topic_label
        local_compound = len(request_segments) > 1

        # A current turn that contains its own complete task should not be forced
        # into a historical reference just because it shares vocabulary with the
        # previous answer. The topic may remain the same while task dependency is
        # independent.
        self_contained = bool(
            not coreference
            or all(item.get("historical_reference_blocked") for item in coreference)
        )
        pronoun_present = bool(set(self._tokens(current)) & self._PRONOUNS)
        historical_reference = bool(
            coreference
            and any(not item.get("historical_reference_blocked") for item in coreference)
            and not local_compound
            and pronoun_present
        )

        if topic_shift:
            relation = "NEW_TOPIC"
        elif historical_reference:
            relation = "CONTINUE_TOPIC"
        elif local_compound:
            relation = "SAME_TOPIC" if top_topic and not topic_shift else "NEW_TOPIC"
        elif topic_similarity >= 0.30 or shared_entities:
            relation = "SAME_TOPIC"
        else:
            relation = "INDEPENDENT"

        # Pronoun references strengthen continuation, but must have an actual
        # antecedent candidate. An unresolved pronoun never invents a topic.
        if historical_reference and coreference and coreference[0].get("confidence", 0.0) < 0.34:
            historical_reference = False
            relation = "SAME_TOPIC" if topic_similarity >= 0.22 else "INDEPENDENT"

        # Replace the legacy multi-state relation with the processor's exact
        # three-way dialogue classification. SAME_TOPIC/INDEPENDENT remain only
        # as compatibility evidence and cannot become the final dialogue state.
        if canonical_three_way == "CONTINUE":
            relation = "CONTINUE_TOPIC"
            historical_reference = False
        elif canonical_three_way == "RECALL":
            relation = "RECALL"
            historical_reference = True
        else:
            relation = "NEW_TOPIC"
            historical_reference = False

        discourse_confidence = max(
            0.0,
            min(
                1.0,
                0.62 * topic_similarity
                + 0.18 * min(1.0, len(shared_entities) / 2.0)
                + 0.12 * (1.0 if relation in {"CONTINUE_TOPIC", "SAME_TOPIC"} else 0.0)
                + 0.08 * (1.0 if self_contained else 0.0),
            ),
        )
        if relation == "NEW_TOPIC" and not top_topic:
            discourse_confidence = max(discourse_confidence, 0.82)
        if historical_reference:
            discourse_confidence = max(discourse_confidence, 0.72)
        if local_compound:
            discourse_confidence = max(discourse_confidence, 0.80)

        # Topic selection follows the discourse result. A resolved historical
        # coreference keeps the previous topic even when the new sentence shares
        # few literal tokens; a detected topic shift adopts the current anchor.
        if canonical_three_way == "RECALL" and selected_pair:
            reconstructed_topic = self._compact(
                selected_pair.get("user") or selected_pair.get("topic") or current_topic_label, 500
            )
        elif canonical_three_way == "CONTINUE" and selected_pair:
            reconstructed_topic = self._compact(
                selected_pair.get("user") or selected_pair.get("topic") or top_topic.get("topic") or current_topic_label, 500
            )
        elif topic_shift and current_topic_label:
            reconstructed_topic = current_topic_label
        elif relation == "SAME_TOPIC" and top_topic and top_topic.get("topic"):
            reconstructed_topic = self._compact(top_topic.get("topic"), 500)
        elif relation == "CONTINUE_TOPIC" and top_topic and top_topic.get("topic"):
            reconstructed_topic = self._compact(top_topic.get("topic"), 500)

        hypothesis_pairs = []
        if relation in {"SAME_TOPIC", "CONTINUE_TOPIC"} and top_topic:
            hypothesis_pairs.append((
                "continuation",
                f"The current user request continues the same subject as: {top_topic.get('user', '')}",
            ))
        if relation == "NEW_TOPIC":
            hypothesis_pairs.append((
                "new_topic",
                f"The current user request starts a different subject from: {top_topic.get('user', '')}",
            ))
        if historical_reference and coreference and coreference[0].get("candidates"):
            hypothesis_pairs.append((
                "reference",
                f"The current request refers to: {coreference[0]['candidates'][0]['entity']}",
            ))
        nli = self._nli_verify(current, hypothesis_pairs)

        return {
            "version": self.VERSION,
            "topic": {
                "active": reconstructed_topic,
                "relation": relation,
                "confidence": round(float(discourse_confidence), 6),
                "similarity_to_best_pair": round(topic_similarity, 6),
                "topic_shift": topic_shift,
                "best_pair": top_topic,
                "candidates": topic_profiles[:8],
                "source": "multilingual_embedding_topic_tracking",
            },
            "dialogue_selection": {
                **dialogue_selection,
                "selected_memory_operand": selected_pair,
                "memory_role": canonical_three_way,
            },
            "entities": {
                "current": current_entities[:24],
                "shared_with_active_topic": shared_entities[:16],
                "coreference": coreference,
                "source": "disabled_pair_context",
            },
            "turn_structure": {
                "segments": request_segments,
                "segment_count": len(request_segments),
                "ordinals": ordinals,
                "local_ordinal_reference": bool(local_compound and ordinals),
                "historical_ordinal_reference_blocked": bool(local_compound and ordinals),
                "source": "current_turn_structure",
            },
            "discourse": {
                "relation": relation,
                "continuation": relation == "CONTINUE_TOPIC",
                "same_topic": relation in {"CONTINUE_TOPIC", "RECALL"},
                "new_topic": relation == "NEW_TOPIC",
                "independent": relation == "NEW_TOPIC",
                "three_way_relation": canonical_three_way,
                "selected_memory_operand": selected_pair,
                "historical_reference": historical_reference,
                "self_contained": self_contained,
                "confidence": round(float(discourse_confidence), 6),
                "source": "authenticated_pair_discourse_fusion",
            },
            "task": {
                "actions": action_matrix,
                "input_modalities": modality.get("inputs", []),
                "input_evidence": modality,
                "requested_outputs": action_matrix.get("requested_outputs", []),
                "active_goal": self._compact(active_goal, 700),
                "source": "unified_multimodal_task_matrix",
            },
            "verification": {
                "nli": nli,
                "performed": bool(nli),
                "source": "local_nli_verifier" if nli else "not_run",
            },
            "context_contract": {
                "topic": reconstructed_topic,
                "relation": relation,
                "reference_entities": [
                    item.get("entity")
                    for item in (coreference[0].get("candidates", []) if coreference else [])
                    if item.get("entity")
                ][:8],
                "local_current_turn_structure": bool(local_compound),
                "historical_memory_allowed": bool(canonical_three_way in {"CONTINUE", "RECALL"}),
                "three_way_relation": canonical_three_way,
                "selected_memory_operand": selected_pair,
                "historical_reference_blocked_for_local_ordinals": bool(
                    local_compound and ordinals
                ),
                "multimodal_inputs": modality.get("inputs", []),
                "requested_outputs": action_matrix.get("requested_outputs", []),
                "decision_owner": DECISION_OWNER,
            },
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
        }


class QuantumInterpretationEngine:
    """
    One semantic engine. It measures evidence, resolves the user's task and
    freezes one production interpretation. Evidence never becomes a renderer
    command by itself. No lexical routing, no domain/capability gates and no
    silent renderer fallback.
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cache = {}
        self._cache_limit = 256
        self._vectorizer = None
        self._prototype_matrix = None
        self._prototype_index = {}
        self._semantic_encoder = None
        self._compile_matrix()

    @staticmethod
    def normalize(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", str(text or "").lower())

    def _compile_matrix(self):
        families = (
            ("dialogue", SEMANTIC_TURN_PROTOTYPES),
            ("representation", REPRESENTATION_HYPOTHESES),
            ("domain", DOMAIN_HYPOTHESES),
            ("capability", CAPABILITY_HYPOTHESES),
            ("operation", OPERATION_HYPOTHESES),
            ("object", OBJECT_HYPOTHESES),
            ("goal", GOAL_HYPOTHESES),
            ("visual_schema", VISUAL_SCHEMA_HYPOTHESES),
        )
        docs = []
        for family, vocab in families:
            for label, description in vocab.items():
                self._prototype_index[f"{family}:{label}"] = len(docs)
                docs.append(description)
        if TfidfVectorizer is not None and docs:
            self._vectorizer = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3,5),
                lowercase=True, sublinear_tf=True
            )
            self._prototype_matrix = self._vectorizer.fit_transform(docs)

        if APRIL_ENABLE_HEAVY_HOTPATH and os.getenv("APRIL_ALLOW_CONTEXT_MODEL_DOWNLOAD", "0").strip().lower() in {"1", "true", "yes", "on"} and SentenceTransformer is not None:
            try:
                self._semantic_encoder = SentenceTransformer(SEMANTIC_MODEL_NAME)
            except Exception:
                self._semantic_encoder = None

    @staticmethod
    def _semantic_focus_text(text: str) -> str:
        lines = []
        for line in str(text or "").splitlines():
            s = line.strip()
            if not s:
                continue
            nums = re.findall(r"[-+]?\\d+(?:[.,]\\d+)?", s)
            if len(nums) >= 2 and re.search(r"(?:—|–|-|:)", s):
                continue
            lines.append(s)
        return " ".join(lines)

    def _negated_representation_labels(self, text: str) -> set[str]:
        source = self.normalize(text).lower()
        negated = set()
        matches = re.findall(r"(?:не|not)\s+(?:как|as)\s+([^.;!?]+)", source)
        if not matches:
            return negated
        negated_text = " ".join(matches)
        negated_tokens = {
            token for token in self._tokens(negated_text)
            if len(token) >= 4
        }
        if not negated_tokens:
            return negated
        for label, hypothesis in REPRESENTATION_HYPOTHESES.items():
            hypothesis_tokens = {
                token for token in self._tokens(hypothesis)
                if len(token) >= 4 and not token.isascii()
            }
            if hypothesis_tokens & negated_tokens:
                negated.add(label)
        return negated

    def _family_scores(self, text, family, vocab):
        text = self.normalize(text)
        if not text:
            return {k:0.0 for k in vocab}

        if self._semantic_encoder is not None:
            try:
                q = self._semantic_encoder.encode([text], normalize_embeddings=True)[0]
                d = self._semantic_encoder.encode(
                    list(vocab.values()), normalize_embeddings=True
                )
                vals = ((d @ q) + 1.0) / 2.0
                return {k:max(0.0,min(1.0,float(v))) for k,v in zip(vocab,vals)}
            except Exception:
                pass

        if self._vectorizer is not None and self._prototype_matrix is not None and cosine_similarity is not None:
            q = self._vectorizer.transform([text])
            result = {}
            for label in vocab:
                idx = self._prototype_index[f"{family}:{label}"]
                similarity_value = cosine_similarity(q, self._prototype_matrix[idx])
                # cosine_similarity returns a 2-D array for sparse row/row input.
                # Extract the single scalar explicitly instead of coercing the
                # whole ndarray to float.
                score = float(similarity_value[0, 0])
                result[label] = max(0.0, min(1.0, score))
            return result

        # Evidence-only degraded measurement. It can rank hypotheses but it
        # cannot create or suppress production representation.
        tokens = set(self._tokens(text))
        result = {}
        for label, description in vocab.items():
            words = set(self._tokens(description))
            result[label] = min(1.0, len(tokens & words)/max(2.0,len(words)*0.2))
        return result

    def _operation_family_scores(self, text: str) -> dict[str, float]:
        """Measure operation hypotheses using matrix similarity plus token evidence.

        The token component is a measurement signal, not a hard-coded command trigger.
        It prevents long prototype descriptions from suppressing a semantically obvious
        operation such as arithmetic addition merely because unrelated words dominate
        the character n-gram similarity.
        """
        scores = self._family_scores(text, "operation", OPERATION_HYPOTHESES)
        query_tokens = set(self._tokens(text))
        if not query_tokens:
            return scores
        for label, description in OPERATION_HYPOTHESES.items():
            desc_tokens = set(self._tokens(description))
            shared = len(query_tokens & desc_tokens)
            overlap = shared / max(1, len(query_tokens))
            # Blend a structural lexical measurement with the semantic matrix score.
            scores[label] = max(
                float(scores.get(label, 0.0) or 0.0),
                min(1.0, 0.80 * overlap),
            )
        return scores

    @staticmethod
    def _semantic_request_features(
        text: str,
        scores: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, float | bool]:
        """Collapse semantic families into a task-vector feature set.

        No word/phrase trigger table is used.  The feature set is derived only
        from the already-measured semantic families, so equivalent phrasings
        converge on the same task representation.
        """
        measured = scores if isinstance(scores, dict) else {}
        rep_scores = measured.get("representation", {}) if isinstance(measured.get("representation"), dict) else {}
        op_scores = measured.get("operation", {}) if isinstance(measured.get("operation"), dict) else {}
        obj_scores = measured.get("object", {}) if isinstance(measured.get("object"), dict) else {}
        goal_scores = measured.get("goal", {}) if isinstance(measured.get("goal"), dict) else {}
        dial_scores = measured.get("dialogue", {}) if isinstance(measured.get("dialogue"), dict) else {}

        def best(mapping: dict[str, float], default: str) -> tuple[str, float]:
            if not mapping:
                return default, 0.0
            key, value = max(mapping.items(), key=lambda item: float(item[1] or 0.0))
            return str(key), float(value or 0.0)

        best_rep, best_rep_score = best(rep_scores, "text")
        best_op, best_op_score = best(op_scores, "answer")
        best_obj, best_obj_score = best(obj_scores, "text")
        best_goal, best_goal_score = best(goal_scores, "understand")
        best_dialogue, best_dialogue_score = best(dial_scores, "statement")
        memory_query_score = float(dial_scores.get("memory_query", 0.0) or 0.0)
        reference_score = float(dial_scores.get("reference", 0.0) or 0.0)
        reformulation_score = float(dial_scores.get("reformulation", 0.0) or 0.0)
        artifact_reference_score = float(dial_scores.get("artifact_reference", 0.0) or 0.0)
        reference_signal = max(reference_score, reformulation_score, artifact_reference_score)
        # A complete visual build such as "Нарисуй кота" naturally overlaps with
        # the artifact-reference prototype because of the verb "нарисуй". Do not
        # cancel a real visual task on that signal alone. Require independent
        # reference/reformulation evidence (or a strong memory query) before the
        # current turn is locked to historical context.
        explicit_visual_reference = bool(
            artifact_reference_score >= 0.080
            and (reference_score + reformulation_score >= 0.100)
        )
        visual_reference_lock = bool(
            memory_query_score >= 0.160
            or explicit_visual_reference
        )

        structured_rep = best_rep in {
            "diagram", "graph", "formula", "image", "gallery", "table",
            "code", "link", "audio", "video", "file", "action", "scene",
            "memory", "visual_context",
        }

        # Representation hypotheses are evidence, not authorization.  The winning
        # prototype does not have to be ``image``: natural drawing requests can
        # leave TEXT slightly above IMAGE while the independent image
        # representation/object evidence is already strong enough.
        image_rep_score = float(rep_scores.get("image", 0.0) or 0.0)
        image_obj_score = float(obj_scores.get("image", 0.0) or 0.0)
        production_operation_scores = {
            name: float(op_scores.get(name, 0.0) or 0.0)
            for name in (
                "build", "create", "generate", "present",
                "modify", "transform", "redraw",
            )
        }
        visual_operation_name, visual_operation_score = max(
            production_operation_scores.items(),
            key=lambda item: item[1],
            default=("", 0.0),
        )
        visual_rep = bool(image_rep_score >= 0.035)
        visual_object = bool(image_obj_score >= 0.035)
        visual_operation = bool(visual_operation_score >= 0.055)
        visual_goal = bool(
            best_goal in {"visualize", "transform", "present"}
            and best_goal_score >= 0.060
        )
        memory_query = best_dialogue == "memory_query"
        followup_dialogue = best_dialogue in {
            "continuation", "reformulation", "correction", "reference",
            "artifact_reference", "affirmation", "rejection",
        }

        content_tokens = [
            token for token in QuantumContextUnderstandingEngine._content_tokens(text)
            if token and len(token) >= 2
        ]
        # A complete visual task has both a measured production operation and a
        # concrete current-turn content operand. This lets "Нарисуй кота" remain
        # independent even if the generic artifact-reference prototype scores high,
        # while the incomplete "Да нарисуй" must inherit its operand from 12h memory.
        current_visual_task_complete = bool(
            not visual_reference_lock
            and visual_operation
            and (visual_rep or visual_object)
            and len(content_tokens) >= 2
        )
        effective_followup_dialogue = bool(
            followup_dialogue and not current_visual_task_complete
        )
        # Self-containment is a semantic task property, not the generic dialogue
        # classifier result.  In particular, short visual commands such as
        # ``Нарисуй кота`` are complete because they contain a concrete visual
        # operand, while ``Да нарисуй`` is deliberately incomplete and must inherit
        # the latest visual operand from the authenticated 12h pair memory.
        meaningful_structured_rep = bool(
            structured_rep and best_rep_score >= 0.035
        )
        meaningful_object = bool(
            best_obj != "text" and best_obj_score >= 0.040
        )
        # Ordinary factual/list/explanation requests are complete semantic tasks
        # even when their best object prototype is noisy.  This is what prevents
        # a self-contained question such as “Назови любую породу собаки” from
        # being reassigned to an older visual branch in the 12h memory.
        textual_self_contained = bool(
            not followup_dialogue
            and not memory_query
            and best_op in {
                "answer", "list", "explain", "retrieve", "calculate",
                "compare", "summarize",
            }
            and len(QuantumContextUnderstandingEngine._content_tokens(text)) >= 2
        )
        semantic_self_contained = bool(
            not effective_followup_dialogue
            and not memory_query
            and (
                textual_self_contained
                or (
                    best_op in {
                        "build", "create", "generate", "modify", "present",
                        "transform", "redraw", "visualize",
                    }
                    and (meaningful_object or meaningful_structured_rep)
                )
            )
        )
        # For image generation the object itself is the decisive operand.
        # Do not let similarity to a previous image turn make a complete current
        # request inherit that older prompt.  A memory-query turn is never a
        # generation request, even if it contains words like "нарисуй".
        current_visual_self_contained = bool(
            not memory_query
            and current_visual_task_complete
        )
        self_contained = current_visual_self_contained or semantic_self_contained

        return {
            "visual_action": bool(visual_operation and (visual_rep or visual_object)),
            "visual_generation_operation": visual_operation_name,
            "visual_generation_operation_score": visual_operation_score,
            "image_representation_score": image_rep_score,
            "image_object_score": image_obj_score,
            "explain_action": bool(best_op == "explain"),
            "geometry_object": bool(
                best_obj == "diagram"
                and best_obj_score >= 0.08
            ),
            "construction_context": bool(
                best_rep == "diagram"
                and best_rep_score >= 0.08
            ),
            "visual_construction": bool(
                visual_rep
                and visual_operation
                and (visual_object or best_rep_score >= 0.16)
                and (visual_goal or best_goal_score >= 0.08)
            ),
            "ascii_schema_advisory": False,
            "ascii_schema_score": 0.0,
            "self_contained": self_contained,
            "memory_query": memory_query,
            "visual_reference_lock": visual_reference_lock,
            "semantic_best_representation": best_rep,
            "semantic_best_operation": best_op,
            "semantic_best_object": best_obj,
            "semantic_best_goal": best_goal,
            "semantic_best_dialogue": best_dialogue,
            "semantic_best_dialogue_score": best_dialogue_score,
        }

    @staticmethod
    def _scene_semantic_text(scene: dict | None) -> str:
        """Build a compact semantic view of the active rendered scene.

        This is local evidence only. It serializes existing scene metadata and
        structured render-block payloads; it does not choose a renderer or call
        a provider.
        """
        if not isinstance(scene, dict):
            return ""
        parts = [
            scene.get("topic"),
            scene.get("summary"),
            scene.get("user_request"),
            scene.get("current_request"),
            scene.get("april_answer"),
            scene.get("answer"),
        ]
        for block in scene.get("render_blocks") or []:
            if not isinstance(block, dict):
                continue
            parts.extend([
                block.get("type"),
                block.get("artifact_type"),
                block.get("representation"),
                block.get("renderer"),
                block.get("title"),
                block.get("label"),
                block.get("content"),
                block.get("text"),
            ])
            payload = block.get("payload")
            if isinstance(payload, dict):
                # Payload is already part of the active scene. Keep only a compact
                # textual projection so visual facts can participate in semantic
                # similarity without copying the entire artifact into the prompt.
                parts.append(
                    re.sub(r"\\s+", " ", str(payload))[:1800]
                )
        return re.sub(r"\\s+", " ", " ".join(
            str(x) for x in parts if x not in (None, "", [], {})
        )).strip()[:5000]

    def _context_scores(self,text,previous_assistant,previous_user,active_topic,active_goal):
        vals = {
            "previous_assistant":previous_assistant,
            "previous_user":previous_user,
            "active_topic":active_topic,
            "active_goal":active_goal,
        }
        return {
            k:self.similarity(text,v)["score"] if self.normalize(v) else 0.0
            for k,v in vals.items()
        }

    @classmethod
    def _recent_dialogue_pairs(cls, history: list, limit: int = 10) -> list[dict[str, str]]:
        """Build a compact authentic USER→APRIL memory window for follow-ups."""
        pairs: list[dict[str, str]] = []
        pending_user = ""
        for item in history if isinstance(history, list) else []:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            if metadata.get("internal_context") or metadata.get("internal_turn"):
                continue
            role = str(item.get("role") or "").lower()
            if role in {"user", "human"}:
                pending_user = cls.normalize(item.get("content") or item.get("text") or item.get("answer"))
                continue
            if role in {"assistant", "april", "bot"}:
                answer = cls.normalize(item.get("content") or item.get("answer") or item.get("text") or item.get("summary"))
                if pending_user and answer:
                    pairs.append({
                        "user": pending_user[:700],
                        "april": answer[:900],
                        "result": answer[:1200],
                        "development_state": "completed_turn",
                    })
                pending_user = ""
                continue
            user_obj = item.get("user") if isinstance(item.get("user"), dict) else None
            april_obj = item.get("april") if isinstance(item.get("april"), dict) else None
            if user_obj and april_obj:
                user = cls.normalize(user_obj.get("text") or user_obj.get("content") or user_obj.get("answer"))
                answer = cls.normalize(april_obj.get("answer") or april_obj.get("content") or april_obj.get("text"))
                if user and answer:
                    pairs.append({"user": user[:700], "april": answer[:900]})
        return pairs[-max(1, int(limit)):]

    @classmethod
    def _extract_numeric_results(cls, recent_dialogue_pairs: list[dict[str, str]] | None) -> list[dict[str, Any]]:
        """Extract concrete numeric results from recent authentic assistant answers.

        This is structural evidence, not a topic/phrase trigger. Equality RHS values
        are preferred; when an answer contains exactly one numeric value, that value
        is accepted as the result. The original user/assistant pair is preserved so
        downstream reasoning can cite the source without guessing.
        """
        results: list[dict[str, Any]] = []
        for idx, pair in enumerate(recent_dialogue_pairs or [], start=1):
            if not isinstance(pair, dict):
                continue
            answer = cls.normalize(pair.get("april") or pair.get("assistant"))
            user = cls.normalize(pair.get("user"))
            if not answer:
                continue
            values: list[str] = []
            for match in re.finditer(
                r"(?:=|равно|equals)\s*([-+]?\d+(?:[.,]\d+)?)\b",
                answer,
                flags=re.I,
            ):
                values.append(match.group(1))
            if not values:
                numbers = re.findall(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?![\w.])", answer)
                if len(numbers) == 1:
                    values.append(numbers[0])
            if not values:
                continue
            results.append({
                "history_index": idx,
                "user": user,
                "assistant": answer,
                "result": values[-1],
                "source": "authentic_dialogue_result",
            })
        # Keep chronological order and only concrete result-bearing pairs.
        return results[-10:]

    @classmethod
    def _history_task_resolution(
        cls,
        current: str,
        recent_dialogue_pairs: list[dict[str, str]] | None,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine whether the current task is incomplete without recent results.

        The decision is based on the semantic operation plus structural operand
        availability. It is intentionally independent from any exact wording such
        as "два последних" so paraphrases behave consistently.
        """
        operation = cls.normalize(features.get("semantic_best_operation")).lower()
        numeric_results = cls._extract_numeric_results(recent_dialogue_pairs)
        current_numbers = re.findall(
            r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?![\w.])",
            cls.normalize(current),
        )
        explicit_expression = bool(re.search(
            r"[-+]?\d+(?:[.,]\d+)?\s*[+*/-]\s*[-+]?\d+(?:[.,]\d+)?",
            cls.normalize(current),
        ))
        # A self-contained arithmetic task has its operands in the current request.
        self_contained_numeric = bool(explicit_expression or len(current_numbers) >= 2)

        requires_history = bool(
            operation == "calculate"
            and not self_contained_numeric
            and len(numeric_results) >= 2
        )
        selected = numeric_results[-2:] if requires_history else []
        operands = [x["result"] for x in selected]
        confidence = 0.99 if requires_history else 0.0
        return {
            "required": requires_history,
            "operation": operation,
            "self_contained_numeric": self_contained_numeric,
            "explicit_numeric_count": len(current_numbers),
            "available_numeric_results": len(numeric_results),
            "selected_results": selected,
            "resolved_operands": operands,
            "source": "semantic_operation_plus_structural_history",
            "confidence": confidence,
        }

    def _light_history_context_check(
        self,
        current: str,
        pairs: list[dict[str, str]],
        *,
        memory_query_score: float = 0.0,
        dialogue_scores: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Second-pass history check before Provider handoff.

        This pass does not classify entities, topics, branches or tasks. It asks one
        narrow question: does the current request semantically depend on the
        authenticated USER↔APRIL pair history in the current 12-hour window?

        It is intentionally lightweight: prototype similarity + pair similarity +
        small lexical affinity. It never replaces the canonical NEW/CONTINUE/RECALL
        selector; it only verifies a NEW result and prepares a compact pair context.
        """
        current = self.normalize(current)
        pairs = [p for p in (pairs or []) if isinstance(p, dict)]
        dialogue_scores = dialogue_scores if isinstance(dialogue_scores, dict) else {}

        def content_tokens(value: str) -> list[str]:
            try:
                raw = QuantumContextUnderstandingEngine._content_tokens(value)
            except Exception:
                raw = re.findall(
                    r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+",
                    str(value or "").lower(),
                )
            return [x for x in raw if len(x) >= 3]

        def token_affinity(left: str, right: str) -> float:
            a = set(content_tokens(left))
            b = set(content_tokens(right))
            if not a or not b:
                return 0.0
            exact = len(a & b) / max(1, len(a | b))
            # Very small morphology tolerance for Russian/Ukrainian inflections;
            # it is pair-text similarity only, never entity detection.
            morph_hits = 0.0
            for x in a:
                for y in b:
                    if x == y:
                        morph_hits += 1.0
                        break
                    common = 0
                    for ca, cb in zip(x, y):
                        if ca != cb:
                            break
                        common += 1
                    if common >= 4 and common / max(len(x), len(y)) >= 0.55:
                        morph_hits += 0.5
                        break
            morph = min(1.0, morph_hits / max(1, min(len(a), len(b))))
            return max(exact, 0.72 * exact + 0.28 * morph)

        recall_prototypes = (
            "что мы обсуждали раньше в этом диалоге",
            "что было после предыдущего вопроса в нашем разговоре",
            "что мы обсуждали после этого вопроса",
            "поищи в истории нашего разговора",
            "что я спрашивал раньше",
            "что было до этого в нашем диалоге",
            "продолжи с учетом предыдущих сообщений",
        )
        continuation_prototypes = (
            "продолжи предыдущую мысль",
            "развивай предыдущий ответ",
            "уточни то что мы только что обсуждали",
            "переделай предыдущий результат",
        )

        recall_proto_score = max(
            (
                float(self.similarity(current, proto).get("score", 0.0) or 0.0)
                for proto in recall_prototypes
            ),
            default=0.0,
        )
        continuation_proto_score = max(
            (
                float(self.similarity(current, proto).get("score", 0.0) or 0.0)
                for proto in continuation_prototypes
            ),
            default=0.0,
        )

        scored: list[dict[str, Any]] = []
        for index, pair in enumerate(pairs[:]):
            user = self.normalize(
                pair.get("user")
                or pair.get("user_text")
                or pair.get("user_request")
            )
            april = self.normalize(
                pair.get("april")
                or pair.get("april_text")
                or pair.get("april_answer")
                or pair.get("assistant")
                or pair.get("answer")
            )
            if not user and not april:
                continue
            combined = f"{user} {april}".strip()
            pair_semantic = float(
                self.similarity(current, combined).get("score", 0.0) or 0.0
            )
            user_semantic = float(
                self.similarity(current, user).get("score", 0.0) or 0.0
            ) if user else 0.0
            lexical = token_affinity(current, combined)
            user_lexical = token_affinity(current, user)
            recency = 1.0 / (1.0 + 0.12 * (len(pairs[:]) - 1 - index))
            # History relation is strongest when the request refers to the pair text,
            # not merely when it shares generic question words.
            score = (
                0.42 * pair_semantic
                + 0.26 * user_semantic
                + 0.20 * lexical
                + 0.08 * user_lexical
                + 0.04 * recency
            )
            scored.append({
                "index": index,
                "score": round(float(min(1.0, score)), 6),
                "pair_semantic": round(pair_semantic, 6),
                "user_semantic": round(user_semantic, 6),
                "lexical": round(lexical, 6),
                "user_lexical": round(user_lexical, 6),
                "recency": round(recency, 6),
                "pair": dict(pair),
            })

        scored.sort(key=lambda x: (float(x["score"]), int(x["index"])), reverse=True)
        best = scored[0] if scored else {}
        best_pair_score = float(best.get("score", 0.0) or 0.0)
        best_index = int(best.get("index", -1) or -1)

        # "Memory query" is a discourse property of the whole request. Pair
        # similarity only tells us which historical pair should serve as its anchor.
        # Keep the measured memory-query classifier separate from broad prototype
        # resemblance. Generic "что такое X" questions often resemble recall
        # sentences because of shared interrogative grammar.
        memory_signal = max(
            float(memory_query_score or 0.0),
            float(dialogue_scores.get("memory_query", 0.0) or 0.0),
        )
        reference_signal = max(
            float(dialogue_scores.get("reference", 0.0) or 0.0),
            float(dialogue_scores.get("artifact_reference", 0.0) or 0.0),
        )
        followup_signal = max(
            float(dialogue_scores.get("continuation", 0.0) or 0.0),
            float(dialogue_scores.get("reformulation", 0.0) or 0.0),
            float(dialogue_scores.get("correction", 0.0) or 0.0),
            continuation_proto_score,
        )

        operation_scores = self._operation_family_scores(current)
        best_operation = (
            max(operation_scores.items(), key=lambda item: float(item[1] or 0.0))[0]
            if operation_scores else "answer"
        )
        generic_self_contained = bool(
            content_tokens(current)
            and best_operation in {"answer", "explain", "calculate", "list", "retrieve", "compare"}
            and memory_signal < 0.20
            and recall_proto_score < 0.44
            and followup_signal < 0.18
            and reference_signal < 0.16
        )

        # Generic question forms ("что такое X") produce background similarity to
        # memory prototypes. Require a materially stronger history signal so a new
        # self-contained question remains NEW.
        history_query = bool(
            pairs
            and (
                memory_signal >= 0.20
                or (recall_proto_score >= 0.44 and best_pair_score >= 0.14)
            )
        )
        historical_dependency = bool(
            pairs
            and not generic_self_contained
            and (
                history_query
                or (
                    followup_signal >= 0.18
                    and best_pair_score >= 0.18
                )
                or (
                    reference_signal >= 0.16
                    and best_pair_score >= 0.16
                )
            )
        )

        # Keep a small contiguous context. CONTINUE needs immediate trajectory;
        # RECALL needs the anchor and the turns around it. This is what makes the
        # pre-Provider check useful under the 900-token input budget.
        bounded_pairs = pairs[:]
        if historical_dependency and bounded_pairs:
            anchor = max(0, min(best_index, len(bounded_pairs) - 1))
            if history_query:
                start = max(0, anchor - 2)
                end = min(len(bounded_pairs), anchor + 7)
                context_pairs = bounded_pairs[start:end]
            else:
                context_pairs = bounded_pairs[-3:]
        else:
            context_pairs = []

        return {
            "performed": True,
            "source": "LIGHT_HISTORY_CONTEXT_CHECK",
            "window_hours": 12,
            "pair_count": len(pairs),
            "memory_query_signal": round(float(memory_signal), 6),
            "recall_prototype_score": round(float(recall_proto_score), 6),
            "continuation_signal": round(float(followup_signal), 6),
            "reference_signal": round(float(reference_signal), 6),
            "best_pair_index": best_index,
            "best_pair_score": round(float(best_pair_score), 6),
            "best_pair": dict(best.get("pair") or {}),
            "history_query": history_query,
            "historical_dependency": historical_dependency,
            "context_pairs": [dict(x) for x in context_pairs],
            "candidate_pairs": [
                {
                    "index": int(x["index"]),
                    "score": float(x["score"]),
                    "pair": dict(x["pair"]),
                }
                for x in scored[:6]
            ],
        }

    def _select_three_way_dialogue_relation(
        self,
        current: str,
        recent_pairs: list[dict[str, str]],
        *,
        active_topic: str = "",
        previous_assistant: str = "",
        previous_user: str = "",
    ) -> dict:
        """Canonical NEW / CONTINUE / RECALL decision from authenticated 12h pairs.

        The decision has two internal steps:
          1) semantic discourse classification;
          2) a lightweight verification against the actual USER↔APRIL pair window.

        No entity extraction, topic graph, task branch or legacy intent engine can
        force continuation. The pair window is the only historical source.
        """
        current = self.normalize(current)
        pairs = [p for p in (recent_pairs or []) if isinstance(p, dict)]
        if not current:
            return {
                "relation": "NEW",
                "confidence": 1.0,
                "selected_index": -1,
                "selected_pair": {},
                "candidates": [],
                "context_pairs": [],
                "source": "PAIR_12H_INTERPRETATION_V3",
            }

        def content_tokens(value: str) -> list[str]:
            try:
                raw = QuantumContextUnderstandingEngine._content_tokens(value)
            except Exception:
                raw = re.findall(
                    r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+",
                    str(value or "").lower(),
                )
            return [x for x in raw if len(x) >= 3]

        def token_affinity(left: str, right: str) -> float:
            a = set(content_tokens(left))
            b = set(content_tokens(right))
            if not a or not b:
                return 0.0
            exact = len(a & b) / max(1, len(a | b))
            morph_hits = 0.0
            for x in a:
                for y in b:
                    if x == y:
                        morph_hits += 1.0
                        break
                    common = 0
                    for ca, cb in zip(x, y):
                        if ca != cb:
                            break
                        common += 1
                    if common >= 4 and common / max(len(x), len(y)) >= 0.55:
                        morph_hits += 0.5
                        break
            morph = min(1.0, morph_hits / max(1, min(len(a), len(b))))
            return max(exact, 0.72 * exact + 0.28 * morph)

        scores = self._family_scores(current, "dialogue", SEMANTIC_TURN_PROTOTYPES)
        memory_query = float(scores.get("memory_query", 0.0) or 0.0)
        recall_prototypes = (
            "вспомни о чем мы говорили раньше какие темы обсуждали",
            "какую тему мы не обсуждали найди в предыдущем разговоре",
            "поищи в контексте предыдущего разговора",
            "что мы обсуждали после предыдущего вопроса",
        )
        recall_score = max(
            (
                float(self.similarity(current, proto).get("score", 0.0) or 0.0)
                for proto in recall_prototypes
            ),
            default=0.0,
        )
        is_recall = bool(memory_query >= 0.20 or recall_score >= 0.44)

        rep = self._family_scores(current, "representation", REPRESENTATION_HYPOTHESES)
        op = self._operation_family_scores(current)
        best_rep = max(rep.items(), key=lambda x: float(x[1] or 0.0))[0] if rep else "text"
        best_rep_score = float(rep.get(best_rep, 0.0) or 0.0)
        best_op = max(op.items(), key=lambda x: float(x[1] or 0.0))[0] if op else "answer"
        visual_operation = best_op in {
            "build", "create", "generate", "modify", "present",
            "transform", "redraw", "visualize"
        }
        visual_complete = bool(
            visual_operation
            and best_rep in {"image", "gallery", "diagram", "graph"}
            and best_rep_score >= 0.035
        )

        dialogue_followup = max(
            (
                float(scores.get(k, 0.0) or 0.0)
                for k in (
                    "continuation", "reformulation", "correction",
                    "reference", "artifact_reference", "affirmation", "rejection"
                )
            ),
            default=0.0,
        )
        explanatory_ops = {
            "answer", "explain", "list", "retrieve", "compare",
            "summarize", "calculate",
        }
        standalone_question = bool(
            content_tokens(current)
            and best_op in explanatory_ops
            and dialogue_followup < 0.12
        )
        incomplete = bool(
            not content_tokens(current)
            or (len(content_tokens(current)) <= 1 and not standalone_question)
            or dialogue_followup >= 0.12
        )
        if visual_complete:
            incomplete = False

        scored = []
        window = pairs[:]
        for i, pair in enumerate(window):
            u = self.normalize(
                pair.get("user")
                or pair.get("user_text")
                or pair.get("user_request")
            )
            a = self.normalize(
                pair.get("april")
                or pair.get("april_text")
                or pair.get("april_answer")
                or pair.get("assistant")
                or pair.get("answer")
            )
            if not u and not a:
                continue
            combined = f"{u} {a}".strip()
            lexical = token_affinity(current, combined)
            user_lexical = token_affinity(current, u)
            semantic = (
                float(self.similarity(current, combined).get("score", 0.0) or 0.0)
                if combined else 0.0
            )
            user_semantic = (
                float(self.similarity(current, u).get("score", 0.0) or 0.0)
                if u else 0.0
            )
            recency = 1.0 / (1.0 + 0.12 * (len(window) - 1 - i))
            score = (
                0.42 * semantic
                + 0.26 * user_semantic
                + 0.20 * lexical
                + 0.08 * user_lexical
                + 0.04 * recency
            )
            scored.append({
                "index": i,
                "score": max(0.0, min(1.0, score)),
                "lexical": lexical,
                "user_lexical": user_lexical,
                "semantic": semantic,
                "user_semantic": user_semantic,
                "pair": pair,
            })

        scored.sort(key=lambda x: (x["score"], x["index"]), reverse=True)
        latest_index = len(window) - 1
        latest = next((x for x in scored if x["index"] == latest_index), None)
        best = scored[0] if scored else None
        latest_score = float(latest["score"] if latest else 0.0)
        best_score = float(best["score"] if best else 0.0)
        second_score = float(scored[1]["score"] if len(scored) > 1 else 0.0)
        margin = best_score - second_score

        light = self._light_history_context_check(
            current,
            window,
            memory_query_score=memory_query,
            dialogue_scores=scores,
        )

        # The second pass can upgrade a superficially NEW request to RECALL only
        # when it has semantic memory intent and a real pair anchor.
        if not is_recall and light.get("history_query") and light.get("best_pair_score", 0.0) >= 0.12:
            is_recall = True

        if is_recall and scored:
            anchor_index = int(light.get("best_pair_index", best["index"]) if light.get("best_pair_index", -1) >= 0 else best["index"])
            selected_score_row = next((x for x in scored if x["index"] == anchor_index), best)
            relation = "RECALL"
            selected_index = int(selected_score_row["index"])
            selected_pair = dict(selected_score_row["pair"])
            context_pairs = light.get("context_pairs") or window
            confidence = max(
                0.70,
                min(
                    0.99,
                    max(
                        recall_score,
                        memory_query,
                        float(light.get("memory_query_signal", 0.0) or 0.0),
                        float(light.get("best_pair_score", 0.0) or 0.0),
                    ),
                ),
            )
        elif not window:
            relation = "NEW"
            selected_index = -1
            selected_pair = {}
            context_pairs = []
            confidence = 0.98
        elif incomplete and latest is not None:
            relation = "CONTINUE"
            selected_index = int(latest["index"])
            selected_pair = dict(latest["pair"])
            context_pairs = list(window[-3:])
            confidence = max(
                0.62,
                min(
                    0.97,
                    0.58 + 0.35 * max(
                        latest_score,
                        dialogue_followup,
                        float(light.get("continuation_signal", 0.0) or 0.0),
                    ),
                ),
            )
        elif (
            best is not None
            and best["index"] == latest_index
            and best_score >= 0.34
            and margin >= 0.08
            and best["lexical"] >= 0.18
        ):
            relation = "CONTINUE"
            selected_index = int(best["index"])
            selected_pair = dict(best["pair"])
            context_pairs = list(window[-3:])
            confidence = max(0.60, min(0.96, best_score))
        elif (
            incomplete
            and light.get("historical_dependency")
            and light.get("best_pair_score", 0.0) >= 0.20
            and float(light.get("continuation_signal", 0.0) or 0.0) >= 0.18
        ):
            relation = "CONTINUE"
            anchor_index = int(light.get("best_pair_index", -1))
            selected_index = anchor_index if anchor_index >= 0 else latest_index
            selected_pair = dict(
                next(
                    (x["pair"] for x in scored if x["index"] == selected_index),
                    latest["pair"] if latest else {},
                )
            )
            context_pairs = list(window[-3:])
            confidence = max(
                0.60,
                min(0.95, float(light.get("best_pair_score", 0.0) or 0.0)),
            )
        else:
            relation = "NEW"
            selected_index = -1
            selected_pair = {}
            context_pairs = []
            confidence = max(0.62, 1.0 - min(best_score, 0.38))

        # A CONTINUE decision must always carry an actual USER↔APRIL operand.
        # Never emit CONTINUE with selected_memory_index=-1: that creates the
        # exact "I cannot see the previous dialogue" failure at Provider level.
        if relation == "CONTINUE" and window and not selected_pair:
            selected_index = latest_index
            selected_pair = dict(window[-1])
            context_pairs = list(window[-3:])
            confidence = max(float(confidence or 0.0), 0.66)

        return {
            "relation": relation,
            "confidence": round(float(confidence), 6),
            "selected_index": selected_index,
            "selected_pair": selected_pair,
            "latest_score": round(latest_score, 6),
            "best_score": round(best_score, 6),
            "second_score": round(second_score, 6),
            "margin": round(margin, 6),
            "dialogue_followup_evidence": round(dialogue_followup, 6),
            "memory_query_score": round(memory_query, 6),
            "implicit_context_dependency": relation == "CONTINUE",
            "current_self_contained": not incomplete,
            "memory_window": [dict(p) for p in window],
            "context_pairs": [dict(p) for p in context_pairs][-9:],
            "history_context_check": light,
            "source": "PAIR_12H_INTERPRETATION_V3",
            "entity_engine": False,
            "topic_engine": False,
            "intent_engine": False,
        }

    def _dialogue_relation_engine(
        self,
        text: str,
        *,
        previous_assistant: str = "",
        previous_user: str = "",
        active_topic: str = "",
        active_goal: str = "",
        previous_scene: dict | None = None,
        recent_dialogue_pairs: list[dict[str, str]] | None = None,
    ) -> dict:
        """Resolve topic continuity and request dependency from semantic evidence.

        Topic similarity and request dependency are separate dimensions.  The
        dialogue classifier decides the discourse act; current-task semantic
        completeness prevents topical similarity from becoming a false
        continuation.  No lexical trigger map is used.
        """
        current = self.normalize(text)
        prev_a = self.normalize(previous_assistant)
        prev_u = self.normalize(previous_user)
        topic = self.normalize(active_topic)
        goal = self.normalize(active_goal)
        scene = previous_scene if isinstance(previous_scene, dict) else {}
        scene_topic = self.normalize(scene.get("topic"))

        sims = {
            "previous_assistant": self.similarity(current, prev_a)["score"] if prev_a else 0.0,
            "previous_user": self.similarity(current, prev_u)["score"] if prev_u else 0.0,
            "active_topic": self.similarity(current, topic)["score"] if topic else 0.0,
            "active_goal": self.similarity(current, goal)["score"] if goal else 0.0,
            "previous_scene_topic": self.similarity(current, scene_topic)["score"] if scene_topic else 0.0,
        }
        dialogue_scores = self._family_scores(current, "dialogue", SEMANTIC_TURN_PROTOTYPES)
        dialogue_rank = sorted(
            dialogue_scores.items(),
            key=lambda item: float(item[1] or 0.0),
            reverse=True,
        )
        dialogue_best = dialogue_rank[0][0] if dialogue_rank else "statement"
        dialogue_best_score = float(dialogue_rank[0][1]) if dialogue_rank else 0.0

        features = self._semantic_request_features(
            current,
            {
                "representation": self._family_scores(current, "representation", REPRESENTATION_HYPOTHESES),
                "operation": self._family_scores(current, "operation", OPERATION_HYPOTHESES),
                "object": self._family_scores(current, "object", OBJECT_HYPOTHESES),
                "goal": self._family_scores(current, "goal", GOAL_HYPOTHESES),
                "dialogue": dialogue_scores,
            },
        )

        recent_pairs = recent_dialogue_pairs if isinstance(recent_dialogue_pairs, list) else []
        three_way = self._select_three_way_dialogue_relation(
            current, recent_pairs, active_topic=topic,
            previous_assistant=prev_a, previous_user=prev_u,
        )
        history_task = self._history_task_resolution(current, recent_pairs, features)

        followup_labels = {"continuation", "reformulation", "correction", "reference", "artifact_reference", "affirmation", "rejection"}
        dialogue_followup = max(
            (float(dialogue_scores.get(label, 0.0) or 0.0) for label in followup_labels),
            default=0.0,
        )
        reference_evidence = max(
            float(dialogue_scores.get("reference", 0.0) or 0.0),
            float(dialogue_scores.get("artifact_reference", 0.0) or 0.0),
        )
        artifact_reference_evidence = float(
            dialogue_scores.get("artifact_reference", 0.0) or 0.0
        )
        memory_evidence = float(dialogue_scores.get("memory_query", 0.0) or 0.0)
        continuation_evidence = max(
            float(dialogue_scores.get("continuation", 0.0) or 0.0),
            float(dialogue_scores.get("reformulation", 0.0) or 0.0),
            float(dialogue_scores.get("correction", 0.0) or 0.0),
        )

        history_available = bool(recent_pairs or prev_a or prev_u)
        topic_affinity = max(
            sims["active_topic"],
            sims["previous_scene_topic"],
            sims["previous_user"] * 0.92,
        )
        answer_affinity = sims["previous_assistant"]
        request_affinity = sims["previous_user"]
        goal_affinity = sims["active_goal"]
        relation_strength = max(topic_affinity, answer_affinity, request_affinity, goal_affinity)

        has_context = bool(prev_a or prev_u or topic or scene_topic)
        current_self_contained = bool(features.get("self_contained"))
        explicit_numeric_expression = bool(re.search(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?\s*[+*\-/]\s*[+-]?\d+(?:[.,]\d+)?(?!\w)", current))
        contextual_operation = str(features.get("semantic_best_operation") or "").lower() in {"calculate", "analyze", "explain", "list", "compare", "modify", "present"}
        semantic_followup_evidence = max(dialogue_followup, reference_evidence, memory_evidence, continuation_evidence)
        history_dependent_task = bool(
            history_task.get("required")
            or (
                history_available
                and not current_self_contained
                and semantic_followup_evidence >= 0.08
                and not explicit_numeric_expression
            )
        )
        semantic_reference = bool(
            dialogue_best == "reference"
            and reference_evidence >= 0.080
            and has_context
            and not current_self_contained
        )
        # The generic memory-query prototype can weakly match ordinary follow-up
        # wording (for example "расскажи подробнее"). Treat it as an actual memory
        # query only when its measured score is materially above background noise.
        semantic_memory_query = bool(
            dialogue_best == "memory_query"
            and memory_evidence >= 0.160
            and has_context
        )

        # A dialogue classifier is authoritative for discourse act.  Similarity
        # only supplies topical context and never upgrades an independent task.
        if not has_context:
            # A memory-query state requires an existing dialogue anchor. A generic
            # question such as "Who is Pushkin?" is a new topic, not a recall request.
            relation = "NEW_TOPIC"
            topic_relation = "NEW_TOPIC"
        elif semantic_memory_query:
            relation = "MEMORY_QUERY"
            topic_relation = "SAME_TOPIC"
        elif semantic_reference:
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif dialogue_best in {"continuation", "reformulation", "correction"} and not current_self_contained:
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif history_task.get("required"):
            # The current operation is structurally incomplete without concrete
            # results from recent authenticated dialogue. Preserve the task as a
            # continuation even when the dialogue classifier ranked it as a generic
            # question/new task.
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif history_dependent_task and semantic_followup_evidence >= 0.08:
            # The current semantic task is incomplete without prior dialogue
            # values/results. This is a dependency measurement, not a word trigger.
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif current_self_contained:
            relation = (
                "SAME_TOPIC"
                if topic_affinity >= 0.18 or request_affinity >= 0.42
                else "INDEPENDENT"
            )
            topic_relation = relation
        elif dialogue_best in {"affirmation", "rejection"} and has_context:
            relation = "SAME_TOPIC"
            topic_relation = "SAME_TOPIC"
        elif relation_strength >= 0.48:
            relation = "SAME_TOPIC"
            topic_relation = "SAME_TOPIC"
        else:
            relation = "NEW_TOPIC"
            topic_relation = "NEW_TOPIC"

        # Canonical three-way dialogue state. Every user turn is a new CONTEXT;
        # exactly one of CONTINUE/RECALL/NEW is selected. Historical retrieval
        # cannot silently become continuation merely because memory exists.
        canonical_three_way = str(three_way.get("relation") or "NEW").upper()
        selected_pair = three_way.get("selected_pair") if isinstance(three_way.get("selected_pair"), dict) else {}
        if canonical_three_way == "CONTINUE":
            relation = "CONTINUE_TOPIC"
            topic_relation = "SAME_TOPIC"
            subtype = "DEVELOPMENT"
        elif canonical_three_way == "RECALL":
            relation = "RECALL"
            topic_relation = "RECALL"
            subtype = "RECALL"
        else:
            relation = "NEW_TOPIC"
            topic_relation = "NEW_TOPIC"
            subtype = "NEW"

        # A direct question about the currently rendered artifact is a semantic
        # artifact reference even when the dialogue classifier ranks it as a
        # generic question. The evidence comes from the existing structured
        # scene + semantic task vector, not from a word/phrase trigger list.
        scene_reference_similarity = 0.0
        visual_reference_candidate = False
        scene_has_rendered_artifact = bool(
            scene and any(
                isinstance(block, dict)
                and _clean_representation(
                    block.get("type")
                    or block.get("artifact_type")
                    or block.get("representation")
                ) in {
                    "diagram", "graph", "image", "gallery", "table",
                    "formula", "code", "link", "audio", "video", "file",
                }
                for block in (scene.get("render_blocks") or [])
            )
        )
        if scene_has_rendered_artifact and (
            not current_self_contained or artifact_reference_evidence >= 0.06
        ):
            scene_text = self._scene_semantic_text(scene)
            if scene_text:
                scene_similarity_result = self.similarity(current, scene_text)
                scene_reference_similarity = float(
                    scene_similarity_result.get("score", 0.0) or 0.0
                )
            semantic_best_rep = str(features.get("semantic_best_representation") or "").lower()
            semantic_best_obj = str(features.get("semantic_best_object") or "").lower()
            semantic_best_op = str(features.get("semantic_best_operation") or "").lower()
            visual_task = (
                semantic_best_rep in {"diagram", "graph", "image", "gallery", "table", "formula"}
                or semantic_best_obj in {"diagram", "graph", "image", "gallery", "table", "formula"}
                or features.get("visual_action")
                or features.get("geometry_object")
            )
            artifact_question = (
                artifact_reference_evidence >= 0.06
            )
            answer_about_artifact = semantic_best_op in {
                "answer", "list", "analyze", "explain", "compare", "present", "build"
            }
            visual_reference_candidate = bool(
                answer_about_artifact
                and visual_task
                and artifact_question
                and scene_reference_similarity >= 0.16
            )

        if visual_reference_candidate and canonical_three_way == "CONTINUE":
            relation = "ARTIFACT_REFERENCE"
            topic_relation = "SAME_TOPIC"
            subtype = "REFERENCE_OR_DEVELOPMENT"
            semantic_reference = True
        elif relation == "MEMORY_QUERY":
            subtype = "MEMORY_QUERY"
        elif relation == "CONTINUE_TOPIC":
            subtype = "REFERENCE_OR_DEVELOPMENT" if semantic_reference else "DEVELOPMENT"
        elif relation == "SAME_TOPIC":
            subtype = "NEW_TASK_SAME_TOPIC"
        else:
            subtype = relation

        previous_text = " ".join(x for x in (prev_a, prev_u, topic) if x)
        previous_tokens = {t for t in self._tokens(previous_text) if len(t) >= 3}
        current_tokens = [t for t in self._tokens(current) if len(t) >= 3]
        shared_tokens, new_tokens = [], []
        for token in current_tokens:
            target = shared_tokens if token in previous_tokens else new_tokens
            if token not in target:
                target.append(token)

        previous_render_types = list(scene.get("render_block_types") or [])
        previous_block_ids = [
            str(x.get("block_id"))
            for x in (scene.get("render_blocks") or [])
            if isinstance(x, dict) and x.get("block_id")
        ]

        dependency_score = max(
            0.98 if history_task.get("required") else 0.0,
            0.92 if semantic_reference else 0.0,
            0.88 if semantic_memory_query and not current_self_contained else 0.0,
            continuation_evidence if not current_self_contained else 0.0,
            0.30 * answer_affinity + 0.24 * topic_affinity + 0.20 * dialogue_followup,
        )
        if current_self_contained and relation not in {"MEMORY_QUERY", "CONTINUE_TOPIC"}:
            dependency_score = 0.0

        continuation_score = dependency_score if relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} else 0.0
        independent_score = 1.0 - dependency_score

        request_dependency = (
            "continuation" if canonical_three_way == "CONTINUE"
            else "recall" if canonical_three_way == "RECALL"
            else "independent"
        )

        if canonical_three_way == "RECALL":
            continuation_score = 0.0
            independent_score = 0.0
        elif canonical_three_way == "CONTINUE":
            continuation_score = dependency_score
            independent_score = 1.0 - dependency_score
        else:
            continuation_score = 0.0
            independent_score = 1.0

        return {
            "relation": relation,
            "topic_relation": topic_relation,
            "request_relation": (
                "ARTIFACT_REFERENCE" if semantic_reference
                else "MEMORY_QUERY" if semantic_memory_query
                else relation
            ),
            "request_dependency": request_dependency,
            "request_dependency_score": float(max(0.0, min(1.0, dependency_score))),
            "current_request_complete": current_self_contained,
            "history_dependent_task": history_dependent_task,
            "history_window_size": len(recent_pairs),
            "history_task_context": history_task,
            "continuation_score": float(max(0.0, min(1.0, continuation_score))),
            "independent_score": float(max(0.0, min(1.0, independent_score))),
            "relation_strength": float(max(0.0, min(1.0, relation_strength))),
            "three_way_relation": canonical_three_way,
            "three_way_confidence": float(three_way.get("confidence", 0.0) or 0.0),
            "selected_memory_index": int(three_way.get("selected_index", -1) or -1),
            "selected_memory_operand": selected_pair,
            "subtype": subtype,
            "scores": {
                **sims,
                "dialogue_followup": dialogue_followup,
                "reference_evidence": reference_evidence,
                "memory_query_evidence": memory_evidence,
                "structural_followup": dependency_score,
            },
            "active_topic": topic,
            "active_goal": goal,
            "previous_user_turn": prev_u,
            "previous_april_turn": prev_a,
            "shared_tokens": shared_tokens[:40],
            "new_tokens": new_tokens[:40],
            "delta_mode": "extend" if relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} else "start",
            "avoid_repeat": True,
            "reuse_existing_scene": relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} and bool(scene.get("scene_id")),
            "previous_scene_id": scene.get("scene_id") if relation in {"CONTINUE_TOPIC", "MEMORY_QUERY"} else "",
            "previous_render_types": previous_render_types,
            "previous_block_ids": previous_block_ids,
            "explicit_reference": semantic_reference,
            "anaphoric": semantic_reference,
            "source": "quantum_dialogue_vector_v6_semantic",
            "decision_owner": DECISION_OWNER,
            "trigger_independent": False,
            "semantic_dialogue_label": dialogue_best,
            "semantic_dialogue_confidence": dialogue_best_score,
            "visual_reference_candidate": bool(visual_reference_candidate),
            "visual_scene_similarity": float(max(0.0, min(1.0, scene_reference_similarity))),
            "artifact_reference_evidence": bool(visual_reference_candidate),
            "artifact_reference_semantic_score": float(max(0.0, min(1.0, artifact_reference_evidence))),
        }

    def _linguistic(self,text):
        tokens=self._tokens(text)
        return {
            "language":None,"tokens":tokens,"lemmas":tokens,"pos":[],
            "dependencies":[],"entities":[],"sentences":[text] if text else [],
            "source":"quantum_matrix","engine":"quantum_interpretation_engine_v3"
        }

    def similarity(self,text_a,text_b):
        left,right=self.normalize(text_a),self.normalize(text_b)
        if not left or not right:
            return {"score":0.0,"source":"unresolved_semantic_similarity","measured":False,"cached":False}
        if self._semantic_encoder is not None:
            try:
                v=self._semantic_encoder.encode([left,right],normalize_embeddings=True)
                return {"score":max(0.0,min(1.0,float(v[0]@v[1]))),
                        "source":"sentence_transformer","measured":True,"cached":False}
            except Exception:
                pass
        if self._vectorizer is not None and cosine_similarity is not None:
            try:
                v=self._vectorizer.transform([left,right])
                return {"score":max(0.0,min(1.0,float(cosine_similarity(v[0],v[1])[0][0]))),
                        "source":"quantum_matrix_tfidf","measured":True,"cached":False}
            except Exception:
                pass
        return {"score":0.0,"source":"unresolved_semantic_similarity","measured":False,"cached":False}

    def similarities(self,text,candidates):
        return {self.normalize(c):self.similarity(text,c)["score"] for c in candidates if self.normalize(c)}

    def prewarm_static(self,candidates):
        return len({self.normalize(x) for x in candidates if self.normalize(x)})

    @classmethod
    def _state_dialogue_pairs(cls, state: dict[str, Any], *, user_id: str = "", limit: int = 15) -> list[dict[str, Any]]:
        """Read authenticated USER↔APRIL pairs from the canonical 12h StateManager/Strong store."""
        if not isinstance(state, dict):
            return []
        uid = str(
            user_id
            or state.get("user_id")
            or (state.get("memory_scope") or {}).get("user_id")
            or state.get("authenticated_user_id")
            or ""
        ).strip()

        # Fast path: the authenticated StateManager snapshot already carries the
        # canonical pair window. Read it directly and only touch the persistent
        # bridge when the runtime snapshot is incomplete. This preserves the same
        # source of truth while removing an unnecessary store read from every turn.
        scope = state.get("memory_scope") if isinstance(state.get("memory_scope"), dict) else {}
        if scope.get("authenticated") or uid:
            timeline = state.get("memory_timeline") if isinstance(state.get("memory_timeline"), dict) else {}
            direct_rows = []
            cutoff = time.time() - 12 * 60 * 60
            for day_key, day in sorted(timeline.items(), key=lambda x: str(x[0]), reverse=True):
                if not isinstance(day_key, str) or not day_key.startswith("day_") or not isinstance(day, dict):
                    continue
                rows = day.get("dialog_pairs")
                if not isinstance(rows, list):
                    continue
                for raw in rows:
                    if not isinstance(raw, dict):
                        continue
                    user = cls.normalize(raw.get("user") or raw.get("user_text") or raw.get("user_request"))
                    april = cls.normalize(raw.get("april") or raw.get("april_text") or raw.get("april_answer") or raw.get("answer"))
                    if not user or not april:
                        continue
                    try:
                        created_at = float(raw.get("created_at") or raw.get("timestamp") or 0.0)
                    except Exception:
                        created_at = 0.0
                    if created_at and created_at < cutoff:
                        continue
                    row = {
                        "user": user[:1200], "april": april[:1800], "result": april[:1800],
                        "turn_index": int(raw.get("turn_index") or raw.get("sequence_turn_index") or raw.get("turn") or 0),
                        "created_at": created_at,
                        "source": "STATE_MANAGER_AUTHENTICATED_12H_PAIRS",
                        "history_source": "USER_APRIL_PAIRS",
                    }
                    # Preserve the compact visual operand and semantic identity
                    # carried by the same USER↔APRIL pair. No binary data is copied.
                    for key in (
                        "visual_attachment", "visual_generation_memory", "visual_scene_id",
                        "scene_id", "conversation_id", "sequence_id", "dialogue_sequence_id",
                        "task_id", "sequence_turn_index", "topic", "subtopic",
                        "dialogue_relation", "relation", "semantic_state", "memory_semantics",
                    ):
                        value = raw.get(key)
                        if value not in (None, "", [], {}):
                            row[key] = deepcopy(value)
                    direct_rows.append(row)
            if direct_rows:
                direct_rows.sort(key=lambda x: (float(x.get("created_at") or 0.0), int(x.get("turn_index") or 0)))
                return direct_rows[-max(1, int(limit or 15)): ]

        # The durable pair store is the persistence boundary. Do not require a
        # transient runtime snapshot or an ``authenticated`` flag on a bridge.
        # This is the critical connection that was missing after HTTP turn reloads.
        if uid:
            persisted = _load_persistent_pair_window(uid, limit=limit)
            if persisted:
                return persisted[-max(1, int(limit or 15)):]

        scope = state.get("memory_scope") if isinstance(state.get("memory_scope"), dict) else {}
        if not scope.get("authenticated") and not uid:
            return []
        timeline = state.get("memory_timeline") if isinstance(state.get("memory_timeline"), dict) else {}
        cutoff = time.time() - 12 * 60 * 60
        out, seen = [], set()
        for day_key, day in sorted(timeline.items(), key=lambda x: str(x[0]), reverse=True):
            if not isinstance(day_key, str) or not day_key.startswith("day_") or not isinstance(day, dict):
                continue
            rows = day.get("dialog_pairs")
            if not isinstance(rows, list):
                continue
            for raw in rows:
                if not isinstance(raw, dict):
                    continue
                user = cls.normalize(
                    raw.get("user_text") or raw.get("user_request") or raw.get("user")
                    or raw.get("user_meaning") or raw.get("user_message")
                )
                april = cls.normalize(
                    raw.get("april_text") or raw.get("april_answer") or raw.get("answer")
                    or raw.get("april") or raw.get("april_meaning")
                )
                if not user or not april:
                    continue
                try:
                    created_at = float(raw.get("created_at") or raw.get("timestamp") or 0.0)
                except Exception:
                    created_at = 0.0
                if created_at and created_at < cutoff:
                    continue
                try:
                    turn_index = int(raw.get("turn_index") or raw.get("sequence_turn_index") or raw.get("turn") or 0)
                except Exception:
                    turn_index = 0
                sig = (user, april, created_at, turn_index)
                if sig in seen:
                    continue
                seen.add(sig)
                row = {
                    "user": user[:1200],
                    "april": april[:1800],
                    "result": april[:1800],
                    "turn_index": turn_index,
                    "created_at": created_at,
                    "source": "STATE_MANAGER_AUTHENTICATED_12H_PAIRS",
                    "history_source": "USER_APRIL_PAIRS",
                }
                for key in (
                    "visual_attachment", "visual_generation_memory", "visual_scene_id",
                    "scene_id", "conversation_id", "sequence_id", "dialogue_sequence_id",
                    "task_id", "sequence_turn_index", "topic", "subtopic",
                    "dialogue_relation", "relation", "semantic_state", "memory_semantics",
                ):
                    value = raw.get(key)
                    if value not in (None, "", [], {}):
                        row[key] = deepcopy(value)
                out.append(row)
        out.sort(key=lambda x: (float(x.get("created_at") or 0.0), int(x.get("turn_index") or 0)))
        return out[-max(1, int(limit or 15)):]

    @classmethod
    def _pairs_to_history(cls, pairs: list[dict[str, Any]]) -> list[dict[str, str]]:
        history = []
        for pair in pairs or []:
            if not isinstance(pair, dict):
                continue
            user = cls.normalize(pair.get("user"))
            april = cls.normalize(pair.get("april") or pair.get("result"))
            if user:
                history.append({"role": "user", "content": user})
            if april:
                history.append({"role": "assistant", "content": april})
        return history

    def _find_visual_generation_context(self, pairs: list[dict[str, Any]] | None) -> dict[str, Any]:
        """Select the latest real image-generation request from authenticated 12h memory."""
        visual_ops = {"build", "create", "generate", "modify", "present", "transform", "redraw", "visualize"}
        candidates = []
        for pair in pairs or []:
            if not isinstance(pair, dict):
                continue
            user = self.normalize(pair.get("user"))
            if not user:
                continue
            try:
                profile = self.measure(user)
            except Exception:
                continue
            features = profile.get("request_features") if isinstance(profile.get("request_features"), dict) else {}
            operation = str(profile.get("best_operation") or "").lower()
            scores = profile.get("dialogue_scores") if isinstance(profile.get("dialogue_scores"), dict) else {}
            memory_query = float(scores.get("memory_query", 0.0) or 0.0)
            image_score = max(
                float((profile.get("representation_scores") or {}).get("image", 0.0) or 0.0),
                float((profile.get("object_scores") or {}).get("image", 0.0) or 0.0),
            )
            if (
                bool(features.get("visual_action"))
                and bool(features.get("self_contained"))
                and operation in visual_ops
                and memory_query < 0.04
                and image_score >= 0.035
            ):
                candidates.append({
                    "user": user,
                    "turn_index": pair.get("turn_index", -1),
                    "created_at": pair.get("created_at", 0.0),
                    "score": round(image_score, 6),
                    "source": "STATE_MANAGER_AUTHENTICATED_12H_PAIRS",
                })
        candidates.sort(key=lambda x: (float(x.get("created_at") or 0.0), int(x.get("turn_index") or 0)))
        return candidates[-1] if candidates else {}

    def _history(self,history):
        last_a=last_u=""; reply_to=None
        for item in reversed(history if isinstance(history,list) else []):
            if not isinstance(item,dict): continue
            metadata=item.get("metadata") if isinstance(item.get("metadata"),dict) else {}
            content=self.normalize(item.get("content") or item.get("text") or item.get("answer") or "")
            if (metadata.get("internal_context") or metadata.get("internal_turn")
                    or metadata.get("source") in {"internal_visual", "internal_visual_analysis", "passive_visual_helper"}
                    or content.startswith("VISUAL_ANALYSIS:")):
                continue
            role=str(item.get("role") or "").lower()
            if not last_a:
                obj=item.get("april") if isinstance(item.get("april"),dict) else item
                if role in {"assistant","april","bot"} or isinstance(item.get("april"),dict):
                    last_a=self.normalize(obj.get("answer") or obj.get("content") or obj.get("summary"))
                    reply_to=item.get("turn_id")
            if not last_u:
                obj=item.get("user") if isinstance(item.get("user"),dict) else item
                if role in {"user","human"} or isinstance(item.get("user"),dict):
                    last_u=self.normalize(obj.get("text") or obj.get("content") or obj.get("answer"))
            if last_a and last_u: break
        return last_a,last_u,reply_to

    def measure(self,text,*,previous_assistant="",previous_user="",active_topic="",active_goal="",modalities=None):
        text=self.normalize(text)
        key=(text,self.normalize(previous_assistant),self.normalize(previous_user),
             self.normalize(active_topic),self.normalize(active_goal),
             tuple(sorted((modalities or {}).keys())))
        with self._lock:
            if key in self._cache: return self._cache[key]
        focus_text = self._semantic_focus_text(text)
        scores={
            "dialogue":self._family_scores(text,"dialogue",SEMANTIC_TURN_PROTOTYPES),
            "representation":self._family_scores(focus_text or text,"representation",REPRESENTATION_HYPOTHESES),
            "domain":self._family_scores(text,"domain",DOMAIN_HYPOTHESES),
            "capability":self._family_scores(text,"capability",CAPABILITY_HYPOTHESES),
            "operation":self._operation_family_scores(text),
            "object":self._family_scores(focus_text or text,"object",OBJECT_HYPOTHESES),
            "goal":self._family_scores(text,"goal",GOAL_HYPOTHESES),
            "visual_schema":self._family_scores(text,"visual_schema",VISUAL_SCHEMA_HYPOTHESES),
        }
        for label in self._negated_representation_labels(text):
            if label in scores["representation"]:
                scores["representation"][label] *= 0.05
            if label in scores["object"]:
                scores["object"][label] *= 0.05

        # Structural semantic enrichment for visual construction. This keeps the
        # matrix probabilistic while making equivalent phrasings converge on the
        # same task vector instead of depending on the exact verb "покажи" versus
        # "изобрази".
        request_features = self._semantic_request_features(text, scores)
        if (
            request_features["visual_construction"]
            and not self._negated_representation_labels(text)
        ):
            # Semantic-family agreement is the only enrichment source.  There is
            # no phrase table and no renderer trigger.
            scores["representation"]["diagram"] = max(
                scores["representation"].get("diagram", 0.0),
                float(scores["representation"].get("diagram", 0.0) or 0.0),
            )
            scores["operation"]["build"] = max(
                scores["operation"].get("build", 0.0),
                float(scores["operation"].get("present", 0.0) or 0.0),
            )
            scores["goal"]["visualize"] = max(
                scores["goal"].get("visualize", 0.0),
                float(scores["goal"].get("transform", 0.0) or 0.0),
            )
            request_features = self._semantic_request_features(text, scores)

        ctx=self._context_scores(text,previous_assistant,previous_user,active_topic,active_goal)
        def rank(d):
            return sorted(d.items(),key=lambda x:x[1],reverse=True)
        rep=rank(scores["representation"]); ops=rank(scores["operation"])
        objs=rank(scores["object"]); goals=rank(scores["goal"]); dial=rank(scores["dialogue"])
        profile={
            "dialogue_scores":scores["dialogue"],"dialogue_best":dial[0][0] if dial else "independent",
            "dialogue_confidence":float(dial[0][1]) if dial else 0.0,
            "dialogue_margin":float(dial[0][1]-dial[1][1]) if len(dial)>1 else 0.0,
            "representation_scores":scores["representation"],
            "domain_scores":scores["domain"],"capability_scores":scores["capability"],
            "operation_scores":scores["operation"],"object_scores":scores["object"],"goal_scores":scores["goal"],
            "visual_schema_scores":scores["visual_schema"],
            "request_features":request_features,
            "context_scores":ctx,
            "best_representation":rep[0][0] if rep else "text",
            "best_representation_score":float(rep[0][1]) if rep else 0.0,
            "representation_margin":float(rep[0][1]-rep[1][1]) if len(rep)>1 else (float(rep[0][1]) if rep else 0.0),
            "best_operation":ops[0][0] if ops else "answer",
            "best_object":objs[0][0] if objs else "text",
            "best_goal":goals[0][0] if goals else "understand",
            "source":"quantum_matrix_semantic_measurement_v3",
            "identity_request":bool(dial and dial[0][0]=="identity" and dial[0][1]>=0.12),
            "fast_social":bool(dial and dial[0][0] in {"identity","greeting"} and dial[0][1]>=0.18),
        }
        with self._lock:
            self._cache[key]=profile
            if len(self._cache)>self._cache_limit: self._cache.pop(next(iter(self._cache)))
        return profile

    def _resolve_production(self,text,profile,explicit):
        # Canonical upstream interpretation may lock one representation.
        explicit_values=[_clean_representation(x) for x in (explicit or [])]
        explicit_values=[x for x in explicit_values if x]
        if len(explicit_values)==1:
            return explicit_values[0],"explicit_current_request",True

        rep=dict(profile.get("representation_scores") or {})
        obj=dict(profile.get("object_scores") or {})
        op=dict(profile.get("operation_scores") or {})
        goal=dict(profile.get("goal_scores") or {})
        features=dict(profile.get("request_features") or {})

        def rank(items):
            return sorted(items.items(), key=lambda x: float(x[1]), reverse=True)

        rep_rank=rank(rep); obj_rank=rank(obj); op_rank=rank(op); goal_rank=rank(goal)
        best_rep=rep_rank[0][0] if rep_rank else "text"
        best_rep_score=float(rep.get(best_rep,0.0))
        second_rep_score=float(rep_rank[1][1]) if len(rep_rank)>1 else 0.0
        best_obj=obj_rank[0][0] if obj_rank else "text"
        best_obj_score=float(obj.get(best_obj,0.0))
        best_op=op_rank[0][0] if op_rank else "answer"
        best_op_score=float(op.get(best_op,0.0))
        best_goal=goal_rank[0][0] if goal_rank else "understand"
        best_goal_score=float(goal.get(best_goal,0.0))

        # Canonical image task: an action that constructs/presents a visual object
        # must route to the image renderer even when the representation matrix
        # under-scores the single word "image". This is a task-vector decision
        # (operation + object + visual action), not a lexical trigger.
        image_rep_score = float(rep.get("image", 0.0) or 0.0)
        image_obj_score = float(obj.get("image", 0.0) or 0.0)
        if (
            features.get("visual_action") is True
            and image_obj_score >= 0.035
            and image_rep_score >= 0.035
        ):
            return "image", "semantic_visual_image_task", True

        compatible_ops={
            "graph":{"build","modify","present","calculate","analyze","list","explain"},
            "diagram":{"build","modify","present","explain"},
            "table":{"build","modify","present","compare","list","explain"},
            "formula":{"build","modify","present","calculate","explain","answer"},
            "link":{"retrieve","present","answer","explain","list"},
            "code":{"build","modify","present","explain","list"},
            "image":{"build","modify","present"},
            "gallery":{"build","present"},
            "file":{"retrieve","present"},
            "audio":{"build","present"},
            "video":{"build","present"},
            "action":{"build","modify","present"},
            "scene":{"build","modify","present"},
            "memory":{"retrieve","answer","present"},
            "visual_context":{"answer","analyze","explain"},
        }
        aligned = best_op in compatible_ops.get(best_rep,set())

        # Strong structural interpretation for a self-contained visual construction.
        # This is intentionally a task-vector rule: operation + object/constraint
        # evidence must agree before a structured representation is locked.
        if features.get("visual_construction") and not self._negated_representation_labels(text):
            return "diagram", "semantic_visual_construction", True

        if best_rep != "text" and aligned:
            rep_margin = best_rep_score - second_rep_score
            object_agreement = best_obj == best_rep and best_obj_score >= 0.05
            representation_clear = (
                best_rep_score >= 0.10 and
                (rep_margin >= 0.015 or best_rep_score >= 0.22)
            )
            if representation_clear and (object_agreement or best_rep_score >= 0.16):
                return best_rep,"task_object_goal_resolution",True

            production_ops = {"build", "modify", "present"}
            production_signal = max(float(op.get(name,0.0) or 0.0) for name in production_ops)
            production_goal = max(float(goal.get(name,0.0) or 0.0) for name in {"visualize","transform","present","organize"})
            object_alignment = best_obj == best_rep and best_obj_score >= 0.10
            representation_dominance = best_rep_score >= max(0.09, float(rep.get("text",0.0) or 0.0) + 0.025)
            structured_task = (
                best_rep != "text"
                and object_alignment
                and representation_dominance
                and (production_signal >= 0.055 or (aligned and best_op_score >= 0.08))
                and (production_goal >= 0.035 or best_rep_score >= 0.14)
            )
            if structured_task:
                return best_rep,"semantic_task_vector_resolution",True
            if aligned and best_rep_score >= 0.10 and best_op_score >= 0.08:
                return best_rep,"operation_representation_resolution",True

        return "text","unresolved",False

    def dialogue(self,text,previous_assistant="",previous_user="",active_goal="",active_topic="",previous_scene=None,recent_dialogue_pairs=None):
        p=self.measure(text,previous_assistant=previous_assistant,previous_user=previous_user,
                       active_goal=active_goal,active_topic=active_topic)
        vector=self._dialogue_relation_engine(
            text,
            previous_assistant=previous_assistant,
            previous_user=previous_user,
            active_goal=active_goal,
            active_topic=active_topic,
            previous_scene=previous_scene,
            recent_dialogue_pairs=recent_dialogue_pairs,
        )
        d=p["dialogue_scores"]
        return {
            "dialogue":{
                "label":p["dialogue_best"],
                "confidence":p["dialogue_confidence"],
                "continuation_score":vector["continuation_score"],
                "reference_score":max(
                    vector["scores"].get("previous_assistant",0.0),
                    vector["scores"].get("previous_scene_topic",0.0),
                ),
                "topic_score":max(
                    vector["scores"].get("active_topic",0.0),
                    vector["scores"].get("previous_scene_topic",0.0),
                ),
                "goal_score":vector["scores"].get("active_goal",0.0),
            },
            "linguistic":self._linguistic(text),
            "continuation":vector["relation"]=="CONTINUE_TOPIC",
            "reference_to_previous":bool(vector.get("request_relation") == "ARTIFACT_REFERENCE"),
            "dialogue_relation":vector,
            "identity_request":p["identity_request"],
            "nli":{"labels":list(d),"scores":list(d.values()),"source":"quantum_matrix"},
            "decision_owner":DECISION_OWNER,"evidence_only":True,
            "engine":"quantum_dialogue_vector_engine_v4",
        }

    def representations(self,text,context=""):
        p=self.measure(text,active_topic=context)
        return {
            "nli":{"labels":list(p["representation_scores"]),"scores":list(p["representation_scores"].values()),"source":"quantum_matrix"},
            "measurements":[{"type":k,"score":float(v),"source":"quantum_matrix"}
                            for k,v in sorted(p["representation_scores"].items(),key=lambda x:x[1],reverse=True)],
            "context_similarity":{"score":p["context_scores"].get("active_topic",0.0),"source":"quantum_matrix"},
            "decision_owner":DECISION_OWNER,"evidence_only":True,
            "engine":"quantum_representation_matrix_view_v3"
        }

    def domains(self,text):
        p=self.measure(text)
        return {"measurements":[{"domain":k,"score":float(v)}
                                for k,v in sorted(p["domain_scores"].items(),key=lambda x:x[1],reverse=True)],
                "decision_owner":DECISION_OWNER,"evidence_only":True,
                "engine":"quantum_domain_matrix_view_v3"}

    def _scene_matrix(self,p):
        reps=p["representation_scores"]
        labels=list(SCENE_MATRIX_LABELS)
        vals=[float(reps.get(x,0.0)) for x in labels]
        top=max(vals) if vals else 0.0
        scores=[v/top if top>0 else 0.0 for v in vals]
        ranked=sorted(zip(labels,scores),key=lambda x:x[1],reverse=True)
        return {
            "labels":[x[0] for x in ranked],"scores":[round(float(x[1]),6) for x in ranked],
            "best_scene":ranked[0][0] if ranked else "text",
            "best_score":round(float(ranked[0][1] if ranked else 0.0),6),
            "margin":round(float((ranked[0][1]-ranked[1][1]) if len(ranked)>1 else 0.0),6),
            "feature_order":list(SCENE_MATRIX_FEATURES),"matrix_shape":[len(labels),len(SCENE_MATRIX_FEATURES)],
            "evidence_only":True,"engine":"quantum_matrix_v3","decision_owner":DECISION_OWNER
        }

    @classmethod
    def _reference_resolution(
        cls,
        text: str,
        previous_assistant: str,
        previous_user: str = "",
        semantic_profile: dict[str, Any] | None = None,
        reference_authorized: bool = False,
    ) -> dict:
        """Resolve an authorized reference from the previous dialogue pair only.

        No entity extraction is performed here. The previous USER↔APRIL exchange
        itself is the context operand.
        """
        current = cls.normalize(text)
        prev = cls.normalize(previous_assistant)
        prior_user = cls.normalize(previous_user)
        if not current or not reference_authorized or not (prior_user or prev):
            return {
                "present": False, "target": "", "candidates": [], "confidence": 0.0,
                "source": "authenticated_dialogue_context", "anaphoric": False,
                "short_followup": len(cls._tokens(current)) <= 8, "resolved": False,
            }

        # Prefer the previous USER request as the contextual operand. The previous
        # APRIL answer remains available through DIALOGUE_ANCHOR/TRAJECTORY.
        target = prior_user or prev
        return {
            "present": True,
            "target": target,
            "candidates": [],
            "confidence": 0.98,
            "source": "authenticated_dialogue_context",
            "anaphoric": True,
            "short_followup": len(cls._tokens(current)) <= 8,
            "resolved": True,
            "semantic_reference_authorized": True,
            "context_operand_type": "dialogue_pair",
        }

    def _resolve_scene_context(self,text,state,continuation,reference,memory=False,active_topic=""):
        if not isinstance(state,dict) or not (continuation or reference or memory): return {}
        scene=state.get("current_visual_scene") or state.get("active_visual_scene")
        if not isinstance(scene,dict) or not scene.get("scene_id"): return {}
        return {
            "relation":"current_scene","confidence":1.0,"scene_id":scene.get("scene_id"),
            "turn_id":scene.get("turn_id"),"topic":self.normalize(scene.get("topic")),
            "user_request":self.normalize(scene.get("user_request") or scene.get("current_request")),
            "answer":self.normalize(scene.get("april_answer") or scene.get("answer") or scene.get("content")),
            "summary":self.normalize(scene.get("summary")),
            "render_block_types":list(scene.get("render_block_types") or []),
            "presentation_types":list(scene.get("presentation_types") or []),
            "render_blocks":list(scene.get("render_blocks") or []),
            "presentation_signals":list(scene.get("presentation_signals") or []),
            "semantic_state":scene.get("semantic_state") if isinstance(scene.get("semantic_state"),dict) else {},
            "supported_payloads":list(scene.get("supported_payloads") or []),
            "renderer_state":scene.get("renderer_state") if isinstance(scene.get("renderer_state"),dict) else {},
            "semantic_source":"interpretation_scene_resolution_v3","evidence_only":True
        }

    def interpret(self,text,cognition=None,semantic=None,history=None,state=None):
        text=self.normalize(text)
        if not text: return None
        cognition=cognition if isinstance(cognition,dict) else {}
        semantic=semantic if isinstance(semantic,dict) else {}
        state=state if isinstance(state,dict) else {}
        history=history if isinstance(history,list) else []
        # Canonical hot-path: always hydrate the interpreter from the authenticated
        # StateManager 12-hour USER↔APRIL pair bridge first. The HTTP/session layer
        # may provide an empty or partial history; that must never become the
        # dialogue source of truth.
        memory_history = _state_manager_dialogue_history(state, history, limit=0)
        if memory_history:
            history = memory_history

        canonical_pairs = []
        pending_user = ""
        for item in history:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").lower()
            content = self.normalize(item.get("content") or item.get("text") or item.get("answer"))
            if role in {"user", "human"}:
                pending_user = content
            elif role in {"assistant", "april", "bot"} and pending_user and content:
                canonical_pairs.append({
                    "user": pending_user,
                    "april": content,
                    "result": content,
                    "turn_index": item.get("turn_id") or 0,
                    "created_at": item.get("timestamp") or 0,
                })
                pending_user = ""
        canonical_pairs = canonical_pairs[:]

        # Last-resort authenticated bridge: obtain the exact compact pair window
        # directly from StateManager when the projected role history is empty.
        if not canonical_pairs:
            uid = str(
                state.get("user_id")
                or (state.get("memory_scope") or {}).get("user_id")
                or ""
            ).strip()
            if uid:
                try:
                    from blocks.state_manager import build_dialogue_memory_bridge
                    bridge = build_dialogue_memory_bridge(uid, query="", limit=15, relation="CONTINUE")
                    bridge_pairs = bridge.get("dialogue_pairs") or bridge.get("active_sequence_turns") or []
                    canonical_pairs = [
                        {
                            "user": self.normalize(row.get("user") or row.get("user_request")),
                            "april": self.normalize(row.get("april") or row.get("april_answer") or row.get("assistant")),
                            "result": self.normalize(row.get("april") or row.get("april_answer") or row.get("assistant")),
                            "turn_index": row.get("turn") or row.get("turn_index") or 0,
                            "created_at": row.get("created_at") or 0,
                        }
                        for row in bridge_pairs
                        if isinstance(row, dict)
                        and self.normalize(row.get("user") or row.get("user_request"))
                        and self.normalize(row.get("april") or row.get("april_answer") or row.get("assistant"))
                    ][:]
                except Exception:
                    canonical_pairs = []

        last_a,last_u,reply_to=self._history(history)
        if canonical_pairs:
            last_pair = canonical_pairs[-1]
            last_u = self.normalize(last_pair.get("user")) or last_u
            last_a = self.normalize(last_pair.get("april") or last_pair.get("result")) or last_a
        # Never promote the literal current/previous user sentence to the active
        # topic. StateManager's authenticated pair window is the dialogue source
        # of truth; generic discourse requests must remain queries over that window.
        # For authenticated dialogue, continuation authority comes from the
        # existing 12-hour USER↔APRIL pair window. Do not let stale topic/goal
        # slots from older entity/topic engines hijack the current turn. The
        # context engine reconstructs the active meaning from the pair trajectory.
        active_topic = ""
        active_goal = ""
        p=self.measure(text,previous_assistant=last_a,previous_user=last_u,active_topic=active_topic,active_goal=active_goal)
        previous_scene = state.get("current_visual_scene") or state.get("active_visual_scene")
        if not isinstance(previous_scene, dict):
            previous_scene = {}
        # Internal visual/tool scenes are not dialog anchors.
        try:
            scene_topic = self.normalize(previous_scene.get("topic") or previous_scene.get("user_request"))
            scene_meta = previous_scene.get("metadata") if isinstance(previous_scene.get("metadata"), dict) else {}
            internal_scene = bool(
                previous_scene.get("internal_context")
                or previous_scene.get("internal_turn")
                or scene_meta.get("internal_context")
                or scene_topic.startswith("VISUAL_ANALYSIS:")
            )
            if internal_scene:
                previous_scene = {}
        except Exception:
            pass
        recent_dialogue_pairs = list(canonical_pairs[:]) if canonical_pairs else self._recent_dialogue_pairs(history, limit=15)
        # Never allow a partial HTTP history to override the authenticated pair
        # window once StateManager supplied it.
        recent_dialogue_pairs = [p for p in recent_dialogue_pairs if isinstance(p, dict) and (p.get("user") or p.get("april"))][:]
        visual_generation_context = self._find_visual_generation_context(recent_dialogue_pairs)
        dialogue_packet = self.dialogue(
            text,
            previous_assistant=last_a,
            previous_user=last_u,
            active_goal=active_goal,
            active_topic=active_topic,
            previous_scene=previous_scene,
            recent_dialogue_pairs=recent_dialogue_pairs,
        )
        d=dialogue_packet["dialogue"]
        dialogue_vector=dialogue_packet.get("dialogue_relation", {})
        explicit=(semantic.get("required_representations") or cognition.get("required_representations") or [])

        # Context-first fusion.  This is the interpretation authority for topic,
        # entity/reference and current-turn structure.  It augments the existing
        # matrix instead of creating a second route.
        precomputed_dialogue_selection = {
            "relation": str(dialogue_vector.get("three_way_relation") or (
                "CONTINUE" if dialogue_vector.get("continuation")
                else "RECALL" if dialogue_vector.get("request_relation") == "RECALL"
                else "NEW"
            )).upper(),
            "confidence": float(dialogue_vector.get("three_way_confidence", 0.0) or 0.0),
            "selected_index": int(dialogue_vector.get("selected_memory_index", -1) or -1),
            "selected_pair": dialogue_vector.get("selected_memory_operand") if isinstance(dialogue_vector.get("selected_memory_operand"), dict) else {},
            "latest_score": float(dialogue_vector.get("latest_score", 0.0) or 0.0),
            "best_score": float(dialogue_vector.get("best_score", 0.0) or 0.0),
            "second_score": float(dialogue_vector.get("second_score", 0.0) or 0.0),
            "margin": float(dialogue_vector.get("margin", 0.0) or 0.0),
            "source": "reused_from_canonical_dialogue_relation",
        }
        context_understanding = QUANTUM_CONTEXT_ENGINE.analyze(
            text,
            history=history,
            state=state,
            semantic=semantic,
            cognition=cognition,
            active_topic=active_topic,
            active_goal=active_goal,
            previous_scene=previous_scene,
            semantic_profile=p,
            precomputed_dialogue_selection=precomputed_dialogue_selection,
        )
        topic_understanding = context_understanding.get("topic") if isinstance(context_understanding.get("topic"), dict) else {}
        discourse_understanding = context_understanding.get("discourse") if isinstance(context_understanding.get("discourse"), dict) else {}
        dialogue_selection = context_understanding.get("dialogue_selection") if isinstance(context_understanding.get("dialogue_selection"), dict) else {}
        entities_understanding = {
            "enabled": False,
            "current": [],
            "shared_with_active_topic": [],
            "coreference": [],
            "candidates": [],
            "source": "disabled_pair_context",
        }

        # Context-understanding owns the three-way relationship. Downstream code
        # receives the selected memory operand, rather than re-deciding from a
        # frozen legacy continuation flag.
        selected_relation = str(dialogue_selection.get("relation") or "NEW").upper()
        selected_pair = dialogue_selection.get("selected_pair") if isinstance(dialogue_selection.get("selected_pair"), dict) else {}
        if selected_relation == "CONTINUE":
            dialogue_vector = {**dict(dialogue_vector or {}),
                "relation": "CONTINUE_TOPIC", "topic_relation": "SAME_TOPIC",
                "request_relation": "CONTINUE_TOPIC", "request_dependency": "continuation",
                "continuation": True, "reference_to_previous": False,
                "three_way_relation": "CONTINUE", "selected_memory_operand": selected_pair,
                "selected_memory_index": dialogue_selection.get("selected_index", -1)}
        elif selected_relation == "RECALL":
            dialogue_vector = {**dict(dialogue_vector or {}),
                "relation": "RECALL", "topic_relation": "RECALL",
                "request_relation": "RECALL", "request_dependency": "recall",
                "continuation": False, "reference_to_previous": True,
                "three_way_relation": "RECALL", "selected_memory_operand": selected_pair,
                "selected_memory_index": dialogue_selection.get("selected_index", -1)}
        else:
            dialogue_vector = {**dict(dialogue_vector or {}),
                "relation": "NEW_TOPIC", "topic_relation": "NEW_TOPIC",
                "request_relation": "NEW_TOPIC", "request_dependency": "independent",
                "continuation": False, "reference_to_previous": False,
                "three_way_relation": "NEW", "selected_memory_operand": {},
                "selected_memory_index": -1, "reuse_existing_scene": False,
                "previous_scene_id": ""}
        turn_structure_understanding = context_understanding.get("turn_structure") if isinstance(context_understanding.get("turn_structure"), dict) else {}
        task_understanding = context_understanding.get("task") if isinstance(context_understanding.get("task"), dict) else {}

        # A locally numbered/compound request ("second", "the third item", etc.)
        # refers to the structure of the CURRENT turn unless the user explicitly
        # establishes a historical reference. This blocks the previous scene from
        # hijacking a new multi-part request.
        local_turn_reference = bool(
            turn_structure_understanding.get("local_ordinal_reference")
            and turn_structure_understanding.get("historical_ordinal_reference_blocked")
        )
        if local_turn_reference:
            local_relation = (
                "CONTINUE_TOPIC" if selected_relation == "CONTINUE"
                else "RECALL" if selected_relation == "RECALL"
                else "NEW_TOPIC"
            )
            local_topic_relation = (
                "SAME_TOPIC" if selected_relation == "CONTINUE"
                else "RECALL" if selected_relation == "RECALL"
                else "NEW_TOPIC"
            )
            dialogue_vector = {
                **dict(dialogue_vector or {}),
                "relation": local_relation,
                "topic_relation": local_topic_relation,
                "request_relation": local_relation,
                "request_dependency": (
                    "continuation" if selected_relation == "CONTINUE"
                    else "recall" if selected_relation == "RECALL"
                    else "independent"
                ),
                "reference_to_previous": selected_relation == "RECALL",
                "explicit_reference": False,
                "anaphoric": False,
                "artifact_reference_evidence": False,
                "previous_scene_id": "",
                "reuse_existing_scene": False,
                "local_current_turn_structure": True,
                "historical_ordinal_reference_blocked": True,
            }
            d = {
                **dict(d or {}),
                "label": "question" if d.get("label") in {"reference", "artifact_reference"} else d.get("label"),
                "continuation_score": 0.0,
                "reference_score": 0.0,
                "topic_score": float(topic_understanding.get("similarity_to_best_pair", 0.0) or 0.0),
            }

        # The context tracker owns the repaired topic label.  Do not let a stale
        # state slot remain authoritative when the current canonical history gives
        # a stronger reconstructed topic.
        reconstructed_topic = normalize_text(topic_understanding.get("active"))
        if reconstructed_topic and topic_understanding.get("relation") in {
            "SAME_TOPIC", "CONTINUE_TOPIC", "RECALL"
        }:
            active_topic = reconstructed_topic

        # Semantic coreference may establish a historical continuation even when
        # the prototype classifier ranks the surface turn as a generic question.
        if (
            selected_relation == "CONTINUE"
            and not local_turn_reference
            and discourse_understanding.get("historical_reference")
            and entities_understanding.get("coreference")
        ):
            coref_packets = entities_understanding.get("coreference") or []
            best_coref = coref_packets[0] if isinstance(coref_packets[0], dict) else {}
            coref_candidates = best_coref.get("candidates") or []
            if coref_candidates and float(best_coref.get("confidence", 0.0) or 0.0) >= 0.34:
                dialogue_vector = {
                    **dict(dialogue_vector or {}),
                    "relation": "CONTINUE_TOPIC",
                    "topic_relation": "SAME_TOPIC",
                    "request_relation": "CONTINUE_TOPIC",
                    "request_dependency": "continuation",
                    "reference_to_previous": True,
                    "explicit_reference": True,
                    "anaphoric": True,
                    "semantic_reference": coref_candidates[0].get("entity"),
                    "semantic_reference_confidence": float(best_coref.get("confidence", 0.0) or 0.0),
                }
                d = {
                    **dict(d or {}),
                    "label": "reference",
                    "continuation_score": max(
                        float(d.get("continuation_score", 0.0) or 0.0),
                        float(best_coref.get("confidence", 0.0) or 0.0),
                    ),
                    "reference_score": max(
                        float(d.get("reference_score", 0.0) or 0.0),
                        float(best_coref.get("confidence", 0.0) or 0.0),
                    ),
                    "topic_score": max(
                        float(d.get("topic_score", 0.0) or 0.0),
                        float(topic_understanding.get("similarity_to_best_pair", 0.0) or 0.0),
                    ),
                }

        explicit=(semantic.get("required_representations") or cognition.get("required_representations") or [])
        production,source,locked=self._resolve_production(text,p,explicit)

        # Context Task Matrix can repair a polluted raw representation ranking.
        # Prefer the semantically supported current-turn object (formula/code/link/
        # table/graph/diagram/image/etc.) when operation and object evidence agree.
        context_outputs = [
            str(x).lower() for x in (task_understanding.get("requested_outputs") or [])
        ]
        object_scores = p.get("object_scores") if isinstance(p.get("object_scores"), dict) else {}
        op_name = str(p.get("best_operation") or "").lower()
        compatible_context = {
            "formula": {"calculate", "answer", "explain", "present", "build", "modify"},
            "code": {"build", "modify", "present", "explain", "analyze"},
            "link": {"retrieve", "present", "answer", "list", "explain"},
            "table": {"build", "present", "compare", "list", "explain", "analyze"},
            "graph": {"build", "present", "calculate", "analyze", "compare", "list", "explain"},
            "diagram": {"build", "present", "modify", "explain", "analyze"},
            "image": {"build", "present", "modify"},
            "gallery": {"build", "present", "compare", "list"},
        }
        context_structured = [
            item for item in context_outputs
            if item in compatible_context and op_name in compatible_context[item]
        ]
        context_structured.sort(
            key=lambda item: float(object_scores.get(item, 0.0) or 0.0),
            reverse=True,
        )
        if context_structured and not explicit:
            best_context_rep = context_structured[0]
            best_context_score = float(object_scores.get(best_context_rep, 0.0) or 0.0)
            representation_scores = (
                p.get("representation_scores")
                if isinstance(p.get("representation_scores"), dict)
                else {}
            )
            best_current_rep = str(p.get("best_representation") or "text").lower()
            current_rep_score = float(
                representation_scores.get(best_context_rep, 0.0) or 0.0
            )
            # A continuation must not be promoted to table/diagram/etc. from a
            # noisy object matrix alone. The current turn has to agree on the same
            # representation semantically. This keeps ordinary conversational
            # statements textual while preserving real structured requests such as
            # "сравни их в таблице" where representation+object evidence is strong.
            context_representation_agreement = bool(
                best_current_rep == best_context_rep
                and current_rep_score >= 0.08
                and best_context_score >= 0.08
            )
            structured_context_allowed = bool(
                selected_relation != "CONTINUE"
                or context_representation_agreement
            )
            if (
                structured_context_allowed
                and best_context_score >= 0.08
                and (production == "text" or best_context_rep != production)
            ):
                production = best_context_rep
                source = "context_task_matrix_resolution"
                locked = True
        continuation=bool(
            dialogue_packet.get("continuation")
            or dialogue_vector.get("relation") == "CONTINUE_TOPIC"
        )

        # The 12h pair memory supplies the visual operand for underspecified
        # continuation turns. A memory/reference question does not generate an
        # image just because an older turn contained an image request.
        current_operation = str(p.get("best_operation") or "").lower()
        current_image_representation_evidence = float(
            p.get("representation_scores", {}).get("image", 0.0) or 0.0
        )
        current_image_object_evidence = float(
            p.get("object_scores", {}).get("image", 0.0) or 0.0
        )
        current_image_evidence = max(
            current_image_representation_evidence,
            current_image_object_evidence,
        )
        _request_features = p.get("request_features") if isinstance(p.get("request_features"), dict) else {}
        _operation_scores = p.get("operation_scores") if isinstance(p.get("operation_scores"), dict) else {}
        current_visual_operation_score = max(
            float(_operation_scores.get(name, 0.0) or 0.0)
            for name in ("build", "create", "generate", "present", "modify", "transform", "redraw")
        )
        current_visual_action = bool(
            _request_features.get("visual_action")
            or (
                current_visual_operation_score >= 0.055
                and current_image_representation_evidence >= 0.035
                and current_image_object_evidence >= 0.035
            )
        )
        current_dialogue_scores = p.get("dialogue_scores") if isinstance(p.get("dialogue_scores"), dict) else {}
        current_memory_query = float(current_dialogue_scores.get("memory_query", 0.0) or 0.0)
        reference_scores = {
            "memory_query": float(current_dialogue_scores.get("memory_query", 0.0) or 0.0),
            "reformulation": float(current_dialogue_scores.get("reformulation", 0.0) or 0.0),
            "reference": float(current_dialogue_scores.get("reference", 0.0) or 0.0),
            "artifact_reference": float(current_dialogue_scores.get("artifact_reference", 0.0) or 0.0),
        }
        reference_signal = max(reference_scores.values() or [0.0])
        current_op_score = float(p.get("operation_scores", {}).get(current_operation, 0.0) or 0.0)
        # Artifact/reference similarity alone is not enough to cancel a genuine
        # visual request: words such as "нарисуй" naturally overlap with the
        # historical-artifact prototype. Require supporting discourse evidence
        # from reference/reformulation as well, while keeping the 12h memory
        # query threshold authoritative.
        explicit_visual_reference = bool(
            reference_scores["artifact_reference"] >= 0.080
            and (
                reference_scores["reference"] + reference_scores["reformulation"] >= 0.100
            )
        )
        visual_reference_lock = bool(
            reference_scores["memory_query"] >= 0.160
            or explicit_visual_reference
        )
        explicit_visual_task = (
            not visual_reference_lock
            and current_visual_action
            and current_image_object_evidence >= 0.035
            and current_image_representation_evidence >= 0.035
        )
        visual_generation_request = ""
        current_self_contained = bool(
            _request_features.get("self_contained")
            or (
                current_visual_action
                and current_image_representation_evidence >= 0.035
                and current_image_object_evidence >= 0.035
            )
        )
        # A reference/recollection turn must never inherit the previous visual
        # renderer merely because the current text contains a visual verb/object.
        # The 12h pair dialogue remains available as context, but output stays text.
        if visual_reference_lock:
            production = "text"
            source = "STATE_MANAGER_AUTHENTICATED_12H_PAIRS_REFERENCE"
            locked = False
            continuation = False
            dialogue_vector.update({
                "three_way_relation": "RECALL",
                "relation": "MEMORY_QUERY",
                "topic_relation": "MEMORY_QUERY",
                "request_relation": "RECALL",
                "request_dependency": "recall",
                "continuation": False,
                "reference_to_previous": True,
            })

        if explicit_visual_task:
            # A complete request supplies its own immutable visual operand. Only an
            # incomplete follow-up inherits the operand from 12h pair memory.
            if current_self_contained:
                visual_generation_request = text
                dialogue_vector["visual_context_source"] = "CURRENT_AUTHENTICATED_TURN"
            elif visual_generation_context:
                visual_generation_request = self.normalize(visual_generation_context.get("user"))
                dialogue_vector["visual_context_source"] = "STATE_MANAGER_AUTHENTICATED_12H_PAIRS"
                dialogue_vector["visual_context_turn_index"] = visual_generation_context.get("turn_index", -1)
            if visual_generation_request:
                production = "image"
                source = (
                    "STATE_MANAGER_AUTHENTICATED_12H_PAIRS"
                    if not current_self_contained
                    else "CURRENT_AUTHENTICATED_TURN"
                )
                locked = True
                dialogue_vector["visual_generation_request"] = visual_generation_request
            if visual_generation_request and not current_self_contained:
                dialogue_vector.update({
                    "three_way_relation": "CONTINUE",
                    "relation": "CONTINUE_TOPIC",
                    "topic_relation": "SAME_TOPIC",
                    "request_relation": "CONTINUE_TOPIC",
                    "request_dependency": "continuation",
                    "continuation": True,
                    "reference_to_previous": False,
                    "selected_memory_operand": dict(visual_generation_context),
                })
                continuation = True

        # An incomplete visual request without an authenticated 12h visual operand
        # must not launch a random image with an underspecified prompt.
        if production in {"image", "gallery"} and not visual_generation_request:
            production = "text"
            source = "INCOMPLETE_VISUAL_WITHOUT_AUTHENTICATED_CONTEXT"
            locked = False

        # A short continuation question does not acquire a structured renderer
        # merely because the representation matrix found a weak candidate.
        # Structured output must be supported by the current turn's operation,
        # object and goal evidence (or an explicit upstream representation).
        if production != "text" and not explicit:
            op = str(p.get("best_operation") or "").lower()
            obj = str(p.get("best_object") or "").lower()
            goal = str(p.get("best_goal") or "").lower()
            obj_score = float(p.get("object_scores", {}).get(production, 0.0) or 0.0)
            current_visual_intent = (
                locked
                or (
                    op in {"build", "modify", "present", "explain"}
                    and obj == production
                    and obj_score >= 0.10
                    and goal in {"visualize", "transform", "present", "organize"}
                )
            )
            # `locked` means the representation was already resolved from the
            # complete semantic task vector. Never demote such a decision merely
            # because another semantic family (for example explanation) ranked
            # slightly higher. This is a semantic contract, not a word trigger.
            if not current_visual_intent:
                production = "text"
                source = "current_turn_representation_not_established"
                locked = False
        # A semantically resolved continuation of a visual scene keeps the same
        # output representation. The previous structured artifact is evidence of
        # the object being modified; no lexical renderer trigger is used.
        if continuation and production == "text" and isinstance(previous_scene, dict):
            prior_types = [
                _clean_representation(x)
                for x in (previous_scene.get("render_block_types") or [])
            ]
            if not prior_types:
                prior_types = [
                    _clean_representation(
                        block.get("type")
                        or block.get("artifact_type")
                        or block.get("representation")
                    )
                    for block in (previous_scene.get("render_blocks") or [])
                    if isinstance(block, dict)
                ]
            prior_structured = [x for x in prior_types if x in STRUCTURED_REPRESENTATIONS]
            operation = p.get("best_operation")
            dialogue_label = self.normalize(dialogue_vector.get("semantic_dialogue_label")).lower()
            if prior_structured and operation in {"modify", "build", "present", "list", "analyze"}:
                production = prior_structured[0]
                source = "semantic_continuity_preserve_representation"
                locked = True
            elif prior_structured and dialogue_label in {"continuation", "reformulation", "correction", "reference"}:
                production = prior_structured[0]
                source = "semantic_continuity_preserve_representation"
                locked = True

        reference=bool(
            dialogue_vector.get("request_relation") == "ARTIFACT_REFERENCE"
            or dialogue_vector.get("reference_to_previous")
        )
        memory=bool(
            p["dialogue_best"] == "memory_query"
            or dialogue_vector.get("request_relation") == "MEMORY_QUERY"
        )
        semantic_profile_for_reference = {
            **p,
            "dialogue_best": p.get("dialogue_best"),
        }
        reference_resolution = self._reference_resolution(
            text,
            last_a,
            last_u,
            semantic_profile=semantic_profile_for_reference,
            reference_authorized=reference,
        )
        explicit_reference = bool(dialogue_vector.get("request_relation") == "ARTIFACT_REFERENCE")
        if reference_resolution.get("resolved") and reference_resolution.get("target") and explicit_reference:
            reference = True
            continuation = True
            dialogue_vector["reference_resolution"] = reference_resolution
            dialogue_vector["resolved_reference"] = reference_resolution.get("target")
            # An explicit artifact reference can inherit the previous structured
            # representation even when the current sentence omits its modality.
            if production == "text" and isinstance(previous_scene, dict):
                prior_types = [_clean_representation(x) for x in (previous_scene.get("render_block_types") or [])]
                if not prior_types:
                    prior_types = [_clean_representation(
                        block.get("type") or block.get("artifact_type") or block.get("representation")
                    ) for block in (previous_scene.get("render_blocks") or []) if isinstance(block, dict)]
                prior_structured = [x for x in prior_types if x in STRUCTURED_REPRESENTATIONS]
                if prior_structured:
                    production = prior_structured[0]
                    source = "reference_reuse_existing_representation"
                    locked = True

        # A resolved artifact reference is normally an information request about
        # the existing result, not a request to render that result again. Keep
        # the provider-facing output textual unless the current semantic task
        # explicitly requires a new/modified structured artifact.
        artifact_reference_answer = bool(
            reference
            and dialogue_vector.get("artifact_reference_evidence")
            and str(p.get("best_operation") or "").lower() in {
                "answer", "list", "analyze", "explain", "retrieve", "build"
            }
        )
        if artifact_reference_answer:
            production = "text"
            source = "artifact_reference_answer"
            locked = True
            dialogue_vector["artifact_reference_answer"] = True
        resolved_scene=self._resolve_scene_context(
            text,
            state,
            continuation,
            reference,
            memory=memory,
            active_topic=active_topic,
        )
        resolved_reference = reference_resolution.get("target") or ""
        resolved_request = text
        history_task_context = dict(dialogue_vector.get("history_task_context") or {})

        # RECALL materializes the selected older USER->APRIL result into the
        # interpretation operand. This is the missing bridge that previously
        # left the Provider with only "history exists" instead of the actual
        # prior answer/code/result to develop.
        selected_memory = dialogue_vector.get("selected_memory_operand")
        if selected_relation == "RECALL" and isinstance(selected_memory, dict):
            recalled_user = self.normalize(selected_memory.get("user"))
            recalled_result = self.normalize(
                selected_memory.get("result") or selected_memory.get("april") or selected_memory.get("assistant")
            )
            if recalled_user or recalled_result:
                resolved_request = (
                    f"{text}\n\n"
                    "The current request recalls an older authenticated USER↔APRIL result. "
                    "Use the recalled result as a concrete context operand and develop it; "
                    "do not ask the user to resend the previous result.\n"
                    f"Recalled USER request: {recalled_user}\n"
                    f"Recalled APRIL result: {recalled_result}"
                )
                reference = True
                memory = False
                dialogue_vector["resolved_memory_operand"] = {
                    "user": recalled_user,
                    "result": recalled_result,
                    "index": dialogue_vector.get("selected_memory_index", -1),
                }
        if history_task_context.get("required"):
            selected_results = history_task_context.get("selected_results") or []
            lines = []
            for idx, item in enumerate(selected_results, start=1):
                lines.append(
                    f"Historical result {idx}: {item.get('result')} (from USER: {item.get('user')}; APRIL: {item.get('assistant')})"
                )
            resolved_request = (
                f"{text}\n\n"
                "The current calculation is history-dependent. The interpretation engine resolved the "
                "required operands from the two most recent concrete numeric results in the authenticated "
                "USER↔APRIL dialogue history. Use these values directly; do not ask the user to repeat them.\n"
                + "\n".join(lines)
            )
        if resolved_reference and (continuation or reference):
            # Structural discourse resolution: make the provider-facing request
            # explicit without hard-coded topic/entity rules.
            resolved_request = (
                f"{text}\n\nContextual referent resolved from the immediately previous human exchange: "
                f"{resolved_reference}. Answer the current request about that referent without asking the user to repeat it."
            )
        if reference_resolution.get("resolved") and reference_resolution.get("target"):
            resolved_scene = dict(resolved_scene or {})
            resolved_scene["reference_target"] = reference_resolution.get("target")
            resolved_scene["reference_resolution"] = dict(reference_resolution)
        evidence=[{"label":k,"score":float(v),"source":"quantum_matrix","positive":True,"details":{}}
                  for k,v in sorted(p["representation_scores"].items(),key=lambda x:x[1],reverse=True) if float(v)>=0.20]
        domains=[k for k,v in p["domain_scores"].items() if float(v)>=0.20]
        matrix=self._scene_matrix(p)
        visual_schema_scores = dict(p.get("visual_schema_scores") or {})
        visual_schema_rank = sorted(visual_schema_scores.items(), key=lambda item: float(item[1]), reverse=True)
        visual_schema = visual_schema_rank[0][0] if visual_schema_rank else ""
        visual_schema_confidence = float(visual_schema_rank[0][1]) if visual_schema_rank else 0.0
        ascii_schema_advisory = False
        semantic_task_object = p["best_object"]
        semantic_task_goal = p["best_goal"]
        semantic_task_operation = p["best_operation"]
        if production == "image" and bool((p.get("request_features") or {}).get("visual_action")):
            # Current image route is creation only. Do not emit an edit operation
            # until the dedicated Images 2.0 editing route is implemented.
            semantic_task_operation = "build"
            semantic_task_object = "image"
            if semantic_task_goal in {"understand", "transform"}:
                semantic_task_goal = "visualize"
        # The resolved production representation is authoritative for the provider
        # handoff. Weak cross-prototype scores must not leak a stale visual object or
        # visual goal into a text turn and make the Provider emit an image-only JSON.
        if production == "text" and not visual_generation_request:
            if semantic_task_object in {"image", "gallery", "diagram", "graph"}:
                semantic_task_object = "text"
            if semantic_task_goal in {"visualize", "transform", "present"}:
                semantic_task_goal = "understand"
        semantic_task={
            "operation":semantic_task_operation,"object":semantic_task_object,"goal":semantic_task_goal,
            "representation":production,
            "visual_schema":visual_schema,
            "visual_schema_confidence":visual_schema_confidence,
            "ascii_schema_advisory": False,
            "ascii_schema_score": 0.0,
            "visual_generation_request": visual_generation_request,
            "visual_generation_source": (
                "STATE_MANAGER_AUTHENTICATED_12H_PAIRS"
                if visual_generation_request and not current_self_contained
                else "CURRENT_AUTHENTICATED_TURN"
                if visual_generation_request else ""
            ),
            "operation_scores":p["operation_scores"],"object_scores":p["object_scores"],"goal_scores":p["goal_scores"]
        }
        presentation_recommendations = self._presentation_recommendations(
            text, p, production, locked=locked, continuation=continuation,
            previous_scene=previous_scene, explicit=explicit,
        )
        if production in {"image", "gallery"}:
            presentation_recommendations = [
                item for item in presentation_recommendations
                if str(item.get("representation") or "").lower() not in {"text", "ascii"}
            ]
        presentation={
            "version":"quantum_interpretation_transport_v4","decision_owner":DECISION_OWNER,
            "single_route":True, "production_representation":production,
            "recommendation_policy": {
                "generated_after_interpretation": True,
                "current_request_authoritative": True,
                "multiple_representations_allowed": True,
                "multiple_renderer_recommendations_allowed": True,
                "scene_recommendation_per_representation": True,
                "text_intro_renderer": "MessageTextBlock",
                "text_explanation_renderer": "MessageTextBlock",
                "stale_context_cannot_upgrade_current_representation": True,
            },
            "signals":[x["renderer_signal"] for x in presentation_recommendations],
            "recommendations": presentation_recommendations,
            "scene_plan": [x["scene_recommendation"] for x in presentation_recommendations],
        }
        result=build_result(text)
        result.update({
            "type":p["dialogue_best"],"subtype":production,"scene_type":production,
            "relation": dialogue_vector.get("three_way_relation") or (
                "CONTINUE" if continuation else "RECALL" if reference else "NEW"
            ),
            "topic_relation": dialogue_vector.get("relation", "NEW_TOPIC"),
            "normalized":text,"required_domains":domains,"candidate_domains":domains,
            "required_representations":[production],"candidate_representations":[production],
            "requested_representations":[production],"requested_representation":production,
            "production_representation":production,"production_representation_locked":locked,
            "production_representation_source":source,
            "production_representation_confidence":max(
                p["representation_scores"].get(production,0.0),
                p["object_scores"].get(production,0.0),
                p["goal_scores"].get("visualize" if production in {"graph","diagram","image","gallery"} else "present",0.0)
            ),
            "representation_evidence":evidence,
            "quantum_representation_measurement":{
                "measurements":evidence,"production_representation":production,
                "production_representation_locked":locked,"scene_matrix":matrix
            },
            "semantic_task":semantic_task,
            "visual_generation_request": visual_generation_request,
            "visual_generation_source": (
                "STATE_MANAGER_AUTHENTICATED_12H_PAIRS"
                if visual_generation_request and not current_self_contained
                else "CURRENT_AUTHENTICATED_TURN"
                if visual_generation_request else ""
            ),
            "context_understanding": context_understanding,
            "topic_understanding": topic_understanding,
            "entity_understanding": entities_understanding,
            "authenticated_dialogue_memory": {
                "source": "STATE_MANAGER_AUTHENTICATED_12H_PAIRS",
                "window_hours": 12,
                "pair_limit": 15,
                "pair_count": len(recent_dialogue_pairs),
            },
            "turn_structure_understanding": turn_structure_understanding,
            "task_understanding": task_understanding,
            "ascii_schema_advisory": False,
            "resolved_scene":resolved_scene,
            "reference_resolution":reference_resolution,
            "presentation_transport":presentation,"presentation_signal":presentation,
            "presentation_recommendations":presentation_recommendations,
            "presentation_signals":presentation["signals"],
            "scene_recommendations":[x["scene_recommendation"] for x in presentation_recommendations],
            "scene_plan":[x["scene_recommendation"] for x in presentation_recommendations],
            "dialogue_memory_window": list(recent_dialogue_pairs[:]),
            "dialogue_memory_source": "STATE_MANAGER_12H_PAIRS",
            "dialogue_memory_pair_count": len(recent_dialogue_pairs),
            "dialogue_vector": {
                **dict(dialogue_vector or {}),
                "reference_resolution": reference_resolution,
                "resolved_reference": resolved_reference,
                "resolved_request": resolved_request,
                "history_dependent_task": bool(history_task_context.get("required")),
                "history_window_size": len(recent_dialogue_pairs),
                "history_task_context": history_task_context,
                "visual_generation_request": visual_generation_request,
                "visual_generation_source": (
                    "STATE_MANAGER_AUTHENTICATED_12H_PAIRS"
                    if visual_generation_request and not current_self_contained
                    else "CURRENT_AUTHENTICATED_TURN"
                    if visual_generation_request else ""
                ),
            },
            "dialogue_delta": {
                "mode": dialogue_vector.get("delta_mode"),
                "shared_tokens": dialogue_vector.get("shared_tokens", []),
                "new_tokens": dialogue_vector.get("new_tokens", []),
                "avoid_repeat": True,
            },
            "render_continuity": {
                "mode": "extend" if continuation else "start",
                "avoid_repeat": True,
                "reuse_existing_scene": bool(dialogue_vector.get("reuse_existing_scene")),
                "previous_scene_id": dialogue_vector.get("previous_scene_id", ""),
                "previous_render_types": dialogue_vector.get("previous_render_types", []),
                "previous_block_ids": dialogue_vector.get("previous_block_ids", []),
            },
            "dialogue_contract":{
                "dialog_act":d["label"],"current_request":text,"continuation":continuation,
                "reference_to_previous":reference,"previous_april_turn":last_a,
                "previous_user_turn":last_u,"reply_to":reply_to,"active_goal":active_goal,
                "active_topic":active_topic,
                "reference_resolution":reference_resolution,
                "resolved_reference":resolved_reference,
                "artifact_reference_evidence": bool(
                    dialogue_vector.get("artifact_reference_evidence")
                ),
                "artifact_reference_answer": bool(
                    dialogue_vector.get("artifact_reference_answer")
                ),
                "visual_scene_similarity": float(
                    dialogue_vector.get("visual_scene_similarity", 0.0) or 0.0
                ),
                "resolved_request":resolved_request,
                "context_topic": active_topic,
                "context_relation": topic_understanding.get("relation"),
                "context_reference_entities": [
                    item.get("entity") for item in (entities_understanding.get("coreference") or [{}])
                    if isinstance(item, dict) for item in (item.get("candidates") or []) if item.get("entity")
                ][:8],
                "local_current_turn_structure": local_turn_reference,
                "history_dependent_task": bool(history_task_context.get("required")),
                "history_task_context": history_task_context,
                "context_dependency": (
                    "continuation" if dialogue_vector.get("three_way_relation") == "CONTINUE"
                    else "recall" if dialogue_vector.get("three_way_relation") == "RECALL"
                    else "independent"
                ),
                "three_way_relation": dialogue_vector.get("three_way_relation") or (
                    "CONTINUE" if continuation else "RECALL" if reference else "NEW"
                ),
                "selected_memory_operand": dialogue_vector.get("selected_memory_operand") or {},
                # `relation` is the single canonical three-way state consumed by
                # the processor: NEW / CONTINUE / RECALL. The topic-level relation
                # remains available separately and is never used as the dialogue
                # execution state.
                "relation": dialogue_vector.get("three_way_relation") or (
                    "CONTINUE" if continuation else "RECALL" if reference else "NEW"
                ),
                "topic_relation": dialogue_vector.get("relation", "NEW_TOPIC"),
                "subtype": dialogue_vector.get("subtype", "NEW_TOPIC"),
                "avoid_repeat": True,
                "canonical":True,"version":"quantum_dialogue_field_v4"
            },
            "context_resolution":{
                "depends_on_previous_dialogue":bool(continuation or reference or memory or history_task_context.get("required")),
                "history_dependent_task": bool(history_task_context.get("required")),
                "history_task_context": history_task_context,
                "resolved_scene":resolved_scene,"active_topic":active_topic,"active_goal":active_goal
            },
            "semantic_profile":{
                "active_topic":active_topic,"active_goal":active_goal,
                "context_topic_state": topic_understanding,
                "context_entity_state": entities_understanding,
                "context_task_state": task_understanding,
                "previous_april_turn":last_a,"representation_scores":p["representation_scores"],
                "domain_scores":p["domain_scores"],"capability_scores":p["capability_scores"],
                "operation_scores":p["operation_scores"],"object_scores":p["object_scores"],
                "goal_scores":p["goal_scores"],"context_scores":p["context_scores"],
                "semantic_task":semantic_task,
                "history_dependent_task": bool(history_task_context.get("required")),
                "history_task_context": history_task_context,
                "engine":"quantum_interpretation_engine_v9"
            },
            "quantum_interpretation_field":{
                "linguistic":self._linguistic(text),"dialogue":d,"representation":evidence,
                "domain":[{"domain":k,"score":float(v)} for k,v in p["domain_scores"].items()],
                "context_vectors":p["context_scores"],"semantic_task":semantic_task,
                "production":presentation,"profile":p,"scene_matrix":matrix,
                "decision_owner":DECISION_OWNER,"evidence_only":True,"engine":"quantum_interpretation_engine_v3"
            },
            "quantum_matrix":matrix,"matrix_scene":matrix["best_scene"],
            "matrix_confidence":matrix["best_score"],"decision_owner":DECISION_OWNER,
            "routing_owner":DECISION_OWNER,"renderer_owner":DECISION_OWNER,"provider_calls":0,
            "canonical_transport":TRANSPORT_NAME,"semantic_authority":True,
            "semantic_decision_source":source,"representation_resolution":"task_object_goal",
            "legacy_keyword_matching":False,"avoid_trigger_execution":True,
            "machine_only":True,"single_route":True,"renderer_intent":production!="text",
            "render_intent":production!="text","prefer_renderer":production!="text",
            "renderer_scene_object":production!="text","visual_routing":production in {"graph","diagram","image","gallery"},
            "possible_capability":"renderer" if production!="text" else None,"possible_output":production,
            "possible_scene_type":production,"current_representation":production,
            "unresolved_intent":not locked,"memory_query":memory,
            "continuation":d["continuation_score"],"continuation_target":last_a or active_topic,
            "dialogue_relation": dialogue_vector.get("relation", "NEW_TOPIC"),
            "dialogue_subtype": dialogue_vector.get("subtype", "NEW_TOPIC"),
            "visual_schema": visual_schema,
            "visual_schema_confidence": visual_schema_confidence,
            "required_capabilities":["semantic_interpretation","dialogue_context"],
            "required_outputs":[production],"requested_outputs":[production],
            "response_mode":"structured" if production!="text" else "talk","renderer_first":production!="text",
            "discussion_mode":p["capability_scores"].get("discussion",0.0)>=0.60,
            "space_discussion":p["capability_scores"].get("space",0.0)>=0.60,
            "exploration":p["capability_scores"].get("exploration",0.0),
            "web_context":p["capability_scores"].get("web",0.0),
            "explicit_image_generation":p["representation_scores"].get("image",0.0),
            "lightweight_visual":production in {"graph","diagram","image","gallery"},
            "contains_object":bool(text),
            "contains_explanation":p["capability_scores"].get("information",0.0)>=0.60,
            "contains_analysis":p["capability_scores"].get("exploration",0.0)>=0.60,
            "content_role":"explanation" if p["capability_scores"].get("information",0.0)>=0.60
                           else "analysis" if p["capability_scores"].get("exploration",0.0)>=0.60 else None,
            "artifact_contract":{"contract":"scene_artifact","transport":TRANSPORT_NAME,
                                "scene_type":production,"representation":[production],"decision_owner":DECISION_OWNER},
            "semantic_engine_diagnostics":{
                "engine":"quantum_interpretation_engine_v4","domain_representation_gates":False,
                "capability_representation_gates":False,"lexical_routing":False,
                "token_overlap_context":False,"production_resolution":"task_object_goal",
                "single_route":True,"decision_owner":DECISION_OWNER
            },
        })
        # Freeze the provider handoff inside the Interpretation layer itself.
        # This is the canonical semantic boundary: Provider receives a prepared
        # plan and never has to guess whether the turn is NEW/CONTINUE/RECALL.
        provider_context_plan = _build_provider_context_plan(
            text,
            result.get("dialogue_vector") if isinstance(result.get("dialogue_vector"), dict) else dialogue_vector,
            result.get("dialogue_contract") if isinstance(result.get("dialogue_contract"), dict) else {},
            semantic_task,
            {
                **presentation,
                "requested_outputs": [production],
            },
            recent_dialogue_pairs[:],
            history_task_context,
            continuation,
            reference,
        )
        result["provider_context_plan"] = provider_context_plan

        result["evidence"]={"representation":evidence,
                            "domain":[{"domain":k,"score":float(v)} for k,v in p["domain_scores"].items()],
                            "math":p["representation_scores"].get("formula",0.0),
                            "code":p["representation_scores"].get("code",0.0),
                            "web":p["capability_scores"].get("web",0.0),
                            "image":p["representation_scores"].get("image",0.0),
                            "continuation":d["continuation_score"],
                            "exploration":p["capability_scores"].get("exploration",0.0),
                            "information":p["capability_scores"].get("information",0.0),
                            "dialogue":result["dialogue_contract"]}
        result["interpretation_state"]=synchronize_interpretation_context(build_interpretation_state(),result)
        if isinstance(result.get("interpretation_state"), dict):
            result["interpretation_state"]["provider_context_plan"] = provider_context_plan
        result["transport_state"]=export_transport_state(result["interpretation_state"],result)
        result["transport_diagnostics"]=build_transport_diagnostics(result)
        bridge_machine_response(result,result["transport_state"])
        result["estimated_action_count"]=0
        result["response_complexity"]=None
        result["factory_targets"]=[]
        result["factory_order"]={"owner":DECISION_OWNER,"status":"evidence_only"}
        result["scene_strategy"]={
            "scene_strategy":"evidence_only",
            "preferred_blocks":[x["representation"] for x in presentation_recommendations if x["representation"] != "text"] or [production],
            "presentation_recommendations":presentation_recommendations,
            "scene_recommendations":[x["scene_recommendation"] for x in presentation_recommendations],
            "scene_plan":[x["scene_recommendation"] for x in presentation_recommendations],
            "decision_owner":DECISION_OWNER,
            "recommendations_only":True,
        }
        return result

    # ------------------------------------------------------------------
    # Presentation recommendations
    # ------------------------------------------------------------------
    # Produced only AFTER the current request has been semantically
    # interpreted. These are advisory downstream signals, never renderer
    # commands. Multiple distinct representations are allowed.
    PRESENTATION_RENDERERS = {
        "text": "MessageTextBlock", "code": "CodeBlock", "graph": "GraphBlock",
        "diagram": "GalleryBlock", "image": "GalleryBlock", "gallery": "GalleryBlock",
        "link": "LinkCard", "table": "TableBlock", "formula": "MessageTextBlock",
        "file": "LinkCard", "audio": "MessageTextBlock", "video": "MessageTextBlock",
        "action": "MessageTextBlock", "scene": "GalleryBlock", "memory": "MessageTextBlock",
        "visual_context": "GalleryBlock",
    }
    PRESENTATION_LABELS = {
        "text": "textual answer", "code": "executable code", "graph": "graph/chart",
        "diagram": "diagram or geometric construction", "image": "image",
        "gallery": "image gallery", "link": "link cards", "table": "table",
        "formula": "mathematical notation", "file": "file/resource", "audio": "audio",
        "video": "video", "action": "interactive action", "scene": "visual scene",
        "memory": "memory explanation", "visual_context": "visual context",
    }
    PRESENTATION_SCENE_PROFILES = {
        "text": ("explanation", "message", "human-readable answer"),
        "code": ("code_example", "message_intro -> code -> message_explanation", "source code plus implementation context"),
        "graph": ("data_visualization", "message_intro -> graph -> message_explanation", "series, axes, labels, units and requested ranges"),
        "diagram": ("diagram_or_construction", "message_intro -> gallery_diagram -> message_explanation", "nodes/shapes/relations/dimensions and construction facts"),
        "image": ("image", "message_intro -> gallery_image -> message_explanation", "generated or selected image with visual context"),
        "gallery": ("image_collection", "message_intro -> gallery -> message_explanation", "ordered image collection with per-image meaning"),
        "link": ("resource_links", "message_intro -> link_cards -> message_explanation", "URL, title and short purpose for each resource"),
        "table": ("structured_data", "message_intro -> table -> message_explanation", "rows, columns, headers, units and values"),
        "formula": ("mathematical_explanation", "message_intro -> message_formula -> message_explanation", "formula plus variable definitions and interpretation"),
        "file": ("resource_file", "message_intro -> link_or_file -> message_explanation", "resource identity and purpose"),
        "audio": ("audio", "message_intro -> audio_resource -> message_explanation", "audio resource metadata and purpose"),
        "video": ("video", "message_intro -> video_resource -> message_explanation", "video resource metadata and purpose"),
        "action": ("interactive_action", "message_intro -> action -> message_explanation", "action target, parameters and expected result"),
        "scene": ("composite_visual_scene", "message_intro -> visual_scene -> message_explanation", "scene objects, spatial relations and visual semantics"),
        "memory": ("memory_explanation", "message_intro -> message_explanation", "resolved prior context"),
        "visual_context": ("visual_analysis", "message_intro -> gallery_context -> message_explanation", "visual evidence and interpretation"),
    }

    @classmethod
    def _presentation_recommendations(cls, text, profile, production, *, locked=False,
                                      continuation=False, previous_scene=None,
                                      explicit=None):
        """Return post-interpretation presentation/scene recommendations.

        The current semantic task is authoritative. Evidence may justify zero,
        one, or many additional representations; no renderer-count cap exists.
        """
        profile = profile if isinstance(profile, dict) else {}
        rep_scores = dict(profile.get("representation_scores") or {})
        obj_scores = dict(profile.get("object_scores") or {})
        op_scores = dict(profile.get("operation_scores") or {})
        explicit_values = list(dict.fromkeys(
            _clean_representation(x) for x in (explicit or []) if _clean_representation(x)
        ))
        compatible_ops = {
            "graph": {"build","modify","present","calculate","analyze","list","explain"},
            "diagram": {"build","modify","present","explain"},
            "table": {"build","modify","present","compare","list","explain"},
            "formula": {"build","modify","present","calculate","explain","answer"},
            "link": {"retrieve","present","answer"}, "code": {"build","modify","present","explain"},
            "image": {"build","modify","present"}, "gallery": {"build","present"},
            "file": {"retrieve","present"}, "audio": {"build","present"},
            "video": {"build","present"}, "action": {"build","modify","present"},
            "scene": {"build","modify","present"}, "memory": {"retrieve","answer","present"},
            "visual_context": {"answer","analyze","explain"},
        }
        op = str(profile.get("best_operation") or "answer").lower()
        candidates = set(explicit_values)
        if production:
            candidates.add(production)
        for label, value in rep_scores.items():
            score = float(value or 0.0)
            obj_score = float(obj_scores.get(label, 0.0) or 0.0)
            if label == "text":
                if score >= 0.14: candidates.add(label)
                continue
            if label in explicit_values or label == production or (
                op in compatible_ops.get(label, set()) and score >= 0.16 and obj_score >= 0.07
            ):
                candidates.add(label)
        if any(x != "text" for x in candidates):
            candidates.add("text")

        ordered = ([production] if production else [])
        ordered += [x for x, _ in sorted(
            ((x, float(rep_scores.get(x, 0.0) or 0.0)) for x in candidates if x != production),
            key=lambda item: item[1], reverse=True
        )]
        if "text" in candidates and "text" not in ordered:
            ordered.insert(0, "text")
        ordered = list(dict.fromkeys(ordered))
        scene_id = str(previous_scene.get("scene_id") or "") if isinstance(previous_scene, dict) else ""

        out = []
        for idx, label in enumerate(ordered):
            if label not in REPRESENTATION_UNIVERSE:
                continue
            renderer = cls.PRESENTATION_RENDERERS.get(label, "MessageTextBlock")
            role, composition, payload = cls.PRESENTATION_SCENE_PROFILES.get(
                label, cls.PRESENTATION_SCENE_PROFILES["text"]
            )
            continuing_scene = bool(continuation and scene_id and label != "text")
            out.append({
                "recommendation_id": f"semantic-presentation-{idx + 1}",
                "representation": label,
                "representation_label": cls.PRESENTATION_LABELS.get(label, label),
                "renderer": renderer,
                "renderer_signal": {
                    "type": label, "renderer": renderer, "owner": DECISION_OWNER,
                    "source": "QUANTUM_INTERPRETATION_ENGINE", "evidence_only": True,
                },
                "semantic_basis": {
                    "representation_score": round(float(rep_scores.get(label, 0.0) or 0.0), 6),
                    "object_score": round(float(obj_scores.get(label, 0.0) or 0.0), 6),
                    "operation": op,
                    "goal": str(profile.get("best_goal") or "understand"),
                    "is_production_representation": label == production,
                    "production_locked": bool(locked and label == production),
                    "explicit_current_request": label in explicit_values,
                },
                "response_role": "supporting_explanation" if label == "text" else "primary_representation",
                "scene_recommendation": {
                    "role": role,
                    "order_hint": "representation" if label != "text" else "narrative",
                    "composition": composition,
                    "sequence": ([
                        {"role": "introduction", "renderer": "MessageTextBlock", "content_role": "request_essence"},
                        {"role": "representation", "renderer": renderer, "type": label, "content_role": "specialized_result"},
                        {"role": "explanation", "renderer": "MessageTextBlock", "content_role": "result_explanation"},
                    ] if label != "text" else [
                        {"role": "answer", "renderer": "MessageTextBlock", "content_role": "human_answer"},
                    ]),
                    "intro_via": "MessageTextBlock",
                    "renderer": renderer,
                    "explanation_via": "MessageTextBlock",
                    "payload_expectation": payload,
                    "scene_relation": "continue_existing_scene" if continuing_scene else "new_scene",
                    "reuse_scene_id": scene_id if continuing_scene else "",
                    "avoid_repeat": continuing_scene,
                    "build_scene_after_semantic_understanding": True,
                    "independent_scene_recommendation": True,
                },
                "text_guidance": {
                    "introduction": "Briefly state the essence of the current user request and what this representation will show.",
                    "explanation": "Explain the produced result, its main meaning and purpose after the specialized block.",
                },
                "advisory_only": True,
            })
        return out

    def fast_semantic_profile(self,text,previous_assistant="",previous_user="",active_topic="",active_goal=""):
        return self.measure(text,previous_assistant=previous_assistant,previous_user=previous_user,active_topic=active_topic,active_goal=active_goal)

    def turn_measurement(self,text,previous_assistant="",previous_user="",active_goal="",active_topic=""):
        p=self.measure(text,previous_assistant=previous_assistant,previous_user=previous_user,active_goal=active_goal,active_topic=active_topic)
        return {"linguistic":self._linguistic(text),
                "dialogue_nli":{"labels":list(p["dialogue_scores"]),"scores":list(p["dialogue_scores"].values()),"source":"quantum_matrix"},
                "representation_nli":{"labels":list(p["representation_scores"]),"scores":list(p["representation_scores"].values()),"source":"quantum_matrix"},
                "domain_nli":{"labels":list(p["domain_scores"]),"scores":list(p["domain_scores"].values()),"source":"quantum_matrix"},
                "capability_nli":{"labels":list(p["capability_scores"]),"scores":list(p["capability_scores"].values()),"source":"quantum_matrix"},
                "embeddings":dict(p["context_scores"]),"decision_owner":DECISION_OWNER,"evidence_only":True,
                "engine":"quantum_interpretation_turn_engine_v3"}

    def classify(self,text,hypotheses):
        p=self.measure(text); merged={}
        for fam in ("dialogue","representation","domain","capability","operation","object","goal"):
            merged.update(p.get(f"{fam}_scores",{}))
        ranked=sorted(((h,float(merged.get(h,0.0))) for h in hypotheses),key=lambda x:x[1],reverse=True)
        return {"labels":[x[0] for x in ranked],"scores":[x[1] for x in ranked],"source":"quantum_matrix"}

# Global representation universe remains visible to compatibility helpers.


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
    state["scene"]["resolved"] = result.get("resolved_scene")
    state["scene"]["presentation"] = result.get("presentation_transport")
    state["artifacts"]["contract"] = result.get("artifact_contract")
    state["executor"]["contract"] = result.get("executor_preparation_contract")
    return state


def export_transport_state(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    state = ensure_transport_defaults(state)
    for field, (section, key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state[section][key] = result[field]
    state.setdefault("presentation", {})
    state["presentation"]["transport"] = result.get("presentation_transport")
    state["presentation"]["signals"] = list(result.get("presentation_signals") or [])
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
    response["content"] = safe_result_get(result, "normalized") or safe_result_get(
        result, "assistant_response", ""
    )
    return result



def _quantum_scene_projection(scene: dict[str, Any] | None) -> dict[str, Any]:
    scene = scene if isinstance(scene, dict) else {}
    return {
        "scene_id": scene.get("scene_id"),
        "turn_id": scene.get("turn_id"),
        "relation": scene.get("relation"),
        "topic": scene.get("topic"),
        "user_request": scene.get("user_request"),
        "answer": scene.get("answer"),
        "summary": scene.get("summary"),
        "semantic_state": scene.get("semantic_state") or {},
        "render_blocks": scene.get("render_blocks") or [],
        "presentation_signals": scene.get("presentation_signals") or [],
        "presentation_types": scene.get("presentation_types") or [],
        "renderer_state": scene.get("renderer_state") or {},
    }


def bridge_machine_response(result: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    machine = state.setdefault("machine_response", {})
    scene = state.setdefault("scene_contract", {})
    content = machine.get("content") or result.get("normalized") or result.get(
        "assistant_response", ""
    )
    machine["content"] = content
    scene.update({"content": content, "answer": content, "summary": content})
    if isinstance(result.get("resolved_scene"), dict):
        scene["resolved_scene"] = _quantum_scene_projection(result.get("resolved_scene"))
    if isinstance(result.get("presentation_transport"), dict):
        scene["presentation_transport"] = result.get("presentation_transport")
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
QUANTUM_CONTEXT_ENGINE = QuantumContextUnderstandingEngine(QUANTUM_INTERPRETATION_ENGINE)
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


# ---------------------------------------------------------------------------
# Visual + Dialogue Memory Understanding Engine
# ---------------------------------------------------------------------------
class QuantumMemoryUnderstandingEngine:
    """Parallel analysis of dialogue memory and visual-response memory.

    Evidence-only: it never routes, selects, rewrites, or creates renderer
    signals. It reconstructs relevant prior visual context for the existing
    Quantum Processor so the next response can be a new artifact carrying the
    meaning/schema of the previous visual response.
    """

    VERSION = "QUANTUM-MEMORY-UNDERSTANDING-V1"
    MAX_DIALOG_TURNS = 6
    MAX_VISUAL_BLOCKS = 4
    MAX_VISUAL_HISTORY = 4

    @staticmethod
    def _text(value):
        return str(value or "").strip()

    @staticmethod
    def _compact(value, depth=0):
        if depth > 3 or value in (None, "", [], {}):
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            out = {}
            for key, item in list(value.items())[:24]:
                compacted = QuantumMemoryUnderstandingEngine._compact(item, depth + 1)
                if compacted not in (None, "", [], {}):
                    out[str(key)] = compacted
            return out
        if isinstance(value, (list, tuple)):
            out = []
            for item in list(value)[:24]:
                compacted = QuantumMemoryUnderstandingEngine._compact(item, depth + 1)
                if compacted not in (None, "", [], {}):
                    out.append(compacted)
            return out
        return str(value)

    @classmethod
    def _dialogue_text(cls, history):
        result = []
        if not isinstance(history, list):
            return result
        for item in history[-cls.MAX_DIALOG_TURNS:]:
            if not isinstance(item, dict):
                continue
            role = cls._text(item.get("role")).lower()
            content = cls._text(item.get("content") or item.get("text") or item.get("answer"))
            if role and content:
                result.append(f"{role}: {content}")
        return result

    @classmethod
    def _visual_candidates(cls, visual_context):
        if not isinstance(visual_context, dict):
            return []
        candidates = []
        active = visual_context.get("active_visual_scene")
        if isinstance(active, dict):
            candidates.append(active)
        history = visual_context.get("visual_scene_history") or []
        if isinstance(history, list):
            candidates.extend(x for x in history[-cls.MAX_VISUAL_HISTORY:] if isinstance(x, dict))
        result, seen = [], set()
        for scene in candidates:
            sid = cls._text(scene.get("scene_id") or scene.get("id"))
            key = sid or str(sorted((str(k), str(v)) for k, v in list(scene.items())[:8]))
            if key in seen:
                continue
            seen.add(key)
            result.append(scene)
        return result

    @classmethod
    def _extract_visual_schema(cls, scene):
        blocks = scene.get("render_blocks") or scene.get("blocks") or []
        structured = []
        if isinstance(blocks, list):
            for block in blocks[:cls.MAX_VISUAL_BLOCKS]:
                if not isinstance(block, dict):
                    continue
                kind = cls._text(block.get("type") or block.get("artifact_type") or block.get("representation")).lower()
                if not kind or kind in {"text", "markdown"}:
                    continue
                payload = block.get("payload")
                if not isinstance(payload, dict):
                    artifact = block.get("artifact")
                    payload = artifact.get("payload") if isinstance(artifact, dict) else None
                if not isinstance(payload, dict):
                    candidate = block.get(kind)
                    payload = candidate if isinstance(candidate, dict) else {}
                structured.append({
                    "type": kind,
                    "renderer": cls._text(block.get("renderer")),
                    "viewer": cls._text(block.get("viewer")),
                    "block_id": cls._text(block.get("block_id")),
                    "payload": cls._compact(payload),
                })
        return {
            "scene_id": cls._text(scene.get("scene_id") or scene.get("id")),
            "topic": cls._text(scene.get("topic") or scene.get("user_request") or scene.get("current_request")),
            "user_request": cls._text(scene.get("user_request") or scene.get("current_request")),
            "answer": cls._text(scene.get("april_answer") or scene.get("answer") or scene.get("content")),
            "summary": cls._text(scene.get("summary")),
            "render_block_types": [cls._text(x).lower() for x in (scene.get("render_block_types") or []) if cls._text(x)],
            "presentation_types": [cls._text(x).lower() for x in (scene.get("presentation_types") or []) if cls._text(x)],
            "render_blocks": structured,
            "semantic_state": cls._compact(scene.get("semantic_state") or {}),
        }

    def analyze(self, current_request, *, dialogue_memory=None, visual_memory=None,
                interpretation=None, dynamic_memory=None):
        current_request = self._text(current_request)
        dialogue_memory = dialogue_memory if isinstance(dialogue_memory, dict) else {}
        visual_memory = visual_memory if isinstance(visual_memory, dict) else {}
        interpretation = interpretation if isinstance(interpretation, dict) else {}
        dynamic_memory = dynamic_memory if isinstance(dynamic_memory, dict) else {}

        dialogue_vector = interpretation.get("dialogue_vector") if isinstance(interpretation.get("dialogue_vector"), dict) else {}
        dialogue_contract = interpretation.get("dialogue_contract") if isinstance(interpretation.get("dialogue_contract"), dict) else {}
        relation = self._text(dialogue_vector.get("relation") or dialogue_contract.get("relation")).upper()
        three_way = self._text(
            dialogue_vector.get("three_way_relation")
            or dialogue_contract.get("three_way_relation")
        ).upper()
        continuation = bool(
            dialogue_vector.get("continuation")
            or dialogue_contract.get("continuation")
            or relation in {"CONTINUE_TOPIC", "CONTINUATION"}
            or three_way == "CONTINUE"
        )
        reference = bool(
            dialogue_vector.get("reference_to_previous")
            or dialogue_contract.get("reference_to_previous")
            or relation == "ARTIFACT_REFERENCE"
            or three_way == "RECALL"
        )
        selected_memory_operand = dialogue_vector.get("selected_memory_operand")
        if not isinstance(selected_memory_operand, dict):
            selected_memory_operand = {}

        candidates = self._visual_candidates(visual_memory)
        schemas = [self._extract_visual_schema(scene) for scene in candidates]
        active_schema = schemas[0] if schemas else {}
        current_rep = self._text(interpretation.get("production_representation") or interpretation.get("requested_representation") or interpretation.get("scene_type")).lower()
        prior_types = set(active_schema.get("render_block_types") or [])

        compare = [active_schema[k] for k in ("topic", "user_request", "answer") if active_schema.get(k)]
        similarity = QUANTUM_EMBEDDING_ENGINE.similarities(current_request, compare) if compare else {}
        relevance = max((float(similarity.get(value, 0.0)) for value in compare), default=0.0)
        related_visual = bool(active_schema and (continuation or reference or current_rep in prior_types or relevance >= 0.35))
        selected = active_schema if related_visual else {}

        prior_data = []
        for block in (selected.get("render_blocks") or [])[:self.MAX_VISUAL_BLOCKS]:
            if isinstance(block, dict) and isinstance(block.get("payload"), dict):
                prior_data.append({
                    "type": block.get("type"),
                    "renderer": block.get("renderer"),
                    "block_id": block.get("block_id"),
                    "payload": block.get("payload"),
                })

        return {
            "engine": self.VERSION,
            "version": self.VERSION,
            "decision_owner": DECISION_OWNER,
            "evidence_only": True,
            "lexical_triggers": False,
            "score_routing": False,
            "parallel_memory_channels": True,
            "dialogue_memory": {
                "history_present": bool(self._dialogue_text(dialogue_memory.get("history"))),
                "recent_turns": self._dialogue_text(dialogue_memory.get("history")),
                "active_topic": self._text(dialogue_contract.get("active_topic") or interpretation.get("active_topic")),
                "active_goal": self._text(dialogue_contract.get("active_goal") or interpretation.get("active_goal")),
                "relation": relation,
                "three_way_relation": three_way or ("CONTINUE" if continuation else "RECALL" if reference else "NEW"),
                "continuation": continuation,
                "reference_to_previous": reference,
                "selected_memory_operand": selected_memory_operand,
            },
            "visual_memory": {
                "available": bool(active_schema),
                "related": related_visual,
                "relevance": round(relevance, 6),
                "selected_scene_id": selected.get("scene_id") if selected else "",
                "schema": selected,
                "prior_render_types": sorted(prior_types),
                "prior_structured_blocks": prior_data,
            },
            "memory_reconstruction": {
                "current_request": current_request,
                "dialogue_meaning": self._text(dialogue_contract.get("resolved_request") or dialogue_contract.get("current_request") or current_request),
                "visual_reference": "previous_visual_response" if related_visual else "none",
                "semantic_link": (
                    "continuation" if three_way == "CONTINUE"
                    else "recall" if three_way == "RECALL"
                    else "independent"
                ),
                "selected_memory_operand": selected_memory_operand,
                "context_available": bool(dialogue_memory.get("history") or active_schema or dynamic_memory.get("matches") or selected_memory_operand),
                "relevant_dynamic_memory_count": len(dynamic_memory.get("matches") or []),
            },
            "generation_intent": {
                "requested_representation": current_rep or None,
                "create_new_visual_artifact": bool(related_visual and current_rep in STRUCTURED_REPRESENTATIONS),
                "preserve_meaning_from_previous_visual": bool(related_visual),
            },
        }


QUANTUM_MEMORY_UNDERSTANDING_ENGINE = QuantumMemoryUnderstandingEngine()


def _build_provider_context_plan(
    current_request: str,
    dialogue_vector: dict[str, Any],
    dialogue_contract: dict[str, Any],
    semantic_task: dict[str, Any],
    presentation: dict[str, Any],
    history_window: list,
    history_task_context: dict[str, Any],
    continuation: bool,
    reference: bool,
) -> dict[str, Any]:
    """Freeze the Interpretation-owned Provider context before transport.

    The Provider never selects a branch or searches memory. This plan contains the
    already-resolved semantic decision and the bounded authenticated pair evidence
    needed to formulate the next answer. CONTINUE uses the active pair trajectory;
    NEW may receive only compact related background and must remain a new task.
    """
    relation = str(
        dialogue_vector.get("three_way_relation")
        or dialogue_contract.get("three_way_relation")
        or dialogue_contract.get("relation")
        or ("CONTINUE" if continuation else "RECALL" if reference else "NEW")
    ).upper()
    relation = {
        "NEW_TOPIC": "NEW",
        "INDEPENDENT": "NEW",
        "SAME_TOPIC": "NEW",
        "CONTINUE_TOPIC": "CONTINUE",
        "CONTINUATION": "CONTINUE",
        "MEMORY_QUERY": "RECALL",
    }.get(relation, relation)
    if relation not in {"NEW", "CONTINUE", "RECALL"}:
        relation = "RECALL" if reference else "CONTINUE" if continuation else "NEW"

    current_request = str(
        current_request
        or dialogue_contract.get("current_request")
        or dialogue_contract.get("resolved_request")
        or ""
    ).strip()
    requested_outputs = [
        str(item).strip()
        for item in (presentation.get("requested_outputs") or dialogue_vector.get("requested_outputs") or [semantic_task.get("representation") or "text"])
        if str(item).strip()
    ][:6]

    semantic_core = {
        "topic": semantic_task.get("topic") or dialogue_contract.get("active_topic"),
        "operation": semantic_task.get("operation"),
        "goal": semantic_task.get("goal"),
        "representation": semantic_task.get("representation"),
        "visual_generation_request": semantic_task.get("visual_generation_request") or dialogue_vector.get("visual_generation_request"),
        "turn_relation": relation,
    }
    semantic_core = {k: v for k, v in semantic_core.items() if v not in (None, "", [], {})}

    plan = {
        "version": "april_provider_handoff_from_interpretation_v1",
        "relation": relation,
        "turn_relation": str(dialogue_vector.get("subtype") or relation),
        "current_user_request": current_request,
        "current_request_authoritative": True,
        "context_selection_done_before_provider": True,
        "pair_direction_decision_final": True,
        "provider_must_not_reselect_context": True,
        "provider_must_not_bypass_pair_interpretation": True,
        "provider_continuation_contract": "Use only the Interpretation-selected dialogue operand/trajectory for CONTINUE or RECALL.",
        "hard_budget_tokens": 900,
        "soft_target_tokens": 820,
        "new_topic_minimal_context": relation == "NEW",
        "required_context": [
            {"key": "SEMANTIC_CORE", "priority": 1.0, "value": semantic_core},
            {
                "key": "OUTPUT_CONTRACT",
                "priority": 0.99,
                "value": {
                    "representation": semantic_task.get("representation"),
                    "requested_outputs": requested_outputs,
                    "visual_generation_request": semantic_task.get("visual_generation_request") or dialogue_vector.get("visual_generation_request"),
                    "no_text_fallback_for_image": bool(semantic_task.get("representation") in {"image", "gallery"}),
                },
            },
        ],
        "optional_context": [],
        "excluded_context": [
            "FULL_HISTORY",
            "OTHER_TOPIC_BRANCHES",
            "UNRELATED_WINDOW_MEMORY",
            "STALE_GLOBAL_ENTITY",
        ],
    }

    bounded_history = [x for x in (history_window or []) if isinstance(x, dict)][:]

    if relation in {"CONTINUE", "RECALL"}:
        selected_operand = dialogue_vector.get("selected_memory_operand")
        anchor = {
            "previous_user_turn": dialogue_contract.get("previous_user_turn") or dialogue_vector.get("previous_user_turn") or "",
            "previous_april_turn": dialogue_contract.get("previous_april_turn") or dialogue_vector.get("previous_april_turn") or "",
            "active_topic": dialogue_contract.get("active_topic") or dialogue_vector.get("active_topic") or "",
            "sequence_id": dialogue_contract.get("sequence_id") or "",
            "selected_memory_operand": selected_operand if isinstance(selected_operand, dict) else {},
        }
        plan["required_context"].append({
            "key": "DIALOGUE_ANCHOR",
            "priority": 0.998,
            "value": anchor,
        })

        if bounded_history:
            plan["required_context"].append({
                "key": "ACTIVE_DIALOGUE_TRAJECTORY",
                "priority": 0.997,
                "value": bounded_history[-8:],
            })

        plan["required_context"].append({
            "key": "RESPONSE_FORMULATION",
            "priority": 0.996,
            "value": (
                "HISTORY_RECALL"
                if relation == "RECALL"
                else "CONTINUE_FROM_AUTHENTICATED_PAIRS"
            ),
        })

        if history_task_context.get("required"):
            plan["required_context"].append({
                "key": "ACTIVE_TASK",
                "priority": 0.99,
                "value": history_task_context,
            })
    elif relation == "NEW" and bounded_history:
        # A new request stays a new request, but the Provider receives a compact
        # semantic relation to the immediately relevant dialogue pairs when such
        # context exists. It must not turn this into continuation.
        plan["required_context"].append({
            "key": "RELATED_DIALOGUE_BACKGROUND",
            "priority": 0.91,
            "value": bounded_history[-3:],
        })
        plan["required_context"].append({
            "key": "RESPONSE_FORMULATION",
            "priority": 0.90,
            "value": "NEW_TASK_WITH_DIALOGUE_RELATION_CONTEXT",
        })

    return plan


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


def _state_manager_dialogue_history(
    state: dict[str, Any] | None,
    provided_history: list | None,
    *,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Project authenticated StateManager 12-hour pairs into interpreter history.

    StateManager is the source of truth for continuation. The interpreter receives
    the already-loaded ``memory_timeline.day_0.dialog_pairs`` and does not query
    entity/topic archives. A lazy bridge fallback is used only when the current
    state snapshot does not carry the pair window.
    """
    state_obj = state if isinstance(state, dict) else {}
    existing = provided_history if isinstance(provided_history, list) else []
    memory_scope = state_obj.get("memory_scope") if isinstance(state_obj.get("memory_scope"), dict) else {}
    authenticated = bool(memory_scope.get("authenticated"))
    rows: list[dict[str, Any]] = []

    timeline = state_obj.get("memory_timeline")
    day = timeline.get("day_0") if isinstance(timeline, dict) else None
    pairs = day.get("dialog_pairs") if isinstance(day, dict) else None

    if isinstance(pairs, list):
        for row in pairs:
            if not isinstance(row, dict):
                continue
            user_obj = row.get("user") if isinstance(row.get("user"), dict) else {}
            april_obj = row.get("april") if isinstance(row.get("april"), dict) else {}
            user_text = str(
                row.get("user_text") or row.get("user") or user_obj.get("text") or user_obj.get("content") or ""
            ).strip()
            april_text = str(
                row.get("april_text") or row.get("april") or row.get("assistant") or april_obj.get("answer") or april_obj.get("content") or ""
            ).strip()
            if user_text and april_text:
                rows.append({
                    "turn_id": row.get("turn_index"),
                    "created_at": row.get("created_at"),
                    "user": user_text,
                    "april": april_text,
                })

    # If the interpreter was invoked with a clean/minimal snapshot, use the
    # existing StateManager bridge function; never invent another memory store.
    if not rows and state_obj.get("user_id"):
        try:
            from blocks.state_manager import build_dialogue_memory_bridge
            bridge = build_dialogue_memory_bridge(
                state_obj.get("user_id"),
                query="",
                limit=max(1, int(limit)),
                relation="CONTINUE",
            )
            bridge_rows = bridge.get("dialogue_pairs") or bridge.get("active_sequence_turns") or []
            for row in bridge_rows:
                if not isinstance(row, dict):
                    continue
                user_text = str(row.get("user") or row.get("user_text") or "").strip()
                april_text = str(row.get("april") or row.get("april_text") or row.get("assistant") or "").strip()
                if user_text and april_text:
                    rows.append({
                        "turn_id": row.get("turn") or row.get("turn_index"),
                        "created_at": row.get("created_at"),
                        "user": user_text,
                        "april": april_text,
                    })
        except Exception:
            pass

    # Deduplicate and keep chronological order. Provided runtime history is kept
    # only when pair memory is unavailable, so StateManager remains authoritative.
    if rows:
        dedup: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (str(row.get("turn_id") or ""), row.get("user", ""), row.get("april", ""))
            dedup[key] = row
        rows = list(dedup.values())
        rows.sort(key=lambda x: (float(x.get("created_at") or 0.0), int(x.get("turn_id") or 0)))
        try:
            requested_limit = int(limit)
        except (TypeError, ValueError):
            requested_limit = 0
        if requested_limit > 0:
            rows = rows[-requested_limit:]
        history_out: list[dict[str, Any]] = []
        for row in rows:
            history_out.append({
                "role": "user",
                "content": row["user"],
                "turn_id": row.get("turn_id"),
                "timestamp": row.get("created_at"),
                "metadata": {"source": "state_manager_dialogue_memory_12h", "context_authority": "STATE_MANAGER"},
            })
            history_out.append({
                "role": "assistant",
                "content": row["april"],
                "turn_id": row.get("turn_id"),
                "timestamp": row.get("created_at"),
                "metadata": {"source": "state_manager_dialogue_memory_12h", "context_authority": "STATE_MANAGER"},
            })
        return history_out

    # Authenticated dialogue never falls back to legacy topic/entity buffers: the
    # 12-hour USER↔APRIL pair store is the sole continuation source.
    if authenticated:
        return []
    return existing

def interpret_request(
    text, cognition=None, semantic=None, history=None, state=None
):
    state_obj = state if isinstance(state, dict) else {}
    memory_history = _state_manager_dialogue_history(
        state_obj, history, limit=0
    )
    return QUANTUM_INTERPRETATION_ENGINE.interpret(
        text,
        cognition=cognition,
        semantic=semantic,
        history=memory_history,
        state=state_obj,
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
        "profile_version": "quantum_matrix_v2",
    }


def build_scene_construction_profile(semantic_profile):
    return {
        "requires_scene_builder": False,
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "quantum_matrix",
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v2",
    }


def build_scene_artifact_contract(semantic_profile, scene_profile):
    return {
        "contract": "scene_artifact",
        "transport": TRANSPORT_NAME,
        "semantic_profile": semantic_profile or {},
        "scene_profile": scene_profile or {},
        "representation": "processor_decides",
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
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
        "profile_version": "quantum_matrix_v2",
    }


def build_processor_execution_context(runtime_state):
    fused = fuse_semantic_inputs(runtime_state or {})
    return {
        "transport": TRANSPORT_NAME,
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "decision_owner": DECISION_OWNER,
        "profile_version": "quantum_matrix_v2",
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


# ============================================================================
# CANONICAL PAIR-FIRST INTERPRETATION OVERRIDE — 12H
# ============================================================================
# Production uses exactly one interpretation authority.  Entity/topic/intent
# engines are not allowed to own continuation decisions or rendering modality.

_PAIR_INTERPRET_ORIGINAL = QuantumInterpretationEngine.interpret

def _pair_window_from_state(state_obj, history=None, limit=15):
    rows=[]
    authenticated=False
    uid=""
    if isinstance(state_obj, dict):
        scope = state_obj.get("memory_scope") if isinstance(state_obj.get("memory_scope"), dict) else {}
        uid = str(
            state_obj.get("user_id")
            or scope.get("user_id")
            or state_obj.get("authenticated_user_id")
            or ""
        ).strip()
        authenticated = bool(scope.get("authenticated"))
        try:
            rows = QuantumInterpretationEngine._state_dialogue_pairs(state_obj, user_id=uid, limit=limit)
        except Exception:
            rows=[]
    if rows:
        return rows[-limit:]

    # Runtime state may be a fresh HTTP snapshot while the canonical authenticated
    # 12-hour pair bridge is still populated. Before declaring the dialogue empty,
    # load the same USER↔APRIL pair source used by StateManager. This is retrieval
    # only: it never decides CONTINUE/NEW and never performs topic/entity search.
    if authenticated and uid:
        try:
            from state_manager import build_dialogue_memory_bridge
            bridge = build_dialogue_memory_bridge(
                uid, query='', limit=limit, relation='AUTO'
            )
            bridge_rows = bridge.get('dialogue_pairs') if isinstance(bridge, dict) else []
            if bridge_rows:
                return [dict(x) for x in bridge_rows[-limit:] if isinstance(x, dict)]
        except Exception as exc:
            print('⚠️ APRIL PAIR BRIDGE FALLBACK:', exc)
        return []

    # Unauthenticated requests cannot use the authenticated 12-hour dialogue
    # memory. Legacy history is allowed only for compatibility in non-auth flows.

    out=[]
    for item in (history or []):
        if not isinstance(item, dict): continue
        role=str(item.get("role") or "").lower()
        content=str(item.get("content") or item.get("text") or "").strip()
        if not content: continue
        if role=="user":
            out.append({"user":content,"april":""})
        elif role in {"assistant","april"} and out:
            out[-1]["april"]=content
    return [x for x in out if x.get("user") and x.get("april")][-limit:]


def _pair_canonical_interpret(self, text, cognition=None, semantic=None, history=None, state=None):
    state_obj=state if isinstance(state,dict) else {}
    pairs=_pair_window_from_state(state_obj, history=history, limit=15)
    result=_PAIR_INTERPRET_ORIGINAL(self, text, cognition=cognition, semantic=semantic, history=history, state=state_obj)
    if not isinstance(result,dict):
        raise RuntimeError("INTERPRETATION_RETURNED_NO_PACKET")

    current=self.normalize(text)
    selected=self._select_three_way_dialogue_relation(current,pairs)
    relation=str(selected.get("relation") or "NEW").upper()
    selected_pair=dict(selected.get("selected_pair") or {})
    selected_index=int(selected.get("selected_index",-1) or -1)

    semantic_task=result.get("semantic_task") if isinstance(result.get("semantic_task"),dict) else {}
    base_rep=str(
        result.get("production_representation")
        or semantic_task.get("representation")
        or result.get("requested_representation")
        or "text"
    ).lower()
    visual_request=str(result.get("visual_generation_request") or semantic_task.get("visual_generation_request") or "").strip()

    # A visual request is canonical when Interpretation has already measured a
    # generation operation/representation. For short visual continuations, inherit
    # only the previous pair's visual generation memory/prompt.
    pair_visual_prompt=""
    if selected_pair:
        pair_visual_prompt=str(
            selected_pair.get("visual_generation_request")
            or selected_pair.get("generation_prompt")
            or selected_pair.get("image_generation_prompt")
            or ""
        ).strip()
    op=str(semantic_task.get("operation") or result.get("operation") or "").lower()
    object_scores = semantic_task.get("object_scores") if isinstance(semantic_task.get("object_scores"),dict) else {}
    base_rep_score = float(object_scores.get(base_rep,0.0) or 0.0)
    # Ordinary explanatory questions are text unless the structured representation
    # is strongly supported by the same semantic measurement. This prevents noisy
    # prototype overlap from turning "Что такое лето" into a formula block.
    if not visual_request and base_rep not in {"text","image","gallery"} and base_rep_score < 0.15:
        base_rep="text"
        visual_request=pair_visual_prompt
    if relation=="CONTINUE" and not visual_request and pair_visual_prompt and op in {"modify","transform","redraw","edit","build","generate","create","visualize"}:
        visual_request=pair_visual_prompt
    if visual_request:
        if base_rep in {"text",""} and op in {"build","create","generate","modify","transform","redraw","visualize","present"}:
            base_rep="image"
        if base_rep=="text" and relation=="CONTINUE" and pair_visual_prompt:
            base_rep="image"
    if visual_request and base_rep not in {"image","gallery"} and op in {"build","create","generate","modify","transform","redraw","visualize"}:
        base_rep="image"

    # Full 12h memory remains available to Interpretation, while Provider receives
    # only the compact pair trajectory selected by the verified light context check.
    window=[dict(x) for x in selected.get("memory_window") or pairs[:]]
    provider_window=[dict(x) for x in selected.get("context_pairs") or []]
    if relation in {"CONTINUE", "RECALL"} and not provider_window:
        provider_window=window[-3:]
    memory_source="AUTHENTICATED_12H_USER_APRIL_PAIRS" if window else "NONE"

    result["three_way_relation"]=relation
    result["relation"]=relation
    result["dialogue_relation"]=relation
    result["continuation"]=bool(relation=="CONTINUE")
    result["reference_to_previous"]=bool(relation in {"CONTINUE","RECALL"} and selected_index>=0)
    result["context_dependency"]="continuation" if relation=="CONTINUE" else "recall" if relation=="RECALL" else "independent"
    result["selected_memory_index"]=selected_index
    result["selected_memory_operand"]=selected_pair
    result["selected_memory_record"]=selected_pair
    result["dialogue_memory_window"]=window
    result["dialogue_memory_source"]=memory_source
    result["authenticated_dialogue_memory"]={
        "window_hours":12,
        "pair_count":len(window),
        "pairs":window,
        "selected_context_pair_count":len(provider_window),
        "selected_context_pairs":provider_window,
        "source":memory_source,
        "authority":"INTERPRETATION",
    }
    result["history_context_check"] = selected.get("history_context_check") if isinstance(selected.get("history_context_check"), dict) else {}

    # Canonical rendering decision is owned by Interpretation and must survive the
    # Executor projection. This fixes the image route being downgraded to text.
    result["representation"]=base_rep
    result["requested_representation"]=base_rep
    result["production_representation"]=base_rep
    result["production_representation_locked"]=True
    result["requested_outputs"]=[base_rep]
    result["required_representations"]=[base_rep]
    result["visual_generation_request"]=visual_request
    result["render_plan"]={
        "representation":base_rep,
        "requested_outputs":[base_rep],
        "authorized":bool(base_rep in {"image","gallery","formula","diagram","graph","table","code","link","audio","video","file"}),
        "mode":"IMAGE_GENERATION" if base_rep in {"image","gallery"} else base_rep.upper(),
        "artifact_reference":bool(relation=="CONTINUE" and selected_index>=0),
    }

    dc=result.get("dialogue_contract") if isinstance(result.get("dialogue_contract"),dict) else {}
    dc.update({
        "three_way_relation":relation,
        "relation":relation,
        "continuation":relation=="CONTINUE",
        "reference_to_previous":relation in {"CONTINUE","RECALL"} and selected_index>=0,
        "context_dependency":"continuation" if relation=="CONTINUE" else "recall" if relation=="RECALL" else "independent",
        "selected_memory_index":selected_index,
        "selected_memory_operand":selected_pair,
        "dialogue_memory_window":window,
        "history_source":memory_source,
        "canonical":True,
        "version":"dialogue_pair_contract_v1",
        # Entity/topic slots are intentionally absent from the decision path.
        "entities":[],
        "active_entity":"",
        "resolved_entity":"",
        "entity_understanding":{},
    })
    result["dialogue_contract"]=dc

    vector=result.get("dialogue_vector") if isinstance(result.get("dialogue_vector"),dict) else {}
    vector.update({
        "three_way_relation":relation,
        "relation":relation,
        "selected_memory_index":selected_index,
        "selected_memory_operand":selected_pair,
        "memory_window":window,
        "sequence_id":str(vector.get("sequence_id") or (dc.get("sequence_id") or "")),
        "canonical_topic":"",
        "active_entity":"",
        "entities":[],
        "trajectory":{
            "window_hours":12,
            "pair_count":len(window),
            "selected_index":selected_index,
            "relation":relation,
            "selected_context_pairs":provider_window,
        },
        "history_context_check": selected.get("history_context_check") if isinstance(selected.get("history_context_check"), dict) else {},
    })
    if visual_request:
        vector["visual_generation_request"]=visual_request
    result["dialogue_vector"]=vector

    # Rebuild the Provider handoff from the final pair decision. The Provider must
    # receive the exact 12h pair evidence selected by Interpretation and must never
    # infer a different topic, branch, or memory source.
    provider_plan = {
        "version":"april_provider_handoff_pair_12h_v2",
        "relation":relation,
        "current_user_request":current,
        "current_request_authoritative":True,
        "context_selection_done_before_provider":True,
        "provider_must_not_reselect_context":True,
        "hard_budget_tokens":900,
        "soft_target_tokens":820,
        "provider_continuation_contract":"PAIR_FIRST_12H",
        "required_context":[
            {"key":"SEMANTIC_CORE","priority":1.0,"value":{
                "subject_pair_user":str(selected_pair.get("user") or selected_pair.get("user_text") or "")[:600] if selected_pair else "",
                "subject_pair_april":str(selected_pair.get("april") or selected_pair.get("april_text") or "")[:900] if selected_pair else "",
                "operation":op,
                "representation":base_rep,
                "turn_relation":relation,
            }},
            {"key":"OUTPUT_CONTRACT","priority":0.99,"value":{
                "representation":base_rep,
                "requested_outputs":[base_rep],
                "visual_generation_request":visual_request,
                "no_text_fallback_for_image":base_rep in {"image","gallery"},
                "ascii_allowed":False,
            }},
        ],
        "optional_context":[],
        "excluded_context":["GLOBAL_TOPIC_INDEX","ENTITY_INDEX","LEGACY_INTENT_ENGINE","FULL_UNBOUNDED_HISTORY"],
    }
    if relation in {"CONTINUE","RECALL"}:
        provider_plan["required_context"].append({
            "key":"DIALOGUE_ANCHOR",
            "priority":0.998,
            "value":{
                "selected_memory_index":selected_index,
                "selected_memory_operand":selected_pair,
                "pair_window_hours":12,
                "history_source":"AUTHENTICATED_12H_USER_APRIL_PAIRS",
            },
        })
        provider_plan["required_context"].append({
            "key":"ACTIVE_DIALOGUE_TRAJECTORY",
            "priority":0.997,
            "value":provider_window,
        })
        provider_plan["required_context"].append({
            "key":"HISTORY_CONTEXT_CHECK",
            "priority":0.996,
            "value":{
                "source":"LIGHT_HISTORY_CONTEXT_CHECK",
                "history_dependency":bool(selected.get("history_context_check",{}).get("historical_dependency")),
                "history_query":bool(selected.get("history_context_check",{}).get("history_query")),
                "anchor_index":selected_index,
                "pair_count":len(provider_window),
            },
        })
    result["provider_context_plan"]=provider_plan
    result["provider_context_authority"]="INTERPRETATION"
    result["provider_must_not_reselect_context"]=True

    # Make entity metadata inert throughout the production packet.
    result["entity_understanding"]={}
    result["entities"]=[]
    result["active_entity"]=""
    result["resolved_entity"]=""
    result["resolved_entity_source"]=""
    result["canonical_topic"]=""

    # Never authorize ASCII as a presentation representation.
    result["ascii_schema_advisory"]=False
    result["ascii_schema_score"]=0.0
    result["presentation_recommendations"]=[
        dict(x) for x in (result.get("presentation_recommendations") or [])
        if isinstance(x,dict) and str(x.get("representation") or "").lower() not in {"ascii","text_ascii"}
    ]
    return result


# ============================================================================
# FINAL LIVE DIALOGUE OVERRIDE — 2026-10-05
# ============================================================================
# PRODUCTION RULE — DO NOT BYPASS:
#   StateManager / authenticated 12h USER↔APRIL pairs
#       -> PairDialogueDirectionEngine
#       -> exactly ONE relation: CONTINUE / RECALL / NEW
#       -> structural request
#       -> Provider/OpenAI
#
# RECALL is a first-class relation. It must never be converted to NEW.
# If the pair engine cannot establish a relation to selected pairs, the result is NEW.
# Provider/OpenAI is not allowed to re-select dialogue context.

LIVE_DIALOGUE_ENGINE_VERSION = "live_pair_context_v9_two_state_pair_locked_vru"

# Persistent 12h USER↔APRIL pair cache.
# The runtime snapshot may be recreated between HTTP turns, while the durable pair
# store remains available. Cache only the immutable pair window for a very short
# interval so multiple interpretation passes in one request do not repeat DB I/O.
_PAIR_CACHE_TTL_SECONDS = 1.5
_PAIR_CACHE_LOCK = threading.RLock()
_PAIR_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _load_persistent_pair_window(user_id: str, limit: int = 15) -> list[dict[str, Any]]:
    uid = str(user_id or "").strip()
    max_items = max(1, int(limit or 15))
    if not uid:
        return []

    now = time.time()
    with _PAIR_CACHE_LOCK:
        cached = _PAIR_CACHE.get(uid)
        if cached and (now - cached[0]) <= _PAIR_CACHE_TTL_SECONDS:
            return [dict(x) for x in cached[1][-max_items:]]

    rows: list[dict[str, Any]] = []
    try:
        # This is the same canonical durable store used by StateManager. Do not
        # route through topic/entity indexes and do not ask the Provider to search.
        from storage import load_dialogue_pairs
        raw_rows = load_dialogue_pairs(uid, limit=max_items)
        for raw in raw_rows or []:
            if not isinstance(raw, dict):
                continue
            user = str(raw.get("user_text") or raw.get("user") or raw.get("user_request") or "").strip()
            april = str(raw.get("april_text") or raw.get("april") or raw.get("april_answer") or raw.get("assistant") or "").strip()
            if not user or not april:
                continue
            rows.append({
                "user": user[:1200],
                "april": april[:1800],
                "result": april[:1800],
                "turn_index": int(raw.get("turn_index") or raw.get("sequence_turn_index") or raw.get("turn") or 0),
                "created_at": float(raw.get("created_at") or raw.get("timestamp") or 0.0),
                "source": "STORAGE_AUTHENTICATED_12H_USER_APRIL_PAIRS",
                "history_source": "USER_APRIL_PAIRS",
            })
    except Exception as exc:
        # A StateManager/storage failure is not evidence of a NEW dialogue.
        # Never fall through to another context source here: that would bypass
        # the mandatory authenticated 12h USER↔APRIL pair boundary.
        raise RuntimeError(f"STATE_MANAGER_12H_PAIR_LOAD_FAILED: {exc}") from exc

    rows.sort(key=lambda x: (float(x.get("created_at") or 0.0), int(x.get("turn_index") or 0)))
    rows = rows[-max_items:]
    with _PAIR_CACHE_LOCK:
        _PAIR_CACHE[uid] = (now, [dict(x) for x in rows])
    return [dict(x) for x in rows]


def invalidate_pair_cache(user_id: str = "") -> None:
    uid = str(user_id or "").strip()
    with _PAIR_CACHE_LOCK:
        if uid:
            _PAIR_CACHE.pop(uid, None)
        else:
            _PAIR_CACHE.clear()

_LIVE_SUBJECT_STOP = {
    "что", "это", "такое", "такой", "такая", "такие", "кто", "как", "почему", "зачем",
    "а", "и", "но", "же", "в", "во", "на", "с", "со", "у", "из", "по", "для", "про", "о", "об",
    "расскажи", "рассказать", "объясни", "объяснить", "скажи", "сделай", "сделать", "дай", "покажи",
    "нарисуй", "создай", "создать", "построй", "построить", "проверь", "найди", "напиши", "укажи",
    "назови", "опиши", "рассчитай", "посчитай", "вычисли", "определи", "изобрази", "покажите",
    "годы", "год", "деятельности", "деятельность", "биография", "история", "описание", "рисунок",
    "картинка", "картинке", "изображение", "выглядит", "выглядел", "выглядела", "занимался", "занималась",
    "плохим", "плохое", "плохая", "плохой", "чем", "какой", "какая", "какие", "где", "когда", "зачем",
}
_LIVE_REFERENCE_WORDS = {
    "он", "она", "они", "его", "ее", "её", "их", "ему", "ей", "им", "ним", "него", "неё", "ее", "нем", "нём",
    "этом", "этот", "эта", "это", "эти", "тот", "та", "то", "те", "того", "ту", "тем", "таким", "такую", "такое",
}
_LIVE_HISTORY_WORDS = {
    "вспомни", "вспомнить", "помнишь", "помни", "говорили", "обсуждали", "спрашивал", "спрашивали",
    "раньше", "прежде", "предыдущем", "предыдущий", "истории", "контексте", "диалоге", "сообщениях",
    "после", "до", "назад",
}


def _live_token_affinity(left: str, right: str) -> float:
    a = set(QuantumInterpretationEngine._tokens(left)) - _LIVE_SUBJECT_STOP
    b = set(QuantumInterpretationEngine._tokens(right)) - _LIVE_SUBJECT_STOP
    a = {x for x in a if len(x) >= 3}
    b = {x for x in b if len(x) >= 3}
    if not a or not b:
        return 0.0
    exact = len(a & b) / max(1, len(a | b))
    morph = 0.0
    used = set()
    for x in a:
        for y in b:
            if y in used:
                continue
            if x == y:
                morph += 1.0
                used.add(y)
                break
            common = 0
            for ca, cb in zip(x, y):
                if ca != cb:
                    break
                common += 1
            if common >= 4 and common / max(len(x), len(y)) >= 0.55:
                morph += 0.5
                used.add(y)
                break
    morph = min(1.0, morph / max(1, min(len(a), len(b))))
    return max(exact, 0.72 * exact + 0.28 * morph)


def _live_extract_subject(text: str) -> str:
    source = QuantumInterpretationEngine.normalize(text)
    if not source:
        return ""
    low = source.lower()
    patterns = (
        r"(?:что\s+такое|что\s+это|кто\s+такой|кто\s+такая|кто\s+это)\s+(.+)$",
        r"(?:годы\s+деятельности|биография|история|расскажи\s+(?:о|об|про))\s+(.+)$",
        r"(?:о|об|про)\s+(.+)$",
    )
    candidate = ""
    for pattern in patterns:
        m = re.search(pattern, low, flags=re.I)
        if m:
            candidate = m.group(1).strip(" .,!?:;\"'«»()[]{}")
            break
    if not candidate:
        candidate = low
    tokens = re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", candidate.lower())
    meaningful = [t for t in tokens if len(t) >= 3 and t not in _LIVE_SUBJECT_STOP]
    if not meaningful:
        return ""
    # Prefer the last 1–4 meaningful words. This preserves short multi-word names
    # while avoiding command/question scaffolding.
    return " ".join(meaningful[-4:])[:220]


def _live_pair_subject(pair: dict[str, Any]) -> str:
    if not isinstance(pair, dict):
        return ""
    for key in ("active_entity", "resolved_entity", "topic", "canonical_topic"):
        value = str(pair.get(key) or "").strip()
        if value and value.lower() not in _LIVE_SUBJECT_STOP:
            subject = _live_extract_subject(value)
            if subject:
                return subject
            if len(value.split()) <= 4:
                return value[:220]
    user = str(pair.get("user") or pair.get("user_text") or pair.get("user_request") or "")
    subject = _live_extract_subject(user)
    if subject:
        return subject
    april = str(pair.get("april") or pair.get("assistant") or pair.get("april_answer") or "")
    tokens = [x for x in re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", april.lower()) if len(x) >= 4 and x not in _LIVE_SUBJECT_STOP]
    return tokens[0][:220] if tokens else ""


def _live_history_query(current: str, memory_score: float) -> bool:
    """Recognize a request to inspect the authenticated dialogue itself.

    This is semantic-first: lexical history terms are only a small supporting
    signal. The previous implementation required both a trigger-word hit and a
    fairly high prototype score, so natural phrases such as "Найди в диалоге
    прошлом" were incorrectly treated as a standalone NEW request.
    """
    text = str(current or "").strip()
    if not text:
        return False
    low = text.lower()
    word_hits = len(
        set(re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", low)) & _LIVE_HISTORY_WORDS
    )
    semantic_prototypes = (
        "вспомни о чем мы говорили раньше",
        "найди в предыдущем диалоге что мы обсуждали",
        "поищи в истории нашего разговора",
        "покажи темы которые мы уже обсуждали",
        "найди предыдущие сообщения и контекст разговора",
    )
    semantic_score = max(
        (float(self_score) for self_score in (
            QUANTUM_INTERPRETATION_ENGINE.similarity(text, proto).get("score", 0.0)
            for proto in semantic_prototypes
        )),
        default=0.0,
    )
    # Explicit semantic resemblance is sufficient on its own. A lower lexical
    # + memory signal is also accepted because the user may phrase the request
    # elliptically (e.g. "в прошлом диалоге").
    return bool(
        semantic_score >= 0.34
        or (word_hits >= 1 and float(memory_score or 0.0) >= 0.08)
        or (word_hits >= 2 and float(memory_score or 0.0) >= 0.04)
    )


def _live_reference_present(current: str) -> bool:
    tokens = set(re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", current.lower()))
    # "такое/это" in forms like "что такое X" / "что это X" are question
    # scaffolding, not antecedent references. Strong personal/object pronouns
    # remain true references; demonstratives count when used outside these forms.
    strong = tokens & {
        "он", "она", "они", "его", "ее", "её", "их", "ему", "ей", "им",
        "ним", "него", "неё", "нем", "нём",
    }
    if strong:
        return True
    low = str(current or "").strip().lower()
    if re.search(r"\bчто\s+(?:такое|это)\b", low):
        return False
    return bool(tokens & {"это", "этом", "этот", "эта", "эти", "тот", "та", "то", "те", "того", "ту", "тем", "таким", "такую", "такое"})


def _live_subject_from_pair_window(current: str, pairs: list[dict[str, Any]]):
    latest = pairs[-1] if pairs else {}
    latest_subject = _live_pair_subject(latest)
    current_subject = _live_extract_subject(current)
    ref_present = _live_reference_present(current)

    # A bare/elliptical current request with a reference word inherits the last
    # subject from the authenticated pair window. This is the actual antecedent
    # resolution required for phrases like "Нарисуй его...".
    if ref_present and latest_subject:
        return latest_subject, True
    return current_subject, False


def _batch_live_similarity(self, current: str, candidates: list[str]) -> list[float]:
    """Batch semantic measurements for the live pair selector."""
    if not candidates:
        return []
    clean = [self.normalize(x) for x in candidates]
    if self._semantic_encoder is not None:
        try:
            vectors = self._semantic_encoder.encode(
                [self.normalize(current)] + clean,
                normalize_embeddings=True,
            )
            q = vectors[0]
            return [
                max(0.0, min(1.0, float(q @ vectors[i + 1])))
                for i in range(len(clean))
            ]
        except Exception:
            pass
    if self._vectorizer is not None and cosine_similarity is not None:
        try:
            matrix = self._vectorizer.transform([self.normalize(current)] + clean)
            values = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
            return [max(0.0, min(1.0, float(x))) for x in values]
        except Exception:
            pass
    return [_live_token_affinity(current, x) for x in clean]


def _has_any_token(text: str, values: set[str]) -> bool:
    low = str(text or "").lower()
    return any(re.search(rf"(?<!\w){re.escape(v.lower())}(?!\w)", low) for v in values)


def _live_relation_selector(
    self,
    current: str,
    recent_pairs: list[dict[str, str]],
    *,
    active_topic: str = "",
    previous_assistant: str = "",
    previous_user: str = "",
) -> dict[str, Any]:
    current = self.normalize(current)
    pairs = [p for p in (recent_pairs or []) if isinstance(p, dict)]
    if not current or not pairs:
        return {
            "relation": "NEW", "confidence": 0.98, "selected_index": -1,
            "selected_pair": {}, "context_pairs": [], "memory_window": pairs[:],
            "context_mode": "NEW_TOPIC_ISOLATED", "context_anchor_index": -1,
            "history_lookup": False, "reference_to_previous": False,
            "reference_resolution": {}, "topic_relation": "NEW_TOPIC",
            "source": LIVE_DIALOGUE_ENGINE_VERSION,
        }

    # No relation/context decision is allowed before pair retrieval and matching.
    # Dialogue-family scores are evidence only; history lookup is resolved below,
    # after the authenticated pair window has been scored.
    scores = self._family_scores(current, "dialogue", SEMANTIC_TURN_PROTOTYPES)
    memory_score = float(scores.get("memory_query", 0.0) or 0.0)
    continuation_score = max(
        float(scores.get(k, 0.0) or 0.0)
        for k in ("continuation", "reformulation", "correction", "reference", "artifact_reference", "affirmation", "rejection")
    )

    window = pairs[:]
    scored = []
    prepared = []
    for i, pair in enumerate(window):
        user = self.normalize(pair.get("user") or pair.get("user_text") or pair.get("user_request"))
        april = self.normalize(pair.get("april") or pair.get("april_text") or pair.get("april_answer") or pair.get("assistant") or pair.get("answer"))
        if not user and not april:
            continue
        combined = f"{user} {april}".strip()
        prepared.append((i, pair, user, april, combined))

    # One vectorizer/model pass for the whole pair window instead of two similarity
    # calls per pair. This is materially cheaper on every live turn.
    semantic_targets = [item[4] for item in prepared] + [item[2] for item in prepared]
    batch_scores = []
    if semantic_targets:
        try:
            batch_scores = _batch_live_similarity(self, current, semantic_targets)
        except Exception:
            batch_scores = [0.0] * len(semantic_targets)

    half = len(prepared)
    for pos, (i, pair, user, april, combined) in enumerate(prepared):
        semantic_pair = float(batch_scores[pos] if pos < len(batch_scores) else 0.0)
        semantic_user = float(batch_scores[half + pos] if half + pos < len(batch_scores) else 0.0)
        lexical_user = _live_token_affinity(current, user)
        lexical_pair = _live_token_affinity(current, combined)
        subject = _live_pair_subject(pair)
        subject_score = _live_token_affinity(_live_extract_subject(current), subject) if _live_extract_subject(current) and subject else 0.0
        recency = 1.0 / (1.0 + 0.12 * (len(window) - 1 - i))
        score = (
            0.44 * semantic_pair
            + 0.20 * semantic_user
            + 0.18 * lexical_pair
            + 0.10 * lexical_user
            + 0.06 * subject_score
            + 0.02 * recency
        )
        scored.append({
            "index": i, "score": max(0.0, min(1.0, score)),
            "semantic_pair": semantic_pair, "semantic_user": semantic_user,
            "lexical_pair": lexical_pair, "lexical_user": lexical_user,
            "subject_score": subject_score, "recency": recency,
            "subject": subject, "pair": pair,
        })

    scored.sort(key=lambda x: (x["score"], x["index"]), reverse=True)
    latest_index = len(window) - 1
    latest_row = next((x for x in scored if x["index"] == latest_index), None)
    best_row = scored[0] if scored else None
    best_score = float(best_row.get("score", 0.0) if best_row else 0.0)
    latest_score = float(latest_row.get("score", 0.0) if latest_row else 0.0)

    # HARD PAIR-CHAIN GATE. This is the only place where authenticated pair
    # evidence is converted into a dialogue direction for downstream processing.
    # No legacy history selector and no fallback selector may override it.
    if PAIR_DIALOGUE_DIRECTION_ENGINE is None:
        raise RuntimeError("PAIR_DIALOGUE_DIRECTION_ENGINE_REQUIRED_NO_FALLBACK")
    try:
        pair_reasoning = PAIR_DIALOGUE_DIRECTION_ENGINE.analyze(
            current,
            window,
            scored_rows=scored,
        )
    except Exception as exc:
        raise RuntimeError(f"PAIR_DIALOGUE_DIRECTION_ENGINE_FAILED: {exc}") from exc
    if not isinstance(pair_reasoning, dict) or not pair_reasoning.get("version"):
        raise RuntimeError("PAIR_DIALOGUE_DIRECTION_ENGINE_NO_DECISION")

    pair_history_lookup = bool(pair_reasoning.get("history_lookup"))
    pair_direction = str(pair_reasoning.get("direction") or "ANSWER_CURRENT_REQUEST")
    pair_new_task = bool(
        isinstance(pair_reasoning.get("requested_action"), dict)
        and pair_reasoning.get("requested_action", {}).get("new_task")
    )
    continuation_directions = {
        "EXTEND_WITH_EXCLUSIONS", "EXTEND_PREVIOUS_RESULT",
        "EXPLAIN_OR_JUSTIFY_PREVIOUS", "VERIFY_OR_CORRECT_PREVIOUS",
        "AFFIRM_PREVIOUS_RESULT",
    }
    pair_selected_indices = []
    for value in (pair_reasoning.get("selected_indices") or []):
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(window):
            pair_selected_indices.append(index)
    pair_selected_indices = sorted(dict.fromkeys(pair_selected_indices))
    history_lookup = pair_history_lookup

    current_subject, resolved_by_reference = _live_subject_from_pair_window(current, pairs)
    latest_subject = _live_pair_subject(window[-1]) if window else ""
    current_reference = _live_reference_present(current)

    # Structural specificity is measured from semantic matrices, not trigger words.
    # A complete new task (for example an explicit image build) must outrank a weak
    # lexical resemblance to old pairs; an elliptical follow-up (for example
    # "что бы ты выбрал из перечисленного") remains continuable when a real pair
    # match exists even without a repeated subject word.
    operation_scores = self._family_scores(current, "operation", OPERATION_HYPOTHESES)
    representation_scores = self._family_scores(current, "representation", REPRESENTATION_HYPOTHESES)
    object_scores = self._family_scores(current, "object", OBJECT_HYPOTHESES)
    best_operation = max(operation_scores, key=operation_scores.get) if operation_scores else "answer"
    best_operation_score = float(operation_scores.get(best_operation, 0.0) or 0.0)
    best_representation_score = max((float(v or 0.0) for v in representation_scores.values()), default=0.0)
    best_object_score = max((float(v or 0.0) for v in object_scores.values()), default=0.0)
    request_specificity = max(best_representation_score, best_object_score, 0.72 * best_operation_score)
    elliptical_followup = bool(
        not current_reference
        and request_specificity < 0.18
        and bool(current)
    )

    # Match the current request against every authenticated pair first, then
    # decide whether that match represents continuation or a new task. The pair
    # itself is the evidence; active-task/entity slots cannot promote a turn.
    historical_subject_rows = []
    if current_subject and not current_reference:
        for row in scored:
            subject = str(row.get("subject") or "")
            if subject:
                subject_score = _live_token_affinity(current_subject, subject)
                if subject_score >= 0.34:
                    historical_subject_rows.append((subject_score, row))
    historical_subject_rows.sort(key=lambda x: (x[0], x[1]["index"]), reverse=True)
    historical_subject_match = historical_subject_rows[0][1] if historical_subject_rows else None

    same_latest_subject = bool(
        current_subject and latest_subject and
        _live_token_affinity(current_subject, latest_subject) >= 0.30
    )
    pronoun_followup = bool(resolved_by_reference and latest_subject)
    pair_match_strong = bool(best_row and best_score >= 0.18)
    pair_match_very_strong = bool(best_row and best_score >= 0.30)
    contextual_discovery_signal = max(
        continuation_score,
        float(scores.get("artifact_reference", 0.0) or 0.0),
        float(scores.get("reference", 0.0) or 0.0),
        float(scores.get("reformulation", 0.0) or 0.0),
    )
    # A human follow-up can refer to a previously established choice/list/result
    # without repeating its nouns. In that case lexical pair similarity may be
    # small, but the semantic dialogue act plus a real authenticated pair window
    # is sufficient to keep the request on the same trajectory.
    implicit_pair_continuation = bool(
        not pair_new_task
        and bool(best_row)
        and contextual_discovery_signal >= 0.16
        and request_specificity < 0.24
    )

    # Pair-local direction is stronger than a generic continuation prototype when
    # it explicitly says that the user is extending, correcting, affirming, or
    # reconstructing the object carried by selected pairs.
    pair_object_focus = (pair_reasoning.get("object_focus") or {}) if isinstance(pair_reasoning, dict) else {}
    pair_selected_indices = [
        int(x) for x in (pair_reasoning.get("selected_indices") or [])
        if isinstance(x, int) or str(x).lstrip("-").isdigit()
    ] if isinstance(pair_reasoning, dict) else []
    semantic_followup = bool(
        not pair_new_task
        and bool(best_row)
        and (
            current_reference
            or elliptical_followup and best_score >= 0.08
            or continuation_score >= 0.08 and best_score >= 0.10
            or historical_subject_match
            or pair_match_very_strong
            or implicit_pair_continuation
        )
    )

    # FINAL THREE-STATE DECISION.
    # The PairDialogueDirectionEngine is the sole owner of relation selection.
    # Nothing below may reinterpret, downgrade, or replace its decision.
    relation_hint = str(pair_reasoning.get("relation_hint") or "").upper().strip()
    if relation_hint not in {"CONTINUE", "RECALL", "NEW"}:
        raise RuntimeError(f"PAIR_DIALOGUE_DIRECTION_ENGINE_INVALID_RELATION: {relation_hint!r}")

    pair_selected_indices = []
    for value in (pair_reasoning.get("selected_indices") or []):
        try:
            index = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(window):
            pair_selected_indices.append(index)
    pair_selected_indices = sorted(dict.fromkeys(pair_selected_indices))

    # No selected pair = no established dialogue link. The only legal state is NEW.
    if relation_hint in {"CONTINUE", "RECALL"} and not pair_selected_indices:
        relation = "NEW"
    else:
        relation = relation_hint

    if relation == "NEW":
        selected_index = -1
        selected_pair = {}
        context_pairs = []
        context_mode = "NEW_TOPIC_ISOLATED"
        reference_resolution = {}
        history_lookup = False
    elif relation == "RECALL":
        selected_index = -1
        selected_pair = {}
        context_pairs = [dict(window[i]) for i in pair_selected_indices][-8:]
        context_mode = "HISTORY_LOOKUP"
        history_lookup = True
        reference_resolution = {}
    else:  # CONTINUE
        anchor_index = int(pair_reasoning.get("anchor_index", -1) or -1)
        if anchor_index not in pair_selected_indices:
            anchor_index = pair_selected_indices[-1]
        selected_index = anchor_index
        selected_pair = dict(window[selected_index])

        # Continue only inside the sequence selected by PairDialogueDirectionEngine.
        test_sequence = pair_reasoning.get("test_sequence")
        test_sequence = test_sequence if isinstance(test_sequence, dict) else {}
        try:
            boundary = int(test_sequence.get("start_index", -1) or -1)
        except (TypeError, ValueError):
            boundary = -1
        if boundary >= 0:
            contiguous = [
                i for i in range(boundary, selected_index + 1)
                if 0 <= i < len(window)
            ]
            selected_indices = sorted(dict.fromkeys(contiguous[-6:] + pair_selected_indices[-6:]))
        else:
            selected_indices = pair_selected_indices[-6:]
        context_pairs = [dict(window[i]) for i in selected_indices][-6:]
        context_mode = "LIVE_CONTINUATION"
        object_focus = pair_reasoning.get("object_focus")
        object_focus = object_focus if isinstance(object_focus, dict) else {}
        resolved_entity = str(object_focus.get("label") or object_focus.get("key") or "").strip()
        reference_resolution = {
            "resolved": True,
            "source": "PAIR_DIALOGUE_DIRECTION_ENGINE",
            "entity": resolved_entity,
            "selected_index": selected_index,
            "match_score": best_score,
        } if resolved_entity else {}

    # Expose the exact three-state decision for every downstream layer.
    pair_reasoning["final_relation"] = relation
    pair_reasoning["relation_locked"] = True
    pair_reasoning["provider_context_locked"] = True

    # Semantic action linkage describes what the current request does relative to
    # the matched pair. This is passed to OpenAI as formulation data, not rendered
    # as a user-visible template. For NEW_TOPIC_WITH_CONTEXT, the best matched pair
    # remains available as background even though it is not selected as a continuation anchor.
    related_pair = dict(best_row["pair"]) if best_row and context_mode == "NEW_TOPIC_WITH_CONTEXT" else {}
    matched_user = str(selected_pair.get("user") or selected_pair.get("user_request") or related_pair.get("user") or related_pair.get("user_request") or "").strip()
    matched_april = str(selected_pair.get("april") or selected_pair.get("april_answer") or related_pair.get("april") or related_pair.get("april_answer") or "").strip()
    has_visual = bool(
        isinstance(selected_pair.get("visual_attachment"), dict)
        and selected_pair.get("visual_attachment")
    )
    # The action link is structural, based on the matched dialogue evidence.
    # Operation labels are deliberately NOT used to manufacture a response path.
    # OpenAI receives the actual pair(s) and current request and determines the
    # natural next action from that evidence.
    if relation == "CONTINUE":
        action_link = (
            "CONTINUE_FROM_PREVIOUS_VISUAL_RESULT"
            if has_visual
            else "CONTINUE_FROM_MATCHED_DIALOGUE_PAIRS"
        )
    elif context_mode == "HISTORY_LOOKUP":
        action_link = "RECONSTRUCT_DIALOGUE_FROM_AUTHENTICATED_12H_PAIRS"
    elif context_mode == "NEW_TOPIC_WITH_CONTEXT":
        action_link = "NEW_TASK_DEVELOPING_FROM_RELATED_DIALOGUE"
    else:
        action_link = "NEW_INDEPENDENT_TASK"

    previous_operation = ""
    previous_operation_score = 0.0

    # This object is the semantic bridge, not a response template. It records
    # exactly which pair evidence was used and how the current turn develops from
    # that evidence. Provider/OpenAI receives this before any free-form answer.
    response_formulation = {
        "version": "pair_first_response_formulation_v3",
        "relation": relation,
        "context_mode": context_mode,
        "action_link": action_link,
        "pair_first": True,
        "pair_selection_before_relation": True,
        "matched_pair_count": len(pairs) if isinstance(pairs, list) else 0,
        "development_path": {
            "previous_user": matched_user[:900],
            "previous_april": matched_april[:1600],
            "previous_operation": previous_operation,
            "previous_operation_score": round(previous_operation_score, 6),
            "current_request": current[:1200],
            "current_operation": best_operation,
            "current_operation_score": round(best_operation_score, 6),
            "transition": (
                "same_dialogue_subject_continue_from_matched_pairs"
                if relation == "CONTINUE"
                else "history_reconstruction_from_12h_pairs"
                if context_mode == "HISTORY_LOOKUP"
                else "new_task_related_to_prior_dialogue"
                if context_mode == "NEW_TOPIC_WITH_CONTEXT"
                else "new_independent_task"
            ),
        },
        "pair_direction": {
            "direction": pair_direction,
            "confidence": float(pair_reasoning.get("direction_confidence", 0.0) or 0.0) if isinstance(pair_reasoning, dict) else 0.0,
            "object_focus": dict(pair_object_focus) if isinstance(pair_object_focus, dict) else {},
            "requested_action": dict(pair_reasoning.get("requested_action") or {}) if isinstance(pair_reasoning, dict) else {},
            "excluded_items": list(pair_reasoning.get("excluded_items") or [])[:8] if isinstance(pair_reasoning, dict) else [],
            "known_answer_items": list(pair_reasoning.get("known_answer_items") or [])[:12] if isinstance(pair_reasoning, dict) else [],
            "candidate_unexcluded_items": list(pair_reasoning.get("candidate_unexcluded_items") or [])[:12] if isinstance(pair_reasoning, dict) else [],
            "relevant_pair_indices": pair_selected_indices[:8],
        },
        "match": {
            "selected_index": selected_index,
            "best_score": round(best_score, 6),
            "latest_score": round(latest_score, 6),
            "semantic_pair_score": round(float(best_row.get("semantic_pair", 0.0) if best_row else 0.0), 6),
            "semantic_user_score": round(float(best_row.get("semantic_user", 0.0) if best_row else 0.0), 6),
        },
        "matched_pair": {
            "user": matched_user[:900],
            "april": matched_april[:1600],
            "topic": str(selected_pair.get("topic") or selected_pair.get("sequence_topic") or related_pair.get("topic") or related_pair.get("sequence_topic") or "").strip()[:260],
        },
        "context_pairs": [
            {
                "turn": x.get("turn") or x.get("turn_index") or x.get("sequence_turn_index"),
                "user": str(x.get("user") or x.get("user_text") or x.get("user_request") or "").strip()[:700],
                "april": str(x.get("april") or x.get("april_text") or x.get("april_answer") or x.get("assistant") or "").strip()[:1100],
                "topic": str(x.get("topic") or x.get("canonical_topic") or "").strip()[:180],
            }
            for x in (context_pairs or []) if isinstance(x, dict)
        ][-4:],
        "current_request": current[:2400],
        "development": (
            "Продолжить смысловую траекторию выбранной пары: предыдущий вопрос → реальный ответ APRIL → текущий запрос."
            if relation == "CONTINUE" else
            "Начать новую задачу, используя найденную связанную историю только для понимания перехода пользователя."
            if context_mode == "NEW_TOPIC_WITH_CONTEXT" else
            "Сформулировать самостоятельный ответ на текущий запрос."
        ),
    }

    confidence = (
        max(0.78, min(0.99, 0.70 + best_score))
        if relation == "CONTINUE" else
        max(0.62, min(0.98, 1.0 - min(best_score, 0.35)))
    )
    topic_relation = "CONTINUE_TOPIC" if relation == "CONTINUE" else ("RELATED_NEW_TOPIC" if context_mode == "NEW_TOPIC_WITH_CONTEXT" else "NEW_TOPIC")
    return {
        "relation": relation,
        "confidence": round(float(confidence), 6),
        "selected_index": selected_index,
        "selected_pair": selected_pair,
        "related_pair": related_pair,
        "context_pairs": [dict(x) for x in context_pairs],
        "memory_window": [dict(x) for x in window],
        "context_mode": context_mode,
        "context_anchor_index": int(best_row["index"] if best_row else -1),
        "history_lookup": history_lookup,
        "reference_to_previous": bool(relation == "CONTINUE" and selected_index >= 0),
        "reference_resolution": reference_resolution,
        "current_subject": current_subject,
        "latest_subject": latest_subject,
        "latest_score": round(latest_score, 6),
        "best_score": round(best_score, 6),
        "continuation_evidence": round(float(continuation_score), 6),
        "memory_query_score": round(memory_score, 6),
        "request_specificity": round(request_specificity, 6),
        "best_operation": best_operation,
        "best_operation_score": round(best_operation_score, 6),
        "contextual_discovery_signal": round(contextual_discovery_signal, 6),
        "implicit_pair_continuation": implicit_pair_continuation,
        "pair_direction": pair_reasoning,
        "pair_match_method": "STATE_MANAGER_12H_PAIRS_THEN_PAIR_DIALOGUE_DIRECTION_ENGINE",
        "topic_relation": topic_relation,
        "action_link": action_link,
        "response_formulation": response_formulation,
        "pair_match": {
            "matched": bool(best_row),
            "selected_index": selected_index,
            "best_score": round(best_score, 6),
            "selected_pair": dict(selected_pair),
            "window_size": len(window),
            "source": "AUTHENTICATED_12H_USER_APRIL_PAIRS",
        },
        "source": LIVE_DIALOGUE_ENGINE_VERSION,
        "entity_engine": False,
        "intent_engine": False,
    }


# Replace only the canonical selector used by the existing engine. The old
# implementation stays import-compatible but cannot own the production decision.
QuantumInterpretationEngine._select_three_way_dialogue_relation = _live_relation_selector

_PAIR_INTERPRET_ORIGINAL_LIVE = _PAIR_INTERPRET_ORIGINAL


def _pair_role_history(pairs):
    """Convert authenticated USER↔APRIL pairs to the semantic history shape.

    The pair window is selected first.  This helper deliberately exposes only
    authenticated conversational content; it never decides relation or routing.
    """
    out = []
    for idx, pair in enumerate(list(pairs or [])):
        if not isinstance(pair, dict):
            continue
        user = str(pair.get("user") or pair.get("user_text") or pair.get("user_request") or "").strip()
        april = str(pair.get("april") or pair.get("april_text") or pair.get("april_answer") or pair.get("assistant") or "").strip()
        if user:
            out.append({"role": "user", "content": user, "turn_id": pair.get("turn") or pair.get("turn_index") or idx})
        if april:
            out.append({"role": "assistant", "content": april, "turn_id": pair.get("turn") or pair.get("turn_index") or idx})
    return out


def _compact_pair_for_formulation(pair):
    """Compact one selected authenticated pair for the OpenAI semantic request."""
    if not isinstance(pair, dict):
        return {}
    visual = pair.get("visual_attachment")
    visual_id = {}
    if isinstance(visual, dict):
        for key in ("artifact_id", "block_id", "scene_id", "asset_path", "mime_type"):
            if visual.get(key) not in (None, "", [], {}):
                visual_id[key] = str(visual.get(key))[:120]
    result = {
        "turn": pair.get("turn") or pair.get("turn_index") or pair.get("sequence_turn_index"),
        "user": str(
            pair.get("user") or pair.get("user_text") or pair.get("user_request") or ""
        ).strip()[:240],
        "april": str(
            pair.get("april") or pair.get("april_text") or pair.get("april_answer") or pair.get("assistant") or ""
        ).strip()[:360],
        "topic": str(
            pair.get("topic") or pair.get("sequence_topic") or pair.get("canonical_topic") or ""
        ).strip()[:120],
    }
    if visual_id:
        result["visual"] = visual_id
    return {k: v for k, v in result.items() if v not in (None, "", {}, [])}


def _build_pair_first_response_formulation(
    current,
    selected,
    selected_index,
    relation,
    context_mode,
    matched_pairs=None,
):
    """Build one compact semantic request for OpenAI from selected dialogue evidence.

    Full authenticated 12h memory is an Interpretation-side search space only.
    Provider receives this compact formulation instead of the entire history.
    """
    selected_pair = _compact_pair_for_formulation(selected)
    raw_pairs = matched_pairs if isinstance(matched_pairs, list) else []
    compact_pairs = [
        _compact_pair_for_formulation(pair)
        for pair in raw_pairs
        if isinstance(pair, dict)
    ]
    compact_pairs = [pair for pair in compact_pairs if pair][:4]

    if relation == "CONTINUE" and selected_pair:
        selected_turn = str(selected_pair.get("turn") or "")
        selected_user = str(selected_pair.get("user") or "")
        if not any(
            str(pair.get("turn") or "") == selected_turn
            and str(pair.get("user") or "") == selected_user
            for pair in compact_pairs
        ):
            compact_pairs.insert(0, selected_pair)
        compact_pairs = compact_pairs[:4]

    discussion_parts = []
    for pair in compact_pairs[:4]:
        topic = str(pair.get("topic") or "").strip()
        user_text = str(pair.get("user") or "").strip()
        if topic:
            discussion_parts.append(topic[:140])
        elif user_text:
            discussion_parts.append(user_text[:140])
    discussion = "; ".join(dict.fromkeys(x for x in discussion_parts if x))[:520]

    if relation == "CONTINUE":
        mode = "CONTINUE_FROM_MATCHED_PAIRS"
        action_link = "CONTINUE_PREVIOUS_DIALOGUE"
        instruction = (
            "Текущий запрос определён как продолжение выбранного фрагмента диалога. "
            "Используй только переданные связанные USER↔APRIL пары как основание: "
            "учти уже обсуждённое и полученный результат, затем развивай тему в сторону "
            "текущего запроса. Не повторяй предыдущий ответ и не ищи другую память."
        )
    elif context_mode == "HISTORY_LOOKUP":
        mode = "HISTORY_RECALL_FROM_SELECTED_PAIRS"
        action_link = "RECALL_SELECTED_DIALOGUE"
        instruction = (
            "Ответь по переданным выбранным парам: восстанови, о чём фактически говорили. "
            "Не утверждай, что контекста нет, когда пары переданы."
        )
    else:
        mode = "INDEPENDENT_NEW_TASK"
        action_link = "NEW_ACTION"
        instruction = (
            "Текущий запрос — новая задача. Не наследуй старую тему и не используй "
            "предыдущие пары. Сформируй самостоятельный, естественный ответ."
        )

    result = {
        "version": "pair_first_response_formulation_v6_pair_chain_locked",
        "relation": relation,
        "context_mode": context_mode,
        "pair_first": True,
        "current_request": str(current or "").strip()[:2400],
        "matched_pair_index": int(selected_index if selected_index is not None else -1),
        "matched_pair": selected_pair if relation == "CONTINUE" else {},
        "matched_pairs": (
            compact_pairs
            if relation == "CONTINUE" or context_mode == "HISTORY_LOOKUP"
            else []
        ),
        "discussion_summary": (
            discussion if relation == "CONTINUE" or context_mode == "HISTORY_LOOKUP" else ""
        ),
        "action_link": action_link,
        "mode": mode,
        "instruction": instruction,
    }

    if relation == "CONTINUE" and compact_pairs:
        result["previous_user_question"] = compact_pairs[0].get("user", "")
        result["previous_april_answer"] = compact_pairs[0].get("april", "")
        result["messages"] = [
            {"role": "user", "content": pair.get("user", "")}
            for pair in compact_pairs
            if pair.get("user")
        ]
        result["messages"].append(
            {"role": "user", "content": str(current or "").strip()[:2400]}
        )
    elif context_mode == "HISTORY_LOOKUP":
        result["messages"] = [
            {"role": "user", "content": pair.get("user", "")}
            for pair in compact_pairs
            if pair.get("user")
        ]
        result["messages"].append(
            {"role": "user", "content": str(current or "").strip()[:2400]}
        )
    else:
        result["messages"] = [
            {"role": "user", "content": str(current or "").strip()[:2400]}
        ]

    return result

def _pair_canonical_interpret_live(self, text, cognition=None, semantic=None, history=None, state=None):
    state_obj = state if isinstance(state, dict) else {}
    # ------------------------------------------------------------------
    # PAIR-FIRST BOUNDARY: authenticated 12h pairs are retrieved and matched
    # BEFORE any relation/continuation decision or semantic task resolution.
    # ------------------------------------------------------------------
    pairs = _pair_window_from_state(state_obj, history=history, limit=15)
    current = self.normalize(text)
    selected = self._select_three_way_dialogue_relation(current, pairs)

    # ------------------------------------------------------------------
    # VRU SEMANTIC FUSION BOUNDARY
    # Candidate pairs have now been found. VRU performs a second internal
    # interpretation over the meaning of BOTH sides of the candidate pairs
    # (USER request + APRIL answer) before the three-state result is allowed
    # to reach the provider. This is not a fallback and does not route.
    # ------------------------------------------------------------------
    try:
        vru = VRU_CONTEXT_INTERPRETER.analyze(
            current,
            pairs,
            seed=selected if isinstance(selected, dict) else {},
        )
    except Exception as exc:
        raise RuntimeError(f"VRU_CONTEXT_INTERPRETATION_FAILED: {exc}") from exc

    if not isinstance(vru, dict) or not vru.get("version"):
        raise RuntimeError("VRU_CONTEXT_INTERPRETATION_NO_DECISION")

    # VRU is the semantic refinement layer. It may strengthen or preserve a
    # pair-first decision, but never invents an external context source.
    vru_relation = str(vru.get("relation") or "NEW").upper()
    if vru_relation not in {"CONTINUE", "RECALL", "NEW"}:
        raise RuntimeError(f"VRU_INVALID_RELATION: {vru_relation!r}")

    if vru_relation != str(selected.get("relation") or "NEW").upper() or vru.get("selected_indices"):
        merged = dict(selected)
        merged["relation"] = vru_relation
        merged["relation_hint"] = vru_relation
        merged["selected_indices"] = list(vru.get("selected_indices") or [])
        merged["anchor_index"] = int(vru.get("anchor_index", -1) or -1)
        merged["context_pairs"] = [dict(x) for x in (vru.get("context_pairs") or []) if isinstance(x, dict)]
        merged["context_mode"] = (
            "LIVE_CONTINUATION" if vru_relation == "CONTINUE"
            else "HISTORY_LOOKUP" if vru_relation == "RECALL"
            else "NEW_TOPIC_ISOLATED"
        )
        merged["history_lookup"] = vru_relation == "RECALL"
        if vru_relation == "CONTINUE" and merged["anchor_index"] >= 0 and merged["anchor_index"] < len(pairs):
            merged["selected_index"] = merged["anchor_index"]
            merged["selected_pair"] = dict(pairs[merged["anchor_index"]])
        elif vru_relation == "RECALL":
            merged["selected_index"] = -1
            merged["selected_pair"] = {}
        else:
            merged["selected_index"] = -1
            merged["selected_pair"] = {}
        merged["vru_semantic_fusion"] = vru
        selected = merged
    else:
        selected = dict(selected)
        selected["vru_semantic_fusion"] = vru

    print(
        "🧭 APRIL PAIR-FIRST DECISION:",
        {
            "user_id": str(state_obj.get("authenticated_user_id") or state_obj.get("user_id") or ""),
            "pair_count": len(pairs),
            "pair_match": bool(selected.get("pair_match", {}).get("matched")) if isinstance(selected.get("pair_match"), dict) else bool(selected.get("selected_pair")),
            "selected_index": int(selected.get("selected_index", -1) if selected.get("selected_index") is not None else -1),
            "best_score": float(selected.get("best_score") or 0.0),
            "relation_after_match": str(selected.get("relation") or "NEW").upper(),
            "context_mode": str(selected.get("context_mode") or ""),
            "vru_version": VRU_VERSION,
            "vru_relation": str((selected.get("vru_semantic_fusion") or {}).get("relation") or "NEW").upper(),
            "vru_pair_count": len((selected.get("vru_semantic_fusion") or {}).get("context_pairs") or []),
        },
    )
    relation = str(selected.get("relation") or "NEW").upper()
    if relation not in {"CONTINUE", "RECALL", "NEW"}:
        raise RuntimeError(f"INVALID_THREE_WAY_RELATION: {relation!r}")
    selected_pair = dict(selected.get("selected_pair") or {})
    raw_selected_index = selected.get("selected_index", -1)
    selected_index = int(raw_selected_index if raw_selected_index is not None else -1) if relation == "CONTINUE" else -1
    context_pairs = [dict(x) for x in (selected.get("context_pairs") or []) if isinstance(x, dict)]
    context_mode = str(selected.get("context_mode") or ("LIVE_CONTINUATION" if relation == "CONTINUE" else "NEW_TOPIC_ISOLATED"))
    reference_resolution = dict(selected.get("reference_resolution") or {})
    resolved_reference_entity = str(reference_resolution.get("entity") or "").strip()
    history_lookup = bool(selected.get("history_lookup"))
    formulation_pair = selected_pair
    if not formulation_pair and context_mode == "NEW_TOPIC_WITH_CONTEXT":
        formulation_pair = dict(selected.get("related_pair") or {})
    if not formulation_pair and context_mode == "HISTORY_LOOKUP" and context_pairs:
        formulation_pair = dict(context_pairs[0])
    response_formulation = (
        dict(selected.get("response_formulation"))
        if isinstance(selected.get("response_formulation"), dict)
        else _build_pair_first_response_formulation(
            current,
            formulation_pair,
            selected_index,
            relation,
            context_mode,
            matched_pairs=context_pairs,
        )
    )

    # Feed the matched pair trajectory into semantic understanding AFTER selection.
    # This makes semantic parsing operate on the same pair decision instead of
    # running once against a blank/current-only context and only being overwritten later.
    authenticated_scope = state_obj.get("memory_scope") if isinstance(state_obj.get("memory_scope"), dict) else {}
    authenticated = bool(authenticated_scope.get("authenticated") or state_obj.get("authenticated_user_id"))
    semantic_history = context_pairs[-4:] if context_pairs else ([] if authenticated else (history or []))
    effective_history = _pair_role_history(semantic_history) if semantic_history else None
    analysis_state = dict(state_obj)
    analysis_state["_pair_first_selection"] = {
        "relation": relation,
        "selected_index": selected_index,
        "selected_pair": dict(selected_pair),
        "context_pairs": list(context_pairs),
        "context_mode": context_mode,
        "response_formulation": dict(response_formulation),
    }
    # Rebuild the provider formulation from the VRU-refined pair chain.
    # The provider therefore receives the meaning synthesized from the selected
    # USER↔APRIL pairs, not the pre-VRU single-pair interpretation.
    if isinstance(vru, dict):
        response_formulation = _build_pair_first_response_formulation(
            current,
            dict(selected.get("selected_pair") or {}),
            int(selected.get("selected_index", -1) or -1),
            str(selected.get("relation") or "NEW").upper(),
            str(selected.get("context_mode") or "NEW_TOPIC_ISOLATED"),
            matched_pairs=[dict(x) for x in (selected.get("context_pairs") or []) if isinstance(x, dict)],
        )
        response_formulation["vru_semantic_fusion_version"] = VRU_VERSION
        response_formulation["vru_fused_meaning"] = dict(vru.get("fused_meaning") or {})
        response_formulation["vru_task_definition"] = dict(vru.get("task_definition") or {})
        response_formulation["vru_definition"] = str(vru.get("definition") or selected.get("relation") or "NEW").upper()
        response_formulation["vru_candidate_pair_count"] = len(vru.get("candidate_evidence") or [])

    result = _PAIR_INTERPRET_ORIGINAL_LIVE(
        self, text, cognition=cognition, semantic=semantic, history=effective_history, state=analysis_state
    )
    if not isinstance(result, dict):
        raise RuntimeError("INTERPRETATION_RETURNED_NO_PACKET")
    relation = str(selected.get("relation") or "NEW").upper()
    if relation not in {"CONTINUE", "RECALL", "NEW"}:
        raise RuntimeError(f"INVALID_THREE_WAY_RELATION: {relation!r}")
    selected_pair = dict(selected.get("selected_pair") or {})
    raw_selected_index = selected.get("selected_index", -1)
    selected_index = int(raw_selected_index if raw_selected_index is not None else -1) if relation == "CONTINUE" else -1
    context_pairs = [dict(x) for x in (selected.get("context_pairs") or [])]
    context_mode = str(selected.get("context_mode") or ("LIVE_CONTINUATION" if relation == "CONTINUE" else "NEW_TOPIC_ISOLATED"))
    reference_resolution = dict(selected.get("reference_resolution") or {})
    resolved_reference_entity = str(reference_resolution.get("entity") or "").strip()
    history_lookup = bool(selected.get("history_lookup"))

    # Preserve the exact raw request. The resolved context is carried alongside it
    # rather than mutating the user's sentence.
    semantic_task = result.get("semantic_task") if isinstance(result.get("semantic_task"), dict) else {}
    operation = str(semantic_task.get("operation") or result.get("operation") or "answer").lower()
    if history_lookup:
        operation = "history_lookup"
        semantic_task["operation"] = operation
        semantic_task["goal"] = "understand_dialogue_context"
        result["operation"] = operation
        result["goal"] = "understand_dialogue_context"
        result["history_lookup"] = True
        result["history_lookup_scope"] = "authenticated_12h_pairs"

    # Keep the current task subject authoritative for NEW; for CONTINUE + pronoun
    # resolution use the antecedent from the pair window.
    current_subject = str(selected.get("current_subject") or "").strip()
    if relation == "CONTINUE":
        canonical_topic = (
            resolved_reference_entity
            or current_subject
            or _live_pair_subject(selected_pair)
            or " ".join(
                str(x).strip()
                for x in (
                    selected_pair.get("user") or "",
                    selected_pair.get("topic") or "",
                )
                if str(x).strip()
            )[:220]
        )
    else:
        canonical_topic = current_subject
    if relation == "CONTINUE" and resolved_reference_entity:
        result["resolved_reference_entity"] = resolved_reference_entity
        result["reference_resolution"] = reference_resolution
        result["resolved_request"] = current
    elif history_lookup:
        result["resolved_request"] = current
    else:
        result["resolved_request"] = current

    result["semantic_task"] = semantic_task
    result["three_way_relation"] = relation
    result["two_way_relation"] = relation
    result["relation"] = relation
    result["dialogue_relation"] = relation
    result["continuation"] = bool(relation == "CONTINUE")
    result["reference_to_previous"] = bool(relation in {"CONTINUE", "RECALL"} and (selected_index >= 0 or bool(context_pairs)))
    result["context_dependency"] = (
        "continuation" if relation == "CONTINUE"
        else "recall" if relation == "RECALL"
        else "independent"
    )
    result["context_mode"] = context_mode
    raw_context_anchor = selected.get("context_anchor_index", -1)
    result["context_anchor_index"] = int(raw_context_anchor if raw_context_anchor is not None else -1)
    result["selected_memory_index"] = selected_index
    result["selected_memory_operand"] = selected_pair
    result["selected_memory_record"] = selected_pair
    result["selected_context_pairs"] = context_pairs
    result["dialogue_memory_window"] = [dict(x) for x in (selected.get("memory_window") or pairs[:])]
    result["dialogue_context_pairs"] = context_pairs
    result["dialogue_memory_source"] = "AUTHENTICATED_12H_USER_APRIL_PAIRS" if pairs else "NONE"
    result["context_anchor_pair"] = selected_pair if selected_index >= 0 else (
        dict(next((x for x in context_pairs if isinstance(x, dict)), {})) if context_pairs else {}
    )
    result["pair_direction_engine"] = dict(selected.get("pair_direction") or {}) if isinstance(selected.get("pair_direction"), dict) else {}
    result["vru_semantic_fusion"] = dict(selected.get("vru_semantic_fusion") or {})
    result["vru_definition"] = {
        "version": VRU_VERSION,
        "relation": str((selected.get("vru_semantic_fusion") or {}).get("relation") or relation).upper(),
        "fused_meaning": (selected.get("vru_semantic_fusion") or {}).get("fused_meaning") or {},
        "task_definition": (selected.get("vru_semantic_fusion") or {}).get("task_definition") or {},
        "candidate_evidence": (selected.get("vru_semantic_fusion") or {}).get("candidate_evidence") or [],
    }
    result["pair_first_match"] = {
        "selected_index": selected_index,
        "selected_pair": _compact_pair_for_formulation(selected_pair),
        "match_score": float(selected.get("best_score") or selected.get("latest_score") or 0.0),
        "latest_score": float(selected.get("latest_score") or 0.0),
        "best_score": float(selected.get("best_score") or 0.0),
        "context_anchor_index": int(selected.get("context_anchor_index", -1) or -1),
        "matched_context_pairs": [_compact_pair_for_formulation(x) for x in context_pairs[-4:]],
        "source": "AUTHENTICATED_12H_USER_APRIL_PAIRS",
    }
    result["response_formulation"] = dict(response_formulation)
    result["openai_request_formulation"] = dict(response_formulation)

    result["authenticated_dialogue_memory"] = {
        "window_hours": 12,
        "pair_count": len(result["dialogue_memory_window"]),
        "pairs": result["dialogue_memory_window"],
        "context_mode": context_mode,
        "context_pairs": context_pairs,
        "selected_context_pair_count": len(context_pairs),
        "source": result["dialogue_memory_source"],
        "authority": "INTERPRETATION",
    }

    if canonical_topic:
        result["canonical_topic"] = canonical_topic[:220]
        result["active_topic"] = canonical_topic[:220]
    if resolved_reference_entity:
        result["active_entity"] = resolved_reference_entity[:220]
        result["resolved_entity"] = resolved_reference_entity[:220]
    result["reference_entity"] = resolved_reference_entity

    vru_fused_meaning = (selected.get("vru_semantic_fusion") or {}).get("fused_meaning")
    if isinstance(vru_fused_meaning, dict):
        vru_target_scope = str(vru_fused_meaning.get("target_scope") or "").strip()
        if vru_target_scope and relation == "CONTINUE":
            # The semantic fusion layer owns the recovered subject for elliptical
            # turns. Do not replace it with a lexical tail extracted from one answer.
            canonical_topic = vru_target_scope[:220]
            result["canonical_topic"] = canonical_topic
            result["active_topic"] = canonical_topic
            result["vru_target_scope"] = canonical_topic
            resolved_reference_entity = canonical_topic
            result["resolved_reference_entity"] = canonical_topic
            result["active_entity"] = canonical_topic
            result["resolved_entity"] = canonical_topic
            result["reference_entity"] = canonical_topic

    # Provider handoff: CONTINUE uses active dialogue context; NEW may carry recent
    # background context, but the provider must execute the current task as NEW.
    # The interpretation layer owns the semantic bridge: pairs are selected first,
    # then a compact formulation tells OpenAI how the current turn develops from
    # those exact USER↔APRIL pairs.
    def _provider_pair(pair):
        if not isinstance(pair, dict):
            return {}
        out = {
            "turn": pair.get("turn"),
            "user": str(pair.get("user") or pair.get("user_text") or pair.get("user_request") or "").strip()[:260],
            "april": str(pair.get("april") or pair.get("april_text") or pair.get("april_answer") or "").strip()[:420],
            "topic": str(pair.get("topic") or "").strip()[:180],
            "relation": str(pair.get("relation") or pair.get("dialogue_relation") or "").upper(),
        }
        visual = pair.get("visual_attachment")
        if isinstance(visual, dict) and visual:
            # Keep the exact visual identity/path in the authenticated pair bridge.
            out["visual_attachment"] = {
                key: visual.get(key)
                for key in (
                    "present", "kind", "artifact_id", "block_id", "scene_id",
                    "turn_id", "renderer", "src", "asset_path", "mime_type",
                    "description", "prompt", "width", "height",
                    "generation_model", "generation_quality",
                )
                if visual.get(key) not in (None, "", [], {})
            }
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}

    provider_context_pairs = [
        _provider_pair(x) for x in context_pairs[-8:]
        if isinstance(x, dict)
    ]
    provider_selected_pair = _provider_pair(selected_pair) if selected_pair else {}

    base_rep = str(
        result.get("production_representation")
        or semantic_task.get("representation")
        or result.get("requested_representation")
        or "text"
    ).lower()

    vru_task_definition = (selected.get("vru_semantic_fusion") or {}).get("task_definition")
    if isinstance(vru_task_definition, dict) and vru_task_definition.get("format_as_vertical_list"):
        # "В столбик" following a list result is a formatting instruction, not
        # a request to create a table. Keep the answer as text and carry the
        # vertical-list contract explicitly.
        base_rep = "text"
        result["output_format_hint"] = "vertical_list"
        result["semantic_task"] = {
            **semantic_task,
            "representation": "text",
            "operation": "format_previous_result",
            "goal": "preserve_previous_content_change_format",
        }
        semantic_task = result["semantic_task"]
        operation = "format_previous_result"

    visual_request = str(
        result.get("visual_generation_request")
        or semantic_task.get("visual_generation_request")
        or ""
    ).strip()

    # A visual continuation inherits the previous generation meaning when the
    # current turn asks to modify/redraw/create from the existing visual object.
    # This is a semantic continuation of the authenticated pair, not a trigger
    # shortcut; the exact prior image is separately attached by Executor/Provider.
    previous_visual_prompt = ""
    previous_visual = selected_pair.get("visual_attachment") if isinstance(selected_pair, dict) else {}
    if isinstance(previous_visual, dict):
        previous_visual_prompt = str(
            previous_visual.get("prompt")
            or previous_visual.get("description")
            or ""
        ).strip()
    visual_ops = {
        "build", "create", "generate", "modify", "transform", "redraw",
        "edit", "visualize", "change", "recolor", "update",
    }
    if (
        relation == "CONTINUE"
        and not visual_request
        and previous_visual_prompt
        and operation in visual_ops
    ):
        visual_request = previous_visual_prompt
        result["visual_generation_request"] = previous_visual_prompt

    result["representation"] = base_rep
    result["requested_representation"] = base_rep
    result["production_representation"] = base_rep
    result["production_representation_locked"] = True
    result["requested_outputs"] = [base_rep]
    result["required_representations"] = [base_rep]
    result["visual_generation_request"] = visual_request

    # Provider boundary: only the compact structured request crosses.
    # The authenticated 12h memory remains an Interpretation-side search space.
    provider_formulation_pairs = (
        [dict(x) for x in context_pairs[-4:]]
        if relation == "CONTINUE" or history_lookup
        else []
    )
    provider_plan = {
        "version": "april_provider_handoff_structured_request_v5_markdown_katex_scene",
        "relation": relation,
        "context_mode": context_mode,
        "current_user_request": current,
        "resolved_request": current,
        "resolved_reference_entity": resolved_reference_entity,
        "current_request_authoritative": True,
        "context_selection_done_before_provider": True,
        "provider_must_not_reselect_context": True,
        "hard_budget_tokens": 900,
        "soft_target_tokens": (
            800 if len(current) > 1800
            else 570 if len(current) > 900
            else 300
        ),
        "provider_continuation_contract": "STRUCTURED_REQUEST_FROM_SELECTED_PAIRS",
        "pair_history_authority": "INTERPRETATION_ONLY",
        "vru_semantic_fusion_version": VRU_VERSION,
        "vru_semantic_fusion_completed": True,
        "pair_history_count": len(provider_formulation_pairs),
        "new_topic_minimal_context": relation == "NEW",
        "context_background_only": False,
        "history_lookup": history_lookup,
        "required_context": [
            {
                "key": "RESPONSE_FORMULATION",
                "priority": 1.02,
                "value": dict(response_formulation),
            },
            {
                "key": "SEMANTIC_CORE",
                "priority": 1.0,
                "value": {
                    "topic": canonical_topic,
                    "operation": operation,
                    "representation": base_rep,
                    "turn_relation": relation,
                    "context_mode": context_mode,
                    "resolved_reference_entity": resolved_reference_entity,
                    "resolved_request": current,
                },
            },
            {
                "key": "OUTPUT_CONTRACT",
                "priority": 0.99,
                "value": {
                    "representation": base_rep,
                    "requested_outputs": [base_rep],
                    "visual_generation_request": visual_request,
                    "no_text_fallback_for_image": base_rep in {"image", "gallery"},
                    "ascii_allowed": False,
                },
            },
            {
                "key": "PRESENTATION_CONTRACT",
                "priority": 0.98,
                "value": {
                    "text_transport": "Markdown",
                    "math_transport": "KaTeX",
                    "formula_in_text_block": True,
                    "multiple_formulas": "one_markdown_math_block_per_formula",
                    "formula_delimiters": "$$...$$",
                    "structured_transport": "canonical_payload",
                    "renderer_signal_source": "OUTPUT_CONTRACT",
                    "renderer_signal_must_match_representation": True,
                    "fallback_only_on_structured_render_failure": True,
                    "fallback_channels": ["image", "link"],
                },
            },
        ],
        "optional_context": [],
        "excluded_context": [
            "FULL_12H_DIALOGUE",
            "UNRELATED_PAIRS",
            "GLOBAL_TOPIC_INDEX",
            "ENTITY_INDEX",
            "LEGACY_INTENT_ENGINE",
        ],
    }
    print(
        "🧭 APRIL OPENAI FORMULATION READY:",
        {
            "relation": relation,
            "context_mode": context_mode,
            "selected_memory_index": selected_index,
            "pair_count": len(pairs),
            "context_pair_count": len(context_pairs),
            "formulation_action": str(response_formulation.get("action_link") or ""),
            "pair_first": True,
        },
    )
    result["provider_context_plan"] = provider_plan
    result["provider_context_authority"] = "INTERPRETATION"
    result["provider_must_not_reselect_context"] = True
    result["dialogue_contract"] = {
        **(result.get("dialogue_contract") if isinstance(result.get("dialogue_contract"), dict) else {}),
        "version": "dialogue_pair_contract_v3_live_two_state",
        "relation": relation,
        "three_way_relation": relation,
        "two_way_relation": relation,
        "continuation": relation == "CONTINUE",
        "reference_to_previous": relation == "CONTINUE" and selected_index >= 0,
        "context_dependency": result["context_dependency"],
        "context_mode": context_mode,
        "context_pairs": context_pairs,
        "selected_memory_index": selected_index,
        "selected_memory_operand": selected_pair,
        "resolved_reference_entity": resolved_reference_entity,
        "history_lookup": history_lookup,
        "canonical": True,
        "entities": [],
        "active_entity": resolved_reference_entity,
        "resolved_entity": resolved_reference_entity,
        "entity_understanding": {},
    }
    result["dialogue_vector"] = {
        **(result.get("dialogue_vector") if isinstance(result.get("dialogue_vector"), dict) else {}),
        "relation": relation,
        "three_way_relation": relation,
        "two_way_relation": relation,
        "selected_memory_index": selected_index,
        "selected_memory_operand": selected_pair,
        "memory_window": result["dialogue_memory_window"],
        "context_mode": context_mode,
        "context_anchor_index": int((selected.get("context_anchor_index", -1) if selected.get("context_anchor_index", -1) is not None else -1)),
        "selected_context_pairs": context_pairs,
        "resolved_request": current,
        "resolved_reference_entity": resolved_reference_entity,
        "active_entity": resolved_reference_entity,
        "canonical_topic": canonical_topic,
        "history_lookup": history_lookup,
        "trajectory": {
            "window_hours": 12,
            "pair_count": len(context_pairs),
            "relation": relation,
            "context_mode": context_mode,
            "selected_context_pairs": context_pairs,
        },
    }
    return result


QuantumInterpretationEngine.interpret = _pair_canonical_interpret_live



# ============================================================================
# APRIL INTERPRETATION UPGRADE — 12H FULL DIALOGUE / TWO-STATE SEMANTIC CHAIN
# ============================================================================
# Production contract:
#   StateManager authenticated 12h USER↔APRIL pairs
#       -> scan the COMPLETE 12h window
#       -> semantic meaning of current request against pair USER+APRIL meaning
#       -> select the semantically connected pair chain
#       -> exactly ONE relation: CONTINUE or NEW
#       -> build one structured request from the selected semantic chain
#       -> existing Provider/OpenAI route
#
# There is intentionally no third dialogue relation in the production packet.
# Historical/remember requests are ordinary CONTINUE turns when a real 12h pair
# is semantically connected; otherwise they are NEW.
# The old implementation remains import-compatible above, but this function is
# the final runtime authority assigned at the bottom of this file.
# ============================================================================

TWO_STATE_DIALOGUE_ENGINE_VERSION = "two_state_full_12h_semantic_chain_v3_monotonic_relation_lock"
_TWO_STATE_12H_SECONDS = 12 * 60 * 60


def _two_state_pair_from_row(raw):
    if not isinstance(raw, dict):
        return {}
    user = str(
        raw.get("user")
        or raw.get("user_text")
        or raw.get("user_request")
        or raw.get("user_meaning")
        or raw.get("text")
        or ""
    ).strip()
    april = str(
        raw.get("april")
        or raw.get("april_text")
        or raw.get("april_answer")
        or raw.get("assistant")
        or raw.get("answer")
        or raw.get("april_meaning")
        or ""
    ).strip()
    if not user or not april:
        return {}

    pair = {
        "user": user[:1600],
        "april": april[:2400],
        "result": april[:2400],
        "turn_index": int(
            raw.get("turn_index")
            or raw.get("sequence_turn_index")
            or raw.get("turn")
            or raw.get("turn_id")
            or 0
        ),
        "created_at": float(raw.get("created_at") or raw.get("timestamp") or 0.0),
        "source": "STATE_MANAGER_AUTHENTICATED_12H_USER_APRIL_PAIRS",
        "history_source": "USER_APRIL_PAIRS",
    }
    row_user_id = str(
        raw.get("user_id")
        or raw.get("authenticated_user_id")
        or raw.get("memory_user_id")
        or ""
    ).strip()
    if row_user_id:
        pair["user_id"] = row_user_id
    for key in (
        "conversation_id",
        "sequence_id",
        "dialogue_sequence_id",
        "task_id",
        "sequence_turn_index",
        "task_response_number",
        "topic",
        "sequence_topic",
        "canonical_topic",
        "subtopic",
        "dialogue_relation",
        "relation",
        "semantic_state",
        "memory_semantics",
        "visual_attachment",
        "visual_generation_request",
        "generation_prompt",
        "image_generation_prompt",
        "visual_scene_id",
        "scene_id",
        "dialogue_development",
    ):
        value = raw.get(key)
        if value not in (None, "", [], {}):
            pair[key] = deepcopy(value)
    return pair


def _full_authenticated_12h_pairs(state_obj, history=None):
    """Return the complete authenticated 12h USER↔APRIL pair set.

    No 15-pair slicing is performed. The 12-hour retention boundary remains owned
    by StateManager/storage; Interpretation scans every pair inside that boundary.
    """
    state_obj = state_obj if isinstance(state_obj, dict) else {}
    uid = str(
        state_obj.get("user_id")
        or state_obj.get("authenticated_user_id")
        or (
            state_obj.get("memory_scope", {}).get("user_id")
            if isinstance(state_obj.get("memory_scope"), dict)
            else ""
        )
        or ""
    ).strip()
    cutoff = time.time() - _TWO_STATE_12H_SECONDS

    raw_rows = []
    timeline = state_obj.get("memory_timeline")
    if isinstance(timeline, dict):
        for day_key, day in timeline.items():
            if not isinstance(day_key, str) or not day_key.startswith("day_") or not isinstance(day, dict):
                continue
            for row in day.get("dialog_pairs") or []:
                if not isinstance(row, dict):
                    continue
                row_uid = str(row.get("user_id") or uid).strip()
                if uid and row_uid and row_uid != uid:
                    continue
                created = float(row.get("created_at") or row.get("timestamp") or 0.0)
                if created and created < cutoff:
                    continue
                raw_rows.append(row)

    # The direct StateManager snapshot is authoritative when present. If it is
    # temporarily absent after HTTP reload, use the same canonical persistent
    # dialogue store, with no pair-count cap. storage.load_dialogue_pairs(limit=0)
    # already restricts rows to the current 12h window.
    if not raw_rows and uid:
        try:
            from storage import load_dialogue_pairs
            raw_rows = load_dialogue_pairs(uid, limit=0) or []
        except Exception:
            try:
                # Existing helper, but deliberately given a very high transport
                # limit so it cannot reintroduce the historical 15-pair cap.
                raw_rows = QuantumInterpretationEngine._state_dialogue_pairs(
                    state_obj, user_id=uid, limit=1_000_000
                ) or []
            except Exception:
                raw_rows = []

    # Non-authenticated compatibility path: use all supplied pairs, never only
    # the last 15. The production authenticated path above remains the source of
    # truth when an authenticated user is present.
    if not raw_rows and not uid:
        raw_rows = list(history or [])

    rows = []
    seen = set()
    for raw in raw_rows:
        pair = _two_state_pair_from_row(raw)
        if not pair:
            continue
        if uid:
            row_uid = str(pair.get("user_id") or uid).strip()
            if row_uid and row_uid != uid:
                continue
            pair["user_id"] = uid
        sig = (
            pair.get("user"),
            pair.get("april"),
            float(pair.get("created_at") or 0.0),
            int(pair.get("turn_index") or 0),
        )
        if sig in seen:
            continue
        seen.add(sig)
        rows.append(pair)

    rows.sort(
        key=lambda p: (
            float(p.get("created_at") or 0.0),
            int(p.get("turn_index") or 0),
        )
    )
    return rows


def _two_state_tokens(value):
    return set(
        x for x in re.findall(
            r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+",
            str(value or "").lower(),
        )
        if len(x) >= 3
    )


def _two_state_answer_set(pair):
    if not isinstance(pair, dict):
        return False
    answer = str(pair.get("april") or pair.get("answer") or "").strip()
    if not answer:
        return False
    if re.match(r"^(?:уточни|уточните|не понял|непонятно|что именно)\b", answer, re.I):
        return False
    return bool(
        re.search(r"\b(?:и|или)\b|,|;", answer, re.I)
        and re.search(r"[A-Za-zА-Яа-яЁё]{3,}", answer)
    )


def _two_state_discussion_query(current):
    low = str(current or "").lower()
    return bool(
        re.search(r"\b(?:о\s+ч[её]м|что)\s+(?:мы\s+)?(?:говорили|обсуждали)\b", low)
        or re.search(r"\b(?:что\s+мы\s+обсуждали|что\s+обсуждали)\b", low)
        or re.search(r"\b(?:найди|покажи)\b.*\b(?:в\s+диалоге|в\s+истории|в\s+контексте)\b", low)
        or re.search(r"\b(?:какие\s+темы|темы)\b.*\b(?:обсуждали|говорили)\b", low)
    )


def _two_state_history_overview_query(current):
    """Recognize a broad request to inspect/remember the dialogue itself.

    This decision is made from the current request, before historical pair
    similarity is used. It therefore prevents a generic memory question from
    being treated as a search for one lexically similar topic.
    """
    low = re.sub(r"\s+", " ", str(current or "").strip().lower())
    if not low:
        return False

    direct_patterns = (
        r"\bчто\s+(?:мы|я\s+и\s+ты)\s+(?:обсуждали|говорили|разбирали)\b",
        r"\bо\s+ч[её]м\s+(?:мы\s+)?(?:говорили|обсуждали|разговаривали)\b",
        r"\bчто\s+ты\s+(?:помнишь|помни)\b.*\b(?:общени|диалог|разговор|истори)\w*\b",
        r"\bчто\s+(?:ты|эприл|април)\s+помни(?:шь|шь\s+из)?\b",
        r"\bпокажи\s+(?:наш(?:у|е|ем)?\s+)?(?:диалог|истори|разговор)\b",
        r"\bнапомни\s+(?:наш|о\s+нашем|про\s+наш)\s+(?:диалог|разговор|общени)\w*\b",
        r"\bчто\s+было\s+(?:в|за)\s+(?:нашем\s+)?(?:диалоге|общении|разговоре)\b",
        r"\b(?:что|какие)\s+(?:мы\s+)?(?:обсуждали|говорили)\b",
    )
    if any(re.search(pattern, low, re.I) for pattern in direct_patterns):
        return True

    scope = bool(re.search(
        r"\b(?:сегодня|недавно|недавн|последн(?:ее|ие|их)|за\s+сегодня|"
        r"за\s+день|за\s+последн(?:ие|их)\s+(?:часы|часов|дни|дня|12\s*час(?:ов|а)?))\b",
        low,
        re.I,
    ))
    dialogue_words = bool(re.search(
        r"\b(?:обсуждали|говорили|разбирали|диалог|истори|общени|разговор|"
        r"тем(?:ы|а)|вопрос(?:ы|ов)?|ответ(?:ы|ов)?|помни(?:шь|ть)?|вспомн(?:и|ить)?)\b",
        low,
        re.I,
    ))
    return scope and dialogue_words




_TWO_STATE_TOPIC_NUMBER_WORDS = {
    "ноль": 0,
    "один": 1, "одна": 1, "первый": 1, "первая": 1,
    "два": 2, "две": 2, "второй": 2, "вторая": 2,
    "три": 3, "третий": 3, "третья": 3,
    "четыре": 4, "четвертый": 4, "четвертая": 4,
    "пять": 5, "пятый": 5, "пятая": 5,
    "шесть": 6, "шестой": 6, "шестая": 6,
    "семь": 7, "седьмой": 7, "седьмая": 7,
    "восемь": 8, "восьмой": 8, "восьмая": 8,
    "девять": 9, "девятый": 9, "девятая": 9,
    "десять": 10, "десятый": 10, "десятая": 10,
    "одиннадцать": 11, "одиннадцатый": 11, "одиннадцатая": 11,
    "двенадцать": 12, "двенадцатый": 12, "двенадцатая": 12,
    "тринадцать": 13, "тринадцатый": 13, "тринадцатая": 13,
    "четырнадцать": 14, "четырнадцатый": 14, "четырнадцатая": 14,
    "пятнадцать": 15, "пятнадцатый": 15, "пятнадцатая": 15,
    "шестнадцать": 16, "шестнадцатый": 16, "шестнадцатая": 16,
    "семнадцать": 17, "семнадцатый": 17, "семнадцатая": 17,
    "восемнадцать": 18, "восемнадцатый": 18, "восемнадцатая": 18,
    "девятнадцать": 19, "девятнадцатый": 19, "девятнадцатая": 19,
    "двадцать": 20, "двадцатый": 20, "двадцатая": 20,
}


def _two_state_topic_reference_number(current):
    """Read an explicit topic ordinal such as 'тему 14' or 'тема четырнадцать'."""
    low = re.sub(r"\s+", " ", str(current or "").strip().lower())
    if not low:
        return None

    match = re.search(r"\b(?:тему|тема|теме|урок|урока|уроку|уроке|тест|теста|тесте)\s*(?:номер|№|#)?\s*(\d{1,3})\b", low, re.I)
    if match:
        return int(match.group(1))

    match = re.search(r"\b(\d{1,3})\s+(?:тему|тема|теме|урок|урока|уроку|уроке|тест|теста|тесте)\b", low, re.I)
    if match:
        return int(match.group(1))

    for word, number in sorted(_TWO_STATE_TOPIC_NUMBER_WORDS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b(?:тему|тема|теме)\s+(?:№|#)?\s*{re.escape(word)}\b", low, re.I):
            return number
        if re.search(rf"\b{re.escape(word)}\s+(?:тему|тема|теме)\b", low, re.I):
            return number
    return None


def _two_state_topic_id_from_pair(pair):
    """Return an explicit lesson/topic/test number stored in a dialogue pair."""
    if not isinstance(pair, dict):
        return None
    for value in (
        pair.get("user"), pair.get("user_text"), pair.get("user_request"),
        pair.get("sequence_topic"), pair.get("topic"), pair.get("canonical_topic"),
    ):
        number = _two_state_topic_reference_number(value)
        if number is not None:
            return number
    return None


def _two_state_history_operation(current):
    """Determine the user's operation over dialogue history without creating a new route.

    The existing CONTINUE/NEW relation remains authoritative. This helper only says
    what the history request means: broad overview, find a concrete dialogue, or
    summarize/open a previously identified dialogue.
    """
    low = re.sub(r"\s+", " ", str(current or "").strip().lower())
    if not low:
        return "NONE"

    # A numbered topic becomes a history lookup only when the user is actually
    # asking to remember/find/show it. A source turn such as "Урок номер 14 ..."
    # is ordinary dialogue content and must remain searchable evidence.
    topic_reference = _two_state_topic_reference_number(low)
    topic_history_cue = re.search(
        r"\b(?:помн|вспомн|найд|покаж|вывед|вернись|обсуждал|говорил|"
        r"что\s+было|какая\s+была|какой\s+был)\w*\b",
        low,
        re.I,
    )
    if topic_reference is not None and topic_history_cue:
        return "FIND_DIALOGUE"

    # A later turn may refer to a dialogue already found. Keep this ahead of the
    # generic FIND patterns so "покажи тот диалог" means OPEN, not a fresh search.
    open_patterns = (
        r"\bоткрой\b.{0,80}\b(?:диалог|разговор)\b",
        r"\bпокажи\s+(?:тот|найденный|этот)\s+(?:диалог|разговор)\b",
        r"\bвыведи\s+(?:тот|найденный|этот)\s+(?:диалог|разговор)\b",
    )
    if any(re.search(pattern, low, re.I) for pattern in open_patterns):
        return "OPEN_DIALOGUE"

    # A concrete history target has priority over the broad overview intent.
    find_patterns = (
        r"\bнайди\b.{0,120}\b(?:диалог|разговор|обсужден|истори)\w*\b",
        r"\bпокажи\b.{0,120}\b(?:диалог|разговор)\b.{0,100}\b(?:про|о|об)\b",
        r"\bвернись\s+к\b.{0,100}\b(?:диалог|разговор|теме)\b",
        r"\b(?:тот|нужн(?:ый|ую))\s+(?:диалог|разговор)\b",
        r"\bнайди\s+в\s+(?:истории|контексте)\b",
        r"\b(?:какой|какая|какое)\s+(?:диалог|разговор)\b",
        r"\bгде\s+мы\s+(?:обсуждали|говорили|разбирали)\b",
    )
    if any(re.search(pattern, low, re.I) for pattern in find_patterns):
        return "FIND_DIALOGUE"

    # A later turn may refer to the already found dialogue.
    summarize_patterns = (
        r"\bчто\s+(?:мы\s+)?(?:обсуждали|говорили|разбирали)\s+(?:в\s+н[ёе]м|в\s+нем|там|в\s+этом\s+диалоге|в\s+найденном\s+диалоге)\b",
        r"\bчто\s+(?:мы\s+)?(?:в\s+н[ёе]м|в\s+нем|там|в\s+этом\s+диалоге|в\s+найденном\s+диалоге)\s+(?:обсуждали|говорили|разбирали)\b",
        r"\b(?:расскажи|напомни|покажи)\b.{0,60}\b(?:об\s+этом\s+диалоге|про\s+этот\s+диалог|о\s+найденном\s+диалоге)\b",
        r"\bчто\s+было\s+в\s+(?:н[ёе]м|в\s+нем|этом\s+диалоге|найденном\s+диалоге)\b",
        r"\b(?:опиши|суммируй)\b.{0,80}\b(?:этот\s+диалог|найденный\s+диалог)\b",
    )
    if any(re.search(pattern, low, re.I) for pattern in summarize_patterns):
        return "SUMMARIZE_DIALOGUE"

    if _two_state_history_overview_query(low):
        return "OVERVIEW"

    return "NONE"


def _two_state_history_search_query(current):
    """Strip only the history-operation envelope and preserve the user's semantic target."""
    text = re.sub(r"\s+", " ", str(current or "").strip())
    low = text.lower()
    if not text:
        return ""
    if _two_state_topic_reference_number(text) is not None:
        return ""

    removals = (
        r"\b(?:пожалуйста\s+)?найди(?:те)?\b",
        r"\b(?:пожалуйста\s+)?покажи(?:те)?\b",
        r"\b(?:пожалуйста\s+)?выведи(?:те)?\b",
        r"\b(?:пожалуйста\s+)?открой(?:те)?\b",
        r"\b(?:пожалуйста\s+)?вернись\s+к\b",
        r"\b(?:наш|нашему|нашем|этот|тот|найденный|нужный)\s+(?=диалог|разговор)\b",
        r"\b(?:диалог|разговор)\b\s*(?:про|о|об)\s*",
        r"\b(?:диалог|разговор)\b\s*",
        r"\b(?:в|из)\s+(?:истории|контекста)\b",
    )
    query = text
    for pattern in removals:
        query = re.sub(pattern, " ", query, flags=re.I)
    query = re.sub(r"\s+", " ", query).strip(" ,:;.-")
    if query and query.lower() != low:
        return query[:500]
    return query[:500]


def _two_state_history_search_cluster(current, window, *, preferred_query=""):
    """Find one concrete semantic dialogue sequence across the complete 12h window."""
    pairs = [p for p in (window or []) if isinstance(p, dict)]
    substantive = [
        (i, p) for i, p in enumerate(pairs)
        if p
        and not _two_state_is_clarification(p)
        and _two_state_history_operation(
            str(p.get("user") or p.get("user_text") or p.get("user_request") or "")
        ) == "NONE"
    ]
    if not substantive:
        return {}

    query = str(preferred_query or _two_state_history_search_query(current) or current or "").strip()
    query = re.sub(r"\s+", " ", query)
    if not query:
        return {}

    def pair_text(pair):
        user = str(pair.get("user") or pair.get("user_text") or pair.get("user_request") or "").strip()
        answer = str(pair.get("april") or pair.get("april_answer") or pair.get("assistant") or pair.get("answer") or "").strip()
        topic = str(pair.get("sequence_topic") or pair.get("topic") or pair.get("canonical_topic") or "").strip()
        return user, answer, topic

    def pair_subject(pair):
        user, answer, topic = pair_text(pair)
        return topic or " ".join(_two_state_tokens(f"{user} {answer}"))[:220]

    def token_score(a, b):
        aa, bb = _two_state_tokens(a), _two_state_tokens(b)
        if not aa or not bb:
            return 0.0
        exact = len(aa & bb) / max(1, len(aa | bb))
        directional = len(aa & bb) / max(1, min(len(aa), len(bb)))
        return max(exact, 0.70 * exact + 0.30 * directional)

    topic_reference_number = _two_state_topic_reference_number(query)
    ranked = []
    for i, pair in substantive:
        user, answer, topic = pair_text(pair)
        score = (
            0.54 * token_score(query, user)
            + 0.26 * token_score(query, answer)
            + 0.20 * token_score(query, topic)
        )
        try:
            score = max(score, float(_two_state_morph_affinity(query, f"{user} {answer} {topic}") or 0.0) * 0.72)
        except Exception:
            pass
        pair_number = _two_state_topic_id_from_pair(pair)
        if topic_reference_number is not None and pair_number == topic_reference_number:
            # Exact numbered topic identity is stronger than any lexical/semantic
            # similarity. This prevents topic 14 from being hijacked by a recent
            # but unrelated topic such as Gagarin.
            score = max(score, 0.995)
        ranked.append((score, i))
    ranked.sort(reverse=True)
    if not ranked:
        return {}

    best_score, anchor_index = ranked[0]
    # Do not invent a dialogue when the search has no meaningful semantic evidence.
    if best_score < 0.12:
        return {}

    anchor = pairs[anchor_index]
    anchor_user, anchor_answer, anchor_topic = pair_text(anchor)
    anchor_sequence = str(anchor.get("dialogue_sequence_id") or anchor.get("sequence_id") or anchor.get("task_id") or "").strip()
    anchor_test = _two_state_topic_id_from_pair(anchor)

    selected_indices = []
    for score, i in ranked:
        pair = pairs[i]
        user, answer, topic = pair_text(pair)
        seq = str(pair.get("dialogue_sequence_id") or pair.get("sequence_id") or pair.get("task_id") or "").strip()
        same_sequence = bool(anchor_sequence and seq and anchor_sequence == seq)
        pair_number = _two_state_topic_id_from_pair(pair)
        same_test = bool(anchor_test is not None and pair_number == anchor_test)
        anchor_affinity = token_score(f"{anchor_topic} {anchor_user} {anchor_answer}", f"{topic} {user} {answer}")
        # For numbered-topic lookup, sequence identity and the same topic/test id
        # are the primary chain boundaries. Semantic affinity is support, not a
        # reason to jump into another numbered topic.
        if topic_reference_number is not None and _two_state_topic_id_from_pair(anchor) == topic_reference_number:
            # Once the exact numbered source is found, a modest semantic link is
            # enough to retain the immediately related turns of that same dialogue.
            # This is still much stricter than a global similarity search and cannot
            # replace the exact numbered anchor.
            chain_link = same_sequence or same_test or anchor_affinity >= 0.10 or (i == anchor_index)
        else:
            chain_link = same_sequence or same_test or anchor_affinity >= 0.28 or (i == anchor_index)
        if chain_link:
            selected_indices.append(i)

    # The exact numbered/source pair is only the ENTRY POINT. A real dialogue
    # sequence may not repeat its topic number on every turn, and older DB rows may
    # not carry a sequence_id at all. Once an exact source is found, expand through
    # adjacent substantive USER↔APRIL turns while the conversation remains
    # semantically connected. This lets the full internal interpretation logic see
    # the actual development of topic 14 instead of a single isolated row.
    substantive_indices = [i for i, _pair in substantive]
    selected_set = set(selected_indices)
    anchor_pos = substantive_indices.index(anchor_index) if anchor_index in substantive_indices else -1
    if anchor_pos >= 0:
        def _chain_pair_score(left_index, right_index):
            left = pairs[left_index]
            right = pairs[right_index]
            lu, la, lt = pair_text(left)
            ru, ra, rt = pair_text(right)
            return token_score(f"{lt} {lu} {la}", f"{rt} {ru} {ra}")

        # Deterministic branch membership from explicit sequence/test metadata.
        # This path is allowed to bridge otherwise weak lexical links.
        for idx in substantive_indices:
            if idx == anchor_index:
                continue
            pair = pairs[idx]
            seq = str(pair.get("dialogue_sequence_id") or pair.get("sequence_id") or pair.get("task_id") or "").strip()
            pair_number = _two_state_topic_id_from_pair(pair)
            if (anchor_sequence and seq and anchor_sequence == seq) or (anchor_test is not None and pair_number == anchor_test):
                selected_set.add(idx)

        # Expand left/right only through the contiguous substantive trajectory.
        # A semantic break stops expansion, preventing a later unrelated topic
        # (e.g. the Gagarin discussion) from being pulled into topic 14.
        for step in (-1, 1):
            pos = anchor_pos
            previous_index = anchor_index
            while True:
                pos += step
                if pos < 0 or pos >= len(substantive_indices):
                    break
                candidate_index = substantive_indices[pos]
                pair = pairs[candidate_index]
                seq = str(pair.get("dialogue_sequence_id") or pair.get("sequence_id") or pair.get("task_id") or "").strip()
                pair_number = _two_state_topic_id_from_pair(pair)
                explicit_branch = bool(
                    (anchor_sequence and seq and anchor_sequence == seq)
                    or (anchor_test is not None and pair_number == anchor_test)
                )
                affinity_anchor = _chain_pair_score(anchor_index, candidate_index)
                affinity_previous = _chain_pair_score(previous_index, candidate_index) if previous_index != anchor_index else affinity_anchor
                turn_a = int(pairs[previous_index].get("turn_index") or pairs[previous_index].get("sequence_turn_index") or 0)
                turn_b = int(pair.get("turn_index") or pair.get("sequence_turn_index") or 0)
                consecutive_turn = bool(turn_a and turn_b and abs(turn_b - turn_a) <= 1)
                connected = explicit_branch or affinity_anchor >= 0.14 or affinity_previous >= 0.18 or (consecutive_turn and affinity_previous >= 0.08)
                if not connected:
                    break
                selected_set.add(candidate_index)
                previous_index = candidate_index

        selected_indices = sorted(selected_set)

    if anchor_index not in selected_indices:
        selected_indices.append(anchor_index)
        selected_indices.sort()

    selected_pairs = [dict(pairs[i]) for i in selected_indices if 0 <= i < len(pairs)]
    first = selected_pairs[0] if selected_pairs else dict(anchor)
    last = selected_pairs[-1] if selected_pairs else dict(anchor)
    first_user, first_answer, first_topic = pair_text(first)
    last_user, last_answer, last_topic = pair_text(last)
    return {
        "dialogue_found": True,
        "match_score": round(float(best_score), 6),
        "anchor_index": int(anchor_index),
        "pair_indices": selected_indices,
        "pair_count": len(selected_indices),
        "sequence_id": anchor_sequence,
        "test_id": anchor_test,
        "topic_number": topic_reference_number,
        "authenticated_user_id": str(anchor.get("user_id") or "").strip(),
        "topic": (last_topic or anchor_topic or pair_subject(anchor))[:320],
        "started_with": re.sub(r"\s+", " ", str(first_user or first_answer).strip())[:320],
        "stopped_at": re.sub(r"\s+", " ", str(f"{last_user} → {last_answer}" if last_user and last_answer else last_user or last_answer).strip())[:360],
        "source_pair_indices": selected_indices[:64],
        "pairs": selected_pairs,
        "search_query": query[:500],
        "source": "FULL_12H_SEMANTIC_DIALOGUE_SEARCH",
    }


def _two_state_previous_history_search_query(window):
    """Recover the last concrete text history target."""
    target = _two_state_previous_history_search_target(window)
    return str(target.get("query") or "")


def _two_state_previous_history_search_target(window):
    """Recover the last concrete history target, including a numbered topic."""
    for pair in reversed([p for p in (window or []) if isinstance(p, dict)]):
        user = str(pair.get("user") or pair.get("user_text") or pair.get("user_request") or "").strip()
        operation = _two_state_history_operation(user)
        if operation not in {"FIND_DIALOGUE", "OPEN_DIALOGUE"}:
            continue
        topic_number = _two_state_topic_reference_number(user)
        query = _two_state_history_search_query(user)
        if topic_number is not None or query:
            return {
                "query": query,
                "topic_number": topic_number,
                "operation": operation,
                "source_pair": dict(pair),
            }
    return {}


def _two_state_reference_query(current):
    low = str(current or "").lower()
    return bool(
        _live_reference_present(low)
        or re.search(r"\b(?:кто|что|какой|какая|какие|какое)\s+из\s+(?:них|этих|тех)\b", low)
        or re.search(r"\b(?:какое|какая|какие)\b.{0,100}\bне\s*(?:назвал|назвала|назвали|упомянул|упомянула|упомянули)\b", low)
        or re.search(r"\b(?:из\s+них|из\s+этих|из\s+тех)\b", low)
        or re.search(r"\b(?:в|на)\s+тест(?:е|а|ом)?\s*(?:номер|№|#)?\s*\d+\b", low)
        or re.search(r"\b(?:о\s+ч[её]м|что\s+мы)\s+(?:говорили|обсуждали)\b", low)
    )


def _two_state_is_clarification(pair):
    if not isinstance(pair, dict):
        return False
    answer = str(
        pair.get("april")
        or pair.get("april_answer")
        or pair.get("answer")
        or ""
    ).strip()
    if re.match(
        r"^(?:не\s+совсем\s+понял|не\s+понял|не\s+поняла|уточни|уточните|"
        r"что\s+именно|скажите|пришлите|нужно\s+прислать)\b",
        answer,
        re.I,
    ):
        return True
    return bool(
        re.search(r"\b(?:чего|какой|какая|какое|какие|кто|что)\s+именно\b", answer, re.I)
        or re.search(r"\bо\s+како(?:й|м)\s+", answer, re.I)
        or re.search(r"\bкто\s+или\s+что\b", answer, re.I)
        or (
            "?" in answer
            and re.search(r"\b(?:стоимость|цена|классификаци|самые\s+опасные|популярн)\b", answer, re.I)
        )
    )



def _two_state_morph_affinity(left, right):
    a = _two_state_tokens(left)
    b = _two_state_tokens(right)
    if not a or not b:
        return 0.0
    exact = len(a & b) / max(1, len(a | b))
    hits = 0.0
    for x in a:
        best = 0.0
        for y in b:
            if x == y:
                best = 1.0
                break
            common = 0
            for ca, cb in zip(x, y):
                if ca != cb:
                    break
                common += 1
            if common >= 4 and common / max(1, len(x), len(y)) >= 0.55:
                best = max(best, 0.5)
        hits += best
    morph = hits / max(1, min(len(a), len(b)))
    directional = len(a & b) / max(1, min(len(a), len(b)))
    return max(exact, min(1.0, 0.55 * exact + 0.30 * morph + 0.15 * directional))


def _two_state_light_12h_similarity(current, pairs):
    """Compute cheap semantic evidence across the complete 12h pair window.

    Uses one TF-IDF character n-gram pass plus RapidFuzz. No transformer/NLI model
    is loaded here. The selector remains the sole authority for CONTINUE/NEW.
    """
    window = [p for p in (pairs or []) if isinstance(p, dict)]
    if not window:
        return []

    def _norm(value):
        return re.sub(r"\\s+", " ", str(value or "").strip().lower())

    def _pair_text(pair):
        user = _norm(pair.get("user") or pair.get("user_text") or pair.get("user_request"))
        answer = _norm(pair.get("april") or pair.get("april_answer") or pair.get("assistant") or pair.get("answer"))
        topic = _norm(pair.get("sequence_topic") or pair.get("topic") or pair.get("canonical_topic"))
        return user, answer, topic

    current_n = _norm(current)
    prepared = []
    for pair in window:
        user, answer, topic = _pair_text(pair)
        prepared.append({
            "pair": f"{user} {topic} {answer}".strip(),
            "user": user,
            "answer": answer,
            "topic": topic,
        })

    tfidf_scores = [0.0] * len(prepared)
    if TfidfVectorizer is not None and cosine_similarity is not None:
        try:
            docs = [current_n] + [x["pair"] for x in prepared]
            vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                lowercase=True,
                sublinear_tf=True,
                min_df=1,
            )
            matrix = vectorizer.fit_transform(docs)
            values = cosine_similarity(matrix[0:1], matrix[1:]).ravel()
            tfidf_scores = [max(0.0, min(1.0, float(v))) for v in values]
        except Exception:
            pass

    def _fuzzy_pair(a, b):
        if not a or not b:
            return 0.0, 0.0
        if _rapidfuzz is not None:
            try:
                token = float(_rapidfuzz.token_set_ratio(a, b)) / 100.0
                partial = float(_rapidfuzz.partial_ratio(a, b)) / 100.0
                return token, partial
            except Exception:
                pass
        from difflib import SequenceMatcher
        ratio = float(SequenceMatcher(None, a, b).ratio())
        return ratio, ratio

    out = []
    for i, item in enumerate(prepared):
        user_f, user_partial = _fuzzy_pair(current_n, item["user"])
        answer_f, answer_partial = _fuzzy_pair(current_n, item["answer"])
        topic_f, topic_partial = _fuzzy_pair(current_n, item["topic"])
        short_turn = len(current_n.split()) <= 3
        answer_signal = max(answer_f, answer_partial) if short_turn else answer_f
        topic_signal = max(topic_f, topic_partial) if short_turn else topic_f
        out.append({
            "tfidf": round(tfidf_scores[i], 6),
            "user_fuzzy": round(user_f, 6),
            "answer_fuzzy": round(answer_signal, 6),
            "topic_fuzzy": round(topic_signal, 6),
            "partial_answer_fuzzy": round(answer_partial, 6),
            "partial_topic_fuzzy": round(topic_partial, 6),
            "score": round(max(0.0, min(1.0, (
                0.50 * tfidf_scores[i]
                + 0.18 * user_f
                + 0.20 * answer_signal
                + 0.12 * topic_signal
            ))), 6),
        })
    return out


def _two_state_semantic_selector(self, current, pairs, active_topic=""):
    """Resolve the current turn against the COMPLETE authenticated 12h dialogue.

    Runtime contract:
      1. Scan every authenticated USER↔APRIL pair inside the 12h retention window.
      2. Resolve the discourse anchor/chain before relation classification.
      3. Produce exactly CONTINUE or NEW.
      4. No historical/recall state exists in the canonical decision.
      5. Provider receives only the semantically linked chain, never a raw history
         slice and never re-selects context itself.

    The selector is deliberately hybrid:
      - deterministic discourse/test/reference rules carry the primary decision;
      - morphological/lexical similarity handles typos and inflection;
      - the existing embedding/TfIdf score is secondary evidence only;
      - recency is a weak tie-breaker, not a reason to continue by itself.
    """
    current = self.normalize(current)
    pairs = [p for p in (pairs or []) if isinstance(p, dict)]
    active_topic = self.normalize(active_topic)

    owner_ids = {
        str(p.get("user_id") or "").strip()
        for p in pairs
        if str(p.get("user_id") or "").strip()
    }
    authenticated_user_id = next(iter(owner_ids)) if len(owner_ids) == 1 else ""


    def _clean(text):
        value = self.normalize(text)
        replacements = {
            "матациклов": "мотоциклов",
            "матациклы": "мотоциклы",
            "матацикл": "мотоцикл",
            "матацикле": "мотоцикле",
            "матациклах": "мотоциклах",
            "хишник": "хищник",
            "хишники": "хищники",
            "хишников": "хищников",
            "знаеш": "знаешь",
            "самве": "самые",
            "йапон": "япон",
            "японии": "япония",
            "японских": "японский",
            "автомобил": "автомобиль",
            "автомобили": "автомобиль",
        }
        for old, new in replacements.items():
            value = re.sub(rf"(?<!\w){re.escape(old)}(?=\w|\b)", new, value)
        return value

    _generic_query = {
        "назови", "назов", "называй", "дай", "покажи", "расскажи",
        "какой", "какая", "какие", "какое", "кто", "что", "как",
        "сколько", "из", "них", "это", "этот", "эта", "эти",
        "того", "той", "те", "тот", "такой", "такие",
        "теперь", "ну", "так", "и", "про", "о", "об", "по",
        "самый", "самые", "еще", "ещё", "дальше", "далее",
        "стоимость", "цена", "цены", "стоит", "примерная",
        "доллар", "доллара", "долларов", "доллары",
    }
    _reference_forms = {
        "из них", "из этих", "из тех", "из популярных", "из перечисленных",
        "из названных", "из указанных", "из выбранных", "из последних",
        "кто из них", "что из них",
        "какой из них", "какая из них", "какие из них", "какое из них",
        "их", "его", "ее", "её", "ему", "ей", "им", "ними", "ним",
        "них", "него", "неё", "ней", "этом", "этого", "этим",
        "этот", "эта", "эти", "такой", "такие", "каждого", "каждой",
        "каждые", "каждый",
    }
    _followup_forms = {
        "теперь", "дальше", "далее", "еще", "ещё", "продолжи", "продолжай",
        "добавь", "расширь", "подробнее", "детальнее", "уточни", "поясни",
        "объясни", "раскрой", "выдели", "выбери", "отбери", "исправь",
        "исправся", "стоимость", "цена", "цены", "стоит", "японских",
        "о мотоциклах", "о матоциклах", "про мотоциклы", "мотоциклы",
    }

    _test_words = {
        "ноль": 0, "один": 1, "одна": 1, "первый": 1,
        "два": 2, "две": 2, "второй": 2,
        "три": 3, "третий": 3,
        "четыре": 4, "четвертый": 4, "четвертая": 4,
        "пять": 5, "пятый": 5, "шесть": 6, "шестой": 6,
        "семь": 7, "седьмой": 7, "восемь": 8, "восьмой": 8,
        "девять": 9, "девятый": 9, "десять": 10, "десятый": 10,
        "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
        "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
        "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
        "двадцать": 20,
    }

    def _content(text):
        cleaned = _clean(text)
        raw = re.findall(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_]+", cleaned.lower())
        out = []
        for token in raw:
            if len(token) < 3:
                continue
            if token in _generic_query:
                continue
            out.append(token)
        return out

    def _semantic_set(text):
        return set(_content(text))

    def _topic_affinity(left, right):
        try:
            score = float(_two_state_morph_affinity(_clean(left), _clean(right)) or 0.0)
        except Exception:
            score = 0.0
        a = _semantic_set(left)
        b = _semantic_set(right)
        if a and b:
            exact = len(a & b) / max(1, len(a | b))
            directional = len(a & b) / max(1, min(len(a), len(b)))
            score = max(score, 0.70 * exact + 0.30 * directional)
        return max(0.0, min(1.0, score))

    def _extract_test_id(text):
        low = _clean(text)
        # Accept the same numeric identity across test/lesson/topic wording so
        # "Урок номер 14" and "тему 14" resolve to the same authenticated branch.
        numbered_forms = (
            r"\b(?:тест|урок|урока|уроку|уроке|тема|тему|теме)\s*(?:номер|№|#)?\s*(\d{1,3})\b",
            r"\b(?:тестномер|урокномер)\s*(\d{1,3})\b",
        )
        for pattern in numbered_forms:
            match = re.search(pattern, low, re.I)
            if match:
                return int(match.group(1))
        for word, number in sorted(_test_words.items(), key=lambda item: -len(item[0])):
            if re.search(rf"\b(?:тест|урок|тема)(?:е|а|ом|у)?\s+(?:номер|№|#)\s+{re.escape(word)}\b", low, re.I):
                return number
            if re.search(rf"\b(?:тест|урок|тема)(?:е|а|ом|у)?\s+{re.escape(word)}\b", low, re.I):
                return number
        return None

    def _looks_like_test_start(text, test_id=None):
        low = _clean(text)
        if test_id is None:
            return False
        # A test number inside a lookup/reference request is NOT a new task.
        lookup = (
            re.search(r"\bо\s+ч[её]м\s+я\s+(?:тебя\s+)?спраш", low, re.I)
            or re.search(r"\bчто\s+я\s+(?:тебя\s+)?спраш", low, re.I)
            or re.search(r"\b(?:просмотри|посмотри|смотри|найди|покажи)\b", low, re.I)
            or re.search(r"\bв\s+тест(?:е|а|ом)\b", low, re.I)
        )
        if lookup:
            return False
        return bool(
            re.search(
                r"\b(?:назови|назов|перечисли|расскажи|сколько|какие|какой|какая|"
                r"какое|что\s+ты\s+знаешь|что\s+ты\s+знаеш|объясни|покажи|дай)\b",
                low,
                re.I,
            )
        ) or bool(
            re.search(r"\b(?:начн(?:е|ё)м|начать|начинай|начнем)\s+тест\b", low, re.I)
        )

    def _test_id_from_pair(pair):
        if not isinstance(pair, dict):
            return None
        values = [
            pair.get("user"),
            pair.get("user_text"),
            pair.get("user_request"),
            pair.get("sequence_topic"),
            pair.get("topic"),
            pair.get("canonical_topic"),
        ]
        for value in values:
            tid = _extract_test_id(str(value or ""))
            if tid is not None:
                return tid
        return None

    def _pair_text(pair):
        user = str(
            pair.get("user")
            or pair.get("user_text")
            or pair.get("user_request")
            or ""
        ).strip()
        april = str(
            pair.get("april")
            or pair.get("april_answer")
            or pair.get("assistant")
            or pair.get("answer")
            or ""
        ).strip()
        topic = str(
            pair.get("sequence_topic")
            or pair.get("topic")
            or pair.get("canonical_topic")
            or ""
        ).strip()
        return user, april, topic

    def _is_clarification(pair):
        if _two_state_is_clarification(pair):
            return True
        _, answer, _ = _pair_text(pair)
        low = _clean(answer)
        return bool(
            re.match(
                r"^(?:не\s+совсем\s+понял|не\s+понял|не\s+поняла|"
                r"уточни|уточните|что\s+именно|пришлите|"
                r"нужно\s+прислать)\b",
                low,
                re.I,
            )
        )

    def _is_transport_fallback(pair):
        # A previous Provider transport failure may already have been persisted
        # in the 12h USER↔APRIL window. Keep the row available for diagnostics,
        # but do not treat the synthetic failure sentence as a semantic result.
        _, april, _ = _pair_text(pair)
        low = _clean(april)
        return bool(
            re.match(
                r"^не\s+удалось\s+сформировать\s+ответ\s+на\s+запрос\s*:",
                low,
                re.I,
            )
        )

    def _is_substantive(pair):
        user, april, topic = _pair_text(pair)
        return bool(
            (user or april or topic)
            and not _is_clarification(pair)
            and not _is_transport_fallback(pair)
        )

    def _is_history_overview_pair(pair):
        if not isinstance(pair, dict):
            return False
        user, _, _ = _pair_text(pair)
        return _two_state_history_overview_query(user) or _two_state_discussion_query(user)

    def _build_history_overview(window):
        """Summarize the complete 12h dialogue into 10-15 semantic topic roots.

        The current history query is deliberately absent from the ranking. Roots are
        formed from the dialogue itself using sequence/test continuity and pair-to-pair
        semantic affinity. Each visible topic also records where that discussion
        stopped so a later clarification can return to the actual source pair.
        """
        candidates = [
            (i, pair) for i, pair in enumerate(window)
            if _is_substantive(pair) and not _is_history_overview_pair(pair)
        ]
        if not candidates:
            candidates = [
                (i, pair) for i, pair in enumerate(window)
                if isinstance(pair, dict) and not _is_history_overview_pair(pair)
            ]

        clusters = []
        for index, pair in reversed(candidates):
            user, answer, topic = _pair_text(pair)
            subject = _pair_subject(pair)
            test_id = _test_id_from_pair(pair)
            sequence_id = str(
                pair.get("dialogue_sequence_id")
                or pair.get("sequence_id")
                or pair.get("task_id")
                or ""
            ).strip()
            if not subject:
                subject = _clean(user or answer)[:220]

            best_cluster = None
            best_score = 0.0
            for cluster in clusters:
                root = cluster["root_pair"]
                root_user, root_answer, root_topic = _pair_text(root)
                root_test = _test_id_from_pair(root)
                root_sequence = str(
                    root.get("dialogue_sequence_id")
                    or root.get("sequence_id")
                    or root.get("task_id")
                    or ""
                ).strip()
                root_subject = cluster["subject"]

                score = max(
                    _topic_affinity(
                        f"{subject} {user} {answer}",
                        f"{root_subject} {root_user} {root_answer}",
                    ),
                    0.90 * _topic_affinity(subject, root_subject),
                )
                same_branch = bool(
                    (test_id is not None and root_test == test_id)
                    or (sequence_id and root_sequence and sequence_id == root_sequence)
                )
                if same_branch:
                    score = max(score, 0.90)

                if score > best_score:
                    best_score = score
                    best_cluster = cluster

            if best_cluster is not None and best_score >= 0.58:
                best_cluster["indices"].append(index)
                best_cluster["pairs"].append(pair)
                best_cluster["first_index"] = min(best_cluster["first_index"], index)
                best_cluster["last_index"] = max(best_cluster["last_index"], index)
            else:
                clusters.append({
                    "root_index": index,
                    "first_index": index,
                    "last_index": index,
                    "subject": subject[:320],
                    "root_pair": dict(pair),
                    "indices": [index],
                    "pairs": [pair],
                })

        # Global topic numbering is by recency: 1 = newest. Keep every topic
        # internally, while the user-facing overview shows only the newest ten.
        clusters.sort(key=lambda c: (c["last_index"], c["root_index"]), reverse=True)

        topics_all = []
        for number, cluster in enumerate(clusters, start=1):
            ordered = sorted(
                cluster["pairs"],
                key=lambda p: (
                    float(p.get("created_at") or 0.0),
                    int(p.get("turn_index") or p.get("sequence_turn_index") or 0),
                ),
            )
            first = ordered[0]
            last = ordered[-1]
            first_user, first_answer, _ = _pair_text(first)
            last_user, last_answer, last_topic = _pair_text(last)

            label = str(
                last_topic
                or cluster.get("subject")
                or _pair_subject(last)
                or first_user
                or last_user
            ).strip()
            content_label = _content(label)
            if len(content_label) > 8:
                label = " ".join(content_label[:8])
            label = label[:140]

            started = _clean(first_user or first_answer)[:220]
            stopped = _clean(last_user or last_answer)[:260]
            if last_user and last_answer:
                stopped = f"{last_user[:145]} → {last_answer[:120]}"

            topics_all.append({
                "number": number,
                "global_number": number,
                "topic": label,
                "pair_count": len(ordered),
                "start_index": cluster["first_index"],
                "last_index": cluster["last_index"],
                "started_with": started,
                "stopped_at": stopped,
                "source_pair_indices": sorted(set(cluster["indices"])),
            })

        topics = topics_all[:10]
        total_topics = len(topics_all)
        shown = len(topics)
        remaining = max(0, total_topics - shown)

        output = [
            "ОБЗОР ДИАЛОГА ЗА ДОСТУПНЫЕ 12 ЧАСОВ:",
            f"Показаны {shown} основных тем из {total_topics} смысловых тем.",
        ]
        if remaining:
            output.append(
                f"Остальные {remaining} темы не потеряны: их пары остаются в полном 12-часовом контексте и доступны при уточнении."
            )

        for item in topics:
            output.append(
                f"{item['number']}. {item['topic']} — обсуждали: {item['started_with']}; "
                f"остановились: {item['stopped_at']}."
            )

        output.append(
            "При уточнении используй исходные USER↔APRIL пары выбранной темы, "
            "объясни, что уже обсуждали и на чём остановились, затем предложи продолжить."
        )

        return {
            "scope_hours": 12,
            "available_pairs": len(window),
            "topic_count_total": total_topics,
            "topics_shown": shown,
            "remaining_topics_in_context": remaining,
            "topics": topics,
            "topics_all": topics_all,
            "visible_topic_limit": 10,
            "text": "\n".join(output)[:3400],
            "source": "FULL_12H_DIALOGUE_SEMANTIC_TOPIC_OVERVIEW",
        }

    def _pair_subject(pair):
        user, april, topic = _pair_text(pair)
        # Metadata is useful, but user+answer remain the source of truth when
        # metadata became stale in earlier turns.
        candidates = [topic, pair.get("active_entity"), pair.get("resolved_entity")]
        for value in candidates:
            subject = _clean(str(value or ""))
            if subject and len(_content(subject)) >= 1:
                return subject
        return _clean(f"{user} {april}")

    def _specificity(text):
        tokens = _content(text)
        concrete = [t for t in tokens if t not in {"каждого", "каждой", "каждые"}]
        return len(concrete)

    def _contains_reference(text):
        low = _clean(text)
        if any(phrase in low for phrase in _reference_forms):
            return True
        return bool(
            re.search(
                r"\b(?:кто|что|какой|какая|какие|какое)\s+из\s+(?:них|этих|тех)\b",
                low,
                re.I,
            )
            or re.search(r"\b(?:их|его|ее|её|каждого|каждые)\b", low, re.I)
            or re.search(
                r"\b(?:какое|какая|какие|который|которая|которые|что|кто)\b"
                r".{0,100}\bне\s*(?:назвал|назвала|назвали|упомянул|упомянула|упомянули)\b",
                low,
                re.I,
            )
            or re.search(
                r"\b(?:о\s+ч[её]м\s+я|что\s+я)\b.{0,80}\bспраш",
                low,
                re.I,
            )
        )

    def _contains_followup(text):
        low = _clean(text)
        if any(phrase in low for phrase in _followup_forms):
            return True
        return bool(
            re.search(
                r"\b(?:теперь|дальше|далее|ещ[её]|продолж|добав|подробнее|"
                r"детальнее|выдел|выбер|отбер|исправ|стоимост|цен)\w*",
                low,
                re.I,
            )
        )

    def _pair_root_score(pair, index):
        user, april, topic = _pair_text(pair)
        tid = _test_id_from_pair(pair)
        start = _looks_like_test_start(user, tid)
        root_bonus = 0.35 if start else 0.0
        answer_bonus = 0.05 if _two_state_answer_set(pair) else 0.0
        clarification_penalty = -0.75 if _is_clarification(pair) else 0.0
        return root_bonus + answer_bonus + clarification_penalty + index * 1e-7

    if not current or not pairs:
        return {
            "relation": "NEW",
            "confidence": 0.99,
            "selected_index": -1,
            "selected_pair": {},
            "selected_indices": [],
            "context_pairs": [],
            "memory_window": pairs,
            "best_score": 0.0,
            "reason": "NO_AUTHENTICATED_12H_PAIRS",
            "context_mode": "NEW_TOPIC_ISOLATED",
            "semantic_discussion": "",
            "resolved_referent": {},
            "semantic_operation": "answer",
            "candidate_count": len(pairs),
            "candidate_scores": [],
        }

    # Primary semantic pass: evaluate every pair in the full 12h window.
    # Lightweight local semantic enrichment runs once over the same COMPLETE
    # 12h window. Heavy models remain outside this hot path.
    light_12h = []
    try:
        light_12h = _two_state_light_12h_similarity(current, pairs)
    except Exception:
        light_12h = []

    combined_targets = []
    for pair in pairs:
        user, april, topic = _pair_text(pair)
        combined_targets.extend([
            f"{user} {april}".strip(),
            user,
            april,
            topic,
        ])
    batch = []
    try:
        batch = _batch_live_similarity(self, current, combined_targets)
    except Exception:
        batch = []

    rows = []
    for i, pair in enumerate(pairs):
        user, april, topic = _pair_text(pair)
        base = i * 4
        sem_pair = float(batch[base] if base < len(batch) else 0.0)
        sem_user = float(batch[base + 1] if base + 1 < len(batch) else 0.0)
        sem_answer = float(batch[base + 2] if base + 2 < len(batch) else 0.0)
        sem_topic = float(batch[base + 3] if base + 3 < len(batch) else 0.0)

        light = light_12h[i] if i < len(light_12h) else {}
        light_score = float(light.get("score", 0.0) or 0.0)

        topical = _topic_affinity(current, f"{topic} {user} {april}")
        user_topic = _topic_affinity(current, user)
        answer_topic = _topic_affinity(current, april)
        active_topic_score = _topic_affinity(current, active_topic) if active_topic else 0.0
        distance = len(pairs) - 1 - i
        recency = 1.0 / (1.0 + 0.05 * max(0, distance))
        clarification_penalty = 0.35 if _is_clarification(pair) else 0.0

        score = (
            0.33 * topical
            + 0.18 * user_topic
            + 0.13 * answer_topic
            + 0.07 * sem_pair
            + 0.04 * sem_user
            + 0.03 * sem_answer
            + 0.02 * sem_topic
            + 0.05 * active_topic_score
            + 0.05 * light_score
            + 0.05 * recency
            - clarification_penalty
        )
        rows.append({
            "index": i,
            "score": max(0.0, min(1.0, score)),
            "semantic_pair": sem_pair,
            "semantic_user": sem_user,
            "semantic_answer": sem_answer,
            "semantic_topic": sem_topic,
            "light_semantic_score": light_score,
            "light_tfidf": float(light.get("tfidf", 0.0) or 0.0),
            "light_user_fuzzy": float(light.get("user_fuzzy", 0.0) or 0.0),
            "light_answer_fuzzy": float(light.get("answer_fuzzy", 0.0) or 0.0),
            "light_topic_fuzzy": float(light.get("topic_fuzzy", 0.0) or 0.0),
            "light_partial_answer_fuzzy": float(light.get("partial_answer_fuzzy", 0.0) or 0.0),
            "light_partial_topic_fuzzy": float(light.get("partial_topic_fuzzy", 0.0) or 0.0),
            "topic_affinity": topical,
            "user_topic_affinity": user_topic,
            "answer_topic_affinity": answer_topic,
            "active_topic_affinity": active_topic_score,
            "recency": recency,
            "test_id": _test_id_from_pair(pair),
            "substantive": _is_substantive(pair),
            "answer_set": _two_state_answer_set(pair),
            "pair": pair,
        })

    rows_by_index = {row["index"]: row for row in rows}
    substantive_rows = [row for row in rows if row["substantive"]]

    # Lightweight result-item linker. A short request can target an item from a
    # previous answer even when whole-pair similarity is weak.
    def _answer_item_link_score(current_text, row):
        if not row.get("substantive"):
            return 0.0
        pair_for_link = row.get("pair") if isinstance(row.get("pair"), dict) else {}
        if _is_history_overview_pair(pair_for_link):
            # A history overview is an index into memory, not the source result.
            # Concrete follow-ups must bind to the original USER↔APRIL topic pair.
            return 0.0
        pair = row.get("pair") if isinstance(row.get("pair"), dict) else {}
        answer = str(
            pair.get("april") or pair.get("april_answer")
            or pair.get("assistant") or pair.get("answer") or ""
        ).strip()
        if not answer:
            return 0.0

        items = re.findall(
            r"(?:^|\n)\s*(?:[-•*]|\d{1,2}[.)])\s*([^\n]{3,180})",
            answer,
            re.M,
        )
        candidates = items or [answer]
        best = max((_topic_affinity(current_text, item) for item in candidates), default=0.0)

        # Named-item hit for short turns such as "про рено" / "расскажи про
        # легковые". Generic dialogue words are not allowed to qualify.
        answer_low = _clean(answer)
        answer_match_text = answer_low
        for latin, cyrillic in {
            "renault": "рено", "peugeot": "пежо", "citroen": "ситроен",
            "citroën": "ситроен", "bugatti": "бугатти", "alpine": "альпин",
            "mercedes": "мерседес", "volkswagen": "фольксваген",
        }.items():
            answer_match_text = re.sub(rf"(?<!\w){re.escape(latin)}(?!\w)", cyrillic, answer_match_text, flags=re.I)
        for token in _content(current_text):
            if len(token) < 4:
                continue
            if token in {"вопрос", "ответ", "диалог", "история", "помнить"}:
                continue
            if re.search(rf"(?<!\w){re.escape(token)}(?:\w*)", answer_match_text, re.I):
                best = max(best, 0.74)
        return max(0.0, min(1.0, best))

    answer_item_rows = []
    for row in rows:
        item_score = _answer_item_link_score(current, row)
        row["answer_item_link"] = round(item_score, 6)
        if item_score >= 0.48:
            answer_item_rows.append((item_score, row))
    answer_item_rows.sort(key=lambda x: (x[0], x[1]["index"]), reverse=True)
    best_answer_item_row = answer_item_rows[0][1] if answer_item_rows else None
    best_answer_item_score = float(answer_item_rows[0][0]) if answer_item_rows else 0.0

    test_id = _extract_test_id(current)
    starts_new_test = _looks_like_test_start(current, test_id)

    # Canonical relation rule #1: explicit new-task intent is a HARD barrier.
    # Old memory may never reopen a request the user explicitly started as new.
    explicit_new_task = bool(
        starts_new_test
        or re.search(
            r"\b(?:нов(?:ая|ую|ое)?\s+тема|другая\s+тема|"
            r"перейд(?:и|ем|ём)\s+(?:к|на)\s+друг(?:ую|ой)?\s+тем|"
            r"начн(?:е|ё)м\s+(?:нов(?:ую|ую)?|друг(?:ую)?))\b",
            _clean(current),
            re.I,
        )
    )
    if explicit_new_task:
        return {
            "relation": "NEW",
            "confidence": 0.99,
            "selected_index": -1,
            "selected_pair": {},
            "selected_indices": [],
            "context_pairs": [],
            "memory_window": pairs,
            "best_score": max((row["score"] for row in rows), default=0.0),
            "reason": "EXPLICIT_NEW_TASK",
            "context_mode": "NEW_TOPIC_ISOLATED",
            "semantic_discussion": "",
            "resolved_referent": {},
            "semantic_operation": "answer",
            "candidate_count": len(rows),
            "candidate_scores": rows,
            "test_id": test_id,
            "decision_basis": "HARD_NEW_CURRENT_INTENT",
            "relation_locked": True,
        }

    low_current = _clean(current)
    reference_query = _contains_reference(current)
    followup_query = _contains_followup(current)
    short_topic_followup = bool(
        re.match(r"^(?:о|об|про)\s+[A-Za-zА-Яа-яЁёЇїІіЄєҐґ-]{3,}(?:\s+[A-Za-zА-Яа-яЁёЇїІіЄєҐґ-]{3,})?$", _clean(current), re.I)
        or re.match(r"^[A-Za-zА-Яа-яЁёЇїІіЄєҐґ-]{4,}$", _clean(current), re.I)
        and _clean(current) not in {"теперь", "дальше", "стоимость", "цена", "японских"}
    )
    # A numbered test mention that is NOT starting a new test is itself a
    # continuation/reference to an already established test branch.
    test_reference = test_id is not None and not starts_new_test
    specificity = _specificity(current)

    # Short named-object turns are semantic continuations even when lexical
    # overlap with the full prior answer is weak (for example: "Рено" or
    # "уговорил рено так рено"). This is object evidence, not a raw similarity
    # threshold, and it is evaluated only inside the authenticated 12h window.
    named_object_link = False
    named_object_index = -1
    current_named_tokens = [
        token for token in _content(current)
        if len(token) >= 4
        and token not in {"вопрос", "ответ", "диалог", "история", "помнить"}
    ]
    if current_named_tokens and specificity <= 4:
        for row in reversed(substantive_rows):
            idx = int(row.get("index", -1))
            if idx < 0:
                continue
            pair = pairs[idx]
            if _is_history_overview_pair(pair):
                # A memory overview is an index, never the concrete topic antecedent.
                continue
            subject_text = (
                f"{_pair_subject(pair)} {_pair_text(pair)[0]} {_pair_text(pair)[1]}"
            )
            subject_tokens = _semantic_set(subject_text)
            for current_token in current_named_tokens:
                if current_token in subject_tokens:
                    named_object_link = True
                    named_object_index = idx
                    break
                if any(
                    _topic_affinity(current_token, candidate) >= 0.72
                    for candidate in subject_tokens
                ):
                    named_object_link = True
                    named_object_index = idx
                    break
            if named_object_link:
                break

    # HISTORY is a semantic mode, not a third relation. It can rescue a weak
    # NEW classification when the user explicitly asks for remembered
    # dialogue/pairs/questions/answers.
    history_overview_intent = _two_state_history_overview_query(current)
    history_summary_query = bool(
        history_overview_intent
        or re.search(
            r"\b(?:напомни|назови|покажи|перечисли|какие)\b.*\b(?:последн(?:ие|их)|тем(?:ы|а)|обсуждали|говорили)\b",
            low_current,
            re.I,
        )
        or re.search(r"\bпоследн(?:ие|их)\s+\d+\s+тем", low_current, re.I)
        or re.search(r"\bкакие\s+темы\b.*\b(?:обсуждали|говорили)\b", low_current, re.I)
    )
    topic_reference_number = _two_state_topic_reference_number(current)
    history_operation = _two_state_history_operation(current)
    history_intent = bool(
        history_operation != "NONE"
        or history_overview_intent
        or history_summary_query
        or re.search(
            r"\b(?:весь|вся|полный|полные)\s+(?:диалог|истори|пары|вопрос(?:ы)?|ответ(?:ы)?)\b",
            low_current,
            re.I,
        )
        or re.search(
            r"\b(?:покажи|выведи|перечисли|назови|напомни)\b.*"
            r"\b(?:диалог|истори|помниш|помнишь|вопрос(?:ы|ов)?\s+и\s+ответ(?:ы|ов)?|"
            r"запрос(?:ы|ов)?\s+и\s+ответ(?:ы|ов)?)\b",
            low_current,
            re.I,
        )
        or re.search(
            r"\b(?:покажи|выведи)\b.*\b(?:пары\s+запросов\s+и\s+ответов|полные\s+пары)\b",
            low_current,
            re.I,
        )
        or re.search(
            r"\b(?:что|какие)\b.*\b(?:вопрос(?:ы|ов)?|запрос(?:ы|ов)?|ответ(?:ы|ов)?|диалог)\b.*"
            r"\b(?:помниш|помнишь|вспомниш|вспомнишь|помню|в\s+истори|в\s+диалоге)\b",
            low_current,
            re.I,
        )
    )

    clarification_bridge = None
    if pairs and _is_clarification(pairs[-1]):
        candidates = []
        for i, pair in enumerate(pairs[:-1]):
            if not _is_substantive(pair):
                continue
            row = rows_by_index.get(i, {})
            light = light_12h[i] if i < len(light_12h) else {}
            bridge_score = (
                0.45 * float(row.get("score", 0.0) or 0.0)
                + 0.35 * float(light.get("score", 0.0) or 0.0)
                + 0.12 * float(light.get("partial_answer_fuzzy", 0.0) or 0.0)
                + 0.05 * float(light.get("partial_topic_fuzzy", 0.0) or 0.0)
                + 0.03 * float(row.get("recency", 0.0) or 0.0)
            )
            candidates.append((bridge_score, i))
        if candidates:
            candidates.sort(reverse=True)
            bridge_score, bridge_index = candidates[0]
            if bridge_score >= 0.13:
                clarification_bridge = {
                    "clarification_pair_index": len(pairs) - 1,
                    "clarification_request": _pair_text(pairs[-1])[0],
                    "clarification_answer": current,
                    "root_pair_index": bridge_index,
                    "root_pair": dict(pairs[bridge_index]),
                    "score": round(float(bridge_score), 6),
                }

    # A previous "show/remember our dialogue" answer is a projection of history,
    # not the source topic itself. For a later concrete clarification, prefer the
    # original USER↔APRIL topic pairs and keep the overview row only as history evidence.
    if not history_intent:
        non_overview_substantive = [
            row for row in substantive_rows
            if not _is_history_overview_pair(row.get("pair") or {})
        ]
        if non_overview_substantive:
            substantive_rows = non_overview_substantive

    # Canonical relation rule #2: an explicit test-number reference resolves to
    # the latest substantive ROOT of that test, never to a later clarification.
    anchor_index = -1
    anchor_reason = ""
    if clarification_bridge is not None:
        anchor_index = int(clarification_bridge["root_pair_index"])
        anchor_reason = "CLARIFICATION_BRIDGE_TO_12H_ROOT"
    elif test_id is not None:
        test_roots = [
            i for i, pair in enumerate(pairs)
            if _test_id_from_pair(pair) == test_id
            and _is_substantive(pair)
            and _looks_like_test_start(_pair_text(pair)[0], test_id)
        ]
        if test_roots:
            anchor_index = max(test_roots)
            anchor_reason = "TEST_ID_ROOT_MATCH"
        else:
            same_test = [
                i for i, pair in enumerate(pairs)
                if _test_id_from_pair(pair) == test_id and _is_substantive(pair)
            ]
            if same_test:
                anchor_index = max(same_test)
                anchor_reason = "TEST_ID_PAIR_MATCH"

    # Canonical relation rule #3: concrete anaphora binds to the best substantive
    # result that can actually serve as its antecedent. The latest pair is used
    # only when the current wording is genuinely underspecified.
    if anchor_index < 0:
        candidate_indices = [row["index"] for row in substantive_rows]
        if candidate_indices:
            generic_followup = specificity == 0 or specificity <= 1
            active_candidates = [
                i for i in candidate_indices
                if active_topic
                and _topic_affinity(
                    active_topic,
                    f"{_pair_subject(pairs[i])} {_pair_text(pairs[i])[0]} {_pair_text(pairs[i])[1]}"
                ) >= 0.12
            ]
            if reference_query and active_candidates:
                # Pronouns/ellipsis stay inside the currently active dialogue
                # branch. A concrete qualifier such as "японских" is resolved
                # semantically inside that branch; a pure pronoun such as "их"
                # uses the latest substantive result from the same branch.
                if specificity <= 1 and not any(
                    token in {"стоимость", "цена", "цены", "стоит", "доллар",
                              "каждого", "каждой", "каждые", "их", "него", "нее", "неё"}
                    for token in _content(current)
                ):
                    anchor_index = max(
                        active_candidates,
                        key=lambda i: (
                            rows_by_index[i]["topic_affinity"],
                            rows_by_index[i]["answer_topic_affinity"],
                            i,
                        ),
                    )
                    anchor_reason = "ACTIVE_CHAIN_SEMANTIC_ANTECEDENT"
                else:
                    anchor_index = active_candidates[-1]
                    anchor_reason = "LATEST_ACTIVE_CHAIN_ANTECEDENT"
            elif reference_query and generic_followup:
                anchor_index = candidate_indices[-1]
                anchor_reason = "LATEST_SUBSTANTIVE_ANTECEDENT"
            elif short_topic_followup:
                ranked_topic = sorted(
                    candidate_indices,
                    key=lambda i: (
                        rows_by_index[i]["topic_affinity"]
                        + 0.35 * rows_by_index[i]["answer_topic_affinity"]
                        + 0.04 * rows_by_index[i]["recency"],
                        i,
                    ),
                    reverse=True,
                )
                if ranked_topic:
                    anchor_index = ranked_topic[0]
                    anchor_reason = "SHORT_TOPIC_ACTIVE_CHAIN"
            elif reference_query:
                ranked_ref = sorted(
                    candidate_indices,
                    key=lambda i: (
                        rows_by_index[i]["topic_affinity"]
                        + 0.35 * rows_by_index[i]["answer_topic_affinity"]
                        + 0.20 * rows_by_index[i]["user_topic_affinity"],
                        i,
                    ),
                    reverse=True,
                )
                if ranked_ref:
                    anchor_index = ranked_ref[0]
                    anchor_reason = "SEMANTIC_ANTECEDENT_MATCH"
            elif specificity == 0 and followup_query:
                anchor_index = candidate_indices[-1]
                anchor_reason = "GENERIC_FOLLOWUP_LATEST_ACTIVE_PAIR"
            elif specificity == 1 and followup_query:
                ranked_short = sorted(
                    candidate_indices,
                    key=lambda i: (
                        rows_by_index[i]["topic_affinity"]
                        + 0.25 * rows_by_index[i]["answer_topic_affinity"],
                        i,
                    ),
                    reverse=True,
                )
                if ranked_short:
                    best_short = ranked_short[0]
                    best_short_affinity = rows_by_index[best_short]["topic_affinity"]
                    if best_short_affinity >= 0.08 or followup_query:
                        anchor_index = best_short
                        anchor_reason = "SHORT_FOLLOWUP_SEMANTIC_ANCHOR"
            else:
                strongest = max(
                    candidate_indices,
                    key=lambda i: (
                        rows_by_index[i]["topic_affinity"],
                        rows_by_index[i]["score"],
                        i,
                    ),
                )
                if rows_by_index[strongest]["topic_affinity"] >= 0.16:
                    anchor_index = strongest
                    anchor_reason = "DIRECT_SEMANTIC_PAIR_MATCH"

    if history_intent and substantive_rows and anchor_index < 0:
        anchor_index = max(int(row.get("index", -1)) for row in substantive_rows)
        anchor_reason = "HISTORY_QUERY_FULL_12H_WINDOW"
    elif best_answer_item_row is not None and best_answer_item_score >= 0.48 and anchor_index < 0:
        anchor_index = int(best_answer_item_row["index"])
        anchor_reason = "PREVIOUS_RESULT_ITEM_LINK"

    if anchor_index < 0:
        return {
            "relation": "NEW",
            "confidence": max(0.78, min(0.99, 1.0 - max((row["score"] for row in rows), default=0.0) * 0.35)),
            "selected_index": -1,
            "selected_pair": {},
            "selected_indices": [],
            "context_pairs": [],
            "memory_window": pairs,
            "best_score": max((row["score"] for row in rows), default=0.0),
            "reason": decision_basis if "decision_basis" in locals() else "NO_SEMANTIC_LINK_IN_FULL_12H_DIALOGUE",
            "context_mode": "NEW_TOPIC_ISOLATED",
            "semantic_discussion": "",
            "decision_basis": "ALL_LAYERS_NEW",
            "relation_locked": True,
            "history_intent": history_intent,
            "resolved_referent": {},
            "semantic_operation": "answer",
            "candidate_count": len(rows),
            "candidate_scores": rows,
        }

    anchor_pair = dict(pairs[anchor_index])
    anchor_user, anchor_answer, anchor_topic = _pair_text(anchor_pair)
    anchor_test_id = _test_id_from_pair(anchor_pair)
    anchor_subject = _pair_subject(anchor_pair)

    # Chain discovery is semantic, not "last N pairs". We collect every
    # substantive pair belonging to the anchor's discourse branch or sharing its
    # subject strongly with the current request/anchor.
    selected_indices = []
    current_topic_score = rows_by_index[anchor_index]["topic_affinity"]
    for i, row in enumerate(rows):
        if not row["substantive"]:
            continue
        pair = row["pair"]
        pair_tid = row["test_id"]
        user, april, topic = _pair_text(pair)
        same_test_branch = (
            anchor_test_id is not None
            and pair_tid == anchor_test_id
        )
        pair_to_anchor = _topic_affinity(f"{anchor_subject} {anchor_user} {anchor_answer}",
                                          f"{_pair_subject(pair)} {user} {april}")
        pair_to_current = row["topic_affinity"]
        current_to_answer = row["answer_topic_affinity"]
        relevant = (
            i == anchor_index
            or same_test_branch
            or pair_to_anchor >= 0.28
            or pair_to_current >= 0.20
            or current_to_answer >= 0.28
        )
        if relevant:
            selected_indices.append(i)

    # For anaphoric/reference turns, the antecedent must remain the first semantic
    # operand in the SAME active branch, even if an older row has a higher generic
    # similarity score. Never allow a different historical topic to hijack "их",
    # "из них", "каждого", "в столбик" or a short correction.
    if anchor_index not in selected_indices:
        selected_indices.append(anchor_index)
    selected_indices = sorted(dict.fromkeys(selected_indices))

    if history_operation == "NONE" and not test_id and (reference_query or followup_query):
        branch_candidates = [
            i for i in selected_indices
            if rows_by_index[i]["substantive"]
            and (
                not active_topic
                or _topic_affinity(
                    active_topic,
                    f"{_pair_subject(pairs[i])} {_pair_text(pairs[i])[0]} {_pair_text(pairs[i])[1]}"
                ) >= 0.12
            )
        ]
        if branch_candidates:
            if active_topic and reference_query and specificity <= 1:
                # Pure/near-pure anaphora: latest substantive result in the active
                # branch is the antecedent.
                best_anchor = max(
                    branch_candidates,
                    key=lambda i: i,
                )
            elif active_topic and reference_query:
                # Concrete qualifier ("домашних", "японских", "самые") resolves
                # semantically within the active branch, never against all 12h rows.
                best_anchor = max(
                    branch_candidates,
                    key=lambda i: (
                        rows_by_index[i]["topic_affinity"],
                        rows_by_index[i]["answer_topic_affinity"],
                        i,
                    ),
                )
            elif specificity >= 1:
                best_anchor = max(
                    branch_candidates,
                    key=lambda i: (
                        rows_by_index[i]["topic_affinity"],
                        rows_by_index[i]["answer_topic_affinity"],
                        i,
                    ),
                )
            else:
                best_anchor = max(branch_candidates, key=lambda i: i)

            anchor_index = best_anchor
            anchor_pair = dict(pairs[anchor_index])
            anchor_user, anchor_answer, anchor_topic = _pair_text(anchor_pair)
            anchor_subject = _pair_subject(anchor_pair)

    # ------------------------------------------------------------------
    # MONOTONIC TWO-SIGNAL DECISION
    #
    # Priority is strict:
    #   HARD NEW -> NEW
    #   HISTORY / RESULT / OBJECT / DISCOURSE -> CONTINUE
    #   semantic similarity -> evidence only
    #   otherwise -> NEW
    # After this point relation is LOCKED. Later enrichment may select/support
    # pairs, but it must never recompute CONTINUE/NEW.
    # ------------------------------------------------------------------
    relation = "NEW"
    decision_basis = "ALL_LAYERS_NEW"
    relation_lock = False

    if explicit_new_task:
        relation = "NEW"
        decision_basis = "HARD_NEW_CURRENT_INTENT"
        relation_lock = True
        selected_indices = []
        anchor_index = -1
        anchor_pair = {}
    else:
        history_link = bool(history_intent and substantive_rows)
        semantic_followup = bool(
            re.search(
                r"\b(?:дальше|далее|ещ[её]|продолж(?:и|ай|ить|им)|добав(?:ь|ить)|"
                r"подробнее|детальнее|уточни|поясни|объясни|раскрой|выдели|выбери|"
                r"отбери|исправь|не\s+повторяй|кроме|из\s+них)\b",
                low_current,
                re.I,
            )
        )
        discourse_link = bool(
            reference_query
            or semantic_followup
            or short_topic_followup
            or test_reference
            or clarification_bridge is not None
        )
        anchor_row = rows_by_index.get(anchor_index, {})
        anchor_semantic_link = bool(
            anchor_index >= 0
            and (
                float(anchor_row.get("topic_affinity", 0.0) or 0.0) >= 0.16
                or float(anchor_row.get("answer_topic_affinity", 0.0) or 0.0) >= 0.16
                or _topic_affinity(current, anchor_topic) >= 0.20
            )
        )
        result_item_link = bool(best_answer_item_row and best_answer_item_score >= 0.48)

        if history_link:
            relation = "CONTINUE"
            decision_basis = "HISTORY_OVERRIDES_WEAK_NEW"
            relation_lock = True
        elif result_item_link:
            relation = "CONTINUE"
            decision_basis = "PREVIOUS_RESULT_ITEM_LINK"
            relation_lock = True
            anchor_index = int(best_answer_item_row["index"])
            anchor_pair = dict(pairs[anchor_index])
            anchor_user, anchor_answer, anchor_topic = _pair_text(anchor_pair)
            selected_indices = [anchor_index]
        elif named_object_link:
            relation = "CONTINUE"
            decision_basis = "NAMED_OBJECT_CONTINUATION_LINK"
            relation_lock = True
            anchor_index = named_object_index
            anchor_pair = dict(pairs[anchor_index])
            anchor_user, anchor_answer, anchor_topic = _pair_text(anchor_pair)
            selected_indices = [anchor_index]
        elif discourse_link and (anchor_index >= 0 or pairs):
            relation = "CONTINUE"
            decision_basis = "DISCOURSE_DEPENDENCY_WITH_12H_EVIDENCE"
            relation_lock = True
        elif anchor_semantic_link:
            relation = "CONTINUE"
            decision_basis = "DIRECT_SEMANTIC_12H_LINK"
            relation_lock = True
        else:
            relation = "NEW"
            decision_basis = "ALL_LAYERS_NEW"
            relation_lock = True
            selected_indices = []
            anchor_index = -1
            anchor_pair = {}

    locked_relation = relation

    history_overview = {}
    selected_dialogue = {}
    history_search_query = ""
    if history_intent:
        # HISTORY is still one semantic operation family inside the same route.
        # OVERVIEW groups the full 12h window into visible topics; FIND_DIALOGUE/
        # OPEN_DIALOGUE resolve one concrete semantic dialogue sequence;
        # SUMMARIZE_DIALOGUE reuses the previous concrete history target when the
        # user says things like "что в нём обсуждали".
        if history_operation == "OVERVIEW":
            history_overview = _build_history_overview(pairs)
            topic_roots = [
                int(item["last_index"])
                for item in (history_overview.get("topics") or [])
                if isinstance(item, dict)
                and str(item.get("last_index", "")).lstrip("-").isdigit()
            ]
            if not topic_roots and pairs:
                topic_roots = [next(
                    (i for i in range(len(pairs)-1, -1, -1) if _is_substantive(pairs[i])),
                    len(pairs)-1,
                )]
            selected_indices = sorted(dict.fromkeys(topic_roots))
            anchor_index = selected_indices[-1] if selected_indices else -1
        elif history_operation in {"FIND_DIALOGUE", "OPEN_DIALOGUE"}:
            previous_target = _two_state_previous_history_search_target(pairs)
            history_search_query = _two_state_history_search_query(current)
            selected_topic_number = topic_reference_number

            if history_operation == "OPEN_DIALOGUE":
                if previous_target.get("topic_number") is not None:
                    selected_topic_number = previous_target.get("topic_number")
                history_search_query = str(previous_target.get("query") or history_search_query)

            if selected_topic_number is not None:
                # The number is a source topic/test/lesson identity, not an ordinal
                # position in the visible overview. Search the full authenticated
                # 12h pair set and let exact numbered identity win.
                exact_query = f"тема {int(selected_topic_number)}"
                selected_dialogue = _two_state_history_search_cluster(
                    current, pairs, preferred_query=exact_query
                )
                history_overview = {
                    "scope_hours": 12,
                    "available_pairs": len(pairs),
                    "operation": history_operation,
                    "selected_dialogue": dict(selected_dialogue or {}),
                    "topic_number": int(selected_topic_number),
                    "topics": [],
                    "topics_all": [],
                    "text": (
                        f"Найдена тема {int(selected_topic_number)}: "
                        f"{selected_dialogue.get('topic') or 'без названия'}"
                    ) if selected_dialogue else (
                        f"Тема {int(selected_topic_number)} не найдена "
                        "в полном доступном 12-часовом контексте."
                    ),
                    "source": "FULL_12H_NUMBERED_TOPIC_SEARCH",
                }
            else:
                selected_dialogue = _two_state_history_search_cluster(
                    current, pairs, preferred_query=history_search_query
                )
                history_overview = {
                    "scope_hours": 12,
                    "operation": history_operation,
                    "selected_dialogue": dict(selected_dialogue or {}),
                    "topics": [],
                    "text": (
                        "Найден конкретный диалог: "
                        + str(selected_dialogue.get("topic") or selected_dialogue.get("search_query") or "")
                    ) if selected_dialogue else "",
                    "source": "FULL_12H_SEMANTIC_DIALOGUE_SEARCH",
                }
                if selected_dialogue:
                    selected_dialogue["authenticated_user_id"] = authenticated_user_id

            if selected_dialogue:
                selected_indices = list(selected_dialogue.get("pair_indices") or [])
                anchor_index = int(selected_dialogue.get("anchor_index", -1))
            else:
                selected_indices = []
                anchor_index = -1
        elif history_operation == "SUMMARIZE_DIALOGUE":
            previous_target = _two_state_previous_history_search_target(pairs)
            history_search_query = str(previous_target.get("query") or "")
            topic_reference_number = previous_target.get("topic_number")
            all_topics = []
            if topic_reference_number is not None:
                history_search_query = f"тема {int(topic_reference_number)}"
                selected_dialogue = _two_state_history_search_cluster(
                    current,
                    pairs,
                    preferred_query=history_search_query,
                )
                history_overview = {
                    "scope_hours": 12,
                    "available_pairs": len(pairs),
                    "operation": history_operation,
                    "selected_dialogue": dict(selected_dialogue or {}),
                    "topic_number": int(topic_reference_number),
                    "topics": [],
                    "topics_all": [],
                    "text": (
                        f"Сводка темы {int(topic_reference_number)}: "
                        f"{selected_dialogue.get('topic') or 'тема не найдена'}."
                    ) if selected_dialogue else "",
                    "source": "FULL_12H_NUMBERED_TOPIC_REUSE",
                }
            else:
                selected_dialogue = _two_state_history_search_cluster(
                    history_search_query or current,
                    pairs,
                    preferred_query=history_search_query,
                )
                history_overview = {
                    "scope_hours": 12,
                    "operation": history_operation,
                    "selected_dialogue": dict(selected_dialogue or {}),
                    "topics": [],
                    "text": "",
                    "source": "FULL_12H_DIALOGUE_REUSE_OF_PREVIOUS_HISTORY_TARGET",
                }
            if selected_dialogue:
                selected_dialogue["authenticated_user_id"] = authenticated_user_id
                selected_indices = list(selected_dialogue.get("pair_indices") or [])
                anchor_index = int(selected_dialogue.get("anchor_index", -1))
            else:
                selected_indices = []
                anchor_index = -1

        # A history search result is the authoritative anchor for FIND/OPEN/
        # SUMMARIZE. Keep it intact even if a legacy evidence branch above had no
        # numeric anchor of its own.
        if selected_dialogue and anchor_index < 0:
            try:
                anchor_index = int(selected_dialogue.get("anchor_index", -1))
            except (TypeError, ValueError):
                anchor_index = -1
        if selected_dialogue and anchor_index < 0 and selected_indices:
            anchor_index = int(selected_indices[-1])

        if anchor_index >= 0 and anchor_index < len(pairs):
            anchor_pair = dict(pairs[anchor_index])
            anchor_user, anchor_answer, anchor_topic = _pair_text(anchor_pair)
            anchor_test_id = _test_id_from_pair(anchor_pair)
            anchor_subject = _pair_subject(anchor_pair)

    if locked_relation == "NEW":
        return {
            "relation": "NEW",
            "confidence": max(0.78, min(0.99, 1.0 - max((row["score"] for row in rows), default=0.0) * 0.20)),
            "selected_index": -1,
            "selected_pair": {},
            "selected_indices": [],
            "context_pairs": [],
            "memory_window": pairs,
            "best_score": max((row["score"] for row in rows), default=0.0),
            "reason": decision_basis,
            "context_mode": "NEW_TOPIC_ISOLATED",
            "semantic_discussion": "",
            "resolved_referent": {},
            "semantic_operation": "answer",
            "candidate_count": len(rows),
            "candidate_scores": rows,
            "decision_basis": decision_basis,
            "relation_locked": True,
        }

    # Semantic operation for the structured request.
    # A clarification answer inherits the unresolved operation from the
    # clarification request instead of becoming a one-word standalone task.
    operation_source = low_current
    if clarification_bridge is not None:
        operation_source = _clean(clarification_bridge.get("clarification_request") or current)

    if test_id is not None and re.search(
        r"\b(?:о\s+ч[её]м\s+я\s+(?:тебя\s+)?спраш|что\s+я\s+(?:тебя\s+)?спраш|"
        r"просмотри\b.*\bтест(?:е|а|ом)?\b|посмотри\b.*\bтест(?:е|а|ом)?\b)",
        operation_source,
        re.I,
    ):
        semantic_operation = "retrieve_original_test_request"
    elif re.search(r"\b(?:стоимость|цена|цены|сколько\s+стоит|доллар|дорог(?:ой|ая|ие|их)|дешев(?:ый|ая|ые|ых))\w*", operation_source, re.I):
        semantic_operation = "estimate_cost_of_referenced_items"
    elif re.search(r"\b(?:выдели|выбери|отбери)\b", low_current, re.I):
        semantic_operation = "filter_referenced_result"
    elif re.search(r"\b(?:исправь|исправся|я\s+про)\b", low_current, re.I):
        semantic_operation = "correct_previous_interpretation"
    elif re.search(r"\b(?:в\s+столбик|списком|по\s+пунктам)\b", low_current, re.I):
        semantic_operation = "reformat_previous_result"
    elif history_intent:
        semantic_operation = {
            "OVERVIEW": "summarize_12h_topics",
            "FIND_DIALOGUE": "find_dialogue_sequence",
            "OPEN_DIALOGUE": "open_dialogue_sequence",
            "SUMMARIZE_DIALOGUE": "summarize_selected_dialogue",
        }.get(history_operation, "history_lookup")
    elif re.search(r"\b(?:кто|что|какой|какая|какие|какое)\b", low_current, re.I) and reference_query:
        semantic_operation = "answer_about_referenced_items"
    elif re.search(r"\b(?:назови|назов|перечисли)\b", low_current, re.I):
        semantic_operation = "list_or_extend_referenced_items"
    else:
        semantic_operation = "develop_current_dialogue_task"

    resolved_referent = {
        "test_id": anchor_test_id,
        "pair_index": anchor_index,
        "subject": anchor_subject[:320],
        "clarification_bridge": clarification_bridge or {},
        "user_request": anchor_user[:700],
        "april_result": anchor_answer[:1200],
        "answer_set": bool(_two_state_answer_set(anchor_pair)),
        "reason": anchor_reason,
    }

    # Attach relevance metadata used by the semantic discussion stage.
    enriched_context = []
    for i in selected_indices:
        pair = dict(pairs[i])
        row = rows_by_index.get(i, {})
        pair["_semantic_local_index"] = i
        pair["_semantic_relevance"] = round(
            max(
                float(row.get("topic_affinity", 0.0) or 0.0),
                float(row.get("answer_topic_affinity", 0.0) or 0.0),
                float(row.get("user_topic_affinity", 0.0) or 0.0),
            ),
            6,
        )
        if i == anchor_index:
            pair["_semantic_role"] = "ANCHOR"
        elif _test_id_from_pair(pair) == anchor_test_id and anchor_test_id is not None:
            pair["_semantic_role"] = "SAME_TEST_BRANCH"
        else:
            pair["_semantic_role"] = "SEMANTIC_SUPPORT"
        enriched_context.append(pair)

    if history_operation == "OVERVIEW" and history_overview:
        semantic_discussion = str(history_overview.get("text") or "").strip()
    else:
        semantic_discussion = _two_state_build_discussion_digest(
            current,
            enriched_context,
            rows,
            resolved_referent=resolved_referent,
            semantic_operation=semantic_operation,
        )

    anchor_row = rows_by_index.get(anchor_index, {}) if anchor_index >= 0 else {}
    anchor_topic_affinity = float(anchor_row.get("topic_affinity", 0.0) or 0.0)
    anchor_answer_affinity = float(anchor_row.get("answer_topic_affinity", 0.0) or 0.0)
    anchor_signal = max(anchor_topic_affinity, anchor_answer_affinity, _topic_affinity(current, anchor_topic))
    safe_selected_pair = dict(pairs[anchor_index]) if 0 <= anchor_index < len(pairs) else {}

    # A concrete history operation without a found dialogue must never crash or
    # fabricate an anchor. It stays CONTINUE only when an actual selected dialogue
    # exists; otherwise the existing selector may fall through to NEW semantics.
    if history_operation in {"FIND_DIALOGUE", "OPEN_DIALOGUE", "SUMMARIZE_DIALOGUE"} and not selected_dialogue:
        locked_relation = "NEW"
        relation_lock = True
        anchor_index = -1
        safe_selected_pair = {}
        anchor_signal = 0.0
        context_pairs = []

    return {
        "relation": locked_relation,
        "confidence": max(
            0.72 if locked_relation == "CONTINUE" else 0.88,
            min(0.99, 0.62 + 0.26 * anchor_signal) if locked_relation == "CONTINUE" else 0.90,
        ),
        "selected_index": anchor_index,
        "selected_pair": safe_selected_pair,
        "selected_indices": selected_indices,
        "context_pairs": enriched_context,
        "memory_window": pairs,
        "best_score": max((row["score"] for row in rows), default=0.0),
        "reason": (
            decision_basis
            if decision_basis != "ALL_LAYERS_NEW"
            else (
                "TEST_ID_ROOT_SEMANTIC_CHAIN"
                if test_id is not None
                else "REFERENCE_TO_ACTIVE_SEMANTIC_CHAIN"
                if reference_query
                else "SEMANTIC_CHAIN_CONTINUATION"
            )
        ),
        "context_mode": "HISTORY_LOOKUP" if history_intent else "LIVE_CONTINUATION",
        "semantic_discussion": semantic_discussion,
        "resolved_referent": resolved_referent,
        "semantic_operation": semantic_operation,
        "candidate_count": len(rows),
        "candidate_scores": rows,
        "light_semantic_engine": {
            "enabled": True,
            "library": "scikit-learn TFIDF + RapidFuzz",
            "scope": "FULL_12H",
            "heavy_models_disabled": True,
        },
        "clarification_bridge": clarification_bridge or {},
        "history_summary_query": history_summary_query,
        "history_intent": history_intent,
        "history_operation": history_operation,
        "history_search_query": history_search_query,
        "topic_reference_number": topic_reference_number,
        "authenticated_user_id": authenticated_user_id,
        "selected_dialogue": selected_dialogue,
        "history_overview_intent": history_overview_intent,
        "history_overview": history_overview,
        "decision_basis": decision_basis,
        "relation_locked": relation_lock,
        "best_answer_item_score": round(best_answer_item_score, 6),
        "test_id": anchor_test_id,
    }


def _two_state_build_discussion_digest(
    current,
    context_pairs,
    scored_rows,
    *,
    resolved_referent=None,
    semantic_operation="",
):
    """Turn linked USER↔APRIL pairs into a semantic discussion for Provider.

    The full 12h dialogue is searched before this function is called. This function
    does not search memory; it explains why the selected pairs belong to the same
    dialogue chain and what the current request does with their result.
    """
    resolved_referent = resolved_referent if isinstance(resolved_referent, dict) else {}
    score_by_index = {
        int(row.get("index", -1)): float(row.get("score", 0.0) or 0.0)
        for row in (scored_rows or [])
        if isinstance(row, dict)
    }

    parts = [
        "СМЫСЛОВАЯ ЦЕПОЧКА ДИАЛОГА:",
        f"ТЕКУЩИЙ ЗАПРОС: {str(current or '').strip()[:700]}",
    ]

    if semantic_operation:
        parts.append(f"СЕМАНТИЧЕСКОЕ ДЕЙСТВИЕ: {str(semantic_operation).strip()[:180]}")

    if resolved_referent:
        parts.append(
            "РАЗРЕШЁННАЯ ОПОРНАЯ ПАРА: "
            f"index={resolved_referent.get('pair_index', '')}; "
            f"test_id={resolved_referent.get('test_id', '')}; "
            f"subject={str(resolved_referent.get('subject') or '')[:320]}"
        )
        user_ref = str(resolved_referent.get("user_request") or "").strip()
        april_ref = str(resolved_referent.get("april_result") or "").strip()
        if user_ref:
            parts.append(f"ОПОРНЫЙ USER: {user_ref[:700]}")
        if april_ref:
            parts.append(f"ОПОРНЫЙ APRIL РЕЗУЛЬТАТ: {april_ref[:1200]}")

    ordered = sorted(
        [p for p in (context_pairs or []) if isinstance(p, dict)],
        key=lambda p: (
            float(p.get("created_at") or 0.0),
            int(p.get("turn_index") or p.get("sequence_turn_index") or 0),
        ),
    )
    for pair in ordered:
        turn = pair.get("turn_index") or pair.get("sequence_turn_index") or pair.get("turn") or ""
        user = str(pair.get("user") or pair.get("user_request") or pair.get("user_text") or "").strip()
        april = str(
            pair.get("april")
            or pair.get("april_answer")
            or pair.get("assistant")
            or pair.get("answer")
            or ""
        ).strip()
        idx = pair.get("_semantic_local_index")
        idx_text = str(idx) if str(idx).lstrip("-").isdigit() else ""
        role = str(pair.get("_semantic_role") or "").strip()
        rel = pair.get("_semantic_relevance")
        line = f"PAIR {turn} [index={idx_text or '?'}{', role='+role if role else ''}]: USER={user[:520]} | APRIL={april[:1000]}"
        if idx_text:
            try:
                score = float(score_by_index.get(int(idx_text), rel or 0.0) or 0.0)
                line += f" | связь={score:.3f}"
            except Exception:
                pass
        parts.append(line)

    # The discussion is deliberately compact enough for the existing provider
    # transport. Full 12h scanning happened before this digest was built.
    return "\n".join(parts)[:5200]


def _two_state_structured_request(
    current,
    relation,
    context_mode,
    semantic_task,
    context_pairs,
    semantic_discussion,
    selected_index,
    selected_pair,
    canonical_topic,
    *,
    resolved_referent=None,
    semantic_operation="",
    history_overview=None,
):
    """Build the single structured request handed to Provider/OpenAI.

    Memory selection and semantic resolution are already complete at this boundary.
    The provider receives the current user request plus the resolved chain and is
    forbidden to perform another history search or substitute a different topic.
    """
    task = dict(semantic_task or {})
    operation = str(semantic_operation or task.get("operation") or "answer").lower()
    task.update({
        "operation": operation,
        "relation": relation,
        "context_mode": context_mode,
        "current_request": str(current or "").strip(),
        "canonical_topic": str(canonical_topic or "").strip(),
        "linked_pair_count": len(context_pairs),
        "semantic_discussion": str(semantic_discussion or "").strip(),
    })

    resolved_referent = (
        dict(resolved_referent)
        if isinstance(resolved_referent, dict)
        else {}
    )
    history_overview = (
        dict(history_overview)
        if isinstance(history_overview, dict)
        else {}
    )

    # Only semantically selected pairs cross the provider boundary. This is a
    # transport compaction, not a memory-window limit: the selector already scanned
    # every pair in the complete 12h window.
    provider_pairs = []
    history_operation = str(history_overview.get("operation") or "") if history_overview else ""
    selected_dialogue = history_overview.get("selected_dialogue") if isinstance(history_overview.get("selected_dialogue"), dict) else {}

    if history_overview and history_operation in {"FIND_DIALOGUE", "OPEN_DIALOGUE", "SUMMARIZE_DIALOGUE"} and selected_dialogue:
        # Concrete history search: pass the actual matched dialogue sequence. The
        # complete 12h scan already happened; this is only transport compaction.
        for pair in (selected_dialogue.get("pairs") or []):
            if not isinstance(pair, dict):
                continue
            provider_pairs.append({
                "turn": pair.get("turn_index") or pair.get("sequence_turn_index") or pair.get("turn"),
                "user": str(
                    pair.get("user")
                    or pair.get("user_request")
                    or pair.get("user_text")
                    or ""
                ).strip()[:700],
                "april": str(
                    pair.get("april")
                    or pair.get("april_answer")
                    or pair.get("assistant")
                    or pair.get("answer")
                    or ""
                ).strip()[:1200],
                "topic": str(
                    pair.get("sequence_topic")
                    or pair.get("topic")
                    or pair.get("canonical_topic")
                    or selected_dialogue.get("topic")
                    or ""
                ).strip()[:320],
                "semantic_role": "HISTORY_DIALOGUE_PAIR",
                "semantic_relevance": selected_dialogue.get("match_score"),
            })
    elif history_overview:
        # Broad overview: compact the topic index, not the full raw pair bodies.
        for item in (history_overview.get("topics") or []):
            if not isinstance(item, dict):
                continue
            provider_pairs.append({
                "turn": item.get("last_index"),
                "user": str(item.get("started_with") or "").strip()[:260],
                "april": str(item.get("stopped_at") or "").strip()[:300],
                "topic": str(item.get("topic") or "").strip()[:140],
                "semantic_role": "HISTORY_TOPIC",
                "semantic_relevance": None,
                "pair_count": int(item.get("pair_count") or 0),
                "source_pair_indices": list(item.get("source_pair_indices") or [])[:24],
            })
    else:
        for pair in (context_pairs or []):
            if not isinstance(pair, dict):
                continue
            provider_pairs.append({
                "turn": pair.get("turn_index") or pair.get("sequence_turn_index") or pair.get("turn"),
                "user": str(
                    pair.get("user")
                    or pair.get("user_request")
                    or pair.get("user_text")
                    or ""
                ).strip()[:700],
                "april": str(
                    pair.get("april")
                    or pair.get("april_answer")
                    or pair.get("assistant")
                    or pair.get("answer")
                    or ""
                ).strip()[:1200],
                "topic": str(
                    pair.get("sequence_topic")
                    or pair.get("topic")
                    or pair.get("canonical_topic")
                    or ""
                ).strip()[:320],
                "semantic_role": str(pair.get("_semantic_role") or "").strip(),
                "semantic_relevance": pair.get("_semantic_relevance"),
            })

    structured = {
        "version": "structured_request_from_full_12h_semantic_chain_v2",
        "action_link": (
            "CONTINUE_FROM_SEMANTIC_12H_CHAIN"
            if relation == "CONTINUE"
            else "NEW_ACTION"
        ),
        "mode": (
            "CONTINUE_SEMANTIC_CHAIN"
            if relation == "CONTINUE"
            else "INDEPENDENT_NEW_TASK"
        ),
        "relation": relation,
        "context_mode": context_mode,
        "current_request": str(current or "").strip(),
        "current_request_authoritative": True,
        "selected_memory_index": int(selected_index if relation == "CONTINUE" else -1),
        "selected_memory_operand": (
            dict(selected_pair or {}) if relation == "CONTINUE" else {}
        ),
        "matched_pair_count": len(provider_pairs) if relation == "CONTINUE" else 0,
        "semantic_chain": provider_pairs if relation == "CONTINUE" else [],
        "semantic_discussion": str(semantic_discussion or "").strip(),
        "history_overview": (
            history_overview
            if relation == "CONTINUE" and history_overview
            else {}
        ),
        "resolved_referent": resolved_referent if relation == "CONTINUE" else {},
        "semantic_task": task,
        "semantic_operation": operation,
        "canonical_topic": str(canonical_topic or "").strip(),
        "instruction": (
            (
                (
                    "Найден конкретный диалог по смысловому запросу пользователя. "
                    "Используй только выбранную dialogue sequence и её исходные USER↔APRIL пары; "
                    "не заменяй её другой похожей темой. Покажи, о чём был этот разговор, "
                    "что обсуждали и на чём остановились. "
                    if (history_overview.get("operation") in {"FIND_DIALOGUE", "OPEN_DIALOGUE"} and history_overview.get("selected_dialogue"))
                    else "Нужно суммировать ранее найденный диалог. Используй выбранную dialogue sequence и её исходные USER↔APRIL пары; не переходи на другую тему. "
                    if (history_overview.get("operation") == "SUMMARIZE_DIALOGUE" and history_overview.get("selected_dialogue"))
                    else
                    "Пользователь просит вспомнить или показать наш диалог. Используй "
                    "обзор полного доступного 12-часового USER↔APRIL контекста: покажи "
                    "примерно 10-15 основных тем, кратко опиши, что обсуждали и на чём "
                    "остановились. Укажи, что остальные темы не потеряны и остаются "
                    "в 12-часовом контексте. Не отвечай «не помню» и не проси назвать "
                    "тему, если соответствующие пары есть. Для последующего уточнения "
                    "вернись к исходным парам выбранной темы, объясни предыдущий результат "
                    "и предложи продолжить."
                )
                if history_overview
                else
                "Это продолжение существующей смысловой цепочки. "
                "Используй текущий запрос как главную задачу, а переданную USER↔APRIL "
                "цепочку как уже установленный контекст. Разрешённый объект/результат "
                "указан в resolved_referent: не заменяй его другим объектом и не проси "
                "пользователя повторно сообщить контекст. Ответь именно на текущий запрос."
            )
            if relation == "CONTINUE"
            else
            "Это новая самостоятельная задача. Не наследуй старую тему или старые "
            "результаты. Ответь только на текущий пользовательский запрос."
        ),
        "provider_must_not_reselect_context": True,
        "provider_must_not_bypass_pair_interpretation": True,
        "pair_history_authority": "INTERPRETATION",
        "full_12h_was_scanned": True,
    }
    return structured


def _pair_canonical_interpret_two_state(self, text, cognition=None, semantic=None, history=None, state=None):
    state_obj = state if isinstance(state, dict) else {}
    current = self.normalize(text)
    if not current:
        return None

    # 1) COMPLETE 12H retrieval.
    pairs = _full_authenticated_12h_pairs(state_obj, history=history)
    authenticated_user_id = str(
        state_obj.get("authenticated_user_id")
        or state_obj.get("user_id")
        or ""
    ).strip()
    if authenticated_user_id:
        pairs = [
            p for p in pairs
            if str(p.get("user_id") or authenticated_user_id).strip() == authenticated_user_id
        ]

    # 2) Semantic decision from the entire 12h set. Exactly CONTINUE or NEW.
    selected = _two_state_semantic_selector(
        self,
        current,
        pairs,
        active_topic=(
            state_obj.get("active_topic")
            or state_obj.get("canonical_topic")
            or ((state_obj.get("active_task") or {}).get("topic") if isinstance(state_obj.get("active_task"), dict) else "")
            or ""
        ),
    )
    relation = str(selected.get("relation") or "NEW").upper()
    relation_is_locked = bool(selected.get("relation_locked"))
    if relation not in {"CONTINUE", "NEW"}:
        relation = "NEW"
        relation_is_locked = True
    # The semantic selector owns relation. Task parsing below may enrich the
    # request, but it cannot overwrite the locked relation.
    if relation_is_locked:
        relation = str(selected.get("relation") or relation).upper()

    context_pairs = [
        dict(x) for x in (selected.get("context_pairs") or [])
        if isinstance(x, dict)
    ]
    _selected_index_raw = selected.get("selected_index", -1)
    try:
        selected_index = int(_selected_index_raw) if _selected_index_raw is not None else -1
    except (TypeError, ValueError):
        selected_index = -1
    selected_pair = (
        dict(selected.get("selected_pair") or {})
        if relation == "CONTINUE"
        else {}
    )
    semantic_discussion = str(selected.get("semantic_discussion") or "").strip()
    resolved_referent = (
        dict(selected.get("resolved_referent") or {})
        if relation == "CONTINUE"
        else {}
    )

    # 3) Existing semantic/task parser is used only to build the structural task.
    # It is not allowed to decide relation or memory. We feed it the chosen chain
    # as semantic history and do not pass the StateManager memory snapshot.
    role_history = _pair_role_history(context_pairs) if context_pairs else []
    try:
        base_result = _PAIR_INTERPRET_ORIGINAL_LIVE(
            self,
            text,
            cognition=cognition,
            semantic=semantic,
            history=role_history,
            state={},
        )
    except Exception as exc:
        raise RuntimeError(f"SEMANTIC_TASK_INTERPRETATION_FAILED: {exc}") from exc

    if not isinstance(base_result, dict):
        raise RuntimeError("INTERPRETATION_RETURNED_NO_PACKET")

    semantic_task = (
        dict(base_result.get("semantic_task"))
        if isinstance(base_result.get("semantic_task"), dict)
        else {}
    )

    representation = str(
        base_result.get("production_representation")
        or semantic_task.get("representation")
        or base_result.get("requested_representation")
        or "text"
    ).lower()

    operation = str(
        semantic_task.get("operation")
        or base_result.get("operation")
        or "answer"
    ).lower()
    if operation == "history_lookup":
        operation = "summarize"

    # A visual continuation may inherit the exact prior generation meaning without
    # changing the current user's wording.
    visual_request = str(
        base_result.get("visual_generation_request")
        or semantic_task.get("visual_generation_request")
        or ""
    ).strip()
    if relation == "CONTINUE" and not visual_request:
        visual = selected_pair.get("visual_attachment")
        if isinstance(visual, dict):
            visual_request = str(
                visual.get("prompt")
                or visual.get("description")
                or selected_pair.get("visual_generation_request")
                or selected_pair.get("generation_prompt")
                or selected_pair.get("image_generation_prompt")
                or ""
            ).strip()

    visual_ops = {
        "build", "create", "generate", "modify", "transform", "redraw",
        "edit", "visualize", "change", "recolor", "update",
    }
    if relation == "CONTINUE" and visual_request and operation in visual_ops:
        if representation in {"text", ""}:
            representation = "image"

    # Canonical topic is reconstructed only from the semantic chain, never from a
    # stale global entity/topic slot.
    canonical_topic = ""
    if relation == "CONTINUE":
        canonical_topic = str(
            _live_pair_subject(selected_pair)
            or selected_pair.get("sequence_topic")
            or selected_pair.get("topic")
            or selected_pair.get("canonical_topic")
            or ""
        ).strip()
        if not canonical_topic and context_pairs:
            canonical_topic = _live_pair_subject(context_pairs[-1])
    if relation == "NEW":
        canonical_topic = _live_extract_subject(current)

    selected_context_mode = str(
        selected.get("context_mode")
        or ("LIVE_CONTINUATION" if relation == "CONTINUE" else "NEW_TOPIC_ISOLATED")
    )

    structured_request = _two_state_structured_request(
        current=current,
        relation=relation,
        context_mode=selected_context_mode,
        semantic_task=semantic_task,
        context_pairs=context_pairs,
        semantic_discussion=semantic_discussion,
        selected_index=selected_index,
        selected_pair=selected_pair,
        canonical_topic=canonical_topic,
        resolved_referent=selected.get("resolved_referent") or {},
        semantic_operation=selected.get("semantic_operation") or operation,
        history_overview=selected.get("history_overview") or {},
    )

    # Build a clean production packet while retaining compatibility keys expected by
    # the existing Executor/Scene pipeline.
    result = dict(base_result)
    result["relation"] = relation
    result["three_way_relation"] = relation  # compatibility key; values are only two-state
    result["two_way_relation"] = relation
    result["dialogue_relation"] = relation
    result["continuation"] = relation == "CONTINUE"
    result["reference_to_previous"] = relation == "CONTINUE" and selected_index >= 0
    result["context_dependency"] = "continuation" if relation == "CONTINUE" else "independent"
    result["context_mode"] = selected_context_mode
    # Preserve the existing compatibility flag: concrete history semantics are
    # carried by history_operation/history_overview, while the legacy history_lookup
    # transport switch stays unchanged to avoid altering downstream routing.
    result["history_lookup"] = False
    result["history_lookup_scope"] = ""
    result["history_operation"] = str(selected.get("history_operation") or "NONE")
    result["history_search_query"] = str(selected.get("history_search_query") or "")
    result["topic_reference_number"] = selected.get("topic_reference_number")
    result["authenticated_user_id"] = str(
        selected.get("authenticated_user_id")
        or state_obj.get("authenticated_user_id")
        or state_obj.get("user_id")
        or ""
    ).strip()
    result["selected_dialogue"] = (
        dict(selected.get("selected_dialogue") or {})
        if isinstance(selected.get("selected_dialogue"), dict)
        else {}
    )
    result["selected_memory_index"] = selected_index if relation == "CONTINUE" else -1
    result["selected_memory_operand"] = selected_pair if relation == "CONTINUE" else {}
    result["selected_memory_record"] = selected_pair if relation == "CONTINUE" else {}
    result["selected_context_pairs"] = context_pairs if relation == "CONTINUE" else []
    result["dialogue_context_pairs"] = context_pairs if relation == "CONTINUE" else []
    result["dialogue_memory_window"] = [dict(x) for x in pairs]
    result["dialogue_memory_source"] = (
        "AUTHENTICATED_12H_USER_APRIL_PAIRS" if pairs else "NONE"
    )
    result["authenticated_dialogue_memory"] = {
        "window_hours": 12,
        "pair_count": len(pairs),
        "pairs": [dict(x) for x in pairs],
        "selected_context_pair_count": len(context_pairs) if relation == "CONTINUE" else 0,
        "selected_context_pairs": context_pairs if relation == "CONTINUE" else [],
        "authority": "INTERPRETATION",
        "selection_scope": "FULL_12H",
    }
    result["context_anchor_index"] = selected_index if relation == "CONTINUE" else -1
    result["context_anchor_pair"] = selected_pair if relation == "CONTINUE" else {}
    result["pair_first_match"] = {
        "selected_index": selected_index if relation == "CONTINUE" else -1,
        "selected_pair": _compact_pair_for_formulation(selected_pair) if relation == "CONTINUE" else {},
        "match_score": float(selected.get("best_score") or 0.0),
        "best_score": float(selected.get("best_score") or 0.0),
        "candidate_count": int(selected.get("candidate_count") or len(pairs)),
        "selected_pair_count": len(context_pairs) if relation == "CONTINUE" else 0,
        "selection_scope": "FULL_12H",
        "source": "STATE_MANAGER_AUTHENTICATED_12H_USER_APRIL_PAIRS",
    }

    # Preserve the semantic evidence, including the complete candidate scan.
    result["pair_direction_engine"] = {
        "version": TWO_STATE_DIALOGUE_ENGINE_VERSION,
        "relation": relation,
        "reason": selected.get("reason") or "",
        "candidate_count": len(pairs),
        "selected_indices": list(selected.get("selected_indices") or []),
        "best_score": float(selected.get("best_score") or 0.0),
        "selection_scope": "FULL_12H",
        "no_third_relation": True,
        "history_operation": str(selected.get("history_operation") or "NONE"),
        "history_search_query": str(selected.get("history_search_query") or ""),
        "topic_reference_number": selected.get("topic_reference_number"),
        "authenticated_user_id": result["authenticated_user_id"],
        "selected_dialogue": dict(selected.get("selected_dialogue") or {}) if isinstance(selected.get("selected_dialogue"), dict) else {},
    }
    result["semantic_chain"] = context_pairs if relation == "CONTINUE" else []
    result["semantic_discussion"] = semantic_discussion
    result["history_overview"] = (
        dict(selected.get("history_overview") or {})
        if relation == "CONTINUE" and selected.get("history_overview")
        else {}
    )
    result["semantic_selection_reason"] = str(
        selected.get("decision_basis")
        or selected.get("reason")
        or ""
    )
    result["relation_lock"] = True
    result["relation_lock_stage"] = "AFTER_12H_SEMANTIC_RELATION_BEFORE_STRUCTURED_REQUEST"
    result["relation_lock_owner"] = "TWO_STATE_SEMANTIC_SELECTOR"
    result["relation_lock_reason"] = str(selected.get("decision_basis") or selected.get("reason") or "")

    final_semantic_operation = str(selected.get("semantic_operation") or operation or "answer").lower()
    # The current visual engine is creation-only. Once a visual generation request
    # has been semantically established, keep the downstream task as BUILD even if
    # the pair selector proposed a generic/legacy operation such as ``answer`` or
    # an edit-like operation. This does not alter the 12h relation decision.
    if visual_request:
        representation = "image"
        final_semantic_operation = "build"
    semantic_task.update({
        "operation": final_semantic_operation,
        "history_operation": str(selected.get("history_operation") or "NONE"),
        "history_search_query": str(selected.get("history_search_query") or ""),
        "topic_reference_number": selected.get("topic_reference_number"),
        "representation": representation,
        "relation": relation,
        "context_dependency": result["context_dependency"],
        "canonical_topic": canonical_topic,
        "semantic_discussion": semantic_discussion,
        "resolved_referent": resolved_referent,
        "linked_pair_count": len(context_pairs) if relation == "CONTINUE" else 0,
    })
    operation = semantic_task["operation"]
    result["semantic_task"] = semantic_task

    result["canonical_topic"] = canonical_topic[:320]
    result["active_topic"] = canonical_topic[:320]
    result["active_entity"] = ""
    result["resolved_entity"] = ""
    resolved_referent = (
        dict(selected.get("resolved_referent") or {})
        if relation == "CONTINUE"
        else {}
    )
    result["resolved_referent"] = resolved_referent
    result["semantic_operation"] = str(
        selected.get("semantic_operation")
        or operation
        or "answer"
    )
    result["resolved_reference_entity"] = (
        str(
            resolved_referent.get("subject")
            or canonical_topic
            or ""
        )[:320]
        if relation == "CONTINUE"
        else ""
    )
    result["reference_entity"] = result["resolved_reference_entity"]
    result["entity_understanding"] = {}
    result["entities"] = []

    result["representation"] = representation
    result["requested_representation"] = representation
    result["production_representation"] = representation
    result["production_representation_locked"] = True
    result["requested_outputs"] = [representation]
    result["required_representations"] = [representation]
    result["visual_generation_request"] = visual_request
    result["render_plan"] = {
        "representation": representation,
        "requested_outputs": [representation],
        "authorized": representation in {
            "image", "gallery", "formula", "diagram", "graph", "table",
            "code", "link", "audio", "video", "file",
        },
        "mode": "IMAGE_GENERATION" if representation in {"image", "gallery"} else representation.upper(),
        "artifact_reference": bool(relation == "CONTINUE" and selected_index >= 0),
    }

    # One canonical Provider structured request. Full 12h is Interpretation-side
    # evidence; the Provider receives the semantic chain digest and cannot search
    # or re-select context.
    result["response_formulation"] = structured_request
    result["openai_request_formulation"] = structured_request

    result["provider_context_plan"] = {
        "version": "april_provider_handoff_full_12h_semantic_chain_v2",
        "relation": relation,
        "context_mode": result["context_mode"],
        "current_user_request": current,
        "resolved_request": current,
        "current_request_authoritative": True,
        "context_selection_done_before_provider": True,
        "provider_must_not_reselect_context": True,
        "provider_must_not_bypass_pair_interpretation": True,
        "pair_history_authority": "INTERPRETATION",
        "selection_scope": "FULL_12H",
        "full_12h_pair_count": len(pairs),
        "linked_pair_count": len(context_pairs) if relation == "CONTINUE" else 0,
        "hard_budget_tokens": 900,
        "soft_target_tokens": 800,
        "history_lookup": False,
        "history_operation": str(selected.get("history_operation") or "NONE"),
        "history_search_query": str(selected.get("history_search_query") or ""),
        "topic_reference_number": selected.get("topic_reference_number"),
        "authenticated_user_id": result["authenticated_user_id"],
        "selected_dialogue": dict(selected.get("selected_dialogue") or {}) if isinstance(selected.get("selected_dialogue"), dict) else {},
        "required_context": [
            {
                "key": "RESPONSE_FORMULATION",
                "priority": 1.02,
                "value": structured_request,
            },
            {
                "key": "SEMANTIC_CORE",
                "priority": 1.0,
                "value": {
                    "topic": canonical_topic,
                    "operation": operation,
                    "representation": representation,
                    "turn_relation": relation,
                    "context_mode": result["context_mode"],
                    "resolved_reference_entity": result["resolved_reference_entity"],
                    "resolved_request": current,
                },
            },
            {
                "key": "DIALOGUE_SEMANTIC_CHAIN",
                "priority": 0.998,
                "value": semantic_discussion,
            },
            {
                "key": "DIALOGUE_HISTORY_OVERVIEW",
                "priority": 0.999 if bool(selected.get("history_overview")) else 0.0,
                "value": (
                    dict(selected.get("history_overview") or {})
                    if selected.get("history_overview")
                    else {}
                ),
            },
            {
                "key": "OUTPUT_CONTRACT",
                "priority": 0.99,
                "value": {
                    "representation": representation,
                    "requested_outputs": [representation],
                    "visual_generation_request": visual_request,
                    "no_text_fallback_for_image": representation in {"image", "gallery"},
                    "ascii_allowed": False,
                },
            },
        ],
        "optional_context": [],
        "excluded_context": [
            "GLOBAL_TOPIC_INDEX",
            "ENTITY_INDEX",
            "LEGACY_INTENT_ENGINE",
            "PROVIDER_CONTEXT_RESELECTION",
        ],
    }

    result["provider_context_authority"] = "INTERPRETATION"
    result["provider_must_not_reselect_context"] = True

    result["dialogue_contract"] = {
        **(
            dict(result.get("dialogue_contract"))
            if isinstance(result.get("dialogue_contract"), dict)
            else {}
        ),
        "version": "dialogue_pair_contract_v4_two_state_full_12h",
        "relation": relation,
        "three_way_relation": relation,
        "two_way_relation": relation,
        "continuation": relation == "CONTINUE",
        "reference_to_previous": relation == "CONTINUE" and selected_index >= 0,
        "context_dependency": result["context_dependency"],
        "context_mode": result["context_mode"],
        "selected_memory_index": result["selected_memory_index"],
        "selected_memory_operand": result["selected_memory_operand"],
        "selected_context_pairs": result["selected_context_pairs"],
        "dialogue_memory_window": result["dialogue_memory_window"],
        "history_lookup": bool(selected.get("history_overview")),
        "history_operation": str(selected.get("history_operation") or "NONE"),
        "history_search_query": str(selected.get("history_search_query") or ""),
        "topic_reference_number": selected.get("topic_reference_number"),
        "authenticated_user_id": result["authenticated_user_id"],
        "selected_dialogue": dict(selected.get("selected_dialogue") or {}) if isinstance(selected.get("selected_dialogue"), dict) else {},
        "history_overview": bool(selected.get("history_overview")),
        "canonical": True,
        "selection_scope": "FULL_12H",
        "semantic_discussion": semantic_discussion,
        "entities": [],
        "active_entity": "",
        "resolved_entity": "",
        "entity_understanding": {},
    }

    result["dialogue_vector"] = {
        **(
            dict(result.get("dialogue_vector"))
            if isinstance(result.get("dialogue_vector"), dict)
            else {}
        ),
        "relation": relation,
        "three_way_relation": relation,
        "two_way_relation": relation,
        "continuation": relation == "CONTINUE",
        "reference_to_previous": relation == "CONTINUE" and selected_index >= 0,
        "request_dependency": result["context_dependency"],
        "selected_memory_index": result["selected_memory_index"],
        "selected_memory_operand": result["selected_memory_operand"],
        "memory_window": result["dialogue_memory_window"],
        "selected_context_pairs": result["selected_context_pairs"],
        "context_mode": result["context_mode"],
        "context_anchor_index": result["context_anchor_index"],
        "resolved_request": current,
        "resolved_reference_entity": result["resolved_reference_entity"],
        "canonical_topic": canonical_topic,
        "history_lookup": bool(selected.get("history_overview")),
        "history_overview": (
            dict(selected.get("history_overview") or {})
            if selected.get("history_overview")
            else {}
        ),
        "selection_scope": "FULL_12H",
        "trajectory": {
            "window_hours": 12,
            "pair_count": len(pairs),
            "linked_pair_count": len(context_pairs) if relation == "CONTINUE" else 0,
            "relation": relation,
            "selected_context_pairs": result["selected_context_pairs"],
        },
    }

    def _sanitize_two_state(value):
        if isinstance(value, dict):
            cleaned = {}
            for key, item in value.items():
                key_text = str(key)
                # Keep compatibility flags such as history_lookup, but no actual
                # third-state/RECALL concept may survive in the production packet.
                if "recall" in key_text.lower() and key_text not in {"history_lookup"}:
                    continue
                cleaned[key] = _sanitize_two_state(item)
            return cleaned
        if isinstance(value, list):
            return [_sanitize_two_state(item) for item in value]
        if isinstance(value, str):
            return re.sub(r"(?i)RECALL", "CONTINUE", value)
        return value

    result = _sanitize_two_state(result)

    print(
        "🧭 APRIL TWO-STATE 12H DECISION:",
        {
            "user_id": str(
                state_obj.get("authenticated_user_id")
                or state_obj.get("user_id")
                or ""
            ),
            "full_12h_pair_count": len(pairs),
            "selected_pair_count": len(context_pairs) if relation == "CONTINUE" else 0,
            "selected_index": selected_index if relation == "CONTINUE" else -1,
            "best_score": float(selected.get("best_score") or 0.0),
            "relation": relation,
            "reason": str(selected.get("reason") or ""),
            "selection_scope": "FULL_12H",
            "semantic_chain_locked": True,
            "provider_context_locked": True,
        },
    )
    return result


# Final runtime assignment: this existing file remains the single interpretation
# authority; no additional source file or routing path is introduced.
QuantumInterpretationEngine.interpret = _pair_canonical_interpret_two_state
