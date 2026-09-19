# Unit 1 Pipecat Voice Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a locally testable SmallWebRTC voice tutor using Pipecat 1.11-compatible APIs, Soniox STT/TTS, OpenRouter Gemini, Pipecat Flows, and the validated Unit 1 teaching core.

**Architecture:** The Pipecat CLI scaffold supplies the canonical cascade pipeline and eval transport. A voice adapter converts final Soniox transcripts into `TurnPlanner` input, applies deterministic Teaching Engine decisions, drives activity-level Flow nodes, asks the Pipecat OpenRouter LLM to realize a bounded Teacher request, renders verified Soniox delivery tags, and commits progress only for output that reaches the audio path. SQLite remains the durable state source.

**Tech Stack:** Pipecat AI 1.11-compatible scaffold, Pipecat Flows, SmallWebRTC, Pipecat eval transport, Soniox STT/TTS, OpenRouter LLM, Python 3.12, pytest.

**Spec:** `docs/superpowers/specs/2026-09-19-luna-unit1-design.md`

**Prerequisites:** Core baseline and web plans complete. `SONIOX_API_KEY` exists. Live TTS additionally requires a user-selected Soniox teacher voice in `SONIOX_TTS_VOICE`; do not invent or silently choose a voice ID.

## Global Constraints

- Run Pipecat CLI documentation/example search before each unfamiliar API and run `check-deprecation` for copied symbols.
- Scaffold; do not hand-write Pipecat boilerplate.
- Cascade order remains transport input → Soniox STT → user context/planner → OpenRouter teacher LLM → Soniox TTS → transport output → assistant context.
- Flow nodes represent teaching stages/activities, not individual vocabulary words.
- Teaching Engine alone authorizes node transitions; the LLM cannot call a free-form “complete lesson” edge.
- A word/model is marked spoken only after its audio output completes; interruption clears unspoken pending effects.
- STT/transport/provider failures do not increment learner attempts.
- Use only Soniox delivery tags verified against current official documentation and live audio.

## Review Focus

- Barge-in during a modeled word must not mark the word as taught; Task 4 adds an audio lifecycle test.
- An interim Soniox transcript must never trigger evaluation; Task 3 accepts final transcript frames only.
- Reconnecting a session must reconstruct the correct Flow node from SQLite; Task 2 covers restore.
- A stage transition must produce one Teacher response, not one from the old node plus another from the new node; Task 3 pins this.
- Delivery tags must not be spoken literally or distort target vocabulary; Task 5 covers tag filtering and audio review.

---

## File Structure

```text
voice/
  server/
    bot.py                 # generated then minimally modified
    flow_nodes.py
    teaching_processor.py
    turn_planner_adapter.py
    speech_renderer.py
    progress_processor.py
    evals/
  tests/
```

## Task 1: Scaffold the Pipecat voice app and prove the starter loop

**Files:**
- Create through scaffold: `voice/`
- Modify generated: `voice/server/.env.example`
- Preserve generated: `voice/server/bot.py`, `voice/server/evals/`, `voice/server/pyproject.toml`

**Interfaces:**
- Produces runnable `async bot(runner_args)` entry point with `smallwebrtc` and `eval` transports.

- [ ] **Step 1: Confirm current options and API status**

Run:

```bash
pipecat init --list-options
pipecat context-hub status
pipecat context-hub search-docs "SmallWebRTC eval transport Pipecat Flows cascade"
pipecat context-hub check-deprecation PipelineWorker
pipecat context-hub search-api "SonioxSTTService SonioxTTSService OpenRouterLLMService"
```

Expected: options include `smallwebrtc`, `soniox_stt`, `openrouter_llm`, `soniox_tts`; Context Hub indexes the installed/release API without deprecation blockers.

- [ ] **Step 2: Dry-run the exact scaffold**

Run:

```bash
pipecat init voice --transport smallwebrtc --mode cascade --stt soniox_stt --llm openrouter_llm --tts soniox_tts --eval --no-deploy-to-cloud --client-framework none --dry-run
```

Expected: resolved JSON contains those four services/transports and no cloud deployment.

