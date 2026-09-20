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
  </main>;
}
