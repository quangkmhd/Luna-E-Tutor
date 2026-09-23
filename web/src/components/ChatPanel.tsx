import { useEffect, useRef } from 'react';
import { usePipecatConversation } from '@pipecat-ai/client-react';
import type { BotOutputText, ConversationMessage } from '@pipecat-ai/client-react';
import type { Message } from '@/lib/types';
import { VoiceLatency } from './voice/VoiceLatency';
import { useOptionalVoiceLesson } from './voice/PipecatVoiceProvider';

type DisplayMessage = { role: 'learner' | 'teacher'; text: string; timestamp: string; key?: string; image_url?: string | null; turn_id?: string | null };

function emphasizedText(text: string) {
  return text.split(/(\*[^*\n]+\*)/g).map((part, index) => {
    const emphasis = part.match(/^\*([^*\n]+)\*$/);
    return emphasis ? <strong key={`emphasis-${index}`}>{emphasis[1]}</strong> : part;
  });
}

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
  return teacherDisplayText(text).replace(/\*([^*]+)\*/g, '$1').replace(/\s+/g, ' ').trim();
}

function speechKey(text: string): string {
  return teacherMatchText(text).toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
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

function spokenAuthoredLines(spoken: string, authored: string): string[] {
  const spokenWords = teacherDisplayText(spoken).split(/\s+/).filter(Boolean);
  const authoredLines = teacherDisplayText(authored).split('\n').filter(Boolean);
  if (!authoredLines.length) return spokenWords.length ? [spokenWords.join(' ')] : [];
  let offset = 0;
  return authoredLines.flatMap((line, index) => {
    const lineLength = line.split(/\s+/).filter(Boolean).length;
    const end = index === authoredLines.length - 1
      ? spokenWords.length : Math.min(offset + lineLength, spokenWords.length);
    const visible = spokenWords.slice(offset, end).join(' ');
    offset = end;
    return visible ? [visible] : [];
  });
}

export function ChatPanel({ messages }: { messages: Message[] }) {
  const latestMessage = useRef<HTMLDivElement>(null);
  const voice = useOptionalVoiceLesson();
  const { messages: pipecatMessages } = usePipecatConversation({
    botOutputFilter: { spoken: true, unspoken: false },
  });
  const voiceRuns = voice?.voiceRuns ?? [];
  const spokenOnly = voiceRuns.length > 0;
  const imageCue = voice?.teacherImageCue;
  const lastUserIndex = pipecatMessages.findLastIndex((message) => message.role === 'user');
  const authoredKey = imageCue?.spoken_text ? speechKey(imageCue.spoken_text) : '';
  const cueAssistant = imageCue?.image_url && authoredKey
    ? pipecatMessages.slice(lastUserIndex + 1).findLast((message) => {
      if (message.role !== 'assistant') return false;
      const spokenKey = speechKey(conversationText(message, true));
      return spokenKey && authoredKey.startsWith(spokenKey.slice(0, 24));
    })
    : undefined;
  const pipecatConversation: DisplayMessage[] = pipecatMessages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .flatMap((message) => message.role === 'assistant' && spokenOnly
      ? (message === cueAssistant && imageCue?.spoken_text
        ? spokenAuthoredLines(conversationText(message, true), imageCue.spoken_text)
        : [conversationText(message, true)]).flatMap((text, index) => text
        ? [{ role: 'teacher' as const, text, timestamp: message.createdAt, key: `${message.createdAt}-line-${index}` }]
        : [])
      : [{
        role: message.role === 'user' ? 'learner' as const : 'teacher' as const,
        text: conversationText(message, spokenOnly),
        timestamp: message.createdAt,
      }])
    .filter((message) => message.text);
  const savedMessages = messages.flatMap((message, index) => {
    const precedingRun = voiceRuns.findLast((run) => run.end !== undefined && index >= run.end);
    return [{ ...message, key: `saved-${index}`, timestamp: precedingRun?.endedAt ?? '' }];
  });
  const sentText = voice?.sentText ?? [];
  const liveMessages = voice?.phase === 'off' ? [] : messages.length === 0 ? pipecatConversation : pipecatConversation.flatMap((message, index) => {
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
  const savedCue = imageCue?.image_url && imageCue.turn_id
    ? savedMessages.some((message) => message.role === 'teacher' && message.turn_id === imageCue.turn_id)
    : false;
  const liveImageTarget = imageCue?.image_url && !savedCue && cueAssistant
    ? liveMessages.find((message) => message.role === 'teacher' && message.key === `${cueAssistant.createdAt}-line-0`)
    : undefined;
  const liveMessagesWithImages = liveMessages.map((message) => ({
    ...message,
    image_url: liveImageTarget?.key === message.key ? imageCue?.image_url : message.image_url,
  }));
  const pendingImage: DisplayMessage[] = imageCue?.image_url && !savedCue && !liveImageTarget
    ? [{
      role: 'teacher', text: '', timestamp: imageCue.receivedAt,
      key: `pending-image-${imageCue.turn_id ?? imageCue.receivedAt}`,
      turn_id: imageCue.turn_id, image_url: imageCue.image_url,
    }]
    : [];
  const displayedMessages: DisplayMessage[] = [...savedMessages, ...liveMessagesWithImages, ...pendingImage, ...sentText.filter((message, index) =>
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
    ? (teacherDisplayText(message.text).split('\n').filter(Boolean).length
      ? teacherDisplayText(message.text).split('\n').filter(Boolean).map((line, index) => ({
      ...message, image_url: index === 0 ? message.image_url : null,
      text: line, key: `${message.key ?? message.timestamp}-line-${index}`,
      }))
      : message.image_url ? [message] : [])
    : [message]);
  const latestTeacherIndex = visibleMessages.findLastIndex((message) => message.role === 'teacher');
  useEffect(() => { latestMessage.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [displayedMessages.length]);
  return <div className="chat-scroll" aria-live="polite" aria-label="Conversation with Luna">
    {visibleMessages.map((message, index) => <article className={`bubble-row ${message.role}`} key={`${message.role}-${message.key ?? message.timestamp}-${index}`}>
      {message.role === 'teacher' && <div className="avatar" aria-hidden="true">L</div>}
      <div className="bubble"><span className="speaker"><span>{message.role === 'teacher' ? 'Luna' : 'Quang'}</span>{index === latestTeacherIndex && <VoiceLatency />}</span>{message.text && <p>{message.role === 'teacher' ? emphasizedText(teacherDisplayText(message.text)) : message.text}</p>}{message.role === 'teacher' && message.image_url && <img className="teacher-image-card" src={message.image_url} alt="Hình minh họa cho câu nói của Luna" loading="eager" />}</div>
    </article>)}
    <div ref={latestMessage} aria-hidden="true" />
  </div>;
}
