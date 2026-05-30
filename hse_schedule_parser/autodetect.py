"""Smart detection of courses, groups, and modules from Excel files.

Opens an .xlsx workbook and scans for:
- Available course sheets (1 курс, 2 курс, etc.)
- Group codes within each course sheet
- Module number and period from the title row
- Subgroup information
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import openpyxl

from hse_parser.reader import (
    COURSE_PREFIX_MAP,
    COURSE_TO_SHEET,
    _group_exists_in_sheet,
    extract_title_info,
    find_group_columns,
)
from hse_parser.utils import normalize_group_code

logger = logging.getLogger(__name__)


def detect_courses(file_path: str | Path) -> list[int]:
    """Detect which course sheets are available in the workbook.

    Returns a sorted list of course numbers (e.g. [1, 2, 3, 4]).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    try:
        wb = openpyxl.load_workbook(str(file_path), read_only=True)
    except Exception:
        return []

    available_sheets = set(wb.sheetnames)
    wb.close()

    courses: list[int] = []
    for course_num, sheet_name in COURSE_TO_SHEET.items():
        if sheet_name in available_sheets:
            courses.append(course_num)
        # Also check "1 курс." variant for 1st year
        if course_num == 1 and "1 курс." in available_sheets:
            if 1 not in courses:
                courses.append(1)

    return sorted(courses)


def detect_groups(file_path: str | Path, course: int) -> list[str]:
    """Detect all group codes available for a given course.

    Returns a sorted list of group code strings.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    try:
        wb = openpyxl.load_workbook(str(file_path), read_only=True)
    except Exception:
        return []

    # Determine sheet name
    sheet_name = COURSE_TO_SHEET.get(course)
    if course == 1 and "1 курс." in wb.sheetnames:
        sheet_name = "1 курс."

    if sheet_name not in wb.sheetnames:
        wb.close()
        return []

    ws = wb[sheet_name]
    groups: list[str] = []

    # Scan row 10 for group codes
    for row in ws.iter_rows(min_row=10, max_row=10, values_only=False):
        for cell in row:
            if cell.value is not None:
                val = str(cell.value).strip()
                # Match group code pattern: 2 digits + letters
                if re.match(r"^\d{2}[А-ЯЁа-яё0-9]+$", val):
                    groups.append(val)

    wb.close()
    return sorted(set(groups))


def detect_module_info(
    file_path: str | Path, course: int
) -> dict | None:
    """Detect module number and period for a given course.

    Returns dict with 'module', 'period_start', 'period_end' or None.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    try:
        wb = openpyxl.load_workbook(str(file_path), read_only=True)
    except Exception:
        return None

    sheet_name = COURSE_TO_SHEET.get(course)
    if course == 1 and "1 курс." in wb.sheetnames:
        sheet_name = "1 курс."

    if sheet_name not in wb.sheetnames:
        wb.close()
        return None

    ws = wb[sheet_name]
    title_info = extract_title_info(ws)
    wb.close()

    if title_info is None:
        return None

    module, period_start, period_end = title_info
    return {
        "module": module,
        "period_start": period_start,
        "period_end": period_end,
    }


def detect_subgroups(
    file_path: str | Path, group_code: str
) -> list[int]:
    """Detect if a group has subgroup split.

    Scans the schedule data for 'гр.1' and 'гр.2' markers.
    Returns list of detected subgroup numbers (e.g. [1, 2] or []).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return []

    try:
        wb = openpyxl.load_workbook(str(file_path), read_only=True)
    except Exception:
        return []

    # Find the right sheet
    prefix = group_code[:2]
    course = COURSE_PREFIX_MAP.get(prefix)
    if course is None:
        wb.close()
        return []

    sheet_name = COURSE_TO_SHEET.get(course)
    if course == 1 and "1 курс." in wb.sheetnames:
        sheet_name = "1 курс."

    if sheet_name not in wb.sheetnames:
        wb.close()
        return []

    ws = wb[sheet_name]

    # Find group columns
    columns = find_group_columns(ws, group_code)
    if columns is None:
        wb.close()
        return []

    subject_col, _, _ = columns
    from hse_parser.reader import _col_to_index

    subj_idx = _col_to_index(subject_col)
    subgroups: set[int] = set()

    for row_cells in ws.iter_rows(min_row=12, values_only=False):
        if subj_idx >= len(row_cells):
            continue
        cell = row_cells[subj_idx]
        if cell.value is not None:
            text = str(cell.value)
            # Look for "гр.1" or "гр.2" patterns
            for match in re.finditer(r"гр\.?\s*(\d+)", text):
                sg = int(match.group(1))
                if sg in (1, 2):
                    subgroups.add(sg)

    wb.close()
    return sorted(subgroups)


def suggest_academic_year() -> int:
    """Suggest the academic year start based on current date.

    If current month is >= September, academic year started this year.
    Otherwise, it started last year.
    """
    from datetime import date

    today = date.today()
    if today.month >= 9:
        return today.year
    return today.year - 1