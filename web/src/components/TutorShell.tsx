'use client';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { ChatPanel } from './ChatPanel';
import { CurriculumNav } from './CurriculumNav';
import { LearnerHeader } from './LearnerHeader';
import { Composer } from './Composer';
import { NewSessionButton } from './NewSessionButton';
import { StateInspector } from './StateInspector';
import { UnitSelector } from './UnitSelector';
import { PipecatVoiceProvider } from './voice/PipecatVoiceProvider';
import { VoiceControls } from './voice/VoiceControls';
import { ApiError, TutorApi, tutorApi } from '@/lib/api';
import type { LessonSummary, SessionView, UnitSummary } from '@/lib/types';
import { unitPath } from '@/lib/unit-route';

function newTurnId() { return globalThis.crypto?.randomUUID?.() ?? `turn-${Date.now()}-${Math.random()}`; }

export function TutorShell({
  api = tutorApi,
  initialUnitId,
  initialLessonId,
}: {
  api?: TutorApi;
  initialUnitId?: string;
  initialLessonId?: number;
}) {
  const router = useRouter();
  const [current, setCurrent] = useState<SessionView | null>(null);
  const [units, setUnits] = useState<UnitSummary[]>([]);
  const [lessons, setLessons] = useState<LessonSummary[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const currentSessionId = current?.session_id;
  const lessonUnitId = current?.lesson_id != null ? current.unit_id : null;
  const replaceSession = useCallback((session: SessionView) => { setCurrent(session); }, []);
  useEffect(() => { const controller = new AbortController(); void (async () => {
    try {
      const availableUnits = await api.listUnits(controller.signal);
      setUnits(availableUnits);
      if (initialUnitId) replaceSession(await (
        initialLessonId === undefined
          ? api.createSession(initialUnitId, controller.signal)
          : api.createSession(initialUnitId, controller.signal, initialLessonId)
      ));
    }
    catch (reason) { if ((reason as Error).name !== 'AbortError') setError(reason as ApiError); } finally { if (!controller.signal.aborted) setBusy(false); }
  })(); return () => controller.abort(); }, [api, initialUnitId, initialLessonId, replaceSession]);
  useEffect(() => {
    if (!lessonUnitId) return;
    const controller = new AbortController();
    void api.listLessons(lessonUnitId, controller.signal).then((availableLessons) => {
      if (!controller.signal.aborted) setLessons(availableLessons);
    }).catch((reason: Error) => {
      if (reason.name !== 'AbortError') setError(reason as ApiError);
    });
    return () => controller.abort();
  }, [api, lessonUnitId]);
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
  function selectUnit(unitId: string) {
    const selectedUnit = units.find((unit) => unit.id === unitId);
    if (!selectedUnit) return;
    setBusy(true); setError(null);
    router.push(unitPath(selectedUnit.grade, selectedUnit.unit));
  }
  function chooseAnotherUnit() { setCurrent(null); router.push(current?.lesson_id ? '/grade3/unit1' : '/'); }
  async function startNew() { if (!current) return; setBusy(true); setError(null); try { replaceSession(await (
    current.lesson_id == null
      ? api.resetSession(current.unit.id)
      : api.resetSession(current.unit.id, undefined, current.lesson_id)
  )); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  async function finish() { if (!current) return; setBusy(true); setError(null); try { replaceSession(await api.finishSession(current.session_id, current.state_version)); } catch (reason) { setError(reason as ApiError); } finally { setBusy(false); } }
  if (!current && busy) return <main className="app-shell classroom-shell learner-app" aria-busy="true">
    <LearnerHeader subtitle="Gia sư tiếng Anh" />
    <div className="classroom-loading">
      <div className="classroom-loading-rail" aria-hidden="true" />
      <section className="classroom-loading-content" role="status">
        <span className="eyebrow">Luna English</span>
        <h1>{initialUnitId ? 'Đang mở lớp học…' : 'Đang tải chương trình học…'}</h1>
        <p>Con chờ Luna một chút nhé.</p>
      </section>
      <div className="classroom-loading-rail" aria-hidden="true" />
    </div>
  </main>;
  if (!current) return <><UnitSelector units={units} busy={busy} onSelect={(unitId) => { void selectUnit(unitId); }} />{error && <div className="error-banner" role="alert">{error.message}</div>}</>;
  return <PipecatVoiceProvider key={current.session_id} sessionId={current.session_id} enabled={current.status === 'active'} onSessionChanged={refreshVoiceSession}><main className="app-shell classroom-shell learner-app"><LearnerHeader subtitle={`English Tutor · Grade ${current.unit.grade} · Unit ${current.unit.unit}${current.lesson_id ? ` · Lesson ${current.lesson_id}` : ''}`}><span className={`status-pill ${current.status}`}>{current.status === 'active' ? 'Đang học' : current.status}</span><Link className="secondary-button" href="/talk">Free Talk Room</Link><button className="secondary-button" type="button" disabled={busy} onClick={chooseAnotherUnit}>{current.lesson_id ? 'Chọn Lesson khác' : 'Choose another unit'}</button><NewSessionButton busy={busy} onClick={startNew} /><span className="student-chip" aria-label="Học viên Quang">Q <span>Quang</span></span></LearnerHeader>
    <div className="workspace classroom-workspace"><CurriculumNav units={units} session={current} busy={busy} onSelect={selectUnit} expandedUnitId={lessonUnitId ?? undefined} lessons={lessons} lessonBasePath={lessonUnitId ? `${unitPath(current.unit.grade, current.unit.unit)}/lesson` : undefined} /><section className="lesson-card" role="region" aria-label="Lớp học Luna"><div className="lesson-heading"><div><h1 className="lesson-title">Practice with Luna</h1><span className="lesson-crumb">{current.lesson_id ? `Lesson ${current.lesson_id} · ` : ''}Lớp {current.unit.grade} · Unit {current.unit.unit} · {current.unit.title}</span></div><span className="stage-chip">{current.stage_id.replaceAll('-', ' ')}</span></div><div className="lesson-phases" aria-label="Các chặng học">{current.learning_focus.length > 0 ? current.learning_focus.map((focus) => <span key={focus.stage_id} className={focus.highlighted ? 'phase-current' : ''} aria-current={focus.highlighted ? 'step' : undefined}><span aria-hidden="true">{focus.highlighted ? '●' : '○'}</span> {focus.stage_title}</span>) : <span className="phase-current">● {current.stage_id.replaceAll('-', ' ')}</span>}</div><ChatPanel messages={current.messages} />
      {error && <div className="error-banner" role="alert"><strong>{error.retryable ? 'Please try again.' : 'Something changed.'}</strong> {error.message}</div>}
      {current.status === 'active' && <Composer disabled={busy} onSend={send} voiceControls={<VoiceControls />} />}
      {current.stage_id === 'free-talk' && current.status === 'active' && <button className="finish-button" disabled={busy} onClick={finish}>End Free Talk</button>}
      {current.summary && <section className="summary"><span className="eyebrow">Session complete</span><h2>What Quang showed today</h2><p>Demonstrated: {current.summary.demonstrated.join(', ') || 'Still gathering evidence'}</p><p>Review next time: {current.summary.needs_review.join(', ') || 'No open review items'}</p></section>}
    </section><aside className="sidebar"><StateInspector session={current} /></aside></div></main></PipecatVoiceProvider>;
}
