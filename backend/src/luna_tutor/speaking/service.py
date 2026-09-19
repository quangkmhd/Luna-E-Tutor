from uuid import uuid4

from luna_tutor.speaking.models import (
    ConversationMessage, Evidence, Reply, SessionConfig, SpeakingState, Summary,
    TurnInput, TurnResult,
)
from luna_tutor.speaking.policy import decide


class SpeakingService:
    def __init__(self, repository, models):
        self.repository = repository
        self.models = models

    async def start(self, config: SessionConfig) -> SpeakingState:
        state = SpeakingState.initial(str(uuid4()), config)
        opening = await self.models.opening(state)
        state = state.model_copy(update={
            'opening_message': opening.text,
            'last_delivered_text': opening.text,
            'messages': (ConversationMessage(role='teacher', text=opening.text),),
        })
        return self.repository.create(state)

    async def submit(self, session_id: str, turn: TurnInput) -> TurnResult:
        reservation = self.repository.reserve_turn(session_id, turn)
        if reservation.existing_reply is not None:
            return TurnResult(
                state=self.repository.get(session_id),
                reply=Reply.model_validate(reservation.existing_reply),
            )
        try:
            state = self.repository.get(session_id)
            if turn.quality == 'final':
                evidence = await self.models.evaluate(state, turn)
            else:
                evidence = Evidence(kind='unclear')
            valid_uses = tuple(use for use in evidence.word_uses
                               if use.word.casefold() in state.config.words
                               and use.quote.strip()
                               and use.word.casefold() in use.quote.casefold()
                               and use.quote.casefold() in turn.text.casefold())
            evidence = evidence.model_copy(update={'word_uses': valid_uses})
            decision = decide(state, evidence)
            reply = await self.models.reply(state, turn, evidence, decision)
            next_state = state.with_decision(decision).model_copy(update={
                'version': state.version + 1,
                'status': 'completed' if decision.action == 'finish' else 'active',
                'word_evidence': (*state.word_evidence, *valid_uses),
                'last_delivered_text': reply.text if turn.input_mode == 'text' else '',
                'messages': (*state.messages,
                             ConversationMessage(role='learner', text=turn.text,
                                                 turn_id=turn.turn_id),
                             ConversationMessage(role='teacher', text=reply.text,
                                                 turn_id=turn.turn_id)),
            })
            self.repository.commit_turn(session_id, turn.turn_id, reservation.generation,
                                        next_state, reply.model_dump())
            return TurnResult(state=next_state, reply=reply)
        except BaseException:
            self.repository.release_turn(session_id, turn.turn_id, reservation.generation)
            raise

    def finish(self, session_id: str, expected_version: int) -> Summary:
        state = self.repository.finish(session_id, expected_version)
        independent = tuple(dict.fromkeys(use.word for use in state.word_evidence if use.independent))
        supported = tuple(dict.fromkeys(use.word for use in state.word_evidence
                                        if not use.independent and use.word not in independent))
        unseen = tuple(word for word in state.config.words
                       if word not in independent and word not in supported)
        next_word = unseen[0] if unseen else (supported[0] if supported else '')
        next_practice = (f'Next time, try using “{next_word}” in your own sentence.'
                         if next_word else 'Keep sharing your ideas in English.')
        return Summary(state=state, independent=independent, supported=supported,
                       unseen=unseen, next_practice=next_practice)
