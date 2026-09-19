from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class Topic(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str
    name_en: str
    name_vi: str
    scenario: str
    words: tuple[str, ...]


def load_topics() -> tuple[Topic, ...]:
    path = Path(__file__).with_name('topics.yaml')
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    return tuple(Topic.model_validate(item) for item in data)
