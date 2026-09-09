"""
APRIL — IMAGE SYSTEM / INTENT EVIDENCE + LOCAL NANO SCANNER + NANO PRINTER V4

Role:
    Lightweight semantic evidence layer.

This layer observes the request and emits signals.
It does NOT own the final route, room, provider, renderer, or execution decision.

This same module is the canonical image compatibility surface: local pixel/color/OCR/geometry scanning and local visual printing are exposed without OpenAI/Gemini/provider calls.

Decision owner:
    QUANTUM_PROCESSOR

Single route:
    USER -> INTENT EVIDENCE -> SEMANTIC/COGNITION ->
    QUANTUM PROCESSOR -> EXECUTION/ARTIFACT -> SCENE CONTRACT -> APRIL WEB
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, Optional


APRIL_FILE_ID = "APRIL_IMAGE_SYSTEM_INTENT_NANO_V4"
DECISION_OWNER = "QUANTUM_PROCESSOR"
INTENT_VERSION = "APRIL_INTENT_SYSTEM_QUANTUM_V1"

INPUT_MACHINE_CHANNEL = {
    "source": "executor_input_pipeline",
    "type": "intent_signal_input",
    "isolated": True,
}

OUTPUT_MACHINE_CHANNEL = {
    "target": "semantic_orchestration_pipeline",
    "type": "intent_signal_output",
    "isolated": True,
}

PATCH_LOG = []
MAX_PATCH_LOGS = 120


def safe_patch_log(msg: Any) -> None:
    """Machine telemetry only; never influences intent."""
    try:
        PATCH_LOG.append({
            "timestamp": time.time(),
            "message": str(msg),
            "file_id": APRIL_FILE_ID,
            "machine_only": True,
        })
        if len(PATCH_LOG) > MAX_PATCH_LOGS:
            del PATCH_LOG[:-MAX_PATCH_LOGS]
    except Exception:
        pass


def patch_intent_detect(text: str) -> str:
    safe_patch_log(f"INTENT EVIDENCE: {text[:60]}")
    return text


def patch_intent_future(*args: Any, **kwargs: Any) -> None:
    return None


def normalize(text: str) -> str:
    return str(text or "").lower().strip()


def contains_any(text: str, words: Iterable[str]) -> bool:
    value = normalize(text)
    return any(word in value for word in words)


CONTINUATION_WORDS = (
    "да", "ага", "ок", "окей", "давай", "вот", "примерно",
    "ближе", "уже лучше", "не то", "чуть темнее", "чуть ярче",
    "продолжай", "с этого", "поехали", "дальше", "теперь",
    "еще", "ещё", "в таком стиле", "оставь", "вот это",
    "ближе к этому", "продолжим", "вернемся", "вернёмся",
)

QUESTION_WORDS = (
    "как", "что", "почему", "зачем", "умеешь", "можешь",
    "где", "когда", "сколько", "какой", "какая", "какие",
)

EDIT_WORDS = (
    "добавь", "измени", "убери", "замени", "поменяй",
    "улучши", "подправь", "ярче", "темнее", "переделай",
    "исправь", "сделай темнее", "сделай ярче",
)

GENERATION_WORDS = (
    "создай изображение", "сгенерируй изображение",
    "нарисуй картинку", "создай картинку",
    "draw image", "generate image", "ultra realistic",
    "4k render", "cinematic render", "photorealistic",
    "realistic render",
)

LIGHT_VISUAL_WORDS = (
    "пример", "референс", "концепт", "идея", "вариант",
    "атмосфера", "примерно", "визуально", "как выглядит",
    "схема", "layout", "структура", "расположение",
)

RENDER_WORDS = (
    "график", "таблица", "формула", "diagram", "диаграмма",
    "схема", "layout", "структура", "grid", "line", "point",
    "arrow", "renderer", "пространство", "scene", "композиция",
    "canvas",
)

SPATIAL_WORDS = (
    "слева", "справа", "сверху", "снизу", "по центру",
    "размести", "поставь", "расположи", "между", "рядом",
)

WEB_WORDS = (
    "погода", "новости", "курс валют", "что происходит",
    "где находится", "карта", "маршрут", "рейс", "сейчас в",
    "такси", "отель", "навигация", "локация",
)

TEXT_WORDS = (
    "сообщение", "письмо", "текст", "шаблон", "ответ клиенту",
    "напиши письмо", "напиши сообщение",
)

LINK_WORDS = (
    "ссылка", "url", "линк", "короткая ссылка",
    "сократи ссылку", "short link",
)

EXPLORATION_WORDS = (
    "идея", "вариант", "примерно", "атмосфера", "может",
    "посмотрим", "подумаем", "как думаешь",
)

DISCUSSION_WORDS = ("обсудим", "поговорим", "как думаешь", "что думаешь")
REFLECTION_WORDS = ("почему", "объясни", "рассуждай", "размышляй")
SPACE_WORDS = ("пространство", "scene", "renderer", "график", "таблица", "формула")


def is_continuation(text: str) -> bool:
    t = normalize(text)
    if t in CONTINUATION_WORDS:
        return True
    return len(t) <= 36 and contains_any(t, CONTINUATION_WORDS)


def is_real_question(text: str) -> bool:
    t = normalize(text)
    if is_continuation(t) or len(t) <= 10:
        return False
    return "?" in t or contains_any(t, QUESTION_WORDS)


def is_edit_request(text: str) -> bool:
    return contains_any(text, EDIT_WORDS)


def is_generate_request(text: str) -> bool:
    return contains_any(text, GENERATION_WORDS)


def is_lightweight_visual_request(text: str) -> bool:
    return contains_any(text, LIGHT_VISUAL_WORDS)


def detect_renderer_subtype(text: str) -> str:
    t = normalize(text)
    if "график" in t:
        return "graph"
    if "формула" in t:
        return "formula"
    if "таблица" in t or "grid" in t:
        return "table"
    if "diagram" in t or "диаграмма" in t or "схема" in t:
        return "diagram"
    if any(x in t for x in ("layout", "пространство", "scene", "композиция")):
        return "scene"
    return "renderer"


def is_renderer_request(text: str) -> bool:
    return contains_any(text, RENDER_WORDS)


def is_spatial_request(text: str) -> bool:
    return contains_any(text, SPATIAL_WORDS)


def is_web_request(text: str) -> bool:
    return contains_any(text, WEB_WORDS)


def is_text_request(text: str) -> bool:
    return contains_any(text, TEXT_WORDS)


def is_link_request(text: str) -> bool:
    return contains_any(text, LINK_WORDS)


def is_exploration_request(text: str) -> bool:
    return contains_any(text, EXPLORATION_WORDS)


def is_discussion_request(text: str) -> bool:
    return contains_any(text, DISCUSSION_WORDS)


def is_reflection_request(text: str) -> bool:
    return contains_any(text, REFLECTION_WORDS)


def is_space_discussion_request(text: str) -> bool:
    return (
        contains_any(text, DISCUSSION_WORDS)
        and contains_any(text, SPACE_WORDS)
    )


def build_intent_result() -> Dict[str, Any]:
    """
    Canonical signal packet.

    All modality fields are soft evidence. The Quantum Processor is the only
    component allowed to arbitrate them into a final action.
    """
    return {
        "intent": "chat",
        "confidence": 0.5,
        "source": "default",

        "prefer_renderer": False,
        "prefer_lightweight": False,
        "prefer_guidance": False,
        "prefer_execution": False,
        "prefer_continuation": False,
        "prefer_web": False,

        "renderer_subtype": None,
        "lightweight_visual": False,
        "spatial_scene": False,
        "explicit_image_generation": False,

        "continuation": False,
        "trajectory_safe": True,
        "trajectory_priority": 0.5,

        "exploration": False,
        "discussion_intent": False,
        "reflection_intent": False,
        "space_discussion_intent": False,

        "avoid_heavy_generation": True,
        "avoid_hidden_escalation": True,
        "avoid_telegram_behavior": True,
        "provider_safe": True,

        "machine_only": True,
        "orchestration_ready": True,
        "renderer_first_safe": True,
        "continuity_preserved": True,

        "decision_owner": DECISION_OWNER,
        "provider_calls": 0,
        "parallel_route": False,
        "route_selection": "delegated",
        "renderer_selection": "delegated",
        "execution_selection": "delegated",
    }


def _apply_continuation(result: Dict[str, Any], state: Dict[str, Any]) -> bool:
    raw_text = normalize(result.get("_text", ""))
    # Do not let stale active_flow/visual_scene turn greetings and short social
    # questions into continuation evidence.
    if raw_text in {"привет", "приветик", "здравствуй", "здравствуйте", "добрый день", "добрый вечер", "доброе утро", "кто ты", "как тебя зовут", "как ти бязовут"}:
        return False

    if not is_continuation(result["_text"]):
        return False

    result["continuation"] = True
    result["prefer_continuation"] = True
    result["trajectory_priority"] = 0.9

    if state.get("active_flow"):
        result.update({
            "intent": "continuation",
            "confidence": 0.88,
            "source": "continuation",
        })
        return True

    if state.get("active_visual_scene"):
        result.update({
            "intent": "visual_continuation",
            "confidence": 0.84,
            "source": "visual_scene",
            "prefer_renderer": True,
        })
        return True

    return False


def detect_intent(text: str, state: Optional[dict] = None) -> Dict[str, Any]:
    """
    Produce intent evidence without becoming a hard router.

    Important:
        The order below is evidence collection, not architectural routing.
        The returned packet must be fused with cognition, semantic state,
        dialogue history and scene state by the Quantum Processor.
    """
    t = normalize(text)
    state = state if isinstance(state, dict) else {}

    result = build_intent_result()
    result["_text"] = t
    patch_intent_detect(t)

    # -------------------------------------------------
    # Continuity evidence
    # -------------------------------------------------
    if _apply_continuation(result, state):
        result.pop("_text", None)
        return result

    result["exploration"] = is_exploration_request(t)
    result["discussion_intent"] = is_discussion_request(t)
    result["reflection_intent"] = is_reflection_request(t)
    result["space_discussion_intent"] = is_space_discussion_request(t)

    if result["exploration"]:
        result["prefer_lightweight"] = True
        result["lightweight_visual"] = True
        result["trajectory_priority"] = max(result["trajectory_priority"], 0.72)

    if result["discussion_intent"] or result["reflection_intent"] or result["space_discussion_intent"]:
        result["prefer_guidance"] = True

    # -------------------------------------------------
    # Independent evidence signals
    # -------------------------------------------------
    # We deliberately do not return early here. A user request may contain
    # multiple simultaneous signals: e.g. a graph + explanation + web lookup.
    candidates = []

    if is_web_request(t):
        candidates.append(("web", 0.88, "web"))
        result["prefer_web"] = True

    if is_link_request(t):
        candidates.append(("link", 0.92, "link"))

    if is_edit_request(t):
        candidates.append(("edit", 0.88, "edit"))
        result["prefer_execution"] = True

    if is_spatial_request(t):
        candidates.append(("spatial", 0.84, "spatial"))
        result["spatial_scene"] = True
        result["prefer_renderer"] = True

    if is_renderer_request(t):
        candidates.append(("render", 0.88, "renderer"))
        result["prefer_renderer"] = True
        result["renderer_subtype"] = detect_renderer_subtype(t)

    if is_lightweight_visual_request(t):
        candidates.append(("lightweight_visual", 0.80, "lightweight_visual"))
        result["prefer_lightweight"] = True
        result["lightweight_visual"] = True

    if is_generate_request(t):
        candidates.append(("generate", 0.90, "generate"))
        result["explicit_image_generation"] = True
        result["avoid_heavy_generation"] = False

    if is_text_request(t):
        candidates.append(("text", 0.84, "text"))
        result["prefer_guidance"] = True

    if is_real_question(t):
        candidates.append(("question", 0.72, "question"))
        result["prefer_guidance"] = True

    # Choose a descriptive primary signal only. This is NOT the final action.
    if candidates:
        primary = max(candidates, key=lambda item: item[1])
        result["intent"], result["confidence"], result["source"] = primary
        result["candidate_signals"] = [
            {"intent": intent, "confidence": confidence, "source": source}
            for intent, confidence, source in candidates
        ]

    # -------------------------------------------------
    # Active-flow evidence
    # -------------------------------------------------
    active_flow = state.get("active_flow")
    if active_flow:
        result["continuation"] = True
        result["prefer_continuation"] = True
        result["trajectory_priority"] = max(result["trajectory_priority"], 0.74)

        flow_type = active_flow.get("type") if isinstance(active_flow, dict) else None
        result["active_flow_type"] = flow_type

        if flow_type in {
            "renderer_space", "visual_scene", "image_generate",
            "image_edit", "image", "math",
        }:
            result["trajectory_evidence"] = {
                "flow_type": flow_type,
                "preserve": True,
            }

    # -------------------------------------------------
    # Canonical metadata
    # -------------------------------------------------
    result["quantum_evidence"] = {
        "current_request": t,
        "candidate_signals": result.get("candidate_signals", []),
        "continuation": result["continuation"],
        "active_flow": active_flow or {},
        "active_visual_scene": state.get("active_visual_scene", {}),
        "trajectory_priority": result["trajectory_priority"],
    }

    result["decision_owner"] = DECISION_OWNER
    result["provider_calls"] = 0
    result["parallel_route"] = False
    result["route_selection"] = "delegated"
    result["renderer_selection"] = "delegated"
    result["execution_selection"] = "delegated"
    result.pop("_text", None)

    safe_patch_log(
        f"INTENT EVIDENCE READY: {result.get('intent')} / "
        f"{len(result.get('candidate_signals', []))} candidates"
    )
    return result

import asyncio
import hashlib
import math
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# Optional local acceleration / analysis libraries. None of these are required
# for import or basic scanning.
try:
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

try:
    import cv2 as _cv2
except Exception:  # pragma: no cover
    _cv2 = None

try:
    import pytesseract as _pytesseract
    from pytesseract import Output as _TESS_OUTPUT
except Exception:  # pragma: no cover
    _pytesseract = None
    _TESS_OUTPUT = None

try:
    from skimage.metrics import structural_similarity as _ssim
except Exception:  # pragma: no cover
    _ssim = None

try:
    from skimage import color as _skimage_color
except Exception:  # pragma: no cover
    _skimage_color = None

try:
    from scipy import ndimage as _ndi
except Exception:  # pragma: no cover
    _ndi = None

try:
    import shapely.geometry as _shapely_geometry
except Exception:  # pragma: no cover
    _shapely_geometry = None

try:
    import sympy as _sympy
except Exception:  # pragma: no cover
    _sympy = None

try:
    import networkx as _nx
except Exception:  # pragma: no cover
    _nx = None

try:
    import pandas as _pd
except Exception:  # pragma: no cover
    _pd = None

try:
    import imageio.v3 as _imageio
except Exception:  # pragma: no cover
    _imageio = None

_plt = None
_Axes3D = None

def _get_matplotlib():
    """Lazy-load matplotlib only for actual printer requests that need it."""
    global _plt, _Axes3D
    if _plt is not None:
        return _plt
    if not NANO_USE_OPTIONAL_HEAVY_IMAGE_LIBS:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        _plt = plt
        _Axes3D = Axes3D
        return _plt
    except Exception:
        return None


VERSION = "LOCAL_NANO_VISUAL_SCANNER_NANO_PRINTER_V7_MACROQUANTUM_128BIT_16CORE"
PROVIDER = "local"
MAX_OCR_ITEMS = 500
MAX_TEXT_CHARS = 16000
MAX_REGIONS = 100
MAX_LINES = 240
MAX_CONTOURS = 160
MAX_COLORS = 24
MAX_VECTOR_PRIMITIVES = 260
MAX_DIFF_REGIONS = 80

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# ---------------------------------------------------------------------------
# MACRO-QUANTUM / NANO SCANNER V7
# ---------------------------------------------------------------------------
# "128-bit" is an internal evidence fingerprint width, not a claim of
# physical quantum hardware. The scanner uses 16 parallel logical lanes over
# the same decoded pixel buffer and returns deterministic multiscale evidence.
NANO_SCANNER_VERSION = "NANO_SCANNER_128BIT_16CORE_MACROQUANTUM_V7"
NANO_SCANNER_BITS = 128
NANO_SCANNER_LOGICAL_CORES = 16
NANO_SCANNER_MAX_WORKERS = 16
NANO_PIXEL_LEVELS = (16, 32, 64)
NANO_MICROGRID = 4


def _visual_log(event: str, **data: Any) -> None:
    """Lightweight runtime telemetry for scanner/printer observation only."""
    try:
        print(
            f"[NANO-VISUAL] {event} "
            f"{json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)}",
            flush=True,
        )
    except Exception:
        pass


def _nano_hash_bytes(data: bytes) -> str:
    return hashlib.blake2b(data, digest_size=NANO_SCANNER_BITS // 8).hexdigest()


def _image_fingerprint(img: Image.Image) -> dict:
    """Deterministic 128-bit identity of the decoded RGB pixel stream."""
    try:
        raw = img.tobytes()
        digest = _nano_hash_bytes(raw)
    except Exception:
        digest = _nano_hash_bytes(f"{img.size}:{img.mode}".encode("utf-8"))
    return {
        "bits": NANO_SCANNER_BITS,
        "algorithm": "blake2b-128",
        "digest": digest,
        "resolution": [int(img.width), int(img.height)],
        "mode": img.mode,
    }


def _nano_pixel_pyramid(img: Image.Image) -> dict:
    """Multiscale pixel evidence: coarse whole-image + micro-pixel tiles.

    The scanner never attempts to transmit every source pixel downstream. It
    measures the image at several resolutions and emits deterministic tile
    descriptors plus a 128-bit digest for each level. High-detail regions are
    represented by 4x4 micro-samples inside selected tiles.
    """
    levels = {}
    for grid in NANO_PIXEL_LEVELS:
        small = img.resize((grid, grid), Image.Resampling.BILINEAR)
        px = list(small.getdata())
        total = max(1, len(px))
        mean = [sum(c[i] for c in px) / total for i in range(3)]
        variance = sum(
            ((0.2126*r + 0.7152*g + 0.0722*b) -
             (0.2126*mean[0] + 0.7152*mean[1] + 0.0722*mean[2])) ** 2
            for r, g, b in px
        ) / total
        levels[str(grid)] = {
            "grid": grid,
            "samples": grid * grid,
            "mean_rgb": [round(v, 2) for v in mean],
            "luma_std": round(math.sqrt(max(0.0, variance)) / 255.0, 6),
            "digest_128": _nano_hash_bytes(bytes(int(max(0, min(255, c))) for rgb in px for c in rgb)),
        }

    # Adaptive micro-pixel pass on a bounded 8x8 tile map. A tile is expanded
    # only when its local luma variation is above the image median.
    base_grid = 8
    thumb = img.resize((base_grid, base_grid), Image.Resampling.BILINEAR)
    vals = []
    for rgb in thumb.getdata():
        vals.append(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])
    median = sorted(vals)[len(vals)//2] if vals else 0.0
    adaptive = []
    for idx, value in enumerate(vals):
        if abs(value - median) < 22.0:
            continue
        gx, gy = idx % base_grid, idx // base_grid
        left = int(gx * img.width / base_grid)
        top = int(gy * img.height / base_grid)
        right = max(left + 1, int((gx + 1) * img.width / base_grid))
        bottom = max(top + 1, int((gy + 1) * img.height / base_grid))
        crop = img.crop((left, top, right, bottom))
        micro = crop.resize((NANO_MICROGRID, NANO_MICROGRID), Image.Resampling.BOX)
        micro_values = [list(rgb) for rgb in micro.getdata()]
        adaptive.append({
            "tile": [gx, gy],
            "bbox": [left, top, right - left, bottom - top],
            "luma_deviation": round(abs(value - median) / 255.0, 6),
            "micro_grid": NANO_MICROGRID,
            "micro_pixels": micro_values,
            "digest_128": _nano_hash_bytes(bytes(int(max(0, min(255, c))) for rgb in micro_values for c in rgb)),
        })
        if len(adaptive) >= 64:
            break

    return {
        "engine": "nano_pixel_pyramid_local",
        "levels": levels,
        "adaptive_micro_tiles": adaptive,
        "microgrid": NANO_MICROGRID,
        "pixel_domain": "decoded_rgb_pixels",
        "nano_domain": "adaptive_micro_pixel_tiles",
    }


def _parallel_local_scan(img: Image.Image, user_request: str, previous_path: Optional[str], request: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Run independent local scan engines across 16 logical lanes.

    The lanes are logical worker slots. Actual CPU parallelism is determined by
    the host and whether the underlying library releases the GIL.
    """
    tasks = {
        "visual": lambda: _pil_stats(img),
        "pixels": lambda: _pixel_scan(img),
        "nano_pixels": lambda: _nano_pixel_pyramid(img),
        "color": lambda: _color_scan(img),
        "ocr": lambda: _ocr_scan(img),
        "layout": lambda: _layout_scan(img),
        "components": lambda: _connected_components_scan(img),
        "geometry": lambda: _geometry_scan(img),
        "compare": lambda: _compare_images(img, previous_path),
    }
    results: Dict[str, Any] = {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=NANO_SCANNER_MAX_WORKERS, thread_name_prefix="april-nano") as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = {"available": False, "error": f"{name}_failed:{exc}"}
    results["parallel_elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
    results["logical_lanes"] = NANO_SCANNER_LOGICAL_CORES
    results["worker_slots"] = NANO_SCANNER_MAX_WORKERS
    return results


# Fast adaptive hot-path controls. Expensive secondary passes are disabled by
# default and run only when the first measurement is weak.
NANO_FAST_MODE = os.getenv("APRIL_NANO_FAST_MODE", "1").strip().lower() in {"1", "true", "yes", "on"}
NANO_OCR_MAX_PASSES = max(1, int(os.getenv("APRIL_NANO_OCR_MAX_PASSES", "2")))
NANO_OCR_UPSCALE = os.getenv("APRIL_NANO_OCR_UPSCALE", "1").strip().lower() in {"1", "true", "yes", "on"}
NANO_USE_OPTIONAL_HEAVY_IMAGE_LIBS = os.getenv("APRIL_NANO_USE_OPTIONAL_HEAVY_IMAGE_LIBS", "0").strip().lower() in {"1", "true", "yes", "on"}

URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\]\[()\"']+")
FORMULA_RE = re.compile(
    r"(?:"
    r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ]\s*[=≈≠<>≤≥]\s*[^.;]{1,180}"
    r"|\\(?:frac|sqrt|sum|int|alpha|beta|gamma|pi|Delta|theta|lambda|infty)\b"
    r"|\b\d+(?:[.,]\d+)?\s*[+\-*/×÷=<>≤≥]\s*[-+*/×÷=<>≤≥0-9A-Za-zА-Яа-яЁёЇїІіЄєҐґ()., ^]+"
    r")"
)
CODE_RE = re.compile(
    r"(?m)^(?:\s{2,}|\t+).*(?:[{}();:=]|\b(?:def|class|import|from|return|const|let|var|function|if|else|for|while|async|await|print|SELECT|FROM|WHERE)\b)"
)

