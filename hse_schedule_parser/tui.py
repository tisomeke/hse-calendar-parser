"""Rich UI components for the HSE Schedule Parser TUI wizard.

Provides styled panels, progress bars, report displays, and interactive prompts
using the `rich` and `questionary` libraries.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from hse_parser.models import Warning as ParseWarning

logger = logging.getLogger(__name__)

console = Console()


# ── Banner ──────────────────────────────────────────────────────────────


def show_banner() -> None:
    """Display the application header banner."""
    banner_text = Text()
    banner_text.append("📅 HSE Schedule Parser", style="bold cyan")
    banner_text.append("\n")
    banner_text.append("Конвертер расписания ВШЭ → iCalendar (.ics)", style="dim white")
    banner_text.append("\n")
    banner_text.append("v2.1 • TUI Wizard", style="italic yellow")

    panel = Panel(
        banner_text,
        border_style="cyan",
        padding=(1, 2),
        title="[bold]Добро пожаловать![/]",
        subtitle="[dim]Введи /back чтобы вернуться на шаг назад[/]",
    )
    console.print(panel)
    console.print()


# ── Progress ────────────────────────────────────────────────────────────


def show_progress() -> Progress:
    """Create and return a progress bar context for parsing.

    Usage:
        progress = show_progress()
        with progress:
            task = progress.add_task("Парсинг...", total=100)
            ...
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )
    return progress


# ── Report ──────────────────────────────────────────────────────────────


