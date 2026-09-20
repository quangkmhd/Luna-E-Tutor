import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const startBotAndConnect = vi.fn().mockResolvedValue(undefined);
  const disconnect = vi.fn().mockResolvedValue(undefined);
  const enableMic = vi.fn();
  const client = { startBotAndConnect, disconnect, enableMic, state: 'disconnected' };
  return {
    startBotAndConnect,
    disconnect,
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
import { VoiceControls } from '@/components/voice/VoiceControls';
import { VoiceLatency } from '@/components/voice/VoiceLatency';
import { ChatPanel } from '@/components/ChatPanel';

describe('PipecatVoiceProvider', () => {
  beforeEach(() => {
    sdk.startBotAndConnect.mockClear();
    sdk.disconnect.mockClear();
    sdk.enableMic.mockClear();
    sdk.conversationMessages = [];
    sdk.options = undefined;
    sdk.stores = [];
  });

  afterEach(() => vi.useRealTimers());

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

  it('disconnects and becomes startable again when Pipecat reports a fatal service error', async () => {
    render(
      <PipecatVoiceProvider sessionId="session-7"><VoiceControls /></PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onError(message: { data: { error: string; fatal: boolean } }): void;
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

  it('renders Pipecat conversation as the single source instead of mixing backend messages into it', () => {
    sdk.conversationMessages = [
      { role: 'assistant', final: true, createdAt: '1', parts: [{ text: { spoken: 'Old interrupted answer.', unspoken: '' }, final: true, createdAt: '1' }] },
      { role: 'user', final: true, createdAt: '2', parts: [{ text: 'City.', final: true, createdAt: '2' }] },
      { role: 'assistant', final: false, createdAt: '3', parts: [{ text: { spoken: '', unspoken: 'Current answer.' }, final: false, createdAt: '3' }] },
    ];
    render(
      <PipecatVoiceProvider sessionId="session-7">
        <ChatPanel messages={[{ role: 'teacher', text: 'Backend copy of the current answer.' }]} />
      </PipecatVoiceProvider>,
    );

    expect(screen.getByText('Old interrupted answer.')).toBeInTheDocument();
    expect(screen.getByText('City.')).toBeInTheDocument();
    expect(screen.getByText('Current answer.')).toBeInTheDocument();
    expect(screen.queryByText('Backend copy of the current answer.')).not.toBeInTheDocument();
  });

  it('does not switch back to backend messages while Pipecat owns the conversation', () => {
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
    expect(screen.getAllByText('What do you like about it?')).toHaveLength(1);
    expect(screen.queryByText('Hanoi is a busy city. What do you like about it?')).not.toBeInTheDocument();
  });
});
