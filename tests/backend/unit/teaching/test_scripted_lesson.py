from pathlib import Path

import pytest

from luna_tutor.curriculum.lesson_script import LessonScript, load_lesson_script
from luna_tutor.domain.decisions import TeacherUtterance
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.teaching.scripted_lesson import ScriptedLessonService, _join_spoken


class Evaluator:
    def __init__(self):
        self.requests = []

    async def evaluate(self, request):
        self.requests.append(request)
        return EvaluatorResult(
            turn_id=request.turn_id, state_version=request.state_version,
            response_kind='answer', emotional_signals=[], needs_clarification=False,
            ambiguity_reason=None,
            objective_evidence=[ObjectiveEvidence(
                objective_id=request.active_objectives[0].objective_id,
                meaning_status='satisfied', target_form_status='valid_alternative',
                evidence_quote=request.learner_transcript, recast_needed=False,
                corrected_form=None,
            )],
        )


class Teacher:
    async def respond(self, request):
        return TeacherUtterance(spoken_text='Good work!', delivery_intent='encouraging')


def test_joined_teacher_turn_does_not_double_authored_long_pause():
    assert _join_spoken('Good work!', '[long pause] "Hi" [long pause]') == (
        'Good work! [long pause] "Hi" [long pause]')
    assert _join_spoken('Good work! [long pause]', '[long pause] "Hi" [long pause]') == (
        'Good work! [long pause] "Hi" [long pause]')


@pytest.mark.asyncio
async def test_recited_answer_delivers_only_the_next_authored_line():
    class UnwantedTeacher:
        async def respond(self, request):
            raise AssertionError('Teacher must not add a conversational response')

    service = ScriptedLessonService(script(), Evaluator(), UnwantedTeacher())
    state = service.fresh_state('session-repeated-greeting').model_copy(update={
        'script_index': 1, 'stage_id': 'vocabulary',
        'activity_id': 'lesson-02.exchange-01',
        'objective_id': 'lesson-02.objective-01',
        'last_teacher_turn': 'Say hello.',
    })
    completed = await service.process(state, 'Hello', 'turn-repeated-greeting')
    assert completed.teacher_utterance.spoken_text == 'Say hi.'
    assert completed.teacher_utterance.generation_mode == 'script'


def script():
    return LessonScript.model_validate({
        'lesson': 1, 'title': 'Hello',
        'greeting': {'order': 1, 'say': 'Hi, con!', 'accept': 'Chấp nhận Hi hoặc Hello.'},
        'words': ['hello', 'hi'], 'patterns': {},
        'stations': [
            {'id': 'vocabulary', 'steps': [
                {'order': 2, 'target': 'hello', 'say': 'Say hello.',
                 'accept': 'Chấp nhận hello; nói ngắn vẫn đạt.'},
                {'order': 3, 'target': 'hi', 'say': 'Say hi.', 'accept': 'Chấp nhận hi.'},
            ]},
            {'id': 'patterns', 'steps': [
                {'order': 4, 'say': 'Introduce yourself.', 'accept': 'Chấp nhận tên.',
                 'more': [{'say': 'Hi, {tên}!', 'accept': 'Chấp nhận đáp lại.'}]},
            ]},
            {'id': 'conversation', 'steps': [
                {'order': 5, 'say': 'Greet me.', 'accept': 'Chấp nhận lời chào.',
                 'more': [{'say': 'Good evening, {tên}!'}]},
            ]},
        ],
    })


@pytest.mark.asyncio
async def test_scripted_session_sends_accept_to_evaluator_and_delivers_next_text():
    evaluator = Evaluator()
    service = ScriptedLessonService(script(), evaluator, Teacher())
    state = service.fresh_state('session-1')
    assert state.opening_message == 'Hi, con!'
    assert state.opening_script is None
    assert state.stage_id == 'greeting'
    completed = await service.process(state, 'Hello', 'turn-1')
    assert evaluator.requests[0].active_objectives[0].evidence_criteria == (
        'Chấp nhận Hi hoặc Hello.')
    assert completed.next_state.script_index == 1
    assert completed.next_state.stage_id == 'vocabulary'
    assert completed.teacher_utterance.spoken_text.endswith('Say hello.')


