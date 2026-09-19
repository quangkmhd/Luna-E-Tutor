# Unit 1 Core and Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate the provider-independent teaching core for Grade 5 Unit 1, including Gemini Evaluator, deterministic Teaching Engine, Gemini Teacher, all scripted scenario coverage, and a repeatable development/holdout report.

**Architecture:** A Python package owns curriculum, evidence schemas, deterministic state transitions, OpenRouter adapters, and scenario evaluation. Gemini is called twice per learner turn with separate prompts; all evidence is validated before the Teaching Engine sees it, and the Teacher receives only a bounded `TeacherTurnRequest`. This phase has no web UI and no Pipecat dependency.

**Tech Stack:** Python 3.12, uv, Pydantic 2, httpx, PyYAML, openpyxl, pytest, pytest-asyncio, OpenRouter `google/gemini-3.5-flash-lite`.

**Spec:** `docs/superpowers/specs/2026-09-19-luna-unit1-design.md`

## Global Constraints

- Use `OPENROUTER_API_KEY`; never expose or persist its value.
- Use model `google/gemini-3.5-flash-lite` for Evaluator and Teacher.
- Student name is fixed as Quang in the experimental system prompt.
- Warm-up only greets, checks emotion, and bridges into the lesson.
- Recast naturally; never require repetition after a correction.
- Maximum two attempts at one point before reducing difficulty or moving on.
- Privacy, attempt limits, state transitions, and lesson completion are deterministic code rules.
- A model/API/STT failure never counts as a learner failure and never advances the lesson.
- Free Talk may end with review items still open.
- Do not import or modify `tmp/jev-gemini-spike`; it is historical evidence only.

## Review Focus

- A Vietnamese answer can satisfy meaning while providing no English target-form evidence; Task 5 pins this in engine tests.
- A learner can express emotion and answer correctly in the same turn; Task 3 and Task 5 preserve both signals.
- A stale evaluator response must not mutate a newer state version; Task 6 rejects it.
- An apparent phone number must be redacted before provider calls and storage; Task 3 and Task 4 verify request capture.
- A valid alternative sentence must not be recast merely because it differs from the textbook pattern; Task 3, Task 5, and Task 7 cover it.

---

## File Structure

```text
backend/
  pyproject.toml
  .env.example
  src/luna_tutor/
    config.py
    curriculum/{models.py,loader.py,excel_importer.py}
    domain/{evidence.py,state.py,decisions.py,privacy.py}
    llm/{openrouter.py,evaluator.py,teacher.py}
    prompts/{evaluator.md,teacher-system.md}
    teaching/{engine.py,planner.py,turn_service.py}
    evals/{models.py,loader.py,runner.py,metrics.py,cli.py}
  tests/
    unit/
    integration/
curriculum/
  shared/{teacher.md,teaching-policy.yaml,speech-style.yaml,grade-profiles.yaml}
  grade-05/unit-01/...
evals/unit-01/
  coverage.yaml
  development/*.yaml
  holdout/*.yaml
  reports/.gitkeep
```

## Task 1: Initialize the repository and Python package

**Files:**
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/src/luna_tutor/__init__.py`
- Create: `backend/src/luna_tutor/config.py`
- Test: `backend/tests/unit/test_config.py`

**Interfaces:**
- Produces: `Settings.from_env() -> Settings` with `openrouter_api_key`, `openrouter_model`, `request_timeout_seconds`.

- [ ] **Step 1: Initialize Git because the workspace is currently not a repository**

Run: `git init -b main`
Expected: `.git/` exists and `git branch --show-current` prints `main`.

- [ ] **Step 2: Write the failing settings test**

```python
def test_settings_requires_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        Settings.from_env()


def test_settings_pins_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    settings = Settings.from_env()
    assert settings.openrouter_model == "google/gemini-3.5-flash-lite"
```

- [ ] **Step 3: Verify the test fails before implementation**

Run: `cd backend && uv run pytest tests/unit/test_config.py -v`
Expected: FAIL because `luna_tutor.config` does not exist.

- [ ] **Step 4: Create package metadata and minimal settings**

Use `backend/pyproject.toml` with package source under `src`, Python `>=3.12`, runtime dependencies `pydantic`, `httpx`, `PyYAML`, `openpyxl`, and dev dependencies `pytest`, `pytest-asyncio`, `respx`.

```python
@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_model: str = "google/gemini-3.5-flash-lite"
    request_timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise ValueError("OPENROUTER_API_KEY is required")
        return cls(openrouter_api_key=key)
