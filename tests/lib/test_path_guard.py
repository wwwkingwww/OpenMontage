"""Unit tests for lib.path_guard.demote_pythonpath_shadows.

All scenarios use monkeypatch; none depend on the host PYTHONPATH layout.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.path_guard import demote_pythonpath_shadows  # noqa: E402


def test_pythonpath_entries_moved_to_tail(monkeypatch):
    shadow = os.path.abspath(os.path.join("shadow_pkg_a"))
    other = os.path.abspath(os.path.join("other_pkg"))
    site = os.path.abspath(os.path.join("site_packages"))

    monkeypatch.setenv("PYTHONPATH", shadow)
    monkeypatch.setattr(
        sys,
        "path",
        ["", shadow, other, site],
        raising=False,
    )

    demote_pythonpath_shadows()

    assert sys.path[0] == ""
    assert shadow not in sys.path[:-1]
    assert sys.path[-1] == shadow
    assert other in sys.path
    assert site in sys.path
    assert sys.path.index(other) < sys.path.index(shadow)
    assert sys.path.index(site) < sys.path.index(shadow)


def test_unset_or_empty_pythonpath_leaves_sys_path(monkeypatch):
    original = ["", "/keep/a", "/keep/b"]
    monkeypatch.setattr(sys, "path", list(original), raising=False)

    monkeypatch.delenv("PYTHONPATH", raising=False)
    demote_pythonpath_shadows()
    assert sys.path == original

    monkeypatch.setenv("PYTHONPATH", "")
    demote_pythonpath_shadows()
    assert sys.path == original


def test_idempotent_double_call(monkeypatch):
    shadow = os.path.abspath(os.path.join("idem_shadow"))
    site = os.path.abspath(os.path.join("idem_site"))

    monkeypatch.setenv("PYTHONPATH", shadow)
    monkeypatch.setattr(
        sys,
        "path",
        ["", shadow, site],
        raising=False,
    )

    demote_pythonpath_shadows()
    once = list(sys.path)
    demote_pythonpath_shadows()
    twice = list(sys.path)

    assert once == twice
    assert once[-1] == shadow
    assert once[0] == ""


def test_relative_pythonpath_matched_via_abspath(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    rel = "rel_shadow"
    abs_shadow = os.path.abspath(rel)
    site = os.path.abspath("rel_site")

    monkeypatch.setenv("PYTHONPATH", rel)
    # sys.path often holds the absolute form while PYTHONPATH is relative
    monkeypatch.setattr(
        sys,
        "path",
        ["", abs_shadow, site],
        raising=False,
    )

    demote_pythonpath_shadows()

    assert sys.path[0] == ""
    assert all(os.path.abspath(e) != abs_shadow for e in sys.path[:-1])
    assert os.path.abspath(sys.path[-1]) == abs_shadow
    assert site in sys.path
    assert sys.path.index(site) < len(sys.path) - 1
