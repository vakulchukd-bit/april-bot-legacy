# =====================================================
# 🧠 APRIL PROVIDER ROUTER
# =====================================================

"""
APRIL_FILE_ID: APRIL_PROVIDER_ROUTER

ROLE:
provider_orchestration_layer

PURPOSE:
- provider coordination
- multimodal routing
- fallback stabilization
- provider recovery control
- visual provider balancing
- continuity-safe provider behavior

INPUT:
- text_requests
- image_requests
- voice_requests
- provider_state
- orchestration_signals

OUTPUT:
- normalized_provider_response
- provider_safe_output
- multimodal_response

DEPENDENCIES:
- openai
- gemini
- cognition
- semantic_core
- excrouter
- visual_system

GOLDEN RULE:
Providers generate.
April orchestrates.
"""

print("🧠 APRIL PROVIDER ROUTER LOADED")

# =====================================================
# 🔥 IMPORTS
# =====================================================

import os
import time

from openai import OpenAI
from google import genai


# =====================================================
# 🔥 PROVIDERS
# =====================================================

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PROVIDER_PATCH_LOG = []


def provider_patch_log(msg):

    try:

        print(
            "APRIL PROVIDER:",
            msg
        )

        PROVIDER_PATCH_LOG.append(
            str(msg)
        )

    except Exception:
        pass


# =====================================================
# 🔥 ENTRY / EXIT LOGGING
# =====================================================

def provider_enter(
    provider_type,
    payload=None
):

    provider_patch_log(

        f"ENTER PROVIDER: "
        f"{provider_type}"
    )

    if payload:

        provider_patch_log(
            str(payload)[:120]
        )

    return {

        "provider_active": True,

        "provider_type":
            provider_type,

        "continuity_safe": True
    }


def provider_exit(
    provider_type,
    success=True
):

    provider_patch_log(

        f"EXIT PROVIDER: "
        f"{provider_type} "
        f"SUCCESS={success}"
    )

    return {

        "provider_complete": success,

        "provider_type":
            provider_type,

        "response_ready": True
    }


# =====================================================
# 🔥 FUTURE PLACEHOLDER
# =====================================================

def provider_future(
    *args,
    **kwargs
):

    return None


# =====================================================
# 🔥 PROVIDER STATE
# =====================================================

provider_state = {

    # =================================================
    # 🔥 PRIMARY ORCHESTRATION
    # =====================================================

    "primary": "openai",

    # =================================================
    # 🔥 VISUAL ASSIST LAYER
    # =====================================================

    "gemini_available": True,

    "last_gemini_failure": 0,

    "last_health_check": 0,

    "recovery_cooldown": 45,

    # =================================================
    # 🔥 BEHAVIOR STABILIZATION
    # =====================================================

    "visual_mode": "lightweight",

    "execution_mode": "calm",

    "fallback_pressure": 0.0,

    "provider_balance": "stable"
}


# =====================================================
# 🔥 SAFE LOG
# =====================================================

def provider_log(*args):

    try:

        print(*args)

    except Exception:
        pass


# =====================================================
# 🔥 PROVIDER BEHAVIOR
# =====================================================

def update_provider_behavior():

    now = time.time()

    last_failure = provider_state.get(
        "last_gemini_failure",
        0
    )

    delta = now - last_failure

    if delta <= 60:

        provider_state[
            "fallback_pressure"
        ] = 0.7

        provider_state[
            "provider_balance"
        ] = "recovery"

    else:

        provider_state[
            "fallback_pressure"
        ] = 0.2

        provider_state[
            "provider_balance"
        ] = "stable"

    if provider_state.get(
        "gemini_available"
    ):

        provider_state[
            "visual_mode"
        ] = "distributed"

    else:

        provider_state[
            "visual_mode"
        ] = "restricted"


# =====================================================
# 🔥 GEMINI RESTORE CHECK
# =====================================================

def should_restore_gemini():

    update_provider_behavior()

    if provider_state["gemini_available"]:

        return True

    now = time.time()

    cooldown = provider_state[
        "recovery_cooldown"
    ]

    last_failure = provider_state[
        "last_gemini_failure"
    ]

    if now - last_failure >= cooldown:

        provider_log(
            "🧠 GEMINI RECOVERY WINDOW OPEN"
        )

        provider_state[
            "gemini_available"
        ] = True

        provider_state[
            "last_health_check"
        ] = now

        provider_state[
            "provider_balance"
        ] = "probing"

        return True

    return False


# =====================================================
# 🔥 GEMINI FAILURE
# =====================================================

