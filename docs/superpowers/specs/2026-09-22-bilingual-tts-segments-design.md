# Language-tagged Luna speech

## Goal

Curriculum authors can mark Vietnamese and English spans inside a Luna utterance. Voice playback uses Soniox's matching language for each span, in authored order, while the learner sees only the spoken words, progressively as audio plays. This applies to the initial scripted greeting and to subsequent Teacher responses. Text-only lessons keep their immediate display behavior. The existing Soniox voice and 0.9 speed remain unchanged.

## Authoring contract

Use explicit, paired `<vi>…</vi>` and `<en>…</en>` tags in `say` text, for example:

```yaml
say: |-
  <vi>Cô trò mình sang Trạm 1 học từ mới.</vi>
  <en>[long pause] "HELLO"</en> <vi>nghĩa là xin chào.</vi>
  <en>[long pause] Listen first! "HELLO".</en>
```

Tags may share a line or span multiple lines. Nested, unclosed, or mismatched tags are invalid in authored curriculum and produce a lesson-loading error that identifies the source field. Untagged text remains Vietnamese for backward compatibility. Empty tagged spans and whitespace-only spans outside tags are ignored for TTS; trim outer whitespace of each TTS span, but preserve its internal wording and cues. Removing tags for learner display preserves authored spaces and line breaks, including spaces between adjacent spans. No tag text is sent to TTS, persisted as learner-facing display text, or shown in the browser. A generated Teacher response with malformed tags is handled safely: remove recognizable tag tokens, speak the remaining text with the default Vietnamese setting, and log the invalid markup rather than failing the whole lesson.

## Voice delivery

Parse each utterance into an ordered sequence of `(language, text)` segments. The voice adapter sends each segment through the existing Soniox TTS service as its own complete stream, changing the service's language *between* streams. It never changes language on an active Soniox stream or relies on sentence punctuation to flush a segment. Await/serialize the previous segment's audio before opening the next, so the browser hears one ordered Luna utterance with no overlap. Maintain the same voice ID and speed for both languages. An untagged utterance uses one Vietnamese stream, preserving current behavior.

Both the fixed opening-message/script path and `BoundedTeacherLLM`'s normal and fallback output use this adapter. The Teacher's content and the teaching engine's decisions remain otherwise unchanged. Existing text-only REST responses strip the language tags for display without changing their turn ordering. The Pipecat web conversation continues to use word-aligned `spoken` progress, so a later segment does not appear before its audio; interrupted speech retains only its spoken prefix.

## Grade 3 lesson migration

Update the existing Grade 3 Unit 1 lesson files as part of this change, not just the TTS runtime. Add VI/EN tags around every fixed learner-facing speech span in `lesson-01/content.yaml`, including greeting, station steps, retries, and closing lines; also tag the unit-level `greeting` in `unit.yaml`. Review `lesson-01/legacy.yaml`, `lesson-02/legacy.yaml`, and `lesson-03/legacy.yaml` for verbatim teacher scripts embedded in activity instructions and tag those quoted speech spans so the Teacher can preserve their language. `lesson-02/content.yaml` and `lesson-03/content.yaml` currently contain activity metadata/instructions rather than `say` fields; keep their non-spoken instructions, targets, and examples untagged. Do not turn metadata into TTS markup. Extend `LESSON_AUTHORING.md` with the paired-tag convention.

For each edited speech span, preserve the existing words, capitalization, pronunciation cues, pause cues, and order. A content audit test compares the learner-facing text after removing tags with the pre-migration text, so the migration cannot accidentally rewrite the lesson. This migration covers all three currently present Grade 3 lesson directories, not only one example.

## Completion and interruption

A tagged response is one **logical teaching turn**, even though it contains multiple TTS streams. The current commit trigger (`BotStoppedSpeakingFrame`) may occur between segments, so it cannot alone authorize persistence. The voice adapter waits for the upstream stopped-speaking event from the transport before dispatching the next segment. After the *last* segment's stopped-speaking event, it emits a final-audio marker; that marker is the commit authorization because it is impossible to emit before the final stop. Earlier stopped-speaking signals do not commit. An interruption, provider error, cancellation, or disconnect discards the pending completion and its markers. A fallback Teacher response remains speakable but cannot commit a proposed lesson transition.

## Validation and tests

- Parser tests cover VI → EN → VI, adjacent tags on one line, multiline spans, untagged legacy text, empty spans, malformed tags, and pause cues.
- Frame-level voice tests prove settings and complete speech streams are emitted in order and no markup reaches Soniox or learner-facing frames. Include opening speech, normal Teacher response, and fallback response.
- Commit tests prove an intermediate stop cannot commit, the adapter emits its marker only on the final stop, and interruption/error before completion commits nothing.
- Web tests prove tags/cues never appear, while voice captions still reveal only spoken text and text-only responses display immediately.
- Curriculum tests load every Grade 3 lesson file and assert valid markup in every tagged teacher-speech field; the migration audit asserts the untagged speech remains unchanged.
- Run the backend, voice, and web suites plus lint/build checks. Where credentials and local services permit, make one real Grade 3 Lesson 1 voice pass and inspect Soniox/provider logs for language transitions and `invalid_stream_state`; do not claim a live audio verification if that pass was unavailable.

## Scope limits

Do not change STT language detection, teacher evaluation, lesson progression rules, or the selected Soniox voice. Do not infer language automatically from the words: tags explicitly control it. Grade 5 and non-lesson Grade 3 material do not need mass conversion; legacy untagged text remains supported.
