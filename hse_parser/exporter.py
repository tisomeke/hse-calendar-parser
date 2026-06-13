"""ICS exporter: converts Event objects to iCalendar format."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event as ICalEvent, vText

from hse_parser.models import Event

TZ_MOSCOW = ZoneInfo("Europe/Moscow")


def create_calendar(events: list[Event], group_code: str) -> Calendar:
    """Create an iCalendar from a list of Event objects.

    Args:
        events: List of Event objects
        group_code: Group code for calendar name

    Returns:
        icalendar.Calendar object
    """
    cal = Calendar()
    cal.add("VERSION", "2.0")
    cal.add("PRODID", "-//HSE Schedule Parser//RU")
    cal.add("CALSCALE", "GREGORIAN")
    cal.add("METHOD", "PUBLISH")
    cal.add("X-WR-CALNAME", f"Расписание {group_code}")
    cal.add("X-WR-TIMEZONE", "Europe/Moscow")

    # Add timezone component
    cal.add_component(_create_timezone_component())

    for event in events:
        cal.add_component(_create_event(event))

    return cal


def _create_event(event: Event) -> ICalEvent:
    """Create an icalendar Event from our Event model."""
    ical_event = ICalEvent()

    ical_event.add("UID", event.uid)
    ical_event.add("DTSTART", event.start.replace(tzinfo=TZ_MOSCOW))
    ical_event.add("DTEND", event.end.replace(tzinfo=TZ_MOSCOW))
    ical_event.add("SUMMARY", event.summary)
    ical_event.add("STATUS", event.status)

    if event.location:
        ical_event.add("LOCATION", vText(event.location))

    if event.description:
        ical_event.add("DESCRIPTION", vText(event.description))

    return ical_event


def _create_timezone_component():
    """Create a VTIMEZONE component for Europe/Moscow.

    Moscow has been at UTC+3 year-round since 2014 (no DST).
    Both STANDARD and DAYLIGHT components are included for
    compatibility with calendar applications that expect both.
    """
    from icalendar import Timezone, TimezoneDaylight, TimezoneStandard

    tz = Timezone()
    tz.add("TZID", "Europe/Moscow")

    # Standard time (MSK, UTC+3)
    standard = TimezoneStandard()
    standard.add("DTSTART", datetime(1970, 1, 1, 0, 0, 0))
    standard.add("TZOFFSETFROM", timedelta(hours=3))
    standard.add("TZOFFSETTO", timedelta(hours=3))
    standard.add("TZNAME", "MSK")
    tz.add_component(standard)

    # Daylight time (same as standard — Moscow has no DST since 2014)
    # Included for compatibility with calendar apps that expect both components
    daylight = TimezoneDaylight()
    daylight.add("DTSTART", datetime(1970, 1, 1, 0, 0, 0))
    daylight.add("TZOFFSETFROM", timedelta(hours=3))
    daylight.add("TZOFFSETTO", timedelta(hours=3))
    daylight.add("TZNAME", "MSK")
    tz.add_component(daylight)

    return tz


def serialize_calendar(cal: Calendar) -> bytes:
    """Serialize a Calendar to bytes."""
    return cal.to_ical()


def build_location(
    auditorium: str, building: str, is_online: bool
) -> str | None:
    """Build a location string from auditorium and building info.

    Cleans newlines from auditorium and building strings — Excel cells
    can contain multi-line text (e.g., different auditoriums for different
    subgroups separated by line breaks), which would produce unwanted \\n
    in the ICS LOCATION field.

    Returns None if no location info is available.
    """
    if is_online:
        return "Online"

    parts = []
    if auditorium:
        # Replace newlines with comma+space for clean single-line output
        clean_aud = auditorium.replace("\n", ", ")
        parts.append(f"Ауд. {clean_aud}")
    if building:
        clean_bld = building.replace("\n", ", ")
        parts.append(f"Корпус {clean_bld}")

    if parts:
        return ", ".join(parts)
    return None


def build_summary(lesson_type: str, title: str) -> str:
    """Build an event summary string.

    Format: [Тип] Название дисциплины
    """
    if lesson_type and lesson_type != "занятие":
        return f"[{lesson_type}] {title}"
    return title


WATERMARK = "Создано с помощью hse-calendar-parser (https://github.com/tisomeke/hse-calendar-parser)"


def build_description(teachers: list[str], source_text: str) -> str:
    """Build an event description string.

    Uses \\n (escaped newline) for line breaks, which icalendar
    will serialize as literal \\n in the ICS file — the standard
    way to represent line breaks in DESCRIPTION per RFC 5545.

    Newlines in source_text are replaced with comma+space to prevent
    unwanted line breaks in the ICS output.

    Appends a watermark with a link to the project repository.
    """
    parts = []
    if teachers:
        parts.append(f"Преподаватель: {', '.join(teachers)}")
    if source_text:
        clean_source = source_text[:500].replace("\n", ", ")
        parts.append(f"Источник: {clean_source}")
    parts.append(WATERMARK)
    return "\\n".join(parts)