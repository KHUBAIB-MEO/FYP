"""
Dynamic Theme Styles - QSS Stylesheet for PyQt6
Generates styles based on current theme (Light/Dark)
"""
from shared.settings import get_theme

def generate_stylesheet(theme=None):
    """Generate QSS stylesheet from theme dictionary"""
    if theme is None:
        theme = get_theme()

    t = theme  # shorthand

    return f"""
/* ========== GLOBAL ========== */
QMainWindow, QWidget {{
    font-family: 'Segoe UI', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 14px;
    color: {t['text']};
    background-color: {t['bg']};
}}

QMainWindow::separator {{
    background-color: {t['border']};
    width: 2px;
}}

/* ========== SIDEBAR ========== */
QFrame#sidebar {{
    background-color: {t['sidebar']};
    border-right: 1px solid {t['border']};
    min-width: 220px;
    max-width: 220px;
}}

QPushButton#nav_button {{
    background-color: transparent;
    color: {t['nav_inactive_text']};
    border: none;
    padding: 14px 20px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-radius: 8px;
    margin: 4px 12px;
}}

QPushButton#nav_button:hover {{
    background-color: {t['nav_hover']};
    color: {t['text_secondary']};
}}

QPushButton#nav_button:checked, QPushButton#nav_button:pressed {{
    background-color: {t['nav_active_bg']};
    color: {t['nav_active_text']};
    font-weight: 600;
}}

/* ========== CARDS ========== */
QFrame#card {{
    background-color: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 12px;
    padding: 16px;
}}

QFrame#card:hover {{
    border-color: {t['primary']};
    background-color: {t['hover']};
}}

/* ========== BUTTONS ========== */
QPushButton {{
    background-color: {t['primary']};
    color: white;
    border: none;
    padding: 10px 24px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: {t['primary_dark']};
}}

QPushButton:pressed {{
    background-color: {t['primary_dark']};
}}

QPushButton#secondary {{
    background-color: {t['hover']};
    color: {t['text_secondary']};
    border: 1px solid {t['border']};
}}

QPushButton#secondary:hover {{
    background-color: {t['border']};
    color: {t['text']};
}}

QPushButton#danger {{
    background-color: {t['danger']};
}}

QPushButton#danger:hover {{
    background-color: #dc2626;
}}

QPushButton#success {{
    background-color: {t['success']};
}}

QPushButton#success:hover {{
    background-color: #059669;
}}

QPushButton#icon_button {{
    background-color: transparent;
    color: {t['text_light']};
    border: none;
    padding: 8px;
    border-radius: 6px;
    font-size: 16px;
}}

QPushButton#icon_button:hover {{
    background-color: {t['hover']};
    color: {t['text']};
}}

QPushButton#theme_toggle {{
    background-color: {t['hover']};
    color: {t['text_light']};
    border: 1px solid {t['border']};
    padding: 8px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#theme_toggle:hover {{
    background-color: {t['border']};
    color: {t['text']};
}}

/* ========== INPUTS ========== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {t['input_bg']};
    border: 1px solid {t['input_border']};
    border-radius: 8px;
    padding: 10px 14px;
    color: {t['text']};
    selection-background-color: {t['selection_bg']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {t['primary']};
    background-color: {t['input_bg']};
}}

QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
    color: {t['placeholder']};
}}

/* ========== COMBO BOX ========== */
QComboBox {{
    background-color: {t['input_bg']};
    border: 1px solid {t['input_border']};
    border-radius: 8px;
    padding: 10px 14px;
    min-width: 160px;
    color: {t['text']};
}}

QComboBox:hover {{
    border-color: {t['primary']};
}}

QComboBox:focus {{
    border-color: {t['primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {t['text_light']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {t['menu_bg']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    selection-background-color: {t['nav_active_bg']};
    selection-color: {t['primary']};
    padding: 4px;
    color: {t['text']};
}}

QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: 6px;
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {t['nav_active_bg']};
    color: {t['primary']};
}}

/* ========== LIST WIDGET ========== */
QListWidget {{
    background-color: {t['input_bg']};
    border: 1px solid {t['input_border']};
    border-radius: 8px;
    padding: 8px;
    outline: none;
    color: {t['text']};
}}

QListWidget::item {{
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 0px;
    color: {t['text_secondary']};
}}

QListWidget::item:hover {{
    background-color: {t['hover']};
}}

QListWidget::item:selected {{
    background-color: {t['nav_active_bg']};
    color: {t['primary']};
    font-weight: 600;
}}

/* ========== CHECK BOX ========== */
QCheckBox {{
    spacing: 10px;
    color: {t['text_secondary']};
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid {t['border']};
    background-color: {t['input_bg']};
}}

QCheckBox::indicator:hover {{
    border-color: {t['primary']};
}}

QCheckBox::indicator:checked {{
    background-color: {t['primary']};
    border-color: {t['primary']};
}}

/* ========== SCROLL BARS ========== */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {t['scrollbar']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {t['scrollbar_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {t['scrollbar']};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {t['scrollbar_hover']};
}}

/* ========== GROUP BOX ========== */
QGroupBox {{
    font-weight: 600;
    font-size: 13px;
    color: {t['text_secondary']};
    border: 1px solid {t['border']};
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 16px;
    padding: 16px;
    background-color: {t['card']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {t['group_title']};
}}

/* ========== PROGRESS BAR ========== */
QProgressBar {{
    border: none;
    border-radius: 6px;
    background-color: {t['border']};
    text-align: center;
    color: {t['text_secondary']};
    font-weight: 600;
    font-size: 11px;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {t['primary']};
    border-radius: 6px;
}}

/* ========== LABELS ========== */
QLabel#heading {{
    font-size: 24px;
    font-weight: 700;
    color: {t['text']};
}}

QLabel#subheading {{
    font-size: 16px;
    font-weight: 600;
    color: {t['text_secondary']};
}}

QLabel#caption {{
    font-size: 12px;
    color: {t['text_light']};
}}

QLabel#stat_number {{
    font-size: 32px;
    font-weight: 700;
    color: {t['primary']};
}}

QLabel#stat_label {{
    font-size: 13px;
    color: {t['text_light']};
    font-weight: 500;
}}

QLabel#hint {{
    font-size: 11px;
    color: {t['hint_text']};
    font-style: italic;
}}

/* ========== MENU ========== */
QMenu {{
    background-color: {t['menu_bg']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 8px;
    color: {t['text']};
}}

QMenu::item {{
    padding: 10px 20px;
    border-radius: 6px;
    color: {t['text_secondary']};
}}

QMenu::item:selected {{
    background-color: {t['nav_active_bg']};
    color: {t['primary']};
}}

QMenu::separator {{
    height: 1px;
    background-color: {t['separator']};
    margin: 6px 12px;
}}

/* ========== SPLITTER ========== */
QSplitter::handle {{
    background-color: {t['border']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* ========== DIALOG ========== */
QDialog {{
    background-color: {t['bg']};
}}

/* ========== MESSAGE BOX ========== */
QMessageBox {{
    background-color: {t['bg']};
}}

QMessageBox QLabel {{
    color: {t['text']};
}}

QMessageBox QPushButton {{
    min-width: 80px;
    padding: 8px 16px;
}}

/* ========== FILE DIALOG ========== */
QFileDialog {{
    background-color: {t['bg']};
}}

QFileDialog QLabel {{
    color: {t['text']};
}}

/* ========== TOOLTIP ========== */
QToolTip {{
    background-color: {t['card']};
    color: {t['text']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ========== TAB BAR ========== */
QTabBar::tab {{
    background-color: {t['hover']};
    color: {t['text_light']};
    padding: 10px 20px;
    border-radius: 8px 8px 0 0;
    margin-right: 4px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {t['primary']};
    color: white;
}}

QTabBar::tab:hover:!selected {{
    background-color: {t['border']};
    color: {t['text']};
}}

/* ========== TABLE ========== */
QTableWidget {{
    background-color: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    gridline-color: {t['border']};
    color: {t['text']};
}}

QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid {t['border']};
}}

QTableWidget::item:selected {{
    background-color: {t['nav_active_bg']};
    color: {t['primary']};
}}

QHeaderView::section {{
    background-color: {t['hover']};
    color: {t['text_secondary']};
    padding: 10px 14px;
    border: none;
    border-bottom: 2px solid {t['border']};
    font-weight: 600;
}}

/* ========== SPIN BOX ========== */
QSpinBox, QDoubleSpinBox {{
    background-color: {t['input_bg']};
    border: 1px solid {t['input_border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {t['text']};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {t['primary']};
}}

/* ========== DATE/TIME EDIT ========== */
QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {t['input_bg']};
    border: 1px solid {t['input_border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {t['text']};
}}

QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {{
    border-color: {t['primary']};
}}

/* ========== RADIO BUTTON ========== */
QRadioButton {{
    spacing: 8px;
    color: {t['text_secondary']};
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid {t['border']};
    background-color: {t['input_bg']};
}}

QRadioButton::indicator:checked {{
    background-color: {t['primary']};
    border-color: {t['primary']};
}}
"""

# Legacy constant for backwards compatibility
MAIN_STYLE = generate_stylesheet()
