import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { SpeakingRoom } from '@/components/speaking/SpeakingRoom';
import type { SpeakingApi } from '@/lib/speaking-api';

function fakeApi(): SpeakingApi {
  return {
    async topics() { return [{id: 'food', name_en: 'Food', name_vi: 'Đồ ăn', scenario: 'Picnic', words: ['juice']}]; },
    async suggest(topic) { return {topic, words: [{word: 'juice', meaning_vi: 'nước ép', example: 'I like juice.'}], clarification: null}; },
    async create(config) { return {session_id: 's1', config, version: 0, status: 'active', level: 1, independent_streak: 0, difficulty_streak: 0, word_evidence: [], last_delivered_text: 'What food do you like?', opening_message: 'What food do you like?'}; },
    async submit(_id, turn) { return {state: {...await this.create({grade: 5, topic: 'Food', words: ['juice']}), version: 1}, reply: {text: `Great: ${turn.text}`, support_kind: 'continue'}}; },
    async finish(_id, _version) { const state = {...await this.create({grade: 5, topic: 'Food', words: ['juice']}), status: 'completed' as const}; return {state, independent: [], supported: [], unseen: ['juice'], next_practice: 'Try juice next time.'}; },
  };
}

describe('SpeakingRoom', () => {
  it('creates a custom topic session and completes it', async () => {
    const user = userEvent.setup();
    render(<SpeakingRoom api={fakeApi()} />);
    await screen.findByRole('button', {name: 'Food'});
    await user.click(screen.getByRole('button', {name: 'Food'}));
    await user.type(screen.getByLabelText('Từ muốn luyện'), 'juice');
    await user.click(screen.getByRole('button', {name: 'Thêm từ'}));
    await user.click(screen.getByRole('button', {name: 'Bắt đầu nói'}));
    expect(await screen.findByText('What food do you like?')).toBeVisible();
    await user.type(screen.getByLabelText('Câu trả lời'), 'I like juice');
    await user.click(screen.getByRole('button', {name: 'Gửi'}));
    expect(await screen.findByText('Great: I like juice')).toBeVisible();
    await user.click(screen.getByRole('button', {name: 'Kết thúc'}));
    expect(await screen.findByText('Try juice next time.')).toBeVisible();
  });
});
