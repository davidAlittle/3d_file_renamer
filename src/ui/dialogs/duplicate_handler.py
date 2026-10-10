# src/ui/dialogs/duplicate_handler.py
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
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
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from src.core.file_hasher import FileHasher
from src.database.database import DatabaseManager
from src.database.models import File
from .base_dialog import BaseDialog

@dataclass
class DuplicatePair:
    file1: Path
    file2: Path
    match_type: str
    quick_hash: str
    full_hash: Optional[str] = None

class DuplicateDetector:
    def __init__(self, db: DatabaseManager = None):
        self.db = db
        self.file_hasher = FileHasher()
        
    def find_duplicates(self, files: List[Path], 
                       progress_callback=None) -> List[DuplicatePair]:
        """Find duplicates using both quick and full hash comparisons"""
        duplicates = []
        quick_hash_map: Dict[str, List[Path]] = {}
        
        # First pass: Quick hash
        for idx, file in enumerate(files):
            try:
                quick_hash = self.file_hasher.get_quick_hash(file)
                if not quick_hash:
                    continue
                
                if quick_hash in quick_hash_map:
                    quick_hash_map[quick_hash].append(file)
                else:
                    quick_hash_map[quick_hash] = [file]
                    
                if progress_callback:
                    progress_callback(idx + 1, len(files))
                    
            except Exception as e:
                logging.error(f"Error processing {file}: {e}")
                
        # Second pass: Full hash for potential duplicates
        for quick_hash, files in quick_hash_map.items():
            if len(files) > 1:
                full_hash_map: Dict[str, Path] = {}
                
                for file in files:
                    try:
                        full_hash = self.file_hasher.get_content_hash(file)
                        if not full_hash:
                            continue
                            
                        if full_hash in full_hash_map:
                            duplicates.append(DuplicatePair(
                                file1=full_hash_map[full_hash],
                                file2=file,
                                match_type='Identical Content',
                                quick_hash=quick_hash,
                                full_hash=full_hash
                            ))
                        else:
                            full_hash_map[full_hash] = file
                            
                    except Exception as e:
                        logging.error(f"Error verifying duplicate {file}: {e}")
                        
        return duplicates

class DuplicateScanWorker(QThread):
    """Runs duplicate detection off the UI thread"""
    
    progress = Signal(int, int)
    scan_finished = Signal(list)
    scan_failed = Signal(str)
    
    def __init__(self, files: List[Path], parent=None):
        super().__init__(parent)
        self.files = files
        
    def run(self):
        try:
            detector = DuplicateDetector()
            duplicates = detector.find_duplicates(
                self.files,
                lambda current, total: self.progress.emit(current, total)
            )
            self.scan_finished.emit(duplicates)
        except Exception as e:
            logging.error(f"Duplicate scan failed: {e}", exc_info=True)
            self.scan_failed.emit(str(e))

