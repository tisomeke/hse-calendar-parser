"""Controller: orchestrates the full parsing pipeline."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

from hse_parser.config import ParseConfig
from hse_parser.date_engine import generate_dates
from hse_parser.exporter import (
    build_description,
    build_location,
    build_summary,
    create_calendar,
    serialize_calendar,
)
from hse_parser.models import Event, ParseResult, Warning
from hse_parser.parser.cell_parser import parse_cell
from hse_parser.reader import read_schedule
from hse_parser.utils import (
    generate_uid,
    parse_time_range,
    resolve_year,
)

logger = logging.getLogger(__name__)


def run_pipeline(config: ParseConfig) -> ParseResult:
    """Run the full parsing pipeline.

    Args:
        config: All configuration parameters

    Returns:
        ParseResult with .ics content, report, and warnings
    """
    warnings_list: list[Warning] = []
    events: list[Event] = []
    total_cells = 0
    parsed_cells = 0
    skip_counts: dict[str, int] = {}

    # 1. Read Excel file
    reader_result = read_schedule(
        str(config.file_path),
        config.group_code,
        config.academic_year_start,
    )

    if reader_result is None:
        return ParseResult(
            ics_content=b"",
            report="ОШИБКА: Не удалось прочитать файл или найти группу",
            warnings=[],
            events_count=0,
        )

    # Resolve year for dates
    year = resolve_year(
        reader_result.module, config.academic_year_start
    )

    # 2. Process each row
    for row in reader_result.rows:
        if not row.subject_text.strip():
            continue

        total_cells += 1

        # Parse cell
        blocks, warning_reason = parse_cell(
            text=row.subject_text,
            year=year,
            day_name=row.day_name,
            auditorium=row.auditorium,
            building=row.building,
            subgroup_filter=config.subgroup,
            skip_minor=config.skip_minor,
            skip_english=config.skip_english,
            skip_pe=config.skip_pe,
        )

        if warning_reason:
            skip_counts[warning_reason] = (
                skip_counts.get(warning_reason, 0) + 1
            )
            warnings_list.append(
                Warning(
                    row=row.row_number,
                    col=row.col_letter,
                    text=row.subject_text[:200],
                    reason=warning_reason,
                )
            )
            if config.verbose:
                logger.info(
                    "Row %d: SKIP [%s]",
                    row.row_number,
                    warning_reason,
                )
            continue

        if not blocks:
            continue

        parsed_cells += 1

        # 3. Generate dates for each block
        for block in blocks:
            dates = generate_dates(
                block,
                row.day_name,
                reader_result.module_period_start,
                reader_result.module_period_end,
                year,
                calendar_upper_dates=reader_result.calendar_upper_dates,
            )

            if not dates:
                continue

            # Parse time range
            time_range = parse_time_range(row.time_range)
            if time_range is None:
                continue

            start_time, end_time = time_range

            # 4. Create events for each date
            for dt in dates:
                # Skip cancelled dates
                if block.is_cancelled and dt in block.dates:
                    continue

                # Check location override for this date
                location_override = block.location_override.get(dt)
                if location_override:
                    location = location_override
                else:
                    location = build_location(
                        row.auditorium, row.building, block.is_online
                    )

                # Build summary
                summary = build_summary(block.lesson_type, block.title)

                # Build description
                description = build_description(
                    block.teachers, row.subject_text
                )

                # Generate UID
                uid = generate_uid(
                    config.group_code,
                    dt,
                    start_time,
                    block.title,
                    ", ".join(block.teachers) if block.teachers else "",
                )

                event = Event(
                    uid=uid,
                    summary=summary,
                    start=datetime.combine(dt, start_time),
                    end=datetime.combine(dt, end_time),
                    location=location,
                    description=description,
                    source_text=row.subject_text,
                    status="CONFIRMED",
                )
                events.append(event)

                if config.verbose:
                    logger.info(
                        "Row %d: %s %s %s-%s %s",
                        row.row_number,
                        dt.isoformat(),
                        summary,
                        start_time.strftime("%H:%M"),
                        end_time.strftime("%H:%M"),
                        location or "",
                    )

    # 5. Export to ICS
    cal = create_calendar(events, config.group_code)
    ics_content = serialize_calendar(cal)

    # 6. Build report
    report = _build_report(
        total_cells,
        parsed_cells,
        skip_counts,
        config.group_code,
        reader_result.module,
        len(events),
    )

    return ParseResult(
        ics_content=ics_content,
        report=report,
        warnings=warnings_list,
        events_count=len(events),
    )


def _build_report(
    total_cells: int,
    parsed_cells: int,
    skip_counts: dict[str, int],
    group_code: str,
    module: int,
    events_count: int,
) -> str:
    """Build a human-readable report string."""
    skipped = total_cells - parsed_cells
    lines = [
        "=== ОТЧЁТ ===",
        f"Всего обработано ячеек: {total_cells}",
        f"Успешно распарсено: {parsed_cells}",
        f"Пропущено: {skipped}",
    ]

    reason_labels = {
        "EXTERNAL_SCHEDULE": "Внешнее расписание (английский)",
        "PHYSICAL_EDUCATION": "Физкультура",
        "MINOR": "MINOR",
        "UNPARSEABLE_FORMAT": "Нераспознанный формат",
        "EMPTY_CELL": "Пустая ячейка",
        "ISOLATED_NAME": "Изолированная фамилия",
        "ONLINE_LINKS_HEADER": "Заголовок online-ссылок",
    }

    for reason, count in sorted(skip_counts.items()):
        label = reason_labels.get(reason, reason)
        lines.append(f"  - {label}: {count}")

    lines.append("")
    lines.append(f"Событий в календаре: {events_count}")

    return "\n".join(lines)