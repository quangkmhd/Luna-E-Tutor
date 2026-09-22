# Grade 3 Unit 1: one lesson per session

## Goal and scope

Each Grade 3 lesson is one learning session. Implement Lesson 1 first, using the three teaching stations in `docs/Kich_ban_Co_Luna_Lop3_Unit1_Hello_v3.xlsx`, sheet `Buổi 1`. The sheet's opening and ending scripts are outside this conversion. Keep the application's existing opening and session completion behavior until those parts are designed separately. The learner response evaluator, privacy handling, feedback, and support limit remain in use. Do not put silence hint text from the sheet in Lesson 1 YAML.

## Session selection

The session request identifies the unit and lesson. Grade 3 Unit 1 Lesson 1 loads only its opening, three stations, and completion route. It cannot progress into Lesson 2, `level-02`, `level-03`, or `free-talk` in the same session. Keep the Grade 5 curriculum and existing unit identifiers compatible. A selected lesson must be validated at session creation; unknown lessons return a client error. Expose the selected lesson in session data so reopening a session preserves its identity.

## Authoring format

Lesson YAML has a lesson ID and exactly three ordered stations: `vocabulary`, `patterns`, `conversation`. Each station has a title, learning targets, and ordered script turns. A teacher turn has a stable source row ID (for example `B1-15`) and `teacher_text`. A learner opportunity has a source row ID, objective reference, `acceptance_description`, and optional examples. Teacher text is the sheet's wording, with `[long pause]` inserted only at suitable spoken boundaries; preserve the wording, case, and punctuation. Text shown to the learner can be added separately if needed and must not alter the spoken script.

Targets are authored once in the lesson: vocabulary entries and patterns carry stable IDs; objectives state the communicative evidence to accept. A script opportunity references those IDs. The YAML should make it possible to fill later lessons without embedding the exact teacher script inside a long procedural `instruction` paragraph. Machine rules (required opportunities, attempt limit, repetitions) are separate from teacher wording and acceptance descriptions.

## Lesson 1 mapping

- Station 1 follows workbook rows `B1-15` through `B1-47`: `hello`, `hi`, `I/I'm`, book names `Ben`, `Mai`, `Minh`, then `good evening`, `nice to meet you`, and greeting recognition. Include the `HELLO` meaning and usage from `B1-16`, which the current YAML omits. The nonverbal clapping row needs an explicit response mode or a speech equivalent suitable for this audio and text app.
- Station 2 follows `B1-48` through `B1-67`: when to use the two greeting and self introduction patterns, models, substitution with the learner's chosen name, Tom and Emma role turns, then learner initiation. Keep a pretend name acceptable; do not require a real full name.
- Station 3 follows `B1-68` through `B1-80`: a first evening meeting with Luna, then learner initiated greeting. Keep Luna herself as the conversation partner here.

The source sheet describes levels 1–3 as adjustments to expected answers. These are acceptance variations inside this lesson, not separate stages or prerequisites for conversation.

## Runtime behavior

Enter the three stations in order. Deliver a teacher script turn verbatim when its turn becomes active. Stop at each learner opportunity, send the utterance and its acceptance description to the current evaluator, and use existing feedback and retry decisions. Advance only after the required opportunity is handled according to the existing completion rule. A response that is acceptable in context can satisfy the opportunity without matching the example literally. Teacher feedback after a learner response may be naturally phrased; it must not skip, rewrite, or duplicate the next fixed script turn. On a support limit, advance with an honest transition rather than claiming success.

Silence still counts as a learner event in the existing runtime. This design supplies no scripted silence hints or two choice prompts from the workbook. Existing generic handling may acknowledge silence and move on according to the configured attempt limit; it must not trap the learner at a station.

## Validation and verification

Validate unique row IDs, target references, exactly three ordered stations, and at least one learner opportunity per station. Reject empty teacher text and empty acceptance descriptions. Check all Lesson 1 workbook teacher rows and learner opportunities in the three stations against the YAML; ignore opening and ending rows. Test lesson selection and completion within one session, progression through all three stations, acceptable alternatives, incorrect and silent responses, and that Grade 5 routes are unaffected. Run the focused backend tests and a real session route through the available local stack when services and credentials are available.

## Deliberate additions

Keep source row IDs for Excel traceability. Keep spoken text separate from acceptance criteria and progression rules. Add an explicit response mode for nonverbal workbook activities rather than treating a clap as a spoken word. Defer Lesson 2–4 content conversion until Lesson 1's format and runtime are verified.
