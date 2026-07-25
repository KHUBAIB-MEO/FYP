"""
doc_reader.py - Reads PDF, DOCX, and TXT files into plain text,
then splits the text into small chunks for RAG.
"""
import os
from pypdf import PdfReader
from docx import Document


def read_file(path):
    """Return the plain text of a pdf, docx, or txt file."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = ""
        for page in PdfReader(path).pages:
            text += (page.extract_text() or "") + "\n"
        return text
    if ext == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks of words."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks