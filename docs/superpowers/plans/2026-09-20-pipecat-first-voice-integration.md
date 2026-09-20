# Pipecat-First Voice Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the existing Unit 1 teaching engine to a real Pipecat 1.11.0 SmallWebRTC voice session using Soniox STT/TTS and the official Pipecat React client.

**Architecture:** A single long-lived Pipecat worker owns WebRTC, VAD/Smart Turn, Soniox services, RTVI, FlowManager, and ordered frames for one browser lesson. The deterministic `TurnService` and SQLite repository remain the authorities for decisions and persisted progress; final transcripts enter the teaching adapter, authorized teacher text reaches Soniox TTS, and the completed turn is committed only after Pipecat reports that bot speech stopped.

**Tech Stack:** Python 3.12+, Pipecat AI 1.11.0, Pipecat Flows, Soniox STT/TTS, OpenRouter, FastAPI, SQLite, Next.js 16.3.5, React 19.2.8, Pipecat Client Web, Vitest, pytest, Pipecat eval.

**Spec:** `docs/superpowers/specs/2026-09-20-pipecat-first-voice-integration-design.md`

## Global Constraints

- Pipecat `1.11.0` and APIs verified through the current Pipecat Context Hub are authoritative.
- Keep the generated `bot(runner_args)` and `create_transport()` contract and the canonical cascade order.
- Use `settings=` for Soniox services; do not use deprecated `SonioxInputParams` or direct runtime mutation.
- Pipecat owns browser media, RTVI, VAD/Smart Turn, interruption propagation, and Flow node context.
- The teaching engine owns evidence, pedagogical decisions, lesson transitions, and persistent state.
- Only final transcripts may create a teaching turn. Interim, duplicate, provider-failed, and interrupted turns cannot advance state.
- Keep secrets in `/home/quangnhvn34/dev/massko/E-Voice-Tutor-v1/.env`; never copy values into code, tests, logs, or documentation.
- Preserve all unrelated dirty-tree changes and do not restore the deleted former speaking subsystem.
- Use the official Pipecat browser packages only; do not add custom `getUserMedia`, `RTCPeerConnection`, WebSocket audio, or playback code.
- Test real with the configured OpenRouter and Soniox credentials after deterministic suites pass; redact provider payloads and keys from logs.

## Review Focus

- An interim Soniox transcript followed by a final transcript must produce exactly one teaching decision and one persisted turn.
- A repeated final transcript or reconnect retry with the same turn ID must return the stored result without a second LLM call.
- Barge-in before the teacher finishes must cancel unplayed audio and must not commit the interrupted response as taught.
- Missing/invalid microphone permission or a failed WebRTC offer must leave REST session state unchanged and show an actionable client error.
- Vietnamese or mixed Vietnamese-English learner speech must remain eligible for transcription without strict English-only filtering.

---

### Task 1: Declare Pipecat service and runtime configuration explicitly

**Files:**
- Modify: `voice/server/pyproject.toml`
- Modify: `voice/server/uv.lock`
- Modify: `voice/server/.env.example`
- Create: `voice/server/voice_config.py`
- Create: `tests/voice/test_voice_config.py`

**Interfaces:**
- Consumes: a mapping containing `SONIOX_API_KEY`, `SONIOX_VOICE_ID`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL`.
- Produces: `VoiceConfig.from_environment(environment: Mapping[str, str]) -> VoiceConfig`, `build_soniox_stt(config) -> SonioxSTTService`, and `build_soniox_tts(config) -> SonioxTTSService`.

- [ ] **Step 1: Write failing configuration tests**

```python
def test_voice_config_names_every_missing_live_variable():
    with pytest.raises(ValueError, match=(
        "SONIOX_API_KEY.*SONIOX_VOICE_ID.*OPENROUTER_API_KEY.*OPENROUTER_MODEL"
    )):
        VoiceConfig.from_environment({})


