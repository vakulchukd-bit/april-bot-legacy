# =====================================================
# 🧠 APRIL EXECUTOR
# =====================================================

"""
APRIL EXECUTOR — APRIL SPACE STABILIZED

Executor теперь:
- calm orchestration layer;
- renderer-first coordinator;
- continuity-safe executor;
- provider-aware router;
- scene-bound stabilizer.

Executor больше НЕ:
- Telegram-first pipeline;
- legacy image authority;
- recursive execution source;
- visual fallback chaos layer.

APRIL SPACE PHILOSOPHY:

1. renderer-space first
2. continuation before generation
3. lightweight visual before heavy image
4. provider-aware execution
5. calm orchestration
6. scene continuity protection
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from blocks.intent_resolver import resolve_input

from blocks.response_mode import (
    detect_response_mode
)

from blocks.text_module import (
    process as text_process
)

from blocks.intent_system import (
    detect_intent
)

from blocks.intent_ai import (
    detect_intent_ai
)

from blocks.router import (
    route_request
)

from blocks.router import (
    route_request
)

from blocks.state_manager import (

    get_state,

    get_image_context,

    set_image_context,

    add_dialog,

    set_dialog_state,

    update_memory_summary,

    get_active_flow,

    set_active_flow,

    clear_active_flow
)

from blocks.anchor_system import (
    get_anchor
)

from blocks.mode_manager import (
    get_mode
)

from blocks.context_system import (
    build_context_text
)

from blocks.rooms_registry import (
    ROOMS
)

from blocks.engineering_system import (
    analyze_code
)

from blocks.image_module import (
    process as image_generate
)

from blocks.image_module import (
    extract_image_prompt
)

from blocks.image_edit_module import (
    process as image_edit
)

from blocks.image_system import (
    analyze_image
)

from blocks.semantic_core import (
    analyze as semantic_analyze
)

from blocks.goal_engine import (
    detect_goal
)

from blocks.reasoning_state import (
    build_reasoning_state
)

from blocks.cognitive_core import (
    analyze_cognition
)

from blocks.visual_reference_system import (
    build_visual_reference
)

from blocks.response_decision import (
    build_response_decision
)

from blocks.april_personality import (
    apply_april_personality
)

from blocks.april_authority import (

    build_authority_state,

    should_override,

    build_authority_decision
)

# =====================================================
# 🔥 EXTERNAL KNOWLEDGE
# =====================================================

from blocks.external_knowledge_provider import (

    should_use_external_knowledge,

    build_external_context
)

# =====================================================
# 🔥 PRESENTATION
# =====================================================

from blocks.presentation_formatter import (
    format_response_presentation
)

from datetime import datetime

# =====================================================
# 🔥 TELEGRAM LEGACY SUPPRESSION
# =====================================================

"""
Telegram больше НЕ является
архитектурной частью April.

