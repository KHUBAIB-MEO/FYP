"""
email_agent.py - Sends approval requests and confirmations,
and reads the assistant's YES/NO reply.
"""
import os
import time
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from dotenv import load_dotenv
from voiceagent.core.config import get_assistant_email


load_dotenv()
GMAIL = os.getenv("GMAIL_ADDRESS")
APP_PW = os.getenv("GMAIL_APP_PASSWORD")
ASSISTANT = get_assistant_email()


class EmailAgent:
    def send(self, to_email, subject, body):
        """Send a plain-text email."""
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL, APP_PW)
            server.send_message(msg)
        return True

    def request_approval(self, client_name, slot_text):
        """Email the assistant asking them to approve a meeting."""
        subject = f"Meeting approval needed: {client_name}"
        body = (
            f"A client named {client_name} has requested a meeting at:\n"
            f"{slot_text}\n\n"
            f"Reply to this email with YES to confirm, or NO to decline."
        )
        self.send(ASSISTANT, subject, body)

    def wait_for_reply(self, timeout_seconds=120, check_every=10):
        """
        Poll the inbox for a reply from the assistant containing
        YES or NO. Returns 'yes', 'no', or 'timeout'.
        """
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            answer = self._check_inbox()
            if answer in ("yes", "no"):
                return answer
            time.sleep(check_every)
        return "timeout"

    def _check_inbox(self):
        """Look at the newest unread email from the assistant."""
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL, APP_PW)
            mail.select("inbox")
            status, data = mail.search(
                None, f'(UNSEEN FROM "{ASSISTANT}")')
            ids = data[0].split()
            if not ids:
                mail.logout()
                return None
            latest = ids[-1]
            status, msg_data = mail.fetch(latest, "(RFC822)")
            raw = email.message_from_bytes(msg_data[0][1])
            text = self._get_text(raw)
            mail.store(latest, "+FLAGS", "\\Seen")
            mail.logout()
            return self._interpret(text)
        except Exception as e:
            print(f"[Inbox check error] {e}")
            return None

    def _interpret(self, text):
        """Read only the reply, ignoring the quoted original email."""
        reply_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            # Stop at the quoted original (Gmail quote markers)
            if stripped.startswith(">"):
                continue
            if stripped.startswith("On ") and "wrote:" in stripped:
                break
            if stripped.startswith("From:") or stripped.startswith("-----"):
                break
            reply_lines.append(stripped)

        reply = " ".join(reply_lines).lower()

        # Check for whole-word yes/no in the reply only
        words = reply.replace(",", " ").replace(".", " ").split()
        if "no" in words:
            return "no"
        if "yes" in words:
            return "yes"
        return None

    def _get_text(self, msg):
        """Extract plain text from an email message."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(
                        errors="ignore")
            return ""
        return msg.get_payload(decode=True).decode(errors="ignore")

    def confirm_to_client(self, client_email, slot_text, confirmed):
        """Email the client the final decision."""
        if confirmed:
            subject = "Your meeting is confirmed"
            body = (f"Good news! Your meeting at {slot_text} "
                    f"has been confirmed. We look forward to speaking "
                    f"with you.")
        else:
            subject = "Your meeting could not be confirmed"
            body = (f"Unfortunately your meeting at {slot_text} "
                    f"could not be confirmed at this time. "
                    f"Please contact us to arrange another slot.")
        self.send(client_email, subject, body)