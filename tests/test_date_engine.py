"""Tests for the date engine module.

Tests cover:
- generate_dates: generating concrete dates from lesson blocks
- _filter_by_parity: filtering dates by week parity
- _filter_by_parity with calendar_upper_dates: using calendar sheet data
"""

from __future__ import annotations

from datetime import date

from hse_parser.date_engine import _filter_by_parity, generate_dates
from hse_parser.models import RawLessonBlock


# ── _filter_by_parity ─────────────────────────────────────────────────────


class TestFilterByParity:
    """Tests for _filter_by_parity()."""

    def test_upper_keeps_odd_weeks(self) -> None:
        """Should keep odd week numbers for upper parity."""
        dates = [
            date(2025, 9, 1),   # week 1 (odd) — upper
            date(2025, 9, 8),   # week 2 (even) — lower
            date(2025, 9, 15),  # week 3 (odd) — upper
            date(2025, 9, 22),  # week 4 (even) — lower
        ]
        result = _filter_by_parity(dates, "upper")
        assert result == [date(2025, 9, 1), date(2025, 9, 15)]

    def test_lower_keeps_even_weeks(self) -> None:
        """Should keep even week numbers for lower parity."""
        dates = [
            date(2025, 9, 1),   # week 1 (odd) — upper
            date(2025, 9, 8),   # week 2 (even) — lower
            date(2025, 9, 15),  # week 3 (odd) — upper
        ]
        result = _filter_by_parity(dates, "lower")
        assert result == [date(2025, 9, 8)]

    def test_returns_empty_for_empty_list(self) -> None:
        """Should return empty list for empty input."""
        assert _filter_by_parity([], "upper") == []

    def test_single_date_upper(self) -> None:
        """Single date is week 1 (odd) → upper."""
        result = _filter_by_parity([date(2025, 9, 1)], "upper")
        assert result == [date(2025, 9, 1)]

    def test_single_date_lower(self) -> None:
        """Single date is week 1 (odd) → not lower."""
        result = _filter_by_parity([date(2025, 9, 1)], "lower")
        assert result == []

    # ── With calendar_upper_dates ─────────────────────────────────────

    def test_upper_with_calendar_data(self) -> None:
        """Should use calendar_upper_dates set when provided."""
        dates = [
            date(2025, 9, 1),
            date(2025, 9, 8),
            date(2025, 9, 15),
            date(2025, 9, 22),
        ]
        upper_set = frozenset({date(2025, 9, 1), date(2025, 9, 15)})
        result = _filter_by_parity(dates, "upper", calendar_upper_dates=upper_set)
        assert result == [date(2025, 9, 1), date(2025, 9, 15)]

    def test_lower_with_calendar_data(self) -> None:
        """Should keep dates NOT in calendar_upper_dates for lower parity."""
        dates = [
            date(2025, 9, 1),
            date(2025, 9, 8),
            date(2025, 9, 15),
        ]
        upper_set = frozenset({date(2025, 9, 1), date(2025, 9, 15)})
        result = _filter_by_parity(dates, "lower", calendar_upper_dates=upper_set)
        assert result == [date(2025, 9, 8)]

    def test_calendar_data_empty_set(self) -> None:
        """Empty calendar set means no dates are upper."""
        dates = [date(2025, 9, 1), date(2025, 9, 8)]
        upper_set = frozenset()
        result = _filter_by_parity(dates, "upper", calendar_upper_dates=upper_set)
        assert result == []

    def test_calendar_data_all_upper(self) -> None:
        """All dates in upper set means all kept for upper parity."""
        dates = [date(2025, 9, 1), date(2025, 9, 8)]
        upper_set = frozenset({date(2025, 9, 1), date(2025, 9, 8)})
        result = _filter_by_parity(dates, "upper", calendar_upper_dates=upper_set)
        assert result == dates

    def test_calendar_data_falls_back_when_none(self) -> None:
        """When calendar_upper_dates is None, fall back to relative calc."""
        dates = [
            date(2025, 9, 1),   # week 1 (odd)
            date(2025, 9, 8),   # week 2 (even)
        ]
        result = _filter_by_parity(dates, "upper", calendar_upper_dates=None)
        assert result == [date(2025, 9, 1)]

    def test_calendar_data_with_gap(self) -> None:
        """Should handle dates with gaps (not consecutive weeks)."""
        dates = [
            date(2025, 9, 1),
            date(2025, 9, 15),  # gap: Sept 8 is missing
            date(2025, 9, 22),
        ]
        upper_set = frozenset({date(2025, 9, 1), date(2025, 9, 22)})
        result = _filter_by_parity(dates, "upper", calendar_upper_dates=upper_set)
        assert result == [date(2025, 9, 1), date(2025, 9, 22)]


# ── generate_dates ────────────────────────────────────────────────────────


class TestGenerateDates:
    """Tests for generate_dates()."""

    def test_uses_specific_dates(self) -> None:
        """Should use specific dates from block."""
        block = RawLessonBlock(
            dates={date(2025, 9, 1), date(2025, 9, 8)},
            title="Test",
        )
        result = generate_dates(
            block, None, "01.09", "30.09", 2025
        )
        assert result == [date(2025, 9, 1), date(2025, 9, 8)]

    def test_generates_from_period(self) -> None:
        """Should generate dates from period matching day of week."""
        block = RawLessonBlock(
            week_parity=None,
            title="Test",
        )
        result = generate_dates(
            block, "понедельник", "01.09", "30.09", 2025
        )
        # Mondays in Sept 2025: 1, 8, 15, 22, 29
        assert date(2025, 9, 1) in result
        assert date(2025, 9, 8) in result
        assert date(2025, 9, 29) in result
        assert date(2025, 9, 2) not in result  # Tuesday

    def test_applies_parity_filter(self) -> None:
        """Should filter by week parity."""
        block = RawLessonBlock(
            week_parity="upper",
            title="Test",
        )
        result = generate_dates(
            block, "понедельник", "01.09", "30.09", 2025
        )
        # Upper Mondays: Sept 1, 15, 29 (weeks 1, 3, 5)
        assert result == [date(2025, 9, 1), date(2025, 9, 15), date(2025, 9, 29)]

    def test_applies_calendar_parity(self) -> None:
        """Should use calendar_upper_dates when provided."""
        block = RawLessonBlock(
            week_parity="upper",
            title="Test",
        )
        upper_set = frozenset({date(2025, 9, 1), date(2025, 9, 15)})
        result = generate_dates(
            block,
            "понедельник",
            "01.09",
            "30.09",
            2025,
            calendar_upper_dates=upper_set,
        )
        # Only dates in upper_set should be kept
        assert result == [date(2025, 9, 1), date(2025, 9, 15)]

    def test_adds_recovery_date(self) -> None:
        """Should add recovery date to result."""
        block = RawLessonBlock(
            dates={date(2025, 9, 1)},
            recovery_date=date(2025, 9, 8),
            title="Test",
        )
        result = generate_dates(
            block, None, "01.09", "30.09", 2025
        )
        assert date(2025, 9, 8) in result

    def test_returns_empty_for_no_dates(self) -> None:
        """Should return empty list when no dates can be generated."""
        block = RawLessonBlock(title="Test")
        result = generate_dates(
            block, None, "01.09", "30.09", 2025
        )
        assert result == []

    def test_deduplicates_dates(self) -> None:
        """Should remove duplicate dates."""
        block = RawLessonBlock(
            dates={date(2025, 9, 1), date(2025, 9, 1)},
            title="Test",
        )
        result = generate_dates(
            block, None, "01.09", "30.09", 2025
        )
        assert result == [date(2025, 9, 1)]