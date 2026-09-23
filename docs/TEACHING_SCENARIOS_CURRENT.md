# Kịch bản Evaluator và Teacher: Lớp 3 so với Lớp 5

> Mỗi tình huống có output Evaluator thật và quyết định/request Teacher được tạo bởi code hiện tại. Lớp 5 dùng unit `grade05.unit01`; Lớp 3 dùng `grade03.unit01`, Lesson 1 “Hello”. Các lượt gọi Evaluator chạy qua OpenRouter với Jev ngày 2026-09-23, mỗi mẫu một lần. Teacher LLM không được gọi trong lần kiểm tra này; tài liệu ghi lại payload mà code tạo và liệu luồng runtime sẽ gọi Teacher hay phát script trực tiếp. Mỗi mẫu được chạy độc lập trên state đại diện cho đúng hoạt động hiện tại; đây không phải một phiên hội thoại liên tục có lịch sử nhiều lượt.

**Artifacts:** [output live Lớp 5](evaluation/evaluator-live-outputs-2026-09-23.json) · [Teacher request Lớp 5](evaluation/teacher-requests-from-live-evaluator-2026-09-23.json) · [output và request Lớp 3](evaluation/grade03-live-scenarios-2026-09-23.json).

## So sánh logic hiện tại

| Phần | Lớp 5 | Lớp 3 Lesson 1 |
|---|---|---|
| Điều phối | `TeachingEngine` + `TurnPlanner` dùng chung theo curriculum | `ScriptedLessonService` đi theo từng lượt thoại đã soạn trong lesson script |
| Khi đạt yêu cầu | Engine chọn hoạt động tiếp theo; Teacher LLM diễn đạt instruction/transition | Service chuyển sang câu script kế tiếp; `scripted_say` được phát trực tiếp, không gọi Teacher LLM |
| Khi cần hỗ trợ | Chọn nhánh từ `teacher-description-catalog.yaml`; Teacher LLM nói lại tự nhiên | Tạo request Teacher với criterion/script hiện tại; Teacher prompt Lớp 3 yêu cầu gợi ý ngắn và không phát lại cả lời dẫn |
| Số lượt thử | Do `max_attempts` và trạng thái hoạt động quyết định | Theo số attempts của cơ hội script; hết lượt thì sửa câu cũ rồi nối câu script kế tiếp |
| Prompt theo lớp | Teacher dùng prompt Grade 5 + shared | Teacher dùng prompt Grade 3 + shared |
| Evaluator đang chạy | Jev | Jev |

**Lưu ý về Evaluator:** `.env` hiện chọn `~typesafe/jev-latest`, nên lượt chạy live của cả hai lớp dùng cùng Jev rubric. Prompt riêng `grade-03/evaluator.yaml` chỉ được nạp khi chọn `GeminiEvaluator`; nó không điều khiển những output Jev trong tài liệu này. Grade 3 request dùng `activity_type: scripted_lesson` và tiêu chí chấp nhận lấy từ authored lesson script.

### So sánh điều đáng chú ý từ lượt chạy

- Câu trả lời đúng và câu ngắn đều được nhận diện đạt ở cả hai lớp. Tuy nhiên Grade 3 phát lời dạy tiếp theo đã soạn sẵn; Grade 5 tạo request để Teacher LLM diễn đạt bước tiếp theo.
- Lỗi cấu trúc ở mẫu Lớp 5 được đánh `recast`; mẫu câu Lớp 3 không đạt script criterion đi nhánh `offer_support` và Teacher được yêu cầu gợi ý/mời thử lại. Đây là khác biệt do luồng dạy theo script.
- Tín hiệu mệt ở Lớp 5 tạo `reassure` và giảm độ khó. Ở mẫu Lớp 3, Jev báo cảm xúc nhưng `ScriptedLessonService` vẫn chọn `redirect` nếu `response_kind` là `off_topic`; khi lời chào và cảm xúc cùng xuất hiện, script tiến tiếp và bỏ qua phản hồi cảm xúc. Cần xem lại nếu muốn cảm xúc luôn được ưu tiên.
- Một số lệch của Jev xuất hiện ở cả hai: câu sai loại bị `off_topic`, góp ý “nói chậm hơn” lại kèm `needs_clarification: true`, từ chối bị gộp với “không biết”. Với câu không diễn giải được, Lớp 5 trả `insufficient_data`; mẫu Lớp 3 trả `off_topic` cùng `wrong_semantic_category`.
- Đây là một lượt cho mỗi mẫu; kết quả cho thấy khác biệt đường đi và một số vấn đề cần rà, chưa đo độ ổn định qua nhiều lần.

