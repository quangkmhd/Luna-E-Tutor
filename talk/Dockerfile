FROM python:3.12-slim

# Install system dependencies for audio & WebRTC processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official Docker Hub image
COPY --from=astral/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=0 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy talk code
COPY talk /app/talk

WORKDIR /app/talk/server

# Install dependencies with uv
RUN uv sync --frozen --no-dev

EXPOSE 7863

CMD ["uv", "run", "bot.py", "-t", "webrtc", "--host", "0.0.0.0", "--port", "7863"]
