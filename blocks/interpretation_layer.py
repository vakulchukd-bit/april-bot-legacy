def interpret_request(text: str):
    t = text.lower().strip()

    # ===== ГРАФИКИ =====
    if "парабола" in t:
        return {
            "type": "math",
            "normalized": "y = x**2"
        }

    if "синус" in t:
        return {
            "type": "math",
            "normalized": "y = np.sin(x)"
        }

    if "косинус" in t:
        return {
            "type": "math",
            "normalized": "y = np.cos(x)"
        }

    if "тангенс" in t:
        return {
            "type": "math",
            "normalized": "y = np.tan(x)"
        }

    # ===== ПРОСТЫЕ ГРАФИКИ =====
    if "прямая" in t:
        return {
            "type": "math",
            "normalized": "y = x"
        }

    # ===== КОД =====
    if "кнопка" in t:
        return {
            "type": "code",
            "normalized": "создай html кнопку с обработчиком клика"
        }

    if "анимация" in t or "движется" in t:
        return {
            "type": "code",
            "normalized": "создай html css анимацию"
        }

    # ===== ЕСЛИ НИЧЕГО НЕ ПОНЯЛ =====
    return None
