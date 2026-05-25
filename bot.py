# =========================================================
# 🧠 APRIL BOT ROOT
# =========================================================

"""
APRIL BOT ROOT — APRIL SPACE STABILIZED

BotRoot теперь:
- web-first bridge;
- renderer-aware transport layer;
- continuity-safe gateway;
- multimodal scene connector;
- provider-safe orchestration bridge.

BotRoot больше НЕ:
- telegram-centric authority;
- renderer blocker;
- image escalation source;
- legacy transport chaos layer.

APRIL SPACE PRINCIPLES:

1. renderer-first delivery
2. web-space priority
3. continuity preservation
4. provider-safe transport
5. calm orchestration
6. multimodal scene support
"""

import asyncio
import os
import threading
import traceback
import tempfile
import json

from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer
)

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
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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

    main_keyboard,

    buy_keyboard,

    тариф_keyboard,

    payments_keyboard
)

# =========================================================
# 🧠 STATE
# =========================================================

from blocks.state_manager import (

    set_image_context,

    set_awaiting,

    add_dialog,

    get_state
)

# =========================================================
# 🧠 ANCHORS
# =========================================================

from blocks.anchor_system import (

    create_anchor,

    clear_anchor
)

# =========================================================
# 🧠 ERRORS
# =========================================================

from blocks.error_handler import (

    handle_error,

    get_errors
)

# =========================================================
# 🧠 ADMIN
# =========================================================

from blocks.admin_system import (

    register_user,

    log_event,

    get_admin_panel,

    get_system_status
)

# =========================================================
# 🧠 MODES
# =========================================================

from blocks.mode_manager import (

    get_mode,

    set_mode,

    clear_mode
)

# =========================================================
# 🧠 SESSION
# =========================================================

from blocks.session_manager import (
    is_session_expired
)

# =========================================================
# 🧠 MENUS
# =========================================================

from blocks.menu_system import (

    get_menu,

    build_tariffs_menu,

    build_info_menu
)

# =========================================================
# 🖼 IMAGE
# =========================================================

from blocks.image_module import (
    process as image_generate
)

# =========================================================
# 🧠 MAP
# =========================================================

from architecture.build_map import (

    scan_project,

    save_snapshot
)

# =========================================================
# 🔥 PAYPAL
# =========================================================

from blocks.paypal_module import (

    create_payment,

    capture_payment,

    get_order
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

    ADMIN_ID,

    LITE_PRICE,

    PREMIUM_PRICE
)

tz = pytz.timezone(
    "Europe/Kyiv"
)

# =========================================================
# 🔥 TELEGRAM LEGACY SUPPRESSION
# =========================================================

"""
Telegram теперь:
- passive transport layer;
- compatibility bridge;
- optional UI endpoint.

Telegram больше НЕ:
- главный execution path;
- authority layer;
- visual routing source;
- orchestration core.
"""

TELEGRAM_LEGACY_MODE = False

# =========================================================
# 🔥 RENDERER RESPONSE TYPES
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


def safe_renderer_payload(payload):

    if payload is None:
        return ""

    if isinstance(payload, dict):

        try:

            return json.dumps(

                payload,

                ensure_ascii=False
            )

        except Exception:

            return str(payload)

    return str(payload)

# =========================================================
# 🔥 RESULT NORMALIZATION
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
                "data",
                ""
            ),

        "content":
            result.get(
                "content",
                ""
            ),

        "response":
            result.get(
                "response",
                ""
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
            )
    }

    normalized["final_text"] = (

        normalized["content"]

        or normalized["response"]

        or normalized["data"]

        or ""
    )

    return normalized

# =========================================================
# 🔥 RESPONSE CLEANUP
# =========================================================

