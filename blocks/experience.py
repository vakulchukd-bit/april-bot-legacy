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
    except Exception as e:
        print("🔥 SAVE ERROR:", e)


def update_experience(user_id, state):
    data = load_experience()

    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            "actions": []
        }

    last = state.get("last_action")

    if not last:
        print("⚠️ last_action отсутствует")
        return

    entry = {
        "type": last.get("type", "unknown"),
        "intent": last.get("intent", "unknown"),
        "status": last.get("status", "unknown")
    }

    print("🧠 SAVE EXPERIENCE:", entry)

    data[user_id]["actions"].append(entry)
    data[user_id]["actions"] = data[user_id]["actions"][-50:]

    save_experience(data)
