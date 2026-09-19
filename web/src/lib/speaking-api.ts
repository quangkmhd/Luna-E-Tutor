import { ApiError } from './api';
import type { Config, SpeakingState, Suggestions, Summary, Topic, TurnResult } from './speaking-types';

export interface SpeakingApi {
  topics(): Promise<Topic[]>;
  suggest(topic: string): Promise<Suggestions>;
  create(config: Config): Promise<SpeakingState>;
  submit(id: string, turn: {turn_id: string; text: string; expected_version: number}): Promise<TurnResult>;
  finish(id: string, version: number): Promise<Summary>;
}

export class HttpSpeakingApi implements SpeakingApi {
  constructor(private baseUrl = process.env.NEXT_PUBLIC_TUTOR_API_URL ?? 'http://localhost:8000') {}
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {headers: {'Content-Type': 'application/json'}, ...init});
    const value = await response.json();
    if (!response.ok) {
      const detail = value.detail ?? {};
      throw new ApiError(detail.code ?? 'REQUEST_FAILED', detail.message ?? 'Request failed', Boolean(detail.retryable), response.status);
    }
    return value as T;
  }
  topics() { return this.request<Topic[]>('/api/speaking/topics'); }
  suggest(topic: string) { return this.request<Suggestions>('/api/speaking/suggestions', {method: 'POST', body: JSON.stringify({topic})}); }
  create(config: Config) { return this.request<SpeakingState>('/api/speaking/sessions', {method: 'POST', body: JSON.stringify(config)}); }
  submit(id: string, turn: {turn_id: string; text: string; expected_version: number}) { return this.request<TurnResult>(`/api/speaking/sessions/${id}/turns`, {method: 'POST', body: JSON.stringify(turn)}); }
  finish(id: string, version: number) { return this.request<Summary>(`/api/speaking/sessions/${id}/finish`, {method: 'POST', body: JSON.stringify({expected_version: version})}); }
}

export const speakingApi = new HttpSpeakingApi();
