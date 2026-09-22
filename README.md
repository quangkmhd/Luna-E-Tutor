# Luna English Tutor

Ứng dụng học tiếng Anh lớp 3 và lớp 5 gồm bốn dịch vụ chạy cục bộ độc lập: giao diện
web, API/teaching engine, phòng học có lộ trình, và phòng Free Talk.

## Kiến trúc cục bộ

```text
Browser
  │ http://localhost:3000
  ▼
web (Next.js)
  ├── API bài học ─────────────► backend (FastAPI, :8000)
  ├── Phòng học theo bài ──────► voice (Pipecat/WebRTC, :7860)
  └── Free Talk ───────────────► talk  (Pipecat/WebRTC, :7863)
```

| Thành phần | Thư mục | Vai trò | Local URL/port | Runtime riêng |
| --- | --- | --- | --- | --- |
| `web` | `web/` | Next.js UI; chọn Unit, hiển thị lớp học và Free Talk | http://localhost:3000 | Node.js/npm, không dùng Python venv |
| `backend` | `backend/` | FastAPI API, Teaching Engine, Evaluator, SQLite | http://127.0.0.1:8000 | `backend/.venv` |
| `voice` | `voice/server/` | Pipecat WebRTC cho bài học có lộ trình | http://127.0.0.1:7860/client/ | `voice/server/.venv` |
| `talk` | `talk/server/` | Pipecat WebRTC cho trang `/talk`, không có lesson state | http://127.0.0.1:7863/client/ | `talk/server/.venv` |

Ba Python environment là các venv **tách biệt**, dù cùng được `uv` tạo từ
CPython. Cài dependency tại một dịch vụ sẽ không cài sang dịch vụ khác.
Riêng `voice` dùng package `luna-tutor` từ `backend` dưới dạng editable dependency,
nhưng vẫn chạy bằng `voice/server/.venv`.

## Chuẩn bị lần đầu

Cần có Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js và npm.
`talk` hiện yêu cầu Python 3.11+; thực tế các venv hiện tại cùng dùng Python 3.14.

```bash
cp .env.example .env

cd backend && uv sync
cd ../voice/server && uv sync
cd ../../talk/server && uv sync
cd ../../web && npm install
```

Điền khóa thật vào `.env` ở root; không tạo `.env` riêng trong `voice/server`
hoặc `talk/server`.

| Biến | Dùng bởi |
| --- | --- |
| `OPENROUTER_API_KEY` | backend, voice, talk |
| `OPENROUTER_MODEL` | Teacher/Free Talk; mặc định `google/gemini-3.5-flash-lite` |
| `TUTOR_EVALUATOR_MODEL` | Evaluator của backend |
| `SONIOX_API_KEY`, `SONIOX_VOICE_ID`, `SONIOX_TTS_VOICE` | voice và talk |

Xem đầy đủ biến môi trường, CORS và ICE/STUN trong [`.env.example`](.env.example).
Không commit `.env` hoặc khóa API.

## Chạy cả bốn dịch vụ

Từ root repository:

```bash
chmod +x scripts/run-local.sh
./scripts/run-local.sh
```

Script khởi động đồng thời:

- `backend` tại `127.0.0.1:8000` (tự reload khi sửa Python hoặc YAML trong `backend/src`, và YAML trong `curriculum`)
- `voice` tại `127.0.0.1:7860` (theo dõi `voice/server`, `backend/src` và `curriculum`)
- `talk` tại `127.0.0.1:7863` (theo dõi `talk/server`)
- `web` tại `http://localhost:3000`

Mở `http://localhost:3000` để học theo Unit, hoặc
`http://localhost:3000/talk` để dùng Free Talk. Nhấn `Ctrl+C` ở terminal chạy
script để dừng toàn bộ bốn process.

Màn chọn bài hiện có lớp 3 Unit 1 **Hello** và lớp 5 Unit 1–5. Unit 1 lớp 3
có URL `/grade3/unit1` để chọn Lesson; Lesson 1 mở tại
`/grade3/unit1/lesson/1`. Các URL `/unit1`–`/unit5` của lớp 5 vẫn dùng được.

Trong `curriculum/grade-*/unit-*/.../content.yaml`, hoạt động giới thiệu từ vựng
mặc định cần **3 lượt học sinh nói đúng** trước khi chuyển từ. Có thể đổi cho từng
hoạt động bằng `completion_rule.learner_repetitions` (1–5). Trường
`model_repetitions` đếm số lần Luna đọc mẫu; `max_attempts` giới hạn lượt cần
sửa hoặc hỗ trợ, không đếm lượt đọc đúng.
System prompt Teacher và Gemini Evaluator được ghép từ quy tắc chung trong
`backend/src/luna_tutor/prompts/shared/` và phần riêng của từng lớp trong
`backend/src/luna_tutor/prompts/grades/grade-03/` hoặc `grade-05/`.
Runtime chọn prompt theo lớp của phiên học; thiếu prompt thì báo lỗi cấu hình.

Log tách riêng tại:

```text
.run/logs/backend.log
.run/logs/voice.log
.run/logs/talk.log
.run/logs/web.log
```

## Chạy từng dịch vụ

Mỗi lệnh cần được chạy trong terminal riêng.

### Backend

```bash
cd backend
uv run --env-file ../.env uvicorn luna_tutor.api.runtime:build_runtime_app \
  --factory --host 127.0.0.1 --port 8000 --reload --reload-dir src
```

Kiểm tra API: `http://127.0.0.1:8000/docs`.

### Voice — lớp học theo Unit

```bash
cd voice/server
uv run --env-file ../../.env bot.py -t webrtc \
  --host 127.0.0.1 --port 7860 \
  --allowed-origins http://localhost:3000
```

### Talk — Free Talk

```bash
cd talk/server
uv run --env-file ../../.env bot.py -t webrtc \
  --host 127.0.0.1 --port 7863 \
  --allowed-origins http://localhost:3000
```

### Web

```bash
cd web
NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8000 \
NEXT_PUBLIC_PIPECAT_URL=http://localhost:7860 \
NEXT_PUBLIC_TALK_PIPECAT_URL=http://localhost:7863 \
  npm run dev
```

Các `NEXT_PUBLIC_*` được trình duyệt đọc khi Next.js khởi động. Nếu đổi URL
API/bot, hãy dừng và khởi động lại `web`.

## Kiểm tra nhanh

```bash
# Web UI
curl -I http://localhost:3000

# Backend API
curl -I http://127.0.0.1:8000/docs

# Pipecat browser clients
curl -I http://127.0.0.1:7860/client/
curl -I http://127.0.0.1:7863/client/
```

## Test

```bash
uv run --project backend pytest -q
uv run --project voice/server pytest -q tests/voice tests/scripts tests/ops
uv run --project talk/server pytest -q talk/server/tests
npm test
cd web && npm run lint && npm run build
```

Các test Python phải được gọi bằng project/venv tương ứng; không chạy `pytest`
chung từ root rồi suy ra cả ba Python service đều đã được kiểm tra.

## Docker

`docker-compose.yml` cũng định nghĩa bốn service `backend`, `voice`, `talk`,
và `web` cho môi trường triển khai. Các cổng host mặc định trong `.env.example`
là `8090` cho backend và `3001` cho web; chúng khác với cổng local development
`8000` và `3000` nêu ở trên.
