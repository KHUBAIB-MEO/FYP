"""
Reusable UI Components with Dark Theme Support
Custom widgets for the email agent interface
"""
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from shared.settings import LIGHT_THEME

class LongPressCard(QFrame):
    """
    Email card widget with long-press detection.
    Emits signals for delete, regenerate, and send actions.
    Supports dynamic theme switching.
    """
    clicked = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    editRequested = pyqtSignal(int)
    regenerateRequested = pyqtSignal(int)
    sendRequested = pyqtSignal(int)

    def __init__(self, email_data, index, theme=None, parent=None):
        super().__init__(parent)
        self.email_data = email_data
        self.index = index
        self.theme = theme or LIGHT_THEME
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._setup_ui()

        # Long press timer
        self.press_timer = QTimer(self)
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self._show_context_menu)
        self.pressed = False

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Subject line
        subject_text = self.email_data.get("subject", "No Subject")
        self.subject_label = QLabel(f"📧 <b>{subject_text}</b>")
        self.subject_label.setWordWrap(True)
        self.subject_label.setStyleSheet(f"font-size: 14px; color: {self.theme['text']};")
        layout.addWidget(self.subject_label)

        # Metadata row
        meta_layout = QHBoxLayout()
        tone = self.email_data.get("tone", "")
        length = self.email_data.get("length", "")
        recipient = self.email_data.get("recipient", "")

        meta_text = f"<span style='color:{self.theme['primary']};font-weight:600;'>{tone}</span> • {length}"
        if recipient:
            meta_text += f" • To: {recipient}"

        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet(f"font-size: 12px; color: {self.theme['text_light']};")
        meta_layout.addWidget(meta_label)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Body preview
        body = self.email_data.get("body", "")
        preview = body[:180] + "..." if len(body) > 180 else body
        self.body_label = QLabel(preview)
        self.body_label.setWordWrap(True)
        self.body_label.setStyleSheet(f"font-size: 13px; color: {self.theme['text_secondary']}; line-height: 1.5;")
        layout.addWidget(self.body_label)

        # Hint
        hint = QLabel("Long press for options • Click to select")
        hint.setStyleSheet(f"font-size: 11px; color: {self.theme['hint_text']}; font-style: italic;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.setLayout(layout)
        self.setMinimumHeight(140)

    def update_theme(self, theme):
        """Update component colors for theme change"""
        self.theme = theme
        self.subject_label.setStyleSheet(f"font-size: 14px; color: {theme['text']};")
        self.body_label.setStyleSheet(f"font-size: 13px; color: {theme['text_secondary']}; line-height: 1.5;")
        # Update metadata
        tone = self.email_data.get("tone", "")
        length = self.email_data.get("length", "")
        recipient = self.email_data.get("recipient", "")
        meta_text = f"<span style='color:{theme['primary']};font-weight:600;'>{tone}</span> • {length}"
        if recipient:
            meta_text += f" • To: {recipient}"
        # Find and update meta label (second widget in layout)
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and isinstance(item.layout(), QHBoxLayout):
                for j in range(item.layout().count()):
                    w = item.layout().itemAt(j).widget()
                    if isinstance(w, QLabel) and "•" in w.text():
                        w.setText(meta_text)
                        w.setStyleSheet(f"font-size: 12px; color: {theme['text_light']};")
                        break

        # Update hint
        for i in range(self.layout().count()):
            w = self.layout().itemAt(i).widget()
            if isinstance(w, QLabel) and "Long press" in w.text():
                w.setStyleSheet(f"font-size: 11px; color: {theme['hint_text']}; font-style: italic;")
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed = True
            self.press_timer.start(800)  # 800ms for long press
            self.setStyleSheet(f"background-color: {self.theme['hover']}; border: 2px solid {self.theme['primary']};")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.press_timer.stop()
        self.pressed = False
        self.setStyleSheet("")  # Reset to default from QSS

        if event.button() == Qt.MouseButton.LeftButton:
            # If it was a short click, emit clicked
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)

    def _show_context_menu(self):
        """Show context menu on long press"""
        self.setStyleSheet("")  # Reset style

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {self.theme['menu_bg']};
                border: 1px solid {self.theme['border']};
                border-radius: 10px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                color: {self.theme['text_secondary']};
            }}
            QMenu::item:selected {{
                background-color: {self.theme['nav_active_bg']};
                color: {self.theme['primary']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {self.theme['separator']};
                margin: 6px 12px;
            }}
        """)

        # Edit action
        edit_action = QAction("✏️  Edit", self)
        edit_action.triggered.connect(lambda: self.editRequested.emit(self.index))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("🗑  Delete", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.index))
        menu.addAction(delete_action)

        # Regenerate action
        regen_action = QAction("🔄  Regenerate", self)
        regen_action.triggered.connect(lambda: self.regenerateRequested.emit(self.index))
        menu.addAction(regen_action)

        menu.addSeparator()

        # Send action
        send_action = QAction("📤  Send Now", self)
        send_action.triggered.connect(lambda: self.sendRequested.emit(self.index))
        menu.addAction(send_action)

        menu.exec(self.mapToGlobal(QPoint(self.width()//2, self.height()//2)))

    def update_data(self, email_data):
        """Update card with new email data"""
        self.email_data = email_data
        self.subject_label.setText(f"📧 <b>{email_data.get('subject', 'No Subject')}</b>")
        body = email_data.get("body", "")
        preview = body[:180] + "..." if len(body) > 180 else body
        self.body_label.setText(preview)


class StatCard(QFrame):
    """Dashboard statistic card with number and label. Theme-aware."""

    def __init__(self, number, label, color="#6366f1", theme=None, parent=None):
        super().__init__(parent)
        self.theme = theme or LIGHT_THEME
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        self.number_label = QLabel(str(number))
        self.number_label.setStyleSheet(f"font-size: 36px; font-weight: 700; color: {color};")
        layout.addWidget(self.number_label)

        self.text_label = QLabel(label)
        self.text_label.setStyleSheet(f"font-size: 13px; color: {self.theme['text_light']}; font-weight: 500;")
        layout.addWidget(self.text_label)

        self.setLayout(layout)
        self.setMinimumWidth(160)

    def set_value(self, number):
        self.number_label.setText(str(number))

    def update_theme(self, theme):
        """Update card for theme change"""
        self.theme = theme
        self.text_label.setStyleSheet(f"font-size: 13px; color: {theme['text_light']}; font-weight: 500;")


class RecipientItem(QWidget):
    """Custom widget for recipient list items with checkbox and info. Theme-aware."""

    toggled = pyqtSignal(str, bool)

    def __init__(self, email, name="", theme=None, parent=None):
        super().__init__(parent)
        self.email = email
        self.name = name
        self.theme = theme or LIGHT_THEME

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.toggled.connect(self._on_toggle)
        layout.addWidget(self.checkbox)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        display = f"{name} <{email}>" if name else email
        self.email_label = QLabel(display)
        self.email_label.setStyleSheet(f"font-size: 13px; color: {self.theme['text']};")
        info_layout.addWidget(self.email_label)

        if name:
            self.sub_label = QLabel(email)
            self.sub_label.setStyleSheet(f"font-size: 11px; color: {self.theme['hint_text']};")
            info_layout.addWidget(self.sub_label)

        layout.addLayout(info_layout)
        layout.addStretch()

    def _on_toggle(self, checked):
        self.toggled.emit(self.email, checked)

    def is_checked(self):
        return self.checkbox.isChecked()

    def set_checked(self, checked):
        self.checkbox.setChecked(checked)

    def update_theme(self, theme):
        """Update colors for theme change"""
        self.theme = theme
        self.email_label.setStyleSheet(f"font-size: 13px; color: {theme['text']};")
        if hasattr(self, 'sub_label'):
            self.sub_label.setStyleSheet(f"font-size: 11px; color: {theme['hint_text']};")


class LoadingOverlay(QWidget):
    """Loading overlay with spinner. Theme-aware."""

    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme or LIGHT_THEME
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setStyleSheet(f"background-color: {self.theme['overlay']};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel("⏳ Generating...")
        self.spinner_label.setStyleSheet(f"font-size: 18px; color: {self.theme['primary']}; font-weight: 600;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spinner_label)

        self.setLayout(layout)
        self.hide()

    def show_message(self, msg):
        self.spinner_label.setText(f"⏳ {msg}")
        self.show()
        self.raise_()

    def hide_overlay(self):
        self.hide()

    def update_theme(self, theme):
        """Update overlay for theme change"""
        self.theme = theme
        self.setStyleSheet(f"background-color: {theme['overlay']};")
        self.spinner_label.setStyleSheet(f"font-size: 18px; color: {theme['primary']}; font-weight: 600;")
