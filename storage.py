
import json
import os
from datetime import datetime, timezone

FILE_PATH = "data/subscriptions.json"


def load_data():
    if not os.path.exists(FILE_PATH):
        return {"users": {}}
    
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def set_subscription(user_id, days=30):
    data = load_data()
    
    expire_date = datetime.now(timezone.utc).timestamp() + days * 86400
    
    data["users"][str(user_id)] = {
        "is_subscribed": True,
        "subscription_until": expire_date
    }
    
    save_data(data)


def check_subscription(user_id):
    data = load_data()
    
    user = data["users"].get(str(user_id))
    
    if not user:
        return False
    
    if not user["is_subscribed"]:
        return False
    
    if user["subscription_until"] < datetime.now(timezone.utc).timestamp():
        return False
    
    return True
