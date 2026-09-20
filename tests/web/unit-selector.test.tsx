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
