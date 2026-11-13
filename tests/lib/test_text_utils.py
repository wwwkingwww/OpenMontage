"""Tests for lib.text_utils.slugify and title_case."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.text_utils import slugify, title_case  # noqa: E402


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


def test_title_case_basic_words():
    assert title_case("hello world") == "Hello World"


def test_title_case_upper_input_normalized():
    assert title_case("HELLO WORLD") == "Hello World"


def test_title_case_empty_string():
    assert title_case("") == ""


def test_title_case_whitespace_collapsed_and_trimmed():
    assert title_case("  hello   world  ") == "Hello World"


def test_title_case_non_letter_prefix_stays_lower():
    assert title_case("123abc !bang") == "123abc !bang"


def test_title_case_mixed_case_and_single_letter():
    assert title_case("a bB Cc") == "A Bb Cc"


def test_slugify_empty_separator_deletes_runs():
    assert slugify("Hello World", separator="") == "helloworld"


def test_slugify_multi_char_separator_inserted_literally():
    assert slugify("Hello World", separator="__") == "hello__world"


def test_slugify_non_ascii_run_with_custom_separator():
    assert slugify("你好 World", separator="_") == "world"


def test_slugify_upper_input_with_custom_separator():
    assert slugify("HELLO_WORLD", separator="-") == "hello-world"


def test_title_case_tab_and_newline_as_whitespace():
    assert title_case("hello\tworld\n") == "Hello World"


def test_slugify_leading_trailing_strip_with_custom_separator():
    assert slugify("  --Hello--  ", separator="_") == "hello"
