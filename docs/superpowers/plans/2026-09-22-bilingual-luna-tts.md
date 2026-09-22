# Bilingual Luna TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Speak Grade 3 Luna scripts with explicit Vietnamese/English language spans in order, display no markup, and commit a voice teaching turn only after its final audio.

**Architecture:** A backend speech-markup module owns parsing and plain display text. A voice adapter sends one Pipecat/Soniox TTS utterance at a time and waits for the transport's stopped-speaking event before switching language and dispatching the next. A marker emitted only after the final stop replaces the unsafe first-stop commit trigger. The web and REST boundaries remove markup; Grade 3 authoring sources gain tags without changing speech content.

**Tech Stack:** Python 3.12+, Pydantic, Pipecat 1.11.0, Soniox TTS, Next.js 16, React, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-bilingual-tts-segments-design.md`

## Global Constraints

- Only `<vi>…</vi>` and `<en>…</en>` are language markup; default language is VI.
- Soniox voice ID and speed 0.9 stay unchanged; STT, Evaluator, and Teaching Engine decisions stay unchanged.
- Every language span is a complete stream; never change settings inside an active stream.
- Fixed Grade 3 learner-facing words, punctuation, order, and `[pause]`/`[long pause]` cues do not change.
- Work in `.worktrees/luna-classroom` on `main`; preserve unrelated root-checkout changes.
- Use installed Pipecat 1.11.0 source to verify all frame classes/settings before typing imports. For unfamiliar APIs, consult current Context7 or Pipecat Context Hub first.

## Review Focus

1. Adjacent tags with whitespace outside them: speech and display must retain a word boundary; Task 1 parser test.
2. An unclosed/nested tag in authored YAML: loader fails with the field path; Task 1 validation test.
3. A malformed tag in generated Teacher text: no literal tag is spoken and lesson stays available; Task 1 loose-parser and Task 2 fallback tests.
4. An interruption after the first of several language spans: neither a later span nor the turn is committed; Tasks 2 and 3 interruption tests.
5. An untagged Grade 5 or text-only response: existing VI/default and immediate display behavior remain; Tasks 2 and 4 regression tests.

---

### Task 1: Parse and validate language markup

**Files:**
- Create: `backend/src/luna_tutor/speech/language_segments.py`
- Modify: `backend/src/luna_tutor/curriculum/lesson_script.py`
- Modify: `backend/src/luna_tutor/curriculum/models.py`
- Test: `tests/backend/unit/speech/test_language_segments.py`
- Test: `tests/backend/unit/curriculum/test_lesson_script.py`

**Interfaces:**
- Produce `SpeechSegment(language: Literal['vi', 'en'], text: str)`.
- Produce `parse_speech_segments(text: str, *, strict: bool = True) -> tuple[SpeechSegment, ...]`.
- Produce `plain_speech_text(text: str) -> str`, preserving newlines and removing only language tags and delivery cues for learner display.
- Invalid authored markup raises `ValueError` with a field name; invalid generated markup logs and degrades to one VI span with recognizable tags removed.

- [ ] **Step 1: Write failing parser tests.** Include literal expected segments for `<vi>Xin chào.</vi> <en>HELLO</en> <vi>con nhé.</vi>`, multiline content, empty spans, untagged text, and malformed nesting. A representative assertion:

```python
assert parse_speech_segments('<vi>Xin chào.</vi> <en>HELLO</en>') == (
    SpeechSegment('vi', 'Xin chào.'), SpeechSegment('en', 'HELLO'),
)
assert plain_speech_text('<en>[long pause] HELLO</en>') == 'HELLO'
```

- [ ] **Step 2: Run the targeted test to observe the missing feature.** Run `uv run --project backend pytest -q tests/backend/unit/speech/test_language_segments.py`; expect import failure for the missing parser module.
- [ ] **Step 3: Implement the parser and validators.** Tokenize only the four exact tags, maintain a single active language, preserve inter-tag whitespace at a segment boundary, reject nested/mismatched/unclosed tags in strict mode, and strip recognizable tag tokens to one VI span in non-strict mode. Call strict parsing from Pydantic `say` validators and the Grade 3 unit greeting validator; include field names in failures.

```python
@dataclass(frozen=True)
class SpeechSegment:
    language: Literal['vi', 'en']
    text: str

