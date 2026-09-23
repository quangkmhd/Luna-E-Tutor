# Jev-only Evaluator

## Status

Design approved in conversation: use Jev for every Evaluator path, keep Gemini Teacher for spoken replies, and remove the Gemini-versus-Jev review workbench.

## Goal

Make Jev the only evaluator in learner runtime and evaluation tooling. Remove the Gemini Evaluator implementation and its grade-specific evaluator prompts when no supported path uses them. Keep Gemini Teacher and all grade-specific Teacher prompts unchanged.

## Current behavior

- `TUTOR_EVALUATOR_MODEL` selects Gemini or Jev for normal lesson turns. The current `.env` selects Jev.
- Runtime composition also constructs both evaluator paths for `/api/review/{session_id}`. The `/review` workbench runs them in parallel and compares their evidence, decisions, and Teacher replies.
- The `luna-eval` CLI constructs `GeminiEvaluator` directly, so batch reports do not represent the current Jev evaluator.
- `GeminiEvaluator` loads shared and grade-specific evaluator prompts. Jev uses the shared decision rubric in `jev-evaluator.yaml`; Grade 3 scripted lessons also pass their authored acceptance criteria in each request.
- Gemini Teacher is a separate generative component. It produces spoken replies and is not replaceable by Jev's decision labels.

## Approved design

### Runtime

- Construct Jev as the only Evaluator for every supported Unit and Grade 3 scripted lesson.
- Remove the `TUTOR_EVALUATOR_MODEL` selector and Gemini Evaluator branch from the runtime composition root.
- Preserve `GeminiTeacher`, its model setting, and Grade 3/Grade 5 Teacher prompt loading.
- Preserve Grade 3's `ScriptedLessonService`; accepted authored lines continue to bypass Teacher generation, while generated support responses use the existing Gemini Teacher.

### Evaluation tools and review UI

- Change `luna-eval` to use `JevEvaluator` so benchmark results measure the production evaluator.
- Remove the evaluator A/B comparison service, `/api/review/{session_id}` endpoint, ReviewWorkbench page, and their comparison-only schemas/types/API client methods/tests. The user approved removing this workbench because its sole purpose is comparing Gemini Evaluator with Jev.
- Keep curriculum review queues, lesson summaries, and other learner progress review behavior; those do not depend on evaluator comparison.

### Obsolete configuration and prompts

- Remove `TUTOR_EVALUATOR_MODEL` from `.env`, `.env.example`, and active deployment instructions. Do not modify API keys or the Teacher model setting.
- Remove `GeminiEvaluator` and the evaluator-only system prompts (`shared/evaluator.yaml`, `grades/grade-03/evaluator.yaml`, and `grades/grade-05/evaluator.yaml`) after replacing their active call sites.
- Retain `JevEvaluator`, `jev-evaluator.yaml`, shared evidence contracts, and the Teacher-only prompt loader behavior.
- Update active documentation that presents Gemini Evaluator as a supported runtime or benchmark option. Historical plans and evaluation reports may continue to describe the earlier implementation.

## Scope boundaries

- No change to Teacher model/provider, Teacher prompts, TeachingEngine rules, Jev schema, curriculum acceptance criteria, or Grade 3 authored scripts.
- No attempt to make Jev generate Teacher prose.
- Removing `/review` means users lose the Gemini-versus-Jev A/B comparison page and endpoint; the approved intent is to remove this now-obsolete feature, not convert it into a new single-model debugger.

## Completion criteria

- Runtime has one evaluator implementation: Jev. Grade 3 and Grade 5 both route through it.
- `luna-eval` measures Jev rather than Gemini.
- No active API, UI, configuration, or prompt-loading path constructs or selects `GeminiEvaluator`.
- The A/B review endpoint and UI are removed; learner progress review and queue behavior remain.
- Gemini Teacher generation and grade-specific Teacher prompts remain available.
- The obsolete evaluator selector and Gemini Evaluator prompt files are removed without touching secrets or Teacher configuration.

## Verification boundaries

Implementation should inspect all changed call sites and configuration references. Do not run or add test suites unless the user requests tests or verification.