- [ ] **Step 3: Scaffold and install**

Run the same command without `--dry-run`, then `cd voice/server && uv sync`.

Add `SONIOX_API_KEY`, `OPENROUTER_API_KEY`, and `SONIOX_TTS_VOICE` to generated `.env.example` without values. Add the core package as an editable/path dependency using uv so voice code imports `luna_tutor` rather than copying it.

- [ ] **Step 4: Run generated starter evals before modification**

Start: `cd voice/server && uv run bot.py -t eval 2>&1 | tee /tmp/luna-pipecat-starter.log`

In a second terminal run the generated starter text scenario and audio scenario exactly as documented in `voice/server/evals/README.md` or generated README.

Expected: both starter scenarios pass and `/tmp/luna-pipecat-starter.log` contains no traceback.

- [ ] **Step 5: Commit the untouched baseline**

```bash
git add voice
git commit -m "chore: scaffold Pipecat Soniox voice app"
```

## Task 2: Define activity-level Pipecat Flow nodes

**Files:**
- Create: `voice/server/flow_nodes.py`
- Test: `voice/tests/test_flow_nodes.py`

**Interfaces:**
- Produces `build_node(stage_id: str, state: LessonState, curriculum: UnitCurriculum) -> NodeConfig` and `restore_initial_node(session) -> NodeConfig`.

- [ ] **Step 1: Search and verify Flow APIs**

Run:

```bash
pipecat context-hub search-docs "Pipecat Flows NodeConfig state placeholders context strategy manual transition"
pipecat context-hub search-api "FlowManager initialize set_node_from_config NodeConfig"
pipecat context-hub check-deprecation FlowManager
```

Expected: `FlowManager.initialize(initial_node)` and `set_node_from_config(node_config)` are current.

- [ ] **Step 2: Write failing node tests**

Assert stage IDs map to `warmup`, `lesson_01_vocabulary`, `lesson_01_pattern`, `lesson_02_vocabulary`, `lesson_02_pattern`, `lesson_03_review`, `level_02`, `level_03`, `free_talk`, and `summary`. Assert objective data appears through rendered state/task messages while no node grants the LLM authority to mark completion.

- [ ] **Step 3: Verify failures**

Run: `cd voice/server && uv run pytest ../tests/test_flow_nodes.py -v`
Expected: FAIL because node factory does not exist.

- [ ] **Step 4: Implement nodes and restore**

Use append context within a short activity and reset-plus-structured-summary across major stages to keep prompts bounded. Node functions may answer/record operational events; stage transition occurs only through application code after Teaching Engine decision.

- [ ] **Step 5: Run tests and commit**

Run: `cd voice/server && uv run pytest ../tests/test_flow_nodes.py -v`
Expected: PASS.

```bash
git add voice/server/flow_nodes.py voice/tests/test_flow_nodes.py
git commit -m "feat: map Unit 1 stages to Pipecat Flows"
```

## Task 3: Adapt final transcripts to planned Teacher turns

**Files:**
- Create: `voice/server/turn_planner_adapter.py`
- Create: `voice/server/teaching_processor.py`
- Modify: `voice/server/bot.py`
- Test: `voice/tests/test_teaching_processor.py`

**Interfaces:**
- Consumes core `TurnPlanner.plan(...) -> PlannedTurn` before Teacher generation.
- Produces ordered context/frame updates for the Pipecat OpenRouter LLM and optional manual Flow node transition.

- [ ] **Step 1: Verify the core planner contract and write failing adapter tests**

Import the core `TurnPlanner` and `PlannedTurn` contract established in the core plan. Assert the voice adapter passes the final learner transcript and current state version to that port, then serializes only the bounded `TeacherTurnRequest` for Pipecat's LLM. Web continues to use `TurnService`; voice uses the same planner before Pipecat generates teacher wording.

- [ ] **Step 2: Write failing processor tests**

Feed interim and final transcription frames. Assert interim frames do nothing; final frame produces exactly one plan. Assert `stay_in_current_node` updates Teacher context without transition; `move_to_next_stage` calls one manual transition and still produces exactly one response.

