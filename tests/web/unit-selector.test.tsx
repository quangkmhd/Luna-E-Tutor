import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { UnitSelector } from '@/components/UnitSelector';

it('reports the exact selected curriculum id', async () => {
  const onSelect = vi.fn();
  render(<UnitSelector
    units={[
      { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
      { id: 'grade05.unit02', grade: 5, unit: 2, title: 'Our homes' },
    ]}
    busy={false}
    onSelect={onSelect}
  />);

  await userEvent.click(screen.getByRole(
    'button', { name: /Unit 2.*Our homes/i },
  ));

  expect(onSelect).toHaveBeenCalledWith('grade05.unit02');
});

it('shows both Unit 1 choices under their own grades', async () => {
  const onSelect = vi.fn();
  render(<UnitSelector units={[
    { id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' },
    { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
  ]} busy={false} onSelect={onSelect} />);

  expect(screen.getByRole('heading', { name: 'Grade 3' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Grade 5' })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: /Unit 1.*Hello/i }));
  expect(onSelect).toHaveBeenCalledWith('grade03.unit01');
});

it('offers Free Talk as a separate destination outside the unit choices', () => {
  render(<UnitSelector
    units={[
      { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
    ]}
    busy={false}
    onSelect={vi.fn()}
  />);

  const freeTalk = screen.getByRole('link', { name: /Enter Free Talk/i });
  expect(freeTalk).toHaveAttribute('href', '/talk');
  expect(freeTalk.closest('.free-talk-card')).not.toBeNull();
  expect(screen.getByText(/Practise any topic with Luna/i)).toBeVisible();
  expect(screen.getByRole('button', { name: /Unit 1.*All about me!/i }))
    .not.toContainElement(freeTalk);
});

it('offers the Luna design principles as a separate document destination', () => {
  render(<UnitSelector
    units={[
      { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
    ]}
    busy={false}
    onSelect={vi.fn()}
  />);

  const designLink = screen.getByRole('link', { name: /Xem thiết kế/i });
  expect(designLink).toHaveAttribute('href', '/design');
  expect(designLink.closest('.design-entry-card')).not.toBeNull();
  expect(screen.getByRole('heading', { name: 'Nguyên tắc thiết kế Luna' }))
    .toBeVisible();
  expect(screen.getByText(/11 nguyên tắc định hướng trải nghiệm học/i))
    .toBeVisible();
});
