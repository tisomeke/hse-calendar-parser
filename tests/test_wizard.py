"""Tests for the wizard module.

Tests cover:
- WizardState: initialization, to_presets conversion
- _build_config: building ParseConfig from WizardState
- _find_excel_in_root: scanning for .xlsx files
- step_file, step_group, step_subgroup, step_settings, step_output: mocked
- run_wizard, _run_wizard_impl: entry points
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from hse_schedule_parser.presets import UserPresets
from hse_schedule_parser.wizard import (
    WizardState,
    _build_config,
    _find_excel_in_root,
    step_file,
    step_group,
    step_output,
    step_settings,
    step_subgroup,
)


# ── WizardState ─────────────────────────────────────────────────────────


class TestWizardState:
    """Tests for the WizardState dataclass."""

    def test_default_initialization(self) -> None:
        """Should initialize with default values."""
        state = WizardState()
        assert state.file_path == ""
        assert state.course == 0
        assert state.group_code == ""
        assert state.subgroup is None
        assert state.skip_minor is True
        assert state.skip_english is True
        assert state.skip_pe is True
        assert state.output_path == ""
        assert state.preview_only is False
        assert state._available_courses == []
        assert state._available_groups == []
        assert state._available_subgroups == []

    def test_initialization_with_presets(self) -> None:
        """Should initialize from presets."""
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
        state = WizardState(presets=presets)
        assert state.file_path == "/test/file.xlsx"
        assert state.course == 1
        assert state.group_code == "25ФПЛ1"
        assert state.subgroup == 2
        assert state.skip_minor is False
        assert state.skip_english is True
        assert state.skip_pe is False
        assert state.output_path == "/test/output"

    def test_initialization_with_empty_presets(self) -> None:
        """Should use defaults when presets are empty."""
        presets = UserPresets()
        state = WizardState(presets=presets)
        assert state.file_path == ""
        assert state.course == 0
        assert state.group_code == ""
        assert state.subgroup is None

    def test_to_presets_conversion(self) -> None:
        """Should convert state to UserPresets correctly."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"
        state.course = 1
        state.subgroup = 2
        state.skip_minor = False
        state.skip_english = True
        state.skip_pe = False
        state.output_path = "/test/output/schedule.ics"
        state.academic_year = 2025

        presets = state.to_presets()
        assert presets.last_file_path == "/test/file.xlsx"
        assert presets.last_group_code == "25ФПЛ1"
        assert presets.last_course == 1
        assert presets.last_subgroup == 2
        assert presets.skip_minor is False
        assert presets.skip_english is True
        assert presets.skip_pe is False
        assert presets.last_output_dir == "/test/output"
        assert presets.last_academic_year == 2025

    def test_to_presets_with_empty_output(self) -> None:
        """Should handle empty output path in to_presets."""
        state = WizardState()
        state.output_path = ""
        presets = state.to_presets()
        assert presets.last_output_dir == ""

    def test_to_presets_with_none_subgroup(self) -> None:
        """Should handle None subgroup in to_presets."""
        state = WizardState()
        state.subgroup = None
        presets = state.to_presets()
        assert presets.last_subgroup is None

    def test_academic_year_from_presets(self) -> None:
        """Should use presets academic year when available."""
        presets = UserPresets(last_academic_year=2024)
        state = WizardState(presets=presets)
        assert state.academic_year == 2024

    def test_skip_flags_default_to_true(self) -> None:
        """Should default skip flags to True."""
        state = WizardState()
        assert state.skip_minor is True
        assert state.skip_english is True
        assert state.skip_pe is True

    def test_skip_flags_from_presets(self) -> None:
        """Should use presets skip flags."""
        presets = UserPresets(skip_minor=False, skip_english=False, skip_pe=False)
        state = WizardState(presets=presets)
        assert state.skip_minor is False
        assert state.skip_english is False
        assert state.skip_pe is False


