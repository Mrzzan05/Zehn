from datetime import datetime, timezone

import pytest

from reality.classification.adapters import to_classification_observation
from reality.schemas import Observation

CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_canonical_observation_is_projected_not_duplicated():
    canonical = Observation(id=7, raw_text="Sara likes cats", created_at=CREATED)

    view = to_classification_observation(canonical)

    assert view.observation_id == "7"
    assert view.raw_content == "Sara likes cats"
    assert view.timestamp == CREATED
    assert view.modality_metadata == ()


def test_unpersisted_observation_is_refused():
    with pytest.raises(ValueError, match="Observation.id must not be None"):
        to_classification_observation(Observation(raw_text="not saved yet"))