- [ ] **Step 3: Verify failures**

Run: `cd voice/server && uv run pytest ../tests/test_teaching_processor.py -v`
Expected: FAIL because adapter/processor do not exist.

- [ ] **Step 4: Implement the processor using current frame APIs**

Before writing imports, query `search_api`/`check_deprecation` for each frame and context-update symbol. Push changes as frames in pipeline order; do not mutate LLM context out of band. Provide the Teacher system prompt plus serialized `TeacherTurnRequest`, with the voice-safe instruction to emit no Markdown.

- [ ] **Step 5: Modify only the generated pipeline seams**

Keep scaffolded service constructors, transport params, runner contract, and connection handlers. Insert the teaching processor/context adapter at the correct transcript-to-LLM point; keep assistant aggregation after transport output.

- [ ] **Step 6: Run tests and commit**

Run: `cd voice/server && uv run pytest ../tests/test_teaching_processor.py -v`
Expected: PASS.

```bash
git add voice/server voice/tests/test_teaching_processor.py
git commit -m "feat: plan deterministic voice teaching turns"
```

## Task 4: Commit progress only after spoken output lifecycle events

**Files:**
- Create: `voice/server/progress_processor.py`
- Test: `voice/tests/test_progress_processor.py`

**Interfaces:**
- Produces pending/committed turn lifecycle keyed by `turn_id`; persists only after assistant audio completion and discards unspoken effects on interruption/cancel.

- [ ] **Step 1: Verify current output/interruption frames**

Use Context Hub `search_api` and `check_deprecation` for TTS start/stop, assistant speaking, interruption, cancel, and end frames before imports.

- [ ] **Step 2: Write failing lifecycle tests**

Cover normal TTS completion, barge-in before target word, partial output, disconnect, duplicate completion, and reconnect restore. Assert no modeled-word or activity completion is recorded for content not spoken.

- [ ] **Step 3: Verify failures**

Run: `cd voice/server && uv run pytest ../tests/test_progress_processor.py -v`
Expected: FAIL because progress processor does not exist.

- [ ] **Step 4: Implement pending state and persistence**

Persist learner evidence immediately after validated evaluation, but delay effects that claim Luna taught/spoke content until the matching output lifecycle confirms completion. Use repository state-version checks for both phases.

- [ ] **Step 5: Run tests and commit**

Run: `cd voice/server && uv run pytest ../tests/test_progress_processor.py -v`
Expected: PASS.

```bash
git add voice/server/progress_processor.py voice/tests/test_progress_processor.py
git commit -m "feat: align progress with spoken audio"
```

## Task 5: Render and verify Soniox teacher delivery

**Files:**
- Create: `voice/server/speech_renderer.py`
- Modify: `voice/server/bot.py`
- Test: `voice/tests/test_speech_renderer.py`
- Create: `docs/evaluation/soniox-voice-report.md`

**Interfaces:**
- Produces `render_for_soniox(TeacherUtterance) -> str` using an allow-list of verified Soniox controls.

- [ ] **Step 1: Refresh official Soniox documentation**

Use Context7 and official Soniox emotion/tone/audio-tag pages. Record supported tags, escaping rules, and model restrictions in code comments with source URLs. Inspect current `SonioxTTSSettings` with Context Hub; use `settings=` rather than deprecated input params.

- [ ] **Step 2: Write failing renderer tests**

Test warm, encouraging, reassuring, gentle-roleplay, and neutral instructional intents; unknown/user-supplied tags are escaped or removed; target words remain unchanged; tags never appear in the plain transcript used for eval.

- [ ] **Step 3: Verify failures and implement**

Run: `cd voice/server && uv run pytest ../tests/test_speech_renderer.py -v`
Expected first FAIL, then PASS after an allow-list renderer is added.

- [ ] **Step 4: Require explicit live voice configuration**

Read `SONIOX_TTS_VOICE` from environment and fail startup with its exact name when absent for live transports. Do not pick `Adrian` or any provider voice from examples. Eval text mode remains runnable without live TTS credentials.

