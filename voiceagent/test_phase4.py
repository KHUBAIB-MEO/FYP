"""
test_phase4.py - Build the knowledge base, then ask it questions.
"""
from voiceagent.core.rag_engine import RAGEngine


def main():
    print("=" * 50)
    print("  VOICE AGENT - PHASE 4 RAG TEST")
    print("=" * 50)

    rag = RAGEngine()
    print("Resetting and ingesting documents from uploads/ ...")
    rag.reset()
    n = rag.ingest_folder()
    print(f"Added {n} chunks to the knowledge base.\n")

    print("Ask questions about the company. Type 'quit' to exit.\n")
    while True:
        q = input("Client: ").strip()
        if q.lower() in ("quit", "exit", "q"):
            break
        if not q:
            continue
        print(f"Agent:  {rag.answer(q)}\n")


if __name__ == "__main__":
    main()