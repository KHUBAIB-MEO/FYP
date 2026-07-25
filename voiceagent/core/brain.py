"""
brain.py - The AI brain of the Voice Agent, powered by Groq.
Phase 1: plain text in, text out. Later phases add RAG + scheduling.
"""
import os
from groq import Groq
from dotenv import load_dotenv

# Load the API key from voiceagent/.env
load_dotenv()

# The model we use. llama-3.3-70b is smart and free-tier friendly.
MODEL = "llama-3.3-70b-versatile"


class Brain:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Put it in voiceagent/.env"
            )
        self.client = Groq(api_key=api_key)

    def ask(self, user_message, system_prompt=None):
        """Send a message to Groq and return the AI's reply as text."""
        if system_prompt is None:
            system_prompt = (
                "You are a helpful, polite voice assistant for a business. "
                "Keep answers short and natural, as if speaking on a phone call."
            )
        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Brain error] {e}"