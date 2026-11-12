"""Contract tests for styles.playbook_loader — pin current behavior.

Locks color science helpers, schema validation, and catalog loading as they
behave today. Suspected source defects are pinned, not fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import ValidationError

from styles.playbook_loader import (
    STYLES_DIR,
    _composite_alpha,
    _hex_to_hsl,
    _hsl_to_hex,
    _hue_in_range,
    _relative_luminance,
    _rgb_to_hex,
    _srgb_linearize,
    list_playbooks,
    load_playbook,
    validate_contrast,
    validate_playbook,
)


# ---------------------------------------------------------------------------
# 1. validate_contrast
# ---------------------------------------------------------------------------


def test_validate_contrast_black_on_white_passes_with_ratio_21():
    result = validate_contrast("#000000", "#FFFFFF")
    assert result["foreground"] == "#000000"
    assert result["background"] == "#FFFFFF"
    assert result["ratio"] == 21.0
    assert result["normal_text"] == {"AA": True, "AAA": True}
    assert result["large_text"] == {"AA": True, "AAA": True}


def test_validate_contrast_low_contrast_pair_fails_all_levels():
    result = validate_contrast("#777777", "#888888")
    assert result["ratio"] == 1.26
    assert result["normal_text"] == {"AA": False, "AAA": False}
    assert result["large_text"] == {"AA": False, "AAA": False}


def test_validate_contrast_eight_char_hex_strips_alpha_before_luminance():
    """Current behavior: alpha is ignored; #00000080 is treated as opaque black."""
    result = validate_contrast("#00000080", "#FFFFFF")
    assert result["foreground"] == "#00000080"
    assert result["background"] == "#FFFFFF"
    assert result["ratio"] == 21.0
    assert result["normal_text"]["AA"] is True

    both_alpha = validate_contrast("#FF000080", "#00FF0080")
    assert both_alpha["ratio"] == 2.91
    assert both_alpha["normal_text"]["AA"] is False


# ---------------------------------------------------------------------------
# 2. luminance / sRGB linearize
# ---------------------------------------------------------------------------


def test_relative_luminance_dark_less_than_light():
    assert _relative_luminance("#000000") == 0.0
    assert _relative_luminance("#FFFFFF") == 1.0
    assert _relative_luminance("#111111") < _relative_luminance("#EEEEEE")
    assert _relative_luminance("#111111") == pytest.approx(0.005605391624202723)
    assert _relative_luminance("#EEEEEE") == pytest.approx(0.8549926081242338)


def test_srgb_linearize_boundaries_zero_and_one():
    assert _srgb_linearize(0.0) == 0.0
    assert _srgb_linearize(1.0) == 1.0
    assert _srgb_linearize(0.04045) == pytest.approx(0.04045 / 12.92)
    assert _srgb_linearize(0.04046) == pytest.approx(
        ((0.04046 + 0.055) / 1.055) ** 2.4
    )


# ---------------------------------------------------------------------------
# 3. hex ↔ HSL roundtrip / rgb clamp
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hex_color",
    [
        "#FF0000",
        "#00FF00",
        "#0000FF",
        "#808080",
        "#FFFFFF",
        "#000000",
        "#1A2B3C",
    ],
)
def test_hex_hsl_roundtrip_representative_colors(hex_color: str):
    h, s, l = _hex_to_hsl(hex_color)
    assert _hsl_to_hex(h, s, l) == hex_color


def test_rgb_to_hex_clamps_out_of_range_channels():
    assert _rgb_to_hex(-10, 300, 128.4) == "#00FF80"
    assert _rgb_to_hex(0, 0, 0) == "#000000"
    assert _rgb_to_hex(255, 255, 255) == "#FFFFFF"
    assert _rgb_to_hex(1.4, 1.6, 254.5) == "#0102FE"


# ---------------------------------------------------------------------------
# 4. _composite_alpha
# ---------------------------------------------------------------------------


def test_composite_alpha_transparent_opaque_and_half():
    # Fully transparent red on blue → blue unchanged
    assert _composite_alpha("#FF000000", "#0000FF") == "#0000FF"
    # Fully opaque red on blue → red
    assert _composite_alpha("#FF0000FF", "#0000FF") == "#FF0000"
    # Half-alpha red on blue (current rounding)
    assert _composite_alpha("#FF000080", "#0000FF") == "#80007F"
    # Half-alpha black on white
    assert _composite_alpha("#00000080", "#FFFFFF") == "#7F7F7F"


# ---------------------------------------------------------------------------
# 5. _hue_in_range
# ---------------------------------------------------------------------------


def test_hue_in_range_inside_outside_and_wraparound():
    assert _hue_in_range(15, (0, 30)) is True
    assert _hue_in_range(45, (0, 30)) is False
    # Wrap-around range 330–30
    assert _hue_in_range(350, (330, 30)) is True
    assert _hue_in_range(10, (330, 30)) is True
    assert _hue_in_range(180, (330, 30)) is False
    assert _hue_in_range(330, (330, 30)) is True
    assert _hue_in_range(30, (330, 30)) is True


# ---------------------------------------------------------------------------
# 6. load_playbook — all built-in playbooks
# ---------------------------------------------------------------------------


def test_load_playbook_all_builtin_pass_validate_playbook():
    names = list_playbooks()
    assert names, "expected at least one playbook in styles/"
    for name in names:
        playbook = load_playbook(name)
        validate_playbook(playbook)
        assert playbook["identity"]["name"]


# ---------------------------------------------------------------------------
# 7. schema rejection
# ---------------------------------------------------------------------------


def test_validate_playbook_rejects_missing_required_top_level():
    with pytest.raises(ValidationError, match="'identity' is a required property"):
        validate_playbook({})


def test_validate_playbook_rejects_missing_nested_required_field():
    playbook = load_playbook("clean-professional")
    del playbook["identity"]["name"]
    with pytest.raises(ValidationError, match="'name' is a required property"):
        validate_playbook(playbook)


def test_validate_playbook_rejects_wrong_types():
    playbook = load_playbook("clean-professional")
    playbook["identity"]["name"] = 123
    with pytest.raises(ValidationError, match="123 is not of type 'string'"):
        validate_playbook(playbook)

    playbook = load_playbook("clean-professional")
    playbook["identity"] = "not-an-object"
    with pytest.raises(ValidationError, match="'not-an-object' is not of type 'object'"):
        validate_playbook(playbook)


# ---------------------------------------------------------------------------
# 8. list_playbooks
# ---------------------------------------------------------------------------


def test_list_playbooks_matches_styles_directory_files():
    expected = sorted(
        {
            *(p.stem for p in STYLES_DIR.glob("*.yaml")),
            *(p.stem for p in (STYLES_DIR / "custom").glob("*.yaml")),
        }
    )
    assert list_playbooks() == expected
    assert list_playbooks() == [
        "anime-ghibli",
        "clean-professional",
        "flat-motion-graphics",
        "minimalist-diagram",
        "premium-minimalist",
        "sky-spectrum",
    ]


def test_list_playbooks_nonexistent_directory_returns_empty():
    missing = Path("/tmp/no_such_playbooks_dir_openmontage_contract_xyz")
    assert not missing.exists()
    assert list_playbooks(missing) == []


def test_load_playbook_missing_name_raises_file_not_found():
    with pytest.raises(FileNotFoundError, match="Playbook not found: 'no-such-playbook-zzz'"):
        load_playbook("no-such-playbook-zzz")