```

`.env.example` lists `OPENROUTER_API_KEY=` and `SONIOX_API_KEY=` with no real values. `.gitignore` excludes `.env`, SQLite files, caches, recordings, and eval reports while retaining `.gitkeep`.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend && uv sync --dev && uv run pytest tests/unit/test_config.py -v`
Expected: PASS.

```bash
git add .gitignore backend/pyproject.toml backend/.env.example backend/src backend/tests
git commit -m "chore: initialize Luna teaching core"
```

## Task 2: Define curriculum schemas and Unit 1 content

**Files:**
- Create: `backend/src/luna_tutor/curriculum/models.py`
- Create: `backend/src/luna_tutor/curriculum/loader.py`
- Create: `backend/src/luna_tutor/curriculum/excel_importer.py`
- Create: `curriculum/shared/teacher.md`
- Create: `curriculum/shared/teaching-policy.yaml`
- Create: `curriculum/shared/speech-style.yaml`
- Create: `curriculum/shared/grade-profiles.yaml`
- Create: `curriculum/grade-05/unit-01/unit.yaml`
- Create: `curriculum/grade-05/unit-01/lesson-01/content.yaml`
- Create: `curriculum/grade-05/unit-01/lesson-02/content.yaml`
- Create: `curriculum/grade-05/unit-01/lesson-03/content.yaml`
- Create: `curriculum/grade-05/unit-01/level-02/content.yaml`
- Create: `curriculum/grade-05/unit-01/level-03/content.yaml`
- Create: `curriculum/grade-05/unit-01/free-talk/content.yaml`
- Test: `backend/tests/unit/curriculum/test_loader.py`
- Test: `backend/tests/unit/curriculum/test_excel_importer.py`

**Interfaces:**
- Produces: `load_unit(path: Path) -> UnitCurriculum` and `import_workbook(path: Path, grade: int, unit: int) -> ImportedUnit`.
- `UnitCurriculum.activities` is ordered and every activity has `id`, `kind`, `objective_ids`, `required`, `max_attempts`, and `completion_rule`.

- [ ] **Step 1: Write failing coverage and reference tests**

```python
def test_unit_01_has_expected_vocabulary(unit_01):
    assert unit_01.vocabulary_ids() == {
        "city", "class", "countryside", "dolphin", "pink", "sandwich",
        "table-tennis", "birthday", "hobby", "phone-number", "subject",
        "cottage", "calm", "crowded", "vehicles", "traffic-jam",
        "pavement", "drawback", "amusement-park",
    }


def test_all_activity_references_resolve(unit_01):
    unit_01.validate_references()
```

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/unit/curriculum -v`
Expected: FAIL because schemas and YAML do not exist.

- [ ] **Step 3: Implement strict Pydantic curriculum models**

Define `VocabularyItem`, `Pattern`, `Objective`, `Activity`, `Stage`, and `UnitCurriculum` with `extra="forbid"`. Validate unique IDs, references, required completion rules, maximum attempts of two for retryable activities, and at least one exit from every stage.

- [ ] **Step 4: Transcribe Unit 1 into YAML with source references**

Every item includes `source.file` and `source.section`. Lesson 3 references Lesson 1–2 objectives rather than duplicating them. Level 2 and Level 3 live at unit scope. Warm-up contains no vocabulary-teaching activity. Free Talk declares review selection rules and the Emma role.

- [ ] **Step 5: Implement and test the workbook importer**

The importer reads merged/blank cells by bounded Unit scope, stops forward-fill at the next Unit, and converts “review Lesson 1 + 2” into objective references. Compare the imported Grade 5 Unit 1 vocabulary/pattern IDs with the committed YAML.

- [ ] **Step 6: Run tests and commit**

Run: `cd backend && uv run pytest tests/unit/curriculum -v`
Expected: PASS with 19 vocabulary items and all references valid.

```bash
git add backend/src/luna_tutor/curriculum backend/tests/unit/curriculum curriculum
git commit -m "feat: model Grade 5 Unit 1 curriculum"
```

## Task 3: Define evidence, state, decision, and privacy contracts

**Files:**
- Create: `backend/src/luna_tutor/domain/evidence.py`
- Create: `backend/src/luna_tutor/domain/state.py`
- Create: `backend/src/luna_tutor/domain/decisions.py`
- Create: `backend/src/luna_tutor/domain/privacy.py`
- Test: `backend/tests/unit/domain/test_evidence.py`
- Test: `backend/tests/unit/domain/test_privacy.py`
- Test: `backend/tests/unit/domain/test_state.py`

**Interfaces:**
- Produces: `EvaluatorRequest`, `EvaluatorResult`, `ObjectiveEvidence`, `LessonState`, `TeachingDecision`, `TeacherTurnRequest`, `PlannedTurn`, `CompletedTurn`, `redact_sensitive_contact(text) -> RedactedText`.
- `PlannedTurn` contains sanitized learner text, evidence, decision, bounded Teacher request, and a proposed next state; it contains no teacher wording.
- `CompletedTurn` adds the validated Teacher utterance and the next state that may be persisted.

- [ ] **Step 1: Write failing schema tests**

```python
def test_evaluator_result_supports_answer_and_emotion():
    result = EvaluatorResult.model_validate({
        "turn_id": "t1", "state_version": 4, "response_kind": "answer",
        "emotional_signals": ["tired"],
        "objective_evidence": [{
            "objective_id": "pattern.live-in",
            "meaning_status": "satisfied",
            "target_form_status": "correct_target_form",
            "evidence_quote": "I live in the city",
            "recast_needed": False,
            "corrected_form": None,
        }],
        "needs_clarification": False,
        "ambiguity_reason": None,
    })
    assert result.emotional_signals == ["tired"]
    assert result.objective_evidence[0].meaning_status == "satisfied"
