'use client';

import { FormEvent, useEffect, useState } from 'react';

import { ApiError, TutorApi, tutorApi } from '@/lib/api';
import type { ComparisonBranch, ComparisonResult, SessionView } from '@/lib/types';


function BranchCard({ title, branch }: { title: string; branch: ComparisonBranch }) {
  return (
    <article className="review-branch">
      <header>
        <div>
          <span className="eyebrow">{title}</span>
          <h2>{branch.evaluator_model}</h2>
        </div>
        <span className="review-total">{branch.total_latency_ms} ms total</span>
      </header>
      <div className="teacher-output">
        <span>Gemini Teacher</span>
        <p>{branch.teacher_output}</p>
      </div>
      <div className="latency-row">
        <span>{branch.planning_latency_ms} ms planning</span>
        <span>{branch.teacher_latency_ms} ms teacher</span>
      </div>
      <details>
        <summary>Evaluator evidence and Engine decision</summary>
        <dl className="review-details">
          <div><dt>Response</dt><dd>{branch.evidence.response_kind}</dd></div>
          <div><dt>Feedback</dt><dd>{branch.decision.feedback_action}</dd></div>
          <div><dt>Progression</dt><dd>{branch.decision.progression_action}</dd></div>
        </dl>
        {branch.evidence.objective_evidence.map((item) => (
          <div className="objective-result" key={item.objective_id}>
            <strong>{item.objective_id}</strong>
            <span>{item.meaning_status} · {item.target_form_status} · recast {String(item.recast_needed)}</span>
          </div>
        ))}
      </details>
    </article>
  );
}


export function ReviewWorkbench({ api = tutorApi }: { api?: TutorApi }) {
  const [session, setSession] = useState<SessionView | null>(null);
  const [text, setText] = useState('');
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        const sessions = await api.listSessions(controller.signal);
        const current = sessions.find((item) => item.status === 'active')
          ?? sessions[0]
          ?? await api.createSession(controller.signal);
        setSession(current);
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load Unit state.');
      }
    })();
    return () => controller.abort();
  }, [api]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!session || !text.trim() || busy) return;
    setBusy(true);
    setError('');
    try {
      setResult(await api.compareEvaluators(session.session_id, text.trim()));
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message
        : cause instanceof Error ? cause.message : 'Comparison failed.';
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  if (!session && !error) return <main className="review-loading">Loading Unit state…</main>;

  return (
    <main className="review-page">
      <header className="review-heading">
        <div>
          <span className="eyebrow">Evaluator A/B review</span>
          <h1>Same Unit logic. Two evaluator paths.</h1>
          <p>Both paths use the deterministic Teaching Engine and the same Gemini Teacher.</p>
        </div>
        {session && <div className="review-state">
          <span>State v{session.state_version}</span>
          <strong>{session.stage_id} · {session.activity_id ?? 'no activity'}</strong>
        </div>}
      </header>

      <form className="review-input" onSubmit={submit}>
        <label htmlFor="learner-text">Learner text</label>
        <textarea id="learner-text" value={text} onChange={(event) => setText(event.target.value)}
          placeholder="Type exactly what the learner says…" rows={4} />
        <button type="submit" disabled={!session || !text.trim() || busy}>
          {busy ? 'Running both paths…' : 'Run comparison'}
        </button>
      </form>

      {error && <p className="error-banner" role="alert">{error}</p>}
      {result && <section className="review-grid" aria-label="Comparison results">
        <BranchCard title="Gemini Evaluator path" branch={result.gemini} />
        <BranchCard title="Jev Evaluator path" branch={result.jev} />
      </section>}
    </main>
  );
}
