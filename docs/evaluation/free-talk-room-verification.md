# Standalone Free Talk verification

Verified on 2026-09-20 in branch `codex/standalone-free-talk`. This document
retains the manual provider-backed evidence that cannot run in the credential-free
browser fixture suite.

## Real browser and provider path

The worktree web app ran on port 3091 and the standalone Talk service on port
7863 with the real Gemini and Soniox credentials from the local environment.

- Opened `/talk`, selected **Animals**, and started Free Talk.
- Confirmed the browser posted `topic: Animals` to the Talk `/start` endpoint,
  established the WebRTC session, and showed Luna's opening in the transcript.
- Observed the visible state change from **Speaking** to **Ready**.
- Exercised **Mute microphone**, **Unmute microphone**, and **Stop conversation**.
- Changed to **School life** and confirmed a new provider/store opened with an
  empty transcript before the new School life opening appeared. No Animals
  transcript leaked into the new room.
- Returned to the existing Unit 1 page on port 3000 and independently connected
  its original voice service on port 7860; Luna's Unit 1 greeting remained visible
  and the session stopped normally.

The corresponding process logs were `.run/logs/talk.log` and
`.run/logs/web.log` in this worktree, and `.run/logs/voice.log` for the existing
Unit 1 runtime.

## Real behavioral eval path

The provider-backed text transport completed four successive responses in one
session: the Animals opening, a response to “I like dogs,” a brief Vietnamese
explanation requested for “loyal,” and a natural change to School life. This
proved the real Gemini conversation path and multi-turn context before semantic
judge criteria were added to the checked-in scenarios.

The final scenarios now retain explicit semantic criteria for opening behavior,
balanced conversation, brief Vietnamese help, natural topic changes, and safe
handling of unsuitable content. Their judge is the locally installed
`gemma4:12b-it-qat` Ollama model. The harness parsed that configuration and the
real bot produced its opening, but the judge process could not load because the
GPU was already occupied and Ollama returned CUDA out-of-memory. No unrelated
GPU process was stopped to make room.

## Known verification boundary

An audio-mode eval was attempted, but first-run Kokoro/Moonshine model
initialization did not complete within the test window and the process was stopped
cleanly. Therefore this record does not claim three successful synthesized or
microphone learner utterances. Real browser WebRTC, provider TTS, visible
transcript, controls, and the multi-turn text eval were verified; full automated
audio round-trip remains the optional final confidence pass after the local model
assets are available.
