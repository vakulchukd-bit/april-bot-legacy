import json
import os

DATA_FILE = "data/analytics.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": [],
            "messages": 0,
            "images": 0
        }

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_user(user_id):
    data = load_data()

    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)


def add_event(user_id, event_type):
    data = load_data()

    if event_type == "text":
        data["messages"] += 1
    elif event_type == "image":
        data["images"] += 1

    save_data(data)


def get_stats():
    data = load_data()

    users = len(data.get("users", []))
    messages = data.get("messages", 0)
    images = data.get("images", 0)

    return users, messages, images
