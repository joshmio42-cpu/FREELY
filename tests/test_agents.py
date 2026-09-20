import pytest

from app.agents import validate_claim_ids


def test_claim_ids_accept_known_ids() -> None:
    validate_claim_ids(["pathly.summary.v1"], [{"id": "pathly.summary.v1"}])


def test_claim_ids_reject_unknown_ids() -> None:
    with pytest.raises(ValueError, match="unapproved claim"):
        validate_claim_ids(["fake.client.metric"], [{"id": "pathly.summary.v1"}])
