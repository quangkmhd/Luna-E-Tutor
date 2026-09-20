# Pipecat-First Voice Teaching Integration Design

## Intent

Make Pipecat 1.11.0 the authority for the browser voice session, media transport,
turn lifecycle, Soniox STT/TTS services, RTVI events, and structured conversation
nodes. Preserve the existing deterministic teaching engine as the authority for
pedagogical decisions and persisted lesson progress.

The result is one browser-to-teacher voice path for Unit 1. It must not maintain a
second custom browser media client, a second turn detector, or a second Flow
implementation beside Pipecat.

## Current conflicts to resolve

1. `voice/server/bot.py` is a canonical Pipecat cascade, but it is still a generic
   assistant and does not call the Unit 1 teaching engine or its Flow nodes.
2. `voice/server/text_flows.py` has the authoritative teaching/Flow integration,
   but it accepts custom typed frames and runs in a separate non-audio pipeline.
3. The Next.js application uses the REST teaching API and has no active Pipecat
   React client packages or SmallWebRTC connection.
4. `voice/server/bot.py` reads `SONIOX_VOICE_ID`, while the example environment
   does not declare it.
5. The Python manifest pins Pipecat with the OpenRouter extra only even though the
   runtime directly imports Soniox services.

The existing uncommitted removal of the former speaking subsystem is user-owned.
This work must not restore those deleted files or overwrite unrelated dirty-tree
changes.

## Architecture

The production voice path is:

```text
Pipecat React client
  -> SmallWebRTC transport
  -> SonioxSTTService
  -> final-transcript teaching adapter
  -> deterministic TurnService
  -> FlowManager node/context update
  -> bounded Teacher LLM
  -> SonioxTTSService
  -> transport output
  -> assistant context and completion tracking
```

Pipecat owns media capture/playback, RTVI readiness, interruption propagation,
VAD/Smart Turn, frame ordering, STT/TTS service lifecycles, and Flow node context.
The teaching engine owns evidence validation, allowed actions, next activity, and
durable state transitions. The LLM may phrase the authorized teacher action but
may not choose lesson transitions.

## Server design

Keep the scaffolded `bot(runner_args)` and `create_transport()` contract. Keep the
canonical cascade order, including the assistant aggregator after transport
output. Add a focused teaching processor/adapter between Soniox STT and the
response leg instead of creating another pipeline runner per learner turn.

Only final Soniox transcripts may invoke `TurnService.plan()`. Interim transcripts
may be emitted to the client for display but must not create evidence, increment
attempts, transition a Flow node, or persist a completed turn. Duplicate final
frames for the same turn ID must be idempotent.

Create one `FlowManager` per connected Pipecat worker with the same worker, LLM,
context aggregator, and transport. Initialize it once, restore the persisted
activity node without speaking, then use `set_node_from_config()` after the
teaching engine authorizes the next node. Use `ContextStrategy.RESET` so each
bounded teacher request is the only active task instruction.

Configure Soniox through current `Settings` objects:

- STT model `stt-rt-v5`, English and Vietnamese language hints, non-strict hints,
  and lesson vocabulary context.
- Keep `vad_force_turn_endpoint=True` initially, so Pipecat VAD/Smart Turn owns
  turn completion. Do not configure Soniox endpoint sensitivity settings in this
  mode.
- TTS model `tts-rt-v2`, voice from required `SONIOX_VOICE_ID`, and an explicit
  English language. Any runtime setting change must be sent as an ordered Pipecat
  frame between utterances, never by mutating the service directly.

Startup for a live WebRTC transport must fail with a clear variable name when
`SONIOX_API_KEY`, `SONIOX_VOICE_ID`, `OPENROUTER_API_KEY`, or `OPENROUTER_MODEL`
is absent. Tests and text-mode evals may inject services and avoid live secrets.

## Web design

Use only the official packages:

- `@pipecat-ai/client-js`
- `@pipecat-ai/client-react`
- `@pipecat-ai/small-webrtc-transport`

Create a single client-side Pipecat provider for the active lesson. Connect the
SmallWebRTC client to the Pipecat `/api/offer` endpoint, render bot audio with
`PipecatClientAudio`, use Pipecat's mic control, and derive connection, speaking,
and transcript UI from Pipecat/RTVI state. Do not add `getUserMedia`,
`RTCPeerConnection`, WebSocket audio, or custom audio playback code.

The existing REST API remains the control/data plane for session creation,
history, summaries, and persisted state. The Pipecat voice connection is the
real-time media plane. The browser must not submit the same spoken turn again via
the REST typed-turn endpoint.

For the current self-hosted/local target, use `client.connect()` with
`webrtcRequestParams.endpoint`. Do not use `startBotAndConnect()` unless a future
deployment adds a start endpoint that returns transport credentials.

## Completion and failure semantics

- A provider/STT/transport failure does not count as a learner failure.
- A learner interruption cancels unplayed teacher audio; content not emitted to
  the output path cannot be marked as taught.
- Lesson state is committed once per completed authorized response. Disconnect or
  TTS failure preserves the last committed state and leaves unfinished work for
  retry/recovery.
- Mic permission, connection, backend, and provider errors are shown as actionable
  UI states; API keys and provider details stay server-side.
- The browser disconnects the Pipecat client when leaving the active voice lesson.

## Compatibility and dependency policy

Pipecat `1.11.0` and its current Context Hub API are authoritative. Deprecated
`PipelineTask`, `EndTaskFrame`, `SonioxInputParams`, direct service mutation, and
custom media replacements are not allowed. The Python dependency must explicitly
request both `openrouter` and `soniox` extras at the same `1.11.0` pin.

The Next.js implementation must follow the local Next.js 16 documentation under
`web/node_modules/next/dist/docs/` and remain compatible with React 19.

## Verification

1. Python unit tests prove service configuration, required environment validation,
   final-only transcript handling, duplicate-turn idempotency, Flow restoration,
   provider-error neutrality, and interruption/non-delivery semantics.
2. Pipecat text evals prove teaching decisions and wording without STT/TTS.
3. Pipecat audio evals exercise VAD, Soniox STT/TTS, interruptions, bilingual
   learner input, and pronunciation-sensitive vocabulary.
4. React tests prove provider lifecycle, the exact SmallWebRTC connection params,
   official mic/audio components, transcript rendering, disconnect cleanup, and
   no duplicate REST submission for spoken turns.
5. Run the complete backend, voice, and web suites, then run web lint/build. A live
   Soniox/WebRTC smoke test is reported separately because it requires valid user
   credentials, a selected voice, microphone permission, and listening review.

## Acceptance criteria

- One real voice turn reaches the existing deterministic teaching engine and
  returns authorized teacher speech through Soniox TTS.
- The active lesson node in Pipecat Flow matches persisted lesson state after each
  completed turn.
- The web application uses Pipecat Client and SmallWebRTC without custom browser
  media code.
- Interim, duplicate, failed, and interrupted turns cannot incorrectly advance
  lesson state.
- All automated verification is green, and any unrun credential-dependent checks
  are explicitly reported rather than inferred.
