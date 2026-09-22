import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import { UnitSelector } from '@/components/UnitSelector';

it('opens the classroom layout instead of a separate Unit picker', () => {
  render(<UnitSelector units={[]} busy={false} onSelect={vi.fn()} />);
  expect(screen.getByRole('main')).toHaveClass('classroom-shell');
  expect(screen.getByRole('navigation', { name: 'Chương trình học' })).toBeVisible();
  expect(screen.getByRole('region', { name: 'Lớp học Luna' })).toBeVisible();
  expect(screen.getByText('Chưa có Unit để học.')).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Choose a unit' })).not.toBeInTheDocument();
  expect(screen.getByRole('banner')).toHaveTextContent('Luna');
});

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

  expect(screen.getByRole('heading', { name: /Lớp 3.*Global Success/i })).toBeVisible();
  expect(screen.getByRole('heading', { name: /Lớp 5.*Global Success/i })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: /Unit 1.*Hello/i }));
  expect(onSelect).toHaveBeenCalledWith('grade03.unit01');
});

it('keeps Free Talk in the classroom header, separate from the Unit buttons', () => {
  render(<UnitSelector
    units={[
      { id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' },
    ]}
    busy={false}
    onSelect={vi.fn()}
  />);

  const freeTalk = screen.getByRole('link', { name: 'Free Talk Room' });
  expect(freeTalk).toHaveAttribute('href', '/talk');
  expect(freeTalk.closest('header')).toHaveClass('learner-header');
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
  expect(designLink.closest('.sidebar')).not.toBeNull();
});
