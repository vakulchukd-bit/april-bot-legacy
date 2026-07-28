
# =====================================================
# TEST 51
# Compatibility bootstrap
# =====================================================

def ensure_semantic_constants():
    defaults = {
        "LIGHTWEIGHT_VISUAL_WORDS": ("покажи","визуализируй","схема"),
        "RENDERER_WORDS": ("graph","diagram","table","formula"),
        "MATH_WORDS": ("формула","уравнение"),
        "WEB_WORDS": ("поиск","интернет"),
        "CODE_WORDS": ("код","python"),
        "CONTINUATION_WORDS": ("продолжай",),
        "EXPLORATION_WORDS": ("исследуй",),
        "EXPLICIT_IMAGE_WORDS": ("нарисуй","изображение"),
        "INFORMATIONAL_WORDS": ("что","как","почему"),
    }
    g = globals()
    for k,v in defaults.items():
        if k not in g:
            g[k] = v

ensure_semantic_constants()

# =====================================================
# TEST 40
# DeepHub Preparation Build
# Verified formatting and syntax pass.
# =====================================================

"""
interpretation_test30.py
STAGE 30
Semantic Input Unification
"""

UNIFIED_INTERPRETATION_INPUT = {
    "user_text": None,
    "user_voice": None,
    "user_image": None,
    "assistant_response": None,
    "dialogue_history": [],
    "active_context": {},
    "semantic_memory": {},
    "active_goal": None,
    "semantic_state": {}
}

SEMANTIC_DIALOGUE_STATE = {
    "last_user_turn": None,
    "last_april_turn": None,
    "dialogue_goal": None,
    "dialogue_context": {},
    "scene_state": {},
    "semantic_profile": {}
}


"""
interpretation_test29.py
Canonical Semantic Interpretation Layer
Cleaned transport-oriented version.
"""


SUPER_INTERPRETATION_LAYER = {
    "entrypoint": "transport_state",
    "route": "INTERPRETATION_ROUTE",
    "context": "INTERPRETATION_CONTEXT_SCHEMA",
    "state": "INTERPRETATION_STATE_TEMPLATE",
    "mode": "semantic_only",
    "compatibility": "export_only"
}

INTERPRETATION_ENTRYPOINT = "transport_state"

def resolve_interpretation_payload(result):
    return result.get("transport_state", {})

# TEST 26 - Primary Interpretation Layer

INTERPRETATION_TRANSPORT_FIELDS = {
    "dialogue_profile": ("dialogue","profile"),
    "semantic_evidence_engine": ("evidence","engine"),
    "dialogue_cognition_matrix": ("cognition","matrix"),
    "semantic_dialogue_graph": ("dialogue","graph"),
    "scene_profile": ("scene","profile"),
    "artifact_contract": ("artifacts","contract"),
    "executor_preparation_contract": ("executor","contract"),
}

def export_transport_state(state, result):
    for field,(section,key) in INTERPRETATION_TRANSPORT_FIELDS.items():
        if field in result:
            state.setdefault(section,{})[key]=result[field]
    return state

INTERPRETATION_ROUTE = (
    "dialogue_profile",
    "semantic_evidence_engine",
    "dialogue_cognition_matrix",
    "semantic_dialogue_graph",
    "scene_profile",
    "artifact_contract",
    "executor_preparation_contract",
)

def build_interpretation_route(state, result):
    route = []
    for node in INTERPRETATION_ROUTE:
        route.append({
            "node": node,
            "status": "ready",
            "payload": result.get(node)
        })
    state["diagnostics"]["route"] = route
    return route

INTERPRETATION_CONTEXT_SCHEMA = {
    "state": "interpretation_state",
    "dialogue": "semantic_profile",
    "evidence": "semantic_evidence_engine",
    "scene": "scene_profile",
    "artifact": "artifact_contract",
    "executor": "executor_preparation_contract"
}

def synchronize_interpretation_context(state, result):
    state["dialogue"]["profile"] = result.get("semantic_profile")
    state["evidence"]["engine"] = result.get("semantic_evidence_engine")
    state["scene"]["profile"] = result.get("scene_profile")
    state["artifacts"]["contract"] = result.get("artifact_contract")
    state["executor"]["contract"] = result.get("executor_preparation_contract")
    return state

INTERPRETATION_STATE_TEMPLATE = {
    "dialogue": {},
    "evidence": {},
    "cognition": {},
    "scene": {},
    "artifacts": {},
    "executor": {},
    "diagnostics": {}
}

def build_interpretation_state():
    return {
        k: (v.copy() if isinstance(v, dict) else v)
        for k,v in INTERPRETATION_STATE_TEMPLATE.items()
    }

SEMANTIC_INTERPRETATION_CORE = {
    "decision_source": "semantic_evidence_engine",
    "routing": "semantic_profiles",
    "legacy_mode": "isolated",
    "scene_contract": "artifact_first",
    "executor_contract": "advisory_only",
    "history_model": "incremental",
    "confidence_policy": "multi_evidence"
}

SEMANTIC_PIPELINE = [
    "dialogue_profile",
    "semantic_evidence_engine",
    "dialogue_cognition_matrix",
    "semantic_dialogue_graph",
    "scene_profile",
    "artifact_contract",
    "executor_preparation_contract"
]

# TEST 19

"""
APRIL_FILE_ID:
APRIL_INTERPRETATION_LAYER

ROLE:
SEMANTIC_INTERPRETATION_BRIDGE

INPUT:
USER_TEXT
COGNITION_STATE
SEMANTIC_STATE
ACTIVE_TRAJECTORY

OUTPUT:
INTERPRETATION_HINTS
SCENE_CLASSIFICATION
SEMANTIC_SUPPORT_PAYLOAD
RENDERER_COMPATIBLE_CONTEXT

=====================================================

APRIL SEMANTIC INTERPRETATION LAYER

Этот слой:
- НЕ command router;
- НЕ execution engine;
- НЕ fallback trigger.

Interpretation layer теперь:
- semantic hint system;
- lightweight intention detector;
- continuity-aware interpreter;
- cognition-assisted interpretation layer;
- renderer-aware semantic adapter.

=====================================================

ВАЖНО:

Этот слой НЕ:
- навязывает execution;
- НЕ генерирует prompts;
- НЕ вызывает generation;
- НЕ ломает orchestration;
- НЕ force routing;
- НЕ принимает решения вместо cognition.

=====================================================

Он только:
- помогает semantic_core;
- помогает cognition;
- стабилизирует semantic continuity;
- подготавливает безопасные semantic hints;
- помогает executor понять тип сцены.
"""

import time

INPUT_MACHINE_CHANNEL = {

    "source":
        "semantic_core",

    "type":
        "interpretation_input",

    "isolated":
        True
}

