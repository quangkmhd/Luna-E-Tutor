from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from luna_tutor.api.routes import build_router
from luna_tutor.curriculum.registry import CurriculumRegistry


def create_app(*, repository, turn_service, curriculum_registry=None,
               comparison_service=None, lifespan=None,
               allowed_origins: list[str] | None = None) -> FastAPI:
    if curriculum_registry is None:
        root = Path(__file__).resolve().parents[4]
        curriculum_registry = CurriculumRegistry(
            root / 'curriculum', (
                'grade05.unit01', 'grade05.unit02', 'grade05.unit03',
                'grade05.unit04'))
    app = FastAPI(title='Luna Grade 5 Tutor', version='0.1.0', lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ['http://localhost:3000'],
        allow_credentials=False,
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type'],
    )
    app.include_router(build_router(
        repository, turn_service, curriculum_registry, comparison_service))
    return app
