"""Tests for the TUI module.

Tests cover:
- _validate_file_path: file path validation logic
- _validate_output_path: output path validation logic
- show_banner, show_error, show_info, show_goodbye: rendering (smoke tests)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from hse_schedule_parser.tui import (
    _validate_file_path,
    _validate_output_path,
)


# ── _validate_file_path ─────────────────────────────────────────────────


class TestValidateFilePath:
    """Tests for _validate_file_path()."""

    def test_rejects_empty_path(self) -> None:
        """Should reject empty path with error message."""
        result = _validate_file_path("")
        assert isinstance(result, str)
        assert "не может быть пустым" in result.lower() or "путь" in result.lower()

    def test_rejects_nonexistent_file(self) -> None:
        """Should reject non-existent file path."""
        result = _validate_file_path("/nonexistent/file.xlsx")
        assert isinstance(result, str)
        assert "не найден" in result.lower()

    def test_rejects_non_excel_extension(self) -> None:
        """Should reject non-Excel file extensions."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text("dummy")
            result = _validate_file_path(str(path))
            assert isinstance(result, str)
            assert "Excel" in result or "xlsx" in result.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_accepts_existing_xlsx(self) -> None:
        """Should accept existing .xlsx file."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text("dummy content")
            result = _validate_file_path(str(path))
            assert result is True
        finally:
            path.unlink(missing_ok=True)

    def test_accepts_existing_xls(self) -> None:
        """Should accept existing .xls file."""
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text("dummy content")
            result = _validate_file_path(str(path))
            assert result is True
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_existing_non_excel(self) -> None:
        """Should reject existing file with non-Excel extension."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text("a,b,c")
            result = _validate_file_path(str(path))
            assert isinstance(result, str)
            assert "Excel" in result or "xlsx" in result.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_strips_whitespace(self) -> None:
        """Should strip whitespace from path."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text("dummy")
            result = _validate_file_path(f"  {path}  ")
            assert result is True
        finally:
            path.unlink(missing_ok=True)


# ── _validate_output_path ───────────────────────────────────────────────


class TestValidateOutputPath:
    """Tests for _validate_output_path()."""

    def test_rejects_nonexistent_parent_dir(self) -> None:
        """Should reject path where parent directory doesn't exist."""
        result = _validate_output_path("/nonexistent/deep/dir/output.ics")
        assert isinstance(result, str)
        assert "не существует" in result.lower() or "папк" in result.lower()

    def test_rejects_non_ics_extension(self) -> None:
        """Should reject non-.ics extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_output_path(f"{tmpdir}/output.txt")
            assert isinstance(result, str)
            assert "ics" in result.lower()

    def test_accepts_valid_path(self) -> None:
        """Should accept valid path with .ics extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_output_path(f"{tmpdir}/schedule.ics")
            assert result is True

    def test_strips_whitespace(self) -> None:
        """Should strip whitespace from path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_output_path(f"  {tmpdir}/schedule.ics  ")
            assert result is True


# ── Smoke tests for display functions ───────────────────────────────────


class TestDisplayFunctions:
    """Smoke tests for display functions (just ensure they don't crash)."""

    def test_show_banner_runs(self) -> None:
        """show_banner should not raise."""
        from hse_schedule_parser.tui import show_banner
        show_banner()

    def test_show_error_runs(self) -> None:
        """show_error should not raise."""
        from hse_schedule_parser.tui import show_error
        show_error("Test error", "Test hint")

    def test_show_error_without_hint(self) -> None:
        """show_error without hint should not raise."""
        from hse_schedule_parser.tui import show_error
        show_error("Test error")

    def test_show_info_runs(self) -> None:
        """show_info should not raise."""
        from hse_schedule_parser.tui import show_info
        show_info("Test info message")

    def test_show_goodbye_runs(self) -> None:
        """show_goodbye should not raise."""
        from hse_schedule_parser.tui import show_goodbye
        show_goodbye()

    def test_show_progress_runs(self) -> None:
        """show_progress should create a Progress object."""
        from hse_schedule_parser.tui import show_progress
        progress = show_progress()
        assert progress is not None