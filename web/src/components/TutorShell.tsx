'use client';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { Composer } from './Composer';
import { NewSessionButton } from './NewSessionButton';
import { StateInspector } from './StateInspector';
import { PipecatVoiceProvider } from './voice/PipecatVoiceProvider';
import { VoiceControls } from './voice/VoiceControls';
import { ApiError, TutorApi, tutorApi } from '@/lib/api';
import type { SessionView } from '@/lib/types';

function newTurnId() { return globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}-${Math.random()}`; }

export function TutorShell({ api = tutorApi }: { api?: TutorApi }) {
  const [current, setCurrent] = useState<SessionView | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const currentSessionId = current?.session_id;
  useEffect(() => { const controller = new AbortController(); void (async () => {
    try { setCurrent(await api.resetSession(controller.signal)); }
    catch (reason) { if ((reason as Error).name !== 'AbortError') setError(reason as ApiError); } finally { setBusy(false); }
  })(); return () => controller.abort(); }, [api]);
  const replaceSession = useCallback((session: SessionView) => { setCurrent(session); }, []);
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
  async function startNew() { setBusy(true); setError(null); try { replaceSession(await api.resetSession()); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  async function finish() { if (!current) return; setBusy(true); setError(null); try { replaceSession(await api.finishSession(current.session_id, current.state_version)); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  if (!current) return <main className="loading"><div className="logo-mark">L</div><p>{error ? error.message : 'Opening your lesson…'}</p></main>;
  return <PipecatVoiceProvider key={current.session_id} sessionId={current.session_id} enabled={current.status === 'active'} onSessionChanged={refreshVoiceSession}><main className="app-shell"><header className="topbar"><div className="brand"><div className="logo-mark">L</div><div><span>Luna</span><small>English Tutor · Unit 1</small></div></div><div className="top-actions"><Link className="secondary-button" href="/talk">Free Talk Room</Link><span className={`status-pill ${current.status}`}>{current.status}</span><NewSessionButton busy={busy} onClick={startNew} /></div></header>
    <div className="workspace"><section className="lesson-card"><div className="lesson-heading"><div><span className="eyebrow">All about me!</span><h1 className="lesson-title">Practice with Luna</h1></div><span className="stage-chip">{current.stage_id.replaceAll('-', ' ')}</span></div><ChatPanel messages={current.messages} />
      {error && <div className="error-banner" role="alert"><strong>{error.retryable ? 'Please try again.' : 'Something changed.'}</strong> {error.message}</div>}
      {current.status === 'active' && <Composer disabled={busy} onSend={send} voiceControls={<VoiceControls />} />}
      {current.stage_id === 'free-talk' && current.status === 'active' && <button className="finish-button" disabled={busy} onClick={finish}>End Free Talk</button>}
      {current.summary && <section className="summary"><span className="eyebrow">Session complete</span><h2>What Quang showed today</h2><p>Demonstrated: {current.summary.demonstrated.join(', ') || 'Still gathering evidence'}</p><p>Review next time: {current.summary.needs_review.join(', ') || 'No open review items'}</p></section>}
    </section><aside className="sidebar"><StateInspector session={current} /></aside></div></main></PipecatVoiceProvider>;
}
