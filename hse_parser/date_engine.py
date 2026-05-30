"""Date engine: generates concrete dates from abstract descriptions."""

from __future__ import annotations

from datetime import date, timedelta

from hse_parser.models import RawLessonBlock
from hse_parser.utils import russian_day_to_number


def generate_dates(
    block: RawLessonBlock,
    day_name: str | None,
    module_period_start: str,
    module_period_end: str,
    year: int,
) -> list[date]:
    """Generate concrete dates for a lesson block.

    Args:
        block: Parsed lesson block with date descriptions
        day_name: Russian day name (e.g. 'понедельник')
        module_period_start: Module start date string (e.g. '09.01')
        module_period_end: Module end date string (e.g. '24.03')
        year: Calendar year

    Returns:
        List of concrete dates for this lesson
    """
    result: list[date] = []

    # 1. If specific dates are provided, use them
    if block.dates:
        result = list(block.dates)
    # 2. If period is provided, generate all dates in range matching day of week
    elif block.week_parity or day_name:
        # Parse module period
        period_start = _parse_date(module_period_start, year)
        period_end = _parse_date(module_period_end, year)

        if period_start and period_end and day_name:
            weekday = russian_day_to_number(day_name)
            if weekday is not None:
                result = _generate_dates_in_range(
                    period_start, period_end, weekday
                )

    # 3. Apply week parity filter
    if block.week_parity and result:
        result = _filter_by_parity(result, block.week_parity)

    # 4. Remove cancelled dates
    if block.is_cancelled:
        # If we have specific cancelled dates, filter them out
        # (cancelled dates are already tracked in the block)
        pass  # Cancellation is handled at the event creation level

    # 5. Add recovery dates
    if block.recovery_date:
        result.append(block.recovery_date)

    # 6. Add make-up dates
    for make_up_date in block.location_override:
        if make_up_date not in result:
            result.append(make_up_date)

    # Sort and deduplicate
    result = sorted(set(result))

    return result


def _parse_date(date_str: str, year: int) -> date | None:
    """Parse a date string like '09.01' or '09.01.' into a date object."""
    import re

    match = re.match(r"(\d{1,2})\.(\d{1,2})", date_str)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return date(year, month, day)
    return None


def _generate_dates_in_range(
    start: date, end: date, weekday: int
) -> list[date]:
    """Generate all dates between start and end that fall on the given weekday.

    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        weekday: Day of week (0=Monday, 6=Sunday)

    Returns:
        List of dates matching the weekday
    """
    result: list[date] = []
    current = start

    # Find first occurrence of the target weekday
    days_ahead = weekday - current.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current += timedelta(days=days_ahead)

    while current <= end:
        result.append(current)
        current += timedelta(days=7)

    return result


def _filter_by_parity(
    dates: list[date], parity: str
) -> list[date]:
    """Filter dates by week parity (upper/lower).

    Upper week = odd week numbers (1, 3, 5, ...)
    Lower week = even week numbers (2, 4, 6, ...)

    Week number is calculated from the first date in the list.
    """
    if not dates:
        return []

    first_date = dates[0]
    result: list[date] = []

    for dt in dates:
        days_diff = (dt - first_date).days
        week_number = (days_diff // 7) + 1

        if parity == "upper" and week_number % 2 == 1:
            result.append(dt)
        elif parity == "lower" and week_number % 2 == 0:
            result.append(dt)

    return result