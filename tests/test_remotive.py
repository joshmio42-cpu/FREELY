import pytest

from app.sources.remotive import _validate_api_url, normalize_remotive


def test_normalize_remotive_contract() -> None:
    result = normalize_remotive(
        {
            "id": 209,
            "url": "https://remotive.com/remote-jobs/software-dev/automation-assistant-209",
            "title": "Automation Assistant",
            "company_name": "Example Co",
            "category": "All others",
            "tags": ["Python", "Google Sheets"],
            "job_type": "contract",
            "candidate_required_location": "Worldwide",
            "publication_date": "2026-09-17T10:00:00Z",
            "description": "<p>Clean data and maintain an automation workflow.</p>",
        }
    )
    assert result.platform == "remotive"
    assert result.external_id == "209"
    assert result.required_skills == ["all others", "google sheets", "python"]
    assert result.budget_type == "contract"


def test_remotive_api_url_is_restricted() -> None:
    _validate_api_url("https://remotive.com/api/remote-jobs")
    with pytest.raises(ValueError):
        _validate_api_url("http://remotive.com/api/remote-jobs")
