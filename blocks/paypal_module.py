# =====================================================
# 🧠 APRIL PAYPAL SYSTEM
# =====================================================

"""
APRIL PAYPAL SYSTEM
WEB-FIRST PAYMENT LAYER

=====================================================

Этот модуль больше НЕ:
- telegram payment helper;
- callback-driven checkout;
- UI-bound billing layer;
- payment authority system.

=====================================================

Этот модуль теперь:
- provider-safe payment bridge;
- web-first checkout layer;
- executor-compatible billing provider;
- subscription orchestration helper;
- monetization continuity system.

=====================================================

APRIL PRINCIPLES:

1. payment != authority
2. executor controls subscription state
3. checkout isolated from UI
4. web-first architecture
5. provider-safe billing
6. transport-independent payments
7. orchestration-safe monetization
"""

print("🧠 APRIL PAYPAL SYSTEM LOADED")

# =====================================================
# 🔥 IMPORTS
# =====================================================

import os
import requests

# =====================================================
# 🔥 APRIL FILE ID
# =====================================================

APRIL_FILE_ID = "APRIL_PAYPAL_SYSTEM"

# =====================================================
# 🔥 MACHINE CHANNELS
# =====================================================

INPUT_MACHINE_CHANNEL = {

    "source": "executor_billing_pipeline",
    "type": "payment_machine_input",
    "isolated": True
}

OUTPUT_MACHINE_CHANNEL = {

    "target": "subscription_orchestrator",
    "type": "payment_machine_output",
    "isolated": True
}

# =====================================================
# 🔥 SAFE PATCH MODE
# =====================================================

PATCH_LOG = []


def safe_patch_log(msg):

    try:

        print(
            "PAYPAL PATCH:",
            msg
        )

        PATCH_LOG.append(msg)

    except Exception:
        pass


# =====================================================
# 🔥 CONFIG
# =====================================================

PAYPAL_CLIENT_ID = os.getenv(
    "PAYPAL_CLIENT_ID"
)

PAYPAL_SECRET = os.getenv(
    "PAYPAL_SECRET"
)

BASE_URL = os.getenv(

    "PAYPAL_BASE_URL",

    "https://api-m.paypal.com"
)

# =====================================================
# 🔥 WEB CHECKOUT DOMAIN
# =====================================================

CHECKOUT_DOMAIN = os.getenv(

    "CHECKOUT_DOMAIN",

    "https://aprill.site"
)

# =====================================================
# 🔥 MACHINE BILLING STATES
# =====================================================

PAYMENT_CAPABILITIES = {

    "web_checkout": True,

    "subscription_ready": True,

    "transport_independent": True,

    "executor_compatible": True,

    "provider_safe": True,

    "ui_independent": True,

    "continuity_safe": True
}

# =====================================================
# 🔥 SAFE HELPERS
# =====================================================

def normalize_text(value):

    return str(
        value or ""
    ).strip()


# =====================================================
# 🔥 PAYMENT PACKAGE
# =====================================================

def build_payment_context(

    user_id,
    plan,
    amount
):

    return {

        "user_id":
            str(user_id),

        "plan":
            normalize_text(plan),

        "amount":
            str(amount),

        "billing_provider":
            "paypal",

        "web_checkout":
            True,

        "executor_aware":
            True,

        "machine_state":
            True,

        "continuity_safe":
            True
    }


# =====================================================
# 🔐 ACCESS TOKEN
# =====================================================

def get_access_token():

    safe_patch_log(
        "REQUEST ACCESS TOKEN"
    )

    try:

        response = requests.post(

            f"{BASE_URL}/v1/oauth2/token",

            auth=(
                PAYPAL_CLIENT_ID,
                PAYPAL_SECRET
            ),

            headers={

                "Accept":
                    "application/json",

                "Accept-Language":
                    "en_US"
            },

            data={

                "grant_type":
                    "client_credentials"
            },

            timeout=20
        )

        data = response.json()

        token = data.get(
            "access_token"
        )

        if not token:

            print(
                "🔥 PAYPAL TOKEN ERROR:",
                data
            )

            return None

        return token

    except Exception as e:

        print(
            "🔥 PAYPAL TOKEN EXCEPTION:",
            e
        )

        return None


# =====================================================
# 💳 CREATE PAYMENT
# =====================================================

