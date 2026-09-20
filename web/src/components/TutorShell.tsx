'use client';
import { useCallback, useEffect, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { Composer } from './Composer';
import { HistoryPanel } from './HistoryPanel';
import { NewSessionButton } from './NewSessionButton';
import { StateInspector } from './StateInspector';
import { PipecatVoiceProvider } from './voice/PipecatVoiceProvider';
import { VoiceControls } from './voice/VoiceControls';
import { ApiError, TutorApi, tutorApi } from '@/lib/api';
import type { SessionView } from '@/lib/types';

function newTurnId() { return globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}-${Math.random()}`; }

export function TutorShell({ api = tutorApi }: { api?: TutorApi }) {
  const [sessions, setSessions] = useState<SessionView[]>([]);
  const [current, setCurrent] = useState<SessionView | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const currentSessionId = current?.session_id;
  useEffect(() => { const controller = new AbortController(); void (async () => {
    try { const history = await api.listSessions(controller.signal); const selected = history[0] ?? await api.createSession(controller.signal); setSessions(history.length ? history : [selected]); setCurrent(selected); }
    catch (reason) { if ((reason as Error).name !== 'AbortError') setError(reason as ApiError); } finally { setBusy(false); }
  })(); return () => controller.abort(); }, [api]);
  const replaceSession = useCallback((session: SessionView) => { setCurrent(session); setSessions((items) => [session, ...items.filter((item) => item.session_id !== session.session_id)]); }, []);
  const refreshVoiceSession = useCallback(async () => {
    if (!currentSessionId) return;
    try { replaceSession(await api.getSession(currentSessionId)); }
    catch (reason) { setError(reason as ApiError); }
  }, [api, currentSessionId, replaceSession]);
  async function send(text: string) {
    if (!current || busy) return;
    const previous = current;
    const turnId = newTurnId();
    setCurrent({ ...previous, messages: [...previous.messages, { role: 'learner', text, turn_id: turnId }] });
    setBusy(true); setError(null);
    try {
      const response = await api.submitTurn(previous.session_id, {
        turn_id: turnId, expected_state_version: previous.state_version, learner_text: text,
      });
      replaceSession(response.session);
    } catch (reason) {
      setCurrent(previous);
      setError(reason as ApiError);
    } finally { setBusy(false); }
  }
  async function select(id: string) { setBusy(true); setError(null); try { replaceSession(await api.getSession(id)); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  async function startNew() { if (current?.status === 'active' && !window.confirm('Start over? This session will stay in history.')) return; setBusy(true); setError(null); try { if (current?.status === 'active') { const old = await api.abandonSession(current.session_id); setSessions((items) => items.map((item) => item.session_id === old.session_id ? old : item)); } replaceSession(await api.createSession()); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  async function finish() { if (!current) return; setBusy(true); setError(null); try { replaceSession(await api.finishSession(current.session_id, current.state_version)); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  if (!current) return <main className="loading"><div className="logo-mark">L</div><p>{error ? error.message : 'Opening your lesson…'}</p></main>;
  return <PipecatVoiceProvider key={current.session_id} sessionId={current.session_id} onSessionChanged={refreshVoiceSession}><main className="app-shell"><header className="topbar"><div className="brand"><div className="logo-mark">L</div><div><span>Luna</span><small>English Tutor · Unit 1</small></div></div><div className="top-actions"><span className={`status-pill ${current.status}`}>{current.status}</span><NewSessionButton busy={busy} onClick={startNew} /></div></header>
    <div className="workspace"><section className="lesson-card"><div className="lesson-heading"><div><span className="eyebrow">All about me!</span><h1>Practice with Luna</h1></div><span className="stage-chip">{current.stage_id.replaceAll('-', ' ')}</span></div><ChatPanel messages={current.messages} />
      {error && <div className="error-banner" role="alert"><strong>{error.retryable ? 'Please try again.' : 'Something changed.'}</strong> {error.message}</div>}
      {current.status === 'active' && <><VoiceControls /><div className="typed-fallback"><span>Prefer typing?</span><Composer disabled={busy} onSend={send} /></div></>}
      {current.stage_id === 'free-talk' && current.status === 'active' && <button className="finish-button" disabled={busy} onClick={finish}>End Free Talk</button>}
      {current.summary && <section className="summary"><span className="eyebrow">Session complete</span><h2>What Quang showed today</h2><p>Demonstrated: {current.summary.demonstrated.join(', ') || 'Still gathering evidence'}</p><p>Review next time: {current.summary.needs_review.join(', ') || 'No open review items'}</p></section>}
    </section><aside className="sidebar"><StateInspector session={current} /><HistoryPanel sessions={sessions} selectedId={current.session_id} onSelect={select} /></aside></div></main></PipecatVoiceProvider>;
}
