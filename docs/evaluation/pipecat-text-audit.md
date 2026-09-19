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

## Text delivery and sequential opening

- Added `confirm_text_delivery` to the text TurnService. The completed, validated Teacher text refines the uncommitted proposal with observable target-word occurrences, response invitation, support and feedback. Repository persistence remains atomic. This is text delivery only, not evidence of spoken playback.
- Counts target words actually present, caps model exposure at two, records no delivery for fallback, and attributes feedback to the activity the learner answered rather than the newly introduced activity. An `ask_teacher` invitation requires an explicit invitation to ask Luna, not any question mark.
- Session creation now records that its authored greeting is available in the stored/displayed transcript. Without this receipt the Engine stayed at the greeting forever.
- New regressions reproduced missing model/opportunity receipts and feedback incorrectly assigned to the next word; after correction a real two-turn Planner/Engine/Teacher service sequence moves city → class.
- `pipecat-live-opening.json` is a sequential real-model HTTP + Pipecat experiment: Hello → warm-up.feelings; fine → warm-up.start; start → lesson-01.introduce-city; City → lesson-01.introduce-class. Each response used the state returned by the previous API call. No fixture shortcut or manual state advance was used.
- Combined backend and Pipecat adapter suite: 344 passed, 1 skipped, two existing dependency warnings. Dedicated 1.11 installation still pending, and Flows/full-scenario acceptance remains incomplete.

Limitations to audit next: receipts use observable lexical/question cues, not a semantic proof of correct teaching; the behavioral runner must check relevance and activity fit. Full-turn fallback progression, introduced-word reporting, vocabulary evidence classification, and end-to-end review/support behavior still need explicit coverage. Earlier prompt and curriculum baselines remain historical.

## Numbered behavioral baseline and uncertainty correction

- Replaced implicit scenario activity selection with explicit activity IDs, previous teacher turns and delivery/support fixtures for 40 numbered cases (10 warm-up + 30 station branches). These seeded states represent isolated branch tests, not proof of prior learning. Some cases are topic-preserving variants of the source, not literal transcript reproductions.
- Removed the inherited `attempt_delta: 1` assertion. The behavioral runner now rejects unknown assertions and compares actual Engine actions/state; it executes Evaluator → Engine → Teacher inside Pipecat. Multi-turn cases carry actual resulting state and Teacher history. Failed execution stops that trajectory. Semantic criteria remain pending until reviewed.
- `behavior-baseline.json` preserves 40 real-model outputs. Three cases failed one or more deterministic checks: warmup-05, station1-06, station2-10. The other 37 have no failures in the limited implemented checks; this is **not** a 37/40 pedagogical acceptance score.
- Root cause for station1-06: scenario uncertainty was only reported in metadata, while Planner always passed `final` to Evaluator. Added optional typed transcript status across runner, Pipecat frame, service and planner. A regression first failed on the absent parameter. The real-model rerun in `behavior-uncertainty-revised.json` now clarifies, stays and does not consume an attempt.
- New reproducible entry point: `scripts/eval-pipecat-text.py --env-file <path> --output <new-file> [--scenario <id>]`, using the voice/server Python environment. It refuses to overwrite prior runs, checkpoints each case and hashes code/prompts/content/data. It requires no STT or TTS.
- Verification after this change: 351 tests passed, 1 skipped, two existing dependency deprecation warnings, using installed Pipecat 1.8.1 while dedicated 1.11 sync continues.

### Review findings still open (do not conceal by relabelling gold)

1. warmup-05 and station2-10 encode observed learner silence as `incomplete` transcript. That conflates a pedagogical no-response event with operational uncertainty. Source lines 85–94 call for a gentle choice after first silence; lines 534–548 call for an easier question after the second, preserving later review. Add an explicit simulated no-response event for text evaluation, with no claim to measure an eight-second audio timeout. Correct source context and expected effects alongside this feature. Do not treat typed `[silence]` as measured silence.
2. Baseline station3-02 and station3-07 use “I live ...” without clearly pretend framing. The shared prompt rule needs to cover teacher-supplied practice examples as well as answers to personal questions.
3. Baseline station3-10 offers “crowded; however, it is busy”, an incoherent contrast; structural output checks missed it. Add semantic criteria/contrast examples and rerun paraphrases.
4. Baseline station2-08 asks for a made-up phone number. Source/spec privacy guidance must be reconciled with the existing planner directive; do not call this branch accepted merely because privacy redaction worked.
5. Most state assertions still only check count_attempt. Add activity/progression/review assertions grounded in source rules. Full Unit 1 continuous journey, native Flows, browser live interaction and dedicated 1.11 validation remain pending.

