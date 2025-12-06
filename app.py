from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

app = FastAPI(title="SignalShield Webhook")

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "SignalShield webhook"}

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Twilio will POST WhatsApp messages here.
    For now we just log and return an empty TwiML response.
    """
    form = await request.form()
    from_number = form.get("From")
    body = (form.get("Body") or "").strip()

    # For now just log – later we’ll insert into DB, score, etc.
    print("Incoming WhatsApp:", from_number, body)

    # Twilio expects valid XML (TwiML), even if empty.
    return PlainTextResponse("<Response></Response>", media_type="application/xml")
