import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ReviewWorkbench } from '@/components/ReviewWorkbench';
import type { TutorApi } from '@/lib/api';
import type { ComparisonResult, SessionView } from '@/lib/types';


const session: SessionView = {
  session_id: 's1', unit_id: 'grade05.unit01', state_version: 4,
  unit: { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
  stage_id: 'lesson-01', activity_id: 'lesson-01.live-in', objective_id: 'live-in',
  status: 'active', messages: [{ role: 'teacher', text: 'Where do you live?' }],
  review_queue: [], objective_progress: [], last_evidence: null,
  last_decision: null, summary: null,
};

const result: ComparisonResult = {
  state_version: 4, stage_id: 'lesson-01', activity_id: 'lesson-01.live-in',
  learner_text: 'I live city.', teacher_model: 'google/gemini-3.5-flash-lite',
  gemini: {
    evaluator_model: 'google/gemini-3.5-flash-lite',
    teacher_output: 'Oh, you live in the city! What do you like about it?',
    evidence: { response_kind: 'answer', emotional_signals: [], objective_evidence: [], needs_clarification: false },
    decision: { feedback_action: 'recast', progression_action: 'stay', review_queue_add: [], review_queue_remove: [] },
    planning_latency_ms: 900, teacher_latency_ms: 700, total_latency_ms: 1600,
  },
  jev: {
    evaluator_model: '~typesafe/jev-latest',
    teacher_output: 'You live in the city! What is near your home?',
    evidence: { response_kind: 'answer', emotional_signals: [], objective_evidence: [], needs_clarification: false },
    decision: { feedback_action: 'recast', progression_action: 'stay', review_queue_add: [], review_queue_remove: [] },
    planning_latency_ms: 430, teacher_latency_ms: 710, total_latency_ms: 1140,
  },
};


function api() {
  return {
    listSessions: vi.fn().mockResolvedValue([session]),
    createSession: vi.fn().mockResolvedValue(session),
    compareEvaluators: vi.fn().mockResolvedValue(result),
  } as unknown as TutorApi;
}


describe('ReviewWorkbench', () => {
  it('runs both evaluators at the current Unit state and shows both Gemini Teacher outputs', async () => {
    const client = api();
    const user = userEvent.setup();
    render(<ReviewWorkbench api={client} />);

    await user.type(await screen.findByLabelText('Learner text'), 'I live city.');
    await user.click(screen.getByRole('button', { name: 'Run comparison' }));

    expect(client.compareEvaluators).toHaveBeenCalledWith('s1', 'I live city.');
    expect(await screen.findByText(result.gemini.teacher_output)).toBeVisible();
    expect(screen.getByText(result.jev.teacher_output)).toBeVisible();
    expect(screen.getAllByText('Gemini Teacher')).toHaveLength(2);
    expect(screen.getByText('900 ms planning')).toBeVisible();
    expect(screen.getByText('430 ms planning')).toBeVisible();
    expect(screen.getByText(/lesson-01.live-in/)).toBeVisible();
  });


  it('creates a session when there is no Unit state to review', async () => {
    const client = api();
    vi.mocked(client.listSessions).mockResolvedValue([]);
    render(<ReviewWorkbench api={client} />);

    expect(await screen.findByText(/lesson-01.live-in/)).toBeVisible();
    expect(client.createSession).toHaveBeenCalledOnce();
  });
});
