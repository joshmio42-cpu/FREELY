from decimal import Decimal

import pytest

from app.sources.freelancer import _validate_api_url, normalize_freelancer


def test_normalize_freelancer_project() -> None:
    result = normalize_freelancer(
        {
            "id": 456,
            "title": "Build an n8n lead automation",
            "description": "<p>Connect a webhook to Sheets and an API.</p>",
            "seo_url": "n8n/build-n8n-lead-automation",
            "type": "fixed",
            "submitdate": 1789876800,
            "time_updated": 1789880400,
            "budget": {"minimum": 100, "maximum": 300},
            "currency": {"code": "USD"},
            "jobs": [{"name": "n8n"}, {"name": "API"}, {"name": "n8n"}],
            "location": {"city": "Manila", "country": {"name": "Philippines"}},
        }
    )
    assert result.platform == "freelancer"
    assert result.external_id == "456"
    assert str(result.canonical_url) == (
        "https://www.freelancer.com/projects/n8n/build-n8n-lead-automation"
    )
    assert result.description_clean == "Connect a webhook to Sheets and an API."
    assert result.required_skills == ["api", "n8n"]
    assert result.budget_min == Decimal("100")
    assert result.budget_max == Decimal("300")
    assert result.currency == "USD"
    assert result.budget_type == "fixed"
    assert result.location == "Manila, Philippines"


def test_freelancer_api_url_is_restricted_to_official_https_hosts() -> None:
    _validate_api_url("https://www.freelancer.com/api/projects/0.1")
    _validate_api_url("https://www.freelancer-sandbox.com/api/projects/0.1")
    with pytest.raises(ValueError):
        _validate_api_url("https://example.com/api/projects/0.1")
    with pytest.raises(ValueError):
        _validate_api_url("http://www.freelancer.com/api/projects/0.1")
