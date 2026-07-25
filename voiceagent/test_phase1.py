"""
test_phase1.py - Prove the Groq brain works.
Run this, type a question, get an AI answer. Type 'quit' to exit.
"""
from voiceagent.core.brain import Brain


def main():
    print("=" * 50)
    print("  VOICE AGENT - PHASE 1 BRAIN TEST")
    print("=" * 50)
    print("Type a message and the AI will reply.")
    print("Type 'quit' to exit.\n")

    brain = Brain()

    while True:
        user = input("You: ").strip()
        if user.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user:
            continue
        reply = brain.ask(user)
        print(f"AI:  {reply}\n")


if __name__ == "__main__":
    main()