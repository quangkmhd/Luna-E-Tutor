# Luna English Tutor — Grade 5 Unit 1

Luna is a stateful English tutor for Quang. This repository contains the complete Unit 1 curriculum and an independent, topic-based Free Talk room in the same Next.js interface.

The Evaluator answers “what did Quang demonstrate?”. The Teaching Engine alone decides “what happens next?”. The Teacher receives that bounded decision and turns it into one short, natural spoken response. Contact information is removed locally before any model call.

## Setup

Requirements: Python 3.12 or newer, `uv`, Node.js, and npm.

```bash
cp .env.example .env
# Unit 1: OPENROUTER_API_KEY, SONIOX_API_KEY, SONIOX_TTS_VOICE.
# Free Talk: GEMINI_API_KEY, SONIOX_API_KEY, SONIOX_VOICE_ID.
# The checked-in model defaults can be overridden with TUTOR_EVALUATOR_MODEL
# and TALK_LLM_MODEL.

cd backend
uv sync

cd ../voice/server
uv sync

cd ../../talk/server
uv sync

cd ../../web
npm install
```

The Gemini Teacher is pinned to `google/gemini-3.5-flash-lite`. Select the real-learning evaluator with `TUTOR_EVALUATOR_MODEL`: use `~typesafe/jev-latest` or `google/gemini-3.5-flash-lite`. The checked-in example selects Jev. Real keys stay in `.env` and are never sent to the browser. The same selection is used by the web API and Pipecat voice runtime.

## Run the web experiment

```bash
chmod +x scripts/run-local.sh
./scripts/run-local.sh
```

Open `http://localhost:3000` for Unit 1 or `http://localhost:3000/talk` for the standalone Free Talk room. Unit 1's final guided Free Talk stage remains part of the curriculum and uses its lesson state; `/talk` is a separate Pipecat service with no stations, mastery, lesson summary, or saved lesson session.

The local runner starts the Unit 1 API on port 8000, Unit 1 voice on 7860, standalone Talk voice on 7863, and the web app on 3000. Logs are written separately to `.run/logs/backend.log`, `.run/logs/voice.log`, `.run/logs/talk.log`, and `.run/logs/web.log`.

You can also start each process separately:

```bash
cd backend
uv run uvicorn luna_tutor.api.runtime:build_runtime_app --factory --port 8000 --env-file ../.env

cd talk/server
uv run --env-file ../../.env bot.py -t webrtc --host 127.0.0.1 --port 7863 --allowed-origins http://localhost:3000

cd web
NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8000 \
NEXT_PUBLIC_TALK_PIPECAT_URL=http://localhost:7863 npm run dev
```

## Verification

```bash
uv run --project voice/server pytest -q tests/voice tests/scripts tests/ops
uv run --project talk/server pytest -q talk/server/tests
uv run --project talk/server ruff check talk/server
uv run --project talk/server pyright talk/server
uv run --project backend python -m luna_tutor.evals.cli verify-baseline evals/unit-01/baseline.json

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
The standalone room's provider-backed browser and eval evidence is retained in
`docs/evaluation/free-talk-room-verification.md`.
