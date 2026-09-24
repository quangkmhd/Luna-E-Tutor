# Voice — bài học theo kịch bản lớp 3

Pipecat WebRTC bot cho bài học lớp 3. Soniox STT gửi transcript đã chốt
sang backend để Jev đánh giá và Teacher xử lý ngoại lệ; Soniox TTS phát lời
Teacher hoặc lời `say` nguyên văn. Học sinh ấn mic để nói rồi ấn Gửi để yêu
cầu chốt lượt. `talk` là phòng trò chuyện riêng.

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
```

Xem [`.env.example`](../.env.example) cho CORS và ICE/STUN khi chạy qua mạng.

## Test

Chạy từ repository root:

```bash
uv run --project voice/server pytest -q tests/voice
```

Các scenario eval cũ dùng lượt nói tự chốt và barge-in, không còn áp dụng cho
cơ chế nút Gửi. Test hiện tại dùng frame giả; cần kiểm tra thêm một phiên mic,
Soniox và TTS thật trước khi xác nhận Voice hoạt động trọn vẹn.

## Cấu trúc

```text
voice/
├── server/
│   ├── bot.py       # Pipecat bot entry point
│   ├── lesson_voice_bridge.py  # chốt transcript và giao lời phát
│   ├── pyproject.toml
│   └── .venv/       # service-specific Python environment
└── README.md
```
