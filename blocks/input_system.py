# ==================== 🔵 BLOCK: INPUT SYSTEM ====================

# =====================================================
# 🧠 APRIL INPUT COORDINATION SYSTEM
# =====================================================

"""
APRIL INPUT SYSTEM

APRIL_FILE_ID:
APRIL_INPUT_COORDINATION_SYSTEM

ROLE:
MULTIMODAL_INPUT_COORDINATOR

INPUT:
TEXT_MESSAGE
VOICE_MESSAGE
IMAGE_MESSAGE
RAW_USER_INPUT

OUTPUT:
STRUCTURED_INPUT_PAYLOAD
SEMANTIC_INPUT_STATE
EXECUTOR_READY_INPUT

=====================================================

Этот слой отвечает за:

- multimodal input normalization;
- lightweight semantic entry detection;
- source coordination;
- executor-ready payload assembly;
- safe input preprocessing.

=====================================================

Этот слой НЕ:

- cognition authority;
- orchestration engine;
- reasoning layer;
- renderer authority;
- trajectory manager;
- memory system.

=====================================================

Главная задача:
безопасно подготовить
structured input payload
для April Executor.
"""

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_INPUT_COORDINATION_SYSTEM"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source":
        "user_multimodal_input",

    "type":
        "raw_input_stream",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "executor_input_pipeline",

    "type":
        "structured_input_payload",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

INPUT_SYSTEM_LOGS = []

MAX_INPUT_SYSTEM_LOGS = 60


def log_input_event(
    event,
    payload=None
):

    try:

        INPUT_SYSTEM_LOGS.append({

            "file_id":
                APRIL_FILE_ID,

            "event":
                event,

            "payload":
                payload or {},

            "machine_only":
                True
        })

        if len(INPUT_SYSTEM_LOGS) > MAX_INPUT_SYSTEM_LOGS:

            INPUT_SYSTEM_LOGS.pop(0)

    except:
        pass

# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(
    text
):

    return str(
        text or ""
    ).strip()


def normalize_lower(
    text
):

    return normalize_text(
        text
    ).lower()

# =====================================================
# 🔥 INPUT PROCESSING
# =====================================================

async def process_input(
    message
):

    log_input_event(
        "input_processing_started"
    )

    user_id = message.from_user.id

    # =================================================
    # 🔥 TEXT
    # =====================================================

    if message.text:

        text = message.text

        source = "text"

    # =================================================
    # 🔥 VOICE
    # =====================================================

    elif message.voice:

        text = "[voice message]"

        source = "voice"

    # =================================================
    # 🔥 IMAGE
    # =====================================================

    elif message.photo:

        text = "[image message]"

        source = "image"

    # =================================================
    # 🔥 UNKNOWN
    # =====================================================

    else:

        text = "[unsupported]"

        source = "unknown"

    # =================================================
    # 🔥 INTENT
    # =====================================================

    intent = detect_intent(
        text
    )

    payload = {

        "user_id":
            user_id,

        "text":
            text,

        "source":
            source,

        "intent":
            intent,

        # =============================================
        # 🔥 MACHINE FLAGS
        # =============================================

        "machine_ready":
            True,

        "executor_ready":
            True,

        "multimodal":
            source != "text",

        "machine_only":
            True
    }

    log_input_event(

        "input_payload_created",

        {

            "source":
                source,

            "intent":
                intent
        }
    )

    return payload

# =====================================================
# 🔥 SEMANTIC INTENT DETECTION
# =====================================================

def detect_intent(
    text: str
) -> str:

    """
    Lightweight semantic detection.

    IMPORTANT:
    Это НЕ orchestration authority.
    Это только safe input hint layer.
    """

    t = normalize_lower(
        text
    )

    log_input_event(

        "intent_detection_started",

        {
            "text":
                t[:80]
        }
    )

    # =================================================
    # 🔥 MATH
    # =====================================================

    if any(

        x in t

        for x in [

            "=",
            "x",
            "+",
            "-",
            "*",
            "/"
        ]
    ):

        intent = "math"

        log_input_event(

            "intent_detected",

            {
                "intent":
                    intent
            }
        )

        return intent

    # =================================================
    # 🔥 IMAGE
    # =====================================================

    if any(

        w in t

        for w in [

            "картин",
            "фото",
            "сгенерируй"
        ]
    ):

        intent = "generate_image"

        log_input_event(

            "intent_detected",

            {
                "intent":
                    intent
            }
        )

        return intent

    # =================================================
    # 🔥 DIAGRAM
    # =====================================================

    if any(

        w in t

        for w in [

            "чертеж",
            "схема",
            "диаграмма"
        ]
    ):

        intent = "diagram"

        log_input_event(

            "intent_detected",

            {
                "intent":
                    intent
            }
        )

        return intent

    # =================================================
    # 🔥 DEFAULT CHAT
    # =====================================================

    intent = "chat"

    log_input_event(

        "intent_detected",

        {
            "intent":
                intent
        }
    )

    return intent
