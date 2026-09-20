from pathlib import Path

from luna_tutor.curriculum.loader import load_unit

ROOT = Path(__file__).resolve().parents[4]


def test_unit05_feedback_praises_the_idea_before_pronunciation_support():
    unit = load_unit(ROOT / "curriculum/grade-05/unit-05")
    activity = next(
        item for item in unit.activities if item.id == "level-03.creativity"
    )
    instruction = activity.instruction.lower()
    assert instruction.index("praise") < instruction.index("pronunciation")
    assert "good answer" not in instruction


def test_unit05_family_job_context_is_fictional():
    unit = load_unit(ROOT / "curriculum/grade-05/unit-05")
    activity = next(
        item for item in unit.activities if item.id == "level-02.family-job"
    )
    instruction = activity.instruction.lower()
    assert "fictional" in instruction
    assert "do not invent" in instruction