OUTPUT_MACHINE_CHANNEL = {

    "target":
        "executor_orchestration",

    "type":
        "interpretation_output",

    "isolated":
        True
}

PATCH_LOG = []

MAX_PATCH_LOGS = 120

def safe_patch_log(message):

    try:

        print(
            "INTERPRETATION PATCH:",
            message
        )

        PATCH_LOG.append({

            "timestamp":
                time.time(),

            "message":
                message,

            "file_id":
                "APRIL_INTERPRETATION_LAYER",

            "machine_only":
                True
        })

        if len(PATCH_LOG) > MAX_PATCH_LOGS:

            PATCH_LOG.pop(0)

    except Exception:
        pass

def contains_any(
    text,
    words
):

    return any(
        w in text
        for w in words
    )

def normalize_text(
    text: str
):

    return (
        text or ""
    ).strip()

def normalize_lower(
    text: str
):

    return normalize_text(
        text
    ).lower()

def _semantic_evidence_stub(kind, text):
    lookup={
        "legacy": WEB_WORDS,
        "renderer": RENDERER_WORDS,
        "code": CODE_WORDS,
        "information": INFORMATIONAL_WORDS,
        "continuation": CONTINUATION_WORDS,
        "exploration": EXPLORATION_WORDS,
        "image": EXPLICIT_IMAGE_WORDS,
        "math": MATH_WORDS,
        "web": WEB_WORDS,
    }
    return contains_any(normalize_lower(text), lookup.get(kind,()))

DOMAIN_REGISTRY = {

    "biology": {
        "description": "living systems, genetics, evolution, physiology, ecology, microbiology"
    },

    "chemistry": {
        "description": "reactions, compounds, molecules, materials"
    },

    "physics": {
        "description": "motion, energy, forces, fields, matter"
    },

    "engineering": {
        "description": "systems, design, construction, optimization"
    },

    "it": {
        "description": "software, hardware, networks, computing"
    },

    "literature": {
        "description": "books, texts, authors, narrative analysis"
    },

    "politics": {
        "description": "government, policy, diplomacy, political systems"
    },

    "news": {
        "description": "recent developments and current events"
    },

    "social": {
        "description": "society, behavior, communities, culture"
    },

    "web": {
        "description": "internet resources, search, websites"
    }
}

def detect_domain_candidates(text):

    lower = normalize_lower(text)

    candidates = []

    domain_words = {

        "biology": [
            "биология","генетика","эволюция","клетка","организм",
            "экология","бактерии","днк","животные","растения"
        ],

        "chemistry": [
            "химия","реакция","молекула","атом","вещество"
        ],

        "physics": [
            "физика","энергия","сила","ускорение","электричество"
        ],

        "engineering": [
            "инженерия","конструкция","механизм","система","проектирование"
        ],

        "it": [
            "программирование","алгоритм","сервер","код","разработка"
        ],

        "literature": [
            "литература","роман","поэзия","писатель","произведение"
        ],

        "politics": [
            "политика","государство","выборы","правительство"
        ],

        "news": [
            "новости","события","последние новости"
        ],

        "social": [
            "общество","социум","социальный"
        ],

        "web": [
            "сайт","интернет","поиск","веб"
        ]
    }

    for domain, words in domain_words.items():
        if any(w in lower for w in words):
            candidates.append(domain)

    return candidates

def detect_representation_candidates(text):

    lower = normalize_lower(text)

    reps = []

    if any(x in lower for x in ["график","plot","chart"]):
        reps.append("graph")

    if any(x in lower for x in ["таблица","table"]):
        reps.append("table")

    if any(x in lower for x in ["схема","diagram"]):
        reps.append("diagram")

    if any(x in lower for x in ["формула","уравнение"]):
        reps.append("formula")

    # Do not force text as a representation.
    # Empty means Executor decides from full context.
    if not reps:
        return []

    return reps

DISCUSSION_WORDS = [
    "поговорим","обсудим","как думаешь","мнение",
    "рассуждение","рассуждаем","объясни","почему"
]

ACTION_WORDS = [
    "создай","сделай","построй","отрендери",
    "нарисуй","покажи","сгенерируй"
]

# =====================================================
# RU-43 Semantic Dictionaries
# =====================================================
LIGHTWEIGHT_VISUAL_WORDS=("покажи","визуализируй","иллюстрация","пример","схема")
RENDERER_WORDS=("renderer","scene","graph","diagram","table","formula","график","таблица","формула","схема")
MATH_WORDS=("математика","формула","уравнение","интеграл","производная")
WEB_WORDS=("поиск","найди","интернет","сайт")
CODE_WORDS=("python","javascript","typescript","код")
CONTINUATION_WORDS=("продолжай","дальше","продолжение")
EXPLORATION_WORDS=("исследуй","сравни","проанализируй")
EXPLICIT_IMAGE_WORDS=("нарисуй","создай изображение","сгенерируй изображение")
INFORMATIONAL_WORDS=("что","почему","как","объясни")

def detect_discussion_mode(text):
    return contains_any(
        normalize_lower(text),
        DISCUSSION_WORDS
    )

def detect_space_discussion(text):
    lower = normalize_lower(text)
    return (
        contains_any(lower, ["пространство","scene","renderer","render","блок"])
        and detect_discussion_mode(lower)
    )

def semantic_evidence_math(text):
    return contains_any(
        normalize_lower(text),
        MATH_WORDS
    )

def semantic_evidence_renderer(
    text
):

    lower = normalize_lower(text)

    has_renderer_topic = contains_any(
        lower,
        RENDERER_WORDS
    )

    has_action = contains_any(
        lower,
        ACTION_WORDS
    )

    if detect_space_discussion(lower):
        return False

    return has_renderer_topic and has_action

def detect_lightweight_visual(text):
    ensure_semantic_constants()
    return contains_any(normalize_lower(text), LIGHTWEIGHT_VISUAL_WORDS)

def semantic_evidence_image(
    text
):

    return contains_any(
        normalize_lower(text),
        EXPLICIT_IMAGE_WORDS
    )

def semantic_evidence_exploration(
    text
):

    return contains_any(
        normalize_lower(text),
        EXPLORATION_WORDS
    )

def semantic_evidence_continuation(
    text
):

    return contains_any(
        normalize_lower(text),
        CONTINUATION_WORDS
    )

def semantic_evidence_web(text):
    return contains_any(
        normalize_lower(text),
        WEB_WORDS
    )

def semantic_evidence_code(
    text
):

    return contains_any(
        normalize_lower(text),
        CODE_WORDS
    )