EDIT_TERMS = (
    "исправ", "ошиб", "неправ", "помен", "измени", "убер", "добав",
    "замени", "передел", "сделай", "поправ", "что изменить", "что исправить",
    "помоги", "fix", "change", "remove", "add", "replace", "correct", "edit", "modify",
)
EXPLAIN_TERMS = (
    "что изображено", "что написано", "прочитай", "объясни", "разбери",
    "проанализируй", "что здесь", "что на скрине", "что на экране", "опиши",
    "объяснить", "описать", "explain", "describe", "read", "analyze",
)
CHANGE_TERMS = (
    "изменилось", "изменилось ли", "что изменилось", "сравни", "раньше",
    "теперь", "до этого", "после", "difference", "changed", "compare",
)
COLOR_TERMS = (
    "цвет", "цвета", "раскрас", "закрась", "перекрась", "цветной", "palette",
    "color", "recolor", "paint", "fill",
)
DRAW_TERMS = (
    "нарисуй", "рисуй", "схему", "диаграмму", "график", "рисунок", "фигуру",
    "отрисуй", "svg", "canvas", "draw", "diagram", "chart", "plot", "sketch",
)
THREED_TERMS = (
    "3d", "трехмер", "трёхмер", "объем", "объём", "перспектив", "куб", "цилиндр",
    "сфера", "depth", "mesh", "three-dimensional",
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _clip_text(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[:limit] + "…"


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    value = str(text or "").lower()
    return any(str(n).lower() in value for n in needles)


def _confidence(values: Sequence[float]) -> float:
    vals = [max(0.0, min(1.0, float(v))) for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _load_image(path: str) -> Optional[Image.Image]:
    try:
        with Image.open(path) as img:
            return img.convert("RGB")
    except Exception:
        return None


def _pil_stats(img: Image.Image) -> Dict[str, Any]:
    w, h = img.size
    gray = ImageOps.grayscale(img)
    thumb = gray.copy()
    thumb.thumbnail((480, 480))
    px = list(thumb.getdata())
    mean = sum(px) / max(1, len(px))
    variance = sum((p - mean) ** 2 for p in px) / max(1, len(px))
    contrast = math.sqrt(variance) / 255.0
    edge = ImageChops.difference(gray, gray.filter(ImageFilter.FIND_EDGES)).getbbox()
    return {
        "width": w,
        "height": h,
        "channels": 3,
        "pixel_count": w * h,
        "mean_luma": round(mean / 255.0, 4),
        "contrast": round(contrast, 4),
        "edge_presence": 0.0 if edge is None else 1.0,
        "orientation": "portrait" if h > w * 1.12 else ("landscape" if w > h * 1.12 else "square_like"),
        "aspect_ratio": round(w / max(1, h), 5),
    }


def _cv_array(img: Image.Image):
    if _cv2 is None or _np is None:
        return None
    try:
        return _cv2.cvtColor(_np.array(img), _cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def _sample_grid(img: Image.Image, grid: int = 24) -> List[Dict[str, Any]]:
    w, h = img.size
    px = img.load()
    out: List[Dict[str, Any]] = []
    for gy in range(grid):
        y = min(h - 1, int((gy + 0.5) * h / grid))
        for gx in range(grid):
            x = min(w - 1, int((gx + 0.5) * w / grid))
            r, g, b = px[x, y]
            out.append({"x": x, "y": y, "rgb": [int(r), int(g), int(b)]})
    return out


def _rgb_to_hsv_fallback(r: int, g: int, b: int) -> Tuple[float, float, float]:
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(rf, gf, bf), min(rf, gf, bf)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == rf:
        h = ((gf - bf) / d) % 6
    elif mx == gf:
        h = (bf - rf) / d + 2
    else:
        h = (rf - gf) / d + 4
    h /= 6.0
    s = 0.0 if mx == 0 else d / mx
    return h, s, mx


def _rgb_features(rgb: Sequence[int]) -> Dict[str, float]:
    r, g, b = [int(v) for v in rgb[:3]]
    h, s, v = _rgb_to_hsv_fallback(r, g, b)
    luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return {"h": round(h, 4), "s": round(s, 4), "v": round(v, 4), "luma": round(luma, 4)}


def _color_scan(img: Image.Image) -> Dict[str, Any]:
    # Quantize to keep the scan bounded and deterministic.
    small = img.copy()
    small.thumbnail((360, 360))
    quantized = small.quantize(colors=MAX_COLORS, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    counts = quantized.getcolors(maxcolors=MAX_COLORS * small.size[0] * small.size[1]) or []
    total = max(1, small.size[0] * small.size[1])
    colors: List[Dict[str, Any]] = []
    for count, idx in sorted(counts, reverse=True)[:MAX_COLORS]:
        base = idx * 3
        rgb = [int(palette[base + k]) if base + k < len(palette) else 0 for k in range(3)]
        features = _rgb_features(rgb)
        colors.append({
            "rgb": rgb,
            "hex": "#%02x%02x%02x" % tuple(rgb),
            "pixel_count": int(count),
            "ratio": round(count / total, 5),
            **features,
        })

    dominant = colors[0] if colors else {"rgb": [0, 0, 0], "hex": "#000000", "ratio": 0.0}
    high_sat = sum(c["ratio"] for c in colors if c.get("s", 0) >= 0.5)
    dark = sum(c["ratio"] for c in colors if c.get("v", 1) <= 0.25)
    light = sum(c["ratio"] for c in colors if c.get("v", 0) >= 0.8)
    grayscale = sum(c["ratio"] for c in colors if c.get("s", 1) <= 0.08)

    return {
        "engine": "pil_quantized_local",
        "dominant": dominant,
        "palette": colors,
        "palette_size": len(colors),
        "saturation_ratio": round(high_sat, 4),
        "dark_ratio": round(dark, 4),
        "light_ratio": round(light, 4),
        "grayscale_ratio": round(grayscale, 4),
        "mode_hint": "colorful" if high_sat >= 0.18 else ("grayscale_like" if grayscale >= 0.75 else "mixed"),
        "samples": _sample_grid(img, 16),
    }


def _pixel_scan(img: Image.Image) -> Dict[str, Any]:
    stats = _pil_stats(img)
    sample = _sample_grid(img, 20)
    border = 3
    if img.width > 2 * border and img.height > 2 * border:
        cropped = img.crop((border, border, img.width - border, img.height - border))
        border_diff = ImageChops.difference(img, ImageOps.expand(cropped, border=border, fill=(0, 0, 0))) if False else None
    return {
        "engine": "pil_pixel_local",
        "sample_grid": sample,
        "sample_count": len(sample),
        "pixel_count": stats["pixel_count"],
        "resolution": [stats["width"], stats["height"]],
        "channel_count": stats["channels"],
        "fine_detail_hint": round(min(1.0, stats["contrast"] * 1.4 + stats["edge_presence"] * 0.35), 4),
    }


def _ocr_scan(img: Image.Image) -> Dict[str, Any]:
    if _pytesseract is None or shutil.which("tesseract") is None:
        return {
            "text": "", "items": [], "confidence": 0.0,
            "engine": "unavailable", "languages": [], "available": False,
            "reason": "tesseract_unavailable",
        }

    try:
        installed = set(_pytesseract.get_languages(config=""))
    except Exception:
        installed = {"eng"}
    langs = [x for x in ("rus", "ukr", "eng") if x in installed]
    if not langs and "eng" in installed:
        langs = ["eng"]
    if not langs:
        return {
            "text": "", "items": [], "confidence": 0.0,
            "engine": "unavailable", "languages": [], "available": False,
            "reason": "no_ocr_languages",
        }

    w, h = img.size
    gray = ImageOps.grayscale(img)
    variants: List[Tuple[str, Image.Image, float]] = [("base", gray, 1.0)]

    # One fast base pass. A second pass is only created for low-confidence OCR.
    if NANO_OCR_UPSCALE and max(w, h) < 2600:
        scale = 1.6
        up = gray.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        variants.append(("upscaled", up, scale))

    if NANO_FAST_MODE:
        variants = variants[:NANO_OCR_MAX_PASSES]
    else:
        variants.append(("contrast", ImageEnhance.Contrast(gray).enhance(1.35), 1.0))
        variants = variants[:max(2, NANO_OCR_MAX_PASSES)]

    lang_arg = "+".join(langs)
    best_items: List[Dict[str, Any]] = []
    best_text = ""
    best_conf = 0.0

    for pass_index, (name, variant, factor) in enumerate(variants):
        try:
            data = _pytesseract.image_to_data(
                variant,
                lang=lang_arg,
                config="--oem 3 --psm 11",
                output_type=_TESS_OUTPUT.DICT,
            )
        except Exception:
            continue
        items: List[Dict[str, Any]] = []
        confs: List[float] = []
        fields = data.get("text", [])
        for i, raw in enumerate(fields):
            txt = _normalize_text(raw)
            if not txt:
                continue
            conf = _safe_float(data.get("conf", ["-1"] * len(fields))[i], -1)
            if conf < 0:
                continue
            x = _safe_int(data.get("left", [0] * len(fields))[i]) / factor
            y = _safe_int(data.get("top", [0] * len(fields))[i]) / factor
            ww = _safe_int(data.get("width", [0] * len(fields))[i]) / factor
            hh = _safe_int(data.get("height", [0] * len(fields))[i]) / factor
            c = max(0.0, min(1.0, conf / 100.0))
            items.append({
                "text": txt,
                "confidence": round(c, 4),
                "bbox": [round(x), round(y), round(ww), round(hh)],
                "block": _safe_int(data.get("block_num", [0] * len(fields))[i]),
                "paragraph": _safe_int(data.get("par_num", [0] * len(fields))[i]),
                "line": _safe_int(data.get("line_num", [0] * len(fields))[i]),
            })
            confs.append(c)
        text = _normalize_text(" ".join(x["text"] for x in items))
        confidence = _confidence(confs)
        # Favor useful text and confidence, not simply the number of OCR boxes.
        score = confidence * 1.7 + min(1.0, len(text) / 800.0)
        if score > (best_conf * 1.7 + min(1.0, len(best_text) / 800.0)):
            best_items, best_text, best_conf = items, text, confidence

        # Once OCR is already good enough, do not spend time on secondary passes.
        if pass_index == 0 and best_conf >= 0.72 and len(best_text) >= 12:
            break

    best_items.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    best_items = best_items[:MAX_OCR_ITEMS]
    return {
        "text": _clip_text(best_text),
        "items": best_items,
        "confidence": round(best_conf, 4),
        "engine": "tesseract_local_adaptive",
        "languages": langs,
        "available": True,
        "passes_used": min(len(variants), NANO_OCR_MAX_PASSES),
        "reason": None,
    }

def _layout_scan(img: Image.Image) -> Dict[str, Any]:
    arr = _cv_array(img)
    if arr is None:
        return {"regions": [], "grid_hint": False, "engine": "pil_fallback", "confidence": 0.15}

    gray = _cv2.cvtColor(arr, _cv2.COLOR_BGR2GRAY)
    blur = _cv2.GaussianBlur(gray, (5, 5), 0)
    edges = _cv2.Canny(blur, 60, 160)
    contours, _ = _cv2.findContours(edges, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape[:2]
    regions: List[Dict[str, Any]] = []
    for contour in contours:
        x, y, rw, rh = _cv2.boundingRect(contour)
        area = rw * rh
        if area < max(160, int(w * h * 0.00025)) or rw < 18 or rh < 12:
            continue
        ratio = rw / max(1, rh)
        fill = float(_cv2.contourArea(contour)) / max(1.0, float(area))
        perimeter = float(_cv2.arcLength(contour, True))
        approx = _cv2.approxPolyDP(contour, max(2.0, 0.015 * perimeter), True)
        regions.append({
            "bbox": [int(x), int(y), int(rw), int(rh)],
            "area": int(area),
            "aspect_ratio": round(float(ratio), 4),
            "fill_ratio": round(fill, 4),
            "vertices_hint": int(len(approx)),
            "kind": "wide_region" if ratio >= 3.2 else ("tall_region" if ratio <= 0.33 else "region"),
        })
    regions.sort(key=lambda r: r["area"], reverse=True)
    regions = regions[:MAX_REGIONS]

    bw = _cv2.threshold(gray, 0, 255, _cv2.THRESH_BINARY_INV + _cv2.THRESH_OTSU)[1]
    horizontal = _cv2.morphologyEx(bw, _cv2.MORPH_OPEN, _cv2.getStructuringElement(_cv2.MORPH_RECT, (max(12, w // 40), 1)))
    vertical = _cv2.morphologyEx(bw, _cv2.MORPH_OPEN, _cv2.getStructuringElement(_cv2.MORPH_RECT, (1, max(12, h // 40))))
    h_count = int(_cv2.countNonZero(horizontal))
    v_count = int(_cv2.countNonZero(vertical))
    grid_hint = h_count > w * 5 and v_count > h * 5
    return {
        "regions": regions,
        "horizontal_structure_pixels": h_count,
        "vertical_structure_pixels": v_count,
        "grid_hint": bool(grid_hint),
        "engine": "opencv_local",
        "confidence": 0.80,
    }


def _connected_components_scan(img: Image.Image) -> Dict[str, Any]:
    arr = _cv_array(img)
    if arr is None:
        return {"available": False, "components": [], "count": 0, "confidence": 0.0, "engine": "unavailable"}
    gray = _cv2.cvtColor(arr, _cv2.COLOR_BGR2GRAY)
    bw = _cv2.threshold(gray, 0, 255, _cv2.THRESH_BINARY_INV + _cv2.THRESH_OTSU)[1]
    if _cv2 is not None:
        n, labels, stats, centroids = _cv2.connectedComponentsWithStats(bw, 8)
    else:
        return {"available": False, "components": [], "count": 0, "confidence": 0.0, "engine": "unavailable"}
    h, w = gray.shape[:2]
    comps: List[Dict[str, Any]] = []
    for i in range(1, n):
        x, y, rw, rh, area = [int(v) for v in stats[i]]
        if area < max(8, int(w * h * 0.00001)):
            continue
        cx, cy = [float(v) for v in centroids[i]]
        comps.append({"bbox": [x, y, rw, rh], "area": area, "centroid": [round(cx, 2), round(cy, 2)]})
    comps.sort(key=lambda c: c["area"], reverse=True)
    return {
        "available": True,
        "components": comps[:MAX_REGIONS],
        "count": len(comps),
        "foreground_ratio": round(float(_cv2.countNonZero(bw)) / max(1, w * h), 5),
        "confidence": 0.74,
        "engine": "opencv_connected_components",
    }


def _geometry_scan(img: Image.Image) -> Dict[str, Any]:
    arr = _cv_array(img)
    if arr is None:
        return {
            "engine": "pil_fallback", "line_count": 0, "graph_confidence": 0.0,
            "diagram_confidence": 0.0, "circle_count": 0, "contour_count": 0,
            "lines": [], "primitives": [],
        }

    gray = _cv2.cvtColor(arr, _cv2.COLOR_BGR2GRAY)
    edges = _cv2.Canny(gray, 50, 170)
    minimum = min(gray.shape[:2])
    lines = _cv2.HoughLinesP(
        edges, 1, math.pi / 180,
        threshold=max(22, minimum // 30),
        minLineLength=max(22, minimum // 18),
        maxLineGap=14,
    )
    line_items: List[Dict[str, Any]] = []
    if lines is not None:
        for line in lines[:MAX_LINES]:
            # OpenCV may return HoughLinesP rows as (1, 4) or (4,).
            # In the latter case line[0] is a numpy.int32 scalar and is
            # not iterable. Flatten the row before unpacking.
            try:
                if _np is not None:
                    coords = _np.asarray(line).reshape(-1).tolist()
                else:
                    coords = list(line)
            except Exception:
                continue
            if len(coords) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in coords[:4]]
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            angle = math.degrees(math.atan2(dy, dx))
            line_items.append({
                "points": [x1, y1, x2, y2],
                "length": round(length, 2),
                "angle": round(angle, 2),
                "orientation": "horizontal" if abs(angle) < 8 else ("vertical" if abs(abs(angle) - 90) < 8 else "diagonal"),
            })

    h, w = gray.shape[:2]
    long_h = sum(1 for x in line_items if abs(x["angle"]) < 8 and x["length"] > w * 0.12)
    long_v = sum(1 for x in line_items if abs(abs(x["angle"]) - 90) < 8 and x["length"] > h * 0.12)
    diagonal = sum(1 for x in line_items if x["orientation"] == "diagonal" and x["length"] > min(w, h) * 0.10)

    try:
        circles = _cv2.HoughCircles(
            gray, _cv2.HOUGH_GRADIENT, dp=1.2,
            minDist=max(18, min(h, w) // 30), param1=100, param2=35,
            minRadius=6, maxRadius=max(8, min(h, w) // 6),
        )
        if circles is None:
            circle_count = 0
        else:
            try:
                circle_rows = _np.asarray(circles).reshape(-1, 3) if _np is not None else circles[0]
                circle_count = min(len(circle_rows), 120)
            except Exception:
                circle_count = 0
    except Exception:
        circle_count = 0

    contours, _ = _cv2.findContours(edges, _cv2.RETR_LIST, _cv2.CHAIN_APPROX_SIMPLE)
    primitive_items: List[Dict[str, Any]] = []
    for contour in contours[:MAX_CONTOURS]:
        perimeter = float(_cv2.arcLength(contour, True))
        if perimeter < 20:
            continue
        approx = _cv2.approxPolyDP(contour, max(2.0, 0.018 * perimeter), True)
        x, y, rw, rh = _cv2.boundingRect(approx)
        area = float(_cv2.contourArea(contour))
        if rw < 10 or rh < 10:
            continue
        primitive_items.append({
            "bbox": [int(x), int(y), int(rw), int(rh)],
            "vertices": int(len(approx)),
            "area": round(area, 2),
            "kind": "triangle" if len(approx) == 3 else ("rectangle_like" if 4 <= len(approx) <= 5 else ("polygon" if len(approx) <= 12 else "freeform")),
        })
    primitive_items.sort(key=lambda p: p["area"], reverse=True)
    primitive_items = primitive_items[:MAX_CONTOURS]

    graph_score = min(1.0, 0.18 * min(long_h, 5) + 0.18 * min(long_v, 5) + 0.05 * min(circle_count, 6) + 0.05 * min(diagonal, 6))
    diagram_score = min(1.0, 0.010 * min(len(line_items), 80) + 0.035 * min(circle_count, 8) + 0.010 * min(len(primitive_items), 40))

    perspective_pairs = 0
    angles = [x["angle"] for x in line_items if x["orientation"] != "horizontal" and x["orientation"] != "vertical"]
    if len(angles) >= 4:
        spread = max(angles) - min(angles)
        if spread > 18:
            perspective_pairs += 1

    return {
        "engine": "opencv_local",
        "line_count": len(line_items),
        "lines": line_items,
        "horizontal_axis_candidates": long_h,
        "vertical_axis_candidates": long_v,
        "diagonal_candidates": diagonal,
        "circle_count": int(circle_count),
        "contour_count": len(primitive_items),
        "primitives": primitive_items,
        "graph_confidence": round(graph_score, 4),
        "diagram_confidence": round(diagram_score, 4),
        "perspective_hint": bool(perspective_pairs),
    }


def _table_scan(layout: Dict[str, Any], image_size: Tuple[int, int]) -> Dict[str, Any]:
    w, h = image_size
    candidates: List[Dict[str, Any]] = []
    for region in layout.get("regions", []):
        x, y, rw, rh = region["bbox"]
        ratio = rw / max(1, rh)
        if layout.get("grid_hint") and rw > w * 0.25 and rh > h * 0.06:
            candidates.append({"bbox": region["bbox"], "confidence": 0.80, "reason": "grid_geometry"})
        elif 1.3 <= ratio <= 12 and rw > w * 0.35 and rh > h * 0.08 and region.get("fill_ratio", 0) < 0.85:
            candidates.append({"bbox": region["bbox"], "confidence": 0.42, "reason": "rectangular_region"})
    return {
        "detected": bool(candidates),
        "confidence": max((c["confidence"] for c in candidates), default=0.0),
        "candidates": candidates[:20],
    }


def _text_semantics(text: str) -> Dict[str, Any]:
    text = _normalize_text(text)
    urls = [u.rstrip(".,;:!?)]}") for u in URL_RE.findall(text)]
    formulas: List[str] = []
    for m in FORMULA_RE.finditer(text):
        value = _normalize_text(m.group(0))
        if len(value) >= 3 and value not in formulas:
            formulas.append(value)
    codes: List[str] = []
    for m in CODE_RE.findall(text):
        value = m.strip()
        if value and value not in codes:
            codes.append(value)
    symbolic_math_count = 0
    if text:
        symbolic_math_count = len(re.findall(r"(?:<=|>=|!=|==|[∑∫√≈≠≤≥∞π])", text))
    sympy_parseable: List[str] = []
    if _sympy is not None:
        for candidate in formulas[:30]:
            try:
                expr = candidate.replace("×", "*").replace("÷", "/").replace("^", "**")
                _sympy.sympify(expr.split("=", 1)[-1].strip(), evaluate=False)
                sympy_parseable.append(candidate)
            except Exception:
                pass
    return {
        "urls": urls[:100],
        "formula_candidates": formulas[:100],
        "code_candidates": codes[:100],
        "has_math_evidence": bool(formulas) or symbolic_math_count > 0,
        "has_code_evidence": bool(codes),
        "has_link_evidence": bool(urls),
        "sympy_parseable_formulas": sympy_parseable,
        "symbolic_math_count": symbolic_math_count,
        "token_count": len(text.split()),
        "text_length": len(text),
        "language_evidence": {
            "cyrillic": bool(re.search(r"[А-Яа-яЁёЇїІіЄєҐґ]", text)),
            "latin": bool(re.search(r"[A-Za-z]", text)),
        },
    }


def _vector_plan(geometry: Dict[str, Any], ocr: Dict[str, Any], color: Dict[str, Any], image_size: Tuple[int, int]) -> Dict[str, Any]:
    """Return editable 2D primitives, not a rendered image."""
    primitives: List[Dict[str, Any]] = []
    for line in geometry.get("lines", [])[:MAX_VECTOR_PRIMITIVES]:
        primitives.append({
            "type": "line",
            "points": line.get("points"),
            "angle": line.get("angle"),
            "length": line.get("length"),
        })
    for p in geometry.get("primitives", [])[:MAX_VECTOR_PRIMITIVES - len(primitives)]:
        primitives.append({
            "type": p.get("kind", "polygon"),
            "bbox": p.get("bbox"),
            "vertices": p.get("vertices"),
            "area": p.get("area"),
        })
    text_objects = []
    for item in ocr.get("items", [])[:200]:
        text_objects.append({"type": "text", "text": item.get("text"), "bbox": item.get("bbox"), "confidence": item.get("confidence")})
    return {
        "available": bool(primitives or text_objects),
        "canvas": {"width": int(image_size[0]), "height": int(image_size[1])},
        "primitives": primitives[:MAX_VECTOR_PRIMITIVES],
        "text_objects": text_objects,
        "palette": color.get("palette", [])[:MAX_COLORS],
        "format_hints": ["svg", "canvas2d", "json_scene"],
        "editable": True,
        "note": "Evidence-based vectorization; not pixel-perfect tracing.",
    }


def _recolor_plan(img: Image.Image, color: Dict[str, Any], request: Dict[str, Any]) -> Dict[str, Any]:
    asked = request.get("asks_color_change", False)
    palette = color.get("palette", [])[:MAX_COLORS]
    regions: List[Dict[str, Any]] = []
    # Color regions are represented by palette classes. Exact pixel masks can be
    # built later by the editor from this stable evidence packet.
    for idx, entry in enumerate(palette):
        regions.append({
            "region_id": f"color_{idx}",
            "color": entry.get("hex"),
            "rgb": entry.get("rgb"),
            "coverage": entry.get("ratio", 0.0),
            "editable": True,
        })
    return {
        "requested": bool(asked),
        "available": bool(regions),
        "strategy": "palette_region_replacement",
        "source_palette": regions,
        "target_color": request.get("requested_color"),
        "requires_exact_mask": True,
        "safe_to_execute": False,
        "execution_owner": "QUANTUM_PROCESSOR",
    }


def _pseudo_3d_scan(img: Image.Image, geometry: Dict[str, Any], user_request: str) -> Dict[str, Any]:
    diagonal = int(geometry.get("diagonal_candidates", 0))
    perspective = bool(geometry.get("perspective_hint"))
    circles = int(geometry.get("circle_count", 0))
    requested = _contains_any(user_request, THREED_TERMS)
    score = min(1.0, (0.12 * min(diagonal, 6)) + (0.35 if perspective else 0.0) + (0.05 * min(circles, 4)))
    return {
        "evidence_only": True,
        "requested": requested,
        "perspective_hint": perspective,
        "diagonal_structure": diagonal,
        "circular_volume_hint": circles > 0,
        "confidence": round(score, 4),
        "capabilities": ["depth_hint", "perspective_evidence", "extrusion_candidate"],
        "actual_3d_model_built": False,
        "note": "This is local 2D evidence for future 3D reconstruction; it is not a full VLM or 3D model.",
    }


def _request_evidence(user_request: str) -> Dict[str, Any]:
    t = _normalize_text(user_request)
    low = t.lower()
    asks_explain = _contains_any(low, EXPLAIN_TERMS)
    asks_edit = _contains_any(low, EDIT_TERMS)
    asks_compare = _contains_any(low, CHANGE_TERMS)
    asks_color = _contains_any(low, COLOR_TERMS)
    asks_draw = _contains_any(low, DRAW_TERMS)
    requested_color = None
    color_patterns = [
        r"(?:в|на)\s+(?:цвет|цветом)\s+([a-zа-яё]+)",
        r"(?:перекрась|закрась|сделай)\s+[^.]{0,80}\s+(?:в|на)\s+([a-zа-яё]+)",
        r"(?:color|recolor)\s+[^.]{0,80}\s+(?:to|into)\s+([a-z]+)",
    ]
    for pattern in color_patterns:
        m = re.search(pattern, low, flags=re.IGNORECASE)
        if m:
            requested_color = _normalize_text(m.group(1))[:60]
            break
    requested_changes: List[Dict[str, Any]] = []
    patterns = [
        ("add", r"(?:добав(?:ить|ь)|add)\s+(.{1,180})"),
        ("remove", r"(?:убер(?:и|ем)|удал(?:ить|и)|remove)\s+(.{1,180})"),
        ("replace", r"(?:замен(?:ить|и)|replace)\s+(.{1,180})"),
        ("fix", r"(?:исправ(?:ить|ь)|поправ(?:ить|ь)|fix|correct)\s+(.{1,180})"),
        ("change", r"(?:измен(?:ить|и)|передел(?:ать|ай)|change|modify|edit)\s+(.{1,180})"),
    ]
    for action, pattern in patterns:
        for m in re.finditer(pattern, low, flags=re.IGNORECASE):
            requested_changes.append({"action": action, "target_text": _normalize_text(m.group(1))[:260]})
    return {
        "request_present": bool(t),
        "asks_explanation": bool(asks_explain),
        "asks_edit_or_fix": bool(asks_edit),
        "asks_change_comparison": bool(asks_compare),
        "asks_color_change": bool(asks_color),
        "asks_drawing": bool(asks_draw),
        "requested_color": requested_color,
        "requested_changes": requested_changes,
    }


def _looks_like_screenshot(img: Image.Image, ocr: Dict[str, Any], layout: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    w, h = img.size
    reasons: List[str] = []
    score = 0.0
    if h > w * 1.35:
        score += 0.25; reasons.append("portrait_mobile_like")
    if len(ocr.get("items", [])) >= 8:
        score += 0.28; reasons.append("many_text_regions")
    if len(layout.get("regions", [])) >= 5:
        score += 0.20; reasons.append("interface_like_regions")
    if len(ocr.get("items", [])) >= 15:
        score += 0.10; reasons.append("dense_ui_text")
    if _contains_any(ocr.get("text", "").lower(), ("deploy logs", "network logs", "build logs", "settings", "production", "browser", "terminal", "console")):
        score += 0.20; reasons.append("ui_keyword_evidence")
    return score >= 0.45, round(min(1.0, score), 4), reasons


def _build_summary(visual: Dict[str, Any], ocr: Dict[str, Any], semantics: Dict[str, Any], tables: Dict[str, Any], geometry: Dict[str, Any], compare: Dict[str, Any], request: Dict[str, Any], screenshot_score: float, color: Dict[str, Any]) -> Dict[str, Any]:
    objects: List[Dict[str, Any]] = []
    if ocr.get("text"):
        objects.append({"type": "text", "confidence": ocr.get("confidence", 0.0), "evidence": "ocr"})
    if tables.get("detected"):
        objects.append({"type": "table", "confidence": tables.get("confidence", 0.0), "evidence": "grid_geometry"})
    if geometry.get("graph_confidence", 0.0) >= 0.45:
        objects.append({"type": "graph", "confidence": geometry.get("graph_confidence", 0.0), "evidence": "axis_geometry"})
    if geometry.get("diagram_confidence", 0.0) >= 0.55:
        objects.append({"type": "diagram", "confidence": geometry.get("diagram_confidence", 0.0), "evidence": "shape_line_geometry"})
    if semantics.get("has_math_evidence"):
        objects.append({"type": "formula", "confidence": 0.66, "evidence": "ocr_math_pattern"})
    if semantics.get("has_code_evidence"):
        objects.append({"type": "code", "confidence": 0.66, "evidence": "ocr_code_pattern"})
    if semantics.get("has_link_evidence"):
        objects.append({"type": "link", "confidence": 0.98, "evidence": "ocr_url_pattern"})
    if color.get("mode_hint") in {"colorful", "mixed"}:
        objects.append({"type": "color_structure", "confidence": 0.72, "evidence": "palette_scan"})

    issues: List[Dict[str, Any]] = []
    if request.get("requested_changes"):
        for item in request["requested_changes"]:
            issues.append({"type": "requested_change", "action": item["action"], "target": item["target_text"], "confidence": 0.82, "evidence": "user_request"})
    if request.get("asks_change_comparison") and compare.get("available") and compare.get("changed"):
        issues.append({"type": "change_detected", "confidence": round(1.0 - float(compare.get("similarity", 0.0)), 4), "evidence": compare.get("difference_ratio")})

    desc: List[str] = ["похоже на скриншот интерфейса" if screenshot_score >= 0.45 else "изображение"]
    if ocr.get("text"):
        desc.append(f"распознан текст ({len(ocr.get('items', []))} фрагментов)")
    if tables.get("detected"):
        desc.append("есть табличная структура")
    if geometry.get("graph_confidence", 0.0) >= 0.45:
        desc.append("есть признаки графика")
    if geometry.get("diagram_confidence", 0.0) >= 0.55:
        desc.append("есть признаки схемы/диаграммы")
    if semantics.get("has_math_evidence"):
        desc.append("есть математические выражения")
    if semantics.get("has_code_evidence"):
        desc.append("есть признаки кода")
    if semantics.get("has_link_evidence"):
        desc.append("есть ссылки")
    if color.get("palette"):
        desc.append("считана цветовая палитра")

    mode = "observe"
    if request.get("asks_edit_or_fix"):
        mode = "explain_and_fix"
    elif request.get("asks_color_change"):
        mode = "recolor_assist"
    elif request.get("asks_drawing"):
        mode = "draw_assist"
    elif request.get("asks_change_comparison"):
        mode = "compare"
    elif request.get("asks_explanation"):
        mode = "explain"

    return {
        "description": ", ".join(desc) + ".",
        "objects": objects,
        "issues": issues,
        "help_mode": mode,
    }


def _difference_regions(current: Image.Image, previous: Image.Image, threshold: int = 22) -> List[Dict[str, Any]]:
    size = (512, 512)
    a = ImageOps.grayscale(current).resize(size, Image.Resampling.BILINEAR)
    b = ImageOps.grayscale(previous).resize(size, Image.Resampling.BILINEAR)
    diff = ImageChops.difference(a, b)
    mask = diff.point(lambda v: 255 if v >= threshold else 0)
    if _cv2 is not None and _np is not None:
        arr = _np.array(mask)
        kernel = _np.ones((5, 5), _np.uint8)
        arr = _cv2.morphologyEx(arr, _cv2.MORPH_OPEN, kernel)
        arr = _cv2.morphologyEx(arr, _cv2.MORPH_CLOSE, kernel)
        contours, _ = _cv2.findContours(arr, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE)
        sx, sy = current.width / size[0], current.height / size[1]
        boxes: List[Dict[str, Any]] = []
        for contour in contours[:MAX_DIFF_REGIONS]:
            x, y, w, h = _cv2.boundingRect(contour)
            area = w * h
            if area < 30:
                continue
            boxes.append({
                "bbox": [round(x * sx), round(y * sy), round(w * sx), round(h * sy)],
                "area_ratio": round(area / (size[0] * size[1]), 6),
                "confidence": round(min(1.0, 0.55 + area / (size[0] * size[1]) * 4.0), 4),
            })
        boxes.sort(key=lambda x: x["area_ratio"], reverse=True)
        return boxes
    bbox = mask.getbbox()
    return [] if bbox is None else [{"bbox": list(bbox), "area_ratio": 0.0, "confidence": 0.5}]


def _compare_images(current: Image.Image, previous_path: Optional[str]) -> Dict[str, Any]:
    if not previous_path or not os.path.exists(previous_path):
        return {"available": False, "changed": False, "similarity": None, "difference_ratio": None, "regions": [], "reason": "previous_image_not_supplied"}
    previous = _load_image(previous_path)
    if previous is None:
        return {"available": False, "changed": False, "similarity": None, "difference_ratio": None, "regions": [], "reason": "previous_image_unreadable"}

    size = (512, 512)
    a_gray = ImageOps.grayscale(current).resize(size, Image.Resampling.BILINEAR)
    b_gray = ImageOps.grayscale(previous).resize(size, Image.Resampling.BILINEAR)
    diff = ImageChops.difference(a_gray, b_gray)
    hist = diff.point(lambda v: 255 if v >= 22 else 0).histogram()
    changed_pixels = sum(hist[1:])
    ratio = changed_pixels / float(size[0] * size[1])
    similarity = None
    if _ssim is not None and _np is not None:
        try:
            similarity = float(_ssim(_np.asarray(a_gray), _np.asarray(b_gray), data_range=255))
        except Exception:
            similarity = None
    if similarity is None:
        similarity = max(0.0, min(1.0, 1.0 - ratio))
    regions = _difference_regions(current, previous)
    changed = ratio >= 0.018 and (similarity < 0.985 or bool(regions))
    return {
        "available": True,
        "changed": bool(changed),
        "similarity": round(similarity, 6),
        "difference_ratio": round(ratio, 6),
        "changed_region_count": len(regions),
        "regions": regions,
        "engine": "skimage_ssim+pil_diff" if _ssim is not None else "pil_diff_local",
    }


def _capabilities() -> Dict[str, Any]:
    return {
        "pil": True,
        "opencv": _cv2 is not None,
        "numpy": _np is not None,
        "tesseract": _pytesseract is not None and shutil.which("tesseract") is not None,
        "scikit_image": _ssim is not None,
        "scipy": _ndi is not None,
        "shapely": _shapely_geometry is not None,
        "sympy": _sympy is not None,
        "networkx": _nx is not None,
        "pandas": _pd is not None,
        "imageio": _imageio is not None,
        "matplotlib": _plt is not None or NANO_USE_OPTIONAL_HEAVY_IMAGE_LIBS,
        "nano_printer": True,
    }


def scan_image(path: str, *, user_request: str = "", previous_path: Optional[str] = None, state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Macro-quantum local scan: one decoded image, 16 parallel evidence lanes.

    All observations remain local. The result is a processor-ready evidence
    packet; it does not decide routing and does not call a paid provider.
    """
    t0 = time.perf_counter()
    _visual_log("SCAN_START", path=str(path), request=_clip_text(user_request, 140))
    if not path:
        _visual_log("SCAN_ERROR", reason="image_path_missing")
        return build_error_packet("image_path_missing")
    if not os.path.exists(path):
        _visual_log("SCAN_ERROR", reason="image_file_missing")
        return build_error_packet("image_file_missing")
    if Path(path).suffix.lower() not in IMAGE_EXTENSIONS:
        _visual_log("SCAN_ERROR", reason="unsupported_image_type")
        return build_error_packet("unsupported_image_type")

    img = _load_image(path)
    if img is None:
        _visual_log("SCAN_ERROR", reason="image_decode_failed")
        return build_error_packet("image_decode_failed")

    if not previous_path and isinstance(state, dict):
        candidate = state.get("previous_image_path")
        if isinstance(candidate, str):
            previous_path = candidate

    request = _request_evidence(user_request)
    lanes = _parallel_local_scan(img, user_request, previous_path, request=request)
    visual = lanes.get("visual", {})
    pixels = lanes.get("pixels", {})
    nano_pixels = lanes.get("nano_pixels", {})
    color = lanes.get("color", {})
    ocr = lanes.get("ocr", {})
    layout = lanes.get("layout", {})
    components = lanes.get("components", {})
    geometry = lanes.get("geometry", {})
    compare = lanes.get("compare", {})

    tables = _table_scan(layout, img.size)
    semantics = _text_semantics(ocr.get("text", ""))
    is_screenshot, screenshot_score, screenshot_reasons = _looks_like_screenshot(img, ocr, layout)
    vector_plan = _vector_plan(geometry, ocr, color, img.size)
    recolor = _recolor_plan(img, color, request)
    pseudo_3d = _pseudo_3d_scan(img, geometry, user_request)
    summary = _build_summary(visual, ocr, semantics, tables, geometry, compare, request, screenshot_score, color)

    feature_scores = [
        ocr.get("confidence", 0.0),
        color.get("palette_size", 0) / MAX_COLORS,
        screenshot_score,
        tables.get("confidence", 0.0),
        geometry.get("graph_confidence", 0.0),
        geometry.get("diagram_confidence", 0.0),
        components.get("confidence", 0.0),
    ]
    confidence = round(min(1.0, 0.28 + 0.72 * _confidence(feature_scores)), 4)
    fingerprint = _image_fingerprint(img)

    scope = state if isinstance(state, dict) else {}
    memory_scope = scope.get("memory_scope") if isinstance(scope.get("memory_scope"), dict) else {}
    user_id = scope.get("user_id") or memory_scope.get("user_id")
    conversation_id = scope.get("conversation_id") or memory_scope.get("conversation_id")

    provider_packet = {
        "input_type": "screenshot" if is_screenshot else "image",
        "request": user_request,
        "image_fingerprint": fingerprint,
        "visual": visual,
        "ocr": ocr,
        "text": semantics,
        "layout": layout,
        "geometry": geometry,
        "components": components,
        "color_scan": color,
        "nano_pixels": nano_pixels,
        "screenshot_detection": {
            "is_screenshot": is_screenshot,
            "confidence": screenshot_score,
            "reasons": screenshot_reasons,
        },
        "tables": tables,
        "links": semantics.get("urls", []),
        "formulas": semantics.get("formula_candidates", []),
        "code_blocks": semantics.get("code_candidates", []),
        "change_detection": compare,
        "visual_objects": summary.get("objects", []),
        "issues": summary.get("issues", []),
        "vector_drawing_plan": vector_plan,
        "three_d_evidence": pseudo_3d,
    }

    visual_types = [
        str(x.get("type")) for x in summary.get("objects", [])
        if isinstance(x, dict) and x.get("type")
    ]
    _visual_log(
        "SCAN_DONE",
        kind="screenshot" if is_screenshot else "image",
        resolution=[img.width, img.height],
        ocr_items=len(ocr.get("items", [])),
        ocr_preview=_normalize_text(ocr.get("text", ""))[:180],
        objects=visual_types[:12],
        formulas=len(semantics.get("formula_candidates", [])),
        links=len(semantics.get("urls", [])),
        regions=len(layout.get("regions", [])),
        lines=len(geometry.get("lines", [])),
        nano_levels=list(NANO_PIXEL_LEVELS),
        confidence=confidence,
        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
    )
    result = {
        "version": VERSION,
        "nano_scanner_version": NANO_SCANNER_VERSION,
        "macro_quantum": {
            "enabled": True,
            "architecture": "16_parallel_logical_lanes",
            "logical_core_count": NANO_SCANNER_LOGICAL_CORES,
            "worker_slots": NANO_SCANNER_MAX_WORKERS,
            "bit_width": NANO_SCANNER_BITS,
            "pixel_mode": True,
            "nano_pixel_mode": True,
            "levels": list(NANO_PIXEL_LEVELS),
            "processor_handoff": "direct_structured_evidence",
        },
        "source": PROVIDER,
        "performance": {
            "fast_mode": NANO_FAST_MODE,
            "ocr_max_passes": NANO_OCR_MAX_PASSES,
            "lazy_matplotlib": True,
            "heavy_optional_image_libs_enabled": NANO_USE_OPTIONAL_HEAVY_IMAGE_LIBS,
            "parallel_scan": True,
            "parallel_elapsed_ms": lanes.get("parallel_elapsed_ms", 0.0),
            "total_scan_elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        },
        "provider_calls": 0,
        "single_call": False,
        "paid_provider_used": False,
        "local_only": True,
        "input_type": "screenshot" if is_screenshot else "image",
        "path": str(path),
        "user_id": user_id,
        "conversation_id": conversation_id,
        "image_fingerprint": fingerprint,
        "visual": visual,
        "pixels": pixels,
        "nano_pixels": nano_pixels,
        "color_scan": color,
        "screenshot_detection": {"is_screenshot": is_screenshot, "confidence": screenshot_score, "reasons": screenshot_reasons},
        "ocr": ocr,
        "text": {"content": _clip_text(ocr.get("text", "")), "confidence": ocr.get("confidence", 0.0), "segments": ocr.get("items", [])},
        "links": semantics["urls"],
        "formulas": semantics["formula_candidates"],
        "code_blocks": semantics["code_candidates"],
        "layout": layout,
        "components": components,
        "tables": tables,
        "graphs": {
            "confidence": geometry.get("graph_confidence", 0.0),
            "line_count": geometry.get("line_count", 0),
            "horizontal_axis_candidates": geometry.get("horizontal_axis_candidates", 0),
            "vertical_axis_candidates": geometry.get("vertical_axis_candidates", 0),
        },
        "diagrams": {
            "confidence": geometry.get("diagram_confidence", 0.0),
            "line_count": geometry.get("line_count", 0),
            "circle_count": geometry.get("circle_count", 0),
            "primitives": geometry.get("primitives", [])[:MAX_CONTOURS],
        },
        "change_detection": compare,
        "request_evidence": request,
        "visual_objects": summary["objects"],
        "issues": summary["issues"],
        "local_interpretation": summary,
        "vector_drawing_plan": vector_plan,
        "recolor_plan": recolor,
        "three_d_evidence": pseudo_3d,
        "processor_packet": provider_packet,
        "capabilities": _capabilities(),
        "semantic_scope": {
            "can_explain_visible_content": True,
            "can_extract_text": bool(ocr.get("available")),
            "can_scan_pixels": True,
            "can_scan_nano_pixels": True,
            "can_scan_colors": bool(color.get("palette")),
            "can_extract_links": bool(semantics["urls"]),
            "can_extract_formula_candidates": bool(semantics["formula_candidates"]),
            "can_detect_code_candidates": bool(semantics["code_candidates"]),
            "can_detect_tables": bool(tables["detected"]),
            "can_detect_graph_geometry": geometry.get("graph_confidence", 0.0) > 0.0,
            "can_detect_diagram_geometry": geometry.get("diagram_confidence", 0.0) > 0.0,
            "can_compare_previous_image": compare.get("available", False),
            "can_propose_change_evidence": bool(request["asks_edit_or_fix"] or request["asks_color_change"]),
            "can_build_2d_editable_evidence": bool(vector_plan["available"]),
            "can_build_3d_evidence": bool(pseudo_3d["confidence"] > 0.0),
            "can_print_image_answers": True,
            "can_print_graphs": True,
            "can_print_tables": True,
            "can_print_diagrams": True,
            "can_print_drawings": True,
            "can_print_formulas": True,
            "can_print_3d_scenes": bool(_plt is not None),
            "can_recolor_pixels_locally": True,
            "printer_engine": NANO_PRINTER_VERSION,
            "semantic_decision_owner": "QUANTUM_PROCESSOR",
        },
        "confidence": confidence,
        "safe_for_interpretation": True,
        "decision_owner": "QUANTUM_PROCESSOR",
        "handoff": {
            "route": "INPUT -> NANO_SCANNER -> QUANTUM_PROCESSOR",
            "complete": True,
            "provider_calls": 0,
            "next_consumer": "QUANTUM_PROCESSOR",
        },
    }
    return result


# ============================================================
# NANO PRINTER V4
# ============================================================

NANO_PRINTER_VERSION = "NANO_PRINTER_V7_FIDELITY_LOCAL"
DEFAULT_CANVAS = (1280, 800)
SUPPORTED_PRINT_KINDS = {
    "image", "screenshot", "annotated_image", "drawing", "diagram",
    "graph", "table", "formula", "3d", "scene",
}

def _printer_font(size: int = 24, bold: bool = False):
    candidates = ([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ] if bold else [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])
    for candidate in candidates:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                pass
    return ImageFont.load_default()

def _safe_rgb(value: Any, default=(60, 190, 150)) -> Tuple[int, int, int]:
    if isinstance(value, str):
        v = value.strip().lstrip("#")
        if len(v) == 6:
            try:
                return tuple(int(v[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                return default
        named = {"red":(220,60,60),"green":(50,180,100),"blue":(60,110,220),
                 "yellow":(235,190,40),"white":(245,245,245),"black":(20,20,20),
                 "gray":(130,130,130),"orange":(235,130,40),"purple":(150,90,200),
                 "cyan":(50,190,210),"pink":(220,90,150)}
        return named.get(v.lower(), default)
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return tuple(max(0, min(255, int(x))) for x in value[:3])
        except Exception:
            pass
    return default

def _save_image(img: Image.Image, output_path: str, fmt: Optional[str] = None) -> Dict[str, Any]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ext = (fmt or output.suffix.lstrip(".") or "png").lower()
    if ext == "jpg":
        ext = "jpeg"
    img.save(output, format=ext.upper())
    return {"path":str(output),"mime":f"image/{'jpeg' if ext=='jpeg' else ext}",
            "format":ext,"width":img.width,"height":img.height,"bytes":output.stat().st_size}

def _new_canvas(size=DEFAULT_CANVAS, background=(18,20,24)) -> Image.Image:
    return Image.new("RGB", size, _safe_rgb(background,(18,20,24)))

def _xy(value: Any, width: int, height: int, default=(0,0)) -> Tuple[float,float]:
    if isinstance(value, dict):
        x,y=value.get("x",default[0]),value.get("y",default[1])
    elif isinstance(value,(list,tuple)) and len(value)>=2:
        x,y=value[0],value[1]
    else:
        x,y=default
    try:
        x,y=float(x),float(y)
        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            x,y=x*width,y*height
        return x,y
    except Exception:
        return float(default[0]),float(default[1])

def _draw_wrapped(draw, text, xy, max_width, font, fill=(235,235,235), gap=7):
    words=str(text or "").split()
    lines=[]; cur=""
    for word in words:
        trial=word if not cur else cur+" "+word
        try: tw=draw.textbbox((0,0),trial,font=font)[2]
        except Exception: tw=len(trial)*12
        if tw<=max_width or not cur: cur=trial
        else: lines.append(cur); cur=word
    if cur: lines.append(cur)
    x,y=xy; line_h=int(getattr(font,"size",22)*1.25)
    for line in lines:
        draw.text((x,y),line,font=font,fill=fill); y+=line_h+gap
    return y

def _render_graph(spec,size):
    img=_new_canvas(size,spec.get("background",(18,20,24))); d=ImageDraw.Draw(img)
    W,H=img.size
    d.text((40,28),str(spec.get("title","Graph")),font=_printer_font(30,True),fill=(245,245,245))
    left,right,top,bottom=110,W-50,95,H-90
    d.line((left,bottom,right,bottom),fill=(125,135,150),width=2)
    d.line((left,bottom,left,top),fill=(125,135,150),width=2)
    series=spec.get("series") or [{"name":"series","x":spec.get("x",[]),"y":spec.get("y",[])}]
    allx=[]; ally=[]
    for s in series:
        allx += list(s.get("x",range(len(s.get("y",[])))))
        ally += list(s.get("y",[]))
    try: xs=[float(v) for v in allx]; ys=[float(v) for v in ally]
    except Exception: xs=list(range(len(ally))); ys=[float(v) for v in ally]
    if not ys: d.text((60,140),"No data.",font=_printer_font(22),fill=(220,220,220)); return img
    xmin,xmax=min(xs),max(xs) if xs else 1; ymin,ymax=min(ys),max(ys)
    if xmin==xmax:xmax=xmin+1
    if ymin==ymax:ymax=ymin+1
    palette=spec.get("colors") or ["#42d392","#5aa7ff","#f0b84a","#db78d9","#ea6c6c"]
    for si,s in enumerate(series):
        pts=[]; sx=list(s.get("x",range(len(s.get("y",[]))))); sy=list(s.get("y",[]))
        for xv,yv in zip(sx,sy):
            try:
                xx=left+(float(xv)-xmin)/(xmax-xmin)*(right-left)
                yy=bottom-(float(yv)-ymin)/(ymax-ymin)*(bottom-top)
                pts.append((int(xx),int(yy)))
            except Exception: pass
        c=_safe_rgb(palette[si%len(palette)])
        if len(pts)>=2:d.line(pts,fill=c,width=4,joint="curve")
        for xx,yy in pts:d.ellipse((xx-5,yy-5,xx+5,yy+5),fill=c)
        if s.get("name"): d.text((right-220,top+si*30),str(s["name"]),font=_printer_font(18),fill=c)
    d.text((left+5,bottom+12),str(spec.get("x_label","x")),font=_printer_font(18),fill=(190,195,205))
    d.text((18,top),str(spec.get("y_label","y")),font=_printer_font(18),fill=(190,195,205))
    return img

def _render_table(spec,size):
    rows=spec.get("rows",[]); cols=spec.get("columns")
    if rows and isinstance(rows[0],dict):
        cols=list(cols or rows[0].keys()); rows=[[r.get(c,"") for c in cols] for r in rows]
    cols=list(cols or [])
    if rows and not cols: cols=[f"C{i+1}" for i in range(len(rows[0]))]
    img=_new_canvas(size,spec.get("background",(18,20,24))); d=ImageDraw.Draw(img)
    W,H=img.size; d.text((40,28),str(spec.get("title","Table")),font=_printer_font(30,True),fill=(245,245,245))
    if not cols:return img
    ncols=max(1,len(cols)); cw=max(100,(W-80)//ncols); rh=58; left,top=40,95
    for c,name in enumerate(cols):
        x1=left+c*cw;x2=left+(c+1)*cw
        d.rectangle((x1,top,x2,top+rh),fill=(35,40,48),outline=(105,115,130),width=2)
        d.text((x1+10,top+16),str(name)[:28],font=_printer_font(18,True),fill=(245,245,245))
    for r,row in enumerate(rows[:11]):
        y=top+(r+1)*rh
        for c,val in enumerate(row[:ncols]):
            x1=left+c*cw;x2=left+(c+1)*cw
            d.rectangle((x1,y,x2,y+rh),outline=(85,95,110),width=1)
            d.text((x1+10,y+16),str(val)[:28],font=_printer_font(17),fill=(220,225,235))
    return img

def _render_diagram(spec,size):
    img=_new_canvas(size,spec.get("background",(18,20,24))); d=ImageDraw.Draw(img)
    W,H=img.size; d.text((40,28),str(spec.get("title","Diagram")),font=_printer_font(30,True),fill=(245,245,245))
    nodes=spec.get("nodes",[]); pos={}
    for i,n in enumerate(nodes):
        nid=str(n.get("id",i)); pos[nid]=tuple(int(v) for v in _xy(n.get("position",n),W,H,(120+i*140,H/2)))
    for e in spec.get("edges",[]):
        a,b=pos.get(str(e.get("from"))),pos.get(str(e.get("to")))
        if not a or not b: continue
        c=_safe_rgb(e.get("color",(125,145,165))); d.line((*a,*b),fill=c,width=int(e.get("width",4)))
        if e.get("arrow",True):
            dx,dy=b[0]-a[0],b[1]-a[1]; ln=max(1,math.hypot(dx,dy)); ux,uy=dx/ln,dy/ln; px,py=-uy,ux
            tip=(b[0]-10*ux,b[1]-10*uy); p1=(tip[0]-18*ux+8*px,tip[1]-18*uy+8*py); p2=(tip[0]-18*ux-8*px,tip[1]-18*uy-8*py)
            d.polygon([b,p1,p2],fill=c)
    for i,n in enumerate(nodes):
        x,y=pos.get(str(n.get("id",i)),(100,100)); nw=int(n.get("width",180)); nh=int(n.get("height",70))
        fill=_safe_rgb(n.get("fill",(55,70,85))); outline=_safe_rgb(n.get("outline",(120,160,180)))
        box=(x-nw//2,y-nh//2,x+nw//2,y+nh//2)
        if n.get("shape")=="circle":d.ellipse(box,fill=fill,outline=outline,width=3)
        else:d.rounded_rectangle(box,radius=14,fill=fill,outline=outline,width=3)
        label=str(n.get("label",n.get("id",i))); f=_printer_font(18,True); bb=d.textbbox((0,0),label,font=f)
        d.text((x-(bb[2]-bb[0])/2,y-(bb[3]-bb[1])/2),label,font=f,fill=(245,245,245))
    return img

def _render_drawing(spec,size):
    img=_new_canvas(size,spec.get("background",(18,20,24))); d=ImageDraw.Draw(img)
    for p in spec.get("primitives",[]):
        kind=str(p.get("type","line")); c=_safe_rgb(p.get("color",(80,190,160))); w=max(1,int(p.get("width",4)))
        if kind=="line" and len(p.get("points",[]))>=4:
            d.line(tuple(int(v) for v in p["points"][:4]),fill=c,width=w)
        elif kind in ("rect","rectangle","circle"):
            x,y,rw,rh=p.get("bbox",[0,0,100,60]); box=(x,y,x+rw,y+rh)
            fill=_safe_rgb(p.get("fill"),(0,0,0)) if p.get("fill") else None
            (d.rectangle if kind in ("rect","rectangle") else d.ellipse)(box,fill=fill,outline=c,width=w)
        elif kind in ("polygon","triangle"):
            pts=[(int(a),int(b)) for a,b in p.get("points",[])]
            if pts:d.polygon(pts,fill=_safe_rgb(p.get("fill"),(0,0,0)) if p.get("fill") else None,outline=c)
        elif kind=="text":
            x,y=p.get("position",[40,40]); d.text((x,y),str(p.get("text","")),font=_printer_font(int(p.get("size",22))),fill=c)
    if spec.get("title"):d.text((40,28),str(spec["title"]),font=_printer_font(30,True),fill=(245,245,245))
    return img

def _render_formula(spec,size):
    img=_new_canvas(size,spec.get("background",(18,20,24)))
    if _plt is not None:
        try:
            fig=plt.figure(figsize=(size[0]/120,size[1]/120),dpi=120); ax=fig.add_axes([0,0,1,1]); ax.axis("off")
            ax.text(.5,.55,str(spec.get("formula") or spec.get("text") or ""),ha="center",va="center",fontsize=34)
            fig.canvas.draw(); w,h=fig.canvas.get_width_height()
            rgba=fig.canvas.buffer_rgba(); overlay=Image.frombuffer("RGBA",(w,h),rgba,"raw","RGBA",0,1).copy()
            img.paste(overlay,(0,0),overlay); plt.close(fig); return img
        except Exception:
            try:plt.close("all")
            except Exception:pass
    d=ImageDraw.Draw(img); d.text((40,28),str(spec.get("title","Formula")),font=_printer_font(30,True),fill=(245,245,245))
    d.text((70,340),str(spec.get("formula") or spec.get("text") or ""),font=_printer_font(32,True),fill=(235,235,235))
    return img

def _render_3d(spec,size):
    if _plt is None:return None
    try:
        fig=plt.figure(figsize=(size[0]/120,size[1]/120),dpi=120); ax=fig.add_subplot(111,projection="3d"); ax.set_title(str(spec.get("title","3D Scene")))
        pts=spec.get("points") or []
        if pts: ax.scatter([p[0] for p in pts],[p[1] for p in pts],[p[2] for p in pts],s=36)
        for seg in spec.get("lines",[]):
            if len(seg)>=2:
                ax.plot([seg[0][0],seg[1][0]],[seg[0][1],seg[1][1]],[seg[0][2],seg[1][2]],linewidth=2)
        fig.tight_layout(); fig.canvas.draw(); w,h=fig.canvas.get_width_height()
        rgba=fig.canvas.buffer_rgba(); img=Image.frombuffer("RGBA",(w,h),rgba,"raw","RGBA",0,1).convert("RGB").resize(size,Image.Resampling.LANCZOS)
        plt.close(fig); return img
    except Exception:
        try:plt.close("all")
        except Exception:pass
        return None

def _recolor_exact(source_path,spec,output_path):
    img=_load_image(source_path)
    if img is None:return {"ok":False,"error":"image_decode_failed"}
    target=_safe_rgb(spec.get("source_color") or spec.get("color"),(0,0,0)); repl=_safe_rgb(spec.get("target_color"),(52,211,153))
    tol=max(0,int(spec.get("tolerance",28))); px=img.load(); changed=0
    for y in range(img.height):
        for x in range(img.width):
            r,g,b=px[x,y]
            if max(abs(r-target[0]),abs(g-target[1]),abs(b-target[2]))<=tol:
                px[x,y]=repl; changed+=1
    return {"ok":True,"changed_pixels":changed,"source_color":list(target),"target_color":list(repl),
            "tolerance":tol,"artifact":_save_image(img,output_path)}

def _copy_source_without_reencode(source_path: str, output_path: str) -> Dict[str, Any]:
    """Preserve an image byte-for-byte when the printer is only displaying it."""
    source = Path(source_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    img = _load_image(str(output))
    return {
        "path": str(output),
        "mime": f"image/{output.suffix.lstrip('.').lower() or 'png'}",
        "format": output.suffix.lstrip('.').lower() or 'png',
        "width": img.width if img else 0,
        "height": img.height if img else 0,
        "bytes": output.stat().st_size,
        "byte_preserved": True,
        "digest_128": _nano_hash_bytes(output.read_bytes()),
    }


def print_visual(spec, output_path, *, size=DEFAULT_CANVAS, format=None):
    if not isinstance(spec,dict):
        _visual_log("PRINT_ERROR", reason="spec_must_be_dict")
        return {"ok":False,"error":"spec_must_be_dict","provider_calls":0,"local_only":True}
    kind=str(spec.get("kind") or spec.get("type") or "scene").lower()
    _visual_log("PRINT_START", kind=kind, output_path=str(output_path))
    if kind=="recolor":
        source=spec.get("source_path") or spec.get("path")
        if not source:return {"ok":False,"error":"source_path_required","provider_calls":0,"local_only":True}
        r=_recolor_exact(source,spec,output_path); r.update({"kind":"image","printer_version":NANO_PRINTER_VERSION,"provider_calls":0,"local_only":True}); return r
    if kind in {"image","screenshot"}:
        source_path = str(spec.get("source_path") or spec.get("path",""))
        # Pure display paths are copied without decode/re-encode. This preserves
        # the exact screenshot pixels and is the fastest printer path.
        if source_path and os.path.exists(source_path) and not spec.get("force_reencode"):
            artifact = _copy_source_without_reencode(source_path, output_path)
            _visual_log(
                "PRINT_DONE", kind=kind, mode="byte_preserved_source", ok=True,
                width=artifact.get("width", 0), height=artifact.get("height", 0),
                bytes=artifact.get("bytes", 0),
            )
            return {
                "ok": True,
                "kind": kind,
                "printer_version": NANO_PRINTER_VERSION,
                "provider_calls": 0,
                "single_call": False,
                "paid_provider_used": False,
                "local_only": True,
                "artifact": artifact,
                "editable": False,
                "fidelity_mode": "byte_preserved_source",
            }
        img=_load_image(source_path)
    elif kind=="annotated_image":
        img=_load_image(str(spec.get("source_path") or spec.get("path","")))
        if img:
            d=ImageDraw.Draw(img)
            for i,item in enumerate(spec.get("boxes",[])):
                x,y,w,h=[int(float(v)) for v in item.get("bbox",[0,0,0,0])]
                c=_safe_rgb(item.get("color",(235,90,90))); d.rectangle((x,y,x+w,y+h),outline=c,width=max(2,int(item.get("width",4))))
                d.text((x+4,max(0,y-23)),str(item.get("label") or item.get("text") or f"#{i+1}")[:80],font=_printer_font(16,True),fill=c)
    elif kind=="graph":img=_render_graph(spec,size)
    elif kind=="table":img=_render_table(spec,size)
    elif kind=="diagram":img=_render_diagram(spec,size)
    elif kind in {"drawing","scene"}:img=_render_drawing(spec,size)
    elif kind=="formula":img=_render_formula(spec,size)
    elif kind=="3d":img=_render_3d(spec,size) or _render_drawing({"title":spec.get("title","3D Scene")},size)
    else:return {"ok":False,"error":f"unsupported_print_kind:{kind}","supported":sorted(SUPPORTED_PRINT_KINDS),"provider_calls":0,"local_only":True}
    if img is None:
        _visual_log("PRINT_ERROR", kind=kind, reason="source_image_unreadable")
        return {"ok":False,"error":"source_image_unreadable","provider_calls":0,"local_only":True}
    a=_save_image(img,output_path,format)
    payload_counts = {
        "series": len(spec.get("series", []) or []) if isinstance(spec.get("series"), list) else 0,
        "rows": len(spec.get("rows", []) or []) if isinstance(spec.get("rows"), list) else 0,
        "nodes": len(spec.get("nodes", []) or []) if isinstance(spec.get("nodes"), list) else 0,
        "edges": len(spec.get("edges", []) or []) if isinstance(spec.get("edges"), list) else 0,
        "primitives": len(spec.get("primitives", []) or []) if isinstance(spec.get("primitives"), list) else 0,
        "points": len(spec.get("points", []) or []) if isinstance(spec.get("points"), list) else 0,
    }
    _visual_log(
        "PRINT_DONE", kind=kind, mode="render", ok=True,
        width=img.width, height=img.height, bytes=a.get("bytes", 0),
        payload=payload_counts,
    )
    return {"ok":True,"kind":kind,"printer_version":NANO_PRINTER_VERSION,"provider_calls":0,"single_call":False,
            "paid_provider_used":False,"local_only":True,"artifact":a,"editable":True}

def print_from_evidence(evidence, output_path, *, mode="auto", size=DEFAULT_CANVAS):
    if not isinstance(evidence,dict):return {"ok":False,"error":"evidence_must_be_dict","provider_calls":0,"local_only":True}
    mode=str(mode or "auto").lower()
    if mode=="auto":mode="annotated_image" if evidence.get("path") else "drawing"
    if mode in {"annotated_image","image","screenshot"} and evidence.get("path"):
        boxes=[]
        for item in evidence.get("ocr",{}).get("items",[])[:120]:
            boxes.append({"bbox":item.get("bbox",[0,0,0,0]),"label":item.get("text","")[:70],"color":"#4dd0e1"})
        for item in evidence.get("change_detection",{}).get("regions",[])[:60]:
            boxes.append({"bbox":item.get("bbox",[0,0,0,0]),"label":"CHANGED","color":"#ef6a6a","width":5})
        return print_visual({"kind":"annotated_image","source_path":evidence["path"],"boxes":boxes},output_path,size=size)
    prim=[]; y=130
    for obj in evidence.get("visual_objects",[])[:20]:
        prim += [{"type":"rect","bbox":[70,y,1140,52],"fill":"#374151","color":"#73859a"},
                 {"type":"text","position":[95,y+14],"text":f"{obj.get('type','object')}  confidence={obj.get('confidence',0):.2f}","color":"#e5e7eb","size":20}]
        y+=68
    title=(evidence.get("local_interpretation") or {}).get("description","Visual evidence")
    return print_visual({"kind":"drawing","title":title,"primitives":prim},output_path,size=size)

def render_visual_answer(action, *, output_path, title="April Visual Answer", graph=None, table=None, diagram=None,
                         drawing=None, formula=None, scene_3d=None, source_image=None, recolor=None, size=DEFAULT_CANVAS):
    action=str(action or "").lower()
    _visual_log("RENDER_REQUEST", action=action, title=str(title)[:120])
    if recolor:
        spec=dict(recolor); spec["kind"]="recolor"; spec.setdefault("source_path",source_image)
        return print_visual(spec,output_path,size=size)
    if source_image and action in {"show_image","display_image","image","screenshot","annotate","inspect"}:
        return print_visual({"kind":"annotated_image" if action=="annotate" else "image","source_path":source_image,"title":title},output_path,size=size)
    if graph is not None or action in {"graph","plot","chart"}:
        spec=dict(graph or {}); spec.update({"kind":"graph","title":spec.get("title",title)}); return print_visual(spec,output_path,size=size)
    if table is not None or action=="table":
        spec=dict(table or {}); spec.update({"kind":"table","title":spec.get("title",title)}); return print_visual(spec,output_path,size=size)
    if diagram is not None or action in {"diagram","scheme","flowchart"}:
        spec=dict(diagram or {}); spec.update({"kind":"diagram","title":spec.get("title",title)}); return print_visual(spec,output_path,size=size)
    if formula is not None or action=="formula":
        return print_visual({"kind":"formula","title":title,"formula":formula or ""},output_path,size=size)
    if scene_3d is not None or action in {"3d","3d_scene","model3d"}:
        spec=dict(scene_3d or {}); spec.update({"kind":"3d","title":spec.get("title",title)}); return print_visual(spec,output_path,size=size)
    spec=dict(drawing or {}); spec.update({"kind":"drawing","title":spec.get("title",title)}); return print_visual(spec,output_path,size=size)



# ============================================================
# CANONICAL LOCAL IMAGE API — PROJECT COMPATIBILITY
# ============================================================

def _state_user_request(state: Optional[Dict[str, Any]]) -> str:
    """Extract the current user text without creating a second route."""
    if not isinstance(state, dict):
        return ""
    for key in (
        "user_request", "current_request", "message", "text", "prompt",
        "query", "input_text", "content",
    ):
        value = state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for parent_key in ("meta", "request", "input", "context"):
        parent = state.get(parent_key)
        if isinstance(parent, dict):
            for key in (
                "user_request", "current_request", "message", "text",
                "prompt", "query", "input_text", "content",
            ):
                value = parent.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return ""


async def analyze_image(
    path: str,
    state: Optional[Dict[str, Any]] = None,
    user_request: str = "",
    previous_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Single canonical visual entry point used by ImageRoom/ImageEngine.

    It is local-only: scan_image() performs pixel/color/OCR/geometry analysis,
    and the Nano Printer functions are exposed for later visual output.
    No provider call is made here.
    """
    if not user_request:
        user_request = _state_user_request(state)
    if not previous_path and isinstance(state, dict):
        candidate = state.get("previous_image_path")
        if isinstance(candidate, str) and candidate:
            previous_path = candidate

    result = await asyncio.to_thread(
        scan_image,
        path,
        user_request=user_request,
        previous_path=previous_path,
        state=state,
    )
    if isinstance(result, dict) and isinstance(state, dict):
        meta = state.get("meta")
        if isinstance(meta, dict):
            result.setdefault("user_id", meta.get("user_id"))
    return result


__all__ = [
    "detect_intent",
    "build_intent_result",
    "safe_patch_log",
    "patch_intent_detect",
    "patch_intent_future",
    "normalize",
    "contains_any",
    "scan_image",
    "analyze_image",
    "build_error_packet",
    "print_visual",
    "print_from_evidence",
    "render_visual_answer",
    "NANO_PRINTER_VERSION",
    "NANO_SCANNER_VERSION",
    "NANO_SCANNER_BITS",
    "NANO_SCANNER_LOGICAL_CORES",
]
