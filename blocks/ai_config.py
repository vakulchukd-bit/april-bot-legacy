# =====================================================
# 🧠 APRIL CENTRAL AI CONFIG
# =====================================================

"""
APRIL AI CONFIG

Главная идея:

- text → OpenAI text-first
- vision/OCR → Gemini-first helper
- renderer → local/frontend-first
- image generation → explicit only
- no hidden escalation
- no heavy fallback chaos
"""

# =====================================================
# 🔥 IMAGE GENERATION
# =====================================================

# HEAVY GENERATION
# Используется ТОЛЬКО
# при explicit image intent

IMAGE_MODEL = "gpt-image-1"

# =====================================================
# 🔥 IMAGE QUALITY
# =====================================================

# renderer-first architecture:
# не раздуваем изображения

IMAGE_SIZE = "512x512"

IMAGE_QUALITY = "low"

# =====================================================
# 🔥 TEXT MODELS
# =====================================================

# ОСНОВНОЙ TEXT MODEL
# calm + cheap + stable

TEXT_MODEL = "gpt-4o-mini"

# VISUAL FALLBACK
# только для OCR/vision fallback

VISION_FALLBACK_MODEL = "gpt-4.1-mini"

# VOICE TRANSCRIBE

VOICE_MODEL = "gpt-4o-mini-transcribe"

# =====================================================
# 🔥 PROVIDER PRIORITIES
# =====================================================

TEXT_PROVIDER = "openai"

VISION_PROVIDER = "gemini"

VOICE_PROVIDER = "openai"

# =====================================================
# 🔥 TOKEN LIMITS
# =====================================================

# text stabilization:
# уменьшаем перегруз

MAX_OUTPUT_TOKENS = {

    "LOW": 180,

    "MEDIUM": 350,

    "HIGH": 650
}

# =====================================================
# 🔥 TEMPERATURE
# =====================================================

TEMPERATURE = {

    "LOW": 0.5,

    "MEDIUM": 0.7,

    "HIGH": 0.85
}

# =====================================================
# 🔥 RENDERER-FIRST SAFETY
# =====================================================

# graph/formula/table/diagram
# НЕ должны эскалироваться
# в image generation

RENDERER_FIRST = True

BLOCK_HIDDEN_IMAGE_ESCALATION = True

BLOCK_AUTO_IMAGE_FALLBACKS = True

# =====================================================
# 🔥 VISUAL SAFETY
# =====================================================

# НЕ генерировать изображения
# без прямого explicit intent

EXPLICIT_IMAGE_GENERATION_ONLY = True

# =====================================================
# 🔥 CONTINUITY
# =====================================================

VISUAL_CONTINUITY_ENABLED = True

TEXT_CONTINUITY_ENABLED = True

SCENE_MEMORY_ENABLED = True
