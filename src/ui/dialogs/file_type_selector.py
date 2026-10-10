# src/ui/dialogs/file_type_selector.py
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set

from PySide6.QtWidgets import (
    QHBoxLayout,
    QCheckBox,
    QPushButton,
    QLabel,
    QScrollArea,
    QWidget,
    QVBoxLayout
)
from PySide6.QtCore import Qt

from .base_dialog import BaseDialog

class FileTypeSelector(BaseDialog):
    """Dialog for selecting file types to process"""
    
    # Default file types to select
    DEFAULT_TYPES = {'.zip', '.rar', '.7z'}

    def __init__(self, directory: Path, parent=None):
        self.directory = directory
        self.selected_types: Set[str] = set()
        self.checkboxes: Dict[str, QCheckBox] = {}
        
        super().__init__(parent)
        self.setWindowTitle("Select File Types")
        
        # Set fixed dimensions instead of just minimum width
        self.setFixedSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI components"""
        try:
            # Use content_layout from BaseDialog
            # Add description
            description = QLabel("Select file types to process:")
            description.setWordWrap(True)
            self.content_layout.addWidget(description)

            # Create scrollable area for checkboxes
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            checkbox_widget = QWidget()
            checkbox_layout = QVBoxLayout(checkbox_widget)
            checkbox_layout.setSpacing(self.SPACING)
            checkbox_layout.setContentsMargins(self.MARGIN, self.MARGIN, 
                                            self.MARGIN, self.MARGIN)

            # Scan directory and create checkboxes
            extensions = self.scan_directory()
            if not extensions:
                # Show message if no files found
                no_files_label = QLabel("No files found in selected directory")
                no_files_label.setStyleSheet("color: gray;")
                checkbox_layout.addWidget(no_files_label)
            else:
                for ext, count in sorted(extensions.items()):
                    cb = QCheckBox(f"{ext} ({count} files)")
                    cb.setChecked(ext in self.DEFAULT_TYPES)
                    self.checkboxes[ext] = cb
                    checkbox_layout.addWidget(cb)

            # Add stretch at the bottom of checkbox layout
            checkbox_layout.addStretch()

            scroll.setWidget(checkbox_widget)
            self.content_layout.addWidget(scroll)

            # Create buttons
            select_all = QPushButton("Select All")
            select_all.clicked.connect(self.select_all)
            
            clear_all = QPushButton("Clear All")
            clear_all.clicked.connect(self.clear_all)
            
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(self.accept)
            ok_btn.setDefault(True)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)

            # Add button row using base dialog helper
            button_widget = self.create_button_row(
                select_all, clear_all, ok_btn, cancel_btn
            )
            self.main_layout.addWidget(button_widget)

        except Exception as e:
            logging.error(f"Error setting up file type selector: {e}", exc_info=True)
            self.show_error("Failed to setup selector")

    def scan_directory(self) -> Dict[str, int]:
        """Scan directory for file extensions and their counts"""
        try:
            extensions = defaultdict(int)
            for file in self.directory.rglob("*"):
                if file.is_file():
                    ext = file.suffix.lower()
                    if ext:  # Only count files with extensions
                        extensions[ext] += 1
            return dict(sorted(extensions.items()))
        
        except Exception as e:
            logging.error(f"Error scanning directory {self.directory}: {e}", 
                         exc_info=True)
            self.show_error(f"Error scanning directory: {str(e)}")
            return {}

    def select_all(self):
        """Select all file types"""
        try:
            for cb in self.checkboxes.values():
                cb.setChecked(True)
        except Exception as e:
            logging.error("Error selecting all file types", exc_info=True)

    def clear_all(self):
        """Clear all file type selections"""
        try:
            for cb in self.checkboxes.values():
                cb.setChecked(False)
        except Exception as e:
            logging.error("Error clearing file type selections", exc_info=True)

    def get_selected_types(self) -> list[str]:
        """Return list of selected file extensions"""
        try:
            return [ext for ext, cb in self.checkboxes.items() 
                   if cb.isChecked()]
        except Exception as e:
            logging.error("Error getting selected file types", exc_info=True)
            return []

    def show_error(self, message: str):
        """Show error message in the UI"""
        error_label = QLabel(f"Error: {message}")
        error_label.setStyleSheet("color: red;")
        error_label.setWordWrap(True)
        self.content_layout.addWidget(error_label)