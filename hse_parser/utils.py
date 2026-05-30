"""Utility functions for the HSE schedule parser."""

import hashlib
import re
from datetime import date, time

RUSSIAN_MONTHS: dict[str, int] = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}

RUSSIAN_DAYS: dict[str, int] = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресенье": 6,
}


def normalize_group_code(code: str) -> str:
    """Normalize a group code: strip spaces, uppercase.

    Handles cases like '24 ФПЛ1' → '24ФПЛ1'.
    """
    return re.sub(r"\s+", "", code).upper()


def generate_uid(
    group: str, dt: date, start_time: time, title: str, teacher: str
) -> str:
    """Generate a unique UID for a calendar event.

    Format: hse-<group>-<YYYY-MM-DD>-<HHMM>-<hash(title+teacher)>
    """
    date_str = dt.strftime("%Y-%m-%d")
    time_str = start_time.strftime("%H%M")
    hash_input = f"{title}|{teacher}".encode("utf-8")
    hash_suffix = hashlib.md5(hash_input).hexdigest()[:6]
    return f"hse-{group}-{date_str}-{time_str}-{hash_suffix}"


def parse_time_range(range_str: str) -> tuple[time, time] | None:
    """Parse a time range string like '08:00-09:20' into (start, end) times.

    Returns None if the string cannot be parsed.
    """
    range_str = range_str.strip()
    match = re.match(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})", range_str)
    if not match:
        return None
    start = time(int(match.group(1)), int(match.group(2)))
    end = time(int(match.group(3)), int(match.group(4)))
    return start, end


def russian_month_to_number(month_name: str) -> int | None:
    """Convert a Russian month name (in genitive case) to a month number.

    'января' → 1, 'февраля' → 2, etc.
    """
    return RUSSIAN_MONTHS.get(month_name.strip().lower())


def russian_day_to_number(day_name: str) -> int | None:
    """Convert a Russian day name to a weekday number (0=Monday, 6=Sunday).

    'понедельник' → 0, 'вторник' → 1, etc.
    """
    return RUSSIAN_DAYS.get(day_name.strip().lower())


def resolve_year(module: int, academic_year_start: int) -> int:
    """Resolve the calendar year for a date based on module and academic year start.

    Module 3 (Jan-Mar) → academic_year_start + 1
    Module 4 (Apr-Jun) → academic_year_start + 1
    Module 1 (Sep-Dec) → academic_year_start
    Module 2 (Nov-Dec) → academic_year_start
    """
    if module in (3, 4):
        return academic_year_start + 1
    return academic_year_start


def extract_module_from_title(title: str) -> int | None:
    """Extract module number from a title string.

    'БАКАЛАВРИАТ - 1 курс, 3 модуль (09.01. - 24.03.)' → 3
    """
    match = re.search(r"(\d+)\s+модуль", title)
    if match:
        return int(match.group(1))
    return None


def extract_period_from_title(title: str) -> tuple[str, str] | None:
    """Extract start and end date strings from a title.

    'БАКАЛАВРИАТ - 1 курс, 3 модуль (09.01. - 24.03.)' → ('09.01', '24.03')
    """
    match = re.search(r"\((\d{1,2}\.\d{1,2})\s*\.?\s*[-–]\s*(\d{1,2}\.\d{1,2})\s*\.?\s*\)", title)
    if match:
        return match.group(1), match.group(2)
    return None