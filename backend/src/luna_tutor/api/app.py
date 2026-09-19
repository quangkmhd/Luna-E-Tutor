from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from luna_tutor.api.routes import build_router


def create_app(*, repository, turn_service, lifespan=None,
               allowed_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title='Luna Unit 1 Tutor', version='0.1.0', lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ['http://localhost:3000'],
        allow_credentials=False,
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type'],
    )
    app.include_router(build_router(repository, turn_service))
    return app
