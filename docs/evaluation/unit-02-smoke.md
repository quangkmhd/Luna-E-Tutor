# Unit 2 vertical-slice smoke — 2026-09-20

## Automated evidence

- Browser E2E:
  `npm run test:e2e --workspace web -- tests/e2e/multi-unit-session.spec.ts`
  passed 1/1 in Chromium. It selected `grade05.unit02`, rendered
  `Our homes`, submitted a turn, reloaded, and read the persisted session
  back with Unit 2 metadata. No Unit 1 title was rendered in the lesson.
  The complete Playwright suite subsequently passed 6/6.
- Voice routing:
  `/home/quangnhvn34/dev/massko/E-Voice-Tutor-v1/voice/server/.venv/bin/pytest -q tests/voice/test_voice_bot.py tests/voice/test_voice_teaching.py`
  passed 15/15. The worker routed a persisted Unit 2 state to the Unit 2
  service. Unknown stored Units failed before Soniox STT/TTS construction.
- Scenario audit: `evals/unit-02/development/core.yaml` loads 10 deterministic
  cases, and `coverage.yaml` reports no missing source, branch, or objective
  coverage.

## Native browser smoke

Commands:

```bash
cd backend
ENV=test TUTOR_LLM_MODE=fixture \
  TUTOR_DATABASE_PATH=/tmp/luna-unit2-smoke.sqlite3 \
  .venv/bin/uvicorn luna_tutor.api.runtime:build_runtime_app \
  --factory --host 127.0.0.1 --port 8091

NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8091 \
  npm run dev --workspace web -- --hostname localhost --port 3090
```

Observed in a real Chrome tab at `http://localhost:3090`:

- selector displayed both Unit 1 and Unit 2;
- selecting Unit 2 displayed `English Tutor · Unit 2` and `Our homes`;
- the safe answer `I feel happy.` produced one teacher turn;
- the visible inspector reported Unit 2, `warm-up.feelings`, version 1;
- `GET /api/sessions` confirmed persisted `unit_id: grade05.unit02`,
  title `Our homes`, and no Unit 1 objective.

## Live voice limitation

A provider-backed microphone smoke was not run. The available checkout
`.env` contains Soniox configuration but no `OPENROUTER_API_KEY`, and the
runtime correctly refuses to invent or bypass that required credential.
Therefore this report does not claim live STT/LLM/TTS audio evidence. The
provider-construction boundary and Unit 2 voice routing are covered by the
15 passing voice integration tests above.
