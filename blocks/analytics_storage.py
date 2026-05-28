# =========================================================
# 🧠 APRIL ANALYTICS MEMORY CORE
# =========================================================

"""
APRIL ANALYTICS MEMORY CORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ROLE IN APRIL:
This file is the lightweight analytics
and activity observation core of April.

This is NOT:
- Telegram analytics
- admin authority
- memory authority
- orchestration system
- payment analytics
- subscription tracking

This file IS:
- Web analytics helper core
- activity observation system
- execution statistics layer
- usage pattern observer
- lightweight analytics memory layer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 MAIN PURPOSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This helper core helps April understand:
- execution activity
- usage pressure
- interaction statistics
- media activity
- cognitive workload patterns
- future Web analytics

It supports:
- Executor
- Admin Monitor Core
- future Web admin systems
- future analytics dashboards

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 APRIL ARCHITECTURE POSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BotRoot
 ↓
Executor
 ↓
Analytics Memory Core (THIS FILE)

This file NEVER:
- responds to users
- formats frontend output
- routes execution
- replaces memory systems
- replaces monitoring systems

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN CHANNEL RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file uses TWO isolated machine channels.

1. ANALYTICS TASK CHANNEL
Executor → Analytics Core

2. ANALYTICS RESPONSE CHANNEL
Analytics Core → Executor

Human-layer responses NEVER enter
internal analytics execution.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 IMPORTANT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT RE-ADD:
- Telegram analytics
- aiogram
- admin panels
- subscriptions
- payment systems
- frontend rendering
- orchestration logic

This file must remain:
- lightweight
- analytics-focused
- Web-oriented
- Executor-connected
- future-expandable
"""

# =========================================================
# 🔥 IMPORTS
# =========================================================

import json
import os
from datetime import datetime

# =========================================================
# 🧠 STORAGE CONFIG
# =========================================================

"""
Lightweight local analytics storage.

Can later migrate to:
- PostgreSQL
- Redis
- cloud analytics
- distributed telemetry
"""

DATA_FILE = "data/april_web_analytics.json"

# =========================================================
# 🧠 MACHINE CHANNELS
# =========================================================

ANALYTICS_TASK_CHANNEL = {

    "channel":
        "analytics_machine_task_channel",

    "isolated":
        True
}

ANALYTICS_RESPONSE_CHANNEL = {

    "channel":
        "analytics_machine_response_channel",

    "isolated":
        True
}

# =========================================================
# 🧠 SAFE STORAGE INIT
# =========================================================

def ensure_file():

    """
    Creates analytics storage safely.

    Lightweight structure only.
    """

    if not os.path.exists(DATA_FILE):

        os.makedirs(
            "data",
            exist_ok=True
        )

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump({

                "users": [],

                "messages": 0,

                "images": 0,

                "voice": 0,

                "sessions": 0,

                "last_update": None

            }, f, indent=2)

# =========================================================
# 🧠 LOAD ANALYTICS
# =========================================================

def load_data():

    """
    Safe analytics loading.
    """

    ensure_file()

    with open(

        DATA_FILE,

        "r",

        encoding="utf-8"

    ) as f:

        return json.load(f)

# =========================================================
# 🧠 SAVE ANALYTICS
# =========================================================

def save_data(data):

    """
    Safe analytics saving.
    """

    os.makedirs(
        "data",
        exist_ok=True
    )

    data["last_update"] = (
        datetime.utcnow().isoformat()
    )

    with open(

        DATA_FILE,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            data,

            f,

            indent=2
        )

# =========================================================
# 🧠 USER ACTIVITY TRACKING
# =========================================================

def add_user(user_id):

    """
    Lightweight activity registration.

    NOT identity authority.
    NOT authentication system.
    """

    data = load_data()

    users = data.get(
        "users",
        []
    )

    if user_id not in users:

        users.append(user_id)

        data["users"] = users

        save_data(data)

# =========================================================
# 🧠 EXECUTION EVENT TRACKING
# =========================================================

def add_event(

    user_id,
    event_type
):

    """
    Tracks lightweight execution activity.

    Future integrations:
    - Web admin analytics
    - execution statistics
    - cognitive workload analysis
    - room activity insights
    """

    add_user(user_id)

    data = load_data()

    # =====================================================
    # 🧠 EVENT ANALYTICS
    # =====================================================

    if event_type == "text":

        data["messages"] += 1

    elif event_type == "image":

        data["images"] += 1

    elif event_type == "voice":

        data["voice"] += 1

    elif event_type == "session":

        data["sessions"] += 1

    save_data(data)

# =========================================================
# 🧠 ANALYTICS SNAPSHOT
# =========================================================

def get_stats():

    """
    Lightweight analytics snapshot.

    Used internally by:
    - Executor
    - Admin Monitor Core
    - future Web analytics systems
    """

    data = load_data()

    return {

        "users":
            len(
                data.get(
                    "users",
                    []
                )
            ),

        "messages":
            data.get(
                "messages",
                0
            ),

        "images":
            data.get(
                "images",
                0
            ),

        "voice":
            data.get(
                "voice",
                0
            ),

        "sessions":
            data.get(
                "sessions",
                0
            ),

        "last_update":
            data.get(
                "last_update"
            )
    }

# =========================================================
# 🧠 EXECUTOR ANALYTICS PAYLOAD
# =========================================================

def build_executor_analytics_payload():

    """
    Internal analytics payload
    for Executor stabilization awareness.

    NEVER exposed directly to users.
    """

    stats = get_stats()

    return {

        "channel":
            ANALYTICS_RESPONSE_CHANNEL,

        "payload_type":
            "executor_analytics",

        "analytics": {

            "users":
                stats.get(
                    "users"
                ),

            "messages":
                stats.get(
                    "messages"
                ),

            "images":
                stats.get(
                    "images"
                ),

            "voice":
                stats.get(
                    "voice"
                ),

            "sessions":
                stats.get(
                    "sessions"
                )
        }
    }

# =========================================================
# 🧠 WEB ADMIN ANALYTICS PAYLOAD
# =========================================================

def build_admin_analytics_payload():

    """
    Future private Web admin analytics payload.

    Reserved for:
    - creator admin panel
    - execution insights
    - room analytics
    - activity statistics
    - workload analysis
    """

    stats = get_stats()

    return {

        "channel":
            ANALYTICS_RESPONSE_CHANNEL,

        "dashboard_type":
            "private_web_analytics",

        "analytics":
            stats,

        "executor_connected":
            True,

        "future_expandable":
            True
    }
