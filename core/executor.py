# =====================================================
# 🧠 APRIL EXECUTOR
# =====================================================

from blocks.intent_resolver import resolve_input

from blocks.response_mode import detect_response_mode
from blocks.text_module import process as text_process

from blocks.intent_system import detect_intent
from blocks.intent_ai import detect_intent_ai
from blocks.router import route_request

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

from blocks.anchor_system import get_anchor
from blocks.mode_manager import get_mode

from blocks.context_system import build_context_text

from blocks.rooms_registry import ROOMS
from blocks.engineering_system import analyze_code

from blocks.image_module import process as image_generate
from blocks.image_module import extract_image_prompt
from blocks.image_edit_module import process as image_edit

from blocks.image_system import analyze_image

from blocks.semantic_core import analyze as semantic_analyze
from blocks.goal_engine import detect_goal
from blocks.reasoning_state import build_reasoning_state

from blocks.cognitive_core import analyze_cognition

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

        print("PATCH LOG ERROR:", e)


def patch_executor_start(
    user_id,
    text
):

    safe_patch_log(

        f"EXECUTOR START: "
        f"{user_id} | {text[:50]}"
    )

    return None


def patch_executor_hook(
    *args,
    **kwargs
):

    return None


# =====================================================
# 🧠 RESPONSE QUALITY ANALYSIS
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

        "не удалось",
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
# 🧠 EXECUTION FAILURE ANALYSIS
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

            "⚠️ Я почти завершила "
            "обработку, но execution "
            "столкнулся с syntax-конфликтом. "
            "Продолжаю искать решение."
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
            "слишком много времени. "
            "Пробую более лёгкий путь."
        )

        return analysis

    analysis["reason"] = (
        "execution_failure"
    )

    analysis["should_change_room"] = True

    analysis["user_safe_message"] = (

        "⚠️ Текущий execution path "
        "не смог нормально завершить "
        "задачу. Продолжаю искать "
        "другой способ."
    )

    return analysis


# =====================================================
# 🧠 CAPABILITY AWARENESS
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

    t = text.lower().strip()

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

    operators = [

        "+",
        "-",
        "*",
        "/"
    ]

    if any(
        op in t
        for op in operators
    ):

        digit_count = sum(
            ch.isdigit()
            for ch in t
        )

        if digit_count >= 2:

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

    if any(
        w in t
        for w in [

            "график html",
            "интерактив",
            "браузер"
        ]
    ):

        return "graph_html"

    if any(
        w in t
        for w in [

            "картинкой",
            "png",
            "изображением"
        ]
    ):

        return "graph_image"

    return "auto"


# =====================================================
# 🔥 MEMORY EXTRACTION
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
# 🚀 EXECUTOR
# =====================================================

