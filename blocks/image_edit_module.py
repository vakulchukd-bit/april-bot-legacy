# blocks/image_edit_module.py

import base64
import asyncio
import random
import tempfile

from openai import OpenAI

from storage import (
    get_user_plan,
    get_limits,
    get_conn,
    today
)

# 🔥 NEW (META)
from blocks.state_manager import (
    set_last_entity
)

client = OpenAI()

ADMIN_ID = 2016592532


# 🔥 ЖИВЫЕ СООБЩЕНИЯ
def get_limit_message():

    messages = [

        "Сегодня ты уже выжал максимум из редактирования 😌",

        "Я бы продолжил менять изображение, но сегодня уже предел 👀",

        "На сегодня с изображениями всё, завтра продолжим 😉",

        "Похоже, лимит на сегодня закончился. Но мы ещё можем пообщаться 🙂",

        "Сегодня лимит закончился, но я всё ещё здесь, если нужно что-то другое 👍"
    ]

    return random.choice(messages)


# ===== РЕДАКТИРОВАНИЕ ЧЕРЕЗ PATH =====
async def edit_image(
    image_path,
    prompt
):

    def run():

        try:

            print(
                "🛑 OPENAI IMAGE EDIT DISABLED (PATH)"
            )

            return None

        except Exception as e:

            print(
                "EDIT IMAGE ERROR:",
                e
            )

            return None

    return await asyncio.to_thread(run)


# ===== РЕДАКТИРОВАНИЕ ЧЕРЕЗ BYTES =====
async def edit_image_bytes(
    image_bytes,
    prompt
):

    def run():

        try:

            print(
                "🛑 OPENAI IMAGE EDIT DISABLED (BYTES)"
            )

            return None

        except Exception as e:

            print(
                "EDIT IMAGE BYTES ERROR:",
                e
            )

            return None

    return await asyncio.to_thread(run)


# ===== INCREMENT =====
def increment_images(user_id):

    conn = get_conn()

    if not conn:
        return

    uid = str(user_id)

    with conn:

        with conn.cursor() as cur:

            cur.execute(
                "SELECT images_today, last_reset FROM users WHERE user_id = %s",
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
                SET images_today = %s, last_reset = %s
                WHERE user_id = %s
                """,
                (
                    images + 1,
                    today(),
                    uid
                )
            )


# ===== PROCESS =====
async def process(
    user_id,
    prompt,
    state
):

    try:

        print(
            "🛑 IMAGE EDITING DISABLED FOR GEMINI TEST MODE"
        )

        return {

            "type": "error",

            "data":
                "⚠️ Редактирование изображений временно отключено во время Gemini migration"
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

        # 🔥 FIX: админ и premium без лимитов
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

        img = None

        # ===============================
        # 🔥 1. META ПРИОРИТЕТ
        # ===============================

        meta = state.get(
            "meta",
            {}
        )

        entity = meta.get(
            "last_entity",
            {}
        )

        image_bytes = None

        if (

            entity.get("type") == "image"
            and entity.get("data")

        ):

            print(
                "🧠 EDIT FROM META"
            )

            image_bytes = entity.get(
                "data"
            )

        # ===============================
        # 🔥 2. FALLBACK: state
        # ===============================

        if not image_bytes:

            image_bytes = state.get(
                "image_current"
            )

            if image_bytes:

                print(
                    "🧠 EDIT FROM STATE"
                )

        # ===============================
        # 🔥 3. EDIT FROM BYTES
        # ===============================

        if image_bytes:

            img = await asyncio.wait_for(

                edit_image_bytes(
                    image_bytes,
                    prompt
                ),

                timeout=40
            )

        # ===============================
        # 🔥 4. FALLBACK: PATH
        # ===============================

        if not img:

            ctx = state.get(
                "image_context"
            ) or {}

            path = ctx.get("path")

            if path:

                print(
                    "📂 EDIT FROM PATH"
                )

                img = await asyncio.wait_for(

                    edit_image(
                        path,
                        prompt
                    ),

                    timeout=40
                )

        if not img:

            print(
                "❌ EDIT FAILED"
            )

            return {

                "type": "error",

                "data": None,

                "error": "edit_failed"
            }

        # 🔥 FIX: не увеличиваем лимиты для админа и premium
        if (

            not is_admin
            and plan != "premium"

        ):

            increment_images(
                user_id
            )

        # 🔥 СОХРАНЯЕМ КАК НОВУЮ ТЕКУЩУЮ
        state["image_current"] = img

        # 🔥 META UPDATE
        set_last_entity(

            user_id,

            {
                "type": "image",
                "data": img,
                "source": "edited"
            }
        )

        print(
            "🧠 META UPDATED AFTER EDIT"
        )

        # 🔥 обновляем контекст
        state["image_context"] = {

            "type": "generated",

            "hint": prompt
        }

        return {

            "type": "image",

            "data": img
        }

    except asyncio.TimeoutError:

        print(
            "⏱ EDIT TIMEOUT"
        )

        return {

            "type": "error",

            "data": None,

            "error": "timeout"
        }

    except Exception as e:

        print(
            "🔥 EDIT ERROR:",
            e
        )

        return {

            "type": "error",

            "data": None,

            "error": str(e)
        }
