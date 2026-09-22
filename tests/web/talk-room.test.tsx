import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const voice = vi.hoisted(() => ({
  provider: vi.fn(),
}));

vi.mock('@/components/voice/PipecatVoiceProvider', () => ({
  PipecatVoiceProvider: (props: {
    children: React.ReactNode;
    endpoint?: string;
    requestBody?: Record<string, unknown>;
  }) => {
    voice.provider(props);
    return <div data-testid="talk-provider">{props.children}</div>;
  },
}));
vi.mock('@/components/voice/VoiceControls', () => ({
  VoiceControls: ({
    startLabel,
    stopLabel,
    onStopped,
  }: {
    startLabel?: string;
    stopLabel?: string;
    onStopped?: () => void;
  }) => (
    <>
      <button type="button">{startLabel}</button>
      <button type="button" onClick={onStopped}>{stopLabel}</button>
    </>
  ),
}));
vi.mock('@/components/ChatPanel', () => ({
  ChatPanel: () => <div data-testid="talk-transcript">Transcript</div>,
}));

import { TalkRoom } from '@/components/talk/TalkRoom';

describe('TalkRoom', () => {
  beforeEach(() => voice.provider.mockClear());

  it('shows classroom-like topic, work, and guide regions without fake progress', () => {
    render(<TalkRoom />);
    expect(screen.getByRole('navigation', { name: 'Chủ đề Free Talk' })).toBeVisible();
    expect(screen.getByRole('region', { name: 'Chọn chủ đề trò chuyện' })).toBeVisible();
    expect(screen.getByText('Mẹo trò chuyện')).toBeVisible();
    expect(screen.queryByText(/ngày liên tiếp|huy hiệu|điểm thưởng/i)).not.toBeInTheDocument();
  });

  it('will not start from whitespace only', async () => {
    const user = userEvent.setup();
    render(<TalkRoom />);
    await user.type(screen.getByLabelText('Or enter another topic'), '   ');
    expect(screen.getByRole('button', { name: 'Start Free Talk' })).toBeDisabled();
    expect(voice.provider).not.toHaveBeenCalled();
  });

  it('requires a topic before starting', () => {
    render(<TalkRoom />);
    expect(screen.getByRole('button', { name: 'Start Free Talk' })).toBeDisabled();
  });

  it('selects Animals and passes only that topic to port 7863', async () => {
    const user = userEvent.setup();
    render(<TalkRoom />);

    await user.click(screen.getByRole('button', { name: 'Animals' }));
    await user.click(screen.getByRole('button', { name: 'Start Free Talk' }));

    expect(voice.provider).toHaveBeenCalled();
    expect(voice.provider.mock.lastCall?.[0]).toMatchObject({
      endpoint: 'http://localhost:7863',
      requestBody: { topic: 'Animals' },
    });
  });

  it('trims a custom topic and enforces maxlength 120', async () => {
    const user = userEvent.setup();
    render(<TalkRoom />);
    const input = screen.getByLabelText('Or enter another topic');

    expect(input).toHaveAttribute('maxlength', '120');
    await user.type(input, '  My dream job  ');
    await user.click(screen.getByRole('button', { name: 'Start Free Talk' }));

    expect(voice.provider.mock.lastCall?.[0]).toMatchObject({
      requestBody: { topic: 'My dream job' },
    });
  });

  it('renders the Pipecat transcript through ChatPanel after starting', async () => {
    const user = userEvent.setup();
    render(<TalkRoom />);
    await user.click(screen.getByRole('button', { name: 'Food' }));
    await user.click(screen.getByRole('button', { name: 'Start Free Talk' }));

    expect(screen.getByTestId('talk-transcript')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Phòng trò chuyện Luna' })).toBeVisible();
    expect(screen.getByText('Food')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Start conversation' })).toBeInTheDocument();
  });

  it('changes topic by unmounting the previous voice provider', async () => {
    const user = userEvent.setup();
    render(<TalkRoom />);
    await user.click(screen.getByRole('button', { name: 'Travel' }));
    await user.click(screen.getByRole('button', { name: 'Start Free Talk' }));
    expect(screen.getByTestId('talk-provider')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Change topic' }));

    expect(screen.queryByTestId('talk-provider')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start Free Talk' })).toBeEnabled();
  });

  it('returns to setup after stopping so a restart gets a fresh transcript store', async () => {
    const user = userEvent.setup();
    render(<TalkRoom />);
    await user.click(screen.getByRole('button', { name: 'Animals' }));
    await user.click(screen.getByRole('button', { name: 'Start Free Talk' }));

    await user.click(screen.getByRole('button', { name: 'Stop conversation' }));

    expect(screen.queryByTestId('talk-provider')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start Free Talk' })).toBeEnabled();
  });
});
