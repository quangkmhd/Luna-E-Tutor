from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from luna_tutor.api.routes import build_router


def create_app(*, repository, turn_service, speaking_service=None, speaking_repository=None, lifespan=None,
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
    if speaking_service is not None:
        from luna_tutor.speaking.routes import build_speaking_router
        app.include_router(build_speaking_router(speaking_service, speaking_repository))
    return app
