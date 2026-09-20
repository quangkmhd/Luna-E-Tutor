FROM python:3.12-slim

# Install uv from official Docker Hub image
COPY --from=astral/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=0 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy backend (dependency of voice), curriculum, and voice
COPY backend /app/backend
COPY curriculum /app/curriculum
COPY voice /app/voice

WORKDIR /app/voice/server

# Install dependencies with uv
RUN uv sync --frozen --no-dev

EXPOSE 7860

CMD ["uv", "run", "bot.py", "-t", "webrtc", "--host", "0.0.0.0", "--port", "7860"]
