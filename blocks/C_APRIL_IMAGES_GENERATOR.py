# =====================================================
# APRIL IMAGES GENERATION
# =====================================================
"""Canonical April image-generation engine.

Route:
    April Bot -> Interpretation -> C_APRIL_IMAGES_GENERATOR
      -> C_ARTIFACT_CONTRACT -> GalleryBlock / April Web

Important contract rule:
    This module creates real raster pixels only through the configured local
    Diffusers image model. It does NOT silently fall back to a procedural
    placeholder or another image provider. The existing C_ARTIFACT/Gallery
    payload is preserved so Web keeps all existing image signals.
"""

from __future__ import annotations

import base64
import io
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, Optional

from PIL import Image

from blocks.C_ARTIFACT_CONTRACT import (
    UniversalArtifactContract,
    build_universal_contract,
    create_artifact,
)

try:
    from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image
except Exception:  # pragma: no cover
    AutoPipelineForText2Image = None
    AutoPipelineForImage2Image = None

try:
    import torch
except Exception:  # pragma: no cover
    torch = None


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
    """The only image producer between Interpretation and C_ARTIFACT."""

    ENGINE_NAME = "April Images Generation"
    ENGINE_VERSION = "2.1.0"
    BACKEND = "diffusers_single_backend"

    DEFAULT_SIZE = (1024, 1024)
    MIN_SIZE = 256
    MAX_SIZE = 1536

    _pipeline_lock = threading.RLock()
    _text_pipeline = None
    _edit_pipeline = None
    _pipeline_path = None
    _pipeline_cache_key = None

    def __init__(self) -> None:
        self.engine_name = self.ENGINE_NAME
        self.engine_version = self.ENGINE_VERSION

    # -------------------------------------------------
    # Configuration
    # -------------------------------------------------

    @classmethod
    def _model_source(cls) -> str:
        """Return the single configured Diffusers model source.

        A local path is preferred when explicitly configured. Otherwise one
        canonical model id is used. Both are the same Diffusers backend; there
        is no alternate provider or rendering fallback.
        """
        local_path = os.getenv("APRIL_IMAGES_MODEL_PATH", "").strip()
        if local_path:
            return local_path

        return (
            os.getenv(
                "APRIL_IMAGES_MODEL_ID",
                "stabilityai/stable-diffusion-xl-base-1.0",
            ).strip()
            or "stabilityai/stable-diffusion-xl-base-1.0"
        )

    @classmethod
    def _model_path(cls) -> str:
        # Backward-compatible accessor retained for callers that expect it.
        return os.getenv("APRIL_IMAGES_MODEL_PATH", "").strip()

    @classmethod
    def _model_is_local(cls) -> bool:
        path = cls._model_path()
        return bool(path) and os.path.isdir(path)

    @classmethod
    def _local_files_only(cls) -> bool:
        configured = os.getenv("APRIL_IMAGES_LOCAL_ONLY", "0").strip().lower()
        return configured in {"1", "true", "yes", "on"} or cls._model_is_local()

    @classmethod
    def _device(cls) -> str:
        configured = os.getenv("APRIL_IMAGES_DEVICE", "auto").strip().lower()
        if configured in {"cuda", "cpu", "mps"}:
            return configured
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        if torch is not None and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    @classmethod
    def _dtype(cls):
        configured = os.getenv("APRIL_IMAGES_DTYPE", "auto").strip().lower()
        if torch is None:
            return None
        if configured in {"float16", "fp16"}:
            return torch.float16
        if configured in {"bfloat16", "bf16"}:
            return torch.bfloat16
        if configured in {"float32", "fp32"}:
            return torch.float32
        return torch.float16 if cls._device() in {"cuda", "mps"} else torch.float32

    @classmethod
    def _quality_settings(cls, quality: str) -> tuple[int, float]:
        """Quality profile for the single active Diffusers model."""
        return {
            "draft": (28, 6.0),
            "standard": (40, 6.5),
            "high": (50, 7.0),
            "ultra": (60, 7.5),
        }.get(str(quality or "standard").strip().lower(), (40, 6.5))

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
        width = max(64, (width // 64) * 64)
        height = max(64, (height // 64) * 64)
        return width, height

    @staticmethod
    def _clean_prompt(prompt: Any) -> str:
        text = " ".join(str(prompt or "").split()).strip()
        if not text:
            raise ValueError("APRIL_IMAGES_EMPTY_PROMPT")
        return text[:8000]

    @staticmethod
    def _negative_prompt(spec: Optional[dict[str, Any]] = None) -> str:
        values = [
            "low quality", "blurry", "pixelated", "jpeg artifacts",
            "deformed", "bad anatomy", "extra limbs", "duplicate subject",
            "distorted face", "disfigured hands", "malformed eyes",
            "watermark", "text artifacts", "cropped subject",
        ]
        if isinstance(spec, dict) and isinstance(spec.get("negative"), list):
            values.extend(str(x).strip() for x in spec["negative"][:24] if str(x).strip())
        return ", ".join(dict.fromkeys(values))

    @staticmethod
    def _compose_prompt(prompt: str, spec: Optional[dict[str, Any]] = None) -> str:
        parts = [str(prompt).strip()]
        if isinstance(spec, dict):
            style = str(spec.get("style") or "").strip()
            if style and style.lower() not in prompt.lower():
                parts.append(f"Style: {style}")

            context = spec.get("visual_context")
            if isinstance(context, dict):
                # Preserve every useful visual signal without inventing facts.
                for key in (
                    "subject", "composition", "lighting", "camera",
                    "environment", "palette", "mood", "materials",
                    "character", "pose", "background", "details",
                ):
                    value = context.get(key)
                    if value:
                        label = key.replace("_", " ").title()
                        parts.append(f"{label}: {value}")

        # Quality guidance improves coherence while leaving scene semantics
        # authoritative. It does not change the requested subject.
        parts.append(
            "High-quality finished artwork, coherent composition, clear subject "
            "separation, natural perspective, detailed textures, consistent "
            "lighting, depth, clean edges, visually rich but faithful to the "
            "requested scene."
        )
        return "\n".join(parts)[:8000]

    @classmethod
    def _require_backend(cls) -> None:
        source = cls._model_source()
        if not source:
            raise RuntimeError("APRIL_IMAGES_MODEL_SOURCE_NOT_CONFIGURED")
        if AutoPipelineForText2Image is None or AutoPipelineForImage2Image is None:
            raise RuntimeError("APRIL_IMAGES_DIFFUSERS_NOT_INSTALLED")
        if torch is None:
            raise RuntimeError("APRIL_IMAGES_TORCH_NOT_INSTALLED")

        # An explicitly supplied local path must exist. A model id is allowed
        # and will be resolved by Diffusers/Hugging Face into the runtime cache.
        if cls._model_path() and not os.path.isdir(cls._model_path()):
            raise RuntimeError("APRIL_IMAGES_MODEL_PATH_NOT_FOUND")

    # -------------------------------------------------
    # Real Diffusers backend
    # -------------------------------------------------

    @classmethod
    def _configure_pipeline(cls, pipeline: Any) -> Any:
        for method_name in (
            "enable_vae_slicing",
            "enable_vae_tiling",
            "enable_attention_slicing",
        ):
            method = getattr(pipeline, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

        device = cls._device()
        if device == "cuda" and os.getenv("APRIL_IMAGES_CPU_OFFLOAD", "0") == "1":
            method = getattr(pipeline, "enable_model_cpu_offload", None)
            if callable(method):
                method()
                return pipeline
        return pipeline.to(device)

    @classmethod
    def _load_text_pipeline(cls):
        cls._require_backend()
        source = cls._model_source()
        cache_key = f"text::{source}::{cls._dtype()}::{cls._device()}::{cls._local_files_only()}"
        with cls._pipeline_lock:
            if cls._text_pipeline is not None and cls._pipeline_cache_key == cache_key:
                return cls._text_pipeline

            kwargs: dict[str, Any] = {
                "local_files_only": cls._local_files_only(),
            }
            dtype = cls._dtype()
            if dtype is not None:
                kwargs["torch_dtype"] = dtype
            if os.getenv("APRIL_IMAGES_USE_SAFETENSORS", "1").strip().lower() in {"1", "true", "yes"}:
                kwargs["use_safetensors"] = True

            pipeline = AutoPipelineForText2Image.from_pretrained(source, **kwargs)
            cls._text_pipeline = cls._configure_pipeline(pipeline)
            cls._pipeline_path = source
            cls._pipeline_cache_key = cache_key
            return cls._text_pipeline

    @classmethod
    def _load_edit_pipeline(cls):
        cls._require_backend()
        source = cls._model_source()
        cache_key = f"edit::{source}::{cls._dtype()}::{cls._device()}::{cls._local_files_only()}"
        with cls._pipeline_lock:
            if cls._edit_pipeline is not None and cls._pipeline_cache_key == cache_key:
                return cls._edit_pipeline

            kwargs: dict[str, Any] = {
                "local_files_only": cls._local_files_only(),
            }
            dtype = cls._dtype()
            if dtype is not None:
                kwargs["torch_dtype"] = dtype
            if os.getenv("APRIL_IMAGES_USE_SAFETENSORS", "1").strip().lower() in {"1", "true", "yes"}:
                kwargs["use_safetensors"] = True

            pipeline = AutoPipelineForImage2Image.from_pretrained(source, **kwargs)
            cls._edit_pipeline = cls._configure_pipeline(pipeline)
            cls._pipeline_path = source
            cls._pipeline_cache_key = cache_key
            return cls._edit_pipeline

    @classmethod
    def _diffusion_image(
        cls,
        pipeline: Any,
        prompt: str,
        width: int,
        height: int,
        quality: str,
        seed: Optional[int],
        negative_prompt: str,
    ) -> Image.Image:
        steps, guidance = cls._quality_settings(quality)
        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }
        if negative_prompt:
            kwargs["negative_prompt"] = negative_prompt
        if seed is not None and torch is not None:
            generator_device = "cuda" if cls._device() == "cuda" else "cpu"
            kwargs["generator"] = torch.Generator(device=generator_device).manual_seed(int(seed))

        result = pipeline(**kwargs)
        image = getattr(result, "images", [None])[0]
        if image is None:
            raise RuntimeError("APRIL_IMAGES_DIFFUSION_EMPTY_RESULT")
        return image.convert("RGB")

    @classmethod
    def _generate_real_image(
        cls,
        prompt: str,
        width: int,
        height: int,
        quality: str,
        seed: Optional[int],
        negative_prompt: str,
    ) -> Image.Image:
        pipeline = cls._load_text_pipeline()
        return cls._diffusion_image(
            pipeline, prompt, width, height, quality, seed, negative_prompt
        )

    @classmethod
    def build_visual_prompt(
        cls,
        request: str,
        *,
        visual_context: Optional[dict[str, Any]] = None,
        style: str = "",
        quality: str = "high",
    ) -> str:
        """Build the renderer prompt from the already-authoritative semantic state.

        This method does not inspect or mutate dialogue state; Interpretation
        remains the authority. It only converts supplied visual signals into a
        deterministic image prompt.
        """
        spec = {
            "style": style,
            "quality": quality,
            "visual_context": visual_context or {},
        }
        return cls._compose_prompt(cls._clean_prompt(request), spec)

    # -------------------------------------------------
    # Provider image-spec validation
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
        return {
            "schema": "april_image_spec_v1",
            "prompt": cls._clean_prompt(spec.get("prompt") or ""),
            "width": width,
            "height": height,
            "style": str(spec.get("style") or "illustration")[:64],
            "quality": str(spec.get("quality") or "high")[:32],
            "negative": [str(x)[:120] for x in (spec.get("negative") or [])[:24]],
            "visual_context": dict(spec.get("visual_context") or {})
            if isinstance(spec.get("visual_context"), dict) else {},
            "seed": spec.get("seed"),
        }

    @classmethod
    async def generate_from_spec(
        cls,
        spec: dict[str, Any],
        *,
        variant: str = "provider_spec",
    ) -> dict[str, Any]:
        clean = cls._validate_render_spec(spec)
        prompt = cls._compose_prompt(clean["prompt"], clean)
        width, height = cls._parse_size(f"{clean['width']}x{clean['height']}")
        image = await __import__("asyncio").to_thread(
            cls._generate_real_image,
            prompt,
            width,
            height,
            clean["quality"],
            clean.get("seed"),
            cls._negative_prompt(clean),
        )
        image_bytes = cls._png_bytes(image)
        cls._validate_png(image_bytes, width, height)
        artifact, contract = cls.build_artifact(
            image_bytes=image_bytes,
            prompt=prompt,
            width=width,
            height=height,
            backend=cls.BACKEND,
            variant=variant,
        )
        payload = artifact.get("payload") if isinstance(artifact, dict) else None
        if not isinstance(payload, dict) or not payload.get("src") or not payload.get("images"):
            raise RuntimeError("APRIL_IMAGES_ARTIFACT_DISPLAY_PAYLOAD_MISSING")
        artifact["render_spec"] = clean
        artifact["payload"]["render_spec"] = clean
        artifact["images"] = list(artifact["payload"].get("images") or [])
        return cls._result_dict(ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            width=width,
            height=height,
            backend=cls.BACKEND,
            prompt=prompt,
            artifact=artifact,
            contract=contract,
        ))

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
        backend: str,
        variant: str = "primary",
    ) -> tuple[dict[str, Any], UniversalArtifactContract]:
        data_base64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{data_base64}"

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
                    "images": [{
                        "src": data_uri,
                        "url": data_uri,
                        "image": data_uri,
                        "mime_type": "image/png",
                        "width": width,
                        "height": height,
                        "title": "Image",
                        "alt": prompt,
                        "caption": prompt,
                    }],
                },
            },
        )
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0

        contract = build_universal_contract(artifact)
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
            "architecture": "Interpretation -> C_APRIL_IMAGES_GENERATOR -> C_ARTIFACT_CONTRACT -> GalleryBlock",
            "backend_mode": "diffusers_single_backend",
            "model_source": self._model_source(),
            "local_model_configured": bool(self._model_path()),
            "model_id_configured": bool(os.getenv("APRIL_IMAGES_MODEL_ID", "").strip()),
            "diffusers_available": bool(AutoPipelineForText2Image is not None),
            "device": self._device(),
            "dtype": str(self._dtype()) if self._dtype() is not None else None,
            "external_image_api": False,
            "fallback_backend": None,
            "display_contract": "C_ARTIFACT_CONTRACT -> GalleryBlock",
        }

    @classmethod
    def _can_initialize(cls) -> bool:
        source = cls._model_source()
        return bool(
            source
            and AutoPipelineForText2Image is not None
            and AutoPipelineForImage2Image is not None
            and torch is not None
            and (
                cls._model_is_local()
                or not cls._model_path()
            )
        )

    async def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        quality: str = "standard",
        seed: Optional[int] = None,
        variant: str = "primary",
    ) -> dict[str, Any]:
        prompt = self._clean_prompt(prompt)
        width, height = self._parse_size(size)
        image = await __import__("asyncio").to_thread(
            self._generate_real_image,
            prompt,
            width,
            height,
            quality,
            seed,
            self._negative_prompt(),
        )
        image_bytes = self._png_bytes(image)
        self._validate_png(image_bytes, width, height)
        artifact, contract = self.build_artifact(
            image_bytes=image_bytes,
            prompt=prompt,
            width=width,
            height=height,
            backend=self.BACKEND,
            variant=variant,
        )
        return self._result_dict(ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            width=width,
            height=height,
            backend=self.BACKEND,
            prompt=prompt,
            artifact=artifact,
            contract=contract,
        ))

    async def edit(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        quality: str = "standard",
        strength: float = 0.65,
        variant: str = "edit",
    ) -> dict[str, Any]:
        if not image_bytes:
            raise ValueError("APRIL_IMAGES_EDIT_SOURCE_EMPTY")
        prompt = self._clean_prompt(prompt)
        source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = source.size
        pipeline = self._load_edit_pipeline()
        steps, guidance = self._quality_settings(quality)
        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "image": source,
            "strength": max(0.05, min(0.95, float(strength))),
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "negative_prompt": self._negative_prompt(),
        }
        result = pipeline(**kwargs)
        generated = getattr(result, "images", [None])[0]
        if generated is None:
            raise RuntimeError("APRIL_IMAGES_DIFFUSION_EMPTY_EDIT_RESULT")
        output = self._png_bytes(generated.convert("RGB"))
        self._validate_png(output, width, height)
        artifact, contract = self.build_artifact(
            image_bytes=output,
            prompt=prompt,
            width=width,
            height=height,
            backend="local_diffusion_edit",
            variant=variant,
        )
        return self._result_dict(ImageGenerationResult(
            image_bytes=output,
            mime_type="image/png",
            width=width,
            height=height,
            backend="local_diffusion_edit",
            prompt=prompt,
            artifact=artifact,
            contract=contract,
        ))


april_images_generator = AprilImagesGenerator()


async def generate_from_spec(spec: dict[str, Any], *, variant: str = "provider_spec") -> dict[str, Any]:
    return await april_images_generator.generate_from_spec(spec, variant=variant)


async def generate_image(prompt: str, size: str = "1024x1024", quality: str = "standard") -> Optional[bytes]:
    result = await april_images_generator.generate(prompt, size=size, quality=quality)
    return result.get("image_bytes") if result.get("success") else None


async def generate_image_result(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    variant: str = "primary",
) -> dict[str, Any]:
    return await april_images_generator.generate(prompt, size=size, quality=quality, variant=variant)


async def edit_image(image_bytes: bytes, prompt: str, quality: str = "standard") -> Optional[bytes]:
    result = await april_images_generator.edit(image_bytes, prompt, quality=quality)
    return result.get("image_bytes") if result.get("success") else None


async def edit_image_result(image_bytes: bytes, prompt: str, quality: str = "standard") -> dict[str, Any]:
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