- [ ] **Step 5: Perform recorded audio review**

Record representative word modeling, recast, success, reassurance, Emma role, Vietnamese support, and long target phrases. Document intelligibility, tag handling, word distortion, latency, and chosen voice in `soniox-voice-report.md`; revise mappings until mandatory samples pass human review.

- [ ] **Step 6: Commit**

```bash
git add voice/server/speech_renderer.py voice/server/bot.py voice/tests/test_speech_renderer.py docs/evaluation/soniox-voice-report.md
git commit -m "feat: render verified Soniox teacher delivery"
```

## Task 6: Port Unit 1 coverage into Pipecat behavioral evals

**Files:**
- Modify/Create: `voice/server/evals/unit1-text/*.yaml`
- Modify/Create: `voice/server/evals/unit1-audio/*.yaml`
- Create: `voice/server/evals/suite.yaml`
- Test: `voice/tests/test_eval_manifest.py`

**Interfaces:**
- Produces Pipecat text scenarios for decision/content behavior and audio scenarios for STT, VAD, TTS, interruption, and pronunciation-sensitive paths.

- [ ] **Step 1: Copy generated starter scenario structure**

Do not invent YAML keys. Use scaffolded starters and current Pipecat Evals docs for schema. Add a manifest mapping every core scenario ID to text/audio/not-applicable coverage.

- [ ] **Step 2: Write failing manifest test**

Assert all 40 numbered scenarios, named branches, R01–R20, and audio-only behaviors have a mapped Pipecat scenario or explicit not-applicable reason.

- [ ] **Step 3: Implement text scenarios first**

Drive the running bot in text mode for evaluator/engine/Teacher behavior, multi-turn context, no forced repetition, and Flow transitions. Use deterministic assertions for events/function calls and judge criteria only for meaning/naturalness.

- [ ] **Step 4: Add focused audio scenarios**

Use local eval TTS/transcription for turn-taking and then live Soniox smoke scenarios for names, numbers, bilingual phrases, target vocabulary, interruption, and delivery tags. Save recordings for human review.

- [ ] **Step 5: Run the suite**

Start: `cd voice/server && uv run bot.py -t eval 2>&1 | tee /tmp/luna-pipecat-unit1.log`

Run: `cd voice/server && uv run pipecat eval suite evals/suite.yaml --logs-dir eval-runs`

Expected: exit 0, zero hard-rule failures, and no traceback in the durable bot log.

- [ ] **Step 6: Commit**

```bash
git add voice/server/evals voice/tests/test_eval_manifest.py
git commit -m "test: verify Unit 1 through Pipecat evals"
```

## Task 7: Run end-to-end local voice acceptance

**Files:**
- Create: `docs/evaluation/unit-01-voice-acceptance.md`
- Modify: `README.md`

**Interfaces:**
- Produces repeatable local run instructions and final evidence report.

- [ ] **Step 1: Run full automated verification**

Run backend tests, web tests/build, voice pytest, core eval baseline verification, and Pipecat eval suite. Record exact commands, versions, pass/fail counts, and links to artifacts.

- [ ] **Step 2: Exercise SmallWebRTC manually**

Run `cd voice/server && uv run bot.py -t smallwebrtc`, open Pipecat Prebuilt, and complete representative paths: happy path, short answer, Vietnamese answer, recast, meaning question, silence, tired learner, privacy, barge-in, Level 3, Free Talk review, manual end, reconnect/resume.

- [ ] **Step 3: Audit the resulting state**

Compare transcript, evaluator evidence, engine decision, Flow node, actually spoken audio, and SQLite state for every sampled turn. Any mismatch becomes a failing regression test before the fix.

- [ ] **Step 4: Write acceptance report and final verification**

Report each R01–R20 as pass/fail/not-run/not-applicable, all known limitations, latency p50/p95, provider/model/voice versions, and audio review findings. Do not call the system complete while a mandatory check is failed or unrun.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/evaluation/unit-01-voice-acceptance.md
git commit -m "docs: record Unit 1 voice acceptance"
```
