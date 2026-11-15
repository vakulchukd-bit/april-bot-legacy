"""C_VIDEO: the single Premium room for video understanding and production.

Responsibilities kept in one room:
- classify video analysis / generation / editing requests;
- sample real frames for the normal multimodal April analyzer;
- generate MP4 through the asynchronous Alibaba Wan API;
- edit existing clips locally with ffmpeg (trim, crop, enhance, clip insert);
- emit the canonical VideoBlock via Premium_C_ARTIFACT_CONTRACT.

Binary output is intentionally returned to Premium_executor. The executor owns
user identity, message identity, Premium asset storage, PostgreSQL JSONB memory,
and the only API route. Temporary provider URLs never leave this module.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

API_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
MAX_VIDEO_BYTES = 25 * 1024 * 1024
MAX_VIDEO_INPUT_BYTES = 10 * 1024 * 1024
MAX_VIDEO_FRAMES = 8
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi"}


class CVideoError(RuntimeError):
    """Expected, safe-to-report video operation failure."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _build_data_uri(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64," + base64.b64encode(data).decode("ascii")


def decode_video_data_uri(value: Any) -> tuple[bytes, str] | None:
    """Decode a bounded video data URI without accepting arbitrary URL fetches."""
    raw = _text(value)
    match = re.match(r"^data:(video/[a-z0-9.+-]+);base64,([a-z0-9+/=\r\n]+)$", raw, re.I)
    if not match:
        return None
    try:
        data = base64.b64decode(re.sub(r"\s+", "", match.group(2)), validate=True)
    except Exception:
        return None
    if not data or len(data) > MAX_VIDEO_INPUT_BYTES:
        return None
    return data, match.group(1).lower()


def classify_video_request(text: str, attachments: Any = None) -> dict[str, Any]:
    """Create a deterministic intent plan; analysis never accidentally generates."""
    value = _text(text)
    low = value.lower().replace("ё", "е")
    items = [item for item in (attachments or []) if isinstance(item, dict)]
    videos = [item for item in items if _text(item.get("kind")).lower() == "video"]
    images = [item for item in items if _text(item.get("kind")).lower() == "image"]

    explicit_create = bool(re.search(
        r"(?iu)(?:созда\w*|сгенерир\w*|сними\w*|ожив\w*|анимир\w*|створ\w*|згенер\w*|generate|create|animate)"
        r".{0,100}(?:видео|ролик|клип|відео|video|clip)|"
        r"(?:video|clip).{0,70}(?:generate|create|animate)", low
    ))
    generic_create = bool(re.search(
        r"(?iu)(?:сдела\w*|зроб\w*|make).{0,100}(?:видео|ролик|клип|відео|video|clip)", low
    ))
    edit_words = bool(re.search(
        r"(?iu)(?:обреж\w*|обрез\w*|выреж\w*|укорот\w*|нареж\w*|склей\w*|соедин\w*|встав\w*|налож\w*|добав\w*.{0,24}(?:клип|фрагмент|видео)|"
        r"улучш\w*|лучше|ярче|повыс\w*.{0,24}кач\w*|стабилиз\w*|шум\w*|цветокоррек\w*|кадрир\w*|формат\w*|перемонтаж\w*|смонтир\w*|измен\w*|редактир\w*|передел\w*|"
        r"trim|crop|cut|splice|insert|overlay|enhance|improve|better|sharpen|denoise|stabili[sz]e|edit|montage)", low
    ))
    analyze_words = bool(re.search(
        r"(?iu)(?:анализир\w*|проанализир\w*|разбер\w*|опиш\w*|что\s+(?:происходит|на\s+видео)|содерж\w*|определи\w*|"
        r"analy[sz]e|describe|summari[sz]e|what\s+happens|inspect)", low
    ))

    # A source video plus an editing verb means EDIT, even when the user says
    # "сделай видео лучше". Explicit "создай/сгенерируй" still starts a new render.
    if explicit_create:
        action = "generate"
    elif videos and edit_words:
        action = "edit"
    elif generic_create and not videos:
        action = "generate"
    elif videos or analyze_words:
        action = "analyze"
    else:
        action = "none"

    return {
        "room": "C_VIDEO",
        "action": action,
        "has_video_input": bool(videos),
        "video_input_count": len(videos),
        "has_image_input": bool(images),
        "image_input_count": len(images),
        "requires_video_provider": action == "generate",
        "requires_ffmpeg": action == "edit" or action == "analyze",
        "analysis_method": "sampled_ordered_frames" if action == "analyze" else "not_applicable",
        "artifact_type": "video" if action in {"generate", "edit"} else "text",
    }


