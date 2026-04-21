# blocks/cost_system.py

from blocks.analytics_storage import load_data, save_data

# 💰 цены
TEXT_COST = 0.0005
IMAGE_COST = 0.02


def add_image():
    data = load_data()

    # 🔥 увеличиваем счётчик
    data["images"] = data.get("images", 0) + 1

    save_data(data)


def add_text():
    data = load_data()

    # 🔥 увеличиваем сообщения
    data["messages"] = data.get("messages", 0) + 1

    save_data(data)


def calculate_cost():
    try:
        data = load_data()

        total_text = data.get("messages", 0)
        total_images = data.get("images", 0)

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
