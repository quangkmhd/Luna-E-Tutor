from pathlib import Path

from luna_tutor.curriculum.loader import load_unit

ROOT = Path(__file__).resolve().parents[4]


def test_unit03_free_talk_uses_fictional_friend_without_real_identity_request():
    unit = load_unit(ROOT / "curriculum/grade-05/unit-03")
    activity = next(
        item for item in unit.activities
        if item.id == "free-talk.conversation"
    )
    instruction = activity.instruction.lower()
    assert "fictional" in instruction
    assert "real child" in instruction
