import { describe, expect, it } from 'vitest';

import { unitIdFromSlug, unitPath } from '@/lib/unit-route';

describe('unitIdFromSlug', () => {
  it('keeps Grade 3 and Grade 5 Unit 1 on distinct URLs', () => {
    expect(unitPath(3, 1)).toBe('/grade3/unit1');
    expect(unitPath(5, 1)).toBe('/unit1');
  });
  it.each([
    ['unit1', 'grade05.unit01'],
    ['unit2', 'grade05.unit02'],
    ['unit3', 'grade05.unit03'],
    ['unit4', 'grade05.unit04'],
    ['unit5', 'grade05.unit05'],
  ])('maps %s to the exact curriculum id', (slug, unitId) => {
    expect(unitIdFromSlug(slug)).toBe(unitId);
  });

  it.each(['unit0', 'unit6', 'unit02', 'other'])('rejects unsupported route %s', (slug) => {
    expect(unitIdFromSlug(slug)).toBeNull();
  });
});
