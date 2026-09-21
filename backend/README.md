# Backend — Luna Tutor API và Teaching Engine

FastAPI service cho curriculum lớp 3 và lớp 5, Evaluator, Teaching Engine, Teacher,
session persistence SQLite và API mà web/voice sử dụng. Đây là service riêng
chạy bằng `backend/.venv`; xem [README root](../README.md) để biết bốn service.

## Chạy local

```bash
uv sync
uv run --env-file ../.env uvicorn luna_tutor.api.runtime:build_runtime_app \
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
TUTOR_EVALUATOR_MODEL=~typesafe/jev-latest
SONIOX_API_KEY=
SONIOX_TTS_VOICE=Grace
TUTOR_DATABASE_PATH=backend/data/luna-tutor.sqlite3
```

Không commit `.env` hoặc SQLite runtime data. Đường dẫn database có thể đổi bằng
`TUTOR_DATABASE_PATH`.

## Cấu trúc

```text
backend/
├── src/luna_tutor/
│   ├── api/          # FastAPI routes/runtime
│   ├── teaching/     # deterministic lesson progression
│   ├── prompts/      # Teacher/Evaluator prompt resources
│   └── ...
├── data/             # local SQLite data (runtime)
├── pyproject.toml
└── .venv/            # backend-specific Python environment
```

## Test

Từ repository root:

```bash
uv run --project backend pytest -q
```

Các eval CLI cũng chạy qua backend project, ví dụ:

```bash
uv run --project backend python -m luna_tutor.evals.cli verify-baseline \
  evals/unit-01/baseline.json
```
