"""
APRIL — LOCAL VISUAL / SCREENSHOT SCANNER V1

Purpose
-------
Local, provider-free visual evidence extraction for screenshots/images.

This module is intentionally passive:
    image/screenshot -> local scan -> structured visual evidence

It does NOT:
- call OpenAI, Gemini, or another paid provider;
- select the final room/route;
- generate an answer;
- modify the image;
- replace Quantum Interpretation.

It extracts what can be established locally:
- visible text + OCR boxes/confidence;
- links;
- likely code blocks;
- formulas / mathematical expressions;
- layout regions;
- tables;
- graph-like geometry;
- diagram-like geometry;
- image dimensions / basic visual statistics;
- visual changes when a previous image is supplied;
- repair/change evidence from the user's request.

The returned packet is designed for interpretation_layer.py / Quantum Processor.
"""

from __future__ import annotations

import asyncio
import os
import re
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image
import pytesseract
from pytesseract import Output


VERSION = "LOCAL_VISUAL_SCANNER_V1"
PROVIDER = "local"
MAX_OCR_ITEMS = 500
MAX_TEXT_CHARS = 12000
MAX_REGIONS = 80

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"
}

URL_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\]\[()\"']+"
)

# Conservative mathematical candidates. This is evidence, not proof.
FORMULA_RE = re.compile(
    r"(?:"
    r"[A-Za-zА-Яа-я]\s*=\s*[^.;]{1,120}"
    r"|"
    r"\\(?:frac|sqrt|sum|int|alpha|beta|gamma|pi|Delta|theta)\b"
    r"|"
    r"\b\d+\s*[+\-*/×÷=<>]\s*[-+*/×÷=<>0-9A-Za-zА-Яа-я()., ]+"
    r")"
)

CODE_RE = re.compile(
    r"(?m)^(?:\s{2,}|\t+).*(?:[{}();:=]|\b(?:def|class|import|from|return|const|let|var|function|if|else|for|while)\b)"
)

EDIT_TERMS = (
    "исправ", "ошиб", "неправ", "помен", "измени", "убер", "добав",
    "замени", "передел", "сделай", "нужно поправ", "что изменить",
    "что исправить", "помоги", "help", "fix", "change", "remove",
    "add", "replace", "correct", "edit", "modify",
)

EXPLAIN_TERMS = (
    "что изображено", "что написано", "прочитай", "объясни",
    "разбери", "проанализируй", "что здесь", "что на скрине",
    "объяснить", "описать", "explain", "describe", "read", "analyze",
)

CHART_TERMS = (
    "график", "chart", "plot", "диаграм", "diagram", "схем", "scheme",
)

TABLE_TERMS = (
    "таблиц", "table", "rows", "columns",
)

