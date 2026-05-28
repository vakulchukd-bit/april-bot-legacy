# =====================================================
# 🧠 APRIL IMAGE GENERATION MODULE
# =====================================================

"""
APRIL IMAGE GENERATION MODULE

APRIL_FILE_ID:
APRIL_IMAGE_GENERATION_CONTINUITY_MODULE

ROLE:
VISUAL_GENERATION_CONTINUITY_COORDINATOR

INPUT:
USER_IMAGE_REQUEST
VISUAL_HINTS
SCENE_STATE
IMAGE_CONTEXT

OUTPUT:
VISUAL_GENERATION_STATE
IMAGE_TRAJECTORY
WEB_RENDERER_CONTEXT

Главная задача:
- visual continuity;
- image trajectory preservation;
- renderer-safe visual coordination;
- Web Space preparation;
- lightweight visual orchestration.

Этот файл НЕ:
- renderer authority;
- frontend renderer;
- Telegram-only image pipeline;
- hidden orchestration layer;
- recursive generation router.
"""

# =====================================================
# 🔥 SAFE PATCH MODE (IMAGE MODULE)
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "IMAGE MODULE PATCH:",
            msg
        )

        PATCH_LOG.append(msg)

    except:
        pass


# 🔥 PATCH: контроль генерации изображения
def patch_image_generate(prompt):

    safe_patch_log(
        f"IMAGE GENERATE: {str(prompt)[:50]}"
    )

    return prompt


# 🔥 PATCH: будущая логика генерации
def patch_image_module_future(
    *args,
    **kwargs
):

    return None

# =====================================================
# 🔥 IMPORTS
# =====================================================

import base64
import asyncio

from openai import OpenAI

from storage import (

    get_user_plan,
    get_limits,
    get_conn,
    today
)

from blocks.state_manager import (
    set_last_entity
)

# =====================================================
# 🔥 FILE ID
# =====================================================

APRIL_FILE_ID = (
    "APRIL_IMAGE_GENERATION_CONTINUITY_MODULE"
)

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

IMAGE_GENERATION_TASK_CHANNEL = {

    "channel":
        "image_generation_machine_task_channel",

    "isolated":
        True
}

IMAGE_GENERATION_RESPONSE_CHANNEL = {

    "channel":
        "image_generation_machine_response_channel",

    "isolated":
        True
}

# =====================================================
# 🔥 MACHINE LOGS
# =====================================================

IMAGE_GENERATION_LOGS = []

MAX_IMAGE_GENERATION_LOGS = 50


def log_image_generation_event(
    event,
    payload=None
):

    try:

        IMAGE_GENERATION_LOGS.append({

            "file_id":
                APRIL_FILE_ID,

            "event":
                event,

            "payload":
                payload or {},

            "machine_only":
                True
        })

        if (

            len(
                IMAGE_GENERATION_LOGS
            )

            > MAX_IMAGE_GENERATION_LOGS

        ):

            IMAGE_GENERATION_LOGS.pop(0)

    except:
        pass

# =====================================================
# 🔥 OPENAI
# =====================================================

client = OpenAI()

# =====================================================
# 🔥 ADMIN
# =====================================================

ADMIN_ID = 2016592532

# =====================================================
# 🔥 PATCH MARKER
# =====================================================

def _patch_marker():

    return True

# =====================================================
# 🔥 SAVE TO MEMORY
# =====================================================

def save_to_memory(
    state,
    item
):

    memory = state.get(
        "image_memory",
        []
    )

    memory.append(item)

    if len(memory) > 3:

        memory = memory[-3:]

    state[
        "image_memory"
    ] = memory

    state[
        "image_context"
    ] = item

    log_image_generation_event(

        "memory_updated",

        {
            "memory_size":
                len(memory)
        }
    )

# =====================================================
# 🔥 CLEAN PROMPT
# =====================================================

def clean_prompt(
    text: str
):

    if not text:
        return ""

    t = text.strip()

    banned = [

        "система",
        "анализ личности",
        "контекст:",
        "опыт:"
    ]

    for b in banned:

        if b in t.lower():

            t = t.lower().replace(
                b,
                ""
            )

    return t.strip()

# =====================================================
# 🔥 EXTRACT IMAGE PROMPT
# =====================================================

def extract_image_prompt(
    text: str
):

    if not text:
        return ""

    t = text.lower()

    banned = [

        "давай",
        "хочу",
        "сделай",
        "создай",
        "нарисуй",
        "пожалуйста",
        "можешь",
        "как думаешь"
    ]

    for b in banned:

        t = t.replace(
            b,
            ""
        )

    t = t.strip()

    separators = [

        ".",
        ",",
        ":",
        ";",
        "\n"
    ]

    for sep in separators:

        if sep in t:

            t = t.split(sep)[0]

    t = t.strip()

    if len(t) > 300:

        t = t[:300]

    return t

