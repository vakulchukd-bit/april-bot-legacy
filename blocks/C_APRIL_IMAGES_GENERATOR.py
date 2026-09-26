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
import html
import io
import json
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
    ENGINE_VERSION = "2.3.0"
    BACKEND = "diffusers_single_backend"

    DEFAULT_SIZE = (512, 512)
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
                "stabilityai/sdxl-turbo",
            ).strip()
            or "stabilityai/sdxl-turbo"
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
    def _is_turbo_model(cls) -> bool:
        return "sdxl-turbo" in cls._model_source().strip().lower()

    @classmethod
    def _quality_settings(cls, quality: str) -> tuple[int, float]:
        """Return sampling settings for the configured image backend.

        SDXL Turbo is explicitly trained for 1-4 denoising steps with guidance
        disabled.  The ordinary SDXL profile remains available when a different
        model id is explicitly configured.
        """
        normalized = str(quality or "standard").strip().lower()
        if cls._is_turbo_model():
            return {
                "draft": (1, 0.0),
                "standard": (1, 0.0),
                "high": (2, 0.0),
                "ultra": (4, 0.0),
            }.get(normalized, (1, 0.0))
        return {
            "draft": (28, 6.0),
            "standard": (40, 6.5),
            "high": (50, 7.0),
            "ultra": (60, 7.5),
        }.get(normalized, (40, 6.5))

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

    @classmethod
    def _extract_semantic_prompt(cls, value: Any, *, _depth: int = 0) -> str:
        """Extract a semantic image request without feeding render artifacts to CLIP.

        The local image engine must receive a visual description, not a serialized
        MachineResponse, SVG/XML markup, data URI, or base64 payload. OpenAI remains
        the semantic planner; this Diffusers backend remains the only pixel generator.
        """
        if _depth > 4 or value is None:
            return ""

        if isinstance(value, dict):
            preferred_keys = (
                "prompt", "description", "visual_prompt", "image_prompt",
                "image", "visual", "visual_context",
                "scene", "subject", "request", "title", "summary",
                "answer", "content", "alt",
            )
            for key in preferred_keys:
                if key in value:
                    candidate = cls._extract_semantic_prompt(value.get(key), _depth=_depth + 1)
                    if candidate:
                        return candidate
            for key in ("data", "spec"):
                if key in value:
                    candidate = cls._extract_semantic_prompt(value.get(key), _depth=_depth + 1)
                    if candidate:
                        return candidate
            return ""

        if isinstance(value, (list, tuple)):
            parts = []
            for item in value[:16]:
                candidate = cls._extract_semantic_prompt(item, _depth=_depth + 1)
                if candidate:
                    parts.append(candidate)
            return " ".join(parts).strip()

        text = str(value or "").strip()
        if not text:
            return ""

        if text[:1] in "{[":
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = None
            if parsed is not None:
                candidate = cls._extract_semantic_prompt(parsed, _depth=_depth + 1)
                if candidate:
                    return candidate

        lowered = text.lstrip().lower()
        if (
            lowered.startswith("<svg")
            or lowered.startswith("<?xml")
            or "data:image/" in lowered
            or "<svg " in lowered
            or "<path" in lowered
            or "<rect" in lowered
            or "<circle" in lowered
        ):
            candidates = []
            patterns = (
                r"aria-label=[\"']([^\"']+)[\"']",
                r"data-(?:prompt|description|alt)=[\"']([^\"']+)[\"']",
                r"<title[^>]*>(.*?)</title>",
                r"<desc[^>]*>(.*?)</desc>",
                r"<text[^>]*>(.*?)</text>",
            )
            for pattern in patterns:
                for match in re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                    cleaned = html.unescape(re.sub(r"<[^>]+>", " ", str(match)))
                    cleaned = " ".join(cleaned.split()).strip()
                    if cleaned:
                        candidates.append(cleaned)
            if candidates:
                return " ".join(dict.fromkeys(candidates))
            return ""

        text = re.sub(r"^```(?:json|text|xml|svg)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()
        text = re.sub(r"^data:image/[^;]+;base64,.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
        return " ".join(text.split()).strip()

    @classmethod
    def _clean_prompt(cls, prompt: Any) -> str:
        text = cls._extract_semantic_prompt(prompt)
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

    @classmethod
    def _compose_prompt(cls, prompt: str, spec: Optional[dict[str, Any]] = None) -> str:
        semantic_prompt = cls._clean_prompt(prompt)
        parts = [semantic_prompt]
        if isinstance(spec, dict):
            style = cls._clean_prompt(spec.get("style") or "") if str(spec.get("style") or "").strip() else ""
            if style and style.lower() not in semantic_prompt.lower():
                parts.append(f"Style: {style}")

            context = spec.get("visual_context")
            if isinstance(context, dict):
                for key in (
                    "subject", "composition", "lighting", "camera",
                    "environment", "palette", "mood", "materials",
                    "character", "pose", "background", "details",
                ):
                    value = context.get(key)
                    if value:
                        semantic_value = cls._extract_semantic_prompt(value)
                        if semantic_value:
                            label = key.replace("_", " " ).title()
                            parts.append(f"{label}: {semantic_value}")
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

        # SDXL Turbo requires trailing timestep spacing.  This is part of the
        # model's sampling contract, not an alternate backend or a fallback.
        if cls._is_turbo_model():
            try:
                from diffusers import EulerAncestralDiscreteScheduler
                pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(
                    pipeline.scheduler.config,
                    timestep_spacing="trailing",
                )
            except Exception as exc:
                raise RuntimeError("APRIL_IMAGES_TURBO_SCHEDULER_CONFIGURATION_FAILED") from exc

        # Do not enable attention slicing by default: on CPU it can make the
        # already expensive denoising loop slower.  It remains an explicit opt-in.
        if os.getenv("APRIL_IMAGES_CPU_ATTENTION_SLICING", "0").strip().lower() in {"1", "true", "yes", "on"}:
            method = getattr(pipeline, "enable_attention_slicing", None)
            if callable(method):
                method()

        if device != "cpu":
            for method_name in ("enable_vae_slicing", "enable_vae_tiling"):
                method = getattr(pipeline, method_name, None)
                if callable(method):
                    try:
                        method()
                    except Exception:
                        pass

        # Hugging Face recommends keeping the default SDXL VAE in float32.
        # upcast_vae() performs that conversion once for CUDA/MPS inference.
        if cls._is_turbo_model() and device != "cpu":
            method = getattr(pipeline, "upcast_vae", None)
            if callable(method):
                method()

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
            if cls._is_turbo_model() and cls._device() in {"cuda", "mps"}:
                kwargs["variant"] = "fp16"

            pipeline = AutoPipelineForText2Image.from_pretrained(source, **kwargs)
            cls._text_pipeline = cls._configure_pipeline(pipeline)
            cls._pipeline_path = source
            cls._pipeline_cache_key = cache_key
            print(
                "🧠 IMAGE BACKEND READY:",
                {
                    "model": source,
                    "turbo": cls._is_turbo_model(),
                    "device": cls._device(),
                    "dtype": str(cls._dtype()),
                    "default_size": cls.DEFAULT_SIZE,
                    "standard_steps": cls._quality_settings("standard")[0],
                    "guidance_scale": cls._quality_settings("standard")[1],
                },
            )
            return cls._text_pipeline

    @classmethod
    def _load_edit_pipeline(cls):
        cls._require_backend()
        source = cls._model_source()
        cache_key = f"edit::{source}::{cls._dtype()}::{cls._device()}::{cls._local_files_only()}"
        with cls._pipeline_lock:
            if cls._edit_pipeline is not None and cls._pipeline_cache_key == cache_key:
                return cls._edit_pipeline

            # SDXL Turbo uses the same checkpoint for text-to-image and
            # image-to-image.  Reuse the loaded pipeline when possible so an
            # edit request does not download/load the model a second time.
            if cls._is_turbo_model() and cls._text_pipeline is not None:
                try:
                    pipeline = AutoPipelineForImage2Image.from_pipe(cls._text_pipeline)
                    cls._edit_pipeline = pipeline
                    cls._pipeline_path = source
                    cls._pipeline_cache_key = cache_key
                    return cls._edit_pipeline
                except Exception as exc:
                    raise RuntimeError("APRIL_IMAGES_TURBO_EDIT_PIPELINE_CONFIGURATION_FAILED") from exc

            kwargs: dict[str, Any] = {
                "local_files_only": cls._local_files_only(),
            }
            dtype = cls._dtype()
            if dtype is not None:
                kwargs["dtype"] = dtype
            if os.getenv("APRIL_IMAGES_USE_SAFETENSORS", "1").strip().lower() in {"1", "true", "yes"}:
                kwargs["use_safetensors"] = True
            if cls._is_turbo_model() and cls._device() in {"cuda", "mps"}:
                kwargs["variant"] = "fp16"

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
    def _pad_batch_size(cls, tensor: Any, target_batch: int) -> Any:
        """Align the number of prompt chunks used by positive/negative embeds.

        Long-prompt chunking can produce multiple positive CLIP windows while
        an empty/short negative prompt produces only one. Diffusers expects
        classifier-free positive/negative embeddings to have the same batch
        dimension. The negative conditioning is therefore repeated across
        the missing windows rather than allowing a shape mismatch to reach
        the diffusion pipeline.
        """
        if tensor is None:
            return None
        current = int(tensor.shape[0])
        if current == target_batch:
            return tensor
        if current <= 0 or target_batch <= 0:
            raise RuntimeError("APRIL_IMAGES_PROMPT_BATCH_INVALID")
        if current > target_batch:
            return tensor[:target_batch]
        repeats = target_batch - current
        tail = tensor[-1:].expand(repeats, *tensor.shape[1:])
        return torch.cat([tensor, tail], dim=0)

    @classmethod
    def _long_prompt_kwargs(
        cls,
        pipeline: Any,
        prompt: str,
        negative_prompt: str,
        *,
        include_negative: bool = True,
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

        neg_hidden_1 = None
        _neg_pooled_1 = None
        neg_count_1 = 0
        if include_negative:
            neg_hidden_1, _neg_pooled_1, neg_count_1 = cls._encode_text_encoder_chunks(
                tokenizer_1, text_encoder_1, negative_prompt or "", device=execution_device
            )

        if tokenizer_2 is not None and text_encoder_2 is not None:
            hidden_2, pooled_2, count_2 = cls._encode_text_encoder_chunks(
                tokenizer_2, text_encoder_2, prompt, device=execution_device
            )

            neg_hidden_2 = None
            neg_pooled_2 = None
            neg_count_2 = 0
            if include_negative:
                neg_hidden_2, neg_pooled_2, neg_count_2 = cls._encode_text_encoder_chunks(
                    tokenizer_2, text_encoder_2, negative_prompt or "", device=execution_device
                )

            target_prompt_len = max(int(hidden_1.shape[1]), int(hidden_2.shape[1]))
            hidden_1 = cls._pad_sequence_length(hidden_1, target_prompt_len)
            hidden_2 = cls._pad_sequence_length(hidden_2, target_prompt_len)

            prompt_batch = max(int(hidden_1.shape[0]), int(hidden_2.shape[0]))
            hidden_1 = cls._pad_batch_size(hidden_1, prompt_batch)
            hidden_2 = cls._pad_batch_size(hidden_2, prompt_batch)

            prompt_embeds = torch.cat([hidden_1, hidden_2], dim=-1)
            pooled_prompt_embeds = pooled_2
            if pooled_prompt_embeds is not None:
                pooled_prompt_embeds = cls._pad_batch_size(
                    pooled_prompt_embeds, prompt_batch
                )

            if include_negative:
                target_negative_len = max(
                    int(neg_hidden_1.shape[1]), int(neg_hidden_2.shape[1])
                )
                neg_hidden_1 = cls._pad_sequence_length(neg_hidden_1, target_negative_len)
                neg_hidden_2 = cls._pad_sequence_length(neg_hidden_2, target_negative_len)
                negative_batch = max(
                    int(neg_hidden_1.shape[0]),
                    int(neg_hidden_2.shape[0]),
                    prompt_batch,
                )
                neg_hidden_1 = cls._pad_batch_size(neg_hidden_1, negative_batch)
                neg_hidden_2 = cls._pad_batch_size(neg_hidden_2, negative_batch)
                prompt_embeds = cls._pad_batch_size(prompt_embeds, negative_batch)
                pooled_prompt_embeds = cls._pad_batch_size(
                    pooled_prompt_embeds, negative_batch
                ) if pooled_prompt_embeds is not None else None
                prompt_batch = negative_batch

                negative_prompt_embeds = torch.cat([neg_hidden_1, neg_hidden_2], dim=-1)
                negative_pooled_prompt_embeds = neg_pooled_2
                if negative_pooled_prompt_embeds is not None:
                    negative_pooled_prompt_embeds = cls._pad_batch_size(
                        negative_pooled_prompt_embeds, negative_batch
                    )
            else:
                negative_prompt_embeds = None
                negative_pooled_prompt_embeds = None

            prompt_chunks = max(count_1, count_2)
            negative_chunks = max(neg_count_1, neg_count_2) if include_negative else 0
        else:
            prompt_embeds = hidden_1
            pooled_prompt_embeds = None
            prompt_chunks = count_1
            if include_negative:
                negative_batch = max(int(prompt_embeds.shape[0]), int(neg_hidden_1.shape[0]))
                prompt_embeds = cls._pad_batch_size(prompt_embeds, negative_batch)
                neg_hidden_1 = cls._pad_batch_size(neg_hidden_1, negative_batch)
                negative_prompt_embeds = neg_hidden_1
                negative_pooled_prompt_embeds = _neg_pooled_1
                if negative_pooled_prompt_embeds is not None:
                    negative_pooled_prompt_embeds = cls._pad_batch_size(
                        negative_pooled_prompt_embeds, negative_batch
                    )
                prompt_chunks = max(count_1, 0)
                negative_chunks = neg_count_1
            else:
                negative_prompt_embeds = None
                negative_pooled_prompt_embeds = None
                negative_chunks = 0

        if prompt_embeds is None:
            raise RuntimeError("APRIL_IMAGES_PROMPT_EMBEDDINGS_MISSING")
        if include_negative and negative_prompt_embeds is None:
            raise RuntimeError("APRIL_IMAGES_NEGATIVE_PROMPT_EMBEDDINGS_MISSING")

        # Match the positive/negative sequence lengths; there is no maximum
        # here, only equality required by classifier-free guidance.
        if include_negative:
            if negative_prompt_embeds is None:
                raise RuntimeError("APRIL_IMAGES_NEGATIVE_PROMPT_EMBEDDINGS_MISSING")
            # Match both sequence length and batch size for classifier-free
            # guidance. The batch dimension equals the number of native CLIP
            # windows after long-prompt chunking.
            shared_len = max(
                int(prompt_embeds.shape[1]),
                int(negative_prompt_embeds.shape[1]),
            )
            prompt_embeds = cls._pad_sequence_length(prompt_embeds, shared_len)
            negative_prompt_embeds = cls._pad_sequence_length(
                negative_prompt_embeds, shared_len
            )
            shared_batch = max(
                int(prompt_embeds.shape[0]),
                int(negative_prompt_embeds.shape[0]),
            )
            prompt_embeds = cls._pad_batch_size(prompt_embeds, shared_batch)
            negative_prompt_embeds = cls._pad_batch_size(
                negative_prompt_embeds, shared_batch
            )
            if pooled_prompt_embeds is not None:
                pooled_prompt_embeds = cls._pad_batch_size(
                    pooled_prompt_embeds, shared_batch
                )
            if negative_pooled_prompt_embeds is not None:
                negative_pooled_prompt_embeds = cls._pad_batch_size(
                    negative_pooled_prompt_embeds, shared_batch
                )

        # Keep embeddings compatible with the pipeline's UNet/text dtype.
        target_dtype = getattr(getattr(pipeline, "unet", None), "dtype", None)
        if target_dtype is not None and getattr(prompt_embeds, "is_floating_point", lambda: False)():
            prompt_embeds = prompt_embeds.to(dtype=target_dtype)
            if negative_prompt_embeds is not None:
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
        }
        if negative_prompt_embeds is not None:
            result["negative_prompt_embeds"] = negative_prompt_embeds
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

        if cls._is_turbo_model():
            steps = max(1, min(4, int(steps)))
            guidance = 0.0
            width, height = cls._parse_size(f"{width}x{height}")

        kwargs: dict[str, Any] = {
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }

        # A one-window prompt should use the pipeline's native text path.
        # Longer prompts are encoded with every native CLIP window, without an
        # April/OpenAI token cap. For Turbo guidance_scale=0, negative guidance
        # is disabled by the model and therefore no negative embedding is built.
        tokenizer = getattr(pipeline, "tokenizer", None)
        prompt_token_count = len(cls._token_ids_for_long_prompt(tokenizer, prompt)) if tokenizer is not None else 0
        negative_token_count = len(cls._token_ids_for_long_prompt(tokenizer, negative_prompt or "")) if tokenizer is not None else 0
        native_limit = int(getattr(tokenizer, "model_max_length", 77) or 77) if tokenizer is not None else 77

        if (
            tokenizer is not None
            and prompt_token_count <= native_limit
            and negative_token_count <= native_limit
            and not cls._is_turbo_model()
        ):
            kwargs["prompt"] = prompt
            kwargs["negative_prompt"] = negative_prompt or ""
            print(
                "🧠 IMAGE PROMPT ENCODING:",
                {
                    "prompt_raw_tokens": prompt_token_count,
                    "negative_raw_tokens": negative_token_count,
                    "prompt_native_windows": 1,
                    "negative_native_windows": 1,
                    "strategy": "pipeline_native_single_window",
                    "april_openai_prompt_cap": None,
                },
            )
        else:
            prompt_kwargs = cls._long_prompt_kwargs(
                pipeline,
                prompt,
                negative_prompt,
                include_negative=guidance != 0.0,
            )
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
        print(
            "🧠 IMAGE PROMPT NORMALIZED:",
            {
                "semantic_chars": len(prompt),
                "contains_markup": bool(re.search(r"<(?:svg|path|rect|circle)\b|data:image/", prompt, flags=re.IGNORECASE)),
                "native_clip_limit_is_window_only": True,
            },
        )
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

        # The raster is authoritative at this point: generation already
        # succeeded and the PNG has passed validation.  Reassert the canonical
        # Web display payload from those bytes instead of turning a transport
        # normalization mismatch into a failed generation.  This stays on the
        # existing C_APRIL -> C_ARTIFACT -> SceneContract route and does not
        # accept or forward a Provider-rendered image.
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
            "alt": payload.get("alt") or prompt,
            "caption": payload.get("caption") or prompt,
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
        })

        if not isinstance(artifact, dict):
            artifact = {}
        artifact["artifact_type"] = "image"
        artifact["mime_type"] = "image/png"
        artifact["width"] = int(width)
        artifact["height"] = int(height)
        artifact["image_base64"] = data_base64
        artifact["image_data_uri"] = data_uri
        artifact["payload"] = payload
        artifact["images"] = [image_item]
        artifact["render_spec"] = clean
        artifact["payload"]["render_spec"] = clean

        # Keep the BaseArtifact used by C_ARTIFACT_CONTRACT in sync with the
        # repaired display payload.  Rebuilding the universal contract here
        # guarantees that its render block carries the same PNG source.
        base_artifact = getattr(contract, "artifact", None) if contract is not None else None
        if base_artifact is not None:
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

        if not artifact["payload"].get("src") or not artifact["payload"].get("images"):
            raise RuntimeError("APRIL_IMAGES_ARTIFACT_DISPLAY_PAYLOAD_BUILD_FAILED")
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
        print(
            "🧠 IMAGE PROMPT NORMALIZED:",
            {
                "semantic_chars": len(prompt),
                "contains_markup": bool(re.search(r"<(?:svg|path|rect|circle)\b|data:image/", prompt, flags=re.IGNORECASE)),
                "native_clip_limit_is_window_only": True,
            },
        )
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
        source_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = source_image.size
        pipeline = self._load_edit_pipeline()
        steps, guidance = self._quality_settings(quality)
        strength_value = max(0.05, min(0.95, float(strength)))
        if self._is_turbo_model():
            import math
            steps = max(2, steps, int(math.ceil(1.0 / strength_value)))
            steps = min(4, steps)
            guidance = 0.0

        kwargs: dict[str, Any] = {
            "image": source_image,
            "strength": strength_value,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }

        tokenizer = getattr(pipeline, "tokenizer", None)
        if tokenizer is not None and not self._is_turbo_model():
            prompt_tokens = len(self._token_ids_for_long_prompt(tokenizer, prompt))
            negative = self._negative_prompt()
            negative_tokens = len(self._token_ids_for_long_prompt(tokenizer, negative))
            native_limit = int(getattr(tokenizer, "model_max_length", 77) or 77)
        else:
            prompt_tokens = negative_tokens = 0
            native_limit = 77
            negative = ""

        if (
            tokenizer is not None
            and not self._is_turbo_model()
            and prompt_tokens <= native_limit
            and negative_tokens <= native_limit
        ):
            kwargs["prompt"] = prompt
            kwargs["negative_prompt"] = negative
        else:
            kwargs.update(
                self._long_prompt_kwargs(
                    pipeline,
                    prompt,
                    "" if guidance == 0.0 else self._negative_prompt(),
                )
            )

        if torch is not None:
            with torch.inference_mode():
                result = pipeline(**kwargs)
        else:
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


async def generate_image(prompt: str, size: str = "512x512", quality: str = "standard") -> Optional[bytes]:
    result = await april_images_generator.generate(prompt, size=size, quality=quality)
    return result.get("image_bytes") if result.get("success") else None


async def generate_image_result(
    prompt: str,
    size: str = "512x512",
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
