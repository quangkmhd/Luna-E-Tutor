import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

it('lists all four Unit 1 sessions, including the review lesson', async () => {
  const listLessons = vi.fn().mockResolvedValue([
    { lesson: 1, title: 'Chào hỏi và giới thiệu tên' },
    { lesson: 2, title: 'Hỏi thăm sức khỏe và cảm ơn' },
    { lesson: 3, title: 'Chào tạm biệt và chào theo thời điểm' },
    { lesson: 4, title: 'Ôn tập Unit 1' },
  ]);
  const listUnits = vi.fn().mockResolvedValue([{ id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' }]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons, listUnits } as unknown as TutorApi} />);

  const lesson = await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi và giới thiệu tên/i });
  expect(listLessons).toHaveBeenCalledWith('grade03.unit01', expect.any(AbortSignal));
  expect(lesson).toHaveAttribute('href', '/grade3/unit1/lesson/1');
  expect(screen.getByRole('button', { name: /Unit 1.*Hello/i })).toBeDisabled();
  expect(screen.getByRole('link', { name: /Lesson 2.*Hỏi thăm sức khỏe/i })).toHaveAttribute('href', '/grade3/unit1/lesson/2');
  expect(screen.getByRole('link', { name: /Lesson 3.*Chào tạm biệt/i })).toHaveAttribute('href', '/grade3/unit1/lesson/3');
  expect(screen.getByRole('link', { name: /Lesson 4.*Ôn tập Unit 1/i })).toHaveAttribute('href', '/grade3/unit1/lesson/4');
  expect(screen.getByRole('link', { name: /Chọn Unit khác/i })).toHaveAttribute('href', '/');
});

it('keeps Grade 5 out of the lesson navigation when returned by the API', async () => {
  const listLessons = vi.fn().mockResolvedValue([{ lesson: 1, title: 'Chào hỏi và giới thiệu tên' }]);
  const listUnits = vi.fn().mockResolvedValue([
    { id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' },
    { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
  ]);
  render(<LessonSelector unitId="grade03.unit01" unitTitle="Hello"
    api={{ listLessons, listUnits } as unknown as TutorApi} />);

  expect(await screen.findByRole('link', { name: /Lesson 1.*Chào hỏi/i })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Tất cả' }));
  expect(screen.queryByRole('heading', { name: /Lớp 5.*Global Success/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /All about me!/i })).not.toBeInTheDocument();
});