# =====================================================
# 🔥 VISUAL CONTINUITY
# =====================================================

def build_visual_generation_state(
    prompt,
    source="generation"
):

    return {

        "prompt":
            prompt,

        "source":
            source,

        "renderer_expected":
            True,

        "visual_continuity":
            True,

        "web_visual_space":
            True,

        "machine_channel":
            IMAGE_GENERATION_RESPONSE_CHANNEL,

        "file_id":
            APRIL_FILE_ID
    }

# =====================================================
# 🔥 V1 (LEGACY RESERVE)
# =====================================================

async def generate_image(
    prompt
):

    def run():

        try:

            print(
                "🛑 OPENAI IMAGE DISABLED (V1)"
            )

            log_image_generation_event(
                "legacy_generation_blocked"
            )

            return None

        except Exception as e:

            print(
                "IMAGE GENERATION ERROR:",
                e
            )

            log_image_generation_event(

                "legacy_generation_error",

                {
                    "error":
                        str(e)
                }
            )

            return None

    return await (
        asyncio.get_event_loop()
        .run_in_executor(
            None,
            run
        )
    )

# =====================================================
# 🔥 V2 (PRIMARY)
# =====================================================

async def generate_image_v2(
    prompt
):

    def run():

        try:

            print(
                "🛑 OPENAI IMAGE DISABLED (V2)"
            )

            log_image_generation_event(
                "v2_generation_blocked"
            )

            return None

        except Exception as e:

            print(
                "IMAGE GENERATION V2 ERROR:",
                e
            )

            log_image_generation_event(

                "v2_generation_error",

                {
                    "error":
                        str(e)
                }
            )

            return None

    return await (
        asyncio.get_event_loop()
        .run_in_executor(
            None,
            run
        )
    )

# =====================================================
# 🔥 INCREMENT
# =====================================================

def increment_images(
    user_id
):

    conn = get_conn()

    if not conn:
        return

    uid = str(user_id)

    with conn:

        with conn.cursor() as cur:

            cur.execute(

                "SELECT images_today, last_reset "
                "FROM users "
                "WHERE user_id = %s",

                (uid,)
            )

            user = cur.fetchone()

            if not user:
                return

            images = (
                user["images_today"]
                or 0
            )

            if (
                user["last_reset"]
                != today()
            ):

                images = 0

            cur.execute(
                """
                UPDATE users
                SET images_today = %s,
                    last_reset = %s
                WHERE user_id = %s
                """,
                (
                    images + 1,
                    today(),
                    uid
                )
            )

# =====================================================
# 🔥 PROCESS
# =====================================================

