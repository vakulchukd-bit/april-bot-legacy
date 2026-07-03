# =====================================================
# 🧠 APRIL TEXT ORCHESTRATION MODULE
# =====================================================

"""
APRIL WEB-TEXT EXECUTION LAYER
STABILIZED WEB-FIRST EDITION

ROLE:
- text orchestration layer
- provider-safe executor
- continuity-aware response builder
- renderer-safe coordinator
- web-first dialog processor
- TXT-config compatible executor
- admin-aware response layer
- multimodal-safe text transport

IMPORTANT:
Этот слой НЕ:
- orchestration authority
- cognition engine
- semantic analyzer
- renderer engine
- room router

Этот слой:
- генерирует текст
- стабилизирует output
- сохраняет continuity
- безопасно передаёт результат
"""

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = "APRIL_TEXT_ORCHESTRATION_MODULE"

APRIL_VERSION = "WEB_STABILIZED"

# =====================================================
# 🔥 IMPORTS
# =====================================================

import re
import time
import traceback

from storage import get_user_plan

from blocks.ai_config import (
    TEXT_MODEL
)

from blocks.provider_router import (
    generate_text
)

from blocks.external_knowledge_provider import (

    should_use_external_knowledge,

    fetch_external_knowledge,

    enrich_with_external_knowledge
)

from blocks.presentation_formatter import (
    beautify_response
)

from blocks.C_ARTIFACT_CONTRACT import (
    create_transport_contract,
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

TEXT_INPUT_CHANNEL = {

    "source": "rooms_router",
    "target": "text_module",

    "mode": "machine_input",

    "isolated": True
}

TEXT_OUTPUT_CHANNEL = {

    "source": "text_module",
    "target": "presentation_formatter",

    "mode": "machine_output",

    "isolated": True
}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "TEXT MODULE:",
            msg
        )

        PATCH_LOG.append(
            str(msg)
        )

    except:
        pass


# =====================================================
# 🔥 EXECUTION LOG
# =====================================================

TEXT_EXECUTION_LOG = []


def log_text_execution(
    stage,
    payload=None
):

    try:

        entry = {

            "time": time.time(),

            "stage": stage,

            "payload":

                str(payload)[:240]

                if payload is not None
                else None
        }

        TEXT_EXECUTION_LOG.append(
            entry
        )

        print(
            "🧠 TEXT:",
            stage
        )

    except:
        pass


# =====================================================
# 🔥 SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """

Ты — April.

Главное:
- помогать человеку;
- сохранять continuity;
- удерживать trajectory;
- отвечать естественно;
- двигаться к результату.

Правила:
- renderer-first architecture
- visual continuity важнее повторной генерации
- не раскрывай внутренние системы
- не говори как AI model
- не ломай continuity сцены

