import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TutorShell } from '@/components/TutorShell';
import { ChatPanel } from '@/components/ChatPanel';
import { ApiError, TutorApi } from '@/lib/api';
import type { SessionView, UnitSummary } from '@/lib/types';

const push = vi.fn();
const voice = vi.hoisted(() => ({ transportState: 'disconnected', phase: 'ready', micMode: 'off', elapsedSeconds: 0, stop: vi.fn().mockResolvedValue(undefined), sendText: vi.fn().mockResolvedValue(undefined) }));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

const UNITS: UnitSummary[] = [
  { id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' },
];

vi.mock('@/components/voice/PipecatVoiceProvider', () => ({
  PipecatVoiceProvider: ({ children }: { children: React.ReactNode }) => children,
  useOptionalVoiceLesson: () => ({ ttfaSeconds: 2.84, ...voice }),
  useVoiceLesson: () => voice,
}));
vi.mock('@/components/voice/VoiceControls', () => ({
  VoiceControls: () => <button type="button">Start voice lesson</button>,
}));
vi.mock('@pipecat-ai/client-react', () => ({
  usePipecatConversation: () => ({ messages: [] }),
}));

function session(changes: Partial<SessionView> = {}): SessionView {
  return {
    session_id: 's1', unit_id: 'grade03.unit01', state_version: 0,
    unit: UNITS[0],
    stage_id: 'warm-up', activity_id: 'warm-up.hello', objective_id: null,
    flashcards: [],
    status: 'active', messages: [{ role: 'teacher', text: 'Hello, Quang!' }],
    ...changes,
  };
}

function mockApi(overrides: Record<string, unknown> = {}) {
  return {
    listUnits: vi.fn().mockResolvedValue(UNITS),
    listLessons: vi.fn().mockResolvedValue([]),
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
  render(<TutorShell api={api} initialUnitId="grade03.unit01" />);
  await screen.findByText('English Tutor · Grade 3 · Unit 1');
}

describe('TutorShell', () => {
  beforeEach(() => { voice.transportState = 'disconnected'; voice.phase = 'ready'; voice.micMode = 'off'; voice.stop.mockClear(); voice.sendText.mockClear(); });
  it('keeps a classroom loading frame while a direct-route session is opening', async () => {
    let openSession: ((value: SessionView) => void) | undefined;
    const api = mockApi({
      createSession: vi.fn().mockImplementation(() => new Promise<SessionView>((resolve) => { openSession = resolve; })),
    });

    render(<TutorShell api={api} initialUnitId="grade03.unit01" initialLessonId={2} />);
    await waitFor(() => expect(openSession).toBeDefined());

    expect(screen.getByRole('status')).toHaveTextContent('Đang mở lớp học');
    expect(screen.getByRole('status').closest('main')).toHaveClass('learner-app');
    expect(screen.queryByRole('heading', { name: 'Choose a unit' })).not.toBeInTheDocument();
    openSession?.(session({ lesson_id: 2 }));
    expect(await screen.findByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
  });

  it('does not flash the Unit picker when a superseded request is aborted', async () => {
    let resolveSecond: ((value: UnitSummary[]) => void) | undefined;
    let calls = 0;
    const api = mockApi({
      listUnits: vi.fn().mockImplementation((signal: AbortSignal) => {
        calls += 1;
        if (calls === 1) return new Promise<UnitSummary[]>((_, reject) => {
          signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
        });
        return new Promise<UnitSummary[]>((resolve) => { resolveSecond = resolve; });
      }),
    });

    render(<StrictMode><TutorShell api={api} initialUnitId="grade03.unit01" /></StrictMode>);
    await waitFor(() => expect(resolveSecond).toBeDefined());
    await waitFor(() => expect(calls).toBe(2));

    expect(screen.getByRole('status')).toHaveTextContent('Đang mở lớp học');
    expect(screen.queryByRole('heading', { name: 'Choose a unit' })).not.toBeInTheDocument();
    resolveSecond?.(UNITS);
    expect(await screen.findByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
  });

  it('shows the three classroom regions using available units', async () => {
    await openLesson(mockApi());
    expect(screen.getByRole('navigation', { name: 'Chương trình học' })).toBeVisible();
    expect(screen.getByRole('button', { name: /Unit 1.*Hello/i })).toBeVisible();
    expect(screen.getByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
    expect(screen.getByLabelText('Loại hoạt động')).toHaveTextContent('warm up');
    expect(screen.getByRole('heading', { name: 'Thẻ từ vựng' })).toBeVisible();
    expect(screen.queryByRole('button', { name: /Trò chơi|Gửi hình ảnh|Nghe lại/i })).not.toBeInTheDocument();
    expect(screen.queryByText('4 ngày')).not.toBeInTheDocument();
  });

  it('keeps every Grade 3 lesson in the curriculum while Lesson 2 is active', async () => {
    const api = mockApi({
      listUnits: vi.fn().mockResolvedValue(UNITS),
      listLessons: vi.fn().mockResolvedValue([
        { lesson: 1, title: 'Chào hỏi và giới thiệu tên' },
        { lesson: 2, title: 'Hỏi thăm sức khỏe và cảm ơn' },
        { lesson: 3, title: 'Chào tạm biệt' },
      ]),
      createSession: vi.fn().mockResolvedValue(session({ lesson_id: 2 })),
    });

    render(<TutorShell api={api} initialUnitId={UNITS[0].id} initialLessonId={2} />);

    const nav = await screen.findByRole('navigation', { name: 'Chương trình học' });
    expect(await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i })).toHaveAttribute('href', '/grade3/unit1/lesson/1');
    expect(nav).toContainElement(screen.getByRole('link', { name: /Lesson 3.*Chào tạm biệt/i }));
    expect(screen.getByRole('link', { name: /Lesson 2.*Hỏi thăm sức khỏe/i })).toHaveAttribute('aria-current', 'page');
    expect(nav).not.toHaveTextContent('Lesson 2 · Đang học');
  });

  it('filters the curriculum without showing obsolete progress metrics', async () => {
    const user = userEvent.setup();
    await openLesson(mockApi());
    await user.type(screen.getByRole('searchbox', { name: 'Tìm bài học' }), 'unknown lesson');
    expect(screen.queryByRole('button', { name: /Unit 1.*Hello/i })).not.toBeInTheDocument();
    await user.clear(screen.getByRole('searchbox', { name: 'Tìm bài học' }));
    await user.type(screen.getByRole('searchbox', { name: 'Tìm bài học' }), 'Hello');
    expect(screen.getByRole('button', { name: /Unit 1.*Hello/i })).toBeVisible();
    expect(screen.queryByRole('tab', { name: 'Tiến độ' })).not.toBeInTheDocument();
    expect(screen.queryByText('12:30')).not.toBeInTheDocument();
  });
  it('opens the requested direct-route lesson without showing or selecting another unit', async () => {
    const lesson2 = session({
      session_id: 'direct-lesson-2',
      lesson_id: 2,
    });
    const api = mockApi({
      createSession: vi.fn().mockResolvedValue(lesson2),
    });

    render(<TutorShell api={api} initialUnitId="grade03.unit01" initialLessonId={2} />);

    await waitFor(() => expect(api.createSession).toHaveBeenCalledWith(
      'grade03.unit01', expect.any(AbortSignal), 2,
    ));
    const subtitle = await screen.findByText('English Tutor · Grade 3 · Unit 1 · Lesson 2');
    expect(subtitle).toBeVisible();
    expect(subtitle.closest('header')).toHaveClass('learner-header');
    expect(subtitle.closest('header')).toHaveTextContent('Luna');
    expect(screen.getByRole('link', { name: 'Free Talk Room' })).toHaveAttribute('href', '/talk');
    expect(screen.getByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Choose a unit' })).not.toBeInTheDocument();
  });

  it('uses canonical unit URLs when entering and leaving a lesson', async () => {
    const api = mockApi();
    const user = userEvent.setup();
    const view = render(<TutorShell api={api} />);

    await user.click(await screen.findByRole(
      'button', { name: /Unit 1.*Hello/i },
    ));
    expect(push).toHaveBeenCalledWith('/grade3/unit1');
    view.unmount();
    render(<TutorShell api={api} initialUnitId="grade03.unit01" />);
    await user.click(await screen.findByRole('button', { name: 'Choose another unit' }));
    expect(push).toHaveBeenCalledWith('/');
  });

  it('links to Free Talk without invoking a lesson action', async () => {
    const api = mockApi();
    render(<TutorShell api={api} initialUnitId="grade03.unit01" />);
    await screen.findByText('English Tutor · Grade 3 · Unit 1');
    const link = screen.getByRole('link', { name: 'Free Talk Room' });

    expect(link).toHaveAttribute('href', '/talk');
    expect(api.submitTurn).not.toHaveBeenCalled();
    expect(api.finishSession).not.toHaveBeenCalled();
  });

  it('hides an obsolete Grade 5 unit from the home curriculum', async () => {
    const api = mockApi({
      listUnits: vi.fn().mockResolvedValue([
        ...UNITS,
        { id: 'grade05.unit02', grade: 5, unit: 2, title: 'Our homes' },
      ]),
    });
    render(<TutorShell api={api} />);

    expect(api.createSession).not.toHaveBeenCalled();
    expect(await screen.findByRole('button', { name: /Unit 1.*Hello/i })).toBeVisible();
    expect(screen.queryByRole('button', { name: /Unit 2.*Our homes/i })).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole(
      'button', { name: /Unit 1.*Hello/i },
    ));

    expect(push).toHaveBeenCalledWith('/grade3/unit1');
    expect(api.createSession).not.toHaveBeenCalled();
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
    const view = render(<TutorShell api={api} />);
    expect(await screen.findByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
    expect(screen.getByRole('navigation', { name: 'Chương trình học' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Choose a unit' })).not.toBeInTheDocument();
    expect(api.createSession).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole(
      'button', { name: /Unit 1.*Hello/i },
    ));
    expect(api.createSession).not.toHaveBeenCalled();
    view.unmount();
    render(<TutorShell api={api} initialUnitId="grade03.unit01" />);
    expect(await screen.findByText('Hello, Quang!')).toBeVisible();
    expect(api.createSession).toHaveBeenCalledWith('grade03.unit01', expect.any(AbortSignal));
    expect(api.resetSession).not.toHaveBeenCalled();
    expect(api.listSessions).not.toHaveBeenCalled();
    expect(screen.queryByText('Session history')).not.toBeInTheDocument();
    expect(screen.getByText('warm up')).toBeVisible();
    expect(screen.getByText('Đang học')).toBeVisible();
  });

  it('shows authored vocabulary without legacy objective metrics', async () => {
    const focused = session({
      stage_id: 'practice',
      flashcards: [{ word: 'hello', meaning_vi: 'xin chào' }],
    });
    await openLesson(mockApi({ createSession: vi.fn().mockResolvedValue(focused) }));

    expect(await screen.findByRole('heading', { name: 'Thẻ từ vựng' })).toBeVisible();
    expect(screen.getAllByText('xin chào')).toHaveLength(2);
    expect(screen.queryByText('Mẫu câu cần nhớ')).not.toBeInTheDocument();
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

  it('stops Voice and sends typed input through the Text API', async () => {
    voice.transportState = 'ready';
    const api = mockApi(); const user = userEvent.setup(); await openLesson(api);
    await user.type(await screen.findByLabelText('Your answer'), 'I like dolphins');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(voice.stop).toHaveBeenCalledOnce();
    expect(api.submitTurn).toHaveBeenCalledOnce();
    expect(voice.sendText).not.toHaveBeenCalled();
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

  it('keeps the answer field focused and editable while Luna responds', async () => {
    let resolveTurn: ((value: { turn_id: string; session: SessionView }) => void) | undefined;
    const pendingTurn = new Promise<{ turn_id: string; session: SessionView }>((resolve) => { resolveTurn = resolve; });
    const api = mockApi({ submitTurn: vi.fn().mockReturnValue(pendingTurn) });
    const user = userEvent.setup();
    await openLesson(api);

    const input = screen.getByRole('textbox', { name: 'Your answer' });
    await user.type(input, 'hello');
    await user.click(screen.getByRole('button', { name: 'Send' }));

    expect(input).toHaveFocus();
    expect(input).toBeEnabled();
    expect(screen.getByRole('status')).toHaveTextContent('Luna đang nghĩ');
    await user.type(input, 'How are you?');
    expect(input).toHaveValue('How are you?');
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
    expect(api.submitTurn).toHaveBeenCalledOnce();

    resolveTurn?.({ turn_id: 't1', session: session({ state_version: 1 }) });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled());
    expect(input).toHaveValue('How are you?');
    expect(input).toHaveFocus();
  });

  it('scrolls the conversation to the latest message after messages change', async () => {
    const { rerender } = render(<ChatPanel messages={[{ role: 'teacher', text: 'Hello, Quang!' }]} />);
    const scroll = screen.getByLabelText('Conversation with Luna');
    Object.defineProperty(scroll, 'scrollHeight', { configurable: true, value: 500 });
    Object.defineProperty(scroll, 'clientHeight', { configurable: true, value: 200 });
    rerender(<ChatPanel messages={[
      { role: 'teacher', text: 'Hello, Quang!' },
      { role: 'learner', text: 'Hi, Luna!' },
    ]} />);
    expect(scroll.scrollTop).toBe(500);

    scroll.scrollTop = 0;
    fireEvent.scroll(scroll);
    rerender(<ChatPanel messages={[
      { role: 'teacher', text: 'Hello, Quang!' },
      { role: 'learner', text: 'Hi, Luna!' },
      { role: 'teacher', text: 'Nice to see you!' },
    ]} />);
    expect(scroll.scrollTop).toBe(0);
  });

  it('hides bracketed delivery cues from backend Luna messages', () => {
    render(<ChatPanel messages={[
      { role: 'teacher', text: 'Nice thinking. [pause] Can you say “city”? [long pause]' },
    ]} />);

    expect(screen.getByText('Nice thinking. Can you say “city”?')).toBeVisible();
    expect(screen.queryByText(/\[(?:long )?pause\]/i)).not.toBeInTheDocument();
  });

  it('hides language tags and cues from saved Luna messages', () => {
    render(<ChatPanel messages={[{ role: 'teacher', text: '<vi>Xin chào.</vi> <en>[long pause] HELLO</en>' }]} />);
    expect(screen.getByText('Xin chào. HELLO')).toBeVisible();
    expect(screen.queryByText(/<\/?(?:vi|en)>|\[long pause\]/)).not.toBeInTheDocument();
  });

  it('renders each YAML say line as a separate Luna turn', () => {
    render(<ChatPanel messages={[
      { role: 'teacher', text: 'Cô trò mình sang Trạm 1. [long pause]\nHELLO nghĩa là xin chào. [long pause]\n\nListen first! HELLO.\nYour turn now!' },
    ]} />);

    const rows = document.querySelectorAll('.bubble-row.teacher');
    expect(rows).toHaveLength(4);
    expect(Array.from(rows, (row) => row.querySelector('p')?.textContent)).toEqual([
      'Cô trò mình sang Trạm 1.',
      'HELLO nghĩa là xin chào.',
      'Listen first! HELLO.',
      'Your turn now!',
    ]);
    expect(Array.from(rows).every((row) => row.querySelector('.speaker')?.textContent?.includes('Luna'))).toBe(true);
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
    expect(api.resetSession).toHaveBeenCalledWith('grade03.unit01', undefined, undefined, 's1');
    expect(api.abandonSession).not.toHaveBeenCalled();
    expect(confirm).not.toHaveBeenCalled();
    expect(screen.queryByText('Session history')).not.toBeInTheDocument();
  });

});