def cleanup_response_text(
    text,
    user_text=""
):

    text = safe_string(text)

    lower_user_text = (
        user_text or ""
    ).lower()

    visual_words = [

        "что на фото",
        "что это",
        "что изображено",
        "что видишь",
        "посмотри",
        "проанализируй",
        "объясни фото"
    ]

    if any(
        w in lower_user_text
        for w in visual_words
    ):

        text = (
            text
            .replace(
                "На изображении",
                ""
            )
            .replace(
                "На данной фотографии",
                ""
            )
            .replace(
                "Изображение показывает",
                ""
            )
            .strip()
        )

    replacements = {

        "необходимо": "нужно",
        "следует": "лучше",
        "рекомендуется": "можно",
        "пользователь": "человек",
        "представлено": "видно"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return safe_truncate(
        text,
        limit=1400
    )

# =========================================================
# 🔥 RENDERER DELIVERY
# =========================================================

async def send_renderer_response(
    message,
    result,
    result_type
):

    renderer_payload = (

        result.get("scene")

        or result.get("layout")

        or result.get("visual")

        or result.get("graph")

        or result.get("formula")

        or result.get("data")

        or ""
    )

    renderer_payload = safe_renderer_payload(
        renderer_payload
    )

    renderer_payload = safe_truncate(
        renderer_payload,
        limit=3500
    )

    await message.answer(

        f"[[{result_type}:{renderer_payload}]]",

        reply_markup=main_keyboard(
            message.message_id
        )
    )

# =========================================================
# 🔥 SAFE TELEGRAM RESPONSE
# =========================================================

async def send_telegram_response(
    message,
    result,
    user_text=""
):

    result = normalize_result_payload(
        result
    )

    result_type = result.get(
        "type",
        "text"
    )

    result_data = cleanup_response_text(

        result.get(
            "final_text",
            ""
        ),

        user_text=user_text
    )

    # =====================================================
    # 🔥 TEXT
    # =====================================================

    if result_type == "text":

        await message.answer(

            result_data,

            reply_markup=main_keyboard(
                message.message_id
            )
        )

        return

    # =====================================================
    # 🔥 IMAGE
    # =====================================================

    if result_type == "image":

        await safe_send_image(
            message,
            result.get("data")
        )

        return

    # =====================================================
    # 🔥 RENDERER-FIRST DELIVERY
    # =====================================================

    if result_type in RENDERER_RESPONSE_TYPES:

        await send_renderer_response(

            message=message,

            result=result,

            result_type=result_type
        )

        return

    # =====================================================
    # 🔥 HYBRID
    # =====================================================

    if result_type == "hybrid":

        text_part = safe_string(
            result.get("text")
        )

        image_part = result.get(
            "image"
        )

        if text_part:

            await message.answer(

                cleanup_response_text(
                    text_part,
                    user_text
                ),

                reply_markup=main_keyboard(
                    message.message_id
                )
            )

        if image_part:

            await safe_send_image(
                message,
                image_part
            )

        return

    # =====================================================
    # 🔥 REFERENCE
    # =====================================================

    if result_type == "reference":

        await message.answer(

            result_data,

            reply_markup=main_keyboard(
                message.message_id
            )
        )

        return

    # =====================================================
    # 🔥 UNKNOWN SAFE FALLBACK
    # =====================================================

    await message.answer(

        safe_truncate(
            result_data,
            limit=1400
        ),

        reply_markup=main_keyboard(
            message.message_id
        )
    )

# =========================================================
# ⏰ TIME QUESTIONS
# =========================================================

def is_time_question(
    text: str
):

    text = text.lower()

    return any(

        t in text

        for t in [

            "сколько времени",
            "который час",
            "какая дата",
            "какой сегодня день"
        ]
    )

# =========================================================
# ⌨️ ACTIVITY LOOP
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

# =========================================================
# ⚡ RUN WITH ACTIVITY
# =========================================================

async def run_with_activity(
    chat_id,
    coro,
    activity_type="typing"
):

    if not chat_id:

        try:

            return await coro

        except Exception as e:

            print(
                "WEB ACTIVITY ERROR:",
                e
            )

            traceback.print_exc()

            raise e

    await asyncio.sleep(0)

    task = asyncio.create_task(

        activity_loop(
            chat_id,
            activity_type
        )
    )

    try:

        result = await coro

        await asyncio.sleep(0.1)

        return result

    finally:

        task.cancel()

# =========================================================
# 🌐 WEB CHAT ENDPOINT
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

        if not text:

            return jsonify({

                "success": False,

                "error": "EMPTY_TEXT"
            }), 400

        async def process():

            result = await execute(

                user_id,
                text,
                0,
                run_with_activity
            )

            return normalize_result_payload(
                result
            )

        final_result = asyncio.run(
            process()
        )

        print(
            "FINAL RESULT:",
            final_result.get(
                "type"
            )
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

            "blocks":
                final_result.get(
                    "blocks",
                    []
                ),

            "graph":
                final_result.get(
                    "graph"
                ),

            "formula":
                final_result.get(
                    "formula"
                ),

            "gallery":
                final_result.get(
                    "gallery"
                ),

            "scene":
                final_result.get(
                    "scene"
                ),

            "layout":
                final_result.get(
                    "layout"
                ),

            "visual":
                final_result.get(
                    "visual"
                ),

            "image":
                final_result.get(
                    "image"
                )
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e)
        }), 500