def semantic_evidence_information(
    text
):

    return contains_any(
        normalize_lower(text),
        INFORMATIONAL_WORDS
    )

def detect_scene_type(
    text,
    cognition=None
):

    cognition = cognition or {}

    lower = normalize_lower(
        text
    )

    # =================================================
    # 🔥 COGNITION PRIORITY
    # =====================================================

    if cognition.get(
        "prefer_renderer"
    ):

        if (
            "график" in lower
            or "plot" in lower
            or "graph" in lower
        ):

            return "graph"

        if (
            "формула" in lower
            or "equation" in lower
        ):

            return "formula"

        if (
            "таблица" in lower
            or "table" in lower
        ):

            return "table"

        return "scene"

    # =================================================
    # 🔥 SAFE SEMANTIC FALLBACK
    # =====================================================

    if semantic_evidence_renderer(
        lower
    ):

        if (
            "график" in lower
            or "plot" in lower
            or "graph" in lower
        ):

            return "graph"

        if (
            "формула" in lower
            or "equation" in lower
        ):

            return "formula"

        if (
            "таблица" in lower
            or "table" in lower
        ):

            return "table"

        return "scene"

    return None

def build_result(
    text
):

    return {

        # =================================================
        # 🔥 CORE
        # =====================================================

        "type":
            "text",

        "subtype":
            None,

        "scene_type":
            None,

        "normalized":
            text,

        # =================================================
        # 🔥 SCENE COMPOSITION HINTS
        # =====================================================

        "content_role":
            None,

        "contains_object":
            False,

        "contains_explanation":
            False,

        "contains_analysis":
            False,

        "contains_legend":
            False,

        "scene_composition_ready":
            True,

        # =================================================
        # 🔥 SEMANTIC HINTS
        # =====================================================

        "renderer_intent":
            False,

        "discussion_mode":
            False,

        "space_discussion":
            False,

        "lightweight_visual":
            False,

        "exploration":
            False,

        "continuation":
            False,

        "web_context":
            False,

        "explicit_image_generation":
            False,

        # =================================================
        # 🔥 COGNITION COOPERATION
        # =====================================================

        "cognition_assisted":
            True,

        "continuity_aware":
            True,

        "scene_aware":
            True,

        "supports_executor":
            True,

        # =================================================
        # 🔥 ORCHESTRATION
        # =====================================================

        "prefer_renderer":
            False,

        "prefer_guidance":
            False,

        "prefer_execution":
            False,

        "prefer_continuation":
            False,

        "active_topic_slot":
            None,

        "topic_continuity":
            False,

        # =================================================
        # 🔥 SAFETY
        # =====================================================

        "avoid_force_generation":
            True,

        "avoid_hidden_escalation":
            True,

        "avoid_telegram_behavior":
            True,

        "avoid_trigger_execution":
            True,

        "provider_safe":
            True,

        "renderer_first":
            True,

        # =================================================
        # 🔥 MACHINE FLAGS
        # =====================================================

        "machine_only":
            True,

        "semantic_bridge":
            True,

        "orchestration_safe":
            True,

        "continuity_preserved":
            True,

        "required_domains": [],
        "candidate_domains": [],
        "required_representations": [],
        "candidate_representations": [],
        "domain_confidence": {},
        "response_complexity": None,
        "estimated_action_count": 0
    }

def detect_explanation_content(text):

    lower = normalize_lower(text)

    markers = [
        "объясни",
        "объяснение",
        "пояснение",
        "расшифровка",
        "что означает",
        "что значит"
    ]

    return contains_any(lower, markers)

def detect_analysis_content(text):

    lower = normalize_lower(text)

    markers = [
        "анализ",
        "вывод",
        "заключение",
        "интерпретация"
    ]

    return contains_any(lower, markers)

def detect_legend_content(text):

    lower = normalize_lower(text)

    markers = [
        "обозначение",
        "обозначения",
        "легенда",
        "расшифровка"
    ]

    return contains_any(lower, markers)

def detect_object_content(text):

    return (
        semantic_evidence_information(text) or semantic_evidence_code(text) or semantic_evidence_renderer(text)
        or semantic_evidence_renderer(text)
    )

def build_domain_confidence(text):

    candidates = detect_domain_candidates(text)

    confidence = {}

    for domain in candidates:
        confidence[domain] = 0.85

    return confidence

DOMAIN_ROOM_MAP = {
    "biology": ["biology"],
    "chemistry": ["chemistry"],
    "physics": ["physics"],
    "engineering": ["engineering"],
    "it": ["it"],
    "literature": ["literature"],
    "politics": ["politics"],
    "news": ["news"],
    "social": ["social"],
    "web": ["web"]
}

def build_factory_order(result):

    required_domains = result.get(
        "required_domains",
        []
    )

    required_rooms = []

    for domain in required_domains:

        required_rooms.extend(
            DOMAIN_ROOM_MAP.get(
                domain,
                []
            )
        )

    return {

        "intent":
            result.get("type"),

        "goal":
            result.get("subtype"),

        "required_domains":
            required_domains,

        "required_rooms":
            list(set(required_rooms)),

        "required_artifacts":
            required_domains,

        "quality_target":
            0.95
    }

def build_scene_strategy(result):

    role = result.get(
        "content_role"
    )

    reps = result.get(
        "required_representations",
        []
    )

    strategy = {

        "scene_strategy":
            "default",

        "preferred_blocks":
            ["text"],

        "scene_priority":
            "normal",

        "scene_contribution_mode":
            True,

        "scene_builder_profile":
            "generic"
    }

    if role == "explanation":

        strategy.update({

            "scene_strategy":
                "knowledge_explanation",

            "preferred_blocks": [
                "knowledge_card",
                "relations",
                "resources"
            ],

            "scene_priority":
                "high",

            "scene_builder_profile":
                "knowledge"
        })

    elif role == "analysis":

        strategy.update({

            "scene_strategy":
                "analysis",

            "preferred_blocks": [
                "summary",
                "table",
                "resources"
            ],

            "scene_builder_profile":
                "analysis"
        })

    elif "graph" in reps:

        strategy.update({

            "scene_strategy":
                "knowledge_graph",

            "preferred_blocks": [
                "graph",
                "relations",
                "summary"
            ],

            "scene_builder_profile":
                "graph"
        })

    elif "table" in reps:

        strategy.update({

            "scene_strategy":
                "comparison",

            "preferred_blocks": [
                "table",
                "summary"
            ],

            "scene_builder_profile":
                "comparison"
        })

    return strategy

RESPONSE_COMPLEXITY_LOW = "LOW"
RESPONSE_COMPLEXITY_MEDIUM = "MEDIUM"
RESPONSE_COMPLEXITY_HIGH = "HIGH"

