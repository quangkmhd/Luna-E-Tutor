import type { Message } from '@/lib/types';

export function ChatPanel({ messages }: { messages: Message[] }) {
  return <div className="chat-scroll" aria-live="polite" aria-label="Conversation with Luna">
    {messages.map((message, index) => <article className={`bubble-row ${message.role}`} key={`${message.turn_id ?? 'opening'}-${index}`}>
      {message.role === 'teacher' && <div className="avatar" aria-hidden="true">L</div>}
      <div className="bubble"><span className="speaker">{message.role === 'teacher' ? 'Luna' : 'Quang'}</span><p>{message.text}</p></div>
    </article>)}
  </div>;
}