```

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/unit/domain -v`
Expected: FAIL because domain models do not exist.

- [ ] **Step 3: Implement enums and strict models**

Use exact enum values from spec section 4.1. Add validators: corrected form is required only when `recast_needed`; evidence quote must be non-empty unless status is `not_demonstrated`/`uncertain`; `needs_clarification` requires an ambiguity reason.

- [ ] **Step 4: Implement local privacy redaction**

Detect likely phone numbers before provider calls, replace with `[REDACTED_PHONE]`, and return a boolean safety event. Do not store the matched digits. Test spaces, dots, hyphens, country prefix, ordinary years, and classroom identifiers such as `5A`.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend && uv run pytest tests/unit/domain -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor/domain backend/tests/unit/domain
git commit -m "feat: define teaching turn contracts"
```

## Task 4: Implement the OpenRouter client and Gemini Evaluator

**Files:**
- Create: `backend/src/luna_tutor/llm/openrouter.py`
- Create: `backend/src/luna_tutor/llm/evaluator.py`
- Create: `backend/src/luna_tutor/prompts/evaluator.md`
- Test: `backend/tests/unit/llm/test_openrouter.py`
- Test: `backend/tests/unit/llm/test_evaluator.py`
- Test: `backend/tests/integration/test_evaluator_openrouter.py`

**Interfaces:**
- Produces: `OpenRouterClient.structured_chat(messages, schema, request_id) -> dict` and `GeminiEvaluator.evaluate(request: EvaluatorRequest) -> EvaluatorResult`.

- [ ] **Step 1: Write failing request-shape tests using respx**

Assert the request uses `/api/v1/chat/completions`, exact model, `temperature: 0`, strict `response_format.json_schema`, timeout, and `provider.require_parameters: true`. Capture the body and assert a raw phone number never occurs.

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/unit/llm/test_openrouter.py tests/unit/llm/test_evaluator.py -v`
Expected: FAIL because the client does not exist.

- [ ] **Step 3: Implement the client with bounded retry**

Retry only 429, 502, 503, and 504 once with jittered backoff; do not retry validation or 4xx authentication errors. Return typed exceptions containing status and request ID but never provider response bodies that may echo learner content.

- [ ] **Step 4: Implement the Evaluator prompt and validation**

The system prompt encodes the limits from spec 4.1 and few-shot examples for one-word answer, grammar error, valid alternative, Vietnamese answer, meaning question, wrong category, combined emotion+answer, and uncertain transcript. Validate `turn_id`, `state_version`, objective IDs, exact evidence substrings, and cross-field rules after parsing.