def extract_video_frames(
    video_bytes: bytes,
    filename: str = "input.mp4",
    *,
    max_frames: int = MAX_VIDEO_FRAMES,
) -> list[dict[str, Any]]:
    """Extract timestamped, ordered key frames for April's existing vision model."""
    if not isinstance(video_bytes, (bytes, bytearray)) or not video_bytes:
        return []
    if len(video_bytes) > MAX_VIDEO_INPUT_BYTES:
        raise CVideoError("VIDEO_INPUT_TOO_LARGE_FOR_ANALYSIS: attachment limit is 10 MiB")
    try:
        import imageio_ffmpeg
        from PIL import Image
    except Exception as exc:
        raise CVideoError("C_VIDEO_DEPENDENCIES_MISSING: install Pillow and imageio-ffmpeg") from exc

    frame_limit = max(1, min(MAX_VIDEO_FRAMES, int(max_frames or MAX_VIDEO_FRAMES)))
    suffix = Path(filename or "input.mp4").suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        suffix = ".mp4"
    frames: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="april-c-video-read-") as temp_dir:
        source = Path(temp_dir) / ("source" + suffix)
        pattern = str(Path(temp_dir) / "frame-%02d.jpg")
        source.write_bytes(bytes(video_bytes))
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        duration, _ = _probe_media(ffmpeg, source)
        # Sample the whole clip, not just the first 16 seconds. Long videos are
        # represented by evenly spaced chronological frames with a small end
        # margin so the final frame is included despite source frame-rate rounding.
        sample_interval = max(2.0, duration / max(1.0, frame_limit - 0.5))
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-vf", f"fps=1/{sample_interval:.3f},scale='min(1280,iw)':-2",
            "-frames:v", str(frame_limit), "-q:v", "4", "-y", pattern,
        ]
        result = subprocess.run(command, capture_output=True, timeout=120, check=False)
        if result.returncode != 0:
            details = (result.stderr or b"").decode("utf-8", errors="replace")[-400:]
            raise CVideoError("VIDEO_FRAME_EXTRACTION_FAILED: " + details)
        for index in range(1, frame_limit + 1):
            frame_path = Path(temp_dir) / f"frame-{index:02d}.jpg"
            if not frame_path.exists():
                break
            with Image.open(frame_path) as opened:
                image = opened.convert("RGB")
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=84, optimize=True)
            frames.append({
                "type": "input_image",
                "image_url": _build_data_uri(buffer.getvalue(), "image/jpeg"),
                "filename": f"{Path(filename or 'video').name}-frame-{index:02d}.jpg",
                "source_type": "video_frame",
                "mime_type": "image/jpeg",
                "frame_index": index,
                "timestamp_seconds": round((index - 1) * sample_interval, 2),
                "sequence_index": index - 1,
                "asset_role": "user_input",
            })
    return frames


def _translate_prompt_to_english(prompt: str) -> str:
    """Use the configured Premium provider to translate Wan's prompt only."""
    try:
        from blocks.Premium_provider_router import MODEL, _client_get
    except Exception:
        from blocks.provider_router import MODEL, _client_get
    model = os.getenv("APRIL_VIDEO_PROMPT_TRANSLATION_MODEL", MODEL).strip() or MODEL
    response = _client_get().responses.create(
        model=model,
        max_output_tokens=900,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": (
                "Translate the supplied video-generation instruction faithfully into concise natural English. "
                "Preserve subjects, actions, order, camera directions, style, timing and constraints. Do not answer "
                "or add details. Return JSON with exactly one string field named prompt."
            )}]},
            {"role": "user", "content": [{"type": "input_text", "text": json.dumps({"source": prompt}, ensure_ascii=False)}]},
        ],
    )
    try:
        parsed = json.loads(_text(getattr(response, "output_text", "")))
    except Exception as exc:
        raise CVideoError("C_VIDEO_PROMPT_TRANSLATION_INVALID") from exc
    translated = _text(parsed.get("prompt")) if isinstance(parsed, dict) else ""
    if not translated:
        raise CVideoError("C_VIDEO_PROMPT_TRANSLATION_EMPTY")
    return translated[:18000]


def _region_host(workspace_id: str, region: str) -> str:
    workspace = re.sub(r"[^A-Za-z0-9-]", "", workspace_id.strip())
    region = re.sub(r"[^A-Za-z0-9-]", "", region.strip())
    if not workspace or not region:
        raise CVideoError("Wan API configuration needs workspace ID and region.")
    return f"https://{workspace}.{region}.maas.aliyuncs.com"


