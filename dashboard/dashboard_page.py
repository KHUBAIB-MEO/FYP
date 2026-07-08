"""
Dashboard - Central hub for all AI Agents
Professional, minimalist card-based layout
"""
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from shared.settings import get_theme


class AgentCard(QFrame):
    """Clickable agent card with icon, title, description."""
    clicked = pyqtSignal(str)

    def __init__(self, agent_id, icon, title, description, theme, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.theme = theme
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(250)
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("font-size: 42px; background: transparent; border: none;")
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.title_label = QLabel(title)
        layout.addWidget(self.title_label)

        self.desc_label = QLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMinimumHeight(76)
        layout.addWidget(self.desc_label)

        layout.addStretch()

        self.arrow_label = QLabel("\u2192  Open Agent")
        layout.addWidget(self.arrow_label)

        self._apply_labels()
        self._apply_base_style(hover=False)

    def _apply_labels(self):
        self.title_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {self.theme['text']};"
            f" background: transparent; border: none;"
        )
        self.desc_label.setStyleSheet(
            f"font-size: 13px; color: {self.theme['text_light']};"
            f" background: transparent; border: none;"
        )
        self.arrow_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {self.theme['primary']};"
            f" background: transparent; border: none;"
        )
        self.icon_label.setStyleSheet("font-size: 42px; background: transparent; border: none;")

    def _apply_base_style(self, hover):
        border = self.theme["primary"] if hover else self.theme["border"]
        bg = self.theme["hover"] if hover else self.theme["card"]
        self.setStyleSheet(
            f"QFrame#card {{"
            f"  background-color: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 16px;"
            f"}}"
        )

    def update_theme(self, theme):
        """Recolor the card and all its labels for the new theme."""
        self.theme = theme
        self._apply_labels()
        self._apply_base_style(hover=False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._apply_base_style(hover=True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._apply_base_style(hover=True)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.agent_id)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self._apply_base_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_base_style(hover=False)
        super().leaveEvent(event)


class DashboardPage(QWidget):
    """Main dashboard showing all available agents"""

    agentSelected = pyqtSignal(str)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._setup_ui()

    def _setup_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(32)

        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        self.title_label = QLabel("\U0001F916 AI Agent Platform")
        title_layout.addWidget(self.title_label)
        self.subtitle_label = QLabel("Select an agent to get started")
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.theme_btn = QPushButton("\U0001F319  Dark Mode")
        self.theme_btn.setObjectName("theme_toggle")
        self.theme_btn.setFixedWidth(140)
        self.theme_btn.setFixedHeight(40)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(self.theme_btn)
        layout.addLayout(header_layout)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.separator)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(24)

        self.cards = []

        self.email_card = AgentCard(
            "email", "\u2709\uFE0F", "Email Agent",
            "Generate professional, funny, emotional, or persuasive emails. Import recipients from Excel, auto-generate subject lines, and send bulk emails with one click.",
            self.theme)
        self.email_card.clicked.connect(self.agentSelected.emit)
        self.cards.append(self.email_card)

        self.content_card = AgentCard(
            "content", "\U0001F4DD", "Content Scripting",
            "Generate blog posts, social media captions, ad copy, scripts, and any content with AI. Choose your model, set the tone, and get polished content instantly.",
            self.theme)
        self.content_card.clicked.connect(self.agentSelected.emit)
        self.cards.append(self.content_card)

        self.scraper_card = AgentCard(
            "emailscraper", "\U0001F4E7", "Email Scraper",
            "Find business emails by keyword and city - searches Google Maps, crawls each website, and builds a ready-to-use lead list for the Email Agent.",
            self.theme)
        self.scraper_card.clicked.connect(self.agentSelected.emit)
        self.cards.append(self.scraper_card)

        self.hunter2_card = AgentCard(
            "producthunter2", "\U0001F6D2", "Product Hunter",
            "Finds trending best-seller products and scores each one for opportunity - demand vs competition vs profit - so you spot winners, not just popular items.",
            self.theme)
        self.hunter2_card.clicked.connect(self.agentSelected.emit)
        self.cards.append(self.hunter2_card)

        COLUMNS = 3
        for i, card in enumerate(self.cards):
            grid_layout.addWidget(card, i // COLUMNS, i % COLUMNS, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(grid_layout)

        self.footer_label = QLabel("More agents coming soon - Built with love for your FYP")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.footer_label)
        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        self._apply_chrome_styles()

    def _apply_chrome_styles(self):
        """Style the (non-card) chrome: title, subtitle, footer, separator,
        theme button. Called on build and on every theme change."""
        t = self.theme
        self.title_label.setStyleSheet(
            f"font-size: 36px; font-weight: 800; color: {t['text']}; background: transparent;"
        )
        self.subtitle_label.setStyleSheet(
            f"font-size: 16px; color: {t['text_light']}; margin-top: 4px; background: transparent;"
        )
        self.footer_label.setStyleSheet(
            f"font-size: 13px; color: {t['text_light']}; margin-top: 40px; background: transparent;"
        )
        self.separator.setStyleSheet(f"background-color: {t['border']}; max-height: 1px;")
        self.theme_btn.setStyleSheet(
            f"QPushButton {{ background-color: {t['hover']}; color: {t['text_light']};"
            f" border: 1px solid {t['border']}; border-radius: 20px; padding: 8px 16px;"
            f" font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {t['border']}; color: {t['text']}; }}"
        )

    def update_theme(self, theme):
        """Recolor the whole dashboard in place: chrome + every card."""
        self.theme = theme
        self._apply_chrome_styles()
        for card in self.cards:
            card.update_theme(theme)