@pytest.mark.asyncio
async def test_substitutes_chosen_name_in_next_script_line():
    service = ScriptedLessonService(script(), Evaluator(), Teacher())
    state = service.fresh_state('session-2').model_copy(update={'script_index': 3,
        'stage_id': 'patterns', 'activity_id': 'lesson-04.exchange-01',
        'objective_id': 'lesson-04.objective-01',
        'last_teacher_turn': 'Introduce yourself.'})
    completed = await service.process(state, "Hi. I'm Nam.", 'turn-name')
    assert completed.next_state.script_name == 'Nam'
    assert completed.teacher_utterance.spoken_text.endswith('Hi, Nam!')


@pytest.mark.asyncio
async def test_word_imitation_counts_without_independent_meaning_claim():
    class ImitationEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'objective_evidence': [
                result.objective_evidence[0].model_copy(update={
                    'meaning_status': 'not_demonstrated',
                    'target_form_status': 'correct_target_form',
                })]})

    service = ScriptedLessonService(script(), ImitationEvaluator(), Teacher())
    state = service.fresh_state('session-imitation').model_copy(update={
        'script_index': 1, 'stage_id': 'vocabulary',
        'activity_id': 'lesson-02.exchange-01',
        'objective_id': 'lesson-02.objective-01',
        'last_teacher_turn': 'Say hello.',
    })
    completed = await service.process(state,
                                      'Hello', 'turn-imitation')
    assert completed.next_state.script_index == 2
    assert completed.teacher_utterance.spoken_text.endswith('Say hi.')


@pytest.mark.asyncio
async def test_wrong_answer_gets_one_retry_then_moves_without_false_praise():
    class RejectingEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'objective_evidence': [
                result.objective_evidence[0].model_copy(update={
                    'meaning_status': 'not_demonstrated',
                    'target_form_status': 'not_used',
                })]})

    class SupportTeacher:
        def __init__(self):
            self.requests = []

        async def respond(self, request):
            self.requests.append(request)
            text = ('Mình nhớ cả từ "hello" nhé.' if request.constraints.max_questions == 0
                    else 'Say "hello" once more.')
            return TeacherUtterance(spoken_text=text,
                                    delivery_intent='encouraging')

    teacher = SupportTeacher()
    service = ScriptedLessonService(script(), RejectingEvaluator(), teacher)
    state = service.fresh_state('session-wrong').model_copy(update={
        'script_index': 1, 'stage_id': 'vocabulary',
        'activity_id': 'lesson-02.exchange-01',
        'objective_id': 'lesson-02.objective-01',
        'last_teacher_turn': 'Say hello.',
    })
    first = await service.process(state, 'book', 'wrong-1')
    assert first.next_state.script_index == 1
    assert first.teacher_utterance.spoken_text == 'Say "hello" once more.'
    assert teacher.requests[0].activity_context is not None
    second = await service.process(first.next_state, 'book', 'wrong-2')
    assert second.next_state.script_index == 2
    assert second.teacher_utterance.spoken_text == 'Mình nhớ cả từ "hello" nhé. [long pause] Say hi.'
    assert len(teacher.requests) == 2
    assert teacher.requests[1].constraints.max_questions == 0
    assert [item.text for item in teacher.requests[1].recent_context[-2:]] == [
        'book', 'Say "hello" once more.']
    assert second.next_state.objective_progress == ()


