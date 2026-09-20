'use client';

import { TransportStateEnum } from '@pipecat-ai/client-js';
import {
  usePipecatClient,
  usePipecatClientMicControl,
  usePipecatClientTransportState,
} from '@pipecat-ai/client-react';

export function VoiceControls({sessionId, onConnectionError}: {
  sessionId: string;
  onConnectionError: (message: string) => void;
}) {
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();
  const {enableMic, isMicEnabled} = usePipecatClientMicControl();
  const connected = transportState === TransportStateEnum.CONNECTED
    || transportState === TransportStateEnum.READY;
  const pending = transportState === TransportStateEnum.INITIALIZING
    || transportState === TransportStateEnum.CONNECTING;

  async function toggle() {
    onConnectionError('');
    try {
      if (connected) {
        enableMic(!isMicEnabled);
        return;
      }
      if (!client) throw new Error('Pipecat client is not ready');
      await client.initDevices();
      await client.startBotAndConnect({
        endpoint: 'http://localhost:7860/start',
        requestData: {body: {speaking_session_id: sessionId}},
        timeout: 10_000,
      });
    } catch (error) {
      onConnectionError(error instanceof Error ? error.message : String(error));
    }
  }

  const label = pending
    ? 'Đang kết nối…'
    : connected && isMicEnabled
      ? 'Tắt micro'
      : 'Bật micro';

  return (
    <div className="voice-controls">
      <button className="secondary-button" type="button" onClick={toggle} disabled={pending}>
        {label}
      </button>
    </div>
  );
}