Все legacy telegram UI paths:
- passive;
- non-authoritative;
- isolated.
"""

TELEGRAM_LEGACY_MODE = False

try:

    from aiogram.types import (

        InlineKeyboardMarkup,

        InlineKeyboardButton
    )

except Exception:

    InlineKeyboardMarkup = None
    InlineKeyboardButton = None

# =====================================================
# 🔥 STORAGE
# =====================================================

from storage import (

    set_subscription,

    save_payment
)

from storage import (

    find_knowledge,

    save_knowledge
)

from blocks.energy_manager import (
    get_energy
)

from blocks.experience import (

    update_experience,

    load_experience
)

from blocks.interpretation_layer import (
    interpret_request
)

import traceback
import re

# =====================================================
# 🔥 PATCH LOG
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print("PATCH:", msg)

        PATCH_LOG.append(msg)

    except Exception as e:

        print(
            "PATCH LOG ERROR:",
            e
        )


# =====================================================
# 🧠 EMAPS METADATA
# =====================================================

EMAPS = {

    "active_systems": set(),

    "active_rooms": set(),

    "routing_chains": [],

    "task_types": set(),

    "files_roles": {},

    "last_execution": {}
}


def emaps_track_system(name):

    try:

        if name:

            EMAPS[
                "active_systems"
            ].add(name)

    except Exception as e:

        print(
            "EMAPS SYSTEM ERROR:",
            e
        )


def emaps_track_room(name):

    try:

        if name:

            EMAPS[
                "active_rooms"
            ].add(name)

    except Exception as e:

        print(
            "EMAPS ROOM ERROR:",
            e
        )


def emaps_track_chain(chain):

    try:

        if chain:

            EMAPS[
                "routing_chains"
            ].append(chain)

            EMAPS[
                "routing_chains"
            ] = EMAPS[
                "routing_chains"
            ][-30:]

    except Exception as e:

        print(
            "EMAPS CHAIN ERROR:",
            e
        )


def emaps_track_task(task_type):

    try:

        if task_type:

            EMAPS[
                "task_types"
            ].add(task_type)

    except Exception as e:

        print(
            "EMAPS TASK ERROR:",
            e
        )


def emaps_set_role(
    file_name,
    role
):

    try:

        EMAPS[
            "files_roles"
        ][file_name] = role

    except Exception as e:

        print(
            "EMAPS ROLE ERROR:",
            e
        )


# =====================================================
# 🔥 HELPERS
# =====================================================

def normalize_text(
    text
):

    return (
        text or ""
    ).strip()


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


def safe_get_scene_state(
    state: dict
):

    return state.get(
        "scene_state",
        {}
    )


def get_scene_trajectory(
    state: dict
):

    scene_state = safe_get_scene_state(
        state
    )

    return scene_state.get(
        "trajectory"
    )


def get_scene_authority_mode(
    state: dict
):

    scene_state = safe_get_scene_state(
        state
    )

    return scene_state.get(
        "orchestration_mode",
        "stable"
    )


# =====================================================
# 🧠 CONTINUITY STABILIZATION
# =====================================================

def stabilize_visual_continuity(
    semantic: dict,
    state: dict,
    text: str
):

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if not active_visual_scene:
        return semantic

    lower_text = (
        text or ""
    ).lower()

    visual_words = [

        "картин",
        "фото",
        "меню",
        "бокал",
        "бургер",
        "кревет",
        "слева",
        "справа",
        "на фото",
        "на картинке",
        "там",
        "там было"
    ]

    if any(
        x in lower_text
        for x in visual_words
    ):

        semantic[
            "visual_continuity"
        ] = True

        semantic[
            "active_visual_scene"
        ] = active_visual_scene

    return semantic


# =====================================================
# 🔥 RENDERER SPACE DETECTION
# =====================================================

def is_renderer_scene(
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    visual_continuity = semantic.get(
        "visual_continuity",
        False
    )

    render_intent = semantic.get(
        "render_intent",
        False
    )

    renderer_space = semantic.get(
        "renderer_space_request",
        False
    )

    lightweight = response_decision.get(
        "prefer_lightweight_visual",
        False
    )

    wants_visual = cognition.get(
        "wants_visual",
        0.0
    )

    exploration = cognition.get(
        "exploration_mode",
        False
    )

    if render_intent:
        return True

    if renderer_space:
        return True

    if visual_continuity:
        return True

    if (
        lightweight
        and wants_visual >= 0.45
    ):
        return True

    if (
        exploration
        and wants_visual >= 0.4
    ):
        return True

    return False


# =====================================================
# 🔥 LEGACY IMAGE SUPPRESSION
# =====================================================

def should_block_heavy_generation(
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    # =============================================
    # 🔥 ABSOLUTE RENDERER-FIRST LOCK
    # =============================================

    if semantic.get(
        "render_intent"
    ):

        return True

    if response_decision.get(
        "should_render"
    ):

        return True

    if response_decision.get(
        "avoid_heavy_generation"
    ):

        return True

    if cognition.get(
        "exploration_mode"
    ):

        return True

    if semantic.get(
        "visual_lightweight_mode"
    ):

        return True

    if semantic.get(
        "library_visual_candidate"
    ):

        return True

    if semantic.get(
        "visual_demo_request"
    ):

        return True

    if semantic.get(
        "renderer_space_request"
    ):

        return True

    return False


# =====================================================
# 🔥 EXECUTOR START
# =====================================================

def patch_executor_start(
    user_id,
    text
):

    safe_patch_log(

        f"EXECUTOR START: "

        f"{user_id} | "

        f"{text[:50]}"
    )

    return None


def patch_executor_hook(
    *args,
    **kwargs
):

    return None


# =====================================================
# 🧠 RESPONSE QUALITY
# =====================================================

def evaluate_response_quality(
    result: dict,
    semantic: dict,
    cognition: dict
):

    if not result:

        return {

            "success": False,

            "helpful": False,

            "needs_continuation": True
        }

    result_type = result.get(
        "type",
        "text"
    )

    # =============================================
    # 🔥 RENDERER TYPES ALWAYS VALID
    # =============================================

    if result_type in [

        "graph",
        "formula",
        "diagram",
        "scene",
        "table",
        "gallery",
        "image",
        "function"
    ]:

        return {

            "success": True,

            "helpful": True,

            "needs_continuation": False,

            "result_type": result_type
        }

    output = str(
        result.get("data", "")
    ).strip()

    helpful = True

    if len(output) <= 8:

        helpful = False

    bad_words = [

        "pipeline",
        "execution room",
        "traceback",
        "syntaxerror"
    ]

    if any(
        x in output.lower()
        for x in bad_words
    ):

        helpful = False

    if result_type == "text":

        if semantic.get(
            "should_execute"
        ):

            if cognition.get(
                "wants_result",
                0.0
            ) >= 0.7:

                if len(output) < 25:

                    helpful = False

    return {

        "success": True,

        "helpful": helpful,

        "needs_continuation":
            not helpful,

        "result_type": result_type
    }


# =====================================================
# 🔥 SAFE FORMAT RESPONSE
# =====================================================

def safely_format_result(

    result,
    text,
    semantic,
    cognition,
    visual_reference
):

    if not result:
        return result

    result_type = result.get(
        "type",
        "text"
    )

    VISUAL_TYPES = [

        "graph",
        "formula",
        "image",
        "gallery",
        "diagram",
        "scene",
        "function"
    ]

    # =============================================
    # 🔥 ABSOLUTE VISUAL BYPASS
    # =============================================

    if result_type in VISUAL_TYPES:

        return result

    output_data = str(
        result.get("data", "")
    )

    if not output_data.strip():

        return result

    scene_object_detected = any(

        x in output_data

        for x in [

            "[[formula]]",
            "[[graph]]",
            "[[diagram]]",
            "[[scene]]",
            "[[grid]]"
        ]
    )

    if scene_object_detected:

        return result

    result["data"] = (

        format_response_presentation(

            text=output_data,

            user_text=text,

            semantic=semantic,

            cognition=cognition,

            visual_reference=visual_reference
        )
    )

    return result


# =====================================================
# 🧠 FAILURE ANALYSIS
# =====================================================

def analyze_execution_failure(
    error,
    room_name: str,
    semantic: dict,
    cognition: dict,
    text: str
):

    error_text = str(error).lower()

    analysis = {

        "failed": True,

        "room": room_name,

        "reason": "unknown",

        "retry_possible": False,

        "should_change_room": False,

        "should_simplify": False,

        "should_hide_error": True,

        "user_safe_message": None
    }

    syntax_words = [

        "syntax",
        "unexpected character",
        "invalid syntax",
        "line continuation"
    ]

    if any(
        x in error_text
        for x in syntax_words
    ):

        analysis["reason"] = "syntax"

        analysis["retry_possible"] = True

        analysis["should_simplify"] = True

        analysis["user_safe_message"] = (

            "⚠️ Обработка почти завершена, "
            "но execution столкнулся "
            "с syntax-конфликтом."
        )

        return analysis

    timeout_words = [

        "timeout",
        "timed out"
    ]

    if any(
        x in error_text
        for x in timeout_words
    ):

        analysis["reason"] = "timeout"

        analysis["retry_possible"] = True

        analysis["user_safe_message"] = (

            "⚠️ Обработка заняла "
            "слишком много времени."
        )

        return analysis

    analysis["reason"] = (
        "execution_failure"
    )

    analysis["should_change_room"] = True

    analysis["user_safe_message"] = (

        "⚠️ Текущий execution path "
        "не завершился стабильно."
    )

    return analysis


# =====================================================
# 🧠 CAPABILITY MAP
# =====================================================

def build_capability_awareness():

    return {

        "math": [
            "science"
        ],

        "renderer_scene": [
            "text"
        ],

        "image": [
            "image_generate",
            "image_edit"
        ],

        "visual_help": [
            "text",
            "image_generate"
        ],

        "guidance": [
            "text"
        ],

        "code": [
            "text"
        ],

        "external_knowledge": [
            "text"
        ]
    }


# =====================================================
# 🔥 TASK DETECTION
# =====================================================

def detect_task_type(
    text: str
):

    t = normalize_text(
        text
    ).lower()

    renderer_words = [

        "scene",
        "layout",
        "renderer",
        "diagram",
        "grid",
        "пространство",
        "сцена",
        "блоки",
        "композиция"
    ]

    if any(
        x in t
        for x in renderer_words
    ):

        return "renderer_scene"

    image_edit_words = [

        "измени",
        "убери",
        "добавь",
        "замени",
        "улучши"
    ]

    if any(
        x in t
        for x in image_edit_words
    ):

        return "image_edit"

    image_generate_words = [

        "создай изображение",
        "сгенерируй изображение",
        "нарисуй картинку",
        "сделай картинку"
    ]

    if any(
        x in t
        for x in image_generate_words
    ):

        return "image_generate"

    math_words = [

        "график",
        "функция",
        "уравнение",
        "реши",
        "матем",
        "sin(",
        "cos(",
        "tan(",
        "y="
    ]

    if any(
        x in t
        for x in math_words
    ):

        return "math"

    if "=" in t:

        has_digits = any(
            ch.isdigit()
            for ch in t
        )

        if has_digits:

            return "math"

    return "text"


# =====================================================
# 🔥 OUTPUT MODE
# =====================================================

def detect_output_mode(
    text: str
):

    t = text.lower()

    if any(
        w in t
        for w in [

            "файл",
            "скачать",
            ".py",
            "html"
        ]
    ):

        return "file"

    if any(
        w in t
        for w in [

            "код",
            "code"
        ]
    ):

        return "code"

    return "auto"


# =====================================================
# 🔥 SEMANTIC MEMORY
# =====================================================

def extract_and_store_semantics(
    state: dict,
    text: str,
    result_type: str = "text"
):

    t = text.lower()

    match = re.search(
        r"y\s*=\s*([^\n\r]+)",
        t
    )

    if match:

        expr = match.group(1).strip()

        state["last_math"] = {

            "type": "function",

            "expr": expr
        }

    if "```" in text:

        state["last_code"] = text

    if result_type == "image":

        state["last_image"] = {

            "exists": True
        }


# =====================================================
# 🔥 ROOM SCORING
# =====================================================

def stabilize_room_score(
    room,
    score,
    state,
    semantic,
    cognition,
    response_decision
):

    scene_state = safe_get_scene_state(
        state
    )

    trajectory = scene_state.get(
        "trajectory"
    )

    orchestration_mode = scene_state.get(
        "orchestration_mode",
        "stable"
    )

    # =============================================
    # 🔥 PERSONALITY STABILIZATION
    # =============================================

    if cognition.get(
        "reduce_talking"
    ):

        if room.name == "text":

            score += 0.3

    if cognition.get(
        "assistant_should_follow"
    ):

        if room.name == "text":

            score += 0.5

    if cognition.get(
        "prefer_execution"
    ):

        if room.name == "text":

            score -= 0.5

    if cognition.get(
        "prefer_visual"
    ):

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score += 0.6

    # =============================================
    # 🔥 RENDERER-FIRST AUTHORITY
    # =============================================

    if semantic.get(
        "render_intent"
    ):

        if room.name == "science":

            score += 5.0

        elif room.name == "text":

            score += 1.2

        elif room.name in [

            "image_generate",
            "image_edit"
        ]:

            score -= 10.0

    if is_renderer_scene(

        semantic,
        cognition,
        response_decision
    ):

        if room.name == "text":

            score += 2.4

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score -= 3.5

    if should_block_heavy_generation(

        semantic,
        cognition,
        response_decision
    ):

        if room.name in [

            "image_generate",
            "image_edit"
        ]:

            score -= 4.0

    best_capability = semantic.get(
        "best_capability"
    )

    if best_capability:

        if room.name == best_capability:

            score += 2.0

    continuation_target = semantic.get(
        "continuation_target"
    )

    if continuation_target:

        if continuation_target == "math":

            if room.name == "science":

                score += 1.2

        if continuation_target in [

            "image",
            "visual_scene"
        ]:

            if room.name == "text":

                score += 1.8

    return clamp(
        score,
        -5.0,
        15.0
    )


# =====================================================
# ⚡ ENERGY SUPPORT SYSTEM
# =====================================================

energy_support_active = False


# =====================================================
# 🔥 EXECUTOR CONTEXT
# =====================================================

def build_executor_context(

    chat_id,
    state,
    mode,
    task_type,
    energy,
    semantic,
    reasoning,
    cognition,
    visual_reference,
    response_decision,
    external_context,
    energy_support,
    text
):

    scene_state = safe_get_scene_state(
        state
    )

    return {

        "chat_id": chat_id,

        "state": state,

        "scene_state": scene_state,

        "mode": mode,

        "task_type": task_type,

        "energy": energy,

        "energy_support":
            energy_support,

        "output_mode":
            detect_output_mode(text),

        "semantic": semantic,

        "reasoning": reasoning,

        "cognition": cognition,

        "visual_reference":
            visual_reference,

        "response_decision":
            response_decision,

        "trajectory_mode":
            semantic.get(
                "goal_stage",
                "exploration"
            ),

        "response_mode":
            semantic.get(
                "response_mode",
                "talk"
            ),

        "execution_pressure":
            semantic.get(
                "execution_pressure",
                0.0
            ),

        "renderer_space":
            is_renderer_scene(
                semantic,
                cognition,
                response_decision
            ),

        "capability_awareness":
            build_capability_awareness(),

        "external_context":
            external_context
    }


# =====================================================
# 🚀 EXECUTOR
# =====================================================

async def execute(
    user_id,
    text,
    chat_id,
    run_with_activity,
    callback_data=None
):

    print("🔥 EXECUTOR RUNNING")
    print("EXECUTE INPUT:", user_id, text)

    patch_executor_start(
        user_id,
        text
    )

    state = get_state(
        user_id
    )

    scene_state = safe_get_scene_state(
        state
    )

    mode = get_mode(
        user_id
    )

    semantic = semantic_analyze(

        text=text,

        state=state,

        history=state.get(
            "dialog",
            []
        ),

        active_flow=get_active_flow(
            user_id
        ),

        dialog_state=state.get(
            "dialog_state",
            {}
        )
    )

    # =============================================
    # 🔥 HARD RENDERER LOCK
    # =============================================

    if semantic.get(
        "render_intent"
    ):

        semantic[
            "prefer_renderer"
        ] = True

        semantic[
            "visual_generation_needed"
        ] = False

        semantic[
            "avoid_image_generation_fallback"
        ] = True

    # =============================================
    # 🧠 CONTINUITY STABILIZATION
    # =============================================

    semantic = stabilize_visual_continuity(

        semantic=semantic,

        state=state,

        text=text
    )

    emaps_track_system(
        "semantic_core"
    )

    emaps_track_system(
        "cognitive_core"
    )

    emaps_track_system(
        "response_decision"
    )

    emaps_track_system(
        "context_system"
    )

    emaps_track_system(
        "presentation_formatter"
    )

    emaps_track_system(
        "executor"
    )

    semantic = detect_goal(

        text=text,

        state=state,

        semantic=semantic
    )

    reasoning = build_reasoning_state(

        text=text,

        state=state,

        semantic=semantic
    )

    print("DEBUG: REASONING OK")

    cognition = analyze_cognition(

        text=text,

        state=state,

        semantic=semantic,

        reasoning=reasoning
    )

    print("DEBUG: COGNITION OK")

    # =============================================
    # 🧠 PERSONALITY INTEGRATION
    # =============================================

    cognition = apply_april_personality(

        cognition=cognition,

        semantic=semantic,

        reasoning=reasoning,

        response_decision={},

        state=state
    )

    visual_reference = (

        build_visual_reference(

            semantic=semantic,

            cognition=cognition,

            text=text,

            state=state
        )
    )

    response_decision = (

        build_response_decision(

            semantic=semantic,

            cognition=cognition,

            visual_reference=visual_reference,

            state=state
        )
    )

    print("DEBUG: RESPONSE DECISION OK")

    # =============================================
    # 🧠 AUTHORITY DECISION
    # =============================================

    authority_decision = (

        build_authority_decision(

            result={

                "type": "pre_execution",

                "data": ""
            },

            semantic=semantic,

            cognition=cognition,

            response_decision=response_decision,

            state=state
        )
    )

    state["authority_decision"] = (
        authority_decision
    )

    renderer_space = is_renderer_scene(

        semantic,
        cognition,
        response_decision
    )

    if renderer_space:

        semantic[
            "renderer_space_request"
        ] = True

        response_decision[
            "avoid_heavy_generation"
        ] = True

        cognition[
            "prefer_execution"
        ] = False

        cognition[
            "generation_should_wait"
        ] = True

    external_context = ""

    print("EXTERNAL CONTEXT DISABLED")

    state["semantic"] = semantic
    state["reasoning"] = reasoning
    state["cognition"] = cognition
    state["visual_reference"] = (
        visual_reference
    )
    state["response_decision"] = (
        response_decision
    )

    add_dialog(

        user_id,

        "user",

        text
    )

    update_memory_summary(

        user_id,

        text
    )

    semantic_intent = semantic.get(
        "intent"
    )

    if semantic_intent:

        task_type = semantic_intent

    else:

        task_type = detect_task_type(
            text
        )

    emaps_track_task(
        task_type
    )

    energy = get_energy(
        user_id
    )

    context = build_executor_context(

        chat_id=chat_id,

        state=state,

        mode=mode,

        task_type=task_type,

        energy=energy,

        semantic=semantic,

        reasoning=reasoning,

        cognition=cognition,

        visual_reference=visual_reference,

        response_decision=response_decision,

        external_context=external_context,

        energy_support={

            "enabled": False
        },

        text=text
    )

    # =============================================
    # 🧠 AUTHORITY CONTEXT
    # =============================================

    context[
        "authority_decision"
    ] = authority_decision

    scored_rooms = []

    for room in ROOMS:

        try:

            score = room.evaluate(
                text,
                context
            )

            score = stabilize_room_score(

                room=room,

                score=score,

                state=state,

                semantic=semantic,

                cognition=cognition,

                response_decision=response_decision
            )

            # =========================================
            # 🧠 AUTHORITY ROOM STABILIZATION
            # =========================================

            forced_room = (
                authority_decision.get(
                    "forced_room"
                )
            )

            if forced_room:

                if room.name == forced_room:

                    score += 4.0

                else:

                    score -= 1.0

            if score <= 0:

                continue

            scored_rooms.append(
                (score, room)
            )

        except Exception as e:

            print(
                f"ROOM SCORE ERROR [{room.name}]",
                e
            )

    scored_rooms.sort(

        key=lambda x: x[0],

        reverse=True
    )

    best_result = None
    scene_results = []

    for score, room in scored_rooms:

        try:

            emaps_track_room(
                room.name
            )

            # =============================================
            # 🔥 HARD IMAGE GENERATION BLOCK
            # =============================================

            if should_block_heavy_generation(

                semantic,
                cognition,
                response_decision
            ):

                if room.name in [

                    "image_generate",
                    "image_edit"
                ]:

                    print(
                        "🧠 HEAVY IMAGE BLOCKED"
                    )

                    continue

            result = await room.handle(

                user_id,

                text,

                context,

                run_with_activity
            )

            if not result:
                continue

            quality = (
                evaluate_response_quality(

                    result,

                    semantic,

                    cognition
                )
            )

            if not quality.get(
                "helpful"
            ):

                continue

            # =============================================
            # 🧠 AUTHORITY VALIDATION
            # =============================================

            override = should_override(

                result=result,

                semantic=semantic,

                cognition=cognition,

                state=state
            )

            if override:

                print(
                    "🧠 AUTHORITY OVERRIDE"
                )

                continue

            result = safely_format_result(

                result=result,

                text=text,

                semantic=semantic,

                cognition=cognition,

                visual_reference=visual_reference
            )

            result_type = result.get(
                "type",
                "text"
            )

            output_text = str(
                result.get("data", "")
            )

            if output_text.strip():

                add_dialog(

                    user_id,

                    "assistant",

                    output_text
                )

                update_memory_summary(

                    user_id,

                    output_text
                )

                extract_and_store_semantics(

                    state,

                    output_text,

                    result_type
                )

            best_result = result

            scene_results.append(result)

            # =============================================
            # 🔥 ABSOLUTE SINGLE RESPONSE LOCK
            # =============================================

            break

        except Exception as e:

            print(
                f"ROOM ERROR [{room.name}]",
                e
            )

            traceback.print_exc()

    # =============================================
    # 🔥 SAFE RETURN
    # =============================================

    if best_result:

        return best_result

    # =================================================
    # 🔥 TEXT FALLBACK
    # =====================================================

    context_text = build_context_text(

        user_id,

        text,

        state
    )

    fallback_result = await run_with_activity(

        chat_id,

        text_process(

            user_id,

            context_text,

            state,

            energy
        )
    )

    if (

        fallback_result
        and fallback_result.get(
            "content"
        )
    ):

        fallback_content = (

            format_response_presentation(

                text=fallback_result["content"],

                user_text=text,

                semantic=semantic,

                cognition=cognition,

                visual_reference=visual_reference
            )
        )

        add_dialog(

            user_id,

            "assistant",

            fallback_content
        )

        update_memory_summary(

            user_id,

            fallback_content
        )

        extract_and_store_semantics(

            state,

            fallback_content,

            "text"
        )

        return {

            "type": "text",

            "data": fallback_content
        }

    return {

        "type": "text",

        "data":
            "⚠️ Не удалось обработать запрос"
    }