## Lớp 5 — từng kịch bản

### 5.1. Học sinh trả lời đúng

**Học sinh:** “I live in the countryside.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "satisfied",
      "target_form_status": "correct_target_form",
      "evidence_quote": "I live in the countryside.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "move_to_next_objective",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-01.ask-luna",
  "next_objective_id": "unit01.lesson01.pattern.live_in",
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-01",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "acknowledge_and_continue",
  "corrected_form": null,
  "learner_meaning": "I live in the countryside.",
  "next_teaching_move": "After responding to Quang, invite HIM to ask YOU about the target topic; wait for his question. Do not answer on your own behalf yet, and do not ask him to answer the previous question again. Topic: Create an opportunity to ask Luna where she lives. If still difficult after support, record the opportunity as handled without claiming the learner asked.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.ask-luna",
    "kind": "ask_teacher",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": true,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": true,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.2. Trả lời ngắn nhưng đủ ý

**Học sinh:** “Countryside.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "satisfied",
      "target_form_status": "valid_alternative",
      "evidence_quote": "Countryside.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "move_to_next_objective",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-01.ask-luna",
  "next_objective_id": "unit01.lesson01.pattern.live_in",
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-02",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "acknowledge_and_continue",
  "corrected_form": null,
  "learner_meaning": "Countryside.",
  "next_teaching_move": "After responding to Quang, invite HIM to ask YOU about the target topic; wait for his question. Do not answer on your own behalf yet, and do not ask him to answer the previous question again. Topic: Create an opportunity to ask Luna where she lives. If still difficult after support, record the opportunity as handled without claiming the learner asked.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.ask-luna",
    "kind": "ask_teacher",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": true,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": true,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.3. Nhắc lại đúng từ mẫu

**Học sinh:** “City.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.vocabulary.city",
      "meaning_status": "not_demonstrated",
      "target_form_status": "correct_target_form",
      "evidence_quote": "City.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": true,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-03",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "acknowledge_and_continue",
  "corrected_form": null,
  "learner_meaning": "City.",
  "next_teaching_move": "Quang said the current target successfully. Acknowledge that specific response briefly, then invite another learner turn on the SAME target. This is practice, not a correction: do not restart the introduction or introduce a new word. For vocabulary_introduction, give a DIRECT instruction to SAY the target word aloud, such as \"Say hi to your friend: hi!\" or \"Now greet me with hi: hi!\" Do not ask a yes/no question such as \"Can you use hi...?\", ask for a sentence, or invite an answer about whether he can do it. Use activity_context.successful_learner_repetitions and required_learner_repetitions to keep the remaining turns straight. Vary the acknowledgment and direct speaking instruction from previous_teacher_turn and recent_context. Give only one clear response opportunity.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Can you say “city”?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.introduce-city",
    "kind": "vocabulary_introduction",
    "objectives": [
      "Vocabulary: city"
    ],
    "target_words": [
      "city"
    ],
    "target_patterns": [],
    "examples": [
      "city"
    ],
    "model_repetitions": 2,
    "required_learner_repetitions": 3,
    "successful_learner_repetitions": 1,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.4. Sai ngữ pháp nhưng rõ ý

**Học sinh:** “I live countryside.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "satisfied",
      "target_form_status": "error_in_target_form",
      "evidence_quote": "I live countryside.",
      "recast_needed": true,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "recast",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-04",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "recast",
  "corrected_form": null,
  "learner_meaning": "I live countryside.",
  "next_teaching_move": "The target construction has an error. Do not call it correct. Give corrected_form once if supplied; otherwise model a minimal faithful correction using the target pattern and learner meaning. Ask Quang to try again using that form. Keep his facts unchanged.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.5. Sai loại đáp án

