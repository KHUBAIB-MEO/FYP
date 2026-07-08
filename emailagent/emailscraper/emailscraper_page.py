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
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QObject

from emailscraper.core.lead_finder import find_leads


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

    def __init__(self, keyword, city, max_results, headless,
                 min_delay, max_delay, cooldown_every, cooldown_seconds):
        super().__init__()
        self.keyword = keyword
        self.city = city
        self.max_results = max_results
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.cooldown_every = cooldown_every
        self.cooldown_seconds = cooldown_seconds

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
                on_maps_progress=self.maps_progress.emit,
                on_email_progress=self.email_progress.emit,
            )
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

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._threads = []      # keep references alive so Qt doesn't GC them mid-run
        self.current_leads = [] # last scrape results — Phase 3/4 will use this
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_separator())
        layout.addLayout(self._build_input_form())
        layout.addLayout(self._build_advanced_settings())
        layout.addLayout(self._build_action_row())
        layout.addWidget(self._progress_bar())
        layout.addWidget(self._status_label())
        layout.addWidget(self._log_box())
        layout.addWidget(self._results_table(), stretch=1)

    def _build_header(self):
        row = QHBoxLayout()

        back_btn = QPushButton("←  Back to Dashboard")
        back_btn.setStyleSheet(self._button_style(secondary=True))
        back_btn.clicked.connect(self.backToDashboard.emit)
        row.addWidget(back_btn)

        row.addStretch()

        title = QLabel("📧  Email Scraper")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme['text']};")
        row.addWidget(title)

        row.addStretch()
        # Empty spacer widget so the title stays visually centered
        spacer = QLabel("")
        spacer.setFixedWidth(back_btn.sizeHint().width())
        row.addWidget(spacer)

        return row

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
        row.addStretch()
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
        self.results_table = QTableWidget(0, 5)
        self.results_table.setHorizontalHeaderLabels(
            ["Business Name", "Emails", "Website", "Phone", "Address"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet(
            f"QTableWidget {{ background-color: {self.theme['card']}; color: {self.theme['text']}; "
            f"gridline-color: {self.theme['border']}; border: 1px solid {self.theme['border']}; }}"
            f"QHeaderView::section {{ background-color: {self.theme['hover']}; color: {self.theme['text_secondary']}; "
            f"padding: 6px; border: none; font-weight: 600; }}"
        )
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

        if self.min_delay_input.value() >= self.max_delay_input.value():
            QMessageBox.warning(self, "Invalid Delay Range", "Min delay must be less than max delay.")
            return

        self.scrape_btn.setEnabled(False)
        self.scrape_btn.setText("Scraping...")
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
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.maps_progress.connect(self._on_maps_progress)
        worker.email_progress.connect(self._on_email_progress)
        worker.result.connect(self._on_result)
        worker.error.connect(self._on_error)
        worker.finished.connect(thread.quit)
        thread.start()

        # Keep references so Python/Qt don't garbage-collect the thread mid-run
        self._threads.append((thread, worker))

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
        self.progress_bar.setValue(100)

        if not leads:
            self._log("⚠️ No leads found. Try a different keyword or city.")
            self.status_label.setText("No leads found.")
            return

        with_email = sum(1 for l in leads if l.emails)
        self._log(f"✅ Done. Found {len(leads)} leads, {with_email} with at least one email.")
        self.status_label.setText(f"Found {len(leads)} leads ({with_email} with email).")

        self._populate_table(leads)

    def _on_error(self, message):
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("🔍  Start Scraping")
        self._log(f"❌ Error: {message}")
        self.status_label.setText("Scraping failed — see log.")
        QMessageBox.critical(self, "Scraping Error", message)

    def _populate_table(self, leads):
        self.results_table.setRowCount(len(leads))
        for row, lead in enumerate(leads):
            self.results_table.setItem(row, 0, QTableWidgetItem(lead.business_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(", ".join(lead.emails) if lead.emails else "—"))
            self.results_table.setItem(row, 2, QTableWidgetItem(lead.website or "—"))
            self.results_table.setItem(row, 3, QTableWidgetItem(lead.phone or "—"))
            self.results_table.setItem(row, 4, QTableWidgetItem(lead.address or "—"))

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

        # Clear old layout
        old_layout = self.layout()
        QWidget().setLayout(old_layout)  # detach old layout safely

        self._setup_ui()
        self.keyword_input.setText(keyword)
        self.city_input.setText(city)
