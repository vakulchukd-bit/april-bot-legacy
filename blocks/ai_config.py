# ===== CENTRAL AI CONFIG =====

# --- IMAGE ---
IMAGE_MODEL = "gpt-image-1"
IMAGE_SIZE = "512x512"
IMAGE_QUALITY = "low"

# --- TEXT ---
TEXT_MODEL = "gpt-4o-mini"

# --- SAFETY LIMITS ---
MAX_OUTPUT_TOKENS = {
    "LOW": 300,
    "MEDIUM": 700,
    "HIGH": 1500
}

TEMPERATURE = {
    "LOW": 0.5,
    "MEDIUM": 0.7,
    "HIGH": 0.9
}
