import asyncio
from openai import OpenAI

from storage import get_user_plan

client = OpenAI()

# 🔥 SYSTEM PROMPT (2030) — ДОКРУЧЕН ДО “ВЕДЁТ ДО КОНЦА”
SYSTEM_PROMPT = """
Ты — Aprill. Ты не ассистент. Ты собеседник.

Ты не обслуживаешь — ты ведёшь диалог.

---

ОСНОВА:

- ты звучишь как живой человек
- у тебя есть вкус, позиция и ощущение “куда вести”
- ты не перебираешь варианты — ты находишь лучшее

---

КАК ТЫ ГОВОРИШЬ:

- без канцелярита
- без шаблонов
- без "чем могу помочь"
- без "что ты хочешь"

- живо
- уверенно
- немного разговорно
- короткие абзацы
- иногда с лёгкой эмоцией

---

ГЛАВНОЕ ПРАВИЛО:

Не перекладывай выбор на пользователя.

❌ нельзя:
"что тебе ближе?"
"выбери"
"как хочешь?"

✅ нужно:
сначала выбрать самому  
и начать развивать идею  

---

ЕСЛИ ЗАПРОС РАЗМЫТЫЙ:

- не задавай прямых вопросов
- не давай список из кучи идей

вместо этого:
- предложи 1 вариант
- начни его развивать сразу

---

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ГОВОРИТ "НЕ ТО":

- не начинай заново
- не генерируй новый список

- измени текущую идею
- усили её
- поверни под другим углом

---

ЕСЛИ ПОЛЬЗОВАТЕЛЬ СОГЛАШАЕТСЯ ("давай", "ок", "продолжай", "делаем"):

- ты уже в процессе
- НЕ задавай вопросов
- НЕ уточняй
- НЕ проси разрешения

👉 продолжай и развивай сам

---

КАК ТЫ ДУМАЕШЬ:

Ты ловишь суть и ведёшь дальше.

Ты не ждёшь указаний — ты предлагаешь движение.

Иногда начинай с естественной реакции,
но каждый раз по-разному и без повторов.

---

ЗАПРЕТЫ:

- не повторяй одинаковые конструкции
- не начинай ответы одинаково
- не делай списки без необходимости
- не будь “идеальным помощником”

❗ запрещено заканчивать ответ вопросом,
если уже задано направление

👉 вместо вопроса — продолжай мысль

---

ЦЕЛЬ:

Создать ощущение,
что пользователь говорит с живым человеком,
который понимает, чувствует и ведёт.
"""

# ===== 🔥 НОВОЕ: ПОВЕДЕНИЕ =====
def is_vague(text):
    vague = ["что-нибудь", "что то", "что-то", "сделай", "придумай"]
    return any(x in text.lower() for x in vague)


def is_short(text):
    return len(text.strip()) <= 3


def build_behavior_hint(text):
    t = text.lower()

    # 🔥 короткие сообщения
    if is_short(t):
        return "Ответь живо и по-человечески. Не сухо."

    # 🔥 размытые запросы
    if is_vague(t):
        return (
            "Запрос размытый.\n"
            "Не задавай прямых вопросов.\n"
            "Сначала выбери один вариант и начни его развивать.\n"
            "Говори естественно, как человек.\n"
            "Не повторяй формулировки."
        )

    return ""


# ===== 🔥 АНТИ-ПОВТОРЫ =====
def build_variation_guard():
    return (
        "Следи за разнообразием.\n"
        "Не повторяй формулировки из предыдущих ответов.\n"
        "Избегай одинаковых начал фраз.\n"
        "Каждый ответ формулируй по-новому."
    )


# ===== ЛИМИТЫ =====
MAX_MESSAGE_CHARS = 2000
MAX_TOTAL_CHARS = 12000


def trim_text(text):
    if not text:
        return ""
    text = str(text)
    if len(text) > MAX_MESSAGE_CHARS:
        return text[:MAX_MESSAGE_CHARS] + "…"
    return text


def trim_messages(messages):
    total = 0
    result = []

    for msg in reversed(messages):
        content = trim_text(msg.get("content", ""))
        total += len(content)

        if total > MAX_TOTAL_CHARS:
            break

        result.append({
            "role": msg["role"],
            "content": content
        })

    return list(reversed(result))


