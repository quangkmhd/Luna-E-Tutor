import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { usePipecatConversation } from '@pipecat-ai/client-react';
import type { BotOutputText, ConversationMessage } from '@pipecat-ai/client-react';
import type { Message } from '@/lib/types';
import { VoiceLatency } from './voice/VoiceLatency';
import { useOptionalVoiceLesson } from './voice/PipecatVoiceProvider';

type DisplayMessage = { role: 'learner' | 'teacher'; text: string; timestamp: string; key?: string; image_url?: string | null; turn_id?: string | null };

function emphasizedText(text: string) {
  return text.split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*)/g).map((part, index) => {
    const emphasis = part.match(/^\*\*([^*\n]+)\*\*$/) ?? part.match(/^\*([^*\n]+)\*$/);
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
  return text.replace(/(?<=\S)<\/(?:vi|en)><(?:vi|en)>(?=\S)/g, ' ')
    .replace(/<\/?(?:vi|en)>/g, '').replace(/\[[^\]]*\]/g, '').split(/\r?\n/)
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

function authoredStartIndex(spoken: string, authored: string): number {
  const spokenWords = teacherDisplayText(spoken).replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
  const authoredLead = speechKey(authored).split(' ').slice(0, 5);
  if (!authoredLead.length) return -1;
  const spokenKeys = spokenWords.map((word) => speechKey(word));
  for (let index = spokenKeys.length - 1; index >= 0; index--) {
    let matched = 0;
    while (matched < authoredLead.length && index + matched < spokenKeys.length) {
      const heard = spokenKeys[index + matched];
      const authoredWord = authoredLead[matched];
      if (!heard || (heard !== authoredWord && !(index + matched === spokenKeys.length - 1 && authoredWord.startsWith(heard)))) break;
      matched++;
    }
    if (matched && (matched === authoredLead.length || index + matched === spokenKeys.length)) return index;
  }
  return -1;
}

function trimSpokenToAuthoredStart(spoken: string, authored: string): string {
  const spokenWords = teacherDisplayText(spoken).replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
  const start = authoredStartIndex(spoken, authored);
  return start >= 0 ? spokenWords.slice(start).join(' ') : spokenWords.join(' ');
}

function authoredWordPrefix(text: string, count: number): string {
  const clean = teacherDisplayText(text);
  const words = [...clean.matchAll(/\S+/g)].filter(([word]) => /[\p{L}\p{N}]/u.test(word));
  if (count <= 0 || !words.length) return '';
  const lastWord = words[Math.min(count, words.length) - 1];
  return clean.slice(0, lastWord.index! + lastWord[0].length);
}

export function ChatPanel({ messages }: { messages: Message[] }) {
  const chatScroll = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const voice = useOptionalVoiceLesson();
  const [captionClock, setCaptionClock] = useState(0);
  useEffect(() => {
    if (!voice?.googleCaptionSegments?.length || voice.googleCaptionStartedAt === null) return;
    const timer = setInterval(() => setCaptionClock(Date.now()), 50);
    return () => clearInterval(timer);
  }, [voice?.googleCaptionSegments?.length, voice?.googleCaptionStartedAt]);
  const { messages: pipecatMessages } = usePipecatConversation({
    botOutputFilter: { spoken: true, unspoken: false },
  });
  const voiceRuns = voice?.voiceRuns ?? [];
  const spokenOnly = voiceRuns.length > 0;
  const imageCue = voice?.teacherImageCue;
  const lastUserIndex = pipecatMessages.findLastIndex((message) => message.role === 'user');
  const authoredKey = imageCue?.spoken_text ? speechKey(imageCue.spoken_text) : '';
  const matchesImageCue = (message: ConversationMessage) => {
    if (message.role !== 'assistant') return false;
    return Boolean(authoredKey && authoredStartIndex(conversationText(message, true), imageCue?.spoken_text ?? '') >= 0);
  };
  const cueAssistant = imageCue?.image_url && authoredKey
    ? pipecatMessages.slice(lastUserIndex + 1).findLast(matchesImageCue)
      ?? pipecatMessages.findLast(matchesImageCue)
    : undefined;
  const savedMessages = messages.flatMap((message, index) => {
    const precedingRun = voiceRuns.findLast((run) => run.end !== undefined && index >= run.end);
    return [{ ...message, key: `saved-${index}`, timestamp: precedingRun?.endedAt ?? '' }];
  });
  const googleSegments = voice?.googleCaptionSegments ?? [];
  const latestRun = voiceRuns.at(-1);
  const hasSpokenAssistant = pipecatMessages.some((message) => message.role === 'assistant'
    && conversationText(message, true));
  const waitingForProvider = voice?.ttsProvider == null && !hasSpokenAssistant;
  const googleRun = latestRun && (googleSegments.length || (latestRun.end === undefined
    && (voice?.ttsProvider === 'google' || waitingForProvider)))
    ? latestRun : undefined;
  const playbackMs = (voice?.googleCaptionPlaybackBaseMs ?? 0)
    + (voice?.googleCaptionStartedAt === null || voice?.googleCaptionStartedAt === undefined
      ? 0 : Math.max(0, captionClock - voice.googleCaptionStartedAt));
  let segmentOffsetMs = 0;
  const captionSources: Array<{ id: number; sourceText: string; text: string; receivedAt: string }> = [];
  for (const segment of googleSegments) {
    const playedMs = Math.max(0, Math.min(segment.audioMs, playbackMs - segmentOffsetMs));
    segmentOffsetMs += segment.audioMs;
    const words = teacherDisplayText(segment.segmentText).split(/\s+/).filter(Boolean);
    const isVietnamese = /[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]/i.test(segment.segmentText);
    const estimated = playedMs > 0 ? Math.max(1, Math.floor(playedMs / (isVietnamese ? 300 : 380))) : 0;
    const count = segment.finished && segment.audioMs > 0 && playedMs >= segment.audioMs
      ? words.length : Math.min(words.length, estimated);
    let source = captionSources.find((item) => item.id === segment.sourceId);
    if (!source) {
      source = { id: segment.sourceId, sourceText: segment.sourceText, text: '', receivedAt: segment.receivedAt };
      captionSources.push(source);
    }
    const priorWords = source.text ? source.text.split(/\s+/).filter((word) => /[\p{L}\p{N}]/u.test(word)).length : 0;
    source.text = authoredWordPrefix(segment.sourceText, priorWords + count);
  }
  const runStart = googleRun?.start ?? savedMessages.length;
  const runEnd = googleRun?.end ?? savedMessages.length;
  const lastLearnerBeforeRun = savedMessages.slice(0, runStart).findLastIndex((message) => message.role === 'learner');
  const replayIndex = googleRun && runStart > 0 && savedMessages[runStart - 1]?.role === 'teacher'
    && runStart - 1 > lastLearnerBeforeRun ? runStart - 1 : -1;
  const replayMatched = replayIndex >= 0 && captionSources.length > 0
    && speechKey(captionSources[0].sourceText) === speechKey(savedMessages[replayIndex].text);
  const sourceOffset = replayMatched ? 1 : 0;
  const savedGoogleTeacherCount = savedMessages.slice(runStart, runEnd)
    .filter((message) => message.role === 'teacher').length;
  let googleTeacherIndex = 0;
  const shownSavedMessages = savedMessages.map((message, index) => {
    if (index === replayIndex && (!captionSources.length || replayMatched)) {
      return { ...message, text: captionSources[0]?.text ?? '' };
    }
    if (!googleRun || index < runStart || index >= runEnd || message.role !== 'teacher') return message;
    return { ...message, text: captionSources[sourceOffset + googleTeacherIndex++]?.text ?? '' };
  });
  const googleLiveMessages: DisplayMessage[] = captionSources.slice(sourceOffset + savedGoogleTeacherCount)
    .filter((source) => source.text).map((source) => ({
      role: 'teacher', text: source.text, timestamp: source.receivedAt,
      key: `google-caption-${source.id}`,
    }));
  const pipecatConversation: DisplayMessage[] = pipecatMessages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .flatMap((message) => message.role === 'user' && voice?.manualSubmit
      ? (() => {
        const parts = message.parts.map((part) => conversationText({ ...message, parts: [part] }, false));
        const segments: DisplayMessage[] = [];
        for (let start = 0; start < parts.length;) {
          const savedEnd = parts.findIndex((_, end) => end >= start && savedMessages.some((saved) =>
            saved.role === 'learner' && saved.text === parts.slice(start, end + 1).join(' ').trim()));
          const end = savedEnd >= 0 ? savedEnd + 1 : parts.length;
          segments.push({
            role: 'learner', text: parts.slice(start, end).join(' ').trim(),
            timestamp: message.parts[start].createdAt ?? message.createdAt,
            key: `${message.createdAt}-part-${start}`,
          });
          start = end;
        }
        return segments;
      })()
      : message.role === 'assistant' && spokenOnly
      ? (message === cueAssistant && imageCue?.spoken_text
        ? spokenAuthoredLines(
          trimSpokenToAuthoredStart(conversationText(message, true), imageCue.spoken_text),
          imageCue.spoken_text,
        )
        : [conversationText(message, true)]).flatMap((text, index) => text
        ? [{
          role: 'teacher' as const, text,
          timestamp: message === cueAssistant ? imageCue?.receivedAt ?? message.createdAt : message.createdAt,
          key: `${message.createdAt}-line-${index}`,
        }]
        : [])
      : [{
        role: message.role === 'user' ? 'learner' as const : 'teacher' as const,
        text: conversationText(message, spokenOnly),
        timestamp: message.createdAt,
      }])
    .filter((message) => message.text);
  const sentText = voice?.sentText ?? [];
  const liveMessages = (messages.length === 0 ? pipecatConversation : pipecatConversation.flatMap((message, index) => {
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
  })).filter((message) => !googleRun || message.role !== 'teacher');
  const savedCue = Boolean(imageCue?.image_url && (
    (imageCue.turn_id && savedMessages.some((message) =>
      message.role === 'teacher' && message.turn_id === imageCue.turn_id))
    || (authoredKey && savedMessages.some((message) =>
      message.role === 'teacher' && message.image_url === imageCue.image_url
      && speechKey(message.text) === authoredKey))
  ));
  const pendingImage: DisplayMessage[] = imageCue?.image_url && !savedCue
    ? [{
      role: 'teacher', text: '', timestamp: imageCue.receivedAt,
      key: `image-${imageCue.turn_id ?? imageCue.receivedAt}`,
      turn_id: imageCue.turn_id, image_url: imageCue.image_url,
    }]
    : [];
  const displayedMessages: DisplayMessage[] = [...shownSavedMessages, ...liveMessages, ...googleLiveMessages, ...pendingImage, ...sentText.filter((message, index) =>
    savedMessages.filter((saved) => saved.role === 'learner' && saved.text === message.text).length
      < sentText.slice(0, index + 1).filter((sent) => sent.text === message.text).length,
  ).map((message) => ({
    role: 'learner' as const,
    text: message.text,
    timestamp: message.timestamp,
    key: `sent-${message.id}`,
  }))].sort((left, right) => {
    const leftTime = Date.parse(left.timestamp);
    const rightTime = Date.parse(right.timestamp);
    const timeOrder = (Number.isNaN(leftTime) ? 0 : leftTime) - (Number.isNaN(rightTime) ? 0 : rightTime);
    if (timeOrder) return timeOrder;
    return Number(Boolean(right.key?.startsWith('image-'))) - Number(Boolean(left.key?.startsWith('image-')));
  });
  const visibleMessages = displayedMessages.flatMap((message) => message.role === 'teacher'
    ? [
      ...(message.image_url ? [{
        ...message, text: '',
        key: message.turn_id ? `image-${message.turn_id}` : message.key?.startsWith('image-')
          ? message.key : `image-${message.key ?? message.timestamp}`,
      }] : []),
      ...teacherDisplayText(message.text).split('\n').filter(Boolean).map((line, index) => ({
        ...message, image_url: null,
        text: line, key: `${message.key ?? message.timestamp}-line-${index}`,
      })),
    ]
    : [message]);
  const latestTeacherIndex = visibleMessages.findLastIndex((message) => message.role === 'teacher' && message.text);
  useLayoutEffect(() => {
    if (followLatest.current && chatScroll.current) chatScroll.current.scrollTop = chatScroll.current.scrollHeight;
  });
  return <div ref={chatScroll} className="chat-scroll" aria-live="polite" aria-label="Conversation with Luna" onScroll={(event) => {
    const target = event.currentTarget;
    followLatest.current = target.scrollHeight - target.clientHeight - target.scrollTop < 40;
  }}>
    {visibleMessages.map((message, index) => <article className={`bubble-row ${message.role}${message.role === 'teacher' && message.image_url && !message.text ? ' image-only' : ''}`} key={`${message.role}-${message.key ?? message.timestamp}`}>
      {message.role === 'teacher' && <div className="avatar" aria-hidden="true">L</div>}
      <div className="bubble"><span className="speaker"><span>{message.role === 'teacher' ? 'Luna' : 'Quang'}</span>{index === latestTeacherIndex && <VoiceLatency />}</span>{message.text && <p>{message.role === 'teacher' ? emphasizedText(teacherDisplayText(message.text)) : message.text}</p>}{message.role === 'teacher' && message.image_url && <img className="teacher-image-card" src={message.image_url} alt="Hình minh họa cho câu nói của Luna" width={220} height={220} loading="eager" />}</div>
    </article>)}
  </div>;
}
