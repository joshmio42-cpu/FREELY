import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import Settings
from app.models import NormalizedOpportunity, OpportunityRecord, OpportunityStatus, StatusUpdate


class Database:
    def __init__(self, settings: Settings):
        self.pool = AsyncConnectionPool(
            conninfo=settings.database_url.get_secret_value(),
            min_size=1,
            max_size=8,
            open=False,
            kwargs={"row_factory": dict_row},
        )

    async def open(self) -> None:
        await self.pool.open()
        await self.pool.wait()

    async def close(self) -> None:
        await self.pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[Any]:
        async with self.pool.connection() as conn:
            yield conn

    async def begin_source_run(self, platform_slug: str) -> UUID:
        async with self.connection() as conn:
            row = await conn.execute(
                """
                INSERT INTO source_runs (platform_id)
                SELECT id FROM platforms WHERE slug = %s AND enabled = true
                RETURNING id
                """,
                (platform_slug,),
            )
            result = await row.fetchone()
            if not result:
                raise LookupError(f"Enabled platform not found: {platform_slug}")
            return result["id"]

    async def finish_source_run(
        self,
        source_run_id: UUID,
        *,
        status: str,
        fetched: int = 0,
        inserted: int = 0,
        duplicates: int = 0,
        rejected: int = 0,
        error: str | None = None,
    ) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                UPDATE source_runs
                SET finished_at = now(), status = %s, fetched_count = %s, new_count = %s,
                    duplicate_count = %s, rejected_count = %s, error = %s
                WHERE id = %s
                """,
                (status, fetched, inserted, duplicates, rejected, error, source_run_id),
            )

    async def upsert_opportunity(
        self,
        source_run_id: UUID,
        raw: dict,
        normalized: NormalizedOpportunity,
    ) -> tuple[UUID, bool]:
        raw_json = json.dumps(raw, default=str)
        raw_hash = normalized.content_hash
        async with self.connection() as conn:
            platform = await (
                await conn.execute(
                    "SELECT id FROM platforms WHERE slug = %s", (normalized.platform,)
                )
            ).fetchone()
            if not platform:
                raise LookupError(f"Platform not configured: {normalized.platform}")
            platform_id = platform["id"]
            raw_row = await (
                await conn.execute(
                    """
                    INSERT INTO raw_opportunities
                      (platform_id, source_run_id, external_id, payload, payload_sha256)
                    VALUES (%s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (platform_id, external_id, payload_sha256)
                    DO UPDATE SET fetched_at = now()
                    RETURNING id
                    """,
                    (platform_id, source_run_id, normalized.external_id, raw_json, raw_hash),
                )
            ).fetchone()
            client_id = None
            if normalized.client_name:
                client_row = await (
                    await conn.execute(
                        """
                        INSERT INTO clients (platform_id, external_id, display_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (platform_id, external_id) WHERE external_id IS NOT NULL
                        DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = now()
                        RETURNING id
                        """,
                        (platform_id, normalized.client_name.casefold(), normalized.client_name),
                    )
                ).fetchone()
                client_id = client_row["id"]

            existing = await (
                await conn.execute(
                    "SELECT id, content_hash FROM opportunities WHERE platform_id = %s AND external_id = %s",
                    (platform_id, normalized.external_id),
                )
            ).fetchone()
            inserted = existing is None
            prefilter_json = json.dumps(normalized.prefilter)
            skills_json = json.dumps(normalized.required_skills)
            row = await (
                await conn.execute(
                    """
                    INSERT INTO opportunities (
                      platform_id, raw_opportunity_id, client_id, external_id, canonical_url,
                      title, description_clean, location, required_skills, budget_min, budget_max,
                      currency, budget_type, posted_at, source_updated_at, content_hash, prefilter
                    ) VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                      %s::jsonb
                    )
                    ON CONFLICT (platform_id, external_id) DO UPDATE SET
                      raw_opportunity_id = EXCLUDED.raw_opportunity_id,
                      client_id = EXCLUDED.client_id,
                      canonical_url = EXCLUDED.canonical_url,
                      title = EXCLUDED.title,
                      description_clean = EXCLUDED.description_clean,
                      location = EXCLUDED.location,
                      required_skills = EXCLUDED.required_skills,
                      budget_min = EXCLUDED.budget_min,
                      budget_max = EXCLUDED.budget_max,
                      currency = EXCLUDED.currency,
                      budget_type = EXCLUDED.budget_type,
                      posted_at = EXCLUDED.posted_at,
                      source_updated_at = EXCLUDED.source_updated_at,
                      content_hash = EXCLUDED.content_hash,
                      prefilter = EXCLUDED.prefilter,
                      updated_at = now()
                    RETURNING id
                    """,
                    (
                        platform_id,
                        raw_row["id"],
                        client_id,
                        normalized.external_id,
                        str(normalized.canonical_url),
                        normalized.title,
                        normalized.description_clean,
                        normalized.location,
                        skills_json,
                        normalized.budget_min,
                        normalized.budget_max,
                        normalized.currency,
                        normalized.budget_type,
                        normalized.posted_at,
                        normalized.source_updated_at,
                        normalized.content_hash,
                        prefilter_json,
                    ),
                )
            ).fetchone()
            opportunity_id = row["id"]
            if inserted:
                await conn.execute(
                    """
                    INSERT INTO status_history (opportunity_id, from_status, to_status, reason, actor)
                    VALUES (%s, NULL, 'DISCOVERED', 'source ingestion', 'scout')
                    """,
                    (opportunity_id,),
                )
            return opportunity_id, inserted

    async def get_opportunity(self, opportunity_id: UUID) -> OpportunityRecord:
        async with self.connection() as conn:
            row = await (
                await conn.execute(
                    """
                    SELECT o.id, p.slug AS platform, o.external_id, o.canonical_url, o.title,
                           o.description_clean, c.display_name AS client_name, o.location,
                           o.required_skills, o.budget_min, o.budget_max, o.currency,
                           o.budget_type, o.posted_at, o.status, o.prefilter
                    FROM opportunities o
                    JOIN platforms p ON p.id = o.platform_id
                    LEFT JOIN clients c ON c.id = o.client_id
                    WHERE o.id = %s
                    """,
                    (opportunity_id,),
                )
            ).fetchone()
        if not row:
            raise LookupError(f"Opportunity not found: {opportunity_id}")
        return OpportunityRecord.model_validate(row)

    async def filter_processable_opportunity_ids(self, opportunity_ids: list[UUID]) -> list[UUID]:
        if not opportunity_ids:
            return []
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT id FROM opportunities
                    WHERE id = ANY(%s) AND status IN ('DISCOVERED', 'QUALIFIED')
                    """,
                    (opportunity_ids,),
                )
            ).fetchall()
        processable = {row["id"] for row in rows}
        return [opportunity_id for opportunity_id in opportunity_ids if opportunity_id in processable]

    async def get_processable_ids_for_platform(
        self,
        platform_slug: str,
        limit: int,
    ) -> list[UUID]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT o.id
                    FROM opportunities o
                    JOIN platforms p ON p.id = o.platform_id
                    WHERE p.slug = %s AND o.status IN ('DISCOVERED', 'QUALIFIED')
                    ORDER BY o.discovered_at ASC
                    LIMIT %s
                    """,
                    (platform_slug, limit),
                )
            ).fetchall()
        return [row["id"] for row in rows]

    async def get_capabilities(self) -> list[dict]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT slug, name, proficiency, evidence, limitations
                    FROM capabilities WHERE active = true ORDER BY proficiency DESC, name
                    """
                )
            ).fetchall()
        return list(rows)

    async def get_approved_claims(self) -> list[dict]:
        async with self.connection() as conn:
            rows = await (
                await conn.execute(
                    "SELECT id, claim_text, evidence FROM approved_claims WHERE active = true ORDER BY id"
                )
            ).fetchall()
        return list(rows)

    async def update_status(
        self, opportunity_id: UUID, status: OpportunityStatus, reason: str | None, actor: str
    ) -> None:
        async with self.connection() as conn:
            current = await (
                await conn.execute(
                    "SELECT status FROM opportunities WHERE id = %s", (opportunity_id,)
                )
            ).fetchone()
            if not current:
                raise LookupError(f"Opportunity not found: {opportunity_id}")
            old_status = current["status"]
            await conn.execute(
                """
                UPDATE opportunities SET status = %s, rejection_reason = CASE WHEN %s = 'REJECTED'
                  THEN %s ELSE rejection_reason END, updated_at = now() WHERE id = %s
                """,
                (status.value, status.value, reason, opportunity_id),
            )
            if old_status != status.value:
                await conn.execute(
                    """
                    INSERT INTO status_history (opportunity_id, from_status, to_status, reason, actor)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (opportunity_id, old_status, status.value, reason, actor),
                )

    async def save_fit(self, opportunity_id: UUID, result: dict, model: str) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO fit_assessments
                  (opportunity_id, score, recommendation, fatal_risk, result, prompt_version, model)
                VALUES (%s, %s, %s, %s, %s::jsonb, 'fit.v1', %s)
                """,
                (
                    opportunity_id,
                    result["score"],
                    result["recommendation"],
                    result["fatal_risk"],
                    json.dumps(result),
                    model,
                ),
            )

    async def save_solution(self, opportunity_id: UUID, result: dict, model: str) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO research_solution_reports
                  (opportunity_id, feasible, result, prompt_version, model)
                VALUES (%s, %s, %s::jsonb, 'research-solution.v1', %s)
                """,
                (opportunity_id, result["solution"]["feasible"], json.dumps(result), model),
            )

    async def save_proposal(
        self,
        opportunity_id: UUID,
        proposal: dict,
        critic: dict,
        model: str,
    ) -> None:
        async with self.connection() as conn:
            version_row = await (
                await conn.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM proposal_versions WHERE opportunity_id = %s",
                    (opportunity_id,),
                )
            ).fetchone()
            await conn.execute(
                """
                INSERT INTO proposal_versions (
                  opportunity_id, version, stage, proposal_text, suggested_bid, currency,
                  estimated_hours_min, estimated_hours_max, claims_used, critic_result,
                  prompt_version, model
                ) VALUES (%s, %s, 'FINAL', %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                          'proposal-critic.v1', %s)
                """,
                (
                    opportunity_id,
                    version_row["version"],
                    critic["final_proposal"],
                    proposal.get("suggested_bid"),
                    proposal.get("currency"),
                    proposal["estimated_hours_min"],
                    proposal["estimated_hours_max"],
                    json.dumps(critic.get("claims_used", [])),
                    json.dumps(critic),
                    model,
                ),
            )

    async def record_agent_run(
        self,
        *,
        opportunity_id: UUID,
        agent_name: str,
        prompt_version: str,
        model: str,
        input_hash: str,
        status: str,
        output: dict | None = None,
        usage: dict | None = None,
        error: str | None = None,
    ) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_runs (
                  opportunity_id, agent_name, prompt_version, model, status, input_hash,
                  output, usage, error, finished_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, now())
                """,
                (
                    opportunity_id,
                    agent_name,
                    prompt_version,
                    model,
                    status,
                    input_hash,
                    json.dumps(output) if output is not None else None,
                    json.dumps(usage) if usage is not None else None,
                    error,
                ),
            )

    async def save_delivery(self, opportunity_id: UUID, chunks: list[str]) -> None:
        async with self.connection() as conn:
            await conn.execute(
                """
                INSERT INTO deliveries (opportunity_id, channel, payload)
                VALUES (%s, 'telegram', %s::jsonb)
                """,
                (opportunity_id, json.dumps({"chunks": chunks})),
            )

    async def apply_manual_status(self, opportunity_id: UUID, update: StatusUpdate) -> None:
        await self.update_status(opportunity_id, update.status, update.reason, "user")
        if update.status in {
            OpportunityStatus.SUBMITTED,
            OpportunityStatus.CLIENT_REPLIED,
            OpportunityStatus.INTERVIEW,
            OpportunityStatus.WON,
            OpportunityStatus.LOST,
        }:
            now = datetime.now(UTC)
            submitted_at = now if update.status == OpportunityStatus.SUBMITTED else None
            replied_at = now if update.status == OpportunityStatus.CLIENT_REPLIED else None
            interview_at = now if update.status == OpportunityStatus.INTERVIEW else None
            async with self.connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO applications (
                      opportunity_id, actual_bid, currency, submitted_at, client_replied_at,
                      interview_at, final_project_value, outcome_notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (opportunity_id) DO UPDATE SET
                      actual_bid = COALESCE(EXCLUDED.actual_bid, applications.actual_bid),
                      currency = COALESCE(EXCLUDED.currency, applications.currency),
                      submitted_at = COALESCE(EXCLUDED.submitted_at, applications.submitted_at),
                      client_replied_at = COALESCE(EXCLUDED.client_replied_at, applications.client_replied_at),
                      interview_at = COALESCE(EXCLUDED.interview_at, applications.interview_at),
                      final_project_value = COALESCE(EXCLUDED.final_project_value, applications.final_project_value),
                      outcome_notes = COALESCE(EXCLUDED.outcome_notes, applications.outcome_notes),
                      updated_at = now()
                    """,
                    (
                        opportunity_id,
                        update.actual_bid,
                        update.currency,
                        submitted_at,
                        replied_at,
                        interview_at,
                        update.final_project_value,
                        update.reason,
                    ),
                )
