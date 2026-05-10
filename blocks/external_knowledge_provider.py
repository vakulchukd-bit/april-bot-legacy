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
    # MAPS / LOCATION
    # =============================================

    "карта",
    "маршрут",
    "локация",
    "район"
]

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
# 🧠 EXTERNAL KNOWLEDGE FETCH
# =====================================================

def fetch_external_knowledge(
    text: str,
    semantic: dict,
    cognition: dict
):

    try:

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

            temperature=0.5,

            max_output_tokens=350
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

            "source": "external_knowledge"
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
            "content": ""
        }

    result = fetch_external_knowledge(
        text,
        semantic,
        cognition
    )

    if not result.get("success"):

        return {
            "enabled": False,
            "content": ""
        }

    return {

        "enabled": True,

        "content":
            result.get(
                "content",
                ""
            )
    }
