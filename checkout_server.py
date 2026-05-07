import os
import json

from flask import (
    Flask,
    request,
    redirect,
    render_template,
    render_template_string
)

from blocks.paypal_module import (
    create_payment,
    capture_payment,
    get_order
)

from storage import (
    set_subscription,
    save_payment
)

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

# =========================================================
# 🔥 FLASK
# =========================================================

app = Flask(__name__)

# =========================================================
# 🎨 HTML TEMPLATE
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

    # =====================================================
    # 💰 PRICE
    # =====================================================

    if plan == "lite":

        amount = 12
        plan_name = "⚡ Lite"

    else:

        amount = 69
        plan_name = "👑 Premium"

    # =====================================================
    # 🔥 CREATE PAYMENT
    # =====================================================

    approve_url = create_payment(
        amount,
        plan,
        user_id
    )

    if not approve_url:

        return "PAYPAL ERROR"

    # =====================================================
    # 🔥 GET ORDER ID
    # =====================================================

    try:

        order_id = approve_url.split(
            "token="
        )[-1]

    except:

        return "ORDER ID ERROR"

    # =====================================================
    # 🔥 RENDER CHECKOUT
    # =====================================================

    return render_template(

        "checkout.html",

        client_id=PAYPAL_CLIENT_ID,

        order_id=order_id,

        amount=amount,

        plan_name=plan_name
    )

# =========================================================
# 🟢 SUCCESS
# =========================================================

@app.route("/paypal-success")
def paypal_success():

    order_id = request.args.get("token")

    if not order_id:
        return "NO ORDER ID"

    # =====================================================
    # 🔥 CAPTURE
    # =====================================================

    capture = capture_payment(order_id)

    if not capture:
        return "CAPTURE FAILED"

    # =====================================================
    # 🔥 GET ORDER
    # =====================================================

    order = get_order(order_id)

    if not order:
        return "ORDER ERROR"

    try:

        purchase = order["purchase_units"][0]

        custom_id = purchase["custom_id"]

        user_id, plan = custom_id.split(":")

        user_id = int(user_id)

    except Exception as e:

        print("CUSTOM ID ERROR:", e)

        return "CUSTOM ID ERROR"

    # =====================================================
    # 🔥 ACTIVATE SUBSCRIPTION
    # =====================================================

    try:

        set_subscription(user_id, plan)

        save_payment(user_id, plan)

    except Exception as e:

        print("SUB ERROR:", e)

        return "SUB ERROR"

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
# 🚀 START
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT
    )
