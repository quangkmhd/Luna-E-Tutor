import {render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type {PropsWithChildren} from 'react';
import {beforeEach, describe, expect, it, vi} from 'vitest';

import {SpeakingRoom} from '@/components/speaking/SpeakingRoom';
import type {SpeakingApi} from '@/lib/speaking-api';

const activeRoom = vi.fn(({initialSession}: {initialSession: {session_id: string}}) => (
  <div>Active session {initialSession.session_id}</div>
));
const provider = vi.fn(({children}: PropsWithChildren) => <div data-testid="pipecat-provider">{children}</div>);

vi.mock('@/components/speaking/ActiveSpeakingRoom', () => ({
  ActiveSpeakingRoom: (props: {initialSession: {session_id: string}}) => activeRoom(props),
}));

vi.mock('@/components/speaking/SpeakingPipecatProvider', () => ({
  SpeakingPipecatProvider: ({children}: PropsWithChildren) => provider({children}),
}));

function fakeApi(): SpeakingApi {
  return {
    async topics() { return [{id: 'food', name_en: 'Food', name_vi: 'Đồ ăn', scenario: 'Picnic', words: ['juice']}]; },
    async suggest(topic) { return {topic, words: [{word: 'juice', meaning_vi: 'nước ép', example: 'I like juice.'}], clarification: null}; },
    async create(config) { return {session_id: 's1', config, version: 0, status: 'active', level: 1, independent_streak: 0, difficulty_streak: 0, word_evidence: [], last_delivered_text: 'What food do you like?', opening_message: 'What food do you like?', messages: [{role: 'teacher', text: 'What food do you like?'}]}; },
    async get(_id) { return this.create({grade: 5, topic: 'Food', words: ['juice']}); },
    async submit(_id, turn) { const state = await this.create({grade: 5, topic: 'Food', words: ['juice']}); const reply = {text: `Great: ${turn.text}`, support_kind: 'continue'}; return {state, reply}; },
    async finish(_id, _version) { const state = {...await this.create({grade: 5, topic: 'Food', words: ['juice']}), status: 'completed' as const}; return {state, independent: [], supported: [], unseen: ['juice'], next_practice: 'Try juice next time.'}; },
  };
}

describe('SpeakingRoom', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState(null, '', '/speaking');
  });

  it('uses the Unit 1 shell while choosing a speaking topic', async () => {
    const {container} = render(<SpeakingRoom api={fakeApi()} />);
    await screen.findByRole('button', {name: 'Food'});
    expect(container.querySelector('.app-shell .topbar')).toBeInTheDocument();
    expect(container.querySelector('.workspace .lesson-card')).toBeInTheDocument();
    expect(screen.getByText('English Tutor · Topic Speaking')).toBeVisible();
  });

  it('lets the learner choose an AI-suggested word', async () => {
    const user = userEvent.setup();
    render(<SpeakingRoom api={fakeApi()} />);
    await user.click(await screen.findByRole('button', {name: 'Food'}));
    await user.click(screen.getByRole('button', {name: 'Gợi ý từ cho chủ đề này'}));
    expect(await screen.findByText('nước ép')).toBeVisible();
    await user.click(screen.getByRole('button', {name: /juice/}));
    expect(screen.getByRole('button', {name: 'juice ×'})).toBeVisible();
  });

  it('mounts the active session inside a session-scoped Pipecat provider', async () => {
    const user = userEvent.setup();
    const service = fakeApi();
    render(<SpeakingRoom api={service} />);
    await user.click(await screen.findByRole('button', {name: 'Food'}));
    await user.type(screen.getByLabelText('Tự nhập từ muốn luyện'), 'juice');
    await user.click(screen.getByRole('button', {name: 'Thêm từ'}));
    await user.click(screen.getByRole('button', {name: 'Bắt đầu nói'}));

    expect(await screen.findByTestId('pipecat-provider')).toBeVisible();
    expect(screen.getByText('Active session s1')).toBeVisible();
    expect(activeRoom).toHaveBeenCalledWith(expect.objectContaining({initialSession: expect.objectContaining({session_id: 's1'}), api: service}));
  });

  it('restores a session from the URL inside the provider', async () => {
    window.history.replaceState(null, '', '/speaking?session=s1');
    render(<SpeakingRoom api={fakeApi()} />);

    expect(await screen.findByText('Active session s1')).toBeVisible();
    expect(provider).toHaveBeenCalledTimes(1);
  });
});
