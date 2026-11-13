"""Unit tests for lib.path_guard (PYTHONPATH demotion + safe_join).

PYTHONPATH scenarios use monkeypatch; none depend on the host layout.
safe_join contracts cover confined relative joins and rejection of
absolute / drive / UNC / ``..`` parts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.path_guard import demote_pythonpath_shadows, safe_join  # noqa: E402


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


# ---------------------------------------------------------------------------
# safe_join contracts
# ---------------------------------------------------------------------------


def test_safe_join_legitimate_relative_unchanged(tmp_path):
    base = tmp_path / "root"
    base.mkdir()
    expected = str((base / "a" / "b.txt").resolve())
    assert safe_join(base, "a", "b.txt") == expected
    assert safe_join(str(base), "subdir", "file.json") == str(
        (base / "subdir" / "file.json").resolve()
    )


def test_safe_join_result_stays_inside_base(tmp_path):
    base = tmp_path / "confine"
    base.mkdir()
    result = Path(safe_join(base, "nested", "out.bin"))
    assert result.resolve().is_relative_to(base.resolve())


@pytest.mark.parametrize(
    "part",
    [
        "../x",
        "foo/../bar",
        r"foo\..\bar",
        "C:\\abs",
        "C:/abs",
        "\\\\server\\share",
        "//server/share",
        "/etc/passwd",
    ],
)
def test_safe_join_rejects_unsafe_parts(tmp_path, part):
    base = tmp_path / "root"
    base.mkdir()
    with pytest.raises(ValueError, match="safe_join rejected|escapes base"):
        safe_join(base, part)


def test_safe_join_absolute_base_allowed_for_user_output_sites(tmp_path):
    """Absolute bases remain valid when the user supplies an output directory.

    Call sites that intentionally accept absolute paths as the confinement
    root (not as join parts):

    - tools/analysis/azure_stt.py (_transcribe output_dir)
    - tools/analysis/video_analyzer.py (_save_brief output_dir)
    - tools/cost_tracker.py (_save cost_log_path parent)
    - tools/video/video_compose.py (output_path.parent for props/concat)
    - tools/video/video_stitch.py / video_trimmer.py / silence_cutter.py
      (temp_dir under output_path.parent)
    - lib/corpus.py (user-provided corpus_dir)
    - tools/video/stock_sources/* (download out_path.parent; caller absolute OK)
    """
    abs_base = (tmp_path / "user_out").resolve()
    abs_base.mkdir()
    result = Path(safe_join(abs_base, "artifact.json"))
    assert result.is_absolute()
    assert result.parent == abs_base
    assert result.name == "artifact.json"


# ---------------------------------------------------------------------------
# stock_sources download confinement (T-0403)
# ---------------------------------------------------------------------------


def test_stock_source_download_allows_caller_absolute_out_path(tmp_path, monkeypatch):
    """Pexels download keeps caller absolute out_path; mocks network I/O.

    corpus_builder / direct_clip_search pass an absolute path under the
    corpus (or clips) directory. That absolute parent is the legal
    confinement root — behaviour is preserved when the filename is safe.
    """
    from tools.video.stock_sources.base import Candidate
    from tools.video.stock_sources.pexels import PexelsSource

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"stock-bytes"

    def fake_get(*args, **kwargs):
        return _Resp()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)

    candidate = Candidate(
        source="pexels",
        source_id="1",
        source_url="https://www.pexels.com/video/1",
        download_url="https://videos.pexels.com/video-files/1.mp4",
        kind="video",
    )
    output = (tmp_path / "clips" / "pexels_1.mp4").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    result = PexelsSource().download(candidate, output)
    assert result == output
    assert result.resolve().is_relative_to(tmp_path.resolve())
    assert output.read_bytes() == b"stock-bytes"


def test_stock_source_download_rejects_traversal_out_name(tmp_path):
    """Stock download rejects out_path whose final name is a ``..`` component."""
    from tools.video.stock_sources.base import confine_download_out_path

    unsafe = tmp_path / ".."
    with pytest.raises(ValueError, match="safe_join rejected|escapes base"):
        confine_download_out_path(unsafe)
