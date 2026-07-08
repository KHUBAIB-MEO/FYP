"""
emailscraper/emailscraper_page.py
------------------------------------
Phase 2: PyQt6 page for the Email Scraper agent.

Follows the exact same pattern as producthunter_page.py in this project:
  - A QObject "worker" that does the slow work (scraping)
  - Moved onto a QThread so the scraping never freezes the UI
  - Signals report progress back to the main window

This page currently shows results in a read-only table (Phase 2 scope).
Phase 3 will turn the "Include" column into checkboxes you can toggle,
plus a row to add an email manually.
"""
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGridLayout, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QObject

from emailscraper.core.lead_finder import find_leads
from emailscraper.core.excel_exporter import export_leads_to_excel
from emailscraper.models import Lead


# ======================================================================== #
# Background worker (runs on a separate QThread so the UI never freezes)   #
# ======================================================================== #

class ScrapeWorker(QObject):
    """Runs find_leads() in a background thread."""

    maps_progress = pyqtSignal(int, int)   # current, total listings scraped on Maps
    email_progress = pyqtSignal(int, int)  # current, total websites checked for emails
    result = pyqtSignal(list)              # list[Lead] when done
    error = pyqtSignal(str)
    finished = pyqtSignal()
    stopped_early = pyqtSignal()           # emitted only if the user clicked Stop

    def __init__(self, keyword, city, max_results, headless,
                 min_delay, max_delay, cooldown_every, cooldown_seconds, api_key=""):
        super().__init__()
        self.keyword = keyword
        self.city = city
        self.max_results = max_results
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.cooldown_every = cooldown_every
        self.cooldown_seconds = cooldown_seconds
        self.api_key = api_key
        self.stop_event = threading.Event()

    def request_stop(self):
        """Called from the GUI thread when the user clicks Stop. Setting
        this Event is thread-safe — find_leads() checks it periodically
        from the worker thread and winds down cleanly."""
        self.stop_event.set()

    @pyqtSlot()
    def run(self):
        try:
            leads = find_leads(
                self.keyword,
                self.city,
                max_results=self.max_results,
                headless=self.headless,
                min_delay=self.min_delay,
                max_delay=self.max_delay,
                cooldown_every=self.cooldown_every,
                cooldown_seconds=self.cooldown_seconds,
                api_key=self.api_key,
                on_maps_progress=self.maps_progress.emit,
                on_email_progress=self.email_progress.emit,
                stop_event=self.stop_event,
            )
            if self.stop_event.is_set():
                self.stopped_early.emit()
            self.result.emit(leads)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


# ======================================================================== #
# Main page                                                                #
# ======================================================================== #

