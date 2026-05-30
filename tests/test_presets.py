"""Tests for the presets module.

Tests cover:
- UserPresets dataclass default values
- load_presets from disk
- save_presets to disk
- update_presets convenience function
- Config directory resolution per platform
- Edge cases: empty JSON, missing fields, type coercion
"""

from __future__ import annotations

import json
import platform
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from hse_schedule_parser.presets import (
    UserPresets,
    _get_config_dir,
    _get_presets_path,
    load_presets,
    save_presets,
    update_presets,
)


# ── UserPresets ─────────────────────────────────────────────────────────


class TestUserPresets:
    """Tests for the UserPresets dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        p = UserPresets()
        assert p.last_file_path == ""
        assert p.last_group_code == ""
        assert p.last_course == 0
        assert p.last_subgroup is None
        assert p.skip_minor is True
        assert p.skip_english is True
        assert p.skip_pe is True
        assert p.last_output_dir == ""
        assert p.last_academic_year == 0

    def test_is_empty_returns_true_for_defaults(self) -> None:
        """Should return True when no meaningful data."""
        p = UserPresets()
        assert p.is_empty() is True

    def test_is_empty_returns_false_with_file_path(self) -> None:
        """Should return False when file path is set."""
        p = UserPresets(last_file_path="/some/file.xlsx")
        assert p.is_empty() is False

    def test_is_empty_returns_false_with_group_code(self) -> None:
        """Should return False when group code is set."""
        p = UserPresets(last_group_code="25ФПЛ1")
        assert p.is_empty() is False

    def test_custom_values(self) -> None:
        """Should store custom values correctly."""
        p = UserPresets(
            last_file_path="/path/to/file.xlsx",
            last_group_code="25ФПЛ1",
            last_course=1,
            last_subgroup=2,
            skip_minor=False,
            skip_english=True,
            skip_pe=False,
            last_output_dir="/home/user/Downloads",
            last_academic_year=2025,
        )
        assert p.last_file_path == "/path/to/file.xlsx"
        assert p.last_group_code == "25ФПЛ1"
        assert p.last_course == 1
        assert p.last_subgroup == 2
        assert p.skip_minor is False
        assert p.skip_english is True
        assert p.skip_pe is False
        assert p.last_output_dir == "/home/user/Downloads"
        assert p.last_academic_year == 2025

    def test_subgroup_none_by_default(self) -> None:
        """Should have subgroup as None by default."""
        p = UserPresets()
        assert p.last_subgroup is None

    def test_subgroup_zero_is_valid(self) -> None:
        """Should accept subgroup=0 as a valid value."""
        p = UserPresets(last_subgroup=0)
        assert p.last_subgroup == 0

    def test_academic_year_zero_by_default(self) -> None:
        """Should have academic_year as 0 by default."""
        p = UserPresets()
        assert p.last_academic_year == 0


# ── Config directory ────────────────────────────────────────────────────


class TestGetConfigDir:
    """Tests for _get_config_dir()."""

    @patch("hse_schedule_parser.presets.platform.system")
    def test_linux_config_dir(self, mock_system) -> None:
        """Should use ~/.config on Linux."""
        mock_system.return_value = "Linux"
        config_dir = _get_config_dir()
        assert str(config_dir).endswith(".config/hse-schedule-parser")

    @patch("hse_schedule_parser.presets.platform.system")
    def test_macos_config_dir(self, mock_system) -> None:
        """Should use ~/Library/Application Support on macOS."""
        mock_system.return_value = "Darwin"
        config_dir = _get_config_dir()
        assert "Library/Application Support" in str(config_dir)

    @patch("hse_schedule_parser.presets.platform.system")
    def test_windows_config_dir(self, mock_system) -> None:
        """Should use %APPDATA% on Windows."""
        mock_system.return_value = "Windows"
        config_dir = _get_config_dir()
        assert "AppData/Roaming" in str(config_dir)

    def test_presets_path_ends_correctly(self) -> None:
        """Should end with presets.json."""
        path = _get_presets_path()
        assert path.name == "presets.json"

    @patch("hse_schedule_parser.presets.platform.system")
    def test_unknown_os_falls_back_to_linux(self, mock_system) -> None:
        """Should fall back to Linux-style config dir for unknown OS."""
        mock_system.return_value = "FreeBSD"
        config_dir = _get_config_dir()
        assert str(config_dir).endswith(".config/hse-schedule-parser")


# ── Save and Load ───────────────────────────────────────────────────────


class TestSaveLoadPresets:
    """Tests for save_presets() and load_presets()."""

    @pytest.fixture(autouse=True)
    def temp_config_dir(self, tmp_path: Path) -> None:
        """Override config dir to a temp directory for each test."""
        patcher = patch(
            "hse_schedule_parser.presets._get_config_dir",
            return_value=tmp_path / ".config" / "hse-schedule-parser",
        )
        patcher.start()
        yield
        patcher.stop()

    def test_save_and_load_roundtrip(self) -> None:
        """Should save and load presets correctly."""
        presets = UserPresets(
            last_file_path="/test/file.xlsx",
            last_group_code="25ФПЛ1",
            last_course=1,
            last_subgroup=2,
            skip_minor=False,
            skip_english=True,
            skip_pe=False,
            last_output_dir="/test/output",
            last_academic_year=2025,
        )

        assert save_presets(presets) is True

        loaded = load_presets()
        assert loaded.last_file_path == "/test/file.xlsx"
        assert loaded.last_group_code == "25ФПЛ1"
        assert loaded.last_course == 1
        assert loaded.last_subgroup == 2
        assert loaded.skip_minor is False
        assert loaded.skip_english is True
        assert loaded.skip_pe is False
        assert loaded.last_output_dir == "/test/output"
        assert loaded.last_academic_year == 2025

    def test_load_returns_defaults_when_no_file(self) -> None:
        """Should return default UserPresets when no file exists."""
        presets = load_presets()
        assert presets.is_empty() is True

    def test_load_handles_corrupted_json(self) -> None:
        """Should return defaults when JSON is corrupted."""
        path = _get_presets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json", encoding="utf-8")

        presets = load_presets()
        assert presets.is_empty() is True

    def test_load_filters_unknown_fields(self) -> None:
        """Should ignore unknown fields in JSON."""
        path = _get_presets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_file_path": "/test/file.xlsx",
            "unknown_field": "should be ignored",
            "skip_minor": False,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loaded = load_presets()
        assert loaded.last_file_path == "/test/file.xlsx"
        assert loaded.skip_minor is False
        assert not hasattr(loaded, "unknown_field")

    def test_save_creates_directory(self) -> None:
        """Should create config directory if it doesn't exist."""
        presets = UserPresets(last_file_path="/test.xlsx")
        assert save_presets(presets) is True
        assert _get_presets_path().exists()

    def test_save_returns_false_on_error(self) -> None:
        """Should return False when save fails."""
        # Point to a path that can't be written
        with patch(
            "hse_schedule_parser.presets._get_presets_path",
            return_value=Path("/nonexistent/deep/dir/presets.json"),
        ):
            result = save_presets(UserPresets())
            assert result is False

    def test_load_handles_empty_json_object(self) -> None:
        """Should return defaults for empty JSON object."""
        path = _get_presets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

        presets = load_presets()
        assert presets.is_empty() is True

    def test_load_handles_null_values(self) -> None:
        """Should handle null values in JSON gracefully."""
        path = _get_presets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_file_path": None,
            "last_group_code": None,
            "skip_minor": None,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        presets = load_presets()
        # None values are passed through to the dataclass constructor
        assert presets.last_file_path is None
        assert presets.last_group_code is None
        # skip_minor default is True, but None overrides it
        assert presets.skip_minor is None

    def test_save_overwrites_existing(self) -> None:
        """Should overwrite existing presets file."""
        presets1 = UserPresets(last_file_path="/first.xlsx")
        save_presets(presets1)

        presets2 = UserPresets(last_file_path="/second.xlsx")
        save_presets(presets2)

        loaded = load_presets()
        assert loaded.last_file_path == "/second.xlsx"

    def test_load_handles_partial_data(self) -> None:
        """Should merge partial data with defaults."""
        path = _get_presets_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"last_file_path": "/partial.xlsx"}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loaded = load_presets()
        assert loaded.last_file_path == "/partial.xlsx"
        assert loaded.last_group_code == ""  # default
        assert loaded.skip_minor is True  # default