def mark_gemini_failure():

    provider_log(
        "🔥 GEMINI MARKED UNAVAILABLE"
    )

    provider_state[
        "gemini_available"
    ] = False

    provider_state[
        "last_gemini_failure"
    ] = time.time()

    provider_state[
        "provider_balance"
    ] = "fallback"

    provider_state[
        "fallback_pressure"
    ] = 0.9


# =====================================================
# 🔥 GEMINI SUCCESS
# =====================================================

def mark_gemini_success():

    provider_state[
        "gemini_available"
    ] = True

    provider_state[
        "last_health_check"
    ] = time.time()

    provider_state[
        "provider_balance"
    ] = "stable"

    provider_state[
        "fallback_pressure"
    ] = 0.1


# =====================================================
# 🔥 RESPONSE NORMALIZER
# =====================================================

def normalize_response_text(text):

    if not text:
        return ""

    text = str(text).strip()

    text = text.replace(
        "\n\n\n",
        "\n\n"
    )

    return sanitize_internal_reasoning(text).strip()


# =====================================================
# 🔥 MACHINE RESPONSE WRAPPER
# =====================================================

def build_provider_machine_response(text, parsed_contract=None):
    """Build a unified MachineResponse transport contract."""
    parsed_contract = parsed_contract or {}

    summary = parsed_contract.get("summary", "")
    explanation = parsed_contract.get("explanation", summary)

    content = parsed_contract.get("content")
    if content is None:
        content = text

    answer = parsed_contract.get("answer")
    if answer is None:
        answer = content

    response = parsed_contract.get("response")
    if response is None:
        response = answer

    return {
        "type": "provider_response",
        "machine_response": {
            "summary": summary,
            "explanation": explanation,
            "content": content,
            "answer": answer,
            "response": response,
            "scene": parsed_contract.get("scene", {}),
            "render_blocks": parsed_contract.get("render_blocks", []),
            "artifacts": parsed_contract.get("artifacts", []),
            "scene_plan": parsed_contract.get("scene_plan", ["text"]),
            "confidence": parsed_contract.get("confidence", 1.0),
            "metadata": parsed_contract.get("metadata", {}),
            "provider": "openai",
            "render_priority": parsed_contract.get("render_priority", []),
            "provider_contract": "fiber_v3",
            "transport_contract": "scene_first"
        }
    }

import json

def parse_provider_machine_contract(raw_text):
    """Compatibility parser. Executor now prefers native MachineResponse; parser is fallback-only."""
    try:
        data=json.loads(raw_text)
        if isinstance(data,dict):
            return data
    except Exception:
        pass
    return {
        "scene": {},
        "render_blocks": [],
        "summary": raw_text,
        "explanation": raw_text,
        "artifacts": [],
        "scene_plan": ["text"],
        "confidence": 0.9,
        "render_priority":["text"],
        "metadata":{"fallback_contract":True,"parser":"compat"}
    }





# =====================================================
# STAGE 2 - SCENE-FIRST CONTRACT
# =====================================================

def ensure_scene_first_contract(contract):
    contract = validate_machine_response_contract(contract)
    contract.setdefault("scene", {})
    contract.setdefault("render_blocks", [])
    contract.setdefault("artifacts", [])
    return contract


# =====================================================
# 🔥 SAFE OVERLOAD RESPONSE
# =====================================================



def validate_machine_response_contract(contract):
    """Guarantee a valid transport contract for Executor."""
    if not isinstance(contract, dict):
        contract = {}

    contract.setdefault("summary", "")
    contract.setdefault("explanation", contract["summary"])
    contract.setdefault("artifacts", [])
    contract.setdefault("scene_plan", ["text"])
    contract.setdefault("render_priority", ["text"])
    contract.setdefault("confidence", 0.0)
    contract.setdefault("scene", {})
    contract.setdefault("render_blocks", [])
    contract.setdefault("metadata", {})

    return contract


def provider_contract_ready(machine_response):
    provider_log("🧠 FIBER ROUTE: MachineResponse READY")
    return machine_response


def build_overload_response(
    space="Dialogue-space"
):

    return (
        f"⚠️ {space} "
        f"временно перегружен."
    )



# =====================================================
# 🧠 ASSISTANT-AWARE PROVIDER ROUTING
# =====================================================

