# Unit 1 Web Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a local Next.js web application where Quang can complete all of Unit 1 from the beginning, resume saved sessions, inspect evidence and decisions, start a new session, and end Free Talk manually.

**Architecture:** FastAPI exposes session and turn endpoints backed by SQLite and the already-validated `TurnService`. Next.js App Router renders a chat client plus an experiment inspector; the browser never receives provider credentials or mutates lesson state locally. Each submitted turn is idempotent and persisted atomically with evidence, decision, teacher output, and next state.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLite (`sqlite3`), pytest, httpx TestClient; Next.js App Router, React, TypeScript, npm, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-19-luna-unit1-design.md`

**Prerequisite:** `docs/superpowers/plans/2026-09-19-unit1-core-evaluation.md` completed with an accepted Unit 1 baseline.

## Global Constraints

- Local single-user experiment; no login or multiple learner profiles.
- Student name is Quang and sessions always start at Warm-up.
- SQLite is the durable source of truth; the browser only renders server state.
- `OPENROUTER_API_KEY` remains server-side.
- A new session preserves old history and marks an unfinished prior session `abandoned` only after confirmation.
- Free Talk has no timer and ends only through the explicit End button.
- The UI inspector is experiment metadata and is never spoken as Luna dialogue.
- Responses are non-streaming in this phase.

## Review Focus

- Double-clicking Send must create one persisted turn and one state transition; Task 3 owns the idempotency test.
- Refreshing during an in-flight request must recover from SQLite without inventing a teacher message; Task 3 and Task 6 cover it.
- Starting a new session must preserve prior history and require confirmation for an active session; Task 4 and Task 6 cover it.
- End Free Talk must be rejected before the Free Talk stage and accepted during it; Task 4 covers it.
- Provider failure must show a retryable system error without incrementing attempts or changing state; Task 3 and Task 6 cover it.

---

## File Structure

```text
backend/src/luna_tutor/api/{app.py,schemas.py,routes.py}
backend/src/luna_tutor/storage/{schema.sql,sqlite.py,session_repository.py}
backend/tests/{unit/storage,integration/api}
web/
  src/app/{layout.tsx,page.tsx,globals.css}
  src/components/{TutorShell,ChatPanel,Composer,StateInspector,HistoryPanel,NewSessionButton}.tsx
  src/lib/{api.ts,types.ts}
  tests/
  e2e/
```

## Task 1: Add SQLite persistence with atomic turn commits

**Files:**
- Create: `backend/src/luna_tutor/storage/schema.sql`
- Create: `backend/src/luna_tutor/storage/sqlite.py`
- Create: `backend/src/luna_tutor/storage/session_repository.py`
- Test: `backend/tests/unit/storage/test_session_repository.py`

**Interfaces:**
- Produces: `SessionRepository.create_session()`, `get_session()`, `list_sessions()`, `commit_turn(expected_version, completed_turn)`, `abandon_session()`, and `finish_free_talk()`.

- [ ] **Step 1: Write failing repository tests**

```python
def test_commit_turn_is_atomic(repository, session):
    completed = completed_turn(state_version=session.state_version + 1)
    repository.commit_turn(session.id, session.state_version, completed)
    loaded = repository.get_session(session.id)
    assert loaded.state_version == session.state_version + 1
    assert loaded.turns[-1].turn_id == completed.turn_id


def test_duplicate_turn_id_returns_existing_turn(repository, session):
    first = repository.commit_turn(session.id, 0, completed_turn(turn_id="t1"))
    second = repository.commit_turn(session.id, 0, completed_turn(turn_id="t1"))
    assert second == first
    assert len(repository.get_session(session.id).turns) == 1
```

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/unit/storage -v`
Expected: FAIL because storage modules do not exist.

- [ ] **Step 3: Implement schema and repository**

Tables: `sessions`, `turns`, `objective_evidence`, `review_items`, `prompt_versions`. Use foreign keys, unique `(session_id, turn_id)`, JSON text for immutable request/decision snapshots, and `BEGIN IMMEDIATE` around version check plus inserts. Never store provider credentials or unredacted sensitive spans.

- [ ] **Step 4: Run tests and commit**

Run: `cd backend && uv run pytest tests/unit/storage -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor/storage backend/tests/unit/storage
git commit -m "feat: persist tutor sessions atomically"
```

