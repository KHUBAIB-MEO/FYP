"""
Product Hunter — Main Page
===========================
Full-featured page with sidebar navigation, sub-pages, and
background threading so the UI never freezes during scraping/AI.
Integrates into AI TASKFORCE via dashboard like Email and Content agents.
"""
import csv
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QStackedWidget, QProgressBar, QComboBox,
    QLineEdit, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QTextEdit,
    QSplitter, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QObject
from PyQt6.QtGui import QColor, QFont

from producthunter.database.db_manager import DBManager
from producthunter.core.scraper_agent import ScraperAgent
from producthunter.core.trend_agent import TrendAgent
from producthunter.core.analysis_agent import AnalysisAgent
from producthunter.core.recommendation_agent import RecommendationAgent
from producthunter.models.product import Product


# ======================================================================== #
# Background worker threads (so UI never freezes)                          #
# ======================================================================== #

class ScrapeWorker(QObject):
    """Runs scraping in a background thread."""
    progress   = pyqtSignal(int, int)          # current, total
    result     = pyqtSignal(list)              # list of Product
    error      = pyqtSignal(str)
    finished   = pyqtSignal()

    def __init__(self, source: str, keyword: str, max_pages: int):
        super().__init__()
        self.source    = source
        self.keyword   = keyword
        self.max_pages = max_pages

    @pyqtSlot()
    def run(self):
        try:
            agent = ScraperAgent()
            products = agent.scrape(
                self.source, self.keyword, self.max_pages,
                progress_cb=self.progress.emit
            )
            self.result.emit(products)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class AnalysisWorker(QObject):
    """Runs AI analysis in a background thread."""
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, products: list, model: str):
        super().__init__()
        self.products = products
        self.model    = model

    @pyqtSlot()
    def run(self):
        try:
            agent = AnalysisAgent(model=self.model)
            # Also enrich with trends
            trend_agent = TrendAgent()
            self.products = trend_agent.enrich_products(self.products)

            results = agent.analyse_batch(
                self.products,
                progress_cb=self.progress.emit
            )
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


# ======================================================================== #
# Main ProductHunterPage                                                   #
# ======================================================================== #

