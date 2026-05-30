"""Main cell parser that orchestrates text cleaning, date parsing, and rule checking."""

from __future__ import annotations

import re
from datetime import date

from hse_parser.models import RawLessonBlock
from hse_parser.parser.date_parser import parse_dates_from_block
from hse_parser.parser.rules import should_skip
from hse_parser.parser.text_cleaner import normalize_text, split_into_blocks

# Pattern for lesson type
LESSON_TYPE_PATTERN = re.compile(
    r"[-–]\s*(лекци[яю]|семинар[а-я]*|практикум[а-я]*|НИС|МКД|МДК|консультаци[яю])",
    re.IGNORECASE,
)

# Pattern for teacher name: "Фамилия И.О." or "Фамилия И.О. / Фамилия И.О."
# Allows optional space between initials: "М.М." or "М. М."
TEACHER_PATTERN = re.compile(
    r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?"
)

# Pattern for subgroup: "гр.1", "гр.2", "гр 46"
SUBGROUP_PATTERN = re.compile(r"гр\.?\s*(\d+)", re.IGNORECASE)

# Pattern for MKD/MDK/NIS prefix
MKD_PREFIX = re.compile(r"^(МКД|МДК|НИС)\s+", re.IGNORECASE)

# Pattern for lesson type in parentheses: "(лекция)", "(семинар)"
PAREN_TYPE_PATTERN = re.compile(r"\(([^)]*)\)")


def parse_cell(
    text: str,
    year: int,
    day_name: str | None = None,
    auditorium: str = "",
    building: str = "",
    subgroup_filter: int | None = None,
    skip_minor: bool = True,
    skip_english: bool = True,
    skip_pe: bool = True,
) -> tuple[list[RawLessonBlock], str | None]:
    """Parse a cell's text content into structured lesson blocks.

    Args:
        text: Raw cell text
        year: Calendar year for date resolution
        day_name: Russian day name (for period-based date generation)
        auditorium: Raw auditorium cell text
        building: Raw building cell text
        subgroup_filter: If set, only include blocks matching this subgroup
        skip_minor: Skip MINOR entries
        skip_english: Skip English language entries
        skip_pe: Skip Physical Education entries

    Returns:
        Tuple of (list of RawLessonBlock, warning_reason or None)
    """
    if not text or not text.strip():
        return [], None

    # Normalize text
    normalized = normalize_text(text)

    # Check skip rules
    skip, reason = should_skip(normalized)
    if skip:
        return [], reason

    # Split into blocks
    blocks = split_into_blocks(normalized)
    if not blocks:
        return [], "EMPTY_CELL"

    result: list[RawLessonBlock] = []
    for block_text in blocks:
        lesson = _parse_single_block(
            block_text,
            year,
            auditorium,
            building,
            subgroup_filter,
        )
        if lesson is not None:
            result.append(lesson)

    if not result:
        return [], "UNPARSEABLE_FORMAT"

    return result, None


def _parse_single_block(
    text: str,
    year: int,
    auditorium: str,
    building: str,
    subgroup_filter: int | None,
) -> RawLessonBlock | None:
    """Parse a single text block into a RawLessonBlock."""
    lesson = RawLessonBlock()

    # 1. Extract dates
    date_result = parse_dates_from_block(text, year)
    lesson.dates = date_result.specific_dates
    lesson.week_parity = date_result.week_parity
    lesson.recovery_date = date_result.recovery_dates[0] if date_result.recovery_dates else None
    lesson.is_cancelled = bool(date_result.cancelled_dates)
    lesson.location_override = date_result.location_overrides

    # 2. Extract lesson type from text
    lesson_type = _extract_lesson_type(text)
    if lesson_type:
        lesson.lesson_type = lesson_type

    # 3. Extract subgroup
    subgroup = _extract_subgroup(text)
    if subgroup is not None:
        lesson.subgroup = subgroup
        # Filter by subgroup if specified
        if subgroup_filter is not None and subgroup != subgroup_filter:
            return None

    # 4. Extract title and teacher
    title, teachers = _extract_title_and_teacher(text, lesson.lesson_type)
    lesson.title = title
    lesson.teachers = teachers

    # 5. Handle online
    lesson.is_online = _is_online(auditorium, building)

    # 6. Build location string
    if lesson.is_online:
        pass  # location will be "Online" in exporter
    elif auditorium or building:
        pass  # location will be built in exporter

    return lesson


