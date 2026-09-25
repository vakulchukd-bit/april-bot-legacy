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
    ENGINE_VERSION = "2.2.0"
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
        return text

    @staticmethod
    def _negative_prompt(spec: Optional[dict[str, Any]] = None) -> str:
        values = [
            "low quality", "blurry", "pixelated", "jpeg artifacts",
            "deformed", "bad anatomy", "extra limbs", "duplicate subject",
            "distorted face", "disfigured hands", "malformed eyes",
            "watermark", "text artifacts", "cropped subject",
        ]
        if isinstance(spec, dict) and isinstance(spec.get("negative"), list):
            values.extend(str(x).strip() for x in spec["negative"] if str(x).strip())
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
        return "\n".join(parts)

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
        device = cls._device()
        methods = ["enable_vae_slicing", "enable_vae_tiling"]
        if device != "cpu" or os.getenv("APRIL_IMAGES_CPU_ATTENTION_SLICING", "0").strip().lower() in {"1", "true", "yes", "on"}:
            methods.append("enable_attention_slicing")
        for method_name in methods:
            method = getattr(pipeline, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass

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
                kwargs["dtype"] = dtype
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
                kwargs["dtype"] = dtype
            if os.getenv("APRIL_IMAGES_USE_SAFETENSORS", "1").strip().lower() in {"1", "true", "yes"}:
                kwargs["use_safetensors"] = True

            pipeline = AutoPipelineForImage2Image.from_pretrained(source, **kwargs)
            cls._edit_pipeline = cls._configure_pipeline(pipeline)
            cls._pipeline_path = source
            cls._pipeline_cache_key = cache_key
            return cls._edit_pipeline

    @classmethod
    def _token_ids_for_long_prompt(cls, tokenizer: Any, text: str) -> list[int]:
        """Return raw token ids without truncation.

        The 77-token value exposed by CLIP is the native size of one encoder
        window. It is not an April/OpenAI prompt budget. We split an arbitrarily
        long prompt into native windows and encode every window separately.
        No April-side maximum is imposed here.
        """
        try:
            return list(
                tokenizer.encode(
                    str(text or ""),
                    add_special_tokens=False,
                    truncation=False,
                )
            )
        except Exception as exc:
            raise RuntimeError("APRIL_IMAGES_TOKENIZATION_FAILED") from exc

    @classmethod
    def _prompt_chunks(
        cls,
        tokenizer: Any,
        text: str,
    ) -> list[list[int]]:
        """Split raw token ids into native tokenizer windows without loss.

        Each window reserves its BOS/EOS slots. The tokenizer/encoder's own
        ``model_max_length`` defines the size of a single native window; there
        is deliberately no additional April/OpenAI token cap.
        """
        model_max = getattr(tokenizer, "model_max_length", None)
        try:
            model_max = int(model_max)
        except (TypeError, ValueError):
            model_max = None

        if not model_max or model_max <= 2:
            config = getattr(getattr(tokenizer, "init_kwargs", {}), "get", lambda *_: None)(
                "model_max_length"
            )
            try:
                model_max = int(config)
            except (TypeError, ValueError):
                model_max = None

        if not model_max or model_max <= 2:
            raise RuntimeError("APRIL_IMAGES_TOKENIZER_MAX_LENGTH_UNAVAILABLE")

        bos_id = getattr(tokenizer, "bos_token_id", None)
        eos_id = getattr(tokenizer, "eos_token_id", None)
        pad_id = getattr(tokenizer, "pad_token_id", None)
        if bos_id is None:
            bos_id = getattr(tokenizer, "cls_token_id", None)
        if eos_id is None:
            eos_id = getattr(tokenizer, "sep_token_id", None)
        if pad_id is None:
            pad_id = eos_id if eos_id is not None else 0

        if bos_id is None or eos_id is None:
            raise RuntimeError("APRIL_IMAGES_SPECIAL_TOKENS_UNAVAILABLE")

        raw_ids = cls._token_ids_for_long_prompt(tokenizer, text)
        chunk_body = model_max - 2
        chunks: list[list[int]] = []

        if not raw_ids:
            raw_ids = []

        for start in range(0, len(raw_ids), chunk_body):
            body = raw_ids[start:start + chunk_body]
            ids = [int(bos_id), *map(int, body), int(eos_id)]
            ids.extend([int(pad_id)] * (model_max - len(ids)))
            chunks.append(ids)

        if not chunks:
            chunks.append([int(bos_id), int(eos_id)] + [int(pad_id)] * (model_max - 2))

        return chunks

    @classmethod
    def _encode_text_encoder_chunks(
        cls,
        tokenizer: Any,
        text_encoder: Any,
        text: str,
        *,
        device: Any,
    ) -> tuple[Any, Any, int]:
        """Encode every native CLIP window and concatenate hidden states.

        Returns ``(hidden_states, pooled_embedding, raw_token_count)``.
        ``pooled_embedding`` is the mean of the native-window pooled vectors;
        this preserves information from every window instead of truncating to
        the first 77 tokens.
        """
        raw_ids = cls._token_ids_for_long_prompt(tokenizer, text)
        raw_token_count = len(raw_ids)
        chunks = cls._prompt_chunks(tokenizer, text)
        pad_id = getattr(tokenizer, "pad_token_id", None)
        if pad_id is None:
            pad_id = getattr(tokenizer, "eos_token_id", 0)

        if torch is None:
            raise RuntimeError("APRIL_IMAGES_TORCH_NOT_INSTALLED")

        input_ids = torch.tensor(chunks, dtype=torch.long, device=device)
        attention_mask = (input_ids != int(pad_id)).long()

        with torch.inference_mode():
            outputs = text_encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                return_dict=True,
            )

        hidden_states = getattr(outputs, "hidden_states", None)
        if hidden_states:
            hidden = hidden_states[-2]
        else:
            hidden = getattr(outputs, "last_hidden_state", None)
            if hidden is None:
                raise RuntimeError("APRIL_IMAGES_TEXT_ENCODER_HIDDEN_STATE_MISSING")

        pooled = getattr(outputs, "text_embeds", None)
        if pooled is None:
            pooled = getattr(outputs, "pooler_output", None)
        if pooled is None:
            try:
                candidate = outputs[0]
            except Exception:
                candidate = None
            if candidate is not None and getattr(candidate, "ndim", 0) == 2:
                pooled = candidate

        if pooled is not None and getattr(pooled, "ndim", 0) >= 2:
            pooled = pooled.mean(dim=0, keepdim=True)

        # ``model_max`` is returned for diagnostics; the actual prompt length
        # can grow without an April-side maximum because more native windows
        # are simply concatenated.
        return hidden, pooled, raw_token_count

    @classmethod
    def _pad_sequence_length(cls, tensor: Any, target_length: int) -> Any:
        if tensor is None:
            return None
        current = int(tensor.shape[1])
        if current >= target_length:
            return tensor
        if torch is None:
            raise RuntimeError("APRIL_IMAGES_TORCH_NOT_INSTALLED")
        pad = torch.zeros(
            (tensor.shape[0], target_length - current, tensor.shape[2]),
            dtype=tensor.dtype,
            device=tensor.device,
        )
        return torch.cat([tensor, pad], dim=1)

    @classmethod
    def _long_prompt_kwargs(
        cls,
        pipeline: Any,
        prompt: str,
        negative_prompt: str,
    ) -> dict[str, Any]:
        """Encode long prompts without imposing an April/OpenAI token cap.

        SDXL's CLIP encoders operate on native 77-token windows. That value is
        a backend window size, not a request limit. This implementation uses
        every native window and concatenates their hidden states before calling
        Diffusers. No Compel dependency and no prompt truncation are required.
        """
        if torch is None:
            raise RuntimeError("APRIL_IMAGES_TORCH_NOT_INSTALLED")

        tokenizer_1 = getattr(pipeline, "tokenizer", None)
        tokenizer_2 = getattr(pipeline, "tokenizer_2", None)
        text_encoder_1 = getattr(pipeline, "text_encoder", None)
        text_encoder_2 = getattr(pipeline, "text_encoder_2", None)
        if tokenizer_1 is None or text_encoder_1 is None:
            raise RuntimeError("APRIL_IMAGES_TEXT_ENCODER_NOT_AVAILABLE")

        execution_device = getattr(pipeline, "_execution_device", None)
        if execution_device is None:
            execution_device = cls._device()
        if not hasattr(execution_device, "type"):
            execution_device = torch.device(str(execution_device))

        hidden_1, _pooled_1, count_1 = cls._encode_text_encoder_chunks(
            tokenizer_1, text_encoder_1, prompt, device=execution_device
        )
        neg_hidden_1, _neg_pooled_1, neg_count_1 = cls._encode_text_encoder_chunks(
            tokenizer_1, text_encoder_1, negative_prompt or "", device=execution_device
        )

        if tokenizer_2 is not None and text_encoder_2 is not None:
            hidden_2, pooled_2, count_2 = cls._encode_text_encoder_chunks(
                tokenizer_2, text_encoder_2, prompt, device=execution_device
            )
            neg_hidden_2, neg_pooled_2, neg_count_2 = cls._encode_text_encoder_chunks(
                tokenizer_2, text_encoder_2, negative_prompt or "", device=execution_device
            )

            target_prompt_len = max(int(hidden_1.shape[1]), int(hidden_2.shape[1]))
            target_negative_len = max(
                int(neg_hidden_1.shape[1]), int(neg_hidden_2.shape[1])
            )
            hidden_1 = cls._pad_sequence_length(hidden_1, target_prompt_len)
            hidden_2 = cls._pad_sequence_length(hidden_2, target_prompt_len)
            neg_hidden_1 = cls._pad_sequence_length(neg_hidden_1, target_negative_len)
            neg_hidden_2 = cls._pad_sequence_length(neg_hidden_2, target_negative_len)

            prompt_embeds = torch.cat([hidden_1, hidden_2], dim=-1)
            negative_prompt_embeds = torch.cat([neg_hidden_1, neg_hidden_2], dim=-1)
            pooled_prompt_embeds = pooled_2
            negative_pooled_prompt_embeds = neg_pooled_2

            prompt_chunks = max(count_1, count_2)
            negative_chunks = max(neg_count_1, neg_count_2)
        else:
            prompt_embeds = hidden_1
            negative_prompt_embeds = neg_hidden_1
            pooled_prompt_embeds = None
            negative_pooled_prompt_embeds = None
            prompt_chunks = count_1
            negative_chunks = neg_count_1

        if prompt_embeds is None or negative_prompt_embeds is None:
            raise RuntimeError("APRIL_IMAGES_PROMPT_EMBEDDINGS_MISSING")

        # Match the positive/negative sequence lengths; there is no maximum
        # here, only equality required by classifier-free guidance.
        shared_len = max(
            int(prompt_embeds.shape[1]),
            int(negative_prompt_embeds.shape[1]),
        )
        prompt_embeds = cls._pad_sequence_length(prompt_embeds, shared_len)
        negative_prompt_embeds = cls._pad_sequence_length(
            negative_prompt_embeds, shared_len
        )

        # Keep embeddings compatible with the pipeline's UNet/text dtype.
        target_dtype = getattr(getattr(pipeline, "unet", None), "dtype", None)
        if target_dtype is not None and getattr(prompt_embeds, "is_floating_point", lambda: False)():
            prompt_embeds = prompt_embeds.to(dtype=target_dtype)
            negative_prompt_embeds = negative_prompt_embeds.to(dtype=target_dtype)
            if pooled_prompt_embeds is not None:
                pooled_prompt_embeds = pooled_prompt_embeds.to(dtype=target_dtype)
            if negative_pooled_prompt_embeds is not None:
                negative_pooled_prompt_embeds = negative_pooled_prompt_embeds.to(dtype=target_dtype)

        print(
            "🧠 IMAGE PROMPT ENCODING:",
            {
                "prompt_raw_tokens": count_1 if tokenizer_2 is None else max(count_1, count_2),
                "negative_raw_tokens": neg_count_1 if tokenizer_2 is None else max(neg_count_1, neg_count_2),
                "prompt_native_windows": prompt_chunks,
                "negative_native_windows": negative_chunks,
                "strategy": "native_clip_window_chunking",
                "april_openai_prompt_cap": None,
            },
        )

        result = {
            "prompt_embeds": prompt_embeds,
            "negative_prompt_embeds": negative_prompt_embeds,
        }
        if pooled_prompt_embeds is not None:
            result["pooled_prompt_embeds"] = pooled_prompt_embeds
        if negative_pooled_prompt_embeds is not None:
            result["negative_pooled_prompt_embeds"] = negative_pooled_prompt_embeds
        return result

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
        explicit_steps = os.getenv("APRIL_IMAGES_INFERENCE_STEPS", "").strip()
        if explicit_steps:
            try:
                steps = int(explicit_steps)
            except ValueError:
                pass
        kwargs: dict[str, Any] = {
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }

        # Never truncate an image prompt to the OpenAI/provider budget.
        # Encode every native backend window and concatenate its embeddings.
        prompt_kwargs = cls._long_prompt_kwargs(pipeline, prompt, negative_prompt)
        kwargs.update(prompt_kwargs)
        if seed is not None and torch is not None:
            generator_device = "cuda" if cls._device() == "cuda" else "cpu"
            kwargs["generator"] = torch.Generator(device=generator_device).manual_seed(int(seed))

        if torch is not None:
            with torch.inference_mode():
                result = pipeline(**kwargs)
        else:
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
            "style": str(spec.get("style") or "illustration"),
            "quality": str(spec.get("quality") or "standard"),
            "negative": [str(x) for x in (spec.get("negative") or []) if str(x).strip()],
            "steps": spec.get("steps"),
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
            "long_prompt_support": True,
            "long_prompt_strategy": "native_clip_window_chunking",
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
            "image": source,
            "strength": max(0.05, min(0.95, float(strength))),
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }
        kwargs.update(
            self._long_prompt_kwargs(
                pipeline,
                prompt,
                self._negative_prompt(),
            )
        )
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
