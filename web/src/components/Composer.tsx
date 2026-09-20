'use client';
import { FormEvent, useState } from 'react';
import type { ReactNode } from 'react';

export function Composer({ disabled, onSend, voiceControls }: { disabled: boolean; onSend(text: string): Promise<void>; voiceControls?: ReactNode }) {
  const [text, setText] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault(); const value = text.trim(); if (!value || disabled) return;
    setText(''); await onSend(value);
  }
  return <form className="composer" onSubmit={submit}>
    <label className="sr-only" htmlFor="learner-message">Your answer</label>
    <input id="learner-message" value={text} onChange={(event) => setText(event.target.value)} placeholder="Type what Quang says…" disabled={disabled} autoComplete="off" />
    {voiceControls}
    <button type="submit" disabled={disabled || !text.trim()}>{disabled ? 'Luna is thinking…' : 'Send'}</button>
  </form>;
}
