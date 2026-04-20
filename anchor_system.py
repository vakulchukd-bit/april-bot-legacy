# ==================== ⚓ ANCHOR SYSTEM ====================

anchors = {}


def get_anchor(user_id):
    return anchors.get(user_id)


def create_anchor(user_id, type_, base):
    anchors[user_id] = {
        "type": type_,        # image / text / voice
        "base": base,         # исходное
        "current": base,      # текущее
        "history": []         # изменения
    }


def update_anchor(user_id, new_data):
    anchor = anchors.get(user_id)
    if not anchor:
        return

    anchor["history"].append(anchor["current"])
    anchor["current"] = new_data


def clear_anchor(user_id):
    if user_id in anchors:
        del anchors[user_id]
