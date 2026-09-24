import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const enableMic = vi.fn();
  const client = {
    startBotAndConnect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn().mockResolvedValue(undefined),
    enableMic,
    sendClientMessage: vi.fn(),
  };
  return { enableMic, client, options: undefined as Record<string, unknown> | undefined };
});

vi.mock('@pipecat-ai/client-js', () => ({
  PipecatClient: vi.fn(function (options: Record<string, unknown>) {
    sdk.options = options;
    return sdk.client;
  }),
}));
vi.mock('@pipecat-ai/small-webrtc-transport', () => ({
  SmallWebRTCTransport: vi.fn(function () { return {}; }),
}));
vi.mock('@pipecat-ai/client-react', () => ({
  PipecatClientProvider: ({ children }: { children: React.ReactNode }) => children,
  PipecatClientAudio: () => null,
  PipecatClientMicToggle: ({ children }: { children: (value: object) => React.ReactNode }) => children({
    isMicEnabled: true, disabled: false, onClick: sdk.enableMic,
  }),
}));

import { PipecatVoiceProvider } from '@/components/voice/PipecatVoiceProvider';
import { VoiceControls } from '@/components/voice/VoiceControls';

describe('VoiceControls', () => {
  beforeEach(() => {
    sdk.enableMic.mockClear();
    sdk.client.sendClientMessage.mockClear();
    sdk.client.startBotAndConnect.mockClear();
    sdk.options = undefined;
  });

  it('submits Voice only when Gửi is pressed and keeps the mic off until server readiness', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="s1"><VoiceControls /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onServerMessage(message: unknown): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } }));
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(sdk.client.sendClientMessage).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Gửi' }));
    expect(sdk.enableMic).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeDisabled();
    await waitFor(() => expect(sdk.client.sendClientMessage).toHaveBeenCalledWith(
      'luna.submit-turn', expect.objectContaining({ turn_id: expect.any(String) }),
    ));
  });

  it('connects muted and waits for a separate mic click after Luna speaks', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="s1"><VoiceControls /></PipecatVoiceProvider>);
    expect(screen.queryByRole('button', { name: 'Start voice lesson' })).not.toBeInTheDocument();
    const mic = screen.getByRole('button', { name: 'Bật mic để nói' });
    expect(mic.className).toContain('micButton');
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    expect(mic.querySelector('[data-mic-off-mark]')).toBeInTheDocument();

    await user.click(mic);
    expect(sdk.client.startBotAndConnect).toHaveBeenCalledOnce();
    expect(sdk.enableMic).not.toHaveBeenCalledWith(true);
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
      onServerMessage(message: unknown): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));
    act(() => callbacks.onBotStartedSpeaking());
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    expect(screen.getByRole('status', { name: 'Loa đang phát' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeDisabled();
    act(() => callbacks.onBotStoppedSpeaking());
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } }));
    expect(screen.queryByRole('status', { name: 'Loa đang phát' })).not.toBeInTheDocument();
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(sdk.enableMic).toHaveBeenLastCalledWith(true);
    expect(screen.getByText('Đang nghe')).toBeVisible();
    expect(screen.queryByText('MIC ĐANG TẮT')).not.toBeInTheDocument();
  });

  it('keeps mic on at transcript final and turns it off when Luna audio starts', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="s1"><VoiceControls /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onUserStartedSpeaking(): void;
      onUserTranscript?: (data: { text: string; final: boolean; timestamp: string; user_id: string }) => void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
      onServerMessage(message: unknown): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } }));
    expect(sdk.options).toMatchObject({ enableMic: false });
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(sdk.enableMic).toHaveBeenLastCalledWith(true);
    expect(screen.getByText('Đang nghe')).toBeVisible();
    act(() => callbacks.onUserStartedSpeaking());
    expect(screen.getByText('Đang nói')).toBeVisible();
    act(() => callbacks.onUserTranscript?.({ text: 'Xin chào', final: false, timestamp: '1', user_id: 'u1' }));
    expect(sdk.enableMic).toHaveBeenCalledTimes(1);
    act(() => callbacks.onUserTranscript?.({ text: 'Xin chào', final: true, timestamp: '2', user_id: 'u1' }));
    expect(sdk.enableMic).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Đang nói')).toBeVisible();
    act(() => callbacks.onBotStartedSpeaking());
    expect(sdk.enableMic).toHaveBeenLastCalledWith(false);
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    act(() => callbacks.onBotStoppedSpeaking());
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } }));
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(sdk.enableMic).toHaveBeenLastCalledWith(true);
  });

  it('does not turn mic back on when greeting audio starts during connection', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="s1"><VoiceControls /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
      onBotStartedSpeaking(): void;
      onBotStoppedSpeaking(): void;
      onServerMessage(message: unknown): void;
    };
    sdk.client.startBotAndConnect.mockImplementationOnce(async () => {
      callbacks.onTransportStateChanged('ready');
      callbacks.onBotStartedSpeaking();
    });
    await user.click(screen.getByRole('button', { name: 'Bật mic để nói' }));
    expect(sdk.enableMic).not.toHaveBeenCalledWith(true);
    expect(screen.getByText('MIC ĐANG TẮT')).toBeVisible();
    act(() => callbacks.onBotStoppedSpeaking());
    act(() => callbacks.onServerMessage({ event: 'luna-turn-ready', payload: { ready: true } }));
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeEnabled();
  });

  it('renders an actionable microphone permission error', () => {
    render(<PipecatVoiceProvider sessionId="s1"><VoiceControls /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onDeviceError(error: { type: string }): void;
    };
    act(() => callbacks.onDeviceError({ type: 'permissions' }));
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Allow microphone access in your browser settings, then try again.',
    );
  });

  it('uses custom labels for a non-lesson voice room', () => {
    render(
      <PipecatVoiceProvider sessionId="s1">
        <VoiceControls startLabel="Start conversation" stopLabel="Stop conversation" />
      </PipecatVoiceProvider>,
    );
    expect(screen.getByRole('button', { name: 'Bật mic để nói' })).toBeInTheDocument();

    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));
    expect(screen.getByRole('button', { name: 'Stop conversation' })).toBeInTheDocument();
  });

  it('notifies the room after a conversation is stopped', async () => {
    const user = userEvent.setup();
    const onStopped = vi.fn();
    render(
      <PipecatVoiceProvider sessionId="s1">
        <VoiceControls stopLabel="Stop conversation" onStopped={onStopped} />
      </PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));

    await user.click(screen.getByRole('button', { name: 'Stop conversation' }));

    expect(sdk.client.disconnect).toHaveBeenCalled();
    expect(onStopped).toHaveBeenCalledOnce();
  });

  it('still resets the room when the transport rejects disconnect', async () => {
    const user = userEvent.setup();
    const onStopped = vi.fn();
    sdk.client.disconnect.mockRejectedValueOnce(new Error('transport already closed'));
    render(
      <PipecatVoiceProvider sessionId="s1">
        <VoiceControls stopLabel="Stop conversation" onStopped={onStopped} />
      </PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));

    await user.click(screen.getByRole('button', { name: 'Stop conversation' }));

    expect(onStopped).toHaveBeenCalledOnce();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The voice session could not close cleanly. You can reconnect.',
    );
  });
});
