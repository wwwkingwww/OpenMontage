"""Path safety helpers for import shadow demotion and confined joins.

``demote_pythonpath_shadows`` moves machine-level PYTHONPATH entries to the
end of ``sys.path`` so venv packages resolve first.

``safe_join`` joins relative parts under a base directory and refuses any
result that would resolve outside that base (path traversal hardening).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePath, PureWindowsPath


def safe_join(base: str | os.PathLike[str], *parts: str | os.PathLike[str]) -> str:
    """Join ``parts`` under ``base`` and require the result stays inside ``base``.

    Each part must be a relative path segment (or relative multi-segment
    path without ``..``). Absolute paths, drive-letter paths, UNC paths,
    and any part containing a ``..`` component are rejected with
    ``ValueError`` and a diagnostic message.

    ``base`` itself may be absolute — callers that take a user-supplied
    output directory use that absolute directory as the confinement root
    and only pass relative child names as ``parts``.

    Returns the resolved path as a string.
    """
    if not parts:
        raise ValueError("safe_join requires at least one path part")

    checked: list[str] = []
    for index, part in enumerate(parts):
        raw = os.fspath(part)
        _reject_unsafe_part(raw, index)
        checked.append(raw)

    base_path = Path(base)
    candidate = base_path.joinpath(*checked)
    try:
        base_resolved = base_path.resolve()
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            f"safe_join failed to resolve base={os.fspath(base)!r} "
            f"parts={checked!r}: {exc}"
        ) from exc

    try:
        resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(
            f"safe_join result escapes base: resolved={str(resolved)!r} "
            f"base={str(base_resolved)!r} parts={checked!r}"
        ) from exc

    return str(resolved)


def _reject_unsafe_part(raw: str, index: int) -> None:
    """Raise ValueError if ``raw`` is absolute, drive/UNC, or contains ``..``."""
    if raw == "":
        raise ValueError(f"safe_join rejected empty part at index {index}")

    # UNC (\\server\share or //server/share) — check before Path normalisation.
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise ValueError(
            f"safe_join rejected UNC path {raw!r} at index {index}"
        )

    # Drive-letter paths (C:\abs, C:/abs, c:foo) including relative-to-drive.
    if len(raw) >= 2 and raw[1] == ":":
        raise ValueError(
            f"safe_join rejected drive-letter path {raw!r} at index {index}"
        )

    # Rooted absolute forms (/abs, \abs) — pathlib on Windows may not
    # treat a leading slash as absolute without a drive letter.
    if raw.startswith(("/", "\\")):
        raise ValueError(
            f"safe_join rejected absolute path {raw!r} at index {index}"
        )

    pure = PurePath(raw)
    if pure.is_absolute():
        raise ValueError(
            f"safe_join rejected absolute path {raw!r} at index {index}"
        )

    # Also catch Windows-style absolute forms when running on POSIX.
    win = PureWindowsPath(raw)
    if win.is_absolute() or win.drive:
        raise ValueError(
            f"safe_join rejected Windows absolute/drive path {raw!r} "
            f"at index {index}"
        )

    # Reject ``..`` as any path component (slash or backslash separated).
    components = PurePath(raw.replace("\\", "/")).parts
    if ".." in components:
        raise ValueError(
            f"safe_join rejected path traversal component in {raw!r} "
            f"at index {index}"
        )


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