### Same branch, Teacher review after the routing fix

The first uncertainty rerun's **decision** was correct, but its actual Teacher output was “Countryside. Let's say it together: countryside. How does that sound to you?” This still restarted imitation, so it was not pedagogically accepted. Added a dedicated clarification directive in Planner: confirm intended meaning, do not infer a pronunciation error or restart the introduction. A failing regression reproduced the conflicting generic activity directive before the fix. `behavior-uncertainty-teacher-revised.json` now says “Did you say countryside?”, with stay/no-attempt and model generation. This is one targeted success, not broad acceptance. Final suite for this slice: 351 passed, 1 skipped.

## Observed no-response events and source-data correction

- Corrected warmup-05 and station2-10: `input_event: no_response` is an explicit simulation of observed silence, not `transcript_status: incomplete`. Operationally uncertain input still clarifies without counting attempts. No audio timer is claimed. An application event supplies the absence of a response locally; Gemini is not asked to infer knowledge or emotion from absence. Reports identify this evidence source separately from model evaluation.
- Added propagation through real Pipecat frames and the teaching service. Warm-up first silence offers a feelings choice; a second silence can move past that greeting without academic attempts or learning evidence. Per-activity no-response count is separate from academic attempt count. A real learning activity counts response opportunities toward its support limit, then records later review.
- Restored station2-10's source birthday context (previous fixture used hobby), then expanded it to **two sequential turns** beginning with “When's your birthday?”. The second turn uses actual returned state and actual Teacher history. Both the stay/first-attempt and move/review-queue effects are asserted. The next topic follows the full Unit 1 curriculum (hobby), rather than copying the source's shortened colour example.
- `behavior-silence-revised.json`: warmup response offered happy/sleepy choices, but second birthday silence led to an open hobby question. This was a semantic failure despite passing implemented deterministic checks.
- Strengthened the teaching directive to require two concrete choices when reducing difficulty (or a question starter for ask_teacher). `behavior-silence-choices-revised.json` produced happy/sleepy and football/reading choices; both were directly reviewed as appropriate directions for those two cases.
- `behavior-silence-sequential.json` exercises the two real Teacher turns in sequence through Pipecat, with explicit locally observed no-response evidence. Deterministic checks pass on both turns. The record retains actual outputs and code/data hashes; do not infer whole-unit acceptance from these two turns.
- Latest full suite before the final small validation/wording refinement: 356 passed, 1 skipped, two pre-existing dependency warnings. Targeted no-response/schema tests after refinement: 7 passed. Pipecat version coverage is still 1.8.1; 1.11 installation remains authoritative live process 3073902 / exec handle 71516, not a reason to restart it.

Remaining: full Unit 1 continuous run, native Flows, comprehensive semantic review and regression/paraphrase runs, live browser validation and dedicated dependency environment. Baseline biography, contrast, privacy, delivery/fallback and evidence-mastery findings remain open.

The sequential silence outputs were directly reviewed: first “Is your birthday in May or November, Quang?”, then “No worries, Quang! Is your hobby drawing or playing football?”. The birthday objective is queued for review on turn two. Final full suite after all no-response refinements: **356 passed, 1 skipped**.

## Full journey experiment started

`/tmp/luna-full-journey.py` (reusable version: `scripts/eval-unit1-journey.py`) drives the actual HTTP API from a new session, using SQLite, Pipecat and real Gemini calls; no fixture jumps or edited state. The scripted learner deliberately includes `I live countryside.` then later uses the correct construction. Output is checkpointed to `pipecat-full-journey-baseline.json`. This first diagnostic maps replies to current activities and may repeat one after a stall; such repetitions are test behavior, **not proof that the conversation felt natural**. Review each prior Teacher question against the supplied answer.

