"""
analytics.py - Simple call logging to a JSON file for the dashboard.
"""
import os
import json
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(BASE, "data", "analytics.json")


def _load():
    if os.path.exists(LOG):
        with open(LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"calls": 0, "meetings_booked": 0, "questions_answered": 0,
            "history": []}


def _save(data):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log_event(kind):
    """kind = 'call' | 'meeting' | 'question'"""
    d = _load()
    if kind == "call":
        d["calls"] += 1
    elif kind == "meeting":
        d["meetings_booked"] += 1
    elif kind == "question":
        d["questions_answered"] += 1
    d["history"].append({
        "kind": kind,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    d["history"] = d["history"][-50:]  # keep last 50
    _save(d)


def get_stats():
    return _load()