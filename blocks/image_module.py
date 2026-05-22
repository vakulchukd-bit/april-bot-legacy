# (я сохраняю полностью твою структуру, ничего не трогаю)

# ===============================
# 🔥 SAFE PATCH MODE (IMAGE MODULE)
# ===============================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("IMAGE MODULE PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


# 🔥 PATCH: контроль генерации изображения
def patch_image_generate(prompt):
    safe_patch_log(f"IMAGE GENERATE: {str(prompt)[:50]}")
    return prompt


# 🔥 PATCH: будущая логика генерации
def patch_image_module_future(*args, **kwargs):
    return None

import base64
import asyncio
from openai import OpenAI

from storage import get_user_plan, get_limits, get_conn, today

# 🔥 NEW (META)
from blocks.state_manager import set_last_entity

client = OpenAI()

ADMIN_ID = 2016592532


# 🔥 ДОБАВЛЕНО (не влияет)
def _patch_marker():
    return True


# ===== СОХРАНЕНИЕ В ПАМЯТЬ =====
def save_to_memory(state, item):
    memory = state.get("image_memory", [])

    memory.append(item)

    if len(memory) > 3:
        memory = memory[-3:]

    state["image_memory"] = memory
    state["image_context"] = item


# ===== ОЧИСТКА PROMPT =====
def clean_prompt(text: str):
    if not text:
        return ""

    t = text.strip()

    banned = ["система", "анализ личности", "контекст:", "опыт:"]
    for b in banned:
        if b in t.lower():
            t = t.lower().replace(b, "")

    return t.strip()


# ===== 🔥 НОВОЕ: EXTRACT IMAGE PROMPT =====
def extract_image_prompt(text: str):
    if not text:
        return ""

    t = text.lower()

    banned = [
        "давай", "хочу", "сделай", "создай", "нарисуй",
        "пожалуйста", "можешь", "как думаешь"
    ]

    for b in banned:
        t = t.replace(b, "")

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


# ===== V1 (РЕЗЕРВ) =====
async def generate_image(prompt):

    def run():

        try:

            print(
                "🛑 OPENAI IMAGE DISABLED (V1)"
            )

            return None

        except Exception as e:

            print(
                "IMAGE GENERATION ERROR:",
                e
            )

            return None

    return await asyncio.get_event_loop().run_in_executor(
        None,
        run
    )


# ===== V2 (ОСНОВНОЙ) =====
async def generate_image_v2(prompt):

    def run():

        try:

            print(
                "🛑 OPENAI IMAGE DISABLED (V2)"
            )

            return None

        except Exception as e:

            print(
                "IMAGE GENERATION V2 ERROR:",
                e
            )

            return None

    return await asyncio.get_event_loop().run_in_executor(
        None,
        run
    )


# ===== ИНКРЕМЕНТ =====
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
async def process(user_id, text, state):

    try:

        prompt = clean_prompt(text)
        prompt = extract_image_prompt(prompt)

        # ==========================================
        # 🔥 SAFE IMAGE PROMPT
        # ==========================================

        prompt = prompt.replace("\n", " ")

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

        prompt = prompt[:400].strip()

        # 🔥 PATCH: добавили контекст (НЕ ломает старую логику)
        if state.get("image_context", {}).get("hint"):

            prompt = (
                state["image_context"]["hint"]
                + ", "
                + prompt
            )

        if not prompt:

            return {
                "type": "error",
                "data": "❌ Пустой запрос для генерации"
            }

        is_admin = user_id == ADMIN_ID
        plan = get_user_plan(user_id)

        if not is_admin and plan == "free":

            limit = 1

            limits = get_limits(
                user_id,
                img_limit=limit
            )

            if (
                limits["images_used"]
                >= limits["images_limit"]
            ):

                return {
                    "type": "text",
                    "data": "Сегодня лимит на создание изображений исчерпан 🙂"
                }

        # ===============================
        # 🔥 SAFE TEST MODE
        # ===============================

        print(
            "🛑 IMAGE GENERATION DISABLED FOR GEMINI TEST MODE"
        )

        img = await generate_image_v2(prompt)

        if img:

            state["image_current"] = img

            set_last_entity(
                user_id,
                {
                    "type": "image",
                    "data": img,
                    "source": "v2"
                }
            )

            print(
                "🖼 IMAGE SAVED TO META (V2)"
            )

            if not is_admin and plan == "free":
                increment_images(user_id)

            save_to_memory(
                state,
                {
                    "type": "generated",
                    "source": "v2",
                    "prompt": prompt,
                    "hint": prompt,
                    "path": None
                }
            )

            return {
                "type": "image",
                "data": img
            }

        # 🔥 fallback остаётся КАК БЫЛО
        img = await generate_image(prompt)

        if img:

            state["image_current"] = img

            set_last_entity(
                user_id,
                {
                    "type": "image",
                    "data": img,
                    "source": "v1"
                }
            )

            print(
                "🖼 IMAGE SAVED TO META (V1)"
            )

            if not is_admin and plan == "free":
                increment_images(user_id)

            save_to_memory(
                state,
                {
                    "type": "generated",
                    "source": "v1",
                    "prompt": prompt,
                    "hint": prompt,
                    "path": None
                }
            )

            return {
                "type": "image",
                "data": img
            }

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception as e:

        print(
            "IMAGE MODULE ERROR:",
            e
        )

        return {
            "type": "error",
            "data": None
        }


# ===== RETRY =====
async def retry_process(user_id, text, state):

    try:

        prompt = clean_prompt(text)
        prompt = extract_image_prompt(prompt)

        if not prompt:

            return {
                "type": "final_error",
                "data": "❌ Пустой запрос"
            }

        is_admin = user_id == ADMIN_ID

        img = await generate_image_v2(prompt)

        if not img:
            img = await generate_image(prompt)

        if img:

            state["image_current"] = img

            set_last_entity(
                user_id,
                {
                    "type": "image",
                    "data": img,
                    "source": "retry"
                }
            )

            print(
                "🖼 IMAGE SAVED TO META (RETRY)"
            )

            plan = get_user_plan(user_id)

            if not is_admin and plan == "free":
                increment_images(user_id)

            save_to_memory(
                state,
                {
                    "type": "generated",
                    "source": "retry",
                    "prompt": prompt,
                    "hint": prompt,
                    "path": None
                }
            )

            return {
                "type": "image",
                "data": img
            }

        return {
            "type": "final_error",
            "data": "⚠️ Не удалось создать изображение"
        }

    except Exception as e:

        print(
            "IMAGE RETRY ERROR:",
            e
        )

        return {
            "type": "final_error",
            "data": "⚠️ Сервис временно недоступен"
        }