@pytest.mark.asyncio
async def test_grade3_im_wrong_attempts_get_support_before_good_evening():
    path = (Path(__file__).resolve().parents[4]
            / 'curriculum/grade-03/unit-01/lesson-01/content.yaml')

    class RejectingEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'objective_evidence': [
                result.objective_evidence[0].model_copy(update={
                    'meaning_status': 'not_demonstrated',
                    'target_form_status': 'not_used',
                })]})

    class SupportTeacher:
        async def respond(self, request):
            text = ('Cả từ là "I’m" nhé.' if request.constraints.max_questions == 0
                    else 'Listen: "I’m". Now you.')
            return TeacherUtterance(spoken_text=text,
                                    delivery_intent='encouraging')

    service = ScriptedLessonService(load_lesson_script(path), RejectingEvaluator(), SupportTeacher())
    im_index = next(i for i, item in enumerate(service.opportunities) if item.target == "I'm")
    current = service.opportunities[im_index]
    state = service.fresh_state('session-im-support').model_copy(update={
        'script_index': im_index, 'stage_id': current.stage,
        'activity_id': current.activity_id, 'objective_id': current.objective_id,
        'last_teacher_turn': current.say,
    })
    first = await service.process(state, 'i', 'im-wrong-1')
    assert first.teacher_utterance.spoken_text == 'Listen: "I’m". Now you.'
    assert first.next_state.script_index == im_index

    second = await service.process(first.next_state, 'am', 'im-wrong-2')
    assert '"Good evening"' in second.teacher_utterance.spoken_text
    assert second.teacher_utterance.spoken_text.startswith('Cả từ là "I’m" nhé.')
    assert second.next_state.script_index == im_index + 1


@pytest.mark.asyncio
async def test_second_wrong_pattern_correction_precedes_next_authored_example():
    path = (Path(__file__).resolve().parents[4]
            / 'curriculum/grade-03/unit-01/lesson-01/content.yaml')

    class RejectingEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'objective_evidence': [
                result.objective_evidence[0].model_copy(update={
                    'meaning_status': 'partially_satisfied',
                    'target_form_status': 'error_in_target_form',
                })]})

    class CorrectingTeacher:
        def __init__(self):
            self.requests = []

        async def respond(self, request):
            self.requests.append(request)
            return TeacherUtterance(
                spoken_text='The correct sentence is "Hi. I\'m Mai."',
                delivery_intent='encouraging')

    teacher = CorrectingTeacher()
    service = ScriptedLessonService(load_lesson_script(path), RejectingEvaluator(), teacher)
    index = next(i for i, item in enumerate(service.opportunities)
                 if item.order == 8 and item.exchange == 1)
    current = service.opportunities[index]
    state = service.fresh_state('session-pattern-correction').model_copy(update={
        'script_index': index, 'stage_id': current.stage,
        'activity_id': current.activity_id, 'objective_id': current.objective_id,
        'last_teacher_turn': current.say, 'attempt_count': 1,
    })
    completed = await service.process(state, 'hi i is mai', 'pattern-wrong-2')
    assert completed.plan.decision.support_limit_exit
    assert 'brief declarative sentence' in teacher.requests[0].next_teaching_move
    assert teacher.requests[0].activity_context.examples == (current.say,)
    assert completed.teacher_utterance.spoken_text.startswith(
        'The correct sentence is "Hi. I\'m Mai." [long pause] Listen first!')
    assert '"Hello. I\'m Minh."' in completed.teacher_utterance.spoken_text


@pytest.mark.asyncio
async def test_silence_advances_without_workbook_hint():
    service = ScriptedLessonService(script(), Evaluator(), Teacher())
    completed = await service.process(service.fresh_state('session-silent'), '', 'silent-1',
                                      input_event='no_response')
    assert completed.next_state.script_index == 1
    assert completed.plan.evidence.response_kind == 'no_response'
    assert completed.teacher_utterance.spoken_text.endswith('Say hello.')


@pytest.mark.asyncio
async def test_uncertain_transcript_does_not_consume_attempt_or_advance():
    class UncertainEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={
                'response_kind': 'insufficient_data', 'needs_clarification': True,
                'ambiguity_reason': 'Transcript is uncertain.', 'objective_evidence': [],
            })

    service = ScriptedLessonService(script(), UncertainEvaluator(), Teacher())
    state = service.fresh_state('session-uncertain')
    completed = await service.process(state, 'hel...', 'turn-uncertain',
                                      transcript_status='uncertain')
    assert completed.next_state.script_index == 0
    assert completed.next_state.attempt_count == 0
    assert completed.plan.decision.feedback_action == 'clarify'


