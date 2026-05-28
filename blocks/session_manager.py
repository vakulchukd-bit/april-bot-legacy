# blocks/session_manager.py

# =====================================================
# 🧠 APRIL SESSION MANAGER
# =====================================================

"""
APRIL SESSION MANAGER

ROLE:
- lightweight session continuity
- inactivity expiration
- state freshness control
- continuity-safe session lifecycle

SYSTEM DOES NOT:
- store cognition
- mutate semantic state
- control routing
- own orchestration
- serialize payloads
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

import time

# =====================================================
# 🔥 MACHINE IDENTITY
# =====================================================

APRIL_FILE_ID = "APRIL_SESSION_MANAGER"

SESSION_MACHINE_CHANNEL = {

    "type": "session_manager",

    "mode": "continuity_runtime",

    "isolated": True,

    "web_safe": True,

    "renderer_safe": True
}

# =====================================================
# 🔥 CONFIG
# =====================================================

SESSION_TTL = 60 * 60 * 12  # 12 часов

# =====================================================
# 🔥 STATE
# =====================================================

last_activity = {}

session_state = {}

# =====================================================
# 🔥 PATCH LOG
# =====================================================

SESSION_PATCH_LOG = []

def safe_session_log(msg):

    try:

        print(
            "SESSION:",
            msg
        )

        SESSION_PATCH_LOG.append(
            str(msg)
        )

    except:
        pass

safe_session_log(
    "SESSION MANAGER INITIALIZED"
)

# =====================================================
# 🔥 HELPERS
# =====================================================

def get_now():

    return time.time()


def touch_session(user_id):

    now = get_now()

    last_activity[user_id] = now

    return now


def get_last_activity(user_id):

    return last_activity.get(
        user_id
    )


# =====================================================
# 🔥 SESSION CHECK
# =====================================================

def is_session_expired(
    user_id
):

    now = get_now()

    if user_id not in last_activity:

        last_activity[user_id] = now

        safe_session_log(
            f"NEW SESSION: {user_id}"
        )

        return False

    delta = (
        now
        - last_activity[user_id]
    )

    if delta > SESSION_TTL:

        last_activity[user_id] = now

        safe_session_log(
            f"SESSION EXPIRED: {user_id}"
        )

        return True

    last_activity[user_id] = now

    return False

# =====================================================
# 🔥 SESSION STATE
# =====================================================

def get_session_state(
    user_id
):

    if user_id not in session_state:

        session_state[user_id] = {

            "created_at":
                get_now(),

            "updated_at":
                get_now(),

            "continuity_alive":
                True,

            "renderer_safe":
                True,

            "web_safe":
                True
        }

        safe_session_log(
            f"STATE CREATED: {user_id}"
        )

    return session_state[user_id]


def update_session_state(
    user_id,
    data: dict = None
):

    data = data or {}

    state = get_session_state(
        user_id
    )

    state.update(data)

    state["updated_at"] = get_now()

    touch_session(user_id)

    safe_session_log(
        f"STATE UPDATED: {user_id}"
    )

    return state

# =====================================================
# 🔥 SESSION RESET
# =====================================================

def reset_session(
    user_id
):

    if user_id in session_state:

        del session_state[user_id]

    if user_id in last_activity:

        del last_activity[user_id]

    safe_session_log(
        f"SESSION RESET: {user_id}"
    )

    return True

# =====================================================
# 🔥 SESSION CLEANUP
# =====================================================

def cleanup_expired_sessions():

    now = get_now()

    expired = []

    for user_id, ts in list(
        last_activity.items()
    ):

        if (

            now - ts
            > SESSION_TTL

        ):

            expired.append(
                user_id
            )

    for user_id in expired:

        last_activity.pop(
            user_id,
            None
        )

        session_state.pop(
            user_id,
            None
        )

        safe_session_log(
            f"CLEANUP: {user_id}"
        )

    return len(expired)
