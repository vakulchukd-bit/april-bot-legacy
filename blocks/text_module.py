# =====================================================
# 🧠 APRIL TEXT MODULE
# =====================================================

"""
APRIL TEXT MODULE

ROLE:
- conversational continuity;
- calm dialogue support;
- lightweight explanation layer;
- human communication layer.

NOT ROLE:
- orchestration authority;
- renderer authority;
- execution authority;
- scene owner;
- fallback renderer;
- fake execution system.

APRIL PRINCIPLES:

1. continue trajectory
2. preserve scene
3. avoid narration overflow
4. avoid robotic behavior
5. avoid overexplaining
6. dialogue before monologue
7. renderer before text
8. machine-state before prose
"""

# =====================================================
# 🔥 PATCH LOG
# =====================================================

PATCH_LOG = []

def safe_patch_log(msg):

    try:

        print("TEXT PATCH:", msg)

        PATCH_LOG.append(msg)

    except:
        pass


# =====================================================
# 🔥 IMPORTS
# =====================================================

import re
import time
import traceback

from storage import get_user_plan

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


# =====================================================
# 🧠 MACHINE SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """

APRIL_STATE:

role=continuity_dialogue
mode=calm
style=natural
verbosity=adaptive

RULES:

- continue active trajectory
- preserve continuity
- avoid scene reset
- avoid narration overflow
- avoid robotic explanations
- avoid repeating previous description
- avoid fake execution
- avoid fake links
- avoid fake rendering
- renderer has priority over text
- do not explain internal systems
- do not expose machine language
- help naturally
- guide softly
- answer humanly
"""


# =====================================================
# 🔥 LIMITS
# =====================================================

MAX_MESSAGE_CHARS = 700
MAX_TOTAL_CHARS = 2600


# =====================================================
# 🔥 INTERNAL SAFETY
# =====================================================

SYSTEM_LEAK_PATTERNS = [

    "aprIL_state",
    "renderer has priority",
    "avoid fake execution",
    "continuity_dialogue",
    "verbosity=adaptive",
    "trajectory",
    "machine language",
    "internal systems"
]


def sanitize_model_output(text):

    if not text:
        return ""

    text = str(text)

    lower = text.lower()

    leak_hits = 0

    for pattern in SYSTEM_LEAK_PATTERNS:

        if pattern.lower() in lower:
            leak_hits += 1

    # =================================================
    # 🔥 HARD LEAK
    # =====================================================

    if leak_hits >= 2:

        safe_patch_log(
            "SYSTEM LEAK DETECTED"
        )

        return (
            "Ответ сформировался нестабильно. "
            "Попробуй уточнить запрос."
        )

    # =================================================
    # 🔥 REMOVE MACHINE LINES
    # =====================================================

    cleaned = []

    blocked_prefixes = [

        "aprIL_state",
        "rules:",
        "role=",
        "mode=",
        "style=",
        "verbosity="
    ]

    for line in text.split("\n"):

        stripped = line.strip().lower()

        blocked = False

        for prefix in blocked_prefixes:

            if stripped.startswith(
                prefix.lower()
            ):

                blocked = True

                break

        if not blocked:

            cleaned.append(line)

    return "\n".join(
        cleaned
    ).strip()


# =====================================================
# 🔥 HELPERS
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
            msg.get("content", "")
        )

        total += len(content)

        if total > MAX_TOTAL_CHARS:
            break

        result.append({

            "role":
                msg.get("role", "user"),

            "content":
                content
        })

    return list(
        reversed(result)
    )


def get_config(energy):

    if energy == "LOW":

        return {

            "temperature": 0.45,

            "max_output_tokens": 160
        }

    if energy == "HIGH":

        return {

            "temperature": 0.78,

            "max_output_tokens": 500
        }

    return {

        "temperature": 0.62,

        "max_output_tokens": 300
    }


def get_history_limit(plan):

    return {

        "free": 3,

        "lite": 5,

        "premium": 8

    }.get(plan, 5)


# =====================================================
# 🧠 MACHINE CONTEXT
# =====================================================

def build_machine_state(

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
                f"FLOW={flow_type}"
            )

    # =================================================
    # 🔥 CONTINUITY
    # =====================================================

    if semantic.get(
        "visual_continuity"
    ):

        blocks.append(
            "VISUAL_CONTINUITY=1"
        )

    if cognition.get(
        "needs_continuation"
    ):

        blocks.append(
            "CONTINUE_SCENE=1"
        )

    # =================================================
    # 🔥 USER STATE
    # =====================================================

    if cognition.get(
        "response_should_help_gently"
    ):

        blocks.append(
            "STYLE=CALM"
        )

    if cognition.get(
        "prefer_execution"
    ):

        blocks.append(
            "USER_EXPECTS_RESULT=1"
        )

    if cognition.get(
        "prefer_renderer"
    ):

        blocks.append(
            "RENDERER_PRIORITY=1"
        )

    # =================================================
    # 🔥 RESPONSE STYLE
    # =====================================================

    if response_decision.get(
        "should_reduce_talking"
    ):

        blocks.append(
            "SHORT_RESPONSE=1"
        )

    # =================================================
    # 🔥 VISUAL SCENE
    # =====================================================

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        scene_type = active_visual_scene.get(
            "scene_type"
        )

        if scene_type:

            blocks.append(
                f"SCENE={scene_type}"
            )

        objects = active_visual_scene.get(
            "objects",
            []
        )

        if objects:

            blocks.append(

                "OBJECTS="
                + ",".join(objects[:6])
            )

    # =================================================
    # 🔥 MEMORY
    # =====================================================

    memory_summary = state.get(
        "memory_summary"
    )

    if memory_summary:

        short_memory = trim_text(
            memory_summary[-140:]
        )

        blocks.append(
            "MEMORY="
            + short_memory
        )

    return "\n".join(blocks)


# =====================================================
# 🔥 LOOP PROTECTION
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
            + "\n\nПродолжаю."
        )

    return reply


# =====================================================
# 🔥 ROBOTIC CLEANER
# =====================================================

def reduce_robotic_behavior(
    text
):

    if not text:
        return text

    robotic_phrases = [

        "конечно",
        "давай разберём",
        "отличный вопрос",
        "я помогу",
        "сейчас объясню",
        "рассмотрим подробнее",
        "подробно объясню"
    ]

    cleaned = text

    for phrase in robotic_phrases:

        cleaned = re.sub(

            phrase,

            "",

            cleaned,

            flags=re.IGNORECASE
        )

    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned
    )

    return cleaned.strip()


# =====================================================
# 🔥 DIALOG STABILIZER
# =====================================================

def stabilize_dialogue(

    text,
    cognition,
    semantic
):

    if not text:
        return text

    # =================================================
    # 🔥 EXPLORATION MODE
    # =====================================================

    if cognition.get(
        "exploration_mode"
    ):

        text = reduce_robotic_behavior(
            text
        )

    # =================================================
    # 🔥 VISUAL CONTINUITY
    # =====================================================

    if semantic.get(
        "visual_continuity"
    ):

        repetitive = [

            "на изображении",
            "на этой картинке",
            "я вижу",
            "это изображение показывает"
        ]

        for r in repetitive:

            text = re.sub(

                r,

                "",

                text,

                flags=re.IGNORECASE
            )

    return text.strip()


# =====================================================
# 🔥 CODE ENHANCE
# =====================================================

def enhance_code_block(text):

    if not text:
        return text

    t = text.strip()

    if (
        "<html" in t
        or "<!DOCTYPE html>" in t
    ):

        return (
            "```html\n"
            + t
            + "\n```"
        )

    if (
        "def " in t
        or "import " in t
    ):

        return (
            "```python\n"
            + t
            + "\n```"
        )

    return t


# =====================================================
# 🔥 MAIN PROCESS
# =====================================================

async def process(

    user_id,
    text,
    state,
    energy="MEDIUM"
):

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

        history = state.get(
            "dialog",
            []
        )

        plan = get_user_plan(
            user_id
        )

        limit = get_history_limit(
            plan
        )

        machine_state = build_machine_state(

            state,
            semantic,
            cognition,
            response_decision
        )

        system_prompt = (

            SYSTEM_PROMPT
            + "\n\n"
            + machine_state
        )

        messages = [

            {
                "role": "system",

                "content": trim_text(
                    system_prompt
                )
            }
        ]

        # =================================================
        # 🔥 HISTORY
        # =====================================================

        safe_history = []

        for m in history[-limit:]:

            content = sanitize_model_output(

                trim_text(
                    m.get(
                        "content",
                        ""
                    )
                )
            )

            if not content:
                continue

            safe_history.append({

                "role":
                    m.get("role"),

                "content":
                    content
            })

        messages.extend(

            trim_messages(
                safe_history
            )
        )

        messages.append({

            "role": "user",

            "content":
                trim_text(text)
        })

        config = get_config(
            energy
        )

        # =================================================
        # 🔥 PROVIDER CALL
        # =====================================================

        output = await generate_text(

            messages=messages,

            temperature=config[
                "temperature"
            ],

            max_output_tokens=config[
                "max_output_tokens"
            ],

            model="gpt-4o-mini"
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

        # =================================================
        # 🔥 DIALOG STABILIZATION
        # =====================================================

        output = stabilize_dialogue(

            output,
            cognition,
            semantic
        )

        if not output:

            output = "⚠️ Пустой ответ."

    except Exception as e:

        traceback.print_exc()

        output = (
            "⚠️ Ошибка текстового модуля: "
            + str(e)
        )

    # =====================================================
    # 🔥 FINALIZE
    # =====================================================

    if "```" in output:

        state["last_code"] = output

    reply = enhance_code_block(
        output
    )

    reply = prevent_repeat_response(
        state,
        reply
    )

    reply = beautify_response(

        reply,
        semantic,
        cognition,
        response_decision
    )

    reply = sanitize_model_output(
        reply
    )

    state["last_reply"] = reply

    state["last_text_time"] = time.time()

    return {

        "type": "text",

        "content": reply
    }
