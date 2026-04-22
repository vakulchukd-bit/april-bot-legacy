import base64
import asyncio
from openai import OpenAI

client = OpenAI()


# ===== 🔥 ГЕНЕРАЦИЯ =====
async def generate_image(prompt):
    def run():
        print("🚀 START IMAGE GENERATION:", prompt)

        try:
            result = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024"
            )

            if not result or not result.data:
                print("❌ EMPTY RESULT FROM OPENAI")
                return None

            image_base64 = result.data[0].b64_json

            if not image_base64:
                print("❌ EMPTY b64_json")
                return None

            return base64.b64decode(image_base64)

        except Exception as e:
            print("🔥 IMAGE GENERATION ERROR:", e)
            return None

    return await asyncio.to_thread(run)


# ===== 🔥 ОСНОВНОЙ ПРОЦЕСС =====
async def process(user_id, text, state):
    try:
        # ===== 🔥 ВАЖНО: ВОССТАНОВЛЕНИЕ ПРОМПТА =====
        prompt = text

        # если это подтверждение — берём прошлый запрос
        if state.get("pending_action") == "generate_image":
            last = state.get("last_prompt")
            if last:
                print("♻️ USING LAST PROMPT")
                prompt = last

        # сохраняем текущий как последний
        state["last_prompt"] = prompt

        # ===== П
