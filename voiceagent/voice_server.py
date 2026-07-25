"""
voice_server.py - The full Voice Agent call handler.
Detects intent, books meetings, answers from documents,
and keeps listening until the caller says goodbye.

Email capture is three-tier:
  1. Known caller  -> look up email by phone number
  2. Unknown caller -> send an SMS, take the email by text reply
  3. Fallback       -> capture by voice with read-back confirmation

Bookings are validated against business rules (no past dates,
closed on weekends, within office hours).
"""
import os
import datetime
from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv

from voiceagent.core.analytics import log_event
from voiceagent.core.intent import detect
from voiceagent.core.calendar_agent import CalendarAgent
from voiceagent.core.rag_engine import RAGEngine
from voiceagent.core.email_agent import EmailAgent
from voiceagent.core.contacts import get_email, set_email

load_dotenv()

app = FastAPI()
calendar = CalendarAgent()
rag = RAGEngine()
mailer = EmailAgent()

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"),
                       os.getenv("TWILIO_AUTH_TOKEN"))

sessions = {}
pending_by_phone = {}

# Business rules
CLOSED_WEEKDAYS = {5, 6}   # 5=Saturday, 6=Sunday
OPEN_HOUR = 9
CLOSE_HOUR = 18            # last booking must end by 6 PM


def new_session():
    return {"pending_slot": None, "awaiting_confirm": None, "caller": ""}


def say_and_listen(vr, text, email_mode=False):
    g = Gather(input="speech", action="/handle-speech", method="POST",
               speechTimeout="auto", language="en-US",
               enhanced=True, speechModel="phone_call")
    if email_mode:
        g.hints = ("gmail, yahoo, hotmail, outlook, dot com, at, "
                   "underscore, dash, dot")
    g.say(text, voice="Polly.Joanna")
    vr.append(g)
    vr.redirect("/voice")


def pretty(dt):
    return dt.strftime("%A %d %B at %I:%M %p")


def spoken_email(email):
    return email.replace("@", " at ").replace(".", " dot ")


def slot_problem(slot):
    """Return a reason string if the slot is invalid, else None."""
    now = datetime.datetime.now()
    if slot < now:
        return "that time is in the past"
    if slot.weekday() in CLOSED_WEEKDAYS:
        return "we are closed on weekends"
    if slot.hour < OPEN_HOUR or slot.hour >= CLOSE_HOUR:
        return "that is outside our office hours of 9 A M to 6 P M"
    return None


def send_sms(to_number, body):
    """Text the caller. Used when we don't know their email."""
    try:
        twilio_client.messages.create(
            body=body, from_=os.getenv("TWILIO_NUMBER"), to=to_number)
        return True
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return False


def finalise_booking(slot, email, phone=None):
    """Book the meeting and email the assistant for approval."""
    calendar.book_meeting(
        slot, "Meeting (Voice Agent)",
        description=f"Client email: {email}")
    mailer.request_approval(email, pretty(slot))
    log_event("meeting")
    if phone:
        set_email(phone, email)


# ----------------------------- VOICE -----------------------------

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    sid = form.get("CallSid", "unknown")
    session = new_session()
    session["caller"] = form.get("From", "")
    sessions[sid] = session
    log_event("call")
    vr = VoiceResponse()
    say_and_listen(vr, "Hello! Thank you for calling. I can answer questions "
                       "or schedule a meeting. How can I help you?")
    return Response(content=str(vr), media_type="application/xml")