**Học sinh:** “Pink.”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson02.pattern.favourite",
      "meaning_status": "wrong_semantic_category",
      "target_form_status": "not_used",
      "evidence_quote": "Pink.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-05",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "Pink.",
  "next_teaching_move": "Respond to what Quang just said and continue this activity naturally: Ask about the favourite animal; accept any appropriate animal, not only the textbook example.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "What is your favourite animal?",
  "activity_context": {
    "stage_id": "lesson-02",
    "activity_id": "lesson-02.favourite-animal",
    "kind": "guided_response",
    "objectives": [
      "Vocabulary: dolphin",
      "Pattern: What's your favourite ___? – It's ___."
    ],
    "target_words": [
      "dolphin"
    ],
    "target_patterns": [
      "What's your favourite ___? – It's ___."
    ],
    "examples": [
      "What's your favourite animal? – It's a dolphin.",
      "What's your favourite colour? – It's pink.",
      "What's your favourite food? – It's a sandwich."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Evaluator trả `wrong_semantic_category` nhưng `response_kind: off_topic`; Engine vì thế đi nhánh redirect.

### 5.6. Trả lời đúng một phần

**Học sinh:** “I live...”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "partially_satisfied",
      "target_form_status": "not_used",
      "evidence_quote": "I live...",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": true,
  "ambiguity_reason": "Jev marked the learner input as unclear."
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "clarify",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-06",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "clarify",
  "corrected_form": null,
  "learner_meaning": "I live...",
  "next_teaching_move": "The input is not reliable enough to assess. Ask one short question to confirm what Quang meant, using the previous question for context. Do not treat a partial word as a successful answer, infer a pronunciation error, ask for imitation, or restart the activity introduction.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Grade 5 sample bị đánh `needs_clarification: true` dù ý nghĩa một phần được nhận diện.

### 5.7. Nói không biết

**Học sinh:** “I don't know.”

**Output Evaluator:**

```json
{
  "response_kind": "does_not_know",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-07",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "I don't know.",
  "next_teaching_move": "The answer did not meet the current goal. Do not say it was correct or praise it. Briefly explain the mismatch, then ask Quang to try again on the same question, with at most two concrete choices if helpful. Stay on the current objective.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.8. Sai ở lượt thử thứ hai

**Học sinh:** “Pink.”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson02.pattern.favourite",
      "meaning_status": "wrong_semantic_category",
      "target_form_status": "not_used",
      "evidence_quote": "Pink.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-08",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "Pink.",
  "next_teaching_move": "Respond to what Quang just said and continue this activity naturally: Ask about the favourite animal; accept any appropriate animal, not only the textbook example.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "What is your favourite animal?",
  "activity_context": {
    "stage_id": "lesson-02",
    "activity_id": "lesson-02.favourite-animal",
    "kind": "guided_response",
    "objectives": [
      "Vocabulary: dolphin",
      "Pattern: What's your favourite ___? – It's ___."
    ],
    "target_words": [
      "dolphin"
    ],
    "target_patterns": [
      "What's your favourite ___? – It's ___."
    ],
    "examples": [
      "What's your favourite animal? – It's a dolphin.",
      "What's your favourite colour? – It's pink.",
      "What's your favourite food? – It's a sandwich."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Evaluator trả `off_topic` lần nữa nên Engine không tiêu thụ lượt thử. Bộ đếm không tự sửa nhãn Evaluator.

### 5.9. Hỏi nghĩa từ

**Học sinh:** “What does city mean?”

**Output Evaluator:**

```json
{
  "response_kind": "asks_meaning",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.vocabulary.city",
      "meaning_status": "not_demonstrated",
      "target_form_status": "correct_target_form",
      "evidence_quote": "What does city mean?",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "explain_meaning",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-09",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "explain_meaning",
  "corrected_form": null,
  "learner_meaning": "What does city mean?",
  "next_teaching_move": "Explain the meaning Quang asked about with one concrete example. Check understanding with one easy meaning question or choice; do not ask him to repeat the word or restart the introduction.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Can you say “city”?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.introduce-city",
    "kind": "vocabulary_introduction",
    "objectives": [
      "Vocabulary: city"
    ],
    "target_words": [
      "city"
    ],
    "target_patterns": [],
    "examples": [
      "city"
    ],
    "model_repetitions": 2,
    "required_learner_repetitions": 3,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Model nhận đúng câu hỏi nghĩa nhưng do từ “city” xuất hiện trong lời hỏi, output vẫn đánh dấu `correct_target_form`.

### 5.10. Góp ý tốc độ của cô

**Học sinh:** “Can you speak more slowly?”

**Output Evaluator:**

```json
{
  "response_kind": "asks_teacher",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": true,
  "ambiguity_reason": "Jev marked the learner input as unclear."
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "clarify",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-10",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "clarify",
  "corrected_form": null,
  "learner_meaning": "Can you speak more slowly?",
  "next_teaching_move": "The input is not reliable enough to assess. Ask one short question to confirm what Quang meant, using the previous question for context. Do not treat a partial word as a successful answer, infer a pronunciation error, ask for imitation, or restart the activity introduction.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Câu hỏi rõ nghĩa nhưng output đồng thời yêu cầu làm rõ.

### 5.11. Nói lạc chủ đề

**Học sinh:** “I like playing Minecraft.”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-11",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "I like playing Minecraft.",
  "next_teaching_move": "Respond to what Quang just said and continue this activity naturally: Invite Quang to describe where he lives. Accept one-word or Vietnamese meaning; record English form separately.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.12. Thể hiện mệt mỏi

**Học sinh:** “I'm tired.”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [
    "emotional_signal_detected"
  ],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "reassure",
  "progression_action": "reduce_difficulty",
  "corrected_form": null,
  "emotional_support": true,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-12",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "reassure",
  "corrected_form": null,
  "learner_meaning": "I'm tired.",
  "next_teaching_move": "Briefly acknowledge any expressed feeling or confusion. Make the authorized activity easier with one question containing two concrete, simple answer choices. A one-word choice is enough; do not demand a full sentence, an abstract drawback explanation, or another attempt at the same difficult wording. If the learner gave the wrong semantic category, first explain that distinction briefly. Use the activity context for the CURRENT target, even after a transition. Do not re-ask a fact Quang already gave or repeat the previous question. Choose a missing part of the goal: if he already gave a drawback such as crowding, ask about a positive feature instead. For an addition goal, ask about another positive feature. Choices are possible answers, never asserted learner facts.",
  "scripted_say": null,
  "emotional_support": true,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.13. Từ chối trả lời

**Học sinh:** “I don't want to answer.”

**Output Evaluator:**

```json
{
  "response_kind": "does_not_know",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-13",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "I don't want to answer.",
  "next_teaching_move": "The answer did not meet the current goal. Do not say it was correct or praise it. Briefly explain the mismatch, then ask Quang to try again on the same question, with at most two concrete choices if helpful. Stay on the current objective.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Schema hiện gộp từ chối vào `does_not_know`.

### 5.14. Vừa trả lời vừa thể hiện cảm xúc

**Học sinh:** “I'm tired, but I live in a city.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [
    "emotional_signal_detected"
  ],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "satisfied",
      "target_form_status": "valid_alternative",
      "evidence_quote": "I'm tired, but I live in a city.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "reassure",
  "progression_action": "move_to_next_objective",
  "corrected_form": null,
  "emotional_support": true,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-01.ask-luna",
  "next_objective_id": "unit01.lesson01.pattern.live_in",
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-14",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "reassure",
  "corrected_form": null,
  "learner_meaning": "I'm tired, but I live in a city.",
  "next_teaching_move": "After responding to Quang, invite HIM to ask YOU about the target topic; wait for his question. Do not answer on your own behalf yet, and do not ask him to answer the previous question again. Topic: Create an opportunity to ask Luna where she lives. If still difficult after support, record the opportunity as handled without claiming the learner asked.",
  "scripted_say": null,
  "emotional_support": true,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.ask-luna",
    "kind": "ask_teacher",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": true,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.15. Transcript bị cắt

**Học sinh:** “I live in the”

**Output Evaluator:**

```json
{
  "response_kind": "insufficient_data",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "partially_satisfied",
      "target_form_status": "not_used",
      "evidence_quote": "I live in the",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": true,
  "ambiguity_reason": "Jev marked the learner input as unclear."
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "clarify",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-15",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "clarify",
  "corrected_form": null,
  "learner_meaning": "I live in the",
  "next_teaching_move": "The input is not reliable enough to assess. Ask one short question to confirm what Quang meant, using the previous question for context. Do not treat a partial word as a successful answer, infer a pronunciation error, ask for imitation, or restart the activity introduction.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

### 5.16. Lời nói không thể diễn giải

**Học sinh:** “Blue yesterday under maybe.”

**Output Evaluator:**

```json
{
  "response_kind": "insufficient_data",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "unit01.lesson01.pattern.live_in",
      "meaning_status": "wrong_semantic_category",
      "target_form_status": "not_used",
      "evidence_quote": "Blue yesterday under maybe.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": true,
  "ambiguity_reason": "Jev marked the learner input as unclear."
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "clarify",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo (user payload):**

```json
{
  "turn_id": "live-scenario-16",
  "unit_id": "grade05.unit01",
  "lesson_id": null,
  "feedback_action": "clarify",
  "corrected_form": null,
  "learner_meaning": "Blue yesterday under maybe.",
  "next_teaching_move": "The input is not reliable enough to assess. Ask one short question to confirm what Quang meant, using the previous question for context. Do not treat a partial word as a successful answer, infer a pronunciation error, ask for imitation, or restart the activity introduction.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "Where do you live?",
  "activity_context": {
    "stage_id": "lesson-01",
    "activity_id": "lesson-01.home",
    "kind": "guided_response",
    "objectives": [
      "Pattern: I live in the ___."
    ],
    "target_words": [],
    "target_patterns": [
      "I live in the ___."
    ],
    "examples": [
      "I live in the city.",
      "I live in the countryside."
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": [
      "Ask Quang to try a correction again only when constraints.require_repetition is true; otherwise never require repetition.",
      "Speak one short, natural turn without Markdown.",
      "Never write isolated vocabulary repetitions as separate punctuated sentences such as \"Class. Class.\" unless the active activity instruction explicitly supplies a spoken lesson script. Otherwise embed and quote each lowercase target word naturally, for example, \"Here is our new word: “class”. Can you say “class”?\""
    ]
  }
}
```

**Điểm cần lưu ý:** Output có `wrong_semantic_category` nhưng cũng `insufficient_data`; cần kiểm tra tính nhất quán.

## Lớp 3 — từng kịch bản (Lesson 1: Hello)

### 3.1. Học sinh trả lời đúng

**Học sinh:** “Hi!”

**Cơ hội trong script:** `greeting` — tiêu chí: “Con đáp lại bằng Hi hoặc Hello; có thể gọi tên cô Luna. Một câu chào ngắn cũng đạt.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-01.objective-01",
      "meaning_status": "satisfied",
      "target_form_status": "correct_target_form",
      "evidence_quote": "Hi!",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "move_to_next_stage",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-02.exchange-01",
  "next_objective_id": "lesson-02.objective-01",
  "next_stage_id": "vocabulary"
}
```

**Đường phát lời:** không gọi Teacher LLM; runtime phát `scripted_say` nguyên văn:

```text
<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>
<en>[long pause] "HELLO"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>
<en>[long pause] Listen first! [long pause] "HELLO" </en>
<en>[long pause] Your turn now! Can you say: [long pause] [slowly] "Hello"?</en>
```

### 3.2. Trả lời ngắn nhưng đủ ý

**Học sinh:** “Hello.”

**Cơ hội trong script:** `greeting` — tiêu chí: “Con đáp lại bằng Hi hoặc Hello; có thể gọi tên cô Luna. Một câu chào ngắn cũng đạt.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-01.objective-01",
      "meaning_status": "satisfied",
      "target_form_status": "correct_target_form",
      "evidence_quote": "Hello.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "move_to_next_stage",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-02.exchange-01",
  "next_objective_id": "lesson-02.objective-01",
  "next_stage_id": "vocabulary"
}
```

**Đường phát lời:** không gọi Teacher LLM; runtime phát `scripted_say` nguyên văn:

```text
<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>
<en>[long pause] "HELLO"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>
<en>[long pause] Listen first! [long pause] "HELLO" </en>
<en>[long pause] Your turn now! Can you say: [long pause] [slowly] "Hello"?</en>
```

### 3.3. Nhắc lại đúng từ mẫu

**Học sinh:** “Hello.”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "correct_target_form",
      "evidence_quote": "Hello.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "move_to_next_objective",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-02.exchange-02",
  "next_objective_id": "lesson-02.objective-02",
  "next_stage_id": null
}
```

**Đường phát lời:** không gọi Teacher LLM; runtime phát `scripted_say` nguyên văn:

```text
<en>Once more! [long pause] "Hello" [long pause]</en>
```

### 3.4. Sai ngữ pháp nhưng rõ ý

**Học sinh:** “Hi. I Mai.”

**Cơ hội trong script:** `patterns` — tiêu chí: “Hi/Hello + I'm + Mai”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-08.objective-01",
      "meaning_status": "partially_satisfied",
      "target_form_status": "error_in_target_form",
      "evidence_quote": "Hi. I Mai.",
      "recast_needed": true,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-04",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "Hi. I Mai.",
  "next_teaching_move": "The learner has not yet met the current lesson criterion. Give one short, concrete model or hint from activity_context and invite one retry of the current target. Do not repeat the entire introduction in previous_teacher_turn. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>",
  "activity_context": {
    "stage_id": "patterns",
    "activity_id": "lesson-08.exchange-01",
    "kind": "scripted_practice",
    "objectives": [
      "Hi/Hello + I'm + Mai"
    ],
    "target_words": [],
    "target_patterns": [
      "Hello./Hi. I'm {name}."
    ],
    "examples": [
      "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.5. Sai loại đáp án

**Học sinh:** “Pink.”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "wrong_semantic_category",
      "target_form_status": "not_used",
      "evidence_quote": "Pink.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-05",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "Pink.",
  "next_teaching_move": "Gently return to the same scripted response. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.6. Trả lời đúng một phần

**Học sinh:** “Hi.”

**Cơ hội trong script:** `patterns` — tiêu chí: “Hi/Hello + I'm + Mai”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-08.objective-01",
      "meaning_status": "partially_satisfied",
      "target_form_status": "not_used",
      "evidence_quote": "Hi.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-06",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "Hi.",
  "next_teaching_move": "The learner has not yet met the current lesson criterion. Give one short, concrete model or hint from activity_context and invite one retry of the current target. Do not repeat the entire introduction in previous_teacher_turn. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>",
  "activity_context": {
    "stage_id": "patterns",
    "activity_id": "lesson-08.exchange-01",
    "kind": "scripted_practice",
    "objectives": [
      "Hi/Hello + I'm + Mai"
    ],
    "target_words": [],
    "target_patterns": [
      "Hello./Hi. I'm {name}."
    ],
    "examples": [
      "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.7. Nói không biết

**Học sinh:** “I don't know.”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "does_not_know",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-07",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "I don't know.",
  "next_teaching_move": "The learner has not yet met the current lesson criterion. Give one short, concrete model or hint from activity_context and invite one retry of the current target. Do not repeat the entire introduction in previous_teacher_turn. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.8. Sai ở lượt thử thứ hai

**Học sinh:** “Hi. I Mai.”

**Cơ hội trong script:** `patterns` — tiêu chí: “Hi/Hello + I'm + Mai”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-08.objective-01",
      "meaning_status": "partially_satisfied",
      "target_form_status": "error_in_target_form",
      "evidence_quote": "Hi. I Mai.",
      "recast_needed": true,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "move_to_next_objective",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": true,
  "next_activity_id": "lesson-08.exchange-02",
  "next_objective_id": "lesson-08.objective-02",
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-08",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "Hi. I Mai.",
  "next_teaching_move": "The learner has used the allowed attempts on the current lesson line. Correct the OLD answer in one brief declarative sentence. Compare learner_meaning with the authored model in activity_context.examples and use recent_context to understand the learner's previous attempts. State the complete correct word or sentence for that old exercise, preserving its example name. This is a correction, not another speaking task: do not say \"Let's say\", \"Can you say\", \"Now you\", or ask the learner to repeat it. Do not praise the incorrect answer, claim to have heard pronunciation details from text, or restart the introduction. Stop after the correction; the next authored lesson line, possibly with a different name or target, will be appended exactly afterward. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>",
  "activity_context": {
    "stage_id": "patterns",
    "activity_id": "lesson-08.exchange-01",
    "kind": "scripted_practice",
    "objectives": [
      "Hi/Hello + I'm + Mai"
    ],
    "target_words": [],
    "target_patterns": [
      "Hello./Hi. I'm {name}."
    ],
    "examples": [
      "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 0,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

**Điểm cần lưu ý:** lượt thứ hai kích hoạt `support_limit_exit`; Teacher được yêu cầu sửa đáp án cũ, sau đó code nối script kế tiếp.

### 3.9. Hỏi nghĩa từ

**Học sinh:** “What does hello mean?”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "asks_meaning",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "explain_meaning",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-09",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "explain_meaning",
  "corrected_form": null,
  "learner_meaning": "What does hello mean?",
  "next_teaching_move": "Answer the learner question briefly, then invite the same scripted response. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.10. Góp ý tốc độ của cô

**Học sinh:** “Can you speak more slowly?”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "asks_teacher",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": true,
  "ambiguity_reason": "Jev marked the learner input as unclear."
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "clarify",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-10",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "clarify",
  "corrected_form": null,
  "learner_meaning": "Can you speak more slowly?",
  "next_teaching_move": "Ask for a clear repeat because the input was uncertain; do not call it wrong. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

**Điểm cần lưu ý:** output nhận diện `asks_teacher` nhưng đồng thời bật làm rõ; vì `needs_clarification` được xử lý trước, TeachingDecision thành `clarify`.

### 3.11. Nói lạc chủ đề

**Học sinh:** “I like playing Minecraft.”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-11",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "I like playing Minecraft.",
  "next_teaching_move": "Gently return to the same scripted response. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.12. Thể hiện mệt mỏi

**Học sinh:** “I'm tired.”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [
    "emotional_signal_detected"
  ],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-12",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "I'm tired.",
  "next_teaching_move": "Gently return to the same scripted response. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

**Điểm cần lưu ý:** cảm xúc được phát hiện, nhưng vì `response_kind` là `off_topic`, script chọn `redirect` thay vì nhánh trấn an.

### 3.13. Từ chối trả lời

**Học sinh:** “I don't want to answer.”

**Cơ hội trong script:** `vocabulary` — tiêu chí: “hello (có /h/)”

**Output Evaluator:**

```json
{
  "response_kind": "does_not_know",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-02.objective-01",
      "meaning_status": "not_demonstrated",
      "target_form_status": "not_used",
      "evidence_quote": null,
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "offer_support",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": true,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-13",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "offer_support",
  "corrected_form": null,
  "learner_meaning": "I don't want to answer.",
  "next_teaching_move": "The learner has not yet met the current lesson criterion. Give one short, concrete model or hint from activity_context and invite one retry of the current target. Do not repeat the entire introduction in previous_teacher_turn. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>",
  "activity_context": {
    "stage_id": "vocabulary",
    "activity_id": "lesson-02.exchange-01",
    "kind": "vocabulary_introduction",
    "objectives": [
      "hello (có /h/)"
    ],
    "target_words": [
      "hello"
    ],
    "target_patterns": [],
    "examples": [
      "<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>\n<en>[long pause] \"HELLO\"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>\n<en>[long pause] Listen first! [long pause] \"HELLO\" </en>\n<en>[long pause] Your turn now! Can you say: [long pause] [slowly] \"Hello\"?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": true,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

**Điểm cần lưu ý:** từ chối bị gộp thành `does_not_know`, nên code đưa hỗ trợ cho câu chưa biết.

### 3.14. Vừa trả lời vừa thể hiện cảm xúc

**Học sinh:** “Hi! I'm tired.”

**Cơ hội trong script:** `greeting` — tiêu chí: “Con đáp lại bằng Hi hoặc Hello; có thể gọi tên cô Luna. Một câu chào ngắn cũng đạt.”

**Output Evaluator:**

```json
{
  "response_kind": "answer",
  "emotional_signals": [
    "emotional_signal_detected"
  ],
  "objective_evidence": [
    {
      "objective_id": "lesson-01.objective-01",
      "meaning_status": "satisfied",
      "target_form_status": "correct_target_form",
      "evidence_quote": "Hi! I'm tired.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "acknowledge_and_continue",
  "progression_action": "move_to_next_stage",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": "lesson-02.exchange-01",
  "next_objective_id": "lesson-02.objective-01",
  "next_stage_id": "vocabulary"
}
```

**Đường phát lời:** không gọi Teacher LLM; runtime phát `scripted_say` nguyên văn:

```text
<vi>Cô trò mình sang Trạm 1 học từ mới. Mỗi từ, cô nói nghĩa rồi đọc trước, con đọc theo cô nhé!</vi>
<en>[long pause] "HELLO"</en><vi> nghĩa là xin chào, con nói khi gặp bất kỳ ai bạn bè, thầy cô, hay cô Luna .</vi>
<en>[long pause] Listen first! [long pause] "HELLO" </en>
<en>[long pause] Your turn now! Can you say: [long pause] [slowly] "Hello"?</en>
```

**Điểm cần lưu ý:** Evaluator phát hiện cảm xúc nhưng script vẫn chấp nhận câu trả lời và chuyển sang lời thoại kế tiếp; không tạo phản hồi cảm xúc riêng.

### 3.15. Transcript bị cắt

**Học sinh:** “Hi. I”

**Cơ hội trong script:** `patterns` — tiêu chí: “Hi/Hello + I'm + Mai”

**Output Evaluator:**

```json
{
  "response_kind": "insufficient_data",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-08.objective-01",
      "meaning_status": "partially_satisfied",
      "target_form_status": "error_in_target_form",
      "evidence_quote": "Hi. I",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": true,
  "ambiguity_reason": "Jev marked the learner input as unclear."
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "clarify",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-15",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "clarify",
  "corrected_form": null,
  "learner_meaning": "Hi. I",
  "next_teaching_move": "Ask for a clear repeat because the input was uncertain; do not call it wrong. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>",
  "activity_context": {
    "stage_id": "patterns",
    "activity_id": "lesson-08.exchange-01",
    "kind": "scripted_practice",
    "objectives": [
      "Hi/Hello + I'm + Mai"
    ],
    "target_words": [],
    "target_patterns": [
      "Hello./Hi. I'm {name}."
    ],
    "examples": [
      "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

### 3.16. Lời nói không thể diễn giải

**Học sinh:** “Blue yesterday under maybe.”

**Cơ hội trong script:** `patterns` — tiêu chí: “Hi/Hello + I'm + Mai”

**Output Evaluator:**

```json
{
  "response_kind": "off_topic",
  "emotional_signals": [],
  "objective_evidence": [
    {
      "objective_id": "lesson-08.objective-01",
      "meaning_status": "wrong_semantic_category",
      "target_form_status": "not_used",
      "evidence_quote": "Blue yesterday under maybe.",
      "recast_needed": false,
      "corrected_form": null
    }
  ],
  "needs_clarification": false,
  "ambiguity_reason": null
}
```

**TeachingDecision:**

```json
{
  "feedback_action": "redirect",
  "progression_action": "stay",
  "corrected_form": null,
  "emotional_support": false,
  "count_attempt": false,
  "count_successful_repetition": false,
  "support_limit_exit": false,
  "next_activity_id": null,
  "next_objective_id": null,
  "next_stage_id": null
}
```

**TeacherTurnRequest được tạo; runtime sẽ gọi Teacher LLM:**

```json
{
  "turn_id": "g3-live-scenario-16",
  "unit_id": "grade03.unit01",
  "lesson_id": 1,
  "feedback_action": "redirect",
  "corrected_form": null,
  "learner_meaning": "Blue yesterday under maybe.",
  "next_teaching_move": "Gently return to the same scripted response. The learner is practicing a scripted line, not greeting you. Respond to the current question or difficulty without restarting the greeting.",
  "scripted_say": null,
  "emotional_support": false,
  "previous_teacher_turn": "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>",
  "activity_context": {
    "stage_id": "patterns",
    "activity_id": "lesson-08.exchange-01",
    "kind": "scripted_practice",
    "objectives": [
      "Hi/Hello + I'm + Mai"
    ],
    "target_words": [],
    "target_patterns": [
      "Hello./Hi. I'm {name}."
    ],
    "examples": [
      "<vi>Có từ rồi, giờ cô trò mình ghép từ thành câu — con sẽ biết nói câu này vào lúc nào. [long pause]</vi>\n<vi>Khi gặp một bạn mới, con chào rồi nói tên của con. </vi><en>Listen first! [long pause] \"Hi. I'm Mai.\" [long pause]</en>\n<en>Your turn now! Can you say: [long pause] \"Hi. I'm Mai.\" [long pause]?</en>"
    ],
    "model_repetitions": 0,
    "required_learner_repetitions": 1,
    "successful_learner_repetitions": 0,
    "remaining_model_repetitions": 0,
    "needs_response_invitation": false,
    "delivery_only": false,
    "role_name": null,
    "role_country": null
  },
  "review_objective": null,
  "recent_context": [],
  "constraints": {
    "max_questions": 1,
    "require_repetition": false,
    "allow_pronunciation_claims": false,
    "plain_spoken_text": true,
    "encouragement_required": false,
    "additional": []
  }
}
```

**Điểm cần lưu ý:** Jev gọi câu khó hiểu là `off_topic` và `wrong_semantic_category`, không xin làm rõ như mẫu Lớp 5.

## Prompt Teacher được ghép theo lớp

- **Lớp 5:** [grade-05/teacher.yaml](../backend/src/luna_tutor/prompts/grades/grade-05/teacher.yaml) rồi đến [shared/teacher.yaml](../backend/src/luna_tutor/prompts/shared/teacher.yaml).
- **Lớp 3:** [grade-03/teacher.yaml](../backend/src/luna_tutor/prompts/grades/grade-03/teacher.yaml) rồi đến [shared/teacher.yaml](../backend/src/luna_tutor/prompts/shared/teacher.yaml).
- Cách ghép này do `load_grade_system_prompt()` thực hiện. Teacher nhận system prompt đã ghép và `TeacherTurnRequest` JSON làm user message.
- Với Lớp 3 script, các lượt đạt tiêu chí dùng `scripted_say` và không gọi model Teacher; payload thể hiện rõ `teacher_llm_called: false` trong JSON raw.

## Các tình huống không gọi LLM Evaluator

- **Im lặng:** được backend tạo thành `no_response`; không có lượt gọi Evaluator.
- **Thông tin liên hệ nhạy cảm:** được lọc trước Evaluator; xử lý bởi lớp riêng tư.
