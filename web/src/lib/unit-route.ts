const UNIT_IDS = {
  unit1: 'grade05.unit01',
  unit2: 'grade05.unit02',
  unit3: 'grade05.unit03',
  unit4: 'grade05.unit04',
  unit5: 'grade05.unit05',
} as const;

export function unitIdFromSlug(slug: string): string | null {
  return UNIT_IDS[slug as keyof typeof UNIT_IDS] ?? null;
}

export function unitPath(unitNumber: number): string {
  return `/unit${unitNumber}`;
}

export const unitSlugs = Object.keys(UNIT_IDS);
