# =========================================================
# 🧠 APRIL BOT ROOT
# =========================================================

"""
APRIL BOT ROOT — STABILIZED TRANSPORT EDITION

FIXES:
- internal machine garbage suppression
- renderer transport stabilization
- scene continuity protection
- visual memory separation
- safer telegram delivery
- voice language stabilization hooks
- hidden orchestration isolation
"""

import asyncio
import os
import threading
import traceback
import tempfile
import json
import re

from datetime import (
    datetime,
    timedelta
)

import pytz

from aiogram import (
    Bot,
    Dispatcher,
    types
)

from aiogram.types import (
    BufferedInputFile
)

from aiogram.client.session.aiohttp import (
    AiohttpSession
)

from openai import OpenAI

from io import BytesIO

# =========================================================
# 🔥 STORAGE
# =========================================================

from storage import (

    check_subscription,

    should_warn,

    can_send_message,

    set_subscription,

    get_remaining_messages,

    get_remaining_days,

    get_limits,

    get_admin_stats,

    get_user_plan,

    get_all_users,

    init_db,

    ensure_user_db,

    save_payment
)

# =========================================================
# 🧠 EXECUTOR
# =========================================================

from core.executor import (
    execute,
    EMAPS
)

# =========================================================
# 🧠 UI
# =========================================================

from blocks.ui import (
    main_keyboard
)

# =========================================================
# 🧠 STATE
# =========================================================

from blocks.state_manager import (

    set_image_context,

    get_state
)

# =========================================================
# 🧠 ERRORS
# =========================================================

from blocks.error_handler import (
    handle_error
)

# =========================================================
# 🧠 ADMIN
# =========================================================

from blocks.admin_system import (
    register_user
)

# =========================================================
# 🧠 MODES
# =========================================================

from blocks.mode_manager import (
    get_mode,
    clear_mode
)

# =========================================================
# 🧠 MAP
# =========================================================

from architecture.build_map import (
    scan_project,
    save_snapshot
)

# =========================================================
# 🔥 SUBSCRIPTION
# =========================================================

from blocks.subscription_module import (
    check as subscription_check
)

# =========================================================
# 🎤 PROVIDER ROUTER
# =========================================================

from blocks.provider_router import (
    transcribe_voice
)

# =========================================================
# 🌐 WEB
# =========================================================

from checkout_server import app

from flask import (
    request,
    jsonify
)

# =========================================================
# 🔥 TOKENS
# =========================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

# =========================================================
# 🌐 CHECKOUT DOMAIN
# =========================================================

CHECKOUT_DOMAIN = os.getenv(
    "CHECKOUT_DOMAIN",
    "https://aprill.site"
)

# =========================================================
# 🧠 BOT SESSION
# =========================================================

session = AiohttpSession(
    timeout=300
)

bot = Bot(
    token=TOKEN,
    session=session
)

dp = Dispatcher()

# =========================================================
# 🔥 CENTRAL CONFIG
# =========================================================

from blocks.tariffs_config import (
    ADMIN_ID
)

tz = pytz.timezone(
    "Europe/Kyiv"
)

# =========================================================
# 🔥 RENDER TYPES
# =========================================================

RENDERER_RESPONSE_TYPES = [

    "graph",
    "formula",
    "diagram",
    "table",
    "scene",
    "gallery",
    "layout",
    "visual",
    "function",
    "renderer_scene"
]

# =========================================================
# 🔥 INTERNAL MACHINE FILTER
# =========================================================

MACHINE_PATTERNS = [

    r"\[\[APRIL_RENDERER:",
    r"machine_state",
    r"execution_pressure",
    r"renderer_space",
    r"internal_noise",
    r"signal_overload",
    r"continuity_strength",
    r"orchestration",
    r"semantic_core",
    r"routing_chains",
    r"trajectory_locked",
    r"visual_memory",
    r"scene_stability",
    r"reasoning_state",
    r"executor",
    r"EMAPS",
    r"pipeline",
    r"traceback",
    r"syntaxerror",
]

# =========================================================
# 🔥 SAFE HELPERS
# =========================================================

def safe_string(value):

    if value is None:
        return ""

    return str(value)


def safe_truncate(
    text,
    limit=4000
):

    text = safe_string(text)

    if len(text) <= limit:
        return text

    return text[:limit] + "\n\n..."


