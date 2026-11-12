"""Tests for lib.string_utils.truncate."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.string_utils import truncate, word_wrap  # noqa: E402


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


def test_word_wrap_empty_string():
    assert word_wrap("", 5) == ""


def test_word_wrap_width_less_than_one_raises():
    with pytest.raises(ValueError):
        word_wrap("hello", 0)


def test_word_wrap_breaks_on_spaces():
    assert word_wrap("hello world", 5) == "hello\nworld"


def test_word_wrap_fits_on_one_line():
    assert word_wrap("hello world", 11) == "hello world"


def test_word_wrap_hard_cuts_long_word():
    assert word_wrap("abcdefghij", 3) == "abc\ndef\nghi\nj"


def test_word_wrap_packs_multiple_short_words():
    assert word_wrap("a b c d", 3) == "a b\nc d"
