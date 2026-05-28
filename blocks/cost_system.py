# =====================================================
# 🧠 APRIL RESOURCE & EXECUTION COST COORDINATOR
# =====================================================

"""
APRIL RESOURCE SYSTEM

ROLE:
Этот файл является внутренней
resource-coordination системой April.

=====================================================
🔥 MAIN PURPOSE
=====================================================

Система отвечает за:

- execution resource tracking;
- room execution load;
- renderer pressure tracking;
- provider usage analytics;
- lightweight/heavy execution balance;
- web execution metrics;
- internal cost coordination;
- admin analytics preparation.

=====================================================
🧠 GOLDEN APRIL ARCHITECTURE
=====================================================

INPUT MACHINE CHANNEL:
Executor → Cost Coordinator

OUTPUT MACHINE CHANNEL:
Cost Coordinator → Executor Analytics

=====================================================
🔥 IMPORTANT
=====================================================

Этот файл НЕ:

- billing system;
- subscription manager;
- telegram monetization;
- payment system;
- admin UI;
- user-facing analytics.

=====================================================
🌐 WEB-FIRST ARCHITECTURE
=====================================================

Система полностью адаптирована под:

- April Web Space;
- renderer-first execution;
- room orchestration;
- multimedia rendering;
- structured execution blocks;
- future web-admin integration.

=====================================================
🧠 RESOURCE PHILOSOPHY
=====================================================

Главная задача:
не просто считать расходы,
а помогать Executor понимать:

- execution pressure;
- renderer load;
- provider load;
- heavy generation pressure;
- orchestration balance.

=====================================================
🔥 INTERNAL CHANNEL ISOLATION
=====================================================

Machine analytics никогда
не должны попадать:

- в BotRU output;
- в user responses;
- в renderer blocks.

Только внутренние каналы.

=====================================================
"""

# =====================================================
# 🔥 IMPORTS
# =====================================================

from blocks.analytics_storage import (
    load_data,
    save_data
)

# =====================================================
# 🔥 BASE EXECUTION COSTS
# =====================================================

TEXT_COST = 0.0005

IMAGE_COST = 0.02

RENDERER_COST = 0.0015

WEB_CONTEXT_COST = 0.0008

LIGHT_VISUAL_COST = 0.001

HEAVY_RENDER_COST = 0.015

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source": "executor",
    "type": "resource_input",
    "isolated": True
}

OUTPUT_MACHINE_CHANNEL = {

    "target": "executor_analytics",
    "type": "resource_output",
    "isolated": True
}

# =====================================================
# 🔥 STORAGE INITIALIZATION
# =====================================================

def ensure_resource_structure(data):

    data.setdefault(
        "messages",
        0
    )

    data.setdefault(
        "images",
        0
    )

    data.setdefault(
        "renderer_operations",
        0
    )

    data.setdefault(
        "web_context_operations",
        0
    )

    data.setdefault(
        "lightweight_visuals",
        0
    )

    data.setdefault(
        "heavy_generations",
        0
    )

    data.setdefault(
        "rooms_usage",
        {}
    )

    data.setdefault(
        "providers_usage",
        {}
    )

    data.setdefault(
        "execution_pressure",
        0.0
    )

    return data

# =====================================================
# 🔥 ROOM TRACKING
# =====================================================

def track_room_execution(room_name):

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        rooms = data.get(
            "rooms_usage",
            {}
        )

        rooms[room_name] = (

            rooms.get(
                room_name,
                0
            ) + 1
        )

        data[
            "rooms_usage"
        ] = rooms

        save_data(data)

    except Exception as e:

        print(
            "🔥 ROOM TRACK ERROR:",
            e
        )

# =====================================================
# 🔥 PROVIDER TRACKING
# =====================================================

def track_provider_usage(provider):

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        providers = data.get(
            "providers_usage",
            {}
        )

        providers[provider] = (

            providers.get(
                provider,
                0
            ) + 1
        )

        data[
            "providers_usage"
        ] = providers

        save_data(data)

    except Exception as e:

        print(
            "🔥 PROVIDER TRACK ERROR:",
            e
        )

# =====================================================
# 🔥 TEXT EXECUTION
# =====================================================

def add_text():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data["messages"] += 1

        save_data(data)

    except Exception as e:

        print(
            "🔥 TEXT TRACK ERROR:",
            e
        )

# =====================================================
# 🔥 IMAGE EXECUTION
# =====================================================

def add_image():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data["images"] += 1

        save_data(data)

    except Exception as e:

        print(
            "🔥 IMAGE TRACK ERROR:",
            e
        )

# =====================================================
# 🔥 RENDERER EXECUTION
# =====================================================

def add_renderer_operation():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "renderer_operations"
        ] += 1

        save_data(data)

    except Exception as e:

        print(
            "🔥 RENDER TRACK ERROR:",
            e
        )

# =====================================================
# 🔥 WEB CONTEXT EXECUTION
# =====================================================

