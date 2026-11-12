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
