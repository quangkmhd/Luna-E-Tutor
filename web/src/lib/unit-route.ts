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

export function unitPath(grade: number, unitNumber: number): string {
  if (grade === 3 && unitNumber === 1) return '/grade3/unit1';
  if (grade === 5 && unitNumber >= 1 && unitNumber <= 5) return `/unit${unitNumber}`;
  throw new Error(`Unsupported unit route: grade ${grade} unit ${unitNumber}`);
}

export const unitSlugs = Object.keys(UNIT_IDS);