def estimate_action_count(result):
    """
    Stage 1.

    Infrastructure only.

    Real calculation will be connected
    during Stage 2.
    """
    return 1

def determine_response_complexity(result):
    actions = estimate_action_count(result)

    if actions <= 1:
        return RESPONSE_COMPLEXITY_LOW

    if actions <= 3:
        return RESPONSE_COMPLEXITY_MEDIUM

    return RESPONSE_COMPLEXITY_HIGH

# RU-43: removed duplicate stub override

def interpret_request(
    text: str,
    cognition: dict = None,
    semantic: dict = None
):

    text = normalize_text(
        text
    )

    cognition = cognition or {}

    semantic = semantic or {}

    # =====================================================
    # 🧠 TOPIC MEMORY INPUT
    # =====================================================

    active_topic_slot = cognition.get(
        "active_topic_slot"
    )

    continuity_context_storage = cognition.get(
        "continuity_context_storage",
        []
    )

    memory_anchor_storage = cognition.get(
        "memory_anchor_storage",
        []
    )

    if not text:

        safe_patch_log(
            "EMPTY REQUEST"
        )

        return None

    t = normalize_lower(
        text
    )

    result = build_result(
        text
    )

    # =====================================================
    # 🧠 TEST 2 — SEMANTIC-FIRST PIPELINE
    # =====================================================
    semantic_profile = build_semantic_dialog_profile(text, cognition)
    scene_profile = build_scene_construction_profile(semantic_profile)
    artifact_contract = build_scene_artifact_contract(
        semantic_profile,
        scene_profile
    )
    execution_plan = build_scene_execution_plan(
        semantic_profile,
        scene_profile,
        artifact_contract
    )

    state = build_interpretation_state()
    state["dialogue"]["semantic_profile"] = semantic_profile
    result["semantic_profile"] = semantic_profile
    result["scene_profile"] = scene_profile
    result["artifact_contract"] = artifact_contract
    result["canonical_transport"] = "transport_state"
    result["execution_plan"] = execution_plan

    # TEST 3
    # Semantic pipeline becomes authoritative.
    result["semantic_authority"] = True
    result["compatibility_mode"] = "isolated_compatibility"

    # TEST 4
    # Canonical semantic route.
    result["canonical_interpretation_route"] = list(INTERPRETATION_ROUTE)

    
    
    

    # TEST 5
    # Dialogue interpreter is the canonical source of intent.
    result["dialogue_interpreter_mode"] = "professional"

    # TEST 8
    result["dialogue_memory_mode"] = "semantic_continuity"
    result["dialogue_vector_source"] = "conversation_history"
    result["scene_decision_source"] = "semantic_profiles"
    result["artifact_selection_mode"] = "capability_matching"

    result["capability_registry"] = {
        "graph":"graph_room",
        "table":"table_room",
        "diagram":"diagram_room",
        "formula":"formula_room",
        "gallery":"gallery_room",
        "text":"knowledge_room"
    }

    # TEST 9
    result["dialogue_understanding_mode"] = "contextual_semantic"
    result["intent_continuity_mode"] = "multi_turn"
    result["dialogue_vector_mode"] = "goal_and_history"
    result["scene_resolution_mode"] = "artifact_first"

    result["semantic_signal_priority"] = [
        "conversation_history",
        "active_goal",
        "semantic_profile",
        "scene_profile",
        "artifact_contract"
    ]

    # TEST 10
    result["dialogue_reasoning_pipeline"] = [
        "dialogue_history",
        "user_goal",
        "semantic_analysis",
        "scene_selection",
        "artifact_contract",
        "executor_contract"
    ]

    # TEST 11
    result["dialogue_trajectory_mode"] = "predictive_assistance"

    result["trajectory_analysis"] = {
        "history_weight": 0.45,
        "current_goal_weight": 0.35,
        "semantic_flow_weight": 0.20,
        "allow_prediction": True,
        "prediction_confidence_threshold": 0.80,
        "prediction_is_suggestion": True
    }

    result["candidate_next_intents"] = []

    # TEST 12
    result["professional_orientation_mode"] = "adaptive"

    result["dialogue_profile"] = {
        "estimated_domain": None,
        "estimated_experience": None,
        "confidence": 0.0,
        "evidence": []
    }

    result["orientation_signals"] = [
        "conversation_history",
        "active_goal",
        "domain_vocabulary",
        "artifact_preferences",
        "question_depth",
        "interaction_pattern"
    ]

    result["tool_selection_strategy"] = {
        "prefer_professional_rendering": True,
        "expand_visualization_for_domain": True,
        "adapt_scene_complexity": True,
        "never_assume_identity": True,
        "treat_orientation_as_hypothesis": True
    }

    # TEST 13
    result["semantic_library_registry"] = {
        "dialogue_reasoning": "semantic_dialogue_library",
        "intent_model": "intent_reasoning_library",
        "history_analysis": "conversation_history_library",
        "trajectory_analysis": "dialogue_trajectory_library",
        "domain_profiler": "domain_orientation_library",
        "artifact_planner": "artifact_planning_library",
        "scene_planner": "scene_planning_library",
        "tool_orchestrator": "capability_orchestrator_library"
    }

    result["professional_render_policy"] = {
        "domain_adaptation": True,
        "context_expansion": True,
        "cross_reference_history": True,
        "multi_artifact_planning": True,
        "semantic_first": True
    }

    result["planned_optional_libraries"] = [
        "knowledge_graph",
        "ontology_engine",
        "concept_mapper",
        "dialogue_memory_index",
        "artifact_recommender"
    ]

    # TEST 14
    result["dialogue_direction_engine"] = {
        "enabled": True,
        "history_analysis": True,
        "goal_tracking": True,
        "topic_transition_tracking": True,
        "professional_context_tracking": True,
        "representation_prediction": True,
        "tool_preplanning": True
    }

    result["dialogue_direction_profile"] = {
        "current_topic": None,
        "emerging_topics": [],
        "goal_vector": None,
        "domain_vector": [],
        "recommended_rooms": [],
        "recommended_artifacts": [],
        "recommended_renderers": [],
        "confidence": 0.0
    }

    result["professional_reasoning_mode"] = "incremental_evidence"

    # TEST 15
    result["semantic_dialogue_graph"] = {
        "enabled": True,
        "topic_nodes": [],
        "concept_nodes": [],
        "goal_nodes": [],
        "artifact_nodes": [],
        "room_nodes": [],
        "edges": [],
        "active_focus": None
    }

    result["context_accumulation_policy"] = {
        "preserve_history": True,
        "merge_repeated_topics": True,
        "track_goal_evolution": True,
        "track_domain_evolution": True,
        "prefer_long_term_context": True
    }

    result["adaptive_response_planner"] = {
        "expand_when_confident": True,
        "recommend_visualization": True,
        "recommend_tables": True,
        "recommend_graphs": True,
        "recommend_formulas": True,
        "recommend_comparisons": True
    }

    result["professional_capability_prediction"] = {
        "candidate_capabilities": [],
        "candidate_rooms": [],
        "candidate_renderers": [],
        "selection_reasoning": [],
        "confidence": 0.0
    }

    # TEST 16
    result["dialogue_cognition_matrix"] = {
        "conversation_vector": [],
        "goal_vector": [],
        "knowledge_vector": [],
        "representation_vector": [],
        "tool_vector": [],
        "domain_vector": [],
        "continuity_score": 0.0
    }

    result["semantic_evidence_engine"] = {
        "dispatcher": "semantic_evidence_dispatch",
        "mode": "incremental_evidence",
        "legacy_input": "isolated",
        "enabled": True,
        "history_evidence": [],
        "goal_evidence": [],
        "domain_evidence": [],
        "concept_evidence": [],
        "representation_evidence": [],
        "artifact_evidence": []
    }

    result["executor_preparation_contract"] = {
        "context_schema": "INTERPRETATION_CONTEXT_SCHEMA",
        "state_source": "interpretation_state",
        "predicted_rooms": [],
        "predicted_tools": [],
        "predicted_scene": None,
        "predicted_artifacts": [],
        "prediction_confidence": 0.0,
        "requires_confirmation": False
    }

    result["cross_domain_reasoning"] = {
        "enabled": True,
        "related_domains": [],
        "bridge_concepts": [],
        "comparison_candidates": []
    }

    # TEST 17
    result["semantic_hypothesis_engine"] = {
        "enabled": True,
        "active_hypotheses": [],
        "rejected_hypotheses": [],
        "supporting_evidence": {},
        "confidence_threshold": 0.75
    }

    result["dialogue_state_tracker"] = {
        "topic_history": [],
        "goal_history": [],
        "representation_history": [],
        "room_history": [],
        "context_transitions": []
    }

    result["artifact_prediction_matrix"] = {
        "text": 0.0,
        "table": 0.0,
        "graph": 0.0,
        "diagram": 0.0,
        "formula": 0.0,
        "gallery": 0.0
    }

    result["semantic_quality_contract"] = {
        "require_evidence": True,
        "require_context_consistency": True,
        "require_history_consistency": True,
        "avoid_single_signal_decision": True
    }

    result["representation_resolution"] = "library_dispatch"

    result["semantic_decision_source"] = "semantic_pipeline"

    # TEST 6
    result["scene_contract_mode"] = "executor_ready"
    result["executor_contract_mode"] = "semantic_only"
    result["representation_library"] = {
        "graph": "graph_scene_library",
        "table": "table_scene_library",
        "diagram": "diagram_scene_library",
        "formula": "formula_scene_library",
        "gallery": "gallery_scene_library",
        "text": "knowledge_scene_library"
    }

    result["scene_library_registry"] = {
        "graph": ["axes","series","legend","graph_renderer"],
        "table": ["columns","rows","comparison","table_renderer"],
        "diagram": ["nodes","edges","layout","diagram_renderer"],
        "formula": ["latex","math_context","formula_renderer"],
        "gallery": ["images","captions","gallery_renderer"],
        "text": ["sections","citations","knowledge_renderer"]
    }

    result["legacy_keyword_matching"] = None

    domain_candidates = detect_domain_candidates(t)
    representation_candidates = detect_representation_candidates(t)

    result["candidate_domains"] = domain_candidates
    result["required_domains"] = list(domain_candidates)
    result["domain_confidence"] = build_domain_confidence(t)

    result["candidate_representations"] = representation_candidates
    result["required_representations"] = list(representation_candidates)

    # Preserve machine understanding coming from previous layers.
    semantic_reps = semantic.get("required_representations", []) or []
    cognition_reps = cognition.get("required_representations", []) or []

    for rep in semantic_reps + cognition_reps:
        if rep not in result["required_representations"]:
            result["required_representations"].append(rep)
        if rep not in result["candidate_representations"]:
            result["candidate_representations"].append(rep)

    # Stage: Executor owns routing; interpretation provides only understanding.
    result["factory_order"] = {}
    safe_patch_log("FACTORY ORDER DEFERRED TO EXECUTOR")

    if detect_discussion_mode(t):
        result["discussion_mode"] = True
        result["prefer_guidance"] = True

    if detect_space_discussion(t):
        result["space_discussion"] = True

    # =====================================================
    # 🔥 CONTINUATION
    # =====================================================

    if (
        semantic_evidence_continuation(t)
        or cognition.get(
            "needs_continuation"
        )
    ):

        result[
            "continuation"
        ] = True

        result[
            "prefer_continuation"
        ] = True

        safe_patch_log(
            "CONTINUATION DETECTED"
        )

    # =====================================================
    # 🔥 EXPLORATION
    # =====================================================

    if (
        semantic_evidence_exploration(t)
        or cognition.get(
            "exploration_mode"
        )
    ):

        result[
            "exploration"
        ] = True

        result[
            "lightweight_visual"
        ] = True

        safe_patch_log(
            "EXPLORATION MODE"
        )

    # =====================================================
    # 🔥 WEB
    # =====================================================

    if (
        semantic_evidence_information(text) or semantic_evidence_code(text) or semantic_evidence_renderer(text)
        or cognition.get(
            "internet_context_needed"
        )
    ):

        result[
            "web_context"
        ] = True

        result[
            "prefer_guidance"
        ] = True

        result[
            "subtype"
        ] = "web"

        safe_patch_log(
            "WEB CONTEXT DETECTED"
        )

    # =====================================================
    # 🔥 IMAGE GENERATION
    # =====================================================

    if semantic_evidence_image(
        t
    ):

        result[
            "type"
        ] = "image"

        result[
            "subtype"
        ] = "generation"

        result[
            "explicit_image_generation"
        ] = True

        safe_patch_log(
            "EXPLICIT IMAGE GENERATION"
        )

    # =====================================================
    # 🔥 COGNITION-FIRST RENDERER
    # =====================================================

    elif (

        cognition.get(
            "prefer_renderer"
        )

        or cognition.get(
            "renderer_space_active"
        )

        or scene_profile.get("requires_scene_builder")
        or (
            not scene_profile.get("requires_scene_builder")
            and semantic_evidence_renderer(t)
        )
    ):

        result[
            "renderer_intent"
        ] = True

        result[
            "prefer_renderer"
        ] = True

        result[
            "type"
        ] = "render"

        scene_type = detect_scene_type(
            t,
            cognition
        )

        result[
            "scene_type"
        ] = scene_type

        result[
            "subtype"
        ] = scene_type

        safe_patch_log(
            f"RENDERER MODE: {scene_type}"
        )

    # =====================================================
    # 🔥 MATH
    # =====================================================

    elif (

        semantic_evidence_information(text) or semantic_evidence_code(text) or semantic_evidence_renderer(text)

        or cognition.get(
            "math_reasoning"
        )
    ):

        result[
            "type"
        ] = "math"

        result[
            "subtype"
        ] = "graph"

        result[
            "renderer_intent"
        ] = True

        result[
            "prefer_renderer"
        ] = True

        safe_patch_log(
            "MATH INTERPRETATION"
        )

    # =====================================================
    # 🔥 CODE
    # =====================================================

    elif semantic_evidence_code(
        t
    ):

        result[
            "type"
        ] = "code"

        result[
            "subtype"
        ] = "implementation"

        result[
            "prefer_execution"
        ] = True

        safe_patch_log(
            "CODE REQUEST"
        )

    # =====================================================
    # 🔥 INFORMATIONAL
    # =====================================================

    elif (

        semantic_evidence_information(
            t
        )

        or cognition.get(
            "needs_guidance"
        )
    ):

        result[
            "type"
        ] = "text"

        result[
            "subtype"
        ] = "guidance"

        result[
            "prefer_guidance"
        ] = True

        safe_patch_log(
            "GUIDANCE REQUEST"
        )

    # =====================================================
    # 🔥 LIGHTWEIGHT VISUALS
    # =====================================================

    if (
        detect_lightweight_visual(
            t
        )

        or cognition.get(
            "visual_reference_mode"
        )
    ):

        result[
            "lightweight_visual"
        ] = True

        safe_patch_log(
            "LIGHTWEIGHT VISUAL MODE"
        )

    # =====================================================
    # 🔥 CONTINUITY STABILIZATION
    # =====================================================

    if cognition.get(
        "tracks_multiple_topics"
    ):

        result[
            "continuity_aware"
        ] = True

    if cognition.get(
        "avoid_topic_loss"
    ):

        result[
            "scene_aware"
        ] = True

    # =====================================================
    # 🧠 TOPIC CONTINUITY SUPPORT
    # =====================================================

    if continuity_context_storage:

        result[
            "continuation"
        ] = True

        result[
            "topic_continuity"
        ] = True

    if memory_anchor_storage:

        result[
            "continuity_aware"
        ] = True

    if active_topic_slot:

        result[
            "active_topic_slot"
        ] = active_topic_slot

    # =====================================================
    # 🔥 SCENE COMPOSITION HINTS
    # =====================================================

    if detect_object_content(t):

        result["contains_object"] = True

    if detect_explanation_content(t):

        result["contains_explanation"] = True
        result["content_role"] = "explanation"

    if detect_analysis_content(t):

        result["contains_analysis"] = True

        if not result.get("content_role"):
            result["content_role"] = "analysis"

    if detect_legend_content(t):

        result["contains_legend"] = True

        if not result.get("content_role"):
            result["content_role"] = "legend"


    # =====================================================
    # 🔥 RESPONSE COMPLEXITY (Stage 2)
    # =====================================================

    result["estimated_action_count"] = estimate_action_count(result)
    result["response_complexity"] = determine_response_complexity(result)

    # Semantic scene construction is now preferred.
    result["scene_representation"] = result["representation_library"].get(
        result.get("scene_type") or "text"
    )

    result["scene_strategy"] = build_scene_strategy(
        result
    )

    # =====================================================
    # 🔥 FINAL STABILIZATION
    # =====================================================

    if result.get(
        "prefer_renderer"
    ):

        result[
            "avoid_force_generation"
        ] = True

        result[
            "explicit_image_generation"
        ] = False

    # =====================================================
    # 🔥 EXECUTION STABILIZATION
    # =====================================================

    if cognition.get(
        "prefer_execution"
    ):

        result[
            "prefer_execution"
        ] = True

    # =====================================================
    # 🔥 OUTPUT LOG
    # =====================================================

    safe_patch_log(

        f"INTERPRETATION COMPLETE | "
        f"type={result.get('type')} | "
        f"subtype={result.get('subtype')} | "
        f"complexity={result.get('response_complexity')}"
    )

    # Stage 3
    # Transport fields prepared for downstream layers.
    result["semantic_response_complexity"] = result["response_complexity"]
    result["machine_response_complexity"] = result["response_complexity"]

    # =====================================================
    # 🔥 FINAL
    # =====================================================

    result = validate_response_complexity(result)
    state = ensure_transport_defaults(state)
    state = synchronize_interpretation_context(state, result)
    route = build_interpretation_route(state, result)
    result["interpretation_route"] = route
    state = export_transport_state(state, result)
    result["transport_state"] = state
    result["primary_contract"] = "transport_state"
    result["interpretation_state"] = state
    result["transport_diagnostics"]=build_transport_diagnostics(result)
    result = propagate_canonical_response(result, state)
    result = bridge_machine_response(result, state)

    return result


