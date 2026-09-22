import { useEffect, useRef } from 'react';
import { usePipecatConversation } from '@pipecat-ai/client-react';
import type { BotOutputText, ConversationMessage } from '@pipecat-ai/client-react';
import type { Message } from '@/lib/types';
import { VoiceLatency } from './voice/VoiceLatency';
import { useOptionalVoiceLesson } from './voice/PipecatVoiceProvider';

function conversationText(message: ConversationMessage): string {
  return message.parts.map((part) => {
    if (typeof part.text === 'string') return part.text;
    const output = part.text as BotOutputText;
    return `${output.spoken}${output.unspoken}`;
  }).join(' ').trim();
}

function teacherDisplayText(text: string): string {
  return text.replace(/\[[^\]]*\]/g, '').replace(/\s+/g, ' ').trim();
}

export function ChatPanel({ messages }: { messages: Message[] }) {
  const latestMessage = useRef<HTMLDivElement>(null);
  const voice = useOptionalVoiceLesson();
  const { messages: pipecatMessages } = usePipecatConversation();
  const pipecatConversation = pipecatMessages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .map((message) => ({
      role: message.role === 'user' ? 'learner' as const : 'teacher' as const,
      text: conversationText(message),
      timestamp: message.createdAt,
    }))
    .filter((message) => message.text);
  const baseMessages = pipecatConversation.length > 0
    ? pipecatConversation
    : messages.map((message, index) => ({
      ...message,
      timestamp: `${message.turn_id ?? 'opening'}-${index}`,
    }));
  const displayedMessages = [...baseMessages, ...(voice?.sentText ?? []).map((message) => ({
    role: 'learner' as const,
    text: message.text,
    timestamp: message.timestamp,
  }))].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp);
    const rightTime = Date.parse(right.timestamp);
    return (Number.isNaN(leftTime) ? 0 : leftTime) - (Number.isNaN(rightTime) ? 0 : rightTime);
  });
  const latestTeacherIndex = displayedMessages.findLastIndex((message) => message.role === 'teacher');
  useEffect(() => { latestMessage.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [displayedMessages.length]);
  return <div className="chat-scroll" aria-live="polite" aria-label="Conversation with Luna">
    {displayedMessages.map((message, index) => <article className={`bubble-row ${message.role}`} key={`${message.role}-${message.timestamp}`}>
      {message.role === 'teacher' && <div className="avatar" aria-hidden="true">L</div>}
      <div className="bubble"><span className="speaker"><span>{message.role === 'teacher' ? 'Luna' : 'Quang'}</span>{index === latestTeacherIndex && <VoiceLatency />}</span><p>{message.role === 'teacher' ? teacherDisplayText(message.text) : message.text}</p></div>
    </article>)}
    <div ref={latestMessage} aria-hidden="true" />
  </div>;
}
