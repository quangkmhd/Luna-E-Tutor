import type { SessionView } from '@/lib/types';

export function HistoryPanel({ sessions, selectedId, onSelect }: { sessions: SessionView[]; selectedId: string; onSelect(id: string): void }) {
  return <section className="panel history" aria-labelledby="history-title"><div className="panel-heading"><span className="eyebrow">Saved locally</span><h2 id="history-title">Session history</h2></div><div className="history-list">
    {sessions.map((session, index) => <button className={session.session_id === selectedId ? 'selected' : ''} key={session.session_id} onClick={() => onSelect(session.session_id)}><span>Session {sessions.length - index}</span><small>{session.stage_id.replaceAll('-', ' ')} · {session.status}</small></button>)}
  </div></section>;
}
