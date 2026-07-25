"""
test_phase2.py - Check a slot and optionally book it.
"""
import datetime
from voiceagent.core.calendar_agent import CalendarAgent


def main():
    print("=" * 50)
    print("  VOICE AGENT - PHASE 2 CALENDAR TEST")
    print("=" * 50)

    cal = CalendarAgent()
    print("Connected to Google Calendar!\n")

    # Test slot: tomorrow at 5:00 PM, for 1 hour
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
    slot = tomorrow.replace(hour=17, minute=0, second=0, microsecond=0)
    # No offset attached here — calendar_agent handles the timezone

    print(f"Checking slot: {slot.strftime('%A %d %b, %I:%M %p')}")
    if cal.is_slot_free(slot):
        print("-> Slot is FREE.")
        answer = input("Book it? (y/n): ").strip().lower()
        if answer == "y":
            cal.book_meeting(slot, "Test Meeting (Voice Agent)",
                             description="Booked by Voice Agent Phase 2")
            print("-> Meeting booked! Check your Google Calendar.")
    else:
        print("-> Slot is ALREADY BOOKED. No slot available.")


if __name__ == "__main__":
    main()