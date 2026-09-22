# Luna learner interface redesign

## Purpose and scope

Make every learner-facing web route feel like the reference classroom in `/home/quangnhvn34/dev/massko/E-Voice-Tutor-v1/docs/ban-A-lop-hoc-mina.html` and the user-provided screenshot, while preserving the real teaching and voice flows. The reference file is user-owned in the original checkout and is not copied into this worktree. Keep Luna's name, the existing Roboto font, and responsive use on desktop and mobile. The approved scope is `/`, `/grade3/unit1`, `/grade3/unit1/lesson/[lessonId]`, `/[unitSlug]`, and `/talk`. `/review` and `/design` stay visually and functionally unchanged.

The reference is a visual guide, not a source of product data or behavior. Do not copy its sample grades, learner progress, streak, clock, reward, image/audio cards, upload, or games into the live UI without a real source and working action.

## Visual system

Use one learner-only visual system: warm cream canvas, white surfaces, coral primary actions, teal learning state, compact rounded controls, fine dividers, and the same Luna/student header treatment. Reuse spacing, colors, focus states, and responsive breakpoints across learner routes. Scope rules to learner components so they do not restyle `/review` or `/design`.

At wide widths, use the reference's left navigation / central work area / right context rhythm where the content warrants it. The central task must stay dominant. On narrow screens, stack or collapse secondary panes while leaving primary controls, navigation, topic selection, chat, and voice accessible without horizontal page overflow.

## Learner routes and states

### Unit and Lesson selection

`/` displays available Unit choices grouped by the real grade and Unit data returned by the existing API. Keep Free Talk and the design-document destination as separate links, but present them in the learner visual system; following `/design` does not change that document's own page. `/grade3/unit1` displays the authored lessons returned by the existing lessons API. Empty/loading/error states remain explicit and usable. Selecting a Unit or Lesson must keep the current canonical route and session-creation behavior.

### Lesson classroom

Keep the three-pane classroom already implemented in this worktree. Its curriculum rail uses available Units, the center retains the actual session chat and voice/text controls, and the right pane shows learning targets and progress from the current session. Do not manufacture completion values. Retain the current Unit navigation, new-session, Free Talk, finish, summary, errors, and active/completed guards. Align the header, controls, labels, and mobile behavior with the selection and Talk routes.

### Free Talk setup

`/talk` before starting uses the same learner header and classroom-like composition rather than a disconnected floating card. The left side presents the existing suggested topics; the main area explains the choice and contains the custom-topic input and the Start action; a secondary context area may offer concise, static speaking guidance, clearly distinct from measured progress. Suggested-topic selection and the custom input must remain mutually understandable. Trim a custom topic, require a non-empty value, and retain the 120-character limit.

### Free Talk conversation

After Start, keep the chosen topic visible and make the central conversation the focal area. Reuse `ChatPanel` and the existing `PipecatVoiceProvider`/`VoiceControls` contract: Talk endpoint, `{ topic }` request body, separate voice state, start/stop controls, and errors. Change topic and Stop must continue to unmount the prior voice provider so a new topic starts with a fresh transcript store. No lesson-specific progress, vocabulary, or session status may be implied for standalone Talk.

## Component and data boundaries

Extract only small presentational learner primitives where sharing avoids drift (for example header, colors/tokens, section framing). Keep `TutorShell` responsible for Tutor session API state and `TalkRoom` responsible for topic state; no new cross-flow state container or backend endpoint. Reuse existing `ChatPanel` and voice components rather than duplicating their behavior. Keep real Unit/Lesson and session data as the only source for curriculum and progress. Keep suggested topics as the existing local Talk choices.

## Failure and accessibility behavior

Preserve loading, empty, and API-error feedback. A failed Tutor turn must restore the previous session view, as it does now. Voice connection and device errors remain visible. All links and actions need visible focus, semantic labels, and keyboard access; active tabs, selected topics, and current learning location must be exposed to assistive technology. Mobile controls must remain reachable when the keyboard or long chat occupies the screen.

## Verification

Add or update component tests for the learner-facing route states and behavior contracts, including Unit/Lesson navigation, topic selection/custom input, Talk provider creation and teardown, real-data-only context panels, and absence of nonfunctional reference controls. Run the full web test suite, lint, TypeScript/Next build, and `git diff --check` from the worktree. Inspect the actual worktree-served UI at desktop and mobile widths for `/`, `/grade3/unit1`, a Tutor route, `/talk` setup, and `/talk` conversation. `/review` and `/design` should be checked for unintended global-style changes but not redesigned.
