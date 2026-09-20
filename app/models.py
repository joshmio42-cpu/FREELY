from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class OpportunityStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    REJECTED = "REJECTED"
    QUALIFIED = "QUALIFIED"
    PROPOSAL_READY = "PROPOSAL_READY"
    SUBMITTED = "SUBMITTED"
    CLIENT_REPLIED = "CLIENT_REPLIED"
    INTERVIEW = "INTERVIEW"
    WON = "WON"
    LOST = "LOST"


class NormalizedOpportunity(BaseModel):
    platform: str
    external_id: str
    canonical_url: HttpUrl
    title: str = Field(min_length=1, max_length=500)
    description_clean: str = Field(min_length=1)
    client_name: str | None = None
    location: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    currency: str | None = None
    budget_type: str | None = None
    posted_at: datetime | None = None
    source_updated_at: datetime | None = None
    content_hash: str
    prefilter: dict = Field(default_factory=dict)


class OpportunityRecord(BaseModel):
    id: UUID
    platform: str
    external_id: str
    canonical_url: str
    title: str
    description_clean: str
    client_name: str | None = None
    location: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    budget_min: Decimal | None = None
    budget_max: Decimal | None = None
    currency: str | None = None
    budget_type: str | None = None
    posted_at: datetime | None = None
    status: OpportunityStatus
    prefilter: dict = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    deliverability: int = Field(ge=0, le=50)
    scope_clarity: int = Field(ge=0, le=30)
    portfolio_relevance: int = Field(ge=0, le=20)
    risk_penalty: int = Field(ge=-40, le=0)

    @property
    def total(self) -> int:
        raw = (
            self.deliverability
            + self.scope_clarity
            + self.portfolio_relevance
            + self.risk_penalty
        )
        return max(0, min(100, raw))


class FitAssessment(BaseModel):
    breakdown: ScoreBreakdown
    recommendation: str = Field(pattern="^(PROCEED|REJECT|REVIEW)$")
    fatal_risk: bool
    matched_skills: list[str]
    missing_skills: list[str]
    major_risks: list[str]
    estimated_hours_min: float = Field(ge=0)
    estimated_hours_max: float = Field(ge=0)
    rationale: str
    confidence: float = Field(ge=0, le=1)

    @field_validator("estimated_hours_max")
    @classmethod
    def max_not_negative(cls, value: float) -> float:
        return value

    @property
    def score(self) -> int:
        return self.breakdown.total


class ResearchReport(BaseModel):
    client_problem: str
    desired_outcome: str
    technical_requirements: list[str]
    business_requirements: list[str]
    constraints: list[str]
    hidden_requirements: list[str]
    clarification_questions: list[str]


class SolutionDesign(BaseModel):
    feasible: bool
    architecture_summary: str
    components: list[str]
    workflow_steps: list[str]
    implementation_stages: list[str]
    complexity: str = Field(pattern="^(LOW|MODERATE|HIGH|UNKNOWN)$")
    risks: list[str]
    missing_information: list[str]
    estimated_hours_min: float = Field(ge=0)
    estimated_hours_max: float = Field(ge=0)


class ResearchSolutionResult(BaseModel):
    research: ResearchReport
    solution: SolutionDesign


class ProposalDraft(BaseModel):
    proposal_text: str = Field(min_length=40, max_length=3000)
    suggested_bid: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    estimated_hours_min: float = Field(ge=0)
    estimated_hours_max: float = Field(ge=0)
    claims_used: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


class CriticResult(BaseModel):
    approved: bool
    issues: list[str]
    final_proposal: str = Field(min_length=40, max_length=3000)
    claims_used: list[str] = Field(default_factory=list)


class ScoutResult(BaseModel):
    platform: str
    source_run_id: UUID
    fetched: int
    inserted: int
    updated: int
    prefilter_rejected: int
    opportunity_ids: list[UUID]


class PipelineResult(BaseModel):
    opportunity_id: UUID
    status: OpportunityStatus
    deliver: bool
    reason: str | None = None
    telegram_chunks: list[str] = Field(default_factory=list)


class FreelancerAlertInput(BaseModel):
    """A Freelancer job-alert email forwarded by a user-controlled mailbox."""

    subject: str = Field(min_length=1, max_length=1000)
    text: str = ""
    html: str = ""
    message_id: str | None = Field(default=None, max_length=1000)
    sender: str | None = Field(default=None, max_length=1000)
    received_at: datetime | None = None


class StatusUpdate(BaseModel):
    status: OpportunityStatus
    reason: str | None = None
    actual_bid: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    final_project_value: Decimal | None = Field(default=None, ge=0)