# =====================================================
# RU-45
# Canonical transport propagation
# =====================================================

def propagate_canonical_response(result, state):
    result = result or {}
    state = state or {}

    transport = state.setdefault("transport", {})
    response = transport.setdefault("response", {})

    response["content"] = safe_result_get(result,"normalized") or safe_result_get(result,"assistant_response","")

    result["transport_state"] = state
    return result



# =====================================================
# RU-46
# Safe semantic accessors
# =====================================================

def safe_result_get(result, key, default=None):
    if not isinstance(result, dict):
        return default
    value = result.get(key, default)
    return default if value is None else value

def ensure_transport_defaults(state):
    state = state or {}
    state.setdefault("dialogue", {})
    state.setdefault("scene", {})
    state.setdefault("executor", {})
    state.setdefault("artifacts", {})
    state.setdefault("diagnostics", {})
    return state



# =====================================================
# RU-47
# MachineResponse / SceneContract bridge
# =====================================================

def bridge_machine_response(result, state):
    result = result or {}
    state = state or {}

    machine = state.setdefault("machine_response", {})
    scene = state.setdefault("scene_contract", {})

    content = (
        machine.get("content")
        or result.get("normalized")
        or result.get("assistant_response")
        or ""
    )

    machine["content"] = content
    scene["content"] = content
    scene["answer"] = content
    scene["summary"] = content

    result["machine_response"] = machine
    result["scene_contract"] = scene
    return result


