# voice

A Pipecat AI voice agent built with a cascade pipeline (STT → LLM → TTS).

## Configuration

- **Bot Type**: Web
- **Transport(s)**: SmallWebRTC
- **Pipeline**: Cascade
  - **STT**: Soniox
  - **LLM**: OpenRouter
  - **TTS**: Soniox

## Setup

### Server

1. **Navigate to server directory**:

   ```bash
   cd server
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Configure environment variables once at the repository root**:

   ```bash
   cd ../..
   cp .env.example .env
   # Edit E-Voice-Tutor-v1/.env and add your API keys
   cd voice/server
   ```

4. **Run the bot**:

   ```bash
   uv run bot.py
   ```

   The runner serves every transport; the caller selects which one (a web/mobile
   client picks its transport when it connects; a telephony provider connects to
   `/ws`).

## Testing with evals

This project includes behavioral evals: scripted conversations that drive the bot headless — no live call needed. Starter scenarios live in `server/evals/`; edit them as your bot takes shape and copy them to add more.

From `server/`, run the bot with the eval transport, then drive scenarios against it from a second terminal (the bot stays up across runs):

```bash
uv run bot.py -t eval
# In another terminal:
uv run pipecat eval run evals/starter_text.yaml -v    # fast text-mode check
uv run pipecat eval run evals/starter_audio.yaml -v   # full audio round trip (local models, no API keys)
```

`eval:` criteria are scored by a judge LLM — a local Ollama by default (`ollama pull gemma4:12b`). The comments in the scenario files cover the schema and how to use an OpenAI judge instead.

## Project Structure

```
voice/
├── server/              # Python bot server
│   ├── bot.py           # Main bot implementation
│   ├── evals/           # Behavioral eval scenarios
│   ├── pyproject.toml   # Python dependencies
│   └── ...
├── .gitignore           # Git ignore patterns
└── README.md            # This file
```

All Voice credentials are loaded from the repository-root `.env`; do not create
`voice/server/.env`.
## Building with an AI coding agent

Extending this bot with Claude Code, Codex, or another AI coding assistant? Give it live, accurate Pipecat context instead of stale training data with the **Pipecat Context Hub** — a local index of Pipecat docs, examples, and API source your agent queries over MCP:

```bash
# The Context Hub ships with the CLI
uv tool install "pipecat-ai[cli]"
pipecat context-hub install
```

`install` registers the MCP server with each coding agent it finds and builds the index — a few minutes and about 900 MB the first time. MCP servers load at session start, so do this before opening your coding session, and note the server won't start against an empty index. See the [Pipecat Context Hub docs](https://docs.pipecat.ai/api-reference/context-hub) for the full setup.

## Learn More

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [Pipecat Examples](https://github.com/pipecat-ai/pipecat-examples)
- [Discord Community](https://discord.gg/pipecat)
