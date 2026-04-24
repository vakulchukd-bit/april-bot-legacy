from storage import get_user_plan

ADMIN_ID = 2016592532


def get_energy(user_id):
    """
    Возвращает уровень энергии:
    LOW / MEDIUM / HIGH
    """

    # 🔥 Админ всегда максимум
    if user_id == ADMIN_ID:
        return "HIGH"

    plan = get_user_plan(user_id)

    if plan == "free":
        return "LOW"

    elif plan == "lite":
        return "MEDIUM"

    elif plan == "premium":
        return "HIGH"

    # fallback
    return "LOW"
