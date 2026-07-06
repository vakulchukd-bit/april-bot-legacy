# =====================================================
# 🧠 APRIL WEB PRESENTATION ORCHESTRATOR
# =====================================================

"""
APRIL_FILE_ID: APRIL_WEB_PRESENTATION_ORCHESTRATOR

ROLE:
final_presentation_coordinator

PURPOSE:
- calm response formatting
- semantic pacing
- renderer-safe presentation
- behavioral stabilization
- dialogue density control
- anti-robotic cleanup
- continuity-safe output
- web-space presentation adaptation

INPUT:
- executor_response
- semantic
- cognition
- response_decision
- renderer_payloads
- machine_payloads

OUTPUT:
- machine_scene_passthrough
- human_visible_response
- renderer_safe_output
- web_ui_ready_payload

DEPENDENCIES:
- executor
- excrouter
- cognition
- semantic_core
- personality_core
- web_ui
- botru

GOLDEN RULE:
Presentation layer NEVER mutates:
- machine_scene
- renderer payloads
- machine payloads
- execution routing
- orchestration state
"""

print("🧠 APRIL PRESENTATION ORCHESTRATOR LOADED")

# =====================================================
# 🔥 IMPORTS
# =====================================================

import re
import json

# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

FORMAT_PATCH_LOG = []


def safe_format_log(msg):

    try:

        print(
            "APRIL PRESENTATION:",
            msg
        )

        FORMAT_PATCH_LOG.append(
            str(msg)
        )

    except Exception:
        pass


# =====================================================
# 🔥 ENTRY / EXIT LOGGING
# =====================================================

def presentation_enter(
    response,
    semantic=None
):

    semantic = semantic or {}

    safe_format_log(

        f"ENTER PRESENTATION: "
        f"{str(response)[:80]}"
    )

    return {

        "presentation_active": True,

        "renderer_safe":

            semantic.get(
                "prefer_renderer",
                False
            ),

        "machine_isolation": True
    }


def presentation_exit(
    final_response
):

    safe_format_log(

        f"EXIT PRESENTATION: "
        f"{str(final_response)[:80]}"
    )

    return {

        "presentation_complete": True,

        "human_output_ready": True,

        "continuity_preserved": True
    }


# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def presentation_future(
    *args,
    **kwargs
):

    return None


# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source": "executor",

    "type": "presentation_machine_input",

    "isolated": True
}

OUTPUT_HUMAN_CHANNEL = {

    "target": "botru_web_output",

    "type": "human_response_output",

    "isolated": True
}

# =====================================================
# 🔥 SAFE HELPERS
# =====================================================

def clamp(

    value,
    minimum=0.0,
    maximum=1.0

):

    if value < minimum:
        return minimum

    if value > maximum:
        return maximum

    return value


# =====================================================
# 🔥 RENDERER TYPES
# =====================================================

RENDERER_TYPES = [

    "graph",
    "formula",
    "code",
    "table",
    "diagram",
    "layout",
    "renderer",
    "scene",
    "visual",
    "artifact",
    "message_block",
    "canvas",
    "svg"
]

# =====================================================
# 🔥 PAYLOAD DETECTION
# =====================================================

def is_renderer_payload(value):

    if not isinstance(
        value,
        (dict, list)
    ):

        return False

    # =================================================
    # 🔥 DICT
    # =====================================================

    if isinstance(value, dict):

        payload_type = value.get(
            "type"
        )

        if payload_type in RENDERER_TYPES:

            return True

        if value.get(
            "machine_only"
        ):

            return True

    # =================================================
    # 🔥 LIST
    # =====================================================

    if isinstance(value, list):

        for item in value:

            if isinstance(item, dict):

                item_type = item.get(
                    "type"
                )

                if item_type in RENDERER_TYPES:

                    return True

    return False


# =====================================================
# 🔥 MACHINE PAYLOAD DETECTION
# =====================================================

def is_machine_payload(value):

    if not isinstance(
        value,
        dict
    ):

        return False

    return value.get(
        "machine_only",
        False
    )



# =====================================================
# 🔥 MACHINE RESPONSE DETECTION
# =====================================================

def is_machine_response(value):
    if not isinstance(value, dict):
        return False
    machine_keys = {
        "summary",
        "scene_plan",
        "artifacts",
        "render_priority",
        "confidence",
        "metadata",
    }
    return (value.get("transport_contract")=="scene_first") or (len(machine_keys.intersection(value.keys())) >= 2)



