import asyncio
import os
import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from agents.grocery_agent import process_grocery_message
from agents.payment_agent import create_payment_link

load_dotenv()

app = FastAPI()

user_sessions = {}

twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER = "whatsapp:+14155238886"
GROCERY_AGENT_TIMEOUT_SECONDS = 10


def extract_total(price_comparison: str, platform: str) -> str:
    pattern = rf"^{re.escape(platform)}\s*:\s*₹\s*([0-9]+(?:\.[0-9]+)?)\b"
    for line in price_comparison.splitlines():
        match = re.search(pattern, line.strip(), re.IGNORECASE)
        if match:
            return match.group(1)
    return ""

def extract_confirmation_platform(price_comparison: str) -> str:
    pattern = r"^Reply YES to confirm order on (.+?)\.$"
    for line in price_comparison.splitlines():
        match = re.search(pattern, line.strip(), re.IGNORECASE)
        if match:
            return match.group(1)
    return ""


async def send_whatsapp_reply(phone_number: str, reply: str) -> bool:
    try:
        await asyncio.to_thread(
            twilio_client.messages.create,
            from_=TWILIO_NUMBER,
            to=phone_number,
            body=reply
        )
        print(f"Reply sent to {phone_number}")
        return True
    except Exception as e:
        print(f"Twilio send error: {e}")
        return False

@app.get("/")
async def root():
    return {"message": "Grocery Agent is running!"}

@app.post("/whatsapp")
async def whatsapp_reply(request: Request):
    form_data = await request.form()
    incoming_message = form_data.get("Body", "").strip()
    phone_number = form_data.get("From", "")
    print(f"Message from: {phone_number}")
    print(f"Message content: '{incoming_message}'")
    print(f"Has alnum: {any(c.isalnum() for c in incoming_message)}")

    response = MessagingResponse()
    reply = ""

    # empty message handling
    if not incoming_message or not any(c.isalnum() for c in incoming_message):
        reply = "👋 Hi! Send me a grocery list and I'll find the best prices for you!\n\nExample: 2 litre milk, dozen eggs, brown bread"
    elif phone_number in user_sessions and user_sessions[phone_number]["state"] == "waiting_for_confirmation":
        if incoming_message.upper() == "YES":
            session = user_sessions[phone_number]
            try:
                payment_link = await asyncio.to_thread(
                    create_payment_link,
                    session['total'],
                    session['platform'],
                    f"Grocery order via {session['platform']}"
                )
                reply = f"✅ Order Confirmed!\n\nPlatform: {session['platform']}\nTotal: ₹{session['total']}\n\n💳 Complete your payment:\n{payment_link}\n\nOrder will be placed after payment! 🛒"
            except Exception as e:
                print(f"Payment link error: {e}")
                reply = "😕 Sorry, payment link generation failed. Please try again!"
            del user_sessions[phone_number]
        elif incoming_message.upper() == "NO":
            reply = "❌ Order cancelled. Send me a new grocery list anytime!"
            del user_sessions[phone_number]
        else:
            reply = "Please reply YES to confirm or NO to cancel."
    else:
        try:
            start = time.time()
            print("Calling process_grocery_message...")
            price_comparison = await asyncio.wait_for(
                asyncio.to_thread(process_grocery_message, incoming_message),
                timeout=GROCERY_AGENT_TIMEOUT_SECONDS
            )
            elapsed = time.time() - start
            print(f"process_grocery_message took: {elapsed:.2f}s")
            print(f"Price comparison: {price_comparison}")

            platform = extract_confirmation_platform(price_comparison)
            total = extract_total(price_comparison, platform)
            print(f"Extracted total: '{total}'")
            print(f"Platform: '{platform}'")

            if not total or float(total) == 0:
                reply = "😕 Sorry, I couldn't find any of those items in our database.\n\nAvailable items: milk, eggs, bread, butter, rice, sugar, salt, oil, onion, tomato\n\nPlease try again with items from the list!"
            else:
                user_sessions[phone_number] = {
                    "state": "waiting_for_confirmation",
                    "platform": platform,
                    "total": total
                }
                print(f"Session saved for {phone_number}: {user_sessions[phone_number]}")
                reply = price_comparison
        except asyncio.TimeoutError:
            print("process_grocery_message timed out")
            reply = "😕 Sorry, price comparison is taking too long right now. Please try again in a minute!"
        except Exception as e:
            print(f"Grocery processing error: {e}")
            reply = "😕 Sorry, I couldn't process that grocery list right now. Please try again!"

    sent = await send_whatsapp_reply(phone_number, reply)
    if not sent:
        response.message(reply)
        return Response(content=str(response), media_type="application/xml")

    return Response(content="", media_type="application/xml")
