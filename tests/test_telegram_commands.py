from app.telegram_commands import is_run_command, render_run_summary


def test_run_command_accepts_expected_text_and_bot_mention() -> None:
    assert is_run_command("/go")
    assert is_run_command(" /GO@FreelyOpportunityAssistantBot ")
    assert is_run_command("/run freely")
    assert is_run_command(" /RUN@FreelyOpportunityAssistantBot FREELY ")


def test_run_command_rejects_other_text() -> None:
    assert not is_run_command("   ")
    assert not is_run_command("/run")
    assert not is_run_command("/run another")
    assert not is_run_command("/go now")
    assert not is_run_command("run freely")


def test_run_summary_reports_key_counts() -> None:
    result = {
        "scouts": [
            {"platform": "jobicy", "fetched": 10, "opportunity_ids": ["1", "2"]},
            {"platform": "github", "fetched": 5, "opportunity_ids": ["3"]},
        ],
        "processed": [
            {"status": "PROPOSAL_READY", "deliver": True},
            {"status": "REJECTED", "deliver": False},
        ],
        "deferred_by_limit": 4,
        "errors": [],
        "source_errors": [{"platform": "example", "error": "failed"}],
    }
    summary = render_run_summary(result)
    assert "Mode: Freelancer saved-search alerts only" in summary
    assert "Queued alerts found: 0" in summary
    assert "Proposals prepared: 1" in summary
    assert "Skipped as unsafe or undeliverable: 1" in summary
    assert "Errors: 1" in summary
