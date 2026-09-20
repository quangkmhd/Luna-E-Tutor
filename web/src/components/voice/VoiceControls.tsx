'use client';

import { PipecatClientMicToggle } from '@pipecat-ai/client-react';

import { useVoiceLesson } from './PipecatVoiceProvider';
import styles from './voice.module.css';

export function VoiceControls() {
  const voice = useVoiceLesson();
  const active = voice.transportState === 'connected' || voice.transportState === 'ready';
  const pending = ['initializing', 'connecting', 'authenticating'].includes(
    voice.transportState,
  );
  const transcript = voice.interimTranscript || voice.finalTranscript;

  return (
    <section className={styles.voicePanel} aria-label="Voice lesson controls">
      <div className={styles.heading}>
        <div>
          <span className={styles.eyebrow}>Live speaking</span>
          <strong>Talk with Luna</strong>
        </div>
        <span className={styles.state}>{voice.transportState}</span>
      </div>
      <div className={styles.actions}>
        {!active ? (
          <button type="button" className={styles.primary} disabled={pending} onClick={() => void voice.start()}>
            {pending ? 'Connecting…' : 'Start voice lesson'}
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
            <button type="button" className={styles.secondary} onClick={() => void voice.stop()}>
              Stop voice lesson
            </button>
          </>
        )}
      </div>
      {transcript && (
        <p className={styles.transcript} aria-live="polite">
          <span>You said</span> {transcript}{voice.interimTranscript ? '…' : ''}
        </p>
      )}
      {voice.botOutput && <p className={styles.botOutput} aria-live="polite">Luna: {voice.botOutput}</p>}
      {voice.error && <p className={styles.error} role="alert">{voice.error}</p>}
    </section>
  );
}
