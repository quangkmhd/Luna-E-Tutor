export type Message = {
  role: 'learner' | 'teacher';
  text: string;
  turn_id?: string | null;
  image_url?: string | null;
};

export type VocabularyCard = {
  word: string;
  pronunciation?: string | null;
  meaning_vi?: string | null;
  image_url?: string | null;
};

export type UnitSummary = {
  id: string;
  grade: number;
  unit: number;
  title: string;
};

export type LessonSummary = { lesson: number; title: string };

export type SessionView = {
  session_id: string;
  unit_id: string;
  lesson_id?: number | null;
  unit: UnitSummary;
  state_version: number;
  stage_id: string;
  activity_id?: string | null;
  objective_id?: string | null;
  flashcards: VocabularyCard[];
  status: 'active' | 'paused' | 'completed' | 'abandoned';
  messages: Message[];
};

export type TurnInput = {
  turn_id: string;
  expected_state_version: number;
  learner_text: string;
};

export type TurnResponse = { turn_id: string; session: SessionView };