# =========================================================
# 🌐 RUN SERVER
# =========================================================

def run_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False,

        use_reloader=False
    )

# =========================================================
# 🎤 WEB VOICE ENDPOINT
# =========================================================

@app.route("/voice", methods=["POST"])
def web_voice():

    try:

        audio = request.files.get(
            "audio"
        )

        if not audio:

            return jsonify({
                "error": "No audio"
            }), 400

        with tempfile.NamedTemporaryFile(

            suffix=".webm",

            delete=False

        ) as temp:

            audio.save(temp.name)

            text = asyncio.run(

                transcribe_voice(
                    temp.name
                )
            )

        return jsonify({

            "success": True,

            "text": text
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e)
        }), 500

# =========================================================
# 🌐 WEB IMAGE ENDPOINT
# =========================================================

@app.route("/image", methods=["POST"])
def web_image():

    try:

        image = request.files.get(
            "image"
        )

        if not image:

            return jsonify({

                "success": False,

                "error": "NO_IMAGE"
            }), 400

        user_id = request.form.get(
            "user_id",
            "web_user"
        )

        temp_path = tempfile.mktemp(
            suffix=".jpg"
        )

        image.save(temp_path)

        async def process():

            from blocks.image_system import (
                analyze_image
            )

            state = get_state(
                user_id
            )

            result = await analyze_image(
                temp_path,
                state
            )

            state[
                "active_visual_scene"
            ] = {

                "source": "web_image",

                "summary": safe_string(
                    result
                )[:600],

                "path": temp_path,

                "timestamp":
                    datetime.now().isoformat(),

                "objects": [],

                "continuity_mode":
                    "active"
            }

            return result

        result = asyncio.run(
            process()
        )

        return jsonify({

            "success": True,

            "response":
                safe_truncate(
                    result,
                    limit=1200
                )
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error": str(e)
        }), 500

# =========================================================
# 🖼 SAFE IMAGE SEND
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
            ),

            reply_markup=main_keyboard(
                message.message_id
            )
        )

    except Exception:

        bio = BytesIO(data)

        bio.name = "image.png"

        await bot.send_chat_action(

            message.chat.id,

            "upload_document"
        )

        await message.answer_document(

            bio,

            reply_markup=main_keyboard(
                message.message_id
            )
        )

# =========================================================
# 🌐 WEB MESSAGE PROCESSOR
# =========================================================

async def process_web_message(
    user_id,
    text
):

    result = await execute(

        user_id,
        text,
        0,
        run_with_activity
    )

    return normalize_result_payload(
        result
    )

