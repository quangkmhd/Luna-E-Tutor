'use client';

import { useEffect } from 'react';
import { useVoiceLesson } from './PipecatVoiceProvider';
import styles from './voice.module.css';

export function VoiceControls({
  lessonMode = false,
  startLabel = 'Bật mic để nói',
  stopLabel = 'Stop voice lesson',
  onStopped,
}: {
  lessonMode?: boolean;
  startLabel?: string;
  stopLabel?: string;
  onStopped?: () => void;
}) {
  const voice = useVoiceLesson();
  const active = voice.transportState === 'connected' || voice.transportState === 'ready';
  const pending = ['initializing', 'connecting', 'authenticating'].includes(
    voice.transportState,
  );
  const starting = pending || (!active && voice.phase === 'connecting');
  const submittingLessonTurn = lessonMode && active && voice.manualSubmit && voice.micMode !== 'off';

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.code !== 'Space' || event.repeat || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      if (!active || starting || !voice.turnReady) return;
      if (event.target instanceof Element && event.target.closest('button, input, textarea, select, a, summary, [role="button"], [contenteditable]:not([contenteditable="false"])')) return;
      if (voice.micMode !== 'off' && !voice.manualSubmit) return;
      event.preventDefault();
      if (voice.micMode === 'off') voice.toggleMic();
      else void voice.submitVoice();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [active, starting, voice]);

  async function stop() {
    try {
      await voice.stop();
    } finally {
      onStopped?.();
    }
  }

  return (
    <div className={styles.voiceControls} aria-label="Voice lesson controls">
      <span className={`${styles.state} ${voice.micMode === 'off' ? styles.micOffState : styles.micOnState}`} aria-live="polite">
        <strong>{starting ? 'Đang kết nối' : lessonMode && !active ? 'CHƯA BẮT ĐẦU' : voice.micMode === 'speaking' ? 'Đang nói' : voice.micMode === 'listening' ? 'Đang nghe' : 'MIC ĐANG TẮT'}</strong>
      </span>
      {lessonMode && active && voice.turnReady && <span className={styles.shortcutHint} aria-live="polite">
        {voice.micMode === 'off' ? 'Nhấn Space để mở mic' : 'Nhấn Space để gửi'}
      </span>}
      {active && voice.phase === 'speaking' && <span className={styles.speakerPlaying} role="status" aria-label="Loa đang phát">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4Z" /><path className={styles.speakerWave} d="M16 9a4 4 0 0 1 0 6" /><path className={`${styles.speakerWave} ${styles.speakerWaveOuter}`} d="M18.5 6a8 8 0 0 1 0 12" /></svg>
        <strong>LOA ĐANG PHÁT</strong>
      </span>}
      <div className={styles.actions}>
        {active && voice.retryableTurn && <button type="button" className={styles.secondary} onClick={voice.retryVoice}>
          Gửi lại lượt vừa nói
        </button>}
        {lessonMode && !active ? <button type="button" className={styles.startLesson} disabled={starting} onClick={() => void voice.start()}>
          {starting ? 'Đang kết nối…' : 'Bắt đầu Lesson'}
        </button> : submittingLessonTurn ? <button type="button" className={styles.submitTurn} onClick={() => void voice.submitVoice()}>
          Gửi lượt nói
        </button> : <button
          type="button"
          className={`${styles.micButton} ${voice.micMode === 'off' ? styles.micIdle : ''} ${voice.micMode !== 'off' ? styles.micActive : ''} ${voice.micMode === 'speaking' ? styles.micSpeaking : ''}`}
          aria-label={pending ? 'Đang kết nối mic' : voice.micMode === 'off' ? 'Bật mic để nói' : voice.manualSubmit ? 'Đang thu lời nói' : 'Tắt mic'}
          aria-pressed={active && voice.micMode !== 'off'}
          disabled={starting || (active && (!voice.turnReady || (voice.manualSubmit && voice.micMode !== 'off')))}
          title={!active ? startLabel : undefined}
          onClick={() => { if (active) voice.toggleMic(); else void voice.start(); }}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" />{voice.micMode === 'off' && <path data-mic-off-mark="true" d="M4 4l16 16" />}</svg>
        </button>}
        {!lessonMode && active && voice.manualSubmit && voice.micMode !== 'off' && <button type="button" className={styles.secondary} onClick={() => void voice.submitVoice()}>
          Gửi
        </button>}
        {active && <button type="button" className={styles.secondary} onClick={() => void stop()}>
          {stopLabel}
        </button>}
      </div>
      {voice.error && <p className={styles.error} role="alert">{voice.error}</p>}
    </div>
  );
}