# ── _build_config ───────────────────────────────────────────────────────


class TestBuildConfig:
    """Tests for _build_config()."""

    def test_builds_config_with_all_fields(self) -> None:
        """Should build ParseConfig with all fields."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"
        state.course = 1
        state.subgroup = 2
        state.academic_year = 2025
        state.skip_minor = False
        state.skip_english = True
        state.skip_pe = False
        state.output_path = "/test/output/schedule.ics"

        config = _build_config(state)
        assert str(config.file_path) == "/test/file.xlsx"
        assert config.group_code == "25ФПЛ1"
        assert config.subgroup == 2
        assert config.academic_year_start == 2025
        assert config.skip_minor is False
        assert config.skip_english is True
        assert config.skip_pe is False
        assert str(config.output_path) == "/test/output/schedule.ics"
        assert config.verbose is False

    def test_builds_config_without_output(self) -> None:
        """Should build config with output_path=None when empty."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"
        state.output_path = ""

        config = _build_config(state)
        assert config.output_path is None

    def test_builds_config_without_subgroup(self) -> None:
        """Should build config with subgroup=None when not set."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"
        state.subgroup = None

        config = _build_config(state)
        assert config.subgroup is None


# ── _find_excel_in_root ─────────────────────────────────────────────────


class TestFindExcelInRoot:
    """Tests for _find_excel_in_root()."""

    def test_returns_empty_when_no_xlsx(self, tmp_path: Path) -> None:
        """Should return empty list when no .xlsx files."""
        with patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path):
            result = _find_excel_in_root()
            assert result == []

    def test_finds_single_xlsx(self, tmp_path: Path) -> None:
        """Should find a single .xlsx file."""
        (tmp_path / "schedule.xlsx").write_text("dummy")
        with patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path):
            result = _find_excel_in_root()
            assert len(result) == 1
            assert result[0].name == "schedule.xlsx"

    def test_finds_multiple_xlsx(self, tmp_path: Path) -> None:
        """Should find multiple .xlsx files."""
        (tmp_path / "a.xlsx").write_text("dummy")
        (tmp_path / "b.xlsx").write_text("dummy")
        with patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path):
            result = _find_excel_in_root()
            assert len(result) == 2

    def test_ignores_non_xlsx(self, tmp_path: Path) -> None:
        """Should ignore non-.xlsx files."""
        (tmp_path / "data.txt").write_text("dummy")
        (tmp_path / "data.csv").write_text("dummy")
        with patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path):
            result = _find_excel_in_root()
            assert result == []

    def test_returns_sorted_results(self, tmp_path: Path) -> None:
        """Should return sorted file list."""
        (tmp_path / "z.xlsx").write_text("dummy")
        (tmp_path / "a.xlsx").write_text("dummy")
        (tmp_path / "m.xlsx").write_text("dummy")
        with patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path):
            result = _find_excel_in_root()
            names = [f.name for f in result]
            assert names == sorted(names)


# ── step_file (mocked) ──────────────────────────────────────────────────


class TestStepFile:
    """Tests for step_file() with mocked UI and filesystem."""

    def test_uses_found_file(self, tmp_path: Path) -> None:
        """Should use the first found .xlsx file when option 1 chosen."""
        xlsx = tmp_path / "schedule.xlsx"
        xlsx.write_text("dummy")

        state = WizardState()

        with (
            patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "1 — продолжить с найденным файлом: schedule.xlsx"
            result = step_file(state)

        assert result is not None
        assert result.file_path.endswith("schedule.xlsx")

    def test_manual_path_input(self, tmp_path: Path) -> None:
        """Should accept manual path when option 2 chosen."""
        xlsx = tmp_path / "custom.xlsx"
        xlsx.write_text("dummy")

        state = WizardState()

        with (
            patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.ask_file") as mock_file,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "2 — указать полный путь к таблице с расписанием"
            mock_file.return_value = str(xlsx)
            result = step_file(state)

        assert result is not None
        assert result.file_path == str(xlsx)

    def test_exit_on_cancel(self, tmp_path: Path) -> None:
        """Should return None when user cancels."""
        state = WizardState()

        with (
            patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "✕ Выход"
            result = step_file(state)

        assert result is None

    def test_no_files_found_shows_error(self, tmp_path: Path) -> None:
        """Should show error when no .xlsx files in root."""
        state = WizardState()

        with (
            patch("hse_schedule_parser.wizard.Path.cwd", return_value=tmp_path),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_error") as mock_error,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "✕ Выход"
            result = step_file(state)

        assert result is None
        mock_error.assert_called_once()


# ── step_group (mocked) ─────────────────────────────────────────────────


class TestStepGroup:
    """Tests for step_group() with mocked autodetect and UI."""

    def test_auto_selects_single_course(self) -> None:
        """Should auto-select when only one course detected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"

        with (
            patch("hse_schedule_parser.wizard.detect_courses", return_value=[1]),
            patch("hse_schedule_parser.wizard.detect_groups", return_value=["25ФПЛ1"]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
            patch("hse_schedule_parser.wizard.console"),
        ):
            mock_choice.return_value = "25ФПЛ1"
            result = step_group(state)

        assert result is not None
        assert result.course == 1
        assert result.group_code == "25ФПЛ1"

    def test_asks_for_course_when_multiple(self) -> None:
        """Should ask user to select course when multiple detected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"

        with (
            patch("hse_schedule_parser.wizard.detect_courses", return_value=[1, 2]),
            patch("hse_schedule_parser.wizard.detect_groups", return_value=["25ФПЛ1"]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
            patch("hse_schedule_parser.wizard.console"),
        ):
            mock_choice.side_effect = ["2 курс", "25ФПЛ1"]
            result = step_group(state)

        assert result is not None
        assert result.course == 2

    def test_returns_none_when_no_courses(self) -> None:
        """Should return None when no courses detected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"

        with (
            patch("hse_schedule_parser.wizard.detect_courses", return_value=[]),
            patch("hse_schedule_parser.wizard.show_error"),
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            result = step_group(state)

        assert result is None

    def test_returns_none_when_no_groups(self) -> None:
        """Should return None when no groups detected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"

        with (
            patch("hse_schedule_parser.wizard.detect_courses", return_value=[1]),
            patch("hse_schedule_parser.wizard.detect_groups", return_value=[]),
            patch("hse_schedule_parser.wizard.show_error"),
            patch("hse_schedule_parser.wizard.show_info"),
            patch("hse_schedule_parser.wizard.console"),
        ):
            result = step_group(state)

        assert result is None

    def test_exit_on_course_selection(self) -> None:
        """Should exit when user chooses exit in course selection."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"

        with (
            patch("hse_schedule_parser.wizard.detect_courses", return_value=[1, 2]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
            patch("hse_schedule_parser.wizard.console"),
        ):
            mock_choice.return_value = "✕ Выход"
            result = step_group(state)

        assert result is None

    def test_exit_on_group_selection(self) -> None:
        """Should exit when user chooses exit in group selection."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"

        with (
            patch("hse_schedule_parser.wizard.detect_courses", return_value=[1]),
            patch("hse_schedule_parser.wizard.detect_groups", return_value=["25ФПЛ1"]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
            patch("hse_schedule_parser.wizard.console"),
        ):
            mock_choice.return_value = "✕ Выход"
            result = step_group(state)

        assert result is None


# ── step_subgroup (mocked) ──────────────────────────────────────────────


class TestStepSubgroup:
    """Tests for step_subgroup() with mocked autodetect and UI."""

    def test_skips_when_no_subgroups(self) -> None:
        """Should skip step when no subgroups detected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"

        with patch("hse_schedule_parser.wizard.detect_subgroups", return_value=[]):
            result = step_subgroup(state)

        assert result is not None
        assert result.subgroup is None

    def test_selects_all_subgroups(self) -> None:
        """Should set subgroup=None when 'all' selected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.detect_subgroups", return_value=[1, 2]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
        ):
            mock_choice.return_value = "Все подгруппы (без фильтра)"
            result = step_subgroup(state)

        assert result is not None
        assert result.subgroup is None

    def test_selects_specific_subgroup(self) -> None:
        """Should set subgroup number when specific subgroup selected."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.detect_subgroups", return_value=[1, 2]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
        ):
            mock_choice.return_value = "Подгруппа 2"
            result = step_subgroup(state)

        assert result is not None
        assert result.subgroup == 2

    def test_exit_on_cancel(self) -> None:
        """Should exit when user cancels."""
        state = WizardState()
        state.file_path = "/test/file.xlsx"
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.detect_subgroups", return_value=[1, 2]),
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
        ):
            mock_choice.return_value = "✕ Выход"
            result = step_subgroup(state)

        assert result is None


# ── step_settings (mocked) ──────────────────────────────────────────────


class TestStepSettings:
    """Tests for step_settings() with mocked UI."""

    def test_applies_toggles(self) -> None:
        """Should apply toggle values from user."""
        state = WizardState()
        state.skip_minor = True
        state.skip_english = True
        state.skip_pe = True

        with (
            patch("hse_schedule_parser.wizard.ask_toggles") as mock_toggles,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_toggles.return_value = {
                "Пропускать MINOR": False,
                "Пропускать английский язык": True,
                "Пропускать физкультуру": False,
            }
            result = step_settings(state)

        assert result is not None
        assert result.skip_minor is False
        assert result.skip_english is True
        assert result.skip_pe is False

    def test_keeps_defaults_on_cancel(self) -> None:
        """Should return None when user cancels toggles."""
        state = WizardState()

        with (
            patch("hse_schedule_parser.wizard.ask_toggles") as mock_toggles,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_toggles.return_value = None
            result = step_settings(state)

        assert result is None


# ── step_output (mocked) ────────────────────────────────────────────────


class TestStepOutput:
    """Tests for step_output() with mocked UI."""

    def test_saves_to_cwd(self) -> None:
        """Should save to cwd when option 1 chosen."""
        state = WizardState()
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "1 — сохранить в текущую директорию (schedule_25ФПЛ1.ics)"
            result = step_output(state)

        assert result is not None
        assert "schedule_25ФПЛ1.ics" in result.output_path
        assert result.preview_only is False

    def test_custom_path(self) -> None:
        """Should accept custom path when option 2 chosen."""
        state = WizardState()
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.ask_path") as mock_path,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "2 — указать другой путь для сохранения"
            mock_path.return_value = "/custom/path/schedule.ics"
            result = step_output(state)

        assert result is not None
        assert result.output_path == "/custom/path/schedule.ics"
        assert result.preview_only is False

    def test_exit_on_cancel(self) -> None:
        """Should exit when user cancels."""
        state = WizardState()
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "✕ Выход"
            result = step_output(state)

        assert result is None

    def test_back_navigation(self) -> None:
        """Should go back when user selects back."""
        state = WizardState()
        state.group_code = "25ФПЛ1"

        with (
            patch("hse_schedule_parser.wizard.ask_choice") as mock_choice,
            patch("hse_schedule_parser.wizard.show_info"),
        ):
            mock_choice.return_value = "← Назад"
            result = step_output(state)

        assert result is None


# ── run_wizard (mocked) ─────────────────────────────────────────────────


class TestRunWizard:
    """Tests for run_wizard() with mocked internals."""

    @patch("hse_schedule_parser.wizard._run_wizard_impl")
    def test_run_wizard_calls_impl(self, mock_impl: MagicMock) -> None:
        """Should call _run_wizard_impl."""
        from hse_schedule_parser.wizard import run_wizard

        mock_impl.return_value = None
        run_wizard()
        mock_impl.assert_called_once()

    @patch("hse_schedule_parser.wizard._run_wizard_impl")
    def test_run_wizard_handles_exception(self, mock_impl: MagicMock) -> None:
        """Should handle exceptions gracefully."""
        from hse_schedule_parser.wizard import run_wizard

        mock_impl.side_effect = Exception("Test error")
        with patch("hse_schedule_parser.wizard.show_error") as mock_error:
            with pytest.raises(SystemExit) as exc_info:
                run_wizard()
            assert exc_info.value.code == 1
            mock_error.assert_called_once()

    @patch("hse_schedule_parser.wizard._run_wizard_impl")
    def test_run_wizard_handles_keyboard_interrupt(self, mock_impl: MagicMock) -> None:
        """Should handle KeyboardInterrupt gracefully."""
        from hse_schedule_parser.wizard import run_wizard

        mock_impl.side_effect = KeyboardInterrupt()
        with patch("hse_schedule_parser.wizard.show_goodbye") as mock_goodbye:
            with pytest.raises(SystemExit) as exc_info:
                run_wizard()
            assert exc_info.value.code == 0
            mock_goodbye.assert_called_once()


class TestRunWizardImpl:
    """Tests for _run_wizard_impl() with all steps mocked."""

    def test_full_flow(self) -> None:
        """Should run all steps and save presets."""
        with (
            patch("hse_schedule_parser.wizard.load_presets",
                  return_value=UserPresets()),
            patch("hse_schedule_parser.wizard.show_banner"),
            patch("hse_schedule_parser.wizard.step_file") as mock_file,
            patch("hse_schedule_parser.wizard.step_group") as mock_group,
            patch("hse_schedule_parser.wizard.step_subgroup") as mock_subgroup,
            patch("hse_schedule_parser.wizard.step_settings") as mock_settings,
            patch("hse_schedule_parser.wizard.step_output") as mock_output,
            patch("hse_schedule_parser.wizard._execute_parse"),
            patch("hse_schedule_parser.wizard.save_presets"),
            patch("hse_schedule_parser.wizard.console"),
            patch("builtins.input", return_value=""),
        ):
            state = WizardState()
            mock_file.return_value = state
            mock_group.return_value = state
            mock_subgroup.return_value = state
            mock_settings.return_value = state
            mock_output.return_value = state

            from hse_schedule_parser.wizard import _run_wizard_impl
            _run_wizard_impl()

    def test_exit_on_step_file(self) -> None:
        """Should exit gracefully when step_file returns None."""
        with (
            patch("hse_schedule_parser.wizard.load_presets",
                  return_value=UserPresets()),
            patch("hse_schedule_parser.wizard.show_banner"),
            patch("hse_schedule_parser.wizard.step_file") as mock_file,
            patch("hse_schedule_parser.wizard.show_goodbye") as mock_goodbye,
        ):
            mock_file.return_value = None

            from hse_schedule_parser.wizard import _run_wizard_impl
            _run_wizard_impl()
            mock_goodbye.assert_called_once()

    def test_exit_on_step_group(self) -> None:
        """Should exit gracefully when step_group returns None."""
        with (
            patch("hse_schedule_parser.wizard.load_presets",
                  return_value=UserPresets()),
            patch("hse_schedule_parser.wizard.show_banner"),
            patch("hse_schedule_parser.wizard.step_file") as mock_file,
            patch("hse_schedule_parser.wizard.step_group") as mock_group,
            patch("hse_schedule_parser.wizard.show_goodbye") as mock_goodbye,
        ):
            state = WizardState()
            mock_file.return_value = state
            mock_group.return_value = None

            from hse_schedule_parser.wizard import _run_wizard_impl
            _run_wizard_impl()
            mock_goodbye.assert_called_once()