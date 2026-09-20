export type Message = {
  role: 'learner' | 'teacher';
  text: string;
  turn_id?: string | null;
  delivery_intent?: string | null;
};

export type Evidence = {
  response_kind: string;
  emotional_signals: string[];
  objective_evidence: Array<{
    objective_id: string;
    meaning_status: string;
    target_form_status: string;
    recast_needed: boolean;
    evidence_quote?: string | null;
    corrected_form?: string | null;
  }>;
  needs_clarification: boolean;
  ambiguity_reason?: string | null;
};

export type Decision = {
  feedback_action: string;
  progression_action: string;
  next_objective_id?: string | null;
  next_activity_id?: string | null;
  next_stage_id?: string | null;
  review_queue_add: string[];
  review_queue_remove: string[];
};

export type SessionView = {
  session_id: string;
  unit_id: string;
  state_version: number;
  stage_id: string;
  activity_id?: string | null;
  objective_id?: string | null;
  status: 'active' | 'paused' | 'completed' | 'abandoned';
  messages: Message[];
  review_queue: Array<{ objective_id: string; difficulty: string }>;
  objective_progress: Array<{ objective_id: string; independent_uses: number; supported_uses: number; needs_review: boolean }>;
  last_evidence?: Evidence | null;
  last_decision?: Decision | null;
  summary?: {
    demonstrated: string[];
    supported: string[];
    needs_review: string[];
    not_yet_observed: string[];
  } | null;
};

export type TurnInput = {
  turn_id: string;
  expected_state_version: number;
  learner_text: string;
};

export type TurnResponse = { turn_id: string; session: SessionView };

export type ComparisonBranch = {
  evaluator_model: string;
  teacher_output: string;
  evidence: Evidence;
  decision: Decision;
  planning_latency_ms: number;
  teacher_latency_ms: number;
  total_latency_ms: number;
};

export type ComparisonResult = {
  state_version: number;
  stage_id: string;
  activity_id?: string | null;
  learner_text: string;
  teacher_model: string;
  gemini: ComparisonBranch;
  jev: ComparisonBranch;
};
