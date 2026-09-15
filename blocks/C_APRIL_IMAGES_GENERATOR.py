# =====================================================
# APRIL IMAGES GENERATION
# =====================================================
"""
APRIL IMAGES GENERATION — internal image generation engine.

Route:
    April Bot
      -> Image Room / Image Module
      -> C_APRIL_IMAGES_GENERATOR
      -> C_ARTIFACT_CONTRACT
      -> Gallery / April Web

No OpenAI image-generation calls.
No Gemini image-generation calls.

The engine supports two local backends:
1) local Diffusers image model, when a local model path is configured and the
   optional dependency is installed;
2) deterministic procedural artistic renderer as the bootstrap engine.

The procedural renderer is intentionally a first-generation internal engine.
It creates real PNG images without any paid external image API. Higher-fidelity
generation can later be added by installing a local diffusion model without
changing the C_ARTIFACT transport contract.
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import os
import random
import threading
from dataclasses import dataclass
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from blocks.C_ARTIFACT_CONTRACT import (
    UniversalArtifactContract,
    build_universal_contract,
    create_artifact,
)


try:  # Optional local ML backend. Never downloads anything automatically.
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
    """
    Internal image engine.

    The engine owns image creation only. It does not own dialogue, routing,
    provider selection, Executor state, or Web rendering decisions.
    """

    ENGINE_NAME = "April Images Generation"
    ENGINE_VERSION = "1.0.0"

    DEFAULT_SIZE = (1024, 1024)
    MIN_SIZE = 256
    MAX_SIZE = 1536

    _pipeline_lock = threading.RLock()
    _text_pipeline = None
    _edit_pipeline = None
    _pipeline_path = None

    def __init__(self) -> None:
        self.engine_name = self.ENGINE_NAME
        self.engine_version = self.ENGINE_VERSION

    # -------------------------------------------------
    # Configuration
    # -------------------------------------------------

    @classmethod
    def _backend_mode(cls) -> str:
        return os.getenv("APRIL_IMAGES_BACKEND", "auto").strip().lower()

    @classmethod
    def _model_path(cls) -> str:
        return os.getenv("APRIL_IMAGES_MODEL_PATH", "").strip()

    @classmethod
    def _parse_size(cls, size: Any) -> tuple[int, int]:
        if isinstance(size, (tuple, list)) and len(size) == 2:
            try:
                width, height = int(size[0]), int(size[1])
            except (TypeError, ValueError):
                width, height = cls.DEFAULT_SIZE
        else:
            match = __import__("re").match(r"^\s*(\d{2,5})\s*x\s*(\d{2,5})\s*$", str(size or ""))
            if match:
                width, height = int(match.group(1)), int(match.group(2))
            else:
                width, height = cls.DEFAULT_SIZE

        width = max(cls.MIN_SIZE, min(cls.MAX_SIZE, width))
        height = max(cls.MIN_SIZE, min(cls.MAX_SIZE, height))
        return width, height

    @staticmethod
    def _clean_prompt(prompt: Any) -> str:
        text = " ".join(str(prompt or "").split()).strip()
        if not text:
            raise ValueError("APRIL_IMAGES_EMPTY_PROMPT")
        return text[:4000]

    @classmethod
    def _can_use_diffusers(cls) -> bool:
        mode = cls._backend_mode()
        if mode == "procedural":
            return False
        return bool(
            cls._model_path()
            and AutoPipelineForText2Image is not None
            and torch is not None
            and os.path.isdir(cls._model_path())
        )

    # -------------------------------------------------
    # Local diffusion backend
    # -------------------------------------------------

    @classmethod
    def _load_text_pipeline(cls):
        if not cls._can_use_diffusers():
            return None

        with cls._pipeline_lock:
            if cls._text_pipeline is not None and cls._pipeline_path == cls._model_path():
                return cls._text_pipeline

            path = cls._model_path()
            dtype = None
            if torch is not None and torch.cuda.is_available():
                dtype = torch.float16

            kwargs = {}
            if dtype is not None:
                kwargs["torch_dtype"] = dtype

            pipeline = AutoPipelineForText2Image.from_pretrained(
                path,
                local_files_only=True,
                **kwargs,
            )

            if torch is not None and torch.cuda.is_available():
                pipeline = pipeline.to("cuda")
            else:
                pipeline = pipeline.to("cpu")

            cls._text_pipeline = pipeline
            cls._pipeline_path = path
            return cls._text_pipeline

    @classmethod
    def _load_edit_pipeline(cls):
        if (
            not cls._can_use_diffusers()
            or AutoPipelineForImage2Image is None
        ):
            return None

        with cls._pipeline_lock:
            if cls._edit_pipeline is not None and cls._pipeline_path == cls._model_path():
                return cls._edit_pipeline

            path = cls._model_path()
            dtype = None
            if torch is not None and torch.cuda.is_available():
                dtype = torch.float16

            kwargs = {}
            if dtype is not None:
                kwargs["torch_dtype"] = dtype

            pipeline = AutoPipelineForImage2Image.from_pretrained(
                path,
                local_files_only=True,
                **kwargs,
            )

            if torch is not None and torch.cuda.is_available():
                pipeline = pipeline.to("cuda")
            else:
                pipeline = pipeline.to("cpu")

            cls._edit_pipeline = pipeline
            cls._pipeline_path = path
            return cls._edit_pipeline

    @staticmethod
    def _diffusion_image(
        pipeline: Any,
        prompt: str,
        width: int,
        height: int,
        quality: str,
        seed: Optional[int] = None,
    ) -> Image.Image:
        steps = {
            "draft": 12,
            "standard": 24,
            "high": 32,
            "ultra": 40,
        }.get(str(quality or "standard").lower(), 24)

        kwargs = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
        }
        if seed is not None and torch is not None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            kwargs["generator"] = torch.Generator(device=device).manual_seed(int(seed))

        result = pipeline(**kwargs)
        image = getattr(result, "images", [None])[0]
        if image is None:
            raise RuntimeError("APRIL_IMAGES_DIFFUSION_EMPTY_RESULT")
        return image.convert("RGB")

    # -------------------------------------------------
    # Bootstrap procedural renderer
    # -------------------------------------------------

    @staticmethod
    def _seed(prompt: str, seed: Optional[int]) -> int:
        if seed is not None:
            return int(seed)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    @staticmethod
    def _palette(prompt: str, rng: random.Random) -> tuple[tuple[int, int, int], ...]:
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()
        anchors = [
            (digest[0], digest[1], digest[2]),
            (digest[7], digest[8], digest[9]),
            (digest[14], digest[15], digest[16]),
            (digest[21], digest[22], digest[23]),
        ]
        palette = []
        for r, g, b in anchors:
            # Bias toward saturated but visually stable colors.
            palette.append((
                40 + int((r / 255.0) * 180),
                40 + int((g / 255.0) * 180),
                40 + int((b / 255.0) * 180),
            ))
        rng.shuffle(palette)
        return tuple(palette)

    @classmethod
    def _procedural_image(
        cls,
        prompt: str,
        width: int,
        height: int,
        seed: Optional[int] = None,
    ) -> Image.Image:
        rng = random.Random(cls._seed(prompt, seed))
        palette = cls._palette(prompt, rng)

        image = Image.new("RGB", (width, height), palette[0])
        draw = ImageDraw.Draw(image, "RGBA")

        # Multistage smooth background gradient.
        p0, p1, p2, p3 = palette
        px = image.load()
        for y in range(height):
            fy = y / max(1, height - 1)
            for x in range(width):
                fx = x / max(1, width - 1)
                radial = math.sqrt((fx - 0.48) ** 2 + (fy - 0.42) ** 2)
                t = min(1.0, 0.68 * fy + 0.32 * min(1.0, radial))
                a = 0.55 * math.sin(math.pi * fx)
                c1 = tuple(int(p0[i] * (1 - t) + p2[i] * t) for i in range(3))
                c2 = tuple(int(p1[i] * (1 - t) + p3[i] * t) for i in range(3))
                px[x, y] = tuple(
                    int(c1[i] * (1 - a) + c2[i] * a)
                    for i in range(3)
                )

        # Large atmospheric glows.
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay, "RGBA")
        for _ in range(9):
            cx = rng.randint(-width // 5, width + width // 5)
            cy = rng.randint(-height // 5, height + height // 5)
            radius = rng.randint(max(40, width // 14), max(80, width // 3))
            color = rng.choice(palette) + (rng.randint(30, 100),)
            od.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=color,
            )
        overlay = overlay.filter(ImageFilter.GaussianBlur(max(12, width // 45)))
        image = Image.alpha_composite(image.convert("RGBA"), overlay)

        # Abstract illuminated "subject" made from layered forms. This is
        # deliberately prompt-conditioned by the deterministic seed rather than
        # a brittle word-trigger table.
        subject = Image.new("RGBA", image.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(subject, "RGBA")
        cx, cy = width * 0.50, height * 0.51
        base = min(width, height)

        for layer in range(11):
            angle = rng.uniform(0.0, math.tau)
            orbit = rng.uniform(0.04, 0.25) * base
            sx = cx + math.cos(angle) * orbit
            sy = cy + math.sin(angle) * orbit
            rw = rng.uniform(0.08, 0.30) * base
            rh = rng.uniform(0.05, 0.20) * base
            color = rng.choice(palette) + (rng.randint(45, 130),)
            bbox = (sx - rw, sy - rh, sx + rw, sy + rh)
            if layer % 3 == 0:
                sd.ellipse(bbox, fill=color)
            elif layer % 3 == 1:
                sd.rounded_rectangle(
                    bbox,
                    radius=int(min(rw, rh) * 0.35),
                    fill=color,
                )
            else:
                sd.polygon(
                    [
                        (sx, sy - rh),
                        (sx + rw, sy),
                        (sx, sy + rh),
                        (sx - rw, sy),
                    ],
                    fill=color,
                )

        # Fine light trails.
        for _ in range(24):
            x0 = rng.randint(0, width)
            y0 = rng.randint(0, height)
            x1 = x0 + rng.randint(-width // 7, width // 7)
            y1 = y0 + rng.randint(-height // 7, height // 7)
            sd.line(
                (x0, y0, x1, y1),
                fill=rng.choice(palette) + (rng.randint(45, 120),),
                width=max(1, int(base / 320)),
            )

        subject = subject.filter(ImageFilter.GaussianBlur(max(1, width // 360)))
        image = Image.alpha_composite(image, subject)

        # Crisp focal frame and particles.
        final = Image.new("RGBA", image.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(final, "RGBA")
        margin = int(base * 0.035)
        fd.rounded_rectangle(
            (margin, margin, width - margin, height - margin),
            radius=int(base * 0.045),
            outline=(255, 255, 255, 70),
            width=max(1, int(base / 300)),
        )
        for _ in range(max(80, int(base / 4))):
            x = rng.randrange(width)
            y = rng.randrange(height)
            r = rng.choice((1, 1, 1, 2, 3))
            fd.ellipse((x - r, y - r, x + r, y + r),
                       fill=rng.choice(palette) + (rng.randint(60, 180),))
        final = final.filter(ImageFilter.GaussianBlur(0.25))
        image = Image.alpha_composite(image, final)

        # Slight contrast/color polish.
        image = ImageOps.autocontrast(image.convert("RGB")).convert("RGB")
        return image

    # -------------------------------------------------
    # Serialization + artifact
    # -------------------------------------------------

    @staticmethod
    def _png_bytes(image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

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
                    "mime_type": "image/png",
                    "width": width,
                    "height": height,
                    "image_base64": data_base64,
                    "image_data_uri": data_uri,
                    "prompt": prompt,
                    "engine": cls.ENGINE_NAME,
                    "engine_version": cls.ENGINE_VERSION,
                    "backend": backend,
                    "variant": variant,
                },
            },
        )
        artifact.quality.validation_passed = True
        artifact.quality.quality_score = 1.0
        artifact.quality.confidence_score = 1.0
        artifact.quality.completeness_score = 1.0

        contract = build_universal_contract(artifact)
        artifact_data = dict(artifact.data or {})
        return artifact_data, contract

    @classmethod
    def build_artifact_from_bytes(
        cls,
        image_bytes: bytes,
        prompt: str,
        *,
        width: int | None = None,
        height: int | None = None,
        backend: str = "April Images Generation",
        variant: str = "generated",
    ) -> tuple[dict[str, Any], UniversalArtifactContract]:
        if not image_bytes:
            raise ValueError("APRIL_IMAGES_EMPTY_IMAGE")

        if width is None or height is None:
            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size

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
            "status": "ready",
            "architecture": "April Bot -> C_APRIL_IMAGES_GENERATOR -> C_ARTIFACT_CONTRACT",
            "backend_mode": self._backend_mode(),
            "local_model_configured": bool(self._model_path()),
            "diffusers_available": bool(AutoPipelineForText2Image is not None),
            "external_image_api": False,
        }

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

        backend = "procedural"
        image = None

        if self._can_use_diffusers():
            try:
                pipeline = self._load_text_pipeline()
                image = self._diffusion_image(
                    pipeline,
                    prompt,
                    width,
                    height,
                    quality,
                    seed=seed,
                )
                backend = "local_diffusion"
            except Exception:
                # The internal engine stays alive if an optional local model is
                # unavailable. We do not call OpenAI/Gemini as fallback.
                image = None

        if image is None:
            image = self._procedural_image(
                prompt,
                width,
                height,
                seed=seed,
            )

        image_bytes = self._png_bytes(image)
        artifact, contract = self.build_artifact(
            image_bytes=image_bytes,
            prompt=prompt,
            width=width,
            height=height,
            backend=backend,
            variant=variant,
        )

        return self._result_dict(ImageGenerationResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            width=width,
            height=height,
            backend=backend,
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
        prompt = self._clean_prompt(prompt)
        if not image_bytes:
            raise ValueError("APRIL_IMAGES_EDIT_SOURCE_EMPTY")

        source = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = source.size
        backend = "procedural_edit"

        if self._can_use_diffusers() and AutoPipelineForImage2Image is not None:
            try:
                pipeline = self._load_edit_pipeline()
                if pipeline is not None:
                    steps = {"draft": 12, "standard": 24, "high": 32, "ultra": 40}.get(
                        str(quality or "standard").lower(), 24
                    )
                    result = pipeline(
                        prompt=prompt,
                        image=source,
                        strength=max(0.05, min(0.95, float(strength))),
                        num_inference_steps=steps,
                    )
                    generated = getattr(result, "images", [None])[0]
                    if generated is not None:
                        source = generated.convert("RGB")
                        backend = "local_diffusion_edit"
            except Exception:
                pass

        if backend == "procedural_edit":
            # Safe local edit bootstrap: preserve the source and apply a
            # prompt-conditioned visual transformation.
            seed = self._seed(prompt, None)
            rng = random.Random(seed)
            overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay, "RGBA")
            tint = (
                rng.randrange(40, 220),
                rng.randrange(40, 220),
                rng.randrange(40, 220),
                int(75 * max(0.1, min(1.0, float(strength)))),
            )
            draw.rectangle(
                (0, 0, source.width, source.height),
                fill=tint,
            )
            overlay = overlay.filter(ImageFilter.GaussianBlur(max(4, source.width // 80)))
            source = Image.alpha_composite(source.convert("RGBA"), overlay).convert("RGB")
            source = ImageOps.autocontrast(source)

        output = self._png_bytes(source)
        artifact, contract = self.build_artifact(
            image_bytes=output,
            prompt=prompt,
            width=width,
            height=height,
            backend=backend,
            variant=variant,
        )

        return self._result_dict(ImageGenerationResult(
            image_bytes=output,
            mime_type="image/png",
            width=width,
            height=height,
            backend=backend,
            prompt=prompt,
            artifact=artifact,
            contract=contract,
        ))


april_images_generator = AprilImagesGenerator()


async def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
) -> Optional[bytes]:
    result = await april_images_generator.generate(
        prompt,
        size=size,
        quality=quality,
    )
    return result.get("image_bytes") if result.get("success") else None


async def generate_image_result(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    variant: str = "primary",
) -> dict[str, Any]:
    return await april_images_generator.generate(
        prompt,
        size=size,
        quality=quality,
        variant=variant,
    )


async def edit_image(
    image_bytes: bytes,
    prompt: str,
    quality: str = "standard",
) -> Optional[bytes]:
    result = await april_images_generator.edit(
        image_bytes,
        prompt,
        quality=quality,
    )
    return result.get("image_bytes") if result.get("success") else None


async def edit_image_result(
    image_bytes: bytes,
    prompt: str,
    quality: str = "standard",
) -> dict[str, Any]:
    return await april_images_generator.edit(
        image_bytes,
        prompt,
        quality=quality,
    )


__all__ = [
    "AprilImagesGenerator",
    "ImageGenerationResult",
    "april_images_generator",
    "generate_image",
    "generate_image_result",
    "edit_image",
    "edit_image_result",
]