- [ ] **Step 5: Run unit and opt-in live tests**

Run: `cd backend && uv run pytest tests/unit/llm -v`
Expected: PASS without network.

Run: `cd backend && RUN_LIVE_LLM=1 uv run pytest tests/integration/test_evaluator_openrouter.py -v`
Expected: PASS when `.env` contains `OPENROUTER_API_KEY`; otherwise the test is skipped with a clear reason.

- [ ] **Step 6: Commit**

```bash
git add backend/src/luna_tutor/llm backend/src/luna_tutor/prompts backend/tests/unit/llm backend/tests/integration
git commit -m "feat: evaluate learner evidence with Gemini"
```

## Task 5: Implement the deterministic Teaching Engine

**Files:**
- Create: `backend/src/luna_tutor/teaching/engine.py`
- Test: `backend/tests/unit/teaching/test_engine_feedback.py`
- Test: `backend/tests/unit/teaching/test_engine_progression.py`
- Test: `backend/tests/unit/teaching/test_free_talk_review.py`

**Interfaces:**
- Produces: `TeachingEngine.decide(state: LessonState, evidence: EvaluatorResult, curriculum: UnitCurriculum) -> TeachingDecision`.
- Does not perform I/O or call an LLM.

- [ ] **Step 1: Write failing table-driven feedback tests**

Cover: correct target, valid alternative, one-word meaningful answer, grammar recast, wrong semantic category, asks meaning, asks Luna, off-topic, Vietnamese answer, emotional need plus correct answer, uncertain transcript, and privacy event.

- [ ] **Step 2: Write failing progression tests**

```python
def test_two_failed_attempts_moves_on_and_queues_review(engine, state):
    state.attempt_count = 1
    decision = engine.decide(state, no_evidence_result(), unit_01)
    assert decision.progression_action == "move_to_next_objective"
    assert decision.review_queue_add == [state.objective_id]
    assert decision.mastery_updates == []


def test_valid_alternative_is_success_without_recast(engine, state):
    decision = engine.decide(state, valid_alternative_result(), unit_01)
    assert decision.feedback_action == "acknowledge_and_continue"
    assert decision.review_queue_add == []
```

- [ ] **Step 3: Verify failures**

Run: `cd backend && uv run pytest tests/unit/teaching -v`
Expected: FAIL because `TeachingEngine` does not exist.

- [ ] **Step 4: Implement ordered policy evaluation**

Apply: stop/privacy → operational ambiguity → emotion/question → evidence → support limit → stage completion. Preserve positive evidence when emotion co-occurs. Never increment attempts for meaning questions or provider/STT failures. Distinguish activity completion from objective mastery.

- [ ] **Step 5: Implement contextual Free Talk review selection**

Rank pending items by contextual relevance, importance, required support, and recency. Select at most one item per turn. If the learner independently uses a queued target, record it and cancel any planned prompt for that target.

- [ ] **Step 6: Run tests and commit**

Run: `cd backend && uv run pytest tests/unit/teaching -v`
Expected: PASS with every hard-rule case passing.

```bash
git add backend/src/luna_tutor/teaching/engine.py backend/tests/unit/teaching
git commit -m "feat: add deterministic teaching decisions"
```

## Task 6: Implement Gemini Teacher and atomic turn orchestration

**Files:**
- Create: `backend/src/luna_tutor/llm/teacher.py`
- Create: `backend/src/luna_tutor/prompts/teacher-system.md`
- Create: `backend/src/luna_tutor/teaching/planner.py`
- Create: `backend/src/luna_tutor/teaching/turn_service.py`
- Test: `backend/tests/unit/llm/test_teacher.py`
- Test: `backend/tests/unit/teaching/test_turn_planner.py`
- Test: `backend/tests/unit/teaching/test_turn_service.py`

**Interfaces:**
- Produces: `TurnPlanner.plan(state, learner_text, turn_id) -> PlannedTurn`, `GeminiTeacher.respond(request: TeacherTurnRequest) -> TeacherUtterance`, and `TurnService.process(state, learner_text, turn_id) -> CompletedTurn`.
- `TurnPlanner` owns redact → evaluate → validate state version → decide → build bounded Teacher request → propose next state. It does not generate teacher wording or persist state.
- `TurnService` calls the planner, calls `GeminiTeacher`, validates the utterance, and returns an immutable `CompletedTurn` for the persistence layer.

