# Luna English Tutor — Grade 5 Units 1–5

Luna is a stateful English tutor for Quang. This repository contains source-audited Grade 5 Units 1–5, a selectable Jev or Gemini Evaluator, a separately prompted Gemini Teacher, deterministic teaching progression, local SQLite history, a FastAPI API, and a Next.js interface. The web interface lists the available units and stores the selected `unit_id` with each session.

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

The Gemini Teacher is pinned to `google/gemini-3.5-flash-lite`. Select the real-learning evaluator with `TUTOR_EVALUATOR_MODEL`: use `~typesafe/jev-latest` or `google/gemini-3.5-flash-lite`. The checked-in example selects Jev. Real keys stay in `.env` and are never sent to the browser. The same selection is used by the web API and Pipecat voice runtime.

## Run the web experiment

```bash
chmod +x scripts/run-local.sh
./scripts/run-local.sh
```

Open `http://localhost:3000`. Sessions are saved to `backend/data/luna-tutor.sqlite3` unless `TUTOR_DATABASE_PATH` overrides it. “New session” keeps the old history and starts at Warm-up. Free Talk has no timer and ends only with its explicit button.

Select a unit in the web interface before starting a session. API clients create a session with an explicit curriculum ID, for example:

```json
{"unit_id": "grade05.unit02"}
```

The supported IDs are `grade05.unit01` through `grade05.unit05`.

You can also start each process separately:

```bash
cd backend
uv run uvicorn luna_tutor.api.runtime:build_runtime_app --factory --port 8000 --env-file ../.env

cd web
NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8000 npm run dev
```

## Verification

```bash
uv run --project voice/server python -m pytest -q
uv run --project backend python -m luna_tutor.evals.cli verify-baseline evals/unit-01/baseline.json
uv run --project backend python -m luna_tutor.evals.cli run --unit grade05.unit02 --set development --repetitions 1 --out evals/unit-02/reports
uv run --project backend python -m luna_tutor.evals.cli run --unit grade05.unit03 --set development --repetitions 1 --out evals/unit-03/reports
uv run --project backend python -m luna_tutor.evals.cli run --unit grade05.unit04 --set development --repetitions 1 --out evals/unit-04/reports
uv run --project backend python -m luna_tutor.evals.cli run --unit grade05.unit05 --set development --repetitions 1 --out evals/unit-05/reports

npm install
npm test
cd web
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser suite uses a deterministic fixture service that is accepted only when both `ENV=test` and `TUTOR_LLM_MODE=fixture` are set. Production/local live mode cannot accidentally enable it.

Evaluation details and the reviewed Teacher samples are in `docs/evaluation/unit-01-report.md`.