def _extract_lesson_type(text: str) -> str | None:
    """Extract lesson type from text.

    Checks for patterns like:
    - "- лекция" or "-лекция"
    - "(лекция)" or "(семинар)"
    - "МКД", "МДК", "НИС" prefix
    """
    # Check parenthesized type first
    for match in PAREN_TYPE_PATTERN.finditer(text):
        content = match.group(1).strip().lower()
        type_map = {
            "лекция": "лекция",
            "лекции": "лекция",
            "семинар": "семинар",
            "семинары": "семинар",
            "практикум": "практикум",
            "консультация": "консультация",
        }
        if content in type_map:
            return type_map[content]

    # Check dash-prefixed type
    match = LESSON_TYPE_PATTERN.search(text)
    if match:
        raw = match.group(1).lower().rstrip("юя")
        type_map = {
            "лекци": "лекция",
            "семинар": "семинар",
            "практикум": "практикум",
            "консультаци": "консультация",
        }
        return type_map.get(raw, raw)

    # Check MKD/MDK/NIS prefix
    match = MKD_PREFIX.match(text)
    if match:
        prefix = match.group(1).upper()
        type_map = {"МКД": "МКД", "МДК": "МДК", "НИС": "НИС"}
        return type_map.get(prefix)

    return None


def _extract_subgroup(text: str) -> int | None:
    """Extract subgroup number from text.

    Patterns: "гр.1", "гр.2", "гр 46"
    """
    match = SUBGROUP_PATTERN.search(text)
    if match:
        return int(match.group(1))
    return None


def _extract_title_and_teacher(
    text: str, lesson_type: str | None
) -> tuple[str, list[str]]:
    """Extract discipline title and teacher names from text.

    The title is typically the first meaningful line after removing
    date/type information. Teacher names follow the title.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Remove known pattern lines
    cleaned_lines = []
    for line in lines:
        # Skip separator lines (underscores or dashes, ≥10 chars)
        if re.match(r"^[_\-]{10,}$", line):
            continue
        # Skip period lines like "с 12.01 по 23.03"
        if re.match(r"с\s+\d{1,2}\.\d{1,2}\.?\s*по\s+\d{1,2}\.\d{1,2}\.?\s*", line, re.IGNORECASE):
            continue
        # Skip date-only lines
        if re.match(r"^[\d\s,.\-–/()a-zа-яё]+$", line, re.IGNORECASE):
            # Check if it's mostly dates
            date_count = len(re.findall(r"\d{1,2}\.\d{2}", line))
            if date_count > 0 and date_count >= len(re.findall(r"[а-яё]", line)):
                continue
        # Skip week parity lines
        if re.match(r"(верхн|нижн)[яа]я\s+неделя", line, re.IGNORECASE):
            continue
        # Skip cancellation/recovery lines
        if "отмена" in line or "восстановление" in line or "восстановлено" in line:
            continue
        # Skip make-up lines
        if re.match(r"\d{1,2}\.\d{2}\s*\(за\s+\d{1,2}\.\d{2}\)", line):
            continue
        # Skip location override lines
        if re.match(r"\d{1,2}\.\d{2}\s+(?:ауд\.|в)\s+", line):
            continue
        # Skip lines that are JUST a parenthesized type (e.g., "(семинары)")
        # but NOT lines where the type is part of a title (e.g., "Теория языка I (семинары)")
        if re.match(r"^\([^)]*\)$", line.strip()):
            continue
        # Skip lines that are ONLY the lesson type (no other content)
        # This is a more targeted check: if the line IS the lesson type
        # (e.g., "семинар" as a standalone line), skip it.
        # But do NOT skip lines like "Теория языка I (семинары)" where
        # the type is embedded in a longer title.
        if lesson_type:
            line_lower = line.lower()
            # Only skip if the line is EXACTLY the lesson type (possibly with whitespace/parentheses)
            if line_lower == lesson_type or line_lower == f"({lesson_type})":
                continue
        cleaned_lines.append(line)

    # Find teacher names
    teachers: list[str] = []
    title_lines: list[str] = []

    for line in cleaned_lines:
        teacher_matches = TEACHER_PATTERN.findall(line)
        if teacher_matches:
            teachers.extend(teacher_matches)
        else:
            title_lines.append(line)

    # The title is the first non-empty, non-teacher line
    title = ""
    for line in title_lines:
        if line:
            title = line
            break

    # Clean title from MKD/MDK/NIS prefix
    if title:
        title = MKD_PREFIX.sub("", title).strip()

    # Strip parenthesized lesson type from title (e.g., "Основы высшей математики (лекция)" -> "Основы высшей математики")
    if title and lesson_type:
        # Build a flexible pattern that matches both singular and plural forms
        # e.g., "лекция" matches "(лекция)" or "(лекции)"
        # e.g., "семинар" matches "(семинар)" or "(семинары)"
        type_stem = lesson_type.rstrip("ая")
        title = re.sub(
            rf"\s*\(\s*{re.escape(type_stem)}[а-я]*\s*\)\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

    # Remove duplicate teachers
    unique_teachers = list(dict.fromkeys(teachers))

    return title, unique_teachers


def _is_online(auditorium: str, building: str) -> bool:
    """Check if a lesson is online based on auditorium/building text."""
    online_indicators = ["online", "онлайн", "олайн"]
    combined = f"{auditorium} {building}".lower()
    for indicator in online_indicators:
        if indicator in combined:
            return True
    return False