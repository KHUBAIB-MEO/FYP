"""
voiceagent_page.py - The Voice Agent card page for the FYP dashboard.
Shows analytics, uploads documents for RAG, sets assistant email.
"""
import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt

from voiceagent.core.analytics import get_stats
from voiceagent.core.config import load_settings, save_settings


BASE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(BASE, "uploads")


class VoiceAgentPage(QWidget):
    def __init__(self, go_back=None):
        super().__init__()
        self.go_back = go_back
        self._build()

    def _stat_box(self, title, value, key):
        box = QFrame()
        box.setStyleSheet(
            "QFrame{background:#1E2761;border-radius:12px;padding:14px;}")
        lay = QVBoxLayout(box)
        v = QLabel(str(value))
        v.setStyleSheet("color:#5B7FFF;font-size:30px;font-weight:bold;")
        t = QLabel(title)
        t.setStyleSheet("color:#CADCFC;font-size:13px;")
        lay.addWidget(v)
        lay.addWidget(t)
        # Keep a reference so we can update the number later
        self.stat_labels[key] = v
        return box

    def _build(self):
        layout = QVBoxLayout(self)
        self.stat_labels = {}

        # Header
        header = QLabel("🎙  Voice Agent")
        header.setStyleSheet(
            "font-size:26px;font-weight:bold;color:#1E2761;")
        layout.addWidget(header)
        layout.addWidget(QLabel(
            "AI phone agent: schedules meetings & answers from your docs."))

        # Analytics
        stats = get_stats()
        grid = QGridLayout()
        grid.addWidget(self._stat_box("Calls Handled",
                                      stats["calls"], "calls"), 0, 0)
        grid.addWidget(self._stat_box("Meetings Booked",
                                      stats["meetings_booked"],
                                      "meetings_booked"), 0, 1)
        grid.addWidget(self._stat_box("Questions Answered",
                                      stats["questions_answered"],
                                      "questions_answered"), 0, 2)
        layout.addLayout(grid)

        refresh = QPushButton("🔄 Refresh Analytics")
        refresh.clicked.connect(self._refresh)
        layout.addWidget(refresh)

        # Assistant email setting
        layout.addWidget(QLabel("Assistant email (receives approvals):"))
        row = QHBoxLayout()
        self.email_input = QLineEdit()
        self.email_input.setText(
            load_settings().get("assistant_email", ""))
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_email)
        row.addWidget(self.email_input)
        row.addWidget(save_btn)
        layout.addLayout(row)

        # Document upload
        layout.addWidget(QLabel("Knowledge base documents (PDF/DOCX/TXT):"))
        up_row = QHBoxLayout()
        upload_btn = QPushButton("📄 Upload Document")
        upload_btn.clicked.connect(self._upload)
        rebuild_btn = QPushButton("🧠 Rebuild Knowledge Base")
        rebuild_btn.clicked.connect(self._rebuild)
        up_row.addWidget(upload_btn)
        up_row.addWidget(rebuild_btn)
        layout.addLayout(up_row)

        self.status = QLabel("")
        self.status.setStyleSheet("color:#00B894;")
        layout.addWidget(self.status)

        if self.go_back:
            back = QPushButton("← Back to Dashboard")
            back.clicked.connect(self.go_back)
            layout.addWidget(back)

        layout.addStretch()

    def _refresh(self):
        """Reload the numbers only - never rebuild the page."""
        stats = get_stats()
        for key, label in self.stat_labels.items():
            label.setText(str(stats.get(key, 0)))
        self.status.setText("✓ Analytics refreshed.")

    def _save_email(self):
        save_settings({"assistant_email": self.email_input.text().strip()})
        self.status.setText("✓ Assistant email saved.")

    def _upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a document", "",
            "Documents (*.pdf *.docx *.txt)")
        if path:
            os.makedirs(UPLOADS, exist_ok=True)
            shutil.copy(path, UPLOADS)
            self.status.setText(
                f"✓ Uploaded {os.path.basename(path)}. "
                f"Click 'Rebuild Knowledge Base'.")

    def _rebuild(self):
        self.status.setText("Rebuilding... please wait.")
        QMessageBox.information(self, "Rebuilding",
                                "This may take a moment.")
        from voiceagent.core.rag_engine import RAGEngine  # loaded on demand
        rag = RAGEngine()
        rag.reset()
        n = rag.ingest_folder()
        self.status.setText(f"✓ Knowledge base rebuilt ({n} chunks).")