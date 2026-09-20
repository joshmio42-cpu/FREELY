import pytest

from app.sources.jobicy import _validate_api_url, normalize_jobicy


def test_normalize_jobicy_contract() -> None:
    result = normalize_jobicy(
        {
            "id": 150,
            "url": "https://jobicy.com/jobs/150-automation-assistant",
            "jobTitle": "Automation Assistant",
            "companyName": "Example Co",
            "jobIndustry": ["Product & Operations", "Data Entry"],
            "jobType": ["Contract"],
            "jobGeo": "Worldwide",
            "jobDescription": "<p>Maintain spreadsheets and a small automation.</p>",
            "pubDate": "2026-09-17T13:35:17+08:00",
        }
    )
    assert result.platform == "jobicy"
    assert result.external_id == "150"
    assert result.client_name == "Example Co"
    assert result.required_skills == ["data entry", "product & operations"]
    assert result.budget_type == "contract"


def test_jobicy_api_url_is_restricted() -> None:
    _validate_api_url("https://jobicy.com/api/v2/remote-jobs")
    with pytest.raises(ValueError):
        _validate_api_url("https://example.com/api/v2/remote-jobs")
