# Standalone Free Talk Room Design

**Date:** 2026-09-20  
**Status:** Awaiting written-spec approval

## 1. Intent and success criteria

Add an independent Free Talk room to `E-Voice-Tutor-v1` by copying the proven Free Talk behavior from `/home/quangnhvn34/dev/massko/E-Voice-Tutor` while keeping its Pipecat runtime separate from the Unit 1 lesson runtime.

Success means:

- the existing Unit 1 lesson, including its curriculum-bound `free-talk` stage, continues unchanged;
- the existing Next.js application exposes a separate `/talk` room using the same visual language as Unit 1;
- a learner can choose a suggested topic or enter a custom topic, connect the microphone, talk naturally with Luna, and stop the room explicitly;
- the standalone room does not create a lesson session, evaluate objectives, update mastery, enter stations, or produce a lesson summary;
- Free Talk prompt behavior and topic-safety rules are copied from the legacy room, with only compatibility changes required by the pinned Pipecat version;
- focused automated tests and one real browser voice smoke test verify the delivered path.

## 2. Scope boundaries

### In scope

- A new standalone Pipecat application under `talk/server/`.
- A new `/talk` page and talk-specific components inside the existing `web/` application.
- A small navigation entry between the Unit 1 lesson and the Free Talk room.
- Topic selection, custom-topic validation, connection status, transcript display, microphone control, and explicit stop.
- Headless Pipecat eval coverage plus frontend and backend unit tests.

### Out of scope

- Replacing or modifying Unit 1's guided Free Talk stage.
- Importing Unit 1 curriculum, `TeachingEngine`, evaluator, persistence, mastery, or summary logic into the standalone room.
- Copying the legacy lesson client, lesson selector, stations, curriculum loader, WebSocket lesson state, or deterministic lesson engine.
- Sharing a running Pipecat worker or LLM context between Unit 1 and Free Talk.
- Adding accounts, Free Talk history, scoring, timers, or analytics.

## 3. Source-of-truth behavior to copy

The legacy working tree is a reference source, not a dependency. The new application copies only the independent Free Talk behavior represented by:

- `server/free_talk/prompts.py` for Luna's durable conversation rules and opening developer message;
- `server/session_config.py` for trimming, requiring, and limiting the topic to 120 characters;
- the Free Talk topic controls and topic-display behavior in `client/index.html`, `client/app.js`, and `client/style.css`;
- the Free Talk branch of `server/bot.py` for the canonical voice pipeline and opening turn.

The copied prompt preserves these policies: primarily English, brief Vietnamese only for requested help, one main question per response, natural recasts only when meaning changes, no lesson or score behavior, safe school-age conversation, natural topic changes, and treating the selected topic as untrusted data.

Uncommitted legacy lesson changes and unrelated legacy files must not be copied. The legacy repository must remain untouched.

## 4. Architecture and ownership

```text
E-Voice-Tutor-v1/
├── backend/                  # existing Unit 1 API; unchanged for this feature
├── voice/server/             # existing Unit 1 Pipecat service; unchanged in responsibility
├── talk/server/              # new independent Free Talk Pipecat service
│   ├── bot.py                # worker construction, transport, lifecycle, opening turn
│   ├── free_talk/
│   │   ├── __init__.py
│   │   └── prompts.py        # copied Free Talk conversation contract
│   ├── session_config.py     # topic-only request validation
│   ├── evals/                # text/audio behavioral scenarios
│   ├── tests/                # prompt, config, and composition tests
│   ├── pyproject.toml
│   ├── uv.lock
│   └── .env.example
└── web/
    └── src/
        ├── app/talk/page.tsx
        └── components/talk/  # topic picker, talk voice provider, transcript, controls
```

`talk/server` owns all Free Talk voice behavior. It is a separately runnable service with its own dependency lock and process lifecycle. It may use the same provider credentials as the legacy room, but it does not import executable application code from either the legacy checkout or `voice/server`.

`web` remains the single browser application. Talk-specific React components are isolated under `components/talk/`; they reuse the existing application's layout tokens and visual language without making the Unit 1 page depend on Talk state.

