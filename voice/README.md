# Voice — lớp học theo Unit

Pipecat WebRTC bot cho luồng học có lộ trình. Bot dùng pipeline cascade:
Soniox STT → OpenRouter LLM → Soniox TTS, và dùng teaching core từ `backend`.
Nó khác với `talk`: Voice có lesson state, mục tiêu Unit và tiến trình học.

Xem [README root](../README.md) để biết bốn service cùng chạy như thế nào.

## Môi trường riêng

Python project nằm trong `server/`; venv của service là
`voice/server/.venv`. Nó độc lập với `backend/.venv` và `talk/server/.venv`.
`luna-tutor` từ `../../backend` được khai báo là editable dependency trong venv
này, không có nghĩa hai service dùng chung venv.

Tất cả credentials được nạp từ `.env` ở repository root. Không tạo
`voice/server/.env`.

```bash
cd server
uv sync
uv run --env-file ../../.env bot.py -t webrtc \
  --host 127.0.0.1 --port 7860 \
  --allowed-origins http://localhost:3000
```

Browser client local: http://127.0.0.1:7860/client/.

## Cấu hình cần thiết

Các biến chính trong `.env` root:

```text
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-3.5-flash-lite
SONIOX_API_KEY=
SONIOX_VOICE_ID=Grace
SONIOX_TTS_VOICE=Grace
```

Xem [`.env.example`](../.env.example) cho CORS và ICE/STUN khi chạy qua mạng.

## Evals và test

Chạy từ `voice/server`:

```bash
# Text-mode behavioral eval
uv run bot.py -t eval

# Terminal khác, khi bot eval đang chạy
uv run pipecat eval run evals/starter_text.yaml -v
uv run pipecat eval run evals/starter_audio.yaml -v

# Focused test suite từ repository root
uv run --project voice/server pytest -q tests/voice tests/scripts tests/ops
```

Text eval kiểm tra quyết định/hội thoại; audio eval mới kiểm tra đường STT, VAD
và TTS. Các scenario nằm ở `server/evals/`.

## Cấu trúc

```text
voice/
├── server/
│   ├── bot.py       # Pipecat bot entry point
│   ├── evals/       # headless behavioral scenarios
│   ├── pyproject.toml
│   └── .venv/       # service-specific Python environment
└── README.md
```
