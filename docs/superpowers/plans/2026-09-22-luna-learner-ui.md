# Luna Learner Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all learner routes, including Free Talk setup and conversation, into the approved Luna classroom visual system without changing teaching or voice behavior.

**Architecture:** Keep Tutor session state in `TutorShell` and topic state in `TalkRoom`. Add a small presentational learner header and scoped learner styling, then adapt Unit/Lesson selection and Talk to the existing classroom rhythm. Reuse the existing chat and Pipecat voice components.

**Tech Stack:** Next.js 16, React 19, CSS/CSS modules, Vitest + Testing Library, Pipecat client components already installed.

**Spec:** `docs/superpowers/specs/2026-09-22-luna-learner-ui-design.md`

## Global Constraints

- Work only in `/home/quangnhvn34/dev/massko/E-Voice-Tutor-v1/.worktrees/luna-classroom` on `codex/luna-classroom`; preserve the pre-existing uncommitted classroom implementation there.
- Approved learner routes: `/`, `/grade3/unit1`, `/grade3/unit1/lesson/[lessonId]`, `/[unitSlug]`, `/talk`.
- `/review` and `/design` stay visually and functionally unchanged. Never use unscoped selectors that alter them.
- Preserve Luna's name, the existing Roboto font, real Unit/Lesson/session data, topic limit 120, current canonical routes, and Pipecat endpoint/request contract.
- Do not add sample streaks, clocks, rewards, games, upload, image/audio playback, or fabricated learning progress from the reference.
- Use `apply_patch` for code edits. Test-first for behavior changes. Do not touch the user-owned backend/curriculum edits in the original checkout.

## File Map

- `web/src/components/LearnerHeader.tsx` (new): shared learner-only brand/header frame with caller-owned actions.
- `web/src/components/UnitSelector.tsx`, `LessonSelector.tsx`: existing real-data selection flows, newly placed in the learner frame.
- `web/src/components/TutorShell.tsx`: existing classroom session flow; use the same header frame without changing API calls.
- `web/src/components/talk/TalkRoom.tsx`: existing setup and conversation state; rearrange markup, not voice lifecycle.
- `web/src/app/learner.css` (new), imported by `web/src/app/layout.tsx`: learner-scoped colors, header, and selection layout.
- `web/src/app/globals.css`: preserve and polish the existing classroom-specific rules in Task 3.
- `web/src/components/talk/talk.module.css`: Free Talk setup, conversation, and responsive layout.
- `tests/web/{unit-selector,lesson-selector,tutor-shell,talk-room}.test.tsx`: user-observable behavior and route contracts.

## Review Focus

1. Empty Unit list: show a clear empty state and keep Free Talk reachable (Task 1 test).
2. Long Unit/Lesson titles and 390px viewport: retain readable selection and no page-width overflow (Task 1/3 browser checks).
3. Whitespace-only custom topic: Start stays disabled; custom value is trimmed and capped at 120 (Task 2 test).
4. Change/Stop Free Talk: unmount the previous provider and start fresh, never leak the prior transcript (Task 2 test).
5. Learner styles: do not change `/review` or `/design`, including Roboto and their document layout (Task 3 browser checks).

---

### Task 1: Shared learner header and selection screens

**Files:**
- Create: `web/src/components/LearnerHeader.tsx`, `web/src/app/learner.css`
- Modify: `web/src/components/UnitSelector.tsx`, `web/src/components/LessonSelector.tsx`, `web/src/app/layout.tsx`
- Test: `tests/web/unit-selector.test.tsx`, `tests/web/lesson-selector.test.tsx`

**Interfaces:**
- Consumes: existing `UnitSummary[]`, `LessonSummary[]`, `onSelect(unitId: string)`, `listLessons(unitId, signal)`.
- Produces: `LearnerHeader({ subtitle, children }: { subtitle: string; children?: React.ReactNode })`; `.learner-app` scoped style root for Tasks 2–3.

- [ ] **Step 1: Write failing selection tests.** Add these tests using existing imports and fixtures; the production break they catch is losing the learner header/empty state or routing the wrong Lesson:

```tsx
it('shows the classroom header and an honest empty Unit state', () => {
  render(<UnitSelector units={[]} busy={false} onSelect={vi.fn()} />);
  expect(screen.getByText('Chưa có Unit để học.')).toBeVisible();
  expect(screen.getByRole('link', { name: /Enter Free Talk/i })).toHaveAttribute('href', '/talk');
  expect(screen.getByRole('banner')).toHaveTextContent('Luna');
});

it('keeps the authored Lesson route inside the learner frame', async () => {
  const listLessons = vi.fn().mockResolvedValue([{ lesson: 1, title: 'Chào hỏi và giới thiệu tên' }]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons } as unknown as TutorApi} />);
  expect(await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i }))
    .toHaveAttribute('href', '/grade3/unit1/lesson/1');
  expect(screen.getByRole('banner')).toHaveTextContent('Luna');
});
```

