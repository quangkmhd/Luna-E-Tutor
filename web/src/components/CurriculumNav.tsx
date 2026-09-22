'use client';

import Link from 'next/link';
import { useState } from 'react';
import type { LessonSummary, SessionView, UnitSummary } from '@/lib/types';

export function CurriculumNav({ units, session, busy, onSelect, expandedUnitId, lessons = [], lessonBasePath, initialGrade }: {
  units: UnitSummary[];
  session?: SessionView | null;
  busy: boolean;
  onSelect(unitId: string): void;
  expandedUnitId?: string;
  lessons?: LessonSummary[];
  lessonBasePath?: string;
  initialGrade?: number;
}) {
  const [query, setQuery] = useState('');
  const [grade, setGrade] = useState<number | null>(session?.unit.grade ?? initialGrade ?? null);
  const currentUnitId = session?.unit_id ?? expandedUnitId;
  const grades = [...new Set(units.map((unit) => unit.grade))].sort((a, b) => a - b);
  const visible = units.filter((unit) => {
    const focusTerms = session && unit.id === session.unit_id
      ? session.learning_focus.flatMap((focus) => [focus.stage_title, ...focus.target_words, ...focus.target_patterns])
      : [];
    return (grade === null || unit.grade === grade)
      && `${unit.title} unit ${unit.unit} lớp ${unit.grade} ${focusTerms.join(' ')}`
        .toLocaleLowerCase().includes(query.trim().toLocaleLowerCase());
  });

  return <aside className="classroom-curriculum">
    <div className="curriculum-head">
      <h2>Chương trình học</h2>
      <input type="search" aria-label="Tìm bài học" placeholder="Tìm bài hoặc từ…" value={query} onChange={(event) => setQuery(event.target.value)} />
      <div className="curriculum-filters" role="group" aria-label="Lọc theo lớp">
        <button type="button" aria-pressed={grade === null} onClick={() => setGrade(null)}>Tất cả</button>
        {grades.map((item) => <button type="button" key={item} aria-pressed={grade === item} onClick={() => setGrade(item)}>Lớp {item}</button>)}
      </div>
    </div>
    <nav aria-label="Chương trình học" className="curriculum-tree">
      {visible.length === 0 && <p className="curriculum-empty">{units.length === 0 ? 'Chưa có Unit để học.' : 'Không tìm thấy bài nào.'}</p>}
      {grades.filter((item) => visible.some((unit) => unit.grade === item)).map((item) => <div key={item} className="curriculum-grade">
        <h3>Lớp {item} · Global Success</h3>
        {visible.filter((unit) => unit.grade === item).map((unit) => <div className="curriculum-unit" key={unit.id}>
          <button type="button" className={unit.id === currentUnitId ? 'current' : ''} disabled={busy || unit.id === currentUnitId}
            onClick={() => onSelect(unit.id)} aria-current={unit.id === currentUnitId ? 'page' : undefined}>
            <span className="curriculum-number">{unit.unit}</span><span>Unit {unit.unit} · {unit.title}</span>
          </button>
          {unit.id === expandedUnitId && lessonBasePath && <div className="curriculum-lessons">
            {lessons.map((lesson) => <Link className={`curriculum-lesson-choice${lesson.lesson === session?.lesson_id ? ' current' : ''}`} href={`${lessonBasePath}/${lesson.lesson}`} key={lesson.lesson} aria-current={lesson.lesson === session?.lesson_id ? 'page' : undefined}>
              <span className="curriculum-lesson-number">{lesson.lesson}</span>
              <span><strong>Lesson {lesson.lesson}</strong><small>{lesson.title}</small></span>
            </Link>)}
          </div>}
          {unit.id === session?.unit_id && session.lesson_id != null && !expandedUnitId && <div className="curriculum-lesson" aria-current="step">Lesson {session.lesson_id} · Đang học</div>}
        </div>)}
      </div>)}
    </nav>
  </aside>;
}
