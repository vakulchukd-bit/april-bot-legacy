import os

from google import genai
from google.genai import errors as gemini_errors

from openai import OpenAI


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
# 🔥 PROVIDER STATE
# =====================================================

ACTIVE_PROVIDER = "gemini"


# =====================================================
# 🔥 PROVIDER SWITCH
# =====================================================

def set_provider(name: str):

    global ACTIVE_PROVIDER

    ACTIVE_PROVIDER = name

    print(
        f"🧠 ACTIVE VISUAL PROVIDER: "
        f"{ACTIVE_PROVIDER}"
    )


def get_provider():

    return ACTIVE_PROVIDER


# =====================================================
# 🔥 GEMINI HEALTHCHECK
# =====================================================

async def gemini_available():

    try:

        gemini_client.models.generate_content(

            model="gemini-2.5-flash",

            contents="ping"
        )

        return True

    except Exception:

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
    # 🔥 УБИРАЕМ СЛИШКОМ ДЛИННЫЕ ПРОСТЫНИ
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

    uploaded_file = gemini_client.files.upload(
        file=path
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

    return shape_april_visual_response(
        raw_text
    )


# =====================================================
# 🔥 OPENAI FALLBACK
# =====================================================

async def analyze_with_openai(
    path: str
) -> str:

    with open(path, "rb") as image_file:

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
                                "Без robotic AI тона."
                            )
                        },

                        {
                            "type": "input_image",

                            "image_data":
                                image_file.read()
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

    return shape_april_visual_response(
        raw_text
    )


# =====================================================
# 🔥 MAIN GEMINI SYSTEM
# =====================================================

async def analyze_image_gemini(
    path: str
) -> str:

    global ACTIVE_PROVIDER

    try:

        # =============================================
        # 🔥 PRIMARY PROVIDER
        # =============================================

        if ACTIVE_PROVIDER == "gemini":

            try:

                result = await analyze_with_gemini(
                    path
                )

                return result

            except Exception as gemini_error:

                print(
                    "⚠️ GEMINI FAILED:",
                    gemini_error
                )

                print(
                    "🔁 SWITCHING TO OPENAI FALLBACK"
                )

                set_provider("openai")

        # =============================================
        # 🔥 OPENAI FALLBACK
        # =============================================

        result = await analyze_with_openai(
            path
        )

        # =============================================
        # 🔥 GEMINI RECOVERY CHECK
        # =============================================

        try:

            recovered = await gemini_available()

            if recovered:

                print(
                    "✅ GEMINI RESTORED"
                )

                set_provider("gemini")

        except Exception:
            pass

        return result

    except Exception as e:

        print(
            "🔥 VISUAL SYSTEM ERROR:",
            e
        )

        return (
            "Сейчас visual-space "
            "немного перегружен. "
            "Попробуй ещё раз "
            "через несколько секунд."
        )
