import os

from google import genai


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


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
# 🔥 GEMINI IMAGE ANALYSIS
# =====================================================

async def analyze_image_gemini(
    path: str
) -> str:

    try:

        uploaded_file = client.files.upload(
            file=path
        )

        response = client.models.generate_content(

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

        final_text = (
            shape_april_visual_response(
                raw_text
            )
        )

        return final_text

    except Exception:

        return (
            "Сейчас visual-space "
            "немного перегружен. "
            "Попробуй ещё раз "
            "через несколько секунд."
        )