LANGUAGE_TAG = re.compile(r'</?(?:vi|en)>')

# Walk LANGUAGE_TAG.finditer(text) with an active language. Accumulate text
# before each tag under the active language (VI outside tags). A closing tag
# must match the active language; an opening tag requires no active tag.
# Append the remaining suffix, trim outer whitespace in each TTS span,
# drop empty spans, then merge adjacent same-language spans. The separate
# plain_speech_text() path removes tags without trimming inter-span spaces.
# strict=False catches ValueError, strips LANGUAGE_TAG, logs, and returns
# (SpeechSegment('vi', stripped_text),).
```

- [ ] **Step 4: Run parser, curriculum, and legacy-load tests.** Run `uv run --project backend pytest -q tests/backend/unit/speech tests/backend/unit/curriculum`; verify strict validation and legacy untagged curriculum both pass.
- [ ] **Step 5: Commit** parser, validators, and tests with `git commit -m "Parse bilingual speech markup"`.

### Task 2: Emit complete Soniox language streams

**Files:**
- Create: `voice/server/language_tts.py`
- Modify: `voice/server/text_flows.py`
- Modify: `voice/server/bot.py`
- Test: `tests/voice/test_language_tts.py`
- Test: `tests/voice/test_voice_teaching.py`
- Test: `tests/voice/test_voice_bot.py`

**Interfaces:**
- Consume `parse_speech_segments` from Task 1.
- Produce a Pipecat `LanguageTaggedSpeechFrame(text: str, logical_turn_id: str | None)` for fixed openings and Teacher/fallback output.
- Produce `LanguageSpeechFinishedFrame(logical_turn_id: str | None)` downstream only in response to the transport's upstream `BotStoppedSpeakingFrame` for the final segment.
- Preserve one logical Teacher turn even when the Soniox service synthesizes multiple streams.

- [ ] **Step 1: Write failing frame tests.** Feed `<vi>Xin chào.</vi><en>HELLO</en><vi>Con nói nhé.</vi>` and record the real adapter's outgoing frames. Assert it emits only VI and the first speech frame initially, EN only after one upstream `BotStoppedSpeakingFrame`, VI only after the second, and the completion marker only after the third. No frame text contains `<vi>` or `<en>`. Include plain untagged, malformed Teacher fallback, interruption, and fixed greeting cases.

```python
await adapter.process_frame(LanguageTaggedSpeechFrame(
    '<vi>Xin chào.</vi><en>HELLO</en>', 'turn-1'), FrameDirection.DOWNSTREAM)
assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào.']
await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào.', 'HELLO']
```

- [ ] **Step 2: Run `uv run --project voice/server pytest -q tests/voice/test_language_tts.py` and observe the missing adapter failure.**
- [ ] **Step 3: Implement frame production and routing.** Verify `TTSUpdateSettingsFrame`, `SonioxTTSSettings`, `TTSSpeakFrame`, and upstream `BotStoppedSpeakingFrame` behavior against the pinned package source. Add the adapter immediately before TTS in `bot.py`; route both `on_client_ready` opening text and `BoundedTeacherLLM` output through it. Keep `LLMFullResponseStartFrame`/`EndFrame` semantics required by Flows: hold the response end and `CompletedTeachingFrame` until the last span stops, then release them in order. Do not let a sentence aggregator carry a fragment across language boundaries. Emit one complete `TTSSpeakFrame` per span, wait for its upstream stop, then send the next; send a final marker only after the last stop. Do not send tags to Soniox. Use `self.create_task` for any background task owned by the processor.

```python
async def send_next_span(self):
    span = self.remaining_spans.pop(0)
    await self.push_frame(TTSUpdateSettingsFrame(delta=SonioxTTSSettings(
        language=Language.VI if span.language == 'vi' else Language.EN,
    )))
    await self.push_frame(TTSSpeakFrame(span.text, append_to_context=True))