def add_web_context_operation():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "web_context_operations"
        ] += 1

        save_data(data)

    except Exception as e:

        print(
            "🔥 WEB CONTEXT ERROR:",
            e
        )

# =====================================================
# 🔥 LIGHTWEIGHT VISUALS
# =====================================================

def add_lightweight_visual():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "lightweight_visuals"
        ] += 1

        save_data(data)

    except Exception as e:

        print(
            "🔥 LIGHT VISUAL ERROR:",
            e
        )

# =====================================================
# 🔥 HEAVY GENERATION
# =====================================================

def add_heavy_generation():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "heavy_generations"
        ] += 1

        save_data(data)

    except Exception as e:

        print(
            "🔥 HEAVY GENERATION ERROR:",
            e
        )

# =====================================================
# 🔥 EXECUTION PRESSURE
# =====================================================

def calculate_execution_pressure():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        renderer_ops = data.get(
            "renderer_operations",
            0
        )

        heavy_ops = data.get(
            "heavy_generations",
            0
        )

        image_ops = data.get(
            "images",
            0
        )

        pressure = (

            renderer_ops * 0.01
            + heavy_ops * 0.08
            + image_ops * 0.03
        )

        pressure = round(
            min(
                pressure,
                1.0
            ),
            3
        )

        data[
            "execution_pressure"
        ] = pressure

        save_data(data)

        return pressure

    except Exception as e:

        print(
            "🔥 PRESSURE ERROR:",
            e
        )

        return 0.0

# =====================================================
# 🔥 RESOURCE ANALYTICS
# =====================================================

def calculate_cost():

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        total_text = data.get(
            "messages",
            0
        )

        total_images = data.get(
            "images",
            0
        )

        renderer_ops = data.get(
            "renderer_operations",
            0
        )

        web_context_ops = data.get(
            "web_context_operations",
            0
        )

        lightweight_visuals = data.get(
            "lightweight_visuals",
            0
        )

        heavy_generations = data.get(
            "heavy_generations",
            0
        )

        text_cost = (
            total_text * TEXT_COST
        )

        image_cost = (
            total_images * IMAGE_COST
        )

        renderer_cost = (
            renderer_ops * RENDERER_COST
        )

        web_context_cost = (
            web_context_ops
            * WEB_CONTEXT_COST
        )

        lightweight_cost = (
            lightweight_visuals
            * LIGHT_VISUAL_COST
        )

        heavy_cost = (
            heavy_generations
            * HEAVY_RENDER_COST
        )

        total_cost = (

            text_cost
            + image_cost
            + renderer_cost
            + web_context_cost
            + lightweight_cost
            + heavy_cost
        )

        execution_pressure = (
            calculate_execution_pressure()
        )

        return {

            # =============================================
            # 🔥 COSTS
            # =============================================

            "text_cost":
                round(text_cost, 4),

            "image_cost":
                round(image_cost, 4),

            "renderer_cost":
                round(renderer_cost, 4),

            "web_context_cost":
                round(web_context_cost, 4),

            "lightweight_visual_cost":
                round(lightweight_cost, 4),

            "heavy_generation_cost":
                round(heavy_cost, 4),

            "total_cost":
                round(total_cost, 4),

            # =============================================
            # 🔥 OPERATIONS
            # =============================================

            "messages":
                total_text,

            "images":
                total_images,

            "renderer_operations":
                renderer_ops,

            "web_context_operations":
                web_context_ops,

            "lightweight_visuals":
                lightweight_visuals,

            "heavy_generations":
                heavy_generations,

            # =============================================
            # 🔥 SYSTEM LOAD
            # =============================================

            "execution_pressure":
                execution_pressure,

            # =============================================
            # 🔥 INTERNAL ANALYTICS
            # =============================================

            "rooms_usage":

                data.get(
                    "rooms_usage",
                    {}
                ),

            "providers_usage":

                data.get(
                    "providers_usage",
                    {}
                ),

            # =============================================
            # 🔥 MACHINE FLAGS
            # =============================================

            "machine_only": True,

            "human_visible": False
        }

    except Exception as e:

        print(
            "🔥 COST SYSTEM ERROR:",
            e
        )

        return {

            "total_cost": 0,

            "execution_pressure": 0.0,

            "machine_only": True
        }

# =====================================================
# 🔥 EXECUTOR RESOURCE SNAPSHOT
# =====================================================

def build_executor_resource_snapshot():

    analytics = calculate_cost()

    return {

        "execution_pressure":

            analytics.get(
                "execution_pressure",
                0.0
            ),

        "renderer_pressure":

            analytics.get(
                "renderer_operations",
                0
            ),

        "heavy_generation_pressure":

            analytics.get(
                "heavy_generations",
                0
            ),

        "provider_load":

            analytics.get(
                "providers_usage",
                {}
            ),

        "room_load":

            analytics.get(
                "rooms_usage",
                {}
            ),

        "machine_only": True
    }
