"""
Dashboard - Central hub for all AI Agents
Professional, minimalist card-based layout
"""
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from shared.settings import get_theme


class AgentCard(QFrame):
    """Clickable agent card with icon, title, description"""
    clicked = pyqtSignal(str)

    def __init__(self, agent_id, icon, title, description, theme, parent=None):
        super().__init__(parent)
        self.agent_id = agent_id
        self.theme = theme
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(200)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {theme['text']};"
        )
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(
            f"font-size: 14px; color: {theme['text_light']}; line-height: 1.5;"
        )
        layout.addWidget(desc_label)

        layout.addStretch()

        # Arrow hint
        arrow = QLabel("→  Open Agent")
        arrow.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {theme['primary']};"
        )
        layout.addWidget(arrow)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setStyleSheet(
                f"background-color: {self.theme['hover']}; "
                f"border: 2px solid {self.theme['primary']}; "
                f"border-radius: 12px; padding: 16px;"
            )
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setStyleSheet("")
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.agent_id)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet(
            f"background-color: {self.theme['hover']}; "
            f"border: 1px solid {self.theme['primary']}; "
            f"border-radius: 12px; padding: 16px;"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("")
        super().leaveEvent(event)


class DashboardPage(QWidget):
    """Main dashboard showing all available agents"""

    agentSelected = pyqtSignal(str)

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(32)

        # Header
        header_layout = QHBoxLayout()

        title_layout = QVBoxLayout()
        title = QLabel("🤖 AI Agent Platform")
        title.setStyleSheet(
            f"font-size: 36px; font-weight: 800; color: {self.theme['text']};"
        )
        title_layout.addWidget(title)

        subtitle = QLabel("Select an agent to get started")
        subtitle.setStyleSheet(
            f"font-size: 16px; color: {self.theme['text_light']}; margin-top: 4px;"
        )
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Theme toggle on dashboard
        self.theme_btn = QPushButton("🌙  Dark Mode")
        self.theme_btn.setObjectName("theme_toggle")
        self.theme_btn.setFixedWidth(140)
        self.theme_btn.setFixedHeight(40)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self.theme['hover']};"
            f"  color: {self.theme['text_light']};"
            f"  border: 1px solid {self.theme['border']};"
            f"  border-radius: 20px;"
            f"  padding: 8px 16px;"
            f"  font-size: 13px;"
            f"  font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {self.theme['border']};"
            f"  color: {self.theme['text']};"
            f"}}"
        )
        header_layout.addWidget(self.theme_btn)

        layout.addLayout(header_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {self.theme['border']}; max-height: 1px;")
        layout.addWidget(line)

        # Agents grid
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(24)
        grid_layout.addStretch()

        # Agent 1: Email Agent
        self.email_card = AgentCard(
            "email",
            "✉️",
            "Email Agent",
            "Generate professional, funny, emotional, or persuasive emails. Import recipients from Excel, auto-generate subject lines, and send bulk emails with one click.",
            self.theme
        )
        self.email_card.clicked.connect(self.agentSelected.emit)
        grid_layout.addWidget(self.email_card)

        # Agent 2: Content Scripting
        self.content_card = AgentCard(
            "content",
            "📝",
            "Content Scripting",
            "Generate blog posts, social media captions, ad copy, scripts, and any content with AI. Choose your model, set the tone, and get polished content instantly.",
            self.theme
        )
        self.content_card.clicked.connect(self.agentSelected.emit)
        grid_layout.addWidget(self.content_card)

        # Placeholder for future agents - add more cards here easily
        # self.seo_card = AgentCard("seo", "🔍", "SEO Agent", "...", self.theme)

        grid_layout.addStretch()
        layout.addLayout(grid_layout)

        # Footer
        footer = QLabel("More agents coming soon • Built with ❤️ for your FYP")
        footer.setStyleSheet(
            f"font-size: 13px; color: {self.theme['text_light']}; margin-top: 40px;"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        layout.addStretch()

    def update_theme(self, theme):
        """Update dashboard colors when theme changes"""
        self.theme = theme
        # Update header
        for child in self.findChildren(QLabel):
            text = child.text()
            if "AI Agent Platform" in text:
                child.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {theme['text']};")
            elif "Select an agent" in text:
                child.setStyleSheet(f"font-size: 16px; color: {theme['text_light']}; margin-top: 4px;")
            elif "coming soon" in text:
                child.setStyleSheet(f"font-size: 13px; color: {theme['text_light']}; margin-top: 40px;")

        # Update theme button
        self.theme_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {theme['hover']};"
            f"  color: {theme['text_light']};"
            f"  border: 1px solid {theme['border']};"
            f"  border-radius: 20px;"
            f"  padding: 8px 16px;"
            f"  font-size: 13px;"
            f"  font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {theme['border']};"
            f"  color: {theme['text']};"
            f"}}"
        )

        # Update cards
        for card in [self.email_card, self.content_card]:
            card.theme = theme
