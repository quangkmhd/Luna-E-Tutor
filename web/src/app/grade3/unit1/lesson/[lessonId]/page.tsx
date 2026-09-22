import { notFound } from 'next/navigation';

import { TutorShell } from '@/components/TutorShell';

export default async function Grade3LessonPage({
  params,
}: {
  params: Promise<{ lessonId: string }>;
}) {
  const { lessonId } = await params;
  if (!/^[1-9]\d*$/.test(lessonId)) notFound();
  return <TutorShell initialUnitId="grade03.unit01" initialLessonId={Number(lessonId)} />;
}