@pytest.mark.asyncio
async def test_final_script_line_is_spoken_before_completion():
    service = ScriptedLessonService(script(), Evaluator(), Teacher())
    state = service.fresh_state('session-final').model_copy(update={
        'script_index': 5, 'stage_id': 'conversation',
        'activity_id': 'lesson-05.exchange-01',
        'objective_id': 'lesson-05.objective-01',
        'last_teacher_turn': 'Greet me.', 'script_name': 'Nam',
    })
    completed = await service.process(state, 'Hello!', 'turn-final')
    assert completed.next_state.status == 'completed'
    assert completed.teacher_utterance.spoken_text.endswith('Good evening, Nam!')


@pytest.mark.asyncio
@pytest.mark.parametrize('kind,action', [
    ('asks_meaning', 'explain_meaning'),
    ('asks_teacher', 'answer_teacher_question'),
    ('off_topic', 'redirect'),
])
async def test_question_or_detour_does_not_consume_answer_attempt(kind, action):
    class NonAnswerEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'response_kind': kind, 'objective_evidence': []})

    service = ScriptedLessonService(script(), NonAnswerEvaluator(), Teacher())
    state = service.fresh_state('session-question')
    completed = await service.process(state, 'What does hello mean?', 'turn-question')
    assert completed.next_state.script_index == 0
    assert completed.next_state.attempt_count == 0
    assert completed.plan.decision.feedback_action == action


@pytest.mark.asyncio
async def test_pattern_target_form_alone_does_not_override_accept_judgment():
    class FormOnlyEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'objective_evidence': [
                result.objective_evidence[0].model_copy(update={
                    'meaning_status': 'not_demonstrated',
                    'target_form_status': 'correct_target_form',
                })]})

    service = ScriptedLessonService(script(), FormOnlyEvaluator(), Teacher())
    state = service.fresh_state('session-pattern').model_copy(update={
        'script_index': 3, 'stage_id': 'patterns',
        'activity_id': 'lesson-04.exchange-01',
        'objective_id': 'lesson-04.objective-01',
        'last_teacher_turn': 'Introduce yourself.',
    })
    completed = await service.process(state, 'Hi.', 'turn-form-only')
    assert completed.next_state.script_index == 3
    assert completed.next_state.attempt_count == 1


@pytest.mark.asyncio
async def test_vietnamese_chosen_name_is_kept_for_later_script_lines():
    service = ScriptedLessonService(script(), Evaluator(), Teacher())
    state = service.fresh_state('session-name').model_copy(update={
        'script_index': 3, 'stage_id': 'patterns',
        'activity_id': 'lesson-04.exchange-01',
        'objective_id': 'lesson-04.objective-01',
        'last_teacher_turn': 'Introduce yourself.',
    })
    first = await service.process(state, "Hi. I'm Ngọc.", 'turn-name-1')
    assert first.next_state.script_name == 'Ngọc'
    second = await service.process(first.next_state, "I'm tired", 'turn-name-2')
    assert second.next_state.script_name == 'Ngọc'


@pytest.mark.asyncio
async def test_completed_script_cannot_reopen():
    service = ScriptedLessonService(script(), Evaluator(), Teacher())
    state = service.fresh_state('session-complete').model_copy(update={'status': 'completed'})
    with pytest.raises(ValueError, match='Invalid lesson state'):
        await service.process(state, 'Hello', 'turn-after-end')


@pytest.mark.asyncio
async def test_step_can_override_default_attempt_limit():
    authored = script().model_dump()
    authored['stations'][0]['steps'][0]['attempts'] = 1
    scripted = LessonScript.model_validate(authored)

    class RejectingEvaluator(Evaluator):
        async def evaluate(self, request):
            result = await super().evaluate(request)
            return result.model_copy(update={'objective_evidence': []})

    service = ScriptedLessonService(scripted, RejectingEvaluator(), Teacher())
    state = service.fresh_state('session-limit').model_copy(update={
        'script_index': 1, 'stage_id': 'vocabulary',
        'activity_id': 'lesson-02.exchange-01',
        'objective_id': 'lesson-02.objective-01',
        'last_teacher_turn': 'Say hello.',
    })
    completed = await service.process(state, 'book', 'wrong-1')
    assert completed.next_state.script_index == 2
