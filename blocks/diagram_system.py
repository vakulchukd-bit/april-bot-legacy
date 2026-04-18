# ==================== 🟢 BLOCK: DIAGRAM SYSTEM ====================

def build_diagram_prompt(text, hidden_context=None):
    """
    Создаёт промпт для чертежей / схем
    """

    base_style = """
technical drawing, blueprint, schematic, black lines, white background,
clean geometry, minimalistic, engineering style, precise lines
"""

    if hidden_context:
        return f"{base_style}\n\n{hidden_context}\n\n{text}"

    return f"{base_style}\n\n{text}"


def is_diagram_request(text: str) -> bool:
    """
    Определяет запрос на чертёж/схему
    """

    t = text.lower()

    triggers = [
        "чертеж",
        "чертёж",
        "схема",
        "диаграмма",
        "план",
        "построй",
        "геометр",
        "параллелепипед",
        "треугольник",
        "квадрат",
        "прямоугольник"
    ]

    return any(word in t for word in triggers)
