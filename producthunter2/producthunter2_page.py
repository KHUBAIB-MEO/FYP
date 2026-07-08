"""
producthunter2/producthunter2_page.py
---------------------------------------
Phase 2: PyQt6 page for the Product Hunter (v2) agent.

Same proven structure as emailscraper_page.py:
  - QObject worker on a QThread so the UI never freezes
  - Everything wrapped in a QScrollArea (no squeezing on maximize)
  - Themed table, progress bar, live log
  - update_theme() rebuilds with new colors and preserves results
"""
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QSpinBox, QComboBox,
    QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGridLayout, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QObject

from producthunter2.core.hunter import hunt_products
from producthunter2.core.product_fetcher import CATEGORY_MAP
from producthunter2.core.excel_exporter import export_products_to_excel


# ======================================================================== #
# Background worker                                                        #
# ======================================================================== #

class HuntWorker(QObject):
    """Runs hunt_products() in a background thread."""

    fetch_progress = pyqtSignal(int, int)
    result = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, category, api_key, max_results, country):
        super().__init__()
        self.category = category
        self.api_key = api_key
        self.max_results = max_results
        self.country = country

    @pyqtSlot()
    def run(self):
        try:
            products = hunt_products(
                category=self.category,
                api_key=self.api_key,
                max_results=self.max_results,
                country=self.country,
                on_fetch_progress=self.fetch_progress.emit,
            )
            self.result.emit(products)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


# ======================================================================== #
# Main page                                                                #
# ======================================================================== #

