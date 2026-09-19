"""HTTP text entry point sharing the website's session API and SQLite history.

uv run uvicorn text_runtime:build_app --factory --port 8001 --env-file PATH
"""

from luna_tutor.api.runtime import build_runtime_app

from text_pipeline import PipecatTurnService


def build_app():
    return build_runtime_app(turn_service_adapter=PipecatTurnService)
