'use client';

import { PipecatClient } from '@pipecat-ai/client-js';
import type {
  BotOutputData,
  DeviceError,
  TranscriptData,
  TransportState,
} from '@pipecat-ai/client-js';
import { PipecatClientAudio, PipecatClientProvider } from '@pipecat-ai/client-react';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';
import {
  createContext,
  useContext,
  useEffect,
  useState,
} from 'react';

type VoiceContextValue = {
  botOutput: string;
  error: string | null;
  finalTranscript: string;
  interimTranscript: string;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  transportState: TransportState;
};

const VoiceContext = createContext<VoiceContextValue | null>(null);

function deviceErrorMessage(error: DeviceError): string {
  if (error.type === 'permissions') {
    return 'Allow microphone access in your browser settings, then try again.';
  }
  if (error.type === 'in-use') {
    return 'Your microphone is being used by another app. Close it there, then try again.';
  }
  if (error.type === 'not-found') {
    return 'No microphone was found. Connect one, then try again.';
  }
  return 'The microphone could not start. Check the device and try again.';
}

export function useVoiceLesson(): VoiceContextValue {
  const value = useContext(VoiceContext);
  if (!value) throw new Error('useVoiceLesson must be used inside PipecatVoiceProvider');
  return value;
}

export function PipecatVoiceProvider({
  sessionId,
  children,
  onSessionChanged,
}: {
  sessionId: string;
  children: React.ReactNode;
  onSessionChanged?: () => void | Promise<void>;
}) {
  const [transportState, setTransportState] = useState<TransportState>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [botOutput, setBotOutput] = useState('');
  const [client] = useState(() => new PipecatClient({
    transport: new SmallWebRTCTransport(),
    enableMic: true,
    enableCam: false,
    disconnectOnBotDisconnect: true,
    callbacks: {
      onTransportStateChanged: setTransportState,
      onBotReady: () => setError(null),
      onUserTranscript: (data: TranscriptData) => {
        if (data.final) {
          setFinalTranscript(data.text);
          setInterimTranscript('');
        } else {
          setInterimTranscript(data.text);
        }
      },
      onBotOutput: (data: BotOutputData) => setBotOutput(data.text),
      onBotStoppedSpeaking: () => {
        if (!onSessionChanged) return;
        setTimeout(() => void onSessionChanged(), 150);
      },
      onDeviceError: (reason: DeviceError) => setError(deviceErrorMessage(reason)),
      onError: () => setError('The voice service reported an error. Stop and reconnect.'),
      onMessageError: () => setError('The voice service could not process that message. Try again.'),
    },
  }));

  async function start() {
    setError(null);
    try {
      await client.startBotAndConnect({
        endpoint: `${process.env.NEXT_PUBLIC_PIPECAT_URL ?? 'http://localhost:7860'}/start`,
        requestData: {
          transport: 'webrtc',
          body: { session_id: sessionId },
        },
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start the voice lesson.');
    }
  }

  async function stop() {
    await client.disconnect();
  }

  useEffect(() => () => {
    void client.disconnect();
  }, [client]);

  const value: VoiceContextValue = {
    botOutput,
    error,
    finalTranscript,
    interimTranscript,
    start,
    stop,
    transportState,
  };

  return (
    <PipecatClientProvider client={client}>
      <VoiceContext.Provider value={value}>
        {children}
        <PipecatClientAudio />
      </VoiceContext.Provider>
    </PipecatClientProvider>
  );
}
