# Backend — Luna Tutor lớp 3

FastAPI service cho học liệu lớp 3, Jev, Teacher và phiên học trong bộ nhớ.
Đây là service riêng
chạy bằng `backend/.venv`; xem [README root](../README.md) để biết bốn service.

## Chạy local

```bash
uv sync
uv run --env-file ../.env uvicorn luna_tutor.api.lesson_runtime:build_lesson_runtime_app \
  --factory --host 127.0.0.1 --port 8000 --reload --reload-dir src
```

API docs: http://127.0.0.1:8000/docs.

`voice` nhập `luna-tutor` từ backend dưới dạng editable dependency, nhưng nó vẫn
thực thi trong `voice/server/.venv`. Thay đổi backend source được Voice dev
runner theo dõi và reload.

## Cấu hình

Sao chép `.env.example` tại root thành `.env` và đặt các biến provider cần thiết:

```text
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-3.5-flash-lite
SONIOX_API_KEY=
SONIOX_VOICE_ID=Grace
```

Không commit `.env`. Phiên học kết thúc khi rời bài hoặc service dừng.

## Cấu trúc

```text
backend/
├── src/luna_tutor/
│   ├── api/          # FastAPI routes/runtime
│   ├── teaching/     # deterministic lesson progression
│   ├── prompts/      # Teacher rules; Jev rubric nằm trong docs/evaluation
│   └── ...
├── pyproject.toml
└── .venv/            # backend-specific Python environment
```

## Test

Từ repository root:

```bash
uv run --project backend pytest -q
```
