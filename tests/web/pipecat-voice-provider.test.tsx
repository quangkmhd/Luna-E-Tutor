import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const startBotAndConnect = vi.fn().mockResolvedValue(undefined);
  const disconnect = vi.fn().mockResolvedValue(undefined);
  const sendText = vi.fn().mockResolvedValue(undefined);
  const enableMic = vi.fn();
  const client = { startBotAndConnect, disconnect, sendText, enableMic, sendClientMessage: vi.fn(), state: 'disconnected' };
  return {
    startBotAndConnect,
    disconnect,
    sendText,
    enableMic,
    client,
    conversationMessages: [] as Array<Record<string, unknown>>,
    options: undefined as Record<string, unknown> | undefined,
    stores: [] as unknown[],
  };
});

vi.mock('@pipecat-ai/client-js', () => ({
  PipecatClient: vi.fn(function (options: Record<string, unknown>) {
    sdk.options = options;
    return sdk.client;
  }),
}));
vi.mock('@pipecat-ai/small-webrtc-transport', () => ({
  SmallWebRTCTransport: vi.fn(function () { return { kind: 'small-webrtc' }; }),
}));
vi.mock('@pipecat-ai/client-react', () => ({
  PipecatClientProvider: ({ children, jotaiStore }: { children: React.ReactNode; jotaiStore?: unknown }) => {
    sdk.stores.push(jotaiStore);
    return children;
  },
  PipecatClientAudio: () => <div data-testid="pipecat-audio" />,
  PipecatClientMicToggle: ({ children }: { children: (value: object) => React.ReactNode }) => children({
    isMicEnabled: true, disabled: false, onClick: sdk.enableMic,
  }),
  usePipecatConversation: () => ({ messages: sdk.conversationMessages }),
}));

import { PipecatVoiceProvider } from '@/components/voice/PipecatVoiceProvider';
import { useVoiceLesson } from '@/components/voice/PipecatVoiceProvider';
import { VoiceControls } from '@/components/voice/VoiceControls';
import { VoiceLatency } from '@/components/voice/VoiceLatency';
import { ChatPanel } from '@/components/ChatPanel';

