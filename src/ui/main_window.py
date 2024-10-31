# src/ui/main_window.py
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
    QSizePolicy
)
from PySide6.QtCore import Qt
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import json
import csv
import logging

from ..database.models import File
from ..database.database import DatabaseManager
from ..core.file_hasher import FileHasher
from ..core.archive_analyzer import ArchiveAnalyzer
from ..core.settings_manager import Settings
from ..core.rules_manager import RulesManager
from ..core.name_analyzer import NameAnalyzer
from .dialogs.file_type_selector import FileTypeSelector
from .dialogs.archive_preview import ArchivePreviewDialog
from .dialogs.duplicate_handler import DuplicateHandlerDialog
from .dialogs.preferences_dialog import PreferencesDialog
from .widgets.tag_editor import TagEditor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.rules_manager = RulesManager()
        self.name_analyzer = NameAnalyzer(self.rules_manager)
        self.setWindowTitle("3D Print File Renamer")
        self.setMinimumSize(1200, 600)
        self.db = DatabaseManager()
        self.analyzer = ArchiveAnalyzer()
        self.files_to_rename = []
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
        
        # Import
        import_action = file_menu.addAction("Import Rename Rules")
        import_action.triggered.connect(self.import_rules)
        
        # Export current rules
        export_rules = file_menu.addAction("Export Rename Rules")
        export_rules.triggered.connect(self.export_rules)

        # Add Edit menu
        edit_menu = menubar.addMenu("Edit")
        preferences_action = edit_menu.addAction("Preferences")
        preferences_action.triggered.connect(self.show_preferences)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)  # Add some padding
        layout.setSpacing(8)  # Space between widgets

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
        layout.addWidget(self.tag_editor)

        # Table
 # Table takes all remaining space
        self.file_table = QTableWidget()
        self.file_table.setMinimumHeight(300)  # Minimum reasonable height
        self.file_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Allow table to stretch horizontally but maintain column proportions
        self.file_table.horizontalHeader().setStretchLastSection(False)
        total_width = self.width()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels([
            "Original Name", 
            "New Name (double-click to edit)", 
            "Actions",
            "Status"
        ])
        
        # Set proportional column widths
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # User can resize
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)      # Takes extra space
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)        # Fixed size
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)        # Fixed size
        
        # Initial column widths
        self.file_table.setColumnWidth(0, int(total_width * 0.3))  # 30% of width
        self.file_table.setColumnWidth(2, 200)                     # Fixed action buttons width
        self.file_table.setColumnWidth(3, 100)                     # Fixed status width
        
        layout.addWidget(self.file_table)

    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            dir_path = Path(dir_path)
            
            # Show file type selector
            selector = FileTypeSelector(dir_path, self)
            if selector.exec():
                selected_types = selector.get_selected_types()
                if selected_types:
                    # Get files of selected types
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
            "ZIP Files (*.zip)"
        )
        if files:
            self.load_files([Path(f) for f in files])

    def load_files(self, input_files: List[Path]):
        """Load files with proper hash calculation and duplicate detection"""
        logging.info(f"Loading {len(input_files)} files")
        
        # Process files for duplicates
        file_hashes: Dict[str, Path] = {}
        duplicates = []
        files_to_process = []

        # Quick hash check first
        for file in input_files:
            quick_hash = FileHasher.get_quick_hash(file)
            if not quick_hash:
                logging.warning(f"Could not generate quick hash for {file}")
                continue
                
            if quick_hash in file_hashes:
                # Verify with full hash
                if FileHasher.are_files_identical(file, file_hashes[quick_hash]):
                    duplicates.append((file, file_hashes[quick_hash]))
                    continue
            file_hashes[quick_hash] = file
            files_to_process.append(file)

        # Handle duplicates if found
        if duplicates:
            duplicate_handler = DuplicateHandlerDialog(duplicates, self)
            duplicate_handler.exec()

        # Update the file list and table
        self.files_to_rename = files_to_process
        self.file_table.setRowCount(len(self.files_to_rename))
        
        # Process each file
        for row, filepath in enumerate(self.files_to_rename):
            self._add_file_to_table(row, filepath)

    def _add_file_to_table(self, row: int, filepath: Path):
        """Add a single file to the table"""
        try:
            # Calculate hashes
            quick_hash = FileHasher.get_quick_hash(filepath)
            content_hash = FileHasher.get_content_hash(filepath)
            
            # Store in database
            file_record = self.db.add_file(
                filepath,
                quick_hash=quick_hash,
                content_hash=content_hash
            )
            
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
            self.file_table.setItem(row, 3, QTableWidgetItem("Pending"))
            
        except Exception as e:
            logging.error(f"Error adding file {filepath} to table: {e}")
            self.file_table.setItem(row, 3, QTableWidgetItem(f"Error: {str(e)}"))

    def _create_action_buttons(self, row: int, filepath: Path):
        """Create action buttons for a table row"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create buttons
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(lambda checked, r=row: self.apply_single_change(r))
        
        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(lambda checked, r=row: self.skip_file(r))
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(lambda checked, r=row: self.preview_file(r))
        
        # Add buttons to layout
        actions_layout.addWidget(apply_btn)
        actions_layout.addWidget(skip_btn)
        actions_layout.addWidget(preview_btn)
        
        # Add to table
        self.file_table.setCellWidget(row, 2, actions_widget)

    def preview_file(self, row):
        filepath = self.files_to_rename[row]
        dialog = ArchivePreviewDialog(filepath, self)
        dialog.exec()

    def generate_new_name(self, filename: str) -> str:
        """Generate new name based on analysis"""
        filepath = next((f for f in self.files_to_rename if f.name == filename), None)
        if not filepath:
            return f"MISC {filename}"
            
        analyzer = ArchiveAnalyzer()
        analysis = analyzer.analyze_archive(filepath)
        
        # Build new name
        category = analysis['suggested_category']
        base_name = filepath.stem
        
        # Add tags if any
        tags = " ".join(f"[{tag}]" for tag in analysis['suggested_tags'])
        
        return f"{category} {base_name} {tags}".strip()

    def apply_single_change(self, row):
        try:
            original_path = self.files_to_rename[row]
            new_name = self.file_table.item(row, 1).text()
            
            if not new_name.endswith('.zip'):
                new_name += '.zip'
            
            new_path = original_path.parent / new_name
            
            # Check if destination exists
            if new_path.exists():
                reply = QMessageBox.question(self, 'File exists',
                    f'File {new_name} already exists. Overwrite?',
                    QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.No:
                    self.file_table.item(row, 3).setText("Skipped - File exists")
                    return
            
            # Perform rename
            original_path.rename(new_path)
            self.file_table.item(row, 3).setText("Renamed")
            
            # Disable buttons after successful rename
            actions_widget = self.file_table.cellWidget(row, 2)
            for button in actions_widget.findChildren(QPushButton):
                button.setEnabled(False)
                
        except Exception as e:
            self.file_table.item(row, 3).setText(f"Error: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to rename file: {str(e)}")

    def skip_file(self, row):
        self.file_table.item(row, 3).setText("Skipped")
        # Disable buttons after skip
        actions_widget = self.file_table.cellWidget(row, 2)
        for button in actions_widget.findChildren(QPushButton):
            button.setEnabled(False)

    def apply_all_changes(self):
        reply = QMessageBox.question(self, 'Apply All Changes',
            'Are you sure you want to apply all pending changes?',
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for row in range(self.file_table.rowCount()):
                if self.file_table.item(row, 3).text() == "Pending":
                    self.apply_single_change(row)

    def update_suggested_name(self, tags: list[str]):
        """Update the suggested name when tags change"""
        if self.file_table.currentRow() >= 0:
            current_item = self.file_table.item(self.file_table.currentRow(), 1)
            if current_item:
                base_name = current_item.text().split('[')[0].strip()
                new_name = f"{base_name} {' '.join(tags)}"
                current_item.setText(new_name)

    def export_data(self, format_type: str):
        """Export rename history and file data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "csv":
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export to CSV",
                f"rename_history_{timestamp}.csv",
                "CSV Files (*.csv)"
            )
            if filename:
                try:
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            "Original Name",
                            "New Name",
                            "Status",
                            "Tags",
                            "Category"
                        ])
                        
                        # Export data from database
                        with self.db.get_session() as session:
                            files = session.query(File).all()
                            for file in files:
                                writer.writerow([
                                    file.original_name,
                                    file.new_name or "",
                                    file.status,
                                    ", ".join(tag.name for tag in file.tags),
                                    file.category if hasattr(file, 'category') else ""
                                ])
                    
                    QMessageBox.information(self, "Export Successful", 
                        f"Data exported to {filename}")
                        
                except Exception as e:
                    QMessageBox.warning(self, "Export Failed", 
                        f"Failed to export data: {str(e)}")
                    
        elif format_type == "json":
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export to JSON",
                f"rename_history_{timestamp}.json",
                "JSON Files (*.json)"
            )
            if filename:
                try:
                    export_data = []
                    with self.db.get_session() as session:
                        files = session.query(File).all()
                        for file in files:
                            export_data.append({
                                "original_name": file.original_name,
                                "new_name": file.new_name,
                                "status": file.status,
                                "tags": [tag.name for tag in file.tags],
                                "category": file.category if hasattr(file, 'category') else "",
                                "content_hash": file.content_hash,
                                "processed_date": file.last_modified.isoformat() 
                                    if file.last_modified else None
                            })
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=2)
                    
                    QMessageBox.information(self, "Export Successful", 
                        f"Data exported to {filename}")
                        
                except Exception as e:
                    QMessageBox.warning(self, "Export Failed", 
                        f"Failed to export data: {str(e)}")

    def show_preferences(self):
       dialog = PreferencesDialog(self.settings, self)
       if dialog.exec():
           # Reload any settings that affect the UI
           self.apply_settings()

    def apply_settings(self):
       # Apply settings that affect the UI or behavior
       if self.settings.get("naming", "add_category_prefix"):
           # Update any visible suggested names
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
       # Save window state
       if self.settings.get("general", "save_window_size"):
           self.settings.set("window", "size", 
               [self.width(), self.height()])
           self.settings.set("window", "position", 
               [self.x(), self.y()])

    def export_rules(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Rules",
            str(Path("rules") / "rename_rules.json"),
            "JSON Files (*.json)"
        )
        if filename:
            try:
                self.rules_manager.save_rules(filename)
                rules = self.rules_manager.rules
                rules['tag_categories'] = TagEditor.CATEGORIES
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
                self.rules_manager.validate_rules(rules)
                self.rules_manager.rules = rules
                if 'tag_categories' in rules:
                    TagEditor.CATEGORIES.update(rules['tag_categories'])
                self.refresh_suggested_names()
                QMessageBox.information(self, "Success", 
                    "Rules imported successfully")
            except ValueError as ve:
                logging.error(f"Invalid rules format: {ve}")
                QMessageBox.warning(self, "Error", 
                    f"Invalid rules format: {str(ve)}")
            except Exception as e:
                logging.error(f"Failed to import rules: {e}")
                QMessageBox.warning(self, "Error", 
                    f"Failed to import rules: {str(e)}")

    def refresh_suggested_names(self):
        for row in range(self.file_table.rowCount()):
            filename = self.file_table.item(row, 0).text()
            suggested_name = self.generate_new_name(filename)
            self.file_table.item(row, 1).setText(suggested_name)