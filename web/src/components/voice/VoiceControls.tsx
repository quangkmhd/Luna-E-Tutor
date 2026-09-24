'use client';

import { useVoiceLesson } from './PipecatVoiceProvider';
import styles from './voice.module.css';

export function VoiceControls({
  startLabel = 'Bật mic để nói',
  stopLabel = 'Stop voice lesson',
  onStopped,
}: {
  startLabel?: string;
  stopLabel?: string;
  onStopped?: () => void;
}) {
  const voice = useVoiceLesson();
  const active = voice.transportState === 'connected' || voice.transportState === 'ready';
  const pending = ['initializing', 'connecting', 'authenticating'].includes(
    voice.transportState,
  );

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
        <strong>{pending || (!active && voice.phase === 'connecting') ? 'Đang kết nối' : voice.micMode === 'speaking' ? 'Đang nói' : voice.micMode === 'listening' ? 'Đang nghe' : 'MIC ĐANG TẮT'}</strong>
      </span>
      {active && voice.phase === 'speaking' && <span className={styles.speakerPlaying} role="status" aria-label="Loa đang phát">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4Z" /><path className={styles.speakerWave} d="M16 9a4 4 0 0 1 0 6" /><path className={`${styles.speakerWave} ${styles.speakerWaveOuter}`} d="M18.5 6a8 8 0 0 1 0 12" /></svg>
        <strong>LOA ĐANG PHÁT</strong>
      </span>}
      <div className={styles.actions}>
        <button
          type="button"
          className={`${styles.micButton} ${voice.micMode === 'off' ? styles.micIdle : ''} ${voice.micMode !== 'off' ? styles.micActive : ''} ${voice.micMode === 'speaking' ? styles.micSpeaking : ''}`}
          aria-label={pending ? 'Đang kết nối mic' : voice.micMode === 'off' ? 'Bật mic để nói' : voice.manualSubmit ? 'Đang thu lời nói' : 'Tắt mic'}
          aria-pressed={active && voice.micMode !== 'off'}
          disabled={pending || (active && (!voice.turnReady || (voice.manualSubmit && voice.micMode !== 'off')))}
          title={!active ? startLabel : undefined}
          onClick={() => { if (active) voice.toggleMic(); else void voice.start(); }}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" />{voice.micMode === 'off' && <path data-mic-off-mark="true" d="M4 4l16 16" />}</svg>
        </button>
        {active && voice.manualSubmit && voice.micMode !== 'off' && <button type="button" className={styles.secondary} onClick={() => void voice.submitVoice()}>
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
