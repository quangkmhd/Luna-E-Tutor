"""Execute actual teaching turns; keep deterministic checks and semantic review separate."""
import re
import time
from pathlib import Path

from luna_tutor.curriculum.registry import CurriculumRegistry, SUPPORTED_UNIT_IDS
from luna_tutor.domain.evidence import SupportGiven
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.llm.openrouter import OpenRouterError


class BehaviorRunner:
    def __init__(self, root: Path, service, unit_id: str = 'grade05.unit01'):
        allowed_ids = SUPPORTED_UNIT_IDS
        self.registry = CurriculumRegistry(root / 'curriculum', allowed_ids)
        self.curriculum = self.registry.get(unit_id)
        self.service = service

    def initial_state(self, scenario):
        initial = scenario.initial_state
        activity = next((a for a in self.curriculum.activities if a.id == initial.activity_id), None)
        if activity is None or activity.stage_id != initial.stage_id:
            raise ValueError(f'{scenario.id}: explicit valid activity required')
        if initial.objective_id and initial.objective_id not in activity.objective_ids:
            raise ValueError(f'{scenario.id}: objective outside active activity')
        progress, completed = [], []
        if initial.prior_activities_handled:
            for stage in self.curriculum.stages:
                if stage.id == initial.stage_id:
                    break
                completed.append(stage.id)
            for prior in self.curriculum.activities:
                if prior.id == activity.id:
                    break
                if prior.stage_id == activity.stage_id:
                    progress.append(ActivityProgress(activity_id=prior.id, status='completed'))
        progress.append(ActivityProgress(
            activity_id=activity.id, status='completed' if initial.activity_completed else 'in_progress',
            attempt_count=initial.attempt_count,
            model_repetitions_delivered=initial.model_repetitions_delivered,
            response_opportunity_given=initial.response_opportunity_given))
        return LessonState(
            session_id=f'behavior-{scenario.id}', unit_id=self.curriculum.id,
            stage_id=activity.stage_id, activity_id=activity.id, objective_id=initial.objective_id,
            attempt_count=initial.attempt_count, completed_stage_ids=tuple(completed),
            activity_progress=tuple(progress), review_queue=tuple(initial.review_queue),
            last_teacher_turn=scenario.turns[0].teacher_turn,
            support_given=SupportGiven(model_spoken_recently=initial.support == 'model',
                choices_given=initial.support == 'choices', sentence_starter_given=initial.support == 'starter'))

    async def run(self, scenarios):
        supported = {'support_limit_exit', 'count_attempt', 'stage_id', 'activity_id', 'progression_action', 'review_queue_contains', 'review_queue_excludes', 'objective_id'}
        for scenario in scenarios:
            for turn in scenario.turns:
                unknown = set(turn.expected_state_effects) - supported
                if unknown:
                    raise ValueError(f'Unsupported state assertion: {sorted(unknown)}')
        records = []
        for scenario in scenarios:
            state = self.initial_state(scenario)
            for index, turn in enumerate(scenario.turns):
                started = time.perf_counter()
                record = {'scenario_id': scenario.id, 'turn_index': index + 1,
                          'initial_state': state.model_dump(mode='json'),
                          'semantic_criteria': turn.teacher_criteria,
                          'semantic_review_status': 'pending', 'failures': [],
                          'input_event': turn.input_event, 'transcript_status': turn.transcript_status,
                          'evidence_source': ('local_observed_event' if turn.input_event == 'no_response'
                                              else 'evaluator'),
                          'input_mode': 'simulated_no_response' if turn.input_event == 'no_response'
                          else 'typed_text' if turn.transcript_status == 'final'
                          else 'text_simulation_not_audio_validation'}
                try:
                    metadata = ({'transcript_status': turn.transcript_status}
                                if turn.transcript_status != 'final' else {})
                    if turn.input_event != 'transcript':
                        metadata['input_event'] = turn.input_event
                    completed = await self.service.process(state, turn.learner_text,
                                                           f'{scenario.id}-{index}', **metadata)
                except Exception as error:  # noqa: BLE001 - preserve diagnostics per scenario
                    record['error'] = {'type': type(error).__name__}
                    if isinstance(error, OpenRouterError):
                        record['error'].update(reason=error.reason, status=error.status_code)
                    record['failures'].append('turn_execution')
                    record['latency_ms'] = (time.perf_counter() - started) * 1000
                    records.append(record)
                    break  # No fabricated state to continue from after a failed turn.
                decision, utterance = completed.plan.decision, completed.teacher_utterance
                record['completed_turn'] = completed.model_dump(mode='json')
                failures = record['failures']
                if decision.feedback_action not in turn.allowed_feedback_actions:
                    failures.append('feedback_action')
                actual = {'support_limit_exit': decision.support_limit_exit,
                          'count_attempt': decision.count_attempt,
                          'stage_id': completed.next_state.stage_id,
                          'activity_id': completed.next_state.activity_id,
                          'progression_action': decision.progression_action,
                          'review_queue_contains': [i.objective_id for i in completed.next_state.review_queue],
                          'review_queue_excludes': [i.objective_id for i in completed.next_state.review_queue],
                          'objective_id': completed.next_state.objective_id}
                for key, expected in turn.expected_state_effects.items():
                    matches = (set(expected) <= set(actual[key]) if key == 'review_queue_contains'
                               else not set(expected) & set(actual[key]) if key == 'review_queue_excludes'
                               else expected == actual[key])
                    if not matches:
                        failures.append(f'state:{key}')
                text = utterance.spoken_text.casefold()
                if utterance.generation_mode == 'fallback':
                    failures.append('teacher_fallback')
                if decision.feedback_action == 'recast' and re.search(
                        r'\b(repeat after me|say it again|repeat it|nhắc lại|nói lại)\b', text):
                    failures.append('forced_repetition')
                if re.search(r'perfect pronunciation|pronounced (it |that )?(correctly|wrong)', text):
                    failures.append('pronunciation_claim')
                if re.search(r'```|\*\*|^#{1,6} ', text):
                    failures.append('markdown')
                if text.count('?') > completed.plan.teacher_request.constraints.max_questions:
                    failures.append('too_many_questions')
                delivery_checks = []
                if completed.next_state.activity_id != state.activity_id:
                    target = next(a for a in self.curriculum.activities
                                  if a.id == completed.next_state.activity_id)
                    receipt = next((p for p in completed.next_state.activity_progress
                                    if p.activity_id == target.id), None)
                    delivery_checks.append('new_activity_response_opportunity')
                    if receipt is None or not receipt.response_opportunity_given:
                        failures.append('missing_response_opportunity')
                    if target.completion_rule.model_repetitions:
                        delivery_checks.append('new_activity_models')
                        if receipt is None or receipt.model_repetitions_delivered < target.completion_rule.model_repetitions:
                            failures.append('missing_models')
                record['checked'] = ['feedback_action', *turn.expected_state_effects,
                                     'teacher_fallback', 'forced_repetition',
                                     'pronunciation_claim', 'markdown', 'too_many_questions', *delivery_checks]
                record['unmeasured_forbidden_behaviors'] = sorted(set(turn.forbidden_behaviors)
                    - {'forced_repetition', 'fabricated_pronunciation_claim'})
                record['latency_ms'] = (time.perf_counter() - started) * 1000
                records.append(record)
                state = completed.next_state
        return records
