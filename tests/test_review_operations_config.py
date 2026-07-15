import json
from pathlib import Path

import pytest

from src.review_operations_config import ReviewOperationsConfig, load_review_operations_config
from tests.builders import build_event
from tests.history_helpers import finalizer_paths, write_json
from tools.finalize_weekly_run import finalize_weekly_run


def test_default_config_matches_operational_defaults() -> None:
    config = ReviewOperationsConfig()
    assert config.to_dict() == {
        "stale_after_appearances": 3,
        "sla_due_after_days": 7,
        "sla_overdue_after_days": 14,
        "sla_overdue_after_appearances": 4,
        "capacity_lookback_runs": 4,
    }


def test_config_rejects_invalid_threshold_relationship() -> None:
    with pytest.raises(ValueError, match="must exceed"):
        ReviewOperationsConfig(sla_due_after_days=14, sla_overdue_after_days=14)


def test_config_rejects_unknown_keys() -> None:
    with pytest.raises(ValueError, match="Unknown review configuration keys"):
        ReviewOperationsConfig.from_mapping({"mystery_threshold": 9})


def test_load_config_and_explicit_override_precedence(tmp_path: Path) -> None:
    path = write_json(
        tmp_path / "review_config.json",
        {
            "stale_after_appearances": 5,
            "sla_due_after_days": 10,
            "sla_overdue_after_days": 20,
            "sla_overdue_after_appearances": 6,
            "capacity_lookback_runs": 8,
        },
    )
    config = load_review_operations_config(path).with_overrides(
        stale_after=7, capacity_lookback=3
    )
    assert config.stale_after_appearances == 7
    assert config.sla_due_after_days == 10
    assert config.capacity_lookback_runs == 3


def test_finalizer_persists_effective_configuration(tmp_path: Path) -> None:
    input_path = write_json(tmp_path / "events.json", [build_event()])
    config = ReviewOperationsConfig(
        stale_after_appearances=5,
        sla_due_after_days=10,
        sla_overdue_after_days=20,
        sla_overdue_after_appearances=6,
        capacity_lookback_runs=8,
    )
    result = finalize_weekly_run(
        input_path,
        **finalizer_paths(tmp_path),
        review_config=config,
        stale_after=4,
        run_reports=False,
    )
    assert result["review_config"]["stale_after_appearances"] == 4
    assert result["review_config"]["sla_due_after_days"] == 10
    persisted = json.loads(
        Path(result["review_operations_config"]).read_text(encoding="utf-8")
    )
    assert persisted == result["review_config"]


def test_config_requires_integer_values() -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        ReviewOperationsConfig.from_mapping({"capacity_lookback_runs": "4"})
