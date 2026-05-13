import json
import os

DATA_FILE = "data/analytics.json"


def ensure_file():

    # =================================================
    # 🔥 SAFE FILE INIT
    # =================================================

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

                "images": 0

            }, f, indent=2)


def load_data():

    ensure_file()

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_data(data):

    os.makedirs(
        "data",
        exist_ok=True
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


# =====================================================
# 🧠 USER TRACKING
# =====================================================

def add_user(user_id):

    data = load_data()

    users = data.get(
        "users",
        []
    )

    if user_id not in users:

        users.append(user_id)

        data["users"] = users

        save_data(data)


# =====================================================
# 🧠 EVENT TRACKING
# =====================================================

def add_event(
    user_id,
    event_type
):

    # =================================================
    # 🔥 SAFE USER REGISTRATION
    # =================================================

    add_user(user_id)

    data = load_data()

    # =================================================
    # 🔥 EVENT COUNTING
    # =================================================

    if event_type == "text":

        data["messages"] += 1

    elif event_type == "image":

        data["images"] += 1

    # =================================================
    # 🔥 SAVE
    # =================================================

    save_data(data)


# =====================================================
# 🧠 ANALYTICS
# =====================================================

def get_stats():

    data = load_data()

    users = len(
        data.get(
            "users",
            []
        )
    )

    messages = data.get(
        "messages",
        0
    )

    images = data.get(
        "images",
        0
    )

    return (
        users,
        messages,
        images
    )
