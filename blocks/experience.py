import json
import os

# =====================================================
# 🧠 APRIL EXECUTION STABILIZER
# =====================================================

"""
DeepHub upgrade:

Этот файл больше НЕ:
- execution historian;
- long-term experience memory;
- routing memory system;
- old pattern storage.

Теперь это:
- temporary execution stabilizer;
- short execution buffer;
- anti-loop helper;
- temporary retry support;
- lightweight execution continuity layer.

Главная задача:
не копить noise,
не хранить старые execution patterns,
не загрязнять orchestration,
не мешать Executor.

Файл хранит только
небольшое количество
последних execution-state
для временной stabilization support.
"""

# =====================================================
# 🔥 CONFIG
# =====================================================

DATA_FILE = "experience.json"

# DeepHub:
# только короткая temporary memory
MAX_ACTIONS = 5


# =====================================================
# 🔥 LOAD
# =====================================================

def load_experience():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            "🔥 LOAD ERROR:",
            e
        )

        return {}


# =====================================================
# 🔥 SAVE
# =====================================================

def save_experience(data):

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            "🔥 SAVE ERROR:",
            e
        )


# =====================================================
# 🔥 CLEAN
# =====================================================

def cleanup_old_actions(actions):

    """
    DeepHub philosophy:

    НЕ копим execution-history.
    НЕ создаём long-term noise.
    НЕ тащим старые execution patterns.

    Храним только небольшой
    temporary stabilization buffer.
    """

    if not isinstance(actions, list):
        return []

    return actions[-MAX_ACTIONS:]


# =====================================================
# 🔥 UPDATE EXPERIENCE
# =====================================================

def update_experience(
    user_id,
    state
):

    data = load_experience()

    user_id = str(user_id)

    if user_id not in data:

        data[user_id] = {
            "actions": []
        }

    last = state.get(
        "last_action"
    )

    if not last:

        print(
            "⚠️ last_action отсутствует"
        )

        return

    entry = {

        "type":
            last.get(
                "type",
                "unknown"
            ),

        "intent":
            last.get(
                "intent",
                "unknown"
            ),

        "status":
            last.get(
                "status",
                "unknown"
            )
    }

    print(
        "🧠 TEMP EXECUTION:",
        entry
    )

    data[user_id]["actions"].append(
        entry
    )

    # =================================================
    # 🔥 DEEPHUB STABILIZATION
    # =================================================

    data[user_id]["actions"] = (
        cleanup_old_actions(
            data[user_id]["actions"]
        )
    )

    save_experience(data)
