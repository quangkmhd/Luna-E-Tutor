'use client';

import { useState } from 'react';
import type { SessionView } from '@/lib/types';

function speakWord(word: string) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(word));
}

const statusLabel = { new: 'Chưa học', learning: 'Đang luyện', learned: 'Đã dùng được' };

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
      <h2 id="learning-focus-title">Thẻ từ vựng</h2>
    </header>
    {session.flashcards.length ? <>
      <div className="lesson-flashcards">
        {session.flashcards.map((card) => <article className="lesson-flashcard" key={card.word}>
          {card.image_url ? <img src={card.image_url} alt={card.word} loading="lazy" /> : <div className="flashcard-placeholder" aria-hidden="true">✦</div>}
          <div className="flashcard-caption">
            <div className="flashcard-word-row"><strong>{card.word}</strong><button type="button" aria-label={`Nghe từ ${card.word}`} onClick={() => speakWord(card.word)}>🔊</button></div>
            {card.pronunciation && <span className="flashcard-pronunciation">{card.pronunciation}</span>}
            {card.meaning_vi && <span className="flashcard-meaning">{card.meaning_vi}</span>}
            <span className={`flashcard-status ${card.status}`}>{statusLabel[card.status]}</span>
          </div>
        </article>)}
      </div>
      <section className="lesson-vocabulary-list" aria-label="Từ vựng trong bài">
        <h3>📚 Từ vựng bài học</h3>
        {session.flashcards.map((card) => <button className={`lesson-vocabulary-row ${card.status}`} key={`row-${card.word}`} type="button" onClick={() => speakWord(card.word)}>
          <span><strong>{card.word}</strong>{card.meaning_vi && <small>{card.meaning_vi}</small>}</span><span className="vocabulary-progress" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /></span><span aria-hidden="true">🔊</span>
        </button>)}
      </section>
    </> : <p className="flashcard-empty">Chưa có thẻ từ vựng cho chặng này.</p>}
    <div className="learning-focus-list">
      {session.learning_focus.filter((focus) => focus.highlighted && focus.target_patterns.length > 0).map((focus) => <article className="learning-stage highlighted" key={focus.stage_id}>
        <header><span>Mẫu câu cần nhớ</span><h3>{focus.stage_title}</h3></header>
        <div className="target-patterns">{focus.target_patterns.map((pattern) => <p key={pattern}>{pattern}</p>)}</div>
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
