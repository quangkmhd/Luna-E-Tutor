from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from luna_tutor.api.routes import build_router


def create_app(*, repository, turn_service) -> FastAPI:
    app = FastAPI(title='Luna Unit 1 Tutor', version='0.1.0')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000'],
        allow_credentials=False,
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type'],
    )
    app.include_router(build_router(repository, turn_service))
    return app
