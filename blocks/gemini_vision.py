import os
import time

from google import genai
from google.genai import errors as gemini_errors

from openai import OpenAI

# =====================================================
# 🔥 SHARED PROVIDER STATE
# =====================================================

from blocks.provider_router import (

    provider_state,

    should_restore_gemini,

    mark_gemini_failure,

    mark_gemini_success,

    provider_log
)


# =====================================================
# 🔥 PROVIDERS
# =====================================================

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# =====================================================
# 🔥 VISUAL PROVIDER MODE
# =====================================================

ACTIVE_PROVIDER = "gemini"


# =====================================================
# 🔥 PROVIDER SWITCH
# =====================================================

def set_provider(name: str):

    global ACTIVE_PROVIDER

    ACTIVE_PROVIDER = name

    provider_log(
        f"🧠 ACTIVE VISUAL PROVIDER: "
        f"{ACTIVE_PROVIDER}"
    )


def get_provider():

    return ACTIVE_PROVIDER


# =====================================================
# 🔥 SAFE GEMINI RECOVERY
# =====================================================

def can_try_gemini():

    if ACTIVE_PROVIDER == "gemini":

        return should_restore_gemini()

    return False


# =====================================================
# 🔥 APRIL VISUAL RESPONSE SHAPER
# =====================================================

def shape_april_visual_response(
    text: str
) -> str:

    if not text:

        return (
            "Я получила изображение, "
            "но пока не смогла спокойно "
            "его разобрать."
        )

    cleaned = (
        text
        .replace("*", "")
        .replace("На изображении", "")
        .replace("изображено", "")
        .replace("показано", "")
        .strip()
    )

    # =========================================
    # 🔥 LIMIT RESPONSE SIZE
    # =========================================

    if len(cleaned) > 420:

        cleaned = (
            cleaned[:420].rsplit(".", 1)[0]
            + "."
        )

    # =========================================
    # 🔥 LIGHT APRIL TONE
    # =========================================

    if (
        "надпись" in cleaned.lower()
        or "текст" in cleaned.lower()
    ):

        return (
            f"{cleaned}\n\n"
            "Похоже, в этом есть "
            "небольшое настроение или смысл 🙂"
        )

    return cleaned


# =====================================================
# 🔥 GEMINI ANALYSIS
# =====================================================

async def analyze_with_gemini(
    path: str
) -> str:

    provider_log(
        "🧠 GEMINI VISUAL START"
    )

    uploaded_file = gemini_client.files.upload(
        file=path
    )

    provider_log(
        "🧠 GEMINI FILE UPLOADED"
    )

    response = gemini_client.models.generate_content(

        model="gemini-2.5-flash",

        contents=[

            uploaded_file,

            (
                "Ты visual helper внутри April.\n"
                "\n"
                "НЕ описывай изображение "
                "как robotic AI.\n"
                "\n"
                "НЕ делай длинные простыни.\n"
                "\n"
                "НЕ перечисляй все объекты.\n"
                "\n"
                "Выделяй только главное.\n"
                "\n"
                "Отвечай спокойно, "
                "по-человечески и кратко.\n"
                "\n"
                "Если есть надпись — "
                "объясни её смысл.\n"
                "\n"
                "Допускается лёгкий "
                "живой tone или мягкий юмор.\n"
                "\n"
                "Ты helper layer. "
                "Пользователь должен "
                "ощущать April, "
                "а не Gemini."
            )
        ]
    )

    raw_text = (

        response.text
        if response.text
        else (
            "Изображение получено "
            "и обработано."
        )
    )

    mark_gemini_success()

    provider_log(
        "🧠 GEMINI VISUAL SUCCESS"
    )

    return shape_april_visual_response(
        raw_text
    )


# =====================================================
# 🔥 OPENAI FALLBACK
# =====================================================

async def analyze_with_openai(
    path: str
) -> str:

    provider_log(
        "⚠️ OPENAI VISUAL FALLBACK"
    )

    with open(path, "rb") as image_file:

        image_bytes = image_file.read()

    response = openai_client.responses.create(

        model="gpt-4.1-mini",

        input=[

            {
                "role": "user",

                "content": [

                    {
                        "type": "input_text",

                        "text": (
                            "Кратко и спокойно "
                            "объясни изображение. "
                            "Без robotic AI тона. "
                            "Выдели только главное."
                        )
                    },

                    {
                        "type": "input_image",

                        "image_data": image_bytes
                    }
                ]
            }
        ]
    )

    raw_text = getattr(
        response,
        "output_text",
        ""
    )

    if not raw_text:

        raw_text = (
            "Изображение обработано."
        )

    provider_log(
        "🧠 OPENAI VISUAL SUCCESS"
    )

    return shape_april_visual_response(
        raw_text
    )


# =====================================================
# 🔥 MAIN VISUAL SYSTEM
# =====================================================

async def analyze_image_gemini(
    path: str
) -> str:

    global ACTIVE_PROVIDER

    try:

        # =============================================
        # 🔥 GEMINI PRIMARY
        # =============================================

        if can_try_gemini():

            try:

                result = await analyze_with_gemini(
                    path
                )

                return result

            except Exception as gemini_error:

                provider_log(
                    "🔥 GEMINI VISUAL ERROR:",
                    gemini_error
                )

                mark_gemini_failure()

                set_provider("openai")

        # =============================================
        # 🔥 OPENAI FALLBACK
        # =============================================

        result = await analyze_with_openai(
            path
        )

        # =============================================
        # 🔥 GEMINI RECOVERY WINDOW
        # =============================================

        now = time.time()

        last_failure = provider_state.get(
            "last_gemini_failure",
            0
        )

        cooldown = provider_state.get(
            "recovery_cooldown",
            45
        )

        if now - last_failure >= cooldown:

            provider_log(
                "🧠 GEMINI RECOVERY READY"
            )

            set_provider("gemini")

        return result

    except Exception as e:

        provider_log(
            "🔥 VISUAL SYSTEM ERROR:",
            e
        )

        return (
            "Сейчас visual-space "
            "немного перегружен. "
            "Попробуй ещё раз "
            "через несколько секунд."
        )
