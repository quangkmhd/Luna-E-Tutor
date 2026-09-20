# Pipecat React Speaking Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-written speaking-room media, connection, and streaming conversation layer with the official Pipecat React SDK while preserving the lesson UI and backend learning state.

**Architecture:** A session-scoped `PipecatClientProvider` owns one client and renders `PipecatClientAudio`. The active room consumes official connection, mic, and conversation hooks. REST remains the durable curriculum store, but it no longer polls or drives live media text.

**Tech Stack:** Next.js 16, React 19, TypeScript, Vitest, Testing Library, `@pipecat-ai/client-js` 1.13.x, `@pipecat-ai/client-react` 1.8.2, SmallWebRTC.

**Spec:** `docs/superpowers/specs/2026-09-20-pipecat-react-speaking-client-design.md`

## Global Constraints

- Keep the current `/speaking` visual design and Vietnamese copy.
- `PipecatClientAudio` is the only bot-audio player; app code must not construct `Audio` or `MediaStream`.
- `usePipecatConversation` is the displayed stream; do not recreate partial/final aggregation in component state.
- Never poll REST for transcript or TTS state.
- REST remains authoritative for level, vocabulary evidence, status, summaries, and reload history.
- Preserve SmallWebRTC, the `/start` request contract, and the Soniox server pipeline.
- Stage only task-owned files because the worktree contains unrelated user changes.

## Review Focus

- Denied microphone permission must leave text input usable and expose the real error.
- Repeated final assistant updates must refresh durable state once per Pipecat message.
- Failed durable refresh must not remove completed Pipecat text.
- Changing session must disconnect the old client and seed new history exactly once.
- Typed turns during voice must appear once without re-importing all REST history.

---

### Task 1: Add the official Pipecat React provider

**Files:**
- Create: `web/src/components/speaking/SpeakingPipecatProvider.tsx`
- Create: `tests/web/speaking-pipecat-provider.test.tsx`
- Modify: `web/package.json`
- Modify: `package-lock.json`

**Interfaces:**
- Consumes: React children, `PipecatClient`, `SmallWebRTCTransport`.
- Produces: `SpeakingPipecatProvider({children}: PropsWithChildren)` with one client and one official audio component.

- [ ] **Step 1: Install the verified official package**

Run:

```bash
npm install --workspace web @pipecat-ai/client-react@1.8.2
```

Expected: package and lock files resolve client-react 1.8.2 plus `jotai`; React 19 satisfies `react >=18`.

- [ ] **Step 2: Write the failing provider test**

Create `tests/web/speaking-pipecat-provider.test.tsx`:

```tsx
import {render, screen} from '@testing-library/react';
import {expect, it, vi} from 'vitest';

const disconnect = vi.fn().mockResolvedValue(undefined);
const clients: unknown[] = [];
vi.mock('@pipecat-ai/client-js', () => ({
  PipecatClient: class {
    disconnect = disconnect;
    constructor(options: unknown) { clients.push(options); }
  },
}));
vi.mock('@pipecat-ai/client-react', () => ({
  PipecatClientProvider: ({children}: {children: React.ReactNode}) =>
    <div data-testid="provider">{children}</div>,
  PipecatClientAudio: () => <div data-testid="pipecat-audio" />,
}));
vi.mock('@pipecat-ai/small-webrtc-transport', () => ({SmallWebRTCTransport: class {}}));

import {SpeakingPipecatProvider} from '@/components/speaking/SpeakingPipecatProvider';

it('provides one client and delegates audio to PipecatClientAudio', () => {
  const {rerender, unmount} = render(
    <SpeakingPipecatProvider><span>room</span></SpeakingPipecatProvider>,
  );
  rerender(<SpeakingPipecatProvider><span>room again</span></SpeakingPipecatProvider>);
  expect(clients).toHaveLength(1);
  expect(screen.getByTestId('provider')).toContainElement(screen.getByTestId('pipecat-audio'));
  unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});
```