describe('PipecatVoiceProvider', () => {
  beforeEach(() => {
    sdk.startBotAndConnect.mockClear();
    sdk.disconnect.mockClear();
    sdk.sendText.mockClear();
    sdk.client.sendClientMessage.mockClear();
    sdk.enableMic.mockClear();
    sdk.conversationMessages = [];
    sdk.options = undefined;
    sdk.stores = [];
  });

  afterEach(() => vi.useRealTimers());

  it('reveals a saved Google greeting as audio chunks play', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: '<en>Hello my dear student.</en>' }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as {
      onServerMessage(message: object): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
    };
    const event = (kind: string, audioMs: number) => ({ event: 'google-tts-caption', payload: {
      kind, source_id: 1, source_text: '<en>Hello my dear student.</en>',
      segment_index: 0, segment_text: 'Hello my dear student.', audio_ms: audioMs,
    } });
    expect(screen.queryByText('Hello my dear student.')).not.toBeInTheDocument();
    act(() => callbacks.onServerMessage(event('start', 0)));
    expect(screen.queryByText('Hello my dear student.')).not.toBeInTheDocument();
    act(() => callbacks.onServerMessage(event('chunk', 500)));
    vi.useFakeTimers();
    act(() => callbacks.onBotStartedSpeaking());
    act(() => vi.advanceTimersByTime(420));
    expect(screen.getByText('Hello')).toBeVisible();
    expect(screen.queryByText('Hello my dear student.')).not.toBeInTheDocument();
    act(() => callbacks.onServerMessage(event('end', 500)));
    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByText('Hello my dear student.')).toBeVisible();
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);
  });

  it('keeps the final word when authored punctuation is not spoken by Google TTS', async () => {
    const user = userEvent.setup();
    const sourceText = '<vi>Hôm nay cô trò mình học cách chào hỏi bằng tiếng Anh — gặp ai con cũng biết chào và giới thiệu tên mình.</vi>\n'
      + '<vi>Con đã biết câu chào tiếng Anh nào chưa?</vi>';
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: sourceText }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as {
      onServerMessage(message: object): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
    };
    const event = (kind: string, audioMs: number) => ({ event: 'google-tts-caption', payload: {
      kind, source_id: 1, source_text: sourceText, segment_index: 0,
      segment_text: 'Hôm nay cô trò mình học cách chào hỏi bằng tiếng Anh gặp ai con cũng biết chào và giới thiệu tên mình Con đã biết câu chào tiếng Anh nào chưa',
      audio_ms: audioMs,
    } });
    act(() => callbacks.onServerMessage(event('start', 0)));
    act(() => callbacks.onServerMessage(event('end', 9000)));
    act(() => callbacks.onBotStartedSpeaking());
    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByText('Con đã biết câu chào tiếng Anh nào chưa?')).toBeVisible();
  });

  it('replays a saved Google line in place after reconnecting', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={2} savedHasTurn>
      <ChatPanel messages={[{ role: 'learner', text: 'Hi', turn_id: 'turn-1' },
        { role: 'teacher', text: '<en>Say hello again.</en>' }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as {
      onServerMessage(message: object): void;
      onBotStartedSpeaking(): void;
    };
    const caption = (kind: string, audioMs: number) => callbacks.onServerMessage({
      event: 'google-tts-caption', payload: { kind, source_id: 1,
        source_text: '<en>Say hello again.</en>', segment_index: 0,
        segment_text: 'Say hello again.', audio_ms: audioMs },
    });
    act(() => caption('start', 0));
    expect(screen.queryByText('Say hello again.')).not.toBeInTheDocument();
    act(() => caption('chunk', 1000));
    vi.useFakeTimers();
    act(() => callbacks.onBotStartedSpeaking());
    act(() => vi.advanceTimersByTime(450));
    expect(screen.getByText('Say')).toBeVisible();
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);
  });

  it('does not reveal buffered Google audio after an interruption', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: '<en>One two three four five six.</en>' }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as {
      onServerMessage(message: object): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
      onUserStartedSpeaking(): void;
    };
    act(() => callbacks.onServerMessage({ event: 'google-tts-caption', payload: {
      kind: 'end', source_id: 1, source_text: '<en>One two three four five six.</en>',
      segment_index: 0, segment_text: 'One two three four five six.', audio_ms: 3000,
    } }));
    vi.useFakeTimers();
    act(() => callbacks.onBotStartedSpeaking());
    act(() => vi.advanceTimersByTime(450));
    act(() => callbacks.onUserStartedSpeaking());
    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByText('One')).toBeVisible();
    expect(screen.queryByText('One two three four five six.')).not.toBeInTheDocument();
  });

  it('shows double asterisk emphasis as bold without displaying the markers', () => {
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[{
      role: 'teacher', text: '<en>Say **Hello** now.</en>',
    }]} /></PipecatVoiceProvider>);
    expect(screen.getByText('Hello', { selector: 'strong' })).toBeVisible();
    expect(document.querySelector('.bubble-row.teacher p')).toHaveTextContent('Say Hello now.');
    expect(document.querySelector('.bubble-row.teacher p')).not.toHaveTextContent('**');
  });

  it('leaves Thinking with a retry message when a stopped voice turn produces no response', () => {
    vi.useFakeTimers();
    function Phase() {
      const voice = useVoiceLesson();
      return <><span>{voice.phase}</span><span>{voice.error}</span></>;
    }
    render(<PipecatVoiceProvider sessionId="session-7"><Phase /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onUserStoppedSpeaking(): void;
      onBotStartedSpeaking(): void;
      onError(message: { data: { error: string; fatal: boolean } }): void;
    };

    act(() => callbacks.onUserStoppedSpeaking());
    expect(screen.getByText('thinking')).toBeVisible();
    act(() => callbacks.onBotStartedSpeaking());
    act(() => vi.advanceTimersByTime(30_000));
    expect(screen.getByText('speaking')).toBeVisible();
    expect(screen.queryByText(/did not get a response/i)).not.toBeInTheDocument();

    act(() => callbacks.onUserStoppedSpeaking());
    act(() => vi.advanceTimersByTime(30_000));
    expect(screen.getByText('ready')).toBeVisible();
    expect(screen.getByText(/did not get a response/i)).toBeVisible();

    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.getByText('speaking')).toBeVisible();
    expect(screen.queryByText(/did not get a response/i)).not.toBeInTheDocument();

    act(() => callbacks.onUserStoppedSpeaking());
    act(() => callbacks.onError({ data: { error: 'Soniox TTS error 408', fatal: false } }));
    expect(screen.getByText('ready')).toBeVisible();
  });

  it('connects SmallWebRTC with the active REST session and disconnects on cleanup', async () => {
    const user = userEvent.setup();
    const view = render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(sdk.options).toMatchObject({
      enableMic: false,
      enableCam: false,
      disconnectOnBotDisconnect: true,
    });
    expect(sdk.startBotAndConnect).toHaveBeenCalledWith({
      endpoint: 'http://localhost:7860/start',
      requestData: {
        transport: 'webrtc',
        body: { session_id: 'session-7' },
      },
    });
    view.unmount();
    await waitFor(() => expect(sdk.disconnect).toHaveBeenCalledOnce());
  });

  it('sends typed text through the active voice pipeline and displays it beside voice messages', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{ role: 'assistant', final: true, createdAt: new Date(Date.now() - 1000).toISOString(), parts: [{ text: { spoken: 'Hello!', unspoken: '' }, final: true, createdAt: '1' }] }];
    function TypedInput() {
      const voice = useVoiceLesson();
      return <button onClick={() => void voice.sendText('I like dolphins')}>Type answer</button>;
    }
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><TypedInput /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Type answer' }));

    expect(sdk.sendText).toHaveBeenCalledWith('I like dolphins', { run_immediately: true, audio_response: true });
    expect(screen.getByText('I like dolphins')).toBeVisible();
    expect(screen.getByText('Hello!')).toBeVisible();
  });

  it('connects Talk with topic metadata and Talk-specific labels', async () => {
    const user = userEvent.setup();
    render(
      <PipecatVoiceProvider
        endpoint="http://localhost:7863"
        requestBody={{ topic: 'Animals' }}
      >
        <VoiceControls startLabel="Start conversation" stopLabel="Stop conversation" />
      </PipecatVoiceProvider>,
    );

    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));

    expect(sdk.startBotAndConnect).toHaveBeenCalledWith({
      endpoint: 'http://localhost:7863/start',
      requestData: {
        transport: 'webrtc',
        body: { topic: 'Animals' },
      },
    });
  });

  it('can stop twice and unmount without starting a second client', async () => {
    const user = userEvent.setup();
    const view = render(
      <PipecatVoiceProvider endpoint="http://localhost:7863" requestBody={{ topic: 'Animals' }}>
        <VoiceControls startLabel="Start conversation" stopLabel="Stop conversation" />
      </PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
    };

    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Stop conversation' }));
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Stop conversation' }));
    view.unmount();

    expect(sdk.startBotAndConnect).toHaveBeenCalledOnce();
    expect(sdk.disconnect).toHaveBeenCalledTimes(3);
  });

  it('disconnects the old client when the active session changes', async () => {
    const view = render(
      <PipecatVoiceProvider key="old" sessionId="old"><span>lesson</span></PipecatVoiceProvider>,
    );
    view.rerender(
      <PipecatVoiceProvider key="new" sessionId="new"><span>lesson</span></PipecatVoiceProvider>,
    );
    await waitFor(() => expect(sdk.disconnect).toHaveBeenCalledOnce());
  });

  it('isolates conversation state in a fresh store for each provider session', () => {
    const view = render(
      <PipecatVoiceProvider key="animals" requestBody={{ topic: 'Animals' }}>
        <span>talk</span>
      </PipecatVoiceProvider>,
    );
    const animalsStore = sdk.stores.at(-1);

    view.rerender(
      <PipecatVoiceProvider key="school" requestBody={{ topic: 'School life' }}>
        <span>talk</span>
      </PipecatVoiceProvider>,
    );
    const schoolStore = sdk.stores.at(-1);

    expect(animalsStore).toBeDefined();
    expect(schoolStore).toBeDefined();
    expect(schoolStore).not.toBe(animalsStore);
  });

  it('disconnects when the lesson is no longer active', async () => {
    const view = render(
      <PipecatVoiceProvider sessionId="session-7" enabled><span>lesson</span></PipecatVoiceProvider>,
    );
    view.rerender(
      <PipecatVoiceProvider sessionId="session-7" enabled={false}><span>lesson</span></PipecatVoiceProvider>,
    );
    await waitFor(() => expect(sdk.disconnect).toHaveBeenCalledOnce());
  });

  it('locks manual Mic until reconnect when Pipecat reports a service error', () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onError(message: { data: { error: string; fatal: boolean } }): void;
    };

    act(() => callbacks.onTransportStateChanged('ready'));
    act(() => callbacks.onError({
      data: {
        error: 'TTS context completed with no audio',
        fatal: false,
      },
    }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Lượt nói chưa hoàn tất. Con ngắt rồi kết nối giọng nói lại nhé.',
    );
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeDisabled();
  });

  it('resends the saved manual turn after the lesson API rejects it before commit', () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onServerMessage(message: unknown): void;
      onUserStoppedSpeaking(): void;
    };

    act(() => callbacks.onTransportStateChanged('ready'));
    vi.useFakeTimers();
    act(() => callbacks.onUserStoppedSpeaking());
    act(() => callbacks.onServerMessage({ event: 'luna-turn-error', payload: {
      message: 'Luna chưa đánh giá được câu trả lời. Con bấm gửi lại lượt vừa nói nhé.',
      retryable_turn: true,
    } }));
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: false } }));

    expect(screen.getByRole('alert')).toHaveTextContent('Luna chưa đánh giá được câu trả lời.');
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeDisabled();
    act(() => vi.advanceTimersByTime(30_000));
    expect(screen.getByRole('alert')).toHaveTextContent('Luna chưa đánh giá được câu trả lời.');
    act(() => screen.getByRole('button', { name: 'Gửi lại lượt vừa nói' }).click());
    expect(sdk.client.sendClientMessage).toHaveBeenCalledWith('luna.retry-turn', {});
  });

  it('clears an old recoverable TTS warning when the bot speaks again, but retains a new failure', () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onError(message: { data: { error: string; fatal: boolean } }): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
      onServerMessage(message: unknown): void;
    };

    act(() => callbacks.onError({ data: { error: 'Soniox TTS error 408 request_timeout', fatal: false } }));
    expect(screen.getByRole('alert')).toHaveTextContent('Lượt nói chưa hoàn tất.');

    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    act(() => callbacks.onError({ data: { error: 'Soniox TTS error 408 request_timeout', fatal: false } }));
    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByRole('alert')).toHaveTextContent('Lượt nói chưa hoàn tất.');
  });

  it('disconnects and becomes startable again when Pipecat reports a fatal service error', async () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onError(message: { data: { error: string; fatal: boolean } }): void;
      onBotStartedSpeaking(): void;
      onTransportStateChanged(state: string): void;
    };

    act(() => callbacks.onTransportStateChanged('ready'));
    expect(screen.getByRole('button', { name: 'Stop voice lesson' })).toBeInTheDocument();
    act(() => callbacks.onError({
      data: {
        error: 'The voice worker stopped',
        fatal: true,
      },
    }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'The voice session ended. Reconnect when you are ready.',
    );
    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The voice session ended. Reconnect when you are ready.',
    );
    await waitFor(() => expect(sdk.disconnect).toHaveBeenCalledOnce());
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeInTheDocument();
  });

  it('shows the microphone and Luna speaking states in the voice controls', async () => {
    const user = userEvent.setup();
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onBotReady(): void;
      onUserStartedSpeaking(): void;
      onUserStoppedSpeaking(): void;
      onUserTranscript?: (data: { text: string; final: boolean; timestamp: string; user_id: string }) => void;
      onBotLlmStarted(): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
    };

    act(() => { callbacks.onTransportStateChanged('ready'); callbacks.onBotReady(); });
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } }));
    expect(screen.getByText('MIC ĐANG TẮT')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(screen.getByText('Đang nghe')).toBeInTheDocument();

    act(() => callbacks.onUserStartedSpeaking());
    expect(screen.getByText('Đang nói')).toBeInTheDocument();

    act(() => callbacks.onUserStoppedSpeaking());
    act(() => callbacks.onUserTranscript?.({ text: 'Hello', final: true, timestamp: '1', user_id: 'u1' }));
    expect(screen.getByText('Đang nói')).toBeInTheDocument();

    act(() => callbacks.onBotLlmStarted());

    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.getByText('MIC ĐANG TẮT')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: 'Loa đang phát' })).toBeInTheDocument();

    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByText('MIC ĐANG TẮT')).toBeInTheDocument();
  });

  it('shows perceived TTFA seconds after Luna starts speaking', () => {
    const now = vi.spyOn(Date, 'now')
      .mockReturnValueOnce(1_000)
      .mockReturnValueOnce(3_840);
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceLatency /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onUserStoppedSpeaking(): void;
      onBotStartedSpeaking(): void;
    };

    act(() => callbacks.onUserStoppedSpeaking());
    expect(screen.queryByText('2.84s')).not.toBeInTheDocument();
    act(() => callbacks.onBotStartedSpeaking());

    expect(screen.getByText('2.84s')).toBeInTheDocument();
    now.mockRestore();
  });

  it('shows TTFA on the latest Luna bubble after a manually submitted voice turn', async () => {
    const user = userEvent.setup();
    const now = vi.spyOn(Date, 'now').mockReturnValue(1_000);
    render(<PipecatVoiceProvider sessionId="session-7">
      <ChatPanel messages={[{ role: 'teacher', text: 'Good evening' }]} />
      <VoiceControls lessonMode />
    </PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onServerMessage(message: object): void;
      onBotStartedSpeaking(): void;
    };

    act(() => {
      callbacks.onTransportStateChanged('ready');
      callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } });
    });
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    await user.click(screen.getByRole('button', { name: 'Gửi lượt nói' }));
    expect(sdk.client.sendClientMessage).toHaveBeenCalledWith('luna.submit-turn', expect.any(Object));
    now.mockReturnValue(3_840);
    act(() => callbacks.onBotStartedSpeaking());

    expect(screen.getByText('Good evening').closest('.bubble')?.querySelector('.speaker'))
      .toHaveTextContent('Luna2.84s');
    now.mockRestore();
  });

  it('cancels a pending session refresh on cleanup', () => {
    vi.useFakeTimers();
    const onSessionChanged = vi.fn();
    const view = render(
      <PipecatVoiceProvider sessionId="session-7" onSessionChanged={onSessionChanged}>
        <span>lesson</span>
      </PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as { onBotStoppedSpeaking(): void };
    act(() => callbacks.onBotStoppedSpeaking());
    view.unmount();
    act(() => vi.advanceTimersByTime(200));
    expect(onSessionChanged).not.toHaveBeenCalled();
  });

  it('shows live learner and Luna speech as bubbles in the main conversation', async () => {
    const onSessionChanged = vi.fn();
    sdk.conversationMessages = [
      { role: 'user', final: false, createdAt: '1', parts: [{ text: 'I live in', final: false, createdAt: '1' }] },
      { role: 'assistant', final: false, createdAt: '2', parts: [{ text: { spoken: '', unspoken: 'Great. What city do you live in?' }, final: false, createdAt: '2' }] },
    ];
    render(
      <PipecatVoiceProvider sessionId="session-7" onSessionChanged={onSessionChanged}>
        <ChatPanel messages={[]} />
        <VoiceControls />
      </PipecatVoiceProvider>,
    );
    expect(screen.getByText('I live in').closest('.bubble-row')).toHaveClass('learner');
    expect(onSessionChanged).not.toHaveBeenCalled();
    expect(screen.getByText('Great. What city do you live in?').closest('.bubble-row')).toHaveClass('teacher');
    expect(screen.queryByText('You said')).not.toBeInTheDocument();
  });

  it('keeps earlier sentence segments visible while Luna speaks the next sentence', () => {
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '1', parts: [
        { text: { spoken: 'I can hear you loud and clear too, Quang. ', unspoken: '' }, final: true, createdAt: '1' },
        { text: { spoken: '', unspoken: 'Since we are talking about your class, how many students are in your class?' }, final: false, createdAt: '2' },
      ],
    }];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[]} />
      </PipecatVoiceProvider>,
    );
    expect(screen.getByText(
      'I can hear you loud and clear too, Quang. Since we are talking about your class, how many students are in your class?',
    )).toBeInTheDocument();
  });

  it('hides bracketed delivery cues from live Pipecat Luna messages', () => {
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '1', parts: [
        { text: { spoken: 'My name is Luna. [pause] ', unspoken: 'Can you say “city”? [long pause]' }, final: false, createdAt: '1' },
      ],
    }];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[]} />
      </PipecatVoiceProvider>,
    );

    expect(screen.getByText('My name is Luna. Can you say “city”?')).toBeInTheDocument();
    expect(screen.queryByText(/\[(?:long )?pause\]/i)).not.toBeInTheDocument();
  });

  it('splits multiline live Luna text into separate turns', () => {
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '1', parts: [
        { text: { spoken: 'Listen first! [long pause]\n', unspoken: 'Your turn now!' }, final: false, createdAt: '1' },
      ],
    }];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /></PipecatVoiceProvider>);

    const rows = document.querySelectorAll('.bubble-row.teacher');
    expect(rows).toHaveLength(2);
    expect(Array.from(rows, (row) => row.querySelector('p')?.textContent)).toEqual([
      'Listen first!',
      'Your turn now!',
    ]);
  });

  it('keeps sequential bilingual TTS segments in one bubble without an authored template', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '2026-09-22T00:00:00Z', parts: [
        { text: { spoken: 'Cô trò mình sang Trạm 1 học từ mới.', unspoken: '' }, final: true, createdAt: '1' },
        { text: { spoken: '"HELLO"', unspoken: '' }, final: true, createdAt: '2' },
        { text: { spoken: 'nghĩa là xin chào.', unspoken: '' }, final: true, createdAt: '3' },
        { text: { spoken: 'Listen first! "HELLO"', unspoken: '' }, final: true, createdAt: '4' },
        { text: { spoken: 'Your turn now!', unspoken: ' Can you say "Hello"?' }, final: false, createdAt: '5' },
      ],
    }];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));

    const rows = document.querySelectorAll('.bubble-row.teacher');
    expect(Array.from(rows, (row) => row.querySelector('p')?.textContent)).toEqual([
      'Cô trò mình sang Trạm 1 học từ mới. "HELLO" nghĩa là xin chào. Listen first! "HELLO" Your turn now!',
    ]);
    expect(screen.queryByText(/Can you say/)).not.toBeInTheDocument();
  });

  it('restores YAML line boundaries after all bilingual speech is heard', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{
      role: 'assistant', final: true, createdAt: '2026-09-22T00:00:00Z', parts: [
        { text: { spoken: 'Cô trò mình sang Trạm 1.', unspoken: '' }, final: true, createdAt: '1' },
        { text: { spoken: '"HELLO"', unspoken: '' }, final: true, createdAt: '2' },
        { text: { spoken: 'nghĩa là xin chào.', unspoken: '' }, final: true, createdAt: '3' },
        { text: { spoken: 'Listen first! "HELLO"', unspoken: '' }, final: true, createdAt: '4' },
        { text: { spoken: 'Your turn now!', unspoken: '' }, final: true, createdAt: '5' },
      ],
    }];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[{
      role: 'teacher',
      text: '<vi>Cô trò mình sang Trạm 1.</vi>\n<en>"HELLO"</en><vi> nghĩa là xin chào.</vi>\n<en>Listen first! "HELLO"</en>\n<en>Your turn now!</en>',
    }]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));

    expect(Array.from(document.querySelectorAll('.bubble-row.teacher'), (row) => row.querySelector('p')?.textContent)).toEqual([
      'Cô trò mình sang Trạm 1.',
      '"HELLO" nghĩa là xin chào.',
      'Listen first! "HELLO"',
      'Your turn now!',
    ]);
  });

  it('keeps the image in a separate Luna bubble when its cue arrives after speech starts', async () => {
    const user = userEvent.setup();
    const createdAt = new Date(Date.now() - 1000).toISOString();
    sdk.conversationMessages = [
      { role: 'user', final: true, createdAt, parts: [{ text: 'hi', final: true, createdAt }] },
      { role: 'assistant', final: false, createdAt, parts: [{
        text: { spoken: 'Cô trò mình sang Trạm 1', unspoken: ' học từ mới.' }, final: false, createdAt,
      }] },
    ];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[{
      role: 'teacher', text: 'Xin chào con!',
    }]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-1', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1 học từ mới.</vi>',
      },
    }));

    const image = screen.getByRole('img', { name: 'Hình minh họa cho câu nói của Luna' });
    expect(image.closest('.bubble-row')).not.toHaveTextContent('Cô trò mình sang Trạm 1');
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(3);
    expect(screen.getByText('Cô trò mình sang Trạm 1')).toBeVisible();
    expect(screen.queryByText(/học từ mới/)).not.toBeInTheDocument();
  });

  it('does not duplicate the saved opening image when voice start replays its cue', async () => {
    const user = userEvent.setup();
    const opening = "<en>Hi! My name is Luna. I'm your English tutor!</en>\n<vi>Xin chào con! Cô là Luna, gia sư tiếng Anh của con.</vi>\n<en>We're going to practice English together. Ready?</en>";
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[{
      role: 'teacher', text: opening, image_url: '/images/hello.webp',
    }]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: null, image_url: '/images/hello.webp', spoken_text: opening,
      },
    }));

    expect(screen.getAllByRole('img', { name: 'Hình minh họa cho câu nói của Luna' })).toHaveLength(1);
    expect(Array.from(document.querySelectorAll('.bubble-row.teacher'), (row) =>
      row.querySelector('img') ? 'image' : row.querySelector('p')?.textContent,
    )).toEqual(['image']);
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'tts-provider', payload: { provider: 'soniox' },
    }));
    expect(Array.from(document.querySelectorAll('.bubble-row.teacher'), (row) =>
      row.querySelector('img') ? 'image' : row.querySelector('p')?.textContent,
    )).toEqual([
      'image', "Hi! My name is Luna. I'm your English tutor!",
      'Xin chào con! Cô là Luna, gia sư tiếng Anh của con.',
      "We're going to practice English together. Ready?",
    ]);
  });

  it('does not show the opening image again above a later typed answer', async () => {
    const user = userEvent.setup();
    const opening = "<en>Hi! My name is Luna. I'm your English tutor!</en>\n<vi>Xin chào con! Cô là Luna, gia sư tiếng Anh của con.</vi>\n<en>We're going to practice English together. Ready?</en>";
    const image_url = '/images/hello.webp';
    const view = render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[
      { role: 'teacher', text: opening, image_url },
    ]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: { turn_id: null, image_url, spoken_text: opening },
    }));

    view.rerender(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[
      { role: 'teacher', text: opening, image_url },
      { role: 'learner', text: 'yes', turn_id: 'learner-yes' },
      { role: 'teacher', text: 'Try saying hello to me.' },
    ]} /><VoiceControls /></PipecatVoiceProvider>);

    expect(screen.getAllByRole('img', { name: 'Hình minh họa cho câu nói của Luna' })).toHaveLength(1);
    const rows = Array.from(document.querySelectorAll('.bubble-row'));
    expect(rows.findIndex((row) => row.querySelector('img'))).toBeLessThan(
      rows.findIndex((row) => row.classList.contains('learner')),
    );
  });

  it('restores authored bubbles when Pipecat reuses an assistant message across barge-in', async () => {
    const user = userEvent.setup();
    const assistantCreatedAt = new Date(Date.now() - 2_000).toISOString();
    const learnerCreatedAt = new Date(Date.now() - 1_000).toISOString();
    sdk.conversationMessages = [
      { role: 'assistant', final: false, createdAt: assistantCreatedAt, parts: [
        { text: { spoken: "Hi! My name is Luna. I'm your English tutor!", unspoken: '' }, final: true, createdAt: assistantCreatedAt },
        { text: { spoken: 'Cô trò mình sang Trạm 1 học từ mới.', unspoken: '' }, final: true, createdAt: assistantCreatedAt },
        { text: { spoken: '"HELLO"', unspoken: '' }, final: true, createdAt: assistantCreatedAt },
        { text: { spoken: 'nghĩa là xin chào.', unspoken: '' }, final: true, createdAt: assistantCreatedAt },
        { text: { spoken: 'Listen first! "HELLO"', unspoken: '' }, final: true, createdAt: assistantCreatedAt },
        { text: { spoken: 'Your turn now!', unspoken: '' }, final: true, createdAt: assistantCreatedAt },
      ] },
      { role: 'user', final: true, createdAt: learnerCreatedAt, parts: [
        { text: 'hi', final: true, createdAt: learnerCreatedAt },
      ] },
    ];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[
      { role: 'teacher', text: "Hi! My name is Luna. I'm your English tutor!" },
      { role: 'teacher', text: 'Xin chào con! Cô là Luna, gia sư tiếng Anh của con.' },
    ]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-after-barge-in', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1 học từ mới.</vi>\n<en>"HELLO"</en><vi> nghĩa là xin chào.</vi>\n<en>Listen first! "HELLO"</en>\n<en>Your turn now!</en>',
      },
    }));

    const rows = document.querySelectorAll('.bubble-row.teacher');
    expect(Array.from(rows, (row) => row.querySelector('p')?.textContent).slice(-4)).toEqual([
      'Cô trò mình sang Trạm 1 học từ mới.',
      '"HELLO" nghĩa là xin chào.',
      'Listen first! "HELLO"',
      'Your turn now!',
    ]);
    expect(rows[2].querySelector('img')).toBeInTheDocument();
    expect(Array.from(rows).filter((row) => !row.querySelector('p'))).toHaveLength(1);
    expect(Array.from(document.querySelectorAll('.bubble-row'), (row) => row.classList.contains('learner') ? 'learner' : 'teacher')).toEqual([
      'teacher', 'teacher', 'learner', 'teacher', 'teacher', 'teacher', 'teacher', 'teacher',
    ]);
  });

  it('keeps the first partial words after barge-in below the learner and image', async () => {
    const user = userEvent.setup();
    const assistantCreatedAt = new Date(Date.now() - 2_000).toISOString();
    const learnerCreatedAt = new Date(Date.now() - 1_000).toISOString();
    sdk.conversationMessages = [
      { role: 'assistant', final: false, createdAt: assistantCreatedAt, parts: [{
        text: { spoken: 'Hi! My name is Luna. Cô trò', unspoken: ' mình sang Trạm 1.' },
        final: false, createdAt: assistantCreatedAt,
      }] },
      { role: 'user', final: true, createdAt: learnerCreatedAt, parts: [{ text: 'hi', final: true, createdAt: learnerCreatedAt }] },
    ];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-after-barge-in', image_url: '/images/hello.webp',
        spoken_text: 'Cô trò mình sang Trạm 1.',
      },
    }));

    expect(Array.from(document.querySelectorAll('.bubble-row'), (row) =>
      row.querySelector('img') ? 'image' : row.classList.contains('learner') ? 'learner' : row.querySelector('p')?.textContent,
    )).toEqual(['learner', 'image', 'Cô trò']);
  });

  it('groups bilingual spoken parts by authored YAML lines without revealing future words', async () => {
    const user = userEvent.setup();
    const createdAt = new Date(Date.now() - 1000).toISOString();
    sdk.conversationMessages = [
      { role: 'user', final: true, createdAt, parts: [{ text: 'hi', final: true, createdAt }] },
      { role: 'assistant', final: false, createdAt, parts: [
        { text: { spoken: 'Cô trò mình sang Trạm 1.', unspoken: '' }, final: true, createdAt },
        { text: { spoken: '"HELLO"', unspoken: '' }, final: true, createdAt },
        { text: { spoken: 'nghĩa là xin chào', unspoken: ', con nói khi gặp bạn.' }, final: false, createdAt },
      ] },
    ];
    render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-1', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1.</vi>\n<en>"HELLO"</en><vi> nghĩa là xin chào, con nói khi gặp bạn.</vi>\n<en>Listen first!</en>',
      },
    }));

    const rows = document.querySelectorAll('.bubble-row.teacher');
    expect(rows).toHaveLength(3);
    expect(rows[0].querySelector('img')).toBeInTheDocument();
    expect(rows[0].querySelector('p')).not.toBeInTheDocument();
    expect(rows[1]).toHaveTextContent('Cô trò mình sang Trạm 1.');
    expect(rows[2]).toHaveTextContent('"HELLO" nghĩa là xin chào');
    expect(screen.queryByText(/con nói khi gặp bạn|Listen first/)).not.toBeInTheDocument();
  });

  it('keeps the image in its own Luna bubble while spoken text grows', async () => {
    const user = userEvent.setup();
    const createdAt = new Date(Date.now() - 1000).toISOString();
    sdk.conversationMessages = [{
      role: 'user', final: true, createdAt, parts: [{ text: 'hi', final: true, createdAt }],
    }];
    const view = render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-1', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1 học từ mới.</vi>',
      },
    }));
    const image = screen.getByRole('img', { name: 'Hình minh họa cho câu nói của Luna' });
    const imageRow = image.closest('.bubble-row');
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);
    expect(imageRow).not.toHaveTextContent('Cô trò mình');

    sdk.conversationMessages = [
      sdk.conversationMessages[0],
      { role: 'assistant', final: false, createdAt: new Date().toISOString(), parts: [{
        text: { spoken: 'Cô trò mình sang Trạm 1', unspoken: ' học từ mới.' }, final: false, createdAt,
      }] },
    ];
    view.rerender(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(2);
    expect(image.closest('.bubble-row')).toBe(imageRow);
    expect(imageRow?.nextElementSibling).toHaveTextContent('Cô trò mình sang Trạm 1');
    expect(screen.queryByText(/học từ mới/)).not.toBeInTheDocument();
  });

  it('clears a teacher image cue when the lesson session changes', () => {
    const view = render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /></PipecatVoiceProvider>);
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-session-7', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1 học từ mới.</vi>',
      },
    }));
    expect(screen.getByRole('img', { name: 'Hình minh họa cho câu nói của Luna' })).toBeInTheDocument();

    view.rerender(<PipecatVoiceProvider sessionId="session-8"><ChatPanel messages={[]} /></PipecatVoiceProvider>);

    expect(screen.queryByRole('img', { name: 'Hình minh họa cho câu nói của Luna' })).not.toBeInTheDocument();
  });

  it('reveals only Luna words confirmed spoken during an active voice lesson', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '2026-09-22T00:00:00Z', parts: [
        { text: { spoken: 'Listen first!\nHEL', unspoken: 'LO means hello.\nYour turn now!' }, final: false, createdAt: '1' },
      ],
    }];
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={0}>
      <ChatPanel messages={[]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));

    expect(screen.getByText('Listen first!')).toBeVisible();
    expect(screen.getByText('HEL')).toBeVisible();
    expect(screen.queryByText('Hello, Quang!')).not.toBeInTheDocument();
    expect(screen.queryByText(/LO means hello|Your turn now/)).not.toBeInTheDocument();
  });

  it('hides language markup without revealing unheard voice words', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '2026-09-22T00:00:00Z', parts: [{
        text: { spoken: '<vi>Xin chào.</vi> <en>HE', unspoken: 'LLO</en> [long pause]' },
        final: false, createdAt: '1',
      }],
    }];
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={0}>
      <ChatPanel messages={[]} /><VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));

    expect(screen.getByText('Xin chào. HE')).toBeVisible();
    expect(screen.queryByText(/LLO|<\/?(?:vi|en)>|\[long pause\]/)).not.toBeInTheDocument();
  });

  it('adds Luna lines only as TTS spoken progress advances', async () => {
    const user = userEvent.setup();
    const spoken = (value: string) => [{
      role: 'assistant', final: false, createdAt: '2026-09-22T00:00:00Z', parts: [{
        text: { spoken: value, unspoken: 'HELLO means hello.\nYour turn now!' }, final: false, createdAt: '1',
      }],
    }];
    sdk.conversationMessages = spoken('');
    const view = render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={0}>
      <ChatPanel messages={[]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(0);

    sdk.conversationMessages = spoken('Listen first!');
    view.rerender(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={0}>
      <ChatPanel messages={[]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    expect(screen.getByText('Listen first!')).toBeVisible();
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);

    sdk.conversationMessages = spoken('Listen first!\nHELLO');
    view.rerender(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={0}>
      <ChatPanel messages={[]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    expect(screen.getByText('HELLO')).toBeVisible();
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(2);
    expect(screen.queryByText('Your turn now!')).not.toBeInTheDocument();
  });

  it('keeps only the spoken prefix after interruption and allows later text-only turns', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '2026-09-22T00:00:00Z', parts: [
        { text: { spoken: 'HEL', unspoken: 'LO means hello.' }, final: false, createdAt: '1' },
      ],
    }];
    const view = render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={0}>
      <ChatPanel messages={[]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Stop voice lesson' }));

    expect(screen.getByText('HEL')).toBeVisible();
    expect(screen.queryByText('HELLO means hello.')).not.toBeInTheDocument();
    view.rerender(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={2}>
      <ChatPanel messages={[
        { role: 'learner', text: 'Hi' },
        { role: 'teacher', text: 'Nice to see you!' },
      ]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    expect(screen.getByText('Nice to see you!')).toBeVisible();
    expect(screen.queryByText('HELLO means hello.')).not.toBeInTheDocument();
  });

  it('keeps all final learner transcript chunks in the current Pipecat turn', () => {
    sdk.conversationMessages = [{
      role: 'user', final: false, createdAt: '1', parts: [
        { text: 'I live in', final: true, createdAt: '1' },
        { text: 'Hanoi.', final: true, createdAt: '2' },
      ],
    }];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[]} />
      </PipecatVoiceProvider>,
    );
    expect(screen.getByText('I live in Hanoi.')).toBeInTheDocument();
  });

  it('keeps Luna live speech until the saved turn replaces it', () => {
    sdk.conversationMessages = [{ role: 'assistant', final: false, createdAt: '1', parts: [{ text: { spoken: 'Can you use class in a sentence?', unspoken: '' }, final: true, createdAt: '1' }] }];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[]} />
      </PipecatVoiceProvider>,
    );
    expect(screen.getByText('Can you use class in a sentence?')).toBeInTheDocument();
  });

  it('keeps the saved greeting separate when a live answer arrives', () => {
    sdk.conversationMessages = [
      { role: 'user', final: true, createdAt: '2', parts: [{ text: 'xin chào', final: true, createdAt: '2' }] },
      { role: 'assistant', final: false, createdAt: '3', parts: [{ text: { spoken: 'Chào con!', unspoken: '' }, final: false, createdAt: '3' }] },
    ];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[{ role: 'teacher', text: 'Hi! My name is Luna.' }]} />
      </PipecatVoiceProvider>,
    );

    const rows = document.querySelectorAll('.bubble-row');
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent('Hi! My name is Luna.');
    expect(rows[1]).toHaveTextContent('xin chào');
    expect(rows[2]).toHaveTextContent('Chào con!');
  });

  it('does not collapse the saved greeting and introduction into one live bubble', () => {
    sdk.conversationMessages = [{
      role: 'assistant', final: true, createdAt: '1', parts: [{
        text: { spoken: 'Hi! My name is Luna. Let us learn HELLO.', unspoken: '' }, final: true, createdAt: '1',
      }],
    }];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[
          { role: 'teacher', text: 'Hi! My name is Luna.' },
          { role: 'teacher', text: 'Let us learn HELLO.' },
        ]} />
      </PipecatVoiceProvider>,
    );

    const rows = document.querySelectorAll('.bubble-row');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Hi! My name is Luna.');
    expect(rows[1]).toHaveTextContent('Let us learn HELLO.');
  });

  it('does not repeat typed learner text after the saved session catches up', async () => {
    const user = userEvent.setup();
    function TypedInput() {
      const voice = useVoiceLesson();
      return <button onClick={() => void voice.sendText('xin chào')}>Type answer</button>;
    }
    render(<PipecatVoiceProvider sessionId="session-7">
      <ChatPanel messages={[
        { role: 'teacher', text: 'Hello!' },
        { role: 'learner', text: 'xin chào' },
      ]} />
      <TypedInput />
    </PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Type answer' }));

    expect(screen.getAllByText('xin chào')).toHaveLength(1);
  });

  it('still shows a newly repeated learner answer while an older copy is saved', async () => {
    const user = userEvent.setup();
    function TypedInput() {
      const voice = useVoiceLesson();
      return <button onClick={() => void voice.sendText('xin chào')}>Repeat answer</button>;
    }
    render(<PipecatVoiceProvider sessionId="session-7">
      <ChatPanel messages={[
        { role: 'teacher', text: 'Hello!' },
        { role: 'learner', text: 'xin chào' },
      ]} />
      <TypedInput />
    </PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Repeat answer' }));
    await user.click(screen.getByRole('button', { name: 'Repeat answer' }));

    expect(screen.getAllByText('xin chào')).toHaveLength(2);
  });

  it('keeps a second spoken answer even when its words repeat a saved answer', () => {
    sdk.conversationMessages = [
      { role: 'user', final: true, createdAt: '1', parts: [{ text: 'hello', final: true, createdAt: '1' }] },
      { role: 'user', final: true, createdAt: '2', parts: [{ text: 'hello', final: true, createdAt: '2' }] },
    ];
    render(<PipecatVoiceProvider sessionId="session-7">
      <ChatPanel messages={[{ role: 'learner', text: 'hello' }]} />
    </PipecatVoiceProvider>);

    expect(screen.getAllByText('hello')).toHaveLength(2);
  });

  it('shows finalized manual voice turns separately when Pipecat groups their transcript parts', () => {
    sdk.conversationMessages = [{
      role: 'user', final: false, createdAt: '2026-09-24T14:00:00.000Z',
      parts: [
        { text: "Yes, I'm ready.", final: true, createdAt: '2026-09-24T14:00:00.000Z' },
        { text: 'Hello, Luna.', final: true, createdAt: '2026-09-24T14:00:10.000Z' },
      ],
    }];
    const view = render(<PipecatVoiceProvider sessionId="session-7">
      <ChatPanel messages={[{ role: 'learner', text: "Yes, I'm ready." }]} />
    </PipecatVoiceProvider>);

    expect(screen.getAllByText("Yes, I'm ready.")).toHaveLength(1);
    expect(screen.getAllByText('Hello, Luna.')).toHaveLength(1);
    expect(screen.queryByText("Yes, I'm ready. Hello, Luna.")).not.toBeInTheDocument();

    view.rerender(<PipecatVoiceProvider sessionId="session-7">
      <ChatPanel messages={[
        { role: 'learner', text: "Yes, I'm ready." },
        { role: 'learner', text: 'Hello, Luna.' },
      ]} />
    </PipecatVoiceProvider>);
    expect(screen.getAllByText("Yes, I'm ready.")).toHaveLength(1);
    expect(screen.getAllByText('Hello, Luna.')).toHaveLength(1);
  });

  it('keeps saved lesson history alongside live Pipecat turns', () => {
    sdk.conversationMessages = [
      { role: 'assistant', final: true, createdAt: '1', parts: [{ text: { spoken: 'Old interrupted answer.', unspoken: '' }, final: true, createdAt: '1' }] },
      { role: 'user', final: true, createdAt: '2', parts: [{ text: 'City.', final: true, createdAt: '2' }] },
      { role: 'assistant', final: false, createdAt: '3', parts: [{ text: { spoken: '', unspoken: 'Current answer.' }, final: false, createdAt: '3' }] },
    ];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[{ role: 'teacher', text: 'Saved opening greeting.' }]} />
      </PipecatVoiceProvider>,
    );

    expect(screen.getByText('Old interrupted answer.')).toBeInTheDocument();
    expect(screen.getByText('City.')).toBeInTheDocument();
    expect(screen.getByText('Current answer.')).toBeInTheDocument();
    expect(screen.getByText('Saved opening greeting.')).toBeInTheDocument();
  });

  it('replaces live partial text with the saved complete turn without duplication', () => {
    sdk.conversationMessages = [
      { role: 'user', final: true, createdAt: '1', parts: [{ text: 'I live in Hanoi.', final: true, createdAt: '1' }] },
      { role: 'assistant', final: false, createdAt: '2', parts: [{ text: { spoken: '', unspoken: 'What do you like about it?' }, final: false, createdAt: '2' }] },
    ];
    const view = render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[]} />
      </PipecatVoiceProvider>,
    );
    expect(screen.getByText('I live in Hanoi.').closest('.bubble-row')).toHaveClass('learner');
    expect(screen.getByText('What do you like about it?').closest('.bubble-row')).toHaveClass('teacher');

    view.rerender(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[
          { role: 'learner', text: 'I live in Hanoi.' },
          { role: 'teacher', text: 'Hanoi is a busy city. What do you like about it?' },
        ]} />
      </PipecatVoiceProvider>,
    );

    expect(screen.getAllByText('I live in Hanoi.')).toHaveLength(1);
    expect(screen.getByText('Hanoi is a busy city. What do you like about it?')).toBeInTheDocument();
    expect(screen.queryByText('What do you like about it?')).not.toBeInTheDocument();
  });
});
