import {render, screen} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';

const disconnect = vi.fn().mockResolvedValue(undefined);
const clients: unknown[] = [];

vi.mock('@pipecat-ai/client-js', () => ({
  PipecatClient: class {
    disconnect = disconnect;
    constructor(options: unknown) { clients.push(options); }
  },
}));

vi.mock('@pipecat-ai/client-react', () => ({
  PipecatClientProvider: ({children}: {children: React.ReactNode}) =>
    <div data-testid="provider">{children}</div>,
  PipecatClientAudio: () => <div data-testid="pipecat-audio" />,
}));

vi.mock('@pipecat-ai/small-webrtc-transport', () => ({
  SmallWebRTCTransport: class {},
}));

import {SpeakingPipecatProvider} from '@/components/speaking/SpeakingPipecatProvider';

afterEach(() => vi.unstubAllGlobals());

it('provides one client and delegates audio to PipecatClientAudio', () => {
  const {rerender, unmount} = render(
    <SpeakingPipecatProvider><span>room</span></SpeakingPipecatProvider>,
  );
  rerender(<SpeakingPipecatProvider><span>room again</span></SpeakingPipecatProvider>);

  expect(clients).toHaveLength(1);
  expect(screen.getByTestId('provider')).toContainElement(screen.getByTestId('pipecat-audio'));
  unmount();
  expect(disconnect).toHaveBeenCalledOnce();
});

it('does not create an application-owned Audio element', () => {
  const audioConstructor = vi.fn();
  vi.stubGlobal('Audio', audioConstructor);

  const {unmount} = render(
    <SpeakingPipecatProvider><span>room</span></SpeakingPipecatProvider>,
  );
  unmount();

  expect(audioConstructor).not.toHaveBeenCalled();
});
