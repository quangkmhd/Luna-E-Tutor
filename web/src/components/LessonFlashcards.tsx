'use client';

import type { SessionView } from '@/lib/types';

function speakWord(word: string) {
  if (!('speechSynthesis' in window)) return;
  const utterance = new SpeechSynthesisUtterance(word);
  utterance.lang = 'en-US';
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

export function LessonFlashcards({ session }: { session: SessionView }) {
  return <section className="panel learning-focus" aria-label="Thẻ học">
    <header className="learning-focus-heading">
      <span className="eyebrow">Unit {session.unit.unit}</span>
      <h2 id="learning-focus-title">Thẻ từ vựng</h2>
    </header>
    {session.flashcards.length ?
      <div className="lesson-flashcards">
        {session.flashcards.map((card) => <article className="lesson-flashcard" key={card.word}>
          {card.image_url ? <img src={card.image_url} alt={card.word} loading="lazy" /> : <div className="flashcard-placeholder" aria-hidden="true">✦</div>}
          <div className="flashcard-caption">
            <div className="flashcard-word-row"><strong>{card.word}</strong><button type="button" aria-label={`Nghe từ ${card.word}`} onClick={() => speakWord(card.word)}>🔊</button></div>
            {card.pronunciation && <span className="flashcard-pronunciation">{card.pronunciation}</span>}
            {card.meaning_vi && <span className="flashcard-meaning">{card.meaning_vi}</span>}
          </div>
        </article>)}
      </div>
      : <p className="flashcard-empty">Chưa có thẻ từ vựng cho bài này.</p>}
    {Boolean(session.patterns?.length) && <section className="lesson-patterns" aria-label="Mẫu câu cần học">
      <h3>Mẫu câu cần học</h3>
      <ul>{session.patterns?.map((pattern) => <li key={pattern}>{pattern}</li>)}</ul>
    </section>}
  </section>;
}
