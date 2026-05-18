"""
Content Scripting Agent Page
Professional content generation with model selection, tone control, and export
"""
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from shared.settings import CONTENT_TONES, CONTENT_TYPES, CONTENT_LENGTHS, get_theme
from contentscripting.content_engine import ContentEngine
from shared.ollama_client import OllamaClient


class ContentCard(QFrame):
    """Generated content card with long-press actions"""
    clicked = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)
    editRequested = pyqtSignal(int)
    regenerateRequested = pyqtSignal(int)
    copyRequested = pyqtSignal(int)
    exportRequested = pyqtSignal(int)

    def __init__(self, content_data, index, theme, parent=None):
        super().__init__(parent)
        self.content_data = content_data
        self.index = index
        self.theme = theme
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._setup_ui()

        self.press_timer = QTimer(self)
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self._show_context_menu)
        self.pressed = False

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        title_text = self.content_data.get("title", "Untitled")
        self.title_label = QLabel(f"📝 <b>{title_text}</b>")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"font-size: 15px; color: {self.theme['text']};")
        layout.addWidget(self.title_label)

        # Metadata row
        meta_layout = QHBoxLayout()
        content_type = self.content_data.get("content_type", "")
        tone = self.content_data.get("tone", "")
        length = self.content_data.get("length", "")

        meta_text = f"<span style='color:{self.theme['primary']};font-weight:600;'>{content_type}</span> • {tone} • {length}"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet(f"font-size: 12px; color: {self.theme['text_light']};")
        meta_layout.addWidget(meta_label)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # Content preview
        content = self.content_data.get("content", "")
        preview = content[:250] + "..." if len(content) > 250 else content
        self.content_label = QLabel(preview)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(f"font-size: 13px; color: {self.theme['text_secondary']}; line-height: 1.5;")
        layout.addWidget(self.content_label)

        # Hint
        hint = QLabel("Long press for options • Click to preview")
        hint.setStyleSheet(f"font-size: 11px; color: {self.theme['hint_text']}; font-style: italic;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.setLayout(layout)
        self.setMinimumHeight(160)

    def update_theme(self, theme):
        self.theme = theme
        self.title_label.setStyleSheet(f"font-size: 15px; color: {theme['text']};")
        self.content_label.setStyleSheet(f"font-size: 13px; color: {theme['text_secondary']}; line-height: 1.5;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed = True
            self.press_timer.start(800)
            self.setStyleSheet(f"background-color: {self.theme['hover']}; border: 2px solid {self.theme['primary']};")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.press_timer.stop()
        self.pressed = False
        self.setStyleSheet("")
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)

    def _show_context_menu(self):
        self.setStyleSheet("")
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

        edit_action = QAction("✏️  Edit", self)
        edit_action.triggered.connect(lambda: self.editRequested.emit(self.index))
        menu.addAction(edit_action)

        copy_action = QAction("📋  Copy to Clipboard", self)
        copy_action.triggered.connect(lambda: self.copyRequested.emit(self.index))
        menu.addAction(copy_action)

        export_action = QAction("💾  Export as TXT", self)
        export_action.triggered.connect(lambda: self.exportRequested.emit(self.index))
        menu.addAction(export_action)

        menu.addSeparator()

        regen_action = QAction("🔄  Regenerate", self)
        regen_action.triggered.connect(lambda: self.regenerateRequested.emit(self.index))
        menu.addAction(regen_action)

        delete_action = QAction("🗑  Delete", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self.index))
        menu.addAction(delete_action)

        menu.exec(self.mapToGlobal(QPoint(self.width()//2, self.height()//2)))

    def update_data(self, content_data):
        self.content_data = content_data
        self.title_label.setText(f"📝 <b>{content_data.get('title', 'Untitled')}</b>")
        content = content_data.get("content", "")
        preview = content[:250] + "..." if len(content) > 250 else content
        self.content_label.setText(preview)


class ContentEditDialog(QDialog):
    """Dialog to edit generated content"""

    def __init__(self, content_data, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("✏️ Edit Content")
        self.setMinimumSize(750, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title_label = QLabel("Title")
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {theme['text_secondary']};")
        layout.addWidget(title_label)

        self.title_edit = QLineEdit(content_data.get("title", ""))
        self.title_edit.setStyleSheet(f"font-size: 14px; color: {theme['text']};")
        layout.addWidget(self.title_edit)

        # Content
        content_label = QLabel("Content")
        content_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {theme['text_secondary']};")
        layout.addWidget(content_label)

        self.content_edit = QPlainTextEdit(content_data.get("content", ""))
        self.content_edit.setStyleSheet(f"font-size: 14px; line-height: 1.6; color: {theme['text']};")
        self.content_edit.setMinimumHeight(350)
        layout.addWidget(self.content_edit)

        # Buttons
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
        return {
            "title": self.title_edit.text().strip(),
            "content": self.content_edit.toPlainText().strip()
        }


class ContentPreviewDialog(QDialog):
    """Dialog to preview full content"""

    def __init__(self, content_data, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Content Preview")
        self.setMinimumSize(700, 550)

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(f"<b>Title:</b> {content_data.get('title', 'Untitled')}")
        title_label.setStyleSheet(f"font-size: 16px; color: {theme['text']}; padding-bottom: 12px;")
        layout.addWidget(title_label)

        # Content
        content = content_data.get("content", "")
        content_edit = QPlainTextEdit(content)
        content_edit.setReadOnly(True)
        content_edit.setStyleSheet(f"font-size: 14px; line-height: 1.6; color: {theme['text']};")
        layout.addWidget(content_edit)

        # Copy button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        copy_btn = QPushButton("📋 Copy to Clipboard")
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(content))
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "Content copied to clipboard!")


class ContentPage(QWidget):
    """Main Content Scripting Agent page"""

    backToDashboard = pyqtSignal()

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.is_dark = theme == get_theme()  # Check if dark

        # Initialize engine
        self.content_engine = ContentEngine()
        self.ollama_client = OllamaClient()
        self.current_model = "qwen2.5:7b"
        self.generated_contents = []

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # Main content area
        content_area = self._create_content_area()
        main_layout.addWidget(content_area, stretch=1)

    def _create_sidebar(self):
        """Left sidebar with back button and nav"""
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
        title = QLabel("📝  Content Agent")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text']}; padding: 8px 0 16px 0;")
        layout.addWidget(title)

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

        layout.addStretch()

        return sidebar

    def _create_content_area(self):
        """Main content generation area"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        # Header
        header = QLabel("📝 Content Scripting Agent")
        header.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {self.theme['text']};")
        layout.addWidget(header)

        subheader = QLabel("Generate blogs, social posts, ad copy, scripts, and more with AI")
        subheader.setStyleSheet(f"font-size: 14px; color: {self.theme['text_light']}; margin-bottom: 8px;")
        layout.addWidget(subheader)

        # Settings row
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)

        # Model selection
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

        # Content type
        type_group = QGroupBox("📄 Content Type")
        type_layout = QVBoxLayout(type_group)
        self.type_combo = QComboBox()
        self.type_combo.addItems(CONTENT_TYPES)
        self.type_combo.setMinimumWidth(180)
        type_layout.addWidget(self.type_combo)
        settings_layout.addWidget(type_group)

        # Tone
        tone_group = QGroupBox("🎭 Tone")
        tone_layout = QVBoxLayout(tone_group)
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(CONTENT_TONES)
        self.tone_combo.setMinimumWidth(150)
        tone_layout.addWidget(self.tone_combo)
        settings_layout.addWidget(tone_group)

        # Length
        length_group = QGroupBox("📏 Length")
        length_layout = QVBoxLayout(length_group)
        self.length_combo = QComboBox()
        self.length_combo.addItems(list(CONTENT_LENGTHS.keys()))
        self.length_combo.setMinimumWidth(150)
        length_layout.addWidget(self.length_combo)
        settings_layout.addWidget(length_group)

        settings_layout.addStretch()
        layout.addLayout(settings_layout)

        # Topic / Prompt
        topic_group = QGroupBox("📝 Topic / Prompt")
        topic_layout = QVBoxLayout(topic_group)

        self.topic_input = QPlainTextEdit()
        self.topic_input.setPlaceholderText(
            "Describe what content you want...\n\n"
            "Example: Write a blog post about the benefits of AI in healthcare for small clinics. "
            "Focus on cost savings and patient experience improvements."
        )
        self.topic_input.setMinimumHeight(100)
        topic_layout.addWidget(self.topic_input)

        layout.addWidget(topic_group)

        # Keywords
        keywords_group = QGroupBox("🔑 SEO Keywords (Optional)")
        keywords_layout = QVBoxLayout(keywords_group)

        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("Enter keywords separated by commas, e.g., AI healthcare, digital transformation, patient care")
        keywords_layout.addWidget(self.keywords_input)

        layout.addWidget(keywords_group)

        # Additional instructions
        context_group = QGroupBox("💡 Additional Instructions (Optional)")
        context_layout = QVBoxLayout(context_group)

        self.context_input = QPlainTextEdit()
        self.context_input.setPlaceholderText(
            "Any specific instructions...\n"
            "Example: Include a call-to-action at the end. Mention our company name 'TechMed Solutions'."
        )
        self.context_input.setMaximumHeight(80)
        context_layout.addWidget(self.context_input)

        layout.addWidget(context_group)

        # Generate button
        gen_layout = QHBoxLayout()
        self.generate_btn = QPushButton("✨ Generate Content")
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
        self.generate_btn.clicked.connect(self._generate_content)
        gen_layout.addWidget(self.generate_btn)
        layout.addLayout(gen_layout)

        # Generated content section
        gen_header_layout = QHBoxLayout()
        gen_header = QLabel("Generated Content")
        gen_header.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme['text']};")
        gen_header_layout.addWidget(gen_header)

        self.gen_count = QLabel("0 items")
        self.gen_count.setStyleSheet(f"color: {self.theme['text_light']}; font-size: 13px;")
        gen_header_layout.addWidget(self.gen_count)
        gen_header_layout.addStretch()

        # Export all button
        self.export_all_btn = QPushButton("💾 Export All")
        self.export_all_btn.setObjectName("secondary")
        self.export_all_btn.setEnabled(False)
        self.export_all_btn.clicked.connect(self._export_all)
        gen_header_layout.addWidget(self.export_all_btn)

        layout.addLayout(gen_header_layout)

        # Generated content scroll area
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

        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _load_models(self):
        """Load available Ollama models"""
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
        self.content_engine.set_model(model_name)

    def _generate_content(self):
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "Missing Topic", "Please enter what content you want to generate.")
            return

        content_type = self.type_combo.currentText()
        tone = self.tone_combo.currentText()
        length = self.length_combo.currentText()
        keywords = self.keywords_input.text().strip()
        context = self.context_input.toPlainText().strip()

        # Show loading overlay
        self._show_loading("AI is writing your content...")

        self.gen_thread = ContentGenerationThread(
            self.content_engine, topic, content_type, tone, length, context, keywords
        )
        self.gen_thread.finished.connect(self._on_generation_done)
        self.gen_thread.error.connect(self._on_generation_error)
        self.gen_thread.start()

    def _show_loading(self, msg):
        """Show simple loading indicator"""
        self.generate_btn.setText("⏳ Generating...")
        self.generate_btn.setEnabled(False)
        QApplication.processEvents()

    def _hide_loading(self):
        self.generate_btn.setText("✨ Generate Content")
        self.generate_btn.setEnabled(True)

    def _on_generation_done(self, result):
        self._hide_loading()
        self.generated_contents.append(result)
        self._add_content_card(result, len(self.generated_contents) - 1)
        self._update_gen_count()

        QMessageBox.information(self, "Success", 
            f"Content generated!\n\nTitle: {result['title']}")

    def _on_generation_error(self, error_msg):
        self._hide_loading()
        QMessageBox.critical(self, "Generation Failed", error_msg)

    def _add_content_card(self, content_data, index):
        card = ContentCard(content_data, index, self.theme)
        card.clicked.connect(self._on_content_select)
        card.deleteRequested.connect(self._on_content_delete)
        card.editRequested.connect(self._on_content_edit)
        card.regenerateRequested.connect(self._on_content_regenerate)
        card.copyRequested.connect(self._on_content_copy)
        card.exportRequested.connect(self._on_content_export)

        self.gen_layout.insertWidget(self.gen_layout.count() - 1, card)
        self.export_all_btn.setEnabled(True)

    def _update_gen_count(self):
        self.gen_count.setText(f"{len(self.generated_contents)} items")
        self.export_all_btn.setEnabled(len(self.generated_contents) > 0)

    def _on_content_select(self, index):
        if 0 <= index < len(self.generated_contents):
            data = self.generated_contents[index]
            dialog = ContentPreviewDialog(data, self.theme, self)
            dialog.exec()

    def _on_content_delete(self, index):
        if 0 <= index < len(self.generated_contents):
            reply = QMessageBox.question(self, "Confirm Delete", 
                "Delete this generated content?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.generated_contents.pop(index)
                self._refresh_content_cards()
                self._update_gen_count()

    def _on_content_edit(self, index):
        if 0 <= index < len(self.generated_contents):
            data = self.generated_contents[index]
            dialog = ContentEditDialog(data, self.theme, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                edited = dialog.get_edited_data()
                self.generated_contents[index]["title"] = edited["title"]
                self.generated_contents[index]["content"] = edited["content"]
                self._refresh_content_cards()
                QMessageBox.information(self, "Saved", "Content updated successfully!")

    def _on_content_regenerate(self, index):
        if 0 <= index < len(self.generated_contents):
            original = self.generated_contents[index]
            topic = original.get("topic", "")
            content_type = original.get("content_type", self.type_combo.currentText())
            tone = original.get("tone", self.tone_combo.currentText())
            length = original.get("length", self.length_combo.currentText())
            keywords = original.get("keywords", "")
            context = self.context_input.toPlainText().strip()

            self._show_loading("Regenerating content...")

            self.regen_thread = ContentRegenerationThread(
                self.content_engine, original, topic, content_type, tone, length, context, keywords
            )
            self.regen_thread.finished.connect(
                lambda result, idx=index: self._on_regen_done(result, idx)
            )
            self.regen_thread.error.connect(self._on_generation_error)
            self.regen_thread.start()

    def _on_regen_done(self, result, index):
        self._hide_loading()
        self.generated_contents[index] = result
        self._refresh_content_cards()
        QMessageBox.information(self, "Regenerated", 
            f"Content regenerated!\n\nNew Title: {result['title']}")

    def _on_content_copy(self, index):
        if 0 <= index < len(self.generated_contents):
            content = self.generated_contents[index].get("content", "")
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            QMessageBox.information(self, "Copied", "Content copied to clipboard!")

    def _on_content_export(self, index):
        if 0 <= index < len(self.generated_contents):
            data = self.generated_contents[index]
            self._export_single(data)

    def _export_single(self, data):
        """Export single content to TXT file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Content", 
            f"{data.get('title', 'content').replace(' ', '_')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {data.get('title', 'Untitled')}\n")
                    f.write(f"Type: {data.get('content_type', '')}\n")
                    f.write(f"Tone: {data.get('tone', '')}\n")
                    f.write(f"Length: {data.get('length', '')}\n")
                    f.write(f"Topic: {data.get('topic', '')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(data.get("content", ""))
                QMessageBox.information(self, "Exported", f"Saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

    def _export_all(self):
        """Export all generated content"""
        if not self.generated_contents:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export All Content",
            "all_content.txt",
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for i, data in enumerate(self.generated_contents, 1):
                        f.write(f"\n{'='*60}\n")
                        f.write(f"CONTENT #{i}\n")
                        f.write(f"{'='*60}\n\n")
                        f.write(f"Title: {data.get('title', 'Untitled')}\n")
                        f.write(f"Type: {data.get('content_type', '')}\n")
                        f.write(f"Tone: {data.get('tone', '')}\n")
                        f.write(f"Length: {data.get('length', '')}\n")
                        f.write(f"Topic: {data.get('topic', '')}\n")
                        f.write("-" * 50 + "\n\n")
                        f.write(data.get("content", ""))
                        f.write("\n\n")
                QMessageBox.information(self, "Exported", f"All content saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

    def _refresh_content_cards(self):
        while self.gen_layout.count() > 1:
            item = self.gen_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, content in enumerate(self.generated_contents):
            self._add_content_card(content, i)

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

    def update_theme(self, theme):
        self.theme = theme

        # Sidebar
        sidebar = self.findChild(QFrame, "sidebar")
        if sidebar:
            sidebar.setStyleSheet(
                f"background-color: {theme['sidebar']}; "
                f"border-right: 1px solid {theme['border']};"
            )

        # Inline labels
        self.gen_count.setStyleSheet(f"color: {theme['text_light']}; font-size: 13px;")

        # Refresh cards
        self._refresh_content_cards()


# === WORKER THREADS ===

class ContentGenerationThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, engine, topic, content_type, tone, length, context, keywords):
        super().__init__()
        self.engine = engine
        self.topic = topic
        self.content_type = content_type
        self.tone = tone
        self.length = length
        self.context = context
        self.keywords = keywords

    def run(self):
        try:
            result = self.engine.generate_content(
                self.topic, self.content_type, self.tone, self.length,
                self.context, self.keywords
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ContentRegenerationThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, engine, original, topic, content_type, tone, length, context, keywords):
        super().__init__()
        self.engine = engine
        self.original = original
        self.topic = topic
        self.content_type = content_type
        self.tone = tone
        self.length = length
        self.context = context
        self.keywords = keywords

    def run(self):
        try:
            result = self.engine.regenerate_content(
                self.original, self.topic, self.content_type, self.tone,
                self.length, self.context, self.keywords
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
