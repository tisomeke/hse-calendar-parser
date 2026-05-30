"""Date extraction patterns for cell content parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from hse_parser.utils import russian_month_to_number


@dataclass
class DateParseResult:
    """Result of parsing dates from a text block."""

    specific_dates: list[date] = field(default_factory=list)
    period_start: date | None = None
    period_end: date | None = None
    cancelled_dates: list[date] = field(default_factory=list)
    recovery_dates: list[date] = field(default_factory=list)
    week_parity: Literal["upper", "lower", None] = None
    make_up_dates: dict[date, date] = field(default_factory=dict)
    location_overrides: dict[date, str] = field(default_factory=dict)


# Pattern: specific dates like "03.11, 17.11, 01.12"
DATE_LIST_PATTERN = re.compile(r"(\d{1,2})\.(\d{2})")

# Pattern: period like "с 12.01 по 23.03" or "с 12.01. по 16.02"
PERIOD_PATTERN = re.compile(
    r"с\s+(\d{1,2})\.(\d{1,2})\.?\s*по\s+(\d{1,2})\.(\d{1,2})\.?"
)

# Pattern: cancellation "12.01 - отмена" or "12.01-отмена"
CANCELLATION_PATTERN = re.compile(
    r"(\d{1,2})\.(\d{2})\s*[-–]\s*отмена"
)

# Pattern: cancellation with recovery "29.04 - отмена (восстановлено 02.04)"
RECOVERY_PAREN_PATTERN = re.compile(
    r"(\d{1,2})\.(\d{2})\s*[-–]\s*отмена\s*\(восстановлен[оа]\s+(\d{1,2})\.(\d{2})\)"
)

# Pattern: recovery "25 мая восстановление" or "01.06 восстановление"
RECOVERY_TEXT_PATTERN = re.compile(
    r"(\d{1,2})\s+(мая|июня|апреля|января|февраля|марта|сентября|октября|ноября|декабря)\s+восстановление"
)
RECOVERY_DATE_PATTERN = re.compile(
    r"(\d{1,2})\.(\d{2})\s+восстановление"
)

# Pattern: week parity
UPPER_WEEK_PATTERN = re.compile(r"верхн[яа]я\s+неделя")
LOWER_WEEK_PATTERN = re.compile(r"нижн[яа]я\s+неделя")

# Pattern: make-up class "13.06 (за 12.06)"
MAKE_UP_PATTERN = re.compile(
    r"(\d{1,2})\.(\d{2})\s*\(за\s+(\d{1,2})\.(\d{2})\)"
)

# Pattern: location override "14.03 ауд. 308" or "13.02 в 201 Сорм"
LOCATION_OVERRIDE_PATTERN = re.compile(
    r"(\d{1,2})\.(\d{2})\s+(?:ауд\.|в)\s+(.+?)(?:\s|$)"
)

# Pattern: date with Russian month name "25 мая"
DATE_MONTH_PATTERN = re.compile(
    r"(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
)


def parse_dates_from_block(
    text: str, year: int
) -> DateParseResult:
    """Extract all date-related information from a text block.

    Args:
        text: Normalized text block
        year: The calendar year to assign to dates

    Returns:
        DateParseResult with all extracted date information
    """
    result = DateParseResult()

    # 1. Check week parity
    if UPPER_WEEK_PATTERN.search(text):
        result.week_parity = "upper"
    elif LOWER_WEEK_PATTERN.search(text):
        result.week_parity = "lower"

    # 2. Extract make-up dates first (before general date extraction)
    for match in MAKE_UP_PATTERN.finditer(text):
        d, m, orig_d, orig_m = match.groups()
        make_up = date(year, int(m), int(d))
        original = date(year, int(orig_m), int(orig_d))
        result.make_up_dates[make_up] = original

    # 3. Extract location overrides
    for match in LOCATION_OVERRIDE_PATTERN.finditer(text):
        d, m, location = match.groups()
        override_date = date(year, int(m), int(d))
        result.location_overrides[override_date] = location.strip()

    # 4. Extract recovery with parentheses (cancellation + recovery)
    for match in RECOVERY_PAREN_PATTERN.finditer(text):
        d, m, rd, rm = match.groups()
        cancelled = date(year, int(m), int(d))
        recovered = date(year, int(rm), int(rd))
        result.cancelled_dates.append(cancelled)
        result.recovery_dates.append(recovered)

    # 5. Extract standalone cancellations (not part of recovery pattern)
    # Remove recovery-paren matches from text to avoid double-processing
    text_no_recovery = RECOVERY_PAREN_PATTERN.sub("", text)
    for match in CANCELLATION_PATTERN.finditer(text_no_recovery):
        d, m = match.groups()
        cancelled = date(year, int(m), int(d))
        if cancelled not in result.cancelled_dates:
            result.cancelled_dates.append(cancelled)

    # 6. Extract recovery from text patterns
    for match in RECOVERY_TEXT_PATTERN.finditer(text):
        d, month_name = match.groups()
        m = russian_month_to_number(month_name)
        if m is not None:
            result.recovery_dates.append(date(year, m, int(d)))

    for match in RECOVERY_DATE_PATTERN.finditer(text):
        d, m = match.groups()
        recovered = date(year, int(m), int(d))
        if recovered not in result.recovery_dates:
            result.recovery_dates.append(recovered)

    # 7. Extract period
    period_match = PERIOD_PATTERN.search(text)
    if period_match:
        sd, sm, ed, em = period_match.groups()
        result.period_start = date(year, int(sm), int(sd))
        result.period_end = date(year, int(em), int(ed))

    # 8. Extract specific dates (from remaining text, excluding cancelled)
    # Remove known patterns to avoid false positives
    cleaned = text
    cleaned = PERIOD_PATTERN.sub("", cleaned)
    cleaned = CANCELLATION_PATTERN.sub("", cleaned)
    cleaned = RECOVERY_PAREN_PATTERN.sub("", cleaned)
    cleaned = RECOVERY_TEXT_PATTERN.sub("", cleaned)
    cleaned = RECOVERY_DATE_PATTERN.sub("", cleaned)
    cleaned = MAKE_UP_PATTERN.sub("", cleaned)
    cleaned = UPPER_WEEK_PATTERN.sub("", cleaned)
    cleaned = LOWER_WEEK_PATTERN.sub("", cleaned)

    for match in DATE_LIST_PATTERN.finditer(cleaned):
        d, m = match.groups()
        m_int = int(m)
        d_int = int(d)
        # Only include reasonable month numbers
        if 1 <= m_int <= 12 and 1 <= d_int <= 31:
            specific = date(year, m_int, d_int)
            if specific not in result.specific_dates:
                result.specific_dates.append(specific)

    return result


def has_any_date_info(text: str) -> bool:
    """Check if text contains any date-related information."""
    patterns = [
        DATE_LIST_PATTERN,
        PERIOD_PATTERN,
        CANCELLATION_PATTERN,
        RECOVERY_PAREN_PATTERN,
        RECOVERY_TEXT_PATTERN,
        RECOVERY_DATE_PATTERN,
        MAKE_UP_PATTERN,
        UPPER_WEEK_PATTERN,
        LOWER_WEEK_PATTERN,
    ]
    return any(p.search(text) for p in patterns)