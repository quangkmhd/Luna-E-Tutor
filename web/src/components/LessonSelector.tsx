'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { tutorApi, type TutorApi } from '@/lib/api';
import type { LessonSummary, UnitSummary } from '@/lib/types';
import { unitPath } from '@/lib/unit-route';
import { CurriculumNav } from './CurriculumNav';
import { LearnerHeader } from './LearnerHeader';

export function LessonSelector({
  unitId,
  unitTitle,
  api = tutorApi,
}: {
  unitId: string;
  unitTitle: string;
  api?: TutorApi;
}) {
  const router = useRouter();
  const [units, setUnits] = useState<UnitSummary[]>([]);
  const [lessons, setLessons] = useState<LessonSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const selectedUnit = units.find((unit) => unit.id === unitId);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      api.listUnits(controller.signal),
      api.listLessons(unitId, controller.signal),
    ]).then(([availableUnits, availableLessons]) => {
      setUnits(availableUnits);
      setLessons(availableLessons);
    }).catch((reason: Error) => {
      if (reason.name !== 'AbortError') setError(reason.message);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [api, unitId]);

  function selectUnit(nextUnitId: string) {
    const unit = units.find((item) => item.id === nextUnitId);
    if (unit) router.push(unitPath(unit.grade, unit.unit));
  }

  return <main className="app-shell classroom-shell learner-app">
    <LearnerHeader subtitle="Gia sư tiếng Anh · Lớp 3 · Unit 1">
      <Link className="secondary-button" href="/talk">Free Talk Room</Link>
      <Link className="secondary-button" href="/">Chọn Unit khác</Link>
    </LearnerHeader>
    <div className="workspace classroom-workspace">
      {!loading && <CurriculumNav units={units} expandedUnitId={unitId} lessons={lessons}
        lessonBasePath="/grade3/unit1/lesson" initialGrade={selectedUnit?.grade}
        busy={false} onSelect={selectUnit} />}
      {loading && <aside className="classroom-curriculum" aria-hidden="true" />}
      <section className="lesson-card classroom-lobby" role="region" aria-label="Lớp học Luna">
        <div className="lesson-heading"><div><h1 className="lesson-title">Unit 1 · {unitTitle}</h1><span className="lesson-crumb">Lớp 3 · Global Success</span></div></div>
        <div className="classroom-lobby-content">
          <span className="eyebrow">Luna English · Lớp 3</span>
          <h2>{unitTitle}</h2>
          {loading ? <p role="status">Đang tải danh sách Lesson…</p>
            : error ? <div className="error-banner" role="alert">{error}</div>
              : lessons.length === 0 ? <p>Unit này chưa có Lesson để học.</p>
                : <p>Chọn một Lesson trong chương trình học bên trái để bắt đầu buổi học cùng Luna.</p>}
        </div>
      </section>
      <aside className="sidebar classroom-lobby-side">
        <section className="panel classroom-lobby-guide">
          <h2>Các Lesson</h2>
          <p>Chọn Lesson ở cột bên trái để vào buổi học. Luna sẽ mở đúng nội dung của Lesson đó.</p>
        </section>
      </aside>
    </div>
  </main>;
}