def export_response_complexity(result):
    return {
        "response_complexity": result.get("response_complexity"),
        "estimated_action_count": result.get("estimated_action_count"),
        "semantic_response_complexity": result.get("semantic_response_complexity"),
        "machine_response_complexity": result.get("machine_response_complexity"),
    }

def validate_response_complexity(result):
    if result.get("response_complexity") is None:
        result["response_complexity"] = RESPONSE_COMPLEXITY_LOW
    if result.get("estimated_action_count") is None:
        result["estimated_action_count"] = 0
    return result



# =====================================================
# TEST 31
# Semantic Dialogue Profile
# =====================================================

def build_semantic_dialog_profile(
    text,
    cognition=None,
    semantic=None,
    assistant_response=None,
    dialogue_history=None,
    vision_context=None
):
    cognition = cognition or {}
    semantic = semantic or {}

    return {
        "input_text": text,
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or [],
        "vision_context": vision_context or {},
        "active_goal": cognition.get("active_goal"),
        "active_topic": cognition.get("active_topic_slot"),
        "semantic_state": semantic,
        "requires_scene_builder": False,
        "profile_version": "test31"
    }


# =====================================================
# TEST 32
# Scene Construction Profile
# =====================================================

def build_scene_construction_profile(semantic_profile):
    semantic_profile = semantic_profile or {}

    return {
        "requires_scene_builder": bool(
            semantic_profile.get("vision_context")
            or semantic_profile.get("active_goal")
        ),
        "scene_type": "dialogue",
        "dialogue_mode": "semantic_unified",
        "context_source": "semantic_profile",
        "profile_version": "test32"
    }


