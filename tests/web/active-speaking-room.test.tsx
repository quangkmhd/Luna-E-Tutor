import {act, render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach, expect, it, vi} from 'vitest';

import {ActiveSpeakingRoom} from '@/components/speaking/ActiveSpeakingRoom';
import type {SpeakingApi} from '@/lib/speaking-api';
import type {SpeakingState} from '@/lib/speaking-types';

const injectMessage = vi.fn();
let conversationMessages: Array<Record<string, unknown>> = [];
let onMessageUpdated: ((message: Record<string, unknown>) => void) | undefined;

vi.mock('@pipecat-ai/client-react', () => ({
  usePipecatConversation: (options?: {onMessageUpdated?: (message: Record<string, unknown>) => void}) => {
    onMessageUpdated = options?.onMessageUpdated;
    return {messages: conversationMessages, injectMessage, botOutputEvents: new Map()};
  },
}));

vi.mock('@/components/speaking/VoiceControls', () => ({
  VoiceControls: () => <button type="button">Bật micro</button>,
}));

function state(overrides: Partial<SpeakingState> = {}): SpeakingState {
  return {
    session_id: 's1',
    config: {grade: 5, topic: 'Animals', words: ['rabbit']},
    version: 0,
    status: 'active',
    level: 1,
    independent_streak: 0,
    difficulty_streak: 0,
    word_evidence: [],
    last_delivered_text: 'Hello',
    opening_message: 'Hello',
    messages: [{role: 'teacher', text: 'Hello'}],
    ...overrides,
  };
}

function api(overrides: Partial<SpeakingApi> = {}): SpeakingApi {
  return {
    topics: vi.fn(),
    suggest: vi.fn(),
    create: vi.fn(),
    get: vi.fn().mockResolvedValue(state()),
    submit: vi.fn().mockResolvedValue({
      state: state({
        version: 1,
        messages: [
          {role: 'teacher', text: 'old server history'},
          {role: 'learner', text: 'I like rabbits'},
          {role: 'teacher', text: 'Great choice.'},
        ],
      }),
      reply: {text: 'Great choice.', support_kind: 'continue'},
    }),
    finish: vi.fn(),
    ...overrides,
  } as SpeakingApi;
}

function message(role: 'user' | 'assistant', text: unknown, final = true, createdAt = 'm1') {
  return {role, final, createdAt, parts: [{text, final, createdAt: `${createdAt}-part`}]};
}

beforeEach(() => {
  vi.clearAllMocks();
  conversationMessages = [];
  onMessageUpdated = undefined;
});

it('injects persisted REST history once when rerendered', () => {
  const initial = state({messages: [
    {role: 'teacher', text: 'Welcome'},
    {role: 'learner', text: 'Hello Luna'},
  ]});
  const service = api();
  const view = render(<ActiveSpeakingRoom initialSession={initial} api={service} />);

  expect(injectMessage).toHaveBeenCalledTimes(2);
  expect(injectMessage.mock.calls.map(([value]) => value.role)).toEqual(['assistant', 'user']);

  view.rerender(<ActiveSpeakingRoom initialSession={initial} api={service} />);
  expect(injectMessage).toHaveBeenCalledTimes(2);
});

it('renders spoken and unspoken bot output in one assistant bubble', () => {
  conversationMessages = [message('assistant', {spoken: 'The rabbit ', unspoken: 'is gentle.'})];

  const {container} = render(<ActiveSpeakingRoom initialSession={state({messages: []})} api={api()} />);

  expect(container.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);
  expect(screen.getByText('The rabbit is gentle.')).toBeVisible();
});

it('synchronizes each finalized assistant message only once', async () => {
  conversationMessages = [message('assistant', 'Good job.', true, 'assistant-1')];
  const get = vi.fn().mockResolvedValue(state({level: 2}));
  render(<ActiveSpeakingRoom initialSession={state({messages: []})} api={api({get})} />);
  const completed = message('assistant', 'Good job.', true, 'assistant-1');

  await act(async () => {
    onMessageUpdated?.(completed);
    onMessageUpdated?.(completed);
  });

  expect(get).toHaveBeenCalledTimes(1);
  expect(await screen.findByText('Level 2')).toBeVisible();
});

it('keeps completed output visible when metadata synchronization fails', async () => {
  conversationMessages = [message('assistant', 'Good job.', true, 'assistant-2')];
  const get = vi.fn().mockRejectedValue(new Error('sync failed'));
  render(<ActiveSpeakingRoom initialSession={state({messages: []})} api={api({get})} />);

  await act(async () => onMessageUpdated?.(message('assistant', 'Good job.', true, 'assistant-2')));

  expect(screen.getByText('Good job.')).toBeVisible();
  expect(await screen.findByRole('alert')).toHaveTextContent('sync failed');
});

it('injects only the typed exchange instead of returned REST history', async () => {
  const service = api();
  render(<ActiveSpeakingRoom initialSession={state({messages: []})} api={service} />);
  injectMessage.mockClear();

  await userEvent.type(screen.getByLabelText('Câu trả lời'), 'I like rabbits');
  await userEvent.click(screen.getByRole('button', {name: 'Gửi'}));

  expect(injectMessage).toHaveBeenCalledTimes(2);
  expect(injectMessage.mock.calls.map(([value]) => ({
    role: value.role,
    text: value.parts[0].text,
    final: value.parts[0].final,
  }))).toEqual([
    {role: 'user', text: 'I like rabbits', final: true},
    {role: 'assistant', text: 'Great choice.', final: true},
  ]);
  expect(injectMessage).not.toHaveBeenCalledWith(expect.objectContaining({
    parts: [expect.objectContaining({text: 'old server history'})],
  }));
});
