anchors = {}

def create_anchor(user_id, type_, base):
    anchors[user_id] = {
        "type": type_,
        "base": base,
        "current": base
    }

def get_anchor(user_id):
    return anchors.get(user_id)

def update_anchor(user_id, new_value):
    if user_id in anchors:
        anchors[user_id]["current"] = new_value

def clear_anchor(user_id):
    if user_id in anchors:
        del anchors[user_id]
