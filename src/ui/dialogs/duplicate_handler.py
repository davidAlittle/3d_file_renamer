# src/ui/dialogs/duplicate_handler.py
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLabel,
    QProgressBar,
    QMessageBox
)
import logging
from pathlib import Path
from src.core.file_hasher import FileHasher
from .base_dialog import BaseDialog

class DuplicateHandlerDialog(BaseDialog):
    def __init__(self, files: list[Path], parent=None):
        super().__init__(parent)
        self.files = files
        self.duplicates = []
        self.setWindowTitle("Duplicate File Handler")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.find_duplicates()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Progress section
        self.progress_label = QLabel("Scanning for duplicates...")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "File 1",
            "File 2",
            "Match Type",
            "Action",
            "Status"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()
        
        process_btn = QPushButton("Process Selected Actions")
        process_btn.clicked.connect(self.process_actions)
        button_layout.addWidget(process_btn)
        
        mark_all_btn = QPushButton("Mark All as DUPE")
        mark_all_btn.clicked.connect(self.mark_all_dupes)
        button_layout.addWidget(mark_all_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
def find_duplicates(self):
    """Find duplicate files using multiple methods"""
    try:
        total_files = len(self.files)
        self.progress_bar.setMaximum(total_files)
        processed = 0

        # First pass: Quick hash
        quick_hash_map = {}
        for file in self.files:
            try:
                quick_hash = FileHasher.get_quick_hash(file)
                if quick_hash:
                    if quick_hash in quick_hash_map:
                        quick_hash_map[quick_hash].append(file)
                    else:
                        quick_hash_map[quick_hash] = [file]
            except Exception as e:
                logging.error(f"Error processing file {file}: {e}")
            finally:
                processed += 1
                self.progress_bar.setValue(processed)

        # Second pass: Full hash for potential duplicates
        for files in quick_hash_map.values():
            if len(files) > 1:
                # Verify with full hash
                full_hash_map = {}
                for file in files:
                    try:
                        full_hash = FileHasher.get_content_hash(file)
                        if full_hash:  # Add null check
                            if full_hash in full_hash_map:
                                self.duplicates.append({
                                    'file1': full_hash_map[full_hash],
                                    'file2': file,
                                    'match_type': 'Identical Content'
                                })
                            else:
                                full_hash_map[full_hash] = file
                    except Exception as e:
                        logging.error(f"Error verifying duplicate {file}: {e}")

        self.update_table()
        self.progress_label.setText(f"Found {len(self.duplicates)} duplicate pairs")
        
    except Exception as e:
        logging.error(f"Error in duplicate detection: {e}")
        QMessageBox.warning(self, "Error", f"Error detecting duplicates: {str(e)}")
    def update_table(self):
        """Update the table with found duplicates"""
        self.table.setRowCount(len(self.duplicates))
        
        for row, duplicate in enumerate(self.duplicates):
            # File 1
            self.table.setItem(row, 0, QTableWidgetItem(duplicate['file1'].name))
            
            # File 2
            self.table.setItem(row, 1, QTableWidgetItem(duplicate['file2'].name))
            
            # Match type
            self.table.setItem(row, 2, QTableWidgetItem(duplicate['match_type']))
            
            # Action combo box
            action_combo = QComboBox()
            action_combo.addItems([
                "Keep Both",
                "Mark Newer as DUPE",
                "Mark Older as DUPE",
                "Delete Newer",
                "Delete Older"
            ])
            self.table.setCellWidget(row, 3, action_combo)
            
            # Status
            self.table.setItem(row, 4, QTableWidgetItem("Pending"))

    def process_actions(self):
        """Process the selected actions for duplicates"""
        for row in range(self.table.rowCount()):
            action = self.table.cellWidget(row, 3).currentText()
            file1 = self.duplicates[row]['file1']
            file2 = self.duplicates[row]['file2']
            
            try:
                if "Mark" in action:
                    # Determine which file to mark
                    file_to_mark = file2 if "Newer" in action else file1
                    new_name = file_to_mark.stem + "_DUPE" + file_to_mark.suffix
                    file_to_mark.rename(file_to_mark.parent / new_name)
                    self.table.item(row, 4).setText("Marked")
                    
                elif "Delete" in action:
                    # Determine which file to delete
                    file_to_delete = file2 if "Newer" in action else file1
                    file_to_delete.unlink()
                    self.table.item(row, 4).setText("Deleted")
                    
                else:  # Keep Both
                    self.table.item(row, 4).setText("Kept")
                    
            except Exception as e:
                self.table.item(row, 4).setText(f"Error: {str(e)}")

    def mark_all_dupes(self):
        """Set all actions to Mark Newer as DUPE"""
        for row in range(self.table.rowCount()):
            self.table.cellWidget(row, 3).setCurrentText("Mark Newer as DUPE")