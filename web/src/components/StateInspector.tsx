import type { SessionView } from '@/lib/types';
const human = (value?: string | null) => value?.replaceAll('-', ' ').replaceAll('_', ' ') ?? '—';

export function StateInspector({ session }: { session: SessionView }) {
  return <details className="panel inspector">
    <summary className="inspector-summary"><span><span className="eyebrow">Unit {session.unit.unit}</span><strong>Lesson progress</strong></span><small>View details</small></summary>
    <div className="inspector-content"><div className="panel-heading"><h2>Teaching details</h2></div>
    <dl className="state-grid"><div><dt>Stage</dt><dd>{human(session.stage_id)}</dd></div><div><dt>Activity</dt><dd>{human(session.activity_id)}</dd></div><div><dt>Objective</dt><dd>{human(session.objective_id)}</dd></div><div><dt>Version</dt><dd>{session.state_version}</dd></div></dl>
    <div className="decision-card"><span>Last decision</span><strong>{human(session.last_decision?.feedback_action)}</strong><small>{human(session.last_decision?.progression_action)}</small></div>
    <div className="evidence-list"><span>Evidence</span>{session.last_evidence?.objective_evidence.length ? session.last_evidence.objective_evidence.map((item) => <div key={item.objective_id}><strong>{human(item.objective_id.split('.').at(-1))}</strong><small>{human(item.meaning_status)} · {human(item.target_form_status)}</small></div>) : <p className="muted">No learner evidence yet.</p>}</div>
    {!!session.review_queue.length && <div className="review-box"><span>Review in Free Talk</span>{session.review_queue.map((item) => <small key={item.objective_id}>{human(item.objective_id)}</small>)}</div>}
    </div>
  </details>;
}