def build_provider_task_state(
    cognition=None,
    response_decision=None
):

    cognition = cognition or {}
    response_decision = response_decision or {}

    return {
        "assistant_next_step":
            cognition.get("assistant_next_step"),
        "task_understanding":
            cognition.get("task_understanding", {}),
        "scene_confidence":
            cognition.get("scene_confidence", 1.0),
        "clarification_required":
            response_decision.get(
                "task_requires_clarification",
                False
            ),
        "internal_reasoning_only":
            response_decision.get(
                "internal_reasoning_only",
                False
            )
    }


def sanitize_internal_reasoning(text):
    if not text:
        return ""
    blocked=[
        "possibly",
        "perhaps",
        "internal reasoning",
        "chain of thought",
        "I think",
        "I am reasoning"
    ]
    result=str(text)
    for item in blocked:
        result=result.replace(item,"")
    return result.strip()


PROVIDER_MACHINE_SYSTEM_PROMPT = """
You are the Provider of the APRIL Fiber Route.

Produce one unified MachineResponse for the Executor.
Return one transport contract only.
Do not produce chat text, Markdown, HTML or explanations.

Required top-level fields:
summary
explanation
scene
artifacts
render_blocks
scene_plan
render_priority
confidence
metadata

Every answer must be suitable for direct Scene construction by the Executor.
"""

def normalize_provider_input(messages):
    """
    Normalize Executor payload to Responses API input items.
    """
    system_item = {
        "role": "system",
        "content": [
            {
                "type": "input_text",
                "text": PROVIDER_MACHINE_SYSTEM_PROMPT,
            }
        ],
    }

    if isinstance(messages, str):
        return [system_item, {
            "role": "user",
            "content": [{"type": "input_text", "text": messages}],
        }]

    if isinstance(messages, dict):
        if "role" in messages and "content" in messages:
            return [system_item, messages]
        return [system_item, {
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": json.dumps(messages, ensure_ascii=False)
            }],
        }]

    if isinstance(messages, list):
        return [system_item] + messages

    return [system_item, {
        "role": "user",
        "content": [{"type": "input_text", "text": str(messages)}],
    }]

# =====================================================
# STAGE 3 - UNIFIED PROVIDER CONTRACT
# =====================================================

def create_provider_contract(raw_text):
    if (
        isinstance(raw_text, dict)
        and raw_text.get("type") == "provider_response"
        and isinstance(raw_text.get("machine_response"), dict)
    ):
        return raw_text

    parsed = raw_text if isinstance(raw_text, dict) else parse_provider_machine_contract(raw_text)
    contract = ensure_scene_first_contract(parsed)
    return build_provider_machine_response(raw_text, contract)



# =====================================================
# STAGE 4 - CENTRALIZED FALLBACK CONTRACT
# =====================================================

def build_fallback_provider_contract(space):
    overload = build_overload_response(space)
    return provider_contract_ready(
        create_provider_contract(overload)
    )


# =====================================================
# 🔥 TEXT GENERATION
# =====================================================

async def generate_text(

    messages,
    temperature=0.7,
    max_output_tokens=700,
    model="gpt-4o-mini"
):

    provider_enter(
        "openai_text",
        messages
    )

    try:

        update_provider_behavior()

        provider_log(
            "🧠 OPENAI TEXT START"
        )

        provider_log(
            "========== PROVIDER INPUT =========="
        )
        provider_log("RAW MESSAGE TYPE:", type(messages))
        provider_log("RAW MESSAGE:", str(messages)[:4000])

        provider_log(
            "🧠 PROVIDER BALANCE:",
            provider_state.get(
                "provider_balance"
            )
        )

        normalized_input = normalize_provider_input(messages)

        provider_log("========== NORMALIZED INPUT ==========")
        provider_log(json.dumps(normalized_input, ensure_ascii=False)[:8000])

        response = (

            openai_client.responses.create(

                model=model,

                input=normalized_input,

                temperature=temperature,

                max_output_tokens=max_output_tokens
            )
        )

        provider_log("========== RAW OPENAI OUTPUT ==========")
        provider_log(response.output_text[:8000] if response.output_text else "EMPTY")

        text = normalize_response_text(

            response.output_text
            if response.output_text
            else ""
        )

        if not text:

            provider_log(
                "🔥 OPENAI EMPTY RESPONSE"
            )

            provider_exit(
                "openai_text",
                False
            )

            overload = build_overload_response("Dialogue-space")
            return provider_contract_ready(
                create_provider_contract(overload)
            )

        provider_log(
            "🧠 OPENAI TEXT SUCCESS"
        )

        provider_exit(
            "openai_text",
            True
        )

        contract=create_provider_contract(text)

        provider_log("========== PROVIDER CONTRACT ==========")
        provider_log(json.dumps(contract, ensure_ascii=False)[:8000])

        return provider_contract_ready(contract)

    except Exception as e:

        provider_log(
            "🔥 OPENAI TEXT ERROR:",
            e
        )

        provider_exit(
            "openai_text",
            False
        )

        return build_fallback_provider_contract("Dialogue-space")


