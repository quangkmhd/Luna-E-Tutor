import type { UnitSummary } from './types';

export function isSupportedUnit(unit: UnitSummary): boolean {
  return unit.id === 'grade03.unit01' && unit.grade === 3 && unit.unit === 1;
}

export function unitPath(grade: number, unitNumber: number): string {
  if (grade === 3 && unitNumber === 1) return '/grade3/unit1';
  throw new Error(`Unsupported unit route: grade ${grade} unit ${unitNumber}`);
}
