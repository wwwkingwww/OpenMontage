"""Pure text helpers for URL-safe slugs and similar transforms."""

from __future__ import annotations

import re


def slugify(text: str, *, separator: str = "-") -> str:
    """Lowercase text and fold non-alphanumeric runs into a single separator."""
    lowered = text.lower()
    collapsed = re.sub(r"[^a-z0-9]+", separator, lowered)
    if not separator:
        return collapsed
    return collapsed.strip(separator)


def title_case(text: str) -> str:
    """Capitalize the first letter of each whitespace-separated word.

    Consecutive whitespace is collapsed to a single space; leading and trailing
    whitespace is stripped. Words that do not start with a letter stay lowercased.
    """
    if not text.strip():
        return ""
    parts: list[str] = []
    for word in text.split():
        lowered = word.lower()
        if lowered[0].isalpha():
            parts.append(lowered[0].upper() + lowered[1:])
        else:
            parts.append(lowered)
    return " ".join(parts)