# =====================================================
# 🔥 VOICE TRANSCRIPTION
# =====================================================

async def transcribe_voice(
    file_path
):

    provider_enter(
        "voice_transcription",
        file_path
    )

    try:

        provider_log(
            "🧠 OPENAI VOICE START"
        )

        provider_log(
            "🧠 OPENAI AUDIO PATH:",
            file_path
        )

        with open(file_path, "rb") as f:

            transcript = (

                openai_client.audio.transcriptions.create(

                    model="gpt-4o-mini-transcribe",

                    file=f
                )
            )

        text = normalize_response_text(

            transcript.text
            if transcript.text
            else ""
        )

        provider_log(
            "🧠 OPENAI VOICE RESPONSE:",
            text[:120] if text else "EMPTY"
        )

        if text:

            provider_log(
                "🧠 OPENAI VOICE SUCCESS"
            )

            provider_exit(
                "voice_transcription",
                True
            )

            # Voice pipeline must return the recognized text itself.
            # checkout_server.normalize_voice_transcript() expects a plain
            # transcript (or a simple text field), not a provider wrapper.
            return text

        provider_exit(
            "voice_transcription",
            False
        )

        return ""

    except Exception as e:

        provider_log(
            "🔥 OPENAI VOICE ERROR:",
            e
        )

        provider_exit(
            "voice_transcription",
            False
        )

        return ""


# =====================================================
# 🔥 IMAGE ANALYSIS
# =====================================================

async def analyze_image_with_fallback(
    path,
    prompt
):

    provider_enter(
        "image_analysis",
        path
    )

    update_provider_behavior()

    # =================================================
    # 🔥 GEMINI VISUAL PRIMARY
    # =====================================================

    if should_restore_gemini():

        try:

            provider_log(
                "🧠 GEMINI IMAGE START"
            )

            provider_log(
                "🧠 VISUAL MODE:",
                provider_state.get(
                    "visual_mode"
                )
            )

            provider_log(
                "🧠 GEMINI IMAGE PATH:",
                path
            )

            uploaded = gemini_client.files.upload(
                file=path
            )

            provider_log(
                "🧠 GEMINI IMAGE UPLOADED"
            )

            response = (

                gemini_client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=[
                        uploaded,
                        prompt
                    ]
                )
            )

            text = normalize_response_text(

                response.text
                if response.text
                else ""
            )

            provider_log(
                "🧠 GEMINI IMAGE RESPONSE:",
                text[:120] if text else "EMPTY"
            )

            if text:

                mark_gemini_success()

                provider_exit(
                    "gemini_image",
                    True
                )

                return provider_contract_ready(create_provider_contract(text))

        except Exception as e:

            provider_log(
                "🔥 GEMINI IMAGE ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI VISUAL FALLBACK
    # =====================================================

    try:

        provider_log(
            "⚠️ OPENAI IMAGE FALLBACK"
        )

        provider_log(
            "🧠 FALLBACK PRESSURE:",
            provider_state.get(
                "fallback_pressure"
            )
        )

        with open(path, "rb") as image_file:

            response = (

                openai_client.responses.create(

                    model="gpt-4o-mini",

                    input=[

                        {
                            "role": "user",

                            "content": [

                                {
                                    "type": "input_text",

                                    "text": prompt
                                },

                                {
                                    "type": "input_image",

                                    "image":
                                        image_file.read()
                                }
                            ]
                        }
                    ],

                    max_output_tokens=250
                )
            )

        text = normalize_response_text(

            response.output_text
            if response.output_text
            else ""
        )

        if text:

            provider_exit(
                "openai_image_fallback",
                True
            )

            return provider_contract_ready(create_provider_contract(text))

        provider_exit(
            "openai_image_fallback",
            False
        )

        return build_fallback_provider_contract("Visual-space")

    except Exception as e:

        provider_log(
            "🔥 OPENAI IMAGE ERROR:",
            e
        )

        provider_exit(
            "openai_image_fallback",
            False
        )

        return build_fallback_provider_contract("Visual-space")


PROVIDER_ROUTE_VERSION="fiber_scene_v4"
PROVIDER_LEGACY_MODE=False
