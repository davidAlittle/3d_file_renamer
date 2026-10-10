# src/core/settings_manager.py
import copy
import json
from pathlib import Path
from typing import Any, Dict
import logging

INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def sanitize_tag_separator(separator: str) -> str:
    """Remove characters that are not allowed in Windows filenames"""
    return "".join(
        char for char in separator
        if char not in INVALID_FILENAME_CHARS and ord(char) >= 32
    )


class Settings:
    DEFAULT_SETTINGS = {
        "general": {
            "default_directory": "",
            "auto_check_duplicates": True,
            "confirm_renames": True,
            "save_window_size": True
        },
        "files": {
            "archive_types": [".zip", ".rar", ".7z"],
            "ignore_patterns": ["thumbs.db", ".ds_store"],
            "backup_originals": True
        },
        "naming": {
            "auto_capitalize": True,
            "preserve_version_numbers": True,
            "add_category_prefix": True,
            "default_category": "MISC"
        },
        "tags": {
            "auto_suggest_tags": True,
            "tag_style": "brackets",  # brackets, parentheses, or none
            "tag_separator": " "
        }
    }

    def __init__(self, settings_file: Path = None):
        # Settings and the database live together in the data directory
        self.settings_file = Path(settings_file) if settings_file else (
            Path(__file__).parent.parent / "data" / "settings.json"
        )
        
        # Create data directory if it doesn't exist
        self.data_dir = self.settings_file.parent
        self.data_dir.mkdir(exist_ok=True)
        
        self.settings = self.load_settings()

    def load_settings(self) -> Dict:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    saved_settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged = self._merge_settings(self.DEFAULT_SETTINGS, saved_settings)
                self._sanitize_settings(merged)
                return merged
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
                return copy.deepcopy(self.DEFAULT_SETTINGS)
        else:
            # If settings file doesn't exist, create it with defaults
            self.save_settings(self.DEFAULT_SETTINGS)
            return copy.deepcopy(self.DEFAULT_SETTINGS)

    def _sanitize_settings(self, settings: Dict):
        """Normalize settings values so they stay valid in Windows filenames"""
        tags = dict(settings.get("tags", {}))
        separator = tags.get("tag_separator")
        if separator is not None:
            cleaned = sanitize_tag_separator(str(separator))
            if cleaned != separator:
                logging.warning(
                    f"Adjusted tag separator {separator!r} to {cleaned!r}: "
                    "characters not allowed in Windows filenames were removed"
                )
            tags["tag_separator"] = cleaned
            settings["tags"] = tags

    def _merge_settings(self, default: Dict, saved: Dict) -> Dict:
        """Recursively merge saved settings with defaults"""
        merged = copy.deepcopy(default)
        for key, value in saved.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_settings(merged[key], value)
            else:
                merged[key] = value
        return merged

    def save_settings(self, settings: Dict = None):
        """Save current or provided settings"""
        try:
            settings_to_save = settings if settings is not None else self.settings
            with open(self.settings_file, 'w') as f:
                json.dump(settings_to_save, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            raise

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a setting value with optional default"""
        return self.settings.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any):
        """Set a setting value and save"""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self.save_settings()

    @property
    def data_directory(self) -> Path:
        """Get the data directory path"""
        return self.data_dir