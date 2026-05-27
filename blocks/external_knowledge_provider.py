# =====================================================
# 🧠 APRIL EXTERNAL KNOWLEDGE PROVIDER
# =====================================================

"""
DeepHub / April upgrade:

Этот слой больше НЕ:
- trigger-based internet router;
- keyword escalation layer;
- aggressive external lookup detector;
- text-trigger execution switch.

Теперь это:
- semantic support layer;
- machine-state enrichment provider;
- execution-safe contextual helper;
- renderer-safe external context layer.

Главное:
- НЕ ломать renderer-first;
- НЕ перехватывать orchestration;
- НЕ ломать graph/formula/table pipeline;
- НЕ вмешиваться в scene routing;
- НЕ эскалировать без semantic signal.

External knowledge —
это helper capability,
а НЕ authority layer.
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from openai import OpenAI

from blocks.web_search_system import (
    search_web,
    build_search_summary,
    detect_live_lookup_intent
)

client = OpenAI()

# =====================================================
# 🧠 MACHINE SEMANTIC STATES
# =====================================================

SEMANTIC_EXECUTION_STATES = {

    "renderer_safe": [
        "graph",
        "formula",
        "table",
        "diagram",
        "scene",
        "layout"
    ],

    "knowledge_safe": [
        "knowledge",
        "travel",
        "internet",
        "reference",
        "news",
        "location",
        "realtime"
    ],

    "blocked_modes": [
        "renderer_first",
        "lightweight_visual",
        "scene_render",
        "local_render"
    ]
}

# =====================================================
# 🧠 WEB CAPABILITIES
# =====================================================

WEB_CAPABILITIES = {

    "real_time_search": True,
    "verified_links": True,
    "live_internet_access": True,

    "contextual_enrichment": True,
    "semantic_lookup": True,
    "execution_support": True,

    "renderer_safe": True,
    "provider_aware": True,
    "continuity_safe": True,

    "hallucination_risk": False,
    "requires_verification": True
}

# =====================================================
# 🔥 SEMANTIC HELPERS
# =====================================================

def _safe_lower(value):

    return (
        str(value or "")
        .strip()
        .lower()
    )


def _contains_any(
    text,
    words
):

    return any(
        x in text
        for x in words
    )

# =====================================================
# 🔥 RENDERER PROTECTION
# =====================================================

def should_block_external_lookup(
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    # =================================================
    # 🔥 RENDERER-FIRST
    # =====================================================

    if semantic.get(
        "prefer_renderer"
    ):
        return True

    if semantic.get(
        "renderer_space_active"
    ):
        return True

    if semantic.get(
        "renderer_first"
    ):
        return True

    if semantic.get(
        "scene_render_active"
    ):
        return True

    if semantic.get(
        "lightweight_visual_mode"
    ):
        return True

    # =================================================
    # 🔥 EXPECTED OUTPUT
    # =====================================================

    expected_output = semantic.get(
        "expected_output_type"
    )

    if expected_output in (
        SEMANTIC_EXECUTION_STATES[
            "renderer_safe"
        ]
    ):
        return True

    # =================================================
    # 🔥 RESPONSE DECISION
    # =====================================================

    if response_decision.get(
        "avoid_external_escalation"
    ):
        return True

    if response_decision.get(
        "avoid_heavy_generation"
    ):
        return True

    # =================================================
    # 🔥 COGNITION
    # =====================================================

    if cognition.get(
        "renderer_space_active"
    ):
        return True

    return False

# =====================================================
# 🧠 REALTIME DETECTION
# =====================================================

def detect_realtime_need(
    text: str,
    semantic: dict
):

    text = _safe_lower(
        text
    )

    semantic = semantic or {}

    # =================================================
    # 🔥 MACHINE STATES
    # =====================================================

    if semantic.get(
        "realtime_lookup"
    ):
        return True

    if semantic.get(
        "internet_required"
    ):
        return True

    if semantic.get(
        "live_context_required"
    ):
        return True

    if semantic.get(
        "geo_lookup"
    ):
        return True

    # =================================================
    # 🔥 FALLBACK
    # =====================================================

    if detect_live_lookup_intent(
        text
    ):
        return True

    return False

# =====================================================
# 🧠 EXECUTION SUPPORT
# =====================================================

def should_support_execution(
    semantic: dict,
    cognition: dict
):

    semantic = semantic or {}
    cognition = cognition or {}

    # =================================================
    # 🔥 SEMANTIC STATES
    # =====================================================

    if semantic.get(
        "execution_support_required"
    ):
        return True

    if semantic.get(
        "knowledge_enrichment"
    ):
        return True

    if semantic.get(
        "internet_assistance"
    ):
        return True

    # =================================================
    # 🔥 COGNITION STATES
    # =====================================================

    if cognition.get(
        "needs_guidance"
    ):
        return True

    if cognition.get(
        "needs_external_context"
    ):
        return True

    return False

# =====================================================
# 🧠 EXTERNAL KNOWLEDGE DETECTION
# =====================================================

def should_use_external_knowledge(
    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    # =================================================
    # 🔥 BLOCKED
    # =====================================================

    if should_block_external_lookup(

        semantic,
        cognition,
        response_decision
    ):

        return False

    # =================================================
    # 🔥 REALTIME
    # =====================================================

    if detect_realtime_need(
        text,
        semantic
    ):
        return True

    # =================================================
    # 🔥 EXECUTION SUPPORT
    # =====================================================

    if should_support_execution(
        semantic,
        cognition
    ):
        return True

    # =================================================
    # 🔥 SEMANTIC KNOWLEDGE
    # =====================================================

    if semantic.get(
        "requires_external_knowledge"
    ):
        return True

    if semantic.get(
        "knowledge_lookup"
    ):
        return True

    if semantic.get(
        "travel_lookup"
    ):
        return True

    if semantic.get(
        "reference_lookup"
    ):
        return True

    # =================================================
    # 🔥 ROOM SUPPORT
    # =====================================================

    room = semantic.get(
        "room"
    )

    if room in [

        "knowledge",
        "travel",
        "internet",
        "research",
        "navigation"
    ]:

        return True

    return False

# =====================================================
# 🧠 PROMPT BUILD
# =====================================================

def build_external_prompt(
    text: str,
    semantic: dict,
    cognition: dict
):

    semantic = semantic or {}
    cognition = cognition or {}

    goal_stage = semantic.get(
        "goal_stage",
        "dialog"
    )

    return f"""
