"""Skip rules for cell content that should be ignored."""

import re

# Patterns for content that should be skipped entirely
SKIP_PATTERNS: list[re.Pattern] = [
    re.compile(r"Занятия проводятся по расписанию дисциплины", re.IGNORECASE),
    re.compile(r"Английский язык", re.IGNORECASE),
    re.compile(r"Физическая культура", re.IGNORECASE),
    re.compile(r"дисциплинам дополнительного профиля MINOR", re.IGNORECASE),
    re.compile(r"ССЫЛКИ НА ONLINE", re.IGNORECASE),
]

# Patterns for content that should be skipped if they are the ONLY content
# (isolated teacher names, etc.)
ISOLATED_NAME_PATTERN = re.compile(
    r"^[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.?$"
)
ISOLATED_SURNAME_PATTERN = re.compile(
    r"^[А-ЯЁ][а-яё]+$"
)


def should_skip(text: str) -> tuple[bool, str]:
    """Check if a text block should be skipped.

    Returns (should_skip, reason) tuple.
    If should_skip is False, reason is empty string.
    """
    if not text or not text.strip():
        return True, "EMPTY_CELL"

    for pattern in SKIP_PATTERNS:
        if pattern.search(text):
            # Determine specific reason
            if "Английский" in text:
                return True, "EXTERNAL_SCHEDULE"
            if "Физическая культура" in text:
                return True, "PHYSICAL_EDUCATION"
            if "MINOR" in text:
                return True, "MINOR"
            if "ССЫЛКИ НА ONLINE" in text:
                return True, "ONLINE_LINKS_HEADER"
            return True, "EXTERNAL_SCHEDULE"

    # Check for isolated name (just a teacher name, no context)
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) == 1:
        line = lines[0]
        if ISOLATED_NAME_PATTERN.match(line) or ISOLATED_SURNAME_PATTERN.match(line):
            return True, "ISOLATED_NAME"

    return False, ""