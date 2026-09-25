import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { LessonFlashcards } from '@/components/LessonFlashcards';
import type { SessionView } from '@/lib/types';

afterEach(() => vi.unstubAllGlobals());

it('keeps word audio on the image card and shows lesson patterns without a duplicate vocabulary list', async () => {
  const cancel = vi.fn();
  const speak = vi.fn();
  vi.stubGlobal('speechSynthesis', { cancel, speak });
  vi.stubGlobal('SpeechSynthesisUtterance', class {
    lang = '';
    constructor(public text: string) {}
  });
  const session = {
    unit: { id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' },
    flashcards: [{ word: 'hello', pronunciation: '/həˈloʊ/', meaning_vi: 'xin chào' }],
    patterns: ["Hi. I'm Mai.", "Hello. I'm Minh."],
  } as SessionView;

  render(<LessonFlashcards session={session} />);
  const listenButtons = screen.getAllByRole('button', { name: 'Nghe từ hello' });
  expect(listenButtons).toHaveLength(1);
  expect(screen.getByRole('heading', { name: 'Mẫu câu cần học' })).toBeVisible();
  expect(screen.getByText("Hi. I'm Mai.")).toBeVisible();
  expect(screen.getByText("Hello. I'm Minh.")).toBeVisible();
  expect(screen.queryByRole('region', { name: 'Từ vựng trong bài' })).not.toBeInTheDocument();
  const user = userEvent.setup();
  await user.click(listenButtons[0]);

  expect(cancel).toHaveBeenCalledTimes(1);
  expect(speak).toHaveBeenCalledTimes(1);
  for (const [utterance] of speak.mock.calls) {
    expect(utterance).toMatchObject({ text: 'hello', lang: 'en-US' });
  }
});
