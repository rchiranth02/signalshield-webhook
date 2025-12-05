from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    # Simple health check
    return "SignalShield backend running"


@app.route("/whatsapp", methods=["GET", "POST"])
def whatsapp_webhook():
    # For browser test
    if request.method == "GET":
        return "SignalShield webhook is live"

    # Twilio will send POST here
    incoming_msg = (request.form.get("Body", "") or "").strip()
    from_number = request.form.get("From", "")

    # TODO: later we will save (incoming_msg, from_number) into DB

    resp = MessagingResponse()
    reply = resp.message()

    reply.body(
        "🛡️ SignalShield Alert System\n\n"
        "Please describe the fraud or suspicious activity you encountered.\n"
        "⚠️ Do NOT share OTPs, bank numbers, passwords, or any personal details."
    )

    return str(resp)


if __name__ == "__main__":
    # For local runs; Render will ignore this and use gunicorn
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

