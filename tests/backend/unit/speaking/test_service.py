import pytest

from luna_tutor.llm.openrouter import ProviderError
from luna_tutor.speaking.models import Evidence, Reply, SessionConfig, SpeakingState, TurnInput, WordUse
from luna_tutor.speaking.repository import SpeakingRepository
from luna_tutor.speaking.service import SpeakingService


class FakeModels:
    def __init__(self, evidence=None, error=None):
        self.evidence = evidence or Evidence(kind='answer', independent=True)
        self.error = error

    async def opening(self, state):
        return Reply(text='Let us plan a picnic! What food do you like?', support_kind='none')

    async def evaluate(self, state, turn):
        if self.error: raise self.error
        return self.evidence

    async def reply(self, state, turn, evidence, decision):
        if self.error: raise self.error
        return Reply(text='That sounds tasty! What would you like to drink?', support_kind=decision.action)


@pytest.fixture
def repository(tmp_path):
    return SpeakingRepository(tmp_path / 'speaking.sqlite3')


@pytest.mark.asyncio
async def test_submit_commits_evidence_and_reply(repository):
    evidence = Evidence(kind='answer', independent=True,
                        word_uses=(WordUse(word='juice', quote='I like juice', independent=True),))
    service = SpeakingService(repository, FakeModels(evidence))
    started = await service.start(SessionConfig(grade=5, topic='Food', words=('juice',)))
    result = await service.submit(started.session_id,
        TurnInput(turn_id='t1', text='I like juice', expected_version=started.version))
    assert result.state.version == 1
    assert result.state.word_evidence[0].word == 'juice'
    assert result.reply.text.startswith('That sounds')


@pytest.mark.asyncio
async def test_provider_failure_does_not_advance(repository):
    failure = ProviderError(status_code=503, request_id='t1', reason='fixture failure')
    service = SpeakingService(repository, FakeModels(error=failure))
    started = await service.start(SessionConfig(grade=5, topic='Food', words=('juice',)))
    with pytest.raises(ProviderError):
        await service.submit(started.session_id,
            TurnInput(turn_id='t1', text='I like juice.', expected_version=0))
    assert repository.get(started.session_id).version == 0


@pytest.mark.asyncio
async def test_unlisted_word_is_not_recorded(repository):
    evidence = Evidence(kind='answer', independent=True,
                        word_uses=(WordUse(word='cake', quote='cake', independent=True),))
    service = SpeakingService(repository, FakeModels(evidence))
    started = await service.start(SessionConfig(grade=5, topic='Food', words=('juice',)))
    result = await service.submit(started.session_id,
        TurnInput(turn_id='t1', text='cake', expected_version=0))
    assert result.state.word_evidence == ()


@pytest.mark.asyncio
async def test_unclear_quality_cannot_advance_or_record_empty_quote(repository):
    evidence = Evidence(kind='answer', independent=True,
                        word_uses=(WordUse(word='juice', quote='', independent=True),))
    service = SpeakingService(repository, FakeModels(evidence))
    started = await service.start(SessionConfig(grade=5, topic='Food', words=('juice',)))
    result = await service.submit(started.session_id,
        TurnInput(turn_id='t1', text='hello', expected_version=0, quality='unclear'))
    assert result.state.independent_streak == 0
    assert result.state.word_evidence == ()


@pytest.mark.asyncio
async def test_finish_summary_does_not_invent_unseen_words(repository):
    service = SpeakingService(repository, FakeModels())
    started = await service.start(SessionConfig(grade=5, topic='Food', words=('juice', 'sandwich')))
    finished = service.finish(started.session_id, 0)
    assert finished.unseen == ('juice', 'sandwich')
