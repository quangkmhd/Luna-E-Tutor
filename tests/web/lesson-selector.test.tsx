import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { LessonSelector } from '@/components/LessonSelector';
import type { TutorApi } from '@/lib/api';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

it('keeps the authored Lesson route inside the learner frame', async () => {
  const listLessons = vi.fn().mockResolvedValue([{ lesson: 1, title: 'Chào hỏi và giới thiệu tên' }]);
  const listUnits = vi.fn().mockResolvedValue([{ id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' }]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons, listUnits } as unknown as TutorApi} />);
  expect(await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i }))
    .toHaveAttribute('href', '/grade3/unit1/lesson/1');
  expect(screen.getByRole('banner')).toHaveTextContent('Luna');
  expect(screen.getByRole('main')).toHaveClass('classroom-shell');
  expect(screen.getByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
  expect(screen.getByRole('navigation', { name: 'Chương trình học' }))
    .toContainElement(screen.getByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i }));
});

it('lists authored lessons and links Lesson 1 to its own session route', async () => {
  const listLessons = vi.fn().mockResolvedValue([
    { lesson: 1, title: 'Chào hỏi và giới thiệu tên' },
  ]);
  const listUnits = vi.fn().mockResolvedValue([{ id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' }]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons, listUnits } as unknown as TutorApi} />);

  const lesson = await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i });
  expect(listLessons).toHaveBeenCalledWith('grade03.unit01', expect.any(AbortSignal));
  expect(lesson).toHaveAttribute('href', '/grade3/unit1/lesson/1');
  expect(screen.getByRole('button', { name: /Unit 1.*Hello/i })).toBeDisabled();
});