def test_soniox_services_use_pipecat_settings(monkeypatch):
    config = VoiceConfig.from_environment({
        "SONIOX_API_KEY": "secret",
        "SONIOX_VOICE_ID": "teacher-voice",
        "OPENROUTER_API_KEY": "openrouter-secret",
        "OPENROUTER_MODEL": "provider/model",
    })
    stt = build_soniox_stt(config)
    tts = build_soniox_tts(config)
    assert stt._settings.model == "stt-rt-v5"
    assert set(stt._settings.language_hints) == {Language.EN, Language.VI}
    assert stt._vad_force_turn_endpoint is True
    assert tts._settings.model == "tts-rt-v2"
    assert tts._settings.voice == "teacher-voice"
    assert tts._settings.language == Language.EN
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run --project voice/server pytest tests/voice/test_voice_config.py -q`

Expected: FAIL because `voice_config` does not exist.

- [ ] **Step 3: Implement immutable configuration and current Pipecat Settings factories**

```python
@dataclass(frozen=True)
class VoiceConfig:
    soniox_api_key: str
    soniox_voice_id: str
    openrouter_api_key: str
    openrouter_model: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]):
        names = (
            "SONIOX_API_KEY", "SONIOX_VOICE_ID",
            "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
        )
        missing = [name for name in names if not environment.get(name, "").strip()]
        if missing:
            raise ValueError("Missing required voice configuration: " + ", ".join(missing))
        return cls(*(environment[name].strip() for name in names))
```

Use `SonioxSTTService.Settings(model="stt-rt-v5", language_hints=[Language.EN, Language.VI], language_hints_strict=False, context="Grade 5 Unit 1 All about me: class, city, countryside, address, birthday, hobby, favourite animal, drawback, traffic jam")`, `vad_force_turn_endpoint=True`, and `SonioxTTSService.Settings(model="tts-rt-v2", voice=config.soniox_voice_id, language=Language.EN)`.

- [ ] **Step 4: Declare provider extras and example variables**

Change the dependency to `pipecat-ai[openrouter,soniox]==1.11.0`, regenerate `voice/server/uv.lock` with `uv lock --project voice/server`, and add empty `SONIOX_VOICE_ID`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL` entries to `.env.example`.

- [ ] **Step 5: Run focused tests and static checks**

Run:

```bash
uv run --project voice/server pytest tests/voice/test_voice_config.py -q
uv run --project voice/server ruff check voice/server/voice_config.py tests/voice/test_voice_config.py
uv run --project voice/server pyright voice/server/voice_config.py
```

Expected: PASS with no secret values in output.

### Task 2: Expose one shared teaching runtime composition seam

**Files:**
- Modify: `backend/src/luna_tutor/api/runtime.py`
- Create: `tests/backend/unit/api/test_runtime_components.py`
- Modify: `tests/backend/integration/api/test_runtime.py`

**Interfaces:**
- Produces: `RuntimeComponents(repository: SessionRepository, turn_service: object, client: OpenRouterClient | None)` and `build_runtime_components(environment: Mapping[str, str]) -> RuntimeComponents`.
- Consumes later: the voice worker uses the same repository and `TurnService` construction as FastAPI instead of duplicating provider or lesson setup.

- [ ] **Step 1: Write failing component-construction tests**

```python
def test_fixture_components_are_deterministic_and_have_repository(tmp_path):
    components = build_runtime_components({
        "ENV": "test",
        "TUTOR_LLM_MODE": "fixture",
        "TUTOR_DATABASE_PATH": str(tmp_path / "voice.sqlite3"),
    })
    assert isinstance(components.repository, SessionRepository)
    assert isinstance(components.turn_service, FixtureTurnService)
    assert components.client is None


def test_live_components_require_openrouter_configuration(tmp_path):
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        build_runtime_components({"TUTOR_DATABASE_PATH": str(tmp_path / "voice.sqlite3")})
```

- [ ] **Step 2: Run tests and verify RED**

Run: `uv run --project backend pytest tests/backend/unit/api/test_runtime_components.py -q`

Expected: FAIL because `RuntimeComponents` and `build_runtime_components` do not exist.

- [ ] **Step 3: Extract construction without changing HTTP behavior**

Move the repository, curriculum, OpenRouter client, evaluator, engine, teacher, and fixture selection into `build_runtime_components()`. Make `build_runtime_app()` call that function and retain the existing lifespan cleanup and route behavior.

- [ ] **Step 4: Prove the existing API behavior is unchanged**

Run:

