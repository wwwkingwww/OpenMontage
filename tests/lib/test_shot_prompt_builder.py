"""Tests for lib.shot_prompt_builder.build_shot_prompt and build_batch_prompts.

Contract tests: pin the CURRENT behavior of the 5-layer prompt assembly
(camera -> movement -> subject -> lighting -> style). Every case must stay
green against the existing implementation; quirks found while writing these
tests are pinned as-is and reported, not "fixed".
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.shot_prompt_builder import build_batch_prompts, build_shot_prompt  # noqa: E402


# ---------------------------------------------------------------------------
# build_shot_prompt — layer order and joining
# ---------------------------------------------------------------------------


def test_full_scene_layer_order_camera_movement_subject_lighting():
    scene = {
        "description": "A lighthouse on a cliff",
        "texture_keywords": ["weathered stone", "salt spray"],
        "shot_language": {
            "lens_mm": 35,
            "depth_of_field": "shallow",
            "shot_size": "wide",
            "camera_movement": "dolly_in",
            "lighting_key": "golden_hour",
            "color_temperature": "warm",
        },
    }
    prompt = build_shot_prompt(scene)
    assert prompt == (
        "35mm lens, shallow depth of field with bokeh. "
        "wide shot capturing full scene, slow dolly in toward subject. "
        "A lighthouse on a cliff. weathered stone, salt spray. "
        "warm golden hour sunlight, warm amber-toned color palette"
    )


def test_layers_joined_by_period_space():
    scene = {
        "shot_language": {"lens_mm": 50, "camera_movement": "pan_left"},
        "description": "A harbor at dawn",
    }
    assert build_shot_prompt(scene) == (
        "50mm lens. smooth pan to the left. A harbor at dawn"
    )


def test_single_layer_prompt_has_no_separator():
    scene = {"description": "Only a subject line"}
    assert build_shot_prompt(scene) == "Only a subject line"


# ---------------------------------------------------------------------------
# Layer 1: camera (lens_mm + depth_of_field)
# ---------------------------------------------------------------------------


def test_lens_and_dof_combined_in_camera_layer():
    scene = {"shot_language": {"lens_mm": 35, "depth_of_field": "shallow"}}
    assert build_shot_prompt(scene) == "35mm lens, shallow depth of field with bokeh"


def test_dof_known_values_map_to_phrases():
    assert build_shot_prompt({"shot_language": {"depth_of_field": "medium"}}) == (
        "medium depth of field"
    )
    assert build_shot_prompt({"shot_language": {"depth_of_field": "deep"}}) == (
        "deep focus with everything sharp"
    )


def test_dof_unknown_value_is_dropped_not_passed_through():
    # Quirk pin: unlike shot_size/movement/lighting_key (raw fallback via
    # .get(k, k)), unknown depth_of_field maps to "" and is filtered out of
    # the camera layer.
    scene = {"shot_language": {"lens_mm": 50, "depth_of_field": "frozen"}}
    assert build_shot_prompt(scene) == "50mm lens"

    # Unknown DOF alone yields no camera layer at all.
    assert build_shot_prompt({"shot_language": {"depth_of_field": "frozen"}}) == ""


# ---------------------------------------------------------------------------
# Layer 2: movement (shot_size + camera_movement)
# ---------------------------------------------------------------------------


def test_shot_size_enum_maps_to_phrase():
    scene = {"shot_language": {"shot_size": "medium"}}
    assert build_shot_prompt(scene) == "medium shot from waist up"


def test_shot_size_unknown_value_falls_back_to_raw():
    scene = {"shot_language": {"shot_size": "aerial_drone"}}
    assert build_shot_prompt(scene) == "aerial_drone"


def test_camera_movement_enum_maps_to_phrase():
    scene = {"shot_language": {"camera_movement": "crane_up"}}
    assert build_shot_prompt(scene) == "crane shot rising upward"


def test_camera_movement_unknown_value_falls_back_to_raw():
    scene = {"shot_language": {"camera_movement": "spiral"}}
    assert build_shot_prompt(scene) == "spiral"


def test_static_movement_produces_no_phrase():
    scene = {"shot_language": {"camera_movement": "static"}}
    assert build_shot_prompt(scene) == ""


def test_static_movement_skipped_but_shot_size_kept():
    scene = {"shot_language": {"shot_size": "close_up", "camera_movement": "static"}}
    prompt = build_shot_prompt(scene)
    assert prompt == "close-up focusing on face or detail"
    assert "static" not in prompt
    assert "locked-off" not in prompt


# ---------------------------------------------------------------------------
# Layer 3: subject (description + texture_keywords)
# ---------------------------------------------------------------------------


def test_texture_keywords_appended_to_subject_layer():
    scene = {"description": "A red barn", "texture_keywords": ["old wood", "rust"]}
    assert build_shot_prompt(scene) == "A red barn. old wood, rust"


def test_texture_keywords_list_joined_with_comma():
    scene = {"description": "D", "texture_keywords": ["a", "b", "c"]}
    assert build_shot_prompt(scene) == "D. a, b, c"


def test_empty_texture_list_ignored():
    scene = {"description": "D", "texture_keywords": []}
    assert build_shot_prompt(scene) == "D"


def test_texture_without_description_still_forms_subject_layer():
    scene = {"texture_keywords": ["film grain", "dust motes"]}
    assert build_shot_prompt(scene) == "film grain, dust motes"


# ---------------------------------------------------------------------------
# Layer 4: lighting (lighting_key + color_temperature)
# ---------------------------------------------------------------------------


def test_lighting_key_enum_maps_to_phrase():
    scene = {"shot_language": {"lighting_key": "low_key"}}
    assert build_shot_prompt(scene) == "dramatic low-key lighting with deep shadows"


def test_lighting_key_unknown_value_falls_back_to_raw():
    scene = {"shot_language": {"lighting_key": "candlelight"}}
    assert build_shot_prompt(scene) == "candlelight"


def test_lighting_key_and_color_temperature_combined():
    scene = {"shot_language": {"lighting_key": "neon", "color_temperature": "cool"}}
    assert build_shot_prompt(scene) == (
        "neon-lit with vibrant color spill, cool blue-toned color palette"
    )


def test_color_temperature_unknown_falls_back_to_empty_and_keeps_lighting_layer():
    scene = {"shot_language": {"lighting_key": "neon", "color_temperature": "ultraviolet"}}
    assert build_shot_prompt(scene) == "neon-lit with vibrant color spill"


def test_color_temperature_unknown_alone_yields_no_lighting_layer():
    scene = {"shot_language": {"color_temperature": "ultraviolet"}}
    assert build_shot_prompt(scene) == ""


# ---------------------------------------------------------------------------
# Layer 5: style (playbook-derived, "Style: <hint>" prefix)
# ---------------------------------------------------------------------------


def test_style_layer_prefers_visual_language_aesthetic():
    style = {"visual_language": {"aesthetic": "film noir"}, "mood": "tense"}
    assert build_shot_prompt({"description": "D"}, style) == "D. Style: film noir"


def test_style_layer_falls_back_to_mood_when_aesthetic_empty():
    style = {"visual_language": {"aesthetic": ""}, "mood": "tense"}
    assert build_shot_prompt({"description": "D"}, style) == "D. Style: tense"


def test_style_layer_falls_back_to_mood_when_visual_language_missing():
    style = {"mood": "melancholic"}
    assert build_shot_prompt({"description": "D"}, style) == "D. Style: melancholic"


def test_no_style_layer_when_aesthetic_and_mood_both_empty():
    style = {"visual_language": {"aesthetic": ""}, "mood": ""}
    prompt = build_shot_prompt({"description": "D"}, style)
    assert prompt == "D"
    assert "Style:" not in prompt


def test_empty_style_context_dict_adds_no_style_layer():
    assert build_shot_prompt({"description": "D"}, {}) == "D"


# ---------------------------------------------------------------------------
# Empty scene
# ---------------------------------------------------------------------------


def test_empty_scene_returns_empty_string():
    assert build_shot_prompt({}) == ""


def test_scene_with_empty_shot_language_and_no_description_returns_empty():
    assert build_shot_prompt({"shot_language": {}}) == ""


# ---------------------------------------------------------------------------
# build_batch_prompts — batch expansion
# ---------------------------------------------------------------------------


def test_batch_skips_transition_scenes():
    scenes = [
        {"id": "a", "type": "transition", "description": "fade to black"},
        {"id": "b", "type": "visual", "description": "A harbor"},
        {"id": "c", "description": "No type key is kept"},
    ]
    results = build_batch_prompts(scenes)
    assert [r["scene_id"] for r in results] == ["b", "c"]


def test_batch_output_shape_and_defaults():
    scenes = [{"description": "A market at noon"}]
    results = build_batch_prompts(scenes)
    assert results == [
        {"scene_id": "unknown", "prompt": "A market at noon", "hero_moment": False}
    ]


def test_batch_preserves_input_order():
    scenes = [
        {"id": "s3", "description": "Third"},
        {"id": "s1", "description": "First"},
        {"id": "s2", "description": "Second"},
    ]
    results = build_batch_prompts(scenes)
    assert [r["scene_id"] for r in results] == ["s3", "s1", "s2"]


def test_batch_hero_moment_passthrough_true():
    scenes = [{"id": "h", "hero_moment": True, "description": "Climax shot"}]
    results = build_batch_prompts(scenes)
    assert results[0]["hero_moment"] is True


def test_batch_all_transitions_returns_empty_list():
    scenes = [{"id": "t", "type": "transition"}]
    assert build_batch_prompts(scenes) == []


def test_batch_empty_input_returns_empty_list():
    assert build_batch_prompts([]) == []


def test_batch_propagates_style_context_to_prompts():
    style = {"visual_language": {"aesthetic": "grainy 16mm"}}
    scenes = [
        {"id": "a", "description": "One"},
        {"id": "b", "description": "Two"},
    ]
    results = build_batch_prompts(scenes, style)
    assert len(results) == 2
    assert all(r["prompt"].endswith("Style: grainy 16mm") for r in results)
