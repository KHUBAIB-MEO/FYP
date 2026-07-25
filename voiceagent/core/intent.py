"""
intent.py - Works out what the caller wants and pulls out details.
Uses Groq to return structured JSON.
"""
import json
import datetime
from voiceagent.core.brain import Brain

brain = Brain()

SYSTEM = """You classify a caller's sentence for a business phone agent.
Return ONLY valid JSON, no other text, in this exact shape:
{"intent": "book" | "question" | "goodbye" | "email" | "other",
 "datetime": "YYYY-MM-DD HH:MM" or null,
 "email": "address@example.com" or null}

Rules:
- "book" if they want to schedule/arrange a meeting or appointment.
- "email" if they are giving an email address.
- "goodbye" if they are ending the call.
- "question" if they ask about the company, hours, prices, services.
- Convert spoken times to 24-hour format. Today is {today}.
- If they say a weekday, use the NEXT occurrence of that weekday.
- If no date/time mentioned, datetime must be null.

EMAIL RULES (very important):
- "double X" means the letter X twice. Example: "double e" -> "ee",
  "double l" -> "ll".
- "triple X" means the letter X three times. Example: "triple e" -> "eee",
  "triple l" -> "lll".
- The caller often SPELLS their email letter by letter, and the
  transcript will contain single letters separated by spaces or commas.
- JOIN ALL those single letters together into one word, ignoring
  spaces, commas and periods between them.
- Example: "K h u b a i b n a e e m 42 at gmail.com"
  -> "khubaibnaeem42@gmail.com"
- Example: "K h u b a i b n a double e m 42 at gmail.com"
  -> "khubaibnaeem42@gmail.com"
- Example: "K h u b a i b n a double e m triple 4 at gmail.com"
  -> "khubaibnaeem444@gmail.com"
- Example: "j o h n dot s m i t h at yahoo dot com"
  -> "john.smith@yahoo.com"
- "at" means @, "dot" means "."
- Keep any digits that follow the letters.
- NEVER return only the digits. Always include the spelled letters.
"""


def detect(text):
    """Return a dict: intent, datetime (or None), email (or None)."""
    today = datetime.date.today().isoformat()
    try:
        raw = brain.ask(text, system_prompt=SYSTEM.replace("{today}", today))
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"[INTENT ERROR] {e}")
        return {"intent": "other", "datetime": None, "email": None}

    dt = None
    if data.get("datetime"):
        try:
            dt = datetime.datetime.strptime(
                data["datetime"], "%Y-%m-%d %H:%M")
        except Exception:
            dt = None

    return {
        "intent": data.get("intent", "other"),
        "datetime": dt,
        "email": data.get("email"),
    }