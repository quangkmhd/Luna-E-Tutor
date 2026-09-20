import type { SessionView, TurnInput, TurnResponse } from './types';

export class ApiError extends Error {
  constructor(public code: string, message: string, public retryable = false, public status = 0) {
    super(message);
    this.name = 'ApiError';
  }
}

type Fetcher = typeof fetch;

export class TutorApi {
  constructor(
    private baseUrl = process.env.NEXT_PUBLIC_TUTOR_API_URL ?? 'http://localhost:8000',
    private fetcher: Fetcher = (input, init) => globalThis.fetch(input, init),
  ) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init.headers },
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail ?? {};
      throw new ApiError(detail.code ?? 'REQUEST_FAILED', detail.message ?? 'Request failed.',
        Boolean(detail.retryable), response.status);
    }
    return payload as T;
  }

  createSession(signal?: AbortSignal) {
    return this.request<SessionView>('/api/sessions', { method: 'POST', signal });
  }
  resetSession(signal?: AbortSignal) {
    return this.request<SessionView>('/api/sessions/reset', { method: 'POST', signal });
  }
  listSessions(signal?: AbortSignal) {
    return this.request<SessionView[]>('/api/sessions', { signal });
  }
  getSession(id: string, signal?: AbortSignal) {
    return this.request<SessionView>(`/api/sessions/${id}`, { signal });
  }
  submitTurn(id: string, turn: TurnInput, signal?: AbortSignal) {
    return this.request<TurnResponse>(`/api/sessions/${id}/turns`, {
      method: 'POST', body: JSON.stringify(turn), signal,
    });
  }
  abandonSession(id: string) {
    return this.request<SessionView>(`/api/sessions/${id}/abandon`, { method: 'POST' });
  }
  finishSession(id: string, expected_state_version: number) {
    return this.request<SessionView>(`/api/sessions/${id}/finish`, {
      method: 'POST', body: JSON.stringify({ expected_state_version }),
    });
  }
}

export const tutorApi = new TutorApi();
