# blocks/image_utils.py

# =====================================================
# 🧠 APRIL IMAGE PREPROCESSOR
# =====================================================

"""
APRIL IMAGE PREPROCESSOR

APRIL_FILE_ID:
APRIL_IMAGE_PREPROCESSOR

ROLE:
VISUAL_PREPROCESSING_LAYER

INPUT:
RAW_IMAGE_BYTES

OUTPUT:
OPTIMIZED_IMAGE_BYTES

=====================================================

Этот слой отвечает только за:

- image resizing;
- upload stabilization;
- provider-safe compression;
- visual payload optimization;
- lightweight preprocessing.

=====================================================

Этот слой НЕ:

- image analysis system;
- visual cognition;
- OCR layer;
- renderer authority;
- semantic detector;
- orchestration system.

=====================================================

Главная задача:
безопасная visual preprocessing
для April Web Space pipeline.
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from PIL import Image

import io

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_IMAGE_PREPROCESSOR"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "executor_visual_input",

    "type":
        "raw_image_payload",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "visual_provider_pipeline",

    "type":
        "optimized_image_payload",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

PREPROCESSOR_LOGS = []

MAX_PREPROCESSOR_LOGS = 40


def log_preprocessor_event(
    event,
    payload=None
):

    try:

        PREPROCESSOR_LOGS.append({

            "file_id":
                APRIL_FILE_ID,

            "event":
                event,

            "payload":
                payload or {},

            "machine_only":
                True
        })

        if len(PREPROCESSOR_LOGS) > MAX_PREPROCESSOR_LOGS:

            PREPROCESSOR_LOGS.pop(0)

    except:
        pass

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_bytes(
    image_bytes
):

    return image_bytes or b""


# =====================================================
# 🔥 IMAGE COMPRESSION
# =====================================================

def compress_image(

    image_bytes,

    max_size=1024,

    quality=80
):

    """
    Уменьшает размер изображения:

    - resize по максимальной стороне
    - JPEG conversion
    - quality compression

    IMPORTANT:

    Это preprocessing layer,
    а НЕ semantic visual system.
    """

    image_bytes = normalize_bytes(
        image_bytes
    )

    log_preprocessor_event(

        "compression_started",

        {
            "max_size":
                max_size,

            "quality":
                quality
        }
    )

    # =================================================
    # 🔥 LOAD IMAGE
    # =====================================================

    img = Image.open(

        io.BytesIO(
            image_bytes
        )

    ).convert("RGB")

    original_width, original_height = (
        img.size
    )

    # =================================================
    # 🔥 RESIZE
    # =====================================================

    width, height = img.size

    max_dim = max(
        width,
        height
    )

    resized = False

    if max_dim > max_size:

        ratio = (
            max_size / max_dim
        )

        new_size = (

            int(width * ratio),

            int(height * ratio)
        )

        img = img.resize(

            new_size,

            Image.LANCZOS
        )

        resized = True

    # =================================================
    # 🔥 COMPRESS
    # =====================================================

    buffer = io.BytesIO()

    img.save(

        buffer,

        format="JPEG",

        quality=quality,

        optimize=True
    )

    compressed_bytes = (
        buffer.getvalue()
    )

    # =================================================
    # 🔥 LOGS
    # =====================================================

    log_preprocessor_event(

        "compression_completed",

        {

            "original_size":

                {
                    "width":
                        original_width,

                    "height":
                        original_height
                },

            "final_size":

                {
                    "width":
                        img.size[0],

                    "height":
                        img.size[1]
                },

            "resized":
                resized,

            "output_bytes":
                len(
                    compressed_bytes
                )
        }
    )

    # =================================================
    # 🔥 RESULT
    # =====================================================

    return compressed_bytes
