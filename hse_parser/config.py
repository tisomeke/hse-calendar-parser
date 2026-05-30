"""Configuration models for the HSE schedule parser."""

from pathlib import Path

from pydantic import BaseModel, Field


class ParseConfig(BaseModel):
    """All configuration parameters for a parsing run."""

    file_path: Path = Field(description="Path to the .xlsx file")
    group_code: str = Field(description="Group code, e.g. 25ФПЛ1")
    output_path: Path | None = Field(
        default=None, description="Output .ics file path (auto-generated if None)"
    )
    subgroup: int | None = Field(
        default=None, description="Subgroup number (1 or 2)"
    )
    academic_year_start: int = Field(
        default=2025, description="Start year of the academic year"
    )
    skip_minor: bool = Field(
        default=True, description="Skip MINOR discipline entries"
    )
    skip_english: bool = Field(
        default=True, description="Skip English language entries"
    )
    skip_pe: bool = Field(
        default=True, description="Skip Physical Education entries"
    )
    verbose: bool = Field(default=False, description="Verbose console output")