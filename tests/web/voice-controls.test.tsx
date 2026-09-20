import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const enableMic = vi.fn();
  const client = {
    startBotAndConnect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn().mockResolvedValue(undefined),
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
    sdk.options = undefined;
  });

  it('uses the official Pipecat microphone toggle', async () => {
    const user = userEvent.setup();
    render(<PipecatVoiceProvider sessionId="s1"><VoiceControls /></PipecatVoiceProvider>);
    const callbacks = sdk.options?.callbacks as {
      onTransportStateChanged(state: string): void;
    };
    act(() => callbacks.onTransportStateChanged('ready'));
    await user.click(screen.getByRole('button', { name: 'Mute microphone' }));
    expect(sdk.enableMic).toHaveBeenCalledOnce();
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
    expect(screen.getByRole('button', { name: 'Start conversation' })).toBeInTheDocument();

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
