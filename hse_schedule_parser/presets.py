"""User preferences management for the HSE Schedule Parser.

Saves and loads user settings to/from a JSON file in the XDG config directory.
Supports: last file path, last group, skip flags, reminders preference.
"""

from __future__ import annotations

import json
import logging
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UserPresets:
    """User preferences that persist between sessions."""

    last_file_path: str = ""
    last_group_code: str = ""
    last_course: int = 0
    last_subgroup: int | None = None
    skip_minor: bool = True
    skip_english: bool = True
    skip_pe: bool = True
    last_output_dir: str = ""
    last_academic_year: int = 0

    def is_empty(self) -> bool:
        """Check if presets have any meaningful data."""
        return not (self.last_file_path or self.last_group_code)


def _get_config_dir() -> Path:
    """Get the platform-appropriate config directory.

    - Linux: ~/.config/hse-schedule-parser
    - macOS: ~/Library/Application Support/hse-schedule-parser
    - Windows: %APPDATA%/hse-schedule-parser
    """
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        # Linux / BSD / other Unix
        xdg_config = Path.home() / ".config"
        base = xdg_config

    return base / "hse-schedule-parser"


def _get_presets_path() -> Path:
    """Get the full path to the presets JSON file."""
    return _get_config_dir() / "presets.json"


def load_presets() -> UserPresets:
    """Load user presets from disk.

    Returns a UserPresets object (defaults if file doesn't exist or is invalid).
    """
    path = _get_presets_path()

    if not path.exists():
        logger.debug("No presets file found at %s", path)
        return UserPresets()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Filter to only known fields
        known_fields = {f.name for f in dataclass_fields(UserPresets)}
        filtered = {k: v for k, v in data.items() if k in known_fields}

        presets = UserPresets(**filtered)
        logger.debug("Loaded presets from %s", path)
        return presets

    except (json.JSONDecodeError, OSError, TypeError) as e:
        logger.warning("Failed to load presets from %s: %s", path, e)
        return UserPresets()


def dataclass_fields(cls: type) -> list:
    """Get dataclass fields (compat helper)."""
    import dataclasses
    return dataclasses.fields(cls)


def save_presets(presets: UserPresets) -> bool:
    """Save user presets to disk.

    Args:
        presets: The UserPresets object to save.

    Returns:
        True if saved successfully, False otherwise.
    """
    path = _get_presets_path()

    try:
        # Ensure config directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(presets)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug("Saved presets to %s", path)
        return True

    except OSError as e:
        logger.warning("Failed to save presets to %s: %s", path, e)
        return False


def update_presets(**kwargs) -> UserPresets:
    """Load presets, update with given kwargs, save, and return.

    Args:
        **kwargs: Fields to update on the UserPresets object.

    Returns:
        The updated UserPresets object.
    """
    presets = load_presets()
    for key, value in kwargs.items():
        if hasattr(presets, key):
            setattr(presets, key, value)
    save_presets(presets)
    return presets