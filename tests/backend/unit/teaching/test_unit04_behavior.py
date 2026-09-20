from pathlib import Path

from luna_tutor.curriculum.loader import load_unit

ROOT = Path(__file__).resolve().parents[4]


def test_unit04_internet_activity_never_requests_account_identity():
    unit = load_unit(ROOT / "curriculum/grade-05/unit-04")
    text = " ".join(activity.instruction for activity in unit.activities).lower()
    assert "never ask for an internet username" in text
    assert "account, handle, or platform identity" in text
