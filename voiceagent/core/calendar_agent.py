"""
calendar_agent.py - Checks slot availability and books meetings
on the owner's Google Calendar.
"""
import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_FILE = os.path.join(BASE, "credentials.json")
TOKEN_FILE = os.path.join(BASE, "token.json")
TIMEZONE = "Asia/Karachi"
KARACHI = datetime.timezone(datetime.timedelta(hours=5))  # UTC+5   


def make_aware(dt):
    """Attach Karachi timezone to a naive datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KARACHI)
    return dt

class CalendarAgent:
    def __init__(self):
        self.service = self._connect()

    def _connect(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CRED_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def is_slot_free(self, start_dt, duration_minutes=60):
        """Return True if nothing is booked in that time window."""
        start_dt = make_aware(start_dt)
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        result = self.service.events().list(
            calendarId="primary",
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
        ).execute()
        events = result.get("items", [])
        return len(events) == 0

    def book_meeting(self, start_dt, summary, duration_minutes=60,
                     description=""):
        """Create an event and return it."""
        start_dt = make_aware(start_dt)
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": TIMEZONE,
            },
        }
        return self.service.events().insert(
            calendarId="primary", body=event).execute()