# When the current span's BotStoppedSpeakingFrame arrives upstream:
# send_next_span() if spans remain; otherwise emit
# LanguageSpeechFinishedFrame(logical_turn_id) downstream.
```

- [ ] **Step 4: Run `uv run --project voice/server pytest -q tests/voice/test_language_tts.py tests/voice/test_voice_teaching.py tests/voice/test_voice_bot.py`.** Confirm the adapter preserves frame order, opening speech, fallback output, and existing worker pipeline assertions (update the expected pipeline only for the new adapter).
- [ ] **Step 5: Commit** with `git commit -m "Route Luna speech through language-tagged TTS"`.

### Task 3: Gate teaching commits on final audio

**Files:**
- Modify: `voice/server/voice_teaching.py`
- Modify: `voice/server/language_tts.py`
- Test: `tests/voice/test_voice_teaching.py`
- Test: `tests/voice/test_language_tts.py`

**Interfaces:**
- Consume `LanguageSpeechFinishedFrame` from Task 2.
- `VoiceCommitProcessor` commits a matching final marker, which the adapter can emit only after observing the last stopped-speaking event.

- [ ] **Step 1: Write failing commit tests.** Set a pending completion with three speech spans; deliver an intermediate `BotStoppedSpeakingFrame` and assert repository version remains 0. Deliver a matching final marker and assert one commit, even if an earlier stop passed through. A duplicate or stale marker must not commit twice. Deliver interruption or ErrorFrame before the marker; assert zero commits even if a stale marker arrives later.

```python
await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
assert repository.get_session(session_id).state.state_version == 0
await commit.process_frame(LanguageSpeechFinishedFrame(turn_id), FrameDirection.DOWNSTREAM)
assert repository.get_session(session_id).state.state_version == 1
```

- [ ] **Step 2: Run `uv run --project voice/server pytest -q tests/voice/test_voice_teaching.py` and confirm the intermediate-stop test fails on early commit.**
- [ ] **Step 3: Implement a per-turn completion gate.** Keep marker identity tied to `CompletedTurn.plan.turn_id`; ignore stale markers. Reset the gate in `discard_pending()`, on interruption, errors, cancellation, and disconnect. Confirm with a pinned-Pipecat frame-sequence test that the adapter receives upstream stop after each segment and never emits the marker before the final one; do not trust only a hand-invoked mock sequence.
- [ ] **Step 4: Run `uv run --project voice/server pytest -q tests/voice tests/scripts tests/ops`; verify no premature commit, no duplicate commit, and no transition on interrupted audio.**
- [ ] **Step 5: Commit** with `git commit -m "Commit voice teaching after final language segment"`.

### Task 4: Hide markup at text and browser boundaries

**Files:**
- Modify: `backend/src/luna_tutor/api/routes.py`
- Modify: `web/src/components/ChatPanel.tsx`
- Test: `tests/backend/integration/api/test_sessions.py`
- Test: `tests/web/pipecat-voice-provider.test.tsx`

**Interfaces:**
- Consume `plain_speech_text` from Task 1 for REST `MessageView` text.
- Web removes `<vi>`, `</vi>`, `<en>`, `</en>`, and `[pause]`/`[long pause]` from both saved and Pipecat spoken captions; voice remains spoken-progress-only.

- [ ] **Step 1: Write failing API and UI tests.** A stored Teacher text `<vi>Xin chào.</vi><en>HELLO</en>` yields `Xin chào.HELLO` (preserve authored whitespace when present), and browser captions contain words but no tags or cue. Assert text-only response appears immediately and voice with `unspoken` text still hides its unheard suffix.
- [ ] **Step 2: Run `uv run --project backend pytest -q tests/backend/integration/api` and `npm test -- --run` in `web`; observe the new tagged-content tests fail.**
- [ ] **Step 3: Apply shared backend display conversion in `session_view`/turn responses and the equivalent TS display sanitizer in `ChatPanel`.** Keep raw internal `spoken_text` available to TTS, but never expose markup as learner-facing `MessageView.text`. Preserve YAML newline bubble splitting.

```python
MessageView(role='teacher', text=plain_speech_text(completed.teacher_utterance.spoken_text))
```

- [ ] **Step 4: Run `uv run --project backend pytest -q tests/backend/integration/api`, `npm test -- --run`, `npm run lint`, and `npm run build` in `web`.**
- [ ] **Step 5: Commit** with `git commit -m "Hide speech tags from learner text"`.

### Task 5: Migrate Grade 3 lesson speech

**Files:**
- Modify: `curriculum/grade-03/unit-01/unit.yaml`
- Modify: `curriculum/grade-03/unit-01/lesson-01/content.yaml`
- Modify: `curriculum/grade-03/unit-01/lesson-01/legacy.yaml`
- Modify: `curriculum/grade-03/unit-01/lesson-02/legacy.yaml`
- Modify: `curriculum/grade-03/unit-01/lesson-03/legacy.yaml`
- Modify: `curriculum/grade-03/LESSON_AUTHORING.md`
- Test: `tests/backend/unit/curriculum/test_grade3_lesson1_script.py`
- Test: `tests/backend/unit/curriculum/test_grade3_language_markup.py`

**Interfaces:**
- Consume strict parser from Task 1; do not tag `target`, `accept`, objective IDs, metadata, or non-spoken examples.
- Lesson 2/3 `content.yaml` currently have no `say` fields, so inspect but do not change them unless actual learner-facing scripted speech is found.

- [ ] **Step 1: Write failing curriculum test.** Load every Grade 3 Unit 1 lesson file, parse each fixed spoken field strictly, and assert the greeting and at least one bilingual Lesson 1 teaching step contain both VI and EN spans. Validate tagged verbatim scripts in the three legacy files where they exist.
- [ ] **Step 2: Run `uv run --project backend pytest -q tests/backend/unit/curriculum/test_grade3_language_markup.py`; observe missing tagged spans.**
- [ ] **Step 3: Add tags around existing speech only.** Treat each natural Vietnamese/English stretch as one segment; put Soniox cue tokens inside the correct language span. For the Lesson 1 hello example, preserve the original lines when tags are removed:

```yaml
say: |-
  <vi>Cô trò mình sang Trạm 1 — học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé! [long pause]</vi>
  <en>HELLO</en><vi> nghĩa là xin chào — con nói khi gặp bất kỳ ai: bạn bè, thầy cô, hay cô Luna. [long pause]</vi>
  <en>Listen first! HELLO. [long pause]</en>
  <en>Your turn now! Can you say: Hello?</en>