def create_payment(

    amount,
    plan,
    user_id
):

    safe_patch_log(

        f"CREATE PAYMENT: "
        f"{user_id} -> {plan}"
    )

    payment_context = (

        build_payment_context(

            user_id,
            plan,
            amount
        )
    )

    token = get_access_token()

    if not token:

        return {

            "success": False,

            "error":
                "token_unavailable",

            "payment_context":
                payment_context
        }

    try:

        response = requests.post(

            f"{BASE_URL}/v2/checkout/orders",

            headers={

                "Content-Type":
                    "application/json",

                "Authorization":
                    f"Bearer {token}"
            },

            json={

                # =============================================
                # 🔥 PAYPAL FLOW
                # =============================================

                "intent": "CAPTURE",

                # =============================================
                # 📦 PURCHASE
                # =============================================

                "purchase_units": [

                    {

                        "amount": {

                            "currency_code":
                                "USD",

                            "value":
                                str(amount)
                        },

                        # =====================================
                        # 🧠 MACHINE CONTEXT
                        # =====================================

                        "custom_id":

                            f"{user_id}:{plan}",

                        # =====================================
                        # 🔥 DESCRIPTION
                        # =====================================

                        "description":

                            f"APRIL AI "
                            f"{str(plan).upper()} "
                            f"SUBSCRIPTION"
                    }
                ],

                # =============================================
                # 🔥 UX SETTINGS
                # =============================================

                "application_context": {

                    "brand_name":
                        "APRIL AI",

                    "landing_page":
                        "BILLING",

                    "user_action":
                        "PAY_NOW",

                    "shipping_preference":
                        "NO_SHIPPING",

                    "payment_method": {

                        "payee_preferred":

                            "IMMEDIATE_PAYMENT_REQUIRED"
                    },

                    # =========================================
                    # 🔥 WEB RETURN FLOW
                    # =========================================

                    "return_url":

                        f"{CHECKOUT_DOMAIN}"
                        f"/paypal-success",

                    "cancel_url":

                        f"{CHECKOUT_DOMAIN}"
                        f"/paypal-cancel"
                }
            },

            timeout=30
        )

        data = response.json()

        # =================================================
        # 🔥 DEBUG
        # =====================================================

        if "links" not in data:

            print(
                "🔥 PAYPAL ORDER ERROR:",
                data
            )

            return {

                "success": False,

                "error":
                    "paypal_order_error",

                "paypal_response":
                    data,

                "payment_context":
                    payment_context
            }

        # =================================================
        # 🔗 APPROVE LINK
        # =====================================================

        for link in data.get(
            "links",
            []
        ):

            if link.get("rel") == "approve":

                return {

                    "success": True,

                    "checkout_url":
                        link.get("href"),

                    "provider":
                        "paypal",

                    "payment_context":
                        payment_context,

                    "web_checkout":
                        True,

                    "executor_aware":
                        True
                }

        return {

            "success": False,

            "error":
                "approve_link_missing",

            "payment_context":
                payment_context
        }

    except Exception as e:

        print(
            "🔥 PAYPAL CREATE ERROR:",
            e
        )

        return {

            "success": False,

            "error":
                str(e),

            "payment_context":
                payment_context
        }


# =====================================================
# 🔥 CAPTURE PAYMENT
# =====================================================

def capture_payment(
    order_id
):

    safe_patch_log(

        f"CAPTURE PAYMENT: "
        f"{order_id}"
    )

    token = get_access_token()

    if not token:

        return {

            "success": False,

            "error":
                "token_unavailable"
        }

    try:

        response = requests.post(

            f"{BASE_URL}"
            f"/v2/checkout/orders/"
            f"{order_id}/capture",

            headers={

                "Content-Type":
                    "application/json",

                "Authorization":
                    f"Bearer {token}"
            },

            timeout=30
        )

        data = response.json()

        return {

            "success": True,

            "provider":
                "paypal",

            "capture":
                data,

            "executor_ready":
                True,

            "subscription_event":
                True
        }

    except Exception as e:

        print(
            "🔥 PAYPAL CAPTURE ERROR:",
            e
        )

        return {

            "success": False,

            "error":
                str(e)
        }


# =====================================================
# 🔥 GET ORDER
# =====================================================

def get_order(
    order_id
):

    safe_patch_log(

        f"GET ORDER: "
        f"{order_id}"
    )

    token = get_access_token()

    if not token:

        return {

            "success": False,

            "error":
                "token_unavailable"
        }

    try:

        response = requests.get(

            f"{BASE_URL}"
            f"/v2/checkout/orders/"
            f"{order_id}",

            headers={

                "Content-Type":
                    "application/json",

                "Authorization":
                    f"Bearer {token}"
            },

            timeout=20
        )

        data = response.json()

        return {

            "success": True,

            "provider":
                "paypal",

            "order":
                data,

            "machine_readable":
                True,

            "executor_aware":
                True
        }

    except Exception as e:

        print(
            "🔥 PAYPAL GET ORDER ERROR:",
            e
        )

        return {

            "success": False,

            "error":
                str(e)
        }


# =====================================================
# 🔥 BILLING STATE PACKAGE
# =====================================================

def build_billing_machine_state():

    return {

        "billing_provider":
            "paypal",

        "web_checkout":
            True,

        "subscription_ready":
            True,

        "transport_independent":
            True,

        "executor_aware":
            True,

        "provider_safe":
            True,

        "ui_independent":
            True,

        "continuity_safe":
            True,

        "machine_state":
            True,

        "capabilities":
            PAYMENT_CAPABILITIES
    }
