# Pipecat + Soniox Voice Verification

Date: 2026-09-20 (Asia/Bangkok)

## Runtime under test

- Pipecat AI: 1.11.0
- Soniox STT: `stt-rt-v5`
- Soniox TTS: `tts-rt-v2`
- Language hints: English and Vietnamese, non-strict
- Turn endpoint owner: Pipecat VAD/Smart Turn (`vad_force_turn_endpoint=True`)
- Browser transport: SmallWebRTC through the Pipecat runner `/start` session flow
- Browser packages: `@pipecat-ai/client-js` 1.13.1, `client-react` 1.8.2, and `small-webrtc-transport` 1.10.8
- LLM: the `OPENROUTER_MODEL` value from the root `.env` (value intentionally redacted)

No credential value was printed, copied into a test, or written to this report.

## Deterministic verification

| Area | Command | Result |
| --- | --- | --- |
| Backend | `uv run --project backend pytest tests/backend -q` | 410 passed, 1 skipped |
| Voice and local runner | `uv run --project voice/server pytest tests/voice tests/scripts/test_run_local.py -q` | 24 passed |
| Web | `npm --prefix web test -- --run` | 20 passed |
| Web lint | `npm --prefix web run lint` | passed |
| Web production build | `npm --prefix web run build` | passed |

The voice suite covers final-only transcript handling, duplicate final transcripts, commit-after-speech, interruption/error/disconnect rollback, exact canonical pipeline order, request session selection, and complete Pipecat `LLMSettings` initialization.

The final independent review added two lifecycle regressions: an upstream provider `ErrorFrame` must clear pending teaching state before any later speech-stop frame, and a completed lesson must disconnect the Pipecat client even though its voice controls disappear. The client also cancels delayed REST refresh timers on cleanup.

## Live provider evidence

### OpenRouter teaching path

A live REST turn was submitted with `I am happy today.`. The configured OpenRouter evaluator and teacher completed the turn, returned a 218-character teacher response, persisted exactly one turn, and advanced the session state version from 0 to 1.

### Soniox protocol round trip

A paced real-time Soniox check used the same production models and configured voice as the Pipecat services:

- TTS returned 46,422 bytes of PCM audio.
- That audio was streamed to Soniox STT in real-time-sized chunks.
- Final transcript: `I am happy today.`
- The expected word `happy` was present.

An initial standalone attempt sent the complete audio faster than real time and Soniox closed it with request timeout 408. Pacing the input, as a real Pipecat media transport does, fixed the test. This was a smoke-harness issue, not a runtime code change.

### Browser SmallWebRTC session

The Chrome client successfully:

- called Pipecat runner `/start` with the REST `session_id` in `requestData.body`;
- negotiated the session-specific Pipecat offer route and reached `Ready`;
- connected live Soniox STT and TTS;
- restored the `warm-up.feelings` Pipecat Flow node;
- synthesized `Hello, Quang! I'm Luna. How are you today?` with Soniox TTS;
- exposed the spoken greeting in the official Pipecat client transcript;
- muted and unmuted the microphone; and
- disconnected cleanly without advancing lesson state.

Observed Soniox greeting TTS TTFB was 0.658 seconds before the final configuration fix and 0.575 seconds after it.

The first browser attempt sent the offer directly to `/api/offer`. Pipecat's direct FastAPI route did not deserialize the client's camel-case `requestData`, so the bot received no `session_id`. The client now follows the Pipecat runner contract: `startBotAndConnect({ endpoint: '/start', requestData: { transport: 'webrtc', body: { session_id }}})`. The subsequent real session selected the correct persisted REST session.

The live log also exposed that the custom bounded teacher service inherited a delta-mode `LLMSettings` object containing `NOT_GIVEN` values. A regression test now checks every field, and the service initializes a complete store-mode settings object. A second live run had no `NOT_GIVEN` error.

## Eval harness and manual-only scope

The text and audio scenario files cover greeting, English answers, Vietnamese-English input, a long answer, and barge-in. The audio scenario uses local Kokoro learner speech and Moonshine transcription while the bot itself uses live Soniox STT/TTS.

The text scenario ran against the live worker and passed 1/1 in 17.3 seconds. Its three turns were `I am happy today.`, a Vietnamese request for a slower explanation, and an off-target football answer. This run also found a real integration gap: RTVI `send-text` arrives as `LLMMessagesAppendFrame`, not a Soniox `TranscriptionFrame`. `VoiceTeachingProcessor` now accepts a single user `send-text` turn through the same teaching authorization path, with a regression test, so fast text eval does not bypass the deterministic lesson engine.

The audio scenario parsed successfully and its local dependencies installed, but its first execution had to download the large Kokoro model asset over a slow connection. The download was stopped before any scenario turn ran; no passing audio-eval result or WAV recording is claimed. The direct paced Soniox PCM round trip and the live browser Soniox TTS session above are the completed real-audio checks for this run.

The environment did not provide a human speaker at the microphone. Therefore hearing the output with human ears, speaking an unscripted Vietnamese clarification, and manually interrupting mid-utterance remain human-audible checks. The provider PCM round trip and browser media session above verify the machine-observable parts without claiming those manual observations.

## Log inspection

The successful browser run showed the intended processor order:

`SmallWebRTC input -> Soniox STT -> VoiceTeachingProcessor -> user context -> BoundedTeacherLLM -> Soniox TTS -> SmallWebRTC output -> VoiceCommitProcessor -> assistant context`

No `invalid_stream_state`, duplicate turn commit, state-version conflict, or traceback appeared in the successful post-fix browser run.

Finally, `./scripts/run-local.sh` was started after a clean dependency sync. The backend sessions endpoint, Pipecat WebRTC page, and Next.js page each returned HTTP 200. One Ctrl-C stopped all three child processes, and ports 8000, 7860, and 3000 were confirmed closed.