- [ ] **Step 1: Write failing teacher boundary tests**

Assert that Teacher input contains `feedback_action`, `corrected_form`, `next_teaching_move`, and constraints, but does not contain progression tools or authority to mutate state. Validate output as `spoken_text` plus `delivery_intent`.

- [ ] **Step 2: Write failing planner and orchestration tests**

Test planner order: redact → evaluate → validate state version → decide → build request → propose next state. Then test service order: planner → teacher → validate utterance → complete turn. A stale evaluator result, provider timeout, or invalid teacher response must leave the original state unchanged and return no persistable `CompletedTurn`.

- [ ] **Step 3: Verify failures**

Run: `cd backend && uv run pytest tests/unit/llm/test_teacher.py tests/unit/teaching/test_turn_planner.py tests/unit/teaching/test_turn_service.py -v`
Expected: FAIL because Teacher, TurnPlanner, and TurnService do not exist.

- [ ] **Step 4: Implement Teacher prompt and fallback**

Teacher produces one short spoken turn without Markdown. It must respond to meaning first, perform only the requested recast, ask at most one question, and never announce an unapproved transition. If Teacher fails after the state decision, use a deterministic curriculum fallback and record `generation_mode="fallback"`.

- [ ] **Step 5: Implement the planner boundary and pure orchestration**

Make `TurnPlanner` the reusable boundary shared by web and voice. Keep all domain objects immutable while planning and generation run. Return a proposed next state from the planner and expose it for persistence only through a validated `CompletedTurn`; persistence is added in the web plan. Reject duplicate `turn_id` within the same state version.

- [ ] **Step 6: Run tests and commit**

Run: `cd backend && uv run pytest tests/unit/llm/test_teacher.py tests/unit/teaching/test_turn_planner.py tests/unit/teaching/test_turn_service.py -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor/llm/teacher.py backend/src/luna_tutor/prompts/teacher-system.md backend/src/luna_tutor/teaching/planner.py backend/src/luna_tutor/teaching/turn_service.py backend/tests
git commit -m "feat: orchestrate evaluated teaching turns"
```

## Task 7: Encode every Unit 1 scenario and coverage manifest

**Files:**
- Create: `backend/src/luna_tutor/evals/models.py`
- Create: `backend/src/luna_tutor/evals/loader.py`
- Create: `evals/unit-01/coverage.yaml`
- Create: `evals/unit-01/development/*.yaml`
- Create: `evals/unit-01/holdout/*.yaml`
- Test: `backend/tests/unit/evals/test_coverage.py`
- Test: `backend/tests/unit/evals/test_scenario_schema.py`

**Interfaces:**
- Produces: `load_scenarios(path) -> list[Scenario]` and `validate_coverage(manifest, scenarios, rules) -> CoverageResult`.

- [ ] **Step 1: Write failing manifest tests**

```python
def test_manifest_covers_all_numbered_dialogue_scenarios(manifest):
    assert manifest.numbered_scenarios == 40
    assert manifest.missing_source_refs == []


def test_manifest_covers_every_rule(manifest):
    assert manifest.covered_rule_ids == {f"R{i:02d}" for i in range(1, 21)}
```

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/unit/evals/test_coverage.py -v`
Expected: FAIL because no manifest exists.

- [ ] **Step 3: Define scenario schema**

Each scenario stores source line/heading, initial state, ordered learner turns, evaluator gold fields, allowed feedback actions, forbidden behaviors, expected state effects, and Teacher natural-language criteria. Multi-turn cases include state snapshots after each turn.

- [ ] **Step 4: Encode the complete source set**

Create scenarios for 10 Warm-up + 30 station cases, all named inline branches, four Free Talk branches, main flows, role transitions, ending, and combined/adversarial variants. Put prompt-tuning examples in development; create semantically different holdout paraphrases rather than copying development wording.

- [ ] **Step 5: Run coverage tests and commit**

Run: `cd backend && uv run pytest tests/unit/evals -v`
Expected: PASS with zero missing source references, rules, vocabulary objectives, patterns, and branches.

```bash
git add backend/src/luna_tutor/evals backend/tests/unit/evals evals/unit-01
git commit -m "test: encode complete Unit 1 scenario coverage"
```

## Task 8: Build the repeatable eval runner and metrics

**Files:**
- Create: `backend/src/luna_tutor/evals/runner.py`
- Create: `backend/src/luna_tutor/evals/metrics.py`
- Create: `backend/src/luna_tutor/evals/cli.py`
- Create: `evals/unit-01/reports/.gitkeep`
- Test: `backend/tests/unit/evals/test_metrics.py`
- Test: `backend/tests/integration/test_eval_runner.py`

**Interfaces:**
- Produces CLI: `uv run python -m luna_tutor.evals.cli run --set development --repetitions 3 --out <dir>`.
- Produces JSON and Markdown reports with field accuracy, hard-rule failures, stability, latency p50/p95, invalid responses, and per-scenario diffs.

- [ ] **Step 1: Write failing metric tests**

Test that hard-rule failure is reported independently from average accuracy, provider failures remain in the denominator, and instability is detected when repeated outputs differ.

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/unit/evals/test_metrics.py -v`
Expected: FAIL because metrics do not exist.

