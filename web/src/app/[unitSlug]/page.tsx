import { notFound } from 'next/navigation';

import { TutorShell } from '@/components/TutorShell';
import { unitIdFromSlug, unitSlugs } from '@/lib/unit-route';

export function generateStaticParams() {
  return unitSlugs.map((unitSlug) => ({ unitSlug }));
}

export default async function UnitPage({
  params,
}: {
  params: Promise<{ unitSlug: string }>;
}) {
  const { unitSlug } = await params;
  const unitId = unitIdFromSlug(unitSlug);

  if (!unitId) notFound();

  return <TutorShell initialUnitId={unitId} />;
}
