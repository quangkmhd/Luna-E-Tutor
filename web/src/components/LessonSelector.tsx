'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { tutorApi, type TutorApi } from '@/lib/api';
import type { LessonSummary } from '@/lib/types';

export function LessonSelector({
  unitId,
  unitTitle,
  api = tutorApi,
}: {
  unitId: string;
  unitTitle: string;
  api?: TutorApi;
}) {
  const [lessons, setLessons] = useState<LessonSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    void api.listLessons(unitId, controller.signal).then(setLessons).catch((reason: Error) => {
      if (reason.name !== 'AbortError') setError(reason.message);
    }).finally(() => setLoading(false));
    return () => controller.abort();
  }, [api, unitId]);

  return <main className="unit-selector lesson-selector">
    <Link className="lesson-back" href="/">← Chọn Unit khác</Link>
    <div className="logo-mark">L</div>
    <span className="eyebrow">Luna English · Lớp 3 · Unit 1</span>
    <h1>{unitTitle}</h1>
    <p>Chọn một Lesson. Mỗi Lesson là một buổi học với cô Luna.</p>
    {loading && <p role="status">Đang tải danh sách Lesson…</p>}
    {error && <div className="error-banner" role="alert">{error}</div>}
    {!loading && !error && lessons.length === 0 && <p>Unit này chưa có Lesson để học.</p>}
    <div className="unit-grid lesson-grid">
      {lessons.map((lesson) => <Link
        className="lesson-choice"
        key={lesson.lesson}
        href={`/grade3/unit1/lesson/${lesson.lesson}`}
      >
        <strong>Lesson {lesson.lesson}</strong>
        <span>{lesson.title}</span>
        <small>Vào buổi học →</small>
      </Link>)}
    </div>
  </main>;
}