def _request_json(
    url: str,
    *,
    method: str,
    api_key: str,
    body: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if body is not None:
        headers.update({"Content-Type": "application/json", "X-DashScope-Async": "enable"})
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.loads(response.read(4 * 1024 * 1024).decode("utf-8"))
            if not isinstance(parsed, dict):
                raise CVideoError("Wan returned an invalid JSON response.")
            return parsed
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read(64 * 1024).decode("utf-8", errors="replace"))
            detail = _text(payload.get("message") or payload.get("code"))
        except Exception:
            pass
        raise CVideoError(f"Wan API HTTP {exc.code}: {detail or 'request rejected'}") from exc
    except urllib.error.URLError as exc:
        raise CVideoError(f"Wan API connection failed: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise CVideoError(f"Wan API response failed: {type(exc).__name__}") from exc


def _download_video(url: str, *, max_bytes: int = MAX_VIDEO_BYTES) -> bytes:
    if not url.startswith("https://"):
        raise CVideoError("Wan returned a non-HTTPS video URL.")
    request = urllib.request.Request(url, headers={"User-Agent": "April-C-VIDEO/1.0"})
    chunks: list[bytes] = []
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            mime = (response.headers.get("Content-Type") or "video/mp4").split(";", 1)[0].lower()
            if mime not in {"video/mp4", "application/octet-stream", "video/quicktime"}:
                raise CVideoError(f"Wan returned unsupported video type: {mime}")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > max_bytes:
                raise CVideoError("Generated MP4 exceeds April's 25 MiB artifact limit.")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise CVideoError("Generated MP4 exceeds April's 25 MiB artifact limit.")
                chunks.append(chunk)
    except urllib.error.URLError as exc:
        raise CVideoError(f"Could not download generated MP4: {exc.reason}") from exc
    content = b"".join(chunks)
    if len(content) < 12 or b"ftyp" not in content[:64]:
        raise CVideoError("Wan result is not a valid MP4 file.")
    return content


async def generate_video(
    prompt: str,
    *,
    first_frame_data_uri: str = "",
    duration: int = 5,
    resolution: str = "720P",
    ratio: str = "adaptive",
    audio: bool = True,
    progress_callback: Callable[[str], Any] | None = None,
    timeout_seconds: int = 285,
    source_language: str = "",
) -> dict[str, Any]:
    """Create a video through Wan 3.0 async API and return persistable MP4 bytes."""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    workspace_id = os.getenv("DASHSCOPE_WORKSPACE_ID", "").strip()
    region = os.getenv("DASHSCOPE_REGION", "ap-southeast-1").strip()
    model = os.getenv("APRIL_PREMIUM_VIDEO_MODEL", "wan3.0-video").strip()
    if not api_key or not workspace_id:
        raise CVideoError("Видеогенератор не подключён: настройте DASHSCOPE_API_KEY и DASHSCOPE_WORKSPACE_ID.")
    if model not in {"wan3.0-video", "wan3.0-video-prime"}:
        raise CVideoError("APRIL_PREMIUM_VIDEO_MODEL must be wan3.0-video or wan3.0-video-prime.")
    clean_prompt = _text(prompt)[:18000]
    if not clean_prompt:
        raise CVideoError("Video prompt is empty.")
    source_language = _text(source_language).lower().replace("_", "-").split("-", 1)[0]
    prompt_language = source_language or "en"
    warning = ""
    translation_enabled = os.getenv("APRIL_VIDEO_PROMPT_TRANSLATE", "1").strip().lower() not in {"0", "false", "no", "off"}
    if source_language not in {"en", "zh"} and translation_enabled:
        try:
            clean_prompt = await asyncio.to_thread(_translate_prompt_to_english, clean_prompt)
            prompt_language = "en"
        except Exception as exc:
            warning = f"Prompt translation unavailable: {type(exc).__name__}"
    duration = max(2, min(30, int(duration or 5)))
    resolution = resolution if resolution in {"480P", "720P", "1080P"} else "720P"
    ratio = ratio if ratio in {"adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"} else "adaptive"

    api_base = _region_host(workspace_id, region)
    input_payload: dict[str, Any] = {"prompt": clean_prompt}
    if first_frame_data_uri:
        if not first_frame_data_uri.startswith("data:image/") or ";base64," not in first_frame_data_uri:
            raise CVideoError("Image-to-video source must be a base64 image data URI.")
        input_payload["media"] = [{"type": "first_frame", "url": first_frame_data_uri}]
    request_body = {
        "model": model,
        "input": input_payload,
        "parameters": {
            "resolution": resolution, "ratio": ratio, "duration": duration,
            "audio": bool(audio), "prompt_extend": True, "watermark": False,
        },
    }
    if progress_callback:
        progress_callback("generating")
    created = await asyncio.to_thread(
        _request_json, api_base + API_PATH, method="POST", api_key=api_key, body=request_body,
    )
    output = created.get("output") if isinstance(created.get("output"), dict) else {}
    task_id = _text(output.get("task_id"))
    if not task_id:
        raise CVideoError(_text(created.get("message") or created.get("code")) or "Wan did not return task_id.")

    started = time.monotonic()
    status = "PENDING"
    task_url = api_base + "/api/v1/tasks/" + task_id
    while time.monotonic() - started < max(30, int(timeout_seconds or 285)):
        await asyncio.sleep(15)
        result = await asyncio.to_thread(_request_json, task_url, method="GET", api_key=api_key)
        task_output = result.get("output") if isinstance(result.get("output"), dict) else {}
        status = _text(task_output.get("task_status") or "UNKNOWN").upper()
        if status == "SUCCEEDED":
            video_url = _text(task_output.get("video_url"))
            if not video_url:
                raise CVideoError("Wan task succeeded but did not return video_url.")
            if progress_callback:
                progress_callback("saving")
            content = await asyncio.to_thread(_download_video, video_url)
            usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
            return {
                "success": True, "operation": "generate", "edit_operations": [],
                "video_bytes": content, "mime_type": "video/mp4",
                "filename": f"april-video-{task_id[:8]}.mp4",
                "provider": "Alibaba Cloud Model Studio", "model": model, "task_id": task_id,
                "prompt": clean_prompt, "prompt_language": prompt_language,
                "prompt_translation_warning": warning,
                "duration_seconds": float(usage.get("output_video_duration") or usage.get("duration") or duration),
                "fps": int(usage.get("fps") or 30),
                "resolution": f"{usage.get('SR')}P" if usage.get("SR") else resolution,
                "ratio": _text(usage.get("ratio") or ratio), "audio": bool(audio),
            }
        if status in {"FAILED", "CANCELED", "UNKNOWN"}:
            raise CVideoError(_text(task_output.get("message") or task_output.get("code")) or f"Wan task {status.lower()}.")
        if progress_callback:
            progress_callback("generating")
    raise CVideoError(f"Wan video task timed out after {timeout_seconds} seconds (task {task_id}).")


def _extract_attachment_videos(attachments: Any) -> list[tuple[str, bytes, str]]:
    result: list[tuple[str, bytes, str]] = []
    for item in attachments or []:
        if not isinstance(item, dict) or _text(item.get("kind")).lower() != "video":
            continue
        decoded = decode_video_data_uri(item.get("video_data_uri") or item.get("_video_data_uri") or item.get("data_uri"))
        if decoded:
            data, mime = decoded
            result.append((_text(item.get("filename") or f"input-{len(result) + 1}.mp4"), data, mime))
    return result


def _parse_seconds(value: str) -> float:
    raw = _text(value).replace(",", ".")
    if ":" in raw:
        parts = raw.split(":")
        try:
            values = [float(part) for part in parts]
            total = 0.0
            for part in values:
                total = total * 60 + part
            return max(0.0, total)
        except ValueError:
            return 0.0
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def _edit_plan(request_text: str, video_count: int) -> dict[str, Any]:
    low = _text(request_text).lower().replace("ё", "е")
    trim_start = 0.0
    trim_end: float | None = None
    time_match = re.search(
        r"(?iu)(?:с|от|from)\s*(\d+(?:[.,]\d+)?(?::\d+(?:[.,]\d+)?){0,2})\s*(?:секунд\w*|сек\.?|s)?\s*(?:по|до|to|through)\s*(\d+(?:[.,]\d+)?(?::\d+(?:[.,]\d+)?){0,2})",
        low,
    )
    if time_match:
        trim_start = _parse_seconds(time_match.group(1))
        trim_end = _parse_seconds(time_match.group(2))
    else:
        until_match = re.search(r"(?iu)(?:до|to)\s*(\d+(?:[.,]\d+)?)\s*(?:секунд\w*|сек\.?|seconds?|s)\b", low)
        if until_match and re.search(r"(?iu)обреж|обрез|укорот|trim|cut", low):
            trim_end = _parse_seconds(until_match.group(1))
        start_match = re.search(r"(?iu)(?:начиная\s+с|начни\s+с|start\s+at)\s*(\d+(?:[.,]\d+)?)\s*(?:секунд\w*|сек\.?|seconds?|s)?", low)
        if start_match:
            trim_start = _parse_seconds(start_match.group(1))

    crop_ratio = ""
    if re.search(r"(?iu)(?:9\s*:\s*16|вертикальн\w*|портретн\w*|сторис|reels?|тик.?ток|vertical)", low):
        crop_ratio = "9:16"
    elif re.search(r"(?iu)(?:16\s*:\s*9|горизонтальн\w*|landscape|widescreen)", low):
        crop_ratio = "16:9"
    elif re.search(r"(?iu)(?:1\s*:\s*1|квадратн\w*|square)", low):
        crop_ratio = "1:1"

    stabilize = bool(re.search(r"(?iu)(?:стабилиз\w*|stabili[sz]e)", low))
    enhance = bool(re.search(r"(?iu)(?:улучш\w*|повыс\w*.{0,25}кач\w*|четк\w*|резк\w*|убери\s+шум|enhance|improve|sharpen|denoise)", low))
    trim_requested = bool(re.search(r"(?iu)(?:обреж|обрез|выреж|укорот|trim|cut)", low)) or trim_end is not None or trim_start > 0
    insert_requested = bool(re.search(r"(?iu)(?:встав\w*|добав\w*.{0,30}(?:клип|фрагмент|видео)|налож\w*|insert|overlay|picture.?in.?picture|pip)", low))
    overlay_mode = bool(re.search(r"(?iu)(?:поверх|налож\w*|в\s+угол|в\s+углу|картин\w*\s+в\s+картин\w*|оверле\w*|overlay|picture.?in.?picture|pip)", low))
    insert_position_match = re.search(
        r"(?iu)(?:после|на\s+отметке|в\s+момент|after|at\s+second|at)\s*(\d+(?:[.,]\d+)?)"
        r"|на\s+(\d+(?:[.,]\d+)?)\s*секунд\w*",
        low,
    )
    insert_position = _parse_seconds(next((group for group in insert_position_match.groups() if group), "0")) if insert_position_match else None
    if insert_position is None and re.search(r"(?iu)(?:в\s+самое?\s+начало|в\s+начало|с\s+начала|from\s+the\s+beginning)", low):
        insert_position = 0.0
    elif insert_position is None and re.search(r"(?iu)(?:в\s+самый?\s+конец|в\s+конец|в\s+конце|at\s+the\s+end)", low):
        insert_position = 1e9
    return {
        "trim_start": trim_start,
        "trim_end": trim_end,
        "trim_requested": trim_requested,
        "crop_ratio": crop_ratio,
        "enhance": enhance,
        "stabilize": stabilize,
        "insert_requested": insert_requested,
        "insert_mode": "picture_in_picture" if overlay_mode else "timeline_splice",
        "insert_position": insert_position,
        "requires_second_clip": insert_requested and video_count < 2,
    }


def _crop_filter(ratio: str) -> str:
    if ratio == "9:16":
        return "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'"
    if ratio == "16:9":
        return "crop='min(iw,ih*16/9)':'min(ih,iw*9/16)'"
    if ratio == "1:1":
        return "crop='min(iw,ih)':'min(iw,ih)'"
    return ""


def _probe_media(ffmpeg: str, path: Path) -> tuple[float, bool]:
    """Read duration/audio presence from ffmpeg's input header without rendering."""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True, timeout=30, check=False,
    )
    details = (result.stderr or b"").decode("utf-8", errors="replace")
    duration_match = re.search(r"Duration:\s*(\d{2}:\d{2}:\d{2}(?:\.\d+)?)", details)
    if not duration_match:
        raise CVideoError(f"Could not read video duration: {path.name}")
    return _parse_seconds(duration_match.group(1)), bool(re.search(r"\bAudio:\s*", details))