- [ ] **Step 3: Verify RED**

Run `npm run test --workspace web -- tests/web/speaking-pipecat-provider.test.tsx`.

Expected: FAIL because the provider module does not exist.

- [ ] **Step 4: Implement the provider**

Create `SpeakingPipecatProvider.tsx`:

```tsx
'use client';
import {PipecatClient} from '@pipecat-ai/client-js';
import {PipecatClientAudio, PipecatClientProvider} from '@pipecat-ai/client-react';
import {SmallWebRTCTransport} from '@pipecat-ai/small-webrtc-transport';
import {PropsWithChildren, useEffect, useMemo} from 'react';

export function SpeakingPipecatProvider({children}: PropsWithChildren) {
  const client = useMemo(() => new PipecatClient({
    transport: new SmallWebRTCTransport(), enableMic: true, enableCam: false,
  }), []);
  useEffect(() => () => { void client.disconnect(); }, [client]);
  return <PipecatClientProvider client={client}>
    {children}<PipecatClientAudio />
  </PipecatClientProvider>;
}
```

Do not enable automatic device initialization; permission follows a user click.

- [ ] **Step 5: Verify GREEN and commit**

Run the targeted test; expect PASS. Then:

```bash
git add web/package.json package-lock.json web/src/components/speaking/SpeakingPipecatProvider.tsx tests/web/speaking-pipecat-provider.test.tsx
git commit -m "feat: add official Pipecat React provider"
```

---

### Task 2: Replace the custom connection state machine

**Files:**
- Modify: `web/src/components/speaking/VoiceControls.tsx`
- Modify: `tests/web/voice-controls.test.tsx`

**Interfaces:**
- Consumes: ambient provider, `sessionId: string`, `onConnectionError(message: string): void`.
- Produces: a control driven by Pipecat transport and mic hooks; it owns no audio or transcript logic.

- [ ] **Step 1: Write official-hook fakes and failing tests**

Replace the `SpeakingVoiceClient` mock with:

```tsx
const initDevices = vi.fn().mockResolvedValue(undefined);
const startBotAndConnect = vi.fn().mockResolvedValue({});
const enableMic = vi.fn();
let transportState = 'disconnected';
let isMicEnabled = true;

vi.mock('@pipecat-ai/client-js', () => ({
  TransportStateEnum: {
    DISCONNECTED: 'disconnected', INITIALIZING: 'initializing',
    CONNECTING: 'connecting', CONNECTED: 'connected', READY: 'ready',
    DISCONNECTING: 'disconnecting', ERROR: 'error',
  },
}));
vi.mock('@pipecat-ai/client-react', () => ({
  usePipecatClient: () => ({initDevices, startBotAndConnect}),
  usePipecatClientTransportState: () => transportState,
  usePipecatClientMicControl: () => ({enableMic, isMicEnabled}),
}));
```

Test three literal behaviors: disconnected click calls `initDevices` then `startBotAndConnect` with endpoint, body, and timeout; ready click calls `enableMic(false)` without reconnecting; rejected permission calls `onConnectionError('Microphone permission denied')`.

- [ ] **Step 2: Verify RED**

Run `npm run test --workspace web -- tests/web/voice-controls.test.tsx`.

Expected: FAIL because the component still imports the custom wrapper and owns an `off/connecting/on` state machine.

- [ ] **Step 3: Implement with official hooks**

Use these imports and state derivation:

```tsx
import {TransportStateEnum} from '@pipecat-ai/client-js';
import {
  usePipecatClient,
  usePipecatClientMicControl,
  usePipecatClientTransportState,
} from '@pipecat-ai/client-react';

const client = usePipecatClient();
const state = usePipecatClientTransportState();
const {enableMic, isMicEnabled} = usePipecatClientMicControl();
const connected = state === TransportStateEnum.CONNECTED || state === TransportStateEnum.READY;
const pending = state === TransportStateEnum.INITIALIZING || state === TransportStateEnum.CONNECTING;
```

