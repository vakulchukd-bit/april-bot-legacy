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

# Canonical provider model comes from ai_config.
# Keep text_module and provider_router synchronized.
OPENAI_PROVIDER_MODEL = TEXT_MODEL

from blocks.provider_router import (
    generate_text
)

from blocks.external_knowledge_provider import (

    should_use_external_knowledge,

    fetch_external_knowledge,

    enrich_with_external_knowledge
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

MAX_MESSAGE_CHARS = 1000

MAX_TOTAL_CHARS = 5000

MAX_MEMORY_BLOCK = 3000

# =====================================================
# 🔥 PLAN CONFIG
# =====================================================

PLAN_HISTORY_LIMITS = {

    "free": 15,

    "lite": 30,

    "premium": 999999
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
# 🔥 PROVIDER OUTPUT NORMALIZATION
# =====================================================

def normalize_provider_output(output):
    """Normalize provider dict output into a single text reply and keep packet."""
    provider_packet = None
    reply = ""

    if isinstance(output, dict):
        provider_packet = dict(output)
        mr = provider_packet.get("machine_response") or {}
        if not isinstance(mr, dict):
            mr = {}

        candidate = (
            mr.get("answer")
            or mr.get("content")
            or mr.get("response")
            or mr.get("summary")
            or provider_packet.get("answer")
            or provider_packet.get("content")
            or provider_packet.get("response")
            or provider_packet.get("summary")
            or ""
        )

        if candidate:
            for field in ("answer", "content", "response", "summary"):
                if not mr.get(field):
                    mr[field] = candidate
            provider_packet["machine_response"] = mr
            reply = candidate
        else:
            reply = safe_text(
                provider_packet.get("content")
                or provider_packet.get("answer")
                or provider_packet.get("summary")
                or provider_packet.get("response")
                or ""
            )
    else:
        reply = safe_text(output)

    return reply, provider_packet


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
# 🔥 RICH TEXT PRESENTATION
# =====================================================

def _normalize_word_line(line):
    line = safe_text(line).rstrip()
    if not line:
        return ""
    line = re.sub(r"[ \t]+([,.;:!?%])", r"\1", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip()

def format_rich_text_for_word(text):
    """Preserve Markdown-like structure for Word-style rendering."""
    text = safe_text(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    lines = text.split("\n")
    out = []
    paragraph = []
    in_code_block = False

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            combined = " ".join(paragraph)
            combined = _normalize_word_line(combined)
            if combined:
                out.append(combined)
            paragraph = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            out.append(stripped)
            in_code_block = not in_code_block
            continue

        if in_code_block:
            out.append(line)
            continue

        if not stripped:
            flush_paragraph()
            if not out or out[-1] != "":
                out.append("")
            continue

        markdown_marker = re.match(r"^(#{1,6}\s+|>\s+|[-*•]\s+|\d+[.)]\s+)", stripped)
        if markdown_marker:
            flush_paragraph()
            out.append(_normalize_word_line(stripped))
            continue

        paragraph.append(stripped)

    flush_paragraph()

    compacted = []
    blank_streak = 0
    for item in out:
        if item == "":
            blank_streak += 1
            if blank_streak <= 1:
                compacted.append(item)
        else:
            blank_streak = 0
            compacted.append(item)

    return "\n".join(compacted).strip()

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

            "max_output_tokens": 3000
        }

    if energy == "HIGH":

        return {

            "temperature": 0.82,

            "max_output_tokens": 8000
        }

    return {

        "temperature": 0.68,

        "max_output_tokens": 5000
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

    return format_rich_text_for_word(text)

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

    provider_packet = None

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

        # LEGACY REMOVED
        # STAGE 26 - Executor synchronization
        machine_request = (
            state.get("machine_request")
            or state.get("context", {}).get("machine_request")
            or state.get("executor_context", {}).get("machine_request")
            or state.get("transport", {}).get("machine_request")
        )

        # execution_phase is now set by Executor AFTER the first provider pass.

        if machine_request is None:
            raise RuntimeError("Canonical MachineRequest required before text generation.")

        # Legacy messages stack removed
        messages = machine_request


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

            messages=machine_request,

            temperature=config[
                "temperature"
            ],

            max_output_tokens=config[
                "max_output_tokens"
            ],

            model=OPENAI_PROVIDER_MODEL
        )

        # Provider canonical contract validation.
        if isinstance(output, dict):
            output, provider_packet = normalize_provider_output(output)
            state["provider_response"] = provider_packet
            if isinstance(provider_packet, dict):
                state["provider_machine_response"] = provider_packet.get("machine_response", {})
            else:
                state["provider_machine_response"] = {}
            # Keep the canonical answer available even when the provider packet is partial.
            if not output:
                mr = state.get("provider_machine_response", {}) or {}
                output = (
                    mr.get("answer")
                    or mr.get("content")
                    or mr.get("response")
                    or mr.get("summary")
                    or ""
                )
        else:
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

    reply = sanitize_model_output(
        reply
    )

    reply = format_rich_text_for_word(reply)

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
        "presentation_mode": "word_markdown",
        "runtime": {
            "plan": runtime.get("plan"),
            "token_mode": runtime.get("token_mode"),
        },
        "machine_channels": {
            "input": TEXT_INPUT_CHANNEL,
            "output": TEXT_OUTPUT_CHANNEL,
        },
        "provider_response": provider_packet,
    }

    transport_contract = create_transport_contract(
        artifact_type="text",
        room_source="TEXT_ROOM",
        data=artifact_data,
        user_id=user_id,
        subscription=runtime.get("plan", "Free"),
    )

    # Return a transport wrapper that Executor can read directly.
    # Keep the canonical transport object available for downstream systems.
    return {
        "type": "text",
        "content": reply,
        "answer": reply,
        "summary": reply,
        "machine_response": getattr(transport_contract, "machine_response", None),
        "scene_contract": getattr(getattr(transport_contract, "payload", None), "scene", None)
            if hasattr(transport_contract, "payload") else None,
        "artifact_contract": transport_contract,
        "transport_contract": transport_contract,
        "runtime": artifact_data["runtime"],
        "machine_channels": artifact_data["machine_channels"],
        "provider_response": provider_packet,
        "provider_machine_response": state.get("provider_machine_response", {}),
    }
