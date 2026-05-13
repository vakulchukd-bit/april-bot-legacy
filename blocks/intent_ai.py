from openai import OpenAI
import asyncio

client = OpenAI()


# =====================================================
# 🧠 LOCAL SAFE DETECTION
# =====================================================

def detect_intent_local(
    text: str,
    state: dict = None
):

    t = (text or "").lower().strip()

    state = state or {}

    active_flow = state.get(
        "active_flow",
        {}
    )

    # =================================================
    # 🔥 CONTINUATION PROTECTION
    # =================================================

    continuation_words = [

        "да",
        "ага",
        "вот",
        "примерно",
        "ближе",
        "уже лучше",
        "чуть темнее",
        "чуть светлее",
        "сделай темнее",
        "сделай ярче",
        "не то",
        "переделай",
        "продолжай"
    ]

    if t in continuation_words:

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if flow_type in [

                "image_generate",
                "image_edit",
                "image"
            ]:

                return {
                    "intent": "edit_image",
                    "confidence": 0.82,
                    "source": "local_continuation"
                }

        return {
            "intent": "text",
            "confidence": 0.55,
            "source": "safe_continuation"
        }

    # =================================================
    # 🔥 SAFE IMAGE GENERATION
    # =================================================

    strong_generate_words = [

        "сгенерируй изображение",
        "создай изображение",
        "нарисуй картинку",
        "создай картинку",
        "generate image"
    ]

    if any(x in t for x in strong_generate_words):

        return {
            "intent": "generate_image",
            "confidence": 0.92,
            "source": "local_generate"
        }

    # =================================================
    # 🔥 SAFE IMAGE EDIT
    # =================================================

    edit_words = [

        "измени",
        "добавь",
        "убери",
        "замени",
        "сделай ярче",
        "сделай темнее"
    ]

    if any(x in t for x in edit_words):

        if state.get(
            "image_context"
        ) or active_flow:

            return {
                "intent": "edit_image",
                "confidence": 0.88,
                "source": "local_edit"
            }

    # =================================================
    # 🔥 SAFE IMAGE ANALYZE
    # =================================================

    analyze_words = [

        "что на картинке",
        "что изображено",
        "что это",
        "опиши изображение",
        "что видишь"
    ]

    if any(x in t for x in analyze_words):

        if state.get(
            "image_context"
        ):

            return {
                "intent": "analyze_image",
                "confidence": 0.9,
                "source": "local_analyze"
            }

    # =================================================
    # 🔥 MATH / SCIENCE
    # =================================================

    math_words = [

        "график",
        "уравнение",
        "реши",
        "sin(",
        "cos(",
        "tan(",
        "y="
    ]

    if any(x in t for x in math_words):

        return {
            "intent": "science",
            "confidence": 0.9,
            "source": "local_science"
        }

    return None


# =====================================================
# 🧠 SAFE AI INTENT
# =====================================================

async def detect_intent_ai(
    text: str,
    state: dict = None
):

    state = state or {}

    t = (text or "").strip()

    # =================================================
    # 🔥 LOCAL FIRST
    # =================================================

    local = detect_intent_local(
        t,
        state
    )

    if local:
        return local

    # =================================================
    # 🔥 SHORT INPUT PROTECTION
    # =================================================

    if len(t) <= 15:

        active_flow = state.get(
            "active_flow"
        )

        if active_flow:

            flow_type = active_flow.get(
                "type"
            )

            if flow_type in [

                "image_generate",
                "image_edit",
                "image"
            ]:

                return {
                    "intent": "edit_image",
                    "confidence": 0.65,
                    "source": "short_continuation"
                }

        return {
            "intent": "text",
            "confidence": 0.5,
            "source": "short_safe"
        }

    # =================================================
    # 🔥 AI FALLBACK
    # =================================================

    def run():

        try:

            prompt = f"""
Ты — intent analyzer для April DeepHub.

Главное правило:
НЕ форсируй generate_image без явного запроса.

generate_image:
ТОЛЬКО если пользователь явно хочет СОЗДАТЬ изображение.

edit_image:
если пользователь продолжает,
изменяет,
уточняет,
или правит существующую сцену.

analyze_image:
если пользователь анализирует изображение.

science:
если пользователь хочет:
- график
- математику
- уравнение
- вычисление

text:
во всех остальных случаях.

ВАЖНО:
- continuation важнее trigger words;
- ambiguity НЕ означает generate_image;
- exploration НЕ означает generate_image;
- "картинка", "образ", "атмосфера"
  сами по себе НЕ generate_image.

Ответь ОДНИМ словом.

Варианты:
generate_image
edit_image
analyze_image
science
text

Текст:
{text}
"""

            res = client.chat.completions.create(

                model="gpt-4o-mini",

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],

                temperature=0,

                max_tokens=8
            )

            raw = (
                res.choices[0]
                .message.content
                .strip()
                .lower()
            )

            allowed = [

                "generate_image",
                "edit_image",
                "analyze_image",
                "science",
                "text"
            ]

            if raw not in allowed:

                raw = "text"

            return {
                "intent": raw,
                "confidence": 0.72,
                "source": "openai"
            }

        except Exception as e:

            print(
                "🔥 INTENT AI ERROR:",
                e
            )

            return {
                "intent": "text",
                "confidence": 0.4,
                "source": "fallback_error"
            }

    return await asyncio.to_thread(run)
