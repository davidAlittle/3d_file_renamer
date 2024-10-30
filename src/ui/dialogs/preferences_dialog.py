# src/ui/dialogs/preferences_dialog.py
from PySide6.QtWidgets import (
    QDialog,
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
    QFileDialog
)
from src.core.settings_manager import Settings
from .base_dialog import BaseDialog

class PreferencesDialog(BaseDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()
        
        # Add tabs
        tab_widget.addTab(self._create_general_tab(), "General")
        tab_widget.addTab(self._create_files_tab(), "Files")
        tab_widget.addTab(self._create_naming_tab(), "Naming")
        tab_widget.addTab(self._create_tags_tab(), "Tags")
        
        layout.addWidget(tab_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_preferences)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def _create_general_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # Default directory
        self.default_dir = QLineEdit(
            self.settings.get("general", "default_directory")
        )
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_directory)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.default_dir)
        dir_layout.addWidget(browse_btn)
        layout.addRow("Default Directory:", dir_layout)

        # Auto check duplicates
        self.auto_check_dupes = QCheckBox()
        self.auto_check_dupes.setChecked(
            self.settings.get("general", "auto_check_duplicates")
        )
        layout.addRow("Auto Check Duplicates:", self.auto_check_dupes)

        # Confirm renames
        self.confirm_renames = QCheckBox()
        self.confirm_renames.setChecked(
            self.settings.get("general", "confirm_renames")
        )
        layout.addRow("Confirm Renames:", self.confirm_renames)

        return widget

    def _create_files_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # Archive types
        self.archive_types = QLineEdit(
            " ".join(self.settings.get("files", "archive_types"))
        )
        layout.addRow("Archive Types (space-separated):", self.archive_types)

        # Ignore patterns
        self.ignore_patterns = QLineEdit(
            " ".join(self.settings.get("files", "ignore_patterns"))
        )
        layout.addRow("Ignore Patterns:", self.ignore_patterns)

        # Backup originals
        self.backup_originals = QCheckBox()
        self.backup_originals.setChecked(
            self.settings.get("files", "backup_originals")
        )
        layout.addRow("Backup Original Files:", self.backup_originals)

        return widget

    def _create_naming_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # Auto capitalize
        self.auto_capitalize = QCheckBox()
        self.auto_capitalize.setChecked(
            self.settings.get("naming", "auto_capitalize")
        )
        layout.addRow("Auto Capitalize:", self.auto_capitalize)

        # Preserve version numbers
        self.preserve_versions = QCheckBox()
        self.preserve_versions.setChecked(
            self.settings.get("naming", "preserve_version_numbers")
        )
        layout.addRow("Preserve Version Numbers:", self.preserve_versions)

        # Category prefix
        self.add_category = QCheckBox()
        self.add_category.setChecked(
            self.settings.get("naming", "add_category_prefix")
        )
        layout.addRow("Add Category Prefix:", self.add_category)

        # Default category
        self.default_category = QLineEdit(
            self.settings.get("naming", "default_category")
        )
        layout.addRow("Default Category:", self.default_category)

        return widget

    def _create_tags_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # Auto suggest tags
        self.auto_suggest_tags = QCheckBox()
        self.auto_suggest_tags.setChecked(
            self.settings.get("tags", "auto_suggest_tags")
        )
        layout.addRow("Auto Suggest Tags:", self.auto_suggest_tags)

        # Tag style
        self.tag_style = QComboBox()
        self.tag_style.addItems(["brackets", "parentheses", "none"])
        self.tag_style.setCurrentText(
            self.settings.get("tags", "tag_style")
        )
        layout.addRow("Tag Style:", self.tag_style)

        # Tag separator
        self.tag_separator = QLineEdit(
            self.settings.get("tags", "tag_separator")
        )
        layout.addRow("Tag Separator:", self.tag_separator)

        return widget

    def _browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Directory",
            self.default_dir.text()
        )
        if directory:
            self.default_dir.setText(directory)

    def save_preferences(self):
        # Save General settings
        self.settings.set("general", "default_directory", self.default_dir.text())
        self.settings.set("general", "auto_check_duplicates", 
                         self.auto_check_dupes.isChecked())
        self.settings.set("general", "confirm_renames", 
                         self.confirm_renames.isChecked())

        # Save Files settings
        self.settings.set("files", "archive_types", 
                         self.archive_types.text().split())
        self.settings.set("files", "ignore_patterns", 
                         self.ignore_patterns.text().split())
        self.settings.set("files", "backup_originals", 
                         self.backup_originals.isChecked())

        # Save Naming settings
        self.settings.set("naming", "auto_capitalize", 
                         self.auto_capitalize.isChecked())
        self.settings.set("naming", "preserve_version_numbers", 
                         self.preserve_versions.isChecked())
        self.settings.set("naming", "add_category_prefix", 
                         self.add_category.isChecked())
        self.settings.set("naming", "default_category", 
                         self.default_category.text())

        # Save Tags settings
        self.settings.set("tags", "auto_suggest_tags", 
                         self.auto_suggest_tags.isChecked())
        self.settings.set("tags", "tag_style", 
                         self.tag_style.currentText())
        self.settings.set("tags", "tag_separator", 
                         self.tag_separator.text())

        self.accept()