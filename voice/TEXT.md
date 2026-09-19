# Pipecat text experiment

Current entry point: `server/text_runtime.py`. It uses the existing session HTTP API and SQLite history, so the Next.js page can submit typed input unchanged. A Pipecat worker routes the turn through the existing Evaluator → Engine → Teacher core and returns one completed turn. No STT/TTS service is constructed by this entry point.

From the repository root, once `uv sync --project voice/server` finishes:

```bash
uv run --project voice/server uvicorn text_runtime:build_app --factory --app-dir voice/server --host 127.0.0.1 --port 8000 --env-file /path/to/.env
```

In another terminal:

```bash
cd web
NEXT_PUBLIC_TUTOR_API_URL=http://localhost:8000 npm run dev
```

Only `OPENROUTER_API_KEY` is needed for this text runtime. Model is fixed by the teaching core to `google/gemini-3.5-flash-lite`. The original CLI-generated `server/bot.py` and starter audio/eval files are deferred scaffold references, not the text entry point.

Verification is in progress: four pipeline/API tests and a live recast smoke test have run on the available Pipecat 1.8.1 installation. The dedicated environment pins 1.11.0 and needs its own verification after installation. Flows, text-delivery progress and a full real-model Unit 1 journey remain unfinished; do not use this intermediate adapter as evidence of complete teaching behavior.
