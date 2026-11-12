"""Contract tests for lib.config_model — pin current config defaults/behavior.

Locks OpenMontageConfig.load defaults, explicit YAML passthrough, resolve_path,
and Budget/Checkpoint enum members as they behave today.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from lib.config_model import (
    BudgetConfig,
    BudgetMode,
    CheckpointConfig,
    CheckpointPolicy,
    LLMConfig,
    OpenMontageConfig,
    OutputConfig,
    PathsConfig,
)


# ---------------------------------------------------------------------------
# 7. OpenMontageConfig.load() defaults when file missing
# ---------------------------------------------------------------------------


def test_load_missing_config_file_returns_field_defaults(tmp_path):
    missing = tmp_path / "no-such-config.yaml"
    assert not missing.exists()

    cfg = OpenMontageConfig.load(missing)

    assert cfg.llm == LLMConfig()
    assert cfg.llm.provider == "anthropic"
    assert cfg.llm.model is None
    assert cfg.llm.temperature == 0.7
    assert cfg.llm.max_tokens == 4096

    assert cfg.budget.mode == BudgetMode.WARN
    assert cfg.budget.total_usd == 10.0
    assert cfg.budget.reserve_pct == 0.10
    assert cfg.budget.single_action_approval_usd == 0.50
    assert cfg.budget.require_approval_for_new_paid_tool is True

    assert cfg.checkpoint.policy == CheckpointPolicy.GUIDED
    assert cfg.checkpoint.storage_dir == "pipeline"

    assert cfg.output.default_format == "mp4"
    assert cfg.output.default_codec == "libx264"
    assert cfg.output.default_audio_codec == "aac"
    assert cfg.output.default_resolution == "1920x1080"
    assert cfg.output.default_fps == 30
    assert cfg.output.default_crf == 23

    assert cfg.paths.pipeline_dir == "pipeline"
    assert cfg.paths.library_dir == "library"
    assert cfg.paths.styles_dir == "styles"
    assert cfg.paths.skills_dir == "skills"
    assert cfg.paths.output_dir == "output"


# ---------------------------------------------------------------------------
# 8. explicit config path field passthrough
# ---------------------------------------------------------------------------


def test_load_explicit_config_path_passthrough(tmp_path):
    payload = {
        "llm": {
            "provider": "openai",
            "model": "gpt-test",
            "temperature": 0.2,
            "max_tokens": 1024,
        },
        "budget": {
            "mode": "cap",
            "total_usd": 3.5,
            "reserve_pct": 0.2,
            "single_action_approval_usd": 1.25,
            "require_approval_for_new_paid_tool": False,
        },
        "checkpoint": {
            "policy": "manual_all",
            "storage_dir": "runs",
        },
        "output": {
            "default_format": "webm",
            "default_codec": "libvpx",
            "default_audio_codec": "libopus",
            "default_resolution": "1280x720",
            "default_fps": 24,
            "default_crf": 28,
        },
        "paths": {
            "pipeline_dir": "p",
            "library_dir": "l",
            "styles_dir": "s",
            "skills_dir": "k",
            "output_dir": "o",
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    cfg = OpenMontageConfig.load(path)

    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-test"
    assert cfg.llm.temperature == 0.2
    assert cfg.llm.max_tokens == 1024

    assert cfg.budget.mode == BudgetMode.CAP
    assert cfg.budget.total_usd == 3.5
    assert cfg.budget.reserve_pct == 0.2
    assert cfg.budget.single_action_approval_usd == 1.25
    assert cfg.budget.require_approval_for_new_paid_tool is False

    assert cfg.checkpoint.policy == CheckpointPolicy.MANUAL_ALL
    assert cfg.checkpoint.storage_dir == "runs"

    assert cfg.output.default_format == "webm"
    assert cfg.output.default_codec == "libvpx"
    assert cfg.output.default_audio_codec == "libopus"
    assert cfg.output.default_resolution == "1280x720"
    assert cfg.output.default_fps == 24
    assert cfg.output.default_crf == 28

    assert cfg.paths.pipeline_dir == "p"
    assert cfg.paths.library_dir == "l"
    assert cfg.paths.styles_dir == "s"
    assert cfg.paths.skills_dir == "k"
    assert cfg.paths.output_dir == "o"


# ---------------------------------------------------------------------------
# 9. resolve_path relative / absolute
# ---------------------------------------------------------------------------


def test_resolve_path_relative_joins_project_root(tmp_path):
    import lib.config_model as cm

    cfg = OpenMontageConfig()
    project_root = tmp_path / "proj"
    project_root.mkdir()

    relative = cfg.resolve_path("output_dir", project_root)
    assert relative == (project_root / "output").resolve()
    assert relative.is_absolute()

    expected_root = Path(cm.__file__).resolve().parent.parent
    assert cfg.resolve_path("pipeline_dir") == (expected_root / "pipeline").resolve()


def test_resolve_path_absolute_value_keeps_absolute_operand(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    abs_out = (tmp_path / "abs_media_out").resolve()
    abs_cfg = OpenMontageConfig.model_validate(
        {"paths": {"output_dir": str(abs_out)}}
    )
    resolved_abs = abs_cfg.resolve_path("output_dir", project_root)
    assert resolved_abs == abs_out
    assert resolved_abs.is_absolute()


# ---------------------------------------------------------------------------
# 10. BudgetMode / CheckpointPolicy members and section defaults
# ---------------------------------------------------------------------------


def test_budget_mode_enum_members_and_section_defaults():
    assert list(BudgetMode) == [
        BudgetMode.OBSERVE,
        BudgetMode.WARN,
        BudgetMode.CAP,
    ]
    assert [m.value for m in BudgetMode] == ["observe", "warn", "cap"]

    budget = BudgetConfig()
    assert budget.mode is BudgetMode.WARN
    assert budget.total_usd == 10.0
    assert OutputConfig().default_fps == 30


def test_checkpoint_policy_enum_members_and_section_defaults():
    assert list(CheckpointPolicy) == [
        CheckpointPolicy.GUIDED,
        CheckpointPolicy.MANUAL_ALL,
        CheckpointPolicy.AUTO_NONCREATIVE,
    ]
    assert [p.value for p in CheckpointPolicy] == [
        "guided",
        "manual_all",
        "auto_noncreative",
    ]

    checkpoint = CheckpointConfig()
    assert checkpoint.policy is CheckpointPolicy.GUIDED
    assert checkpoint.storage_dir == "pipeline"
    assert PathsConfig().output_dir == "output"
