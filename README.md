# Luna English Tutor — Grade 5 Unit 1

Luna is a stateful English tutor for Quang. This repository currently contains the complete Unit 1 curriculum, a separately prompted Gemini Evaluator and Gemini Teacher, deterministic teaching progression, local SQLite history, a FastAPI API, and a Next.js experiment interface.

The Evaluator answers “what did Quang demonstrate?”. The Teaching Engine alone decides “what happens next?”. The Teacher receives that bounded decision and turns it into one short, natural spoken response. Contact information is removed locally before any model call.

## Setup

Requirements: Python 3.12 or newer, `uv`, Node.js, and npm.

```bash
cp .env.example .env
# Add the existing OPENROUTER_API_KEY to .env.

cd backend
uv sync

cd ../web
npm install
```

The model is pinned in code to `google/gemini-3.5-flash-lite`. Real keys stay in `.env` and are never sent to the browser.

## Run the web experiment

```bash
chmod +x scripts/run-local.sh
./scripts/run-local.sh
```

Open `http://localhost:3000`. Sessions are saved to `backend/data/luna-tutor.sqlite3` unless `TUTOR_DATABASE_PATH` overrides it. “New session” keeps the old history and starts at Warm-up. Free Talk has no timer and ends only with its explicit button.

You can also start each process separately:

```bash
cd backend
uv run uvicorn luna_tutor.api.runtime:build_runtime_app --factory --port 8000 --env-file ../.env

cd web
NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8000 npm run dev
```

## Verification

```bash
cd backend
uv run pytest -q
uv run python -m luna_tutor.evals.cli verify-baseline ../evals/unit-01/baseline.json

cd ../web
npm test -- --run
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser suite uses a deterministic fixture service that is accepted only when both `ENV=test` and `TUTOR_LLM_MODE=fixture` are set. Production/local live mode cannot accidentally enable it.

Evaluation details and the reviewed Teacher samples are in `docs/evaluation/unit-01-report.md`.
