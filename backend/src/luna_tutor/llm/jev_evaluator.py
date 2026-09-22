"""Decision-only TypeSafe Jev evaluator for the shared teaching pipeline."""

from copy import deepcopy

from luna_tutor.domain.evidence import EvaluatorRequest, EvaluatorResult, ObjectiveEvidence
from luna_tutor.llm.openrouter import InvalidModelOutputError, OpenRouterClient
from luna_tutor.prompts.loader import load_prompt_data


def _choice(answers: dict, name: str, allowed: set[str]) -> str:
    answer = answers.get(name)
    if not isinstance(answer, dict) or answer.get('type') != 'choice':
        raise ValueError(f'Missing choice answer: {name}')
    value = answer.get('choice')
    if value not in allowed:
        raise ValueError(f'Unknown choice answer: {name}')
    return value


def _noul(answers: dict, name: str) -> bool:
    answer = answers.get(name)
    if not isinstance(answer, dict) or answer.get('type') != 'noul':
        raise ValueError(f'Missing noul answer: {name}')
    value = answer.get('noul')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f'Invalid noul answer: {name}')
    return value >= 0.5


class JevEvaluator:
    """Translate the evidence rubric into Jev questions, never generative prose."""

    def __init__(self, client: OpenRouterClient):
        self._client = client
        self._rubric = load_prompt_data('jev-evaluator.yaml')

    def _questions(self, request: EvaluatorRequest) -> dict:
        questions = {
            'response_kind': deepcopy(self._rubric['response_kind']),
            'emotional_signal': deepcopy(self._rubric['emotional_signal']),
            'needs_clarification': deepcopy(self._rubric['needs_clarification']),
        }
        for index, objective in enumerate(request.active_objectives):
            context = (
                f" Objective: {objective.communicative_goal}. "
                f"Target patterns: {list(objective.target_patterns)}. "
                f"Target words: {list(objective.target_words)}. "
                f"Acceptable alternatives: {list(objective.acceptable_alternatives)}. "
                f"Evidence criterion: {objective.evidence_criteria}."
            )
            if request.activity_type == 'scripted_lesson':
                context += (
                    ' This criterion is the authored accept description. '
                    'Treat its allowed omissions and small errors as acceptable learner answers; '
                    'do not require literal string matching.'
                )
            for suffix, rubric_name in (
                ('meaning', 'objective_meaning'),
                ('form', 'objective_form'),
                ('recast', 'objective_recast'),
            ):
                question = deepcopy(self._rubric[rubric_name])
                question['instructions'] += context
                questions[f'objective_{index}_{suffix}'] = question
        return questions

    async def evaluate(self, request: EvaluatorRequest) -> EvaluatorResult:
        state = request.model_dump(mode='json')
        try:
            envelope = await self._client.decisions(
                state=state, questions=self._questions(request), request_id=request.turn_id)
            answers = envelope['answers']
            response_kind = _choice(answers, 'response_kind', {
                'answer', 'asks_meaning', 'asks_teacher', 'off_topic',
                'does_not_know', 'insufficient_data',
            })
            emotional = _noul(answers, 'emotional_signal')
            clarification = _noul(answers, 'needs_clarification')
            if response_kind == 'insufficient_data':
                clarification = True

            items = []
            for index, objective in enumerate(request.active_objectives):
                meaning = _choice(answers, f'objective_{index}_meaning', {
                    'satisfied', 'partially_satisfied', 'wrong_semantic_category',
                    'not_demonstrated', 'uncertain',
                })
                form = _choice(answers, f'objective_{index}_form', {
                    'correct_target_form', 'valid_alternative', 'error_in_target_form',
                    'not_used', 'uncertain',
                })
                wants_recast = _noul(answers, f'objective_{index}_recast')
                recast = bool(
                    wants_recast
                    and response_kind not in {'asks_meaning', 'insufficient_data'}
                    and meaning in {'satisfied', 'partially_satisfied'}
                    and form == 'error_in_target_form'
                )
                demonstrated = (
                    meaning not in {'not_demonstrated', 'uncertain'}
                    or form not in {'not_used', 'uncertain'}
                )
                items.append(ObjectiveEvidence(
                    objective_id=objective.objective_id,
                    meaning_status=meaning,
                    target_form_status=form,
                    evidence_quote=request.learner_transcript if demonstrated else None,
                    recast_needed=recast,
                    corrected_form=None,
                ))
            return EvaluatorResult(
                turn_id=request.turn_id,
                state_version=request.state_version,
                response_kind=response_kind,
                emotional_signals=['emotional_signal_detected'] if emotional else [],
                objective_evidence=items,
                needs_clarification=clarification,
                ambiguity_reason=('Jev marked the learner input as unclear.'
                                  if clarification else None),
            )
        except InvalidModelOutputError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidModelOutputError(
                status_code=200, request_id=request.turn_id,
                reason='Invalid Jev decision output') from None
