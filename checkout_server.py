import os
import json

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    render_template_string,
    redirect
)

from blocks.paypal_module import (
    get_access_token,
    capture_payment,
    get_order
)

from storage import (
    set_subscription,
    save_payment
)

import requests

print("🔥🔥🔥 REAL CHECKOUT SERVER STARTED 🔥🔥🔥")

# =========================================================
# 🔥 CONFIG
# =========================================================

PORT = int(
    os.getenv("CHECKOUT_PORT", 8080)
)

DOMAIN = os.getenv(
    "CHECKOUT_DOMAIN",
    "https://aprill.site"
)

PAYPAL_CLIENT_ID = os.getenv(
    "PAYPAL_CLIENT_ID"
)

BOT_USERNAME = os.getenv(
    "BOT_USERNAME",
    "aprill_bot"
)

BASE_URL = "https://api-m.paypal.com"

# =========================================================
# 🔥 FLASK
# =========================================================

app = Flask(__name__)

# =========================================================
# 🎨 SUCCESS HTML
# =========================================================

SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<title>APRIL PAYMENT</title>

<style>

body{
    background:#0f1117;
    color:white;
    font-family:Arial;
    text-align:center;
    padding-top:80px;
}

.box{
    max-width:500px;
    margin:auto;
    background:#1c1f2b;
    padding:40px;
    border-radius:24px;
}

.title{
    font-size:32px;
    margin-bottom:20px;
}

.text{
    font-size:18px;
    opacity:.8;
}

</style>

</head>

<body>

<div class="box">

<div class="title">
✅ Оплата успешна
</div>

<div class="text">
Можешь возвращаться в APRIL
</div>

</div>

<script>

setTimeout(() => {

    window.location.href =
        "https://t.me/{{ bot_username }}";

}, 2500);

</script>

</body>
</html>
"""

# =========================================================
# ❌ CANCEL PAGE
# =========================================================

CANCEL_HTML = """
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<title>APRIL PAYMENT</title>

<style>

body{
    background:#0f1117;
    color:white;
    font-family:Arial;
    text-align:center;
    padding-top:80px;
}

.box{
    max-width:500px;
    margin:auto;
    background:#1c1f2b;
    padding:40px;
    border-radius:24px;
}

.title{
    font-size:32px;
    margin-bottom:20px;
}

.text{
    font-size:18px;
    opacity:.8;
}

</style>

</head>

<body>

<div class="box">

<div class="title">
❌ Оплата отменена
</div>

<div class="text">
Можешь вернуться позже
</div>

</div>

</body>
</html>
"""

# =========================================================
# 🚀 CHECKOUT PAGE
# =========================================================

@app.route("/checkout/<plan>/<user_id>")
def checkout(plan, user_id):

    if plan == "lite":

        amount = 12
        plan_name = "⚡ Lite"

    else:

        amount = 69
        plan_name = "👑 Premium"

    return render_template(

        "checkout.html",

        client_id=PAYPAL_CLIENT_ID,

        amount=amount,

        plan_name=plan_name,

        plan=plan,

        user_id=user_id
    )

# =========================================================
# 🔥 CREATE ORDER
# =========================================================

@app.route("/create-order", methods=["POST"])
def create_order():

    data = request.json

    amount = data.get("amount")
    plan = data.get("plan")
    user_id = data.get("user_id")

    token = get_access_token()

    if not token:
        return jsonify({
            "error": "TOKEN ERROR"
        }), 500

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

                    "custom_id":
                        f"{user_id}:{plan}",

                    "description":
                        f"APRIL AI {plan.upper()}"
                }
            ],

            "application_context": {

                "brand_name":
                    "APRIL AI",

                "landing_page":
                    "BILLING",

                "user_action":
                    "PAY_NOW",

                "shipping_preference":
                    "NO_SHIPPING"
            }
        }
    )

    result = response.json()

    if "id" not in result:

        print("PAYPAL CREATE ERROR:", result)

        return jsonify(result), 500

    return jsonify({
        "id": result["id"]
    })

# =========================================================
# 🔥 CAPTURE ORDER
# =========================================================

@app.route("/capture-order", methods=["POST"])
def capture_order():

    data = request.json

    order_id = data.get("orderID")

    capture = capture_payment(order_id)

    if not capture:
        return jsonify({
            "error": "CAPTURE FAILED"
        }), 500

    order = get_order(order_id)

    if not order:
        return jsonify({
            "error": "ORDER ERROR"
        }), 500

    try:

        purchase = order["purchase_units"][0]

        custom_id = purchase["custom_id"]

        user_id, plan = custom_id.split(":")

        user_id = int(user_id)

        set_subscription(user_id, plan)

        save_payment(user_id, plan)

    except Exception as e:

        print("CAPTURE PROCESS ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500

    return jsonify({
        "status": "success"
    })

# =========================================================
# 🟢 SUCCESS
# =========================================================

@app.route("/paypal-success")
def paypal_success():

    return render_template_string(
        SUCCESS_HTML,
        bot_username=BOT_USERNAME
    )

# =========================================================
# ❌ CANCEL
# =========================================================

@app.route("/paypal-cancel")
def paypal_cancel():

    return render_template_string(
        CANCEL_HTML
    )

# =========================================================
# 🔥 WEBHOOK
# =========================================================

@app.route("/webhook/paypal", methods=["POST"])
def paypal_webhook():

    try:

        data = request.json

        print(
            "PAYPAL WEBHOOK:",
            json.dumps(data, indent=4)
        )

        return {
            "status": "ok"
        }

    except Exception as e:

        print("WEBHOOK ERROR:", e)

        return {
            "status": "error"
        }

# =========================================================
# 🟢 HEALTH
# =========================================================

@app.route("/")
def health():

    return {
        "status": "APRIL CHECKOUT ONLINE"
    }

# =========================================================
# 🌐 EXTERNAL BROWSER OPEN
# =========================================================

@app.route("/open/<plan>/<user_id>")
def open_external(plan, user_id):

    return f"""
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>APRIL BROWSER OPEN</title>

<style>

body{{
    background:#0f1117;
    color:white;
    font-family:Arial;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
    text-align:center;
}}

.box{{
    max-width:500px;
    padding:40px;
}}

.title{{
    font-size:32px;
    margin-bottom:20px;
}}

.text{{
    opacity:.8;
    margin-bottom:30px;
}}

.button{{
    display:inline-block;
    padding:16px 28px;
    border-radius:14px;
    background:#ffd140;
    color:black;
    text-decoration:none;
    font-weight:bold;
}}

</style>



</head>

<body>

<div class="box">

<div class="title">
🌐 APRIL CHECKOUT
</div>

<div class="text">
Открываем оплату во внешнем браузере...
</div>

<a
    class="button"
    href="{DOMAIN}/checkout/{plan}/{user_id}"
>
    Открыть вручную
</a>

</div>

</body>
</html>
"""
# =========================================================
# 🚀 START
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT
    )
