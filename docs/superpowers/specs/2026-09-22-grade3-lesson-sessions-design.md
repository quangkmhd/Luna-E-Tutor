# Grade 3 Unit 1: one lesson per session

## Goal and scope

Each Grade 3 lesson is one learning session. Implement Lesson 1 first, using the three teaching stations in `docs/Kich_ban_Co_Luna_Lop3_Unit1_Hello_v3.xlsx`, sheet `Buổi 1`. Each lesson retains an initial greeting, editable as a dedicated field in that lesson's YAML. The sheet's opening and ending scripts are outside the three-station conversion; the greeting does not need to copy the sheet. Keep the application's existing session completion behavior until it is designed separately. The learner response evaluator, privacy handling, feedback, and support limit remain in use. Do not put silence hint text from the sheet in Lesson 1 YAML.

## Session selection

The session request identifies the unit and lesson. Grade 3 Unit 1 Lesson 1 loads its editable greeting, three stations, and completion route. It cannot progress into Lesson 2, `level-02`, `level-03`, or `free-talk` in the same session. Keep the Grade 5 curriculum and existing unit identifiers compatible. A selected lesson must be validated at session creation; unknown lessons return a client error. Expose the selected lesson in session data so reopening a session preserves its identity.

## Authoring format

Lesson YAML has `lesson`, `title`, a required `greeting`, short `words` and `patterns` definitions, and exactly three ordered `stations`: `vocabulary`, `patterns`, `conversation`. The greeting has `order: 1`; each teaching step has the next lesson-wide order number, so `hello` is 2, `hi` is 3, and so on across all stations. A step groups the teacher lines for one teaching item in `say` and the learner opportunity that follows in `accept`; `target` refers to a word or pattern key. Teacher-only steps omit `accept`. The number identifies a teaching item, not every sentence or learner reply. Workbook row numbers are not stored in the lesson YAML. Teacher text is the sheet's wording, with `[long pause]` inserted only at suitable spoken boundaries; preserve the wording, case, and punctuation.

Targets are authored once. The loader derives internal activity and objective IDs, stage links, required flags, and normal completion rules. The YAML does not repeat these fields. Attempts and repetitions have code defaults and appear in a step only when that lesson needs an override. This makes a new lesson a script to fill, rather than a serialized runtime state machine.

Illustrative authoring shape (the real file has all steps):

```yaml
lesson: 1
title: Chào hỏi và giới thiệu tên
greeting:
  order: 1
  say: "Hi, con! Cô là Luna. Hôm nay cô trò mình học chào hỏi nhé!"
words: [hello, hi, "I'm", Ben, Mai, Minh, good evening, nice to meet you]
patterns:
  introduce: "Hi. I'm {name}."
  reply: "Hello, {friend}. I'm {name}."
stations:
  - id: vocabulary
    steps:
      - order: 2
        say: |-
          Cô trò mình sang Trạm 1 — học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé! [long pause]
          HELLO nghĩa là xin chào — con nói khi gặp bất kỳ ai: bạn bè, thầy cô, hay cô Luna. [long pause]
          Listen first! HELLO. [long pause]
          Your turn now! Can you say: Hello?
        target: hello
        accept: Con nói “hello”; âm /h/ có thể cần cô nói mẫu lại.
      - order: 3
        say: |-
          Hi cũng là xin chào, nhưng ngắn và thân mật hơn — con dùng với bạn bè. [long pause]
          Listen first! HI. [long pause]
          Your turn now! Hi!
        target: hi
        accept: Con nói “hi” như lời chào.
  - id: patterns
    steps: []
  - id: conversation
    steps: []
```

Empty `steps` lists abbreviate this illustration only; they are invalid in a real lesson. Authors can edit the greeting, words, patterns, teacher lines, and acceptance descriptions without touching Python.

## Lesson 1 mapping

- Station 1 follows workbook rows `B1-15` through `B1-47`: `hello`, `hi`, `I/I'm`, book names `Ben`, `Mai`, `Minh`, then `good evening`, `nice to meet you`, and greeting recognition. Include the `HELLO` meaning and usage from `B1-16`, which the current YAML omits. The nonverbal clapping row needs an explicit response mode or a speech equivalent suitable for this audio and text app.
- Station 2 follows `B1-48` through `B1-67`: when to use the two greeting and self introduction patterns, models, substitution with the learner's chosen name, Tom and Emma role turns, then learner initiation. Keep a pretend name acceptable; do not require a real full name.
- Station 3 follows `B1-68` through `B1-80`: a first evening meeting with Luna, then learner initiated greeting. Keep Luna herself as the conversation partner here.

The source sheet describes levels 1–3 as adjustments to expected answers. These are acceptance variations inside this lesson, not separate stages or prerequisites for conversation.

## Runtime behavior

Enter the three stations in order. Deliver a teacher script turn verbatim when its turn becomes active. Stop at each learner opportunity, send the utterance and its acceptance description to the current evaluator, and use existing feedback and retry decisions. Advance only after the required opportunity is handled according to the existing completion rule. A response that is acceptable in context can satisfy the opportunity without matching the example literally. Teacher feedback after a learner response may be naturally phrased; it must not skip, rewrite, or duplicate the next fixed script turn. On a support limit, advance with an honest transition rather than claiming success.

Silence still counts as a learner event in the existing runtime. This design supplies no scripted silence hints or two choice prompts from the workbook. Existing generic handling may acknowledge silence and move on according to the configured attempt limit; it must not trap the learner at a station.

## Validation and verification

Validate nonempty greeting, `greeting.order == 1`, unique consecutive `order` values across the whole lesson, target references, exactly three ordered stations, and at least one learner opportunity per station. Reject empty `say` for teacher-led steps and empty `accept` when a response is expected. Review all Lesson 1 workbook teacher lines and learner opportunities in the three stations against the YAML, using a test fixture if mechanical traceability is needed; ignore opening and ending rows. Test that editing only the greeting field changes the first teacher message, lesson selection and completion within one session, progression through all three stations, acceptable alternatives, incorrect and silent responses, and that Grade 5 routes are unaffected. Run the focused backend tests and a real session route through the available local stack when services and credentials are available.

## Deliberate additions

Keep workbook traceability outside the runtime YAML. Keep spoken text separate from acceptance criteria and progression rules. Add an explicit response mode for nonverbal workbook activities rather than treating a clap as a spoken word. Defer Lesson 2–4 content conversion until Lesson 1's format and runtime are verified.