```bash
uv run --project backend pytest tests/backend/unit/api/test_runtime_components.py tests/backend/integration -q
```

Expected: PASS; fixture mode remains guarded by `ENV=test`, and live mode refuses an empty OpenRouter key.

### Task 3: Integrate final Soniox transcripts, Flow nodes, and atomic persistence in one Pipecat worker

**Files:**
- Create: `voice/server/voice_teaching.py`
- Modify: `voice/server/text_flows.py`
- Modify: `voice/server/bot.py`
- Create: `tests/voice/test_voice_teaching.py`
- Create: `tests/voice/test_voice_bot.py`

**Interfaces:**
- Produces: `VoiceTeachingExchange`, `VoiceTeachingProcessor`, `VoiceCommitProcessor`, and `build_voice_worker(transport, runner_args, environment=os.environ)`.
- Consumes: `runner_args.body["session_id"]`, `RuntimeComponents`, `FlowManager`, final `TranscriptionFrame`, `BotStoppedSpeakingFrame`, and SQLite `commit_turn()`.

- [ ] **Step 1: Write a failing final-only/idempotency processor test**

```python
@pytest.mark.asyncio
async def test_only_final_transcript_plans_one_turn(tmp_path):
    exchange, processor, service = make_voice_exchange(tmp_path)
    await processor.process_frame(
        InterimTranscriptionFrame("I live", "u", "now", Language.EN),
        FrameDirection.DOWNSTREAM,
    )
    await processor.process_frame(
        TranscriptionFrame("I live in the city.", "u", "now", Language.EN),
        FrameDirection.DOWNSTREAM,
    )
    await processor.process_frame(
        TranscriptionFrame("I live in the city.", "u", "now", Language.EN),
        FrameDirection.DOWNSTREAM,
    )
    assert service.calls == ["I live in the city."]
    assert exchange.pending_completion is not None
```

- [ ] **Step 2: Write failing persistence and interruption tests**

```python
@pytest.mark.asyncio
async def test_completed_turn_commits_only_after_bot_stops(tmp_path):
    exchange, commit = make_pending_completion(tmp_path)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0
    await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 1


@pytest.mark.asyncio
async def test_interruption_discards_unspoken_pending_completion(tmp_path):
    exchange, commit = make_pending_completion(tmp_path)
    await commit.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0
```

- [ ] **Step 3: Run focused tests and verify RED**

Run: `uv run --project voice/server pytest tests/voice/test_voice_teaching.py -q`

Expected: FAIL because the voice teaching processors do not exist.

- [ ] **Step 4: Implement one session exchange and reuse bounded Flow behavior**

`VoiceTeachingProcessor` must ignore/pass interim frames for RTVI observation, derive a stable turn ID from the active user turn, load the latest stored session, short-circuit repository duplicates, call `TurnService.plan()`, update `flow.state["teacher_request"]`, and call `set_node_from_config(... respond_immediately=True)`. It must not pass the final transcript into the ordinary user aggregator and trigger a second response.

Refactor the bounded Teacher LLM from `text_flows.py` into a reusable class that emits teacher text and a completion marker but does not commit. Preserve all typed-flow tests.

- [ ] **Step 5: Implement ordered output completion**

`VoiceCommitProcessor`, placed after `transport.output()`, stores the authorized `CompletedTurn` marker, commits it on the matching downstream `BotStoppedSpeakingFrame`, discards it on `InterruptionFrame`, provider error, cancellation, or disconnect, and treats repository duplicate commits as idempotent.

- [ ] **Step 6: Replace the generic bot with the teaching worker**

Keep this order in `bot.py`:

```python
Pipeline([
    transport.input(),
    stt,
    voice_teaching,
    aggregators.user(),
    teacher_llm,
    tts,
    transport.output(),
    voice_commit,
    aggregators.assistant(),
])
```

Construct one `FlowManager(worker=worker, llm=teacher_llm, context_aggregator=aggregators, transport=transport, context_strategy=RESET)`. On `on_client_ready`, restore the persisted node silently and queue `TTSSpeakFrame(opening_message, append_to_context=True)` only when the session has no committed turns.

- [ ] **Step 7: Test request metadata, canonical pipeline order, and disconnect safety**

