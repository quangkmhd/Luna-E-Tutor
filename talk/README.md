# Talk — Free Talk room

Pipecat WebRTC bot cho trang `/talk`: hội thoại tự do theo chủ đề, không có
station, mastery, lesson summary hoặc lesson session. Đây là service riêng với
Voice lớp học theo Unit.

Pipeline: Soniox STT → OpenRouter LLM → Soniox TTS. Xem [README root](../README.md)
để biết cách bốn service phối hợp.

## Môi trường riêng

Python project nằm trong `server/`; service chạy bằng `talk/server/.venv`, độc
lập với `backend/.venv` và `voice/server/.venv`.

Tất cả credentials được nạp rõ ràng từ `.env` ở repository root. Không tạo
`talk/server/.env`.

```bash
cd server
uv sync
uv run --env-file ../../.env bot.py -t webrtc \
  --host 127.0.0.1 --port 7863 \
  --allowed-origins http://localhost:3000
```

Browser client local: http://127.0.0.1:7863/client/.

## Cấu hình cần thiết

Các biến trong `.env` root:

```text
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-3.5-flash-lite
SONIOX_API_KEY=
SONIOX_VOICE_ID=Grace
```

Không dùng `GEMINI_API_KEY`: LLM hiện chạy qua OpenRouter. Xem
[`.env.example`](../.env.example) cho CORS và ICE/STUN.

## Evals và test

Chạy từ `talk/server`:

```bash
# Eval WebSocket server
uv run bot.py -t eval --runner-body evals/runner-body.yaml --port 7864

# Terminal khác
uv run pipecat eval run evals/starter_text.yaml --bot-url ws://localhost:7864 -v
uv run pipecat eval run evals/starter_audio.yaml --bot-url ws://localhost:7864 -v
PYTHONPATH=. uv run --env-file ../../.env pipecat eval run \
  evals/simple_language_text.yaml --bot-url ws://localhost:7864 -v

# Focused tests từ repository root
uv run --project talk/server pytest -q talk/server/tests
```

Text mode kiểm tra logic hội thoại nhanh. Audio mode thêm STT/VAD/TTS và có thể
tải Kokoro/Moonshine assets ở lần đầu chạy.

## Cấu trúc

```text
talk/
├── server/
│   ├── bot.py       # Pipecat bot entry point
│   ├── evals/       # headless behavioral scenarios
│   ├── tests/
│   ├── pyproject.toml
│   └── .venv/       # service-specific Python environment
└── README.md
```
