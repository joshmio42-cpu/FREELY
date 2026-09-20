import pytest

from app.models import FreelancerAlertInput
from app.sources.freelancer_alerts import (
    canonical_project_url,
    normalize_freelancer_alert,
    split_freelancer_alert,
)


def test_alert_extracts_exact_tracking_free_project_link() -> None:
    alert = FreelancerAlertInput(
        subject="New project: Workflow Automation Setup",
        html=(
            '<p>A client needs an n8n automation with Google Sheets and Telegram.</p>'
            '<a href="https://www.freelancer.com/projects/ai-workflow-automation/'
            'workflow-automation-setup/details?utm_source=email#bid">'
            "Workflow Automation Setup</a>"
        ),
        message_id="mail-1",
    )
    items = split_freelancer_alert(alert)
    assert len(items) == 1
    opportunity = normalize_freelancer_alert(items[0])
    assert str(opportunity.canonical_url) == (
        "https://www.freelancer.com/projects/ai-workflow-automation/"
        "workflow-automation-setup/details"
    )
    assert opportunity.title == "Workflow Automation Setup"
    assert opportunity.platform == "freelancer_alert"
    assert "n8n automation" in opportunity.description_clean


def test_alert_extracts_multiple_unique_links() -> None:
    alert = FreelancerAlertInput(
        subject="Two matching projects",
        text=(
            "https://www.freelancer.com/projects/python/task-one?tracking=1\n"
            "https://www.freelancer.com/projects/python/task-two\n"
            "https://www.freelancer.com/projects/python/task-one?tracking=2"
        ),
    )
    assert len(split_freelancer_alert(alert)) == 2


def test_alert_rejects_non_project_and_non_freelancer_links() -> None:
    alert = FreelancerAlertInput(
        subject="Untrusted mail",
        text="https://example.com/projects/python/fake https://www.freelancer.com/about",
    )
    with pytest.raises(ValueError, match="no valid Freelancer.com project link"):
        split_freelancer_alert(alert)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.freelancer.com/projects/python/task",
        "https://evil.example/projects/python/task",
        "https://www.freelancer.com/projects",
    ],
)
def test_canonical_project_url_is_strict(url: str) -> None:
    assert canonical_project_url(url) is None