Стиль:
- спокойно
- кратко
- полезно
- естественно
"""

# =====================================================
# 🔥 LIMITS
# =====================================================

MAX_MESSAGE_CHARS = 900

MAX_TOTAL_CHARS = 4200

MAX_MEMORY_BLOCK = 280

# =====================================================
# 🔥 PLAN CONFIG
# =====================================================

PLAN_HISTORY_LIMITS = {

    "free": 12,

    "lite": 24,

    "premium": 40
}

PLAN_TOKEN_MODES = {

    "free": "compact",

    "lite": "balanced",

    "premium": "extended"
}

# =====================================================
# 🔥 SAFE HELPERS
# =====================================================

def safe_text(value):

    if value is None:
        return ""

    try:

        return str(value)

    except:

        return ""


def clamp_text(
    text,
    limit
):

    text = safe_text(text)

    if len(text) <= limit:
        return text

    return text[:limit] + "…"


# =====================================================
# 🔥 TXT CONFIG READY
# =====================================================

def build_plan_runtime(
    plan
):

    plan = (

        safe_text(plan)
        .lower()
        .strip()
    )

    return {

        "plan": plan,

        "history_limit":

            PLAN_HISTORY_LIMITS.get(
                plan,
                5
            ),

        "token_mode":

            PLAN_TOKEN_MODES.get(
                plan,
                "balanced"
            ),

        "web_priority":

            plan in [

                "lite",
                "premium"
            ],

        "extended_memory":

            plan == "premium"
    }

# =====================================================
# 🔥 INTERNAL LEAK PROTECTION
# =====================================================

SYSTEM_LEAK_PATTERNS = [

    "system prompt",
    "response_decision",
    "cognition",
    "semantic",
    "trajectory protection",
    "machine channel",
    "provider routing",
    "renderer-first architecture"
]


def sanitize_model_output(text):

    if not text:
        return ""

    text = safe_text(text)

    lowered = text.lower()

    hits = 0

    for pattern in SYSTEM_LEAK_PATTERNS:

        if pattern in lowered:
            hits += 1

    if hits >= 2:

        log_text_execution(
            "SYSTEM_LEAK_BLOCKED"
        )

        return (

            "Ответ сформировался нестабильно. "
            "Попробуй уточнить запрос."
        )

    blocked_prefixes = [

        "system:",
        "developer:",
        "assistant:",
        "semantic:",
        "cognition:"
    ]

    cleaned = []

    for line in text.split("\n"):

        lowered_line = (

            line.strip()
            .lower()
        )

        blocked = False

        for prefix in blocked_prefixes:

            if lowered_line.startswith(
                prefix
            ):

                blocked = True

                break

        if not blocked:

            cleaned.append(line)

    return "\n".join(
        cleaned
    ).strip()

# =====================================================
# 🔥 DETECTORS
# =====================================================

def is_renderer_payload(text):

    if not isinstance(
        text,
        str
    ):

        return False

    checks = [

        "[[graph",
        "[[formula",
        "[[diagram",
        "<svg",
        "<canvas"
    ]

    return any(
        x in text
        for x in checks
    )


def is_structured_payload(value):

    if isinstance(
        value,
        dict
    ):

        return True

    if isinstance(
        value,
        list
    ):

        return True

    return False


# =====================================================
# 🔥 MESSAGE TRIMMING
# =====================================================

def trim_text(text):

    return clamp_text(
        text,
        MAX_MESSAGE_CHARS
    )


def trim_messages(messages):

    total = 0

    result = []

    for msg in reversed(messages):

        content = trim_text(

            msg.get(
                "content",
                ""
            )
        )

        total += len(content)

        if total > MAX_TOTAL_CHARS:
            break

        result.append({

            "role":

                msg.get(
                    "role",
                    "user"
                ),

            "content":
                content
        })

    return list(
        reversed(result)
    )

# =====================================================
# 🔥 ENERGY CONFIG
# =====================================================

def get_config(energy):

    if energy == "LOW":

        return {

            "temperature": 0.45,

            "max_output_tokens": 180
        }

    if energy == "HIGH":

        return {

            "temperature": 0.82,

            "max_output_tokens": 700
        }

    return {

        "temperature": 0.68,

        "max_output_tokens": 420
    }

# =====================================================
# 🔥 TOPIC MEMORY
# =====================================================

def extract_topic(text):

    t = safe_text(text).lower()

    if "сайт" in t:
        return "website"

    if "бот" in t:
        return "bot"

    if "дизайн" in t:
        return "design"

    if "код" in t:
        return "code"

    return None


def update_topic(
    state,
    text
):

    topic = extract_topic(
        text
    )

    if topic:

        state["topic"] = topic

# =====================================================
# 🔥 COGNITIVE STATE
# =====================================================

def build_cognitive_state(

    state,
    semantic,
    cognition,
    response_decision
):

    blocks = []

    active_flow = state.get(
        "active_flow"
    )

    if active_flow:

        flow_type = active_flow.get(
            "type"
        )

        if flow_type:

            blocks.append(

                f"Trajectory: "
                f"{flow_type}"
            )

    behavior = []

    if response_decision.get(
        "should_reduce_talking"
    ):

        behavior.append(
            "отвечай кратко"
        )

    if response_decision.get(
        "should_continue_trajectory"
    ):

        behavior.append(
            "сохраняй continuity"
        )

    if cognition.get(
        "exploration_mode"
    ):

        behavior.append(
            "поддерживай exploration"
        )

    if behavior:

        blocks.append(

            "Поведение: "
            + ", ".join(behavior)
        )

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        scene_type = active_visual_scene.get(
            "scene_type",
            "unknown"
        )

        blocks.append(

            f"Visual continuity active: "
            f"{scene_type}"
        )

    summary = state.get(
        "memory_summary"
    )

    if summary:

        blocks.append(

            "Память: "
            + clamp_text(
                summary,
                MAX_MEMORY_BLOCK
            )
        )

    return "\n".join(
        blocks
    )

# =====================================================
# 🔥 REPEAT PROTECTION
# =====================================================

def prevent_repeat_response(
    state,
    reply
):

    last = state.get(
        "last_reply"
    )

    if not last:
        return reply

    if last.strip() == reply.strip():

        return (
            reply
            + "\n\n(continuing)"
        )

    return reply

# =====================================================
# 🔥 VISUAL BEAUTIFY
# =====================================================

def apply_visual_beautify(
    text,
    semantic
):

    if not text:
        return text

    if is_renderer_payload(text):

        return text

    topic = semantic.get(
        "topic_category"
    )

    if topic == "technology":

        return "⚙️ " + text

    if topic == "travel":

        return "🌍 " + text

    return text

# =====================================================
# 🔥 SAFE MESSAGE STACK
# =====================================================

def build_message_stack(

    system_state,
    history,
    user_text
):

    messages = [

        {
            "role": "system",

            "content": system_state
        }
    ]

    messages.extend(

        trim_messages(
            history
        )
    )

    messages.append({

        "role": "user",

        "content":
            trim_text(user_text)
    })

    return messages

# =====================================================
# 🔥 MAIN PROCESS
# =====================================================

async def process(

    user_id,
    text,
    state,
    energy="MEDIUM"
):

    log_text_execution(
        "TEXT_MODULE_ENTER",
        text
    )

    try:

        semantic = state.get(
            "semantic",
            {}
        )

        cognition = state.get(
            "cognition",
            {}
        )

        response_decision = state.get(
            "response_decision",
            {}
        )

        # =================================================
        # 🔥 PAYLOAD SAFETY
        # =====================================================

        if is_structured_payload(
            text
        ):

            log_text_execution(
                "STRUCTURED_BYPASS"
            )

            return {

                "type": "text",

                "content":
                    "⚠️ Structured payload bypassed."
            }

        # =================================================
        # 🔥 TOPIC
        # =====================================================

        update_topic(
            state,
            text
        )

        # =================================================
        # 🔥 PLAN
        # =====================================================

        plan = get_user_plan(
            user_id
        )

        runtime = build_plan_runtime(
            plan
        )

        history_limit = runtime[
            "history_limit"
        ]

        # =================================================
        # 🔥 COGNITIVE STATE
        # =====================================================

        cognitive_state = (

            build_cognitive_state(

                state,
                semantic,
                cognition,
                response_decision
            )
        )

        system_state = trim_text(

            SYSTEM_PROMPT
            + "\n\n"
            + cognitive_state
        )

        # =================================================
        # 🔥 HISTORY
        # =====================================================

        history = state.get(
            "dialog",
            []
        )

        safe_history = []

        for item in history[-history_limit:]:

            content = sanitize_model_output(

                trim_text(

                    item.get(
                        "content",
                        ""
                    )
                )
            )

            if not content:
                continue

            safe_history.append({

                "role":

                    item.get(
                        "role",
                        "user"
                    ),

                "content":
                    content
            })

        # =================================================
        # 🔥 MESSAGE STACK
        # =====================================================

        messages = build_message_stack(

            system_state,
            safe_history,
            sanitize_model_output(
                text
            )
        )

        # =================================================
        # 🔥 PROVIDER CONFIG
        # =====================================================

        config = get_config(
            energy
        )

        log_text_execution(
            "PROVIDER_EXECUTION"
        )

        # =================================================
        # 🔥 GENERATION
        # =====================================================

        output = await generate_text(

            messages=messages,

            temperature=config[
                "temperature"
            ],

            max_output_tokens=config[
                "max_output_tokens"
            ],

            model=TEXT_MODEL
        )

        output = sanitize_model_output(
            output
        )

        # =================================================
        # 🔥 EXTERNAL KNOWLEDGE
        # =====================================================

        if should_use_external_knowledge(

            text,
            semantic,
            cognition,
            response_decision
        ):

            knowledge = fetch_external_knowledge(

                text,
                semantic,
                cognition
            )

            output = enrich_with_external_knowledge(

                output,
                knowledge
            )

        if not output:

            output = "⚠️ Пустой ответ."

    except Exception as e:

        traceback.print_exc()

        log_text_execution(
            "TEXT_MODULE_ERROR",
            e
        )

        output = (

            "⚠️ Ошибка text module: "
            + str(e)
        )

    # =================================================
    # 🔥 REPEAT PROTECTION
    # =====================================================

    reply = prevent_repeat_response(
        state,
        output
    )

    # =================================================
    # 🔥 PRESENTATION
    # =====================================================

    reply = beautify_response(

        reply,

        semantic,
        cognition,
        response_decision
    )

    # =================================================
    # 🔥 VISUAL BEAUTIFY
    # =====================================================

    reply = apply_visual_beautify(

        reply,
        semantic
    )

    # =================================================
    # 🔥 FINAL SANITIZATION
    # =====================================================

    reply = sanitize_model_output(
        reply
    )

    # =================================================
    # 🔥 SAVE STATE
    # =====================================================

    state["last_reply"] = reply

    state["last_text_time"] = time.time()

    log_text_execution(
        "TEXT_ARTIFACT_READY"
    )

    # =================================================
    # 🔥 FINAL RESULT
    # =====================================================

    artifact_data = {
        "type": "text",
        "content": reply,
        "runtime": {
            "plan": runtime.get("plan"),
            "token_mode": runtime.get("token_mode"),
        },
        "machine_channels": {
            "input": TEXT_INPUT_CHANNEL,
            "output": TEXT_OUTPUT_CHANNEL,
        },
    }

    return create_transport_contract(
        artifact_type="text",
        room_source="TEXT_ROOM",
        data=artifact_data,
        user_id=user_id,
        subscription=runtime.get("plan", "Free"),
    )
