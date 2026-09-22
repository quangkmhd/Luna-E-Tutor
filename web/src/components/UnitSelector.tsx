import Link from 'next/link';
import { LearnerHeader } from './LearnerHeader';

import type { UnitSummary } from '@/lib/types';

export function UnitSelector({
  units,
  busy,
  onSelect,
}: {
  units: UnitSummary[];
  busy: boolean;
  onSelect: (unitId: string) => void;
}) {
  return <div className="learner-app learner-picker-page">
    <LearnerHeader subtitle="Gia sư tiếng Anh" />
    <main className="unit-selector learner-home">
    <span className="eyebrow">Luna English</span>
    <h1>Choose a unit</h1>
    <p>Select what you would like to practise with Luna.</p>
    {units.length === 0 && <p className="learner-empty">Chưa có Unit để học.</p>}
    {[...new Set(units.map((unit) => unit.grade))].sort((a, b) => a - b).map((grade) => <section
      className="grade-unit-group"
      key={grade}
      aria-labelledby={`grade-${grade}-heading`}
    >
      <h2 id={`grade-${grade}-heading`}>Grade {grade}</h2>
      <div className="unit-grid">
        {units.filter((unit) => unit.grade === grade).map((unit) => <button
          key={unit.id}
          type="button"
          disabled={busy}
          onClick={() => onSelect(unit.id)}
        >
          <strong>Unit {unit.unit}</strong>
          <span>{unit.title}</span>
        </button>)}
      </div>
    </section>)}
    <section className="free-talk-card" aria-labelledby="free-talk-title">
      <div className="free-talk-icon" aria-hidden="true">
        <span>···</span>
      </div>
      <div className="free-talk-copy">
        <span className="free-talk-kicker">Open conversation</span>
        <h2 id="free-talk-title">Free Talk with Luna</h2>
        <p>Practise any topic with Luna — no lesson steps.</p>
      </div>
      <Link className="free-talk-link" href="/talk">
        Enter Free Talk <span aria-hidden="true">→</span>
      </Link>
    </section>
    <Link className="design-entry-card" href="/design">
      <div className="design-entry-icon" aria-hidden="true">11</div>
      <div className="design-entry-copy">
        <span className="design-entry-kicker">Tài liệu thiết kế</span>
        <h2>Nguyên tắc thiết kế Luna</h2>
        <p>11 nguyên tắc định hướng trải nghiệm học và cách Luna phản hồi.</p>
      </div>
      <span className="design-entry-action">
        Xem thiết kế <span aria-hidden="true">→</span>
      </span>
    </Link>
    </main>
  </div>;
}
