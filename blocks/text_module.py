# =====================================================
# 🧠 APRIL TEXT ORCHESTRATION MODULE
# =====================================================

"""
APRIL WEB-TEXT EXECUTION LAYER

=====================================================
🔥 ROLE
=====================================================

Этот файл теперь:

- text orchestration layer;
- provider-safe text executor;
- continuity-aware response builder;
- renderer-safe text coordinator;
- web-first dialog processor;
- response stabilization layer.

=====================================================
🔥 WHAT THIS MODULE DOES
=====================================================

Модуль отвечает за:

- text generation;
- provider execution;
- dialog continuity;
- safe response assembly;
- anti-system leakage;
- response stabilization;
- web-space compatible formatting;
- renderer-safe output.

=====================================================
🔥 WHAT THIS MODULE DOES NOT DO
=====================================================

Этот слой НЕ:

- authority system;
- cognition engine;
- semantic analyzer;
- presentation engine;
- renderer engine;
- room router;
- visual executor.

=====================================================
🔥 GOLDEN APRIL ARCHITECTURE
=====================================================

Теперь логика разделена:

Semantic →
Cognition →
Decision →
Rooms →
Text Module →
Presentation Layer →
BotRU UI

=====================================================
🔥 MACHINE CHANNELS
=====================================================

INPUT:
rooms_router → text_module

OUTPUT:
text_module → presentation_formatter

=====================================================
🔥 IMPORTANT
=====================================================

Text module НЕ:

- форматирует renderer payload;
- мутирует scene objects;
- вмешивается в visual routing;
- принимает orchestration decisions.

Он только:
- генерирует;
- стабилизирует;
- безопасно передаёт текст дальше.

=====================================================
🔥 WEB-FIRST READY
=====================================================

Подготовлено под:

- BotRU web architecture;
- multimodal web UI;
- renderer-space;
- future rooms;
- provider scaling;
- cognitive routing.

=====================================================
"""

# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "TEXT MODULE:",
            msg
        )

        PATCH_LOG.append(msg)

    except:
        pass


def patch_text_input(text):

    safe_patch_log(
        f"TEXT INPUT: {str(text)[:80]}"
    )

    return text


def patch_text_future(*args, **kwargs):

    return None


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

# =====================================================
# 🔥 EXTERNAL KNOWLEDGE
# =====================================================

from blocks.external_knowledge_provider import (

    should_use_external_knowledge,

    fetch_external_knowledge,

    enrich_with_external_knowledge
)

# =====================================================
# 🔥 PRESENTATION
# =====================================================

