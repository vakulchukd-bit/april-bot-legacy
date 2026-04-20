# blocks/session_manager.py

import time

SESSION_TTL = 60 * 60 * 12  # 12 часов

last_activity = {}


def is_session_expired(user_id):
    now = time.time()

    if user_id not in last_activity:
        last_activity[user_id] = now
        return False

    if now - last_activity[user_id] > SESSION_TTL:
        last_activity[user_id] = now
        return True

    last_activity[user_id] = now
    return False
