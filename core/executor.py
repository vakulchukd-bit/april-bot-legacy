# =====================================================
# 🧠 APRIL EXECUTOR
# =====================================================

"""
APRIL EXECUTOR — DEEPHUB STABILIZED

Главная идея:

Executor больше НЕ:
- thinker-engine;
- authority-source;
- recursive orchestrator;
- trajectory creator.

Executor теперь:
- calm orchestration layer;
- scene-bound coordinator;
- execution stabilizer;
- continuity-safe router.

Final authority:
всегда принадлежит April Core
через scene_state.
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

from aiogram.types import (

    InlineKeyboardMarkup,

    InlineKeyboardButton
)

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

    """
    DeepHub quality philosophy:

    меньше noisy responses.
    меньше useless output.
    больше continuity-safe execution.
    """

    if not result:

        return {

            "success": False,

            "helpful": False,

            "needs_continuation": True
        }

    output = str(
        result.get("data", "")
    ).strip()

    result_type = result.get(
        "type",
        "text"
    )

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
# 🧠 FAILURE ANALYSIS
# =====================================================

def analyze_execution_failure(
    error,
    room_name: str,
    semantic: dict,
    cognition: dict,
    text: str
):

    """
    Failure analysis теперь:
    calmer;
    continuity-safe;
    less dramatic.
    """

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

        "создай",
        "сгенерируй",
        "нарисуй",
        "создай изображение",
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
    cognition
):

    """
    DeepHub room philosophy:

    Rooms = executors.
    НЕ authority layers.
    """

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

        if continuation_target == "image":

            if room.name in [

                "image_generate",
                "image_edit"
            ]:

                score += 1.2

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
    # =================================================
    # 🔥 VISUAL CONTINUITY BRIDGE
    # =================================================

    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        lower_text = text.lower()

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

    execution_pressure = semantic.get(
        "execution_pressure",
        0.0
    )

    signal_overload = cognition.get(
        "signal_overload",
        0.0
    )

    internal_noise = cognition.get(
        "internal_noise",
        0.0
    )

    dialog_fatigue = cognition.get(
        "dialog_fatigue",
        0.0
    )

    visual_reference = (

        build_visual_reference(

            semantic=semantic,

            cognition=cognition,

            text=text,

            state=state
        )
    )
    active_visual_scene = state.get(
        "active_visual_scene"
    )

    if active_visual_scene:

        semantic[
            "active_visual_scene"
        ] = active_visual_scene

    print("DEBUG: VISUAL OK")

    response_decision = (

        build_response_decision(

            semantic=semantic,

            cognition=cognition,

            visual_reference=visual_reference,

            state=state
        )
    )

    print("DEBUG: RESPONSE DECISION OK")

    external_context = ""

    print("EXTERNAL CONTEXT DISABLED")

    state["dialog_analysis"] = {

        "trajectory_active":
            cognition.get(
                "needs_continuation"
            ),

        "response_mode":
            response_decision.get(
                "final_action"
            ),

        "goal_stage":
            semantic.get(
                "goal_stage"
            ),

        "assistant_understands_goal":
            cognition.get(
                "understands_user_goal"
            )
    }

    state["semantic"] = semantic
    state["reasoning"] = reasoning
    state["cognition"] = cognition
    state["visual_reference"] = (
        visual_reference
    )
    state["response_decision"] = (
        response_decision
    )

    if state.get(
        "image_lock"
    ):

        return {

            "type": "text",

            "data":
                "⏳ Изображение ещё обрабатывается"
        }

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

    active_flow = get_active_flow(
        user_id
    )

    print("DEBUG: ACTIVE FLOW OK")

    semantic_entity = semantic.get(
        "entity",
        {}
    )

    semantic_goal = semantic.get(
        "goal"
    )

    goal_stage = semantic.get(
        "goal_stage",
        "exploration"
    )

    flow_payload = {

        "type": task_type,

        "entity": semantic_entity,

        "goal": semantic_goal,

        "trajectory": goal_stage,

        "original": text,

        "timestamp":
            datetime.now().isoformat(),

        "dialog_continuity":
            semantic.get(
                "dialog_continuity",
                True
            ),

        "conversation_alive":
            semantic.get(
                "conversation_alive",
                True
            )
    }

    if not active_flow:

        if task_type == "math":

            set_active_flow(

                user_id,

                flow_payload
            )

        elif task_type in [

            "image_generate",
            "image_edit",
            "image"
        ]:

            set_active_flow(

                user_id,

                flow_payload
            )

    else:

        active_entity = active_flow.get(
            "entity",
            {}
        )

        current_weight = semantic_entity.get(
            "weight",
            0.0
        )

        previous_weight = active_entity.get(
            "weight",
            0.0
        )

        if current_weight >= previous_weight:

            active_flow["entity"] = (
                semantic_entity
            )

        active_flow["trajectory"] = (
            goal_stage
        )

        active_flow["last_message"] = (
            text
        )

        active_flow["updated_at"] = (
            datetime.now().isoformat()
        )

        active_flow[
            "dialog_continuity"
        ] = semantic.get(
            "dialog_continuity",
            True
        )

        active_flow[
            "conversation_alive"
        ] = semantic.get(
            "conversation_alive",
            True
        )

        set_active_flow(

            user_id,

            active_flow
        )

    energy = get_energy(
        user_id
    )

    print("DEBUG: ENERGY OK")

    local_energy_support_active = False

    if energy == "HIGH":

        local_energy_support_active = True

    if execution_pressure >= 0.72:

        local_energy_support_active = True

    if signal_overload >= 0.65:

        local_energy_support_active = True

    if internal_noise >= 0.65:

        local_energy_support_active = True

    if dialog_fatigue >= 0.75:

        local_energy_support_active = True

    if local_energy_support_active:

        print(
            "⚡ ENERGY SUPPORT ACTIVATED"
        )

        state[
            "energy_support_active"
        ] = True

        context_energy_support = {

            "enabled": True,

            "execution_pressure":
                execution_pressure,

            "signal_overload":
                signal_overload,

            "internal_noise":
                internal_noise,

            "dialog_fatigue":
                dialog_fatigue,

            "stabilization_mode":
                "support"
        }

    else:

        state[
            "energy_support_active"
        ] = False

        context_energy_support = {

            "enabled": False
        }

    print("CONTEXT BUILD START")

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

        energy_support=context_energy_support,

        text=text
    )

    print("DEBUG: EXECUTOR CONTEXT OK")

    scored_rooms = []

    print("ROOM LOOP START")

    for room in ROOMS:

        print("ROOM EVALUATE:", room.name)

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

                cognition=cognition
            )

            web_confidence = cognition.get(
                "web_support_confidence",
                0.0
            )

            internet_needed = cognition.get(
                "internet_context_needed",
                False
            )

            if (

                internet_needed
                and web_confidence >= 0.45

            ):

                if room.name == "text":

                    score += (
                        web_confidence * 1.2
                    )

                elif room.name in [

                    "image_generate",
                    "image_edit"
                ]:

                    score -= (
                        web_confidence * 0.35
                    )

            if score <= 0:

                if room.can_handle(
                    text,
                    context
                ):

                    score = 0.2

            scored_rooms.append(
                (score, room)
            )

        except Exception as e:

            print(
                f"❌ ROOM EVALUATE ERROR "
                f"[{room.name}]",
                e
            )

            traceback.print_exc()

    scored_rooms.sort(

        key=lambda x: x[0],

        reverse=True
    )

    best_result = None
    scene_results = []

    for score, room in scored_rooms:

        try:

            if score <= 0:
                continue

            print(

                f"🧠 ROOM SELECTED: "

                f"{room.name} | "

                f"score={score}"
            )

            emaps_track_room(
                room.name
            )

            print("ROOM HANDLE START:", room.name)

            result = await room.handle(

                user_id,

                text,

                context,

                run_with_activity
            )

            print("ROOM HANDLE RESULT:", room.name, result)

            if (

                result
                and result.get("type")
            ):

                quality = (
                    evaluate_response_quality(

                        result,

                        semantic,

                        cognition
                    )
                )

                state[
                    "last_response_quality"
                ] = quality

                if not quality.get(
                    "helpful"
                ):

                    continue

                VISUAL_TYPES = [

                    "graph",
                    "formula",
                    "image",
                    "gallery",
                    "diagram",
                    "link"
                ]

                result_type = result.get(
                    "type",
                    "text"
                )

                if result_type in VISUAL_TYPES:

                    print(
                        "🧠 VISUAL OBJECT BYPASS FORMATTER"
                    )

                elif (

                    result.get("type") == "text"
                    and result.get("data")
                ):

                    output_data = str(
                        result["data"]
                    )

                    # =============================================
                    # 🔥 SCENE OBJECT DETECTION
                    # =============================================

                    scene_object_detected = any(

                        x in output_data

                        for x in [

                            "[[formula]]",
                            "[[graph]]",
                            "[[diagram]]",
                            "[[scene]]"
                        ]
                    )

                    # =============================================
                    # 🔥 TELEGRAM LEGACY FORMATTER
                    # =============================================

                    if not scene_object_detected:

                        output_data = (

                            format_response_presentation(

                                text=output_data,

                                user_text=text,

                                semantic=semantic,

                                cognition=cognition,

                                visual_reference=visual_reference
                            )
                        )

                    result["data"] = output_data

                output_text = str(
                    result.get("data", "")
                )

                # ================================
                # 🔥 SCENE OBJECT MEMORY
                # ================================

                result_type = result.get(
                    "type",
                    "text"
                )

                if result_type in [

                    "graph",
                    "formula",
                    "image",
                    "gallery",
                    "diagram"

                ]:

                    state[
                        "last_scene_object"
                    ] = {

                        "type": result_type,

                        "content": result.get(
                            "data"
                        ),

                        "created_at":
                            datetime.now().isoformat(),

                        "goal_stage":
                            goal_stage,

                        "visual_continuity":
                            semantic.get(
                                "visual_continuity",
                                False
                            )
                    }

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

                    result.get(
                        "type",
                        "text"
                    )
                )

                current_flow = get_active_flow(
                    user_id
                )

                scene_valid = True

                if current_flow:

                    current_trajectory = current_flow.get(
                        "trajectory"
                    )

                    result_type = result.get(
                        "type",
                        "text"
                    )

                    if result_type in [

                        "image",
                        "image_task",
                        "diagram",
                        "graph"
                    ]:

                        if current_trajectory != goal_stage:

                            scene_valid = False

                            print(
                                "⚠️ STALE VISUAL TASK BLOCKED"
                            )

                if not scene_valid:

                    continue

                emaps_track_chain({

                    "room": room.name,

                    "task_type": task_type,

                    "result_type": result.get(
                        "type",
                        "unknown"
                    )
                })

                best_result = result

                if result.get("type") not in [

                    "graph",
                    "formula",
                    "diagram",
                    "gallery",
                    "image"

                ]:

                    break

        except Exception as e:

            print(
                f"❌ ROOM ERROR [{room.name}]",
                e
            )

            traceback.print_exc()

            failure = (

                analyze_execution_failure(

                    error=e,

                    room_name=room.name,

                    semantic=semantic,

                    cognition=cognition,

                    text=text
                )
            )

            state[
                "last_execution_failure"
            ] = failure

    if best_result:

        print("EXECUTE RESULT:", best_result)

        return best_result

    context_text = build_context_text(

        user_id,

        text,

        state
    )

    if external_context:

        context_text += (

            "\n\n"
            "🌍 Дополнительный контекст:\n"
            f"{external_context}"
        )

    print(
        "💬 TEXT FALLBACK ACTIVATED"
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

        fallback_result["content"] = (

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

            fallback_result[
                "content"
            ]
        )

        update_memory_summary(

            user_id,

            fallback_result[
                "content"
            ]
        )

        extract_and_store_semantics(

            state,

            fallback_result[
                "content"
            ],

            "text"
        )

        print("FALLBACK RESULT:", fallback_result)

        return {

            "type": "text",

            "data":
                fallback_result[
                    "content"
                ]
        }

    print("EXECUTOR FINAL FAIL")

    return {

        "type": "text",

        "data":
            "⚠️ Не удалось обработать запрос"
    }
