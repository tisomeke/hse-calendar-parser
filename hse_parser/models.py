"""Internal data models for the HSE schedule parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


@dataclass
class RawLessonBlock:
    """A single parsed lesson block from a cell's text content."""

    dates: list[date] = field(default_factory=list)
    title: str = ""
    lesson_type: str = "занятие"
    teachers: list[str] = field(default_factory=list)
    subgroup: int | None = None
    is_online: bool = False
    is_cancelled: bool = False
    recovery_date: date | None = None
    week_parity: Literal["upper", "lower", None] = None
    location_override: dict[date, str] = field(default_factory=dict)
    period_start: date | None = None
    """Cell-specific period start (overrides module period when set)."""
    period_end: date | None = None
    """Cell-specific period end (overrides module period when set)."""


@dataclass
class Event:
    """A single calendar event ready for ICS export."""

    uid: str
    summary: str
    start: datetime
    end: datetime
    location: str | None = None
    description: str = ""
    source_text: str = ""
    status: str = "CONFIRMED"


@dataclass
class Warning:
    """A warning about a skipped or problematic cell."""

    row: int
    col: str
    text: str
    reason: str

    def __str__(self) -> str:
        truncated = self.text[:200]
        return f"[{self.reason}] Row {self.row}, Col {self.col}: {truncated}"


@dataclass
class ParseResult:
    """Result of a full parsing pipeline run."""

    ics_content: bytes
    report: str
    warnings: list[Warning]
    events_count: int