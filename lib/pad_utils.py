"""Pure padding helpers."""

from __future__ import annotations


def pad_left(text: str, width: int, fill: str = " ") -> str:
    """Left-pad ``text`` with ``fill`` so the result has length ``width``.

    If ``len(text)`` is already greater than or equal to ``width``, return
    ``text`` unchanged.

    Raises:
        ValueError: If ``width`` is negative, or ``fill`` is empty or longer
            than one character.
    """
    if width < 0:
        raise ValueError(f"width ({width}) must be >= 0")
    if len(fill) != 1:
        raise ValueError(f"fill must be a single character, got {fill!r}")
    if len(text) >= width:
        return text
    return fill * (width - len(text)) + text
