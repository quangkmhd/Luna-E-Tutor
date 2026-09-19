'use client';
import { useEffect, useRef, useState } from 'react';
import { SpeakingVoiceClient } from '@/lib/speaking-voice';

export function VoiceControls({sessionId}: {sessionId: string}) {
  const voice = useRef<SpeakingVoiceClient | null>(null);
  const [status, setStatus] = useState<'off'|'connecting'|'on'|'error'>('off');
  useEffect(() => () => { void voice.current?.disconnect(); }, []);
  async function toggle() {
    if (status === 'on') { await voice.current?.disconnect(); setStatus('off'); return; }
    setStatus('connecting');
    try { voice.current = new SpeakingVoiceClient(); await voice.current.connect(sessionId); setStatus('on'); }
    catch { setStatus('error'); }
  }
  return <div><button type="button" onClick={toggle} disabled={status === 'connecting'}>{status === 'on' ? 'Tắt micro' : status === 'connecting' ? 'Đang kết nối…' : 'Bật micro'}</button>{status === 'error' && <span role="alert"> Không kết nối được micro. Em vẫn có thể nhập câu trả lời.</span>}</div>;
}
