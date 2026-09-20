'use client';

import Link from 'next/link';
import { useState } from 'react';

import { ChatPanel } from '@/components/ChatPanel';
import { PipecatVoiceProvider } from '@/components/voice/PipecatVoiceProvider';
import { VoiceControls } from '@/components/voice/VoiceControls';

import styles from './talk.module.css';

const TOPICS = ['My hobbies', 'My family', 'School life', 'Food', 'Animals', 'Travel'];
const MAX_TOPIC_LENGTH = 120;

export function TalkRoom() {
  const [draftTopic, setDraftTopic] = useState('');
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const normalizedTopic = draftTopic.trim();

  function chooseTopic(topic: string) {
    setSelectedTopic(topic);
    setDraftTopic(topic);
  }

  function startRoom() {
    if (!normalizedTopic) return;
    setActiveTopic(normalizedTopic);
  }

  return (
    <main className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brand}>
          <div className="logo-mark">L</div>
          <div>
            <span>Luna</span>
            <small>English Tutor · Free Talk</small>
          </div>
        </div>
        <Link className="secondary-button" href="/">Back to Unit 1</Link>
      </header>

      {!activeTopic ? (
        <section className={styles.setup} aria-labelledby="talk-heading">
          <span className="eyebrow">Free Talk Room</span>
          <h1 id="talk-heading">What would you like to talk about?</h1>
          <p>Luna will share ideas, ask one question at a time, and help you keep speaking naturally.</p>

          <div className={styles.topics} role="group" aria-label="Suggested topics">
            {TOPICS.map((topic) => (
              <button
                aria-pressed={selectedTopic === topic}
                className={styles.topic}
                key={topic}
                onClick={() => chooseTopic(topic)}
                type="button"
              >
                {topic}
              </button>
            ))}
          </div>

          <label className={styles.label} htmlFor="custom-topic">Or enter another topic</label>
          <input
            autoComplete="off"
            className={styles.input}
            id="custom-topic"
            maxLength={MAX_TOPIC_LENGTH}
            onChange={(event) => {
              setDraftTopic(event.target.value);
              setSelectedTopic(null);
            }}
            placeholder="For example: My dream job"
            type="text"
            value={draftTopic}
          />
          <p className={styles.helper} aria-live="polite">
            {normalizedTopic ? `Ready to talk about ${normalizedTopic}.` : 'Choose or enter a topic to begin.'}
          </p>
          <button
            className={styles.start}
            disabled={!normalizedTopic}
            onClick={startRoom}
            type="button"
          >
            Start Free Talk
          </button>
        </section>
      ) : (
        <section className={styles.conversation}>
          <div className={styles.conversationHeading}>
            <div>
              <span className="eyebrow">Free Talk Room</span>
              <h1>Talking about {activeTopic}</h1>
            </div>
            <button className="secondary-button" onClick={() => setActiveTopic(null)} type="button">
              Change topic
            </button>
          </div>
          <PipecatVoiceProvider
            key={activeTopic}
            endpoint={process.env.NEXT_PUBLIC_TALK_PIPECAT_URL ?? 'http://localhost:7863'}
            requestBody={{ topic: activeTopic }}
          >
            <div className={styles.voiceRoom}>
              <ChatPanel messages={[]} />
              <div className={styles.controls}>
                <VoiceControls
                  startLabel="Start conversation"
                  stopLabel="Stop conversation"
                  onStopped={() => setActiveTopic(null)}
                />
              </div>
            </div>
          </PipecatVoiceProvider>
        </section>
      )}
    </main>
  );
}