class ProductHunter2Page(QWidget):
    """Registered in MainWindow like the other agent pages."""

    backToDashboard = pyqtSignal()
    sendToContentAgent = pyqtSignal(dict)  # {"topic": ..., "keywords": ...}

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._threads = []
        self.current_products = []
        self._included = []   # parallel to current_products: keep/discard checkbox state
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
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
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_separator())
        layout.addLayout(self._build_input_form())
        layout.addLayout(self._build_api_key_row())
        layout.addLayout(self._build_action_row())
        layout.addWidget(self._progress_bar())
        layout.addWidget(self._status_label())
        layout.addWidget(self._log_box())
        layout.addLayout(self._build_table_toolbar())
        layout.addWidget(self._results_table())

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _build_header(self):
        row = QHBoxLayout()
        back_btn = QPushButton("←  Back to Dashboard")
        back_btn.setStyleSheet(self._button_style(secondary=True))
        back_btn.clicked.connect(self.backToDashboard.emit)
        row.addWidget(back_btn)
        row.addStretch()
        title = QLabel("🛒  Product Hunter")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme['text']};")
        row.addWidget(title)
        row.addStretch()
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

        cat_label = QLabel("Category")
        cat_label.setStyleSheet(label_style)
        self.category_input = QComboBox()
        self.category_input.addItems(list(CATEGORY_MAP.keys()))
        self.category_input.setStyleSheet(self._input_style())

        country_label = QLabel("Marketplace")
        country_label.setStyleSheet(label_style)
        self.country_input = QComboBox()
        self.country_input.addItems(["US", "UK", "DE", "IN", "CA", "AU"])
        self.country_input.setStyleSheet(self._input_style())

        results_label = QLabel("Max Results")
        results_label.setStyleSheet(label_style)
        self.max_results_input = QSpinBox()
        self.max_results_input.setRange(5, 50)
        self.max_results_input.setValue(20)
        self.max_results_input.setStyleSheet(self._input_style())

        grid.addWidget(cat_label, 0, 0)
        grid.addWidget(self.category_input, 1, 0)
        grid.addWidget(country_label, 0, 1)
        grid.addWidget(self.country_input, 1, 1)
        grid.addWidget(results_label, 0, 2)
        grid.addWidget(self.max_results_input, 1, 2)
        return grid

    def _build_api_key_row(self):
        wrapper = QVBoxLayout()
        wrapper.setSpacing(4)

        label = QLabel("RapidAPI Key  (optional — leave blank to use built-in demo data)")
        label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme['text_secondary']};")
        wrapper.addWidget(label)

        row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Paste your RapidAPI key for live Amazon data (free tier: ~100 requests/month)")
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
            "Subscribe (free, no card) to 'Real-Time Amazon Data' on RapidAPI, copy the key here. "
            "Without a key, the app runs on realistic sample data so it always works."
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

    def _build_action_row(self):
        row = QHBoxLayout()
        self.hunt_btn = QPushButton("🔍  Hunt Products")
        self.hunt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hunt_btn.setStyleSheet(self._button_style(secondary=False))
        self.hunt_btn.clicked.connect(self._start_hunt)
        row.addWidget(self.hunt_btn)
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
        self.log_box.setFixedHeight(90)
        self.log_box.setStyleSheet(
            f"background-color: {self.theme['code_bg']}; color: {self.theme['text_secondary']}; "
            f"border: 1px solid {self.theme['border']}; border-radius: 6px; font-family: Consolas, monospace; font-size: 12px;"
        )
        return self.log_box

    def _build_table_toolbar(self):
        row = QHBoxLayout()
        self.summary_label = QLabel("No products yet.")
        self.summary_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme['text_secondary']};")
        row.addWidget(self.summary_label)
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

        content_btn = QPushButton("✍️ Write Content")
        content_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        content_btn.setStyleSheet(self._button_style(secondary=False))
        content_btn.clicked.connect(self._send_to_content_agent)
        row.addWidget(content_btn)

        return row

    def _results_table(self):
        self.results_table = QTableWidget(0, 9)
        self.results_table.setMinimumHeight(420)
        self.results_table.setHorizontalHeaderLabels(
            ["Keep", "Score", "Product", "Price", "Rating", "Reviews", "Demand", "Competition", "Why"]
        )
        hdr = self.results_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
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
    # Styles
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
    # Hunt logic
    # ------------------------------------------------------------------ #
    def _start_hunt(self):
        category = self.category_input.currentText()
        country = self.country_input.currentText()

        self.hunt_btn.setEnabled(False)
        self.hunt_btn.setText("Hunting...")
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.results_table.setRowCount(0)

        key = self.api_key_input.text().strip()
        self._log(f"Hunting '{category}' products"
                  f"{' via RapidAPI...' if key else ' (demo data — no API key)...'}")

        thread = QThread()
        worker = HuntWorker(
            category=category,
            api_key=key,
            max_results=self.max_results_input.value(),
            country=country,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.fetch_progress.connect(self._on_fetch_progress)
        worker.result.connect(self._on_result)
        worker.error.connect(self._on_error)
        worker.finished.connect(thread.quit)
        thread.start()
        self._threads.append((thread, worker))

    def _on_fetch_progress(self, current, total):
        pct = int((current / max(total, 1)) * 100)
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"Fetching products: {current}/{total}")

    def _on_result(self, products):
        self.current_products = products
        self._included = [True] * len(products)
        self.hunt_btn.setEnabled(True)
        self.hunt_btn.setText("🔍  Hunt Products")
        self.progress_bar.setValue(100)

        if not products:
            self._log("⚠️ No products found. Try another category.")
            self.status_label.setText("No products found.")
            self.summary_label.setText("No products yet.")
            return

        top = products[0]
        source = products[0].source
        self._log(f"✅ Found {len(products)} products. Top pick: {top.title[:40]} (score {top.opportunity_score:.0f})")
        self._log(f"   Source: {source}")
        self.status_label.setText(f"Found {len(products)} products — sorted best-opportunity-first.")
        self._populate_table(products)

    def _on_error(self, message):
        self.hunt_btn.setEnabled(True)
        self.hunt_btn.setText("🔍  Hunt Products")
        self._log(f"❌ Error: {message}")
        self.status_label.setText("Hunt failed — see log.")
        QMessageBox.critical(self, "Hunt Error", message)

    def _populate_table(self, products):
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(len(products))
        for row, p in enumerate(products):
            keep_item = QTableWidgetItem()
            keep_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checked = self._included[row] if row < len(self._included) else True
            keep_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.results_table.setItem(row, 0, keep_item)

            self.results_table.setItem(row, 1, self._score_item(p.opportunity_score))
            self.results_table.setItem(row, 2, QTableWidgetItem(p.title))
            self.results_table.setItem(row, 3, QTableWidgetItem(p.price_display or "—"))
            self.results_table.setItem(row, 4, QTableWidgetItem(str(p.rating) if p.rating else "—"))
            self.results_table.setItem(row, 5, QTableWidgetItem(f"{p.num_reviews:,}" if p.num_reviews else "—"))
            self.results_table.setItem(row, 6, QTableWidgetItem(f"{p.demand_score:.0f}"))
            self.results_table.setItem(row, 7, QTableWidgetItem(f"{p.competition_score:.0f}"))
            self.results_table.setItem(row, 8, QTableWidgetItem(p.score_reason))
        self.results_table.blockSignals(False)
        self._update_summary()

    def _on_item_changed(self, item):
        if item.column() != 0:
            return
        row = item.row()
        if row < len(self._included):
            self._included[row] = (item.checkState() == Qt.CheckState.Checked)
        self._update_summary()

    def _set_all_included(self, include):
        if not self.current_products:
            return
        self._included = [include] * len(self.current_products)
        self.results_table.blockSignals(True)
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked if include else Qt.CheckState.Unchecked)
        self.results_table.blockSignals(False)
        self._update_summary()

    def _update_summary(self):
        total = len(self.current_products)
        if total == 0:
            self.summary_label.setText("No products yet.")
            return
        kept = sum(1 for x in self._included if x)
        source = self.current_products[0].source
        self.summary_label.setText(f"{kept} of {total} kept  ·  source: {source}")

    def _send_to_content_agent(self):
        """
        Builds a ready-to-generate content prompt from the KEPT products and
        hands it to the Content Scripting agent (via a signal MainWindow
        listens for), which pre-fills its topic + keywords fields. One click
        from 'found a winning product' to 'writing its ad copy'.
        """
        if not self.current_products:
            QMessageBox.information(self, "Nothing to Send", "Run a hunt first — there are no products yet.")
            return

        kept = [p for p, inc in zip(self.current_products, self._included) if inc]
        if not kept:
            QMessageBox.warning(self, "Nothing Selected", "All products are unchecked — check at least one first.")
            return

        # Focus on the single best kept product for a sharp, usable prompt,
        # but include the others as supporting context.
        best = kept[0]
        topic = (
            f"Write compelling marketing copy for this trending product: "
            f"'{best.title}'"
            f"{f' (priced around {best.price_display})' if best.price_display else ''}. "
            f"Highlight why it's a great buy and create urgency."
        )

        # Keywords: product title words + category, comma-separated
        kw_bits = [best.category] if best.category else []
        kw_bits += [w for w in best.title.split() if len(w) > 3][:5]
        keywords = ", ".join(dict.fromkeys(kw_bits))  # dedupe, keep order

        if len(kept) > 1:
            others = "; ".join(p.title for p in kept[1:6])
            topic += f"\n\nOther shortlisted products for reference: {others}."

        self.sendToContentAgent.emit({"topic": topic, "keywords": keywords})
        self._log(f"✍️ Sent '{best.title[:40]}' to the Content agent.")

    def _export_to_excel(self):
        if not self.current_products:
            QMessageBox.information(self, "Nothing to Export", "Run a hunt first — there are no products yet.")
            return
        if not any(self._included):
            QMessageBox.warning(self, "Nothing Selected", "All products are unchecked — check at least one to export.")
            return

        cat = self.category_input.currentText().replace(" ", "_").replace("&", "and")
        default_name = f"products_{cat}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Products to Excel", default_name, "Excel Files (*.xlsx)"
        )
        if not filepath:
            return
        if not filepath.lower().endswith(".xlsx"):
            filepath += ".xlsx"

        try:
            count = export_products_to_excel(self.current_products, filepath, only_included=self._included)
        except PermissionError:
            QMessageBox.critical(self, "Export Failed", "Couldn't write the file — is it open in Excel? Close it and retry.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Something went wrong: {e}")
            return

        self._log(f"📤 Exported {count} products to {filepath}")
        QMessageBox.information(self, "Export Complete", f"Exported {count} products to:\n{filepath}")

    def _score_item(self, score):
        """Score cell, color-coded green/amber/red by opportunity level."""
        item = QTableWidgetItem(f"{score:.0f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        from PyQt6.QtGui import QColor
        if score >= 85:
            item.setForeground(QColor(self.theme["success"]))
        elif score >= 70:
            item.setForeground(QColor(self.theme["warning"]))
        else:
            item.setForeground(QColor(self.theme["text_light"]))
        return item

    def _log(self, message):
        self.log_box.append(message)

    # ------------------------------------------------------------------ #
    # Theme
    # ------------------------------------------------------------------ #
    def update_theme(self, theme):
        self.theme = theme
        category = self.category_input.currentText() if hasattr(self, "category_input") else None
        api_key = self.api_key_input.text() if hasattr(self, "api_key_input") else ""

        old_layout = self.layout()
        QWidget().setLayout(old_layout)

        self._setup_ui()
        if category:
            idx = self.category_input.findText(category)
            if idx >= 0:
                self.category_input.setCurrentIndex(idx)
        self.api_key_input.setText(api_key)

        if self.current_products:
            self._populate_table(self.current_products)
            self.progress_bar.setValue(100)
