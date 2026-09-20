from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.agents import AgentService, validate_claim_ids
from app.config import Settings
from app.db import Database
from app.models import FreelancerAlertInput, OpportunityStatus, PipelineResult, ScoutResult
from app.prefilter import evaluate
from app.sources.freelancer import fetch_freelancer_projects, normalize_freelancer
from app.sources.freelancer_alerts import normalize_freelancer_alert, split_freelancer_alert
from app.sources.github_issues import fetch_github_issues, normalize_github_issue
from app.sources.jobicy import fetch_jobicy, normalize_jobicy
from app.sources.remoteok import fetch_remoteok, normalize_remoteok
from app.sources.remotive import fetch_remotive, normalize_remotive
from app.telegram import render_telegram
from app.text import stable_hash


class PipelineService:
    def __init__(self, settings: Settings, database: Database, agents: AgentService):
        self.settings = settings
        self.database = database
        self.agents = agents

    async def scout_remoteok(self) -> ScoutResult:
        async def fetch() -> list[dict[str, Any]]:
            return await fetch_remoteok(self.settings.remoteok_api_url, self.settings.scout_limit)

        return await self._scout("remoteok", fetch, normalize_remoteok, contract_only=True)

    async def scout_jobicy(self) -> ScoutResult:
        async def fetch() -> list[dict[str, Any]]:
            return await fetch_jobicy(
                self.settings.jobicy_api_url,
                self.settings.jobicy_scout_limit,
            )

        return await self._scout("jobicy", fetch, normalize_jobicy, contract_only=True)

    async def scout_remotive(self) -> ScoutResult:
        async def fetch() -> list[dict[str, Any]]:
            return await fetch_remotive(
                self.settings.remotive_api_url,
                self.settings.remotive_scout_limit,
            )

        return await self._scout("remotive", fetch, normalize_remotive, contract_only=True)

    async def scout_github_issues(self) -> ScoutResult:
        async def fetch() -> list[dict[str, Any]]:
            return await fetch_github_issues(
                self.settings.github_api_url,
                self.settings.github_issue_queries,
                self.settings.github_scout_limit,
                self.settings.github_token.get_secret_value(),
            )

        # The configured query is restricted to paid issues and bounties. Compensation and
        # scope still require human verification before any external action.
        return await self._scout("github", fetch, normalize_github_issue, contract_only=False)

    async def scout_freelancer(self) -> ScoutResult:
        if not self.settings.freelancer_api_authorized:
            raise PermissionError(
                "Freelancer API access is disabled until express written permission is confirmed"
            )
        freelancer_token = self.settings.freelancer_oauth_token.get_secret_value()
        if not freelancer_token:
            raise RuntimeError("FREELANCER_OAUTH_TOKEN is not configured")

        async def fetch() -> list[dict[str, Any]]:
            return await fetch_freelancer_projects(
                self.settings.freelancer_api_url,
                freelancer_token,
                self.settings.freelancer_search_query,
                self.settings.freelancer_scout_limit,
            )

        # Freelancer projects are contract work by definition, so requiring the words
        # "contract" or "freelance" in every project description would create false rejects.
        return await self._scout("freelancer", fetch, normalize_freelancer, contract_only=False)

    async def ingest_freelancer_alert(self, alert: FreelancerAlertInput) -> dict[str, Any]:
        raw_items = split_freelancer_alert(alert)

        async def fetch() -> list[dict[str, Any]]:
            return raw_items

        scout = await self._scout(
            "freelancer_alert",
            fetch,
            normalize_freelancer_alert,
            contract_only=False,
            require_relevant=False,
        )
        return {
            "scout": scout.model_dump(mode="json"),
            "queued": len(scout.opportunity_ids),
            "processed": [],
            "notifications": [],
            "mode": "queued_until_telegram_go",
        }

    async def process_pending_freelancer_alerts(self) -> dict[str, Any]:
        opportunity_ids = await self.database.get_processable_ids_for_platform(
            "freelancer_alert",
            self.settings.pipeline_process_limit,
        )
        processed: list[dict[str, Any]] = []
        notifications: list[str] = []
        errors: list[dict[str, str]] = []
        details_needed = 0
        for opportunity_id in opportunity_ids:
            opportunity = await self.database.get_opportunity(opportunity_id)
            if len(opportunity.description_clean) < self.settings.freelancer_min_description_chars:
                notifications.append(
                    "FREELANCER ALERT — DETAILS NEEDED\n\n"
                    f"Project: {opportunity.title}\n"
                    f"Exact link: {opportunity.canonical_url}\n\n"
                    "The official alert did not include enough project detail to create a safe, "
                    "specific proposal. Open the link and review the full brief; FREELY did not "
                    "guess or submit anything."
                )
                await self.database.update_status(
                    opportunity_id,
                    OpportunityStatus.REJECTED,
                    "Official alert did not include enough project detail",
                    "freelancer-alert-gate",
                )
                details_needed += 1
                continue
            try:
                result = await self.process(opportunity_id)
                processed.append(result.model_dump(mode="json"))
            except Exception as exc:
                errors.append(
                    {"opportunity_id": str(opportunity_id), "error": str(exc)[:1000]}
                )
        return {
            "processed": processed,
            "notifications": notifications,
            "queued_found": len(opportunity_ids),
            "details_needed": details_needed,
            "errors": errors,
        }

    async def _scout(
        self,
        platform_slug: str,
        fetch: Callable[[], Awaitable[list[dict[str, Any]]]],
        normalize: Callable[[dict[str, Any]], Any],
        *,
        contract_only: bool,
        require_relevant: bool = True,
    ) -> ScoutResult:
        run_id = await self.database.begin_source_run(platform_slug)
        inserted = 0
        updated = 0
        rejected = 0
        ids: list[UUID] = []
        raw_items: list[dict] = []
        try:
            raw_items = await fetch()
            for raw in raw_items:
                try:
                    normalized = normalize(raw)
                    decision = evaluate(
                        normalized,
                        contract_only and self.settings.scout_contract_only,
                        require_relevant,
                    )
                    normalized.prefilter = decision.as_dict()
                    opportunity_id, was_inserted = await self.database.upsert_opportunity(
                        run_id, raw, normalized
                    )
                    if decision.accepted:
                        ids.append(opportunity_id)
                    else:
                        rejected += 1
                        await self.database.update_status(
                            opportunity_id,
                            OpportunityStatus.REJECTED,
                            "; ".join(decision.hard_reasons),
                            "prefilter",
                        )
                    if was_inserted:
                        inserted += 1
                    else:
                        updated += 1
                except (ValueError, TypeError):
                    rejected += 1
            await self.database.finish_source_run(
                run_id,
                status="COMPLETED",
                fetched=len(raw_items),
                inserted=inserted,
                duplicates=updated,
                rejected=rejected,
            )
        except Exception as exc:
            await self.database.finish_source_run(
                run_id,
                status="FAILED",
                fetched=len(raw_items),
                inserted=inserted,
                duplicates=updated,
                rejected=rejected,
                error=str(exc)[:2000],
            )
            raise
        return ScoutResult(
            platform=platform_slug,
            source_run_id=run_id,
            fetched=len(raw_items),
            inserted=inserted,
            updated=updated,
            prefilter_rejected=rejected,
            opportunity_ids=ids,
        )

    async def process(self, opportunity_id: UUID) -> PipelineResult:
        if not self.settings.ai_enabled:
            return PipelineResult(
                opportunity_id=opportunity_id,
                status=OpportunityStatus.DISCOVERED,
                deliver=False,
                reason="OPENAI_API_KEY is not configured",
            )
        opportunity = await self.database.get_opportunity(opportunity_id)
        if opportunity.status not in {
            OpportunityStatus.DISCOVERED,
            OpportunityStatus.QUALIFIED,
        }:
            return PipelineResult(
                opportunity_id=opportunity_id,
                status=opportunity.status,
                deliver=False,
                reason=f"Opportunity is already {opportunity.status}",
            )
        capabilities = await self.database.get_capabilities()
        approved_claims = await self.database.get_approved_claims()

        fit, fit_usage = await self._run_logged(
            opportunity_id,
            "fit",
            "fit.v1",
            self.settings.ai_fast_model,
            stable_hash(opportunity.model_dump_json(), capabilities),
            self.agents.fit(opportunity, capabilities),
        )
        fit_data = fit.model_dump(mode="json")
        fit_data["score"] = fit.score
        await self.database.save_fit(opportunity_id, fit_data, self.settings.ai_fast_model)
        if fit.fatal_risk or fit.recommendation == "REJECT":
            reason = (
                f"Fit gate failed: score={fit.score}, recommendation={fit.recommendation}, "
                f"fatal_risk={fit.fatal_risk}"
            )
            await self.database.update_status(
                opportunity_id, OpportunityStatus.REJECTED, reason, "fit-agent"
            )
            return PipelineResult(
                opportunity_id=opportunity_id,
                status=OpportunityStatus.REJECTED,
                deliver=False,
                reason=reason,
            )

        await self.database.update_status(
            opportunity_id, OpportunityStatus.QUALIFIED, "fit gate passed", "fit-agent"
        )
        solution, solution_usage = await self._run_logged(
            opportunity_id,
            "research-solution",
            "research-solution.v1",
            self.settings.ai_quality_model,
            stable_hash(opportunity.model_dump_json(), fit.model_dump_json(), capabilities),
            self.agents.research_solution(opportunity, fit, capabilities),
        )
        solution_data = solution.model_dump(mode="json")
        await self.database.save_solution(
            opportunity_id, solution_data, self.settings.ai_quality_model
        )
        if not solution.solution.feasible:
            reason = "Solution Agent did not find a realistic implementation approach"
            await self.database.update_status(
                opportunity_id, OpportunityStatus.REJECTED, reason, "solution-agent"
            )
            return PipelineResult(
                opportunity_id=opportunity_id,
                status=OpportunityStatus.REJECTED,
                deliver=False,
                reason=reason,
            )

        proposal, proposal_usage = await self._run_logged(
            opportunity_id,
            "proposal",
            "proposal.v1",
            self.settings.ai_quality_model,
            stable_hash(opportunity.model_dump_json(), solution.model_dump_json(), approved_claims),
            self.agents.proposal(opportunity, fit, solution, approved_claims),
        )
        validate_claim_ids(proposal.claims_used, approved_claims)

        critic, critic_usage = await self._run_logged(
            opportunity_id,
            "critic",
            "critic.v1",
            self.settings.ai_quality_model,
            stable_hash(opportunity.model_dump_json(), proposal.model_dump_json(), approved_claims),
            self.agents.critique(opportunity, proposal, approved_claims),
        )
        validate_claim_ids(critic.claims_used, approved_claims)
        await self.database.save_proposal(
            opportunity_id,
            proposal.model_dump(mode="json"),
            critic.model_dump(mode="json"),
            self.settings.ai_quality_model,
        )
        await self.database.update_status(
            opportunity_id,
            OpportunityStatus.PROPOSAL_READY,
            "proposal passed deterministic claim validation",
            "critic-agent",
        )
        chunks = render_telegram(
            opportunity,
            fit,
            solution,
            proposal,
            critic,
            strong_threshold=self.settings.strong_lead_threshold,
        )
        await self.database.save_delivery(opportunity_id, chunks)
        return PipelineResult(
            opportunity_id=opportunity_id,
            status=OpportunityStatus.PROPOSAL_READY,
            deliver=True,
            telegram_chunks=chunks,
        )

    async def _run_logged(
        self,
        opportunity_id: UUID,
        agent_name: str,
        prompt_version: str,
        model: str,
        input_hash: str,
        awaitable,
    ):
        try:
            output, usage = await awaitable
            await self.database.record_agent_run(
                opportunity_id=opportunity_id,
                agent_name=agent_name,
                prompt_version=prompt_version,
                model=model,
                input_hash=input_hash,
                status="COMPLETED",
                output=output.model_dump(mode="json"),
                usage=usage,
            )
            return output, usage
        except Exception as exc:
            await self.database.record_agent_run(
                opportunity_id=opportunity_id,
                agent_name=agent_name,
                prompt_version=prompt_version,
                model=model,
                input_hash=input_hash,
                status="FAILED",
                error=str(exc)[:4000],
            )
            raise

    async def scout_and_process(self, concurrency: int = 2) -> dict:
        """Process only user-queued Freelancer alerts.

        The public job feeds remain available as source adapters, but they are intentionally not
        part of the Telegram command path. This keeps each run focused on marketplace gigs the
        user explicitly chose through Freelancer saved-search alerts.
        """
        freelancer_alerts = await self.process_pending_freelancer_alerts()
        processed = freelancer_alerts["processed"]
        errors = freelancer_alerts["errors"]
        return {
            "mode": "freelancer_alerts_only",
            "scouts": [],
            "source_errors": [],
            "source_skipped": [],
            "processable_found": freelancer_alerts["queued_found"],
            "processing_limit": self.settings.pipeline_process_limit,
            "deferred_by_limit": 0,
            "processed": processed,
            "freelancer_alerts": freelancer_alerts,
            "errors": errors,
        }
