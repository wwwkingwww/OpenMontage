"""Caption formatting helpers composing text_utils and string_utils."""

from __future__ import annotations

from lib.string_utils import word_wrap
from lib.text_utils import title_case


def caption(text: str, width: int) -> str:
    """Title-case ``text`` then wrap to ``width`` characters per line.

    Raises:
        ValueError: If ``width`` is less than 1 (propagated from ``word_wrap``).
    """
    return word_wrap(title_case(text), width)