# =====================================================
# TEST 33
# Unified Artifact Contract
# No new routes. Uses the existing semantic pipeline.
# =====================================================

def build_scene_artifact_contract(
    semantic_profile,
    scene_profile
):
    semantic_profile = semantic_profile or {}
    scene_profile = scene_profile or {}

    return {
        "contract": "scene_artifact",
        "transport": "transport_state",
        "semantic_profile": semantic_profile,
        "scene_profile": scene_profile,
        "dialogue_history": semantic_profile.get("dialogue_history", []),
        "assistant_response": semantic_profile.get("assistant_response"),
        "active_goal": semantic_profile.get("active_goal"),
        "scene_type": scene_profile.get("scene_type", "dialogue"),
        "representation": "executor_decides",
        "profile_version": "test33"
    }


# =====================================================
# TEST 34
# Unified Scene Context
# Single semantic route (no new transport)
# =====================================================

def build_unified_scene_context(
    semantic_profile,
    scene_profile,
    artifact_contract,
    voice_context=None,
    vision_context=None,
    gallery_context=None,
    file_context=None,
    assistant_response=None,
    dialogue_history=None,
    memory_state=None,
):
    semantic_profile = semantic_profile or {}
    scene_profile = scene_profile or {}
    artifact_contract = artifact_contract or {}

    return {
        "semantic_profile": semantic_profile,
        "scene_profile": scene_profile,
        "artifact_contract": artifact_contract,
        "voice_context": voice_context or {},
        "vision_context": vision_context or {},
        "gallery_context": gallery_context or {},
        "file_context": file_context or {},
        "assistant_response": assistant_response,
        "dialogue_history": dialogue_history or semantic_profile.get("dialogue_history", []),
        "active_goal": semantic_profile.get("active_goal"),
        "active_scene": scene_profile.get("scene_type", "dialogue"),
        "memory_state": memory_state or {},
        "continuity_state": {
            "single_route": True,
            "transport": "transport_state",
            "scene_contract": "canonical"
        },
        "profile_version": "test34"
    }


# =====================================================
# TEST 35
# Execution Plan
# Uses UnifiedSceneContext. No new routes.
# =====================================================

def build_scene_execution_plan(
    semantic_profile,
    scene_profile,
    artifact_contract,
    unified_scene_context=None
):
    semantic_profile = semantic_profile or {}
    scene_profile = scene_profile or {}
    artifact_contract = artifact_contract or {}

    if unified_scene_context is None:
        unified_scene_context = build_unified_scene_context(
            semantic_profile,
            scene_profile,
            artifact_contract
        )

    return {
        "transport": "transport_state",
        "scene_contract": "canonical",
        "scene_context": unified_scene_context,
        "scene_type": scene_profile.get("scene_type", "dialogue"),
        "representation": artifact_contract.get("representation", "executor_decides"),
        "execution_mode": "single_semantic_pipeline",
        "profile_version": "test35"
    }


# =====================================================
# TEST 36
# Unified Interpretation Inputs
# Single scene understanding for all modalities.
# =====================================================

UNIFIED_DIALOGUE_INPUTS = (
    "user_text",
    "user_voice",
    "user_files",
    "user_images",
    "user_gallery",
    "assistant_response",
    "dialogue_history",
    "memory_state",
    "active_goal",
    "active_scene",
)

def build_unified_interpretation_state(
    scene_context,
    processor_state=None
):
    scene_context = scene_context or {}
    processor_state = processor_state or {}

    return {
        "transport": "transport_state",
        "scene_context": scene_context,
        "processor_state": processor_state,
        "dialogue_vector": scene_context.get("dialogue_history", []),
        "assistant_response": scene_context.get("assistant_response"),
        "voice_context": scene_context.get("voice_context", {}),
        "vision_context": scene_context.get("vision_context", {}),
        "gallery_context": scene_context.get("gallery_context", {}),
        "file_context": scene_context.get("file_context", {}),
        "active_goal": scene_context.get("active_goal"),
        "active_scene": scene_context.get("active_scene"),
        "executor_mode": "single_scene_contract",
        "profile_version": "test36",
    }


# =====================================================
# TEST 37
# Unified Semantic Processor State
# Canonical interpretation for processor/executor.
# =====================================================

def build_semantic_processor_state(
    interpretation_state,
    execution_plan=None
):
    interpretation_state = interpretation_state or {}
    execution_plan = execution_plan or {}

    return {
        "transport": "transport_state",
        "processor_contract": "canonical",
        "interpretation_state": interpretation_state,
        "execution_plan": execution_plan,
        "semantic_inputs": {
            "text": interpretation_state.get("scene_context", {}).get("semantic_profile", {}).get("input_text"),
            "voice": interpretation_state.get("voice_context", {}),
            "images": interpretation_state.get("vision_context", {}),
            "gallery": interpretation_state.get("gallery_context", {}),
            "files": interpretation_state.get("file_context", {}),
            "assistant": interpretation_state.get("assistant_response"),
            "history": interpretation_state.get("dialogue_vector", []),
        },
        "scene_understanding": {
            "active_scene": interpretation_state.get("active_scene"),
            "active_goal": interpretation_state.get("active_goal"),
            "continuity": True,
            "single_route": True,
        },
        "profile_version": "test37"
    }