- [ ] **Step 2: Run the focused tests and confirm RED.** Run `npm test -- --run tests/web/unit-selector.test.tsx tests/web/lesson-selector.test.tsx` from `web/`. Expect missing empty-state text/header in the new assertions, not a fixture or import error.

- [ ] **Step 3: Add the presentational header and selection markup.** Create the component below, wrap each selector with `<div className="learner-app learner-picker-page">`, keep its existing `<main>` and all current controls, and render a visible empty-state paragraph only when `units.length === 0`. Keep the existing Unit and Lesson destinations and the `/design` link. Import `./learner.css` in `web/src/app/layout.tsx` beside `./globals.css`. The new CSS starts with the exact scoped tokens below, then styles `.learner-header`, `.learner-picker-page .unit-selector`, cards, and their 390px stacking/focus states. Do not style bare `body`, `h1`, or generic `.panel` in this new file.

```tsx
import type { ReactNode } from 'react';

export function LearnerHeader({ subtitle, children }: { subtitle: string; children?: ReactNode }) {
  return <header className="learner-header">
    <div className="learner-brand"><span className="learner-brand-mark" aria-hidden="true">L</span>
      <span><strong>Luna</strong><small>{subtitle}</small></span></div>
    <div className="learner-header-actions">{children}</div>
  </header>;
}
```

```tsx
<div className="learner-app learner-picker-page">
  <LearnerHeader subtitle="Gia sư tiếng Anh" />
  <main className="unit-selector">
    {units.length === 0 && <p className="learner-empty">Chưa có Unit để học.</p>}
  </main>
</div>
```

The `main` above is the wrapping pattern: retain the current Unit grid, Free Talk card, and design link between its tags. The Lesson selector uses `subtitle="Gia sư tiếng Anh · Lớp 3"` and retains its existing lesson loading/error/empty branches inside its `<main>`.

```css
.learner-app{--learner-cream:#fdf8f1;--learner-surface:#fff;--learner-coral:#ef6f4c;--learner-teal:#0f6f6c;--learner-rule:#e6dbca;color:#2a2131;background:var(--learner-cream)}
.learner-header{min-height:72px;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:10px 20px;background:var(--learner-surface);border-bottom:1px solid var(--learner-rule)}
.learner-brand{display:flex;align-items:center;gap:11px}.learner-brand-mark{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;color:#fff;background:linear-gradient(145deg,#ef6f4c,#e09a15)}
.learner-brand>span:last-child{display:grid}.learner-brand strong{font-size:19px}.learner-brand small{color:#6f6479;font-size:12px}
.learner-header-actions{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.learner-app :focus-visible{outline:3px solid var(--learner-coral);outline-offset:2px}
```

- [ ] **Step 4: Run focused and full tests.** Run the two focused files, then `npm test` from the worktree root. Expect the new tests and existing Unit/Lesson route tests to pass. Inspect `/` and `/grade3/unit1` at desktop and 390px in the worktree-served browser; verify long titles wrap instead of expanding the page.

- [ ] **Step 5: Commit only this task's files.**

```bash
git add web/src/components/LearnerHeader.tsx web/src/components/UnitSelector.tsx web/src/components/LessonSelector.tsx web/src/app/layout.tsx web/src/app/learner.css tests/web/unit-selector.test.tsx tests/web/lesson-selector.test.tsx
git commit -m "feat(web): align learner selection screens with classroom"
```

### Task 2: Free Talk setup and conversation surfaces

**Files:**
- Modify: `web/src/components/talk/TalkRoom.tsx`, `web/src/components/talk/talk.module.css`
- Test: `tests/web/talk-room.test.tsx`

**Interfaces:**
- Consumes: `LearnerHeader({ subtitle, children })` from Task 1; existing `TOPICS`, `MAX_TOPIC_LENGTH`, `PipecatVoiceProvider`, `ChatPanel`, `VoiceControls`.
- Produces: no new state API. Setup and conversation remain the two branches of `activeTopic: string | null`.

- [ ] **Step 1: Write failing Talk tests.** Add these assertions to the existing tests (keep existing provider/requestBody and teardown checks). They catch a setup page that is still a disconnected floating card, a missing active conversation region, and a whitespace topic that can start:

