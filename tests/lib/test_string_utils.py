"""Tests for lib.string_utils.truncate."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.string_utils import truncate  # noqa: E402


def test_short_text_returned_unchanged():
    assert truncate("hello", 10) == "hello"


def test_exact_max_len_returned_unchanged():
    assert truncate("hello", 5) == "hello"


def test_truncate_with_default_ellipsis():
    result = truncate("abcdefghij", 8)
    assert result == "abcde..."
    assert len(result) == 8


def test_truncate_with_custom_ellipsis():
    result = truncate("abcdefghij", 7, ellipsis="…")
    assert result == "abcdef…"
    assert len(result) == 7


def test_max_len_equal_to_ellipsis_returns_ellipsis():
    assert truncate("abcdefghij", 3, ellipsis="...") == "..."


def test_max_len_less_than_ellipsis_raises():
    with pytest.raises(ValueError):
        truncate("abcdefghij", 2, ellipsis="...")