# =========================================================
# 💬 MESSAGE HANDLER
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

    if text.strip().lower() == "/map":

        snapshot = scan_project()

        snapshot["emaps"] = {

            "active_systems": list(

                EMAPS.get(
                    "active_systems",
                    []
                )
            ),

            "active_rooms": list(

                EMAPS.get(
                    "active_rooms",
                    []
                )
            ),

            "routing_chains":

                EMAPS.get(
                    "routing_chains",
                    []
                ),

            "task_types": list(

                EMAPS.get(
                    "task_types",
                    []
                )
            )
        }

        pretty = json.dumps(

            snapshot,

            indent=2,

            ensure_ascii=False
        )

        pretty = safe_truncate(
            pretty,
            limit=4000
        )

        await message.answer(

            f"🧠 APRIL MAP\n\n"
            f"<pre>{pretty}</pre>",

            parse_mode="HTML"
        )

        return

    # =====================================================
    # 🎤 VOICE
    # =====================================================

    if message.voice:

        file = await bot.get_file(
            message.voice.file_id
        )

        path = f"{user_id}.ogg"

        await bot.download_file(

            file.file_path,

            destination=path
        )

        text = await transcribe_voice(
            path
        )

        if not safe_string(text).strip():

            await message.answer(
                "🎤 Не расслышал"
            )

            return

        await message.answer(
            f"🎤 {text}"
        )

    # =====================================================
    # 🖼 IMAGE INPUT
    # =====================================================

    if message.photo:

        photo = message.photo[-1]

        file = await bot.get_file(
            photo.file_id
        )

        path = f"{user_id}_image.jpg"

        await bot.download_file(

            file.file_path,

            destination=path
        )

        set_image_context(user_id, {

            "type": "uploaded",

            "path": path
        })

        state = get_state(
            user_id
        )

        from blocks.image_system import (
            analyze_image
        )

        from blocks.event_system import (
            add_event
        )

        analysis = await analyze_image(
            path,
            state
        )

        state[
            "active_visual_scene"
        ] = {

            "source": "telegram_image",

            "summary": safe_string(
                analysis
            )[:600],

            "path": path,

            "timestamp":
                datetime.now().isoformat(),

            "objects": [],

            "continuity_mode":
                "active"
        }

        add_event(

            user_id,

            "user",

            "image_uploaded",

            {

                "text": analysis,

                "path": path
            }
        )

        await message.answer(

            "📸 Изображение получено. "
            "Можешь работать с ним."
        )

        return

    # =====================================================
    # ⏰ TIME
    # =====================================================

    state = get_state(
        user_id
    )

    now = datetime.now(tz)

    state["time_str"] = now.strftime(
        "%H:%M"
    )

    state["date_str"] = now.strftime(
        "%d.%m.%Y"
    )

    if is_time_question(text):

        await message.answer(

            f"🕒 {state['time_str']}\n"
            f"📅 {state['date_str']}"
        )

        return

    # =====================================================
    # 👤 REGISTER USER
    # =====================================================

    register_user(user_id)

    # =====================================================
    # 🔥 SUB CHECK
    # =====================================================

    check_result = await subscription_check(

        user_id,

        "message"
    )

    if not check_result["allowed"]:

        await message.answer(
            check_result["reason"]
        )

        return

    # =====================================================
    # 📢 MODE
    # =====================================================

    mode = get_mode(
        user_id
    )

    if (
        user_id == ADMIN_ID
        and mode == "broadcast"
    ):

        users = get_all_users()

        success = 0

        for uid in users:

            if int(uid) == ADMIN_ID:
                continue

            try:

                await bot.send_message(
                    uid,
                    f"📢 {text}"
                )

                success += 1

            except Exception:
                pass

        clear_mode(user_id)

        await message.answer(
            f"✅ Рассылка отправлена: {success}"
        )

        return

    # =====================================================
    # 🧠 ACTIVITY DETECTION
    # =====================================================

    activity_type = "typing"

    image_words = [

        "нарисуй",
        "создай изображение",
        "сгенерируй",
        "картинку",
        "изображение",
        "арт",
        "фото"
    ]

    text_lower = text.lower()

    if any(
        word in text_lower
        for word in image_words
    ):

        activity_type = (
            "upload_photo"
        )

    # =====================================================
    # 🧠 EXECUTOR
    # =====================================================

    try:

        result = await run_with_activity(

            message.chat.id,

            execute(

                user_id,

                text,

                message.chat.id,

                run_with_activity
            ),

            activity_type=activity_type
        )

        await send_telegram_response(

            message,

            result,

            user_text=text
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
# 🔘 CALLBACKS
# =========================================================

@dp.callback_query()
async def handle_callbacks(
    callback: types.CallbackQuery
):

    data = callback.data
    user_id = callback.from_user.id

    if data.startswith("like_"):

        state = get_state(user_id)

        state["last_action"] = {

            "type": "feedback",

            "intent": "like",

            "status": "positive"
        }

        await callback.answer("👍")

        return

    if data.startswith("dislike_"):

        state = get_state(user_id)

        state["last_action"] = {

            "type": "feedback",

            "intent": "dislike",

            "status": "negative"
        }

        await callback.answer("👎")

        return

    if data == "menu":

        text, keyboard = get_menu(
            user_id
        )

        await callback.message.answer(

            text,

            reply_markup=keyboard
        )

        await callback.answer()

        return

    if data == "info":

        text, keyboard = build_info_menu(
            user_id
        )

        await callback.message.answer(

            text,

            reply_markup=keyboard
        )

        await callback.answer()

        return

    if user_id == ADMIN_ID:

        if data == "admin_stats":

            errors = get_errors()

            text = "📊 Анализ\n\n"

            text += (

                "✅ Ошибок нет"

                if not errors

                else "\n".join(
                    errors[-5:]
                )
            )

            await callback.answer(

                text[:200],

                show_alert=True
            )

            return

        if data == "admin_payments":

            keyboard = InlineKeyboardMarkup(

                inline_keyboard=[

                    [

                        InlineKeyboardButton(

                            text="💳 OpenAI",

                            url="https://platform.openai.com/account/billing"
                        )
                    ],

                    [

                        InlineKeyboardButton(

                            text="🚂 Railway",

                            url="https://railway.app/dashboard"
                        )
                    ],

                    [

                        InlineKeyboardButton(

                            text="⬅️ Назад",

                            callback_data="menu"
                        )
                    ]
                ]
            )

            await callback.message.answer(

                "💳 Оплаты:",

                reply_markup=keyboard
            )

            await callback.answer()

            return

        if data == "admin_broadcast":

            set_mode(
                user_id,
                "broadcast"
            )

            await callback.answer(

                "📢 Введи текст",

                show_alert=True
            )

            return

        if data == "admin_system":

            text = get_system_status()

            await callback.message.answer(
                text
            )

            await callback.answer()

            return

    if data in [

        "buy_lite",
        "lite",
        "go_lite"
    ]:

        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="💳 Карта / PayPal",

                        url=f"{CHECKOUT_DOMAIN}/checkout/lite/{user_id}"
                    )
                ],

                [

                    InlineKeyboardButton(

                        text="🤖 Android • Google Pay",

                        url=f"{CHECKOUT_DOMAIN}/open/lite/{user_id}"
                    )
                ]
            ]
        )

        await callback.message.answer(

            "⚡ Lite Пакет",

            reply_markup=keyboard
        )

        await callback.answer()

        return

    if data in [

        "buy_premium",
        "premium",
        "go_premium"
    ]:

        keyboard = InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="💳 Карта / PayPal",

                        url=f"{CHECKOUT_DOMAIN}/checkout/premium/{user_id}"
                    )
                ],

                [

                    InlineKeyboardButton(

                        text="🤖 Android • Google Pay",

                        url=f"{CHECKOUT_DOMAIN}/open/premium/{user_id}"
                    )
                ]
            ]
        )

        await callback.message.answer(

            "👑 Premium Пакет",

            reply_markup=keyboard
        )

        await callback.answer()

        return

    await callback.answer()

# =========================================================
# 🧠 APRIL MAP AUTO UPDATE
# =========================================================

try:

    snapshot = scan_project()

    save_snapshot(snapshot)

    print(
        "🧠 APRIL MAP AUTO-UPDATED"
    )

except Exception as e:

    print(
        "MAP ERROR:",
        e
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

        target=run_server,

        daemon=True
    ).start()

    asyncio.run(main())