# ── update_presets ──────────────────────────────────────────────────────


class TestUpdatePresets:
    """Tests for update_presets()."""

    @pytest.fixture(autouse=True)
    def temp_config_dir(self, tmp_path: Path) -> None:
        patcher = patch(
            "hse_schedule_parser.presets._get_config_dir",
            return_value=tmp_path / ".config" / "hse-schedule-parser",
        )
        patcher.start()
        yield
        patcher.stop()

    def test_updates_single_field(self) -> None:
        """Should update a single field and save."""
        updated = update_presets(last_file_path="/new/file.xlsx")
        assert updated.last_file_path == "/new/file.xlsx"

        # Verify it was saved
        loaded = load_presets()
        assert loaded.last_file_path == "/new/file.xlsx"

    def test_updates_multiple_fields(self) -> None:
        """Should update multiple fields and save."""
        updated = update_presets(
            last_file_path="/multi.xlsx",
            last_group_code="25ФПЛ2",
            skip_minor=False,
        )
        assert updated.last_file_path == "/multi.xlsx"
        assert updated.last_group_code == "25ФПЛ2"
        assert updated.skip_minor is False

    def test_ignores_unknown_fields(self) -> None:
        """Should ignore unknown kwargs."""
        updated = update_presets(
            last_file_path="/test.xlsx",
            nonexistent_field="value",
        )
        assert updated.last_file_path == "/test.xlsx"
        assert not hasattr(updated, "nonexistent_field")

    def test_update_preserves_existing_values(self) -> None:
        """Should preserve existing values when updating only some fields."""
        update_presets(last_file_path="/existing.xlsx", last_group_code="25ФПЛ1")

        updated = update_presets(last_file_path="/updated.xlsx")
        assert updated.last_file_path == "/updated.xlsx"
        assert updated.last_group_code == "25ФПЛ1"  # preserved

    def test_update_with_no_args_returns_defaults(self) -> None:
        """Should return defaults when no args given and no file exists."""
        updated = update_presets()
        assert updated.is_empty() is True