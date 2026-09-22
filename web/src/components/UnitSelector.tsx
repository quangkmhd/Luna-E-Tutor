import Link from 'next/link';

import { CurriculumNav } from './CurriculumNav';
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
  return <main className="app-shell classroom-shell learner-app">
    <LearnerHeader subtitle="Gia sư tiếng Anh">
      <Link className="secondary-button" href="/talk">Free Talk Room</Link>
    </LearnerHeader>
    <div className="workspace classroom-workspace">
      <CurriculumNav units={units} busy={busy} onSelect={onSelect} />
      <section className="lesson-card classroom-lobby" role="region" aria-label="Lớp học Luna">
        <div className="lesson-heading"><div><h1 className="lesson-title">Lớp học cùng Luna</h1></div></div>
        <div className="classroom-lobby-content">
          <span className="eyebrow">Luna English</span>
          <h2>Chào con!</h2>
          <p>Chọn một Unit trong chương trình học bên trái để bắt đầu buổi học cùng Luna.</p>
        </div>
      </section>
      <aside className="sidebar classroom-lobby-side">
        <section className="panel classroom-lobby-guide">
          <h2>Bắt đầu học</h2>
          <p>Con chọn lớp và Unit ở cột bên trái. Luna sẽ mở đúng bài học đó.</p>
          <p>Muốn trò chuyện tự do? Con có thể vào Free Talk ở phía trên.</p>
          <Link href="/design">Xem thiết kế Luna</Link>
        </section>
      </aside>
    </div>
  </main>;
}