# =========================================================
# 🔥 MACHINE GARBAGE CLEANER
# =========================================================

def remove_machine_garbage(
    text
):

    text = safe_string(text)

    lines = text.splitlines()

    cleaned = []

    for line in lines:

        lower = line.lower()

        blocked = False

        for pattern in MACHINE_PATTERNS:

            if re.search(
                pattern.lower(),
                lower
            ):

                blocked = True
                break

        if blocked:
            continue

        cleaned.append(line)

    text = "\n".join(cleaned)

    text = re.sub(
        r"\{[^\}]*machine[^\}]*\}",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\[[^\]]*renderer[^\]]*\]",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


# =========================================================
# 🔥 RESPONSE NORMALIZATION
# =========================================================

def normalize_result_payload(
    result
):

    result = result or {}

    normalized = {

        "type":
            result.get(
                "type",
                "text"
            ),

        "data":
            result.get(
                "data"
            ),

        "content":
            result.get(
                "content"
            ),

        "response":
            result.get(
                "response"
            ),

        "graph":
            result.get(
                "graph"
            ),

        "formula":
            result.get(
                "formula"
            ),

        "gallery":
            result.get(
                "gallery"
            ),

        "image":
            result.get(
                "image"
            ),

        "scene":
            result.get(
                "scene"
            ),

        "layout":
            result.get(
                "layout"
            ),

        "visual":
            result.get(
                "visual"
            ),

        "blocks":
            result.get(
                "blocks",
                []
            ),

        "continuity":
            result.get(
                "continuity",
                {}
            ),

        "active_scene":
            result.get(
                "active_scene"
            )
    }

    final_text = (

        normalized.get("content")

        or normalized.get("response")

        or (
            normalized.get("data")
            if isinstance(
                normalized.get("data"),
                str
            )
            else ""
        )

        or ""
    )

    final_text = remove_machine_garbage(
        final_text
    )

    normalized["final_text"] = final_text

    normalized["has_scene"] = any([

        normalized.get("scene"),

        normalized.get("layout"),

        normalized.get("visual"),

        normalized.get("graph"),

        normalized.get("formula"),

        normalized.get("blocks")
    ])

    return normalized

# =========================================================
# 🔥 CLEAN USER RESPONSE
# =========================================================

