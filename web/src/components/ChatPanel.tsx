import { useEffect, useRef } from 'react';
import { usePipecatConversation } from '@pipecat-ai/client-react';
import type { BotOutputText, ConversationMessage } from '@pipecat-ai/client-react';
import type { Message } from '@/lib/types';
import { VoiceLatency } from './voice/VoiceLatency';
import { useOptionalVoiceLesson } from './voice/PipecatVoiceProvider';

type DisplayMessage = { role: 'learner' | 'teacher'; text: string; timestamp: string; key?: string };

function conversationText(message: ConversationMessage, spokenOnly: boolean): string {
  return message.parts.map((part) => {
    if (typeof part.text === 'string') return spokenOnly && message.role === 'assistant' ? '' : part.text;
    const output = part.text as BotOutputText;
    return spokenOnly ? output.spoken : `${output.spoken}${output.unspoken}`;
  }).join(' ').trim();
}

function teacherDisplayText(text: string): string {
  return text.replace(/<\/?(?:vi|en)>/g, '').replace(/\[[^\]]*\]/g, '').split(/\r?\n/)
    .map((line) => line.replace(/\s+/g, ' ').trim()).filter(Boolean).join('\n');
}

function teacherMatchText(text: string): string {
  return teacherDisplayText(text).replace(/\s+/g, ' ').trim();
}

function stripSavedTeacherPrefix(text: string, savedText: string): string | null {
  const comparable = teacherMatchText(savedText);
  if (!comparable) return text;
  const prefix = new RegExp(`^${comparable.split(' ').map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+')}`);
  const match = text.match(prefix);
  if (match) return text.slice(match[0].length).trim();
  if (comparable.includes(teacherMatchText(text))) return null;
  return text;
}

function restoreAuthoredLines(live: DisplayMessage[], saved: Message[]): DisplayMessage[] {
  const restored: DisplayMessage[] = [];
  for (let index = 0; index < live.length;) {
    const first = live[index];
    if (first.role !== 'teacher') {
      restored.push(first);
      index += 1;
      continue;
    }
    let end = index + 1;
    while (end < live.length && live[end].role === 'teacher' && live[end].timestamp === first.timestamp) end += 1;
    const segments = live.slice(index, end);
    const spoken = teacherMatchText(segments.map((segment) => segment.text).join(' '));
    const authored = saved.find((message) => message.role === 'teacher' && teacherMatchText(message.text) === spoken);
    if (authored) restored.push({ ...first, text: authored.text });
    else restored.push(...segments);
    index = end;
  }
  return restored;
}

export function ChatPanel({ messages }: { messages: Message[] }) {
  const latestMessage = useRef<HTMLDivElement>(null);
  const voice = useOptionalVoiceLesson();
  const { messages: pipecatMessages } = usePipecatConversation({
    botOutputFilter: { spoken: true, unspoken: false },
  });
  const voiceRuns = voice?.voiceRuns ?? [];
  const spokenOnly = voiceRuns.length > 0;
  const pipecatConversation: DisplayMessage[] = pipecatMessages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .flatMap((message) => message.role === 'assistant' && spokenOnly
      ? message.parts.flatMap((part, index) => {
        const text = typeof part.text === 'string' ? '' : (part.text as BotOutputText).spoken.trim();
        return text ? [{ role: 'teacher' as const, text, timestamp: message.createdAt, key: `${message.createdAt}-part-${index}` }] : [];
      })
      : [{
        role: message.role === 'user' ? 'learner' as const : 'teacher' as const,
        text: conversationText(message, spokenOnly),
        timestamp: message.createdAt,
      }])
    .filter((message) => message.text);
  const savedMessages = messages.flatMap((message, index) => {
    if (voiceRuns.some((run) => index >= run.start && (run.end === undefined || index < run.end))) return [];
    const precedingRun = voiceRuns.findLast((run) => run.end !== undefined && index >= run.end);
    return [{ ...message, timestamp: precedingRun?.endedAt ?? `${message.turn_id ?? 'opening'}-${index}` }];
  });
  const sentText = voice?.sentText ?? [];
  const liveMessages = spokenOnly
    ? pipecatConversation.filter((message) => message.role !== 'learner' || !sentText.some((sent) => sent.text === message.text))
    : messages.length === 0 ? pipecatConversation : pipecatConversation.flatMap((message, index) => {
    if (message.role === 'learner') {
      const savedCount = savedMessages.filter((saved) => saved.role === 'learner' && saved.text === message.text).length;
      const liveCount = pipecatConversation.slice(0, index + 1)
        .filter((live) => live.role === 'learner' && live.text === message.text).length;
      return savedCount >= liveCount || sentText.some((sent) => sent.text === message.text) ? [] : [message];
    }
    let text: string | null = teacherDisplayText(message.text);
    for (const saved of savedMessages) {
      if (saved.role !== 'teacher') continue;
      if (!text) return [];
      text = stripSavedTeacherPrefix(text, saved.text);
    }
    return text ? [{ ...message, text }] : [];
  });
  const displayedMessages: DisplayMessage[] = [...savedMessages, ...(spokenOnly ? restoreAuthoredLines(liveMessages, messages) : liveMessages), ...sentText.filter((message, index) =>
    savedMessages.filter((saved) => saved.role === 'learner' && saved.text === message.text).length
      < sentText.slice(0, index + 1).filter((sent) => sent.text === message.text).length,
  ).map((message) => ({
    role: 'learner' as const,
    text: message.text,
    timestamp: message.timestamp,
  }))].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp);
    const rightTime = Date.parse(right.timestamp);
    return (Number.isNaN(leftTime) ? 0 : leftTime) - (Number.isNaN(rightTime) ? 0 : rightTime);
  });
  const visibleMessages = displayedMessages.flatMap((message) => message.role === 'teacher'
    ? teacherDisplayText(message.text).split('\n').filter(Boolean).map((line, index) => ({
      ...message, text: line, key: `${message.key ?? message.timestamp}-line-${index}`,
    }))
    : [message]);
  const latestTeacherIndex = visibleMessages.findLastIndex((message) => message.role === 'teacher');
  useEffect(() => { latestMessage.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [displayedMessages.length]);
  return <div className="chat-scroll" aria-live="polite" aria-label="Conversation with Luna">
    {visibleMessages.map((message, index) => <article className={`bubble-row ${message.role}`} key={`${message.role}-${message.key ?? message.timestamp}`}>
      {message.role === 'teacher' && <div className="avatar" aria-hidden="true">L</div>}
      <div className="bubble"><span className="speaker"><span>{message.role === 'teacher' ? 'Luna' : 'Quang'}</span>{index === latestTeacherIndex && <VoiceLatency />}</span><p>{message.role === 'teacher' ? teacherDisplayText(message.text) : message.text}</p></div>
    </article>)}
    <div ref={latestMessage} aria-hidden="true" />
  </div>;
}
