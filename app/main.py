from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from secrets import compare_digest
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status

from app.agents import AgentService
from app.config import Settings, get_settings
from app.db import Database
from app.models import FreelancerAlertInput, PipelineResult, ScoutResult, StatusUpdate
from app.pipeline import PipelineService
from app.telegram_commands import TelegramCommandPoller


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    database = Database(settings)
    await database.open()
    app.state.settings = settings
    app.state.database = database
    app.state.pipeline = PipelineService(settings, database, AgentService(settings))
    telegram_poller = TelegramCommandPoller(settings, app.state.pipeline)
    app.state.telegram_poller = telegram_poller
    await telegram_poller.start()
    try:
        yield
    finally:
        await telegram_poller.stop()
        await database.close()


app = FastAPI(
    title="FREELY Acquisition API",
    version="0.1.0",
    description="Human-gated opportunity evaluation and proposal drafting. No submission capability.",
    lifespan=lifespan,
)


def require_internal_token(
    request: Request,
    x_internal_token: str | None = Header(default=None),
) -> None:
    settings: Settings = request.app.state.settings
    configured_token = settings.internal_api_token.get_secret_value()
    if not configured_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API authentication is not configured",
        )
    if x_internal_token is None or not compare_digest(x_internal_token, configured_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_pipeline(request: Request) -> PipelineService:
    return request.app.state.pipeline


def get_database(request: Request) -> Database:
    return request.app.state.database


@app.get("/health")
async def health(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    return {
        "status": "ok",
        "ai_configured": settings.ai_enabled,
        "free_sources": {
            "remoteok": True,
            "jobicy": settings.jobicy_enabled,
            "remotive": settings.remotive_enabled,
            "github": settings.github_issues_enabled,
        },
        "freelancer_api_authorized": settings.freelancer_api_authorized,
        "freelancer_configured": settings.freelancer_enabled,
        "telegram_commands_configured": settings.telegram_commands_enabled,
        "submission_capability": False,
    }


@app.post(
    "/v1/scout/remoteok",
    response_model=ScoutResult,
    dependencies=[Depends(require_internal_token)],
)
async def scout_remoteok(pipeline: PipelineService = Depends(get_pipeline)) -> ScoutResult:
    return await pipeline.scout_remoteok()


@app.post(
    "/v1/scout/jobicy",
    response_model=ScoutResult,
    dependencies=[Depends(require_internal_token)],
)
async def scout_jobicy(pipeline: PipelineService = Depends(get_pipeline)) -> ScoutResult:
    return await pipeline.scout_jobicy()


@app.post(
    "/v1/scout/remotive",
    response_model=ScoutResult,
    dependencies=[Depends(require_internal_token)],
)
async def scout_remotive(pipeline: PipelineService = Depends(get_pipeline)) -> ScoutResult:
    return await pipeline.scout_remotive()


@app.post(
    "/v1/scout/github",
    response_model=ScoutResult,
    dependencies=[Depends(require_internal_token)],
)
async def scout_github(pipeline: PipelineService = Depends(get_pipeline)) -> ScoutResult:
    return await pipeline.scout_github_issues()


@app.post(
    "/v1/scout/freelancer",
    response_model=ScoutResult,
    dependencies=[Depends(require_internal_token)],
)
async def scout_freelancer(pipeline: PipelineService = Depends(get_pipeline)) -> ScoutResult:
    try:
        return await pipeline.scout_freelancer()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    "/v1/pipeline/process/{opportunity_id}",
    response_model=PipelineResult,
    dependencies=[Depends(require_internal_token)],
)
async def process_opportunity(
    opportunity_id: UUID,
    pipeline: PipelineService = Depends(get_pipeline),
) -> PipelineResult:
    try:
        return await pipeline.process(opportunity_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/v1/intake/freelancer-alert",
    dependencies=[Depends(require_internal_token)],
)
async def ingest_freelancer_alert(
    alert: FreelancerAlertInput,
    pipeline: PipelineService = Depends(get_pipeline),
) -> dict:
    try:
        result = await pipeline.ingest_freelancer_alert(alert)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["telegram_messages_sent"] = 0
    return result


@app.post("/v1/pipeline/run", dependencies=[Depends(require_internal_token)])
async def run_pipeline(
    concurrency: int = Query(default=2, ge=1, le=4),
    pipeline: PipelineService = Depends(get_pipeline),
) -> dict:
    return await pipeline.scout_and_process(concurrency)


@app.patch(
    "/v1/opportunities/{opportunity_id}/status",
    dependencies=[Depends(require_internal_token)],
)
async def update_status(
    opportunity_id: UUID,
    update: StatusUpdate,
    database: Database = Depends(get_database),
) -> dict:
    try:
        await database.apply_manual_status(opportunity_id, update)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"opportunity_id": opportunity_id, "status": update.status, "recorded": True}
