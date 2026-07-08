"""
Email Agent Page - Standalone page with back navigation
"""
import os
import re
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from shared.settings import EMAIL_TONES, EMAIL_LENGTHS, get_theme
from emailagent.email_engine import EmailEngine
from emailagent.analytics import Analytics
from shared.ollama_client import OllamaClient
from emailagent.excel_parser import ExcelParser
from emailagent.email_sender import EmailSender
from dashboard.components import LongPressCard, StatCard, RecipientItem, LoadingOverlay

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('Qt5Agg')


class EmailPage(QWidget):
    """Email Agent as a standalone page with back navigation"""

    backToDashboard = pyqtSignal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.is_dark = theme == get_theme()

        self.email_engine = EmailEngine()
        self.analytics = Analytics()
        self.ollama_client = OllamaClient()
        self.email_sender = EmailSender()

        self.recipients = []
        self.generated_emails = []
        self.current_model = "qwen2.5:7b"

        self._setup_ui()
        self._load_models()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Stacked pages: Compose | Analytics | Settings
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {self.theme['bg']};")

        self.compose_page = self._create_compose_page()
        self.analytics_page = self._create_analytics_page()
        self.settings_page = self._create_settings_page()

        self.stack.addWidget(self.compose_page)
        self.stack.addWidget(self.analytics_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.stack, stretch=1)

        # Loading overlay
        self.overlay = LoadingOverlay(self, self.theme)
        self.overlay.setGeometry(self.rect())

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background-color: {self.theme['sidebar']}; border-right: 1px solid {self.theme['border']};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)

        # Back button
        back_btn = QPushButton("←  Back to Dashboard")
        back_btn.setObjectName("secondary")
        back_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self.theme['hover']};"
            f"  color: {self.theme['text_secondary']};"
            f"  border: 1px solid {self.theme['border']};"
            f"  padding: 10px 16px;"
            f"  border-radius: 8px;"
            f"  font-weight: 600;"
            f"  font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {self.theme['border']};"
            f"  color: {self.theme['text']};"
            f"}}"
        )
        back_btn.clicked.connect(self.backToDashboard.emit)
        layout.addWidget(back_btn)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {self.theme['border']}; max-height: 1px; margin: 8px 0;")
        layout.addWidget(line)

        # App title
        title = QLabel("✉️  Email Agent")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text']}; padding: 8px 0 16px 0;")
        layout.addWidget(title)

        # Nav buttons
        self.nav_compose = QPushButton("✏️  Compose")
        self.nav_compose.setObjectName("nav_button")
        self.nav_compose.setCheckable(True)
        self.nav_compose.setChecked(True)
        self.nav_compose.setStyleSheet(self._nav_button_style())
        self.nav_compose.clicked.connect(lambda: self._switch_page(0))
        layout.addWidget(self.nav_compose)

        self.nav_analytics = QPushButton("📊  Analytics")
        self.nav_analytics.setObjectName("nav_button")
        self.nav_analytics.setCheckable(True)
        self.nav_analytics.setStyleSheet(self._nav_button_style())
        self.nav_analytics.clicked.connect(lambda: self._switch_page(1))
        layout.addWidget(self.nav_analytics)

        self.nav_settings = QPushButton("⚙️  Settings")
        self.nav_settings.setObjectName("nav_button")
        self.nav_settings.setCheckable(True)
        self.nav_settings.setStyleSheet(self._nav_button_style())
        self.nav_settings.clicked.connect(lambda: self._switch_page(2))
        layout.addWidget(self.nav_settings)

        layout.addStretch()

        # Connection status
        self.status_label = QLabel("🟡 Checking Ollama...")
        self.status_label.setStyleSheet(
            f"font-size: 12px; color: {self.theme['text_light']}; "
            f"padding: 12px; background-color: {self.theme['hover']}; "
            f"border-radius: 8px;"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        QTimer.singleShot(1000, self._check_ollama)

        return sidebar

    def _nav_button_style(self):
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme['nav_inactive_text']};
                border: none;
                padding: 14px 20px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                border-radius: 8px;
                margin: 4px 0px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['nav_hover']};
                color: {self.theme['text_secondary']};
            }}
            QPushButton:checked {{
                background-color: {self.theme['nav_active_bg']};
                color: {self.theme['nav_active_text']};
                font-weight: 600;
            }}
        """

    def _switch_page(self, index):
        self.stack.setCurrentIndex(index)
        buttons = [self.nav_compose, self.nav_analytics, self.nav_settings]
        for i, btn in enumerate(buttons):
            btn.setChecked(i == index)
        if index == 1:
            self._refresh_analytics()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def _create_compose_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        left_panel = self._create_recipients_panel()
        layout.addWidget(left_panel, stretch=1)

        right_panel = self._create_composition_panel()
        layout.addWidget(right_panel, stretch=2)

        return page

    def _create_recipients_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(16)

        header = QLabel("Recipients")
        header.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {self.theme['text']};")
        layout.addWidget(header)

        import_group = QGroupBox("📁 Import from Excel")
        import_layout = QVBoxLayout(import_group)

        import_btn_layout = QHBoxLayout()
        self.import_btn = QPushButton("Choose Excel File")
        self.import_btn.setObjectName("secondary")
        self.import_btn.clicked.connect(self._import_excel)
        import_btn_layout.addWidget(self.import_btn)

        self.clear_import_btn = QPushButton("Clear")
        self.clear_import_btn.setObjectName("danger")
        self.clear_import_btn.clicked.connect(self._clear_recipients)
        self.clear_import_btn.setEnabled(False)
        import_btn_layout.addWidget(self.clear_import_btn)

        import_layout.addLayout(import_btn_layout)

        self.import_status = QLabel("No file imported")
        self.import_status.setStyleSheet(f"color: {self.theme['text_light']}; font-size: 12px;")
        import_layout.addWidget(self.import_status)

        layout.addWidget(import_group)

        manual_group = QGroupBox("➕ Add Manually")
        manual_layout = QVBoxLayout(manual_group)

        manual_input_layout = QHBoxLayout()
        self.manual_email = QLineEdit()
        self.manual_email.setPlaceholderText("email@example.com")
        manual_input_layout.addWidget(self.manual_email)

        self.manual_name = QLineEdit()
        self.manual_name.setPlaceholderText("Name (optional)")
        self.manual_name.setMaximumWidth(150)
        manual_input_layout.addWidget(self.manual_name)

        self.add_manual_btn = QPushButton("Add")
        self.add_manual_btn.setObjectName("success")
        self.add_manual_btn.setMaximumWidth(80)
        self.add_manual_btn.clicked.connect(self._add_manual_recipient)
        manual_input_layout.addWidget(self.add_manual_btn)

        manual_layout.addLayout(manual_input_layout)
        layout.addWidget(manual_group)

        list_group = QGroupBox("📋 Recipient List")
        list_layout = QVBoxLayout(list_group)

        select_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setObjectName("secondary")
        self.select_all_btn.setMaximumWidth(100)
        self.select_all_btn.clicked.connect(self._select_all_recipients)
        select_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.setObjectName("secondary")
        self.select_none_btn.setMaximumWidth(100)
        self.select_none_btn.clicked.connect(self._select_none_recipients)
        select_layout.addWidget(self.select_none_btn)

        self.recipient_count = QLabel("0 recipients")
        self.recipient_count.setStyleSheet(f"color: {self.theme['text_light']}; font-size: 12px;")
        self.recipient_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        select_layout.addWidget(self.recipient_count)

        list_layout.addLayout(select_layout)

        recipients_scroll = QScrollArea()
        recipients_scroll.setWidgetResizable(True)
        recipients_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recipients_scroll.setMaximumHeight(400)
        recipients_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.recipients_container = QWidget()
        self.recipients_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.recipients_list_layout = QVBoxLayout(self.recipients_container)
        self.recipients_list_layout.setContentsMargins(0, 0, 0, 0)
        self.recipients_list_layout.setSpacing(4)
        self.recipients_list_layout.addStretch()

        recipients_scroll.setWidget(self.recipients_container)
        list_layout.addWidget(recipients_scroll)

        layout.addWidget(list_group)
        layout.addStretch()

        return panel

    def _create_composition_panel(self):
        panel = QScrollArea()
        panel.setWidgetResizable(True)
        panel.setFrameShape(QFrame.Shape.NoFrame)
        panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QLabel("Compose Email")
        header.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {self.theme['text']};")
        layout.addWidget(header)

        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)

        model_group = QGroupBox("🤖 AI Model")
        model_layout = QVBoxLayout(model_group)
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(180)
        self.model_combo.currentTextChanged.connect(self._on_model_change)
        model_layout.addWidget(self.model_combo)

        refresh_models = QPushButton("🔄")
        refresh_models.setObjectName("icon_button")
        refresh_models.setMaximumWidth(36)
        refresh_models.clicked.connect(self._load_models)
        model_layout.addWidget(refresh_models)

        settings_layout.addWidget(model_group)

        tone_group = QGroupBox("🎭 Tone")
        tone_layout = QVBoxLayout(tone_group)
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(EMAIL_TONES)
        self.tone_combo.setMinimumWidth(150)
        tone_layout.addWidget(self.tone_combo)
        settings_layout.addWidget(tone_group)

        length_group = QGroupBox("📏 Length")
        length_layout = QVBoxLayout(length_group)
        self.length_combo = QComboBox()
        self.length_combo.addItems(list(EMAIL_LENGTHS.keys()))
        self.length_combo.setMinimumWidth(150)
        length_layout.addWidget(self.length_combo)
        settings_layout.addWidget(length_group)

        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        topic_group = QGroupBox("📝 Email Topic / Instructions")
        topic_layout = QVBoxLayout(topic_group)

        self.topic_input = QPlainTextEdit()
        self.topic_input.setPlaceholderText("Describe what the email should be about...\n\nExample: Write a follow-up email to clients who attended our product demo last week, thanking them and offering a 20% discount.")
        self.topic_input.setMinimumHeight(100)
        topic_layout.addWidget(self.topic_input)

        layout.addWidget(topic_group)

        sig_group = QGroupBox("✍️ Signature / Footer")
        sig_layout = QVBoxLayout(sig_group)

        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)

        presets = [
            ("From XYZ Company", "From XYZ Company"),
            ("Contact Info", "For contact, please call +1 (555) 123-4567"),
            ("Best Regards", "Best Regards,\nThe Team"),
            ("Custom", "")
        ]

        for label, text in presets:
            btn = QPushButton(label)
            btn.setObjectName("secondary")
            btn.setMaximumWidth(120)
            btn.clicked.connect(lambda checked, t=text: self._set_signature(t))
            preset_layout.addWidget(btn)

        preset_layout.addStretch()
        sig_layout.addLayout(preset_layout)

        self.signature_input = QPlainTextEdit()
        self.signature_input.setPlaceholderText("Add your custom signature line here...\nThis will appear at the end of every email.")
        self.signature_input.setMaximumHeight(80)
        sig_layout.addWidget(self.signature_input)

        self.use_sig_check = QCheckBox("Append signature to emails")
        self.use_sig_check.setChecked(True)
        sig_layout.addWidget(self.use_sig_check)

        layout.addWidget(sig_group)

        gen_layout = QHBoxLayout()
        self.generate_btn = QPushButton("✨ Generate Email")
        self.generate_btn.setObjectName("success")
        self.generate_btn.setMinimumHeight(48)
        self.generate_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self.theme['success']};"
            f"  color: white;"
            f"  border: none;"
            f"  padding: 10px 24px;"
            f"  border-radius: 8px;"
            f"  font-weight: 700;"
            f"  font-size: 16px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: #059669;"
            f"}}"
        )
        self.generate_btn.clicked.connect(self._generate_email)
        gen_layout.addWidget(self.generate_btn)
        layout.addLayout(gen_layout)

        gen_header_layout = QHBoxLayout()
        gen_header = QLabel("Generated Emails")
        gen_header.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {self.theme['text_secondary']};")
        gen_header_layout.addWidget(gen_header)

        self.gen_count = QLabel("0 emails")
        self.gen_count.setStyleSheet(f"color: {self.theme['text_light']}; font-size: 13px;")
        gen_header_layout.addWidget(self.gen_count)
        gen_header_layout.addStretch()

        self.send_all_btn = QPushButton("📤 Send All Selected")
        self.send_all_btn.setObjectName("success")
        self.send_all_btn.clicked.connect(self._send_all_emails)
        self.send_all_btn.setEnabled(False)
        gen_header_layout.addWidget(self.send_all_btn)

        layout.addLayout(gen_header_layout)

        gen_scroll = QScrollArea()
        gen_scroll.setWidgetResizable(True)
        gen_scroll.setFrameShape(QFrame.Shape.NoFrame)
        gen_scroll.setMinimumHeight(300)

        self.gen_container = QWidget()
        self.gen_layout = QVBoxLayout(self.gen_container)
        self.gen_layout.setContentsMargins(0, 0, 0, 0)
        self.gen_layout.setSpacing(12)
        self.gen_layout.addStretch()

        gen_scroll.setWidget(self.gen_container)
        layout.addWidget(gen_scroll)

        panel.setWidget(container)
        return panel

    def _create_analytics_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("📊 Analytics Dashboard")
        header.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme['text']};")
        layout.addWidget(header)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.stat_total = StatCard("0", "Total Generated", "#6366f1", self.theme)
        self.stat_sent = StatCard("0", "Emails Sent", "#10b981", self.theme)
        self.stat_draft = StatCard("0", "Drafts", "#f59e0b", self.theme)
        self.stat_response = StatCard("0%", "Response Rate", "#8b5cf6", self.theme)

        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_sent)
        stats_layout.addWidget(self.stat_draft)
        stats_layout.addWidget(self.stat_response)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)

        tone_group = QGroupBox("Tone Distribution")
        tone_layout = QVBoxLayout(tone_group)
        self.tone_figure = Figure(figsize=(5, 4), dpi=100)
        self.tone_figure.patch.set_facecolor(self.theme['chart_bg'])
        self.tone_canvas = FigureCanvas(self.tone_figure)
        tone_layout.addWidget(self.tone_canvas)
        charts_layout.addWidget(tone_group)

        length_group = QGroupBox("Length Distribution")
        length_layout = QVBoxLayout(length_group)
        self.length_figure = Figure(figsize=(5, 4), dpi=100)
        self.length_figure.patch.set_facecolor(self.theme['chart_bg'])
        self.length_canvas = FigureCanvas(self.length_figure)
        length_layout.addWidget(self.length_canvas)
        charts_layout.addWidget(length_group)

        layout.addLayout(charts_layout)

        activity_group = QGroupBox("📈 Daily Activity (Last 30 Days)")
        activity_layout = QVBoxLayout(activity_group)
        self.activity_figure = Figure(figsize=(10, 3), dpi=100)
        self.activity_figure.patch.set_facecolor(self.theme['chart_bg'])
        self.activity_canvas = FigureCanvas(self.activity_figure)
        activity_layout.addWidget(self.activity_canvas)
        layout.addWidget(activity_group)

        refresh_btn = QPushButton("🔄 Refresh Data")
        refresh_btn.setObjectName("secondary")
        refresh_btn.setMaximumWidth(150)
        refresh_btn.clicked.connect(self._refresh_analytics)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()

        page.setWidget(container)
        return page

    def _create_settings_page(self):
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("⚙️ Settings")
        header.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme['text']};")
        layout.addWidget(header)

        smtp_group = QGroupBox("📧 SMTP Configuration")
        smtp_layout = QFormLayout(smtp_group)
        smtp_layout.setSpacing(12)

        self.smtp_server = QLineEdit("smtp.gmail.com")
        smtp_layout.addRow("SMTP Server:", self.smtp_server)

        self.smtp_port = QLineEdit("587")
        smtp_layout.addRow("Port:", self.smtp_port)

        self.smtp_username = QLineEdit()
        self.smtp_username.setPlaceholderText("your.email@gmail.com")
        smtp_layout.addRow("Username:", self.smtp_username)

        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.smtp_password.setPlaceholderText("App Password (not your Gmail password)")
        smtp_layout.addRow("Password:", self.smtp_password)

        test_btn = QPushButton("Test Connection")
        test_btn.setObjectName("secondary")
        test_btn.clicked.connect(self._test_smtp)
        smtp_layout.addRow("", test_btn)

        self.smtp_status = QLabel("Not configured")
        self.smtp_status.setStyleSheet(f"color: {self.theme['text_light']}; font-size: 12px;")
        smtp_layout.addRow("Status:", self.smtp_status)

        layout.addWidget(smtp_group)

        ollama_group = QGroupBox("🤖 Ollama Configuration")
        ollama_layout = QFormLayout(ollama_group)
        ollama_layout.setSpacing(12)

        self.ollama_host = QLineEdit("http://localhost:11434")
        ollama_layout.addRow("Host URL:", self.ollama_host)

        check_btn = QPushButton("Check Connection")
        check_btn.setObjectName("secondary")
        check_btn.clicked.connect(self._check_ollama_manual)
        ollama_layout.addRow("", check_btn)

        layout.addWidget(ollama_group)

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setObjectName("success")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

        page.setWidget(container)
        return page

    # === RECIPIENT MANAGEMENT ===
    def _import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel File", "", 
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if not file_path:
            return
        parser = ExcelParser(file_path)
        if parser.read():
            emails = parser.get_emails()
            stats = parser.get_stats()
            if not emails:
                QMessageBox.warning(self, "No Emails Found", "Could not find any valid email addresses in the file.")
                return
            self.recipients.clear()
            self._clear_recipient_widgets()
            for entry in emails:
                self.recipients.append({"email": entry["email"], "name": entry["name"], "checked": True})
            self._update_recipient_list()
            self.import_status.setText(f"✅ {stats['valid_emails']} emails found in {stats['total_rows']} rows")
            self.clear_import_btn.setEnabled(True)
        else:
            QMessageBox.critical(self, "Error", "Failed to read Excel file.")

    def _clear_recipients(self):
        self.recipients.clear()
        self._clear_recipient_widgets()
        self.import_status.setText("No file imported")
        self.clear_import_btn.setEnabled(False)
        self._update_recipient_count()

    def _clear_recipient_widgets(self):
        while self.recipients_list_layout.count() > 1:
            item = self.recipients_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_manual_recipient(self):
        email = self.manual_email.text().strip()
        name = self.manual_name.text().strip()
        if not email:
            QMessageBox.warning(self, "Missing Email", "Please enter an email address.")
            return
        if "@" not in email or "." not in email.split("@")[1]:
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return
        for r in self.recipients:
            if r["email"].lower() == email.lower():
                QMessageBox.information(self, "Duplicate", "This email is already in the list.")
                return
        self.recipients.append({"email": email, "name": name, "checked": True})
        self.manual_email.clear()
        self.manual_name.clear()
        self._update_recipient_list()

    def _update_recipient_list(self):
        self._clear_recipient_widgets()
        for rec in self.recipients:
            item = RecipientItem(rec["email"], rec["name"], self.theme)
            item.set_checked(rec["checked"])
            item.toggled.connect(self._on_recipient_toggle)
            self.recipients_list_layout.insertWidget(self.recipients_list_layout.count() - 1, item)

        # Without this, Qt sometimes keeps the OLD scrollable height after
        # adding widgets at runtime — only the first item shows and the list
        # won't scroll to reveal the rest.
        self.recipients_container.updateGeometry()

        self._update_recipient_count()

    def _on_recipient_toggle(self, email, checked):
        for r in self.recipients:
            if r["email"] == email:
                r["checked"] = checked
                break
        self._update_recipient_count()

    def _select_all_recipients(self):
        for r in self.recipients:
            r["checked"] = True
        self._update_recipient_list()

    def _select_none_recipients(self):
        for r in self.recipients:
            r["checked"] = False
        self._update_recipient_list()

    def _update_recipient_count(self):
        checked = sum(1 for r in self.recipients if r["checked"])
        total = len(self.recipients)
        self.recipient_count.setText(f"{checked}/{total} selected")

    def _get_selected_recipients(self):
        return [r for r in self.recipients if r["checked"]]
    
    def add_recipients_from_leads(self, leads):
        """
        Called externally by the Email Scraper agent to inject recipients
        directly, skipping the Excel export/import round-trip.
        `leads` is a list of {"email": ..., "name": ...} dicts.
        """
        existing_emails = {r["email"].lower() for r in self.recipients}
        added = 0
        for entry in leads:
            email = entry.get("email", "").strip()
            name = entry.get("name", "").strip()
            if not email or email.lower() in existing_emails:
                continue
            self.recipients.append({"email": email, "name": name, "checked": True})
            existing_emails.add(email.lower())
            added += 1

        self._update_recipient_list()
        self.import_status.setText(f"✅ {added} leads received from Email Scraper")
        self.clear_import_btn.setEnabled(bool(self.recipients))

    # === EMAIL GENERATION ===
    def _load_models(self):
        self.model_combo.clear()
        models = self.ollama_client.get_models()
        if models:
            self.model_combo.addItems(models)
            for i, m in enumerate(models):
                if "qwen2.5" in m.lower():
                    self.model_combo.setCurrentIndex(i)
                    break
        else:
            self.model_combo.addItem("qwen2.5:7b (fallback)")
            self.model_combo.addItem("llama3.1:8b")
            self.model_combo.addItem("mistral:7b")

    def _on_model_change(self, model_name):
        self.current_model = model_name
        self.email_engine.set_model(model_name)

    def _set_signature(self, text):
        self.signature_input.setPlainText(text)

    def _generate_email(self):
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "Missing Topic", "Please enter what the email should be about.")
            return
        tone = self.tone_combo.currentText()
        length = self.length_combo.currentText()
        signature = ""
        if self.use_sig_check.isChecked():
            signature = self.signature_input.toPlainText().strip()
        selected = self._get_selected_recipients()
        recipient_name = selected[0]["name"] if selected else ""

        self.overlay.show_message("AI is writing your email...")
        self.gen_thread = EmailGenThread(self.email_engine, topic, tone, length, recipient_name, signature)
        self.gen_thread.finished.connect(self._on_generation_done)
        self.gen_thread.error.connect(self._on_generation_error)
        self.gen_thread.start()

    def _on_generation_done(self, result):
        self.overlay.hide_overlay()
        self.generated_emails.append(result)
        self._add_email_card(result, len(self.generated_emails) - 1)
        self._update_gen_count()
        self.analytics.log_generation(result["tone"], result["length"], self.current_model, result["topic"])
        QMessageBox.information(self, "Success", f"Email generated!\n\nSubject: {result['subject']}")

    def _on_generation_error(self, error_msg):
        self.overlay.hide_overlay()
        QMessageBox.critical(self, "Generation Failed", error_msg)

    def _add_email_card(self, email_data, index):
        card = LongPressCard(email_data, index, self.theme)
        card.clicked.connect(self._on_email_select)
        card.deleteRequested.connect(self._on_email_delete)
        card.editRequested.connect(self._on_email_edit)
        card.regenerateRequested.connect(self._on_email_regenerate)
        card.sendRequested.connect(self._on_email_send)
        self.gen_layout.insertWidget(self.gen_layout.count() - 1, card)
        self.send_all_btn.setEnabled(True)

    def _update_gen_count(self):
        self.gen_count.setText(f"{len(self.generated_emails)} emails")
        self.send_all_btn.setEnabled(len(self.generated_emails) > 0 and len(self._get_selected_recipients()) > 0)

    def _on_email_select(self, index):
        if 0 <= index < len(self.generated_emails):
            data = self.generated_emails[index]
            dialog = EmailPreviewDialog(data, self.theme, self)
            dialog.exec()

    def _on_email_delete(self, index):
        if 0 <= index < len(self.generated_emails):
            reply = QMessageBox.question(self, "Confirm Delete", "Delete this generated email?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.generated_emails.pop(index)
                self._refresh_gen_cards()
                self._update_gen_count()

    def _on_email_edit(self, index):
        if 0 <= index < len(self.generated_emails):
            data = self.generated_emails[index]
            dialog = EmailEditDialog(data, self.theme, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                edited = dialog.get_edited_data()
                self.generated_emails[index]["subject"] = edited["subject"]
                self.generated_emails[index]["body"] = edited["body"]
                sig = data.get("full_text", "").replace(data.get("body", ""), "").strip()
                if sig:
                    self.generated_emails[index]["full_text"] = edited["body"] + "\n\n" + sig
                else:
                    self.generated_emails[index]["full_text"] = edited["body"]
                self._refresh_gen_cards()
                QMessageBox.information(self, "Saved", "Email updated successfully!")

    def _on_email_regenerate(self, index):
        if 0 <= index < len(self.generated_emails):
            original = self.generated_emails[index]
            topic = original.get("topic", "")
            tone = original.get("tone", self.tone_combo.currentText())
            length = original.get("length", self.length_combo.currentText())
            recipient = original.get("recipient", "")
            signature = ""
            if self.use_sig_check.isChecked():
                signature = self.signature_input.toPlainText().strip()
            self.overlay.show_message("Regenerating with fresh wording...")
            self.regen_thread = EmailRegenThread(self.email_engine, original, topic, tone, length, recipient, signature)
            self.regen_thread.finished.connect(lambda result, idx=index: self._on_regen_done(result, idx))
            self.regen_thread.error.connect(self._on_generation_error)
            self.regen_thread.start()

    def _on_regen_done(self, result, index):
        self.overlay.hide_overlay()
        self.generated_emails[index] = result
        self._refresh_gen_cards()
        QMessageBox.information(self, "Regenerated", f"Email regenerated!\n\nNew Subject: {result['subject']}")

    def _on_email_send(self, index):
        if 0 <= index < len(self.generated_emails):
            self._send_emails([self.generated_emails[index]])

    def _send_all_emails(self):
        if not self.generated_emails:
            QMessageBox.warning(self, "No Emails", "No emails to send.")
            return
        selected = self._get_selected_recipients()
        if not selected:
            QMessageBox.warning(self, "No Recipients", "Please select at least one recipient.")
            return
        self._send_emails(self.generated_emails)

    def _send_emails(self, emails):
        if not self.smtp_username.text() or not self.smtp_password.text():
            QMessageBox.warning(self, "SMTP Not Configured", "Please configure SMTP settings in the Settings tab first.")
            self._switch_page(2)
            return
        recipients = self._get_selected_recipients()
        if not recipients:
            QMessageBox.warning(self, "No Recipients", "No recipients selected.")
            return
        total = len(emails) * len(recipients)
        reply = QMessageBox.question(self, "Confirm Send",
            f"Send {len(emails)} email(s) to {len(recipients)} recipient(s)?\n\nTotal: {total} emails",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.overlay.show_message(f"Sending {total} emails...")
        self.send_thread = EmailSendThread(self.email_sender, recipients, emails)
        self.send_thread.progress.connect(self._on_send_progress)
        self.send_thread.finished.connect(self._on_send_done)
        self.send_thread.error.connect(self._on_send_error)
        self.send_thread.start()

    def _on_send_progress(self, current, total):
        self.overlay.show_message(f"Sending... {current}/{total}")

    def _on_send_done(self, sent, failed):
        self.overlay.hide_overlay()
        msg = f"✅ Sent: {sent}\n"
        if failed:
            msg += f"❌ Failed: {len(failed)}\n"
            msg += "\n".join([f"- {f['email']}: {f['error']}" for f in failed[:5]])
            if len(failed) > 5:
                msg += f"\n... and {len(failed) - 5} more"
        QMessageBox.information(self, "Send Complete", msg)
        for email in self.generated_emails:
            self.analytics.log_generation(email["tone"], email["length"], self.current_model,
                email["topic"], len(self._get_selected_recipients()), sent=True, subject=email["subject"])

    def _on_send_error(self, error_msg):
        self.overlay.hide_overlay()
        QMessageBox.critical(self, "Send Failed", error_msg)

    def _refresh_gen_cards(self):
        while self.gen_layout.count() > 1:
            item = self.gen_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, email in enumerate(self.generated_emails):
            self._add_email_card(email, i)

    # === ANALYTICS ===
    def _refresh_analytics(self):
        stats = self.analytics.get_stats()
        self.stat_total.set_value(stats["total_generated"])
        self.stat_sent.set_value(stats["sent_count"])
        self.stat_draft.set_value(stats["draft_count"])
        self.stat_response.set_value(f"{stats['response_rate']}%")
        for card in [self.stat_total, self.stat_sent, self.stat_draft, self.stat_response]:
            card.update_theme(self.theme)
        self._draw_pie_chart(self.tone_figure, self.tone_canvas, stats["tone_stats"], "Tones Used")
        self._draw_pie_chart(self.length_figure, self.length_canvas, stats["length_stats"], "Length Distribution")
        daily = self.analytics.get_daily_activity()
        self._draw_line_chart(daily)

    def _draw_pie_chart(self, figure, canvas, data, title):
        figure.clear()
        ax = figure.add_subplot(111)
        colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981']
        text_color = 'white' if self.is_dark else '#1e293b'
        if data:
            labels = list(data.keys())
            values = list(data.values())
            ax.pie(values, labels=labels, autopct='%1.1f%%',
                   colors=colors[:len(labels)], startangle=90,
                   textprops={'fontsize': 10, 'color': text_color})
            ax.set_title(title, fontsize=12, fontweight='bold', pad=20, color=text_color)
        else:
            ax.text(0.5, 0.5, "No data yet", ha='center', va='center', fontsize=12, color=text_color)
            ax.set_title(title, fontsize=12, fontweight='bold', pad=20, color=text_color)
        ax.axis('equal')
        figure.tight_layout()
        canvas.draw()

    def _draw_line_chart(self, data):
        self.activity_figure.clear()
        ax = self.activity_figure.add_subplot(111)
        text_color = 'white' if self.is_dark else '#1e293b'
        grid_color = '#334155' if self.is_dark else '#e2e8f0'
        if data:
            dates = [d[0] for d in data]
            counts = [d[1] for d in data]
            ax.plot(dates, counts, marker='o', linewidth=2, markersize=6, color='#6366f1')
            ax.fill_between(dates, counts, alpha=0.2, color='#6366f1')
            ax.set_xlabel('Date', fontsize=10, color=text_color)
            ax.set_ylabel('Emails Generated', fontsize=10, color=text_color)
            ax.set_title('Daily Activity', fontsize=12, fontweight='bold', pad=20, color=text_color)
            ax.tick_params(axis='x', rotation=45, labelsize=8, colors=text_color)
            ax.tick_params(axis='y', labelsize=8, colors=text_color)
            ax.grid(True, alpha=0.3, color=grid_color)
            for spine in ax.spines.values():
                spine.set_color(grid_color)
        else:
            ax.text(0.5, 0.5, "No activity data yet", ha='center', va='center', fontsize=12, color=text_color)
        self.activity_figure.tight_layout()
        self.activity_canvas.draw()

    # === SETTINGS ===
    def _test_smtp(self):
        self.email_sender = EmailSender(self.smtp_server.text(), int(self.smtp_port.text() or 587),
            self.smtp_username.text(), self.smtp_password.text())
        success, msg = self.email_sender.test_connection()
        if success:
            self.smtp_status.setText("✅ Connected")
            self.smtp_status.setStyleSheet(f"color: {self.theme['success']}; font-weight: 600;")
            QMessageBox.information(self, "Success", "SMTP connection successful!")
        else:
            self.smtp_status.setText(f"❌ {msg[:50]}")
            self.smtp_status.setStyleSheet(f"color: {self.theme['danger']};")
            QMessageBox.critical(self, "Failed", f"Connection failed:\n{msg}")

    def _check_ollama_manual(self):
        self._check_ollama()

    def _check_ollama(self):
        if self.ollama_client.check_connection():
            self.status_label.setText("🟢 Ollama Connected")
            self.status_label.setStyleSheet(
                f"font-size: 12px; color: {self.theme['success']}; "
                f"padding: 12px; background-color: {self.theme['hover'] if not self.is_dark else '#064e3b'}; "
                f"border-radius: 8px; font-weight: 600;"
            )
        else:
            self.status_label.setText("🔴 Ollama Offline")
            self.status_label.setStyleSheet(
                f"font-size: 12px; color: {self.theme['danger']}; "
                f"padding: 12px; background-color: {self.theme['hover'] if not self.is_dark else '#450a0a'}; "
                f"border-radius: 8px; font-weight: 600;"
            )

    def _save_settings(self):
        self.email_sender = EmailSender(self.smtp_server.text(), int(self.smtp_port.text() or 587),
            self.smtp_username.text(), self.smtp_password.text())
        QMessageBox.information(self, "Saved", "Settings saved successfully!")

    def update_theme(self, theme):
        self.theme = theme

        # --- Fix heading colors on theme change (added by fix_light_headings) ---
        from PyQt6.QtWidgets import QLabel as _QLabel
        for _lbl in self.findChildren(_QLabel):
            _ss = _lbl.styleSheet()
            if "font-weight: 700" in _ss or "font-weight: 800" in _ss:
                import re as _re
                _new = _re.sub(r"color:\s*#[0-9a-fA-F]{3,8}", f"color: {theme['text']}", _ss)
                if "background" not in _new:
                    _new += " background: transparent;"
                _lbl.setStyleSheet(_new)

        # Overlay
        self.overlay.update_theme(theme)

        # Stack background
        self.stack.setStyleSheet(f"background-color: {theme['bg']};")

        # Sidebar (find by objectName)
        sidebar = self.findChild(QWidget, "sidebar")
        if sidebar:
            sidebar.setStyleSheet(
                f"background-color: {theme['sidebar']}; "
                f"border-right: 1px solid {theme['border']};"
            )

        # Nav buttons
        nav_style = self._nav_button_style()
        self.nav_compose.setStyleSheet(nav_style)
        self.nav_analytics.setStyleSheet(nav_style)
        self.nav_settings.setStyleSheet(nav_style)

        # Inline labels
        self.import_status.setStyleSheet(f"color: {theme['text_light']}; font-size: 12px;")
        self.recipient_count.setStyleSheet(f"color: {theme['text_light']}; font-size: 12px;")
        self.gen_count.setStyleSheet(f"color: {theme['text_light']}; font-size: 13px;")
        self.smtp_status.setStyleSheet(f"color: {theme['text_light']}; font-size: 12px;")

        # Stat cards
        self.stat_total.update_theme(theme)
        self.stat_sent.update_theme(theme)
        self.stat_draft.update_theme(theme)
        self.stat_response.update_theme(theme)

        # Chart backgrounds
        self.tone_figure.patch.set_facecolor(theme['chart_bg'])
        self.length_figure.patch.set_facecolor(theme['chart_bg'])
        self.activity_figure.patch.set_facecolor(theme['chart_bg'])
        self.tone_canvas.draw()
        self.length_canvas.draw()
        self.activity_canvas.draw()

        # Refresh cards and analytics
        self._refresh_gen_cards()
        if self.stack.currentIndex() == 1:
            self._refresh_analytics()


# === DIALOGS ===

class EmailEditDialog(QDialog):
    def __init__(self, email_data, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("✏️ Edit Email")
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout(self)
        subject_label = QLabel(f"<b>Subject:</b>")
        subject_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {theme['text_secondary']};")
        layout.addWidget(subject_label)
        self.subject_edit = QLineEdit(email_data.get("subject", ""))
        self.subject_edit.setStyleSheet(f"font-size: 14px; color: {theme['text']};")
        layout.addWidget(self.subject_edit)
        body_label = QLabel("Email Body")
        body_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {theme['text_secondary']};")
        layout.addWidget(body_label)
        self.body_edit = QPlainTextEdit(email_data.get("body", ""))
        self.body_edit.setStyleSheet(f"font-size: 14px; line-height: 1.6; color: {theme['text']};")
        self.body_edit.setMinimumHeight(250)
        layout.addWidget(self.body_edit)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("💾 Save Changes")
        save_btn.setObjectName("success")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_edited_data(self):
        return {"subject": self.subject_edit.text().strip(), "body": self.body_edit.toPlainText().strip()}


class EmailPreviewDialog(QDialog):
    def __init__(self, email_data, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Email Preview")
        self.setMinimumSize(600, 500)
        layout = QVBoxLayout(self)
        subject_label = QLabel(f"<b>Subject:</b> {email_data.get('subject', 'N/A')}")
        subject_label.setStyleSheet(f"font-size: 16px; color: {theme['text']}; padding-bottom: 12px;")
        layout.addWidget(subject_label)
        body = email_data.get('full_text', email_data.get('body', ''))
        body_edit = QPlainTextEdit(body)
        body_edit.setReadOnly(True)
        body_edit.setStyleSheet(f"font-size: 14px; line-height: 1.6; color: {theme['text']};")
        layout.addWidget(body_edit)
        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        self.setLayout(layout)


# === WORKER THREADS ===

class EmailGenThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, engine, topic, tone, length, recipient_name, signature):
        super().__init__()
        self.engine = engine; self.topic = topic; self.tone = tone; self.length = length
        self.recipient_name = recipient_name; self.signature = signature
    def run(self):
        try:
            result = self.engine.generate_email(self.topic, self.tone, self.length, self.recipient_name, signature=self.signature)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class EmailRegenThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    def __init__(self, engine, original, topic, tone, length, recipient, signature):
        super().__init__()
        self.engine = engine; self.original = original; self.topic = topic; self.tone = tone
        self.length = length; self.recipient = recipient; self.signature = signature
    def run(self):
        try:
            result = self.engine.regenerate_email(self.original, self.topic, self.tone, self.length, self.recipient, signature=self.signature)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class EmailSendThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int, list)
    error = pyqtSignal(str)
    def __init__(self, sender, recipients, emails):
        super().__init__()
        self.sender = sender; self.recipients = recipients; self.emails = emails
    def run(self):
        try:
            total_sent = 0; all_failed = []; total = len(self.emails) * len(self.recipients); current = 0
            for email in self.emails:
                sent, failed = self.sender.send_bulk(self.recipients, email["subject"], email["body"],
                    email.get("full_text", "").replace(email["body"], ""))
                total_sent += sent; all_failed.extend(failed); current += len(self.recipients)
                self.progress.emit(current, total)
            self.finished.emit(total_sent, all_failed)
        except Exception as e:
            self.error.emit(str(e))