Already observed before completion:
- Gemini classified “What's your favourite animal?” during ask_teacher as `answer` once, delaying the handover. Repeat then classified correctly. Needs a targeted evidence/prompt regression with paraphrases.
- Lesson 3 introductions accepted class/countryside evidence but still returned offer_support/stay because primary objective defaults to the first vocabulary entry (`city`). This wrongly disfavors countryside despite source acceptance. Review multi-objective activity success semantics; do not merely change the simulated child to live in a city.
- Some introductions/guided responses lacked sufficient delivered-model/opportunity receipts, causing another turn despite correct answers. Inspect actual words and receipt rules before loosening gates.
- These are failures discovered by sequential testing even though many single-case checks passed. Preserve the baseline before fixes.

### Full journey baseline reached Free Talk and exposed a hard failure

The baseline completed 55 HTTP teaching turns, entering `free-talk.conversation`. The next learner turn raised `EvaluatorRequest.active_objectives` validation: the request limit was 20, but the authored Free Talk activity contains 27 objectives. The checkpoint remains `complete: false`, faithfully reflecting the terminated experiment; Free Talk output and finishing were not verified. Also observed: unframed invented biography and the malformed prompt “Can you say calm, cottage?”. Reaching a stage does not establish teaching quality.

A regression using the **actual complete Unit 1 Free Talk activity** reproduced the request failure. Raised the finite context bound to 64 so all 27 authored objectives fit without silently discarding targets. The targeted planner suite now passes 6 tests. Full-journey rerun is active as exec session **98984**, checkpoint `pipecat-full-journey-capacity-revised.json`; do not restart solely because a turn yields. The diagnostic script now records safe exception type/activity if it fails.

Dedicated Pipecat 1.11 dependency sync has now completed successfully (installer 71516 exited 0). First full test invocation in that environment exposed a missing **test dependency** (`respx_mock` fixture), not teaching failures: 275 passed, 82 setup errors. Added `respx` to voice/server dev dependencies and reran the full suite. Existing in-flight full-journey capacity rerun remains on 1.8.1; future live runs should use `voice/server/.venv/bin/python` directly without a site-packages fallback.

Verified dedicated **Pipecat 1.11.0** environment: `voice/server/.venv/bin/python -m pytest backend/tests voice/tests -q` → **357 passed, 1 skipped**, one existing dependency warning. This replaces provisional version coverage for automated tests; live 1.11 behavioral experiments and native Flows remain required.

## Multi-objective completion, invited questions, and fallback atomicity

- `pipecat-full-journey-capacity-revised.json` finishes the diagnostic run with `stopped: request_error`: after 54 teaching turns reached Free Talk, the first Free Talk input got HTTP 503 `INVALID_EVALUATION`. Raising the context bound removed the schema-capacity exception but did not establish a passing full journey. Do not count `complete: true` (experiment stopped) as acceptance.
- Added explicit curriculum `meaning_objective_ids` plus `require_all_meanings`. Lesson 3 introductions now requires class and home meaning, not the first vocabulary item city. Per-activity `demonstrated_meaning_ids` accumulates the child's actual current-activity evidence across turns; earlier learning elsewhere does not complete this activity. Support-limit review includes missing criteria, not already demonstrated ones. Four regression tests cover combined answers, partial answers, two-turn accumulation and missing-only review.
- Generic completion uses activity targets rather than blindly treating `state.objective_id` as the only success criterion. Free Talk retains its selected-review focus. Content now asks for class and home together as separate facts, allowing city or countryside as home alternatives. Partial completion gives Teacher only the remaining-information directive.
- Strengthened Evaluator instruction: a question produced after an invitation to ask the teacher is still `asks_teacher`, even when it satisfies the lesson pattern. New derived development regressions include exact and paraphrased questions plus countryside/class review. They are explicitly not numbered source transcripts.
- Real Pipecat **1.11** run `behavior-interactions-revised.json`: all three question acts classified correctly; countryside/class moved correctly. One paraphrase Teacher output fell back, so this run failed that case. Teacher also phrased the two introduction facts as alternatives in one output.
- Clarified the Lesson 3 activity instruction; `behavior-interactions-repeat.json`: four deterministic case checks passed, including paraphrase and correct next activities. Direct review still found unframed personal preference (“My favourite animal is the cat!”), so broad semantic acceptance remains open.
- Isolated seeded Free Talk diagnosis (`free-talk-diagnosis.json`) ran twice through real Pipecat 1.11 with capture of parsed, sanitized synthetic model outputs: both calls returned valid evidence for 27 objectives and Teacher text. This does **not** explain the earlier intermittent invalid evaluation or establish continuous-session success.
- A new regression proved Teacher fallback previously committed a proposed activity advance. TurnService now rejects fallback as `InvalidTeacherResultError`; API returns retryable `INVALID_TEACHER_OUTPUT`, keeping version/history/state unchanged. This favors an explicit retry over falsely teaching/skipping a new activity. The regression failed before the fix, then passed; API persistence is separately tested. Standalone Teacher fallback wording remains available internally, but cannot authorize a completed production turn.
- Full 1.11 suite after production changes: 361 passed, 1 skipped. After the final extra API regression/import cleanup, targeted suites: 12 passed. One existing dependency warning remains. Current experiments are all terminal; no live evaluation or installer remains running.

