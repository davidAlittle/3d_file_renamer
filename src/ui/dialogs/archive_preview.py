# src/ui/dialogs/archive_preview.py
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QWidget
)
from pathlib import Path
from src.core.archive_analyzer import ArchiveAnalyzer
from .base_dialog import BaseDialog

class ArchivePreviewDialog(BaseDialog):
    def __init__(self, filepath: Path, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.analyzer = ArchiveAnalyzer()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(f"Archive Preview: {self.filepath.name}")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Analysis tab
        analysis_widget = self._create_analysis_tab()
        tab_widget.addTab(analysis_widget, "Analysis")

        # Contents tab
        contents_widget = self._create_contents_tab()
        tab_widget.addTab(contents_widget, "Contents")

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _create_analysis_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Get analysis results
        analysis = self.analyzer.analyze_archive(self.filepath)

        # Display basic info
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setText(
            f"Filename: {analysis['filename']}\n"
            f"Size: {analysis['size']:,} bytes\n"
            f"Suggested Category: {analysis['suggested_category']}\n"
            f"Suggested Tags: {', '.join(analysis['suggested_tags'])}\n"
            f"Contains STL files: {'Yes' if analysis['contains_stls'] else 'No'}\n"
            f"Contains Documentation: {'Yes' if analysis['contains_docs'] else 'No'}\n"
        )
        layout.addWidget(info_text)

        return widget

    def _create_contents_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Get file list
        analysis = self.analyzer.analyze_archive(self.filepath)
        
        # Create table for file list
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Filename", "Type"])
        
        # Populate table
        files = analysis.get('file_list', [])
        table.setRowCount(len(files))
        
        for i, filename in enumerate(files):
            name_item = QTableWidgetItem(filename)
            ext_item = QTableWidgetItem(Path(filename).suffix)
            table.setItem(i, 0, name_item)
            table.setItem(i, 1, ext_item)

        layout.addWidget(table)

        return widget