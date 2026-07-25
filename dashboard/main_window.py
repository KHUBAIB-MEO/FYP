"""
Main Application Window - Central hub for all AI Agents
Dashboard → Email Agent | Content Scripting Agent | (Future agents)
"""
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import QWidget

from dashboard.styles import generate_stylesheet
from dashboard.dashboard_page import DashboardPage
from producthunter2.producthunter2_page import ProductHunter2Page
from emailagent.email_page import EmailPage
from contentscripting.content_page import ContentPage
from emailscraper.emailscraper_page import EmailScraperPage
from shared.settings import APP_NAME, get_theme, save_theme, LIGHT_THEME, DARK_THEME
from voiceagent.voiceagent_page import VoiceAgentPage


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
        self.scraper_page = EmailScraperPage(self.current_theme)
        self.hunter2_page = ProductHunter2Page(self.current_theme)
        self.voice_page = None  # built on first click (keeps startup fast)
        

        # Add to stack
        self.central_stack.addWidget(self.dashboard_page)
        self.central_stack.addWidget(self.email_page)
        self.central_stack.addWidget(self.content_page)
        self.central_stack.addWidget(self.scraper_page)
        self.central_stack.addWidget(self.hunter2_page)
        
        

        # Connect signals
        self.dashboard_page.agentSelected.connect(self._open_agent)
        self.dashboard_page.theme_btn.clicked.connect(self._toggle_theme)
        self.email_page.backToDashboard.connect(self._back_to_dashboard)
        self.content_page.backToDashboard.connect(self._back_to_dashboard)
        self.scraper_page.backToDashboard.connect(self._back_to_dashboard)
        self.hunter2_page.backToDashboard.connect(self._back_to_dashboard)
        self.hunter2_page.sendToContentAgent.connect(self._handle_content_from_hunter)
        self.scraper_page.sendToEmailAgent.connect(self._handle_leads_from_scraper)
        

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
        elif agent_id == "emailscraper":
            self.central_stack.setCurrentWidget(self.scraper_page)
        elif agent_id == "producthunter2":
            self.central_stack.setCurrentWidget(self.hunter2_page)
        elif agent_id == "voiceagent":
            if self.voice_page is None:
                self.voice_page = VoiceAgentPage(
                    go_back=self._back_to_dashboard)
                self.central_stack.addWidget(self.voice_page)
            self.central_stack.setCurrentWidget(self.voice_page)

    def _handle_leads_from_scraper(self, leads):
        self.email_page.add_recipients_from_leads(leads)
        self.central_stack.setCurrentWidget(self.email_page)

    def _handle_content_from_hunter(self, payload):
        self.content_page.topic_input.setPlainText(payload.get("topic", ""))
        self.content_page.keywords_input.setText(payload.get("keywords", ""))
        self.central_stack.setCurrentWidget(self.content_page)

    def _back_to_dashboard(self):
        """Return to dashboard from any agent"""
        self.central_stack.setCurrentIndex(0)

    def _force_restyle(self, widget):
        """Force Qt to drop cached styling and recompute — without this,
        a theme change often doesn't visually apply because Qt caches
        stylesheets and inline styles override the global one."""
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
        for child in widget.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
            child.update()

    def _toggle_theme(self):
        """Toggle theme WITHOUT rebuilding pages (rebuilding re-ran the slow
        Ollama network call and hung the app). Each page re-themes itself
        in place; the global stylesheet is re-applied for the shell."""
        self.is_dark = not self.is_dark
        self.current_theme = DARK_THEME if self.is_dark else LIGHT_THEME
        save_theme(self.is_dark)

        # Re-theme each page in place (lightweight, no __init__, no network)
        self.dashboard_page.update_theme(self.current_theme)
        self.email_page.update_theme(self.current_theme)
        self.content_page.update_theme(self.current_theme)
        self.scraper_page.update_theme(self.current_theme)
        self.hunter2_page.update_theme(self.current_theme)

        self.dashboard_page.theme_btn.setText(
            "\u2600\ufe0f  Light Mode" if self.is_dark else "\U0001f319  Dark Mode"
        )

        # Re-apply the global stylesheet so the window shell + any
        # selector-based styling updates too.
        self.setStyleSheet(generate_stylesheet(self.current_theme))

        # Force Qt to drop cached styling on every widget so inline styles
        # that were just updated actually repaint.
        for page in [self.dashboard_page, self.email_page, self.content_page,
                     self.scraper_page, self.hunter2_page]:
            page.style().unpolish(page)
            page.style().polish(page)
            page.update()
            for child in page.findChildren(QWidget):
                child.style().unpolish(child)
                child.style().polish(child)
                child.update()

    def _apply_styles(self):
        """Apply global stylesheet"""
        self.setStyleSheet(generate_stylesheet(self.current_theme))
