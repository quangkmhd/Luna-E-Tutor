import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const sdk = vi.hoisted(() => {
  const startBotAndConnect = vi.fn().mockResolvedValue(undefined);
  const disconnect = vi.fn().mockResolvedValue(undefined);
  const enableMic = vi.fn();
  const client = { startBotAndConnect, disconnect, enableMic, state: 'disconnected' };
  return { startBotAndConnect, disconnect, enableMic, client, options: undefined as Record<string, unknown> | undefined };
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
  PipecatClientProvider: ({ children }: { children: React.ReactNode }) => children,
  PipecatClientAudio: () => <div data-testid="pipecat-audio" />,
  PipecatClientMicToggle: ({ children }: { children: (value: object) => React.ReactNode }) => children({
    isMicEnabled: true, disabled: false, onClick: sdk.enableMic,
  }),
}));

import { PipecatVoiceProvider } from '@/components/voice/PipecatVoiceProvider';
import { VoiceControls } from '@/components/voice/VoiceControls';

describe('PipecatVoiceProvider', () => {
  beforeEach(() => {
    sdk.startBotAndConnect.mockClear();
    sdk.disconnect.mockClear();
    sdk.enableMic.mockClear();
    sdk.options = undefined;
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

  it('disconnects the old client when the active session changes', async () => {
    const view = render(
      <PipecatVoiceProvider key="old" sessionId="old"><span>lesson</span></PipecatVoiceProvider>,
    );
    view.rerender(
      <PipecatVoiceProvider key="new" sessionId="new"><span>lesson</span></PipecatVoiceProvider>,
    );
    await waitFor(() => expect(sdk.disconnect).toHaveBeenCalledOnce());
  });

  it('shows interim speech without submitting it as a typed turn', async () => {
    const onSessionChanged = vi.fn();
    render(
      <PipecatVoiceProvider sessionId="session-7" onSessionChanged={onSessionChanged}>
        <VoiceControls />
      </PipecatVoiceProvider>,
    );
    const callbacks = sdk.options?.callbacks as {
      onUserTranscript(data: { text: string; final: boolean }): void;
      onBotStoppedSpeaking(): void;
    };
    act(() => callbacks.onUserTranscript({ text: 'I live in', final: false }));
    expect(screen.getByText('You said').closest('p')).toHaveTextContent('I live in');
    expect(onSessionChanged).not.toHaveBeenCalled();
    act(() => callbacks.onUserTranscript({ text: 'I live in the city.', final: true }));
    expect(screen.getByText('You said').closest('p')).toHaveTextContent('I live in the city.');
  });
});
