"""
contacts.py - Maps caller phone numbers to email addresses.
Avoids unreliable email capture by voice.
"""
import os
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(BASE, "data", "contacts.json")


def _load():
    if os.path.exists(FILE):
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_email(phone):
    """Return the email registered for a phone number, or None."""
    return _load().get(phone)


def set_email(phone, email):
    """Register or update a phone -> email mapping."""
    data = _load()
    data[phone] = email
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def all_contacts():
    return _load()