"""Text normalization utilities for cell content."""

import re


def normalize_text(text: str) -> str:
    """Normalize cell text for parsing.

    Steps:
    1. Replace HTML tags: <br> → \\n, <br/> → \\n
    2. Replace &nbsp; → space
    3. Normalize line endings: \\r\\n → \\n
    4. Strip leading/trailing whitespace per line
    5. Normalize online variants → 'online'
    6. Normalize отмена variants → 'отмена'
    7. Normalize восстановление variants → 'восстановление'
    8. Collapse multiple empty lines
    """
    if not text:
        return ""

    # 1. Replace HTML tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?[^>]+>", "", text)

    # 2. Replace &nbsp;
    text = text.replace("&nbsp;", " ")

    # 3. Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 4. Strip whitespace per line
    lines = text.split("\n")
    lines = [line.strip() for line in lines]
    text = "\n".join(lines)

    # 5. Normalize online variants
    text = re.sub(
        r"\b(?:онлайн|олайн|ONLINE|Онлайн|Олайн)\b",
        "online",
        text,
    )

    # 6. Normalize отмена variants
    text = re.sub(
        r"\b(?:Отмена|ОТМЕНА|отмена)\b",
        "отмена",
        text,
    )

    # 7. Normalize восстановление variants (including typos)
    text = re.sub(
        r"\b(?:восстановление|восстановлено|восст[ао]н[ао]вление|восстнолвение|Восстановление|Восстнолвение)\b",
        "восстановление",
        text,
    )

    # 8. Collapse multiple empty lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 9. Strip overall
    text = text.strip()

    return text


def split_into_blocks(text: str) -> list[str]:
    """Split normalized text into logical lesson blocks.

    Separators (in order of priority):
    - Line of underscores: ____+ (≥10 chars of _ or -)
    - Double newline: \\n\\n
    """
    if not text:
        return []

    # Try underscore/hyphen line separator first
    blocks = re.split(r"\n[_\-]{10,}\n", text)
    if len(blocks) > 1:
        return [b.strip() for b in blocks if b.strip()]

    # Try double newline
    blocks = re.split(r"\n\n", text)
    return [b.strip() for b in blocks if b.strip()]