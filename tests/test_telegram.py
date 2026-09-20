from uuid import uuid4

from app.models import (
    CriticResult,
    FitAssessment,
    OpportunityRecord,
    OpportunityStatus,
    ProposalDraft,
    ResearchReport,
    ResearchSolutionResult,
    ScoreBreakdown,
    SolutionDesign,
)
from app.telegram import render_telegram


def test_telegram_message_contains_manual_gate_and_attribution() -> None:
    opportunity = OpportunityRecord(
        id=uuid4(),
        platform="remoteok",
        external_id="123",
        canonical_url="https://remoteok.com/remote-jobs/123",
        title="n8n Automation Consultant",
        description_clean="Build a workflow",
        client_name="Example",
        required_skills=["n8n"],
        status=OpportunityStatus.QUALIFIED,
    )
    fit = FitAssessment(
        breakdown=ScoreBreakdown(
            deliverability=45,
            scope_clarity=27,
            portfolio_relevance=18,
            risk_penalty=0,
        ),
        recommendation="PROCEED",
        fatal_risk=False,
        matched_skills=["n8n", "webhooks"],
        missing_skills=[],
        major_risks=[],
        estimated_hours_min=5,
        estimated_hours_max=8,
        rationale="Strong overlap with the approved capability profile.",
        confidence=0.9,
    )
    solution = ResearchSolutionResult(
        research=ResearchReport(
            client_problem="Manual lead routing",
            desired_outcome="Automated routing",
            technical_requirements=["webhook"],
            business_requirements=[],
            constraints=[],
            hidden_requirements=[],
            clarification_questions=[],
        ),
        solution=SolutionDesign(
            feasible=True,
            architecture_summary="Webhook to n8n",
            components=["n8n"],
            workflow_steps=["Lead form", "Webhook", "n8n", "Google Sheets"],
            implementation_stages=["Build", "Test"],
            complexity="MODERATE",
            risks=[],
            missing_information=[],
            estimated_hours_min=5,
            estimated_hours_max=8,
        ),
    )
    proposal = ProposalDraft(
        proposal_text="I can build this workflow and test the failure paths before handoff.",
        estimated_hours_min=5,
        estimated_hours_max=8,
    )
    critic = CriticResult(
        approved=True,
        issues=[],
        final_proposal="I can build this workflow and test the failure paths before handoff.",
    )
    chunks = render_telegram(opportunity, fit, solution, proposal, critic)
    message = "\n".join(chunks)
    assert "FREELANCE MATCH: 90%" in message
    assert "STRONG LEAD" in message
    assert chunks[0].endswith("https://remoteok.com/remote-jobs/123")
    assert "EXACT GIG LINK" in chunks[0]
    assert "FINAL PROPOSAL — COPY AND REVIEW" in chunks[-1]
    assert critic.final_proposal in chunks[-1]
    assert "does not submit bids" in message
    assert "Source: Remote OK" in message
    assert all(len(chunk) <= 3900 for chunk in chunks)


def test_telegram_uses_freelancer_attribution() -> None:
    opportunity = OpportunityRecord(
        id=uuid4(),
        platform="freelancer",
        external_id="456",
        canonical_url="https://www.freelancer.com/projects/n8n/example",
        title="n8n Automation",
        description_clean="Build a workflow",
        required_skills=["n8n"],
        status=OpportunityStatus.QUALIFIED,
    )
    fit = FitAssessment(
        breakdown=ScoreBreakdown(
            deliverability=50,
            scope_clarity=30,
            portfolio_relevance=20,
            risk_penalty=0,
        ),
        recommendation="PROCEED",
        fatal_risk=False,
        matched_skills=["n8n"],
        missing_skills=[],
        major_risks=[],
        estimated_hours_min=2,
        estimated_hours_max=4,
        rationale="Direct match.",
        confidence=0.9,
    )
    solution = ResearchSolutionResult(
        research=ResearchReport(
            client_problem="Manual work",
            desired_outcome="Automation",
            technical_requirements=[],
            business_requirements=[],
            constraints=[],
            hidden_requirements=[],
            clarification_questions=[],
        ),
        solution=SolutionDesign(
            feasible=True,
            architecture_summary="n8n workflow",
            components=["n8n"],
            workflow_steps=["Trigger", "n8n"],
            implementation_stages=["Build", "Test"],
            complexity="LOW",
            risks=[],
            missing_information=[],
            estimated_hours_min=2,
            estimated_hours_max=4,
        ),
    )
    proposal = ProposalDraft(
        proposal_text="I can build and test this workflow before a documented handoff.",
        estimated_hours_min=2,
        estimated_hours_max=4,
    )
    critic = CriticResult(
        approved=True,
        issues=[],
        final_proposal="I can build and test this workflow before a documented handoff.",
    )
    message = "\n".join(render_telegram(opportunity, fit, solution, proposal, critic))
    assert "Source: Freelancer.com" in message
    assert "https://www.freelancer.com/projects/n8n/example" in message


def test_telegram_labels_lower_scoring_deliverable_work_as_possible() -> None:
    opportunity = OpportunityRecord(
        id=uuid4(),
        platform="freelancer_alert",
        external_id="789",
        canonical_url="https://www.freelancer.com/projects/data-entry/example",
        title="Spreadsheet cleanup",
        description_clean="Clean and organize a spreadsheet.",
        status=OpportunityStatus.QUALIFIED,
    )
    fit = FitAssessment(
        breakdown=ScoreBreakdown(
            deliverability=30,
            scope_clarity=20,
            portfolio_relevance=10,
            risk_penalty=0,
        ),
        recommendation="REVIEW",
        fatal_risk=False,
        matched_skills=["spreadsheet"],
        missing_skills=[],
        major_risks=[],
        estimated_hours_min=2,
        estimated_hours_max=4,
        rationale="Plausible small project that needs normal clarification.",
        confidence=0.7,
    )
    solution = ResearchSolutionResult(
        research=ResearchReport(
            client_problem="Untidy spreadsheet",
            desired_outcome="Clean data",
            technical_requirements=[],
            business_requirements=[],
            constraints=[],
            hidden_requirements=[],
            clarification_questions=[],
        ),
        solution=SolutionDesign(
            feasible=True,
            architecture_summary="Review, normalize, and validate the spreadsheet",
            components=["spreadsheet"],
            workflow_steps=["Review", "Clean", "Validate"],
            implementation_stages=["Clean", "Quality check"],
            complexity="LOW",
            risks=[],
            missing_information=[],
            estimated_hours_min=2,
            estimated_hours_max=4,
        ),
    )
    proposal = ProposalDraft(
        proposal_text="I can clean, organize, and validate the spreadsheet, then return a clear summary of the changes.",
        estimated_hours_min=2,
        estimated_hours_max=4,
    )
    critic = CriticResult(
        approved=True,
        issues=[],
        final_proposal="I can clean, organize, and validate the spreadsheet, then return a clear summary of the changes.",
    )

    message = "\n".join(render_telegram(opportunity, fit, solution, proposal, critic))
    assert "POSSIBLE LEAD — FREELANCE MATCH: 60%" in message
    assert "FINAL PROPOSAL — COPY AND REVIEW" in message
