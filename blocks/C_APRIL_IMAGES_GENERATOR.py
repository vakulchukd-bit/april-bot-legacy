# =====================================================
# APRIL IMAGES GENERATION
# =====================================================
"""Canonical April image-generation engine backed by OpenAI GPT Image 2.

Route:
    April Bot -> Interpretation -> Provider -> C_APRIL_IMAGES_GENERATOR
      -> C_ARTIFACT_CONTRACT -> GalleryBlock / April Web

Contract rules:
    * OpenAI Provider remains the semantic authority.
    * C_APRIL_IMAGES_GENERATOR is the sole image producer for this route.
    * The image generator receives the same-turn user request together with the
      OpenAI structured visual plan and sends that combined semantic payload to
      ``gpt-image-2`` without adding local artistic styles or unrelated scene
      content.
    * GPT Image 2 returns base64 image data; this module decodes the bytes,
      normalizes the requested Web size when necessary, validates the PNG and
      forwards the resulting bytes through the existing C_ARTIFACT_CONTRACT.
    * Diagnostic logging is observer-only and never changes image bytes.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from PIL import Image

from blocks.C_ARTIFACT_CONTRACT import (
    UniversalArtifactContract,
    build_universal_contract,
    create_artifact,
)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


@dataclass
class ImageGenerationResult:
    image_bytes: bytes
    mime_type: str
    width: int
    height: int
    backend: str
    prompt: str
    artifact: dict[str, Any]
    contract: UniversalArtifactContract


class AprilImagesGenerator:
    """The only image producer between Provider and C_ARTIFACT_CONTRACT."""

    ENGINE_NAME = "GPT Image 2.0"
    ENGINE_VERSION = "2.0.0"
    MODEL = "gpt-image-2"
    BACKEND = "openai_gpt_image_2"

    DEFAULT_SIZE = (512, 512)
    MIN_SIZE = 256
    MAX_SIZE = 1536

    # GPT Image 2 minimum output area is 655,360 pixels.  April's Web route
    # remains 512x512 by decoding the model's compliant raster and then
    # downsampling it to the requested canonical Web size.
    API_MIN_PIXELS = 655_360
    API_MAX_PIXELS = 8_294_400
    API_MAX_EDGE = 3_840

    # Official GPT Image 2 standard rates used for local cost diagnostics.
    TEXT_INPUT_USD_PER_MILLION = 2.50
    IMAGE_INPUT_USD_PER_MILLION = 4.00
    IMAGE_OUTPUT_USD_PER_MILLION = 15.00
    LOW_1024_IMAGE_ESTIMATE_USD = 0.006

    MAX_SEMANTIC_PROMPT_TOKENS = 12_000

    def __init__(self) -> None:
        self.engine_name = self.ENGINE_NAME
        self.engine_version = self.ENGINE_VERSION

    # -------------------------------------------------
    # OpenAI client / configuration
    # -------------------------------------------------

    @classmethod
    def _api_key(cls) -> str:
        return os.getenv("OPENAI_API_KEY", "").strip()

    @classmethod
    def _client(cls):
        if OpenAI is None:
            raise RuntimeError("APRIL_IMAGES_OPENAI_SDK_NOT_INSTALLED")
        api_key = cls._api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")
        # Do not cache a client globally: the existing Provider path and the
        # generator use the same environment-backed key without sharing state.
        return OpenAI(api_key=api_key)

    @classmethod
    def _model_source(cls) -> str:
        return cls.MODEL

    @classmethod
    def _model_path(cls) -> str:
        """Compatibility accessor kept for old callers; GPT Image 2 is API-backed."""
        return ""

    @classmethod
    def _device(cls) -> str:
        return "openai_api"

    @classmethod
    def _dtype(cls):
        return None

    @classmethod
    def _can_initialize(cls) -> bool:
        return OpenAI is not None and bool(cls._api_key())

    @classmethod
    def _require_backend(cls) -> None:
        if OpenAI is None:
            raise RuntimeError("APRIL_IMAGES_OPENAI_SDK_NOT_INSTALLED")
        if not cls._api_key():
            raise RuntimeError("OPENAI_API_KEY_NOT_CONFIGURED")

    # -------------------------------------------------
    # Semantic input normalization
    # -------------------------------------------------

    @staticmethod
    def _safe_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return str(value)

    @classmethod
    def _extract_semantic_prompt(cls, value: Any, *, _depth: int = 0) -> str:
        """Extract text without passing serialized artifacts or data URIs."""
        if _depth > 5 or value is None:
            return ""

        if isinstance(value, dict):
            preferred = (
                "prompt",
                "description",
                "visual_prompt",
                "image_prompt",
                "visual_generation_prompt",
                "image",
                "visual",
                "visual_context",
                "scene",
                "subject",
                "request",
                "title",
                "summary",
                "answer",
                "content",
                "alt",
            )
            for key in preferred:
                if key not in value:
                    continue
                candidate = cls._extract_semantic_prompt(value.get(key), _depth=_depth + 1)
                if candidate:
                    return candidate
            return ""

        if isinstance(value, (list, tuple)):
            parts: list[str] = []
            for item in value[:24]:
                candidate = cls._extract_semantic_prompt(item, _depth=_depth + 1)
                if candidate:
                    parts.append(candidate)
            return " ".join(dict.fromkeys(parts)).strip()

        text = cls._safe_text(value).strip()
        if not text:
            return ""
        text = re.sub(r"^```(?:json|text|xml)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()
        if re.match(r"^data:image/[^;]+;base64,", text, flags=re.IGNORECASE):
            return ""
        return " ".join(text.split())

    @classmethod
    def _clean_prompt(cls, prompt: Any) -> str:
        text = cls._extract_semantic_prompt(prompt)
        if not text:
            raise ValueError("APRIL_IMAGES_EMPTY_PROMPT")
        if len(text.split()) > cls.MAX_SEMANTIC_PROMPT_TOKENS:
            raise ValueError(
                f"APRIL_IMAGES_PROMPT_TOO_LONG:{len(text.split())}>{cls.MAX_SEMANTIC_PROMPT_TOKENS}"
            )
        return text

    @classmethod
    def _compact_json(cls, value: Any, limit: int = 12_000) -> str:
        if value in (None, "", [], {}):
            return ""
        try:
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        except Exception:
            text = cls._safe_text(value)
        return text[:limit]

    @classmethod
    def _semantic_plan_for_generation(cls, spec: dict[str, Any]) -> str:
        """Keep only same-turn OpenAI visual data; no render-profile injection."""
        raw_plan = spec.get("openai_structured_visual_plan_raw")
        plan_semantic = cls._clean_prompt(
            spec.get("openai_structured_visual_plan_semantic")
            or spec.get("prompt")
            or ""
        )
        visual_context = spec.get("visual_context")

        parts: list[str] = []
        request_anchor = cls._safe_text(spec.get("request_anchor") or "").strip()
        if request_anchor:
            parts.append(f"User request: {request_anchor}")

        parts.append(f"OpenAI visual meaning: {plan_semantic}")

        if isinstance(visual_context, dict) and visual_context:
            encoded_context = cls._compact_json(visual_context, 8_000)
            if encoded_context:
                parts.append(f"OpenAI visual constraints: {encoded_context}")

        if isinstance(raw_plan, dict):
            # Preserve structured same-turn visual fields when they contain
            # information beyond the already extracted semantic description.
            nontrivial_keys = {
                str(key) for key in raw_plan.keys()
                if str(key) not in {"description", "prompt", "visual_prompt", "image_prompt"}
            }
            if nontrivial_keys:
                encoded_plan = cls._compact_json(raw_plan, 8_000)
                if encoded_plan:
                    parts.append(f"OpenAI structured visual plan: {encoded_plan}")

        parts.append(
            "Render the supplied visual content faithfully. Do not replace the requested subject, "
            "do not add unrelated subjects or environments, and do not invent missing scene elements."
        )
        return "\n".join(parts)

    @classmethod
    def _compose_prompt(cls, prompt: str, spec: Optional[dict[str, Any]] = None) -> str:
        """Compose only user request + same-turn OpenAI visual meaning."""
        if not isinstance(spec, dict):
            return cls._clean_prompt(prompt)
        composed = cls._semantic_plan_for_generation(spec)
        if composed:
            return composed
        return cls._clean_prompt(prompt)

    # -------------------------------------------------
    # Size / quality
    # -------------------------------------------------

    @classmethod
    def _parse_size(cls, size: Any) -> tuple[int, int]:
        if isinstance(size, (tuple, list)) and len(size) == 2:
            try:
                width, height = int(size[0]), int(size[1])
            except (TypeError, ValueError):
                width, height = cls.DEFAULT_SIZE
        else:
            match = re.match(r"^\s*(\d{2,5})\s*x\s*(\d{2,5})\s*$", str(size or ""))
            if match:
                width, height = int(match.group(1)), int(match.group(2))
            else:
                width, height = cls.DEFAULT_SIZE
        width = max(cls.MIN_SIZE, min(cls.MAX_SIZE, width))
        height = max(cls.MIN_SIZE, min(cls.MAX_SIZE, height))
        width = max(16, (width // 16) * 16)
        height = max(16, (height // 16) * 16)
        return width, height

    @classmethod
    def _api_generation_size(cls, width: int, height: int) -> tuple[int, int]:
        width, height = cls._parse_size((width, height))
        if max(width, height) > cls.API_MAX_EDGE:
            raise ValueError("APRIL_IMAGES_GPT_IMAGE_SIZE_EDGE_INVALID")
        ratio = max(width, height) / max(1, min(width, height))
        if ratio > 3.0:
            raise ValueError("APRIL_IMAGES_GPT_IMAGE_ASPECT_RATIO_INVALID")

        pixels = width * height
        if pixels < cls.API_MIN_PIXELS:
            # April's canonical 512x512 Web output maps to the documented
            # 1024x1024 square generation target, which keeps the low-quality
            # image price deterministic and then downsamples only at the final
            # decoder boundary.
            if width == height:
                return 1024, 1024
            scale = math.sqrt(cls.API_MIN_PIXELS / float(pixels))
            width = int(math.ceil((width * scale) / 16.0) * 16)
            height = int(math.ceil((height * scale) / 16.0) * 16)

        width = min(width, cls.API_MAX_EDGE)
        height = min(height, cls.API_MAX_EDGE)
        width = max(16, (width // 16) * 16)
        height = max(16, (height // 16) * 16)

        if width * height > cls.API_MAX_PIXELS:
            scale = math.sqrt(cls.API_MAX_PIXELS / float(width * height))
            width = max(16, int((width * scale) // 16) * 16)
            height = max(16, int((height * scale) // 16) * 16)

        if width * height < cls.API_MIN_PIXELS:
            # 1024x1024 is the canonical compliant square for April's current Web route.
            if width == height:
                return 1024, 1024
            while width * height < cls.API_MIN_PIXELS:
                width += 16
                height += 16
                if width > cls.API_MAX_EDGE or height > cls.API_MAX_EDGE:
                    raise ValueError("APRIL_IMAGES_GPT_IMAGE_SIZE_NORMALIZATION_FAILED")

        return width, height

    @staticmethod
    def _normalize_quality(quality: str) -> str:
        value = str(quality or "low").strip().lower()
        mapping = {
            "draft": "low",
            "standard": "low",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "ultra": "high",
            "auto": "auto",
        }
        normalized = mapping.get(value, "low")
        if normalized == "auto":
            # April currently prefers deterministic cost control over automatic upsizing.
            return "low"
        return normalized

    # -------------------------------------------------
    # GPT Image 2 request / base64 decoder
    # -------------------------------------------------

    @classmethod
    def _extract_response_data(cls, response: Any) -> tuple[str, dict[str, Any]]:
        data = getattr(response, "data", None)
        if data is None and isinstance(response, dict):
            data = response.get("data")
        if not isinstance(data, (list, tuple)) or not data:
            raise RuntimeError("APRIL_IMAGES_GPT_IMAGE_EMPTY_RESPONSE")
        first = data[0]
        if isinstance(first, dict):
            encoded = first.get("b64_json") or first.get("base64") or first.get("image")
            meta = dict(first)
        else:
            encoded = getattr(first, "b64_json", None) or getattr(first, "base64", None)
            meta = {}
        encoded = cls._safe_text(encoded).strip()
        if not encoded:
            raise RuntimeError("APRIL_IMAGES_GPT_IMAGE_NO_BASE64")
        return encoded, meta

    @classmethod
    def _decode_gpt_image(cls, response: Any) -> tuple[bytes, dict[str, Any]]:
        encoded, item_meta = cls._extract_response_data(response)
        if encoded.startswith("data:image/"):
            encoded = encoded.split(",", 1)[1]
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except Exception as exc:
            raise RuntimeError("APRIL_IMAGES_GPT_IMAGE_BASE64_DECODE_FAILED") from exc
        if not image_bytes:
            raise RuntimeError("APRIL_IMAGES_GPT_IMAGE_DECODED_EMPTY")
        return image_bytes, item_meta

    @classmethod
    def _usage_dict(cls, response: Any) -> dict[str, Any]:
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        if usage is None:
            return {}
        if isinstance(usage, dict):
            return dict(usage)
        for method_name in ("model_dump", "to_dict", "dict"):
            method = getattr(usage, method_name, None)
            if callable(method):
                try:
                    value = method()
                    if isinstance(value, dict):
                        return dict(value)
                except Exception:
                    pass
        result: dict[str, Any] = {}
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "image_input_tokens",
            "image_output_tokens",
            "text_input_tokens",
        ):
            value = getattr(usage, key, None)
            if value is not None:
                result[key] = value
        return result

    @classmethod
    def _estimate_prompt_tokens(cls, text: str) -> int:
        # Conservative local diagnostic only; billing truth is the API response/account.
        total = 0.0
        for ch in str(text or ""):
            if ch.isspace():
                total += 0.15
            elif ord(ch) > 127:
                total += 0.50
            elif ch in '{}[]":,;|_-':
                total += 0.35
            else:
                total += 0.25
        return max(1, int(total + 0.999))

    @classmethod
    def _log_cost(
        cls,
        *,
        response: Any,
        prompt: str,
        requested_size: tuple[int, int],
        api_size: tuple[int, int],
        quality: str,
        item_meta: dict[str, Any],
    ) -> dict[str, Any]:
        usage = cls._usage_dict(response)
        input_tokens = usage.get("text_input_tokens")
        if input_tokens is None:
            input_tokens = usage.get("input_tokens")
        image_output_tokens = usage.get("image_output_tokens")

        estimated_text_tokens = cls._estimate_prompt_tokens(prompt)
        text_cost = (
            float(input_tokens) * cls.TEXT_INPUT_USD_PER_MILLION / 1_000_000
            if input_tokens is not None else
            float(estimated_text_tokens) * cls.TEXT_INPUT_USD_PER_MILLION / 1_000_000
        )

        if image_output_tokens is not None:
            image_cost = float(image_output_tokens) * cls.IMAGE_OUTPUT_USD_PER_MILLION / 1_000_000
            image_cost_method = "api_usage_image_output_tokens"
        elif api_size == (1024, 1024) and quality == "low":
            image_cost = cls.LOW_1024_IMAGE_ESTIMATE_USD
            image_cost_method = "official_1024x1024_low_price"
        else:
            image_cost = None
            image_cost_method = "usage_not_returned_custom_size"

        total_cost = (text_cost + image_cost) if image_cost is not None else None
        request_id = getattr(response, "_request_id", None) or getattr(response, "request_id", None)
        log_payload = {
            "model": cls.MODEL,
            "quality": quality,
            "requested_size": f"{requested_size[0]}x{requested_size[1]}",
            "api_generation_size": f"{api_size[0]}x{api_size[1]}",
            "output_format": "png",
            "image_count": 1,
            "request_id": cls._safe_text(request_id),
            "input_text_tokens_api": input_tokens,
            "input_text_tokens_estimated": estimated_text_tokens,
            "image_output_tokens_api": image_output_tokens,
            "image_output_cost_usd": round(image_cost, 8) if image_cost is not None else None,
            "text_input_cost_usd": round(text_cost, 8),
            "estimated_total_cost_usd": round(total_cost, 8) if total_cost is not None else None,
            "cost_method": image_cost_method,
            "api_response_item": item_meta,
            "usage": usage,
        }
        print("💰 GPT IMAGE 2 COST:", json.dumps(log_payload, ensure_ascii=False, default=str))
        return log_payload

    @classmethod
    def _resize_to_requested(cls, image_bytes: bytes, requested_width: int, requested_height: int) -> bytes:
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            if source.size == (requested_width, requested_height):
                converted = source.copy()
            else:
                # Preserve the raster returned by GPT Image 2; only normalize to the
                # existing April Web contract size at the final decoder boundary.
                converted = source.resize(
                    (requested_width, requested_height),
                    Image.Resampling.LANCZOS,
                )
            output = io.BytesIO()
            converted.save(output, format="PNG", optimize=True)
            return output.getvalue()

    @classmethod
    def _generate_gpt_image_bytes(
        cls,
        prompt: str,
        *,
        requested_width: int,
        requested_height: int,
        quality: str,
    ) -> tuple[bytes, dict[str, Any]]:
        cls._require_backend()
        api_width, api_height = cls._api_generation_size(requested_width, requested_height)
        normalized_quality = cls._normalize_quality(quality)

        request = {
            "model": cls.MODEL,
            "prompt": prompt,
            "size": f"{api_width}x{api_height}",
            "quality": normalized_quality,
            "output_format": "png",
            "n": 1,
        }
        print(
            "🧠 GPT IMAGE 2 REQUEST:",
            json.dumps(
                {
                    "model": cls.MODEL,
                    "quality": normalized_quality,
                    "requested_size": f"{requested_width}x{requested_height}",
                    "api_generation_size": f"{api_width}x{api_height}",
                    "output_format": "png",
                    "image_count": 1,
                    "prompt_chars": len(prompt),
                },
                ensure_ascii=False,
            ),
        )

        client = cls._client()
        response = client.images.generate(**request)
        decoded_bytes, item_meta = cls._decode_gpt_image(response)
        decoded_bytes = cls._resize_to_requested(
            decoded_bytes,
            requested_width,
            requested_height,
        )

        cost = cls._log_cost(
            response=response,
            prompt=prompt,
            requested_size=(requested_width, requested_height),
            api_size=(api_width, api_height),
            quality=normalized_quality,
            item_meta=item_meta,
        )
        meta = {
            "api_generation_size": (api_width, api_height),
            "requested_size": (requested_width, requested_height),
            "effective_quality": normalized_quality,
            "cost": cost,
            "request_id": cls._safe_text(
                getattr(response, "_request_id", None)
                or getattr(response, "request_id", None)
            ),
        }
        return decoded_bytes, meta

    # -------------------------------------------------
    # PNG + C_ARTIFACT
    # -------------------------------------------------

    @staticmethod
    def _png_bytes(image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    @staticmethod
    def _validate_png(image_bytes: bytes, expected_width: int, expected_height: int) -> None:
        if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("APRIL_IMAGES_OUTPUT_NOT_PNG")
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.verify()
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.width != int(expected_width) or image.height != int(expected_height):
                raise RuntimeError("APRIL_IMAGES_OUTPUT_DIMENSIONS_INVALID")
            if all(lo == hi for lo, hi in image.convert("RGB").getextrema()):
                raise RuntimeError("APRIL_IMAGES_OUTPUT_EMPTY_PIXELS")

    @classmethod
    def build_artifact(
        cls,
        *,
        image_bytes: bytes,
        prompt: str,
        width: int,
        height: int,
        backend: str = BACKEND,
        variant: str = "primary",
        dialogue_context: Optional[dict[str, Any]] = None,
    ) -> tuple[dict[str, Any], UniversalArtifactContract]:
        data_base64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{data_base64}"
        image_item = {
            "src": data_uri,
            "url": data_uri,
            "image": data_uri,
            "mime_type": "image/png",
            "width": width,
            "height": height,
            "title": "Image",
            "alt": prompt,
            "caption": prompt,
        }
        dialogue_context = dict(dialogue_context or {}) if isinstance(dialogue_context, dict) else {}
        artifact = create_artifact(
            artifact_type="image",
            room_source="APRIL_IMAGES_GENERATION",
            data={
                "prompt": prompt,
                "variant": variant,
                "backend": backend,
                "mime_type": "image/png",
                "width": width,
                "height": height,
                "image_base64": data_base64,
                "image_data_uri": data_uri,
                "human_visible": True,
                "machine_only": False,
                "presentation": {
                    "mode": "gallery",
                    "renderer": "GalleryBlock",
                    "viewer": "GalleryBlock",
                    "source_engine": cls.ENGINE_NAME,
                    "generation_backend": backend,
                },
                "payload": {
                    "kind": "generated_image",
                    "artifact_type": "image",
                    "mime_type": "image/png",
                    "width": width,
                    "height": height,
                    "image_base64": data_base64,
                    "image_data_uri": data_uri,
                    "src": data_uri,
                    "url": data_uri,
                    "prompt": prompt,
                    "engine": cls.ENGINE_NAME,
                    "engine_version": cls.ENGINE_VERSION,
                    "backend": backend,
                    "variant": variant,
                    "presentation": {
                        "mode": "gallery",
                        "renderer": "GalleryBlock",
                        "viewer": "GalleryBlock",
                        "payload_type": "image",
                        "mime_type": "image/png",
                    },
                    "images": [image_item],
                    "dialogue_context": dialogue_context,
                    "flow_id": dialogue_context.get("flow_id", ""),
                    "turn_id": dialogue_context.get("turn_id", ""),
                    "scene_id": dialogue_context.get("scene_id", ""),
                    "conversation_id": dialogue_context.get("conversation_id", ""),
                    "dialogue_sequence_id": dialogue_context.get("dialogue_sequence_id", ""),
                },
            },
        )
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0

        contract = build_universal_contract(artifact, user_id=str(dialogue_context.get("user_id") or ""))
        artifact_data = dict(artifact.data or {})
        payload = artifact_data.get("payload") if isinstance(artifact_data.get("payload"), dict) else {}
        images = payload.get("images") if isinstance(payload.get("images"), list) else []
        if not images or not isinstance(images[0], dict) or not images[0].get("src"):
            raise RuntimeError("APRIL_IMAGES_GALLERY_CONTRACT_INVALID")
        artifact_data["images"] = list(images)
        return artifact_data, contract

    @classmethod
    def build_artifact_from_bytes(
        cls,
        image_bytes: bytes,
        prompt: str,
        *,
        width: int | None = None,
        height: int | None = None,
        backend: str = BACKEND,
        variant: str = "generated",
    ) -> tuple[dict[str, Any], UniversalArtifactContract]:
        if not image_bytes:
            raise ValueError("APRIL_IMAGES_EMPTY_IMAGE")
        if width is None or height is None:
            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
        cls._validate_png(image_bytes, int(width), int(height))
        return cls.build_artifact(
            image_bytes=image_bytes,
            prompt=prompt,
            width=int(width),
            height=int(height),
            backend=backend,
            variant=variant,
        )

    @staticmethod
    def _result_dict(result: ImageGenerationResult) -> dict[str, Any]:
        return {
            "success": True,
            "image_bytes": result.image_bytes,
            "mime_type": result.mime_type,
            "width": result.width,
            "height": result.height,
            "backend": result.backend,
            "prompt": result.prompt,
            "artifact": result.artifact,
            "contract": result.contract,
        }

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def get_engine_info(self) -> dict[str, Any]:
        return {
            "engine": self.engine_name,
            "version": self.engine_version,
            "status": "ready" if self._can_initialize() else "configuration_required",
            "architecture": "Interpretation -> Provider -> GPT Image 2.0 -> C_ARTIFACT_CONTRACT -> GalleryBlock",
            "backend_mode": self.BACKEND,
            "model_source": self.MODEL,
            "local_model_configured": False,
            "model_id_configured": True,
            "diffusers_available": False,
            "long_prompt_support": True,
            "max_semantic_prompt_tokens": self.MAX_SEMANTIC_PROMPT_TOKENS,
            "long_prompt_strategy": "provider_semantic_plan_passthrough",
            "device": self._device(),
            "dtype": None,
            "external_image_api": True,
            "fallback_backend": None,
            "display_contract": "C_ARTIFACT_CONTRACT -> GalleryBlock",
            "default_quality": "low",
            "default_web_size": "512x512",
            "api_generation_size_for_512": "1024x1024",
        }

    @classmethod
    def build_visual_prompt(
        cls,
        request: str,
        *,
        visual_context: Optional[dict[str, Any]] = None,
        style: str = "",
        quality: str = "low",
    ) -> str:
        # Compatibility method. Style is intentionally not injected.
        spec = {
            "prompt": request,
            "quality": quality,
            "visual_context": visual_context or {},
            "request_anchor": request,
            "openai_structured_visual_plan_semantic": request,
        }
        return cls._compose_prompt(cls._clean_prompt(request), spec)

    # -------------------------------------------------
    # Provider image-spec validation / execution
    # -------------------------------------------------

    @classmethod
    def _validate_render_spec(cls, spec: Any) -> dict[str, Any]:
        if not isinstance(spec, dict):
            raise ValueError("APRIL_IMAGES_INVALID_SPEC")
        if spec.get("schema") != "april_image_spec_v1":
            raise ValueError("APRIL_IMAGES_INVALID_SPEC_SCHEMA")

        width, height = cls._parse_size(
            f"{spec.get('width', cls.DEFAULT_SIZE[0])}x{spec.get('height', cls.DEFAULT_SIZE[1])}"
        )
        generator_signal = cls._safe_text(spec.get("generator_signal") or "").strip()
        if generator_signal and generator_signal != "C_APRIL_IMAGES_GENERATOR":
            raise ValueError("APRIL_IMAGES_INVALID_GENERATOR_SIGNAL")

        request_anchor = cls._safe_text(spec.get("request_anchor") or "").strip()
        if generator_signal == "C_APRIL_IMAGES_GENERATOR" and not request_anchor:
            raise ValueError("APRIL_IMAGES_MISSING_REQUEST_ANCHOR")

        semantic = cls._clean_prompt(
            spec.get("openai_structured_visual_plan_semantic")
            or spec.get("prompt")
            or ""
        )
        return {
            "schema": "april_image_spec_v1",
            "prompt": semantic,
            "width": width,
            "height": height,
            "style": cls._safe_text(spec.get("style") or ""),
            "quality": cls._normalize_quality(cls._safe_text(spec.get("quality") or "low")),
            "negative": [str(x) for x in (spec.get("negative") or []) if str(x).strip()],
            "visual_context": dict(spec.get("visual_context") or {}) if isinstance(spec.get("visual_context"), dict) else {},
            "openai_structured_visual_plan_raw": spec.get("openai_structured_visual_plan_raw"),
            "openai_structured_visual_plan_semantic": semantic,
            "render_profile": "",
            "render_profile_source": "",
            "seed": None,
            "generator_signal": generator_signal,
            "request_anchor": request_anchor,
            "flow_id": cls._safe_text(spec.get("flow_id") or ""),
            "turn_id": cls._safe_text(spec.get("turn_id") or ""),
            "scene_id": cls._safe_text(spec.get("scene_id") or ""),
            "user_id": cls._safe_text(spec.get("user_id") or ""),
            "conversation_id": cls._safe_text(spec.get("conversation_id") or ""),
            "dialogue_sequence_id": cls._safe_text(spec.get("dialogue_sequence_id") or ""),
            "dialogue_development": dict(spec.get("dialogue_development") or {}) if isinstance(spec.get("dialogue_development"), dict) else {},
        }

    @classmethod
    async def generate_from_spec(
        cls,
        spec: dict[str, Any],
        *,
        variant: str = "provider_spec",
    ) -> dict[str, Any]:
        clean = cls._validate_render_spec(spec)
        width, height = cls._parse_size(f"{clean['width']}x{clean['height']}")
        prompt = cls._compose_prompt(clean["prompt"], clean)
        final_prompt_tokens = cls._estimate_prompt_tokens(prompt)

        print(
            "\n===== IMAGE PROMPT TRACE: GENERATOR ENTRY =====\n"
            + json.dumps(
                {
                    "variant": variant,
                    "schema": clean.get("schema"),
                    "generator_signal": clean.get("generator_signal") or "implicit_canonical_route",
                    "request_anchor": clean.get("request_anchor") or "",
                    "semantic_generation_prompt": clean.get("prompt") or "",
                    "prompt_chars": len(prompt),
                    "openai_plan_preserved": clean.get("openai_structured_visual_plan_raw") is not None,
                    "provider_model": cls.MODEL,
                    "quality": clean.get("quality") or "low",
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
            + "\n===== END GENERATOR ENTRY =====\n"
        )
        print(
            "===== IMAGE PROMPT TRACE: GENERATOR COMPOSED PROMPT =====\n"
            + prompt[:12000]
            + "\n===== END IMAGE PROMPT TRACE: GENERATOR COMPOSED PROMPT =====\n"
        )
        print(
            "🔒 IMAGE PROMPT SEMANTIC LOCK:",
            {
                "request_anchor": clean.get("request_anchor") or "",
                "source_prompt": clean.get("prompt") or "",
                "generation_prompt": prompt,
                "scene_content_authority": "USER_REQUEST_PLUS_OPENAI_STRUCTURED_VISUAL_PLAN",
                "generation_prompt_source": "USER_REQUEST_PLUS_OPENAI_SEMANTIC_PLAN_PLUS_STRUCTURED_PLAN",
                "user_request_is_trigger_only": False,
                "openai_structured_plan_preserved": clean.get("openai_structured_visual_plan_raw") is not None,
                "render_profile_injected_into_prompt": False,
                "provider_model": cls.MODEL,
                "generator_scene_invention": False,
            },
        )
        print(
            "🧠 IMAGE PROMPT NORMALIZED:",
            {
                "semantic_chars": len(prompt),
                "estimated_prompt_tokens": int(final_prompt_tokens),
                "contains_markup": bool(re.search(r"<(?:svg|path|rect|circle)\\b|data:image/", prompt, flags=re.IGNORECASE)),
                "generation_model": cls.MODEL,
                "quality": clean["quality"],
                "output_format": "png",
            },
        )

        image_bytes, meta = await asyncio.to_thread(
            cls._generate_gpt_image_bytes,
            prompt,
            requested_width=width,
            requested_height=height,
            quality=clean["quality"],
        )
        cls._validate_png(image_bytes, width, height)

        try:
            output_sha256 = hashlib.sha256(image_bytes).hexdigest()
            print(
                "🔎 APRIL IMAGE GENERATOR RASTER EXIT (OBSERVATION ONLY):",
                {
                    "request_anchor": clean.get("request_anchor") or "",
                    "generator_prompt": prompt,
                    "model": cls.MODEL,
                    "backend": cls.BACKEND,
                    "variant": variant,
                    "width": int(width),
                    "height": int(height),
                    "png_bytes": len(image_bytes),
                    "png_sha256": output_sha256,
                    "png_validation": "passed",
                    "next_route": "C_ARTIFACT_CONTRACT",
                    "decoded_png_forwarded_unchanged_to_artifact": True,
                    "api_raster_resized_to_web_contract": bool(
                        meta["api_generation_size"] != (width, height)
                    ),
                    "api_generation_size": f"{meta['api_generation_size'][0]}x{meta['api_generation_size'][1]}",
                    "effective_quality": meta["effective_quality"],
                },
            )
        except Exception as diag_exc:
            print(
                "⚠️ APRIL IMAGE GENERATOR RASTER EXIT DIAGNOSTIC FAILED:",
                {
                    "error_type": type(diag_exc).__name__,
                    "error": str(diag_exc)[:240],
                    "decoded_png_forwarded_unchanged_to_artifact": True,
                },
            )

        artifact, contract = cls.build_artifact(
            image_bytes=image_bytes,
            prompt=prompt,
            width=width,
            height=height,
            backend=cls.BACKEND,
            variant=variant,
            dialogue_context={
                "user_id": clean.get("user_id", ""),
                "flow_id": clean.get("flow_id", ""),
                "turn_id": clean.get("turn_id", ""),
                "scene_id": clean.get("scene_id", ""),
                "conversation_id": clean.get("conversation_id", ""),
                "dialogue_sequence_id": clean.get("dialogue_sequence_id", ""),
                "dialogue_development": clean.get("dialogue_development", {}),
            },
        )

        payload = artifact.get("payload") if isinstance(artifact, dict) else None
        payload = dict(payload) if isinstance(payload, dict) else {}
        data_base64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{data_base64}"
        image_item = {
            "src": data_uri,
            "url": data_uri,
            "image": data_uri,
            "mime_type": "image/png",
            "width": int(width),
            "height": int(height),
            "title": payload.get("title") or "Image",
            "alt": payload.get("alt") or clean.get("request_anchor") or prompt,
            "caption": payload.get("caption") or clean.get("request_anchor") or prompt,
        }
        payload.update({
            "kind": "generated_image",
            "artifact_type": "image",
            "mime_type": "image/png",
            "width": int(width),
            "height": int(height),
            "image_base64": data_base64,
            "image_data_uri": data_uri,
            "src": data_uri,
            "url": data_uri,
            "image": data_uri,
            "prompt": prompt,
            "engine": cls.ENGINE_NAME,
            "engine_version": cls.ENGINE_VERSION,
            "backend": cls.BACKEND,
            "variant": variant,
            "images": [image_item],
            "generation_model": cls.MODEL,
            "generation_quality": meta["effective_quality"],
        })

        if not isinstance(artifact, dict):
            artifact = {}
        artifact.update({
            "artifact_type": "image",
            "mime_type": "image/png",
            "width": int(width),
            "height": int(height),
            "image_base64": data_base64,
            "image_data_uri": data_uri,
            "payload": payload,
            "images": [image_item],
            "render_spec": clean,
            "generation_model": cls.MODEL,
            "generation_quality": meta["effective_quality"],
        })
        artifact["payload"]["render_spec"] = clean
        artifact["payload"]["generation_model"] = cls.MODEL
        artifact["payload"]["generation_quality"] = meta["effective_quality"]

        base_artifact = getattr(contract, "artifact", None) if contract is not None else None
        if base_artifact is not None:
            try:
                base_data = dict(getattr(base_artifact, "data", {}) or {})
                base_data.update({
                    "artifact_type": "image",
                    "mime_type": "image/png",
                    "width": int(width),
                    "height": int(height),
                    "image_base64": data_base64,
                    "image_data_uri": data_uri,
                    "human_visible": True,
                    "machine_only": False,
                    "payload": payload,
                })
                base_artifact.data = base_data
                contract = build_universal_contract(base_artifact)
            except Exception as exc:
                print("⚠️ GPT IMAGE 2 ARTIFACT CONTRACT REFRESH:", exc)

        print(
            "🧠 IMAGE ARTIFACT OUTPUT:",
            {
                "artifact_type": artifact.get("artifact_type"),
                "mime_type": artifact.get("mime_type"),
                "width": artifact.get("width"),
                "height": artifact.get("height"),
                "has_image_base64": bool(artifact.get("image_base64")),
                "has_image_data_uri": bool(artifact.get("image_data_uri")),
                "payload_has_src": bool(artifact.get("payload", {}).get("src")),
                "images_count": len(artifact.get("images") or []),
                "display_contract": "C_ARTIFACT_CONTRACT -> GalleryBlock",
                "generation_model": cls.MODEL,
                "generation_quality": meta["effective_quality"],
            },
        )
        return cls._result_dict(
            ImageGenerationResult(
                image_bytes=image_bytes,
                mime_type="image/png",
                width=width,
                height=height,
                backend=cls.BACKEND,
                prompt=prompt,
                artifact=artifact,
                contract=contract,
            )
        )

    async def generate(
        self,
        prompt: str,
        *,
        size: str = "512x512",
        quality: str = "low",
        seed: Optional[int] = None,
        variant: str = "primary",
    ) -> dict[str, Any]:
        # Direct legacy callers still end in the same GPT Image 2 route.
        request = self._clean_prompt(prompt)
        width, height = self._parse_size(size)
        spec = {
            "schema": "april_image_spec_v1",
            "prompt": request,
            "width": width,
            "height": height,
            "quality": self._normalize_quality(quality),
            "visual_context": {},
            "openai_structured_visual_plan_semantic": request,
            "openai_structured_visual_plan_raw": None,
            "request_anchor": request,
            "generator_signal": "C_APRIL_IMAGES_GENERATOR",
        }
        return await self.generate_from_spec(spec, variant=variant)

    async def edit(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        quality: str = "low",
        strength: float = 0.65,
        variant: str = "edit",
    ) -> dict[str, Any]:
        """GPT Image 2 image edit compatibility path.

        ``strength`` is accepted for API compatibility with the old Diffusers
        implementation but is not sent to GPT Image 2 because the Images API
        controls edits by prompt + input image rather than a diffusion strength.
        """
        cls = type(self)
        cls._require_backend()
        if not image_bytes:
            raise ValueError("APRIL_IMAGES_EDIT_SOURCE_EMPTY")
        clean_prompt = cls._clean_prompt(prompt)
        quality_value = cls._normalize_quality(quality)
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.load()
            original_size = source.size
        api_width, api_height = cls._api_generation_size(*original_size)

        def _do_edit() -> tuple[bytes, dict[str, Any]]:
            client = cls._client()
            handle = io.BytesIO(image_bytes)
            handle.name = "april_input.png"
            response = client.images.edit(
                model=cls.MODEL,
                image=handle,
                prompt=clean_prompt,
                size=f"{api_width}x{api_height}",
                quality=quality_value,
                output_format="png",
            )
            output, item_meta = cls._decode_gpt_image(response)
            output = cls._resize_to_requested(output, original_size[0], original_size[1])
            usage = cls._usage_dict(response)
            print(
                "💰 GPT IMAGE 2 EDIT COST:",
                json.dumps(
                    {
                        "model": cls.MODEL,
                        "quality": quality_value,
                        "requested_size": f"{original_size[0]}x{original_size[1]}",
                        "api_generation_size": f"{api_width}x{api_height}",
                        "usage": usage,
                        "estimated_text_input_tokens": cls._estimate_prompt_tokens(clean_prompt),
                        "note": "Image edit input tokens depend on the supplied source image; see API billing usage/account for exact charge.",
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            )
            return output, item_meta

        output, _item_meta = await asyncio.to_thread(_do_edit)
        cls._validate_png(output, original_size[0], original_size[1])
        artifact, contract = cls.build_artifact(
            image_bytes=output,
            prompt=clean_prompt,
            width=original_size[0],
            height=original_size[1],
            backend=cls.BACKEND,
            variant=variant,
        )
        return cls._result_dict(
            ImageGenerationResult(
                image_bytes=output,
                mime_type="image/png",
                width=original_size[0],
                height=original_size[1],
                backend=cls.BACKEND,
                prompt=clean_prompt,
                artifact=artifact,
                contract=contract,
            )
        )


april_images_generator = AprilImagesGenerator()


async def generate_from_spec(spec: dict[str, Any], *, variant: str = "provider_spec") -> dict[str, Any]:
    return await april_images_generator.generate_from_spec(spec, variant=variant)


async def generate_image(prompt: str, size: str = "512x512", quality: str = "low") -> Optional[bytes]:
    result = await april_images_generator.generate(prompt, size=size, quality=quality)
    return result.get("image_bytes") if result.get("success") else None


async def generate_image_result(
    prompt: str,
    size: str = "512x512",
    quality: str = "low",
    variant: str = "primary",
) -> dict[str, Any]:
    return await april_images_generator.generate(prompt, size=size, quality=quality, variant=variant)


async def edit_image(image_bytes: bytes, prompt: str, quality: str = "low") -> Optional[bytes]:
    result = await april_images_generator.edit(image_bytes, prompt, quality=quality)
    return result.get("image_bytes") if result.get("success") else None


async def edit_image_result(image_bytes: bytes, prompt: str, quality: str = "low") -> dict[str, Any]:
    return await april_images_generator.edit(image_bytes, prompt, quality=quality)


__all__ = [
    "AprilImagesGenerator",
    "ImageGenerationResult",
    "april_images_generator",
    "generate_image",
    "generate_image_result",
    "generate_from_spec",
    "edit_image",
    "edit_image_result",
]
