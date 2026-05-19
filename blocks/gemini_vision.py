import os

from google import genai


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


async def analyze_image_gemini(path: str) -> str:

    try:

        uploaded_file = client.files.upload(
            file=path
        )

        response = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=[

                uploaded_file,

                (
                    "Ты visual helper внутри April. "
                    "Коротко, спокойно и понятно "
                    "опиши изображение для помощи человеку."
                )
            ]
        )

        text = (

            response.text
            if response.text
            else "Изображение обработано."
        )

        return text

    except Exception as e:

        return (
            f"Gemini image error: {str(e)}"
        )
