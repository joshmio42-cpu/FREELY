from app.sources.remoteok import normalize_remoteok


def test_normalize_remoteok() -> None:
    result = normalize_remoteok(
        {
            "id": "123",
            "date": "2026-09-20T00:00:00+00:00",
            "company": "Example Co",
            "position": "Automation Consultant",
            "description": "<p>Build an n8n workflow and REST API integration.</p>",
            "location": "Worldwide",
            "tags": ["n8n", "API", "n8n"],
            "salary_min": 100,
            "salary_max": 200,
            "url": "https://remoteOK.com/remote-jobs/example-123",
        }
    )
    assert result.external_id == "123"
    assert result.title == "Automation Consultant"
    assert result.client_name == "Example Co"
    assert result.required_skills == ["api", "n8n"]
    assert str(result.canonical_url) == "https://remoteok.com/remote-jobs/example-123"
    assert result.currency == "USD"
