from pathlib import Path

from fastapi.testclient import TestClient
from luna_tutor.api.app import create_app
from luna_tutor.curriculum.registry import CurriculumRegistry
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.session_repository import SessionRepository


class UnusedTurnService:
    async def process(self, *_):
        raise AssertionError("turn service should not be called")


def test_lists_enabled_units_and_creates_selected_unit(tmp_path):
    root = Path(__file__).resolve().parents[4]
    registry = CurriculumRegistry(
        root / "curriculum", ("grade05.unit01", "grade05.unit02")
    )
    api = TestClient(
        create_app(
            repository=SessionRepository(tmp_path / "units.sqlite3"),
            turn_service=UnusedTurnService(),
            curriculum_registry=registry,
        )
    )

    response = api.get("/api/units")
    assert response.status_code == 200
    assert [
        (item["id"], item["title"]) for item in response.json()
    ] == [
        ("grade05.unit01", "All about me!"),
        ("grade05.unit02", "Our homes"),
    ]

    created = api.post(
        "/api/sessions", json={"unit_id": "grade05.unit02"}
    )
    assert created.status_code == 200
    body = created.json()
    assert body["unit_id"] == "grade05.unit02"
    assert body["unit"] == {
        "id": "grade05.unit02",
        "grade": 5,
        "unit": 2,
        "title": "Our homes",
    }
    assert body["stage_id"] == "warm-up"
    assert body["activity_id"] == "warm-up.feelings"


def test_create_requires_known_unit(tmp_path):
    root = Path(__file__).resolve().parents[4]
    registry = CurriculumRegistry(
        root / "curriculum", ("grade05.unit01", "grade05.unit02")
    )
    api = TestClient(
        create_app(
            repository=SessionRepository(tmp_path / "units.sqlite3"),
            turn_service=UnusedTurnService(),
            curriculum_registry=registry,
        )
    )

    assert api.post("/api/sessions").status_code == 422
    unknown = api.post(
        "/api/sessions", json={"unit_id": "grade05.unit99"}
    )
    assert unknown.status_code == 400
    assert unknown.json()["detail"]["code"] == "UNKNOWN_UNIT"


def test_stored_unknown_unit_returns_stable_configuration_error(tmp_path):
    root = Path(__file__).resolve().parents[4]
    registry = CurriculumRegistry(
        root / "curriculum", ("grade05.unit01", "grade05.unit02")
    )
    repository = SessionRepository(tmp_path / "unknown.sqlite3")
    repository.create_session(
        LessonState(
            session_id="unknown-unit",
            unit_id="grade05.unit99",
            stage_id="warm-up",
            activity_id="warm-up.feelings",
        )
    )
    api = TestClient(
        create_app(
            repository=repository,
            turn_service=UnusedTurnService(),
            curriculum_registry=registry,
        )
    )

    response = api.get("/api/sessions/unknown-unit")

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "UNKNOWN_STORED_UNIT"