def edit_video(
    request_text: str,
    attachments: Any,
    *,
    progress_callback: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Apply real MP4 trim/crop/enhancement plus timeline or picture-in-picture insertion."""
    sources = _extract_attachment_videos(attachments)
    if not sources:
        raise CVideoError("Для монтажа не найден исходный MP4. Прикрепите видео или восстановите его из этого диалога.")
    if any(len(source[1]) > MAX_VIDEO_INPUT_BYTES for source in sources):
        raise CVideoError("Каждый исходный видеоклип должен быть не больше 10 MiB.")
    plan = _edit_plan(request_text, len(sources))
    if plan["requires_second_clip"]:
        raise CVideoError("Для вставки второго клипа прикрепите два видео: основное и вставляемое.")
    if not any((plan["trim_requested"], plan["crop_ratio"], plan["enhance"], plan["stabilize"], plan["insert_requested"])):
        # A generic edit request is safely interpreted as enhancement, not as a no-op.
        plan["enhance"] = True

    try:
        import imageio_ffmpeg
    except Exception as exc:
        raise CVideoError("C_VIDEO_DEPENDENCIES_MISSING: install imageio-ffmpeg.") from exc
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    edit_operations: list[dict[str, Any]] = []
    filters: list[str] = []
    if plan["crop_ratio"]:
        filters.append(_crop_filter(plan["crop_ratio"]))
        edit_operations.append({"operation": "crop", "ratio": plan["crop_ratio"], "anchor": "center"})
    if plan["stabilize"]:
        filters.insert(0, "deshake=rx=16:ry=16:edge=mirror")
        edit_operations.append({"operation": "stabilize", "method": "ffmpeg-deshake"})
    if plan["enhance"]:
        filters.extend([
            "hqdn3d=1.5:1.5:6:6",
            "eq=contrast=1.04:saturation=1.06:brightness=0.005",
            "unsharp=5:5:0.55:3:3:0.25",
        ])
        edit_operations.append({"operation": "enhance", "denoise": True, "sharpen": True, "color_adjustment": True})
    if plan["trim_requested"]:
        edit_operations.append({"operation": "trim", "start_seconds": plan["trim_start"], "end_seconds": plan["trim_end"]})
    if plan["insert_requested"]:
        if plan["insert_mode"] == "picture_in_picture":
            edit_operations.append({"operation": "insert_overlay", "mode": "picture_in_picture", "description": "Second clip overlays the main clip at the lower-right corner."})
        else:
            edit_operations.append({"operation": "insert_clip", "mode": "timeline_splice", "description": "Second clip is inserted into the main clip timeline."})

    output_duration: float | None = None
    output_has_audio = True
    with tempfile.TemporaryDirectory(prefix="april-c-video-edit-") as temp_dir:
        temp = Path(temp_dir)
        main_suffix = Path(sources[0][0]).suffix.lower()
        if main_suffix not in VIDEO_EXTENSIONS:
            main_suffix = ".mp4"
        main_path = temp / ("main" + main_suffix)
        output_path = temp / "april-edited.mp4"
        main_path.write_bytes(sources[0][1])
        command = [ffmpeg, "-hide_banner", "-loglevel", "error"]
        if plan["insert_requested"]:
            insert_suffix = Path(sources[1][0]).suffix.lower()
            if insert_suffix not in VIDEO_EXTENSIONS:
                insert_suffix = ".mp4"
            insert_path = temp / ("insert" + insert_suffix)
            insert_path.write_bytes(sources[1][1])
            main_duration, main_has_audio = _probe_media(ffmpeg, main_path)
            insert_duration, insert_has_audio = _probe_media(ffmpeg, insert_path)
            if plan["trim_end"] is not None:
                source_duration = plan["trim_end"] - plan["trim_start"]
                if source_duration <= 0:
                    raise CVideoError("Время обрезки указано неверно: конечная отметка должна быть позже начальной.")
                effective_main_duration = min(source_duration, max(0.0, main_duration - plan["trim_start"]))
            else:
                effective_main_duration = max(0.0, main_duration - plan["trim_start"])
            if effective_main_duration <= 0 or insert_duration <= 0:
                raise CVideoError("Один из клипов имеет нулевую длительность.")
            position = plan.get("insert_position")
            if position is None:
                position = effective_main_duration / 2.0
            position = max(0.0, min(float(position), effective_main_duration))
            output_duration = effective_main_duration + insert_duration
            main_video_trim = f"trim=start={plan['trim_start']:.3f}"
            if plan["trim_end"] is not None:
                main_video_trim += f":end={plan['trim_end']:.3f}"
            main_effects = ",".join(filters)
            main_video_chain = f"{main_video_trim},setpts=PTS-STARTPTS"
            if main_effects:
                main_video_chain += "," + main_effects
            if plan["crop_ratio"] == "9:16":
                canvas_w, canvas_h = 720, 1280
            elif plan["crop_ratio"] == "1:1":
                canvas_w, canvas_h = 1080, 1080
            else:
                canvas_w, canvas_h = 1280, 720
            normalize = (
                f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
                f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
            )
            if plan["insert_mode"] == "picture_in_picture":
                command += ["-i", str(main_path), "-i", str(insert_path)]
                at = position if plan.get("insert_position") is not None else 2.0
                insert_end = min(effective_main_duration, at + min(5.0, insert_duration))
                output_duration = effective_main_duration
                filter_complex = (
                    f"[0:v]{main_video_chain}[base];"
                    f"[1:v]setpts=PTS-STARTPTS,scale=w='min(480,iw)':h=-2[insert];"
                    f"[base][insert]overlay=x=W-w-24:y=H-h-24:"
                    f"enable='between(t,{at:.3f},{insert_end:.3f})':eof_action=pass[v]"
                )
                command += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "0:a?"]
                edit_operations[-1].update({"start_seconds": at, "duration_seconds": max(0.0, insert_end - at)})
                output_has_audio = main_has_audio
            else:
                command += ["-i", str(main_path), "-i", str(insert_path)]
                # Normalize both clips to a common canvas/fps so concat is valid
                # even when the source aspect ratios or frame rates differ.
                base = f"[0:v]{main_video_chain},{normalize},split=2[main_pre_src][main_post_src];"
                inserted = f"[1:v]{normalize},setpts=PTS-STARTPTS[inserted];"
                if position <= 0.001:
                    video_graph = (
                        f"[0:v]{main_video_chain},{normalize}[main_tail];" + inserted +
                        f"[inserted][main_tail]concat=n=2:v=1:a=0[v]"
                    )
                elif position >= effective_main_duration - 0.001:
                    video_graph = (
                        f"[0:v]{main_video_chain},{normalize}[main_head];" + inserted +
                        f"[main_head][inserted]concat=n=2:v=1:a=0[v]"
                    )
                else:
                    video_graph = (
                        base + inserted +
                        f"[main_pre_src]trim=end={position:.3f},setpts=PTS-STARTPTS[pre];"
                        f"[main_post_src]trim=start={position:.3f},setpts=PTS-STARTPTS[post];"
                        f"[pre][inserted][post]concat=n=3:v=1:a=0[v]"
                    )
                if main_has_audio:
                    main_audio_trim = f"atrim=start={plan['trim_start']:.3f}"
                    if plan["trim_end"] is not None:
                        main_audio_trim += f":end={plan['trim_end']:.3f}"
                    if position <= 0.001:
                        audio_graph = (
                            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={insert_duration:.3f}[insert_audio];"
                            if insert_has_audio else
                            f"aevalsrc=0|0:s=48000:d={insert_duration:.3f}[insert_audio];"
                        )
                        audio_graph += f"[0:a]{main_audio_trim},asetpts=PTS-STARTPTS[main_audio];[insert_audio][main_audio]concat=n=2:v=0:a=1[a]"
                    elif position >= effective_main_duration - 0.001:
                        audio_graph = (
                            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={insert_duration:.3f}[insert_audio];"
                            if insert_has_audio else
                            f"aevalsrc=0|0:s=48000:d={insert_duration:.3f}[insert_audio];"
                        )
                        audio_graph += f"[0:a]{main_audio_trim},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[main_audio];[main_audio][insert_audio]concat=n=2:v=0:a=1[a]"
                    else:
                        if insert_has_audio:
                            inserted_audio = f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,apad,atrim=duration={insert_duration:.3f}[insert_audio];"
                        else:
                            inserted_audio = f"aevalsrc=0|0:s=48000:d={insert_duration:.3f}[insert_audio];"
                        audio_graph = (
                            f"[0:a]{main_audio_trim},aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,asplit=2[a_pre_src][a_post_src];"
                            f"[a_pre_src]atrim=end={position:.3f},asetpts=PTS-STARTPTS[a_pre];"
                            f"[a_post_src]atrim=start={position:.3f},asetpts=PTS-STARTPTS[a_post];"
                            + inserted_audio +
                            "[a_pre][insert_audio][a_post]concat=n=3:v=0:a=1[a]"
                        )
                    filter_complex = video_graph + ";" + audio_graph
                    command += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]
                    output_has_audio = True
                else:
                    command += ["-filter_complex", video_graph, "-map", "[v]"]
                    output_has_audio = False
                edit_operations[-1].update({"position_seconds": position, "inserted_duration_seconds": insert_duration})
            duration = output_duration
        else:
            if plan["trim_start"] > 0:
                command += ["-ss", f"{plan['trim_start']:.3f}"]
            command += ["-i", str(main_path)]
            if plan["trim_end"] is not None:
                duration = plan["trim_end"] - plan["trim_start"]
                if duration <= 0:
                    raise CVideoError("Время обрезки указано неверно: конечная отметка должна быть позже начальной.")
                command += ["-t", f"{duration:.3f}"]
            else:
                duration = None
            if filters:
                command += ["-vf", ",".join(filters)]
            output_duration = duration
            _, output_has_audio = _probe_media(ffmpeg, main_path)

        command += [
            "-map_metadata", "0", "-c:v", "libx264", "-preset", os.getenv("APRIL_VIDEO_EDIT_PRESET", "veryfast"),
            "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        ]
        if output_has_audio:
            command += ["-c:a", "aac", "-b:a", "128k"]
        if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice":
            command += ["-r", "30"]
        command += ["-y", str(output_path)]
        if progress_callback:
            progress_callback("rendering")
        result = subprocess.run(command, capture_output=True, timeout=int(os.getenv("APRIL_VIDEO_EDIT_TIMEOUT", "240") or 240), check=False)
        if result.returncode != 0 or not output_path.exists():
            details = (result.stderr or b"").decode("utf-8", errors="replace")[-600:]
            raise CVideoError("VIDEO_EDIT_RENDER_FAILED: " + (details or "ffmpeg did not create an output file."))
        content = output_path.read_bytes()
        if not content or len(content) < 12 or b"ftyp" not in content[:64]:
            raise CVideoError("Edited output is not a valid MP4 file.")
        if len(content) > MAX_VIDEO_BYTES:
            raise CVideoError("Edited MP4 exceeds April's 25 MiB artifact storage limit.")

    if progress_callback:
        progress_callback("saving")
    filename = f"april-edited-video-{int(time.time())}.mp4"
    return {
        "success": True, "operation": "edit", "edit_operations": edit_operations,
        "video_bytes": content, "mime_type": "video/mp4", "filename": filename,
        "provider": "April C_VIDEO / FFmpeg", "model": "ffmpeg-local",
        "prompt": _text(request_text)[:1200], "prompt_language": "local",
        "duration_seconds": output_duration if output_duration is not None else None,
        "fps": 30 if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice" else None,
        "resolution": (
            "720x1280" if plan["crop_ratio"] == "9:16" else
            "1080x1080" if plan["crop_ratio"] == "1:1" else
            "1280x720" if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice" else
            "source-preserving"
        ),
        "ratio": plan["crop_ratio"] or ("16:9" if plan["insert_requested"] and plan["insert_mode"] == "timeline_splice" else "source"),
        "audio": output_has_audio, "insert_mode": plan.get("insert_mode", ""), "task_id": "",
    }


async def execute_video_operation(
    plan: dict[str, Any],
    request_text: str,
    attachments: Any,
    visual_context: Any = None,
    *,
    progress_callback: Callable[[str], Any] | None = None,
    source_language: str = "",
    timeout_seconds: int = 285,
) -> dict[str, Any]:
    """Single entry point used by Premium_executor after Interpretation selects C_VIDEO."""
    action = _text(plan.get("action")).lower()
    if action == "generate":
        first_frame = ""
        for item in visual_context or []:
            if not isinstance(item, dict) or item.get("recalled_from_memory"):
                continue
            uri = _text(item.get("image_url") or item.get("data_uri"))
            if uri.startswith("data:image/") and ";base64," in uri:
                first_frame = uri
                break
        prompt = (
            "Create a coherent, polished video following the user direction. Keep subjects consistent, "
            "use natural motion and intentional camera movement, preserve the requested sequence and style, "
            "avoid captions/text unless explicitly requested. Direction: " + _text(request_text)[:12000]
        )
        duration_match = re.search(r"(?iu)(2[0-9]|30|[2-9]|1[0-9])\s*(?:секунд|сек|seconds?|s)\b", _text(request_text))
        duration = int(duration_match.group(1)) if duration_match else int(os.getenv("APRIL_VIDEO_DEFAULT_DURATION", "5") or 5)
        ratio = "9:16" if re.search(r"(?iu)(?:вертикальн|портретн|сторис|reel|тик.?ток|vertical|portrait)", request_text) else (
            "1:1" if re.search(r"(?iu)(?:квадратн|square)", request_text) else "adaptive"
        )
        audio = not bool(re.search(r"(?iu)(?:без\s+звука|без\s+аудио|mute|no\s+audio|silent)", request_text))
        return await generate_video(
            prompt, first_frame_data_uri=first_frame, duration=duration,
            resolution=os.getenv("APRIL_VIDEO_RESOLUTION", "720P"), ratio=ratio,
            audio=audio, progress_callback=progress_callback,
            timeout_seconds=timeout_seconds, source_language=source_language,
        )
    if action == "edit":
        return await asyncio.to_thread(edit_video, request_text, attachments, progress_callback=progress_callback)
    raise CVideoError(f"Unsupported C_VIDEO action: {action or 'none'}")


def build_video_render_block(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a VideoBlock by projecting a C_VIDEO artifact through the canonical contract."""
    from blocks.Premium_C_ARTIFACT_CONTRACT import create_artifact, _artifact_canonical_render_blocks

    clean_payload = {key: value for key, value in dict(payload or {}).items() if value is not None}
    artifact = create_artifact(
        "video",
        "C_VIDEO",
        {
            "title": _text(clean_payload.get("filename") or "April video"),
            "answer": _text(clean_payload.get("description") or "Video artifact created by April."),
            "renderer": "VideoBlock",
            "viewer": "VideoBlock",
            "payload": clean_payload,
            "machine_only": False,
            "human_visible": True,
            "priority": 90,
            "complexity": "balanced",
            "layout": "single",
            "capabilities": ["video", "download", "share", "playback"],
            "artifact_outputs": ["video/mp4"],
        },
    )
    blocks = _artifact_canonical_render_blocks(artifact)
    if not blocks:
        raise CVideoError("C_VIDEO could not project its artifact into SceneContract.")
    block = blocks[0]
    block["final_output"] = True
    block["source_room"] = "C_VIDEO"
    return block


class CVideoRoom:
    """Canonical Premium video room. It does not own identity or persistence."""

    room_id = "C_VIDEO"
    artifact_type = "video"
    capabilities = (
        "video", "video_analysis", "video_generation", "video_editing",
        "video_render", "timeline_editing", "media_processing", "download", "share",
    )

    @staticmethod
    def interpret(request_text: str, attachments: Any = None) -> dict[str, Any]:
        return classify_video_request(request_text, attachments)

    @staticmethod
    def extract_frames(video_bytes: bytes, filename: str = "input.mp4", *, max_frames: int = MAX_VIDEO_FRAMES) -> list[dict[str, Any]]:
        return extract_video_frames(video_bytes, filename, max_frames=max_frames)

    @staticmethod
    async def execute(plan: dict[str, Any], request_text: str, attachments: Any, visual_context: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await execute_video_operation(plan, request_text, attachments, visual_context, **kwargs)

    @staticmethod
    def render(payload: dict[str, Any]) -> dict[str, Any]:
        return build_video_render_block(payload)


__all__ = [
    "CVideoError", "CVideoRoom", "MAX_VIDEO_BYTES", "MAX_VIDEO_FRAMES",
    "VIDEO_EXTENSIONS", "build_video_render_block", "classify_video_request",
    "decode_video_data_uri", "edit_video", "execute_video_operation",
    "extract_video_frames", "generate_video",
]
