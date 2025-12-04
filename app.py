from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "")
    from_number = request.form.get("From", "")

    # TODO: store incoming messages later

    resp = MessagingResponse()
    reply = resp.message()

    reply.body(
        "🛡️ SignalShield Alert System\n\n"
        "Please describe the fraud or suspicious activity you encountered.\n"
        "⚠️ Do NOT share OTPs, bank numbers, or personal information."
    )

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
