'use client';
import { FormEvent, useRef, useState } from 'react';
import type { ReactNode } from 'react';

export function Composer({ disabled, onSend, voiceControls }: { disabled: boolean; onSend(text: string): Promise<void>; voiceControls?: ReactNode }) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  async function submit(event: FormEvent) {
    event.preventDefault(); const value = text.trim(); if (!value || disabled) return;
    setText(''); inputRef.current?.focus(); await onSend(value);
  }
  return <form className="composer" onSubmit={submit}>
    <label className="sr-only" htmlFor="learner-message">Your answer</label>
    <input ref={inputRef} id="learner-message" value={text} onChange={(event) => setText(event.target.value)} placeholder="Type what Quang says…" autoComplete="off" />
    {voiceControls}
    {disabled && <span className="composer-status" role="status">Luna đang nghĩ<span aria-hidden="true">…</span></span>}
    <button type="submit" aria-label="Send" disabled={disabled || !text.trim()}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6" /></svg></button>
  </form>;
}