@app.post("/handle-speech")
async def handle_speech(request: Request):
    form = await request.form()
    sid = form.get("CallSid", "unknown")
    speech = (form.get("SpeechResult") or "").strip()
    session = sessions.setdefault(sid, new_session())
    if not session.get("caller"):
        session["caller"] = form.get("From", "")
    vr = VoiceResponse()

    print(f"[{sid[:8]}] HEARD: {speech}")

    if not speech:
        say_and_listen(vr, "Sorry, I didn't catch that. Please repeat.")
        return Response(content=str(vr), media_type="application/xml")

    try:
        result = detect(speech)
        intent = result["intent"]
        print(f"[{sid[:8]}] INTENT: {result}")
        print(f"[{sid[:8]}] SESSION: {session}")

        # --- Caller is finished ---
        if intent == "goodbye":
            vr.say("Thank you for calling. Have a great day. Goodbye!",
                   voice="Polly.Joanna")
            vr.hangup()
            sessions.pop(sid, None)
            return Response(content=str(vr), media_type="application/xml")

        # --- Caller is confirming a read-back email ---
        if session.get("awaiting_confirm"):
            low = speech.lower()
            if any(w in low for w in ["yes", "correct", "right", "yeah"]):
                finalise_booking(session["pending_slot"],
                                 session["awaiting_confirm"],
                                 session.get("caller"))
                session["pending_slot"] = None
                session["awaiting_confirm"] = None
                say_and_listen(
                    vr, "Thank you. Your request is submitted and we will "
                        "confirm by email shortly. Anything else?")
            else:
                session["awaiting_confirm"] = None
                say_and_listen(vr, "No problem. Please say your email "
                                   "address slowly.", email_mode=True)
            return Response(content=str(vr), media_type="application/xml")

        # --- Caller is giving their email by voice ---
        if intent == "email" and result["email"]:
            if not session["pending_slot"]:
                say_and_listen(vr, "Thanks. First, what day and time "
                                   "would you like to meet?")
                return Response(content=str(vr), media_type="application/xml")
            session["awaiting_confirm"] = result["email"]
            say_and_listen(
                vr, f"I heard {spoken_email(result['email'])}. "
                    f"Is that correct? Say yes or no.")
            return Response(content=str(vr), media_type="application/xml")

        # --- Caller wants to book ---
        if intent == "book":
            slot = result["datetime"]
        #    / print(f"[DEBUG] slot={slot}, weekday={slot.weekday() if slot else 'none'}, problem={slot_problem(slot) if slot else 'no slot'}")
            if not slot:
                say_and_listen(vr, "Sure. What day and time would you like?")
                return Response(content=str(vr), media_type="application/xml")

            # Validate against business rules
            problem = slot_problem(slot)
            if problem:
                say_and_listen(
                    vr, f"Sorry, {problem}. Please choose another time "
                        f"during our office hours, Monday to Friday.")
                return Response(content=str(vr), media_type="application/xml")

            if not calendar.is_slot_free(slot):
                say_and_listen(
                    vr, f"Sorry, there is no slot available at {pretty(slot)}. "
                        f"Would you like a different time?")
                return Response(content=str(vr), media_type="application/xml")

            session["pending_slot"] = slot
            caller = session.get("caller", "")
            known = get_email(caller)

            # Tier 1: known caller
            if known:
                session["awaiting_confirm"] = known
                say_and_listen(
                    vr, f"{pretty(slot)} is available. I have your email as "
                        f"{spoken_email(known)}. Shall I use that? "
                        f"Say yes or no.")
                return Response(content=str(vr), media_type="application/xml")

            # Tier 2: text them for their email
            sent = send_sms(
                caller,
                f"Thanks for calling! Your meeting request for "
                f"{pretty(slot)} is pending. Please reply to this message "
                f"with your email address to confirm.")
            if sent:
                pending_by_phone[caller] = slot
                say_and_listen(
                    vr, f"{pretty(slot)} is available. I have sent you a text "
                        f"message. Please reply to it with your email "
                        f"address. Is there anything else?")
            else:
                # Tier 3: voice capture
                say_and_listen(
                    vr, f"{pretty(slot)} is available. Please say your email "
                        f"address slowly.", email_mode=True)
            return Response(content=str(vr), media_type="application/xml")

        # --- Caller asked a question: answer from documents ---
        answer = rag.answer(speech)
        log_event("question")
        say_and_listen(vr, answer + " Is there anything else?")
        return Response(content=str(vr), media_type="application/xml")

    except Exception as e:
        print(f"[{sid[:8]}] ERROR: {e}")
        say_and_listen(vr, "Sorry, I had trouble with that. "
                           "Could you say it again?")
        return Response(content=str(vr), media_type="application/xml")


# ------------------------ SMS REPLY HANDLER ------------------------

@app.post("/sms")
async def sms(request: Request):
    """Receives the caller's texted email and completes the booking."""
    form = await request.form()
    phone = form.get("From", "")
    body = (form.get("Body") or "").strip()
    resp = MessagingResponse()

    print(f"[SMS] {phone}: {body}")

    slot = pending_by_phone.get(phone)
    if not slot:
        resp.message("We don't have a pending meeting request for this "
                     "number. Please call us to book a time.")
        return Response(content=str(resp), media_type="application/xml")

    email = None
    for word in body.split():
        if "@" in word and "." in word:
            email = word.strip(".,;:")
            break

    if not email:
        resp.message("That didn't look like an email address. "
                     "Please reply with just your email.")
        return Response(content=str(resp), media_type="application/xml")

    finalise_booking(slot, email, phone)
    pending_by_phone.pop(phone, None)
    resp.message(f"Thank you! Your meeting request for {pretty(slot)} "
                 f"has been submitted. We will confirm by email shortly.")
    return Response(content=str(resp), media_type="application/xml")