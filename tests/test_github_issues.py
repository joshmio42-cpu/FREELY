import pytest

from app.sources.github_issues import _validate_api_url, normalize_github_issue


def test_normalize_paid_github_issue() -> None:
    result = normalize_github_issue(
        {
            "id": 551,
            "html_url": "https://github.com/example/project/issues/7",
            "repository_url": "https://api.github.com/repos/example/project",
            "title": "Paid task: repair webhook automation",
            "body": "A small paid bounty to repair a Python webhook and Google Sheets workflow.",
            "labels": [{"name": "bounty"}, {"name": "Python"}],
            "created_at": "2026-09-18T01:00:00Z",
            "updated_at": "2026-09-19T01:00:00Z",
        }
    )
    assert result.platform == "github"
    assert result.client_name == "example/project"
    assert result.required_skills == ["bounty", "python"]
    assert "manual verification" in str(result.budget_type)


def test_github_api_url_is_restricted() -> None:
    _validate_api_url("https://api.github.com/search/issues")
    with pytest.raises(ValueError):
        _validate_api_url("https://github.com/search/issues")
