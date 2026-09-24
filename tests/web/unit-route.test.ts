import { describe, expect, it } from 'vitest';

import { isSupportedUnit, unitPath } from '@/lib/unit-route';

describe('Grade 3 unit routes', () => {
  it('opens the authored Grade 3 Unit 1 path', () => {
    expect(unitPath(3, 1)).toBe('/grade3/unit1');
  });

  it.each([[5, 1], [5, 5], [3, 2]])('rejects unsupported Grade %i Unit %i', (grade, unit) => {
    expect(() => unitPath(grade, unit)).toThrow('Unsupported unit route');
  });

  it('accepts only the authored Grade 3 curriculum unit', () => {
    expect(isSupportedUnit({ id: 'grade03.unit01', grade: 3, unit: 1, title: 'Hello' })).toBe(true);
    expect(isSupportedUnit({ id: 'grade05.unit01', grade: 5, unit: 1, title: 'All about me!' })).toBe(false);
    expect(isSupportedUnit({ id: 'grade03.unit02', grade: 3, unit: 2, title: 'Other' })).toBe(false);
  });
});
