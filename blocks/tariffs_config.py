# =========================================================
# 🧠 APRIL TARIFF CONFIG
# =========================================================

"""
APRIL WEB ADMIN TARIFF CONFIG

ROLE:
- centralized tariffs source
- web-admin compatible config
- runtime-safe limits architecture
- future TXT-config integration
- admin panel synchronization layer

IMPORTANT:
Этот файл больше НЕ хранит:
- hardcoded telegram logic
- static admin IDs
- transport-specific assumptions

Теперь:
admin/web system может:
- подменять runtime config
- загружать TXT tariffs
- управлять лимитами из web panel
- менять pricing без patching кода
"""

# =========================================================
# 🔥 FILE ID
# =========================================================

APRIL_FILE_ID = "APRIL_WEB_TARIFF_CONFIG"

APRIL_CONFIG_VERSION = "WEB_ADMIN_READY"

# =========================================================
# 🔥 SYSTEM FLAGS
# =========================================================

TARIFFS_ENABLED = True

PAYMENTS_ENABLED = False

WEB_ADMIN_READY = True

TXT_CONFIG_READY = True

RUNTIME_OVERRIDE_ALLOWED = True

HOT_RELOAD_ALLOWED = False

# =========================================================
# 🔥 ADMIN INTEGRATION
# =========================================================

"""
ВАЖНО:

Admin ID больше НЕ хранится здесь.

Web admin:
- должен брать admin/session/auth
из:
- database
- auth layer
- admin backend
- runtime session

Этот файл:
ТОЛЬКО про тарифы.
"""

ADMIN_RUNTIME_CONTROL = True

ADMIN_RUNTIME_PROVIDER = "web_admin"

# =========================================================
# 🆓 FREE
# =========================================================

FREE_PLAN_ID = "free"

FREE_TITLE = "Free"

FREE_ENABLED = True

FREE_PRICE = 0

FREE_DURATION_DAYS = 999999

# =========================================================
# 🔥 LIMITS
# =========================================================

FREE_MESSAGES_LIMIT = 10

FREE_IMAGES_LIMIT = 1

FREE_HISTORY_LIMIT = 3

FREE_MEMORY_MODE = "compact"

FREE_CONTEXT_WINDOW = "small"

# =========================================================
# 🔥 RESET POLICY
# =========================================================

FREE_RESET_HOURS = 24

# =========================================================
# 🔥 FEATURES
# =========================================================

FREE_FEATURES = {

    "text": True,

    "image_generation": True,

    "image_edit": True,

    "renderer": True,

    "web": True,

    "memory_extended": False,

    "priority_provider": False,

    "priority_queue": False,

    "experimental_features": False
}

# =========================================================
# ⚡ LITE
# =========================================================

LITE_PLAN_ID = "lite"

LITE_TITLE = "Lite"

LITE_ENABLED = True

LITE_PRICE = 12

LITE_DURATION_DAYS = 5

# =========================================================
# 🔥 LIMITS
# =========================================================

LITE_MESSAGES_LIMIT = -1

LITE_IMAGES_LIMIT = 15

LITE_HISTORY_LIMIT = 5

LITE_MEMORY_MODE = "balanced"

LITE_CONTEXT_WINDOW = "medium"

# =========================================================
# 🔥 RESET POLICY
# =========================================================

LITE_RESET_HOURS = 12

# =========================================================
# 🔥 FEATURES
# =========================================================

LITE_FEATURES = {

    "text": True,

    "image_generation": True,

    "image_edit": True,

    "renderer": True,

    "web": True,

    "memory_extended": True,

    "priority_provider": True,

    "priority_queue": True,

    "experimental_features": False
}

# =========================================================
# 👑 PREMIUM
# =========================================================

PREMIUM_PLAN_ID = "premium"

PREMIUM_TITLE = "Premium"

PREMIUM_ENABLED = True

PREMIUM_PRICE = 69

PREMIUM_DURATION_DAYS = 30

# =========================================================
# 🔥 LIMITS
# =========================================================

PREMIUM_MESSAGES_LIMIT = -1

PREMIUM_IMAGES_LIMIT = 20

PREMIUM_HISTORY_LIMIT = 8

PREMIUM_MEMORY_MODE = "extended"

PREMIUM_CONTEXT_WINDOW = "large"

# =========================================================
# 🔥 RESET POLICY
# =========================================================

PREMIUM_RESET_HOURS = 12

# =========================================================
# 🔥 FEATURES
# =========================================================

PREMIUM_FEATURES = {

    "text": True,

    "image_generation": True,

    "image_edit": True,

    "renderer": True,

    "web": True,

    "memory_extended": True,

    "priority_provider": True,

    "priority_queue": True,

    "experimental_features": True
}

# =========================================================
# 🧠 CENTRAL PLAN MATRIX
# =========================================================