def show_report(
    report_text: str,
    warnings: list[ParseWarning],
    events_count: int,
) -> None:
    """Display a formatted parsing report with warnings table.

    Args:
        report_text: The plain-text report from the controller.
        warnings: List of warnings from the parsing run.
        events_count: Number of events generated.
    """
    # ── Report panel ──
    report_panel = Panel(
        report_text,
        title="[bold green]✅ Отчёт[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(report_panel)
    console.print()

    # ── Warnings table ──
    if warnings:
        table = Table(
            title="⚠️ Предупреждения",
            border_style="yellow",
            header_style="bold yellow",
        )
        table.add_column("Строка", style="dim", width=8)
        table.add_column("Колонка", style="dim", width=8)
        table.add_column("Причина", style="yellow", width=24)
        table.add_column("Текст", style="white", width=60, no_wrap=False)

        for w in warnings[:20]:  # Show max 20 warnings
            table.add_row(
                str(w.row),
                w.col,
                w.reason,
                w.text[:120],
            )

        if len(warnings) > 20:
            table.add_row(
                "...",
                "...",
                "...",
                f"... и ещё {len(warnings) - 20} предупреждений",
            )

        console.print(table)
        console.print()

    # ── Summary ──
    summary = Text()
    summary.append(f"✅ Создано событий: {events_count}", style="bold green")
    if warnings:
        summary.append(f"\n⚠️ Предупреждений: {len(warnings)}", style="yellow")
    console.print(summary)
    console.print()


def show_success(ics_path: Path | None = None) -> None:
    """Display a success/completion message with import instructions.

    Args:
        ics_path: Path to the saved .ics file, or None if preview-only.
    """
    if ics_path:
        text = Text()
        text.append("✅ Файл успешно сохранён!\n\n", style="bold green")
        text.append(f"📁 {ics_path.resolve()}\n\n", style="cyan")
        text.append("📌 Чтобы импортировать в календарь:\n", style="bold")
        text.append("   • Google Календарь: Настройки → Импорт\n", style="dim")
        text.append("   • Apple Календарь: Файл → Импортировать\n", style="dim")
        text.append("   • Outlook: Файл → Открыть и экспортировать\n", style="dim")
        text.append("   • Яндекс Календарь: Настройки → Импорт\n", style="dim")

        panel = Panel(
            text,
            title="[bold green]Готово![/]",
            border_style="green",
            padding=(1, 2),
        )
    else:
        text = Text()
        text.append("📋 Предпросмотр завершён\n\n", style="bold yellow")
        text.append("Файл не был сохранён. Запусти wizard снова, чтобы сохранить.", style="dim")

        panel = Panel(
            text,
            title="[bold yellow]Предпросмотр[/]",
            border_style="yellow",
            padding=(1, 2),
        )

    console.print(panel)
    console.print()


# ── Error ───────────────────────────────────────────────────────────────


def show_error(message: str, hint: str | None = None) -> None:
    """Display an error message panel.

    Args:
        message: The error message to display.
        hint: Optional hint for how to fix the error.
    """
    text = Text()
    text.append(f"❌ {message}", style="bold red")
    if hint:
        text.append(f"\n💡 {hint}", style="dim italic")

    panel = Panel(
        text,
        title="[bold red]Ошибка[/]",
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def show_info(message: str) -> None:
    """Display an informational message panel.

    Args:
        message: The info message to display.
    """
    panel = Panel(
        message,
        title="[bold blue]ℹ️ Информация[/]",
        border_style="blue",
        padding=(1, 1),
    )
    console.print(panel)
    console.print()


# ── Interactive Prompts (questionary wrappers) ──────────────────────────


def ask_file(
    message: str = "📂 Укажи путь к файлу расписания (.xlsx)",
    default: str | None = None,
) -> str | None:
    """Ask the user to input a file path.

    Returns the path string, or None if the user wants to go back.
    """
    import questionary

    result = questionary.text(
        message,
        default=default or "",
        validate=_validate_file_path,
    ).ask()

    return result


def _validate_file_path(path: str) -> bool | str:
    """Validate that a file path exists and is an .xlsx file."""
    if not path.strip():
        return "Путь не может быть пустым. Укажи путь к файлу."
    p = Path(path.strip())
    if not p.exists():
        return f"Файл не найден: {path}"
    if p.suffix.lower() not in (".xlsx", ".xls"):
        return "Файл должен быть Excel (.xlsx)"
    return True


def ask_choice(
    title: str,
    choices: list[str],
    default: str | None = None,
    instruction: str = "↑↓ для навигации, Enter для выбора",
) -> str | None:
    """Show a numbered list selection prompt.

    Args:
        title: The question/prompt text.
        choices: List of options to choose from.
        default: Default selected value.
        instruction: Helper text shown below the prompt.

    Returns:
        Selected value string, or None if user wants to go back.
    """
    import questionary

    if not choices:
        return None

    result = questionary.select(
        title,
        choices=choices,
        default=default or choices[0],
        instruction=instruction,
    ).ask()

    return result


def ask_toggles(
    title: str,
    toggles: dict[str, bool],
    instruction: str = "Space для переключения, Enter для подтверждения",
) -> dict[str, bool] | None:
    """Show a checkbox prompt for toggling boolean settings.

    Args:
        title: The prompt text.
        toggles: Dict mapping label -> default value.
        instruction: Helper text.

    Returns:
        Dict with updated values, or None if user wants to go back.
    """
    import questionary

    # Build questionary checklist items
    choices = []
    for label, default_val in toggles.items():
        choices.append(
            questionary.Choice(
                title=label,
                checked=default_val,
                value=label,
            )
        )

    selected = questionary.checkbox(
        title,
        choices=choices,
        instruction=instruction,
    ).ask()

    if selected is None:
        return None

    # Convert back to dict: checked items are True, unchecked are False
    result = {}
    for label in toggles:
        result[label] = label in selected

    return result


def ask_path(
    message: str = "💾 Куда сохранить файл?",
    default: str | None = None,
    file_name: str = "schedule.ics",
) -> str | None:
    """Ask the user for a save path.

    Args:
        message: The prompt text.
        default: Default directory path.
        file_name: Suggested file name.

    Returns:
        Path string, or None to go back.
    """
    import questionary

    default_path = str(Path(default or Path.home() / "Downloads") / file_name)

    result = questionary.text(
        message,
        default=default_path,
        validate=_validate_output_path,
    ).ask()

    return result


def _validate_output_path(path: str) -> bool | str:
    """Validate that the output directory exists."""
    p = Path(path.strip())
    if not p.parent.exists():
        return f"Папка не существует: {p.parent}"
    if p.suffix.lower() != ".ics":
        return "Файл должен иметь расширение .ics"
    return True


def ask_confirm(
    message: str = "Продолжить?",
    default: bool = True,
) -> bool | None:
    """Ask a yes/no confirmation question.

    Returns:
        True/False, or None to go back.
    """
    import questionary

    result = questionary.confirm(message, default=default).ask()
    return result


def ask_text(
    message: str,
    default: str = "",
    validate: Callable[[str], bool | str] | None = None,
    instruction: str = "",
) -> str | None:
    """Ask for free-form text input.

    Args:
        message: The prompt text.
        default: Default value.
        validate: Optional validation function.
        instruction: Helper text.

    Returns:
        Input string, or None to go back.
    """
    import questionary

    result = questionary.text(
        message,
        default=default,
        validate=validate,
        instruction=instruction,
    ).ask()

    return result


# ── Graceful exit ───────────────────────────────────────────────────────


def show_goodbye() -> None:
    """Display a goodbye message on exit."""
    text = Text()
    text.append("👋 До встречи!", style="bold cyan")
    text.append("\n")
    text.append("HSE Schedule Parser v2.1", style="dim")

    panel = Panel(
        text,
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)