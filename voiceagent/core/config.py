"""
config.py - Editable settings the owner can change from the dashboard
(without touching .env). Stored as JSON.
"""
import os
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE, "data", "settings.json")

DEFAULTS = {"assistant_email": ""}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    return dict(DEFAULTS)


def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    current = load_settings()
    current.update(data)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current


def get_assistant_email():
    """Dashboard value first; fall back to .env if empty."""
    email = load_settings().get("assistant_email", "").strip()
    if email:
        return email
    return os.getenv("ASSISTANT_EMAIL", "")