import os
import requests

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

BASE_URL = "https://api-m.paypal.com"


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

    return data["access_token"]


def create_payment(amount, plan, user_id):

    token = get_access_token()

    response = requests.post(
        f"{BASE_URL}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": str(amount)
                    },
                    "custom_id": f"{user_id}:{plan}"
                }
            ],
            "application_context": {
                "brand_name": "APRIL AI",
                "landing_page": "LOGIN",
                "user_action": "PAY_NOW",
                "return_url": "https://google.com",
                "cancel_url": "https://google.com"
            }
        }
    )

    data = response.json()

    for link in data.get("links", []):

        if link["rel"] == "approve":
            return link["href"]

    return None