Add tests asserting missing/unknown `session_id` fails before provider connection, `runner_args.body["session_id"]` selects the correct stored session, the exact processor order above is constructed, and disconnect cancels the worker without committing a pending completion.

- [ ] **Step 8: Run all voice tests**

Run:

```bash
uv run --project voice/server pytest tests/voice -q
uv run --project voice/server ruff check voice/server tests/voice
uv run --project voice/server pyright voice/server
```

Expected: PASS, including the existing typed Pipecat Flow tests.

### Task 4: Add the official Pipecat React SmallWebRTC client to the existing Tutor UI

**Files:**
- Modify: `web/package.json`
- Modify: `web/package-lock.json`
- Create: `web/src/components/voice/PipecatVoiceProvider.tsx`
- Create: `web/src/components/voice/VoiceControls.tsx`
- Create: `web/src/components/voice/voice.module.css`
- Modify: `web/src/components/TutorShell.tsx`
- Create: `tests/web/pipecat-voice-provider.test.tsx`
- Create: `tests/web/voice-controls.test.tsx`
- Modify: `tests/web/tutor-shell.test.tsx`

**Interfaces:**
- Produces: `PipecatVoiceProvider({ sessionId, children })` and `VoiceControls`.
- Sends: `requestData: { session_id: sessionId }` inside SmallWebRTC offer parameters.
- Consumes: Pipecat transport state, conversation transcript/output events, mic state, and errors.

- [ ] **Step 1: Install only official Pipecat packages**

Run:

```bash
npm --prefix web install @pipecat-ai/client-js@1.13.1 @pipecat-ai/client-react@1.8.2 @pipecat-ai/small-webrtc-transport@1.10.8
```

Verify the installed TypeScript declaration for `webrtcRequestParams.requestData` before writing the provider. If the published type differs, follow that installed declaration and update the test API accordingly; do not cast to `any`.

- [ ] **Step 2: Write a failing provider lifecycle test**

```tsx
it('connects SmallWebRTC with the active REST session and disconnects on cleanup', async () => {
  const connect = vi.fn().mockResolvedValue(undefined);
  const disconnect = vi.fn().mockResolvedValue(undefined);
  mockPipecatClient({ connect, disconnect });
  const view = render(<PipecatVoiceProvider sessionId="session-7"><span>lesson</span></PipecatVoiceProvider>);
  await userEvent.click(screen.getByRole('button', { name: 'Start voice lesson' }));
  expect(connect).toHaveBeenCalledWith({
    webrtcRequestParams: {
      endpoint: 'http://localhost:7860/api/offer',
      requestData: { session_id: 'session-7' },
    },
  });
  view.unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});
```

- [ ] **Step 3: Run web test and verify RED**

Run: `npm --prefix web test -- pipecat-voice-provider.test.tsx`

Expected: FAIL because the provider does not exist.

- [ ] **Step 4: Implement a client-only provider with official APIs**

Create one lazily initialized `PipecatClient` with `SmallWebRTCTransport`, `enableMic: true`, `enableCam: false`, `disconnectOnBotDisconnect: true`, and official callbacks for transport state, bot readiness, user transcript, bot output, device errors, and backend errors. Wrap children with `PipecatClientProvider` and render `PipecatClientAudio` once.

Use `NEXT_PUBLIC_PIPECAT_URL ?? "http://localhost:7860"`; no provider credential may use a `NEXT_PUBLIC_` name.

- [ ] **Step 5: Write and implement mic/error/transcript UI tests**

Tests must prove the official Pipecat mic toggle is used, interim transcript is display-only, final spoken input is not submitted through `TutorApi.submitTurn`, device permission errors are actionable, and switching/new sessions disconnects the old voice client before connecting the new session.

Integrate voice controls into the existing `TutorShell` without restoring the deleted `/speaking` route or former custom speaking components. Keep the typed composer available as an explicit fallback, not as a duplicate submission path for voice turns.

- [ ] **Step 6: Run complete web verification**

Run:

```bash
npm --prefix web test
npm --prefix web run lint
npm --prefix web run build
```

Expected: all tests pass, lint has zero errors, and the Next.js production build exits 0.

### Task 5: Start the complete local stack and run deterministic plus real provider verification

