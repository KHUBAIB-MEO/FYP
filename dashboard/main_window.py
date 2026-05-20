"""
Main Application Window - Central hub for all AI Agents
Dashboard → Email Agent | Content Scripting Agent | (Future agents)
"""
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from dashboard.styles import generate_stylesheet
from dashboard.dashboard_page import DashboardPage
from emailagent.email_page import EmailPage
from contentscripting.content_page import ContentPage
from producthunter.producthunter_page import ProductHunterPage
from shared.settings import APP_NAME, get_theme, save_theme, LIGHT_THEME, DARK_THEME


class MainWindow(QMainWindow):
    """
    Central application window.
    Shows Dashboard first. Click agent card → navigate to agent page.
    Back button returns to Dashboard. Supports Light/Dark theme.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1400, 900)

        # Theme state
        self.current_theme = get_theme()
        self.is_dark = self.current_theme == DARK_THEME

        # Central stacked widget for all pages
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # Create pages
        self.dashboard_page = DashboardPage(self.current_theme)
        self.email_page = EmailPage(self.current_theme)
        self.content_page = ContentPage(self.current_theme)
        self.product_hunter_page = ProductHunterPage(self.current_theme)

        # Add to stack
        self.central_stack.addWidget(self.dashboard_page)
        self.central_stack.addWidget(self.email_page)
        self.central_stack.addWidget(self.content_page)
        self.central_stack.addWidget(self.product_hunter_page)

        # Connect signals
        self.dashboard_page.agentSelected.connect(self._open_agent)
        self.dashboard_page.theme_btn.clicked.connect(self._toggle_theme)

        self.email_page.backToDashboard.connect(self._back_to_dashboard)
        self.content_page.backToDashboard.connect(self._back_to_dashboard)
        self.product_hunter_page.backToDashboard.connect(self._back_to_dashboard)

        # Apply initial styles
        self._apply_styles()

        # Show dashboard first
        self.central_stack.setCurrentIndex(0)



        

        

    def _open_agent(self, agent_id):
        """Open the selected agent page"""
        if agent_id == "email":
            self.central_stack.setCurrentIndex(1)
            self.email_page._load_models()
            self.email_page._check_ollama()
        elif agent_id == "content":
            self.central_stack.setCurrentIndex(2)
            self.content_page._load_models()
            self.content_page._check_ollama()
        elif agent_id == "producthunter":
            self.central_stack.setCurrentWidget(self.product_hunter_page)

    def _back_to_dashboard(self):
        """Return to dashboard from any agent"""
        self.central_stack.setCurrentIndex(0)

    def _toggle_theme(self):
        """Toggle between light and dark themes globally"""
        self.is_dark = not self.is_dark
        self.current_theme = DARK_THEME if self.is_dark else LIGHT_THEME
        self.product_hunter_page.update_theme(self.current_theme)

        # Save preference
        save_theme(self.is_dark)

        # Update all pages
        self.dashboard_page.update_theme(self.current_theme)
        self.email_page.update_theme(self.current_theme)
        self.content_page.update_theme(self.current_theme)

        # Update button texts
        btn_text = "☀️  Light Mode" if self.is_dark else "🌙  Dark Mode"
        self.dashboard_page.theme_btn.setText(btn_text)

        # Re-apply stylesheet
        self._apply_styles()

        # Force refresh
        self.update()
        QApplication.processEvents()

    def _apply_styles(self):
        """Apply global stylesheet"""
        self.setStyleSheet(generate_stylesheet(self.current_theme))
