"""5-step wizard for the HSE Schedule Parser TUI.

Implements a state machine with WizardState dataclass and step functions.
Each step returns an updated WizardState or None (go back / exit).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from hse_parser.config import ParseConfig
from hse_parser.controller import run_pipeline

from hse_schedule_parser.autodetect import (
    detect_courses,
    detect_groups,
    detect_module_info,
    detect_subgroups,
    suggest_academic_year,
)
from hse_schedule_parser.presets import UserPresets, load_presets, save_presets
from hse_schedule_parser.tui import (
    ask_choice,
    ask_file,
    ask_path,
    ask_toggles,
    console,
    show_banner,
    show_error,
    show_goodbye,
    show_info,
    show_progress,
    show_report,
    show_success,
)

logger = logging.getLogger(__name__)


# ── Wizard State ────────────────────────────────────────────────────────


class WizardExit(Exception):
    """Raised to gracefully exit the wizard."""
    pass


class WizardState:
    """Holds all user choices throughout the wizard flow.

    Each step populates its relevant fields. The state is passed through
    the step pipeline and finally used to build a ParseConfig.
    """

    def __init__(self, presets: UserPresets | None = None) -> None:
        self.file_path: str = presets.last_file_path if presets else ""
        self.course: int = presets.last_course if presets else 0
        self.group_code: str = presets.last_group_code if presets else ""
        self.subgroup: int | None = presets.last_subgroup if presets else None
        self.academic_year: int = (
            presets.last_academic_year if presets and presets.last_academic_year
            else suggest_academic_year()
        )

        # Settings toggles (default from presets or True)
        self.skip_minor: bool = presets.skip_minor if presets else True
        self.skip_english: bool = presets.skip_english if presets else True
        self.skip_pe: bool = presets.skip_pe if presets else True

        # Output
        self.output_path: str = presets.last_output_dir if presets else ""
        self.preview_only: bool = False

        # Cached detection results (to avoid re-reading the file)
        self._available_courses: list[int] = []
        self._available_groups: list[str] = []
        self._available_subgroups: list[int] = []

    def to_presets(self) -> UserPresets:
        """Convert current state to UserPresets for saving."""
        return UserPresets(
            last_file_path=self.file_path,
            last_group_code=self.group_code,
            last_course=self.course,
            last_subgroup=self.subgroup,
            skip_minor=self.skip_minor,
            skip_english=self.skip_english,
            skip_pe=self.skip_pe,
            last_output_dir=str(Path(self.output_path).parent)
            if self.output_path else "",
            last_academic_year=self.academic_year,
        )


# ── Step 1: File Selection ──────────────────────────────────────────────


def _find_excel_in_root() -> list[Path]:
    """Scan the project root directory for .xlsx files."""
    root = Path.cwd()
    return sorted(root.glob("*.xlsx"))


def step_file(state: WizardState) -> WizardState | None:
    """Step 1: Select the Excel file with the schedule.

    Scans the project root for .xlsx files. If found, offers a choice:
      1 — use the found file
      2 — specify full path manually
      ← — go back (exit wizard)
      ✕ — exit
    If no .xlsx is found in root, shows an error and offers:
      1 — check again (after user placed the file)
      2 — specify full path manually
      ← — go back (exit wizard)
      ✕ — exit
    """
    found = _find_excel_in_root()

    if found:
        # File(s) found in root — offer choice
        file_list = "\n".join(f"  • {f.name}" for f in found)
        show_info(
            "📂 Найдены файлы в текущей директории:\n"
            f"{file_list}\n\n"
            "Выбери действие:"
        )
        choice = ask_choice(
            "Что делаем?",
            choices=[
                f"1 — продолжить с найденным файлом: {found[0].name}",
                "2 — указать полный путь к таблице с расписанием",
                "← Назад",
                "✕ Выход",
            ],
            default=f"1 — продолжить с найденным файлом: {found[0].name}",
        )
        if choice is None or choice == "✕ Выход":
            return None
        if choice == "← Назад":
            return None

        if choice.startswith("1"):
            state.file_path = str(found[0].resolve())
            return state

        # Fall through to manual path input
    else:
        # No files found in root
        show_error(
            "В этой директории файл не найден.",
            "Перемести файл с таблицей в эту директорию или укажи полный путь.",
        )
        choice = ask_choice(
            "Что делаем?",
            choices=[
                "1 — я переместил(а) файл, проверить снова",
                "2 — указать полный путь к таблице с расписанием",
                "✕ Выход",
            ],
            default="1 — я переместил(а) файл, проверить снова",
        )
        if choice is None or choice == "✕ Выход":
            return None

        if choice.startswith("1"):
            return step_file(state)  # Retry — scan again

        # Fall through to manual path input

    # Manual path input
    path = ask_file(
        "📂 Введи путь к файлу расписания (.xlsx):",
        default=state.file_path or "",
    )
    if path is None:
        return None

    path = path.strip()
    if not path:
        show_error("Путь не может быть пустым.", "Укажи путь к .xlsx файлу.")
        return step_file(state)

    # Validate
    p = Path(path)
    if not p.exists():
        show_error(
            f"Файл не найден: {path}",
            "Проверь путь. Можно перетащить файл в окно терминала.",
        )
        return step_file(state)  # Retry

    state.file_path = path
    return state


# ── Step 2: Group Selection ─────────────────────────────────────────────


def step_group(state: WizardState) -> WizardState | None:
    """Step 2: Detect courses and groups, let user select.

    First detects available courses from the file, then groups for the
    selected course.
    """
    show_info("Определяю доступные курсы и группы в файле...")

    # Detect courses
    courses = detect_courses(state.file_path)
    if not courses:
        show_error(
            "Не удалось определить курсы в файле.",
            "Убедись, что файл содержит листы с названиями "
            "'1 курс', '2 курс' и т.д.",
        )
        return None

    state._available_courses = courses

    # If only one course, auto-select
    if len(courses) == 1:
        state.course = courses[0]
        console.print(f"[dim]→ Обнаружен курс: {state.course}[/dim]")
    else:
        course_choices = [f"{c} курс" for c in courses] + ["← Назад", "✕ Выход"]
        selected = ask_choice(
            "🎓 Выбери курс:",
            choices=course_choices,
            default=f"{state.course} курс" if state.course else course_choices[0],
        )
        if selected is None or selected == "✕ Выход":
            return None
        if selected == "← Назад":
            return None
        # Parse course number from "N курс"
        state.course = int(selected.split()[0])

    # Detect groups for the selected course
    groups = detect_groups(state.file_path, state.course)
    if not groups:
        show_error(
            f"Не найдено групп для {state.course} курса.",
            "Возможно, файл имеет нестандартный формат.",
        )
        return None

    state._available_groups = groups

    # If we have a last group and it's in the list, pre-select it
    default_group = state.group_code if state.group_code in groups else groups[0]

    group_choices = groups + ["← Назад", "✕ Выход"]
    selected_group = ask_choice(
        f"👥 Выбери группу ({state.course} курс):",
        choices=group_choices,
        default=default_group,
    )
    if selected_group is None or selected_group == "✕ Выход":
        return None
    if selected_group == "← Назад":
        return None

    state.group_code = selected_group
    return state


# ── Step 3: Subgroup Filter ─────────────────────────────────────────────


def step_subgroup(state: WizardState) -> WizardState | None:
    """Step 3: Detect and optionally filter by subgroup.

    If the group has no subgroup split, skip this step.
    """
    subgroups = detect_subgroups(state.file_path, state.group_code)
    state._available_subgroups = subgroups

    if not subgroups:
        # No subgroups detected — skip
        state.subgroup = None
        return state

    # Build choices
    choices = ["Все подгруппы (без фильтра)"]
    for sg in subgroups:
        choices.append(f"Подгруппа {sg}")
    choices += ["← Назад", "✕ Выход"]

    selected = ask_choice(
        f"🔢 В расписании обнаружены подгруппы. Выбери фильтр:",
        choices=choices,
        default="Все подгруппы (без фильтра)",
    )
    if selected is None or selected == "✕ Выход":
        return None
    if selected == "← Назад":
        return None

    if selected == "Все подгруппы (без фильтра)":
        state.subgroup = None
    else:
        # Parse "Подгруппа N"
        state.subgroup = int(selected.split()[-1])

    return state


# ── Step 4: Settings ────────────────────────────────────────────────────


def step_settings(state: WizardState) -> WizardState | None:
    """Step 4: Toggle skip flags and configure settings.

    Shows checkboxes for:
    - Skip MINOR disciplines
    - Skip English language
    - Skip Physical Education

    Academic year is auto-detected from the current date.
    """
    show_info(
        "Настройки фильтрации.\n"
        "Отметь галочками то, что нужно пропустить (исключить из календаря).\n"
        "По умолчанию MINOR, английский и физра пропускаются.\n"
        f"Учебный год: {state.academic_year}/{state.academic_year + 1} (определён автоматически)"
    )

    # Toggle skip flags
    toggles = {
        "Пропускать MINOR": state.skip_minor,
        "Пропускать английский язык": state.skip_english,
        "Пропускать физкультуру": state.skip_pe,
    }

    result = ask_toggles(
        "⚙️ Что пропускать? (Space — переключить, Enter — подтвердить)",
        toggles=toggles,
    )
    if result is None:
        return None

    state.skip_minor = result.get("Пропускать MINOR", True)
    state.skip_english = result.get("Пропускать английский язык", True)
    state.skip_pe = result.get("Пропускать физкультуру", True)

    return state


# ── Step 5: Output ──────────────────────────────────────────────────────


def step_output(state: WizardState) -> WizardState | None:
    """Step 5: Choose output — save to cwd/ or specify custom path.

    Default: save to ./schedule_<group>.ics in the working directory.
    """
    default_name = f"schedule_{state.group_code}.ics"
    default_path = str(Path.cwd() / default_name)

    show_info(
        "Файл готов к обработке.\n"
        f"По умолчанию календарь сохранится в:\n"
        f"  {default_path}\n\n"
        "Выбери действие:"
    )

    choice = ask_choice(
        "💾 Сохранение календаря:",
        choices=[
            f"1 — сохранить в текущую директорию ({default_name})",
            "2 — указать другой путь для сохранения",
            "← Назад",
            "✕ Выход",
        ],
        default=f"1 — сохранить в текущую директорию ({default_name})",
    )
    if choice is None or choice == "✕ Выход":
        return None
    if choice == "← Назад":
        return None

    if choice.startswith("1"):
        state.output_path = default_path
        state.preview_only = False
        return state

    # Custom path
    path = ask_path(
        "💾 Укажи путь для сохранения .ics файла:",
        default=default_path,
    )
    if path is None:
        return None

    state.output_path = path
    state.preview_only = False
    return state


# ── Execution ───────────────────────────────────────────────────────────


def _build_config(state: WizardState) -> ParseConfig:
    """Build a ParseConfig from the wizard state."""
    return ParseConfig(
        file_path=Path(state.file_path),
        group_code=state.group_code,
        output_path=Path(state.output_path) if state.output_path else None,
        subgroup=state.subgroup,
        academic_year_start=state.academic_year,
        skip_minor=state.skip_minor,
        skip_english=state.skip_english,
        skip_pe=state.skip_pe,
        verbose=False,
    )


def _execute_parse(state: WizardState) -> None:
    """Run the parsing pipeline and show results."""
    config = _build_config(state)

    # Show progress
    progress = show_progress()
    with progress:
        task = progress.add_task(
            f"⏳ Парсинг расписания для {state.group_code}...",
            total=100,
        )

        # Update progress to 10% — reading file
        progress.update(task, advance=10)

        # Run pipeline
        result = run_pipeline(config)

        # Update to 100%
        progress.update(task, completed=100)

    console.print()

    # Show report
    show_report(
        report_text=result.report,
        warnings=result.warnings,
        events_count=result.events_count,
    )

    # Save or preview
    if state.preview_only or not state.output_path:
        show_success(ics_path=None)
    else:
        try:
            output = Path(state.output_path)
            output.write_bytes(result.ics_content)
            show_success(ics_path=output)
        except OSError as e:
            show_error(
                f"Не удалось сохранить файл: {e}",
                "Проверь права на запись в папку.",
            )


# ── Main Wizard Entry Point ─────────────────────────────────────────────


def run_wizard() -> None:
    """Run the full 5-step wizard.

    This is the main entry point called from __main__.py.
    """
    try:
        _run_wizard_impl()
    except WizardExit:
        pass
    except KeyboardInterrupt:
        console.print()
        show_goodbye()
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled error in wizard")
        show_error(
            f"Произошла непредвиденная ошибка: {e}",
            "Пожалуйста, создай issue на GitHub с описанием проблемы.",
        )
        sys.exit(1)


def _run_wizard_impl() -> None:
    """Internal wizard implementation with step-by-step flow."""
    # Load presets
    presets = load_presets()

    # Show banner
    show_banner()

    # Initialize state
    state = WizardState(presets=presets)

    # ── Step 1: File ──
    result = step_file(state)
    if result is None:
        show_goodbye()
        return
    state = result

    # ── Step 2: Group ──
    result = step_group(state)
    if result is None:
        show_goodbye()
        return
    state = result

    # ── Step 3: Subgroup ──
    result = step_subgroup(state)
    if result is None:
        show_goodbye()
        return
    state = result

    # ── Step 4: Settings ──
    result = step_settings(state)
    if result is None:
        show_goodbye()
        return
    state = result

    # ── Step 5: Output ──
    result = step_output(state)
    if result is None:
        show_goodbye()
        return
    state = result

    # ── Execute ──
    _execute_parse(state)

    # ── Save presets ──
    save_presets(state.to_presets())

    # ── Done ──
    console.print("[dim]Нажми Enter, чтобы выйти...[/dim]")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

    show_goodbye()