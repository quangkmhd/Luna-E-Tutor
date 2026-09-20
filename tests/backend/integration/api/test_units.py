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
        root / "curriculum",
        ("grade05.unit01", "grade05.unit02", "grade05.unit03", "grade05.unit04", "grade05.unit05"),
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
        ("grade05.unit03", "My foreign friends"),
        ("grade05.unit04", "Our free-time activities"),
        ("grade05.unit05", "My future job"),
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
    assert [item["stage_id"] for item in body["learning_focus"]] == [
        "lesson-01", "lesson-02", "lesson-03", "level-02", "level-03",
    ]
    assert body["learning_focus"][0] == {
        "stage_id": "lesson-01",
        "stage_title": "Lesson 01",
        "target_words": ["building", "flat", "house", "tower"],
        "target_patterns": [
            "Do you live in this/that ___? – Yes, I do./No, I don't."
        ],
        "highlighted": True,
    }


def test_session_exposes_only_the_current_units_stage_targets(tmp_path):
    root = Path(__file__).resolve().parents[4]
    registry = CurriculumRegistry(
        root / "curriculum",
        ("grade05.unit01", "grade05.unit02"),
    )
    repository = SessionRepository(tmp_path / "focus.sqlite3")
    repository.create_session(LessonState(
        session_id="unit-2-lesson-1",
        unit_id="grade05.unit02",
        stage_id="lesson-01",
        activity_id="lesson-01.introduce-house",
    ))
    api = TestClient(create_app(
        repository=repository,
        turn_service=UnusedTurnService(),
        curriculum_registry=registry,
    ))

    body = api.get("/api/sessions/unit-2-lesson-1").json()

    assert body["learning_focus"][0] == {
        "stage_id": "lesson-01",
        "stage_title": "Lesson 01",
        "target_words": ["building", "flat", "house", "tower"],
        "target_patterns": [
            "Do you live in this/that ___? – Yes, I do./No, I don't."
        ],
        "highlighted": True,
    }
    assert sum(item["highlighted"] for item in body["learning_focus"]) == 1


def test_create_requires_known_unit(tmp_path):
    root = Path(__file__).resolve().parents[4]
    registry = CurriculumRegistry(
        root / "curriculum",
        ("grade05.unit01", "grade05.unit02", "grade05.unit03", "grade05.unit04", "grade05.unit05"),
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
        root / "curriculum",
        ("grade05.unit01", "grade05.unit02", "grade05.unit03", "grade05.unit04", "grade05.unit05"),
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
