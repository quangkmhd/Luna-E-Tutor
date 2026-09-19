# Grade 5 topic-speaking evaluation

The deterministic fixture suite covers beginner help, an independent target-word use, a child asking Luna a question, unclear input, and ending before all selected words are used. Live text and audio remain separate verification steps because they consume provider services.

Run the local app in fixture mode, then:

```bash
uv run --project backend python scripts/eval-speaking-grade5.py --base-url http://127.0.0.1:8000
```

For live audio, open `/speaking`, create a session, enable the microphone, and inspect Soniox STT/TTS latency and interruption behavior. Do not treat transcript-only success as pronunciation evidence.
