# Grade 3 Scripted Teaching Refactor Implementation Plan

> Implementation note (2026-09-24): the refactor was implemented through the new
> Grade 3 lesson modules and `voice/server/lesson_voice_bridge.py`. The task lists
> below record the original plan and old filenames; current implementation status
> and the remaining author-owned YAML/live Voice checks are in
> `docs/grade3_lesson_refactor_spec.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current multi-label teaching engine with the approved five-code Grade 3 scripted flow for Voice and Text, and remove Grade 5 product code and unused legacy paths.

**Architecture:** Curriculum items are validated as `practice`, `narration`, or `end`. A session-local controller owns the active item, four-failure counter, applied turn IDs, and transitions. Jev returns one `TurnEvaluation`; Pipecat owns Teacher conversation context and summary. Both input modes call the same controller. Voice delivery completion gates the next turn; Text completes delivery after display.

**Tech Stack:** Python/FastAPI/Pydantic, Pipecat 1.11/OpenRouter/Soniox, Next.js/React, pytest/Vitest.

**Spec:** `docs/grade3_lesson_refactor_spec.md` and `backend/src/luna_tutor/prompts/grade3_jev_rubric.yaml`.

## Global Constraints

- Apply only to Grade 3; delete Grade 5 curriculum, routes, prompts and now-unused code.
- Do not rewrite Grade 3 lesson content; the author edits `learner_goal` by hand. Reject an invalid new item rather than infer a goal from `accept`.
- `PASSED` emits the next authored `say` with no Teacher call. Every other code calls Teacher with one current developer rule.
- Teacher history is Pipecat context; session exit discards it. Voice and Text use the same logical transitions.
- Pipecat built-ins take precedence; custom code covers only the curriculum, decision, and delivery boundaries.
- Preserve pre-existing unrelated workspace changes.

## Review Focus

- A duplicate turn ID must not increment failures twice (Task 3).
- A later Jev response must not move a lesson while Luna is still speaking (Task 5).
- `PASSED_WITH_REPLY` must finish Teacher output before the next authored `say` (Tasks 3 and 5).
- An invalid or missing Jev choice must leave item/counter intact (Task 2).
- Old `accept` curriculum must fail with a useful validation location and must not be silently converted (Task 1).

---

### Task 1: Grade 3 curriculum contract

**Files:** `backend/src/luna_tutor/curriculum/lesson_script.py`, `backend/src/luna_tutor/curriculum/registry.py`, `tests/backend/unit/curriculum/test_lesson_script.py`.

**Interfaces:** `LessonScript.items: tuple[ScriptItem, ...]`; `ScriptItem.type`, `.say`, `.learner_goal`, `.image_url`; `load_lesson_script(path) -> LessonScript`.

- [ ] Write tests for one `practice`/`narration`/`end` sequence, missing `learner_goal`, forbidden goal on non-practice, and missing terminal `end`.
- [ ] Run focused tests and observe expected failures.
- [ ] Implement strict parser and registry loading without authoring curriculum text.
- [ ] Run focused tests and verify pass.

### Task 2: One-code Jev evaluation

**Files:** `backend/src/luna_tutor/llm/jev_evaluator.py`, `backend/src/luna_tutor/domain/evidence.py`, `backend/src/luna_tutor/prompts/grade3_jev_rubric.yaml`, `tests/backend/unit/llm/test_jev_evaluator.py`.

**Interfaces:** `TurnEvaluation` five-value enum; `JevEvaluator.evaluate_turn(learner_goal, learner_query, history, turn_id) -> TurnEvaluation`.

- [ ] Write tests for exact request `state`/`questions`, each valid code, malformed choice and provider failure.
- [ ] Run tests to confirm red.
- [ ] Implement the narrow Jev adapter and install the approved rubric as runtime YAML.
- [ ] Run tests to confirm green.

### Task 3: Shared scripted transition controller

**Files:** `backend/src/luna_tutor/teaching/scripted_lesson.py`, `backend/src/luna_tutor/teaching/descriptions.py`, `tests/backend/unit/teaching/test_scripted_lesson.py`.

**Interfaces:** session-local `ScriptedLessonSession.start()` and `.accept_turn(turn_id, query, evaluation)` return ordered output commands; `.delivery_finished()` activates the next practice or ends; `attempt_count` belongs to item index.

- [ ] Write transition tests for five codes, all four failures, duplicate turns, narration, end, and delivery gate.
- [ ] Run tests and observe red.
- [ ] Implement controller and approved Teacher descriptions; never concatenate multiple codes.
- [ ] Run tests and observe green.

### Task 4: Pipecat Teacher context

**Files:** `voice/server/bot.py`, `voice/server/text_flows.py`, `voice/server/voice_teaching.py`, new narrow context/rule helper if necessary, Pipecat tests under `tests/voice/`.

**Interfaces:** one per-session `LLMContext`, Pipecat `OpenRouterLLMService` with developer role, APPEND context strategy and default automatic summarization; spoken/displayed `say` and Teacher responses become assistant history.

- [ ] Write tests for live context roles, replacement of old developer instruction, history retention, and model request using the provider-supported developer role.
- [ ] Observe failing tests.
- [ ] Replace the bounded JSON Teacher adapter and RESET flows with Pipecat context/LLM service.
- [ ] Verify tests and source signatures against installed Pipecat.

### Task 5: Voice delivery and manual submit

**Files:** `voice/server/bot.py`, `voice/server/voice_teaching.py`, `voice/server/voice_rtvi.py`, `web/src/components/voice/PipecatVoiceProvider.tsx`, `web/src/components/voice/VoiceControls.tsx`, tests under `tests/voice/` and `tests/web/`.

**Interfaces:** client Mic begins capture, Gửi asks finalization, mic stays off until explicitly pressed; server rejects overlap and activates next item only on full TTS completion.

- [ ] Write tests for submit-only finalization, late transcript suppression, no interruption, mic lock, Teacher correction followed by authored `say`.
- [ ] Observe red.
- [ ] Implement using Pipecat's available turn and interruption APIs and minimal session state.
- [ ] Verify focused tests plus a real browser/voice probe when provider access exists.

### Task 6: Text parity and ephemeral session lifecycle

**Files:** `backend/src/luna_tutor/api/runtime.py`, `backend/src/luna_tutor/api/routes.py`, `voice/server/text_pipeline.py`, web session/turn consumers, tests under `tests/backend/integration/api/` and `tests/web/`.

**Interfaces:** Text query enters the same session controller and Pipecat Teacher context; no STT/TTS. Leaving removes state/context, re-entry starts at item zero.

- [ ] Write tests for Text five-code routing, history including `say`, exit reset, no storage replay, and Voice/Text equivalent lesson progression.
- [ ] Observe red.
- [ ] Replace persistent old teaching path while preserving API errors and UI display.
- [ ] Verify green.

### Task 7: Remove Grade 5 and dead implementation paths

**Files:** `curriculum/grade-05/`, `backend/src/luna_tutor/prompts/grades/grade-05/`, old engine/planner/evaluator/Teacher wrappers once unreferenced, Grade 5 web routes and references, old Grade 5 tests/docs where applicable.

**Interfaces:** only Grade 3 unit/lesson selection remains; no import of removed modules.

- [ ] Add assertions that registry/API/UI expose Grade 3 only.
- [ ] Observe red against existing Grade 5 registrations.
- [ ] Delete Grade 5 assets and unreferenced old code; update imports, docs, and tests for the new contract.
- [ ] Run Python test suites, Vitest, type checks, build, and an import/dead-reference scan; report any prerequisite curriculum edits separately.

## Verification

Run unit and integration suites from each service environment, web test/type/build commands, `rg` for Grade 5 runtime references and removed symbols, a sample synthetic Grade 3 lesson journey, and available Pipecat text/audio eval scenarios. Separate automated results from microphone/provider behavior that cannot be verified locally.
