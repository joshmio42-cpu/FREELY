from app.models import (
    CriticResult,
    FitAssessment,
    OpportunityRecord,
    ProposalDraft,
    ResearchSolutionResult,
)


def _budget(opportunity: OpportunityRecord, proposal: ProposalDraft) -> str:
    if proposal.suggested_bid is not None:
        currency = proposal.currency or opportunity.currency or ""
        return f"Suggested bid: {currency} {proposal.suggested_bid}".strip()
    if opportunity.budget_min is not None or opportunity.budget_max is not None:
        low = opportunity.budget_min if opportunity.budget_min is not None else "?"
        high = opportunity.budget_max if opportunity.budget_max is not None else "?"
        return f"Source budget: {opportunity.currency or ''} {low}–{high}".strip()
    return "Suggested bid: needs clarification"


def render_telegram(
    opportunity: OpportunityRecord,
    fit: FitAssessment,
    solution: ResearchSolutionResult,
    proposal: ProposalDraft,
    critic: CriticResult,
    *,
    strong_threshold: int = 70,
) -> list[str]:
    lead_label = "STRONG LEAD" if fit.score >= strong_threshold else "POSSIBLE LEAD"
    skills = ", ".join(fit.matched_skills[:8]) or "No confirmed matches"
    gaps = ", ".join(fit.missing_skills[:6]) or "None significant"
    architecture = " → ".join(solution.solution.workflow_steps[:8])
    gig_link = (
        "QUALIFIED OPPORTUNITY\n\n"
        f"Project: {opportunity.title}\n"
        f"Platform: {_source_name(opportunity.platform)}\n\n"
        "EXACT GIG LINK\n"
        f"{opportunity.canonical_url}"
    )
    header = (
        f"{lead_label} — FREELANCE MATCH: {fit.score}%\n\n"
        f"Client/company: {opportunity.client_name or 'Not provided'}\n"
        f"Difficulty: {solution.solution.complexity.title()}\n"
        f"Estimated work: {solution.solution.estimated_hours_min:g}–"
        f"{solution.solution.estimated_hours_max:g} hours\n"
        f"{_budget(opportunity, proposal)}\n\n"
        f"Skill match: {skills}\n"
        f"Potential gaps: {gaps}\n\n"
        f"WHY IT MATCHES\n{fit.rationale}\n\n"
        f"PROPOSED SOLUTION\n{architecture or solution.solution.architecture_summary}"
    )
    proposal_message = (
        "FINAL PROPOSAL — COPY AND REVIEW\n\n"
        f"{critic.final_proposal}\n\n"
        "Manual review required. This system does not submit bids or applications.\n"
        f"Source: {_source_name(opportunity.platform)}"
    )
    return _split_chunks([gig_link, header, proposal_message])


def _source_name(platform: str) -> str:
    return {
        "remoteok": "Remote OK",
        "jobicy": "Jobicy",
        "remotive": "Remotive",
        "github": "GitHub",
        "freelancer": "Freelancer.com",
        "freelancer_alert": "Freelancer.com",
    }.get(platform, platform)


def _split_chunks(sections: list[str], limit: int = 3900) -> list[str]:
    chunks: list[str] = []
    for section in sections:
        remaining = section.strip()
        while len(remaining) > limit:
            split_at = remaining.rfind("\n", 0, limit)
            if split_at < limit // 2:
                split_at = limit
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            chunks.append(remaining)
    return chunks
