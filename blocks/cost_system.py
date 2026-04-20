# blocks/cost_system.py

from blocks.analytics_storage import load_data

# 💰 цены
TEXT_COST = 0.0005
IMAGE_COST = 0.02

# 🔥 счётчики (в памяти)
image_counter = 0


def add_image():
    global image_counter
    image_counter += 1


def calculate_cost():
    try:
        data = load_data()

        total_text = data.get("messages", 0)
        total_images = data.get("images", 0) + image_counter

        text_cost = total_text * TEXT_COST
        image_cost = total_images * IMAGE_COST

        total_cost = text_cost + image_cost

        return {
            "text": round(text_cost, 4),
            "images": round(image_cost, 4),
            "cost": round(total_cost, 4)
        }

    except Exception as e:
        print("🔥 COST ERROR:", e)

        return {
            "text": 0,
            "images": 0,
            "cost": 0
        }
