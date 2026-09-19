'use client';
import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import type { SpeakingApi } from '@/lib/speaking-api';
import { speakingApi } from '@/lib/speaking-api';
import type { SpeakingState, Summary, Topic } from '@/lib/speaking-types';
import styles from './speaking.module.css';
import { VoiceControls } from './VoiceControls';

type Message = {role: 'luna'|'learner'; text: string};
type SuggestedWord = {word: string; meaning_vi: string; example: string};
const turnId = () => globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}`;
const displayMessages = (state: SpeakingState): Message[] => state.messages.map((message) => ({
  role: message.role === 'teacher' ? 'luna' : 'learner', text: message.text,
}));

export function SpeakingRoom({api = speakingApi}: {api?: SpeakingApi}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topic, setTopic] = useState('');
  const [wordInput, setWordInput] = useState('');
  const [words, setWords] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestedWord[]>([]);
  const [session, setSession] = useState<SpeakingState|null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [answer, setAnswer] = useState('');
  const [summary, setSummary] = useState<Summary|null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const pending = useRef<{turn_id: string; text: string; expected_version: number}|null>(null);

  useEffect(() => { void api.topics().then(setTopics).catch((e) => setError(e.message)); }, [api]);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('session');
    if (!id) return;
    void api.get(id).then((value) => {
      setSession(value); setMessages(displayMessages(value));
    }).catch(() => window.history.replaceState(null, '', window.location.pathname));
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
      setSession(value); setMessages(displayMessages(value));
      window.history.replaceState(null, '', `?session=${encodeURIComponent(value.session_id)}`);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!session || !answer.trim() || busy) return;
    const text = answer.trim();
    const turn = pending.current ?? {turn_id: turnId(), text, expected_version: session.version};
    pending.current = turn; setAnswer(''); setBusy(true); setError('');
    try {
      const result = await api.submit(session.session_id, turn);
      pending.current = null; setSession(result.state); setMessages(displayMessages(result.state));
    } catch (e) { setAnswer(text); setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function finish() {
    if (!session) return;
    setBusy(true);
    try { const value = await api.finish(session.session_id, session.version); setSummary(value); setSession(value.state); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  const refresh = useCallback(async () => {
    if (!session) return;
    const value = await api.get(session.session_id);
    setSession(value); setMessages(displayMessages(value));
  }, [api, session]);

  if (!session) return <main className={styles.page}>
    <Link href="/">← Phòng học</Link>
    <section className={styles.card}>
      <span className={styles.eyebrow}>Lớp 5</span><h1>Luyện nói theo chủ đề</h1>
      <p>Chọn điều em thích và những từ em muốn dùng.</p>
      <div className={styles.topics}>{topics.map((item) => <button type="button" key={item.id} className={topic === item.name_en ? styles.selected : ''} onClick={() => { setTopic(item.name_en); setSuggestions(item.words.map((word) => ({word, meaning_vi: '', example: ''}))); }}>{item.name_en}</button>)}</div>
      <label>Chủ đề của em<input value={topic} onChange={(e) => { setTopic(e.target.value); setSuggestions([]); }} /></label>
      <button type="button" disabled={busy} onClick={suggest}>Gợi ý từ cho chủ đề này</button>
      {suggestions.length > 0 && <div className={styles.suggestions}>{suggestions.map((item) => <button type="button" key={item.word} disabled={words.includes(item.word) || words.length >= 5} onClick={() => setWords([...words, item.word])}><strong>{item.word}</strong>{item.meaning_vi && <span>{item.meaning_vi}</span>}{item.example && <small>{item.example}</small>}</button>)}</div>}
      <label>Tự nhập từ muốn luyện<input value={wordInput} onChange={(e) => setWordInput(e.target.value)} /></label>
      <button type="button" onClick={addWord}>Thêm từ</button>
      <div className={styles.chips}>{words.map((word) => <button type="button" key={word} onClick={() => setWords(words.filter((item) => item !== word))}>{word} ×</button>)}</div>
      {error && <p role="alert">{error}</p>}
      <button className={styles.primary} disabled={busy} onClick={start}>Bắt đầu nói</button>
    </section>
  </main>;

  return <main className={styles.page}><section className={styles.card}>
    <header><span className={styles.eyebrow}>{session.config.topic}</span><h1>Talk with Luna</h1>{session.status === 'active' && <VoiceControls sessionId={session.session_id} onRefresh={refresh} />}</header>
    <div className={styles.chat}>{messages.map((message, index) => <p className={message.role === 'luna' ? styles.luna : styles.learner} key={index}>{message.text}</p>)}</div>
    {error && <p role="alert">{error}</p>}
    {summary ? <section><h2>Good work!</h2><p>{summary.next_practice}</p><p>Đã tự dùng: {summary.independent.join(', ') || 'Chưa có bằng chứng'}</p></section> : <>
      <form onSubmit={send}><label>Câu trả lời<input value={answer} onChange={(e) => { setAnswer(e.target.value); if (pending.current && e.target.value !== pending.current.text) pending.current = null; }} disabled={busy}/></label><button className={styles.primary} disabled={busy}>Gửi</button></form>
      <button type="button" disabled={busy} onClick={finish}>Kết thúc</button>
    </>}
  </section></main>;
}