# =====================================================
# STAGE 1 - SCENE CONTRACT DETECTION
# =====================================================

def is_scene_contract(value):
    return (
        isinstance(value, dict)
        and value.get("type")=="scene_contract"
    )


# =====================================================
# 🔥 NORMALIZATION
# =====================================================

def normalize_text_payload(value):

    # =================================================
    # 🔥 RENDERER SAFE
    # =====================================================

    if is_renderer_payload(value):

        safe_format_log(
            "RENDERER PAYLOAD PRESERVED"
        )

        return value

    # =================================================
    # 🔥 MACHINE SAFE
    # =====================================================

    if is_machine_payload(value):

        safe_format_log(
            "MACHINE PAYLOAD PRESERVED"
        )

        return value

    # =================================================
    # 🔥 NONE
    # =====================================================

    if value is None:
        return ""

    # =================================================
    # 🔥 STRING
    # =====================================================

    if isinstance(value, str):
        return value

    # =================================================
    # 🔥 OBJECT SAFE
    # =====================================================

    if isinstance(
        value,
        (dict, list)
    ):

        if is_scene_contract(value):
            return value
        safe_format_log("OBJECT PAYLOAD PRESERVED")
        return value

    try:

        return str(value)

    except Exception:

        return ""


# =====================================================
# 🔥 JSON DETECTION
# =====================================================

def looks_like_json(text):

    if not isinstance(
        text,
        str
    ):

        return False

    text = text.strip()

    if not text:
        return False

    if not (

        text.startswith("{")
        or text.startswith("[")

    ):

        return False

    try:

        json.loads(text)

        return True

    except Exception:

        return False


# =====================================================
# 🔥 CODE DETECTION
# =====================================================

def is_code_payload(text):

    if not isinstance(
        text,
        str
    ):

        return False

    if not text:
        return False

    checks = [

        "```",

        "import ",
        "from ",

        "const ",
        "let ",
        "var ",

        "function ",
        "async function",

        "export default",

        "return (",

        "def ",
        "async def",

        "console.log(",

        "<div",
        "</div>"
    ]

    return any(
        x in text
        for x in checks
    )


# =====================================================
# 🔥 BEHAVIOR EXTRACTION
# =====================================================

def extract_behavior_field(
    cognition=None
):

    cognition = cognition or {}

    behavior = cognition.get(
        "behavior_state",
        {}
    )

    return {

        "response_density":

            behavior.get(
                "response_density",
                0.5
            ),

        "initiative_level":

            behavior.get(
                "initiative_level",
                0.35
            ),

        "latent_guidance":

            behavior.get(
                "latent_guidance",
                0.6
            ),

        "robotic_suppression":

            behavior.get(
                "robotic_suppression",
                0.9
            ),

        "humanization":

            behavior.get(
                "humanization",
                0.6
            )
    }


# =====================================================
# 🧠 ASSISTANT PRESENTATION FILTERS
# =====================================================

def suppress_internal_reasoning(text):

    if not isinstance(text, str):
        return text

    blocked = [
        "возможно",
        "предположительно",
        "скорее всего",
        "я думаю",
        "мне кажется",
        "вероятно"
    ]

    result = text

    for item in blocked:
        result = result.replace(item, "")

    return result.strip()


def inject_guidance_context(
    text,
    cognition=None,
    response_decision=None
):

    cognition = cognition or {}

    if not isinstance(text, str):
        return text

    next_step = cognition.get(
        "assistant_next_step",
        "ready_to_help"
    )

    if next_step == "request_image":
        return text

    if next_step == "request_formula":
        return text

    if next_step == "request_error_details":
        return text

    return text


# =====================================================
# 🔥 CLEANUP
# =====================================================

def cleanup_markdown(text):

    if not isinstance(
        text,
        str
    ):

        return text

    if not text:
        return ""

    text = text.replace(
        "**",
        ""
    )

    text = text.replace(
        "__",
        ""
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ ]{2,}",
        " ",
        text
    )

    return text.strip()


# =====================================================
# 🔥 SECTION SPLITTER
# =====================================================

