'use client';

import { PipecatClient } from '@pipecat-ai/client-js';
import type {
  DeviceError,
  ErrorData,
  RTVIMessage,
  TransportState,
} from '@pipecat-ai/client-js';
import { PipecatClientAudio, PipecatClientProvider } from '@pipecat-ai/client-react';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';
import { createStore } from 'jotai';
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

export type VoiceRun = { start: number; end?: number; endedAt?: string; connected: boolean };

type VoiceContextValue = {
  error: string | null;
  voiceRuns: VoiceRun[];
  phase: VoicePhase;
  sentText: Array<{ id: string; text: string; timestamp: string }>;
  ttfaSeconds: number | null;
  sendText: (text: string) => Promise<void>;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  transportState: TransportState;
};

export type VoicePhase = 'off' | 'connecting' | 'ready' | 'listening' | 'thinking' | 'speaking';

const VoiceContext = createContext<VoiceContextValue | null>(null);

type VoiceRequestValue =
  | boolean
  | null
  | number
  | string
  | VoiceRequestValue[]
  | { [key: string]: VoiceRequestValue };

type PipecatVoiceProviderProps = {
  children: React.ReactNode;
  enabled?: boolean;
  endpoint?: string;
  onSessionChanged?: () => void | Promise<void>;
  requestBody?: Record<string, VoiceRequestValue>;
  savedMessageCount?: number;
  savedHasTurn?: boolean;
  sessionId?: string;
};

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

function voiceServiceErrorMessage(message: RTVIMessage): string {
  const data = message.data as ErrorData;
  if (data.fatal) {
    console.error('Pipecat reported a fatal voice error:', data.error);
    return 'The voice session ended. Reconnect when you are ready.';
  }
  console.warn('Pipecat reported a recoverable voice error:', data.error);
  return 'Voice audio was interrupted. Please try speaking again.';
}

export function useVoiceLesson(): VoiceContextValue {
  const value = useOptionalVoiceLesson();
  if (!value) throw new Error('useVoiceLesson must be used inside PipecatVoiceProvider');
  return value;
}

export function useOptionalVoiceLesson(): VoiceContextValue | null {
  return useContext(VoiceContext);
}

