# blocks/event_system.py

from blocks.state_manager import add_dialog, update_memory_summary


def add_event(user_id, role, event_type, content):
    """
    Универсальное событие диалога
    """

    # 🔥 делаем читаемый след
    text = f"[{event_type}]: {content}"

    # 🔥 добавляем в диалог
    add_dialog(user_id, role, text)

    # 🔥 добавляем в память
    update_memory_summary(user_id, text)
