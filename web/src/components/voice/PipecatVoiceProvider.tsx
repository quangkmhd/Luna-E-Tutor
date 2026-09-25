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
export type GoogleCaptionSegment = {
  sourceId: number;
  sourceText: string;
  segmentIndex: number;
  segmentText: string;
  audioMs: number;
  finished: boolean;
  receivedAt: string;
};
type SessionTeacherImageCue = TeacherImageCue & { sessionId: string | undefined };

type VoiceContextValue = {
  error: string | null;
  voiceRuns: VoiceRun[];
  phase: VoicePhase;
  micMode: 'off' | 'listening' | 'speaking';
  teacherImageCue: TeacherImageCue | null;
  googleCaptionSegments: GoogleCaptionSegment[];
  googleCaptionPlaybackBaseMs: number;
  googleCaptionStartedAt: number | null;
  ttsProvider: 'google' | 'soniox' | null;
  sentText: Array<{ id: string; text: string; timestamp: string }>;
  ttfaSeconds: number | null;
  elapsedSeconds: number;
  sendText: (text: string) => Promise<void>;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  toggleMic: () => void;
  submitVoice: () => Promise<void>;
  retryVoice: () => void;
  retryableTurn: boolean;
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
  const [retryableTurn, setRetryableTurn] = useState(false);
  const [teacherImageCue, setTeacherImageCue] = useState<SessionTeacherImageCue | null>(null);
  const [googleCaptionSegments, setGoogleCaptionSegments] = useState<GoogleCaptionSegment[]>([]);
  const googleCaptionSegmentsRef = useRef<GoogleCaptionSegment[]>([]);
  const [googleCaptionPlaybackBaseMs, setGoogleCaptionPlaybackBaseMs] = useState(0);
  const [googleCaptionStartedAt, setGoogleCaptionStartedAt] = useState<number | null>(null);
  const [ttsProvider, setTtsProvider] = useState<'google' | 'soniox' | null>(null);
  const googleCaptionStartedAtRef = useRef<number | null>(null);
  const googleCaptionPlaybackBaseRef = useRef(0);
  const googleCaptionAudioMsRef = useRef(0);
  const googleCaptionIgnoreThroughSourceIdRef = useRef(0);
  const botInterruptedRef = useRef(false);
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
  const manualSubmittedAt = useRef<number | null>(null);
  const [refreshTimer, setRefreshTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [thinkingTimeout] = useState(createThinkingTimeout);
  const [conversationStore] = useState(createStore);
  function finishGoogleCaptionPlayback(interrupted: boolean) {
    let playedMs = googleCaptionAudioMsRef.current;
    if (interrupted && googleCaptionStartedAtRef.current !== null) {
      playedMs = Math.min(playedMs, googleCaptionPlaybackBaseRef.current
        + Math.max(0, Date.now() - googleCaptionStartedAtRef.current));
      let offset = 0;
      const truncated = googleCaptionSegmentsRef.current.map((segment) => {
        const availableMs = Math.max(0, Math.min(segment.audioMs, playedMs - offset));
        offset += segment.audioMs;
        return { ...segment, audioMs: availableMs,
          finished: segment.finished && availableMs === segment.audioMs };
      });
      googleCaptionIgnoreThroughSourceIdRef.current = Math.max(
        googleCaptionIgnoreThroughSourceIdRef.current,
        ...truncated.map((segment) => segment.sourceId),
      );
      googleCaptionSegmentsRef.current = truncated;
      googleCaptionAudioMsRef.current = playedMs;
      setGoogleCaptionSegments(truncated);
    }
    googleCaptionPlaybackBaseRef.current = playedMs;
    setGoogleCaptionPlaybackBaseMs(playedMs);
    googleCaptionStartedAtRef.current = null;
    setGoogleCaptionStartedAt(null);
  }
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
          if (turnReadyRef.current) {
            setRetryableTurn(false);
            setPhase('ready');
          }
          return;
        }
        if (data.event === 'luna-turn-error') {
          const payload = data.payload as { message?: unknown; retryable_turn?: unknown } | undefined;
          thinkingTimeout.clear();
          setRetryableTurn(payload?.retryable_turn === true);
          if (payload?.retryable_turn === true) setPhase('ready');
          setErrorState({ message: typeof payload?.message === 'string' ? payload.message : 'Con thử lại nhé.', fatal: false });
          return;
        }
        if (data.event === 'tts-provider' && data.payload && typeof data.payload === 'object') {
          const provider = (data.payload as { provider?: unknown }).provider;
          if (provider === 'google' || provider === 'soniox') setTtsProvider(provider);
          return;
        }
        if (data.event === 'google-tts-caption' && data.payload && typeof data.payload === 'object') {
          const payload = data.payload as Record<string, unknown>;
          if (typeof payload.source_id !== 'number' || typeof payload.source_text !== 'string'
            || typeof payload.segment_index !== 'number' || typeof payload.segment_text !== 'string'
            || typeof payload.audio_ms !== 'number') return;
          if (payload.source_id <= googleCaptionIgnoreThroughSourceIdRef.current) return;
          {
            const previous = googleCaptionSegmentsRef.current;
            const key = (segment: GoogleCaptionSegment) => segment.sourceId === payload.source_id
              && segment.segmentIndex === payload.segment_index;
            const next: GoogleCaptionSegment = {
              sourceId: payload.source_id as number,
              sourceText: payload.source_text as string,
              segmentIndex: payload.segment_index as number,
              segmentText: payload.segment_text as string,
              audioMs: payload.audio_ms as number,
              finished: payload.kind === 'end',
              receivedAt: new Date().toISOString(),
            };
            const index = previous.findIndex(key);
            const updated = index < 0 ? [...previous, next] : previous.map((segment, position) => position === index
              ? { ...next, receivedAt: segment.receivedAt, finished: segment.finished || next.finished }
              : segment);
            googleCaptionSegmentsRef.current = updated;
            googleCaptionAudioMsRef.current = updated.reduce((total, segment) => total + segment.audioMs, 0);
            setGoogleCaptionSegments(updated);
          }
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
          if (botSpeakingRef.current) finishGoogleCaptionPlayback(true);
          manualSubmittedAt.current = null;
          turnReadyRef.current = false;
          setTurnReady(false);
          setRetryableTurn(false);
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
        if (botSpeakingRef.current) botInterruptedRef.current = true;
        manualSubmittedAt.current = null;
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
        botInterruptedRef.current = false;
        const speakingStartedAt = Date.now();
        if (googleCaptionStartedAtRef.current === null) {
          googleCaptionStartedAtRef.current = speakingStartedAt;
          setGoogleCaptionStartedAt(googleCaptionStartedAtRef.current);
        }
        turnReadyRef.current = false;
        setTurnReady(false);
        botSpeakingRef.current = true;
        micArmedRef.current = false;
        voiceClient.enableMic(false);
        setMicMode('off');
        thinkingTimeout.clear();
        setErrorState((previous) => previous.fatal ? previous : { message: null, fatal: false });
        const submittedAt = manualSubmittedAt.current;
        manualSubmittedAt.current = null;
        setUserStoppedAt((stoppedAt) => {
          const turnEndedAt = submittedAt ?? stoppedAt;
          if (turnEndedAt !== null) setTtfaSeconds((speakingStartedAt - turnEndedAt) / 1_000);
          return null;
        });
        setPhase('speaking');
      },
      onBotStoppedSpeaking: () => {
        finishGoogleCaptionPlayback(botInterruptedRef.current);
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
        setRetryableTurn(false);
        micArmedRef.current = false;
        botSpeakingRef.current = false;
        setMicMode('off');
        setErrorState({ message: deviceErrorMessage(reason), fatal: false });
      },
      onError: (message: RTVIMessage) => {
        thinkingTimeout.clear();
        setRetryableTurn(false);
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
        setRetryableTurn(false);
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
    manualSubmittedAt.current = null;
    resumeElapsedClock();
    setTtsProvider(null);
    setGoogleCaptionSegments([]);
    googleCaptionSegmentsRef.current = [];
    googleCaptionAudioMsRef.current = 0;
    googleCaptionIgnoreThroughSourceIdRef.current = 0;
    botInterruptedRef.current = false;
    googleCaptionPlaybackBaseRef.current = 0;
    setGoogleCaptionPlaybackBaseMs(0);
    googleCaptionStartedAtRef.current = null;
    setGoogleCaptionStartedAt(null);
    setVoiceRuns((previous) => [...previous, {
      start: savedHasTurn ? savedMessageCount : 0,
      connected: false,
    }]);
    setErrorState({ message: null, fatal: false });
    setRetryableTurn(false);
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
    manualSubmittedAt.current = Date.now();
    micArmedRef.current = false;
    turnReadyRef.current = false;
    setTurnReady(false);
    client.enableMic(false);
    setMicMode('off');
    setPhase('thinking');
    try {
      client.sendClientMessage('luna.submit-turn', {
        turn_id: globalThis.crypto?.randomUUID?.() ?? `voice-${Date.now()}`,
      });
    } catch {
      manualSubmittedAt.current = null;
      turnReadyRef.current = true;
      setTurnReady(true);
      setErrorState({ message: 'Chưa gửi được lời nói. Con thử lại nhé.', fatal: false });
    }
  }

  function retryVoice() {
    if (!retryableTurn || (transportState !== 'connected' && transportState !== 'ready')) return;
    setRetryableTurn(false);
    setErrorState({ message: null, fatal: false });
    setPhase('thinking');
    try {
      client.sendClientMessage('luna.retry-turn', {});
    } catch {
      setRetryableTurn(true);
      setPhase('ready');
      setErrorState({ message: 'Chưa gửi lại được lượt vừa nói. Con bấm thử lại nhé.', fatal: false });
    }
  }

  async function stop() {
    thinkingTimeout.clear();
    manualSubmittedAt.current = null;
    setRetryableTurn(false);
    if (botSpeakingRef.current) finishGoogleCaptionPlayback(true);
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
    googleCaptionSegments,
    googleCaptionPlaybackBaseMs,
    googleCaptionStartedAt,
    ttsProvider,
    sentText,
    sendText,
    start,
    stop,
    toggleMic,
    submitVoice,
    retryVoice,
    retryableTurn,
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
