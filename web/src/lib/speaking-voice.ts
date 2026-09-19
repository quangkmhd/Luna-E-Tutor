import { PipecatClient } from '@pipecat-ai/client-js';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';

export class SpeakingVoiceClient {
  private client: PipecatClient | null = null;
  private audio: HTMLAudioElement | null = null;
  constructor(private onPlaybackBlocked: () => void = () => undefined) {}
  async connect(sessionId: string) {
    if (this.client) await this.disconnect();
    const client = new PipecatClient({transport: new SmallWebRTCTransport(), enableMic: true, enableCam: false,
      callbacks: {onTrackStarted: (track) => {
        if (track.kind !== 'audio') return;
        this.audio = new Audio(); this.audio.autoplay = true;
        this.audio.srcObject = new MediaStream([track]);
        void this.audio.play().catch(() => this.onPlaybackBlocked());
      }}});
    await client.startBotAndConnect({
      endpoint: process.env.NEXT_PUBLIC_SPEAKING_VOICE_URL ?? 'http://localhost:7860/start',
      requestData: {speaking_session_id: sessionId},
    });
    this.client = client;
  }
  async resumeAudio() { await this.audio?.play(); }
  async disconnect() { if (this.client) await this.client.disconnect(); this.client = null; if (this.audio) { this.audio.pause(); this.audio.srcObject = null; this.audio = null; } }
  setMuted(muted: boolean) { this.client?.transport.enableMic(!muted); }
}
