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
export type TeacherImageCue = {
  image_url: string | null;
  turn_id: string | null;
  spoken_text: string | null;
  receivedAt: string;
};
type SessionTeacherImageCue = TeacherImageCue & { sessionId: string | undefined };

type VoiceContextValue = {
  error: string | null;
  voiceRuns: VoiceRun[];
  phase: VoicePhase;
  micMode: 'off' | 'listening' | 'speaking';
  teacherImageCue: TeacherImageCue | null;
  sentText: Array<{ id: string; text: string; timestamp: string }>;
  ttfaSeconds: number | null;
  elapsedSeconds: number;
  sendText: (text: string) => Promise<void>;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  toggleMic: () => void;
  submitVoice: () => Promise<void>;
  turnReady: boolean;
  manualSubmit: boolean;
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

function voiceServiceErrorMessage(message: RTVIMessage, manualSubmit: boolean): string {
  const data = message.data as ErrorData;
  if (data.fatal) {
    console.error('Pipecat reported a fatal voice error:', data.error);
    return 'The voice session ended. Reconnect when you are ready.';
  }
  console.warn('Pipecat reported a recoverable voice error:', data.error);
  if (manualSubmit) return 'Lượt nói chưa hoàn tất. Con ngắt rồi kết nối giọng nói lại nhé.';
  if (data.error.includes('completed with no audio')) {
    return 'Luna could not produce audio for that reply. Please try speaking again.';
  }
  return 'The voice service could not complete that reply. Please try speaking again.';
}

function createThinkingTimeout() {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return {
    clear() {
      if (timer !== null) clearTimeout(timer);
      timer = null;
    },
    start(onTimeout: () => void) {
      this.clear();
      timer = setTimeout(() => {
        timer = null;
        onTimeout();
      }, 30_000);
    },
  };
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
  const manualSubmit = Boolean(sessionId);
  const [phase, setPhase] = useState<VoicePhase>('off');
  const [micMode, setMicMode] = useState<VoiceContextValue['micMode']>('off');
  const micArmedRef = useRef(false);
  const botSpeakingRef = useRef(false);
  const turnReadyRef = useRef(false);
  const [turnReady, setTurnReady] = useState(false);
  const [teacherImageCue, setTeacherImageCue] = useState<SessionTeacherImageCue | null>(null);
  const sessionIdRef = useRef(sessionId);
  useEffect(() => { sessionIdRef.current = sessionId; }, [sessionId]);
  const [errorState, setErrorState] = useState<{ message: string | null; fatal: boolean }>({ message: null, fatal: false });
  const [voiceRuns, setVoiceRuns] = useState<VoiceRun[]>([]);
  const savedMessageCountRef = useRef(savedMessageCount);
  useEffect(() => { savedMessageCountRef.current = savedMessageCount; }, [savedMessageCount]);
  const [sentText, setSentText] = useState<VoiceContextValue['sentText']>([]);
  const [ttfaSeconds, setTtfaSeconds] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const elapsedBase = useRef(0);
  const elapsedStartedAt = useRef<number | null>(null);
  function resumeElapsedClock() {
    if (elapsedStartedAt.current === null) elapsedStartedAt.current = Date.now();
    setElapsedSeconds(elapsedBase.current);
  }
  function pauseElapsedClock() {
    if (elapsedStartedAt.current === null) return;
    elapsedBase.current += Math.floor((Date.now() - elapsedStartedAt.current) / 1_000);
    elapsedStartedAt.current = null;
    setElapsedSeconds(elapsedBase.current);
  }
  const [, setUserStoppedAt] = useState<number | null>(null);
  const [refreshTimer, setRefreshTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [thinkingTimeout] = useState(createThinkingTimeout);
  const [conversationStore] = useState(createStore);
  // The SDK invokes these callbacks after construction, never during render.
  // eslint-disable-next-line react-hooks/refs
  const [client] = useState(() => {
    const voiceClient = new PipecatClient({
      transport: new SmallWebRTCTransport(),
      enableMic: false,
      enableCam: false,
      disconnectOnBotDisconnect: true,
      callbacks: {
      onServerMessage: (message: unknown) => {
        if (!message || typeof message !== 'object') return;
        const data = message as { event?: unknown; payload?: unknown };
        if (data.event === 'luna-turn-ready') {
          const payload = data.payload as { ready?: unknown } | undefined;
          turnReadyRef.current = payload?.ready === true;
          setTurnReady(turnReadyRef.current);
          if (turnReadyRef.current) setPhase('ready');
          return;
        }
        if (data.event === 'luna-turn-error') {
          const payload = data.payload as { message?: unknown } | undefined;
          setErrorState({ message: typeof payload?.message === 'string' ? payload.message : 'Con thử lại nhé.', fatal: false });
          return;
        }
        if (data.event !== 'teacher-image' || !data.payload || typeof data.payload !== 'object') return;
        const payload = data.payload as { image_url?: unknown; turn_id?: unknown; spoken_text?: unknown };
        setTeacherImageCue({
          image_url: typeof payload.image_url === 'string' ? payload.image_url : null,
          turn_id: typeof payload.turn_id === 'string' ? payload.turn_id : null,
          spoken_text: typeof payload.spoken_text === 'string' ? payload.spoken_text : null,
          receivedAt: new Date().toISOString(),
          sessionId: sessionIdRef.current,
        });
      },
      onTransportStateChanged: (state: TransportState) => {
        setTransportState(state);
        if (['initializing', 'connecting', 'authenticating'].includes(state)) {
          setPhase('connecting');
        } else if (state === 'disconnected') {
          turnReadyRef.current = false;
          setTurnReady(false);
          micArmedRef.current = false;
          botSpeakingRef.current = false;
          setMicMode('off');
          pauseElapsedClock();
          thinkingTimeout.clear();
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
        thinkingTimeout.clear();
        setErrorState({ message: null, fatal: false });
        if (!sessionId) { turnReadyRef.current = true; setTurnReady(true); }
        setPhase('ready');
      },
      onUserStartedSpeaking: () => {
        thinkingTimeout.clear();
        setErrorState((previous) => previous.fatal ? previous : { message: null, fatal: false });
        setUserStoppedAt(null);
        setTtfaSeconds(null);
        setPhase('listening');
        if (micArmedRef.current) setMicMode('speaking');
      },
      onUserStoppedSpeaking: () => {
        thinkingTimeout.clear();
        setUserStoppedAt(Date.now());
        setPhase('thinking');
        thinkingTimeout.start(() => {
          setPhase('ready');
          setErrorState({ message: 'Luna did not get a response. Please try speaking again.', fatal: false });
        });
      },
      onBotLlmStarted: () => setPhase('thinking'),
      onBotStartedSpeaking: () => {
        turnReadyRef.current = false;
        setTurnReady(false);
        botSpeakingRef.current = true;
        micArmedRef.current = false;
        voiceClient.enableMic(false);
        setMicMode('off');
        thinkingTimeout.clear();
        setErrorState((previous) => previous.fatal ? previous : { message: null, fatal: false });
        setUserStoppedAt((stoppedAt) => {
          if (stoppedAt !== null) setTtfaSeconds((Date.now() - stoppedAt) / 1_000);
          return null;
        });
        setPhase('speaking');
      },
      onBotStoppedSpeaking: () => {
        botSpeakingRef.current = false;
        thinkingTimeout.clear();
        if (!sessionId) { turnReadyRef.current = true; setTurnReady(true); }
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
      onDeviceError: (reason: DeviceError) => {
        micArmedRef.current = false;
        botSpeakingRef.current = false;
        setMicMode('off');
        setErrorState({ message: deviceErrorMessage(reason), fatal: false });
      },
      onError: (message: RTVIMessage) => {
        thinkingTimeout.clear();
        setTeacherImageCue(null);
        const data = message.data as ErrorData;
        setErrorState({ message: voiceServiceErrorMessage(message, manualSubmit), fatal: data.fatal });
        if (!data.fatal) {
          if (manualSubmit) { turnReadyRef.current = false; setTurnReady(false); }
          setPhase('ready');
          return;
        }
        micArmedRef.current = false;
        setMicMode('off');
        void voiceClient.disconnect()
          .catch(() => undefined)
          .finally(() => {
            setTransportState('disconnected');
            setPhase('off');
          });
      },
      onMessageError: () => {
        thinkingTimeout.clear();
        setTeacherImageCue(null);
        if (manualSubmit) { turnReadyRef.current = false; setTurnReady(false); }
        setPhase('ready');
        setErrorState({ message: manualSubmit
          ? 'Lượt nói chưa hoàn tất. Con ngắt rồi kết nối giọng nói lại nhé.'
          : 'The voice service could not process that message. Try again.', fatal: false });
      },
      },
    });
    return voiceClient;
  });

  async function start() {
    thinkingTimeout.clear();
    resumeElapsedClock();
    setVoiceRuns((previous) => [...previous, {
      start: savedHasTurn ? savedMessageCount : 0,
      connected: false,
    }]);
    setErrorState({ message: null, fatal: false });
    turnReadyRef.current = false;
    setTurnReady(false);
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
      pauseElapsedClock();
      setVoiceRuns((previous) => previous.at(-1)?.connected ? previous : previous.slice(0, -1));
      setPhase('off');
      setErrorState({ message: reason instanceof Error ? reason.message : 'Could not start the voice lesson.', fatal: false });
    }
  }

  function toggleMic() {
    if ((transportState !== 'connected' && transportState !== 'ready') || botSpeakingRef.current || !turnReadyRef.current || (manualSubmit && micArmedRef.current)) return;
    const next = manualSubmit || !micArmedRef.current;
    try {
      client.enableMic(next);
      micArmedRef.current = next;
      setMicMode(next ? 'listening' : 'off');
      setPhase(next ? 'listening' : 'ready');
      setErrorState({ message: null, fatal: false });
    } catch {
      setErrorState({ message: 'The microphone could not change state. Please try again.', fatal: false });
    }
  }

  async function submitVoice() {
    if (!micArmedRef.current || !turnReadyRef.current) return;
    micArmedRef.current = false;
    turnReadyRef.current = false;
    setTurnReady(false);
    client.enableMic(false);
    setMicMode('off');
    setPhase('thinking');
    try {
      // The WebRTC audio track and control data channel are independent.
      // Allow the final encoded audio packet to leave before Soniox finalize.
      await new Promise((resolve) => setTimeout(resolve, 250));
      client.sendClientMessage('luna.submit-turn', {
        turn_id: globalThis.crypto?.randomUUID?.() ?? `voice-${Date.now()}`,
      });
    } catch {
      turnReadyRef.current = true;
      setTurnReady(true);
      setErrorState({ message: 'Chưa gửi được lời nói. Con thử lại nhé.', fatal: false });
    }
  }

  async function stop() {
    thinkingTimeout.clear();
    micArmedRef.current = false;
    botSpeakingRef.current = false;
    setMicMode('off');
    try {
      await client.disconnect();
    } catch {
      setErrorState({ message: 'The voice session could not close cleanly. You can reconnect.', fatal: false });
    } finally {
      pauseElapsedClock();
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
      setErrorState({ message: 'Could not send your typed message. Please try again.', fatal: false });
      throw reason;
    }
  }

  useEffect(() => {
    if (!enabled) void client.disconnect();
  }, [client, enabled]);

  useEffect(() => {
    const timer = setInterval(() => {
      const startedAt = elapsedStartedAt.current;
      if (startedAt !== null) {
        setElapsedSeconds(elapsedBase.current + Math.floor((Date.now() - startedAt) / 1_000));
      }
    }, 1_000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => () => {
    if (refreshTimer) clearTimeout(refreshTimer);
  }, [refreshTimer]);

  useEffect(() => () => thinkingTimeout.clear(), [thinkingTimeout]);

  useEffect(() => () => {
    void client.disconnect();
  }, [client]);

  const value: VoiceContextValue = {
    error: errorState.message,
    voiceRuns,
    phase,
    micMode,
    teacherImageCue: teacherImageCue?.sessionId === sessionId ? teacherImageCue : null,
    sentText,
    sendText,
    start,
    stop,
    toggleMic,
    submitVoice,
    turnReady,
    manualSubmit,
    ttfaSeconds,
    elapsedSeconds,
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
