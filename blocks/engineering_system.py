from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_code(code: str) -> str:
    prompt = f"""
Ты инженер.

Сделай анализ кода.

Формат:

🛠 ENGINEERING REPORT

Проблемы:
- ...

Решение:
(код)

Код:
{code}
"""

    r = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    )

    return r.output_text