**Files:**
- Modify: `scripts/run-local.sh`
- Modify: `voice/server/evals/starter_text.yaml`
- Modify: `voice/server/evals/starter_audio.yaml`
- Create: `docs/evaluation/pipecat-soniox-voice-report.md`
- Create: `tests/scripts/test_run_local.py`

**Interfaces:**
- Produces: one local command that starts REST backend on `8000`, Pipecat SmallWebRTC on `7860`, and Next.js on `3000`, all reading the root `.env` without printing secrets.

- [ ] **Step 1: Write a failing local-runner composition test**

```python
def test_local_runner_starts_and_cleans_up_all_three_processes():
    script = (ROOT / "scripts/run-local.sh").read_text()
    assert "voice_pid=$!" in script
    assert 'uv run --env-file "$project_root/.env" bot.py' in script
    assert 'NEXT_PUBLIC_PIPECAT_URL="${NEXT_PUBLIC_PIPECAT_URL:-http://localhost:7860}"' in script
    assert 'kill "${backend_pid:-}" "${voice_pid:-}" "${web_pid:-}"' in script
    assert 'wait -n "$backend_pid" "$voice_pid" "$web_pid"' in script
```

Run: `uv run --project backend pytest tests/scripts/test_run_local.py -q`

Expected: FAIL because the voice process and cleanup are not present.

- [ ] **Step 2: Implement three-process local startup**

Add the voice process:

```bash
(
  cd "$project_root/voice/server"
  uv run --env-file "$project_root/.env" bot.py \
    -t webrtc --host 127.0.0.1 --port 7860 \
    --allowed-origins http://localhost:3000
) &
voice_pid=$!
```

- [ ] **Step 3: Run deterministic full suites before provider calls**

Run:

```bash
uv run --project backend pytest tests/backend -q
uv run --project voice/server pytest tests/voice -q
npm --prefix web test
npm --prefix web run lint
npm --prefix web run build
```

Record exact pass/fail counts.

- [ ] **Step 4: Boot the real stack with durable redacted logs**

Start each process with stdout/stderr captured under a new temporary directory created by `mktemp -d`. Never echo the `.env` contents. Verify health endpoints and the SmallWebRTC offer route before running evals.

- [ ] **Step 5: Run Pipecat text eval against the real OpenRouter teaching path**

The scenario must cover greeting, a valid English answer, a Vietnamese clarification, an off-topic answer, and a retry-safe provider error boundary. Run with verbose output and save the run under `eval-runs/`.

- [ ] **Step 6: Run Pipecat audio eval through real Soniox STT and TTS**

Use synthesized learner audio but the bot's configured Soniox STT/TTS. Cover:

- clear English target phrase;
- Vietnamese-English code switching;
- a long answer with a natural pause;
- interruption/barge-in;
- pronunciation-sensitive Unit 1 vocabulary;
- disconnect/reconnect with the same REST session.

Save WAV recordings and inspect logs for traceback, `invalid_stream_state`, duplicated turn IDs, unexpected second LLM calls, and state-version conflicts.

- [ ] **Step 7: Perform one browser SmallWebRTC smoke session**

Open the local web app, start voice for a fresh session, grant mic permission, speak one English answer and one Vietnamese clarification, hear both Soniox teacher responses, mute/unmute, interrupt one response, reload, reconnect, and verify the transcript/history/state match the server. This is the required human-audible check that automated transcription cannot replace.

- [ ] **Step 8: Write the evidence report and run final verification**

Document commands, timestamps, Pipecat version, provider models, scenario results, recording paths, latency observations, and any unrun/manual-only checks in `docs/evaluation/pipecat-soniox-voice-report.md`. Redact request IDs or user data where appropriate.

Run the complete deterministic suites again after the real-test fixes. Do not claim completion unless both the fresh full-suite output and the real provider report support it.

- [ ] **Step 9: Commit only task-owned files**

Before each commit, run `git status --short` and stage explicit paths only. Do not stage the unrelated existing modifications or deletions. Suggested commits:

```bash
git commit -m "build: declare Pipecat Soniox voice configuration"
git commit -m "feat: connect teaching flows to Pipecat voice"
git commit -m "feat: add Pipecat React voice client"
git commit -m "test: verify real Soniox voice lesson"
```