## Task 2: Expose the FastAPI session contract

**Files:**
- Create: `backend/src/luna_tutor/api/app.py`
- Create: `backend/src/luna_tutor/api/schemas.py`
- Create: `backend/src/luna_tutor/api/routes.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/integration/api/test_sessions.py`

**Interfaces:**
- Produces REST endpoints:
  - `POST /api/sessions`
  - `GET /api/sessions`
  - `GET /api/sessions/{session_id}`
  - `POST /api/sessions/{session_id}/turns`
  - `POST /api/sessions/{session_id}/finish`
  - `POST /api/sessions/{session_id}/abandon`

- [ ] **Step 1: Write failing endpoint contract tests**

Assert a new session returns Warm-up state and Luna's generated/fallback greeting; list/get include history; missing session returns 404; request/response models reject unknown fields.

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/integration/api/test_sessions.py -v`
Expected: FAIL because the API app does not exist.

- [ ] **Step 3: Implement application factory and routes**

Use `create_app(settings, repository, turn_service)` for dependency injection. Permit CORS only from `http://localhost:3000`. Return a typed `SessionView` containing messages, current stage/objective, review queue, last evidence/decision, status, and state version.

- [ ] **Step 4: Run tests and commit**

Run: `cd backend && uv run pytest tests/integration/api/test_sessions.py -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor/api backend/pyproject.toml backend/tests/integration/api
git commit -m "feat: expose tutor session API"
```

## Task 3: Make turn submission idempotent and failure-safe

**Files:**
- Modify: `backend/src/luna_tutor/api/routes.py`
- Modify: `backend/src/luna_tutor/storage/session_repository.py`
- Test: `backend/tests/integration/api/test_turns.py`

**Interfaces:**
- `POST /turns` consumes `{turn_id, expected_state_version, learner_text}` and returns the committed turn plus session view.

- [ ] **Step 1: Write failing concurrency and failure tests**

Test duplicate `turn_id`, stale state version (409), two concurrent different turns against one version (one succeeds, one conflicts), evaluator timeout (503 retryable), invalid evaluator output, and Teacher fallback. Assert learner attempts and state remain unchanged for provider failures.

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/integration/api/test_turns.py -v`
Expected: FAIL on missing idempotency/version behavior.

- [ ] **Step 3: Implement transaction boundary**

Load state, process the turn without mutation, then commit only if `expected_state_version` still matches. Duplicate IDs return the prior result. Use stable error codes `STATE_CONFLICT`, `PROVIDER_UNAVAILABLE`, `INVALID_EVALUATION`, and `SESSION_NOT_ACTIVE`.

- [ ] **Step 4: Run tests and commit**

Run: `cd backend && uv run pytest tests/integration/api/test_turns.py -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor/api/routes.py backend/src/luna_tutor/storage/session_repository.py backend/tests/integration/api/test_turns.py
git commit -m "fix: make learner turns idempotent"
```

## Task 4: Implement session lifecycle and Free Talk ending

**Files:**
- Modify: `backend/src/luna_tutor/api/routes.py`
- Modify: `backend/src/luna_tutor/teaching/engine.py`
- Test: `backend/tests/integration/api/test_session_lifecycle.py`

**Interfaces:**
- Finish endpoint accepts `{expected_state_version}` and returns summary plus status `completed`.

- [ ] **Step 1: Write failing lifecycle tests**

Test abandon preserves turns; new session starts at Warm-up; finish before Free Talk returns 409 `NOT_IN_FREE_TALK`; finish during Free Talk creates an evidence-based summary, saves open review items, exits Emma role, and is idempotent.

- [ ] **Step 2: Verify failures**

Run: `cd backend && uv run pytest tests/integration/api/test_session_lifecycle.py -v`
Expected: FAIL because lifecycle rules are absent.

- [ ] **Step 3: Implement lifecycle operations**

Summary separates demonstrated, supported, needs-review, and not-yet-observed objectives. It never upgrades an open review item to mastered to close the session.

- [ ] **Step 4: Run tests and commit**

Run: `cd backend && uv run pytest tests/integration/api/test_session_lifecycle.py -v`
Expected: PASS.

```bash
git add backend/src/luna_tutor backend/tests/integration/api/test_session_lifecycle.py
git commit -m "feat: manage tutor session lifecycle"
```

## Task 5: Scaffold Next.js and implement the API client

**Files:**
- Create through scaffold: `web/`
- Create: `web/src/lib/types.ts`
- Create: `web/src/lib/api.ts`
- Test: `web/tests/api.test.ts`

**Interfaces:**
- Produces typed `TutorApi` methods matching Task 2 endpoints and an `ApiError` with stable server error code.

- [ ] **Step 1: Scaffold non-interactively**

Run: `npx create-next-app@latest web --ts --eslint --app --src-dir --use-npm --no-tailwind --import-alias "@/*"`
Expected: Next.js app created with App Router and TypeScript.

- [ ] **Step 2: Add Vitest and write failing client tests**

Test serialized turn IDs/state versions, typed error handling, abort behavior, and no credential fields in requests.

- [ ] **Step 3: Implement API types and client**

Use `NEXT_PUBLIC_TUTOR_API_URL` defaulting to `http://localhost:8000`. Only learner/session data is sent; provider credentials never appear in client configuration.

