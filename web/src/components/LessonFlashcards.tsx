import type { SessionView } from '@/lib/types';

export function LessonFlashcards({ session }: { session: SessionView }) {
  return <section className="panel learning-focus" aria-label="Thẻ học">
    <header className="learning-focus-heading">
      <span className="eyebrow">Unit {session.unit.unit}</span>
      <h2 id="learning-focus-title">Thẻ từ vựng</h2>
    </header>
    {session.flashcards.length ? <>
      <div className="lesson-flashcards">
        {session.flashcards.map((card) => <article className="lesson-flashcard" key={card.word}>
          {card.image_url ? <img src={card.image_url} alt={card.word} loading="lazy" /> : <div className="flashcard-placeholder" aria-hidden="true">✦</div>}
          <div className="flashcard-caption">
            <div className="flashcard-word-row"><strong>{card.word}</strong></div>
            {card.pronunciation && <span className="flashcard-pronunciation">{card.pronunciation}</span>}
            {card.meaning_vi && <span className="flashcard-meaning">{card.meaning_vi}</span>}
          </div>
        </article>)}
      </div>
      <section className="lesson-vocabulary-list" aria-label="Từ vựng trong bài">
        <h3>📚 Từ vựng bài học</h3>
        {session.flashcards.map((card) => <div className="lesson-vocabulary-row" key={`row-${card.word}`}>
          <span><strong>{card.word}</strong>{card.meaning_vi && <small>{card.meaning_vi}</small>}</span>
        </div>)}
      </section>
    </> : <p className="flashcard-empty">Chưa có thẻ từ vựng cho bài này.</p>}
  </section>;
}