```tsx
it('shows classroom-like topic, work, and guide regions without fake progress', () => {
  render(<TalkRoom />);
  expect(screen.getByRole('navigation', { name: 'Chủ đề Free Talk' })).toBeVisible();
  expect(screen.getByRole('region', { name: 'Chọn chủ đề trò chuyện' })).toBeVisible();
  expect(screen.getByText('Mẹo trò chuyện')).toBeVisible();
  expect(screen.queryByText(/ngày liên tiếp|huy hiệu|điểm thưởng/i)).not.toBeInTheDocument();
});

it('will not start from whitespace only', async () => {
  const user = userEvent.setup();
  render(<TalkRoom />);
  await user.type(screen.getByLabelText('Or enter another topic'), '   ');
  expect(screen.getByRole('button', { name: 'Start Free Talk' })).toBeDisabled();
  expect(voice.provider).not.toHaveBeenCalled();
});
```

```tsx
// In the existing "renders the Pipecat transcript" test after Start:
expect(screen.getByRole('region', { name: 'Phòng trò chuyện Luna' })).toBeVisible();
expect(screen.getByText('Food')).toBeVisible();
```

- [ ] **Step 2: Run Talk tests and confirm RED.** Run `npm test -- --run tests/web/talk-room.test.tsx` from `web/`. Expect absent navigation/region/guide assertions; the whitespace test may already pass and is a guard, not the red signal.

- [ ] **Step 3: Reframe Talk markup and styles.** Replace its local header with `LearnerHeader`, retaining the back link. Put topic buttons in a left `<nav aria-label="Chủ đề Free Talk">`; put the input, helper, and Start control inside `<section aria-label="Chọn chủ đề trò chuyện">`; put only static guidance in a right aside headed `Mẹo trò chuyện`. When active, central `<section aria-label="Phòng trò chuyện Luna">` contains the current heading, `ChatPanel`, and `VoiceControls`; show the chosen topic in context. Keep `PipecatVoiceProvider` nested only under the active branch with `key={activeTopic}`, existing endpoint, `requestBody={{ topic: activeTopic }}`, and `onStopped={() => setActiveTopic(null)}`. Change topic must still call `setActiveTopic(null)`. Use the learner cream/white/coral/teal palette and responsive three-pane-to-stack styles in `talk.module.css`.

```tsx
<main className={`${styles.shell} learner-app`}>
  <LearnerHeader subtitle="Gia sư tiếng Anh · Free Talk">
    <Link href="/">Chọn Unit</Link>
  </LearnerHeader>
  <div className={styles.workspace}>
    <nav className={styles.topicRail} aria-label="Chủ đề Free Talk">
      <h2>Chọn chủ đề</h2>
      {!activeTopic ? TOPICS.map((topic) => <button type="button" key={topic}
        aria-pressed={selectedTopic === topic} onClick={() => chooseTopic(topic)}>{topic}</button>)
        : <p>{activeTopic}</p>}
    </nav>
    {!activeTopic ? <section className={styles.setup} aria-label="Chọn chủ đề trò chuyện">
      <h1 id="talk-heading">Con muốn nói về điều gì?</h1>
      <p>Luna sẽ cùng con trò chuyện từng câu một.</p>
      <label htmlFor="custom-topic">Or enter another topic</label>
      <input id="custom-topic" maxLength={MAX_TOPIC_LENGTH} value={draftTopic}
        onChange={(event) => { setDraftTopic(event.target.value); setSelectedTopic(null); }} />
      <p aria-live="polite">{normalizedTopic ? `Ready to talk about ${normalizedTopic}.` : 'Choose or enter a topic to begin.'}</p>
      <button type="button" disabled={!normalizedTopic} onClick={startRoom}>Start Free Talk</button>
    </section> : <section className={styles.conversation} aria-label="Phòng trò chuyện Luna">
      <div className={styles.conversationHeading}><h1>Talking about {activeTopic}</h1>
        <button type="button" onClick={() => setActiveTopic(null)}>Change topic</button></div>
      <PipecatVoiceProvider key={activeTopic}
        endpoint={process.env.NEXT_PUBLIC_TALK_PIPECAT_URL ?? 'http://localhost:7863'}
        requestBody={{ topic: activeTopic }}>
        <div className={styles.voiceRoom}><ChatPanel messages={[]} />
          <div className={styles.controls}><VoiceControls startLabel="Start conversation"
            stopLabel="Stop conversation" onStopped={() => setActiveTopic(null)} /></div>
        </div>
      </PipecatVoiceProvider>
    </section>}
    <aside className={styles.guide}><h2>Mẹo trò chuyện</h2><p>Con có thể nói ngắn rồi kể thêm khi sẵn sàng.</p></aside>
  </div>
</main>
```

  Keep the existing `autoComplete="off"`, custom-topic placeholder, helper class, topic/start styling hooks, and all current semantic labels when moving these blocks. Do not make topic buttons look clickable during an active connection; show the selected topic as text until Change topic returns to setup.

