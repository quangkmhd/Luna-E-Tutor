# Unit 1 Pipecat text integration and behavioral improvement

User-approved scope: integrate Pipecat using typed input and text output first. Defer STT, TTS, audio models, delivery tags and audio lifecycle tests. Preserve the Unit 1 design and the separation between evidence, deterministic decisions and Teacher wording. Implement inline without subagents.

## Acceptance

- Existing website sends typed turns through a real Pipecat pipeline.
- Evaluator and Teacher use OpenRouter google/gemini-3.5-flash-lite; no local speech models or Soniox credentials required for text.
- Teaching Engine alone authorizes transitions; Flows mirrors activity-level state, restored from SQLite.
- One input produces one validated Teacher response; errors cannot commit partial state, duplicate turns cannot advance twice.
- Review all 30 source scenarios and additional Unit 1 coverage against the real spec and curriculum. Review initial states, prior teacher questions, support and labels, not just model output.
- Run full Planner/Engine/Teacher paths through Pipecat, including multi-turn state continuity. Score behavior, context relevance, progression, support and review queue; allow different natural wording.
- Run baseline, classify failures by data/prompt/content/code, improve, rerun, and preserve regression and unseen paraphrase evidence. A model judging its own output is advisory; report limitations and inspect outputs directly.
- Report prompt/content/data hashes, real provider failures, fallback use, checked and unmeasured rules separately. Gold labels must never produce actual results.

## Tasks

- [ ] 1. Audit and repair evaluation measurement and scenario data. Preserve previous reports as historical, qualify their narrower claims.
- [ ] 2. Adapt CLI scaffold to text-only dependencies, verify current Pipecat and Flow APIs with CLI/source. Add failing pipeline integration tests before implementation.
- [ ] 3. Wire existing Planner, Teacher validation and SQLite into Pipecat and Flows; use the existing web interface to exercise it.
- [ ] 4. Add behavioral runner with actual stage/activity context and independent assertions; run baseline over 30 source scenarios and extended Unit 1 paths.
- [ ] 5. Improve prompt/content/logic and invalid data based on evidence; rerun development and fresh paraphrases; review representative outputs and all failures.
- [ ] 6. Verify backend, browser and live Pipecat text results, document commands and remaining limitations.

## Initial audit (2026-09-19)

- Existing EvalRunner evaluates only evidence classification; it does not run Teaching Engine, Teacher or Pipecat. Empty hard_rule_failures cannot prove behavioral compliance.
- Privacy actual output was copied from evaluator_gold. Regression reproduced by intentionally changing gold; production privacy result must be reused independently of gold.
- Browser tests use fixtures, including a direct Free Talk jump, so they establish UI behavior rather than a complete real-model learning journey.
- Google prompt guidance consulted: https://ai.google.dev/gemini-api/docs/prompting-strategies . Apply explicit tasks, relevant context, representative examples and iterative evaluation; keep general identity/rules separate from curriculum and current turn.
