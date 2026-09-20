import hashlib
import json
from pathlib import Path

import pytest
from luna_tutor.curriculum.registry import UnknownUnitError
from luna_tutor.evals.metrics import EvalRecord
from luna_tutor.evals.runner import EvalRunner

ROOT = Path(__file__).resolve().parents[3]


def _directory_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*.yaml")):
        digest.update(item.relative_to(item.parents[2]).as_posix().encode())
        digest.update(item.read_bytes())
    return digest.hexdigest()


def test_runner_selects_unit03_paths_objectives_and_report_name(tmp_path):
    runner = EvalRunner(ROOT, evaluator=None, unit_id="grade05.unit03")
    assert runner.curriculum.id == "grade05.unit03"
    assert any(item.id.startswith("unit03.") for item in runner.curriculum.objectives)
    assert runner.curriculum_dir == ROOT / "curriculum/grade-05/unit-03"
    assert runner.scenario_dir == ROOT / "evals/unit-03"

    record = EvalRecord(
        scenario_id="unit03-offline", turn_index=1, repetition=1,
        expected={"response_kind": "answer"},
        actual={"response_kind": "answer"}, schema_valid=True,
        provider_failure=False, latency_ms=1,
    )
    report = runner.write_report([record], tmp_path)
    assert report.json_path.name.startswith("unit-03-")
    assert report.curriculum_sha256 == _directory_hash(runner.curriculum_dir)
    assert json.loads(report.json_path.read_text())["unit_id"] == "grade05.unit03"
    assert "Unit 3 evaluation" in report.markdown_path.read_text()


def test_runner_rejects_unknown_unit():
    with pytest.raises(UnknownUnitError):
        EvalRunner(ROOT, evaluator=None, unit_id="grade05.unit99")