```

- [ ] **Step 4: Run a one-time migration audit against commit `8db2fc6`: strip only tags from each changed YAML speech field and assert exact equality to its pre-migration value.** Keep this audit as `tests/backend/unit/curriculum/test_grade3_language_markup.py` with a checked-in baseline fixture for the original speech fields, not a runtime Git dependency. Then run `uv run --project backend pytest -q tests/backend/unit/curriculum` and `uv run --project voice/server pytest -q tests/voice`.
- [ ] **Step 5: Update `LESSON_AUTHORING.md` with paired-tag syntax, default VI, and no tags in non-spoken fields. Commit** with `git commit -m "Tag Grade 3 lesson speech by language"`.

### Task 6: Verify integrated behavior

**Files:**
- Modify only defects found by the checks above, with a failing regression test first.

- [ ] **Step 1: Run full backend suite:** `uv run --project backend pytest -q`.
- [ ] **Step 2: Run full voice suite:** `uv run --project voice/server pytest -q tests/voice tests/scripts tests/ops`.
- [ ] **Step 3: Run full web checks in `web`:** `npm test -- --run`, `npm run lint`, `npm run build`.
- [ ] **Step 4: Check runtime route and provider logs.** `curl -fsS http://localhost:3000/grade3/unit1/lesson/1` and inspect active voice process/logs. If credentials/local services permit, start one isolated Grade 3 voice session; verify VI → EN → VI playback, spoken-progress captions, and absence of Soniox `invalid_stream_state`. Never consume or alter the user's active browser session.
- [ ] **Step 5: Run `git diff --check`, inspect `git status --short`, report the precise tested scope and any unavailable live-audio verification.**
