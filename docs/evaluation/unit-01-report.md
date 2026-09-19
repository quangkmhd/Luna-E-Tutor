# Unit 1 evaluation report

## Accepted baseline

The evaluated model is `google/gemini-3.5-flash-lite` through OpenRouter. The final holdout run contained 15 records (five sealed paraphrases, each repeated three times) and achieved 100% exact-record agreement, 100% schema validity, zero provider failures, zero invalid responses, and zero hard-rule failures. Median latency was 1,388 ms and p95 latency was 1,486 ms.

The final development run contained 159 records (53 scenarios repeated three times). It achieved 94.34% exact-record agreement, 100% schema validity, zero provider failures, zero invalid responses, and zero hard-rule failures. This metric is deliberately strict: a record counts as correct only when every evaluated field matches.

- Evaluator prompt SHA-256: `f2bfcc4b29354676a89a1fcbe2369d625124bf1f8d38a4aefe794771e4f383b4`
- Teacher prompt SHA-256: `faeec9311a64ee423d1102decee5af24303dd58381b7e77d3e1f0506018c2ba1`
- Curriculum SHA-256: `dcbdfff063739b2173eb9f89ea48e6c3244095e54eb13e66e9329c4032081b84`
- Development report: `evals/unit-01/reports/unit-01-20260919T060225.268086Z.json`
- Holdout report: `evals/unit-01/reports/unit-01-20260919T060343.043357Z.json`

## Improvement findings

Failures were assigned to their owning layer before changes were made.

| Owner | Finding | Resolution |
|---|---|---|
| Evaluator prompt | Greetings without an academic objective were sometimes marked off-topic; direct “What is X?” questions were sometimes treated as questions for the teacher; unrelated nouns were sometimes treated as wrong-category answers. | Clarified all three distinctions and added examples for exact target form, acceptable alternatives, semantic-category errors, and unrelated answers. |
| Scenario context | Off-topic scenarios omitted Luna's immediately preceding question, making the intended relation unknowable. | Added `teacher_turn` to scenario turns and passed it through the runner. |
| Scenario labels | Several gold labels conflated communicative meaning with target form, or treated an explicitly accepted alternative as the exact target. | Corrected labels against the curriculum evidence criteria and the source dialogue. Meaning and form remain separately scored. |
| Privacy boundary | Redacted phone placeholders were still sent to Gemini, which could return an invalid evaluation. | Phone/contact events now bypass Gemini entirely and take the deterministic privacy path. Tests assert that the evaluator receives no request. |
| Provider/model | One initial holdout response was invalid JSON. | Recorded as an invalid response; a clean repeat produced 15/15 valid, stable results. No prompt was tuned to that provider failure. |
| Teaching Engine | No defect was found during the live evaluation loop. | Existing table-driven policy tests remained unchanged and passing. |

The final development run still showed three one-off semantic variations: whether a longer exact construction is exact or an alternative, and whether a tired, fragmented Level 3 response demonstrates partial meaning. These misses are visible in the report. They do not affect schema safety, privacy, deterministic progression, or holdout acceptance.

The holdout label for “I'm a bit tired, but my town is quiet and nice” was corrected after first inspection because `but` is a grammatical alternative to the target contrast with `however`. This was a label correction only; the Evaluator prompt was not changed after opening holdout.

## Teacher wording review

Ten live Gemini Teacher responses covered every feedback action used by Unit 1 and all stages. All ten used model generation rather than fallback, remained plain spoken text, asked at most one question, avoided forced repetition, made no pronunciation claims, and followed the bounded action.

| Stage | Action | Reviewed output | Result |
|---|---|---|---|
| Warm-up | acknowledge and continue | “Hello, Quang! It is so wonderful to see you today. Are you ready for our lesson?” | Pass: warm, short, greeting only. |
| Lesson 1 | recast | “I live in the countryside. What do you like about living there, Quang?” | Pass: exact correction once, no request to repeat. |
| Lesson 2 | explain meaning | “A hobby is something you like doing in your free time, Quang. What is one of your hobbies?” | Pass: age-appropriate explanation and one question. |
| Lesson 3 | answer teacher question | “I really like dolphins, Quang! What is another favourite thing of yours?” | Pass: answers first and continues naturally. |
| Level 2 | offer support | “That is totally okay, Quang. Would you like to talk about table tennis or drawing?” | Pass: gives two concrete choices without counting failure. |
| Level 3 | redirect | “Dolphins are wonderful animals! But let's come back to our town. How would you describe your town using the word however?” | Pass: acknowledges, then redirects with one question. |
| Level 3 | reassure | “I understand, Quang. It is okay to feel tired. Would you like to take a quick stretch before we do one more fun thing?” | Pass: responds to emotion before teaching. |
| Free Talk | clarify | “I didn't quite catch the last part, Quang. Where do you live?” | Pass: treats uncertain input as an audio/transcript issue. |
| Free Talk | privacy redirect | “Let's keep our real phone numbers private, Quang! How about we use a made-up number instead?” | Pass: does not repeat or infer the number. |
| Summary | stop | “We are all done for today, Quang. You did a wonderful job sharing your ideas and working so hard on your English!” | Pass: exits warmly without a mastery claim. |

The review found no need to change the Teacher prompt. Delivery emotion remains a separate intent field so the voice adapter can render it with verified Soniox controls later.

## Acceptance

The core is accepted for the web experiment: all curriculum references and scenario coverage validate, privacy is enforced before model calls, deterministic policy owns progression, and the holdout baseline passes every gate. The remaining development variations are retained as evidence for future prompt/model comparison rather than hidden by changing acceptance rules.
