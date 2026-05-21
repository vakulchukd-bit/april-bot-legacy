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

    "last_gemini_failure": 0,

    "last_health_check": 0,

    "recovery_cooldown": 45
}


# =====================================================
# 🔥 SAFE LOG
# =====================================================

def provider_log(*args):

    try:

        print(*args)

    except:
        pass


# =====================================================
# 🔥 GEMINI RESTORE CHECK
# =====================================================

def should_restore_gemini():

    if provider_state["gemini_available"]:

        return True

    now = time.time()

    cooldown = provider_state[
        "recovery_cooldown"
    ]

    last_failure = provider_state[
        "last_gemini_failure"
    ]

    if now - last_failure >= cooldown:

        provider_log(
            "🧠 GEMINI RECOVERY WINDOW OPEN"
        )

        provider_state[
            "gemini_available"
        ] = True

        provider_state[
            "last_health_check"
        ] = now

        return True

    return False


# =====================================================
# 🔥 GEMINI FAILURE
# =====================================================

def mark_gemini_failure():

    provider_log(
        "🔥 GEMINI MARKED UNAVAILABLE"
    )

    provider_state[
        "gemini_available"
    ] = False

    provider_state[
        "last_gemini_failure"
    ] = time.time()


# =====================================================
# 🔥 GEMINI SUCCESS
# =====================================================

def mark_gemini_success():

    provider_state[
        "gemini_available"
    ] = True

    provider_state[
        "last_health_check"
    ] = time.time()


# =====================================================
# 🔥 BUILD GEMINI PROMPT
# =====================================================

def build_gemini_prompt(
    messages
):

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

                f"{role.upper()}: "
                f"{content}"
            )

    return (

        system_prompt
        + "\n\n"
        + "\n".join(conversation)
    )


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

            provider_log(
                "🧠 GEMINI TEXT START"
            )

            final_prompt = (
                build_gemini_prompt(
                    messages
                )
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

                provider_log(
                    "🧠 GEMINI TEXT SUCCESS"
                )

                mark_gemini_success()

                return text

        except Exception as e:

            provider_log(
                "🔥 GEMINI TEXT ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI FALLBACK
    # =================================================

    try:

        provider_log(
            "⚠️ USING OPENAI FALLBACK"
        )

        response = (

            openai_client.responses.create(

                model="gpt-4o-mini",

                input=messages,

                temperature=temperature,

                max_output_tokens=max_output_tokens
            )
        )

        provider_log(
            "🧠 OPENAI TEXT SUCCESS"
        )

        return response.output_text

    except Exception as e:

        provider_log(
            "🔥 OPENAI TEXT ERROR:",
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

            provider_log(
                "🧠 GEMINI VOICE START"
            )

            provider_log(
                "🧠 GEMINI AUDIO PATH:",
                file_path
            )

            uploaded = gemini_client.files.upload(
                file=file_path
            )

            provider_log(
                "🧠 GEMINI AUDIO UPLOADED"
            )

            for _ in range(60):

                uploaded = gemini_client.files.get(
                    name=uploaded.name
                )

                provider_log(
                    "🧠 GEMINI FILE STATE:",
                    uploaded.state.name
                )

                if uploaded.state.name == "ACTIVE":

                    break

                await asyncio.sleep(1)

            if uploaded.state.name != "ACTIVE":

                raise Exception(
                    "GEMINI FILE NOT ACTIVE"
                )

            provider_log(
                "🧠 GEMINI START TRANSCRIBE"
            )

            response = (

                gemini_client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=[

                        uploaded,

                        (
                            "Сделай точную "
                            "транскрипцию аудио. "
                            "Без комментариев."
                        )
                    ]
                )
            )

            text = (

                response.text.strip()
                if response.text
                else ""
            )

            provider_log(
                "🧠 GEMINI TRANSCRIBE RESPONSE:",
                text[:120] if text else "EMPTY"
            )

            if text:

                mark_gemini_success()

                return text

        except Exception as e:

            provider_log(
                "🔥 GEMINI VOICE ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI FALLBACK
    # =================================================

    try:

        provider_log(
            "⚠️ OPENAI VOICE FALLBACK"
        )

        with open(file_path, "rb") as f:

            transcript = (

                openai_client.audio.transcriptions.create(

                    model="gpt-4o-mini-transcribe",

                    file=f
                )
            )

        provider_log(
            "🧠 OPENAI VOICE SUCCESS"
        )

        return transcript.text.strip()

    except Exception as e:

        provider_log(
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

            provider_log(
                "🧠 GEMINI IMAGE START"
            )

            provider_log(
                "🧠 GEMINI IMAGE PATH:",
                path
            )

            uploaded = gemini_client.files.upload(
                file=path
            )

            provider_log(
                "🧠 GEMINI IMAGE UPLOADED"
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

            provider_log(
                "🧠 GEMINI IMAGE RESPONSE:",
                text[:120] if text else "EMPTY"
            )

            if text:

                mark_gemini_success()

                return text

        except Exception as e:

            provider_log(
                "🔥 GEMINI IMAGE ERROR:",
                e
            )

            mark_gemini_failure()

    # =================================================
    # 🔥 OPENAI EMERGENCY FALLBACK
    # =====================================================

    try:

        provider_log(
            "⚠️ OPENAI IMAGE FALLBACK"
        )

        return (
            "⚠️ Visual fallback "
            "временно активирован."
        )

    except Exception as e:

        provider_log(
            "🔥 OPENAI IMAGE ERROR:",
            e
        )

        return (
            "⚠️ Visual-space "
            "временно перегружен."
        )
