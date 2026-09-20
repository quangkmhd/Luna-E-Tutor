'use client';
import {useEffect, useState} from 'react';
import Link from 'next/link';
import type { SpeakingApi } from '@/lib/speaking-api';
import { speakingApi } from '@/lib/speaking-api';
import type {SpeakingState, Topic} from '@/lib/speaking-types';
import styles from './speaking.module.css';
import {ActiveSpeakingRoom} from './ActiveSpeakingRoom';
import {SpeakingPipecatProvider} from './SpeakingPipecatProvider';

type SuggestedWord = {word: string; meaning_vi: string; example: string};

export function SpeakingRoom({api = speakingApi}: {api?: SpeakingApi}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topic, setTopic] = useState('');
  const [wordInput, setWordInput] = useState('');
  const [words, setWords] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestedWord[]>([]);
  const [session, setSession] = useState<SpeakingState|null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { void api.topics().then(setTopics).catch((e) => setError(e.message)); }, [api]);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('session');
    if (!id) return;
    void api.get(id).then(setSession)
      .catch(() => window.history.replaceState(null, '', window.location.pathname));
  }, [api]);

  function addWord() {
    const value = wordInput.trim().toLowerCase();
    if (!value || words.includes(value)) return;
    if (words.length >= 5) return setError('Mỗi phiên chọn tối đa 5 từ.');
    setWords([...words, value]); setWordInput(''); setError('');
  }

  async function suggest() {
    if (!topic.trim()) return setError('Hãy chọn hoặc nhập chủ đề trước.');
    setBusy(true); setError('');
    try { setSuggestions((await api.suggest(topic)).words); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function start() {
    if (!topic.trim() || words.length < 1) return setError('Hãy chọn chủ đề và ít nhất một từ.');
    setBusy(true); setError('');
    try {
      const value = await api.create({grade: 5, topic, words});
      setSession(value);
      window.history.replaceState(null, '', `?session=${encodeURIComponent(value.session_id)}`);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (!session) return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="logo-mark">L</div><div><span>Luna</span><small>English Tutor · Topic Speaking</small></div></div>
      <div className="top-actions"><Link className="secondary-button" href="/">Unit 1</Link></div>
    </header>
    <div className={`workspace ${styles.setupWorkspace}`}>
      <section className="lesson-card">
        <div className="lesson-heading"><div><span className="eyebrow">Lớp 5 · Luyện nói</span><h1>Chọn chủ đề của em</h1></div><span className="stage-chip">Chuẩn bị</span></div>
        <div className={styles.setupContent}>
          <p className={styles.lead}>Chọn điều em thích và tối đa năm từ em muốn dùng trong cuộc trò chuyện với Luna.</p>
          <div className={styles.topics}>{topics.map((item) => <button type="button" key={item.id} className={topic === item.name_en ? styles.selected : ''} onClick={() => { setTopic(item.name_en); setSuggestions(item.words.map((word) => ({word, meaning_vi: '', example: ''}))); }}>{item.name_en}</button>)}</div>
          <label className={styles.field}>Chủ đề của em<input value={topic} onChange={(e) => { setTopic(e.target.value); setSuggestions([]); }} /></label>
          <button className="secondary-button" type="button" disabled={busy} onClick={suggest}>Gợi ý từ cho chủ đề này</button>
          {suggestions.length > 0 && <div className={styles.suggestions}>{suggestions.map((item) => <button type="button" key={item.word} disabled={words.includes(item.word) || words.length >= 5} onClick={() => setWords([...words, item.word])}><strong>{item.word}</strong>{item.meaning_vi && <span>{item.meaning_vi}</span>}{item.example && <small>{item.example}</small>}</button>)}</div>}
          <div className={styles.wordEntry}><label className={styles.field}>Tự nhập từ muốn luyện<input value={wordInput} onChange={(e) => setWordInput(e.target.value)} /></label><button className="secondary-button" type="button" onClick={addWord}>Thêm từ</button></div>
          <div className={styles.chips}>{words.map((word) => <button type="button" key={word} onClick={() => setWords(words.filter((item) => item !== word))}>{word} ×</button>)}</div>
          {error && <div className="error-banner" role="alert">{error}</div>}
          <button className={styles.primary} disabled={busy} onClick={start}>Bắt đầu nói</button>
        </div>
      </section>
      <aside className="sidebar"><section className="panel"><div className="panel-heading"><span className="eyebrow">Cách học</span><h2>Speak your way</h2></div><p className="muted">Em có thể nói bằng micro hoặc nhập câu trả lời. Luna sẽ giúp em tiếp tục bằng những câu hỏi ngắn.</p></section></aside>
    </div>
  </main>;

  return <SpeakingPipecatProvider key={session.session_id}>
    <ActiveSpeakingRoom initialSession={session} api={api}/>
  </SpeakingPipecatProvider>;
}
