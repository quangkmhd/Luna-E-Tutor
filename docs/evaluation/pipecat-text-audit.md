# Pipecat text evaluation audit — 2026-09-19

Scope: real typed input → Pipecat → evaluated teaching decision → Teacher output. STT/TTS are deferred by user instruction. This document records findings, not completion.

## Verified corrections

1. `EvalRunner` copied `evaluator_gold` into actual output for contact information. A mutation regression deliberately supplies wrong gold and was observed failing. Production and eval now share `EvaluatorResult.contact_removed`; expected and actual are independent. The corresponding privacy gold now records no learning evidence, rather than claiming satisfied meaning from removed contact information.
2. Evaluator reports now explicitly identify classification-only scope and unmeasured teaching behavior. Historical reports remain intact, with an audit note in `unit-01-report.md` correcting broad acceptance claims.

## Open findings requiring implementation and reruns

| Layer | Evidence | Required correction |
|---|---|---|
| Scenario context | Numbered YAML has 40 source-numbered cases: 10 warm-up plus the 30 station cases. 37 lack a prior teacher turn. 39 lack a specific activity ID. Many objective/stage combinations match multiple activities. | Review against source dialogue; explicitly select actual activity, prior teacher utterance and preceding delivery/support. Do not infer arbitrary contexts just to get passing scores. |
| Scenario state assertions | Every numbered case inherits `attempt_delta: 1`, including privacy, warm-up and uncertain transcript events. | Author scenario-specific effects from the agreed rules; operational uncertainty must not count as learner failure. |
| Runtime delivery | Engine reads `response_opportunity_given` and `model_repetitions_delivered`; planner/TurnService/API do not update them. Greeting creation does not record delivery. | Add verified text-delivery effects and a real multi-turn progression test. Do not bypass the engine or pre-complete activities solely in fixtures. |
| Teacher context | `TeacherTurnRequest` carries learner text, feedback and an instruction but no preceding teacher question or structured curriculum targets. | Supply bounded relevant task context, support and review intent; preserve reusable system identity/rules. Verify output follows the teaching move rather than relying on vocabulary guessed by the model. |
| Behavioral measurement | Existing EvalRunner never executes Engine or Teacher. `hard_rule_failures` always empty. | Run the actual pipeline and assert decision, state effects, no forced correction repetition, permitted questioning, semantic relevance, review handling and progression. Clearly mark non-text requirements deferred. |
| Browser evidence | Browser fixture contains a magic Free Talk jump. | Retain it for UI testing, add real pipeline integration and a complete learning journey without magic transitions. |

## Prompt research

Official Google guidance: https://ai.google.dev/gemini-api/docs/prompting-strategies . Use explicit instructions, relevant context and representative examples; test variants empirically. Wording similarity is not an acceptance criterion. Teacher decisions, support, reaction to meaning and curriculum direction are.

## Next experimental sequence

1. Repair scenario context/state fixtures against source requirements and test the eval oracle with deliberately incorrect results.
2. Integrate Pipecat text pipeline and activity-level Flows with the existing deterministic core and SQLite. Keep one output per accepted input.
3. Run a baseline of actual pipeline outputs and multi-turn trajectories.
4. Classify each failure as data, content, prompt, engine or integration. Preserve outputs and hashes before changes.
5. Improve the responsible layer, rerun development cases and fresh paraphrases, and review all remaining failures. Never change gold solely to agree with current output.

## Teacher diagnostic iteration — 2026-09-19

Changes: a typed Teacher activity context now supplies stage/activity, objectives, words, patterns, examples and the previous teacher question. Meaning clarification gets a specific teaching directive instead of the entire vocabulary-introduction instruction. Teacher fallback no longer reads internal curriculum directives aloud. System prompt clarifies task-data boundaries and provides transferable examples for meaning, short answers and teacher questions.

Experiments (all isolated Teacher calls on the configured OpenRouter model, not Pipecat or full Unit 1):

| Run | Meaning clarification | Short response | Learner asks Luna |
|---|---|---|---|
| `teacher-context-before.json` | Explained city, then requested saying it | Accepted countryside and followed up | Fallback leaked internal activity instruction |
| `teacher-context-after.json` | Still requested saying city | Redundantly asked whether learner lives there | Safe fallback, but no useful answer |
| `teacher-context-diagnosis.json` | Still requested saying city | Redundant confirmation | Invented residence without pretend framing |
| `teacher-context-revised.json` | Explained, then meaning-choice check | Acknowledged and asked about surroundings | Clearly framed pretend residence |
| `teacher-context-revised-repeat.json` | Explained, then meaning-choice check | Connected follow-up about village/fields | Clearly framed pretend residence |

All six outputs in the two revised runs used model generation; direct review found the three targeted behaviors followed. This tiny development sample does not establish broad accuracy, holdout performance or progression safety. Early experiments did not capture provider error provenance, so the cause of their fallback cannot be determined from those artifacts. The checked-in diagnostic script now captures safe provider errors and parsed model replies separately, resetting capture per request.

Verification: new planner-context and fallback regressions were observed failing before implementation; full backend suite after fixes: 333 passed, 1 skipped (existing live test), two existing dependency deprecation warnings. The previous accepted Teacher prompt hash is historical; a new full behavioral baseline has not been accepted.

Outstanding: actual Pipecat/Flows integration, text-delivery progress, complete source-data corrections, full pipeline baseline and iterative reruns remain required. Pipecat installation is running as tracked exec session 71516; do not launch a duplicate installer without checking its authoritative status.

## Real Pipecat adapter and live smoke iteration

- Added `voice/server/text_pipeline.py`, with typed input and completed-turn frames, a real PipelineWorker/WorkerRunner and a per-request result processor. It wraps the existing core rather than creating a parallel teaching policy.
- Added `text_runtime.py` using the existing API factory, SQLite and browser contract. Four tests exercise actual Pipecat frame routing, provider-error propagation, isolated parallel requests and API idempotency/history. These were first observed failing and then passing.
- The dedicated 1.11 install remains in progress. To make independent progress, tests used the already installed Pipecat 1.8.1 source/dependencies read-only; no global environment was modified. This is explicitly provisional version coverage.
- `pipecat-live-smoke.json`: live Evaluator and Teacher through Pipecat produced a valid recast decision, review item and next activity. Teacher copied first-person correction and asked the learner to guess instead of inviting a question. This is a behavioral failure despite successful plumbing.
- Changed recast validation to allow limited grammatical first-to-second-person changes while preserving the corrected construction. A regression rejects a recast still missing the target preposition. Prompt now assigns the learner the questioning role explicitly.
- `pipecat-live-smoke-revised.json`: two outputs corrected person but still volunteered Luna's residence and repeated the previous question. Not accepted.
- Added an explicit next-move instruction when Engine enters `ask_teacher`: invite the learner to ask, then wait; do not answer yet. This retains curriculum topic data and changes no transition policy. Added a transferable hobby example in the shared prompt.
- `pipecat-live-role-handover.json`: both live outputs now recast naturally and invite Quang to ask where Luna lives. Both used model generation. This proves only the targeted single-turn behavior, not all activities or a multi-turn journey.
- Latest core suite: 335 passed, 1 skipped; four Pipecat adapter tests passed on the locally installed 1.8.1. Full 1.11 verification, Flows, delivery progress and the full scenario loop remain open.
