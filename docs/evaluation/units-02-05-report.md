# Grade 5 Units 2–5 verification — 2026-09-20

## Source and scenario audit

All four curricula load through the production loader and match the reviewed
workbook cells. The final counts are:

| Unit | Title | Vocabulary | Patterns | Numbered scenarios |
|---|---|---:|---:|---:|
| 2 | Our homes | 19 | 7 | 10 |
| 3 | My foreign friends | 20 | 7 | 11 |
| 4 | Our free-time activities | 22 | 7 | 12 |
| 5 | My future job | 23 | 7 | 13 |

`validate_coverage` reported no missing source references, branches, or
objectives for any Unit. A cross-Unit check found no objective ID belonging to
another Unit in any of the four scenario sets.

## Automated regression evidence

- Backend: `466 passed, 1 skipped`.
- Voice: `28 passed`; one old integration test was updated to supply the now
  required explicit `unit_id` when creating a session.
- Web component tests: `37 passed`.
- Web lint: passed.
- Next.js production build: passed.
- Chromium Playwright: `6 passed`, including Unit 2 selection, persistence,
  and absence of Unit 1 content.
- `git diff --check`: passed.
- Ruff on every Python file changed for Units 2–5: passed. The pre-existing
  repository-wide Ruff command still reports 70 unrelated legacy findings;
  this run did not mechanically rewrite those out-of-scope files.

## Provider-backed evaluator reports

The generalized CLI was run with one development repetition per Unit and the
available OpenRouter credential. These reports evaluate classification only;
they do not claim Teaching Engine or live voice acceptance.

| Unit | Records | Field accuracy | Schema validity | Provider failures | Invalid responses | Structural gate |
|---|---:|---:|---:|---:|---:|---|
| 2 | 10 | 0.800 | 0.900 | 0 | 1 | not accepted |
| 3 | 11 | 0.909 | 1.000 | 0 | 0 | accepted |
| 4 | 12 | 0.833 | 1.000 | 0 | 0 | accepted |
| 5 | 13 | 0.615 | 1.000 | 0 | 0 | accepted |

Unit 2's gate failure is retained as evidence rather than hidden: one model
response did not validate against the evaluator schema. Unit 5's lower semantic
accuracy also remains visible even though its structural gate passed.

## Native browser and persistence evidence

A real Chrome tab was used against fixture-mode backend and web processes from
this worktree. The UI displayed all five choices. Units 2, 3, 4, and 5 each
rendered the correct `English Tutor · Unit N` label and title. Safe warm-up
turns were submitted for Units 3–5. `GET /api/sessions` then returned:

- `grade05.unit02`, `Our homes`, `warm-up.feelings`, version 0;
- `grade05.unit03`, `My foreign friends`, `warm-up.feelings`, version 1;
- `grade05.unit04`, `Our free-time activities`, `warm-up.feelings`, version 1;
- `grade05.unit05`, `My future job`, `warm-up.feelings`, version 1.

The Unit 2 vertical slice had already submitted and persisted a turn in its
dedicated smoke run; this final pass only reconfirmed selection and metadata.

## Live voice status

Voice routing is covered by the 28 passing tests, including selection from the
persisted session before STT/TTS construction and rejection of unknown Units.
Both Soniox and OpenRouter credentials were present during the final run.

A worktree voice server was started successfully on port 7870 because ports
7860–7863 were already occupied by other local processes. The web UI created a
Unit 5 session but remained at `Connecting`; the worktree server received no
`POST /start` (only a manual CORS preflight used to verify reachability).
Therefore this report does not claim a successful microphone, STT, LLM, or TTS
round trip. The worktree backend, web, and port-7870 voice processes were
stopped after the attempt; unrelated pre-existing processes were left intact.