When disconnected, clear the error, call `client.initDevices()`, then:

```tsx
await client.startBotAndConnect({
  endpoint: process.env.NEXT_PUBLIC_SPEAKING_VOICE_URL
    ?? `${window.location.protocol}//${window.location.hostname}:7860/start`,
  requestData: {body: {speaking_session_id: sessionId}},
  timeout: 10_000,
});
```

When connected, call `enableMic(!isMicEnabled)`. Derive the Vietnamese label from `pending`, `connected`, and `isMicEnabled`. Do not add callbacks, intervals, media tracks, or local transport enums.

- [ ] **Step 4: Verify GREEN and commit**

Run the targeted test; expect PASS. Then:

```bash
git add web/src/components/speaking/VoiceControls.tsx tests/web/voice-controls.test.tsx
git commit -m "refactor: use Pipecat hooks for voice controls"
```

---

### Task 3: Use the official conversation store for all chat rendering

**Files:**
- Create: `web/src/components/speaking/ActiveSpeakingRoom.tsx`
- Create: `tests/web/active-speaking-room.test.tsx`
- Modify: `web/src/components/speaking/SpeakingRoom.tsx`
- Modify: `tests/web/speaking-room.test.tsx`

**Interfaces:**
- Consumes: `initialSession: SpeakingState`, `api: SpeakingApi`.
- Produces: active lesson UI rendered from `usePipecatConversation().messages`; REST state supplies metadata and persistence only.

- [ ] **Step 1: Create a complete official-conversation fake**

The test fake must return `{messages, injectMessage, botOutputEvents: new Map()}`. Each message contains `role`, `final`, `createdAt`, and complete `parts`; each part contains `text`, `final`, and `createdAt`. Capture `onMessageUpdated` so tests can deliver finalized assistant messages.

- [ ] **Step 2: Write failing behavior tests**

Add tests proving:

1. Persisted `initialSession.messages` are injected once even after rerender.
2. `{spoken: 'The rabbit ', unspoken: 'is gentle.'}` renders as `The rabbit is gentle.` in one assistant bubble.
3. Calling `onMessageUpdated` twice with the same final assistant message calls `api.get` once and updates `Level 2`.
4. If `api.get` rejects with `sync failed`, the completed `Good job.` message remains visible and the error appears.
5. A typed `I like rabbits` submission injects exactly one final user message and one final assistant message; it does not import the returned full REST history.

The production mutations caught are custom partial state, premature clearing, repeated completion refreshes, and duplicate typed exchanges.

- [ ] **Step 3: Verify RED**

Run `npm run test --workspace web -- tests/web/active-speaking-room.test.tsx`.

Expected: FAIL because the module does not exist.

- [ ] **Step 4: Implement conversion and seeding**

Use official `ConversationMessage`, `ConversationMessagePart`, and `BotOutputText` types. Convert text with:

```tsx
function partText(text: ReactNode | BotOutputText): ReactNode {
  if (typeof text === 'object' && text !== null && 'spoken' in text && 'unspoken' in text) {
    return `${text.spoken}${text.unspoken}`;
  }
  return text;
}
```

Seed initial REST history through `injectMessage`, mapping `teacher` to `assistant` and `learner` to `user`. Use `seededSessionId.current` so one session seeds once. Give persisted parts stable final timestamps derived from message order.

- [ ] **Step 5: Implement completion synchronization without polling**

Use a stable callback and completed-message set:

```tsx
const synchronized = useRef(new Set<string>());
const onMessageUpdated = useCallback((message: ConversationMessage) => {
  if (message.role !== 'assistant' || !message.final) return;
  if (synchronized.current.has(message.createdAt)) return;
  synchronized.current.add(message.createdAt);
  void api.get(session.session_id).then((value) => {
    setSession(value);
    setError('');
  }).catch((error) => {
    synchronized.current.delete(message.createdAt);
    setError(error instanceof Error ? error.message : String(error));
  });
}, [api, session.session_id]);
```

Call `usePipecatConversation({onMessageUpdated})`. Never clear an official conversation message after refresh.

- [ ] **Step 6: Move active UI and typed submission**

Move the post-session JSX and handlers from `SpeakingRoom` into `ActiveSpeakingRoom`. Render official conversation parts. After text `api.submit` succeeds, inject only the submitted user text and `result.reply.text`, both final, then update session metadata from `result.state`. Do not replace the official conversation from `result.state.messages`.

Keep summary, vocabulary evidence, level, status, and finish behavior based on local session metadata. Pass `setError` to `VoiceControls` as `onConnectionError`.

- [ ] **Step 7: Add the session-scoped provider boundary**

When setup has a session, `SpeakingRoom` returns:

```tsx
<SpeakingPipecatProvider key={session.session_id}>
  <ActiveSpeakingRoom initialSession={session} api={api} />
