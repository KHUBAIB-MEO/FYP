"""
Analytics Module - Tracks email generation metrics
Uses SQLite for robust data storage and querying
"""
import sqlite3
import os
from datetime import datetime
from shared.settings import ANALYTICS_DB

class Analytics:
    """
    Tracks and reports email generation analytics.
    Metrics: total generated, tone distribution, length stats, send rates.
    """

    def __init__(self):
        self.db = ANALYTICS_DB
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        # Main emails table
        c.execute('''CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tone TEXT,
            length TEXT,
            model TEXT,
            topic TEXT,
            recipient_count INTEGER DEFAULT 0,
            sent INTEGER DEFAULT 0,
            subject TEXT
        )''')

        # Response tracking (manual entry by admin)
        c.execute('''CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER,
            recipient TEXT,
            responded INTEGER DEFAULT 0,
            response_time TEXT,
            FOREIGN KEY (email_id) REFERENCES emails(id)
        )''')

        conn.commit()
        conn.close()

    def log_generation(self, tone, length, model, topic="", recipient_count=0, 
                       sent=False, subject=""):
        """
        Log an email generation event

        Args:
            tone: Selected tone
            length: Selected length
            model: LLM model used
            topic: Email topic
            recipient_count: Number of recipients
            sent: Whether email was sent
            subject: Generated subject line
        """
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute('''INSERT INTO emails 
                     (timestamp, tone, length, model, topic, recipient_count, sent, subject)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (datetime.now().isoformat(), tone, length, model, topic, 
                   recipient_count, 1 if sent else 0, subject))
        conn.commit()
        conn.close()

    def log_response(self, email_id, recipient, responded=True):
        """Log a recipient response (manually tracked by admin)"""
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute('''INSERT INTO responses (email_id, recipient, responded, response_time)
                     VALUES (?, ?, ?, ?)''',
                  (email_id, recipient, 1 if responded else 0, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_stats(self):
        """
        Get comprehensive analytics statistics

        Returns:
            dict with total_generated, tone_stats, length_stats, 
            sent_count, draft_count, common_tone, response_rate
        """
        conn = sqlite3.connect(self.db)
        c = conn.cursor()

        # Total generated
        c.execute("SELECT COUNT(*) FROM emails")
        total = c.fetchone()[0]

        # Tone distribution
        c.execute("SELECT tone, COUNT(*) FROM emails GROUP BY tone")
        tone_stats = dict(c.fetchall())

        # Length distribution
        c.execute("SELECT length, COUNT(*) FROM emails GROUP BY length")
        length_stats = dict(c.fetchall())

        # Sent vs draft
        c.execute("SELECT SUM(recipient_count) FROM emails WHERE sent=1")
        sent_count = c.fetchone()[0] or 0

        c.execute("SELECT SUM(recipient_count) FROM emails WHERE sent=0")
        draft_count = c.fetchone()[0] or 0

        # Most common tone
        c.execute("SELECT tone, COUNT(*) as cnt FROM emails GROUP BY tone ORDER BY cnt DESC LIMIT 1")
        row = c.fetchone()
        common_tone = row[0] if row else "N/A"

        # Response rate
        c.execute("SELECT COUNT(*) FROM responses WHERE responded=1")
        responded = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM responses")
        total_responses = c.fetchone()[0]
        response_rate = (responded / total_responses * 100) if total_responses > 0 else 0

        # Recent activity (last 7 days)
        c.execute("SELECT COUNT(*) FROM emails WHERE timestamp > datetime('now', '-7 days')")
        recent = c.fetchone()[0]

        conn.close()

        return {
            "total_generated": total,
            "tone_stats": tone_stats,
            "length_stats": length_stats,
            "sent_count": sent_count,
            "draft_count": draft_count,
            "common_tone": common_tone,
            "response_rate": round(response_rate, 1),
            "recent_7_days": recent
        }

    def get_tone_distribution(self):
        """Get tone data for charting"""
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute("SELECT tone, COUNT(*) FROM emails GROUP BY tone")
        data = c.fetchall()
        conn.close()
        return data

    def get_length_distribution(self):
        """Get length data for charting"""
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute("SELECT length, COUNT(*) FROM emails GROUP BY length")
        data = c.fetchall()
        conn.close()
        return data

    def get_daily_activity(self):
        """Get daily generation counts for trend chart"""
        conn = sqlite3.connect(self.db)
        c = conn.cursor()
        c.execute('''SELECT date(timestamp), COUNT(*) 
                     FROM emails 
                     WHERE timestamp > datetime('now', '-30 days')
                     GROUP BY date(timestamp)
                     ORDER BY date(timestamp)''')
        data = c.fetchall()
        conn.close()
        return data
