from dataclasses import dataclass

from app.models import NormalizedOpportunity

RELEVANT_TERMS = {
    "airtable",
    "ai chatbot",
    "ai content",
    "n8n",
    "automation",
    "automation troubleshooting",
    "blog draft",
    "chatbot",
    "competitor research",
    "content formatting",
    "crm",
    "csv processing",
    "dashboard",
    "data cleanup",
    "data collection",
    "data conversion",
    "data entry",
    "document extraction",
    "document formatting",
    "workflow",
    "webhook",
    "api integration",
    "openai",
    "gemini",
    "excel",
    "faq bot",
    "file renaming",
    "google workspace",
    "telegram bot",
    "google sheets",
    "gmail",
    "landing page",
    "lead generation",
    "lead pipeline",
    "make.com",
    "market research",
    "ocr",
    "ai agent",
    "product description",
    "prompt engineering",
    "recruitment automation",
    "report automation",
    "research report",
    "resume formatting",
    "social media content",
    "spreadsheet",
    "data extraction",
    "virtual assistant",
    "web research",
    "web scraping",
    "website maintenance",
    "wordpress",
    "zapier",
    "python automation",
}

CONTRACT_TERMS = {
    "contract",
    "contractor",
    "freelance",
    "freelancer",
    "consultant",
    "consulting",
    "project-based",
    "short-term",
    "temporary",
}

DISALLOWED_TERMS = {
    "academic cheating",
    "bypass captcha",
    "captcha bypass",
    "credential theft",
    "fake engagement",
    "fake reviews",
    "mass messaging",
    "unpaid trial",
    "pay a fee",
    "purchase equipment from",
    "scrape behind login",
    "send spam",
    "telegram interview only",
    "crypto payment only",
}


@dataclass(frozen=True)
class PrefilterDecision:
    accepted: bool
    relevant_terms: tuple[str, ...]
    contract_terms: tuple[str, ...]
    hard_reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "relevant_terms": list(self.relevant_terms),
            "contract_terms": list(self.contract_terms),
            "hard_reasons": list(self.hard_reasons),
        }


def evaluate(
    opportunity: NormalizedOpportunity,
    contract_only: bool = True,
    require_relevant: bool = True,
) -> PrefilterDecision:
    haystack = " ".join(
        [
            opportunity.title,
            opportunity.description_clean,
            " ".join(opportunity.required_skills),
            opportunity.budget_type or "",
        ]
    ).casefold()
    relevant = tuple(sorted(term for term in RELEVANT_TERMS if term in haystack))
    contracts = tuple(sorted(term for term in CONTRACT_TERMS if term in haystack))
    reasons = []
    for term in DISALLOWED_TERMS:
        if term in haystack:
            reasons.append(f"disallowed signal: {term}")
    if require_relevant and not relevant:
        reasons.append("no relevant supported-service capability signal")
    if contract_only and not contracts:
        reasons.append("not clearly contract or freelance work")
    return PrefilterDecision(not reasons, relevant, contracts, tuple(reasons))