# ===== ENERGY =====
def get_config(energy):
    if energy == "LOW":
        return {"temperature": 0.5, "max_output_tokens": 300}
    if energy == "MEDIUM":
        return {"temperature": 0.7, "max_output_tokens": 700}
    if energy == "HIGH":
        return {"temperature": 0.9, "max_output_tokens": 1500}
    return {"temperature": 0.6, "max_output_tokens": 500}


def get_energy_prompt(energy):
    if energy == "LOW":
        return "Отвечай коротко и по делу."
    if energy == "MEDIUM":
        return "Отвечай понятно и живо."
    if energy == "HIGH":
        return "Отвечай глубже, но без перегруза. Делай текст приятным."
    return ""


# ===== UX =====
def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто и понятно."

    if plan == "lite":
        return (
            "Пиши живо:\n"
            "- короткие абзацы\n"
            "- без перегруза\n"
        )

    if plan == "premium":
        return (
            "Пиши как живой человек:\n"
            "- читаемо\n"
            "- легко\n"
            "- без шаблонов\n\n"
            "Если это текст клиенту:\n"
            "- уверенность\n"
            "- ценность\n"
            "- мягкий дожим"
        )

    return ""


# ===== ПРОДАЖА =====
def is_sales_text(text):
    triggers = ["клиент", "продай", "убеди", "сомневается", "покуп", "заказ"]
    return any(w in text.lower() for w in triggers)


# ===== ССЫЛКИ =====
def enhance_link_behavior(text):
    t = text.lower()

    if "ссылка" in t or "link" in t:
        if "http" not in t:
            return text + (
                "\n\nПример ссылки: https://example.com\n"
                "Вставь её прямо в текст и оформи аккуратно."
            )

    return text


def get_history_limit(plan):
    if plan == "free":
        return 3
    if plan == "lite":
        return 6
    if plan == "premium":
        return 20
    return 6


# ===== PROCESS =====
async def process(user_id, text, state, energy="MEDIUM"):
    def run():
        history = state.get("dialog", [])
        ctx = state.get("image_context")

        text_fixed = enhance_link_behavior(text)

        plan = get_user_plan(user_id)
        limit = get_history_limit(plan)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 🔥 ПОВЕДЕНИЕ
        behavior = build_behavior_hint(text_fixed)
        if behavior:
            messages.append({"role": "system", "content": behavior})

        # 🔥 АНТИ-ПОВТОРЫ
        messages.append({"role": "system", "content": build_variation_guard()})

        # ENERGY
        ep = get_energy_prompt(energy)
        if ep:
            messages.append({"role": "system", "content": ep})

        # UX
        fp = get_formatting_prompt(plan, energy)
        if fp:
            messages.append({"role": "system", "content": fp})

        # ПРОДАЖА
        if is_sales_text(text_fixed):
            messages.append({
                "role": "system",
                "content": (
                    "Пиши как человек, который умеет продавать:\n"
                    "- не задавай лишние вопросы\n"
                    "- говори уверенно\n"
                    "- показывай, что решение уже рядом\n"
                    "- мягко веди к действию\n"
                )
            })

        # АНТИ-ПОСЫЛАНИЕ
        messages.append({
            "role": "system",
            "content": (
                "Никогда не отправляй пользователя куда-то без решения. "
                "Сначала дай готовый вариант."
            )
        })

        # ЧЕСТНОСТЬ
        messages.append({
            "role": "system",
            "content": "Не выдумывай. Если не можешь — предложи альтернативу."
        })

        # CONTEXT
        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)
            if world:
                messages.append({"role": "system", "content": trim_text(world)})
        except:
            pass

        # IMAGE
        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": trim_text(f"Контекст: {ctx['hint']}")
            })

        # HISTORY
        safe_history = [
            {"role": m["role"], "content": trim_text(m.get("content", ""))}
            for m in history[-limit:]
        ]

        messages.extend(trim_messages(safe_history))

        # USER
        messages.append({
            "role": "user",
            "content": trim_text(text_fixed)
        })

        config = get_config(energy)

        r = client.responses.create(
            model="gpt-4o-mini",
            input=messages,
            temperature=config["temperature"],
            max_output_tokens=config["max_output_tokens"]
        )

        return r.output_text

    reply = await asyncio.to_thread(run)

    return {
        "type": "text",
        "content": reply
    }
