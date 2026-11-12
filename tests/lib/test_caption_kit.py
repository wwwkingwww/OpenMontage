"""Tests for lib.caption_kit.caption."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.caption_kit import caption  # noqa: E402


def test_caption_title_case_then_wrap_width_11():
    result = caption("hello openmontage world", 11)
    lines = result.split("\n")
    assert len(lines) >= 2
    assert all(len(line) <= 11 for line in lines)
    assert result == "Hello\nOpenmontage\nWorld"


def test_caption_empty_string_returns_empty():
    assert caption("", 10) == ""


def test_caption_whitespace_only_returns_empty():
    assert caption("   \t  ", 10) == ""


def test_caption_width_less_than_one_raises():
    with pytest.raises(ValueError):
        caption("hello", 0)


def test_caption_negative_width_raises():
    with pytest.raises(ValueError):
        caption("hello", -1)


def test_caption_fits_on_single_line():
    assert caption("hello world", 20) == "Hello World"


def test_caption_upper_input_normalized_then_wrapped():
    result = caption("HELLO OPENMONTAGE WORLD", 11)
    assert result == "Hello\nOpenmontage\nWorld"
    assert all(len(line) <= 11 for line in result.split("\n"))