Next: improve/verify Teacher personal-example framing and semantic relevance, delivery readiness without redundant correct-answer retries, vocabulary evidence/mastery accuracy, robust Free Talk validation/review and finish, native Flows, live browser and full development/holdout acceptance. These requirements remain active.

## Native Pipecat Flows integration — 2026-09-19

- Read current CLI Context Hub docs/examples and installed 1.11 sources before implementation. Context7 confirmed external `set_node_from_config`, `respond_immediately`, and RESET strategy. Native source: `pipecat.flows.manager.FlowManager`; API reference https://docs.pipecat.ai/api-reference/pipecat-flows/flow-manager . Removed separate `pipecat-ai-flows` because 1.11 bundles it and emits a warning when both are installed.
- Production TurnService now exposes plan/respond/complete boundaries without duplicating teaching policy. `text_flows.py` restores the persisted activity node silently, executes Evaluator/Engine in a processor, asks FlowManager to replace the authorized node context, and invokes the existing Gemini Teacher through a real custom `LLMService` receiving `LLMContextFrame`. The actual Flow-rendered request is validated against the Engine authorization before generation. Output frames reach the result collector before assistant aggregation; one complete turn returns for atomic persistence.
- Node context embeds learner data through a single Flow state substitution, preventing learner-authored `{{...}}` from becoming a template instruction. Native tests verify actual Flow transitions, exact bounded request, one Teacher call, errors without completion, concurrent session isolation and absence of default audio-turn model initialization. Typed turns explicitly use ExternalUserTurnStrategies; no STT/TTS or local turn analyzer is initialized.
- Process-only test fixtures retain the small legacy adapter; actual production TurnService always selects the native Flow path. Shared frame definitions were extracted to avoid circular imports. SQLite remains authoritative; Flow state is per request, not a second persistence system.
- Five native tests passed; full suite: **367 passed, 1 skipped**, one existing dependency warning. After frame extraction/formatting, all 11 pipeline/Flows tests passed. The following full run after prompt/privacy changes also passed 367/1.
- `native-flows-interactions.json`: four real Gemini cases used native Flows on 1.11 and passed implemented action/state checks. No automatic semantic acceptance is inferred.

### Source-grounded correction to Teacher review criteria

Ruling: prior audit overreached by treating every unframed first-person preference as a failure. Source dialogue explicitly has Luna say “My favourite animal is a dolphin” and answer where she lives (source lines 166, 343, 351). The requirement is a natural, coherent teaching character, with explicit entry/exit for Emma roleplay, not a repeated disclaimer before every practice answer. The shared prompt now establishes a stable **fictional Luna practice profile** (small city, dolphin, sandwich, pink, table tennis; reading and May as reusable illustrative defaults). It forbids claiming real lived experience. Derived eval criteria now check consistency rather than mandatory per-turn pretend wording. If those illustrative defaults are changed later, update the profile rather than scattering facts into Unit logic.

