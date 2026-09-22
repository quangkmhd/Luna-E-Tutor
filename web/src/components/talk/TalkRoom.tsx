'use client';

import Link from 'next/link';
import { useState } from 'react';

import { ChatPanel } from '@/components/ChatPanel';
import { LearnerHeader } from '@/components/LearnerHeader';
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
    <main className={`${styles.shell} learner-app`}>
      <LearnerHeader subtitle="Gia sư tiếng Anh · Free Talk">
        <Link className={styles.backLink} href="/">Chọn Unit</Link>
      </LearnerHeader>
      <div className={styles.workspace}>
        <nav className={styles.topicRail} aria-label="Chủ đề Free Talk">
          <h2>Chọn chủ đề</h2>
          {!activeTopic ? TOPICS.map((topic) => <button
            aria-pressed={selectedTopic === topic}
            className={styles.topic}
            key={topic}
            onClick={() => chooseTopic(topic)}
            type="button"
          >{topic}</button>) : <div className={styles.currentTopic}><span>Đang trò chuyện</span><strong>{activeTopic}</strong></div>}
        </nav>
        {!activeTopic ? <section className={styles.setup} aria-label="Chọn chủ đề trò chuyện">
          <span className={styles.kicker}>FREE TALK ROOM</span>
          <h1 id="talk-heading">Con muốn nói về điều gì?</h1>
          <p>Luna sẽ cùng con trò chuyện từng câu một. Chọn một chủ đề bên trái hoặc nhập điều con thích.</p>
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
          <button className={styles.start} disabled={!normalizedTopic} onClick={startRoom} type="button">
            Start Free Talk
          </button>
        </section> : <section className={styles.conversation} aria-label="Phòng trò chuyện Luna">
          <div className={styles.conversationHeading}>
            <div><span className={styles.kicker}>FREE TALK ROOM</span><h1>Talking about {activeTopic}</h1></div>
            <button className={styles.changeTopic} onClick={() => setActiveTopic(null)} type="button">Change topic</button>
          </div>
          <PipecatVoiceProvider
            key={activeTopic}
            endpoint={process.env.NEXT_PUBLIC_TALK_PIPECAT_URL ?? 'http://localhost:7863'}
            requestBody={{ topic: activeTopic }}
          >
            <div className={styles.voiceRoom}>
              <ChatPanel messages={[]} />
              <div className={styles.controls}>
                <VoiceControls startLabel="Start conversation" stopLabel="Stop conversation"
                  onStopped={() => setActiveTopic(null)} />
              </div>
            </div>
          </PipecatVoiceProvider>
        </section>}
        <aside className={styles.guide}>
          <h2>Mẹo trò chuyện</h2>
          <p>Con có thể nói ngắn rồi kể thêm khi sẵn sàng.</p>
          <p>Nếu cần nghĩ một chút, con cứ thong thả. Luna sẽ chờ con.</p>
        </aside>
      </div>
    </main>
  );
}
