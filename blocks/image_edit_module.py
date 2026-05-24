# blocks/image_edit_module.py

import asyncio
import random

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
# 🧠 APRIL IMAGE EDIT MODULE
# =====================================================

"""
APRIL IMAGE EDIT MODULE — WEB-FIRST STABILIZED

Главная идея:

Image edit module больше НЕ:
- OpenAI authority;
- Telegram image pipeline;
- hidden generation fallback;
- recursive image rerouting.

Image edit module теперь:
- lightweight visual continuity layer;
- scene-safe edit coordinator;
- web-space compatible visual helper;
- continuity-aware visual state updater.

Visual rendering authority:
всегда принадлежит April Web Space.
"""

ADMIN_ID = 2016592532

# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "IMAGE EDIT PATCH:",
            msg
        )

        PATCH_LOG.append(msg)

    except:
        pass


# =====================================================
# 🔥 VISUAL EDIT DISABLED
# =====================================================

VISUAL_EDIT_DISABLED = True


# =====================================================
# 🔥 LIMIT MESSAGES
# =====================================================

def get_limit_message():

    messages = [

        "Сегодня ты уже выжал максимум из редактирования 😌",

        "Я бы продолжил менять изображение, но сегодня уже предел 👀",

        "На сегодня с изображениями всё, завтра продолжим 😉",

        "Похоже, лимит на сегодня закончился. Но мы ещё можем пообщаться 🙂",

        "Сегодня лимит закончился, но я всё ещё здесь, если нужно что-то другое 👍"
    ]

    return random.choice(messages)


# =====================================================
# 🔥 IMAGE EDIT STUBS
# =====================================================

async def edit_image(
    image_path,
    prompt
):

    safe_patch_log(
        "LEGACY PATH EDIT BLOCKED"
    )

    return None


async def edit_image_bytes(
    image_bytes,
    prompt
):

    safe_patch_log(
        "LEGACY BYTE EDIT BLOCKED"
    )

    return None


# =====================================================
# 🔥 LIMIT INCREMENT
# =====================================================

def increment_images(user_id):

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

            images = user["images_today"] or 0

            if user["last_reset"] != today():

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
# 🔥 VISUAL CONTINUITY UPDATE
# =====================================================

def update_visual_continuity(
    state: dict,
    prompt: str
):

    active_visual_scene = state.get(
        "active_visual_scene"
    ) or {}

    objects = active_visual_scene.get(
        "objects",
        []
    )

    summary = active_visual_scene.get(
        "summary",
        ""
    )

    state["active_visual_scene"] = {

        "objects": objects,

        "summary": summary,

        "last_edit_prompt": prompt,

        "edit_requested": True,

        "renderer_expected": True,

        "web_visual_space": True
    }

    return state["active_visual_scene"]


# =====================================================
# 🔥 SAFE VISUAL RESPONSE
# =====================================================

def build_safe_visual_response(
    prompt: str
):

    return {

        "type": "visual_guidance",

        "data": {

            "mode": "web_renderer_expected",

            "message": (

                "🎨 Visual edit request accepted.\n\n"

                "April сохранила continuity сцены "
                "и подготовила visual edit trajectory "
                "для Web Space renderer."
            ),

            "prompt": prompt,

            "renderer_expected": True,

            "generation_executed": False,

            "legacy_pipeline_disabled": True
        }
    }


# =====================================================
# 🔥 PROCESS
# =====================================================

async def process(
    user_id,
    prompt,
    state
):

    try:

        safe_patch_log(
            f"EDIT REQUEST: {str(prompt)[:80]}"
        )

        prompt = (
            prompt or ""
        ).strip()

        if not prompt:

            return {

                "type": "error",

                "data":
                    "⚠️ Пустой edit-запрос."
            }

        is_admin = (
            user_id == ADMIN_ID
        )

        plan = get_user_plan(
            user_id
        )

        if plan == "premium":

            limit = 999

        elif plan == "lite":

            limit = 2

        else:

            limit = 1

        limits = get_limits(
            user_id,
            img_limit=limit
        )

        # =================================================
        # 🔥 LIMIT PROTECTION
        # =====================================================

        if (

            not is_admin
            and plan != "premium"
            and limits["images_used"]
            >= limits["images_limit"]

        ):

            return {

                "type": "text",

                "data":
                    get_limit_message()
            }

        # =================================================
        # 🔥 VISUAL CONTINUITY
        # =====================================================

        update_visual_continuity(
            state,
            prompt
        )

        state["image_context"] = {

            "type": "visual_edit_request",

            "hint": prompt,

            "web_renderer_expected": True,

            "legacy_pipeline_disabled": True
        }

        # =================================================
        # 🔥 META MEMORY UPDATE
        # =====================================================

        set_last_entity(

            user_id,

            {
                "type": "image_edit",

                "prompt": prompt,

                "source": "web_visual_space",

                "renderer_expected": True
            }
        )

        safe_patch_log(
            "VISUAL CONTINUITY UPDATED"
        )

        # =================================================
        # 🔥 LIMIT UPDATE
        # =====================================================

        if (

            not is_admin
            and plan != "premium"

        ):

            increment_images(
                user_id
            )

        # =================================================
        # 🔥 WEB-FIRST RESPONSE
        # =====================================================

        return build_safe_visual_response(
            prompt
        )

    except asyncio.TimeoutError:

        print(
            "⏱ EDIT TIMEOUT"
        )

        return {

            "type": "error",

            "data":
                "⚠️ Visual edit timeout."
        }

    except Exception as e:

        print(
            "🔥 IMAGE EDIT ERROR:",
            e
        )

        return {

            "type": "error",

            "data":
                "⚠️ Visual edit processing failed."
        }
