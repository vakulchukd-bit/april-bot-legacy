def detect_energy(text: str, intent: str, room: str) -> str:
    t = text.lower()

    if intent == "generate":
        return "HIGH"

    if room in ["image", "engineering"]:
        return "HIGH"

    if any(w in t for w in ["подробно", "развернуто", "глубже"]):
        return "HIGH"

    if any(w in t for w in ["кратко", "быстро"]):
        return "LOW"

    return "MEDIUM"


def apply_subscription_limit(energy: str, plan: str) -> str:
    limits = {
        "free": ["LOW"],
        "lite": ["LOW", "MEDIUM"],
        "premium": ["LOW", "MEDIUM", "HIGH"]
    }

    allowed = limits.get(plan, ["LOW"])

    if energy in allowed:
        return energy

    if "MEDIUM" in allowed:
        return "MEDIUM"

    return "LOW"
