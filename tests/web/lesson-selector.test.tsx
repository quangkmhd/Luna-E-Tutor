import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { LessonSelector } from '@/components/LessonSelector';
import type { TutorApi } from '@/lib/api';

it('lists all four Unit 1 sessions, including the review lesson', async () => {
  const listLessons = vi.fn().mockResolvedValue([
    { lesson: 1, title: 'Chào hỏi và giới thiệu tên' },
    { lesson: 2, title: 'Hỏi thăm sức khỏe và cảm ơn' },
    { lesson: 3, title: 'Chào tạm biệt và chào theo thời điểm' },
    { lesson: 4, title: 'Ôn tập Unit 1' },
  ]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons } as unknown as TutorApi} />);

  const lesson = await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i });
  expect(listLessons).toHaveBeenCalledWith('grade03.unit01', expect.any(AbortSignal));
  expect(lesson).toHaveAttribute('href', '/grade3/unit1/lesson/1');
  expect(screen.getByRole('link', { name: /Lesson 2.*Hỏi thăm sức khỏe/i })).toHaveAttribute('href', '/grade3/unit1/lesson/2');
  expect(screen.getByRole('link', { name: /Lesson 3.*Chào tạm biệt/i })).toHaveAttribute('href', '/grade3/unit1/lesson/3');
  expect(screen.getByRole('link', { name: /Lesson 4.*Ôn tập Unit 1/i })).toHaveAttribute('href', '/grade3/unit1/lesson/4');
  expect(screen.getByRole('link', { name: /Chọn Unit khác/i })).toHaveAttribute('href', '/');
});
