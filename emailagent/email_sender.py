"""
Email Sender - SMTP-based email delivery
Supports bulk sending with progress tracking
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Tuple

class EmailSender:
    """
    Handles SMTP email sending with support for bulk delivery.
    Compatible with Gmail, Outlook, and custom SMTP servers.
    """

    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587, 
                 username="", password="", use_tls=True):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.last_error = None

    def test_connection(self):
        """Test SMTP connection with current credentials"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.quit()
            return True, "Connection successful"
        except Exception as e:
            self.last_error = str(e)
            return False, str(e)

    def send_bulk(self, recipients: List[dict], subject: str, body: str, 
                  signature: str = "", progress_callback=None) -> Tuple[int, List]:
        """
        Send emails to multiple recipients

        Args:
            recipients: List of dicts with 'email' and optionally 'name'
            subject: Email subject
            body: Email body
            signature: Optional signature to append
            progress_callback: Function(current, total) for progress updates

        Returns:
            Tuple of (success_count, failed_list)
        """
        if not recipients:
            return 0, []

        sent_count = 0
        failed = []
        total = len(recipients)

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)

            for idx, recipient in enumerate(recipients):
                email = recipient.get("email", "")
                name = recipient.get("name", "")

                try:
                    # Personalize subject and body
                    personalized_subject = subject
                    personalized_body = body

                    if name:
                        personalized_body = personalized_body.replace("{name}", name)
                        personalized_body = personalized_body.replace("{Name}", name)

                    # Build message
                    msg = MIMEMultipart('alternative')
                    msg['From'] = self.username
                    msg['To'] = email
                    msg['Subject'] = Header(personalized_subject, 'utf-8')

                    full_body = personalized_body
                    if signature:
                        full_body += f"\n\n---\n{signature}"

                    msg.attach(MIMEText(full_body, 'plain', 'utf-8'))

                    server.send_message(msg)
                    sent_count += 1

                except Exception as e:
                    failed.append({"email": email, "error": str(e)})

                if progress_callback:
                    progress_callback(idx + 1, total)

            server.quit()

        except Exception as e:
            self.last_error = str(e)
            # If connection failed, all are failed
            if sent_count == 0:
                for r in recipients:
                    failed.append({"email": r.get("email", ""), "error": str(e)})

        return sent_count, failed

    def send_single(self, to_email: str, subject: str, body: str, 
                    signature: str = "", name: str = "") -> Tuple[bool, str]:
        """
        Send a single email

        Returns:
            Tuple of (success, message)
        """
        recipients = [{"email": to_email, "name": name}]
        sent, failed = self.send_bulk(recipients, subject, body, signature)

        if sent > 0:
            return True, "Email sent successfully"
        elif failed:
            return False, failed[0].get("error", "Unknown error")
        return False, "Failed to send"
