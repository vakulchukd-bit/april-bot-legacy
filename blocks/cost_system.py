# blocks/cost_system.py

from blocks.analytics_storage import load_data

# 💰 примерные цены (можно менять)
TEXT_COST = 0.0005
IMAGE_COST = 0.02


def calculate_cost():
    data = load_data()

    total_text = 0
    total_images = 0

    for e in data["events"]:
        if e["type"] == "text":
            total_text += 1
        elif e["type"] == "image":
            total_images += 1

    total_cost = (total_text * TEXT_COST) + (total_images * IMAGE_COST)

    return {
        "text": total_text,
        "images": total_images,
        "cost": round(total_cost, 4)
    }
