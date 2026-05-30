"""Tests for the autodetect module.

Tests cover:
- detect_courses: finding available course sheets
- detect_groups: finding group codes in a course sheet
- detect_subgroups: detecting subgroup markers
- suggest_academic_year: year suggestion logic
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

from hse_schedule_parser.autodetect import (
    detect_courses,
    detect_groups,
    detect_subgroups,
    suggest_academic_year,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def workbook_with_courses() -> openpyxl.Workbook:
    """Create a workbook with standard course sheets."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    for sheet_name in ["1 курс", "2 курс", "3 курс", "4 курс"]:
        ws = wb.create_sheet(title=sheet_name)
        # Add group codes in row 10
        for col_idx, group in enumerate(["25ФПЛ1", "25ФПЛ2", "25БИВ1"], start=1):
            ws.cell(row=10, column=col_idx, value=group)

    return wb


@pytest.fixture
def workbook_with_subgroups() -> openpyxl.Workbook:
    """Create a workbook with subgroup markers in cells."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(title="1 курс")

    # Add group code in row 10
    ws.cell(row=10, column=1, value="25ФПЛ1")

    # Add subject cells with subgroup markers (row 12+)
    ws.cell(row=12, column=1, value="Иностранный язык (гр.1)")
    ws.cell(row=13, column=1, value="Иностранный язык (гр.2)")
    ws.cell(row=14, column=1, value="История (без подгруппы)")

    return wb


@pytest.fixture
def workbook_no_courses() -> openpyxl.Workbook:
    """Create a workbook with no recognizable course sheets."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    wb.create_sheet(title="Sheet1")
    wb.create_sheet(title="Data")
    return wb


@pytest.fixture
def temp_xlsx(workbook_with_courses) -> Path:
    """Save a workbook to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = Path(f.name)
    workbook_with_courses.save(str(path))
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_xlsx_subgroups(workbook_with_subgroups) -> Path:
    """Save a workbook with subgroups to a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = Path(f.name)
    workbook_with_subgroups.save(str(path))
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def temp_xlsx_no_courses(workbook_no_courses) -> Path:
    """Save a workbook with no courses to a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = Path(f.name)
    workbook_no_courses.save(str(path))
    yield path
    path.unlink(missing_ok=True)


# ── detect_courses ──────────────────────────────────────────────────────


class TestDetectCourses:
    """Tests for detect_courses()."""

    def test_detects_all_courses(self, temp_xlsx: Path) -> None:
        """Should detect courses 1-4 when all sheets present."""
        courses = detect_courses(temp_xlsx)
        assert courses == [1, 2, 3, 4]

    def test_returns_empty_for_missing_file(self) -> None:
        """Should return empty list for non-existent file."""
        courses = detect_courses("/nonexistent/file.xlsx")
        assert courses == []

    def test_returns_empty_for_no_courses(self, temp_xlsx_no_courses: Path) -> None:
        """Should return empty list when no course sheets found."""
        courses = detect_courses(temp_xlsx_no_courses)
        assert courses == []

    def test_handles_corrupted_file(self) -> None:
        """Should return empty list for corrupted file."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"not an excel file")
            path = Path(f.name)
        try:
            courses = detect_courses(path)
            assert courses == []
        finally:
            path.unlink(missing_ok=True)

    def test_detects_single_course(self) -> None:
        """Should detect just one course if only one sheet."""
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        wb.create_sheet(title="1 курс")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        wb.save(str(path))
        try:
            courses = detect_courses(path)
            assert courses == [1]
        finally:
            path.unlink(missing_ok=True)

    def test_detects_first_course_variant(self) -> None:
        """Should detect '1 курс.' variant for first year."""
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        wb.create_sheet(title="1 курс.")
        wb.create_sheet(title="2 курс")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = Path(f.name)
        wb.save(str(path))
        try:
            courses = detect_courses(path)
            assert 1 in courses
            assert 2 in courses
        finally:
            path.unlink(missing_ok=True)


# ── detect_groups ───────────────────────────────────────────────────────


class TestDetectGroups:
    """Tests for detect_groups()."""

    def test_detects_groups(self, temp_xlsx: Path) -> None:
        """Should detect group codes for a course."""
        groups = detect_groups(temp_xlsx, 1)
        assert "25ФПЛ1" in groups
        assert "25ФПЛ2" in groups
        assert "25БИВ1" in groups

    def test_returns_empty_for_missing_file(self) -> None:
        """Should return empty list for non-existent file."""
        groups = detect_groups("/nonexistent/file.xlsx", 1)
        assert groups == []

    def test_returns_empty_for_nonexistent_course(self, temp_xlsx: Path) -> None:
        """Should return empty list for course not in file."""
        groups = detect_groups(temp_xlsx, 5)
        assert groups == []

    def test_returns_sorted_unique(self, temp_xlsx: Path) -> None:
        """Should return sorted unique group codes."""
        groups = detect_groups(temp_xlsx, 1)
        assert groups == sorted(set(groups))

    def test_handles_corrupted_file(self) -> None:
        """Should return empty list for corrupted file."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"corrupted data")
            path = Path(f.name)
        try:
            groups = detect_groups(path, 1)
            assert groups == []
        finally:
            path.unlink(missing_ok=True)


# ── detect_subgroups ────────────────────────────────────────────────────


class TestDetectSubgroups:
    """Tests for detect_subgroups()."""

    def test_detects_subgroups(self, temp_xlsx_subgroups: Path) -> None:
        """Should detect subgroups 1 and 2 from cell content."""
        subgroups = detect_subgroups(temp_xlsx_subgroups, "25ФПЛ1")
        assert 1 in subgroups
        assert 2 in subgroups

    def test_returns_empty_for_no_subgroups(self, temp_xlsx: Path) -> None:
        """Should return empty list when no subgroup markers."""
        subgroups = detect_subgroups(temp_xlsx, "25ФПЛ1")
        assert subgroups == []

    def test_returns_empty_for_missing_file(self) -> None:
        """Should return empty list for non-existent file."""
        subgroups = detect_subgroups("/nonexistent/file.xlsx", "25ФПЛ1")
        assert subgroups == []

    def test_returns_empty_for_unknown_prefix(self, temp_xlsx: Path) -> None:
        """Should return empty list for unknown group prefix."""
        subgroups = detect_subgroups(temp_xlsx, "99XXXX")
        assert subgroups == []


# ── suggest_academic_year ───────────────────────────────────────────────


class TestSuggestAcademicYear:
    """Tests for suggest_academic_year()."""

    @patch("datetime.date")
    def test_suggests_current_year_in_september(self, mock_date: MagicMock) -> None:
        """Should suggest current year when month >= 9."""
        mock_date.today.return_value = type("Date", (), {"month": 9, "year": 2025})()
        assert suggest_academic_year() == 2025

    @patch("datetime.date")
    def test_suggests_previous_year_in_march(self, mock_date: MagicMock) -> None:
        """Should suggest previous year when month < 9."""
        mock_date.today.return_value = type("Date", (), {"month": 3, "year": 2025})()
        assert suggest_academic_year() == 2024

    @patch("datetime.date")
    def test_suggests_previous_year_in_january(self, mock_date: MagicMock) -> None:
        """Should suggest previous year in January."""
        mock_date.today.return_value = type("Date", (), {"month": 1, "year": 2025})()
        assert suggest_academic_year() == 2024

    @patch("datetime.date")
    def test_suggests_current_year_in_december(self, mock_date: MagicMock) -> None:
        """Should suggest current year in December."""
        mock_date.today.return_value = type("Date", (), {"month": 12, "year": 2025})()
        assert suggest_academic_year() == 2025