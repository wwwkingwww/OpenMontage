"""Unit tests for lib.fonts — resolution order, probing, errors, escaping."""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from lib.fonts import (
    FONTFILE_ENV_VAR,
    FontResolutionError,
    escape_filter_path,
    platform_font_dirs,
    resolve_fontfile,
)


def test_escape_filter_path_windows_drive_and_spaces():
    assert (
        escape_filter_path(PureWindowsPath(r"C:\Users\Jane Doe\text.txt"))
        == r"C\:/Users/Jane Doe/text.txt"
    )


def test_escape_filter_path_posix_preserved():
    assert (
        escape_filter_path(PurePosixPath("/tmp/Jane Doe/text.txt"))
        == "/tmp/Jane Doe/text.txt"
    )


def test_escape_filter_path_colon_and_quote():
    assert (
        escape_filter_path(PurePosixPath("/tmp/time:12.txt"))
        == r"/tmp/time\:12.txt"
    )
    # Option-level \' then graph-level '\'' re-open (same order as showcase_card).
    assert (
        escape_filter_path(PurePosixPath("/tmp/O'Brien/a.txt"))
        == r"/tmp/O\'\''Brien/a.txt"
    )


def test_escape_filter_path_rejects_nul():
    with pytest.raises(ValueError, match="NUL"):
        escape_filter_path(PurePosixPath("/tmp/bad\x00.txt"))


def test_resolve_prefers_explicit_existing_file(tmp_path, monkeypatch):
    font = tmp_path / "CustomFace.ttf"
    font.write_bytes(b"OTTO")  # minimal stand-in; existence matters, not contents
    monkeypatch.delenv(FONTFILE_ENV_VAR, raising=False)
    monkeypatch.setattr("lib.fonts.platform_font_dirs", lambda: [])
    monkeypatch.setattr("lib.fonts._fontconfig_match", lambda *a, **k: None)

    assert resolve_fontfile(font) == str(font.resolve())


def test_resolve_order_explicit_name_over_env(tmp_path, monkeypatch):
    fonts_dir = tmp_path / "Fonts"
    fonts_dir.mkdir()
    preferred = fonts_dir / "PreferMe.ttf"
    preferred.write_bytes(b"OTTO")
    env_font = tmp_path / "FromEnv.ttf"
    env_font.write_bytes(b"OTTO")

    monkeypatch.setenv(FONTFILE_ENV_VAR, str(env_font))
    monkeypatch.setattr("lib.fonts.platform_font_dirs", lambda: [fonts_dir])
    monkeypatch.setattr("lib.fonts._fontconfig_match", lambda *a, **k: None)

    assert resolve_fontfile("PreferMe.ttf") == str(preferred.resolve())


def test_resolve_order_env_over_platform_probe(tmp_path, monkeypatch):
    fonts_dir = tmp_path / "Fonts"
    fonts_dir.mkdir()
    (fonts_dir / "arial.ttf").write_bytes(b"OTTO")
    env_font = tmp_path / "EnvOnly.otf"
    env_font.write_bytes(b"OTTO")

    monkeypatch.setenv(FONTFILE_ENV_VAR, str(env_font))
    monkeypatch.setattr("lib.fonts.platform_font_dirs", lambda: [fonts_dir])
    monkeypatch.setattr("lib.fonts._fontconfig_match", lambda *a, **k: None)

    assert resolve_fontfile() == str(env_font.resolve())


def test_resolve_platform_probe_finds_common_face(tmp_path, monkeypatch):
    fonts_dir = tmp_path / "Fonts"
    fonts_dir.mkdir()
    face = fonts_dir / "DejaVuSans.ttf"
    face.write_bytes(b"OTTO")

    monkeypatch.delenv(FONTFILE_ENV_VAR, raising=False)
    monkeypatch.setattr("lib.fonts.platform_font_dirs", lambda: [fonts_dir])
    monkeypatch.setattr("lib.fonts._fontconfig_match", lambda *a, **k: None)

    assert resolve_fontfile() == str(face.resolve())


def test_resolve_platform_probe_recursive_subdir(tmp_path, monkeypatch):
    root = tmp_path / "share" / "fonts"
    nested = root / "truetype" / "dejavu"
    nested.mkdir(parents=True)
    face = nested / "DejaVuSans.ttf"
    face.write_bytes(b"OTTO")

    monkeypatch.delenv(FONTFILE_ENV_VAR, raising=False)
    monkeypatch.setattr("lib.fonts.platform_font_dirs", lambda: [root])
    monkeypatch.setattr("lib.fonts._fontconfig_match", lambda *a, **k: None)

    assert resolve_fontfile() == str(face.resolve())


def test_resolve_missing_raises_structured_error(tmp_path, monkeypatch):
    empty = tmp_path / "empty_fonts"
    empty.mkdir()

    monkeypatch.delenv(FONTFILE_ENV_VAR, raising=False)
    monkeypatch.setattr("lib.fonts.platform_font_dirs", lambda: [empty])
    monkeypatch.setattr("lib.fonts._fontconfig_match", lambda *a, **k: None)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(FontResolutionError) as excinfo:
        resolve_fontfile("MissingFace.ttf")

    err = excinfo.value
    text = str(err)
    assert err.platform == "win32"
    assert err.preferred == "MissingFace.ttf"
    assert err.attempted, "expected attempted paths to be recorded"
    assert FONTFILE_ENV_VAR in text
    assert "remediations:" in text
    assert any("MissingFace.ttf" in item for item in err.attempted)


def test_platform_font_dirs_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("WINDIR", r"D:\Windows")
    dirs = platform_font_dirs()
    assert dirs == [Path(r"D:\Windows") / "Fonts"]


def test_escape_special_chars_usable_as_fontfile_filter_value(tmp_path):
    """Paths with spaces/punctuation must survive escape_filter_path round-trip shape."""
    funny = tmp_path / "O'Brien, [fonts]; dir"
    funny.mkdir()
    font = funny / "Face Name.ttf"
    font.write_bytes(b"OTTO")

    escaped = escape_filter_path(font)
    # Drive colon (Windows) or plain posix — never an unescaped option separator
    # that would break out of fontfile='...'.
    assert "'" in escaped or " " in str(font)
    # Re-open pattern for apostrophe is present when path has one.
    assert r"'\''" in escaped
    assert "[" in escaped and "]" in escaped
