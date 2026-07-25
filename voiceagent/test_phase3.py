"""
test_phase3.py - Full email approval loop.
"""
from voiceagent.core.email_agent import EmailAgent


def main():
    print("=" * 50)
    print("  VOICE AGENT - PHASE 3 EMAIL TEST")
    print("=" * 50)

    ea = EmailAgent()
    client_name = "Ahmed Khan"
    client_email = input("Client's email (where final result goes): ").strip()
    slot_text = "Tuesday, 5:00 PM"

    print("\n1) Emailing the assistant for approval...")
    ea.request_approval(client_name, slot_text)
    print("   Sent! Now go to the ASSISTANT inbox and REPLY with YES or NO.")

    print("\n2) Waiting for the assistant's reply (up to 2 minutes)...")
    result = ea.wait_for_reply(timeout_seconds=120, check_every=10)
    print(f"   Assistant said: {result.upper()}")

    if result == "yes":
        ea.confirm_to_client(client_email, slot_text, confirmed=True)
        print("3) Client emailed: CONFIRMED.")
    elif result == "no":
        ea.confirm_to_client(client_email, slot_text, confirmed=False)
        print("3) Client emailed: NOT confirmed.")
    else:
        print("3) No reply received in time (timeout).")


if __name__ == "__main__":
    main()