def cleanup_response_text(
    text,
    result_type="text"
):

    text = safe_string(text)

    if result_type in RENDERER_RESPONSE_TYPES:
        return text

    text = remove_machine_garbage(
        text
    )

    replacements = {

        "необходимо": "нужно",
        "следует": "лучше",
        "рекомендуется": "можно",
        "представлено": "видно"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return safe_truncate(
        text,
        limit=3000
    )

# =========================================================
# 🔥 SCENE STATE
# =========================================================

def build_scene_state(
    result,
    user_id
):

    state = get_state(
        user_id
    )

    if not result:
        return

    has_scene = any([

        result.get("scene"),

        result.get("layout"),

        result.get("visual"),

        result.get("graph"),

        result.get("formula")
    ])

    if not has_scene:
        return

    state["active_visual_scene"] = {

        "updated":
            datetime.now().isoformat(),

        "continuity_mode":
            "active",

        "scene":
            result.get("scene"),

        "layout":
            result.get("layout"),

        "visual":
            result.get("visual"),

        "graph":
            result.get("graph"),

        "formula":
            result.get("formula")
    }

# =========================================================
# 🔥 TELEGRAM RESPONSE
# =========================================================

async def send_telegram_response(
    message,
    result
):

    result = normalize_result_payload(
        result
    )

    result_type = result.get(
        "type",
        "text"
    )

    text = cleanup_response_text(

        result.get(
            "final_text",
            ""
        ),

        result_type=result_type
    )

    if not text.strip():

        text = (
            "⚠️ Ответ обработан, "
            "но transport вернул "
            "пустой payload."
        )

    # =====================================================
    # TEXT
    # =====================================================

    if result_type == "text":

        await message.answer(

            text,

            reply_markup=main_keyboard(
                message.message_id
            )
        )

        return

    # =====================================================
    # IMAGE
    # =====================================================

    if result_type == "image":

        await safe_send_image(
            message,
            result.get("data")
        )

        return

    # =====================================================
    # RENDERER
    # =====================================================

    if (

        result_type in RENDERER_RESPONSE_TYPES

        or result.get("has_scene")
    ):

        renderer_payload = {

            "type": result_type,

            "scene":
                result.get("scene"),

            "layout":
                result.get("layout"),

            "visual":
                result.get("visual"),

            "graph":
                result.get("graph"),

            "formula":
                result.get("formula"),

            "blocks":
                result.get(
                    "blocks",
                    []
                )
        }

        await message.answer(

            f"[[APRIL_RENDERER:{json.dumps(renderer_payload, ensure_ascii=False)}]]",

            reply_markup=main_keyboard(
                message.message_id
            )
        )

        return

    # =====================================================
    # FALLBACK
    # =====================================================

    await message.answer(

        text,

        reply_markup=main_keyboard(
            message.message_id
        )
    )

# =========================================================
# 🔥 SAFE IMAGE SEND
# =========================================================

async def safe_send_image(
    message,
    data
):

    try:

        await bot.send_chat_action(

            message.chat.id,

            "upload_photo"
        )

        await message.answer_photo(

            BufferedInputFile(

                data,

                filename="image.png"
            )
        )

    except Exception:

        bio = BytesIO(data)

        bio.name = "image.png"

        await message.answer_document(
            bio
        )

# =========================================================
# ⚡ ACTIVITY
# =========================================================

async def activity_loop(
    chat_id,
    activity_type="typing"
):

    try:

        for _ in range(120):

            await bot.send_chat_action(
                chat_id,
                activity_type
            )

            await asyncio.sleep(2)

    except Exception:
        pass


async def run_with_activity(
    chat_id,
    coro,
    activity_type="typing"
):

    task = asyncio.create_task(

        activity_loop(
            chat_id,
            activity_type
        )
    )

    try:

        return await coro

    finally:

        task.cancel()

# =========================================================
# 🌐 CHAT
# =========================================================

@app.route("/chat", methods=["POST"])
def april_web_chat():

    try:

        data = request.json or {}

        user_id = str(
            data.get(
                "user_id",
                "web_user"
            )
        )

        text = (
            data.get(
                "text",
                ""
            ).strip()
        )

        async def process():

            result = await execute(

                user_id,
                text,
                0,
                run_with_activity
            )

            normalized = normalize_result_payload(
                result
            )

            build_scene_state(
                normalized,
                user_id
            )

            return normalized

        final_result = asyncio.run(
            process()
        )

        return jsonify({

            "success": True,

            "response":
                final_result.get(
                    "final_text",
                    ""
                ),

            "type":
                final_result.get(
                    "type",
                    "text"
                ),

            "scene":
                final_result.get(
                    "scene"
                ),

            "layout":
                final_result.get(
                    "layout"
                ),

            "graph":
                final_result.get(
                    "graph"
                ),

            "formula":
                final_result.get(
                    "formula"
                ),

            "visual":
                final_result.get(
                    "visual"
                ),

            "blocks":
                final_result.get(
                    "blocks",
                    []
                )
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e)
        }), 500

# =========================================================
# 💬 TELEGRAM
# =========================================================

@dp.message()
async def handle(
    message: types.Message
):

    user_id = message.from_user.id

    ensure_user_db(user_id)

    text = (
        message.text
        or message.caption
        or ""
    )

    register_user(user_id)

    check_result = await subscription_check(

        user_id,
        "message"
    )

    if not check_result["allowed"]:

        await message.answer(
            check_result["reason"]
        )

        return

    try:

        result = await run_with_activity(

            message.chat.id,

            execute(

                user_id,

                text,

                message.chat.id,

                run_with_activity
            )
        )

        normalized = normalize_result_payload(
            result
        )

        build_scene_state(
            normalized,
            user_id
        )

        await send_telegram_response(
            message,
            normalized
        )

    except Exception as e:

        traceback.print_exc()

        await handle_error(

            bot,
            message,
            e,
            "global_handler"
        )

# =========================================================
# 🚀 MAIN
# =========================================================

async def main():

    init_db()

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)

# =========================================================
# ▶️ START
# =========================================================

if __name__ == "__main__":

    threading.Thread(

        target=lambda: app.run(

            host="0.0.0.0",

            port=int(
                os.environ.get(
                    "PORT",
                    10000
                )
            ),

            debug=False,

            use_reloader=False
        ),

        daemon=True
    ).start()

    asyncio.run(main())
