import { describe, expect, it } from 'vitest';

import { unitIdFromSlug } from '@/lib/unit-route';

describe('unitIdFromSlug', () => {
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