- [ ] **Step 4: Verify behavior and actual Talk UI.** Run focused Talk tests and `npm test`. In the worktree browser, inspect `/talk` before Start and after selecting a topic/Start at desktop and 390px. Avoid granting microphone permission during visual inspection; verify the pre-connection room and button/error affordances. Confirm Stop and Change topic reset the provider through tests.

- [ ] **Step 5: Commit only Talk files.**

```bash
git add web/src/components/talk/TalkRoom.tsx web/src/components/talk/talk.module.css tests/web/talk-room.test.tsx
git commit -m "feat(web): bring Free Talk into Luna classroom UI"
```

### Task 3: Shared classroom polish, cross-route regression, and final verification

**Files:**
- Modify: `web/src/components/TutorShell.tsx`, `web/src/app/globals.css`
- Test: `tests/web/tutor-shell.test.tsx`
- Existing uncommitted classroom files to preserve and include in the scoped final commit: `web/src/components/CurriculumNav.tsx`, `web/src/components/StateInspector.tsx`.

**Interfaces:**
- Consumes: `LearnerHeader({ subtitle, children })` from Task 1 and existing `SessionView`/Tutor API contract.
- Produces: the same `TutorShell` public props and API calls as before; no new backend contract.

- [ ] **Step 1: Write a failing header/route regression test.** In `tests/web/tutor-shell.test.tsx`, extend the direct-route test without changing its session fixture:

```tsx
expect(screen.getByRole('banner')).toHaveTextContent('Luna');
expect(screen.getByRole('link', { name: 'Free Talk Room' })).toHaveAttribute('href', '/talk');
expect(screen.getByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
```

  If the banner assertion already passes, add `expect(screen.getByRole('banner')).toHaveClass('learner-header')` as the red assertion. Existing tests pin optimistic send, error rollback, session reset, Free Talk end, and latest Luna latency placement; do not weaken them.

- [ ] **Step 2: Run the focused test and confirm RED.** Run `npm test -- --run tests/web/tutor-shell.test.tsx` from `web/`. Expect the `learner-header` class assertion to fail on the old classroom header.

- [ ] **Step 3: Reuse the header without changing Tutor session logic.** Wrap the Tutor shell in `.learner-app`; replace only the topbar brand/action markup with `LearnerHeader`. Pass the existing status pill, Free Talk link, choose-another control, and `NewSessionButton` as `children`; preserve their labels and handlers. Keep `CurriculumNav`, phases, `ChatPanel`, `Composer`, `VoiceControls`, `StateInspector`, finish/summary/error blocks and Pipecat provider in their current positions. Update only the scoped classroom CSS selectors needed to match the new header at desktop/mobile.

```tsx
<LearnerHeader subtitle={`English Tutor · Grade ${current.unit.grade} · Unit ${current.unit.unit}${current.lesson_id ? ` · Lesson ${current.lesson_id}` : ''}`}>
  <span className={`status-pill ${current.status}`}>{current.status === 'active' ? 'Đang học' : current.status}</span>
  <Link className="secondary-button" href="/talk">Free Talk Room</Link>
  <button className="secondary-button" type="button" disabled={busy} onClick={chooseAnotherUnit}>{current.lesson_id ? 'Chọn Lesson khác' : 'Choose another unit'}</button>
  <NewSessionButton busy={busy} onClick={startNew} />
</LearnerHeader>
```

Use the header above inside `<main className="app-shell classroom-shell learner-app">`; keep the existing `<div className="workspace classroom-workspace">` and all its children immediately after it. The code change is confined to the header boundary and scoped CSS.

- [ ] **Step 4: Verify all routes and isolation.** Run `npm test`, `npm run lint --workspace web`, `npm run build --workspace web`, and `git diff --check` from the worktree root. Inspect `/`, `/grade3/unit1`, `/unit1`, `/talk` setup/room at desktop and 390px in a browser served from this worktree. Compare their header/colors/spacing and check no horizontal page overflow or hidden primary controls. Open `/review` and `/design` only to confirm learner-scoped CSS did not change them. Record any browser limitation honestly.

- [ ] **Step 5: Commit the existing classroom changes plus this polish, not unrelated files.**

```bash
git add web/src/components/TutorShell.tsx web/src/components/CurriculumNav.tsx web/src/components/StateInspector.tsx web/src/app/globals.css tests/web/tutor-shell.test.tsx
git commit -m "feat(web): complete Luna learner classroom styling"
```
