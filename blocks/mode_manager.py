# blocks/mode_manager.py

_modes = {}


def set_mode(user_id, mode):
    _modes[user_id] = mode


def get_mode(user_id):
    return _modes.get(user_id)


def clear_mode(user_id):
    _modes.pop(user_id, None)


def has_mode(user_id):
    return user_id in _modes
