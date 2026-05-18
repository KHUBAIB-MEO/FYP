"""
AI TASKFORCE - Multi-Agent Desktop Platform
=============================================
A scalable multi-agent platform featuring:
- Email Agent       (AI-powered email generation & bulk sending)
- Content Scripting Agent (AI content generation for blogs, ads, social media)
- Dashboard         (Central navigation hub with Light/Dark theme)
- Easy to add more agents in future — just add a new agent folder!

How to add a new agent:
  1. Create a folder: <agentname>/
  2. Add your agent's page (QWidget with backToDashboard signal)
  3. Add your agent's engine and any utilities inside the same folder
  4. Register it in dashboard/main_window.py and dashboard/dashboard_page.py

Author: AI TASKFORCE Team
Version: 1.0.0
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from dashboard.main_window import MainWindow


def main():
    """Application entry point"""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI TASKFORCE")
    app.setApplicationVersion("1.0.0")

    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
