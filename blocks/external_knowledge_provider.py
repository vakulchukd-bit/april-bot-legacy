# =====================================================
# 🧠 APRIL EXTERNAL KNOWLEDGE PROVIDER
# =====================================================

"""
External knowledge layer для April.

Главная задача:
- НЕ заменять rooms;
- НЕ ломать personality;
- НЕ перехватывать execution;
- НЕ отвечать напрямую пользователю.

Этот модуль:
- помогает April получать внешние знания;
- расширяет ответы;
- поддерживает web-style knowledge;
- даёт contextual enrichment;
- работает как capability самой April.

April остаётся единым субъектом.
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from openai import OpenAI

# =====================================================
# 🌐 REAL WEB SEARCH LAYER
# =====================================================

from blocks.web_search_system import (
    search_web,
    build_search_summary
)

client = OpenAI()


# =====================================================
# 🧠 KNOWLEDGE TRIGGERS
# =====================================================

WEB_KNOWLEDGE_TOPICS = [

    # =============================================
    # TRAVEL
    # =============================================

    "путешествие",
    "отдых",
    "страна",
    "город",
    "курорт",
    "море",
    "горы",
    "куда поехать",

    # =============================================
    # PLACES
    # =============================================

    "достопримечательность",
    "история города",
    "интересные места",
    "музей",
    "архитектура",

    # =============================================
    # NEWS
    # =============================================

    "новости",
    "что произошло",
    "сейчас происходит",

    # =============================================
    # RECOMMENDATIONS
    # =============================================

    "лучше",
    "сравнение",
    "что выбрать",
    "где лучше",

    # =============================================
    # KNOWLEDGE
    # =============================================

    "объясни",
    "расскажи",
    "интересный факт",
    "что такое",

    # =============================================
    # INTERNET
    # =============================================

    "youtube",
    "ютуб",
    "telegram",
    "телеграм",
    "instagram",
    "facebook",
    "twitter",
    "x.com",
    "reddit",
    "github",
    "tiktok",
    "discord",
    "ссылка",
    "канал",
    "сайт",
    "соцсеть",

    # =============================================
    # MAPS / LOCATION
    # =============================================

    "карта",
    "маршрут",
    "локация",
    "район"
]


# =====================================================
# 🧠 INTERNET PLATFORM AWARENESS
# =====================================================

INTERNET_PLATFORM_TYPES = {

    "youtube": "media_platform",

    "telegram": "community_platform",

    "instagram": "social_platform",

    "facebook": "social_platform",

    "twitter": "social_platform",

    "x": "social_platform",

    "reddit": "discussion_platform",

    "github": "development_platform",

    "tiktok": "media_platform",

    "discord": "community_platform",

    "wikipedia": "knowledge_platform"
}


# =====================================================
# 🧠 WEB CAPABILITY STATE
# =====================================================

WEB_CAPABILITIES = {

    # =================================================
    # 🌐 REAL WEB STATUS
    # =================================================

    "real_time_search": True,

    "verified_links": True,

    "live_internet_access": True,

    # =================================================
    # 🧠 COGNITIVE AWARENESS
    # =================================================

    "platform_understanding": True,

    "social_media_awareness": True,

    "link_reasoning": True,

    # =================================================
    # 🔥 SAFETY
    # =================================================

    "hallucination_risk": False,

    "requires_verification": True
}


# =====================================================
# 🧠 WEB ESCALATION DETECTION
# =====================================================

def should_use_external_knowledge(
    text: str,
    semantic: dict,
    cognition: dict,
    response_decision: dict
):

    text = (text or "").lower()

    semantic = semantic or {}
    cognition = cognition or {}
    response_decision = response_decision or {}

    # =================================================
    # 🔥 EXECUTION PRIORITY PROTECTION
    # =================================================

    if semantic.get(
        "should_execute"
    ):
        return False

    # =================================================
    # 🔥 VISUAL GENERATION PROTECTION
    # =================================================

    if response_decision.get(
        "should_generate"
    ):
        return False

    # =================================================
    # 🔥 ROOM PRIORITY
    # =================================================

    room = semantic.get(
        "room"
    )

    if room in [
        "science",
        "image_generate",
        "image_edit"
    ]:
        return False

    # =================================================
    # 🔥 USER EXPLORATION
    # =================================================

    if cognition.get(
        "exploration_mode"
    ):

        if cognition.get(
            "wants_dialog",
            0.0
        ) >= 0.5:

            return True

    # =================================================
    # 🔥 KNOWLEDGE TOPICS
    # =================================================

    for topic in WEB_KNOWLEDGE_TOPICS:

        if topic in text:
            return True

    # =================================================
    # 🔥 HIGH AMBIGUITY
    # =================================================

    if semantic.get(
        "ambiguity_level",
        0.0
    ) >= 0.75:

        return True

    return False


# =====================================================
# 🧠 LEGACY PROMPT LAYER
# =====================================================

"""
Старый prompt-layer сохранён
для continuity architecture.

Но:
- больше НЕ является главным
  internet source;
- НЕ используется для URL generation;
- НЕ имеет authority над ссылками.

Теперь:
real web layer имеет приоритет.
"""


# =====================================================
# 🧠 EXTERNAL KNOWLEDGE REQUEST
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

    emotional = cognition.get(
        "emotional_trajectory",
        "neutral"
    )

    return f"""
Ты помогаешь cognitive assistant April.

ВАЖНО:
- НЕ отвечай как отдельный ИИ.
- НЕ roleplay.
- НЕ используй фразы:
  "как ИИ",
  "я не могу",
  "я модель".

КРИТИЧЕСКИ ВАЖНО:
- НЕ придумывай ссылки.
- НЕ выдумывай Telegram.
- НЕ выдумывай YouTube.
- НЕ выдумывай сайты.
- НЕ придумывай соцсети.
- НЕ hallucinate URL.

Если информация не проверена:
- честно скажи это.

Нужна:
- краткая,
- полезная,
- актуальная,
- человеческая информация.

Тон:
- естественный,
- мягкий,
- readable,
- informative.

Эмоциональный контекст:
{emotional}

Текущий режим:
{goal_stage}

Запрос пользователя:
{text}

Дай:
- ключевые факты,
- полезные детали,
- contextual enrichment,
- без воды.
"""


# =====================================================
# 🌐 REAL EXTERNAL KNOWLEDGE FETCH
# =====================================================

def fetch_external_knowledge(
    text: str,
    semantic: dict,
    cognition: dict
):

    try:

        # =============================================
        # 🌐 REAL WEB SEARCH
        # =============================================

        web_results = search_web(
            text
        )

        summary = build_search_summary(
            web_results
        )

        # =============================================
        # 🌐 VERIFIED RESULTS
        # =============================================

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

                "used_real_web": True
            }

        # =============================================
        # 🧠 SAFE FALLBACK
        # =============================================

        prompt = build_external_prompt(
            text,
            semantic,
            cognition
        )

        response = client.responses.create(

            model="gpt-4o-mini",

            input=[
                {
                    "role": "system",
                    "content":
                        "Ты knowledge layer April."
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.2,

            max_output_tokens=220
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
# 🧠 KNOWLEDGE ENRICHMENT
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

    # =================================================
    # 🔥 SAFE MERGE
    # =================================================

    if not base_response:
        return knowledge

    return (
        base_response.strip()
        + "\n\n"
        + knowledge
    )


# =====================================================
# 🧠 EXTERNAL CONTEXT BUILDER
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

        "used_real_web":
            result.get(
                "used_real_web",
                False
            ),

        "web_capabilities":
            WEB_CAPABILITIES
    }
