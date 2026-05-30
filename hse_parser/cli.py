"""CLI interface for the HSE schedule parser."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from hse_parser.config import ParseConfig
from hse_parser.controller import run_pipeline


def _setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


@click.command()
@click.option(
    "--file",
    "-f",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the .xlsx schedule file",
)
@click.option(
    "--group",
    "-g",
    required=True,
    help="Group code (e.g. 25ФПЛ1)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    help="Output .ics file path (default: <group>_module<N>.ics)",
)
@click.option(
    "--subgroup",
    type=click.IntRange(1, 2),
    help="Subgroup number (1 or 2)",
)
@click.option(
    "--academic-year-start",
    default=2025,
    show_default=True,
    help="Start year of the academic year",
)
@click.option(
    "--skip-minor/--no-skip-minor",
    default=True,
    show_default=True,
    help="Skip MINOR discipline entries",
)
@click.option(
    "--skip-english/--no-skip-english",
    default=True,
    show_default=True,
    help="Skip English language entries",
)
@click.option(
    "--skip-pe/--no-skip-pe",
    default=True,
    show_default=True,
    help="Skip Physical Education entries",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output with per-row progress",
)
def main(
    file: str,
    group: str,
    output: str | None,
    subgroup: int | None,
    academic_year_start: int,
    skip_minor: bool,
    skip_english: bool,
    skip_pe: bool,
    verbose: bool,
) -> None:
    """Parse HSE schedule from EXCEL_FILE and generate an .ics calendar.

    Reads a university schedule Excel file (.xlsx) exported from Google Sheets,
    extracts events for the specified student GROUP, and generates an iCalendar
    (.ics) file compatible with Google Calendar, Apple Calendar, and Outlook.
    """
    _setup_logging(verbose)

    config = ParseConfig(
        file_path=Path(file),
        group_code=group,
        output_path=Path(output) if output else None,
        subgroup=subgroup,
        academic_year_start=academic_year_start,
        skip_minor=skip_minor,
        skip_english=skip_english,
        skip_pe=skip_pe,
        verbose=verbose,
    )

    # Run pipeline
    result = run_pipeline(config)

    # Print report
    click.echo(result.report)

    # Determine output path
    if config.output_path:
        output_path = config.output_path
    else:
        # Auto-generate: <group>_module<N>.ics
        # Extract module from file name or use default
        module_str = "?"
        import re

        file_match = re.search(r"(\d+)\s+модуль", str(config.file_path))
        if file_match:
            module_str = file_match.group(1)
        output_path = Path(f"{config.group_code}_module{module_str}.ics")

    # Save .ics file
    output_path.write_bytes(result.ics_content)
    click.echo(f"\nСохранено в: {output_path}")

    # Print warnings
    if result.warnings:
        has_critical = any(
            w.reason in ("UNPARSEABLE_FORMAT", "MULTIPLE_SUBGROUPS_UNSPECIFIED")
            for w in result.warnings
        )
        if verbose or has_critical:
            click.echo("\n=== ПРЕДУПРЕЖДЕНИЯ ===")
            for w in result.warnings:
                click.echo(f"  {w}")

        if has_critical:
            click.secho(
                "ВНИМАНИЕ: Обнаружены нераспознанные ячейки. "
                "Проверьте отчёт выше.",
                err=True,
                fg="yellow",
            )


if __name__ == "__main__":
    main()