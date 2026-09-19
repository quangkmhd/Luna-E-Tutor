"""Shared validation primitives, independent of curriculum file structure."""

from typing import Annotated, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from luna_tutor.curriculum.models import Identifier

Text = Annotated[str, Field(min_length=1, pattern=r'\S')]
Version = Annotated[int, Field(ge=0)]
AttemptCount = Annotated[int, Field(ge=0, le=2)]
T = TypeVar('T')


def _snapshot_array(value):
    # Accept only the JSON-array equivalent, not arbitrary iterables/coercions.
    return tuple(value) if isinstance(value, list) else value


SnapshotItems = Annotated[tuple[T, ...], BeforeValidator(_snapshot_array)]


class Contract(BaseModel):
    model_config = ConfigDict(
        strict=True, extra='forbid', frozen=True, revalidate_instances='always',
        hide_input_in_errors=True,
    )


__all__ = ['AttemptCount', 'Contract', 'Identifier', 'SnapshotItems', 'Text', 'Version']
