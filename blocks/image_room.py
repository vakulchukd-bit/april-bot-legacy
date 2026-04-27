from blocks.image_module import process as image_generate
from blocks.image_edit_module import process as image_edit
from blocks.image_system import analyze_image

from blocks.state_manager import get_image_context


class ImageRoom:
    name = "image"

    # ===== ОПРЕДЕЛЕНИЕ =====
    def can_handle(self, text, context):
        t = text.lower()

        # генерация
        if any(w in t for w in ["создай", "сгенерируй", "нарисуй", "сделай"]):
            return True

        # редактирование
        if any(w in t for w in ["убери", "добавь", "измени", "замени"]):
            return True

        # анализ
        if any(w in t for w in [
            "что на картинке",
            "что это",
            "что изображено"
        ]):
            return True

        return False

    # ===== ОЦЕНКА =====
    def evaluate(self, text, context):
        t = text.lower()

        score = 0.0

        try:
            if self.can_handle(text, context):
                score += 0.5
        except:
            pass

        # генерация
        if any(w in t for w in ["картин", "изображ", "рисунок", "арт"]):
            score += 0.4

        # короткая команда → сильный сигнал
        if any(w in t for w in ["сделай", "создай", "нарисуй"]):
            score += 0.4

        return score

    # ===== ОБРАБОТКА =====
    async def handle(self, user_id, text, context, run_with_typing):
        ctx = get_image_context(user_id)

        t = text.lower()

        # ===== РЕДАКТИРОВАНИЕ =====
        if ctx and any(w in t for w in ["убери", "добавь", "измени", "замени"]):
            path = ctx.get("path")
            if path:
                return await image_edit(user_id, path, text)

        # ===== АНАЛИЗ =====
        if ctx and any(w in t for w in [
            "что на картинке",
            "что это",
            "что изображено"
        ]):
            path = ctx.get("path")
            if path:
                return await analyze_image(user_id, path, text)

        # ===== ГЕНЕРАЦИЯ =====
        return {
            "type": "image_task",
            "prompt": text
        }
