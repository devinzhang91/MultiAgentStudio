"""
Common helpers shared across MushTech Studio screens.
"""

import unicodedata


def display_width(text: str) -> int:
    """Return the terminal display width for the given text."""
    width = 0
    for char in text:
        if unicodedata.east_asian_width(char) in ("F", "W") or unicodedata.category(char) == "So":
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text: str, width: int) -> str:
    """Pad or truncate text so that its display width matches the target."""
    if width <= 0:
        return ""

    current = display_width(text)
    padding = width - current

    if padding > 0:
        return text + " " * padding

    if padding < 0:
        truncated = ""
        filled = 0
        for char in text:
            char_width = display_width(char)
            if filled + char_width > width - 1:
                return truncated + "…"
            truncated += char
            filled += char_width
        return truncated + " " * max(0, width - filled)

    return text
