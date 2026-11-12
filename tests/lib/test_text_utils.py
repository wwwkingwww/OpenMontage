"""Tests for lib.text_utils.slugify."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.text_utils import slugify  # noqa: E402


def test_lowercase_and_whitespace_collapsed():
    assert slugify("Hello   World") == "hello-world"


def test_punctuation_stripped_and_separators_merged():
    assert slugify("Hello, World!!! Foo") == "hello-world-foo"


def test_non_ascii_stripped_char_by_char():
    assert slugify("Hello 你好 World") == "hello-world"


def test_empty_string_returns_empty():
    assert slugify("") == ""


def test_all_punctuation_returns_empty():
    assert slugify("!!!@@@###") == ""


def test_custom_separator():
    assert slugify("Hello World", separator="_") == "hello_world"


def test_leading_trailing_separators_removed():
    assert slugify("  --Hello--  ") == "hello"


def test_mixed_boundary_numbers_and_hyphens():
    assert slugify("API v2 — Release Notes") == "api-v2-release-notes"
