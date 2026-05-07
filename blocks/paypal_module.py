import os
import requests

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

BASE_URL = "https://api-m.paypal.com"

# =========================================================
# 🔥 CHECKOUT DOMAIN
# =========================================================

CHECKOUT_DOMAIN = os.getenv(
    "CHECKOUT_DOMAIN",
    "https://aprill.site"
)


# =========================================================
# 🔐 ACCESS TOKEN
# =========================================================

def get_access_token():

    response = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        headers={
            "Accept": "application/json",
            "Accept-Language": "en_US"
        },
        data={
            "grant_type": "client_credentials"
        }
    )

    data = response.json()

    return data.get("access_token")


# =========================================================
# 💳 CREATE PAYMENT
# =========================================================

def create_payment(amount, plan, user_id):

    token = get_access_token()

    if not token:
        return None

    response = requests.post(
        f"{BASE_URL}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        json={

            # =================================================
            # 🔥 PAYPAL FLOW
            # =================================================

            "intent": "CAPTURE",

            # =================================================
            # 📦 PURCHASE
            # =================================================

            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": str(amount)
                    },

                    # =============================================
                    # 🔥 USER + PLAN
                    # =============================================

                    "custom_id": f"{user_id}:{plan}",

                    # =============================================
                    # 🧠 DESCRIPTION
                    # =============================================

                    "description": f"APRIL AI {plan.upper()} SUBSCRIPTION"
                }
            ],

            # =================================================
            # 🔥 UX SETTINGS
            # =================================================

            "application_context": {

                # =============================================
                # 🏷 BRAND
                # =============================================

                "brand_name": "APRIL AI",

                # =============================================
                # 🔥 GUEST CHECKOUT
                # =============================================

                "landing_page": "BILLING",

                # =============================================
                # ⚡ PAY NOW
                # =============================================

                "user_action": "PAY_NOW",

                # =============================================
                # 🔥 NO SHIPPING
                # =============================================

                "shipping_preference": "NO_SHIPPING",

                # =============================================
                # 🔥 PAYMENT REQUIRED
                # =============================================

                "payment_method": {
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED"
                },

                # =============================================
                # 🔥 RETURN URL
                # =============================================

                "return_url":
                    f"{CHECKOUT_DOMAIN}/paypal-success",

                # =============================================
                # 🔥 CANCEL URL
                # =============================================

                "cancel_url":
                    f"{CHECKOUT_DOMAIN}/paypal-cancel"
            }
        }
    )

    data = response.json()

    # =====================================================
    # 🔥 DEBUG
    # =====================================================

    if "links" not in data:
        print("PAYPAL ERROR:", data)
        return None

    # =====================================================
    # 🔗 APPROVE LINK
    # =====================================================

    for link in data.get("links", []):

        if link["rel"] == "approve":
            return link["href"]

    return None


# =========================================================
# 🔥 CAPTURE PAYMENT
# =========================================================

def capture_payment(order_id):

    token = get_access_token()

    if not token:
        return None

    response = requests.post(
        f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    return response.json()


# =========================================================
# 🔥 GET ORDER
# =========================================================

def get_order(order_id):

    token = get_access_token()

    if not token:
        return None

    response = requests.get(
        f"{BASE_URL}/v2/checkout/orders/{order_id}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )

    return response.json()