# ---------------------------------------------------------
# Lightweight utilities
# ---------------------------------------------------------

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
    value = str(text or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _clip_text(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    text = str(text or "")
    return text if len(text) <= limit else text[:limit] + "…"


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    value = str(text or "").lower()
    return any(n.lower() in value for n in needles)


def _safe_confidence(values: Sequence[float]) -> float:
    vals = [max(0.0, min(1.0, float(v))) for v in values if v is not None]
    return round(float(np.mean(vals)), 4) if vals else 0.0


def _load_cv_image(path: str) -> Tuple[Optional[np.ndarray], Optional[Image.Image]]:
    try:
        pil = Image.open(path).convert("RGB")
        cv = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        return cv, pil
    except Exception:
        return None, None


# ---------------------------------------------------------
# OCR
# ---------------------------------------------------------

def _ocr_scan(cv_image: np.ndarray) -> Dict[str, Any]:
    rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

    # A small preprocessing ladder. We keep the best useful result.
    variants: List[Tuple[str, np.ndarray]] = [("rgb", rgb)]
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    variants.append(("gray", gray))

    # Upscaling helps screenshots with small UI text.
    h, w = gray.shape[:2]
    scale = 1.5 if max(h, w) < 2200 else 1.0
    if scale > 1.0:
        up = cv2.resize(
            gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )
        variants.append(("upscaled_gray", up))
        variants.append(("adaptive", cv2.adaptiveThreshold(
            up, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 11
        )))

    candidates: List[Dict[str, Any]] = []
    best_text = ""
    best_score = -1.0

    for variant_name, img in variants:
        try:
            data = pytesseract.image_to_data(
                img,
                lang="rus+ukr+eng",
                config="--oem 3 --psm 11",
                output_type=Output.DICT,
            )
        except Exception:
            continue

        items = []
        confs = []
        for i, raw_text in enumerate(data.get("text", [])):
            text = _normalize_text(raw_text)
            if not text:
                continue
            conf = _safe_float(data.get("conf", ["-1"])[i], -1)
            if conf < 0:
                continue
            scale_back = scale if variant_name != "rgb" and variant_name != "gray" else 1.0
            x = _safe_int(data.get("left", [0])[i]) / scale_back
            y = _safe_int(data.get("top", [0])[i]) / scale_back
            ww = _safe_int(data.get("width", [0])[i]) / scale_back
            hh = _safe_int(data.get("height", [0])[i]) / scale_back
            items.append({
                "text": text,
                "confidence": round(max(0.0, min(1.0, conf / 100.0)), 4),
                "bbox": [round(x), round(y), round(ww), round(hh)],
                "block": _safe_int(data.get("block_num", [0])[i]),
                "line": _safe_int(data.get("line_num", [0])[i]),
            })
            confs.append(max(0.0, min(1.0, conf / 100.0)))

        text = _normalize_text(" ".join(x["text"] for x in items))
        score = (len(text) / max(1, len(items) * 2)) + _safe_confidence(confs)
        if score > best_score:
            best_score = score
            best_text = text
            candidates = items

    # Stable ordering for downstream consumers.
    candidates = sorted(
        candidates,
        key=lambda x: (x["bbox"][1], x["bbox"][0])
    )[:MAX_OCR_ITEMS]

    return {
        "text": _clip_text(best_text),
        "items": candidates,
        "confidence": _safe_confidence([x["confidence"] for x in candidates]),
        "engine": "tesseract_local",
        "languages": ["rus", "ukr", "eng"],
    }


# ---------------------------------------------------------
# Layout / regions
# ---------------------------------------------------------

def _layout_scan(cv_image: np.ndarray) -> Dict[str, Any]:
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 160)

    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    h, w = gray.shape[:2]
    regions: List[Dict[str, Any]] = []

    for contour in contours:
        x, y, rw, rh = cv2.boundingRect(contour)
        area = rw * rh
        if area < max(180, int(w * h * 0.00035)):
            continue
        ratio = rw / max(1, rh)
        if rw < 24 or rh < 16:
            continue

        regions.append({
            "bbox": [int(x), int(y), int(rw), int(rh)],
            "area": int(area),
            "aspect_ratio": round(float(ratio), 4),
            "kind": (
                "wide_region" if ratio >= 3.2 else
                "tall_region" if ratio <= 0.33 else
                "region"
            ),
        })

    regions = sorted(regions, key=lambda r: r["area"], reverse=True)[:MAX_REGIONS]

    # Simple horizontal/vertical structure hints.
    horizontal = cv2.morphologyEx(
        cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, w // 40), 1)),
    )
    vertical = cv2.morphologyEx(
        cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1],
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(12, h // 40))),
    )

    h_count = int(cv2.countNonZero(horizontal))
    v_count = int(cv2.countNonZero(vertical))
    grid_hint = h_count > w * 5 and v_count > h * 5

    return {
        "regions": regions,
        "horizontal_structure_pixels": h_count,
        "vertical_structure_pixels": v_count,
        "grid_hint": bool(grid_hint),
    }


# ---------------------------------------------------------
# Tables
# ---------------------------------------------------------

def _table_scan(cv_image: np.ndarray, layout: Dict[str, Any]) -> Dict[str, Any]:
    h, w = cv_image.shape[:2]
    horizontal = layout.get("horizontal_structure_pixels", 0)
    vertical = layout.get("vertical_structure_pixels", 0)

    strong_grid = bool(layout.get("grid_hint"))
    candidates = []

    for region in layout.get("regions", []):
        x, y, rw, rh = region["bbox"]
        ratio = rw / max(1, rh)
        if strong_grid and rw > w * 0.25 and rh > h * 0.06:
            candidates.append({
                "bbox": region["bbox"],
                "confidence": 0.72,
                "reason": "grid_geometry",
            })
        elif 1.3 <= ratio <= 12 and rw > w * 0.35 and rh > h * 0.08:
            candidates.append({
                "bbox": region["bbox"],
                "confidence": 0.42,
                "reason": "rectangular_region",
            })

    return {
        "detected": bool(candidates),
        "confidence": max([c["confidence"] for c in candidates], default=0.0),
        "candidates": candidates[:20],
        "geometry": {
            "horizontal": horizontal,
            "vertical": vertical,
        },
    }


# ---------------------------------------------------------
# Graphs / diagrams
# ---------------------------------------------------------

def _geometry_scan(cv_image: np.ndarray) -> Dict[str, Any]:
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 180)

    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=max(30, min(cv_image.shape[:2]) // 25),
        minLineLength=max(30, min(cv_image.shape[:2]) // 14),
        maxLineGap=12,
    )

    line_items = []
    if lines is not None:
        for line in lines[:300]:
            x1, y1, x2, y2 = [int(v) for v in line[0]]
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx * dx + dy * dy)
            angle = math.degrees(math.atan2(dy, dx))
            line_items.append({
                "points": [x1, y1, x2, y2],
                "length": round(length, 2),
                "angle": round(angle, 2),
            })

    h, w = gray.shape[:2]
    long_horizontal = sum(
        1 for x in line_items
        if abs(x["angle"]) < 8 and x["length"] > w * 0.12
    )
    long_vertical = sum(
        1 for x in line_items
        if abs(abs(x["angle"]) - 90) < 8 and x["length"] > h * 0.12
    )

    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(20, min(h, w) // 30),
        param1=100,
        param2=35,
        minRadius=6,
        maxRadius=max(8, min(h, w) // 6),
    )
    circle_count = 0 if circles is None else int(min(len(circles[0]), 100))

    graph_score = min(
        1.0,
        0.18 * min(long_horizontal, 5)
        + 0.18 * min(long_vertical, 5)
        + 0.05 * min(circle_count, 6)
    )

    diagram_score = min(
        1.0,
        0.012 * min(len(line_items), 70)
        + 0.04 * min(circle_count, 8)
    )

    return {
        "line_count": len(line_items),
        "lines": line_items[:200],
        "horizontal_axis_candidates": long_horizontal,
        "vertical_axis_candidates": long_vertical,
        "circle_count": circle_count,
        "graph_confidence": round(graph_score, 4),
        "diagram_confidence": round(diagram_score, 4),
    }


# ---------------------------------------------------------
# Text-derived semantic evidence
# ---------------------------------------------------------

def _text_semantics(ocr_text: str) -> Dict[str, Any]:
    text = _normalize_text(ocr_text)
    urls = []
    for url in URL_RE.findall(text):
        urls.append(url.rstrip(".,;:!?)]}"))

    formulas = []
    for m in FORMULA_RE.findall(text):
        value = _normalize_text(m)
        if len(value) >= 3 and value not in formulas:
            formulas.append(value)

    code_candidates = []
    for m in CODE_RE.findall(text):
        value = m.strip()
        if value and value not in code_candidates:
            code_candidates.append(value)

    lower = text.lower()

    return {
        "urls": urls[:100],
        "formula_candidates": formulas[:100],
        "code_candidates": code_candidates[:100],
        "has_math_evidence": bool(formulas),
        "has_code_evidence": bool(code_candidates),
        "has_link_evidence": bool(urls),
        "token_count": len(text.split()),
        "text_length": len(text),
        "text_language_evidence": {
            "cyrillic": bool(re.search(r"[А-Яа-яЁёЇїІіЄєҐґ]", text)),
            "latin": bool(re.search(r"[A-Za-z]", text)),
        },
        "keyword_evidence": {
            "chart": _contains_any(lower, CHART_TERMS),
            "table": _contains_any(lower, TABLE_TERMS),
        },
    }


# ---------------------------------------------------------
# Visual statistics / object hints
# ---------------------------------------------------------

def _visual_stats(cv_image: np.ndarray) -> Dict[str, Any]:
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    mean = float(np.mean(gray))
    std = float(np.std(gray))
    edges = cv2.Canny(gray, 80, 160)
    edge_ratio = float(np.count_nonzero(edges)) / max(1, w * h)

    return {
        "width": int(w),
        "height": int(h),
        "channels": int(cv_image.shape[2]) if cv_image.ndim == 3 else 1,
        "mean_luma": round(mean / 255.0, 4),
        "contrast": round(std / 255.0, 4),
        "edge_density": round(edge_ratio, 4),
        "orientation": "portrait" if h > w * 1.12 else (
            "landscape" if w > h * 1.12 else "square_like"
        ),
    }


# ---------------------------------------------------------
# Change detection
# ---------------------------------------------------------

def _compare_images(current: np.ndarray, previous_path: Optional[str]) -> Dict[str, Any]:
    if not previous_path or not os.path.exists(previous_path):
        return {
            "available": False,
            "changed": False,
            "similarity": None,
            "difference_ratio": None,
            "regions": [],
        }

    previous, _ = _load_cv_image(previous_path)
    if previous is None:
        return {
            "available": False,
            "changed": False,
            "similarity": None,
            "difference_ratio": None,
            "regions": [],
        }

    current_small = cv2.resize(current, (640, 640), interpolation=cv2.INTER_AREA)
    prev_small = cv2.resize(previous, (640, 640), interpolation=cv2.INTER_AREA)

    g1 = cv2.cvtColor(current_small, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(prev_small, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(g1, g2)
    # Ignore very small antialiasing/compression differences.
    _, threshold = cv2.threshold(diff, 22, 255, cv2.THRESH_BINARY)
    threshold = cv2.morphologyEx(
        threshold, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)
    )

    ratio = float(np.count_nonzero(threshold)) / threshold.size
    similarity = 1.0 - ratio

    contours, _ = cv2.findContours(
        threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    changed_regions = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < 120:
            continue
        changed_regions.append({
            "bbox_640": [int(x), int(y), int(w), int(h)],
            "area_ratio": round(float(w * h) / threshold.size, 6),
        })

    changed_regions.sort(key=lambda x: x["area_ratio"], reverse=True)

    return {
        "available": True,
        "changed": bool(ratio >= 0.015),
        "similarity": round(max(0.0, min(1.0, similarity)), 4),
        "difference_ratio": round(ratio, 6),
        "regions": changed_regions[:40],
    }


# ---------------------------------------------------------
# Request-to-help evidence
# ---------------------------------------------------------

def _request_evidence(user_request: str) -> Dict[str, Any]:
    t = str(user_request or "").strip().lower()

    asks_explain = _contains_any(t, EXPLAIN_TERMS)
    asks_edit = _contains_any(t, EDIT_TERMS)

    requested_changes = []
    patterns = [
        ("добавить", r"(?:добав(?:ить|ь)|add)\s+(.{1,120})"),
        ("удалить", r"(?:убер(?:и|ем)|удал(?:ить|и)|remove)\s+(.{1,120})"),
        ("заменить", r"(?:замен(?:ить|и)|replace)\s+(.{1,120})"),
        ("исправить", r"(?:исправ(?:ить|ь)|fix|correct)\s+(.{1,120})"),
        ("изменить", r"(?:измен(?:ить|и)|change|modify|edit)\s+(.{1,120})"),
    ]
    for action, pattern in patterns:
        m = re.search(pattern, t, flags=re.IGNORECASE)
        if m:
            requested_changes.append({
                "action": action,
                "target_text": _normalize_text(m.group(1))[:240],
            })

    return {
        "request_present": bool(t),
        "asks_explanation": bool(asks_explain),
        "asks_edit_or_fix": bool(asks_edit),
        "requested_changes": requested_changes,
    }


# ---------------------------------------------------------
# Human-facing local interpretation hints
# ---------------------------------------------------------

def _build_local_summary(
    visual: Dict[str, Any],
    ocr: Dict[str, Any],
    text_sem: Dict[str, Any],
    tables: Dict[str, Any],
    geometry: Dict[str, Any],
    compare: Dict[str, Any],
    request: Dict[str, Any],
) -> Dict[str, Any]:
    objects: List[Dict[str, Any]] = []

    if ocr.get("text"):
        objects.append({
            "type": "text",
            "confidence": round(max(0.0, min(1.0, ocr.get("confidence", 0.0))), 4),
            "evidence": "ocr",
        })

    if tables.get("detected"):
        objects.append({
            "type": "table",
            "confidence": tables.get("confidence", 0.0),
            "evidence": "grid_geometry",
        })

    if geometry.get("graph_confidence", 0) >= 0.35:
        objects.append({
            "type": "graph",
            "confidence": geometry.get("graph_confidence", 0.0),
            "evidence": "line_geometry",
        })

    if geometry.get("diagram_confidence", 0) >= 0.35:
        objects.append({
            "type": "diagram",
            "confidence": geometry.get("diagram_confidence", 0.0),
            "evidence": "shape_line_geometry",
        })

    if text_sem.get("has_math_evidence"):
        objects.append({
            "type": "formula",
            "confidence": 0.62,
            "evidence": "ocr_math_pattern",
        })

    if text_sem.get("has_code_evidence"):
        objects.append({
            "type": "code",
            "confidence": 0.62,
            "evidence": "ocr_code_pattern",
        })

    if text_sem.get("has_link_evidence"):
        objects.append({
            "type": "link",
            "confidence": 0.98,
            "evidence": "ocr_url_pattern",
        })

    # The scanner must not invent a problem merely because a picture is complex.
    issues: List[Dict[str, Any]] = []
    if request.get("asks_edit_or_fix"):
        if compare.get("available") and compare.get("changed"):
            issues.append({
                "type": "change_detected",
                "confidence": 1.0 - float(compare.get("similarity", 0.0)),
                "evidence": compare.get("regions", [])[:10],
            })
        if request.get("requested_changes"):
            for item in request["requested_changes"]:
                issues.append({
                    "type": "requested_change",
                    "action": item["action"],
                    "target": item["target_text"],
                    "confidence": 0.78,
                    "evidence": "user_request",
                })

    description_parts = []
    if visual.get("orientation"):
        description_parts.append(visual["orientation"])
    if ocr.get("text"):
        description_parts.append(f"распознан текст ({len(ocr.get('items', []))} фрагментов)")
    if tables.get("detected"):
        description_parts.append("обнаружена табличная структура")
    if geometry.get("graph_confidence", 0) >= 0.35:
        description_parts.append("обнаружены признаки графика")
    if geometry.get("diagram_confidence", 0) >= 0.35:
        description_parts.append("обнаружены признаки схемы/диаграммы")
    if text_sem.get("has_math_evidence"):
        description_parts.append("обнаружены математические выражения")
    if text_sem.get("has_code_evidence"):
        description_parts.append("обнаружены признаки кода")
    if text_sem.get("has_link_evidence"):
        description_parts.append("обнаружены ссылки")

    summary = "На изображении " + ", ".join(description_parts) if description_parts else (
        "Локальный сканер получил изображение, но уверенных структурных признаков мало."
    )

    return {
        "description": summary,
        "objects": objects,
        "issues": issues,
        "help_mode": (
            "explain_and_fix" if request.get("asks_edit_or_fix") else
            "explain" if request.get("asks_explanation") else
            "observe"
        ),
    }


# ---------------------------------------------------------
# Public scanner
# ---------------------------------------------------------

def scan_image(
    path: str,
    *,
    user_request: str = "",
    previous_path: Optional[str] = None,
    state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synchronous local scan.

    `state` is accepted only for compatibility. It may contain:
        state["previous_image_path"]
    It never becomes an alternative route or provider selection.
    """
    if not path:
        return build_error_packet("image_path_missing")

    if not os.path.exists(path):
        return build_error_packet("image_file_missing")

    suffix = Path(path).suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        return build_error_packet("unsupported_image_type")

    cv_image, pil_image = _load_cv_image(path)
    if cv_image is None or pil_image is None:
        return build_error_packet("image_decode_failed")

    if not previous_path and isinstance(state, dict):
        candidate = state.get("previous_image_path")
        if isinstance(candidate, str):
            previous_path = candidate

    visual = _visual_stats(cv_image)
    ocr = _ocr_scan(cv_image)
    layout = _layout_scan(cv_image)
    tables = _table_scan(cv_image, layout)
    geometry = _geometry_scan(cv_image)
    text_sem = _text_semantics(ocr.get("text", ""))
    compare = _compare_images(cv_image, previous_path)
    request = _request_evidence(user_request)
    local_summary = _build_local_summary(
        visual, ocr, text_sem, tables, geometry, compare, request
    )

    input_kind = "screenshot" if _looks_like_screenshot(visual, ocr, layout) else "image"

    # Overall confidence is evidence quality, not semantic correctness.
    confidence = round(
        min(
            1.0,
            0.40 * ocr.get("confidence", 0.0)
            + 0.20 * (1.0 if layout.get("regions") else 0.0)
            + 0.20 * max(
                geometry.get("graph_confidence", 0.0),
                geometry.get("diagram_confidence", 0.0),
                0.0,
            )
            + 0.20 * (1.0 if visual.get("width") and visual.get("height") else 0.0)
        ),
        4,
    )

    return {
        "version": VERSION,
        "source": PROVIDER,
        "provider_calls": 0,
        "input_type": input_kind,
        "path": str(path),

        "visual": visual,

        "ocr": ocr,
        "text": {
            "content": _clip_text(ocr.get("text", "")),
            "confidence": ocr.get("confidence", 0.0),
            "segments": ocr.get("items", []),
        },

        "links": text_sem["urls"],
        "formulas": text_sem["formula_candidates"],
        "code_blocks": text_sem["code_candidates"],

        "layout": layout,
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
        },

        "change_detection": compare,
        "request_evidence": request,

        "visual_objects": local_summary["objects"],
        "issues": local_summary["issues"],
        "local_interpretation": local_summary,

        "semantic_scope": {
            "can_explain_visible_content": True,
            "can_extract_text": True,
            "can_extract_links": bool(text_sem["urls"]),
            "can_extract_formula_candidates": bool(text_sem["formula_candidates"]),
            "can_detect_code_candidates": bool(text_sem["code_candidates"]),
            "can_detect_tables": bool(tables["detected"]),
            "can_detect_graph_geometry": geometry.get("graph_confidence", 0.0) > 0.0,
            "can_detect_diagram_geometry": geometry.get("diagram_confidence", 0.0) > 0.0,
            "can_compare_previous_image": compare["available"],
            "can_propose_change_evidence": request["asks_edit_or_fix"],
            "semantic_decision_owner": "QUANTUM_INTERPRETATION",
        },

        "confidence": confidence,
        "local_only": True,
        "paid_provider_used": False,
        "safe_for_interpretation": True,
    }


def _looks_like_screenshot(
    visual: Dict[str, Any],
    ocr: Dict[str, Any],
    layout: Dict[str, Any],
) -> bool:
    # Structural evidence only; never assert that any arbitrary photo is a screenshot.
    portrait = visual.get("orientation") == "portrait"
    many_text_boxes = len(ocr.get("items", [])) >= 8
    has_ui_like_regions = len(layout.get("regions", [])) >= 5
    return bool(many_text_boxes and (has_ui_like_regions or portrait))


def build_error_packet(reason: str) -> Dict[str, Any]:
    return {
        "version": VERSION,
        "source": PROVIDER,
        "provider_calls": 0,
        "input_type": "unknown",
        "error": reason,
        "confidence": 0.0,
        "local_only": True,
        "paid_provider_used": False,
        "safe_for_interpretation": False,
        "semantic_scope": {
            "semantic_decision_owner": "QUANTUM_INTERPRETATION",
        },
    }


async def analyze_image(
    path: str,
    state: Optional[Dict[str, Any]] = None,
    user_request: str = "",
    previous_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Existing async compatibility surface.

    Existing callers can keep:
        await analyze_image(path)

    The scan itself is local CPU work and therefore runs off the event loop.
    """
    return await asyncio.to_thread(
        scan_image,
        path,
        user_request=user_request,
        previous_path=previous_path,
        state=state,
    )


__all__ = [
    "VERSION",
    "scan_image",
    "analyze_image",
    "build_error_packet",
]
