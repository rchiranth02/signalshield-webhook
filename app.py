from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# super simple in-memory state (OK for sandbox prototype)
user_state = {}  # { from_number: {"stage": "...", "category": "..."} }

CATEGORY_MENU = (
    "Please choose the option that best fits the issue:\n"
    "1️⃣ Payment / UPI scam\n"
    "2️⃣ Job or work-from-home scam\n"
    "3️⃣ Account / OTP / login issue\n"
    "4️⃣ Phishing link / KYC / delivery update\n"
    "5️⃣ Loan or credit scam\n"
    "6️⃣ Investment / trading / crypto scam\n"
    "7️⃣ Online shopping / marketplace issue\n"
    "8️⃣ Romance or emotional pressure\n"
    "9️⃣ Fake police / bank / authority / impersonation\n"
    "🔟 Other / not sure"
)

CATEGORY_MAP = {
    "1": ("PAYMENT", "UPI_OR_PAYMENT_SCAM"),
    "2": ("JOB", "JOB_SCAM"),
    "3": ("ACCOUNT", "ACCOUNT_TAKEOVER"),
    "4": ("PHISHING", "PHISHING_LINK"),
    "5": ("LOAN", "LOAN_SCAM"),
    "6": ("INVEST", "INVESTMENT_SCAM"),
    "7": ("ECOM", "ECOMMERCE_SCAM"),
    "8": ("ROMANCE", "ROMANCE_SCAM"),
    "9": ("IMPERSONATION", "FAKE_AUTHORITY"),
    "10": ("OTHER", "OTHER_UNSURE"),
    "🔟": ("OTHER", "OTHER_UNSURE"),  # in case someone literally sends the emoji
}


@app.route("/", methods=["GET"])
def home():
    return "SignalShield backend running ✅"


@app.route("/whatsapp", methods=["GET", "POST"])
def whatsapp_webhook():
    if request.method == "GET":
        return "SignalShield webhook is live ✅"

    incoming_msg = (request.form.get("Body", "") or "").strip()
    from_number = request.form.get("From", "")

    resp = MessagingResponse()
    reply = resp.message()

    # get or init state
    state = user_state.get(from_number, {"stage": "start", "category": None})

    # --- stage 1: first contact or reset ---
    if state["stage"] == "start":
        # send greeting + menu
        reply.body(
            "🛡️ SignalShield Alert System\n\n"
            "Thanks for reaching out. We help people document and understand\n"
            "online fraud and suspicious activity.\n\n"
            "⚠️ Do NOT share OTPs, bank numbers, passwords, or personal details.\n\n"
            + CATEGORY_MENU
        )
        state["stage"] = "await_category"

    # --- stage 2: waiting for category selection ---
    elif state["stage"] == "await_category":
        normalized = incoming_msg.strip()

        # accept "10" or "🔟"
        if normalized == "10" or normalized == "🔟":
            key = "10"
        else:
            key = normalized

        if key in CATEGORY_MAP:
            cat_main, cat_sub = CATEGORY_MAP[key]
            state["category"] = {"main": cat_main, "sub": cat_sub}
            state["stage"] = "await_description"

            reply.body(
                f"Got it ✅ Category selected: *{cat_main}*.\n\n"
                "Now, in 2–3 sentences, please describe what happened.\n"
                "You can include:\n"
                "• What the scammer said/sent\n"
                "• Where you saw it (WhatsApp, Insta, SMS, etc.)\n"
                "• If any money or data was shared\n\n"
                "⚠️ Please still avoid OTPs, full card numbers, or IDs."
            )
        else:
            # invalid option – resend menu
            reply.body(
                "Sorry, I couldn’t understand that option. 🙏\n\n"
                + CATEGORY_MENU
            )

    # --- stage 3: we have category + description text ---
    elif state["stage"] == "await_description":
        description = incoming_msg

        # TODO (Week 2): save description + category + number to DB

        cat = state.get("category", {})
        cat_main = cat.get("main", "UNSET")

        reply.body(
            "Thank you for sharing this report with SignalShield 🛡️\n\n"
            f"We've recorded it under: *{cat_main}*.\n"
            "In the next version, we’ll analyse patterns across reports and\n"
            "share guidance on risks and next actions.\n\n"
            "If you want to submit another case, just say *Hi*."
        )

        # reset state for future conversations
        state = {"stage": "start", "category": None}

    # save state back
    user_state[from_number] = state

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


