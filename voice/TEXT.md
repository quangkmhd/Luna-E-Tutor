# Pipecat text runtime

`server/text_runtime.py` serves the existing HTTP session API and SQLite history for the Next.js website. Production turns use Pipecat 1.11's bundled **native Flows**:

1. Restore the current activity node from the authoritative session snapshot, without generating speech/text.
2. Evaluator supplies evidence; Teaching Engine authorizes the next action.
3. FlowManager selects the authorized activity node and replaces its bounded task context.
4. A custom Pipecat LLMService passes that context to the existing Gemini Teacher prompt/schema/validation.
5. One validated response plus its state proposal returns to the API for atomic persistence.

Each HTTP request owns its worker, context and FlowManager. Retries restore SQLite state; failed evaluation, node setup or Teacher output cannot commit advancement. Flows transports the authorized context; it does not give Gemini authority to choose transitions. Process-only test fixtures retain a minimal pipeline adapter and are not the production teaching path.

No STT/TTS is constructed. User turns use `ExternalUserTurnStrategies`, with no default local audio turn analyzer. The separate `pipecat-ai-flows` dependency was removed because Flows is bundled in the pinned framework.

From the repository root:

```bash
uv sync --project voice/server
uv run --project voice/server uvicorn text_runtime:build_app --factory --app-dir voice/server --host 127.0.0.1 --port 8000 --env-file /path/to/.env
```

In another terminal:

```bash
cd web
NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8000 npm run dev
```

Only `OPENROUTER_API_KEY` is needed. The teaching core fixes the model to `google/gemini-3.5-flash-lite`. Original CLI-generated `server/bot.py` and starter audio/eval files remain deferred scaffold references, not the text entry point.

Verification commands:

```bash
voice/server/.venv/bin/python -m pytest backend/tests voice/tests -q
voice/server/.venv/bin/python scripts/eval-pipecat-text.py --env-file /path/to/.env --output /tmp/new-behavior-run.json
voice/server/.venv/bin/python scripts/eval-unit1-journey.py --env-file /path/to/.env --output /tmp/new-journey-run.json
```

The scenario command runs real model outputs with independent state/action checks and keeps semantic criteria pending review. The journey uses scripted answers; repeated scripted answers and reaching Free Talk are not proof of natural or complete teaching. See `docs/evaluation/pipecat-text-audit.md` for failures, corrections and outstanding acceptance work.