class EmailScraperPage(QWidget):
    """
    Registered in MainWindow exactly like EmailPage / ProductHunterPage.
    Emits backToDashboard when the user clicks the back button.
    """

    backToDashboard = pyqtSignal()
    sendToEmailAgent = pyqtSignal(list)  # emits [{"email": ..., "name": ...}, ...]

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._threads = []      # keep references alive so Qt doesn't GC them mid-run
        self.current_leads = [] # last scrape results — Phase 3/4 will use this
        self._active_worker = None  # the currently-running ScrapeWorker, if any
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(self._create_sidebar())

        # Everything lives inside a scroll area, same pattern as email_page.py.
        # This means if the window is short, the PAGE scrolls — nothing gets
        # squeezed or clipped, and the results table always gets a proper,
        # readable height.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(self._build_page_title())
        layout.addWidget(self._build_separator())
        layout.addLayout(self._build_input_form())
        layout.addLayout(self._build_api_key_row())
        layout.addLayout(self._build_advanced_settings())
        layout.addLayout(self._build_action_row())
        layout.addWidget(self._progress_bar())
        layout.addWidget(self._status_label())
        layout.addWidget(self._log_box())
        layout.addLayout(self._build_manual_add_row())
        layout.addLayout(self._build_table_toolbar())
        layout.addWidget(self._results_table())

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(
            f"QFrame#sidebar {{ background-color: {{self.theme['sidebar']}}; "
            f"border-right: 1px solid {{self.theme['border']}}; }}".replace("{{", "{").replace("}}", "}")
        )

        col = QVBoxLayout(sidebar)
        col.setContentsMargins(16, 24, 16, 24)
        col.setSpacing(8)

        back_btn = QPushButton("←  Back to Dashboard")
        back_btn.setStyleSheet(self._button_style(secondary=True))
        back_btn.clicked.connect(self.backToDashboard.emit)
        col.addWidget(back_btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {self.theme['border']}; max-height: 1px; margin: 8px 0;")
        col.addWidget(line)

        title = QLabel("📧  Email Scraper")
        title.setStyleSheet(f"font-size: 19px; font-weight: 700; color: {self.theme['text']}; padding: 8px 0 4px 0; background: transparent;")
        title.setWordWrap(True)
        col.addWidget(title)

        blurb = QLabel("Find business emails by keyword and city. Searches Google Maps, crawls each website, and builds a ready-to-use lead list.")
        blurb.setWordWrap(True)
        blurb.setStyleSheet(f"font-size: 12px; color: {self.theme['text_light']}; padding: 0 0 8px 0; background: transparent;")
        col.addWidget(blurb)

        col.addStretch()

        pill = QLabel("🌐  Free • Google Maps")
        pill.setStyleSheet(
            f"font-size: 12px; color: {self.theme['text_light']}; padding: 12px; "
            f"background-color: {self.theme['hover']}; border-radius: 8px;"
        )
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(pill)

        return sidebar

    def _build_page_title(self):
        title = QLabel("📧  Email Scraper")
        title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme['text']}; background: transparent;")
        return title

    def _build_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {self.theme['border']}; max-height: 1px;")
        return line

    def _build_input_form(self):
        grid = QGridLayout()
        grid.setSpacing(10)

        label_style = f"font-size: 13px; font-weight: 600; color: {self.theme['text_secondary']};"

        kw_label = QLabel("Keyword")
        kw_label.setStyleSheet(label_style)
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("e.g. software house")
        self.keyword_input.setStyleSheet(self._input_style())

        city_label = QLabel("City")
        city_label.setStyleSheet(label_style)
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("e.g. Karachi")
        self.city_input.setText("Karachi")
        self.city_input.setStyleSheet(self._input_style())

        results_label = QLabel("Max Results")
        results_label.setStyleSheet(label_style)
        self.max_results_input = QSpinBox()
        self.max_results_input.setRange(5, 50)
        self.max_results_input.setValue(15)
        self.max_results_input.setStyleSheet(self._input_style())

        grid.addWidget(kw_label, 0, 0)
        grid.addWidget(self.keyword_input, 1, 0)
        grid.addWidget(city_label, 0, 1)
        grid.addWidget(self.city_input, 1, 1)
        grid.addWidget(results_label, 0, 2)
        grid.addWidget(self.max_results_input, 1, 2)

        return grid

    def _build_api_key_row(self):
        """
        Optional: paste a Google Places API key to use the paid, official
        API instead of free Playwright scraping. Leave blank to keep using
        the free method — nothing else changes.
        """
        wrapper = QVBoxLayout()
        wrapper.setSpacing(4)

        label = QLabel("Google Places API Key  (optional — leave blank for free scraping)")
        label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme['text_secondary']};")
        wrapper.addWidget(label)

        row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Paste a Google Places API key here to use the paid API (faster, no delay tuning needed)")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setStyleSheet(self._input_style())
        row.addWidget(self.api_key_input)

        show_btn = QPushButton("👁")
        show_btn.setFixedWidth(36)
        show_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        show_btn.setStyleSheet(self._button_style(secondary=True))
        show_btn.clicked.connect(self._toggle_api_key_visibility)
        row.addWidget(show_btn)

        wrapper.addLayout(row)

        hint = QLabel(
            "Requires a Google Cloud project with billing enabled (Google gives free monthly "
            "credit, but a card must be on file). When set, the anti-ban delay settings below are ignored."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"font-size: 11px; color: {self.theme['text_light']};")
        wrapper.addWidget(hint)

        return wrapper

    def _toggle_api_key_visibility(self):
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _build_advanced_settings(self):
        """
        Anti-ban controls — manual delay tuning, as requested. Collapsed
        visually into one row so it doesn't dominate the page.
        """
        box = QFrame()
        box.setStyleSheet(
            f"QFrame {{ background-color: {self.theme['hover']}; "
            f"border: 1px solid {self.theme['border']}; border-radius: 8px; }}"
        )
        outer = QVBoxLayout(box)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        heading = QLabel("⚙️  Anti-ban settings")
        heading.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme['text_light']};")
        outer.addWidget(heading)

        row = QHBoxLayout()
        row.setSpacing(16)

        self.headless_checkbox = QCheckBox("Run headless (hide browser)")
        self.headless_checkbox.setChecked(True)  # hidden by default — uncheck only if you want to watch/debug
        self.headless_checkbox.setStyleSheet(f"color: {self.theme['text']}; font-size: 13px;")
        row.addWidget(self.headless_checkbox)

        row.addWidget(self._small_label("Min delay (s)"))
        self.min_delay_input = QDoubleSpinBox()
        self.min_delay_input.setRange(0.5, 15.0)
        self.min_delay_input.setSingleStep(0.5)
        self.min_delay_input.setValue(1.5)
        self.min_delay_input.setStyleSheet(self._input_style())
        row.addWidget(self.min_delay_input)

        row.addWidget(self._small_label("Max delay (s)"))
        self.max_delay_input = QDoubleSpinBox()
        self.max_delay_input.setRange(1.0, 30.0)
        self.max_delay_input.setSingleStep(0.5)
        self.max_delay_input.setValue(3.0)
        self.max_delay_input.setStyleSheet(self._input_style())
        row.addWidget(self.max_delay_input)

        row.addWidget(self._small_label("Cooldown every"))
        self.cooldown_every_input = QSpinBox()
        self.cooldown_every_input.setRange(2, 20)
        self.cooldown_every_input.setValue(5)
        self.cooldown_every_input.setStyleSheet(self._input_style())
        row.addWidget(self.cooldown_every_input)

        row.addWidget(self._small_label("Cooldown (s)"))
        self.cooldown_seconds_input = QDoubleSpinBox()
        self.cooldown_seconds_input.setRange(2.0, 60.0)
        self.cooldown_seconds_input.setSingleStep(1.0)
        self.cooldown_seconds_input.setValue(10.0)
        self.cooldown_seconds_input.setStyleSheet(self._input_style())
        row.addWidget(self.cooldown_seconds_input)

        row.addStretch()
        outer.addLayout(row)

        wrapper = QHBoxLayout()
        wrapper.addWidget(box)
        return wrapper

    def _small_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size: 12px; color: {self.theme['text_light']};")
        return lbl

    def _build_action_row(self):
        row = QHBoxLayout()
        self.scrape_btn = QPushButton("🔍  Start Scraping")
        self.scrape_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scrape_btn.setStyleSheet(self._button_style(secondary=False))
        self.scrape_btn.clicked.connect(self._start_scraping)
        row.addWidget(self.scrape_btn)

        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(self._button_style(secondary=True))
        self.stop_btn.clicked.connect(self._stop_scraping)
        self.stop_btn.setVisible(False)  # only shown while a scrape is running
        row.addWidget(self.stop_btn)

        row.addStretch()
        return row

    def _build_manual_add_row(self):
        """
        Lets the user add a business + email that the scraper didn't find —
        e.g. they know the contact from somewhere else, or want to fix a
        listing that had no website.
        """
        box = QFrame()
        box.setStyleSheet(
            f"QFrame {{ background-color: {self.theme['hover']}; "
            f"border: 1px solid {self.theme['border']}; border-radius: 8px; }}"
        )
        outer = QVBoxLayout(box)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        heading = QLabel("➕  Add an email manually")
        heading.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {self.theme['text_light']};")
        outer.addWidget(heading)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.manual_name_input = QLineEdit()
        self.manual_name_input.setPlaceholderText("Business name")
        self.manual_name_input.setStyleSheet(self._input_style())
        row.addWidget(self.manual_name_input, 2)

        self.manual_email_input = QLineEdit()
        self.manual_email_input.setPlaceholderText("Email address")
        self.manual_email_input.setStyleSheet(self._input_style())
        row.addWidget(self.manual_email_input, 2)

        self.manual_website_input = QLineEdit()
        self.manual_website_input.setPlaceholderText("Website (optional)")
        self.manual_website_input.setStyleSheet(self._input_style())
        row.addWidget(self.manual_website_input, 2)

        add_btn = QPushButton("+ Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(self._button_style(secondary=False))
        add_btn.clicked.connect(self._add_manual_lead)
        row.addWidget(add_btn)

        outer.addLayout(row)

        wrapper = QHBoxLayout()
        wrapper.addWidget(box)
        return wrapper

    def _build_table_toolbar(self):
        """Selection summary + select-all/none, sits right above the table."""
        row = QHBoxLayout()

        self.selection_label = QLabel("No leads yet.")
        self.selection_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme['text_secondary']};")
        row.addWidget(self.selection_label)
        row.addStretch()

        select_all_btn = QPushButton("☑ Select All")
        select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_all_btn.setStyleSheet(self._button_style(secondary=True))
        select_all_btn.clicked.connect(lambda: self._set_all_included(True))
        row.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("☐ Deselect All")
        deselect_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deselect_all_btn.setStyleSheet(self._button_style(secondary=True))
        deselect_all_btn.clicked.connect(lambda: self._set_all_included(False))
        row.addWidget(deselect_all_btn)

        export_btn = QPushButton("📤 Export to Excel")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(self._button_style(secondary=False))
        export_btn.clicked.connect(self._export_to_excel)
        row.addWidget(export_btn)

        send_btn = QPushButton("📨 Send to Email Agent")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(self._button_style(secondary=False))
        send_btn.clicked.connect(self._send_to_email_agent)
        row.addWidget(send_btn)

        return row

    def _progress_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(18)
        return self.progress_bar

    def _status_label(self):
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {self.theme['text_light']};")
        return self.status_label

    def _log_box(self):
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(110)
        self.log_box.setStyleSheet(
            f"background-color: {self.theme['code_bg']}; color: {self.theme['text_secondary']}; "
            f"border: 1px solid {self.theme['border']}; border-radius: 6px; font-family: Consolas, monospace; font-size: 12px;"
        )
        return self.log_box

    def _results_table(self):
        self.results_table = QTableWidget(0, 6)
        self.results_table.setMinimumHeight(420)
        self.results_table.setHorizontalHeaderLabels(
            ["Include", "Business Name", "Emails", "Website", "Phone", "Address"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        # Only the Emails column is directly editable (double-click a cell).
        # Business Name / Website / Phone / Address stay read-only so the
        # scraped data can't be accidentally corrupted.
        self.results_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet(
            f"QTableWidget {{ background-color: {self.theme['card']}; color: {self.theme['text']}; "
            f"gridline-color: {self.theme['border']}; border: 1px solid {self.theme['border']}; }}"
            f"QHeaderView::section {{ background-color: {self.theme['hover']}; color: {self.theme['text_secondary']}; "
            f"padding: 6px; border: none; font-weight: 600; }}"
        )
        self.results_table.itemChanged.connect(self._on_item_changed)
        return self.results_table

    # ------------------------------------------------------------------ #
    # Style helpers
    # ------------------------------------------------------------------ #
    def _input_style(self):
        return (
            f"QWidget {{ background-color: {self.theme['input_bg']}; color: {self.theme['text']}; "
            f"border: 1px solid {self.theme['input_border']}; border-radius: 6px; padding: 6px 8px; }}"
        )

    def _button_style(self, secondary=False):
        if secondary:
            return (
                f"QPushButton {{ background-color: {self.theme['hover']}; color: {self.theme['text_secondary']}; "
                f"border: 1px solid {self.theme['border']}; padding: 10px 16px; border-radius: 8px; "
                f"font-weight: 600; font-size: 13px; }}"
                f"QPushButton:hover {{ background-color: {self.theme['border']}; color: {self.theme['text']}; }}"
            )
        return (
            f"QPushButton {{ background-color: {self.theme['primary']}; color: white; "
            f"padding: 10px 20px; border-radius: 8px; font-weight: 700; font-size: 13px; border: none; }}"
            f"QPushButton:hover {{ background-color: {self.theme['primary_dark']}; }}"
            f"QPushButton:disabled {{ background-color: {self.theme['border']}; color: {self.theme['text_light']}; }}"
        )

    # ------------------------------------------------------------------ #
    # Scraping logic
    # ------------------------------------------------------------------ #
    def _start_scraping(self):
        keyword = self.keyword_input.text().strip()
        city = self.city_input.text().strip()

        if not keyword or not city:
            QMessageBox.warning(self, "Input Required", "Please enter both a keyword and a city.")
            return

        if not self.api_key_input.text().strip() and self.min_delay_input.value() >= self.max_delay_input.value():
            QMessageBox.warning(self, "Invalid Delay Range", "Min delay must be less than max delay.")
            return

        self.scrape_btn.setEnabled(False)
        self.scrape_btn.setText("Scraping...")
        self.stop_btn.setVisible(True)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.results_table.setRowCount(0)
        self._log(f"Starting search: '{keyword}' in '{city}'...")

        thread = QThread()
        worker = ScrapeWorker(
            keyword=keyword,
            city=city,
            max_results=self.max_results_input.value(),
            headless=self.headless_checkbox.isChecked(),
            min_delay=self.min_delay_input.value(),
            max_delay=self.max_delay_input.value(),
            cooldown_every=self.cooldown_every_input.value(),
            cooldown_seconds=self.cooldown_seconds_input.value(),
            api_key=self.api_key_input.text().strip(),
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.maps_progress.connect(self._on_maps_progress)
        worker.email_progress.connect(self._on_email_progress)
        worker.result.connect(self._on_result)
        worker.error.connect(self._on_error)
        worker.stopped_early.connect(lambda: self._log("⏹ Stop requested — finishing up the current item..."))
        worker.finished.connect(thread.quit)
        worker.finished.connect(lambda: self.stop_btn.setVisible(False))
        thread.start()

        # Keep references so Python/Qt don't garbage-collect the thread mid-run
        self._threads.append((thread, worker))
        self._active_worker = worker  # so the Stop button can reach it

    def _stop_scraping(self):
        if self._active_worker is not None:
            self._active_worker.request_stop()
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Stopping...")
            self.status_label.setText("Stopping — finishing the current item, please wait...")

    def _on_maps_progress(self, current, total):
        pct = int((current / max(total, 1)) * 50)  # Maps phase = first half of the bar
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"Scanning Google Maps: listing {current}/{total}")
        self._log(f"[Maps] scraped listing {current}/{total}")

    def _on_email_progress(self, current, total):
        pct = 50 + int((current / max(total, 1)) * 50)  # Email phase = second half
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"Checking websites for emails: {current}/{total}")
        self._log(f"[Email] checked website {current}/{total}")

    def _on_result(self, leads):
        self.current_leads = leads
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("🔍  Start Scraping")
        self.stop_btn.setVisible(False)
        self.stop_btn.setEnabled(True)
        self.stop_btn.setText("⏹  Stop")
        self._active_worker = None
        self.progress_bar.setValue(100)

        if not leads:
            self._log("⚠️ No leads found. Try a different keyword or city.")
            self.status_label.setText("No leads found.")
            self.selection_label.setText("No leads yet.")
            return

        with_email = sum(1 for l in leads if l.emails)
        self._log(f"✅ Done. Found {len(leads)} leads, {with_email} with at least one email.")
        self.status_label.setText(f"Found {len(leads)} leads ({with_email} with email).")

        self._populate_table(leads)

    def _on_error(self, message):
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("🔍  Start Scraping")
        self.stop_btn.setVisible(False)
        self.stop_btn.setEnabled(True)
        self.stop_btn.setText("⏹  Stop")
        self._active_worker = None
        friendly = self._friendly_error_message(message)
        self._log(f"❌ Error: {friendly}")
        self.status_label.setText("Scraping failed — see log.")
        QMessageBox.critical(self, "Scraping Error", friendly)

    def _friendly_error_message(self, raw_message: str) -> str:
        """Translates common raw exception text into something the user can
        actually act on, instead of a confusing stack-trace-style string."""
        msg = raw_message.lower()

        if "executable doesn't exist" in msg or "playwright install" in msg:
            return (
                "Playwright's browser isn't installed yet. Open a terminal in your "
                "project folder (with your venv active) and run:\n\n"
                "    playwright install chromium\n\n"
                "Then try again."
            )
        if "err_internet_disconnected" in msg or "net::err" in msg or "name_not_resolved" in msg:
            return "Couldn't reach Google Maps — check your internet connection and try again."
        if "captcha" in msg or "unusual traffic" in msg or "consent" in msg:
            return raw_message  # already written to be user-friendly in maps_agent.py
        if "request_denied" in msg:
            return "Google Places API rejected the request — double check the API key is correct and pasted in full."
        if "over_query_limit" in msg:
            return "Google Places API quota reached for today — leave the API key blank to use free scraping instead, or wait and retry."
        if "invalid_request" in msg:
            return "Google Places API says the request was invalid — try a simpler keyword or city name."

        return raw_message

    def _populate_table(self, leads):
        # Block signals while we bulk-build rows — otherwise itemChanged
        # would fire for every single cell as we create it.
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(0)
        for lead in leads:
            self._append_row(lead)
        self.results_table.blockSignals(False)
        self._update_selection_summary()

    def _append_row(self, lead):
        """Adds ONE row to the table for a single Lead — used both by bulk
        population and by manually adding a new lead."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        include_item = QTableWidgetItem()
        include_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        include_item.setCheckState(Qt.CheckState.Checked if lead.include else Qt.CheckState.Unchecked)
        self.results_table.setItem(row, 0, include_item)

        self.results_table.setItem(row, 1, self._readonly_item(lead.business_name))

        email_item = QTableWidgetItem(", ".join(lead.emails) if lead.emails else "")
        email_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
        self.results_table.setItem(row, 2, email_item)

        self.results_table.setItem(row, 3, self._readonly_item(lead.website or "—"))
        self.results_table.setItem(row, 4, self._readonly_item(lead.phone or "—"))
        self.results_table.setItem(row, 5, self._readonly_item(lead.address or "—"))

    def _readonly_item(self, text):
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        return item

    def _on_item_changed(self, item):
        """
        Fires whenever a checkbox is toggled or the Emails cell is edited.
        Keeps self.current_leads in sync with whatever's shown in the table
        — this is the data Phase 4's Excel export will read from.
        """
        row = item.row()
        col = item.column()
        if row >= len(self.current_leads):
            return
        lead = self.current_leads[row]

        if col == 0:  # Include checkbox
            lead.include = (item.checkState() == Qt.CheckState.Checked)
        elif col == 2:  # Emails column — comma-separated, user-edited
            text = item.text().strip()
            lead.emails = [e.strip() for e in text.split(",") if e.strip()]

        self._update_selection_summary()

    def _set_all_included(self, include):
        if not self.current_leads:
            return
        self.results_table.blockSignals(True)
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            item.setCheckState(Qt.CheckState.Checked if include else Qt.CheckState.Unchecked)
            self.current_leads[row].include = include
        self.results_table.blockSignals(False)
        self._update_selection_summary()

    def _update_selection_summary(self):
        total = len(self.current_leads)
        if total == 0:
            self.selection_label.setText("No leads yet.")
            return
        selected = sum(1 for l in self.current_leads if l.include)
        self.selection_label.setText(f"{selected} of {total} leads selected to keep")

    def _export_to_excel(self):
        if not self.current_leads:
            QMessageBox.information(self, "Nothing to Export", "Run a search first — there are no leads yet.")
            return

        included_count = sum(1 for l in self.current_leads if l.include)
        if included_count == 0:
            QMessageBox.warning(
                self, "Nothing Selected",
                "All leads are unchecked — nothing would be exported. Check at least one lead first."
            )
            return

        keyword = self.keyword_input.text().strip().replace(" ", "_") or "leads"
        city = self.city_input.text().strip().replace(" ", "_") or "export"
        default_name = f"leads_{keyword}_{city}.xlsx"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Leads to Excel", default_name, "Excel Files (*.xlsx)"
        )
        if not filepath:
            return  # user cancelled the dialog

        if not filepath.lower().endswith(".xlsx"):
            filepath += ".xlsx"

        try:
            row_count = export_leads_to_excel(self.current_leads, filepath, only_included=True)
        except PermissionError:
            QMessageBox.critical(
                self, "Export Failed",
                "Couldn't write the file — is it already open in Excel? Close it and try again."
            )
            return
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Something went wrong: {e}")
            return

        self._log(f"📤 Exported {row_count} rows to {filepath}")
        QMessageBox.information(
            self, "Export Complete",
            f"Exported {row_count} rows to:\n{filepath}\n\n"
            f"This file is ready to import straight into your Email Agent."
        )

    def _send_to_email_agent(self):
        """
        Skips the Excel export/import round-trip entirely — flattens the
        checked leads into {"email", "name"} entries (same one-email-per-row
        logic as the Excel export, since a lead can have multiple emails)
        and hands them straight to the Email Agent via a signal MainWindow
        listens for.
        """
        if not self.current_leads:
            QMessageBox.information(self, "Nothing to Send", "Run a search first — there are no leads yet.")
            return

        entries = []
        for lead in self.current_leads:
            if not lead.include:
                continue
            for email in lead.emails:
                entries.append({"email": email, "name": lead.business_name})

        if not entries:
            QMessageBox.warning(
                self, "No Emails to Send",
                "None of the checked leads have an email address. Add one manually or check a different lead."
            )
            return

        self.sendToEmailAgent.emit(entries)
        self._log(f"📨 Sent {len(entries)} recipients to the Email Agent.")

    def _add_manual_lead(self):
        name = self.manual_name_input.text().strip()
        email = self.manual_email_input.text().strip()
        website = self.manual_website_input.text().strip()

        if not email:
            QMessageBox.warning(self, "Email Required", "Please enter an email address to add.")
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            QMessageBox.warning(self, "Invalid Email", "That doesn't look like a valid email address.")
            return

        lead = Lead(
            business_name=name or "Manually added",
            keyword=self.keyword_input.text().strip(),
            city=self.city_input.text().strip(),
            website=website,
            emails=[email],
            source="Manual",
            include=True,
        )
        self.current_leads.append(lead)
        self._append_row(lead)
        self._update_selection_summary()

        self.manual_name_input.clear()
        self.manual_email_input.clear()
        self.manual_website_input.clear()
        self._log(f"➕ Manually added: {lead.business_name} ({email})")

    def _log(self, message):
        self.log_box.append(message)

    # ------------------------------------------------------------------ #
    # Theme support (matches DashboardPage.update_theme pattern)
    # ------------------------------------------------------------------ #
    def update_theme(self, theme):
        self.theme = theme
        # Simplest reliable approach for this page: rebuild the UI with the
        # new theme colors (cheap for a form this size, and guarantees every
        # widget picks up the new palette correctly).
        keyword = self.keyword_input.text()
        city = self.city_input.text()
        api_key = self.api_key_input.text()

        # Clear old layout
        old_layout = self.layout()
        QWidget().setLayout(old_layout)  # detach old layout safely

        self._setup_ui()
        self.keyword_input.setText(keyword)
        self.city_input.setText(city)
        self.api_key_input.setText(api_key)

        # Restore last results too, so toggling the theme mid-review doesn't
        # wipe out a scrape the user already ran.
        if self.current_leads:
            self._populate_table(self.current_leads)
            with_email = sum(1 for l in self.current_leads if l.emails)
            self.status_label.setText(f"Found {len(self.current_leads)} leads ({with_email} with email).")
            self.progress_bar.setValue(100)
