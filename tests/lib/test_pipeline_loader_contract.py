"""Contract tests for lib.pipeline_loader — pin current assembly behavior.

Locks stage order, tool/skill lookups, cache semantics, catalog listing, and
conditional sub-stage gates as they behave today. Suspected source defects are
pinned, not fixed.
"""

from __future__ import annotations

import pytest
import yaml

from lib.pipeline_loader import (
    PIPELINE_DEFS_DIR,
    get_required_tools,
    get_stage_human_approval_default,
    get_stage_order,
    get_stage_skill,
    get_stage_sub_stages,
    get_stage_tools,
    list_pipelines,
    load_pipeline,
    load_pipeline_readonly,
)

PIPELINE_NAME = "animated-explainer"


def _raw_manifest(name: str = PIPELINE_NAME) -> dict:
    path = PIPELINE_DEFS_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 1. load_pipeline + get_stage_order
# ---------------------------------------------------------------------------


def test_load_pipeline_stage_order_matches_builtin_yaml():
    manifest = load_pipeline(PIPELINE_NAME)
    raw = _raw_manifest()
    expected = [stage["name"] for stage in raw["stages"]]
    assert get_stage_order(manifest) == expected
    assert expected == [
        "research",
        "proposal",
        "script",
        "scene_plan",
        "assets",
        "edit",
        "compose",
        "publish",
    ]


# ---------------------------------------------------------------------------
# 2. get_required_tools / get_stage_tools
# ---------------------------------------------------------------------------


def test_get_required_tools_aggregates_known_stage_and_reference_tools():
    manifest = load_pipeline(PIPELINE_NAME)
    required = get_required_tools(manifest)
    # Aggregates preferred/fallback/tools_available (+ reference analysis_tools),
    # but does NOT include required_tools / optional_tools fields.
    assert required == {
        "audio_mixer",
        "code_snippet",
        "diagram_gen",
        "export_bundle",
        "frame_sampler",
        "hyperframes_compose",
        "image_selector",
        "math_animate",
        "music_gen",
        "scene_detect",
        "transcript_fetcher",
        "tts_selector",
        "video_analyzer",
        "video_compose",
        "video_downloader",
        "video_selector",
        "video_stitch",
    }


def test_get_stage_tools_returns_expected_sets_for_known_stages():
    manifest = load_pipeline(PIPELINE_NAME)
    assert get_stage_tools(manifest, "proposal") == {
        "tts_selector",
        "image_selector",
        "video_selector",
        "video_compose",
        "audio_mixer",
    }
    assert get_stage_tools(manifest, "research") == set()
    assert get_stage_tools(manifest, "not_a_stage") == set()


# ---------------------------------------------------------------------------
# 3. get_stage_skill / get_stage_human_approval_default
# ---------------------------------------------------------------------------


def test_get_stage_skill_returns_skill_name_or_none():
    manifest = load_pipeline(PIPELINE_NAME)
    assert get_stage_skill(manifest, "research") == (
        "pipelines/explainer/research-director"
    )
    assert get_stage_skill(manifest, "proposal") == (
        "pipelines/explainer/proposal-director"
    )
    assert get_stage_skill(manifest, "not_a_stage") is None

    smoke = load_pipeline("framework-smoke")
    assert get_stage_skill(smoke, "research") is None


def test_get_stage_human_approval_default_bool_or_none():
    manifest = load_pipeline(PIPELINE_NAME)
    # Declared true/false are returned as bool; missing stage -> None;
    # missing field defaults to False via bool(...).
    assert get_stage_human_approval_default(manifest, "proposal") is True
    assert get_stage_human_approval_default(manifest, "research") is False
    assert get_stage_human_approval_default(manifest, "not_a_stage") is None

    smoke = load_pipeline("framework-smoke")
    assert get_stage_human_approval_default(smoke, "research") is True


# ---------------------------------------------------------------------------
# 4. load_pipeline vs load_pipeline_readonly cache semantics
# ---------------------------------------------------------------------------


def test_load_pipeline_vs_readonly_cache_object_identity():
    a = load_pipeline(PIPELINE_NAME)
    b = load_pipeline(PIPELINE_NAME)
    # Uncached path: equal content, distinct objects each call.
    assert a == b
    assert a is not b

    c = load_pipeline_readonly(PIPELINE_NAME)
    d = load_pipeline_readonly(PIPELINE_NAME)
    # Cached path: same object returned on repeat.
    assert c is d
    assert c == a
    assert c is not a


# ---------------------------------------------------------------------------
# 5. list_pipelines + missing name error
# ---------------------------------------------------------------------------


def test_list_pipelines_matches_pipeline_defs_dir():
    listed = sorted(list_pipelines())
    on_disk = sorted(p.stem for p in PIPELINE_DEFS_DIR.glob("*.yaml"))
    assert listed == on_disk
    assert "animated-explainer" in listed
    assert "framework-smoke" in listed


def test_load_pipeline_missing_name_raises_file_not_found():
    missing = "definitely-not-a-pipeline-xyz"
    with pytest.raises(FileNotFoundError, match="Pipeline manifest not found"):
        load_pipeline(missing)
    with pytest.raises(FileNotFoundError, match="Pipeline manifest not found"):
        load_pipeline_readonly(missing)


# ---------------------------------------------------------------------------
# 6. conditional gate via get_stage_sub_stages
# ---------------------------------------------------------------------------


def test_get_stage_sub_stages_filters_inactive_conditions():
    manifest = load_pipeline(PIPELINE_NAME)
    condition = "video_analysis_brief_exists"

    all_subs = get_stage_sub_stages(manifest, "proposal")
    assert [s["name"] for s in all_subs] == ["sample"]
    assert all_subs[0]["condition"] == condition

    # include_inactive=False with no/empty/false context: condition inactive
    # (_condition_is_active returns False when context is falsy or key falsy).
    assert (
        get_stage_sub_stages(
            manifest, "proposal", context=None, include_inactive=False
        )
        == []
    )
    assert (
        get_stage_sub_stages(
            manifest, "proposal", context={}, include_inactive=False
        )
        == []
    )
    assert (
        get_stage_sub_stages(
            manifest,
            "proposal",
            context={condition: False},
            include_inactive=False,
        )
        == []
    )

    active = get_stage_sub_stages(
        manifest,
        "proposal",
        context={condition: True},
        include_inactive=False,
    )
    assert [s["name"] for s in active] == ["sample"]


def test_get_stage_order_include_sub_stages_respects_condition_context():
    manifest = load_pipeline(PIPELINE_NAME)
    condition = "video_analysis_brief_exists"

    # context=None -> include_inactive=True, so conditioned sub-stages appear.
    assert "proposal.sample" in get_stage_order(
        manifest, include_sub_stages=True
    )
    assert "proposal.sample" not in get_stage_order(
        manifest, include_sub_stages=True, context={}
    )
    assert "proposal.sample" in get_stage_order(
        manifest,
        include_sub_stages=True,
        context={condition: True},
    )
