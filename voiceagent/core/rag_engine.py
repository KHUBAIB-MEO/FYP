"""
rag_engine.py - Builds a searchable knowledge base from the owner's
documents and answers questions using Groq, grounded in those docs.
"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"
import chromadb
from sentence_transformers import SentenceTransformer
from voiceagent.core.doc_reader import read_file, chunk_text
from voiceagent.core.brain import Brain

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS = os.path.join(BASE, "uploads")
DB_DIR = os.path.join(BASE, "data", "chroma")


class RAGEngine:
    def __init__(self):
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=DB_DIR)
        self.collection = self.client.get_or_create_collection("company_docs")
        self.brain = Brain()

    def ingest_folder(self):
        """Read every file in uploads/ and add it to the knowledge base."""
        count = 0
        for name in os.listdir(UPLOADS):
            path = os.path.join(UPLOADS, name)
            if not os.path.isfile(path):
                continue
            text = read_file(path)
            if not text.strip():
                continue
            chunks = chunk_text(text)
            for idx, chunk in enumerate(chunks):
                vec = self.embedder.encode(chunk).tolist()
                self.collection.add(
                    ids=[f"{name}_{idx}"],
                    embeddings=[vec],
                    documents=[chunk],
                    metadatas=[{"source": name}],
                )
                count += 1
        return count

    def reset(self):
        """Clear the knowledge base (used before re-ingesting)."""
        try:
            self.client.delete_collection("company_docs")
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection("company_docs")

    def answer(self, question, top_k=3):
        """Answer a question using only the ingested documents."""
        # Reconnect in case the collection was rebuilt elsewhere
        try:
            self.collection = self.client.get_or_create_collection(
                "company_docs")
        except Exception as e:
            print(f"[RAG reconnect error] {e}")
            return "Sorry, I don't have any company information right now."

        if self.collection.count() == 0:
            return "Sorry, I don't have any company information yet."

        q_vec = self.embedder.encode(question).tolist()
        results = self.collection.query(
            query_embeddings=[q_vec], n_results=top_k)
        found = results.get("documents", [[]])[0]

        if not found:
            return "Sorry, I don't have information about that."

        context = "\n\n".join(found)
        system = (
            "You are a company phone assistant. Answer the caller's question "
            "using ONLY the context below. If the answer is not in the "
            "context, say you don't have that information. Keep it short and "
            "natural for a phone call.\n\n"
            f"CONTEXT:\n{context}"
        )
        return self.brain.ask(question, system_prompt=system)