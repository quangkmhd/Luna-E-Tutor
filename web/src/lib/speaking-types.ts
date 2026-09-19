export type Topic = {id: string; name_en: string; name_vi: string; scenario: string; words: string[]};
export type Config = {grade: 5; topic: string; words: string[]};
export type WordUse = {word: string; quote: string; independent: boolean};
export type SpeakingState = {session_id: string; config: Config; version: number; status: 'active'|'completed'; level: number; independent_streak: number; difficulty_streak: number; word_evidence: WordUse[]; last_delivered_text: string; opening_message: string; messages: {role: 'learner'|'teacher'; text: string; turn_id?: string}[]};
export type Reply = {text: string; support_kind: string};
export type TurnResult = {state: SpeakingState; reply: Reply};
export type Summary = {state: SpeakingState; independent: string[]; supported: string[]; unseen: string[]; next_practice: string};
export type Suggestions = {topic: string; words: {word: string; meaning_vi: string; example: string}[]; clarification: string|null};