</SpeakingPipecatProvider>
```

The key makes a session switch disconnect the old client, reset Pipecat conversation state, and seed the new history once.

- [ ] **Step 8: Verify GREEN and commit**

Run:

```bash
npm run test --workspace web -- tests/web/active-speaking-room.test.tsx tests/web/speaking-room.test.tsx
```

Expected: PASS without duplicate bubbles or timer warnings. Then commit only the four task files with message `refactor: use Pipecat conversation state in speaking room`.

---

### Task 4: Delete the legacy wrapper and verify the complete migration

**Files:**
- Delete: `web/src/lib/speaking-voice.ts`
- Delete: `tests/web/speaking-voice.test.ts`
- Modify: `web/README.md`
- Modify: `tests/web/hydration-guard.test.tsx` only if the provider boundary changes its mocks.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: one official Pipecat React media path with no app-owned audio lifecycle.

- [ ] **Step 1: Add the final provider regression test**

In the provider test, stub the global `Audio` constructor, render/unmount the provider with its mocked `PipecatClientAudio`, and assert the application did not invoke `new Audio()`. This tests the ownership boundary; Pipecat's package owns its internal audio implementation.

- [ ] **Step 2: Run the provider test**

Run `npm run test --workspace web -- tests/web/speaking-pipecat-provider.test.tsx`.

Expected: PASS before legacy deletion.

- [ ] **Step 3: Delete obsolete files and audit remaining code**

Delete both wrapper files with `apply_patch`, then run:

```bash
rg -n "SpeakingVoiceClient|new Audio\(|new MediaStream\(|setInterval\(" web/src tests/web
```

Expected: no speaking voice wrapper, app-owned audio, or voice polling matches. Review unrelated matches instead of deleting them.

- [ ] **Step 4: Update operational documentation**

Document in `web/README.md`:

- client-react owns context, media state, conversation aggregation, and bot audio;
- SmallWebRTC uses `NEXT_PUBLIC_SPEAKING_VOICE_URL` or the page host on port 7860;
- REST stores curriculum/history and is not polled for live transcript/TTS;
- remote browser access still requires the voice endpoint to be reachable by forwarding or proxying.

- [ ] **Step 5: Run complete automated verification**

Run separately and require exit code 0:

```bash
npm test
npm run lint --workspace web
npm run build --workspace web
```

- [ ] **Step 6: Run live acceptance**

Restart the web process after dependency installation. In a fresh speaking session verify: permission begins on click; one growing user message; one growing Luna message; no disappearing message; mute does not reconnect; one audible assistant response; one typed exchange; new session has no previous live conversation.

If automation cannot exercise the physical microphone, report acoustic echo as a manual check rather than claiming it from unit tests.

- [ ] **Step 7: Commit cleanup**

Stage only changed task files, verify `git status --short`, and commit with:

```bash
git commit -m "refactor: remove custom speaking media client"
```