Ты — external support layer April.

ВАЖНО:
- НЕ перехватывай orchestration;
- НЕ ломай trajectory;
- НЕ отвечай как отдельный AI;
- НЕ создавай renderer artifacts;
- НЕ выдумывай ссылки;
- НЕ hallucinate URL.

Режим:
{goal_stage}

Запрос:
{text}

Нужны:
- verified facts;
- lightweight enrichment;
- useful context;
- concise information.
"""

# =====================================================
# 🌐 FETCH KNOWLEDGE
# =====================================================

def fetch_external_knowledge(
    text: str,
    semantic: dict,
    cognition: dict
):

    try:

        # =================================================
        # 🌐 REAL WEB SEARCH
        # =====================================================

        web_results = search_web(
            text
        )

        summary = build_search_summary(
            web_results
        )

        if summary:

            return {

                "success": True,

                "content": summary,

                "source": "real_web_search",

                "verified": True,

                "results":
                    web_results.get(
                        "results",
                        []
                    ),

                "live_intent":
                    web_results.get(
                        "live_intent",
                        False
                    ),

                "used_real_web": True
            }

        # =================================================
        # 🔥 SAFE FALLBACK
        # =====================================================

        prompt = build_external_prompt(

            text,
            semantic,
            cognition
        )

        response = client.responses.create(

            model="gpt-4o-mini",

            input=prompt,

            temperature=0.2,

            max_output_tokens=180
        )

        output = (
            response.output_text
            or ""
        ).strip()

        if not output:

            return {

                "success": False,

                "content": ""
            }

        return {

            "success": True,

            "content": output,

            "source": "safe_contextual_fallback",

            "verified": False,

            "used_real_web": False
        }

    except Exception as e:

        print(
            "EXTERNAL KNOWLEDGE ERROR:",
            e
        )

        return {

            "success": False,

            "content": "",

            "error": str(e)
        }

# =====================================================
# 🧠 ENRICHMENT
# =====================================================

def enrich_with_external_knowledge(
    base_response: str,
    knowledge_result: dict
):

    if not knowledge_result:
        return base_response

    if not knowledge_result.get(
        "success"
    ):
        return base_response

    knowledge = knowledge_result.get(
        "content",
        ""
    ).strip()

    if not knowledge:
        return base_response

    if not base_response:
        return knowledge

    return (

        base_response.strip()
        + "\n\n"
        + knowledge
    )

# =====================================================
# 🧠 CONTEXT BUILD
# =====================================================

def build_external_context(
    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    if not should_use_external_knowledge(

        text,
        semantic,
        cognition,
        response_decision
    ):

        return {

            "enabled": False,

            "content": "",

            "web_capabilities":
                WEB_CAPABILITIES
        }

    result = fetch_external_knowledge(

        text,
        semantic,
        cognition
    )

    if not result.get(
        "success"
    ):

        return {

            "enabled": False,

            "content": "",

            "web_capabilities":
                WEB_CAPABILITIES
        }

    return {

        "enabled": True,

        "content":
            result.get(
                "content",
                ""
            ),

        "verified":
            result.get(
                "verified",
                False
            ),

        "results":
            result.get(
                "results",
                []
            ),

        "live_intent":
            result.get(
                "live_intent",
                False
            ),

        "used_real_web":
            result.get(
                "used_real_web",
                False
            ),

        "web_capabilities":
            WEB_CAPABILITIES
    }
