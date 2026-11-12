"""Pure string helpers."""

from __future__ import annotations


def truncate(text: str, max_len: int, *, ellipsis: str = "...") -> str:
    """Return ``text`` unchanged if it fits, otherwise truncate with ``ellipsis``.

    The returned string always has length exactly ``max_len`` when truncated,
    with ``ellipsis`` counted toward that limit.

    Raises:
        ValueError: If ``max_len`` is less than ``len(ellipsis)``.
    """
    if max_len < len(ellipsis):
        raise ValueError(
            f"max_len ({max_len}) must be >= len(ellipsis) ({len(ellipsis)})"
        )
    if len(text) <= max_len:
        return text
    if max_len == len(ellipsis):
        return ellipsis
    return text[: max_len - len(ellipsis)] + ellipsis


def word_wrap(text: str, width: int) -> str:
    """Wrap ``text`` so each line is at most ``width`` characters.

    Breaks on spaces between words. Words longer than ``width`` are hard-cut.

    Raises:
        ValueError: If ``width`` is less than 1.
    """
    if width < 1:
        raise ValueError(f"width ({width}) must be >= 1")
    if not text:
        return ""

    words = text.split(" ")
    lines: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current:
            lines.append(current)
            current = ""

    def emit_hard(chunk: str) -> None:
        nonlocal current
        flush()
        for i in range(0, len(chunk), width):
            lines.append(chunk[i : i + width])

    for word in words:
        if not word:
            # Preserve consecutive spaces only as separators already consumed.
            continue
        if len(word) > width:
            flush()
            emit_hard(word)
            continue
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            flush()
            current = word
    flush()
    return "\n".join(lines)