- [ ] **Step 4: Run tests and commit**

Run: `cd web && npm test -- --run`
Expected: PASS.

```bash
git add web
git commit -m "chore: scaffold tutor web client"
```

## Task 6: Build the chat, history, and inspector experience

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/app/globals.css`
- Create: `web/src/components/TutorShell.tsx`
- Create: `web/src/components/ChatPanel.tsx`
- Create: `web/src/components/Composer.tsx`
- Create: `web/src/components/StateInspector.tsx`
- Create: `web/src/components/HistoryPanel.tsx`
- Create: `web/src/components/NewSessionButton.tsx`
- Test: `web/tests/tutor-shell.test.tsx`

**Interfaces:**
- `TutorShell` owns selected session ID and server-fetched view; components emit user intent but never calculate next lesson state.

- [ ] **Step 1: Write failing component tests**

Test initial session creation, submit lock, retryable error, refresh/resume, history selection, confirmation before abandoning active session, inspector evidence/decision display, Free Talk End button visibility, and completed summary.

- [ ] **Step 2: Verify failures**

Run: `cd web && npm test -- --run`
Expected: FAIL because components do not exist.

- [ ] **Step 3: Implement the page**

Use a responsive two-column layout: chat as primary content; inspector/history as a secondary panel. On small screens make inspector/history collapsible. Show stage and objective labels in experiment chrome, never inside Luna's message bubble. Use accessible labels, focus return after send, live region for new Luna messages, and disabled controls while a request is active.

- [ ] **Step 4: Run component tests and commit**

Run: `cd web && npm test -- --run`
Expected: PASS.

```bash
git add web/src web/tests
git commit -m "feat: add Unit 1 experiment interface"
```

## Task 7: Add browser journeys and local run documentation

**Files:**
- Create: `web/playwright.config.ts`
- Create: `web/e2e/unit1-session.spec.ts`
- Create: `web/e2e/failure-recovery.spec.ts`
- Create: `README.md`
- Create: `scripts/run-local.sh`

**Interfaces:**
- Produces one command that launches backend and frontend and a browser suite against deterministic fake LLM fixtures.

- [ ] **Step 1: Write failing Playwright journeys**

Cover start from Warm-up, one recast without repeat demand, resume after reload, duplicate-submit prevention, provider retry, new session preserving old history, manual Free Talk finish, and evidence-based summary.

- [ ] **Step 2: Add deterministic test mode**

Backend `TUTOR_LLM_MODE=fixture` loads scenario responses from test-only fixtures and rejects this mode unless `ENV=test`. Do not put test branches in Teaching Engine.

- [ ] **Step 3: Add local runner and documentation**

`scripts/run-local.sh` starts FastAPI on 8000 and Next.js on 3000, forwards termination to both, and does not print secrets. README documents `uv sync`, `npm install`, `.env`, start, test, and report commands.

- [ ] **Step 4: Run full verification**

Run: `cd backend && uv run pytest -v`
Expected: PASS.

Run: `cd web && npm test -- --run && npm run lint && npm run build`
Expected: all exit 0.

Run: `cd web && npm run test:e2e`
Expected: all browser journeys pass.

- [ ] **Step 5: Commit**

```bash
git add README.md scripts web backend
git commit -m "test: verify complete Unit 1 web journey"
```
