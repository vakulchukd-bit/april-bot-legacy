import json
import os

DATA_FILE = "experience.json"


def load_experience():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_experience(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


def update_experience(user_id, state):
    data = load_experience()

    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "actions": []
        }

    last = state.get("last_action")

    if not last:
        return

    entry = {
        "type": last.get("type"),
        "intent": last.get("intent"),
        "status": last.get("status")
    }

    data[user_id]["actions"].append(entry)

    # ограничиваем до последних 50
    data[user_id]["actions"] = data[user_id]["actions"][-50:]

    save_experience(data)
