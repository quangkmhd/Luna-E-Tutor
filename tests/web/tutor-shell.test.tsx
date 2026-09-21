import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TutorShell } from '@/components/TutorShell';
import { ChatPanel } from '@/components/ChatPanel';
import { ApiError, TutorApi } from '@/lib/api';
import type { SessionView, UnitSummary } from '@/lib/types';

const push = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

const UNITS: UnitSummary[] = [
  { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
  { id: 'grade05.unit02', grade: 5, unit: 2, title: 'Our homes' },
];

vi.mock('@/components/voice/PipecatVoiceProvider', () => ({
  PipecatVoiceProvider: ({ children }: { children: React.ReactNode }) => children,
  useOptionalVoiceLesson: () => ({ ttfaSeconds: 2.84 }),
}));
vi.mock('@/components/voice/VoiceControls', () => ({
  VoiceControls: () => <button type="button">Start voice lesson</button>,
}));
vi.mock('@pipecat-ai/client-react', () => ({
  usePipecatConversation: () => ({ messages: [] }),
}));

function session(changes: Partial<SessionView> = {}): SessionView {
  return {
    session_id: 's1', unit_id: 'grade05.unit01', state_version: 0,
    unit: UNITS[0],
    stage_id: 'warm-up', activity_id: 'warm-up.hello', objective_id: null,
    learning_focus: [{
      stage_id: 'lesson-01', stage_title: 'Lesson 01',
      target_words: ['class'], target_patterns: ['I am in Class ___.'], highlighted: true,
    }],
    status: 'active', messages: [{ role: 'teacher', text: 'Hello, Quang!' }],
    review_queue: [], objective_progress: [], last_evidence: null,
    last_decision: null, summary: null, ...changes,
  };
}

function mockApi(overrides: Record<string, unknown> = {}) {
  return {
    listUnits: vi.fn().mockResolvedValue(UNITS),
    listSessions: vi.fn().mockResolvedValue([]),
    createSession: vi.fn().mockResolvedValue(session()),
    resetSession: vi.fn().mockResolvedValue(session()),
    getSession: vi.fn().mockResolvedValue(session()),
    submitTurn: vi.fn().mockResolvedValue({ turn_id: 't1', session: session({
      state_version: 1,
      messages: [{ role: 'teacher', text: 'Hello, Quang!' }, { role: 'learner', text: 'Hi' }, { role: 'teacher', text: 'Nice to see you!' }],
    }) }),
    abandonSession: vi.fn().mockResolvedValue(session({ status: 'abandoned' })),
    finishSession: vi.fn().mockResolvedValue(session({ status: 'completed' })),
    ...overrides,
  } as unknown as TutorApi;
}

async function openLesson(api: TutorApi) {
  render(<TutorShell api={api} />);
  await userEvent.click(await screen.findByRole(
    'button', { name: /Unit 1.*All about me!/i },
  ));
}

describe('TutorShell', () => {
  it('opens the requested direct-route unit without showing or selecting another unit', async () => {
    const unit2 = session({
      session_id: 'direct-unit-2',
      unit_id: 'grade05.unit02',
      unit: UNITS[1],
    });
    const api = mockApi({
      createSession: vi.fn().mockResolvedValue(unit2),
    });

    render(<TutorShell api={api} initialUnitId="grade05.unit02" />);

    await waitFor(() => expect(api.createSession).toHaveBeenCalledWith(
      'grade05.unit02', expect.any(AbortSignal),
    ));
    expect(await screen.findByText('English Tutor · Unit 2')).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Choose a unit' })).not.toBeInTheDocument();
  });

  it('uses canonical unit URLs when entering and leaving a lesson', async () => {
    const api = mockApi();
    const user = userEvent.setup();
    render(<TutorShell api={api} />);

    await user.click(await screen.findByRole(
      'button', { name: /Unit 1.*All about me!/i },
    ));
    expect(push).toHaveBeenCalledWith('/unit1');

    await user.click(await screen.findByRole('button', { name: 'Choose another unit' }));
    expect(push).toHaveBeenCalledWith('/');
  });

  it('links to Free Talk without invoking a lesson action', async () => {
    const api = mockApi();
    render(<TutorShell api={api} />);
    await userEvent.click(await screen.findByRole(
      'button', { name: /Unit 1.*All about me!/i },
    ));
    const link = screen.getByRole('link', { name: 'Free Talk Room' });

    expect(link).toHaveAttribute('href', '/talk');
    expect(api.submitTurn).not.toHaveBeenCalled();
    expect(api.finishSession).not.toHaveBeenCalled();
  });

  it('starts Unit 2 only after the learner selects it', async () => {
    const unit2 = session({
      session_id: 'unit-2',
      unit_id: 'grade05.unit02',
      unit: UNITS[1],
    });
    const api = mockApi({
      createSession: vi.fn().mockResolvedValue(unit2),
    });
    render(<TutorShell api={api} />);

    expect(api.createSession).not.toHaveBeenCalled();
    await userEvent.click(await screen.findByRole(
      'button', { name: /Unit 2.*Our homes/i },
    ));

    expect(api.createSession).toHaveBeenCalledWith('grade05.unit02');
    expect(await screen.findByText('Our homes')).toBeVisible();
    expect(screen.getByText('English Tutor · Unit 2')).toBeVisible();
    expect(screen.queryByText('All about me!')).not.toBeInTheDocument();
  });

  it('shows latency beside Luna on the latest teacher message', async () => {
    await openLesson(mockApi());

    const heading = await screen.findByRole('heading', { name: /Practice with Luna/ });
    expect(heading).not.toHaveTextContent('2.84s');
    const greeting = screen.getByText('Hello, Quang!').closest('.bubble');
    expect(greeting?.querySelector('.speaker')).toHaveTextContent('Luna2.84s');
  });

  it('starts with a fresh session and renders the server greeting without history', async () => {
    const api = mockApi();
    render(<TutorShell api={api} />);
    expect(await screen.findByRole('heading', { name: 'Choose a unit' })).toBeVisible();
    expect(api.createSession).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole(
      'button', { name: /Unit 1.*All about me!/i },
    ));
    expect(await screen.findByText('Hello, Quang!')).toBeVisible();
    expect(api.createSession).toHaveBeenCalledWith('grade05.unit01');
    expect(api.resetSession).not.toHaveBeenCalled();
    expect(api.listSessions).not.toHaveBeenCalled();
    expect(screen.queryByText('Session history')).not.toBeInTheDocument();
    expect(screen.getByText('warm up')).toBeVisible();
    expect(screen.getByText('Lesson 01')).toBeVisible();
    expect(screen.getByText('Đang học tiếp')).toBeVisible();
  });

  it('shows the current learning focus without technical teaching state', async () => {
    const focused = session({
      stage_id: 'lesson-01',
      learning_focus: [
        {
          stage_id: 'lesson-01', stage_title: 'Lesson 01',
          target_words: ['building', 'flat', 'house', 'tower'],
          target_patterns: ["Do you live in this/that ___? – Yes, I do./No, I don't."],
          highlighted: true,
        },
        {
          stage_id: 'lesson-02', stage_title: 'Lesson 02',
          target_words: ['road'], target_patterns: ['What is your address?'],
          highlighted: false,
        },
      ],
    });
    await openLesson(mockApi({ createSession: vi.fn().mockResolvedValue(focused) }));

    expect(await screen.findByRole('heading', { name: 'Nội dung cần học' })).toBeVisible();
    expect(screen.getAllByText('Chặng')).toHaveLength(2);
    expect(screen.getByText('Lesson 01')).toBeVisible();
    expect(screen.getByText('Lesson 02')).toBeVisible();
    expect(screen.getAllByText('Từ / cấu trúc trọng tâm')).toHaveLength(2);
    expect(screen.getByText('building')).toBeVisible();
    expect(screen.getByText("Do you live in this/that ___? – Yes, I do./No, I don't.")).toBeVisible();
    expect(screen.queryByText('Chưa có từ hoặc cấu trúc mới ở chặng này.')).not.toBeInTheDocument();
    expect(screen.queryByText('Activity')).not.toBeInTheDocument();
    expect(screen.queryByText('Objective')).not.toBeInTheDocument();
    expect(screen.queryByText('Version')).not.toBeInTheDocument();
    expect(screen.queryByText('Last decision')).not.toBeInTheDocument();
    expect(screen.queryByText('Evidence')).not.toBeInTheDocument();
  });

  it('submits once while locked and renders the returned teacher turn', async () => {
    const api = mockApi(); const user = userEvent.setup(); await openLesson(api);
    const input = await screen.findByLabelText('Your answer');
    await user.type(input, 'Hi');
    await user.dblClick(screen.getByRole('button', { name: 'Send' }));
    expect(api.submitTurn).toHaveBeenCalledOnce();
    expect(await screen.findByText('Nice to see you!')).toBeVisible();
  });

  it('does not submit a typed API turn when voice starts', async () => {
    const api = mockApi(); const user = userEvent.setup(); await openLesson(api);
    const voiceButton = await screen.findByRole('button', { name: 'Start voice lesson' });
    expect(voiceButton.closest('form')).toHaveClass('composer');
    expect(screen.queryByText('Prefer typing?')).not.toBeInTheDocument();
    await user.click(voiceButton);
    expect(api.submitTurn).not.toHaveBeenCalled();
  });

  it('shows Quang’s message while the teacher response is still pending', async () => {
    let resolveTurn: ((value: { turn_id: string; session: SessionView }) => void) | undefined;
    const pendingTurn = new Promise<{ turn_id: string; session: SessionView }>((resolve) => { resolveTurn = resolve; });
    const api = mockApi({ submitTurn: vi.fn().mockReturnValue(pendingTurn) });
    const user = userEvent.setup();
    await openLesson(api);

    await user.type(await screen.findByLabelText('Your answer'), 'I am in Class 5A.');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(screen.getByText('I am in Class 5A.')).toBeVisible();
    resolveTurn?.({ turn_id: 't1', session: session({ state_version: 1, messages: [
      { role: 'teacher', text: 'Hello, Quang!' },
      { role: 'learner', text: 'I am in Class 5A.' },
      { role: 'teacher', text: 'Nice to see you!' },
    ] }) });
    expect(await screen.findByText('Nice to see you!')).toBeVisible();
  });

  it('scrolls the conversation to the latest message after messages change', async () => {
    const scrollIntoView = vi.fn();
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true, value: scrollIntoView,
    });
    const { rerender } = render(<ChatPanel messages={[{ role: 'teacher', text: 'Hello, Quang!' }]} />);
    rerender(<ChatPanel messages={[
      { role: 'teacher', text: 'Hello, Quang!' },
      { role: 'learner', text: 'Hi, Luna!' },
    ]} />);

    await waitFor(() => expect(scrollIntoView).toHaveBeenLastCalledWith({ behavior: 'smooth', block: 'end' }));
  });

  it('hides bracketed delivery cues from backend Luna messages', () => {
    render(<ChatPanel messages={[
      { role: 'teacher', text: 'Nice thinking. [pause] Can you say “city”? [long pause]' },
    ]} />);

    expect(screen.getByText('Nice thinking. Can you say “city”?')).toBeVisible();
    expect(screen.queryByText(/\[(?:long )?pause\]/i)).not.toBeInTheDocument();
  });

  it('shows retryable provider errors without inventing a message', async () => {
    const api = mockApi({ submitTurn: vi.fn().mockRejectedValue(new ApiError('PROVIDER_UNAVAILABLE', 'Provider down', true, 503)) });
    const user = userEvent.setup(); await openLesson(api);
    await user.type(await screen.findByLabelText('Your answer'), 'Hi');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Please try again. Provider down');
    expect(screen.queryByText('Nice to see you!')).not.toBeInTheDocument();
  });

  it('starts over immediately without preserving or abandoning the active session', async () => {
    const replacement = session({ session_id: 's2' });
    const api = mockApi({ resetSession: vi.fn().mockResolvedValue(replacement) });
    const confirm = vi.spyOn(window, 'confirm');
    const user = userEvent.setup(); await openLesson(api);
    await screen.findByText('Hello, Quang!');
    await user.click(screen.getByRole('button', { name: /New session/i }));
    await waitFor(() => expect(api.resetSession).toHaveBeenCalledOnce());
    expect(api.resetSession).toHaveBeenCalledWith('grade05.unit01');
    expect(api.abandonSession).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
    expect(screen.queryByText('Session history')).not.toBeInTheDocument();
  });

  it('shows the manual end control only in Free Talk and displays summary', async () => {
    const free = session({ stage_id: 'free-talk', activity_id: 'free-talk.conversation' });
    const done = session({ stage_id: 'free-talk', status: 'completed', summary: { demonstrated: ['city'], supported: [], needs_review: ['hobby'], not_yet_observed: [] } });
    const api = mockApi({ createSession: vi.fn().mockResolvedValue(free), finishSession: vi.fn().mockResolvedValue(done) });
    const user = userEvent.setup(); await openLesson(api);
    await user.click(await screen.findByRole('button', { name: 'End Free Talk' }));
    expect(await screen.findByText('What Quang showed today')).toBeVisible();
    expect(screen.getByText('Demonstrated: city')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'End Free Talk' })).not.toBeInTheDocument();
  });
});