## 5. Runtime and data flow

1. The learner opens `/talk` from the existing web application.
2. The learner selects a suggested topic or enters a custom topic. The client trims it, requires a non-empty value, and enforces the same 120-character limit as the server.
3. The browser starts a SmallWebRTC session against `NEXT_PUBLIC_TALK_PIPECAT_URL`, defaulting locally to a dedicated Talk port rather than the Unit 1 port.
4. The `/start` request contains only Talk-owned metadata, including the normalized `topic`. There is no Unit 1 `session_id`.
5. `talk/server` validates the topic before constructing provider services.
6. The worker builds an independent cascade: transport input → Soniox STT → user context aggregator → conversational LLM → Soniox TTS → transport output → assistant context aggregator. Exact imports and settings will be confirmed against the pinned Pipecat package and current documentation during implementation.
7. On client readiness, the server appends the copied developer opening message and triggers one LLM response. The chosen topic remains developer-message data and never becomes part of the system instruction.
8. Pipecat transcript events update the Talk transcript in the existing Next.js page. Unit 1 session refresh callbacks are not used.
9. Stop disconnects the Talk client and cancels only that Talk worker. Starting again creates a fresh context with no carryover.

The legacy provider behavior is the baseline: Soniox STT, Google Gemini LLM, and Soniox TTS. Credentials are read from environment variables and documented in `talk/server/.env.example`; no secrets are copied.

## 6. Web experience

The `/talk` page has two states:

- **Setup:** title, short explanation, suggested topic chips, custom-topic input, validation message, and Start button.
- **Conversation:** selected-topic pill, connection/listening/thinking/speaking state, transcript, microphone mute control, and Stop button.

The room reuses the current web application's brand header, spacing, colors, typography, responsive shell, and accessible button conventions. It does not show lesson status, station state, objectives, summary, or the Unit 1 text composer.

The existing Unit 1 page receives only a navigation entry to `/talk`; its session creation, lesson API calls, voice request body, and guided Free Talk finish button remain unchanged.

## 7. Validation and failure behavior

- Blank or overlong topics are rejected in both browser and server without opening provider connections.
- Topic content is treated as untrusted conversation data. Prompt-injection-like topics are placed only inside the delimited developer message.
- Missing `SONIOX_API_KEY`, `SONIOX_VOICE_ID`, `GEMINI_API_KEY`, or configured model fails clearly before the worker starts; `.env.example` contains names only.
- Connection and device failures appear inside the Talk page and leave the learner able to retry.
- A fatal Pipecat error returns the UI to a stopped/reconnectable state.
- Disconnect cleanup affects only the Talk worker. It cannot abandon, finish, or mutate a Unit 1 session.

## 8. Verification strategy

Implementation is test-driven and includes:

1. Python unit tests for topic normalization and rejection, prompt content, prompt-injection separation, and Free Talk pipeline composition.
2. Tests proving the Talk server does not import or instantiate Unit 1 backend, evaluator, teaching engine, or persistence components.
3. React tests for topic selection, custom-topic validation, request metadata, transcript rendering, and stop/retry behavior.
4. Regression tests for the existing Unit 1 voice request and lesson page.
5. A Pipecat text eval covering opening, balanced conversation, one-question behavior, a short learner answer, requested Vietnamese help, and a safe topic change.
6. An audio eval or focused real voice check for STT/TTS and turn-taking.
7. A live browser smoke test at `/talk`: select a topic, connect through the dedicated Talk service, exchange multiple real turns, observe transcript/status, mute/unmute, stop, and confirm Unit 1 still starts independently afterward.

Focused passing suites are reported separately from any unrelated full-suite dependency failures.

## 9. Delivery constraints

- Do not copy `.env`, credentials, caches, generated files, or unrelated legacy code.
- Do not modify the dirty legacy working tree.
- Preserve the existing v1 Git working tree and isolate all product changes to the approved files.
- No deployment or external service mutation is included; local run commands and required environment variables will be documented.
