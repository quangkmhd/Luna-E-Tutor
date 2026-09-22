import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { LessonSelector } from '@/components/LessonSelector';
import type { TutorApi } from '@/lib/api';

it('lists authored lessons and links Lesson 1 to its own session route', async () => {
  const listLessons = vi.fn().mockResolvedValue([
    { lesson: 1, title: 'Chào hỏi và giới thiệu tên' },
  ]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons } as unknown as TutorApi} />);

  const lesson = await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i });
  expect(listLessons).toHaveBeenCalledWith('grade03.unit01', expect.any(AbortSignal));
  expect(lesson).toHaveAttribute('href', '/grade3/unit1/lesson/1');
  expect(screen.getByRole('link', { name: /Chọn Unit khác/i })).toHaveAttribute('href', '/');
});
