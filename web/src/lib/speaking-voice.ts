import { PipecatClient } from '@pipecat-ai/client-js';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';

export class SpeakingVoiceClient {
  private client: PipecatClient | null = null;
  async connect(sessionId: string) {
    if (this.client) await this.disconnect();
    const client = new PipecatClient({transport: new SmallWebRTCTransport(), enableMic: true, enableCam: false});
    await client.startBotAndConnect({
      endpoint: process.env.NEXT_PUBLIC_SPEAKING_VOICE_URL ?? 'http://localhost:7860/start',
      requestData: {speaking_session_id: sessionId},
    });
    this.client = client;
  }
  async disconnect() { if (this.client) await this.client.disconnect(); this.client = null; }
  setMuted(muted: boolean) { this.client?.transport.enableMic(!muted); }
}
