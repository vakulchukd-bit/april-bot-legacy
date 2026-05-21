# =====================================================
# 🧠 APRIL PROVIDER ROUTER
# =====================================================

import os
import time
import asyncio

from openai import OpenAI
from google import genai


# =====================================================
# 🔥 PROVIDERS
# =====================================================

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# =====================================================
# 🔥 PROVIDER STATE
# =====================================================

provider_state = {

    "primary": "gemini",

    "gemini_available": True,

    "last_gemini_failure": 0
}


# =====================================================
# 🔥 HEALTH CHECK
# =====================================================

def should_restore_gemini():

    if provider_state["gemini_available"]:
        return True

    cooldown = 45

    last_failure = provider_state[
        "last_gemini_failure"
    ]

    now = time.time()

    if now - last_failure >= cooldown:

        provider_state[
            "gemini_available"
        ] = True

        return True

    return False


# =====================================================
# 🔥 MARK FAILURE
# =====================================================

def mark_gemini_failure():

    provider_state[
        "gemini_available"
    ] = False

    provider_state[
        "last_gemini_failure"
    ] = time.time()


# =====================================================
# 🔥 TEXT GENERATION
# =====================================================

async def generate_text(

    messages,
    temperature=0.7,
    max_output_tokens=700,
    model="gemini-2.5-flash"
):

    # =================================================
    # 🔥 GEMINI PRIMARY
    # =================================================

    if should_restore_gemini():

        try:

            system_prompt = ""

            conversation = []

            for msg in messages:

                role = msg.get(
                    "role",
                    "user"
                )

                content = msg.get(
                    "content",
                    ""
                )

                if role == "system":

                    system_prompt += (
                        content + "\n"
                    )

                else:

                    conversation.append(
                        f"{role.upper()}: {content}"
                    )

            final_prompt = (

                system_prompt
                + "\n\n"
                + "\n".join(conversation)
            )

            response = (
                gemini_client.models.generate_content(

                    model=model,

                    contents=final_prompt
                )
            )

            text = (
                response.text.strip()
                if response.text
                else ""
            )

            if text:

                return text

        except Exception as e:

            print(
                "🔥 GEMINI TEXT ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI FALLBACK
    # =================================================

    try:

        response = (
            openai_client.responses.create(

                model="gpt-4o-mini",

                input=messages,

                temperature=temperature,

                max_output_tokens=max_output_tokens
            )
        )

        return response.output_text

    except Exception as e:

        print(
            "🔥 OPENAI FALLBACK ERROR:",
            e
        )

        return (
            "⚠️ Сейчас dialogue-space "
            "временно перегружен."
        )


# =====================================================
# 🔥 VOICE TRANSCRIPTION
# =====================================================

async def transcribe_voice(
    file_path
):

    # =================================================
    # 🔥 GEMINI PRIMARY
    # =================================================

    if should_restore_gemini():

        try:

            uploaded = (
                gemini_client.files.upload(
                    file=file_path
                )
            )

            response = (
                gemini_client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=[

                        uploaded,

                        (
                            "Сделай точную "
                            "транскрипцию аудио."
                        )
                    ]
                )
            )

            text = (
                response.text.strip()
                if response.text
                else ""
            )

            if text:

                return text

        except Exception as e:

            print(
                "🔥 GEMINI VOICE ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI FALLBACK
    # =================================================

    try:

        with open(file_path, "rb") as f:

            transcript = (
                openai_client.audio.transcriptions.create(

                    model="gpt-4o-mini-transcribe",

                    file=f
                )
            )

        return transcript.text.strip()

    except Exception as e:

        print(
            "🔥 OPENAI VOICE ERROR:",
            e
        )

        return ""


# =====================================================
# 🔥 IMAGE ANALYSIS
# =====================================================

async def analyze_image_with_fallback(
    path,
    prompt
):

    # =================================================
    # 🔥 GEMINI PRIMARY
    # =================================================

    if should_restore_gemini():

        try:

            uploaded = (
                gemini_client.files.upload(
                    file=path
                )
            )

            response = (
                gemini_client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=[
                        uploaded,
                        prompt
                    ]
                )
            )

            text = (
                response.text.strip()
                if response.text
                else ""
            )

            if text:

                return text

        except Exception as e:

            print(
                "🔥 GEMINI IMAGE ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI FALLBACK
    # =================================================

    return (
        "⚠️ Visual fallback currently "
        "limited."
    )