async def process(
    user_id,
    text,
    state
):

    log_image_generation_event(

        "process_started",

        {
            "user_id":
                str(user_id)
        }
    )

    try:

        prompt = clean_prompt(
            text
        )

        prompt = extract_image_prompt(
            prompt
        )

        # ==========================================
        # 🔥 SAFE IMAGE PROMPT
        # ==========================================

        prompt = prompt.replace(
            "\n",
            " "
        )

        banned = [

            "april",
            "personality",
            "психология",
            "характер",
            "эмоции",
            "диалог",
            "roleplay",
            "system",
            "assistant",
            "user",
            "conversation",
            "memory",
            "context"
        ]

        cleaned = []

        for word in prompt.split():

            low = word.lower()

            if any(
                b in low
                for b in banned
            ):

                continue

            cleaned.append(word)

        prompt = " ".join(cleaned)

        prompt = (
            prompt[:400]
            .strip()
        )

        # ==========================================
        # 🔥 VISUAL CONTEXT
        # ==========================================

        if (

            state.get(
                "image_context",
                {}
            ).get("hint")

        ):

            prompt = (

                state[
                    "image_context"
                ]["hint"]

                + ", "

                + prompt
            )

        if not prompt:

            log_image_generation_event(
                "empty_prompt"
            )

            return {

                "type":
                    "error",

                "data":
                    "❌ Пустой запрос для генерации"
            }

        is_admin = (
            user_id == ADMIN_ID
        )

        plan = get_user_plan(
            user_id
        )

        # ==========================================
        # 🔥 LIMITS
        # ==========================================

        if (

            not is_admin
            and plan == "free"

        ):

            limit = 1

            limits = get_limits(

                user_id,

                img_limit=limit
            )

            if (

                limits["images_used"]
                >= limits["images_limit"]

            ):

                log_image_generation_event(
                    "limit_reached"
                )

                return {

                    "type":
                        "text",

                    "data":
                        "Сегодня лимит на создание изображений исчерпан 🙂"
                }

        # ==========================================
        # 🔥 TEST MODE
        # ==========================================

        print(
            "🛑 IMAGE GENERATION DISABLED FOR GEMINI TEST MODE"
        )

        log_image_generation_event(
            "test_mode_active"
        )

        img = await generate_image_v2(
            prompt
        )

        if img:

            visual_state = (
                build_visual_generation_state(
                    prompt,
                    source="v2"
                )
            )

            state[
                "image_current"
            ] = img

            state[
                "active_visual_scene"
            ] = visual_state

            set_last_entity(

                user_id,

                {

                    "type":
                        "image",

                    "data":
                        img,

                    "source":
                        "v2",

                    "renderer_expected":
                        True
                }
            )

            print(
                "🖼 IMAGE SAVED TO META (V2)"
            )

            if (

                not is_admin
                and plan == "free"

            ):

                increment_images(
                    user_id
                )

            save_to_memory(

                state,

                {

                    "type":
                        "generated",

                    "source":
                        "v2",

                    "prompt":
                        prompt,

                    "hint":
                        prompt,

                    "path":
                        None,

                    "renderer_expected":
                        True
                }
            )

            log_image_generation_event(
                "v2_generation_success"
            )

            return {

                "type":
                    "image",

                "data":
                    img
            }

        # ==========================================
        # 🔥 LEGACY FALLBACK
        # ==========================================

        img = await generate_image(
            prompt
        )

        if img:

            visual_state = (
                build_visual_generation_state(
                    prompt,
                    source="v1"
                )
            )

            state[
                "image_current"
            ] = img

            state[
                "active_visual_scene"
            ] = visual_state

            set_last_entity(

                user_id,

                {

                    "type":
                        "image",

                    "data":
                        img,

                    "source":
                        "v1",

                    "renderer_expected":
                        True
                }
            )

            print(
                "🖼 IMAGE SAVED TO META (V1)"
            )

            if (

                not is_admin
                and plan == "free"

            ):

                increment_images(
                    user_id
                )

            save_to_memory(

                state,

                {

                    "type":
                        "generated",

                    "source":
                        "v1",

                    "prompt":
                        prompt,

                    "hint":
                        prompt,

                    "path":
                        None,

                    "renderer_expected":
                        True
                }
            )

            log_image_generation_event(
                "v1_generation_success"
            )

            return {

                "type":
                    "image",

                "data":
                    img
            }

        log_image_generation_event(
            "generation_failed"
        )

        return {

            "type":
                "final_error",

            "data":
                "⚠️ Не удалось создать изображение"
        }

    except Exception as e:

        print(
            "IMAGE MODULE ERROR:",
            e
        )

        log_image_generation_event(

            "process_error",

            {
                "error":
                    str(e)
            }
        )

        return {

            "type":
                "error",

            "data":
                None
        }

# =====================================================
# 🔥 RETRY
# =====================================================

async def retry_process(
    user_id,
    text,
    state
):

    log_image_generation_event(
        "retry_started"
    )

    try:

        prompt = clean_prompt(
            text
        )

        prompt = extract_image_prompt(
            prompt
        )

        if not prompt:

            return {

                "type":
                    "final_error",

                "data":
                    "❌ Пустой запрос"
            }

        is_admin = (
            user_id == ADMIN_ID
        )

        img = await generate_image_v2(
            prompt
        )

        if not img:

            img = await generate_image(
                prompt
            )

        if img:

            visual_state = (
                build_visual_generation_state(
                    prompt,
                    source="retry"
                )
            )

            state[
                "image_current"
            ] = img

            state[
                "active_visual_scene"
            ] = visual_state

            set_last_entity(

                user_id,

                {

                    "type":
                        "image",

                    "data":
                        img,

                    "source":
                        "retry",

                    "renderer_expected":
                        True
                }
            )

            print(
                "🖼 IMAGE SAVED TO META (RETRY)"
            )

            plan = get_user_plan(
                user_id
            )

            if (

                not is_admin
                and plan == "free"

            ):

                increment_images(
                    user_id
                )

            save_to_memory(

                state,

                {

                    "type":
                        "generated",

                    "source":
                        "retry",

                    "prompt":
                        prompt,

                    "hint":
                        prompt,

                    "path":
                        None,

                    "renderer_expected":
                        True
                }
            )

            log_image_generation_event(
                "retry_success"
            )

            return {

                "type":
                    "image",

                "data":
                    img
            }

        log_image_generation_event(
            "retry_failed"
        )

        return {

            "type":
                "final_error",

            "data":
                "⚠️ Не удалось создать изображение"
        }

    except Exception as e:

        print(
            "IMAGE RETRY ERROR:",
            e
        )

        log_image_generation_event(

            "retry_error",

            {
                "error":
                    str(e)
            }
        )

        return {

            "type":
                "final_error",

            "data":
                "⚠️ Сервис временно недоступен"
        }