PLAN_MATRIX = {

    FREE_PLAN_ID: {

        "id":
            FREE_PLAN_ID,

        "title":
            FREE_TITLE,

        "enabled":
            FREE_ENABLED,

        "price":
            FREE_PRICE,

        "duration_days":
            FREE_DURATION_DAYS,

        "limits": {

            "messages":
                FREE_MESSAGES_LIMIT,

            "images":
                FREE_IMAGES_LIMIT,

            "history":
                FREE_HISTORY_LIMIT
        },

        "memory_mode":
            FREE_MEMORY_MODE,

        "context_window":
            FREE_CONTEXT_WINDOW,

        "reset_hours":
            FREE_RESET_HOURS,

        "features":
            FREE_FEATURES
    },

    LITE_PLAN_ID: {

        "id":
            LITE_PLAN_ID,

        "title":
            LITE_TITLE,

        "enabled":
            LITE_ENABLED,

        "price":
            LITE_PRICE,

        "duration_days":
            LITE_DURATION_DAYS,

        "limits": {

            "messages":
                LITE_MESSAGES_LIMIT,

            "images":
                LITE_IMAGES_LIMIT,

            "history":
                LITE_HISTORY_LIMIT
        },

        "memory_mode":
            LITE_MEMORY_MODE,

        "context_window":
            LITE_CONTEXT_WINDOW,

        "reset_hours":
            LITE_RESET_HOURS,

        "features":
            LITE_FEATURES
    },

    PREMIUM_PLAN_ID: {

        "id":
            PREMIUM_PLAN_ID,

        "title":
            PREMIUM_TITLE,

        "enabled":
            PREMIUM_ENABLED,

        "price":
            PREMIUM_PRICE,

        "duration_days":
            PREMIUM_DURATION_DAYS,

        "limits": {

            "messages":
                PREMIUM_MESSAGES_LIMIT,

            "images":
                PREMIUM_IMAGES_LIMIT,

            "history":
                PREMIUM_HISTORY_LIMIT
        },

        "memory_mode":
            PREMIUM_MEMORY_MODE,

        "context_window":
            PREMIUM_CONTEXT_WINDOW,

        "reset_hours":
            PREMIUM_RESET_HOURS,

        "features":
            PREMIUM_FEATURES
    }
}

# =========================================================
# 🔥 WEB ADMIN EXPORT
# =========================================================

def export_web_admin_config():

    """
    Главный export для web admin panel.

    Используется:
    - admin dashboard
    - runtime editor
    - TXT import/export
    - pricing editor
    - limits editor
    """

    return {

        "version":
            APRIL_CONFIG_VERSION,

        "runtime_override_allowed":
            RUNTIME_OVERRIDE_ALLOWED,

        "plans":
            PLAN_MATRIX
    }

# =========================================================
# 🔥 TXT IMPORT READY
# =========================================================

TXT_RUNTIME_CONFIG = {

    "enabled":
        TXT_CONFIG_READY,

    "allow_import":
        True,

    "allow_export":
        True,

    "allow_hot_swap":
        False,

    "allow_web_sync":
        True
}

# =========================================================
# 🔥 RUNTIME HELPERS
# =========================================================

def normalize_plan(plan):

    if not plan:
        return FREE_PLAN_ID

    plan = str(plan).lower().strip()

    if plan not in PLAN_MATRIX:
        return FREE_PLAN_ID

    return plan


def get_plan(plan):

    normalized = normalize_plan(
        plan
    )

    return PLAN_MATRIX.get(
        normalized,
        PLAN_MATRIX[FREE_PLAN_ID]
    )


def get_plan_limits(plan):

    return get_plan(plan).get(
        "limits",
        {}
    )


def get_plan_features(plan):

    return get_plan(plan).get(
        "features",
        {}
    )


def is_unlimited(value):

    return value == -1

# =========================================================
# 🔥 PROVIDER PRIORITIES
# =========================================================

PROVIDER_RUNTIME_POLICY = {

    "free":
        "balanced",

    "lite":
        "priority",

    "premium":
        "priority_plus"
}

# =========================================================
# 🔥 MEMORY POLICY
# =========================================================

MEMORY_RUNTIME_POLICY = {

    "free":
        "compact",

    "lite":
        "balanced",

    "premium":
        "extended"
}

# =========================================================
# 🔥 FUTURE WEB ADMIN EXTENSIONS
# =========================================================

WEB_ADMIN_CAPABILITIES = {

    "live_tariff_editing": True,

    "live_limit_editing": True,

    "live_feature_toggle": True,

    "txt_import_export": True,

    "runtime_reload": False,

    "provider_priority_edit": True,

    "plan_activation_toggle": True
}
# =========================================================
# 🔥 LEGACY COMPATIBILITY LAYER
# =========================================================

"""
Temporary compatibility layer.

Нужен для модулей,
которые ещё используют
старые Telegram-era импорты.

После полной миграции
на WEB_ADMIN_READY
может быть удалён.
"""

# =========================================================
# 🔥 LEGACY PLAN NAMES
# =========================================================

FREE_PLAN = FREE_PLAN_ID

LITE_PLAN = LITE_PLAN_ID

PREMIUM_PLAN = PREMIUM_PLAN_ID

# =========================================================
# 🔥 LEGACY DURATIONS
# =========================================================

LITE_DAYS = LITE_DURATION_DAYS

PREMIUM_DAYS = PREMIUM_DURATION_DAYS

# =========================================================
# 🔥 LEGACY TITLES
# =========================================================

FREE_NAME = FREE_TITLE

LITE_NAME = LITE_TITLE

PREMIUM_NAME = PREMIUM_TITLE

# =========================================================
# 🔥 LEGACY ADMIN IMPORT
# =========================================================

"""
Старые файлы всё ещё могут делать:

from blocks.tariffs_config import ADMIN_ID

В web-архитектуре ADMIN_ID больше
не хранится в тарифах.

Но импорт не должен падать.
"""

ADMIN_ID = None

# =========================================================
# 🔥 LEGACY FLAG
# =========================================================

LEGACY_COMPATIBILITY_ENABLED = True
