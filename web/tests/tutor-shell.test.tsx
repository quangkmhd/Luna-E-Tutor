import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TutorShell } from '@/components/TutorShell';
import { ApiError, TutorApi } from '@/lib/api';
import type { SessionView } from '@/lib/types';

function session(changes: Partial<SessionView> = {}): SessionView {
  return {
    session_id: 's1', unit_id: 'grade05.unit01', state_version: 0,
    stage_id: 'warm-up', activity_id: 'warm-up.hello', objective_id: null,
    status: 'active', messages: [{ role: 'teacher', text: 'Hello, Quang!' }],
    review_queue: [], objective_progress: [], last_evidence: null,
    last_decision: null, summary: null, ...changes,
  };
}

function mockApi(overrides: Record<string, unknown> = {}) {
  return {
    listSessions: vi.fn().mockResolvedValue([]),
    createSession: vi.fn().mockResolvedValue(session()),
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

describe('TutorShell', () => {
  it('creates a first session and renders the server greeting', async () => {
    const api = mockApi(); render(<TutorShell api={api} />);
    expect(await screen.findByText('Hello, Quang!')).toBeVisible();
    expect(api.createSession).toHaveBeenCalledOnce();
    expect(screen.getAllByText('warm up')).toHaveLength(2);
  });

  it('submits once while locked and renders the returned teacher turn', async () => {
    const api = mockApi(); const user = userEvent.setup(); render(<TutorShell api={api} />);
    const input = await screen.findByLabelText('Your answer');
    await user.type(input, 'Hi');
    await user.dblClick(screen.getByRole('button', { name: 'Send' }));
    expect(api.submitTurn).toHaveBeenCalledOnce();
    expect(await screen.findByText('Nice to see you!')).toBeVisible();
  });

  it('shows retryable provider errors without inventing a message', async () => {
    const api = mockApi({ submitTurn: vi.fn().mockRejectedValue(new ApiError('PROVIDER_UNAVAILABLE', 'Provider down', true, 503)) });
    const user = userEvent.setup(); render(<TutorShell api={api} />);
    await user.type(await screen.findByLabelText('Your answer'), 'Hi');
    await user.click(screen.getByRole('button', { name: 'Send' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Please try again. Provider down');
    expect(screen.queryByText('Nice to see you!')).not.toBeInTheDocument();
  });

  it('resumes history and confirms before abandoning an active session', async () => {
    const old = session({ session_id: 'old', status: 'completed', stage_id: 'lesson-01' });
    const api = mockApi({ listSessions: vi.fn().mockResolvedValue([session(), old]) });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup(); render(<TutorShell api={api} />);
    await screen.findByText('Session history');
    await user.click(screen.getByRole('button', { name: /New session/i }));
    await waitFor(() => expect(api.abandonSession).toHaveBeenCalledWith('s1'));
    expect(api.createSession).toHaveBeenCalledOnce();
  });

  it('shows the manual end control only in Free Talk and displays summary', async () => {
    const free = session({ stage_id: 'free-talk', activity_id: 'free-talk.conversation' });
    const done = session({ stage_id: 'free-talk', status: 'completed', summary: { demonstrated: ['city'], supported: [], needs_review: ['hobby'], not_yet_observed: [] } });
    const api = mockApi({ listSessions: vi.fn().mockResolvedValue([free]), finishSession: vi.fn().mockResolvedValue(done) });
    const user = userEvent.setup(); render(<TutorShell api={api} />);
    await user.click(await screen.findByRole('button', { name: 'End Free Talk' }));
    expect(await screen.findByText('What Quang showed today')).toBeVisible();
    expect(screen.getByText('Demonstrated: city')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'End Free Talk' })).not.toBeInTheDocument();
  });
});
