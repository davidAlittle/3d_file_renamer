# src/ui/dialogs/file_type_selector.py
from PySide6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout, 
    QCheckBox, 
    QPushButton,
    QLabel
)
from pathlib import Path
from collections import defaultdict
from .base_dialog import BaseDialog

class FileTypeSelector(BaseDialog):
    def __init__(self, directory: Path, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.selected_types = set()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Select File Types")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)

        # Scan directory for extensions
        extensions = self._scan_directory()
        
        # Add description
        layout.addWidget(QLabel("Select file types to process:"))

        # Create checkboxes with counts
        self.checkboxes = {}
        for ext, count in sorted(extensions.items()):
            cb = QCheckBox(f"{ext} ({count} files)")
            cb.setChecked(ext in {'.zip', '.rar', '.7z'})  # Default checked
            self.checkboxes[ext] = cb
            layout.addWidget(cb)

        # Buttons row
        btn_layout = QHBoxLayout()
        
        select_all = QPushButton("Select All")
        select_all.clicked.connect(self.select_all)
        btn_layout.addWidget(select_all)

        clear_all = QPushButton("Clear All")
        clear_all.clicked.connect(self.clear_all)
        btn_layout.addWidget(clear_all)

        btn_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _scan_directory(self):
        """Scan directory for file extensions and their counts"""
        extensions = defaultdict(int)
        for file in self.directory.rglob("*"):
            if file.is_file():
                ext = file.suffix.lower()
                if ext:
                    extensions[ext] += 1
        return extensions

    def select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def clear_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def get_selected_types(self):
        """Return list of selected file extensions"""
        return [ext for ext, cb in self.checkboxes.items() if cb.isChecked()]