# blocks/mode_manager.py

modes = {}


def set_mode(user_id, mode):
    modes[user_id] = mode


def get_mode(user_id):
    return modes.get(user_id, None)


def clear_mode(user_id):
    if user_id in modes:
        del modes[user_id]
