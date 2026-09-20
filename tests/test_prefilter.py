from app.models import NormalizedOpportunity
from app.prefilter import evaluate


def opportunity(title: str, description: str) -> NormalizedOpportunity:
    return NormalizedOpportunity(
        platform="remoteok",
        external_id="1",
        canonical_url="https://remoteok.com/remote-jobs/1",
        title=title,
        description_clean=description,
        content_hash="abc",
    )


def test_accepts_relevant_contract() -> None:
    decision = evaluate(
        opportunity(
            "Automation Consultant",
            "Short-term contract to build an n8n webhook and API integration.",
        )
    )
    assert decision.accepted
    assert "n8n" in decision.relevant_terms
    assert "contract" in decision.contract_terms


def test_rejects_full_time_role_when_contract_only() -> None:
    decision = evaluate(
        opportunity("Automation Engineer", "Full-time role building workflow automation."),
        contract_only=True,
    )
    assert not decision.accepted
    assert "not clearly contract or freelance work" in decision.hard_reasons


def test_rejects_disallowed_signal() -> None:
    decision = evaluate(
        opportunity(
            "n8n Contractor",
            "Contract role. Applicants must pay a fee before the interview.",
        )
    )
    assert not decision.accepted
    assert any("pay a fee" in reason for reason in decision.hard_reasons)


def test_accepts_beginner_service_categories_on_project_marketplace() -> None:
    examples = [
        ("Data cleanup", "Clean and format an Excel spreadsheet."),
        ("Research assistant", "Compile competitor research into Google Sheets."),
        ("Simple scraper", "Collect public product data into CSV using web scraping."),
        ("Document assistant", "Format resumes and rewrite product descriptions."),
        ("Small website", "Set up a simple WordPress landing page."),
        ("Python utility", "Build a basic Python automation for file renaming."),
    ]

    for title, description in examples:
        decision = evaluate(opportunity(title, description), contract_only=False)
        assert decision.accepted, (title, decision.hard_reasons)


def test_rejects_unsafe_scraping_even_when_relevant() -> None:
    decision = evaluate(
        opportunity(
            "Web scraping automation",
            "Scrape behind login and bypass CAPTCHA to collect account data.",
        ),
        contract_only=False,
    )
    assert not decision.accepted
    assert any("captcha" in reason for reason in decision.hard_reasons)


def test_contract_type_from_source_metadata_satisfies_contract_gate() -> None:
    item = opportunity("Data cleanup assistant", "Clean and organize spreadsheet records.")
    item.budget_type = "contract"
    decision = evaluate(item, contract_only=True)
    assert decision.accepted
    assert "contract" in decision.contract_terms


def test_freelancer_alert_can_skip_keyword_gate_but_not_safety_gate() -> None:
    generic = opportunity("Help with a small task", "Please review the linked project brief.")
    assert evaluate(generic, contract_only=False, require_relevant=False).accepted

    unsafe = opportunity(
        "Help with a small task",
        "The job is to send spam to a purchased contact list.",
    )
    decision = evaluate(unsafe, contract_only=False, require_relevant=False)
    assert not decision.accepted
    assert "disallowed signal: send spam" in decision.hard_reasons