def split_into_sections(text):

    if not isinstance(
        text,
        str
    ):

        return [text]

    if not text:
        return []

    blocks = re.split(
        r"\n{2,}",
        text
    )

    result = []

    for block in blocks:

        cleaned = block.strip()

        if cleaned:

            result.append(
                cleaned
            )

    return result


# =====================================================
# 🔥 DIALOG BLOAT SUPPRESSION
# =====================================================

def suppress_dialog_bloat(

    text,
    behavior=None

):

    behavior = behavior or {}

    if not isinstance(
        text,
        str
    ):

        return text

    density = behavior.get(
        "response_density",
        0.5
    )

    if density >= 0.55:

        return text

    replacements = {

        "Я думаю, что": "",
        "Мне кажется, что": "",
        "Стоит отметить, что": "",
        "Можно сказать, что": "",
        "Важно понимать, что": "",
        "Следует отметить, что": ""
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return text.strip()


# =====================================================
# 🔥 ROBOTIC SUPPRESSION
# =====================================================

def suppress_robotic_phrasing(

    text,
    behavior=None

):

    behavior = behavior or {}

    if not isinstance(
        text,
        str
    ):

        return text

    suppression = behavior.get(
        "robotic_suppression",
        0.9
    )

    if suppression < 0.5:

        return text

    robotic_phrases = [

        "Конечно!",
        "Отличный вопрос!",
        "Давай разберемся.",
        "Я готов помочь.",
        "Чем еще помочь?",
        "Буду рад помочь.",
        "С удовольствием."
    ]

    for phrase in robotic_phrases:

        text = text.replace(
            phrase,
            ""
        )

    return text.strip()


# =====================================================
# 🔥 LATENT GUIDANCE
# =====================================================

def stabilize_latent_guidance(

    text,
    behavior=None

):

    behavior = behavior or {}

    if not isinstance(
        text,
        str
    ):

        return text

    guidance = behavior.get(
        "latent_guidance",
        0.6
    )

    if guidance < 0.65:

        return text

    sections = split_into_sections(
        text
    )

    if not sections:

        return text

    final = []

    for section in sections:

        cleaned = section.strip()

        if not cleaned:
            continue

        cleaned = re.sub(
            r"\?$",
            ".",
            cleaned
        )

        final.append(
            cleaned
        )

    return "\n\n".join(final)


# =====================================================
# 🔥 SEMANTIC PACING
# =====================================================

def stabilize_semantic_flow(

    text,
    behavior=None

):

    behavior = behavior or {}

    if not isinstance(
        text,
        str
    ):

        return text

    if not text:
        return ""

    sections = split_into_sections(
        text
    )

    stabilized = []

    for section in sections:

        cleaned = section.strip()

        if not cleaned:
            continue

        cleaned = re.sub(
            r"\n{2,}",
            "\n",
            cleaned
        )

        stabilized.append(
            cleaned
        )

    return "\n\n".join(
        stabilized
    ).strip()


# =====================================================
# 🔥 VISUAL ENRICHMENT
# =====================================================

def detect_primary_emoji(text):

    if not isinstance(
        text,
        str
    ):

        return None

    t = text.lower()

    checks = [

        (
            ["код", "python", "react"],
            "💻"
        ),

        (
            ["идея", "концепция"],
            "💡"
        ),

        (
            ["ошибка", "warning"],
            "⚠️"
        ),

        (
            ["обновление", "новость"],
            "📰"
        )
    ]

    for words, emoji in checks:

        for word in words:

            if word in t:

                return emoji

    return None


def apply_visual_enrichment(

    text,
    behavior=None

):

    behavior = behavior or {}

    if not isinstance(
        text,
        str
    ):

        return text

    if not text:
        return ""

    if is_code_payload(text):

        return text

    initiative = behavior.get(
        "initiative_level",
        0.35
    )

    if initiative <= 0.25:

        return text

    emoji = detect_primary_emoji(
        text
    )

    if not emoji:

        return text

    if text.startswith(emoji):

        return text

    return f"{emoji} {text}"


# =====================================================
# 🔥 BYPASS RULES
# =====================================================

def should_skip_formatting(

    text,
    semantic=None,
    response_decision=None

):

    semantic = semantic or {}

    response_decision = (
        response_decision or {}
    )

    # =================================================
    # 🔥 MACHINE SAFE
    # =====================================================

    if is_machine_payload(text):

        safe_format_log(
            "MACHINE BYPASS"
        )

        return True

    # =================================================
    # 🔥 RENDERER SAFE
    # =====================================================

    if is_renderer_payload(text):

        safe_format_log(
            "RENDERER BYPASS"
        )

        return True

    # =================================================
    # 🔥 OBJECT SAFE
    # =====================================================

    if isinstance(
        text,
        (dict, list)
    ):

        safe_format_log(
            "OBJECT BYPASS"
        )

        return True

    # =================================================
    # 🔥 STRING SAFE
    # =====================================================

    if not isinstance(
        text,
        str
    ):

        return True

    if not text:

        return True

    # =================================================
    # 🔥 JSON SAFE
    # =====================================================

    # Legacy JSON route retired.
    # JSON strings continue through the normal formatter.


    # =================================================
    # 🔥 CODE SAFE
    # =====================================================

    if is_code_payload(text):
        # Do not bypass renderer candidates such as markdown tables.
        if "|" in text and "\n|" in text:
            safe_format_log("TABLE CANDIDATE")
        else:
            safe_format_log(
                "CODE BYPASS"
            )
            return True

    return False



# =====================================================
# 🔥 MATH NORMALIZATION
# =====================================================

def normalize_math_explanations(text):

    if not isinstance(text, str):
        return text

    normalized = []

    for line in text.splitlines():

        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)

        line = re.sub(
            r"^\s*[-•]\s*([A-Za-zА-Яа-яα-ωΑ-Ω0-9_ρλωθπΩΣμν]+)\s*[:–-]\s*",
            r"\1 — ",
            line
        )

        line = re.sub(
            r"^\s*([A-Za-zА-Яа-яα-ωΑ-Ω0-9_ρλωθπΩΣμν]+)\s*[:–-]\s*",
            r"\1 — ",
            line
        )

        normalized.append(line)

    return "\n".join(normalized)


