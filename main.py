import os
import asyncpg
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

# ---------- Simple in-memory state for conversation ----------
# { "<phone_number>": {"stage": "...", "category": {"main": "...", "sub": "..."}} }
user_state = {}

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
    "🔟": ("OTHER", "OTHER_UNSURE"),
}

# ---------- DB pool (Supabase Postgres via asyncpg) ----------
pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup_db():
    """
    Create a global connection pool to Supabase Postgres.
    """
    global pool

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL env var not set")

    # Supabase usually gives postgresql:// already; asyncpg is fine with this.
    pool = await asyncpg.create_pool(dsn=db_url)


@app.on_event("shutdown")
async def shutdown_db():
    global pool
    if pool:
        await pool.close()


async def save_report_to_db(phone_number: str,
                            category_main: str,
                            category_sub: str,
                            description: str):
    """
    Upsert user and insert fraud report into Supabase tables.
    """
    async with pool.acquire() as conn:  # type: ignore[arg-type]
        # 1) Upsert user and get id
        user_row = await conn.fetchrow(
            """
            INSERT INTO users (phone_number)
            VALUES ($1)
            ON CONFLICT (phone_number)
            DO UPDATE SET last_seen_at = NOW()
            RETURNING id;
            """,
            phone_number,
        )
        user_id = user_row["id"]

        # 2) Insert raw report
        await conn.execute(
            """
            INSERT INTO fraud_reports_raw
                (user_id, category_main, category_sub, description)
            VALUES
                ($1, $2, $3, $4);
            """,
            user_id,
            category_main,
            category_sub,
            description,
        )


# ---------- Health check ----------
@app.get("/", response_class=PlainTextResponse)
async def home():
    return "SignalShield FastAPI backend running ✅"


# ---------- Main WhatsApp webhook ----------
@app.post("/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    Body: str = Form(""),
    From: str = Form(""),
):
    """
    Twilio sends x-www-form-urlencoded with Body, From, etc.
    We respond with TwiML.
    """
    incoming_msg = (Body or "").strip()
    from_number = From or ""

    resp = MessagingResponse()
    reply = resp.message()

    # Fetch or initialise user state
    state = user_state.get(from_number, {"stage": "start", "category": None})

    # --- Stage 1: Greeting & menu ---
    if state["stage"] == "start":
        reply.body(
            "🛡️ SignalShield Alert System\n\n"
            "Thanks for reaching out. We help people document and understand "
            "online fraud and suspicious activity.\n\n"
            "⚠️ Do NOT share OTPs, bank numbers, passwords, or personal details.\n\n"
            + CATEGORY_MENU
        )
        state["stage"] = "await_category"

    # --- Stage 2: Expecting category selection ---
    elif state["stage"] == "await_category":
        normalized = incoming_msg

        if normalized in ("10", "🔟"):
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
            reply.body(
                "Sorry, I couldn’t understand that option. 🙏\n\n" + CATEGORY_MENU
            )

    # --- Stage 3: Got description: save to DB + close loop ---
    elif state["stage"] == "await_description":
        description = incoming_msg
        cat = state.get("category") or {}
        cat_main = cat.get("main", "UNSET")
        cat_sub = cat.get("sub", "UNSET")

        # Save in DB (ignore failures for now, just log)
        try:
            await save_report_to_db(
                phone_number=from_number,
                category_main=cat_main,
                category_sub=cat_sub,
                description=description,
            )
        except Exception as e:
            # In real code you’d log this somewhere
            print("DB error while saving report:", e)

        reply.body(
            "Thank you for sharing this report with SignalShield 🛡️\n\n"
            f"We've recorded it under: *{cat_main}*.\n"
            "As we collect more reports, we'll analyse patterns and "
            "share guidance on risks and next actions.\n\n"
            "If you want to submit another case, just say *Hi*."
        )

        # Reset state so a new conversation can start
        state = {"stage": "start", "category": None}

    # Persist state in memory
    user_state[from_number] = state

    # Return TwiML as plain text
    return str(resp)