export function PipecatVoiceProvider({
  sessionId,
  children,
  onSessionChanged,
  enabled = true,
  endpoint,
  requestBody,
  savedMessageCount = 0,
  savedHasTurn = false,
}: PipecatVoiceProviderProps) {
  const [transportState, setTransportState] = useState<TransportState>('disconnected');
  const [phase, setPhase] = useState<VoicePhase>('off');
  const [error, setError] = useState<string | null>(null);
  const [voiceRuns, setVoiceRuns] = useState<VoiceRun[]>([]);
  const savedMessageCountRef = useRef(savedMessageCount);
  useEffect(() => { savedMessageCountRef.current = savedMessageCount; }, [savedMessageCount]);
  const [sentText, setSentText] = useState<VoiceContextValue['sentText']>([]);
  const [ttfaSeconds, setTtfaSeconds] = useState<number | null>(null);
  const [, setUserStoppedAt] = useState<number | null>(null);
  const [refreshTimer, setRefreshTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [conversationStore] = useState(createStore);
  const [client] = useState(() => {
    const voiceClient = new PipecatClient({
      transport: new SmallWebRTCTransport(),
      enableMic: true,
      enableCam: false,
      disconnectOnBotDisconnect: true,
      callbacks: {
      onTransportStateChanged: (state: TransportState) => {
        setTransportState(state);
        if (['initializing', 'connecting', 'authenticating'].includes(state)) {
          setPhase('connecting');
        } else if (state === 'disconnected') {
          setPhase('off');
          setVoiceRuns((previous) => {
            const current = previous.at(-1);
            if (!current || current.end !== undefined) return previous;
            if (!current.connected) return previous.slice(0, -1);
            return [...previous.slice(0, -1), {
              ...current, end: savedMessageCountRef.current, endedAt: new Date().toISOString(),
            }];
          });
        } else if (state === 'ready' || state === 'connected') {
          setVoiceRuns((previous) => {
            const current = previous.at(-1);
            return current && current.end === undefined && !current.connected
              ? [...previous.slice(0, -1), { ...current, connected: true }]
              : previous;
          });
        }
      },
      onBotReady: () => {
        setError(null);
        setPhase('ready');
      },
      onUserStartedSpeaking: () => {
        setUserStoppedAt(null);
        setTtfaSeconds(null);
        setPhase('listening');
      },
      onUserStoppedSpeaking: () => {
        setUserStoppedAt(Date.now());
        setPhase('thinking');
      },
      onBotLlmStarted: () => setPhase('thinking'),
      onBotStartedSpeaking: () => {
        setUserStoppedAt((stoppedAt) => {
          if (stoppedAt !== null) setTtfaSeconds((Date.now() - stoppedAt) / 1_000);
          return null;
        });
        setPhase('speaking');
      },
      onBotStoppedSpeaking: () => {
        setPhase('ready');
        if (!onSessionChanged) return;
        setRefreshTimer((previous) => {
          if (previous) clearTimeout(previous);
          return setTimeout(() => {
            setRefreshTimer(null);
            void onSessionChanged();
          }, 150);
        });
      },
      onDeviceError: (reason: DeviceError) => setError(deviceErrorMessage(reason)),
      onError: (message: RTVIMessage) => {
        const data = message.data as ErrorData;
        setError(voiceServiceErrorMessage(message));
        if (!data.fatal) return;
        void voiceClient.disconnect()
          .catch(() => undefined)
          .finally(() => {
            setTransportState('disconnected');
            setPhase('off');
          });
      },
      onMessageError: () => setError('The voice service could not process that message. Try again.'),
      },
    });
    return voiceClient;
  });

  async function start() {
    setVoiceRuns((previous) => [...previous, {
      start: savedHasTurn ? savedMessageCount : 0,
      connected: false,
    }]);
    setError(null);
    setPhase('connecting');
    try {
      const resolvedEndpoint = endpoint
        ?? process.env.NEXT_PUBLIC_PIPECAT_URL
        ?? 'http://localhost:7860';
      const body = requestBody ?? (sessionId ? { session_id: sessionId } : null);
      if (!body) throw new Error('Voice connection metadata is missing.');
      await client.startBotAndConnect({
        endpoint: `${resolvedEndpoint}/start`,
        requestData: {
          transport: 'webrtc',
          body,
        },
      });
    } catch (reason) {
      setVoiceRuns((previous) => previous.at(-1)?.connected ? previous : previous.slice(0, -1));
      setPhase('off');
      setError(reason instanceof Error ? reason.message : 'Could not start the voice lesson.');
    }
  }

  async function stop() {
    try {
      await client.disconnect();
    } catch {
      setError('The voice session could not close cleanly. You can reconnect.');
    } finally {
      setVoiceRuns((previous) => {
        const current = previous.at(-1);
        return current && current.end === undefined
          ? [...previous.slice(0, -1), {
            ...current, end: savedMessageCount, endedAt: new Date().toISOString(),
          }]
          : previous;
      });
      setTransportState('disconnected');
      setPhase('off');
    }
  }

  async function sendText(text: string) {
    if (transportState !== 'connected' && transportState !== 'ready') {
      throw new Error('Voice is not connected yet. Please try again in a moment.');
    }
    const id = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
    setSentText((previous) => [...previous, { id, text, timestamp: new Date().toISOString() }]);
    try {
      await client.sendText(text, { run_immediately: true, audio_response: true });
    } catch (reason) {
      setSentText((previous) => previous.filter((message) => message.id !== id));
      setError('Could not send your typed message. Please try again.');
      throw reason;
    }
  }

  useEffect(() => {
    if (!enabled) void client.disconnect();
  }, [client, enabled]);

  useEffect(() => () => {
    if (refreshTimer) clearTimeout(refreshTimer);
  }, [refreshTimer]);

  useEffect(() => () => {
    void client.disconnect();
  }, [client]);

  const value: VoiceContextValue = {
    error,
    voiceRuns,
    phase,
    sentText,
    sendText,
    start,
    stop,
    ttfaSeconds,
    transportState,
  };

  return (
    <PipecatClientProvider client={client} jotaiStore={conversationStore}>
      <VoiceContext.Provider value={value}>
        {children}
        <PipecatClientAudio />
      </VoiceContext.Provider>
    </PipecatClientProvider>
  );
}
