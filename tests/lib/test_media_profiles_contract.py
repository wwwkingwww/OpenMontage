"""Contract tests for lib.media_profiles — pin current profile helpers.

Locks get_profile, get_profiles_for_platform, and ffmpeg_output_args as they
behave today. Suspected source defects are pinned, not fixed.
"""

from __future__ import annotations

import pytest

from lib.media_profiles import (
    ALL_PROFILES,
    AspectRatio,
    MediaProfile,
    ffmpeg_output_args,
    get_profile,
    get_profiles_for_platform,
)


# ---------------------------------------------------------------------------
# 11. get_profile known / unknown
# ---------------------------------------------------------------------------


def test_get_profile_known_returns_complete_fields():
    profile = get_profile("youtube_landscape")
    assert isinstance(profile, MediaProfile)
    assert profile.name == "youtube_landscape"
    assert profile.width == 1920
    assert profile.height == 1080
    assert profile.aspect_ratio == AspectRatio.LANDSCAPE_16_9
    assert profile.fps == 30
    assert profile.codec == "libx264"
    assert profile.audio_codec == "aac"
    assert profile.crf == 18
    assert profile.pixel_format == "yuv420p"
    assert profile.max_file_size_mb is None
    assert profile.max_duration_seconds is None
    assert profile.caption_format == "srt"
    assert profile.notes == "YouTube standard HD upload"

    # Same registry object (frozen dataclass in ALL_PROFILES).
    assert profile is ALL_PROFILES["youtube_landscape"]


def test_get_profile_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown profile 'nope'"):
        get_profile("nope")


# ---------------------------------------------------------------------------
# 12. get_profiles_for_platform filtering
# ---------------------------------------------------------------------------


def test_get_profiles_for_platform_youtube_and_instagram():
    assert [p.name for p in get_profiles_for_platform("youtube")] == [
        "youtube_landscape",
        "youtube_4k",
        "youtube_shorts",
    ]
    assert [p.name for p in get_profiles_for_platform("instagram")] == [
        "instagram_reels",
        "instagram_feed",
    ]


def test_get_profiles_for_platform_exact_name_and_unknown():
    # Exact name also matches as a prefix of itself.
    assert [p.name for p in get_profiles_for_platform("tiktok")] == ["tiktok"]
    assert get_profiles_for_platform("does-not-exist") == []


# ---------------------------------------------------------------------------
# 13. ffmpeg_output_args key parameters
# ---------------------------------------------------------------------------


def test_ffmpeg_output_args_youtube_landscape_resolution_fps_codec():
    profile = get_profile("youtube_landscape")
    assert ffmpeg_output_args(profile) == [
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-vf",
        "scale=1920:1080",
    ]


def test_ffmpeg_output_args_cinematic_resolution_fps_codec():
    cinematic = get_profile("cinematic")
    cine_args = ffmpeg_output_args(cinematic)
    assert cine_args[cine_args.index("-c:v") + 1] == "libx264"
    assert cine_args[cine_args.index("-r") + 1] == "24"
    assert cine_args[cine_args.index("-vf") + 1] == "scale=2560:1080"
    assert cine_args[cine_args.index("-crf") + 1] == "16"
