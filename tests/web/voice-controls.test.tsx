import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';

import { VoiceControls } from '@/components/speaking/VoiceControls';

const initDevices = vi.fn();
const startBotAndConnect = vi.fn();
const enableMic = vi.fn();
let transportState = 'disconnected';
let isMicEnabled = true;

vi.mock('@pipecat-ai/client-js', () => ({
  TransportStateEnum: {
    DISCONNECTED: 'disconnected',
    INITIALIZING: 'initializing',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    READY: 'ready',
  },
}));

vi.mock('@pipecat-ai/client-react', () => ({
  usePipecatClient: () => ({initDevices, startBotAndConnect}),
  usePipecatClientTransportState: () => transportState,
  usePipecatClientMicControl: () => ({isMicEnabled, enableMic}),
}));

beforeEach(() => {
  vi.clearAllMocks();
  initDevices.mockResolvedValue(undefined);
  startBotAndConnect.mockResolvedValue(undefined);
  enableMic.mockResolvedValue(undefined);
  transportState = 'disconnected';
  isMicEnabled = true;
});

afterEach(() => vi.unstubAllEnvs());

it('initializes devices and connects the Pipecat client', async () => {
  render(<VoiceControls sessionId="s1" onConnectionError={vi.fn()} />);

  await userEvent.click(screen.getByRole('button', {name: 'Bật micro'}));

  expect(initDevices).toHaveBeenCalledTimes(1);
  expect(startBotAndConnect).toHaveBeenCalledWith({
    endpoint: 'http://localhost:7860/start',
    requestData: {body: {speaking_session_id: 's1'}},
    timeout: 10_000,
  });
});

it('toggles the microphone without reconnecting when transport is ready', async () => {
  transportState = 'ready';
  isMicEnabled = true;
  render(<VoiceControls sessionId="s1" onConnectionError={vi.fn()} />);

  await userEvent.click(screen.getByRole('button', {name: 'Tắt micro'}));

  expect(enableMic).toHaveBeenCalledWith(false);
  expect(initDevices).not.toHaveBeenCalled();
  expect(startBotAndConnect).not.toHaveBeenCalled();
});

it('reports microphone permission errors to the room', async () => {
  initDevices.mockRejectedValueOnce(new Error('Microphone permission denied'));
  const onConnectionError = vi.fn();
  render(<VoiceControls sessionId="s1" onConnectionError={onConnectionError} />);

  await userEvent.click(screen.getByRole('button', {name: 'Bật micro'}));

  expect(onConnectionError).toHaveBeenCalledWith('Microphone permission denied');
  expect(startBotAndConnect).not.toHaveBeenCalled();
});

it('uses the public voice URL for remote browser access', async () => {
  vi.stubEnv('NEXT_PUBLIC_SPEAKING_VOICE_URL', 'https://voice.example.com/');
  render(<VoiceControls sessionId="s1" onConnectionError={vi.fn()} />);

  await userEvent.click(screen.getByRole('button', {name: 'Bật micro'}));

  expect(startBotAndConnect).toHaveBeenCalledWith(expect.objectContaining({
    endpoint: 'https://voice.example.com/start',
  }));
});

it('accepts a public voice URL that already includes the start endpoint', async () => {
  vi.stubEnv('NEXT_PUBLIC_SPEAKING_VOICE_URL', 'https://voice.example.com/start');
  render(<VoiceControls sessionId="s1" onConnectionError={vi.fn()} />);

  await userEvent.click(screen.getByRole('button', {name: 'Bật micro'}));

  expect(startBotAndConnect).toHaveBeenCalledWith(expect.objectContaining({
    endpoint: 'https://voice.example.com/start',
  }));
});
