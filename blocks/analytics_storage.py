# =========================================================
# 🧠 APRIL ANALYTICS MEMORY CORE
# =========================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_ANALYTICS_MEMORY_CORE

ROLE:
LIGHTWEIGHT_ANALYTICS_MEMORY_SYSTEM

ROOM:
ANALYTICS_ROOM

INPUT:
EXECUTOR_ANALYTICS_SIGNAL
USER_ACTIVITY_SIGNAL
SESSION_ACTIVITY_SIGNAL
VOICE_ACTIVITY_SIGNAL
IMAGE_ACTIVITY_SIGNAL
ADMIN_ANALYTICS_REQUEST

OUTPUT:
ANALYTICS_PAYLOAD
EXECUTION_STATISTICS
ACTIVITY_OBSERVATION
ADMIN_TELEMETRY
ANALYZER_DATA

DEPENDENCIES:
EXECUTOR
ADMIN_MONITOR_CORE
WEB_ADMIN_SPACE
ANALYZER_SYSTEM

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER:
- performs cognition
- replaces memory systems
- controls orchestration
- formats frontend output

This file ONLY:
- tracks activity
- stabilizes analytics
- exposes telemetry-safe statistics
- preserves lightweight analytics continuity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ANALYZER VISIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analyzer may observe:
- execution activity
- usage pressure
- interaction statistics
- activity growth
- analytics continuity
- workload stabilization

Analyzer may NEVER:
- alter analytics
- inject orchestration
- replace Executor authority
"""

# =========================================================
# 🔥 IMPORTS
# =========================================================

import json
import os

from datetime import datetime

# =========================================================
# 🔥 APRIL TRACE LOGS
# =========================================================

def APRIL_LOG_IN(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_IN",

            "room":
                room,

            "file":
                "APRIL_ANALYTICS_MEMORY_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass


def APRIL_LOG_OUT(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_OUT",

            "room":
                room,

            "file":
                "APRIL_ANALYTICS_MEMORY_CORE",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

# =========================================================
# 🧠 STORAGE CONFIG
# =========================================================

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

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "ensure_file"
        }
    )

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

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "storage_ready"
        }
    )

# =========================================================
# 🧠 LOAD ANALYTICS
# =========================================================

def load_data():

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "load_data"
        }
    )

    ensure_file()

    with open(

        DATA_FILE,

        "r",

        encoding="utf-8"

    ) as f:

        data = json.load(f)

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "data_loaded"
        }
    )

    return data

# =========================================================
# 🧠 SAVE ANALYTICS
# =========================================================

def save_data(data):

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "save_data"
        }
    )

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

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "data_saved"
        }
    )

# =========================================================
# 🧠 USER ACTIVITY TRACKING
# =========================================================

def add_user(user_id):

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "add_user",

            "user_id":
                user_id
        }
    )

    data = load_data()

    users = data.get(
        "users",
        []
    )

    if user_id not in users:

        users.append(user_id)

        data["users"] = users

        save_data(data)

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "user_registered"
        }
    )

# =========================================================
# 🧠 EXECUTION EVENT TRACKING
# =========================================================

def add_event(

    user_id,
    event_type
):

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "add_event",

            "event_type":
                event_type
        }
    )

    add_user(user_id)

    data = load_data()

    if event_type == "text":

        data["messages"] += 1

    elif event_type == "image":

        data["images"] += 1

    elif event_type == "voice":

        data["voice"] += 1

    elif event_type == "session":

        data["sessions"] += 1

    save_data(data)

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "event_saved",

            "event_type":
                event_type
        }
    )

# =========================================================
# 🧠 ANALYTICS SNAPSHOT
# =========================================================

def get_stats():

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "get_stats"
        }
    )

    data = load_data()

    stats = {

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

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "stats_ready"
        }
    )

    return stats

# =========================================================
# 🧠 ANALYZER TELEMETRY
# =========================================================

def build_analytics_telemetry_payload():

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "build_analytics_telemetry_payload"
        }
    )

    stats = get_stats()

    payload = {

        "file_id":
            "APRIL_ANALYTICS_MEMORY_CORE",

        "room":
            "ANALYTICS_ROOM",

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
            ),

        "last_update":
            stats.get(
                "last_update"
            ),

        "analytics_active":
            True,

        "executor_connected":
            True
    }

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "analytics_telemetry_ready"
        }
    )

    return payload

# =========================================================
# 🧠 EXECUTOR ANALYTICS PAYLOAD
# =========================================================

def build_executor_analytics_payload():

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "build_executor_analytics_payload"
        }
    )

    stats = get_stats()

    payload = {

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

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "executor_analytics_ready"
        }
    )

    return payload

# =========================================================
# 🧠 WEB ADMIN ANALYTICS PAYLOAD
# =========================================================

def build_admin_analytics_payload():

    APRIL_LOG_IN(

        "ANALYTICS_ROOM",

        {
            "action":
                "build_admin_analytics_payload"
        }
    )

    stats = get_stats()

    payload = {

        "channel":
            ANALYTICS_RESPONSE_CHANNEL,

        "dashboard_type":
            "private_web_analytics",

        "analytics":
            stats,

        "telemetry":
            build_analytics_telemetry_payload(),

        "executor_connected":
            True,

        "future_expandable":
            True
    }

    APRIL_LOG_OUT(

        "ANALYTICS_ROOM",

        {
            "action":
                "admin_analytics_ready"
        }
    )

    return payload
