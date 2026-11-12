"""Tests for lib.pad_utils.pad_left."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.pad_utils import pad_left  # noqa: E402


def test_text_longer_than_width_returned_unchanged():
    assert pad_left("hello", 3) == "hello"


def test_text_equal_to_width_returned_unchanged():
    assert pad_left("hello", 5) == "hello"


def test_pads_left_with_default_space():
    assert pad_left("hi", 5) == "   hi"


def test_pads_left_with_custom_fill():
    assert pad_left("7", 4, fill="0") == "0007"


def test_negative_width_raises():
    with pytest.raises(ValueError):
        pad_left("hi", -1)


def test_empty_fill_raises():
    with pytest.raises(ValueError):
        pad_left("hi", 4, fill="")


def test_multi_char_fill_raises():
    with pytest.raises(ValueError):
        pad_left("hi", 4, fill="ab")
