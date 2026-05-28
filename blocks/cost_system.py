# =====================================================
# 🧠 APRIL RESOURCE & EXECUTION COST COORDINATOR
# =====================================================

"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APRIL FILE ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

APRIL_FILE_ID:
APRIL_RESOURCE_EXECUTION_COST_COORDINATOR

ROLE:
RESOURCE_COORDINATOR

ROOM:
RESOURCE_ROOM

INPUT:
EXECUTOR_EVENTS
ROOM_ACTIVITY
PROVIDER_ACTIVITY
RENDER_ACTIVITY
WEB_CONTEXT_ACTIVITY
GENERATION_ACTIVITY

OUTPUT:
RESOURCE_ANALYTICS
EXECUTION_PRESSURE
ROOM_LOAD
PROVIDER_LOAD
ADMIN_ANALYTICS
EXECUTOR_RESOURCE_SNAPSHOT

DEPENDENCIES:
ANALYTICS_STORAGE
EXECUTOR
ADMIN_MONITOR_CORE

CRITICAL:
TRUE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 GOLDEN RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file NEVER:
- performs billing
- controls subscriptions
- exposes analytics to users
- formats frontend output
- performs orchestration

This file ONLY:
- coordinates execution resources
- tracks system pressure
- tracks provider usage
- tracks room load
- stabilizes execution awareness
- prepares admin analytics
"""

# =====================================================
# 🔥 APRIL TRACE LOGS
# =====================================================

def APRIL_LOG_IN(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_IN",

            "room":
                room,

            "file":
                "APRIL_RESOURCE_EXECUTION_COST_COORDINATOR",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass


def APRIL_LOG_OUT(
    room,
    metadata=None
):

    try:

        print({

            "type":
                "APRIL_LOG_OUT",

            "room":
                room,

            "file":
                "APRIL_RESOURCE_EXECUTION_COST_COORDINATOR",

            "metadata":
                metadata or {}
        })

    except Exception:
        pass

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
# 🔥 ANALYZER TELEMETRY
# =====================================================

def build_resource_telemetry():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "build_resource_telemetry"
        }
    )

    payload = {

        "file_id":
            "APRIL_RESOURCE_EXECUTION_COST_COORDINATOR",

        "room":
            "RESOURCE_ROOM",

        "resource_tracking":
            True,

        "execution_pressure_tracking":
            True,

        "provider_tracking":
            True,

        "room_tracking":
            True,

        "admin_analytics_ready":
            True,

        "executor_connected":
            True
    }

    APRIL_LOG_OUT(

        "RESOURCE_ROOM",

        {
            "telemetry":
                "ready"
        }
    )

    return payload

# =====================================================
# 🔥 STORAGE INITIALIZATION
# =====================================================

def ensure_resource_structure(data):

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "ensure_resource_structure"
        }
    )

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

    APRIL_LOG_OUT(

        "RESOURCE_ROOM",

        {
            "resource_structure":
                "validated"
        }
    )

    return data

# =====================================================
# 🔥 ROOM TRACKING
# =====================================================

def track_room_execution(room_name):

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "track_room_execution",

            "room_name":
                room_name
        }
    )

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

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "room_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 ROOM TRACK ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "room_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 PROVIDER TRACKING
# =====================================================

def track_provider_usage(provider):

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "track_provider_usage",

            "provider":
                provider
        }
    )

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

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "provider_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 PROVIDER TRACK ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "provider_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 TEXT EXECUTION
# =====================================================

def add_text():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "add_text"
        }
    )

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data["messages"] += 1

        save_data(data)

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "text_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 TEXT TRACK ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "text_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 IMAGE EXECUTION
# =====================================================

def add_image():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "add_image"
        }
    )

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data["images"] += 1

        save_data(data)

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "image_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 IMAGE TRACK ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "image_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 RENDERER EXECUTION
# =====================================================

def add_renderer_operation():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "add_renderer_operation"
        }
    )

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "renderer_operations"
        ] += 1

        save_data(data)

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "renderer_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 RENDER TRACK ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "renderer_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 WEB CONTEXT EXECUTION
# =====================================================

def add_web_context_operation():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "add_web_context_operation"
        }
    )

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "web_context_operations"
        ] += 1

        save_data(data)

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "web_context_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 WEB CONTEXT ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "web_context_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 LIGHTWEIGHT VISUALS
# =====================================================

def add_lightweight_visual():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "add_lightweight_visual"
        }
    )

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "lightweight_visuals"
        ] += 1

        save_data(data)

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "light_visual_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 LIGHT VISUAL ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "light_visual_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 HEAVY GENERATION
# =====================================================

def add_heavy_generation():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "add_heavy_generation"
        }
    )

    try:

        data = load_data()

        data = ensure_resource_structure(
            data
        )

        data[
            "heavy_generations"
        ] += 1

        save_data(data)

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "heavy_generation_tracking":
                    "success"
            }
        )

    except Exception as e:

        print(
            "🔥 HEAVY GENERATION ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "heavy_generation_tracking":
                    "failed"
            }
        )

# =====================================================
# 🔥 EXECUTION PRESSURE
# =====================================================

def calculate_execution_pressure():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "calculate_execution_pressure"
        }
    )

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

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "execution_pressure":
                    pressure
            }
        )

        return pressure

    except Exception as e:

        print(
            "🔥 PRESSURE ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "execution_pressure":
                    "failed"
            }
        )

        return 0.0

# =====================================================
# 🔥 RESOURCE ANALYTICS
# =====================================================

def calculate_cost():

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "calculate_cost"
        }
    )

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

        payload = {

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

            "human_visible": False,

            "telemetry":
                build_resource_telemetry()
        }

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "analytics":
                    "ready"
            }
        )

        return payload

    except Exception as e:

        print(
            "🔥 COST SYSTEM ERROR:",
            e
        )

        APRIL_LOG_OUT(

            "RESOURCE_ROOM",

            {
                "analytics":
                    "failed"
            }
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

    APRIL_LOG_IN(

        "RESOURCE_ROOM",

        {
            "action":
                "build_executor_resource_snapshot"
        }
    )

    analytics = calculate_cost()

    payload = {

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

        "machine_only": True,

        "telemetry":
            build_resource_telemetry()
    }

    APRIL_LOG_OUT(

        "RESOURCE_ROOM",

        {
            "resource_snapshot":
                "ready"
        }
    )

    return payload
