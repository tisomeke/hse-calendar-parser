"""Tests for the TUI module.

Tests cover:
- _validate_file_path: file path validation logic
- _validate_output_path: output path validation logic
- show_banner, show_error, show_info, show_goodbye: rendering (smoke tests)
- show_success, show_report, show_progress: rendering (smoke tests)
- ask_choice, ask_file, ask_path, ask_toggles, ask_confirm, ask_text: mocked questionary
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_rejects_whitespace_only_path(self) -> None:
        """Should reject whitespace-only path."""
        result = _validate_file_path("   ")
        assert isinstance(result, str)

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

    def test_accepts_uppercase_extension(self) -> None:
        """Should accept .XLSX (case-insensitive)."""
        with tempfile.NamedTemporaryFile(suffix=".XLSX", delete=False) as f:
            path = Path(f.name)
        try:
            path.write_text("dummy")
            result = _validate_file_path(str(path))
            assert result is True
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_directory_path(self) -> None:
        """Should reject a directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_file_path(tmpdir)
            assert isinstance(result, str)
            assert "Excel" in result or "xlsx" in result.lower()


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

    def test_rejects_empty_path(self) -> None:
        """Should reject empty output path."""
        result = _validate_output_path("")
        assert isinstance(result, str)

    def test_rejects_path_without_filename(self) -> None:
        """Should reject path without a filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_output_path(str(tmpdir))
            assert isinstance(result, str)

    def test_accepts_uppercase_ics(self) -> None:
        """Should accept .ICS extension (case-insensitive)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _validate_output_path(f"{tmpdir}/schedule.ICS")
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

    def test_show_error_with_unicode(self) -> None:
        """show_error with unicode characters should not raise."""
        from hse_schedule_parser.tui import show_error
        show_error("❌ Ошибка: файл не найден", "📁 Проверь путь")

    def test_show_info_runs(self) -> None:
        """show_info should not raise."""
        from hse_schedule_parser.tui import show_info
        show_info("Test info message")

    def test_show_info_with_multiline(self) -> None:
        """show_info with multiline message should not raise."""
        from hse_schedule_parser.tui import show_info
        show_info("Line 1\nLine 2\nLine 3")

    def test_show_goodbye_runs(self) -> None:
        """show_goodbye should not raise."""
        from hse_schedule_parser.tui import show_goodbye
        show_goodbye()

    def test_show_progress_runs(self) -> None:
        """show_progress should create a Progress object."""
        from hse_schedule_parser.tui import show_progress
        progress = show_progress()
        assert progress is not None

    def test_show_success_with_path(self) -> None:
        """show_success with a path should not raise."""
        from hse_schedule_parser.tui import show_success
        show_success(ics_path=Path("/tmp/schedule.ics"))

    def test_show_success_without_path(self) -> None:
        """show_success without path should not raise."""
        from hse_schedule_parser.tui import show_success
        show_success(ics_path=None)

    def test_show_report_runs(self) -> None:
        """show_report should not raise."""
        from hse_schedule_parser.tui import show_report
        show_report(
            report_text="Test report\nLine 2",
            warnings=[],
            events_count=42,
        )

    def test_show_report_zero_events(self) -> None:
        """show_report with zero events should not raise."""
        from hse_schedule_parser.tui import show_report
        show_report(
            report_text="No events",
            warnings=[],
            events_count=0,
        )


# ── Mocked questionary interaction tests ────────────────────────────────
# Note: questionary is imported inside function bodies (import questionary),
# so we patch at the module level: "questionary.select", "questionary.text", etc.


class TestAskChoice:
    """Tests for ask_choice() with mocked questionary."""

    @patch("questionary.select")
    def test_returns_selected_value(self, mock_select: MagicMock) -> None:
        """Should return the selected value."""
        mock_select.return_value.ask.return_value = "Option B"
        from hse_schedule_parser.tui import ask_choice

        result = ask_choice("Test?", ["Option A", "Option B", "Option C"])
        assert result == "Option B"

    @patch("questionary.select")
    def test_returns_none_on_cancel(self, mock_select: MagicMock) -> None:
        """Should return None when user cancels."""
        mock_select.return_value.ask.return_value = None
        from hse_schedule_parser.tui import ask_choice

        result = ask_choice("Test?", ["A", "B"])
        assert result is None

    @patch("questionary.select")
    def test_returns_none_on_empty_choices(self, mock_select: MagicMock) -> None:
        """Should return None when choices list is empty."""
        from hse_schedule_parser.tui import ask_choice

        result = ask_choice("Test?", [])
        assert result is None
        mock_select.return_value.ask.assert_not_called()

    @patch("questionary.select")
    def test_uses_default(self, mock_select: MagicMock) -> None:
        """Should pass default to questionary."""
        mock_select.return_value.ask.return_value = "B"
        from hse_schedule_parser.tui import ask_choice

        ask_choice("Test?", ["A", "B", "C"], default="C")
        call_kwargs = mock_select.call_args[1]
        assert call_kwargs["default"] == "C"

    @patch("questionary.select")
    def test_single_choice_returns_it(self, mock_select: MagicMock) -> None:
        """Should work with a single choice."""
        mock_select.return_value.ask.return_value = "Only"
        from hse_schedule_parser.tui import ask_choice

        result = ask_choice("Test?", ["Only"])
        assert result == "Only"


