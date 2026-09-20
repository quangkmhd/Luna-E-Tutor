'use client';

import { useOptionalVoiceLesson } from './PipecatVoiceProvider';

export function VoiceLatency() {
  const voice = useOptionalVoiceLesson();
  if (!voice || voice.ttfaSeconds === null) return null;
  return <span className="voice-latency">{voice.ttfaSeconds.toFixed(2)}s</span>;
}
