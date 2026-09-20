from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.models import NormalizedOpportunity
from app.text import canonicalize_url, clean_html, stable_hash

SOURCE_NAME = "Freelancer.com"
ALLOWED_API_HOSTS = {"www.freelancer.com", "www.freelancer-sandbox.com"}


def _validate_api_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_API_HOSTS:
        raise ValueError("Freelancer API URL must use HTTPS on an official Freelancer host")


async def fetch_freelancer_projects(
    api_url: str,
    oauth_token: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    _validate_api_url(api_url)
    if not oauth_token:
        raise ValueError("FREELANCER_OAUTH_TOKEN is not configured")
    headers = {
        "Accept": "application/json",
        "Freelancer-OAuth-V1": oauth_token,
        "User-Agent": "FREELY/0.2 personal opportunity assistant",
    }
    params = {
        "query": query,
        "limit": limit,
        "offset": 0,
        "or_search_query": True,
        "sort_field": "time_updated",
        "reverse_sort": True,
        "full_description": True,
        "job_details": True,
    }
    endpoint = urljoin(api_url.rstrip("/") + "/", "projects/active/")
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, headers=headers) as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        payload = response.json()
    result = payload.get("result") if isinstance(payload, dict) else None
    projects = result.get("projects") if isinstance(result, dict) else None
    if not isinstance(projects, list):
        raise ValueError("Freelancer API returned an unexpected project-search payload")
    return [item for item in projects if isinstance(item, dict) and item.get("id")][:limit]


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (OSError, TypeError, ValueError):
        return None


def _job_names(raw: dict[str, Any]) -> list[str]:
    jobs = raw.get("jobs") or []
    return sorted(
        {
            clean_html(str(job.get("name"))).casefold()
            for job in jobs
            if isinstance(job, dict) and job.get("name")
        }
    )


def normalize_freelancer(raw: dict[str, Any]) -> NormalizedOpportunity:
    external_id = str(raw["id"])
    title = clean_html(str(raw.get("title") or "Untitled Freelancer project"))
    description = clean_html(str(raw.get("description") or raw.get("preview_description") or ""))
    if not description:
        raise ValueError(f"Freelancer project {external_id} has no description")
    seo_url = str(raw.get("seo_url") or "").strip("/")
    if not seo_url:
        raise ValueError(f"Freelancer project {external_id} has no canonical URL")
    canonical_url = canonicalize_url(f"https://www.freelancer.com/projects/{seo_url}")

    budget = raw.get("budget") if isinstance(raw.get("budget"), dict) else {}
    currency_data = raw.get("currency") if isinstance(raw.get("currency"), dict) else {}
    location_data = raw.get("location") if isinstance(raw.get("location"), dict) else {}
    country_data = (
        location_data.get("country") if isinstance(location_data.get("country"), dict) else {}
    )
    location = ", ".join(
        part
        for part in [
            clean_html(str(location_data.get("city") or "")),
            clean_html(str(country_data.get("name") or "")),
        ]
        if part
    )
    budget_min = _decimal(budget.get("minimum"))
    budget_max = _decimal(budget.get("maximum"))
    currency = clean_html(str(currency_data.get("code") or "")) or None
    project_type = clean_html(str(raw.get("type") or "")).casefold() or None
    posted_at = _timestamp(raw.get("submitdate"))
    updated_at = _timestamp(raw.get("time_updated"))
    skills = _job_names(raw)
    return NormalizedOpportunity(
        platform="freelancer",
        external_id=external_id,
        canonical_url=canonical_url,
        title=title,
        description_clean=description,
        location=location or None,
        required_skills=skills,
        budget_min=budget_min,
        budget_max=budget_max,
        currency=currency,
        budget_type=project_type,
        posted_at=posted_at,
        source_updated_at=updated_at,
        content_hash=stable_hash(
            title, description, skills, budget_min, budget_max, currency, updated_at
        ),
    )
