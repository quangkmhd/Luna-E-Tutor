import Link from 'next/link';

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
  return <main className="unit-selector">
    <div className="logo-mark">L</div>
    <span className="eyebrow">Grade 5 English</span>
    <h1>Choose a unit</h1>
    <p>Select what you would like to practise with Luna.</p>
    <div className="unit-grid">
      {units.map((unit) => <button
        key={unit.id}
        type="button"
        disabled={busy}
        onClick={() => onSelect(unit.id)}
      >
        <strong>Unit {unit.unit}</strong>
        <span>{unit.title}</span>
      </button>)}
    </div>
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
  </main>;
}
