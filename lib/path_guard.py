"""Demote PYTHONPATH entries so later site-packages win on import.

Machine-level PYTHONPATH can inject directories ahead of a venv's
site-packages (sys.path order). ``demote_pythonpath_shadows`` moves those
entries to the end of ``sys.path`` so venv packages resolve first, while
keeping the paths available as a non-shadowing fallback.
"""

from __future__ import annotations

import os
import sys


def demote_pythonpath_shadows() -> None:
    """Move PYTHONPATH entries from early ``sys.path`` slots to the end.

    - Reads ``PYTHONPATH``; no-op when unset or empty.
    - Matches entries by ``os.path.abspath`` (no hardcoded paths).
    - Removes matching entries wherever they sit, then appends the original
      PYTHONPATH parts at the tail (skipping duplicates already kept).
    - Preserves a non-PYTHONPATH ``sys.path[0]`` such as ``''`` for ``-c``.
    - Idempotent: a second call leaves ``sys.path`` unchanged.
    """
    raw = os.environ.get("PYTHONPATH")
    if not raw:
        return

    parts = [p for p in raw.split(os.pathsep) if p]
    if not parts:
        return

    shadow = {os.path.abspath(p) for p in parts}

    kept: list[str] = []
    for entry in sys.path:
        try:
            if os.path.abspath(entry) in shadow:
                continue
        except (OSError, TypeError, ValueError):
            pass
        kept.append(entry)

    kept_abs = {os.path.abspath(e) for e in kept if e}
    for p in parts:
        ap = os.path.abspath(p)
        if ap not in kept_abs:
            kept.append(p)
            kept_abs.add(ap)

    sys.path[:] = kept
