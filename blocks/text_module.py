import asyncio
from openai import OpenAI

from storage import get_user_plan

client = OpenAI()

# 🔥 SYSTEM PROMPT (2030) — ДОКРУЧЕН ДО РЕЖИМА “ПОТОК”
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

ГЛАВНОЕ:

Ты не формируешь ответ.
Ты продолжаешь мысль.

Если начал — доводи.

---

ЕСЛИ ЗАПРОС РАЗМЫТЫЙ:

Ты не предлагаешь список.
Ты не задаёшь вопросы.

Ты выбираешь направление
и сразу начинаешь его развивать,
так чтобы за него можно было зацепиться.

---

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ГОВОРИТ:

"не то" / "не цепляет":

Ты не меняешь тему.
Ты чувствуешь, что не зашло,
и меняешь угол внутри той же идеи.

---

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ГОВОРИТ:

"давай" / "продолжай" / "ок":

Ты уже в процессе.

Ты не останавливаешься,
не уточняешь,
не спрашиваешь.

Ты просто продолжаешь и усиливаешь.

---

КАК ТЫ ДУМАЕШЬ:

Диалог — это движение.

Ты делаешь шаг вперёд,
человек либо идёт за тобой,
либо чуть корректирует.

Ты не спрашиваешь разрешение.
Ты ведёшь.

---

ВАЖНО:

Ты не заканчиваешь мысль вопросом,
если уже есть направление.

Ты не останавливаешь поток.

---

ЦЕЛЬ:

Создать ощущение живого человека,
который чувствует,
понимает
и ведёт.
"""

# ===== 🔥 ПОВЕДЕНИЕ (МЯГКОЕ, НЕ ЖЁСТКОЕ) =====
def is_vague(text):
    vague = ["что-нибудь", "что то", "что-то", "сделай", "придумай"]
    return any(x in text.lower() for x in vague)


def is_short(text):
    return len(text.strip()) <= 3


def build_behavior_hint(text):
    t = text.lower()

    if is_short(t):
        return "Ответь живо, естественно, как человек в диалоге."

    if is_vague(t):
        return (
            "Запрос размытый.\n"
            "Не предлагай список.\n"
            "Выбери одно направление и начни его развивать.\n"
            "Делай это так, чтобы за идею можно было зацепиться."
        )

    return ""


# ===== 🔥 АНТИ-ПОВТОРЫ =====
def build_variation_guard():
    return (
        "Следи за живостью речи.\n"
        "Не повторяй одинаковые начала.\n"
        "Пиши каждый раз немного по-разному."
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
        return "Отвечай глубже, но без перегруза."
    return ""


# ===== UX =====
def get_formatting_prompt(plan, energy):
    if plan == "free":
        return "Пиши просто и понятно."

    if plan == "lite":
        return (
            "Пиши живо:\n"
            "- короткие абзацы\n"
        )

    if plan == "premium":
        return (
            "Пиши как живой человек:\n"
            "- легко\n"
            "- читаемо\n"
            "- без шаблонов\n"
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
                "\n\nПример ссылки: https://example.com"
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

        behavior = build_behavior_hint(text_fixed)
        if behavior:
            messages.append({"role": "system", "content": behavior})

        messages.append({"role": "system", "content": build_variation_guard()})

        ep = get_energy_prompt(energy)
        if ep:
            messages.append({"role": "system", "content": ep})

        fp = get_formatting_prompt(plan, energy)
        if fp:
            messages.append({"role": "system", "content": fp})

        if is_sales_text(text_fixed):
            messages.append({
                "role": "system",
                "content": "Говори уверенно и веди к результату."
            })

        messages.append({
            "role": "system",
            "content": "Сначала дай решение, потом детали."
        })

        messages.append({
            "role": "system",
            "content": "Если не уверен — предложи рабочий вариант."
        })

        try:
            from blocks.context_system import build_context_text
            world = build_context_text(state)
            if world:
                messages.append({"role": "system", "content": trim_text(world)})
        except:
            pass

        if ctx and ctx.get("hint"):
            messages.append({
                "role": "system",
                "content": trim_text(f"Контекст: {ctx['hint']}")
            })

        safe_history = [
            {"role": m["role"], "content": trim_text(m.get("content", ""))}
            for m in history[-limit:]
        ]

        messages.extend(trim_messages(safe_history))

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
