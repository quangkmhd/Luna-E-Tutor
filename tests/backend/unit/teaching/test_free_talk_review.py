import pytest

from luna_tutor.domain.evidence import SupportGiven
from luna_tutor.domain.state import ActivityProgress, ReviewItem

HOME = 'unit01.lesson01.pattern.live_in'
CITY = 'unit01.lesson01.vocabulary.city'
HOBBY = 'unit01.level02.pattern.hobby'
TRAFFIC = 'unit01.level03.vocabulary.traffic_jam'


def test_context_selects_only_relevant_review_without_switching_topic(engine, free_state, evidence, unit_01):
    queue = (ReviewItem(objective_id=HOBBY, difficulty='word_recall', learner_context='table tennis with dad'),
             ReviewItem(objective_id=TRAFFIC, difficulty='word_recall', learner_context='many cars very slow'))
    state = free_state.model_copy(update={'review_queue': queue})
    decision = engine.decide(state, evidence(objective_id=HOME, quote='Many cars. Very slow.', form='not_used'), unit_01)
    assert decision.next_objective_id == TRAFFIC
    assert decision.progression_action == 'stay'
    assert decision.review_queue_remove == []
    assert not decision.count_attempt


def test_unrelated_review_waits_without_forced_prompt(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'review_queue': (
        ReviewItem(objective_id=TRAFFIC, difficulty='word_recall', learner_context='many cars slow'),)})
    decision = engine.decide(state, evidence(objective_id=HOBBY, quote='I play table tennis with dad.'), unit_01)
    assert decision.next_objective_id is None


@pytest.mark.parametrize('form', ['correct_target_form', 'valid_alternative'])
def test_independent_spontaneous_success_cancels_planned_review(engine, free_state, evidence, unit_01, form):
    state = free_state.model_copy(update={'objective_id': HOME, 'review_queue': (
        ReviewItem(objective_id=HOME, difficulty='target_form', learner_context='city'),)})
    decision = engine.decide(state, evidence(form=form), unit_01)
    assert decision.review_queue_remove == [HOME]
    assert decision.next_objective_id is None
    assert decision.mastery_updates[0].independent_uses == 1
    assert not decision.mastery_updates[0].needs_review
    assert decision.progression_action == 'stay'


def test_supported_use_does_not_clear_review(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'support_given': SupportGiven(model_spoken_recently=True),
        'review_queue': (ReviewItem(objective_id=HOME, difficulty='target_form'),)})
    decision = engine.decide(state, evidence(), unit_01)
    assert decision.review_queue_remove == []
    assert decision.mastery_updates[0].supported_uses == 1
    assert decision.mastery_updates[0].needs_review


def test_meaning_alone_does_not_clear_target_form_review(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'review_queue': (ReviewItem(objective_id=HOME, difficulty='target_form'),)})
    decision = engine.decide(state, evidence(form='not_used', quote='Con sống ở thành phố.'), unit_01)
    assert decision.review_queue_remove == []
    assert decision.mastery_updates[0].independent_uses == 0


@pytest.mark.parametrize('kind', ['asks_teacher', 'asks_meaning'])
def test_questions_receive_priority_over_review_prompt(engine, free_state, evidence, unit_01, kind):
    state = free_state.model_copy(update={'review_queue': (
        ReviewItem(objective_id=TRAFFIC, difficulty='word_recall', learner_context='cars'),)})
    decision = engine.decide(state, evidence(kind=kind, form='not_used', quote='Many cars.'), unit_01)
    assert decision.next_objective_id is None
    assert not decision.count_attempt


def test_ranking_prefers_curriculum_importance_after_equal_relevance(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'review_queue': (
        ReviewItem(objective_id=TRAFFIC, difficulty='word_recall', learner_context='town'),
        ReviewItem(objective_id=HOME, difficulty='meaning', learner_context='town'))})
    decision = engine.decide(state, evidence(objective_id=HOBBY, form='not_used', quote='town'), unit_01)
    # Home has more required curriculum opportunities than traffic jam.
    assert decision.next_objective_id == HOME


