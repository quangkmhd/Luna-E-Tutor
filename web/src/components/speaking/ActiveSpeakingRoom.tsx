'use client';

import type {BotOutputText, ConversationMessage, ConversationMessagePart} from '@pipecat-ai/client-react';
import {usePipecatConversation} from '@pipecat-ai/client-react';
import Link from 'next/link';
import type {FormEvent, ReactNode} from 'react';
import {useCallback, useEffect, useRef, useState} from 'react';

import type {SpeakingApi} from '@/lib/speaking-api';
import type {SpeakingState, Summary} from '@/lib/speaking-types';

import styles from './speaking.module.css';
import {VoiceControls} from './VoiceControls';

const turnId = () => globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}`;

function partText(text: ReactNode | BotOutputText): ReactNode {
  if (typeof text === 'object' && text !== null && 'spoken' in text && 'unspoken' in text) {
    return `${text.spoken}${text.unspoken}`;
  }
  return text;
}

function finalPart(text: string, createdAt: string): ConversationMessagePart {
  return {text, final: true, createdAt};
}

export function ActiveSpeakingRoom({initialSession, api}: {
  initialSession: SpeakingState;
  api: SpeakingApi;
}) {
  const [session, setSession] = useState(initialSession);
  const [answer, setAnswer] = useState('');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const pending = useRef<{turn_id: string; text: string; expected_version: number} | null>(null);
  const seededSessionId = useRef<string | null>(null);
  const synchronized = useRef(new Set<string>());

  const onMessageUpdated = useCallback((message: ConversationMessage) => {
    if (message.role !== 'assistant' || !message.final) return;
    if (synchronized.current.has(message.createdAt)) return;
    synchronized.current.add(message.createdAt);
    void api.get(session.session_id).then((value) => {
      setSession(value);
      setError('');
    }).catch((caught) => {
      synchronized.current.delete(message.createdAt);
      setError(caught instanceof Error ? caught.message : String(caught));
    });
  }, [api, session.session_id]);

  const {messages, injectMessage} = usePipecatConversation({onMessageUpdated});

  useEffect(() => {
    if (seededSessionId.current === initialSession.session_id) return;
    seededSessionId.current = initialSession.session_id;
    initialSession.messages.forEach((message, index) => {
      const createdAt = new Date(index).toISOString();
      injectMessage({
        role: message.role === 'teacher' ? 'assistant' : 'user',
        parts: [finalPart(message.text, createdAt)],
      });
    });
  }, [initialSession, injectMessage]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!answer.trim() || busy) return;
    const text = answer.trim();
    const turn = pending.current ?? {turn_id: turnId(), text, expected_version: session.version};
    pending.current = turn;
    setAnswer('');
    setBusy(true);
    setError('');
    try {
      const result = await api.submit(session.session_id, turn);
      const timestamp = Date.now();
      injectMessage({role: 'user', parts: [finalPart(text, new Date(timestamp).toISOString())]});
      injectMessage({role: 'assistant', parts: [finalPart(result.reply.text, new Date(timestamp + 1).toISOString())]});
      pending.current = null;
      setSession(result.state);
    } catch (caught) {
      setAnswer(text);
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    setBusy(true);
    try {
      const value = await api.finish(session.session_id, session.version);
      setSummary(value);
      setSession(value.state);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="logo-mark">L</div><div><span>Luna</span><small>English Tutor · Topic Speaking</small></div></div>
      <div className="top-actions"><Link className="secondary-button" href="/">Unit 1</Link><span className={`status-pill ${session.status}`}>{session.status}</span></div>
    </header>
    <div className="workspace">
      <section className="lesson-card">
        <div className="lesson-heading"><div><span className="eyebrow">{session.config.topic}</span><h1>Talk with Luna</h1></div><span className="stage-chip">Level {session.level}</span></div>
        <div className="chat-scroll" aria-live="polite" aria-label="Conversation with Luna">
          {messages.filter((message) => message.role === 'user' || message.role === 'assistant').map((message, messageIndex) => <article className={`bubble-row ${message.role === 'assistant' ? 'teacher' : 'learner'}`} key={`${message.createdAt}-${message.role}-${messageIndex}`}>
            {message.role === 'assistant' && <div className="avatar" aria-hidden="true">L</div>}
            <div className="bubble"><span className="speaker">{message.role === 'assistant' ? 'Luna' : 'Em'}</span><p>{message.parts.map((part, index) => <span key={`${part.createdAt}-${index}`}>{partText(part.text)}</span>)}</p></div>
          </article>)}
        </div>
        {error && <div className="error-banner" role="alert"><strong>Hãy thử lại.</strong> {error}</div>}
        {summary ? <section className="summary"><span className="eyebrow">Hoàn thành</span><h2>Good work!</h2><p>{summary.next_practice}</p><p>Đã tự dùng: {summary.independent.join(', ') || 'Chưa có bằng chứng'}</p></section> : <>
          <form className="composer" onSubmit={send}><label className="sr-only" htmlFor="speaking-answer">Câu trả lời</label><input id="speaking-answer" value={answer} placeholder="Nhập câu em muốn nói…" onChange={(event) => { setAnswer(event.target.value); if (pending.current && event.target.value !== pending.current.text) pending.current = null; }} disabled={busy}/><button disabled={busy || !answer.trim()}>{busy ? 'Luna is thinking…' : 'Gửi'}</button></form>
          <button className="finish-button" type="button" disabled={busy} onClick={finish}>Kết thúc</button>
        </>}
      </section>
      <aside className="sidebar">
        <section className="panel"><div className="panel-heading"><span className="eyebrow">Voice</span><h2>Nói cùng Luna</h2></div>{session.status === 'active' && <VoiceControls sessionId={session.session_id} onConnectionError={setError}/>}<p className="muted">Bật micro để dùng Soniox STT và nghe Luna trả lời bằng giọng Grace.</p></section>
        <section className="panel"><div className="panel-heading"><span className="eyebrow">Mục tiêu</span><h2>Từ cần luyện</h2></div><div className={styles.practiceWords}>{session.config.words.map((word) => { const use = session.word_evidence.find((item) => item.word === word); return <div key={word}><strong>{word}</strong><small>{use ? use.independent ? 'Đã tự dùng' : 'Đã dùng với hỗ trợ' : 'Chưa dùng'}</small></div>; })}</div></section>
      </aside>
    </div>
  </main>;
}
