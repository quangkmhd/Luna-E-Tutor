'use client';

import { useState } from 'react';
import type { SessionView } from '@/lib/types';

export function StateInspector({ session }: { session: SessionView }) {
  const [tab, setTab] = useState<'learn' | 'progress'>('learn');
  return <section className="panel learning-focus" aria-label="Thẻ học và tiến độ">
    <div className="classroom-tabs" role="tablist" aria-label="Thẻ học và tiến độ">
      <button type="button" role="tab" aria-selected={tab === 'learn'} onClick={() => setTab('learn')}>Thẻ học</button>
      <button type="button" role="tab" aria-selected={tab === 'progress'} onClick={() => setTab('progress')}>Tiến độ</button>
    </div>
    {tab === 'learn' ? <div role="tabpanel" aria-label="Thẻ học">
    <header className="learning-focus-heading">
      <span className="eyebrow">Unit {session.unit.unit}</span>
      <h2 id="learning-focus-title">Nội dung cần học</h2>
    </header>
    <div className="learning-focus-list">
      {session.learning_focus.map((focus) => <article
        className={`learning-stage${focus.highlighted ? ' highlighted' : ''}`}
        key={focus.stage_id}
      >
        <header>
          <span>Chặng</span>
          <h3>{focus.stage_title}</h3>
          {focus.highlighted && <small>Đang học tiếp</small>}
        </header>
        <div className="learning-targets">
          <span>Từ / cấu trúc trọng tâm</span>
          {!!focus.target_words.length && <div className="target-words">
            {focus.target_words.map((word) => <strong key={word}>{word}</strong>)}
          </div>}
          {!!focus.target_patterns.length && <div className="target-patterns">
            {focus.target_patterns.map((pattern) => <p key={pattern}>{pattern}</p>)}
          </div>}
        </div>
      </article>)}
    </div>
    </div> : <div role="tabpanel" aria-label="Tiến độ" className="classroom-progress">
      <h2>Tiến độ buổi học</h2>
      <p>{session.status === 'completed' ? 'Buổi học đã hoàn thành.' : `Đang ở chặng ${session.stage_id.replaceAll('-', ' ')}.`}</p>
      {session.objective_progress.length === 0 ? <p>Chưa ghi nhận lần sử dụng nào.</p> : <ul>
        {session.objective_progress.map((item) => <li key={item.objective_id}>
          <strong>{item.objective_id}</strong>
          <span>Tự nói: {item.independent_uses} · Có hỗ trợ: {item.supported_uses}{item.needs_review ? ' · Cần ôn lại' : ''}</span>
        </li>)}
      </ul>}
      {session.summary && <p>Đã thể hiện: {session.summary.demonstrated.join(', ') || 'Chưa có'} · Cần ôn: {session.summary.needs_review.join(', ') || 'Không có'}</p>}
    </div>}
  </section>;
}
