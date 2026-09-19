'use client';
import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import type { SpeakingApi } from '@/lib/speaking-api';
import { speakingApi } from '@/lib/speaking-api';
import type { SpeakingState, Summary, Topic } from '@/lib/speaking-types';
import styles from './speaking.module.css';

type Message = {role: 'luna'|'learner'; text: string};
const turnId = () => globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}`;

export function SpeakingRoom({api = speakingApi}: {api?: SpeakingApi}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topic, setTopic] = useState('');
  const [wordInput, setWordInput] = useState('');
  const [words, setWords] = useState<string[]>([]);
  const [session, setSession] = useState<SpeakingState|null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [answer, setAnswer] = useState('');
  const [summary, setSummary] = useState<Summary|null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { void api.topics().then(setTopics).catch((e) => setError(e.message)); }, [api]);
  function addWord() {
    const value = wordInput.trim().toLowerCase();
    if (!value || words.includes(value)) return;
    if (words.length >= 5) return setError('Mỗi phiên chọn tối đa 5 từ.');
    setWords([...words, value]); setWordInput(''); setError('');
  }
  async function start() {
    if (!topic.trim() || words.length < 1) return setError('Hãy chọn chủ đề và ít nhất một từ.');
    setBusy(true); setError('');
    try { const value = await api.create({grade: 5, topic, words}); setSession(value); setMessages([{role: 'luna', text: value.opening_message}]); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function send(event: FormEvent) {
    event.preventDefault(); if (!session || !answer.trim() || busy) return;
    const text = answer.trim(); setAnswer(''); setBusy(true); setError('');
    try { const result = await api.submit(session.session_id, {turn_id: turnId(), text, expected_version: session.version}); setSession(result.state); setMessages((old) => [...old, {role: 'learner', text}, {role: 'luna', text: result.reply.text}]); }
    catch (e) { setAnswer(text); setError((e as Error).message); } finally { setBusy(false); }
  }
  async function finish() { if (!session) return; setBusy(true); try { const value = await api.finish(session.session_id, session.version); setSummary(value); setSession(value.state); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  if (!session) return <main className={styles.page}><Link href="/">← Phòng học</Link><section className={styles.card}><span className={styles.eyebrow}>Lớp 5</span><h1>Luyện nói theo chủ đề</h1><p>Chọn điều em thích và những từ em muốn dùng.</p><div className={styles.topics}>{topics.map((item) => <button type="button" key={item.id} className={topic === item.name_en ? styles.selected : ''} onClick={() => setTopic(item.name_en)}>{item.name_en}</button>)}</div><label>Chủ đề của em<input value={topic} onChange={(e) => setTopic(e.target.value)} /></label><label>Từ muốn luyện<input value={wordInput} onChange={(e) => setWordInput(e.target.value)} /></label><button type="button" onClick={addWord}>Thêm từ</button><div className={styles.chips}>{words.map((word) => <button type="button" key={word} onClick={() => setWords(words.filter((item) => item !== word))}>{word} ×</button>)}</div>{error && <p role="alert">{error}</p>}<button className={styles.primary} disabled={busy} onClick={start}>Bắt đầu nói</button></section></main>;
  return <main className={styles.page}><section className={styles.card}><header><span className={styles.eyebrow}>{session.config.topic}</span><h1>Talk with Luna</h1></header><div className={styles.chat}>{messages.map((message, index) => <p className={message.role === 'luna' ? styles.luna : styles.learner} key={index}>{message.text}</p>)}</div>{error && <p role="alert">{error}</p>}{summary ? <section><h2>Good work!</h2><p>{summary.next_practice}</p><p>Đã tự dùng: {summary.independent.join(', ') || 'Chưa có bằng chứng'}</p></section> : <><form onSubmit={send}><label>Câu trả lời<input value={answer} onChange={(e) => setAnswer(e.target.value)} disabled={busy}/></label><button className={styles.primary} disabled={busy}>Gửi</button></form><button type="button" disabled={busy} onClick={finish}>Kết thúc</button></>}</section></main>;
}
