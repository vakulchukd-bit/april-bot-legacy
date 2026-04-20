import json
import os

FILE = "data/analytics.json"


def load_data():
    if not os.path.exists(FILE):
        return {"users": [], "events": []}

    with open(FILE, "r") as f:
        return json.load(f)


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(FILE, "w") as f:
        json.dump(data, f)


def add_user(user_id):
    data = load_data()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)


def add_event(user_id, event_type):
    data = load_data()

    data["events"].append({
        "user_id": user_id,
        "type": event_type
    })

    save_data(data)


def get_stats():
    data = load_data()

    users = len(data["users"])
    messages = sum(1 for e in data["events"] if e["type"] == "text")
    images = sum(1 for e in data["events"] if e["type"] == "image")

    return users, messages, images