- Added a transferable instruction to check that however expresses a real contrast, moreover an addition, and word repetition does not imply a preference. Grounded privacy redirect in source lines 514–516: practise the phrase “phone number”, without soliciting another digit sequence after redaction.
- `native-flows-persona-revised.json`: five live cases used the profile consistently, avoided requesting digits, and used a meaningful quiet/busy-on-market-days contrast. Direct review found one vocabulary introduction lacked a response invitation; limited deterministic checks missed that. This is not a passing teaching output despite valid JSON.
- `native-flows-full-journey.json` preserves a full-session diagnostic attempt, code/content hashes and framework version. It stopped during Level 2 on retryable `INVALID_TEACHER_OUTPUT`. Parsed synthetic provider diagnostics identify the cause: “When is your birthday, Quang? Is it in January or May?” contains two questions despite the allowed maximum of one. Atomic rejection worked; natural teaching acceptance did not. The earlier multi-objective review and invited-question stalls no longer appeared in this run.
- Full-journey diagnostic now attempts the finish endpoint after a successful Free Talk turn, and captures sanitized parsed outputs on failure (no credentials, HTTP headers or raw provider bodies). The stopped run did not reach that finish check.

Next required loop: add bounded Teacher repair for detected output violations (without rerunning Evaluator/Engine or committing state), record remaining model/invitation requirements explicitly in the Teacher request, and test against the two-question and missing-invitation failures. Then rerun the full native journey, development/holdout scenarios and browser. Free Talk reliability/review, delivery/evidence accuracy and finish/early-end semantics still need acceptance. No evaluation or installer is currently running.

## Bounded Teacher repair and explicit word-practice delivery

- Added remaining-model and pending-invitation fields to the bounded Teacher context. Planner computes them from the target activity's actual delivery receipts. Clarification/meaning explanation does not restart a repetition drill. Shared lexical observation helpers keep validation and delivery recording consistent; they remain cues, not semantic proof.
- Teacher may regenerate **once** after schema/wording validation failure, receiving only application-generated validation feedback plus the unchanged request. It does not rerun Evaluator/Engine and does not retry provider outages. After two invalid drafts, the existing atomic failure path rejects the turn. Tests first failed for an unrepaired two-question output, unbounded-count expectations and missing invitation, then passed.
- Strengthened behavioral checks: entering a new required activity must leave response/model receipts, independently checked against curriculum requirements. A bad synthetic Teacher that merely said “Cottage. Cottage.” was previously accepted by the runner; the new regression fails it.
- `native-flows-repair-targeted.json`: five live cases passed limited deterministic checks. Review found the cottage introduction asked what was near a cottage rather than inviting the word-practice response. Added an explicit introduction invitation check and corresponding prompt instruction.
- `native-flows-numbered-revised.json`: 40 cases / 41 actual turns (two-turn silence case), native Flows and real Gemini. One deterministic failure: station2-02 classified “What is a hobby?” as asks_teacher. Direct semantic review also caught a first-person birthday recast and some weak discourse connections; zero hard-check failures in another record does not certify pedagogy.
- `native-flows-repair-journey.json`: failed at lesson-03.ask-luna → birthday introduction. Both captured Teacher drafts asked the child's birthday month rather than inviting the new word, so rejection was correct. This demonstrates that a repair loop alone does not fix ambiguous teaching content.
- Clarified every Unit 1 new-word activity instruction to invite saying the target word before a topic question. Added the precise failed transition as a derived regression. Added generic article/possessive contrast to Evaluator prompt: “What is a hobby?” requests meaning; “What is your hobby?” asks the teacher.
- Recast validation now requires the second-person construction when converting the child's I/my statement; it no longer accepts a bare first-person correction as Luna's biography. A failing regression reproduced “My birthday is in May!” being wrongly accepted. Model prompt includes an April example to preserve the child's month rather than Luna's profile.
- `native-flows-word-introduction-revised.json`: all three targeted live checks passed. Outputs were directly reviewed: food answer → birthday models + “Can you say birthday?”; a simple hobby definition/check; “Your birthday is in May!” → hobby question. These fix the identified directions without requiring exact source wording.
- Verification: **375 passed, 1 skipped** on Pipecat 1.11, one existing dependency warning. The bounded-repair tests cover same-request preservation, max two attempts, outage no-retry and missing word invitation. No state commits on failed Teacher validation.

New continuous native journey is running as exec session **42624**, checkpoint `native-flows-word-practice-journey.json` and log `/tmp/luna-word-practice-journey.log`. Poll its authoritative handle; do not overwrite/restart solely on elapsed time. Its script records code/content hashes and parsed-response counts and attempts the finish endpoint if Free Talk succeeds.
