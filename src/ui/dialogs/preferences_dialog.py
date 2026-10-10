# src/ui/dialogs/preferences_dialog.py
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QWidget,
    QFormLayout,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QLabel,
    QFileDialog,
    QMessageBox,
    QSpinBox
)
from PySide6.QtCore import Qt

from src.core.settings_manager import Settings, sanitize_tag_separator
from .base_dialog import BaseDialog

class PreferencesDialog(BaseDialog):
    """Dialog for managing application preferences"""

    # Tab indices for reference
    TAB_GENERAL = 0
    TAB_FILES = 1
    TAB_NAMING = 2
    TAB_TAGS = 3

    def __init__(self, settings: Settings, parent=None):
        self.settings = settings
        self.controls: Dict[str, Dict[str, Any]] = {}  # Store controls by section/key
        
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(600)
        self.setup_ui()

    def setup_ui(self):
        """Setup the preferences dialog UI"""
        try:
            # Create tab widget
            tab_widget = QTabWidget(self)
            self.content_layout.addWidget(tab_widget)
            
            # Add tabs
            tab_widget.addTab(self._create_general_tab(), "General")
            tab_widget.addTab(self._create_files_tab(), "Files")
            tab_widget.addTab(self._create_naming_tab(), "Naming")
            tab_widget.addTab(self._create_tags_tab(), "Tags")

            # Create buttons
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(self.save_preferences)
            save_btn.setDefault(True)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            
            button_row = self.create_button_row(save_btn, cancel_btn)
            self.main_layout.addWidget(button_row)

        except Exception as e:
            logging.error(f"Error setting up preferences dialog: {e}", exc_info=True)
            self._show_error("Failed to setup preferences dialog")

    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab"""
        try:
            widget = QWidget()
            layout = QFormLayout(widget)
            layout.setSpacing(self.SPACING)

            # Default directory
            dir_layout = QHBoxLayout()
            self.controls.setdefault("general", {})
            
            self.controls["general"]["default_directory"] = QLineEdit(
                self.settings.get("general", "default_directory", "")
            )
            dir_layout.addWidget(self.controls["general"]["default_directory"])
            
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(self._browse_directory)
            dir_layout.addWidget(browse_btn)
            
            layout.addRow("Default Directory:", dir_layout)

            # Auto check duplicates
            self.controls["general"]["auto_check_duplicates"] = QCheckBox()
            self.controls["general"]["auto_check_duplicates"].setChecked(
                self.settings.get("general", "auto_check_duplicates", True)
            )
            layout.addRow("Auto Check Duplicates:", 
                         self.controls["general"]["auto_check_duplicates"])

            # Confirm renames
            self.controls["general"]["confirm_renames"] = QCheckBox()
            self.controls["general"]["confirm_renames"].setChecked(
                self.settings.get("general", "confirm_renames", True)
            )
            layout.addRow("Confirm Renames:", 
                         self.controls["general"]["confirm_renames"])

            # Save window size
            self.controls["general"]["save_window_size"] = QCheckBox()
            self.controls["general"]["save_window_size"].setChecked(
                self.settings.get("general", "save_window_size", True)
            )
            layout.addRow("Remember Window Size:", 
                         self.controls["general"]["save_window_size"])

            return widget

        except Exception as e:
            logging.error(f"Error creating general tab: {e}", exc_info=True)
            return self._create_error_widget("Failed to create general settings tab")
    def _create_files_tab(self) -> QWidget:
        """Create the files settings tab"""
        try:
            widget = QWidget()
            layout = QFormLayout(widget)
            layout.setSpacing(self.SPACING)

            self.controls.setdefault("files", {})

            # Archive types
            self.controls["files"]["archive_types"] = QLineEdit(
                " ".join(self.settings.get("files", "archive_types", []))
            )
            layout.addRow("Archive Types (space-separated):", 
                         self.controls["files"]["archive_types"])

            # Ignore patterns
            self.controls["files"]["ignore_patterns"] = QLineEdit(
                " ".join(self.settings.get("files", "ignore_patterns", []))
            )
            layout.addRow("Ignore Patterns:", 
                         self.controls["files"]["ignore_patterns"])

            # Backup originals
            self.controls["files"]["backup_originals"] = QCheckBox()
            self.controls["files"]["backup_originals"].setChecked(
                self.settings.get("files", "backup_originals", True)
            )
            layout.addRow("Backup Original Files:", 
                         self.controls["files"]["backup_originals"])

            return widget

        except Exception as e:
            logging.error(f"Error creating files tab: {e}", exc_info=True)
            return self._create_error_widget("Failed to create files settings tab")

    def _create_naming_tab(self) -> QWidget:
        """Create the naming settings tab"""
        try:
            widget = QWidget()
            layout = QFormLayout(widget)
            layout.setSpacing(self.SPACING)

            self.controls.setdefault("naming", {})

            # Auto capitalize
            self.controls["naming"]["auto_capitalize"] = QCheckBox()
            self.controls["naming"]["auto_capitalize"].setChecked(
                self.settings.get("naming", "auto_capitalize", True)
            )
            layout.addRow("Auto Capitalize:", 
                         self.controls["naming"]["auto_capitalize"])

            # Preserve version numbers
            self.controls["naming"]["preserve_version_numbers"] = QCheckBox()
            self.controls["naming"]["preserve_version_numbers"].setChecked(
                self.settings.get("naming", "preserve_version_numbers", True)
            )
            layout.addRow("Preserve Version Numbers:", 
                         self.controls["naming"]["preserve_version_numbers"])

            # Category prefix
            self.controls["naming"]["add_category_prefix"] = QCheckBox()
            self.controls["naming"]["add_category_prefix"].setChecked(
                self.settings.get("naming", "add_category_prefix", True)
            )
            layout.addRow("Add Category Prefix:", 
                         self.controls["naming"]["add_category_prefix"])

            # Default category
            self.controls["naming"]["default_category"] = QLineEdit(
                self.settings.get("naming", "default_category", "MISC")
            )
            layout.addRow("Default Category:", 
                         self.controls["naming"]["default_category"])

            return widget

        except Exception as e:
            logging.error(f"Error creating naming tab: {e}", exc_info=True)
            return self._create_error_widget("Failed to create naming settings tab")

    def _create_tags_tab(self) -> QWidget:
        """Create the tags settings tab"""
        try:
            widget = QWidget()
            layout = QFormLayout(widget)
            layout.setSpacing(self.SPACING)

            self.controls.setdefault("tags", {})

            # Auto suggest tags
            self.controls["tags"]["auto_suggest_tags"] = QCheckBox()
            self.controls["tags"]["auto_suggest_tags"].setChecked(
                self.settings.get("tags", "auto_suggest_tags", True)
            )
            layout.addRow("Auto Suggest Tags:", 
                         self.controls["tags"]["auto_suggest_tags"])

            # Tag style
            self.controls["tags"]["tag_style"] = QComboBox()
            self.controls["tags"]["tag_style"].addItems(["brackets", "parentheses", "none"])
            self.controls["tags"]["tag_style"].setCurrentText(
                self.settings.get("tags", "tag_style", "brackets")
            )
            layout.addRow("Tag Style:", self.controls["tags"]["tag_style"])

            # Tag separator
            self.controls["tags"]["tag_separator"] = QLineEdit(
                self.settings.get("tags", "tag_separator", " ")
            )
            layout.addRow("Tag Separator:", self.controls["tags"]["tag_separator"])

            return widget

        except Exception as e:
            logging.error(f"Error creating tags tab: {e}", exc_info=True)
            return self._create_error_widget("Failed to create tags settings tab")

    def _browse_directory(self):
        """Open directory browser dialog"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Default Directory",
                self.controls["general"]["default_directory"].text()
            )
            if directory:
                self.controls["general"]["default_directory"].setText(directory)
        except Exception as e:
            logging.error(f"Error browsing directory: {e}", exc_info=True)

    def save_preferences(self):
        """Save all preferences to settings"""
        try:
            # Save General settings
            self.settings.set("general", "default_directory", 
                            self.controls["general"]["default_directory"].text())
            self.settings.set("general", "auto_check_duplicates", 
                            self.controls["general"]["auto_check_duplicates"].isChecked())
            self.settings.set("general", "confirm_renames", 
                            self.controls["general"]["confirm_renames"].isChecked())
            self.settings.set("general", "save_window_size", 
                            self.controls["general"]["save_window_size"].isChecked())

            # Save Files settings
            self.settings.set("files", "archive_types", 
                            self.controls["files"]["archive_types"].text().split())
            self.settings.set("files", "ignore_patterns", 
                            self.controls["files"]["ignore_patterns"].text().split())
            self.settings.set("files", "backup_originals", 
                            self.controls["files"]["backup_originals"].isChecked())

            # Save Naming settings
            self.settings.set("naming", "auto_capitalize", 
                            self.controls["naming"]["auto_capitalize"].isChecked())
            self.settings.set("naming", "preserve_version_numbers", 
                            self.controls["naming"]["preserve_version_numbers"].isChecked())
            self.settings.set("naming", "add_category_prefix", 
                            self.controls["naming"]["add_category_prefix"].isChecked())
            self.settings.set("naming", "default_category", 
                            self.controls["naming"]["default_category"].text())

            # Save Tags settings
            self.settings.set("tags", "auto_suggest_tags", 
                            self.controls["tags"]["auto_suggest_tags"].isChecked())
            self.settings.set("tags", "tag_style", 
                            self.controls["tags"]["tag_style"].currentText())
            
            separator = self.controls["tags"]["tag_separator"].text()
            cleaned_separator = sanitize_tag_separator(separator)
            if cleaned_separator != separator:
                QMessageBox.information(
                    self, "Tag Separator Adjusted",
                    "Characters that are not allowed in Windows filenames "
                    "were removed from the tag separator."
                )
            self.settings.set("tags", "tag_separator", cleaned_separator)

            self.accept()

        except Exception as e:
            logging.error(f"Error saving preferences: {e}", exc_info=True)
            self._show_error("Failed to save preferences")

    def _create_error_widget(self, message: str) -> QWidget:
        """Create an error display widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        error_label = QLabel(f"Error: {message}")
        error_label.setStyleSheet("color: red")
        layout.addWidget(error_label)
        return widget

    def _show_error(self, message: str):
        """Show error in the UI"""
        error_widget = self._create_error_widget(message)
        self.content_layout.addWidget(error_widget)