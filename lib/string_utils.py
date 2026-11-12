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
