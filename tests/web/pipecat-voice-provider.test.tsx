import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const startBotAndConnect = vi.fn().mockResolvedValue(undefined);
  const disconnect = vi.fn().mockResolvedValue(undefined);
  const sendText = vi.fn().mockResolvedValue(undefined);
  const enableMic = vi.fn();
  const client = { startBotAndConnect, disconnect, sendText, enableMic, state: 'disconnected' };
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
    sdk.enableMic.mockClear();
    sdk.conversationMessages = [];
    sdk.options = undefined;
    sdk.stores = [];
  });

  afterEach(() => vi.useRealTimers());

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
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    expect(sdk.options).toMatchObject({
      enableMic: true,
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

    await user.click(screen.getByRole('button', { name: 'Start conversation' }));

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

    await user.click(screen.getByRole('button', { name: 'Start conversation' }));
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

  it('does not ask for a reconnect when Pipecat reports a non-fatal service error', () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onError(message: { data: { error: string; fatal: boolean } }): void;
    };

    act(() => callbacks.onError({
      data: {
        error: 'TTS context completed with no audio',
        fatal: false,
      },
    }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Voice audio was interrupted. Please try speaking again.',
    );
    expect(screen.queryByText(/stop and reconnect/i)).not.toBeInTheDocument();
  });

  it('clears an old recoverable TTS warning when the bot speaks again, but retains a new failure', () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onError(message: { data: { error: string; fatal: boolean } }): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
    };

    act(() => callbacks.onError({ data: { error: 'Soniox TTS error 408 request_timeout', fatal: false } }));
    expect(screen.getByRole('alert')).toHaveTextContent('Voice audio was interrupted.');

    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    act(() => callbacks.onError({ data: { error: 'Soniox TTS error 408 request_timeout', fatal: false } }));
    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByRole('alert')).toHaveTextContent('Voice audio was interrupted.');
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
    expect(screen.getByRole('button', { name: 'Start voice lesson' })).toBeInTheDocument();
  });

  it('shows Pipecat listening, thinking, and speaking states in the voice controls', () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onBotReady(): void;
      onUserStartedSpeaking(): void;
      onUserStoppedSpeaking(): void;
      onBotLlmStarted(): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
    };

    act(() => callbacks.onBotReady());
    expect(screen.getByText('Ready')).toBeInTheDocument();

    act(() => callbacks.onUserStartedSpeaking());
    expect(screen.getByText('Listening')).toBeInTheDocument();

    act(() => callbacks.onUserStoppedSpeaking());
    expect(screen.getByText('Thinking')).toBeInTheDocument();

    act(() => callbacks.onBotLlmStarted());
    expect(screen.getByText('Thinking')).toBeInTheDocument();

    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.getByText('Speaking')).toBeInTheDocument();

    act(() => callbacks.onBotStoppedSpeaking());
    expect(screen.getByText('Ready')).toBeInTheDocument();
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
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
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
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));

    expect(Array.from(document.querySelectorAll('.bubble-row.teacher'), (row) => row.querySelector('p')?.textContent)).toEqual([
      'Cô trò mình sang Trạm 1.',
      '"HELLO" nghĩa là xin chào.',
      'Listen first! "HELLO"',
      'Your turn now!',
    ]);
  });

  it('keeps the image with the current spoken line when its cue arrives after the transcript starts', async () => {
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
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-1', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1 học từ mới.</vi>',
      },
    }));

    const image = screen.getByRole('img', { name: 'Hình minh họa cho câu nói của Luna' });
    expect(image.closest('.bubble-row')).toHaveTextContent('Cô trò mình sang Trạm 1');
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(2);
    expect(screen.queryByText(/học từ mới/)).not.toBeInTheDocument();
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
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-1', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1.</vi>\n<en>"HELLO"</en><vi> nghĩa là xin chào, con nói khi gặp bạn.</vi>\n<en>Listen first!</en>',
      },
    }));

    const rows = document.querySelectorAll('.bubble-row.teacher');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Cô trò mình sang Trạm 1.');
    expect(rows[0].querySelector('img')).toBeInTheDocument();
    expect(rows[1]).toHaveTextContent('"HELLO" nghĩa là xin chào');
    expect(screen.queryByText(/con nói khi gặp bạn|Listen first/)).not.toBeInTheDocument();
  });

  it('shows the image before audio and joins it to the first spoken line', async () => {
    const user = userEvent.setup();
    const createdAt = new Date(Date.now() - 1000).toISOString();
    sdk.conversationMessages = [{
      role: 'user', final: true, createdAt, parts: [{ text: 'hi', final: true, createdAt }],
    }];
    const view = render(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    act(() => (sdk.options?.callbacks as { onTransportStateChanged(state: string): void }).onTransportStateChanged('ready'));
    act(() => (sdk.options?.callbacks as { onServerMessage(message: object): void }).onServerMessage({
      event: 'teacher-image', payload: {
        turn_id: 'turn-1', image_url: '/images/hello.webp',
        spoken_text: '<vi>Cô trò mình sang Trạm 1 học từ mới.</vi>',
      },
    }));
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);
    expect(screen.getByRole('img', { name: 'Hình minh họa cho câu nói của Luna' })).toBeInTheDocument();

    sdk.conversationMessages = [
      sdk.conversationMessages[0],
      { role: 'assistant', final: false, createdAt: new Date().toISOString(), parts: [{
        text: { spoken: 'Cô trò mình', unspoken: ' sang Trạm 1 học từ mới.' }, final: false, createdAt,
      }] },
    ];
    view.rerender(<PipecatVoiceProvider sessionId="session-7"><ChatPanel messages={[]} /><VoiceControls /></PipecatVoiceProvider>);
    const image = screen.getByRole('img', { name: 'Hình minh họa cho câu nói của Luna' });
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);
    expect(image.closest('.bubble-row')).toHaveTextContent('Cô trò mình');
    expect(screen.queryByText(/sang Trạm 1 học từ mới/)).not.toBeInTheDocument();
  });

  it('reveals only Luna words confirmed spoken during an active voice lesson', async () => {
    const user = userEvent.setup();
    sdk.conversationMessages = [{
      role: 'assistant', final: false, createdAt: '2026-09-22T00:00:00Z', parts: [
        { text: { spoken: 'Listen first!\nHEL', unspoken: 'LO means hello.\nYour turn now!' }, final: false, createdAt: '1' },
      ],
    }];
    render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={2}>
      <ChatPanel messages={[
        { role: 'teacher', text: 'Hello, Quang!' },
        { role: 'teacher', text: 'Listen first!\nHELLO means hello.\nYour turn now!' },
      ]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
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
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
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
    const view = render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: 'Listen first!\nHELLO means hello.\nYour turn now!' }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(0);

    sdk.conversationMessages = spoken('Listen first!');
    view.rerender(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: 'Listen first!\nHELLO means hello.\nYour turn now!' }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    expect(screen.getByText('Listen first!')).toBeVisible();
    expect(document.querySelectorAll('.bubble-row.teacher')).toHaveLength(1);

    sdk.conversationMessages = spoken('Listen first!\nHELLO');
    view.rerender(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: 'Listen first!\nHELLO means hello.\nYour turn now!' }]} />
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
    const view = render(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={1}>
      <ChatPanel messages={[{ role: 'teacher', text: 'HELLO means hello.' }]} />
      <VoiceControls />
    </PipecatVoiceProvider>);
    await user.click(screen.getByRole('button', { name: 'Start voice lesson' }));
    const callbacks = sdk.options?.callbacks as { onTransportStateChanged(state: string): void };
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Stop voice lesson' }));

    expect(screen.getByText('HEL')).toBeVisible();
    expect(screen.queryByText('HELLO means hello.')).not.toBeInTheDocument();
    view.rerender(<PipecatVoiceProvider sessionId="session-7" savedMessageCount={3}>
      <ChatPanel messages={[
        { role: 'teacher', text: 'HELLO means hello.' },
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
