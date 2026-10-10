# src/tests/test_core.py
"""Behaviour tests for the core modules and duplicate handling."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
import zipfile
from pathlib import Path

import pytest

from src.core.archive_analyzer import ArchiveAnalyzer
from src.core.file_hasher import FileHasher
from src.core.rules_manager import RulesManager
from src.core.settings_manager import Settings, sanitize_tag_separator
from src.database.database import DatabaseManager
from src.database.models import File


def make_archive(directory: Path, name: str, members: dict) -> Path:
    path = directory / name
    with zipfile.ZipFile(path, "w") as archive:
        for member_name, content in members.items():
            archive.writestr(member_name, content)
    return path


class TestRulesManager:
    def test_default_category(self):
        assert RulesManager().get_default_category() == "MISC"

    def test_status_tags_do_not_conflict(self):
        tags = RulesManager().test_name("HEX3D_Flexi_Dragon_v2_nsfw.zip")["tags"]
        assert "NSFW" in tags
        assert "SFW" not in tags

    def test_validate_rules_accepts_current_rules(self):
        assert RulesManager().validate_rules() is True

    def test_validate_rules_checks_given_rules(self):
        with pytest.raises(ValueError):
            RulesManager().validate_rules({"categories": {}})


class TestArchiveAnalyzer:
    def test_suggestions_from_rules_and_content(self, tmp_path):
        archive = make_archive(
            tmp_path,
            "HEX3D_Flexi_Dragon_v2_nsfw.zip",
            {"dragon.stl": "solid", "readme.txt": "docs"},
        )

        result = ArchiveAnalyzer().analyze_archive(archive)

        assert result["suggested_category"] == "FLEXI"
        assert result["base_name"] == "Flexi Dragon"
        assert result["suggested_tags"] == ["DOCUMENTED", "HEX3D", "NSFW", "STL"]

    def test_special_pattern_overrides_category(self, tmp_path):
        archive = make_archive(
            tmp_path,
            "Sonic the Hedgehog Mask v1.5 200mm.zip",
            {"mask.stl": "solid"},
        )

        result = ArchiveAnalyzer().analyze_archive(archive)

        assert result["suggested_category"] == "PROP"
        assert result["base_name"] == "Sonic the Hedgehog Mask"
        assert "FIG" in result["suggested_tags"]

    def test_unsupported_extension_reports_error(self, tmp_path):
        path = tmp_path / "model.stl"
        path.write_bytes(b"solid")

        assert ArchiveAnalyzer().analyze_archive(path)["error"]


class TestFileHasher:
    def test_identical_files(self, tmp_path):
        first = tmp_path / "first.bin"
        second = tmp_path / "second.bin"
        first.write_bytes(b"x" * 10)
        second.write_bytes(b"x" * 10)

        assert FileHasher.are_files_identical(first, second)

    def test_different_files(self, tmp_path):
        first = tmp_path / "first.bin"
        second = tmp_path / "second.bin"
        first.write_bytes(b"x" * 10)
        second.write_bytes(b"y" * 10)

        assert not FileHasher.are_files_identical(first, second)


class TestSettings:
    def test_invalid_tag_separator_is_sanitized_on_load(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps({"tags": {"tag_separator": " |"}}), encoding="utf-8"
        )

        assert Settings(settings_file).get("tags", "tag_separator") == " "

    def test_settings_round_trip(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        Settings(settings_file).set("tags", "tag_separator", " - ")

        assert Settings(settings_file).get("tags", "tag_separator") == " - "

    def test_sanitize_tag_separator_removes_illegal_characters(self):
        assert sanitize_tag_separator("|") == ""
        assert sanitize_tag_separator(" - ") == " - "


class TestDatabaseManager:
    def test_initializes_and_creates_tables(self, tmp_path):
        db = DatabaseManager(tmp_path / "test.db")
        try:
            with db.session_scope() as session:
                assert session.query(File).count() == 0
                session.add(
                    File(
                        original_name="model.zip",
                        original_path=str(tmp_path / "model.zip"),
                    )
                )

            with db.session_scope() as session:
                assert session.query(File).count() == 1
        finally:
            db.close()


class TestDuplicateHandlerDialog:
    @pytest.fixture(autouse=True)
    def qapp(self):
        from PySide6.QtWidgets import QApplication

        yield QApplication.instance() or QApplication([])

    def make_dialog(self, tmp_path, actions):
        from src.ui.dialogs.duplicate_handler import (
            DuplicateHandlerDialog,
            DuplicatePair,
        )

        older = tmp_path / "old.zip"
        newer = tmp_path / "new.zip"
        older.write_bytes(b"identical")
        newer.write_bytes(b"identical")
        os.utime(older, (1_000_000, 1_000_000))
        os.utime(newer, (2_000_000, 2_000_000))

        db = DatabaseManager(tmp_path / "test.db")
        dialog = DuplicateHandlerDialog(
            [older, newer],
            duplicates=[
                DuplicatePair(
                    file1=older,
                    file2=newer,
                    match_type="Identical Content",
                    quick_hash="quick",
                )
            ],
            db=db,
        )
        dialog.table.cellWidget(0, 3).setCurrentText(actions)
        return dialog, older, newer, db

    def test_mark_newer_as_dupe_uses_modification_time(self, tmp_path):
        dialog, older, newer, db = self.make_dialog(tmp_path, "Mark Newer as DUPE")
        try:
            dialog.process_actions()

            assert older.exists()
            assert not newer.exists()
            assert (tmp_path / "new_DUPE.zip").exists()
            assert newer in dialog.handled_files
        finally:
            dialog.close()
            db.close()

    def test_delete_older(self, tmp_path):
        dialog, older, newer, db = self.make_dialog(tmp_path, "Delete Older")
        try:
            dialog.process_actions()

            assert not older.exists()
            assert newer.exists()
            assert older in dialog.handled_files
        finally:
            dialog.close()
            db.close()

    def test_keep_both_leaves_both_files_unhandled(self, tmp_path):
        dialog, older, newer, db = self.make_dialog(tmp_path, "Keep Both")
        try:
            dialog.process_actions()

            assert older.exists()
            assert newer.exists()
            assert dialog.handled_files == set()
        finally:
            dialog.close()
            db.close()


class TestNameGeneration:
    def test_suggested_name_uses_cleaned_base_name(self, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QApplication

        import src.ui.main_window as main_window

        QApplication.instance() or QApplication([])
        monkeypatch.setattr(
            main_window, "Settings", lambda: Settings(tmp_path / "settings.json")
        )
        monkeypatch.setattr(
            main_window,
            "DatabaseManager",
            lambda: DatabaseManager(tmp_path / "test.db"),
        )

        archive = make_archive(
            tmp_path, "HEX3D_Flexi_Dragon_v2_nsfw.zip", {"dragon.stl": "solid"}
        )
        window = main_window.MainWindow()
        window.files_to_rename = [archive]
        try:
            assert window.generate_new_name(archive.name) == (
                "FLEXI Flexi Dragon v2 [HEX3D] [NSFW] [STL]"
            )
        finally:
            window.close()
