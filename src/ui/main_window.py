# src/ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QMenu,
    QHeaderView,
    QProgressDialog,
    QSizePolicy
)
from PySide6.QtCore import Qt
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import json
import csv
import logging

from src.database.models import File
from src.database.database import DatabaseManager
from src.core.file_hasher import FileHasher
from src.core.archive_analyzer import ArchiveAnalyzer
from src.core.settings_manager import Settings
from src.ui.dialogs.file_type_selector import FileTypeSelector
from src.ui.dialogs.archive_preview import ArchivePreviewDialog
from src.ui.dialogs.duplicate_handler import (
    DuplicateHandlerDialog,
    DuplicatePair,
    DuplicateScanWorker,
)
from src.ui.dialogs.preferences_dialog import PreferencesDialog
from src.ui.widgets.tag_editor import TagEditor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize managers - all using singleton pattern
        self.settings = Settings()
        self.analyzer = ArchiveAnalyzer()  # Now includes rules_manager and name analysis
        self.db = DatabaseManager()
        
        # Initialize state
        self.files_to_rename = []
        self.file_analysis_cache = {}  # Cache for file analysis results
        
        self.setup_menu()
        self.setup_ui()
        self.load_window_state()

    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Export submenu
        export_menu = QMenu("Export", self)
        
        export_csv = export_menu.addAction("Export to CSV")
        export_csv.triggered.connect(lambda: self.export_data("csv"))
        
        export_json = export_menu.addAction("Export to JSON")
        export_json.triggered.connect(lambda: self.export_data("json"))
        
        file_menu.addMenu(export_menu)
        
        # Import/Export rules
        import_action = file_menu.addAction("Import Rename Rules")
        import_action.triggered.connect(self.import_rules)
        
        export_rules = file_menu.addAction("Export Rename Rules")
        export_rules.triggered.connect(self.export_rules)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        preferences_action = edit_menu.addAction("Preferences")
        preferences_action.triggered.connect(self.show_preferences)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Top buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)         
        
        self.select_dir_btn = QPushButton("Select Directory")
        self.select_dir_btn.clicked.connect(self.select_directory)
        button_layout.addWidget(self.select_dir_btn)
        
        self.select_files_btn = QPushButton("Select Files")
        self.select_files_btn.clicked.connect(self.select_files)
        button_layout.addWidget(self.select_files_btn)
        
        self.apply_all_btn = QPushButton("Apply All")
        self.apply_all_btn.clicked.connect(self.apply_all_changes)
        button_layout.addWidget(self.apply_all_btn)
        
        layout.addLayout(button_layout)

        # Add tag editor
        self.tag_editor = TagEditor()
        self.tag_editor.tagsChanged.connect(self.update_suggested_name)
        layout.addWidget(self.tag_editor)

        # Setup table
        self.setup_table()
        layout.addWidget(self.file_table)

    def setup_table(self):
        """Setup the main file table with proper column behavior"""
        self.file_table = QTableWidget()
        self.file_table.setMinimumHeight(300)
        self.file_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Configure table columns
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels([
            "Original Name", 
            "New Name (double-click to edit)", 
            "Actions",
            "Status"
        ])
        
        # Get the total width of the table viewport
        viewport_width = self.file_table.viewport().width()
        
        # Set column behaviors
        header = self.file_table.horizontalHeader()
        
        # Original Name: 30% with minimum width
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.file_table.setColumnWidth(0, max(300, int(viewport_width * 0.3)))
        
        # New Name: Stretch but with minimum width
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.file_table.setColumnWidth(1, max(400, int(viewport_width * 0.4)))
        
        # Actions: Fixed width
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(2, 200)
        
        # Status: Fixed width
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(3, 100)
        
        # Enable stretchLastSection after setting individual column modes
        header.setStretchLastSection(False)
        
        # Connect resize event
        self.file_table.horizontalHeader().sectionResized.connect(
            self._handle_column_resize
        )

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        self._update_column_widths()
        
    def _update_column_widths(self):
        """Update column widths based on current window size"""
        if not hasattr(self, 'file_table'):
            return
            
        viewport_width = self.file_table.viewport().width()
        
        # Maintain minimum widths while scaling with window
        original_width = max(300, int(viewport_width * 0.3))
        new_name_width = max(400, int(viewport_width * 0.4))
        
        # Only update if the change is significant (prevents resize loops)
        current_original = self.file_table.columnWidth(0)
        current_new_name = self.file_table.columnWidth(1)
        
        if (abs(current_original - original_width) > 10 or 
            abs(current_new_name - new_name_width) > 10):
            
            self.file_table.setColumnWidth(0, original_width)
            self.file_table.setColumnWidth(1, new_name_width)
            # Actions and Status columns remain fixed width
            
    def _handle_column_resize(self, logical_index: int, old_size: int, new_size: int):
        """Handle manual column resizing"""
        if logical_index in (0, 1):  # Only for resizable columns
            # Store the manually set width
            self._manual_column_widths = getattr(self, '_manual_column_widths', {})
            self._manual_column_widths[logical_index] = new_size
            
    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            dir_path = Path(dir_path)
            
            selector = FileTypeSelector(dir_path, self)
            if selector.exec():
                selected_types = selector.get_selected_types()
                if selected_types:
                    files = []
                    for ext in selected_types:
                        files.extend(dir_path.glob(f"*{ext}"))
                    
                    if files:
                        self.load_files(files)
                    else:
                        QMessageBox.information(
                            self,
                            "No Files Found",
                            f"No files with selected extensions found in directory."
                        )

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Rename",
            "",
            "Archive Files (*.zip *.rar *.7z)"
        )
        if files:
            self.load_files([Path(f) for f in files])

    def load_files(self, input_files: List[Path]):
        """Load files with proper hash calculation and duplicate detection"""
        logging.info(f"Loading {len(input_files)} files")
        
        try:
            # Scan for duplicates without blocking the UI thread
            duplicates = self.find_duplicates_with_progress(input_files)

            files_to_process = input_files
            if duplicates:
                dialog = DuplicateHandlerDialog(
                    input_files, self, duplicates=duplicates, db=self.db
                )
                dialog.exec()

                # Exclude only the files the dialog actually renamed or deleted
                files_to_process = [
                    f for f in input_files if f not in dialog.handled_files
                ]

            # Update the file list and table
            self.files_to_rename = files_to_process
            self.file_table.setRowCount(len(self.files_to_rename))
            
            # Process each file
            for row, filepath in enumerate(self.files_to_rename):
                self._add_file_to_table(row, filepath)

        except Exception as e:
            logging.error(f"Error loading files: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error loading files: {str(e)}")

    def find_duplicates_with_progress(self, files: List[Path]) -> List[DuplicatePair]:
        """Run duplicate detection on a worker thread with modal progress"""
        progress = QProgressDialog("Scanning for duplicates...", "", 0, len(files), self)
        progress.setWindowTitle("Duplicate Check")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        worker = DuplicateScanWorker(files, self)
        result: Dict[str, List[DuplicatePair]] = {}

        def on_progress(current: int, total: int):
            progress.setMaximum(total)
            progress.setValue(current)

        def on_finished(pairs: List[DuplicatePair]):
            result['pairs'] = pairs
            progress.accept()

        def on_failed(message: str):
            result['error'] = message
            progress.reject()

        worker.progress.connect(on_progress)
        worker.scan_finished.connect(on_finished)
        worker.scan_failed.connect(on_failed)

        worker.start()
        progress.exec()
        worker.wait()

        if 'error' in result:
            logging.warning(f"Duplicate scan failed: {result['error']}")
        return result.get('pairs', [])

    def _add_file_to_table(self, row: int, filepath: Path):
        """Add a single file to the table"""
        try:
            # Calculate hashes
            quick_hash = FileHasher.get_quick_hash(filepath)
            content_hash = FileHasher.get_content_hash(filepath)
            
            # Add to database
            with self.db.session_scope() as session:
                file_record = File(
                    original_name=filepath.name,
                    original_path=str(filepath),
                    quick_hash=quick_hash,
                    content_hash=content_hash,
                    status='pending'
                )
                session.add(file_record)
            
            # Analyze file and cache results
            analysis = self.analyzer.analyze_archive(filepath)
            self.file_analysis_cache[str(filepath)] = analysis
            
            # Add to table
            self.file_table.setItem(row, 0, QTableWidgetItem(filepath.name))
            
            # Generate and add suggested name
            suggested_name = self.generate_new_name(filepath.name)
            name_item = QTableWidgetItem(suggested_name)
            name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
            self.file_table.setItem(row, 1, name_item)
            
            # Create and add action buttons
            self._create_action_buttons(row, filepath)
            
            # Set initial status
            status = "Error: " + analysis['error'] if analysis.get('error') else "Pending"
            self.file_table.setItem(row, 3, QTableWidgetItem(status))
            
        except Exception as e:
            logging.error(f"Error adding file {filepath} to table: {e}", exc_info=True)
            self.file_table.setItem(row, 3, QTableWidgetItem(f"Error: {str(e)}"))

    def _create_action_buttons(self, row: int, filepath: Path):
        """Create action buttons for a table row"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(lambda checked=False, r=row: self.apply_single_change(r))
        
        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(lambda checked=False, r=row: self.skip_file(r))
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(lambda checked=False, r=row: self.preview_file(r))
        
        actions_layout.addWidget(apply_btn)
        actions_layout.addWidget(skip_btn)
        actions_layout.addWidget(preview_btn)
        
        self.file_table.setCellWidget(row, 2, actions_widget)

    def preview_file(self, row):
        filepath = self.files_to_rename[row]
        logging.debug(f"Opening preview for file: {filepath}")
        
        # Log cached analysis if available
        cached_analysis = self.file_analysis_cache.get(str(filepath))
        if cached_analysis:
            logging.debug(f"Cached analysis found: {cached_analysis}")
        else:
            logging.debug("No cached analysis found")
        
        dialog = ArchivePreviewDialog(filepath, self)
        dialog.exec()

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be compatible with Windows file systems"""
        # Replace invalid characters with safe alternatives
        invalid_chars = {'<': '⟨', '>': '⟩', ':': '꞉', '"': '″', '/': '∕', 
                        '\\': '∖', '|': '￨', '?': '？', '*': '∗'}
        
        for char, replacement in invalid_chars.items():
            filename = filename.replace(char, replacement)
            
        # Remove any other control characters
        filename = "".join(char for char in filename if ord(char) >= 32)
        
        return filename.strip()

    def generate_new_name(self, filename: str) -> str:
        """Generate new name based on analysis and rules"""
        filepath = next((f for f in self.files_to_rename if f.name == filename), None)
        if not filepath:
            logging.warning(f"File not found for name generation: {filename}")
            return filename

        try:
            # Use cached analysis if available
            if str(filepath) not in self.file_analysis_cache:
                analysis = self.analyzer.analyze_archive(filepath)
                self.file_analysis_cache[str(filepath)] = analysis
            else:
                analysis = self.file_analysis_cache[str(filepath)]

            # Build name components
            parts = []
            
            # Add category if enabled
            if self.settings.get("naming", "add_category_prefix", True):
                parts.append(analysis['suggested_category'])
            
            # Add base name (cleaned by the analyzer when available)
            parts.append(analysis.get('base_name') or Path(filename).stem)
            
            # Add version if present and enabled
            if analysis.get('version') and self.settings.get("naming", "preserve_version_numbers", True):
                parts.append(f"v{analysis['version']}")
            
            # Join parts for base name
            base_name = " ".join(parts)
            
            # Add tags if present
            if analysis['suggested_tags']:
                tag_style = self.settings.get("tags", "tag_style", "brackets")
                tag_separator = self.settings.get("tags", "tag_separator", " ")
                
                formatted_tags = []
                for tag in sorted(analysis['suggested_tags']):
                    if tag_style == "brackets":
                        formatted_tags.append(f"[{tag}]")
                    elif tag_style == "parentheses":
                        formatted_tags.append(f"({tag})")
                    else:
                        formatted_tags.append(tag)
                
                base_name = f"{base_name}{tag_separator}{tag_separator.join(formatted_tags)}"
            
            # Sanitize the final name before returning
            return self._sanitize_filename(base_name.strip())
            
        except Exception as e:
            logging.error(f"Error generating name for {filename}: {e}", exc_info=True)
            return filename

    def apply_single_change(self, row):
        try:
            original_path = self.files_to_rename[row]
            new_name = self._sanitize_filename(self.file_table.item(row, 1).text())
            
            if not new_name.endswith(original_path.suffix):
                new_name += original_path.suffix
            
            new_path = original_path.parent / new_name
            
            if new_path.exists():
                reply = QMessageBox.question(
                    self, 'File exists',
                    f'File {new_name} already exists. Overwrite?',
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    self.file_table.item(row, 3).setText("Skipped - File exists")
                    return
            
            # Perform rename and update database
            with self.db.session_scope() as session:
                original_path.rename(new_path)
                file_record = session.query(File).filter_by(
                    original_path=str(original_path)
                ).first()
                
                if file_record:
                    file_record.new_name = new_name
                    file_record.status = "Renamed"
            
            self.file_table.item(row, 3).setText("Renamed")
            
            # Disable buttons after successful rename
            actions_widget = self.file_table.cellWidget(row, 2)
            for button in actions_widget.findChildren(QPushButton):
                button.setEnabled(False)
                
        except Exception as e:
            logging.error(f"Error renaming file: {e}", exc_info=True)
            self.file_table.item(row, 3).setText(f"Error: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to rename file: {str(e)}")

    def skip_file(self, row):
        try:
            with self.db.session_scope() as session:
                filepath = self.files_to_rename[row]
                file_record = session.query(File).filter_by(
                    original_path=str(filepath)
                ).first()
                
                if file_record:
                    file_record.status = "Skipped"
            
            self.file_table.item(row, 3).setText("Skipped")
            
            # Disable buttons
            actions_widget = self.file_table.cellWidget(row, 2)
            for button in actions_widget.findChildren(QPushButton):
                button.setEnabled(False)
        
        except Exception as e:
            logging.error(f"Error skipping file: {e}", exc_info=True)
            self.file_table.item(row, 3).setText(f"Error: {str(e)}")

    def apply_all_changes(self):
        reply = QMessageBox.question(
            self, 'Apply All Changes',
            'Are you sure you want to apply all pending changes?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for row in range(self.file_table.rowCount()):
                if self.file_table.item(row, 3).text() == "Pending":
                    self.apply_single_change(row)

    def update_suggested_name(self, tags: list[str]):
        """Update the suggested name when tags change"""
        current_row = self.file_table.currentRow()
        if current_row >= 0:
            current_item = self.file_table.item(current_row, 1)
            if current_item:
                base_name = current_item.text().split('[')[0].strip()
                new_name = f"{base_name} {' '.join(tags)}"
                current_item.setText(new_name)

    def refresh_suggested_names(self):
        """Refresh all suggested names in the table"""
        try:
            # Clear analysis cache
            self.file_analysis_cache.clear()
            
            # Update each row
            for row in range(self.file_table.rowCount()):
                filename = self.file_table.item(row, 0).text()
                suggested_name = self.generate_new_name(filename)
                
                # Update only if the name would change
                current_name = self.file_table.item(row, 1).text()
                if current_name != suggested_name:
                    self.file_table.item(row, 1).setText(suggested_name)
                    self.file_table.item(row, 3).setText("Updated")
                    
        except Exception as e:
            logging.error(f"Error refreshing names: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", 
                "Failed to refresh suggested names. Check the logs for details.")

    def export_data(self, format_type: str):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format_type == "csv":
                self._export_to_csv(timestamp)
            elif format_type == "json":
                self._export_to_json(timestamp)
                
        except Exception as e:
            logging.error(f"Export failed: {e}", exc_info=True)
            QMessageBox.warning(self, "Export Failed", 
                f"Failed to export data: {str(e)}")

    def _export_to_csv(self, timestamp: str):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            f"rename_history_{timestamp}.csv",
            "CSV Files (*.csv)"
        )
        if not filename:
            return
            
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Original Name",
                "New Name",
                "Status",
                "Tags",
                "Category"
            ])
            
            with self.db.session_scope() as session:
                files = session.query(File).all()
                for file in files:
                    writer.writerow([
                        file.original_name,
                        file.new_name or "",
                        file.status,
                        ", ".join(tag.name for tag in file.tags),
                        getattr(file, 'category', "")
                    ])
        
        QMessageBox.information(self, "Export Successful", 
            f"Data exported to {filename}")

    def _export_to_json(self, timestamp: str):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export to JSON",
            f"rename_history_{timestamp}.json",
            "JSON Files (*.json)"
        )
        if not filename:
            return
            
        with self.db.session_scope() as session:
            files = session.query(File).all()
            export_data = [{
                "original_name": file.original_name,
                "new_name": file.new_name,
                "status": file.status,
                "tags": [tag.name for tag in file.tags],
                "category": getattr(file, 'category', ""),
                "content_hash": file.content_hash,
                "processed_date": file.last_modified.isoformat() 
                    if file.last_modified else None
            } for file in files]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        QMessageBox.information(self, "Export Successful", 
            f"Data exported to {filename}")

    def export_rules(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Rules",
            str(Path("rules") / "rename_rules.json"),
            "JSON Files (*.json)"
        )
        if filename:
            try:
                rules = self.analyzer.rules_manager.rules
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(rules, f, indent=2)
                QMessageBox.information(self, "Success", 
                    "Rules exported successfully")
            except Exception as e:
                logging.error(f"Failed to export rules: {e}")
                QMessageBox.warning(self, "Error", 
                    f"Failed to export rules: {str(e)}")

    def import_rules(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Rules",
            str(Path("rules")),
            "JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                self.analyzer.rules_manager.validate_rules(rules)
                self.analyzer.rules_manager.rules = rules
                self.analyzer.rules_manager.save_rules()
                self.refresh_suggested_names()
                QMessageBox.information(self, "Success", 
                    "Rules imported successfully")
            except Exception as e:
                logging.error(f"Failed to import rules: {e}")
                QMessageBox.warning(self, "Error", 
                    f"Failed to import rules: {str(e)}")

    def show_preferences(self):
        dialog = PreferencesDialog(self.settings, self)
        if dialog.exec():
            self.apply_settings()

    def apply_settings(self):
        if self.settings.get("naming", "add_category_prefix"):
            self.refresh_suggested_names()

    def load_window_state(self):
        if self.settings.get("general", "save_window_size"):
            size = self.settings.get("window", "size")
            pos = self.settings.get("window", "position")
            if size:
                self.resize(size[0], size[1])
            if pos:
                self.move(pos[0], pos[1])

    def closeEvent(self, event):
        if self.settings.get("general", "save_window_size"):
            self.settings.set("window", "size", 
                [self.width(), self.height()])
            self.settings.set("window", "position", 
                [self.x(), self.y()])