# =====================================================
# TEST 38
# Dialogue Understanding Core
# Unified processor response context.
# =====================================================

def build_dialogue_understanding_core(
    processor_state,
    executor_state=None
):
    processor_state = processor_state or {}
    executor_state = executor_state or {}

    semantic_inputs = processor_state.get("semantic_inputs", {})

    return {
        "transport": "transport_state",
        "dialogue_understanding": {
            "user_text": semantic_inputs.get("text"),
            "voice": semantic_inputs.get("voice"),
            "images": semantic_inputs.get("images"),
            "gallery": semantic_inputs.get("gallery"),
            "files": semantic_inputs.get("files"),
            "assistant_response": semantic_inputs.get("assistant"),
            "dialogue_history": semantic_inputs.get("history", []),
            "scene_understanding": processor_state.get("scene_understanding", {}),
        },
        "processor_reasoning": {
            "single_scene": True,
            "history_aware": True,
            "response_context": True,
            "executor_shared_context": executor_state,
        },
        "profile_version": "test38"
    }


# =====================================================
# TEST 38.1
# Dialogue Optimization Layer
# Extends Test 38 without introducing new routes.
# =====================================================

SEMANTIC_EVIDENCE_PRIORITY = (
    "active_goal",
    "assistant_response",
    "dialogue_history",
    "voice_context",
    "vision_context",
    "gallery_context",
    "file_context",
    "semantic_profile",
)

def optimize_dialogue_understanding(dialogue_core):
    dialogue_core = dialogue_core or {}

    understanding = dialogue_core.get("dialogue_understanding", {})

    return {
        "transport": "transport_state",
        "dialogue_understanding": understanding,
        "optimization": {
            "semantic_priority": list(SEMANTIC_EVIDENCE_PRIORITY),
            "history_weight": 0.40,
            "assistant_weight": 0.20,
            "goal_weight": 0.25,
            "multimodal_weight": 0.15,
            "response_continuity": True,
            "scene_consistency": True,
            "executor_alignment": True,
            "processor_alignment": True,
        },
        "canonical_reasoning": {
            "single_scene": True,
            "single_contract": True,
            "single_transport": True,
            "reuse_previous_answer": True,
            "preserve_dialogue_vector": True,
        },
        "profile_version": "test38.1"
    }


# =====================================================
# TEST 38.2
# Legacy Trigger Isolation
# Removes legacy influence from semantic reasoning.
# =====================================================

LEGACY_TRIGGER_FLAGS = ()

def build_semantic_interpretation_contract(dialogue_optimization):
    dialogue_optimization = dialogue_optimization or {}

    return {
        "transport": "transport_state",
        "semantic_contract": {
            "mode": "canonical_semantic",
            "compatibility_isolated": True,
            "single_scene": True,
            "single_dialogue": True,
            "single_processor": True,
            "single_executor": True,
        },
        "disabled_legacy_flags": list(LEGACY_TRIGGER_FLAGS),
        "dialogue_optimization": dialogue_optimization,
        "reasoning_policy": {
            "history_first": True,
            "assistant_context": True,
            "goal_driven": True,
            "multimodal_fusion": True,
            "trigger_independent": True,
            "scene_continuity": True,
        },
        "profile_version": "test38.2"
    }


# =====================================================
# TEST 39
# Canonical Semantic Runtime
# Replaces remaining descriptive placeholders with code.
# =====================================================

CANONICAL_SEMANTIC_RUNTIME = {
    "transport":"transport_state",
    "reasoning":"semantic_only",
    "legacy_trigger_execution":False,
    "single_scene":True,
    "single_processor":True,
    "single_executor":True,
}

def build_canonical_semantic_runtime(
    semantic_contract,
    processor_state,
    dialogue_core
):
    semantic_contract = semantic_contract or {}
    processor_state = processor_state or {}
    dialogue_core = dialogue_core or {}

    dialogue = dialogue_core.get("dialogue_understanding", {})
    optimization = semantic_contract.get("reasoning_policy", {})

    runtime = {
        "transport":"transport_state",
        "scene": dialogue.get("scene_understanding", {}),
        "dialogue": dialogue,
        "processor": processor_state,
        "reasoning_policy": optimization,
        "continuity_vector":{
            "history": dialogue.get("dialogue_history", []),
            "assistant": dialogue.get("assistant_response"),
            "goal": dialogue.get("scene_understanding",{}).get("active_goal"),
        },
        "compatibility":{
            "enabled": False,
            "trigger_execution": False,
            "keyword_matching": False,
        },
        "profile_version":"test39"
    }

    runtime["input_sources"] = {
        k:v for k,v in (
            ("text",dialogue.get("user_text")),
            ("voice",dialogue.get("voice")),
            ("images",dialogue.get("images")),
            ("gallery",dialogue.get("gallery")),
            ("files",dialogue.get("files")),
        ) if v not in (None,{},[])
    }

    return runtime


# =====================================================
# TEST 39.1
# Canonical Semantic Fusion
# =====================================================

def fuse_semantic_inputs(runtime_state):
    runtime_state = runtime_state or {}

    inputs = dict(runtime_state.get("input_sources", {}))
    continuity = runtime_state.get("continuity_vector", {})
    scene = runtime_state.get("scene", {})

    fused_context = {
        "transport": "transport_state",
        "scene": scene,
        "goal": continuity.get("goal"),
        "history": continuity.get("history", []),
        "assistant_response": continuity.get("assistant"),
        "modalities": {
            "text": inputs.get("text"),
            "voice": inputs.get("voice"),
            "images": inputs.get("images"),
            "gallery": inputs.get("gallery"),
            "files": inputs.get("files"),
        },
        "semantic_state": {
            "single_route": True,
            "multimodal_fusion": True,
            "legacy_trigger_enabled": False,
            "context_complete": True,
        },
        "profile_version": "test39.1",
    }

    fused_context["available_modalities"] = [
        name for name, value in fused_context["modalities"].items()
        if value not in (None, {}, [], "")
    ]

    return fused_context


def build_processor_execution_context(runtime_state):
    runtime_state = runtime_state or {}
    fused = fuse_semantic_inputs(runtime_state)

    return {
        "transport": "transport_state",
        "semantic_context": fused,
        "executor_context": fused,
        "processor_context": fused,
        "profile_version": "test39.1",
    }


# =====================================================
# RU-48 Transport diagnostics
# =====================================================
def build_transport_diagnostics(result):
    return {
        "has_transport": "transport_state" in result,
        "has_machine_response": "machine_response" in result,
        "has_scene_contract": "scene_contract" in result,
        "normalized": bool(result.get("normalized")),
    }
