import shutil
from pathlib import Path

import pytest
import yaml
from luna_tutor.curriculum.registry import (
    CurriculumRegistry,
    UnitSummary,
    UnknownUnitError,
)

ROOT = Path(__file__).resolve().parents[4]
CURRICULUM_ROOT = ROOT / "curriculum"


def test_registry_lists_units_in_numeric_order():
    registry = CurriculumRegistry(CURRICULUM_ROOT, ("grade05.unit01",))

    assert registry.list_units() == (
        UnitSummary(id="grade05.unit01", grade=5, unit=1, title="All about me!"),
    )


def test_registry_never_falls_back_for_unknown_unit():
    registry = CurriculumRegistry(CURRICULUM_ROOT, ("grade05.unit01",))

    with pytest.raises(UnknownUnitError, match="grade05.unit99"):
        registry.get("grade05.unit99")


def test_registry_rejects_manifest_id_mismatch(tmp_path):
    unit_root = tmp_path / "grade-05" / "unit-01"
    shutil.copytree(CURRICULUM_ROOT / "grade-05" / "unit-01", unit_root)
    manifest_path = unit_root / "unit.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["id"] = "grade05.unit99"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="Curriculum ID mismatch for grade05.unit01"):
        CurriculumRegistry(tmp_path, ("grade05.unit01",))
