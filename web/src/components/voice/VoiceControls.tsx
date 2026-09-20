'use client';

import { PipecatClientMicToggle } from '@pipecat-ai/client-react';

import { useVoiceLesson } from './PipecatVoiceProvider';
import type { VoicePhase } from './PipecatVoiceProvider';
import styles from './voice.module.css';

const phaseLabels: Record<VoicePhase, string> = {
  off: 'Voice off',
  connecting: 'Connecting',
  ready: 'Ready',
  listening: 'Listening',
  thinking: 'Thinking',
  speaking: 'Speaking',
};

function VoicePhaseIcon({ phase }: { phase: VoicePhase }) {
  if (phase === 'thinking') {
    return <span className={styles.thinkingDots} aria-hidden="true"><i /><i /><i /></span>;
  }
  if (phase === 'listening') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="4" width="6" height="10" rx="3" /><path d="M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v3M9 20h6" /></svg>;
  }
  if (phase === 'speaking') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 10v4h3l4 3V7l-4 3H5Z" /><path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a7.5 7.5 0 0 1 0 11" /></svg>;
  }
  return <span className={styles.statusDot} aria-hidden="true" />;
}

export function VoiceControls({
  startLabel = 'Start voice lesson',
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
    await voice.stop();
    onStopped?.();
  }

  return (
    <div className={styles.voiceControls} aria-label="Voice lesson controls">
      <span className={`${styles.state} ${styles[voice.phase]}`} aria-live="polite">
        <span className={styles.phaseIcon}><VoicePhaseIcon phase={voice.phase} /></span>
        {phaseLabels[voice.phase]}
      </span>
      <div className={styles.actions}>
        {!active ? (
          <button type="button" className={styles.primary} disabled={pending} onClick={() => void voice.start()}>
            {pending ? 'Connecting…' : startLabel}
          </button>
        ) : (
          <>
            <PipecatClientMicToggle>
              {({ disabled, isMicEnabled, onClick }) => (
                <button type="button" className={styles.primary} disabled={disabled} onClick={onClick}>
                  {isMicEnabled ? 'Mute microphone' : 'Unmute microphone'}
                </button>
              )}
            </PipecatClientMicToggle>
            <button type="button" className={styles.secondary} onClick={() => void stop()}>
              {stopLabel}
            </button>
          </>
        )}
      </div>
      {voice.error && <p className={styles.error} role="alert">{voice.error}</p>}
    </div>
  );
}
