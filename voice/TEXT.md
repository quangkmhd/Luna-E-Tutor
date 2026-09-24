# Text lesson mode

The website sends typed turns directly to the Grade 3 FastAPI service at
`/api/sessions/{session_id}/turns` with `source: text`. The backend uses the same
Jev decision, Teacher context, and scripted lesson state as Voice, and returns
text without Soniox TTS. The browser disconnects the Voice transport before
submitting typed text.

Run the backend with:

```bash
uv run --project backend --env-file .env uvicorn luna_tutor.api.lesson_runtime:build_lesson_runtime_app --factory --host 127.0.0.1 --port 8000
```

The old Pipecat text pipeline and SQLite lesson session were removed. Grade 3
lesson YAML must be converted to the `items` format described in
`docs/grade3_lesson_refactor_spec.md` by the curriculum author.
