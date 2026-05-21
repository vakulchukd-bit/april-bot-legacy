# ===============================
# 🔥 SAFE PATCH MODE (IMAGE ROOM)
# ===============================

PATCH_LOG = []

def safe_patch_log(msg):
    try:
        print("IMAGE PATCH:", msg)
        PATCH_LOG.append(msg)
    except:
        pass


# 🔥 PATCH: контроль входа в image room
def patch_image_enter(text):
    safe_patch_log(f"IMAGE ENTER: {text[:50]}")
    return None


# 🔥 PATCH: будущая логика изображений
def patch_image_future(*args, **kwargs):
    return None


# 🔥 ДОБАВЛЕНО: защита от повторной генерации
def is_image_locked(state):
    return state.get("image_locked") is True


def lock_image(state):
    state["image_locked"] = True


def unlock_image(state):
    state["image_locked"] = False


# 🔥 NEW: мягкий reset lock (на случай зависаний)
def ensure_unlock(state):
    if state.get("image_locked") and not state.get("image_current"):
        print("⚠️ FORCE UNLOCK (no image result)")
        state["image_locked"] = False


from blocks.image_module import process as image_generate
from blocks.image_edit_module import process as image_edit
from blocks.image_system import analyze_image

from blocks.state_manager import get_image_context, get_state


class ImageRoom:
    name = "image"

    # ===== ОПРЕДЕЛЕНИЕ =====
    def can_handle(self, text, context):
        t = text.lower()

        if any(w in t for w in ["создай", "сгенерируй", "нарисуй", "сделай"]):
            return True

        if any(w in t for w in ["убери", "добавь", "измени", "замени"]):
            return True

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

        if any(w in t for w in ["картин", "изображ", "рисунок", "арт"]):
            score += 0.4

        if any(w in t for w in ["сделай", "создай", "нарисуй"]):
            score += 0.4

        return score

    # ===== ОБРАБОТКА =====
    async def handle(self, user_id, text, context, run_with_typing):
        ctx = get_image_context(user_id)
        state = get_state(user_id)

        t = text.lower()

        # 🔥 PATCH: авто-проверка залипания
        ensure_unlock(state)

        # 🔥 PATCH: защита от повторного запуска генерации
        if is_image_locked(state):
            print("⛔ IMAGE LOCKED → skip duplicate")
            return {"type": "text", "data": "⏳ Уже обрабатываю изображение..."}

        # ===== РЕДАКТИРОВАНИЕ =====
        if ctx and any(w in t for w in ["убери", "добавь", "измени", "замени"]):
            path = ctx.get("path")
            if path:
                result = await image_edit(user_id, path, text)

                # 🔥 unlock после завершения
                unlock_image(state)

                return result

        # ===== АНАЛИЗ =====
        if ctx and any(w in t for w in [
            "что на картинке",
            "что это",
            "что изображено"
        ]):
            path = ctx.get("path")

            if path:

                # ==========================================
                # 🔥 FIXED VISUAL CONTINUITY
                # ==========================================

                result = await analyze_image(
                    path,
                    state
                )

                return result

        # ===== ГЕНЕРАЦИЯ =====
        # 🔥 PATCH: ставим lock перед задачей
        lock_image(state)

        return {
            "type": "image_task",
            "prompt": text
        }