# =====================================================
# 🔥 FINAL VOICE STABILIZATION
# =====================================================

def apply_april_final_voice(

    text,
    behavior=None

):

    behavior = behavior or {}

    if not isinstance(
        text,
        str
    ):

        return text

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    text = re.sub(
        r"[ ]{2,}",
        " ",
        text
    )

    return text.strip()


# =====================================================
# 🔥 BEAUTIFY RESPONSE
# =====================================================

def beautify_response(

    text,
    semantic=None,
    cognition=None,
    response_decision=None,
    user_text=""

):

    semantic = semantic or {}

    cognition = cognition or {}

    response_decision = (
        response_decision or {}
    )

    behavior = extract_behavior_field(
        cognition
    )

    if should_skip_formatting(

        text,
        semantic,
        response_decision

    ):

        return text

    text = cleanup_markdown(
        text
    )

    text = suppress_internal_reasoning(
        text
    )

    text = inject_guidance_context(
        text,
        cognition,
        response_decision
    )

    text = suppress_robotic_phrasing(
        text,
        behavior
    )

    text = suppress_dialog_bloat(
        text,
        behavior
    )

    text = stabilize_latent_guidance(
        text,
        behavior
    )

    text = stabilize_semantic_flow(
        text,
        behavior
    )

    text = normalize_math_explanations(
        text
    )

    text = apply_visual_enrichment(
        text,
        behavior
    )

    text = apply_april_final_voice(
        text,
        behavior
    )

    return text


# =====================================================
# 🔥 FINAL PRESENTATION ENTRY
# =====================================================

