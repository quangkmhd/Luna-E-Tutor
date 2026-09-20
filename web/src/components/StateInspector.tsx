import type { SessionView } from '@/lib/types';

export function StateInspector({ session }: { session: SessionView }) {
  return <section className="panel learning-focus" aria-labelledby="learning-focus-title">
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
  </section>;
}
