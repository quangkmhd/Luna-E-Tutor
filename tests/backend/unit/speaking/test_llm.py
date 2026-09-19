import pytest

from luna_tutor.llm.openrouter import InvalidModelOutputError
from luna_tutor.speaking.llm import SpeakingModels
from luna_tutor.speaking.models import Suggestions


class InvalidClient:
    async def structured_chat(self, *_args):
        return {'topic': 'Food', 'words': [{'word': ''}]}


@pytest.mark.asyncio
async def test_schema_validation_is_reported_as_safe_model_output_error():
    models = SpeakingModels(InvalidClient())
    with pytest.raises(InvalidModelOutputError):
        await models._call('system', {}, Suggestions, 'suggestions')