async def execute(
    user_id,
    text,
    chat_id,
    run_with_typing,
    callback_data=None
):

    print("🔥 EXECUTOR RUNNING")

    patch_executor_start(
        user_id,
        text
    )

    state = get_state(user_id)

    mode = get_mode(user_id)

    print("🧠 ROOMS LOADED:",
        [r.name for r in ROOMS]
    )

    capability_awareness = (
        build_capability_awareness()
    )

    # =================================================
    # 🧠 SEMANTIC CORE
    # =================================================

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

    cognition = analyze_cognition(

        text=text,

        state=state,

        semantic=semantic,

        reasoning=reasoning
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

    # =================================================
    # 🧠 RESPONSE DECISION
    # =================================================

    final_action = response_decision.get(
        "final_action",
        "talk"
    )

    if final_action == "guide":

        semantic["should_execute"] = False

        semantic["response_mode"] = "guide"

        semantic["goal_stage"] = (
            "exploration"
        )

    elif final_action == "execute":

        semantic["should_execute"] = True

        semantic["response_mode"] = (
            "execute"
        )

    elif final_action == "reference":

        semantic["should_execute"] = False

        semantic["response_mode"] = (
            "visual_guidance"
        )

    # =================================================
    # 🌐 EXTERNAL KNOWLEDGE
    # =====================================================

    external_context = ""

    try:

        external_result = build_external_context(

            text=text,

            semantic=semantic,

            cognition=cognition,

            response_decision=response_decision
        )

        external_context = external_result.get(
            "content",
            ""
        )

        print(
            "🌍 EXTERNAL CONTEXT ENABLED:",
            bool(external_context)
        )

    except Exception as e:

        print(
            "❌ EXTERNAL CONTEXT ERROR:",
            e
        )

        traceback.print_exc()

        external_result = {}

        external_context = ""

    # =================================================
    # 🧠 INTERNAL DIALOG ANALYSIS
    # =================================================

    state["dialog_analysis"] = {

        "trajectory_active":
            cognition.get(
                "needs_continuation"
            ),

        "user_waiting_action":
            reasoning.get(
                "user_waiting_action"
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
            ),

        "assistant_understands_direction":
            cognition.get(
                "understands_user_direction"
            )
    }

    # =================================================
    # 🧠 STATE
    # =================================================

    state["semantic"] = semantic
    state["reasoning"] = reasoning
    state["cognition"] = cognition
    state["visual_reference"] = (
        visual_reference
    )
    state["response_decision"] = (
        response_decision
    )

    # =================================================
    # 🔒 IMAGE LOCK
    # =================================================

    if state.get("image_lock"):

        return {

            "type": "text",

            "data":
                "⏳ Изображение ещё обрабатывается"
        }

    # =================================================
    # 💬 DIALOG SAVE
    # =================================================

    add_dialog(
        user_id,
        "user",
        text
    )

    update_memory_summary(
        user_id,
        text
    )

    # =================================================
    # 🔥 TASK TYPE
    # =================================================

    semantic_intent = semantic.get(
        "intent"
    )

    if semantic_intent:

        task_type = semantic_intent

    else:

        task_type = detect_task_type(
            text
        )

    # =================================================
    # 🔥 ACTIVE FLOW
    # =================================================

    if task_type == "math":

        set_active_flow(

            user_id,

            {
                "type": "math",
                "original": text
            }
        )

    elif task_type in [

        "image_generate",
        "image_edit",
        "image"
    ]:

        set_active_flow(

            user_id,

            {
                "type": "image"
            }
        )

    # =================================================
    # ⚡ ENERGY
    # =================================================

    energy = get_energy(user_id)

    # =================================================
    # 🧠 CONTEXT
    # =================================================

    context = {

        "chat_id": chat_id,

        "state": state,

        "mode": mode,

        "task_type": task_type,

        "energy": energy,

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
            capability_awareness,

        "external_context":
            external_context
    }

    # =================================================
    # 🧠 ROOM SELECTION
    # =================================================

    scored_rooms = []

    for room in ROOMS:

        try:

            score = room.evaluate(
                text,
                context
            )

            print(
                "🧠 ROOM SCORE:",
                room.name,
                score
            )

            if semantic.get(
                "should_execute"
            ):

                if room.name in [

                    "image_generate",
                    "image_edit",
                    "science"
                ]:

                    score += 1.5

            if cognition.get(
                "prefer_execution"
            ):

                if room.name == "text":

                    score -= 0.7

            if cognition.get(
                "prefer_visual"
            ):

                if room.name in [

                    "image_generate",
                    "image_edit"
                ]:

                    score += 0.8

            continuation_target = semantic.get(
                "continuation_target"
            )

            if continuation_target == "math":

                if room.name == "science":

                    score += 1.5

            if continuation_target == "image":

                if room.name in [

                    "image_generate",
                    "image_edit"
                ]:

                    score += 1.5

            if semantic.get(
                "best_capability"
            ):

                if room.name == semantic.get(
                    "best_capability"
                ):

                    score += 5.0

            if external_context:

                if room.name == "text":

                    score += 0.6

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

    # =================================================
    # 🧠 HARD ROOM AUTHORITY
    # =================================================

    semantic_room = semantic.get(
        "room"
    )

    if semantic_room:

        filtered_rooms = []

        for score, room in scored_rooms:

            if room.name == semantic_room:

                filtered_rooms.append(
                    (score, room)
                )

        if filtered_rooms:

            scored_rooms = filtered_rooms

    # =================================================
    # 🚀 ROOM EXECUTION
    # =================================================

    best_result = None

    for score, room in scored_rooms:

        try:

            if score <= 0:

                continue

            print(

                f"🧠 ROOM SELECTED: "
                f"{room.name} | score={score}"
            )

            result = await room.handle(

                user_id,

                text,

                context,

                run_with_typing
            )

            if (

                result
                and result.get("type")
            ):

                if result.get("type") == "image_task":

                    state["image_lock"] = True

                    try:

                        result = await image_generate(

                            user_id,

                            result["prompt"],

                            state
                        )

                    finally:

                        state["image_lock"] = False

                quality = (
                    evaluate_response_quality(

                        result,

                        semantic,

                        cognition
                    )
                )
                # =============================================
                # 🔥 APRIL AUTHORITY REVIEW
                # =============================================


                override_required = (
                     should_override(

                         result=result,

                         semantic=semantic,

                         cognition=cognition,

                         state=state
                    )
                )

                if override_required:

                    print(
                        "🧠 APRIL AUTHORITY OVERRIDE"
                    )

                    continue

                state[
                    "last_response_quality"
                ] = quality

                if not quality.get(
                    "helpful"
                ):

                    print(
                        "⚠️ RESULT NOT HELPFUL"
                    )

                    continue

                if result.get("data"):

                    result["data"] = (
                        format_response_presentation(

                            text=result["data"],

                            user_text=text,

                            semantic=semantic,

                            cognition=cognition,

                            visual_reference=visual_reference
                        )
                    )

                output_text = str(
                    result.get("data", "")
                )

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

                best_result = result

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

            if failure.get(
                "retry_possible"
            ):

                print(
                    "🧠 EXECUTION RETRY POSSIBLE"
                )

                continue

            if failure.get(
                "should_change_room"
            ):

                print(
                    "🧠 TRYING DIFFERENT ROOM"
                )

                continue

    # =================================================
    # 🧠 POST RESPONSE ANALYSIS
    # =================================================

    if best_result:

        quality = state.get(
            "last_response_quality",
            {}
        )

        if quality.get(
            "needs_continuation"
        ):

            state[
                "continuation_required"
            ] = True

        else:

            state[
                "continuation_required"
            ] = False

        return best_result

    # =================================================
    # 🔥 EXECUTION FAILURE
    # =================================================

    if (

        semantic.get(
            "should_execute"
        )

        or state.get(
            "continuation_required"
        )
    ):

        failure = state.get(
            "last_execution_failure",
            {}
        )

        safe_message = failure.get(
            "user_safe_message"
        )

        return {

            "type": "text",

            "data":

                safe_message

                or

                (
                    "⚠️ Я вижу, что задача "
                    "ещё не завершена "
                    "нормально. Продолжаю "
                    "искать решение."
                )
        }

    # =================================================
    # 💬 TEXT FALLBACK
    # =================================================

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

    print("💬 TEXT FALLBACK ACTIVATED")

    fallback_result = await run_with_typing(

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

        return {

            "type": "text",

            "data":
                fallback_result[
                    "content"
                ]
        }

    return {

        "type": "text",

        "data":
            "⚠️ Не удалось обработать запрос"
    }