class TestAskFile:
    """Tests for ask_file() with mocked questionary."""

    @patch("questionary.text")
    def test_returns_path(self, mock_text: MagicMock) -> None:
        """Should return the entered path."""
        mock_text.return_value.ask.return_value = "/path/to/file.xlsx"
        from hse_schedule_parser.tui import ask_file

        result = ask_file("Enter path:", default="/default.xlsx")
        assert result == "/path/to/file.xlsx"

    @patch("questionary.text")
    def test_returns_none_on_cancel(self, mock_text: MagicMock) -> None:
        """Should return None when user cancels."""
        mock_text.return_value.ask.return_value = None
        from hse_schedule_parser.tui import ask_file

        result = ask_file("Enter path:")
        assert result is None

    @patch("questionary.text")
    def test_passes_validation(self, mock_text: MagicMock) -> None:
        """Should pass validate function to questionary."""
        mock_text.return_value.ask.return_value = "/valid.xlsx"
        from hse_schedule_parser.tui import ask_file

        ask_file("Enter path:", default="/default.xlsx")
        call_kwargs = mock_text.call_args[1]
        assert call_kwargs["validate"] is not None



class TestAskToggles:
    """Tests for ask_toggles() with mocked questionary."""

    @patch("questionary.checkbox")
    def test_returns_all_checked(self, mock_checkbox: MagicMock) -> None:
        """Should return True for checked items."""
        mock_checkbox.return_value.ask.return_value = ["A", "B"]
        from hse_schedule_parser.tui import ask_toggles

        result = ask_toggles("Test?", toggles={"A": True, "B": True, "C": False})
        assert result == {"A": True, "B": True, "C": False}

    @patch("questionary.checkbox")
    def test_returns_none_on_cancel(self, mock_checkbox: MagicMock) -> None:
        """Should return None when user cancels."""
        mock_checkbox.return_value.ask.return_value = None
        from hse_schedule_parser.tui import ask_toggles

        result = ask_toggles("Test?", toggles={"A": True})
        assert result is None

    @patch("questionary.checkbox")
    def test_empty_toggles(self, mock_checkbox: MagicMock) -> None:
        """Should handle empty toggles dict."""
        mock_checkbox.return_value.ask.return_value = []
        from hse_schedule_parser.tui import ask_toggles

        result = ask_toggles("Test?", toggles={})
        assert result == {}

    @patch("questionary.checkbox")
    def test_some_unchecked(self, mock_checkbox: MagicMock) -> None:
        """Should return False for unchecked items."""
        mock_checkbox.return_value.ask.return_value = ["A"]
        from hse_schedule_parser.tui import ask_toggles

        result = ask_toggles("Test?", toggles={"A": True, "B": True})
        assert result == {"A": True, "B": False}


class TestAskConfirm:
    """Tests for ask_confirm() with mocked questionary."""

    @patch("questionary.confirm")
    def test_returns_true(self, mock_confirm: MagicMock) -> None:
        """Should return True when confirmed."""
        mock_confirm.return_value.ask.return_value = True
        from hse_schedule_parser.tui import ask_confirm

        result = ask_confirm("Continue?", default=True)
        assert result is True

    @patch("questionary.confirm")
    def test_returns_false(self, mock_confirm: MagicMock) -> None:
        """Should return False when declined."""
        mock_confirm.return_value.ask.return_value = False
        from hse_schedule_parser.tui import ask_confirm

        result = ask_confirm("Continue?", default=True)
        assert result is False

    @patch("questionary.confirm")
    def test_returns_none_on_cancel(self, mock_confirm: MagicMock) -> None:
        """Should return None when user cancels."""
        mock_confirm.return_value.ask.return_value = None
        from hse_schedule_parser.tui import ask_confirm

        result = ask_confirm("Continue?")
        assert result is None

    @patch("questionary.confirm")
    def test_passes_default(self, mock_confirm: MagicMock) -> None:
        """Should pass default to questionary."""
        mock_confirm.return_value.ask.return_value = True
        from hse_schedule_parser.tui import ask_confirm

        ask_confirm("Continue?", default=False)
        call_kwargs = mock_confirm.call_args[1]
        assert call_kwargs["default"] is False


class TestAskText:
    """Tests for ask_text() with mocked questionary."""

    @patch("questionary.text")
    def test_returns_text(self, mock_text: MagicMock) -> None:
        """Should return the entered text."""
        mock_text.return_value.ask.return_value = "user input"
        from hse_schedule_parser.tui import ask_text

        result = ask_text("Enter:", default="")
        assert result == "user input"

    @patch("questionary.text")
    def test_returns_none_on_cancel(self, mock_text: MagicMock) -> None:
        """Should return None when user cancels."""
        mock_text.return_value.ask.return_value = None
        from hse_schedule_parser.tui import ask_text

        result = ask_text("Enter:")
        assert result is None

    @patch("questionary.text")
    def test_passes_validation(self, mock_text: MagicMock) -> None:
        """Should pass validate function to questionary."""
        mock_text.return_value.ask.return_value = "valid"
        from hse_schedule_parser.tui import ask_text

        validate_fn = lambda v: True
        ask_text("Enter:", validate=validate_fn)
        call_kwargs = mock_text.call_args[1]
        assert call_kwargs["validate"] is validate_fn

    @patch("questionary.text")
    def test_passes_default(self, mock_text: MagicMock) -> None:
        """Should pass default to questionary."""
        mock_text.return_value.ask.return_value = "text"
        from hse_schedule_parser.tui import ask_text

        ask_text("Enter:", default="default_val")
        call_kwargs = mock_text.call_args[1]
        assert call_kwargs["default"] == "default_val"