def format_response_presentation(

    text="",
    response="",
    semantic=None,
    cognition=None,
    response_decision=None,
    user_text="",
    visual_reference=None

):

    presentation_enter(
        response or text,
        semantic
    )

    semantic = semantic or {}

    cognition = cognition or {}

    response_decision = (
        response_decision or {}
    )

    final_text = response or text

    # =================================================
    # 🔥 MACHINE SAFE
    # =====================================================

    if is_machine_response(final_text):
        safe_format_log("MACHINE RESPONSE -> SCENE CONTRACT")
        return finalize_presentation_payload({
            "presentation_mode": "scene_pipeline",
            "machine_response": final_text
        })

    if isinstance(final_text, dict) and final_text.get("type")=="provider_response":
        mr = final_text.get("machine_response")
        if is_machine_response(mr):
            safe_format_log("PROVIDER -> SCENE CONTRACT")
            return finalize_presentation_payload({
                "presentation_mode":"scene_pipeline",
                "machine_response": mr
            })
        safe_format_log("PROVIDER CONTRACT PRESERVED")
        return final_text

    if is_machine_payload(final_text):

        safe_format_log(
            "FINAL MACHINE PAYLOAD PRESERVED"
        )

        return final_text

    # =================================================
    # 🔥 RENDERER SAFE
    # =====================================================

    if is_scene_contract(final_text):
        safe_format_log("SCENE CONTRACT PRESERVED")
        return final_text

    if isinstance(final_text, dict) and final_text.get("type")=="scene":
        safe_format_log("MACHINE SCENE PRESERVED")
        return final_text

    if is_renderer_payload(final_text):

        safe_format_log(
            "FINAL RENDERER PAYLOAD PRESERVED"
        )

        return final_text

    # =================================================
    # 🔥 NORMALIZATION
    # =====================================================

    final_text = normalize_text_payload(
        final_text
    )

    # =================================================
    # 🔥 OBJECT SAFE
    # =====================================================

    if is_scene_contract(final_text):
        safe_format_log("FINAL SCENE CONTRACT")
        return final_text

    if not isinstance(
        final_text,
        str
    ):
        safe_format_log("FINAL OBJECT PRESERVED")
        return final_text

    if not final_text:

        return ""

    # =================================================
    # 🔥 FINAL BYPASS
    # =====================================================

    if should_skip_formatting(

        final_text,
        semantic,
        response_decision

    ):

        safe_format_log(
            "FINAL BYPASS"
        )

        return final_text

    # =================================================
    # 🔥 FINAL HUMAN PRESENTATION
    # =====================================================

    result = beautify_response(

        final_text,

        semantic,
        cognition,
        response_decision,

        user_text
    )

    presentation_exit(
        result
    )

    return result

# APRIL PATCH
def suppress_internal_status(text):
    if not isinstance(text, str):
        return text
    blocked = [
        "Следующий шаг:",
        "ready_to_help",
        "request_formula",
        "request_image",
        "request_error_details"
    ]
    for b in blocked:
        text = text.replace(b, "")
    return text


# =====================================================
# STAGE 3 - Preserve scene pipeline contract
# =====================================================

def preserve_scene_pipeline(payload):
    if isinstance(payload, dict) and payload.get("presentation_mode") == "scene_pipeline":
        safe_format_log("SCENE PIPELINE PRESERVED")
        return payload
    return payload


# =====================================================
# STAGE 4 - MachineResponse -> Scene Contract
# =====================================================

def build_scene_contract(machine_response):
    if not isinstance(machine_response, dict):
        return machine_response

    return {
        "type": "scene_contract",
        "scene_present": True,
        "scene": machine_response.get("scene", {}),
        "artifacts": machine_response.get("artifacts", []),
        "scene_plan": machine_response.get("scene_plan", ""),
        "summary": machine_response.get("summary", {}),
        # Preserve user-facing response fields
        "content": machine_response.get("content", ""),
        "answer": machine_response.get("answer", ""),
        "render_priority": machine_response.get("render_priority", 0),
        "confidence": machine_response.get("confidence", 0),
        "metadata": machine_response.get("metadata", {}),

        # Preserve renderer payloads for AprilWeb
        "render_blocks": machine_response.get("render_blocks", []),
        "blocks": machine_response.get("blocks", machine_response.get("render_blocks", [])),
        "renderer_state": machine_response.get("renderer_state", {}),
        "visual_blocks": machine_response.get("visual_blocks", []),
        "space": machine_response.get("space", {}),
    }


# =====================================================
# STAGE 5 - Unified Presentation Route
# =====================================================

def finalize_presentation_payload(payload):
    if not isinstance(payload, dict):
        return payload

    if is_scene_contract(payload):
        safe_format_log("SCENE CONTRACT PASSTHROUGH")
        return payload

    if (
        payload.get("presentation_mode") == "scene_pipeline"
        and "machine_response" in payload
    ):
        mr = payload["machine_response"]
        if is_scene_contract(mr):
            safe_format_log("READY SCENE CONTRACT")
            return mr
        safe_format_log("SCENE CONTRACT BUILT")
        return build_scene_contract(mr)

    return preserve_scene_pipeline(payload)


# =====================================================
# FINAL ROUTE MARKER
# =====================================================

PRESENTATION_ROUTE_VERSION = "fiber_scene_v1"