- [ ] **Step 3: Implement offline and live runner modes**

Offline mode re-scores recorded outputs without API calls. Live mode runs exact model/prompt versions, writes sanitized artifacts, and records prompt SHA-256 plus curriculum version. Do not overwrite prior reports.

- [ ] **Step 4: Implement acceptance gating**

Fail the command when any hard-rule case fails, schema validity is below 100%, coverage is incomplete, or holdout regresses relative to the accepted baseline. Report semantic field metrics without hiding provider errors.

- [ ] **Step 5: Run tests and commit**

Run: `cd backend && uv run pytest tests/unit/evals tests/integration/test_eval_runner.py -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor/evals backend/tests evals/unit-01/reports
git commit -m "feat: add repeatable Unit 1 evaluation runner"
```

## Task 9: Execute the improvement loop and freeze a reviewed baseline

**Files:**
- Modify: `backend/src/luna_tutor/prompts/evaluator.md`
- Modify: `backend/src/luna_tutor/prompts/teacher-system.md`
- Create: `evals/unit-01/baseline.json`
- Create: `docs/evaluation/unit-01-report.md`

**Interfaces:**
- Produces: accepted prompt hashes and a report that gates the web plan.

- [ ] **Step 1: Run development three times**

Run: `cd backend && uv run python -m luna_tutor.evals.cli run --set development --repetitions 3 --out ../evals/unit-01/reports`
Expected: a timestamped report; no raw phone number or API key in artifacts.

- [ ] **Step 2: Classify every failure by owner**

Record each failure as curriculum label, Evaluator prompt/schema, Teaching Engine, Teacher prompt, provider error, or scenario ambiguity. Correct scenario labels only with an explicit rationale linked to the source document.

- [ ] **Step 3: Improve one owner at a time with TDD**

For engine defects, add a failing unit test before code. For prompt defects, add/adjust a development example, rerun the affected cases, then rerun all development cases. Do not inspect holdout outputs while tuning.

- [ ] **Step 4: Run holdout once after development gates pass**

Run: `cd backend && uv run python -m luna_tutor.evals.cli run --set holdout --repetitions 3 --out ../evals/unit-01/reports`
Expected: 100% schema validity, zero hard-rule failures, full coverage, and no regression relative to the accepted baseline. Any miss is documented rather than hidden by an average.

- [ ] **Step 5: Perform human review of Teacher samples**

Review at least one output from every response class and every stage for age fit, naturalness, English/Vietnamese use, recast behavior, and absence of forced repetition. Record pass/fail and revision notes in `docs/evaluation/unit-01-report.md`.

- [ ] **Step 6: Freeze baseline and run the complete suite**

Run: `cd backend && uv run pytest -v`
Expected: all unit/integration tests pass; live tests skip unless enabled.

Run: `cd backend && uv run python -m luna_tutor.evals.cli verify-baseline ../evals/unit-01/baseline.json`
Expected: PASS.

```bash
git add backend curriculum evals/unit-01/baseline.json docs/evaluation/unit-01-report.md
git commit -m "test: establish reviewed Unit 1 baseline"
```
