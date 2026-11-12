"""Cross-platform font file resolution for ffmpeg drawtext/subtitles.

FFmpeg builds that enable fontconfig (e.g. gyan.dev Windows full builds) crash
or error when drawtext/subtitles rely on the default font and no fonts.conf /
FONTCONFIG_* is present. Callers must pass an absolute ``fontfile`` (drawtext)
or ``fontsdir`` (subtitles) resolved by this module.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePath
from typing import Iterable, Sequence

# Env override — absolute path to a .ttf/.otf/.ttc file.
FONTFILE_ENV_VAR = "OPENMONTAGE_FONTFILE"

# Common bundled / system face filenames, tried in order when no preferred name.
_COMMON_FONT_NAMES: tuple[str, ...] = (
    "segoeui.ttf",
    "segoeuib.ttf",
    "arial.ttf",
    "Arial.ttf",
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "FreeSans.ttf",
    "NotoSans-Regular.ttf",
    "Helvetica.ttc",
    "Helvetica.ttf",
)


class FontResolutionError(Exception):
    """Raised when no usable font file can be resolved for ffmpeg."""

    def __init__(
        self,
        message: str,
        *,
        platform: str,
        attempted: Sequence[str],
        remediations: Sequence[str],
        preferred: str | None = None,
    ) -> None:
        self.platform = platform
        self.attempted = list(attempted)
        self.remediations = list(remediations)
        self.preferred = preferred
        super().__init__(message)

    def __str__(self) -> str:
        lines = [
            super().__str__(),
            f"  platform: {self.platform}",
        ]
        if self.preferred is not None:
            lines.append(f"  preferred: {self.preferred}")
        lines.append("  attempted:")
        if self.attempted:
            for item in self.attempted:
                lines.append(f"    - {item}")
        else:
            lines.append("    - (none)")
        lines.append("  remediations:")
        for item in self.remediations:
            lines.append(f"    - {item}")
        return "\n".join(lines)


def escape_filter_path(path: str | PurePath) -> str:
    """Encode a filesystem path for a single-quoted ffmpeg filter option value.

    Escapes option-level backslashes, colons and quotes, then preserves quotes
    through the graph parser by closing/reopening the caller's single-quoted
    section. Windows drive letters become ``C\\:/...``.
    """
    if isinstance(path, PurePath):
        encoded = path.as_posix()
    else:
        encoded = PurePath(str(path)).as_posix()

    if "\x00" in encoded:
        raise ValueError("filter paths cannot contain NUL bytes")
    encoded = encoded.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return encoded.replace("'", "'\\''")


def platform_font_dirs() -> list[Path]:
    """Return candidate system font directories for the current platform."""
    dirs: list[Path] = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"
        dirs.append(Path(windir) / "Fonts")
    elif sys.platform == "darwin":
        dirs.extend(
            [
                Path("/System/Library/Fonts"),
                Path("/Library/Fonts"),
                Path.home() / "Library" / "Fonts",
            ]
        )
    else:
        dirs.extend(
            [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".fonts",
                Path.home() / ".local" / "share" / "fonts",
            ]
        )
    return dirs


def _looks_like_font_file(path: Path) -> bool:
    return path.suffix.lower() in {".ttf", ".otf", ".ttc"} and path.is_file()


def _candidate_names(preferred: str | None) -> list[str]:
    names: list[str] = []
    if preferred:
        names.append(preferred)
        # If preferred is a bare stem without extension, try common suffixes.
        p = Path(preferred)
        if not p.suffix:
            names.extend([f"{preferred}.ttf", f"{preferred}.otf", f"{preferred}.ttc"])
    for name in _COMMON_FONT_NAMES:
        if name not in names:
            names.append(name)
    return names


def _search_dirs_for_names(
    dirs: Iterable[Path], names: Sequence[str], attempted: list[str]
) -> str | None:
    for directory in dirs:
        for name in names:
            # Bare filename only inside font dirs (no path traversal).
            base = Path(name).name
            candidate = directory / base
            attempted.append(str(candidate))
            if _looks_like_font_file(candidate):
                return str(candidate.resolve())
        # Recursive walk for Linux multi-level font trees (DejaVu under truetype/).
        if directory.is_dir():
            for name in names:
                base = Path(name).name
                try:
                    matches = directory.rglob(base)
                except OSError:
                    continue
                for match in matches:
                    # Skip the flat path we already recorded.
                    if match == directory / base:
                        continue
                    attempted.append(str(match))
                    if _looks_like_font_file(match):
                        return str(match.resolve())
    return None


def _fontconfig_match(preferred: str | None, attempted: list[str]) -> str | None:
    """Ask fontconfig (fc-match) for a file path when the binary is available."""
    fc_match = shutil.which("fc-match")
    if not fc_match:
        attempted.append("fc-match (not found on PATH)")
        return None
    query = preferred or "sans-serif"
    cmd = [fc_match, "-f", "%{file}\n", query]
    attempted.append("fc-match " + " ".join(cmd[1:]))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        attempted.append(f"fc-match failed: {exc}")
        return None
    path_str = (result.stdout or "").strip().splitlines()
    if not path_str:
        attempted.append("fc-match returned empty path")
        return None
    path = Path(path_str[0].strip())
    attempted.append(str(path))
    if _looks_like_font_file(path):
        return str(path.resolve())
    return None


def resolve_fontfile(preferred: str | Path | None = None) -> str:
    """Resolve an absolute font file path for ffmpeg.

    Resolution order:
      1. Explicit ``preferred`` argument (existing file path, or bare filename
         looked up under platform font directories)
      2. ``OPENMONTAGE_FONTFILE`` environment variable
      3. Platform font directory probe for common faces; fontconfig ``fc-match``
         when available
      4. Raise :class:`FontResolutionError` with structured diagnostics
    """
    attempted: list[str] = []
    platform = f"{sys.platform}"
    preferred_str = str(preferred).strip() if preferred is not None else None
    if preferred_str == "":
        preferred_str = None

    # 1. Explicit preferred
    if preferred_str is not None:
        pref_path = Path(preferred_str)
        if pref_path.is_file() and _looks_like_font_file(pref_path):
            return str(pref_path.resolve())
        attempted.append(f"explicit:{preferred_str}")
        # Bare filename / relative: search platform dirs for that name only
        # (do not silently substitute a different common face here).
        preferred_names = [preferred_str]
        if not Path(preferred_str).suffix:
            preferred_names.extend(
                [f"{preferred_str}.ttf", f"{preferred_str}.otf", f"{preferred_str}.ttc"]
            )
        found = _search_dirs_for_names(
            platform_font_dirs(), preferred_names, attempted
        )
        if found:
            return found

    # 2. Environment variable
    env_val = os.environ.get(FONTFILE_ENV_VAR, "").strip()
    if env_val:
        env_path = Path(env_val)
        attempted.append(f"${FONTFILE_ENV_VAR}={env_val}")
        if env_path.is_file() and _looks_like_font_file(env_path):
            return str(env_path.resolve())
        attempted.append(f"${FONTFILE_ENV_VAR} not a usable font file")

    # 3. Platform dirs + fontconfig
    found = _search_dirs_for_names(
        platform_font_dirs(), _candidate_names(None), attempted
    )
    if found:
        return found

    fc = _fontconfig_match(preferred_str, attempted)
    if fc:
        return fc

    remediations = [
        f"Set {FONTFILE_ENV_VAR} to an absolute path of a .ttf/.otf/.ttc file",
        "Pass an absolute font path as the preferred argument to resolve_fontfile()",
        "Install a common TTF font (Arial, Segoe UI, DejaVu Sans) into the system fonts directory",
    ]
    if sys.platform == "win32":
        remediations.append(r"Confirm fonts exist under C:\Windows\Fonts")
    else:
        remediations.append("Install fonts-dejavu-core / fonts-liberation (Linux) or use fc-cache")

    raise FontResolutionError(
        "Could not resolve a font file for ffmpeg text rendering "
        "(drawtext/subtitles). Refusing to rely on broken/missing fontconfig.",
        platform=platform,
        attempted=attempted,
        remediations=remediations,
        preferred=preferred_str,
    )