class ProductHunterPage(QWidget):
    """
    Full-featured Product Hunter agent page.
    Has its own sidebar + stacked sub-pages.
    Registered in MainWindow just like EmailPage and ContentPage.
    """
    backToDashboard = pyqtSignal()

    NAV_ITEMS = [
        ("dashboard",  "🏠", "Dashboard"),
        ("scrape",     "🔍", "Scrape"),
        ("products",   "📦", "Products"),
        ("analysis",   "🤖", "AI Analysis"),
        ("trends",     "📈", "Trends"),
        ("reports",    "📄", "Reports"),
        ("settings",   "⚙️",  "Settings"),
    ]

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme   = theme
        self.db      = DBManager()
        self.current_products: list[Product] = []
        self._threads = []   # Keep references so GC doesn't kill threads
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI Setup                                                             #
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────── #
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(4)

        # Back button
        back_btn = QPushButton("← Dashboard")
        back_btn.setObjectName("back_btn")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(
            f"QPushButton {{ color: {self.theme['text_light']}; "
            f"background: transparent; border: none; "
            f"text-align: left; padding: 8px 12px; font-size: 13px; }}"
            f"QPushButton:hover {{ color: {self.theme['primary']}; }}"
        )
        back_btn.clicked.connect(self.backToDashboard.emit)
        sidebar_layout.addWidget(back_btn)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background: {self.theme['border']}; max-height: 1px;")
        sidebar_layout.addWidget(line)
        sidebar_layout.addSpacing(8)

        # Agent title
        agent_title = QLabel("🛒 Product Hunter")
        agent_title.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {self.theme['text']};"
            f"padding: 4px 12px;"
        )
        sidebar_layout.addWidget(agent_title)
        sidebar_layout.addSpacing(8)

        # Nav buttons
        self.nav_buttons = {}
        for page_id, icon, label in self.NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName(f"nav_{page_id}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(42)
            btn.setStyleSheet(self._nav_style(active=False))
            btn.clicked.connect(lambda checked, pid=page_id: self._navigate(pid))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[page_id] = btn

        sidebar_layout.addStretch()
        root.addWidget(self.sidebar)

        # ── Content stack ─────────────────────────────────────────── #
        self.stack = QStackedWidget()
        self.pages = {}
        builders = {
            "dashboard": self._build_dashboard_page,
            "scrape":    self._build_scrape_page,
            "products":  self._build_products_page,
            "analysis":  self._build_analysis_page,
            "trends":    self._build_trends_page,
            "reports":   self._build_reports_page,
            "settings":  self._build_settings_page,
        }
        for page_id, _ in [(n[0], n) for n in self.NAV_ITEMS]:
            page = builders[page_id]()
            self.pages[page_id] = page
            self.stack.addWidget(page)

        root.addWidget(self.stack)
        self._navigate("dashboard")

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #
    def _navigate(self, page_id: str):
        self.stack.setCurrentWidget(self.pages[page_id])
        for pid, btn in self.nav_buttons.items():
            btn.setStyleSheet(self._nav_style(active=(pid == page_id)))
        if page_id == "dashboard":
            self._refresh_dashboard_stats()
        elif page_id == "products":
            self._load_products_table()

    def _nav_style(self, active: bool) -> str:
        if active:
            return (f"QPushButton {{ background: {self.theme['nav_active_bg']}; "
                    f"color: {self.theme['primary']}; border: none; "
                    f"border-radius: 8px; text-align: left; padding: 0 12px; "
                    f"font-size: 13px; font-weight: 600; }}")
        return (f"QPushButton {{ background: transparent; "
                f"color: {self.theme['nav_inactive_text']}; border: none; "
                f"border-radius: 8px; text-align: left; padding: 0 12px; "
                f"font-size: 13px; }}"
                f"QPushButton:hover {{ background: {self.theme['nav_hover']}; "
                f"color: {self.theme['text']}; }}")

    # ================================================================== #
    # Sub-page builders                                                    #
    # ================================================================== #

    # ── 1. Dashboard ─────────────────────────────────────────────────── #
    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel("📊 Product Hunter Dashboard")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        sub = QLabel("Overview of your product hunting activity")
        sub.setStyleSheet(f"font-size: 14px; color: {self.theme['text_light']};")
        layout.addWidget(sub)

        # Stat cards row
        row = QHBoxLayout()
        row.setSpacing(16)
        self._stat_total    = self._stat_card("0", "Total Products",  "#6366f1")
        self._stat_cats     = self._stat_card("0", "Categories",      "#10b981")
        self._stat_analysed = self._stat_card("0", "AI Analysed",     "#f59e0b")
        self._stat_reports  = self._stat_card("0", "Reports",         "#8b5cf6")
        for c in [self._stat_total, self._stat_cats,
                  self._stat_analysed, self._stat_reports]:
            row.addWidget(c)
        layout.addLayout(row)

        # Quick actions
        qa_frame = QFrame()
        qa_frame.setObjectName("card")
        qa_layout = QVBoxLayout(qa_frame)
        qa_layout.setContentsMargins(20, 20, 20, 20)
        qa_layout.setSpacing(10)
        qa_label = QLabel("⚡ Quick Actions")
        qa_label.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {self.theme['text']};"
        )
        qa_layout.addWidget(qa_label)
        btn_row = QHBoxLayout()
        scrape_btn = QPushButton("🔍 Start Scraping")
        scrape_btn.clicked.connect(lambda: self._navigate("scrape"))
        analyse_btn = QPushButton("🤖 Run AI Analysis")
        analyse_btn.clicked.connect(lambda: self._navigate("analysis"))
        export_btn = QPushButton("📄 Export Report")
        export_btn.clicked.connect(lambda: self._navigate("reports"))
        for b in [scrape_btn, analyse_btn, export_btn]:
            btn_row.addWidget(b)
        btn_row.addStretch()
        qa_layout.addLayout(btn_row)
        layout.addWidget(qa_frame)
        layout.addStretch()
        return page

    def _stat_card(self, number: str, label: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(160)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 20, 20, 20)
        cl.setSpacing(6)
        num = QLabel(number)
        num.setStyleSheet(f"font-size: 34px; font-weight: 700; color: {color};")
        cl.addWidget(num)
        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"font-size: 13px; color: {self.theme['text_light']}; font-weight: 500;"
        )
        cl.addWidget(lbl)
        card._num = num
        return card

    def _refresh_dashboard_stats(self):
        stats = self.db.get_stats()
        self._stat_total._num.setText(str(stats["total_products"]))
        self._stat_cats._num.setText(str(stats["categories"]))
        self._stat_analysed._num.setText(str(stats["analysed"]))
        self._stat_reports._num.setText(str(stats["reports"]))

    # ── 2. Scrape ────────────────────────────────────────────────────── #
    def _build_scrape_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel("🔍 Scrape Products")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        # Controls card
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(16)

        # Source + keyword row
        row1 = QHBoxLayout()
        src_lbl = QLabel("Source:")
        src_lbl.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        row1.addWidget(src_lbl)
        self._scrape_source = QComboBox()
        self._scrape_source.addItems(["Reddit", "Amazon", "AliExpress"])
        self._scrape_source.setFixedWidth(160)
        row1.addWidget(self._scrape_source)
        row1.addSpacing(20)

        kw_lbl = QLabel("Keyword:")
        kw_lbl.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        row1.addWidget(kw_lbl)
        self._scrape_kw = QLineEdit()
        self._scrape_kw.setPlaceholderText("e.g. wireless earbuds, phone case")
        row1.addWidget(self._scrape_kw)
        cl.addLayout(row1)

        # Pages row
        row2 = QHBoxLayout()
        pg_lbl = QLabel("Max Pages:")
        pg_lbl.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        row2.addWidget(pg_lbl)
        self._scrape_pages = QComboBox()
        self._scrape_pages.addItems(["1", "2", "3", "5"])
        self._scrape_pages.setFixedWidth(80)
        row2.addWidget(self._scrape_pages)
        row2.addStretch()
        cl.addLayout(row2)

        # Start button
        self._scrape_btn = QPushButton("🚀 Start Scraping")
        self._scrape_btn.setFixedWidth(180)
        self._scrape_btn.clicked.connect(self._start_scrape)
        cl.addWidget(self._scrape_btn)

        # Progress
        self._scrape_progress = QProgressBar()
        self._scrape_progress.setRange(0, 100)
        self._scrape_progress.setValue(0)
        cl.addWidget(self._scrape_progress)

        # Status
        self._scrape_status = QLabel("Ready")
        self._scrape_status.setStyleSheet(
            f"color: {self.theme['text_light']}; font-size: 13px;"
        )
        cl.addWidget(self._scrape_status)
        layout.addWidget(card)

        # Log box
        self._scrape_log = QTextEdit()
        self._scrape_log.setReadOnly(True)
        self._scrape_log.setMaximumHeight(200)
        self._scrape_log.setStyleSheet(
            f"background: {self.theme['input_bg']}; "
            f"color: {self.theme['text']}; border-radius: 8px; "
            f"font-family: Consolas, monospace; font-size: 12px;"
        )
        layout.addWidget(self._scrape_log)
        layout.addStretch()
        return page

    def _start_scrape(self):
        source  = self._scrape_source.currentText()
        keyword = self._scrape_kw.text().strip()
        pages   = int(self._scrape_pages.currentText())

        if not keyword:
            QMessageBox.warning(self, "Input Required", "Please enter a keyword.")
            return

        self._scrape_btn.setEnabled(False)
        self._scrape_btn.setText("Scraping...")
        self._scrape_progress.setValue(0)
        self._scrape_log.clear()
        self._log(f"Starting {source} scrape for: '{keyword}' ({pages} pages)")

        # Background thread
        self._scrape_thread = QThread()
        self._scrape_worker = ScrapeWorker(source.lower(), keyword, pages)
        self._scrape_worker.moveToThread(self._scrape_thread)

        self._scrape_thread.started.connect(self._scrape_worker.run)
        self._scrape_worker.progress.connect(self._on_scrape_progress)
        self._scrape_worker.result.connect(self._on_scrape_done)
        self._scrape_worker.error.connect(
            lambda e: self._log(f"❌ Error: {e}")
        )
        self._scrape_worker.finished.connect(self._scrape_thread.quit)
        self._scrape_thread.start()
        self._threads.append(self._scrape_thread)

    def _on_scrape_progress(self, current: int, total: int):
        pct = int((current / max(total, 1)) * 100)
        self._scrape_progress.setValue(pct)
        self._scrape_status.setText(f"Page {current} / {total}")

    def _on_scrape_done(self, products: list):
        self._scrape_btn.setEnabled(True)
        self._scrape_btn.setText("🚀 Start Scraping")
        self._scrape_progress.setValue(100)

        if not products:
            self._log("⚠️ No products found. Try a different keyword.")
            return

        self._log(f"✅ Found {len(products)} products. Saving to database...")

        saved = 0
        for p in products:
            try:
                self.db.insert_product(p.to_dict())
                saved += 1
            except Exception as e:
                self._log(f"DB error: {e}")

        self.current_products = products
        self._log(f"💾 Saved {saved} products. Go to Products tab to view them.")
        self._refresh_dashboard_stats()

    def _log(self, msg: str):
        self._scrape_log.append(f"  {msg}")

    # ── 3. Products table ─────────────────────────────────────────────── #
    def _build_products_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("📦 All Products")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        # Search + filter row
        bar = QHBoxLayout()
        self._prod_search = QLineEdit()
        self._prod_search.setPlaceholderText("🔍 Search products...")
        self._prod_search.textChanged.connect(self._filter_products_table)
        bar.addWidget(self._prod_search)

        self._prod_cat_filter = QComboBox()
        self._prod_cat_filter.addItem("All Sources")
        self._prod_cat_filter.addItems(["reddit", "amazon", "aliexpress", "csv"])
        self._prod_cat_filter.currentTextChanged.connect(self._filter_products_table)
        bar.addWidget(self._prod_cat_filter)

        export_btn = QPushButton("📤 Export CSV")
        export_btn.clicked.connect(self._export_csv)
        bar.addWidget(export_btn)

        clear_btn = QPushButton("🗑 Clear All")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear_products)
        bar.addWidget(clear_btn)
        layout.addLayout(bar)

        # Table
        self._prod_table = QTableWidget()
        self._prod_table.setColumnCount(8)
        self._prod_table.setHorizontalHeaderLabels([
            "Title", "Category", "Price (PKR)", "Rating",
            "Reviews", "Sold/Engagement", "Source", "Trend Score"
        ])
        self._prod_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._prod_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._prod_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._prod_table.setAlternatingRowColors(True)
        layout.addWidget(self._prod_table)

        self._prod_count_lbl = QLabel("0 products")
        self._prod_count_lbl.setStyleSheet(
            f"color: {self.theme['text_light']}; font-size: 13px;"
        )
        layout.addWidget(self._prod_count_lbl)
        return page

    def _load_products_table(self, products=None):
        if products is None:
            products = self.db.get_all_products()
        self._prod_table.setRowCount(0)
        for row_data in products:
            row = self._prod_table.rowCount()
            self._prod_table.insertRow(row)
            vals = [
                row_data.get("title", ""),
                row_data.get("category", ""),
                f"{row_data.get('price', 0):.0f}",
                f"{row_data.get('rating', 0):.1f}",
                str(row_data.get("reviews", 0)),
                str(row_data.get("sold_count", 0)),
                row_data.get("source", ""),
                f"{row_data.get('trend_score', 0):.1f}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._prod_table.setItem(row, col, item)

        self._prod_count_lbl.setText(f"{len(products)} products")

    def _filter_products_table(self):
        query  = self._prod_search.text().strip()
        source = self._prod_cat_filter.currentText()

        if query:
            products = self.db.search_products(query)
        else:
            products = self.db.get_all_products()

        if source != "All Sources":
            products = [p for p in products if p.get("source") == source]

        self._load_products_table(products)

    def _export_csv(self):
        products = self.db.get_all_products()
        if not products:
            QMessageBox.information(self, "Empty", "No products to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "products.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=products[0].keys())
            writer.writeheader()
            writer.writerows(products)
        QMessageBox.information(self, "Exported", f"Saved to {path}")

    def _clear_products(self):
        reply = QMessageBox.question(
            self, "Confirm", "Delete all products from the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_all_products()
            self._load_products_table([])
            self._refresh_dashboard_stats()

    # ── 4. AI Analysis ───────────────────────────────────────────────── #
    def _build_analysis_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel("🤖 AI Analysis")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        # Controls card
        ctrl = QFrame()
        ctrl.setObjectName("card")
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(14)

        row = QHBoxLayout()
        m_lbl = QLabel("Model:")
        m_lbl.setStyleSheet(f"color: {self.theme['text']}; font-weight: 500;")
        row.addWidget(m_lbl)
        self._ai_model = QComboBox()
        self._ai_model.addItems(["qwen2.5:7b", "mistral:7b",
                                  "llama3.1:8b", "gemma2:9b"])
        self._ai_model.setFixedWidth(180)
        row.addWidget(self._ai_model)
        row.addStretch()
        cl.addLayout(row)

        self._analyse_btn = QPushButton("🤖 Analyse All Products with AI")
        self._analyse_btn.clicked.connect(self._start_analysis)
        cl.addWidget(self._analyse_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._analyse_progress = QProgressBar()
        self._analyse_progress.setRange(0, 100)
        cl.addWidget(self._analyse_progress)

        self._analyse_status = QLabel("Ready")
        self._analyse_status.setStyleSheet(
            f"color: {self.theme['text_light']}; font-size: 13px;"
        )
        cl.addWidget(self._analyse_status)
        layout.addWidget(ctrl)

        # Results table — Top 10 Recommendations
        top_lbl = QLabel("🏆 Top 10 Recommended Products for Pakistan")
        top_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {self.theme['text']};"
        )
        layout.addWidget(top_lbl)

        self._top_table = QTableWidget()
        self._top_table.setColumnCount(6)
        self._top_table.setHorizontalHeaderLabels([
            "Rank", "Product Title", "Demand", "Competition",
            "Est. Profit (PKR)", "AI Verdict"
        ])
        self._top_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._top_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        self._top_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        layout.addWidget(self._top_table)
        return page

    def _start_analysis(self):
        products_raw = self.db.get_all_products()
        if not products_raw:
            QMessageBox.warning(self, "No Data",
                                "Scrape some products first.")
            return

        # Rebuild Product objects from dicts
        products = []
        for d in products_raw:
            p = Product()
            for k, v in d.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            products.append(p)

        model = self._ai_model.currentText()
        self._analyse_btn.setEnabled(False)
        self._analyse_btn.setText("Analysing...")
        self._analyse_progress.setValue(0)
        self._analyse_status.setText("Starting AI analysis...")

        self._analysis_thread = QThread()
        self._analysis_worker = AnalysisWorker(products, model)
        self._analysis_worker.moveToThread(self._analysis_thread)

        self._analysis_thread.started.connect(self._analysis_worker.run)
        self._analysis_worker.progress.connect(
            lambda cur, tot: (
                self._analyse_progress.setValue(int(cur / max(tot, 1) * 100)),
                self._analyse_status.setText(f"Analysed {cur}/{tot} products")
            )
        )
        self._analysis_worker.finished.connect(self._on_analysis_done)
        self._analysis_worker.error.connect(
            lambda e: QMessageBox.critical(self, "Error", e)
        )
        self._analysis_worker.finished.connect(self._analysis_thread.quit)
        self._analysis_thread.start()
        self._threads.append(self._analysis_thread)

    def _on_analysis_done(self, products: list):
        self._analyse_btn.setEnabled(True)
        self._analyse_btn.setText("🤖 Analyse All Products with AI")
        self._analyse_progress.setValue(100)
        self._analyse_status.setText(
            f"✅ Done! Analysed {len(products)} products."
        )

        # Save updated scores back to DB
        for p in products:
            if hasattr(p, 'id') and p.id:
                self.db.update_product_scores(p.id, {
                    "demand_score":      p.demand_score,
                    "competition_score": p.competition_score,
                    "profit_estimate":   p.profit_estimate,
                    "trend_score":       p.trend_score,
                    "ai_verdict":        p.ai_verdict,
                })

        # Show Top 10
        rec_agent = RecommendationAgent()
        top10 = rec_agent.get_top(products, n=10)
        self._populate_top_table(top10)
        self._refresh_dashboard_stats()

    def _populate_top_table(self, products: list):
        self._top_table.setRowCount(0)
        for rank, p in enumerate(products, 1):
            row = self._top_table.rowCount()
            self._top_table.insertRow(row)
            vals = [
                f"#{rank}",
                p.title,
                f"{p.demand_score:.0f}/100",
                f"{p.competition_score:.0f}/100",
                f"PKR {p.profit_estimate:,.0f}",
                p.ai_verdict[:120] + ("…" if len(p.ai_verdict) > 120 else ""),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft |
                                          Qt.AlignmentFlag.AlignVCenter)
                self._top_table.setItem(row, col, item)
            # Colour rank column
            rank_item = self._top_table.item(row, 0)
            if rank <= 3:
                rank_item.setForeground(QColor("#f59e0b"))

    # ── 5. Trends ─────────────────────────────────────────────────────── #
    def _build_trends_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel("📈 Google Trends (Pakistan)")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self._trend_kw = QLineEdit()
        self._trend_kw.setPlaceholderText("Enter keyword e.g. 'wireless earbuds'")
        row.addWidget(self._trend_kw)
        fetch_btn = QPushButton("🔍 Fetch Trends")
        fetch_btn.clicked.connect(self._fetch_trends)
        row.addWidget(fetch_btn)
        cl.addLayout(row)

        self._trend_result = QTextEdit()
        self._trend_result.setReadOnly(True)
        self._trend_result.setMinimumHeight(200)
        self._trend_result.setPlaceholderText(
            "Trend scores and related keywords will appear here..."
        )
        cl.addWidget(self._trend_result)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _fetch_trends(self):
        kw = self._trend_kw.text().strip()
        if not kw:
            return
        self._trend_result.setText("Fetching Google Trends data for Pakistan…")
        try:
            agent = TrendAgent(geo="PK")
            scores = agent.get_scores([kw])
            related = agent.get_related_keywords(kw)
            score = scores.get(kw, 0.0)
            text = (f"Keyword: {kw}\n"
                    f"Trend Score (PK, last 3 months): {score:.1f}/100\n\n"
                    f"Related / Rising Keywords:\n")
            for r in related[:10]:
                text += f"  • {r}\n"
            self._trend_result.setText(text)
        except Exception as e:
            self._trend_result.setText(f"Error: {e}\n\nMake sure pytrends is installed:\n"
                                       f"  pip install pytrends")

    # ── 6. Reports ────────────────────────────────────────────────────── #
    def _build_reports_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        title = QLabel("📄 Export Reports")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        # Export CSV card
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(14)

        info = QLabel("Export all products and analysis results to CSV.\n"
                      "Open in Excel or Google Sheets for further analysis.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {self.theme['text_light']}; font-size: 14px;")
        cl.addWidget(info)

        btn_row = QHBoxLayout()
        csv_btn = QPushButton("📤 Export All Products (CSV)")
        csv_btn.clicked.connect(self._export_csv_from_reports)
        btn_row.addWidget(csv_btn)

        top10_btn = QPushButton("🏆 Export Top 10 (CSV)")
        top10_btn.clicked.connect(self._export_top10_csv)
        btn_row.addWidget(top10_btn)
        btn_row.addStretch()
        cl.addLayout(btn_row)
        layout.addWidget(card)
        layout.addStretch()
        return page

    def _export_csv_from_reports(self):
        self._navigate("products")
        self._export_csv()

    def _export_top10_csv(self):
        products_raw = self.db.get_all_products()
        if not products_raw:
            QMessageBox.information(self, "No Data", "No products to export.")
            return
        # Filter only analysed products
        analysed = [p for p in products_raw if p.get("demand_score", 0) > 0]
        if not analysed:
            QMessageBox.information(self, "No Analysed Products",
                                    "Run AI Analysis first to get top products.")
            return
        top10 = sorted(analysed, key=lambda x: x.get("demand_score", 0),
                       reverse=True)[:10]
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Top 10 CSV", "top10_products.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=top10[0].keys())
            writer.writeheader()
            writer.writerows(top10)
        QMessageBox.information(self, "Exported", f"Top 10 saved to {path}")

    # ── 7. Settings ───────────────────────────────────────────────────── #
    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title = QLabel("⚙️ Settings")
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {self.theme['text']};"
        )
        layout.addWidget(title)

        # Ollama card
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(14)

        cl.addWidget(QLabel("🤖 Ollama Configuration"))
        host_row = QHBoxLayout()
        host_lbl = QLabel("Host:")
        host_lbl.setStyleSheet(f"color: {self.theme['text']};")
        host_row.addWidget(host_lbl)
        self._settings_host = QLineEdit("http://localhost:11434")
        host_row.addWidget(self._settings_host)
        cl.addLayout(host_row)

        test_btn = QPushButton("🔌 Test Ollama Connection")
        test_btn.setObjectName("secondary")
        test_btn.clicked.connect(self._test_ollama)
        cl.addWidget(test_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(card)

        # Danger zone
        danger = QFrame()
        danger.setObjectName("card")
        dl = QVBoxLayout(danger)
        dl.setContentsMargins(24, 24, 24, 24)
        danger_title = QLabel("⚠️ Danger Zone")
        danger_title.setStyleSheet(f"color: {self.theme['danger']}; font-weight: 600;")
        dl.addWidget(danger_title)
        clear_btn = QPushButton("🗑 Clear All Products from Database")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear_products)
        dl.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(danger)
        layout.addStretch()
        return page

    def _test_ollama(self):
        import requests as req
        host = self._settings_host.text().strip()
        try:
            r = req.get(f"{host}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                QMessageBox.information(
                    self, "Connected",
                    f"✅ Ollama is running!\n\nAvailable models:\n" +
                    "\n".join(models) if models else "No models found."
                )
            else:
                QMessageBox.warning(self, "Error", f"HTTP {r.status_code}")
        except Exception as e:
            QMessageBox.warning(
                self, "Not Running",
                f"Could not connect to Ollama.\n\nError: {e}\n\n"
                f"Make sure Ollama is running:\n  ollama serve"
            )

    # ------------------------------------------------------------------ #
    # Theme update                                                         #
    # ------------------------------------------------------------------ #
    def update_theme(self, theme: dict):
        self.theme = theme
        self.sidebar.setStyleSheet(
            f"background-color: {theme['sidebar']}; "
            f"border-right: 1px solid {theme['border']};"
        )
        # Refresh nav buttons
        current = None
        for i, (pid, _, _) in enumerate(self.NAV_ITEMS):
            if self.stack.currentWidget() == self.pages[pid]:
                current = pid
        for pid, btn in self.nav_buttons.items():
            btn.setStyleSheet(self._nav_style(active=(pid == current)))