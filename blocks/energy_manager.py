from storage import get_user_plan

# ===== 🔥 CENTRAL CONFIG =====
# ADMIN_ID теперь берётся из единого config
# Это безопаснее для всей архитектуры April
from blocks.tariffs_config import ADMIN_ID


def get_energy(user_id):
    """
    Возвращает уровень энергии:
    LOW / MEDIUM / HIGH
    """

    # ===== 👑 ADMIN BYPASS =====
    # Админ всегда без ограничений
    if user_id == ADMIN_ID:
        return "HIGH"

    plan = get_user_plan(user_id)

    if plan == "free":
        return "LOW"

    elif plan == "lite":
        return "MEDIUM"

    elif plan == "premium":
        return "HIGH"

    # ===== FALLBACK =====
    return "LOW"
