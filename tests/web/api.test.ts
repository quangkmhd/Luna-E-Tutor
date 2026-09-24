import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, TutorApi } from '@/lib/api';

afterEach(() => vi.restoreAllMocks());

describe('TutorApi', () => {
  it('calls the browser fetch function with the global receiver', async () => {
    const browserFetch = vi.fn(function (this: unknown) {
      if (this !== globalThis) throw new TypeError('Illegal invocation');
      return Promise.resolve(new Response('[]', {
        status: 200, headers: { 'Content-Type': 'application/json' },
      }));
    });
    vi.stubGlobal('fetch', browserFetch);
    await expect(new TutorApi('http://test').listSessions()).resolves.toEqual([]);
  });

  it('serializes only the turn contract', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ turn_id: 't1' }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    }));
    const api = new TutorApi('http://test', fetcher);
    await api.submitTurn('s1', { turn_id: 't1', expected_state_version: 4, learner_text: 'Hello' });
    const [, init] = fetcher.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({ turn_id: 't1', expected_state_version: 4, learner_text: 'Hello' });
    expect(init.body).not.toContain('API_KEY');
  });

  it('resets to one fresh ephemeral session', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', {
      status: 200, headers: { 'Content-Type': 'application/json' },
    }));
    await new TutorApi('http://test', fetcher).resetSession('grade03.unit01');
    expect(fetcher).toHaveBeenCalledWith(
      'http://test/api/sessions/reset',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ unit_id: 'grade03.unit01' }),
      }),
    );
  });

  it('creates exactly the selected unit', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', {
      status: 200, headers: { 'Content-Type': 'application/json' },
    }));
    await new TutorApi('http://test', fetcher).createSession('grade03.unit01');
    const [, init] = fetcher.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({ unit_id: 'grade03.unit01' });
  });

  it('selects a Grade 3 lesson when supplied', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    await new TutorApi('http://test', fetcher).createSession('grade03.unit01', undefined, 1);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      unit_id: 'grade03.unit01', lesson_id: 1,
    });
  });

  it('returns stable typed server errors', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      detail: { code: 'STATE_CONFLICT', message: 'changed', retryable: false },
    }), { status: 409, headers: { 'Content-Type': 'application/json' } }));
    const api = new TutorApi('http://test', fetcher);
    await expect(api.getSession('s1')).rejects.toMatchObject({ code: 'STATE_CONFLICT', retryable: false } satisfies Partial<ApiError>);
  });

  it('forwards AbortSignal', async () => {
    const fetcher = vi.fn().mockRejectedValue(new DOMException('Aborted', 'AbortError'));
    const controller = new AbortController();
    const api = new TutorApi('http://test', fetcher);
    const request = api.listSessions(controller.signal);
    controller.abort();
    await expect(request).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetcher.mock.calls[0][1].signal).toBe(controller.signal);
  });
});