from blocks.presentation_formatter import (
    beautify_response
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
# 🔥 SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """

Ты — April.

Главное:
- помогать человеку;
- сохранять continuity;
- удерживать trajectory;
- отвечать естественно;
- не перегружать;
- двигаться к результату.

Важные правила:

- renderer-first architecture;
- visual continuity важнее повторной генерации;
- не объясняй внутренние системы;
- не используй system language;
- не раскрывай orchestration;
- не говори как AI model;
- не ломай continuity сцены.

Говори:
- спокойно;
- кратко;
- полезно;
- естественно.

"""

# =====================================================
# 🔥 LIMITS
# =====================================================

MAX_MESSAGE_CHARS = 900
MAX_TOTAL_CHARS = 4200

# =====================================================
# 🔥 INTERNAL LEAK PROTECTION
# =====================================================

SYSTEM_LEAK_PATTERNS = [

    "system prompt",
    "response_decision",
    "cognition",
    "semantic",
    "assistant_restraint",
    "trajectory protection",
    "signal_overload",
    "internal_noise",
    "renderer-first architecture",
    "continuity диалога",
    "calm mobile-first ai assistant",
    "provider routing",
    "machine channel",
    "response_mode",
    "active_flow_strength"
]


def sanitize_model_output(text):

    if not text:
        return ""

    text = str(text)

    lowered = text.lower()

    hits = 0

    for pattern in SYSTEM_LEAK_PATTERNS:

        if pattern in lowered:

            hits += 1

    # =================================================
    # 🔥 HARD LEAK BLOCK
    # =====================================================

    if hits >= 2:

        safe_patch_log(
            "SYSTEM LEAK DETECTED"
        )

        return (

            "Ответ сформировался нестабильно. "
            "Попробуй уточнить запрос."
        )

    # =================================================
    # 🔥 RAW SYSTEM CLEANUP
    # =====================================================

    blocked_prefixes = [

        "system:",
        "developer:",
        "assistant:",
        "semantic:",
        "cognition:",
        "response_decision:"
    ]

    cleaned = []

    for line in text.split("\n"):

        lowered_line = (
            line.strip().lower()
        )

        blocked = False

        for prefix in blocked_prefixes:

            if lowered_line.startswith(
                prefix
            ):

                blocked = True

                safe_patch_log(
                    f"REMOVED: {line[:50]}"
                )

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

    if not isinstance(text, str):
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


def is_code_payload(text):

    if not isinstance(text, str):
        return False

    checks = [

        "```",
        "def ",
        "import ",
        "const ",
        "function ",
        "<!DOCTYPE html>",
        "<html"
    ]

    return any(
        x in text
        for x in checks
    )

# =====================================================
# 🔥 TEXT LIMITERS
# =====================================================

def trim_text(text):

    if not text:
        return ""

    text = str(text)

    if len(text) > MAX_MESSAGE_CHARS:

        return (
            text[:MAX_MESSAGE_CHARS]
            + "…"
        )

    return text


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
# 🔥 HISTORY LIMIT
# =====================================================

def get_history_limit(plan):

    return {

        "free": 3,
        "lite": 5,
        "premium": 8

    }.get(plan, 5)

# =====================================================
# 🔥 TOPIC MEMORY
# =====================================================

def extract_topic(text):

    t = (
        text or ""
    ).lower()

    if "сайт" in t:
        return "website"

    if "бот" in t:
        return "bot"

    if "дизайн" in t:
        return "design"

    if "новост" in t:
        return "news"

    if "код" in t:
        return "code"

    return None


def update_topic(state, text):

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

    # =================================================
    # 🔥 FLOW
    # =====================================================

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

    # =================================================
    # 🔥 RESPONSE STYLE
    # =====================================================

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

    # =================================================
    # 🔥 VISUAL CONTINUITY
    # =====================================================

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

    # =================================================
    # 🔥 MEMORY
    # =====================================================

    summary = state.get(
        "memory_summary"
    )

    if summary:

        blocks.append(

            "Память: "
            + summary[-180:]
        )

    return "\n".join(blocks)

# =====================================================
# 🔥 CODE ENHANCE
# =====================================================

def enhance_code_block(text):

    if not text:
        return text

    stripped = text.strip()

    if is_renderer_payload(
        stripped
    ):

        return stripped

    if (
        "<!DOCTYPE html>" in stripped
        or "<html" in stripped
    ):

        return (

            "```html\n"
            + stripped
            + "\n```"
        )

    if (
        "def " in stripped
        or "import " in stripped
    ):

        return (

            "```python\n"
            + stripped
            + "\n```"
        )

    return stripped

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

    if topic == "history":

        return "🏛 " + text

    return text

# =====================================================
# 🔥 MAIN PROCESS
# =====================================================

async def process(

    user_id,
    text,
    state,
    energy="MEDIUM"

):

    text = patch_text_input(
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

        history_limit = get_history_limit(
            plan
        )

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
        # 🔥 FINAL MESSAGE STACK
        # =====================================================

        messages = [

            {
                "role": "system",
                "content": system_state
            }
        ]

        messages.extend(

            trim_messages(
                safe_history
            )
        )

        messages.append({

            "role": "user",

            "content":

                trim_text(
                    sanitize_model_output(
                        text
                    )
                )
        })

        # =================================================
        # 🔥 PROVIDER CONFIG
        # =====================================================

        config = get_config(
            energy
        )

        # =================================================
        # 🔥 PROVIDER EXECUTION
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

        # =================================================
        # 🔥 SANITIZATION
        # =====================================================

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

        # =================================================
        # 🔥 EMPTY OUTPUT
        # =====================================================

        if not output:

            output = (
                "⚠️ Пустой ответ."
            )

    except Exception as e:

        traceback.print_exc()

        output = (

            "⚠️ Ошибка text module: "
            + str(e)
        )

    # =================================================
    # 🔥 CODE
    # =====================================================

    if "```" in output:

        state["last_code"] = output

    # =================================================
    # 🔥 CODE ENHANCE
    # =====================================================

    reply = enhance_code_block(
        output
    )

    # =================================================
    # 🔥 REPEAT PROTECTION
    # =====================================================

    reply = prevent_repeat_response(
        state,
        reply
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

    # =================================================
    # 🔥 MACHINE OUTPUT
    # =====================================================

    return {

        "type": "text",

        "content": reply,

        "machine_channels": {

            "input":
                TEXT_INPUT_CHANNEL,

            "output":
                TEXT_OUTPUT_CHANNEL
        },

        "renderer_safe": True,

        "presentation_safe": True,

        "web_ready": True,

        "botru_compatible": True
    }