def test_ranking_prefers_less_required_support_after_equal_importance(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'review_queue': (
        ReviewItem(objective_id=CITY, difficulty='word_recall', learner_context='home', support_level='model'),
        ReviewItem(objective_id='unit01.lesson01.vocabulary.countryside', difficulty='word_recall',
                   learner_context='home', support_level='context_hint'))})
    decision = engine.decide(state, evidence(objective_id=HOBBY, form='not_used', quote='home'), unit_01)
    assert decision.next_objective_id == 'unit01.lesson01.vocabulary.countryside'


def test_ranking_prefers_older_item_then_curriculum_order_for_ties(engine, free_state, evidence, unit_01):
    country = 'unit01.lesson01.vocabulary.countryside'
    state = free_state.model_copy(update={'applied_turn_ids': ('old', 'recent', 'latest'), 'review_queue': (
        ReviewItem(objective_id=CITY, difficulty='word_recall', learner_context='home', last_seen_turn_id='recent'),
        ReviewItem(objective_id=country, difficulty='word_recall', learner_context='home', last_seen_turn_id='old'))})
    decision = engine.decide(state, evidence(objective_id=HOBBY, form='not_used', quote='home'), unit_01)
    assert decision.next_objective_id == country
    state = state.model_copy(update={'review_queue': tuple(item.model_copy(update={'last_seen_turn_id': None}) for item in reversed(state.review_queue))})
    assert engine.decide(state, evidence(objective_id=HOBBY, form='not_used', quote='home'), unit_01).next_objective_id == CITY


def test_recently_exhausted_item_is_not_immediately_rephrased(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'objective_id': HOME, 'attempt_count': 2,
        'review_queue': (ReviewItem(objective_id=HOME, difficulty='target_form', learner_context='city'),)})
    decision = engine.decide(state, evidence(form='not_used', quote='city'), unit_01)
    assert decision.next_objective_id is None
    assert not decision.count_attempt


def test_free_talk_only_ends_on_explicit_completion_and_keeps_open_review(engine, free_state, evidence, unit_01):
    queue = (ReviewItem(objective_id=TRAFFIC, difficulty='word_recall'),)
    state = free_state.model_copy(update={'elapsed_seconds': 9999.0, 'review_queue': queue})
    assert engine.decide(state, evidence(), unit_01).progression_action == 'stay'
    state = state.model_copy(update={'activity_progress': (ActivityProgress(
        activity_id='free-talk.conversation', status='completed'),)})
    decision = engine.decide(state, evidence(items=[]), unit_01)
    assert decision.progression_action == 'move_to_next_stage'
    assert decision.next_stage_id == 'summary'
    assert decision.review_queue_remove == []
    assert state.review_queue == queue


@pytest.mark.parametrize('form', ['not_used', 'correct_target_form', 'valid_alternative'])
@pytest.mark.parametrize(('quote', 'supported', 'resolved'), [
    ('There is a traffic jam near my school.', False, True),
    ('Traffic jam.', True, False),
    ('Đường bị tắc.', False, False),
])
def test_vocabulary_review_uses_english_word_evidence_without_requiring_sentence_form(
        engine, free_state, evidence, unit_01, quote, supported, resolved, form):
    state = free_state.model_copy(update={
        'objective_id': TRAFFIC,
        'support_given': SupportGiven(model_spoken_recently=supported),
        'review_queue': (ReviewItem(objective_id=TRAFFIC, difficulty='word_recall'),)})
    decision = engine.decide(state, evidence(objective_id=TRAFFIC, quote=quote, form=form), unit_01)
    assert (TRAFFIC in decision.review_queue_remove) is resolved
    progress = decision.mastery_updates[0]
    assert progress.independent_uses == int(resolved)
    assert progress.supported_uses == int(supported)


def test_review_can_follow_topic_without_claiming_objective_evidence(engine, free_state, evidence, unit_01):
    state = free_state.model_copy(update={'review_queue': (
        ReviewItem(objective_id=TRAFFIC, difficulty='word_recall', learner_context='many cars slow'),)})
    decision = engine.decide(state, evidence(items=[]), unit_01,
                             learner_text='Many cars move slowly near my school.')
    assert decision.next_objective_id == TRAFFIC
    assert decision.mastery_updates == []
    assert decision.review_queue_remove == []
