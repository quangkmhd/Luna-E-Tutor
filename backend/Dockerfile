FROM python:3.12-slim

# Install uv from official Docker Hub image
COPY --from=astral/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=0 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy curriculum data and backend code
COPY curriculum /app/curriculum
COPY backend /app/backend

WORKDIR /app/backend

# Install dependencies with uv
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "luna_tutor.api.lesson_runtime:build_lesson_runtime_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