class DuplicateHandlerDialog(BaseDialog):
    def __init__(self, files: List[Path], parent=None,
                 duplicates: List[DuplicatePair] = None,
                 db: DatabaseManager = None):
        super().__init__(parent)
        self.files = files
        self.db = db or DatabaseManager()
        self.duplicates: List[DuplicatePair] = []
        self.handled_files: set[Path] = set()
        self.scan_worker: Optional[DuplicateScanWorker] = None
        
        self.setWindowTitle("Duplicate File Handler")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        
        if duplicates is not None:
            self._show_duplicates(duplicates)
        else:
            self.start_scan()

    def setup_ui(self):
        # Progress section
        self.progress_label = QLabel("Scanning for duplicates...")
        self.content_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.content_layout.addWidget(self.progress_bar)

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
        self.content_layout.addWidget(self.table)

        # Buttons
        process_btn = QPushButton("Process Selected Actions")
        process_btn.clicked.connect(self.process_actions)
        
        mark_all_btn = QPushButton("Mark All as DUPE")
        mark_all_btn.clicked.connect(self.mark_all_dupes)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        self.main_layout.addWidget(
            self.create_button_row(process_btn, mark_all_btn, close_btn)
        )

    def start_scan(self):
        """Scan for duplicates on a worker thread"""
        self.progress_bar.setMaximum(max(len(self.files), 1))
        self.scan_worker = DuplicateScanWorker(self.files, self)
        self.scan_worker.progress.connect(self._update_progress)
        self.scan_worker.scan_finished.connect(self._show_duplicates)
        self.scan_worker.scan_failed.connect(self._on_scan_failed)
        self.scan_worker.start()

    def _update_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _on_scan_failed(self, message: str):
        self.progress_label.setText("Duplicate scan failed")
        QMessageBox.warning(
            self, "Error", 
            f"Error detecting duplicates: {message}"
        )

    def _show_duplicates(self, duplicates: List[DuplicatePair]):
        self.duplicates = duplicates
        self.update_table()
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_label.setText(
            f"Found {len(self.duplicates)} duplicate pairs"
        )

    def _scan_in_progress(self) -> bool:
        return bool(self.scan_worker and self.scan_worker.isRunning())

    def accept(self):
        """Don't close the dialog while a scan is still running"""
        if self._scan_in_progress():
            return
        super().accept()

    def reject(self):
        """Don't close the dialog while a scan is still running"""
        if self._scan_in_progress():
            return
        super().reject()

    def update_table(self):
        """Update the table with found duplicates"""
        self.table.setRowCount(len(self.duplicates))
        
        for row, duplicate in enumerate(self.duplicates):
            # File 1
            self.table.setItem(
                row, 0, 
                QTableWidgetItem(duplicate.file1.name)
            )
            
            # File 2
            self.table.setItem(
                row, 1, 
                QTableWidgetItem(duplicate.file2.name)
            )
            
            # Match type
            self.table.setItem(
                row, 2, 
                QTableWidgetItem(duplicate.match_type)
            )
            
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
            status_item = self.table.item(row, 4)
            if status_item.text() != "Pending":
                continue
            
            action = self.table.cellWidget(row, 3).currentText()
            duplicate = self.duplicates[row]
            
            try:
                if action == "Keep Both":
                    status_item.setText("Kept")
                    continue
                
                older, newer = self._order_by_age(duplicate)
                target = newer if "Newer" in action else older
                
                if "Mark" in action:
                    new_path = self._make_dupe_path(target)
                    self._update_db_record(target, new_name=new_path.name)
                    target.rename(new_path)
                    self.handled_files.add(target)
                    status_item.setText(f"Marked {target.name} as DUPE")
                    
                else:  # Delete
                    self._update_db_record(target, status="Deleted")
                    target.unlink()
                    self.handled_files.add(target)
                    status_item.setText(f"Deleted {target.name}")
                    
            except Exception as e:
                logging.error(f"Error processing duplicate: {e}", exc_info=True)
                status_item.setText(f"Error: {e}")

    def _order_by_age(self, duplicate: DuplicatePair) -> Tuple[Path, Path]:
        """Return the pair as (older, newer) based on modification time"""
        if (duplicate.file1.stat().st_mtime <= duplicate.file2.stat().st_mtime):
            return duplicate.file1, duplicate.file2
        return duplicate.file2, duplicate.file1

    def _make_dupe_path(self, path: Path) -> Path:
        """Build a non-colliding _DUPE name for the given file"""
        candidate = path.parent / f"{path.stem}_DUPE{path.suffix}"
        counter = 1
        while candidate.exists():
            counter += 1
            candidate = path.parent / f"{path.stem}_DUPE_{counter}{path.suffix}"
        return candidate

    def _update_db_record(self, path: Path, new_name: str = None, status: str = None):
        """Update the tracked record for a file, if one exists"""
        try:
            with self.db.session_scope() as session:
                record = session.query(File).filter_by(
                    original_path=str(path)
                ).first()
                if record:
                    if new_name is not None:
                        record.new_name = new_name
                    if status is not None:
                        record.status = status
        except Exception as e:
            logging.error(f"Failed to update database for {path}: {e}")

    def mark_all_dupes(self):
        """Set all actions to Mark Newer as DUPE"""
        for row in range(self.table.rowCount()):
            self.table.cellWidget(row, 3).setCurrentText(
                "Mark Newer as DUPE"
            )