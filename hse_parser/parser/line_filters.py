"""Line filter rules for extracting titles from cell text blocks.

These rules determine which lines in a parsed text block should be
considered part of the lesson title vs. metadata (dates, types, etc.)
that should be filtered out.

Each filter function takes a line string and returns True if the line
should be skipped (filtered out) from the title extraction.
"""

from __future__ import annotations

import re

# Pattern: separator lines (underscores or dashes, ≥10 chars)
SEPARATOR_LINE = re.compile(r"^[_\-]{10,}$")

# Pattern: period lines like "с 12.01 по 23.03"
PERIOD_LINE = re.compile(
    r"[сc]\s+\d{1,2}\.\d{1,2}\.?\s*по\s+\d{1,2}\.\d{1,2}\.?\s*",
    re.IGNORECASE,
)

# Pattern: week parity lines
PARITY_LINE = re.compile(
    r"(верхн|нижн)[яа]я\s+неделя", re.IGNORECASE
)

# Pattern: make-up lines like "13.06 (за 12.06)"
MAKE_UP_LINE = re.compile(
    r"\d{1,2}\.\d{2}\s*\(за\s+\d{1,2}\.\d{2}\)"
)

# Pattern: location override lines like "14.03 ауд. 308"
LOCATION_OVERRIDE_LINE = re.compile(
    r"\d{1,2}\.\d{2}\s+(?:ауд\.|в)\s+"
)

# Pattern: standalone parenthesized type like "(семинары)"
PAREN_TYPE_ONLY = re.compile(r"^\([^)]*\)$")


def is_separator(line: str) -> bool:
    """Check if line is a separator (underscores or dashes, ≥10 chars)."""
    return bool(SEPARATOR_LINE.match(line))


def is_period_line(line: str) -> bool:
    """Check if line is a period description like 'с 12.01 по 23.03'."""
    return bool(PERIOD_LINE.match(line))


def is_date_only_line(line: str) -> bool:
    """Check if line contains mostly dates and little else.

    A line is considered date-only if it has at least one date pattern
    and the count of date patterns >= count of Cyrillic characters.
    """
    date_count = len(re.findall(r"\d{1,2}\.\d{2}", line))
    if date_count > 0:
        cyrillic_count = len(re.findall(r"[а-яё]", line))
        return date_count >= cyrillic_count
    return False


def is_parity_line(line: str) -> bool:
    """Check if line is a week parity indicator like 'верхняя неделя'."""
    return bool(PARITY_LINE.match(line))


def is_cancellation_or_recovery_line(line: str) -> bool:
    """Check if line contains cancellation or recovery info."""
    return "отмена" in line or "восстановление" in line or "восстановлено" in line


def is_make_up_line(line: str) -> bool:
    """Check if line is a make-up class description like '13.06 (за 12.06)'."""
    return bool(MAKE_UP_LINE.match(line))


def is_location_override_line(line: str) -> bool:
    """Check if line is a location override like '14.03 ауд. 308'."""
    return bool(LOCATION_OVERRIDE_LINE.match(line))


def is_standalone_paren_type(line: str) -> bool:
    """Check if line is JUST a parenthesized type like '(семинары)'."""
    return bool(PAREN_TYPE_ONLY.match(line.strip()))


def is_exact_lesson_type(line: str, lesson_type: str | None) -> bool:
    """Check if the line is exactly the lesson type (possibly in parens).

    E.g. if lesson_type is 'семинар', matches 'семинар' or '(семинар)'.
    Does NOT match 'Теория языка I (семинары)'.
    """
    if not lesson_type:
        return False
    line_lower = line.lower()
    return line_lower == lesson_type or line_lower == f"({lesson_type})"


def should_skip_line(line: str, lesson_type: str | None = None) -> bool:
    """Check if a line should be skipped during title extraction.

    Applies all filter rules in order. Returns True if the line
    should be excluded from the title.

    Args:
        line: The line text to check.
        lesson_type: Optional lesson type string for exact-match filtering.

    Returns:
        True if the line should be skipped.
    """
    if is_separator(line):
        return True
    if is_period_line(line):
        return True
    if is_date_only_line(line):
        return True
    if is_parity_line(line):
        return True
    if is_cancellation_or_recovery_line(line):
        return True
    if is_make_up_line(line):
        return True
    if is_location_override_line(line):
        return True
    if is_standalone_paren_type(line):
        return True
    if is_exact_lesson_type(line, lesson_type):
        return True
    return False