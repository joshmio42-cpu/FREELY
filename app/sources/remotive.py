from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import NormalizedOpportunity
from app.text import canonicalize_url, clean_html, stable_hash

SOURCE_NAME = "Remotive"
ALLOWED_API_HOSTS = {"remotive.com", "www.remotive.com"}


def _validate_api_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_API_HOSTS:
        raise ValueError("Remotive API URL must use HTTPS on an official Remotive host")


async def fetch_remotive(url: str, limit: int) -> list[dict[str, Any]]:
    _validate_api_url(url)
    headers = {
        "Accept": "application/json",
        "User-Agent": "FREELY/0.2 personal opportunity assistant; Remotive credited in delivery",
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, headers=headers) as client:
        response = await client.get(url, params={"limit": limit})
        response.raise_for_status()
        payload = response.json()
    jobs = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(jobs, list):
        raise ValueError("Remotive returned an unexpected jobs payload")
    return [item for item in jobs if isinstance(item, dict) and item.get("id")][:limit]


def normalize_remotive(raw: dict[str, Any]) -> NormalizedOpportunity:
    external_id = str(raw["id"])
    title = clean_html(str(raw.get("title") or "Untitled Remotive opportunity"))
    description = clean_html(str(raw.get("description") or ""))
    if not description:
        raise ValueError(f"Remotive item {external_id} has no description")
    canonical_url = canonicalize_url(str(raw.get("url") or ""))
    if not canonical_url:
        raise ValueError(f"Remotive item {external_id} has no canonical URL")
    tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
    skills = sorted(
        {
            clean_html(str(value)).casefold()
            for value in [raw.get("category"), *tags]
            if value
        }
    )
    posted_at = None
    if raw.get("publication_date"):
        posted_at = datetime.fromisoformat(str(raw["publication_date"]).replace("Z", "+00:00"))
    job_type = clean_html(str(raw.get("job_type") or "")).casefold() or None
    return NormalizedOpportunity(
        platform="remotive",
        external_id=external_id,
        canonical_url=canonical_url,
        title=title,
        description_clean=description,
        client_name=clean_html(str(raw.get("company_name") or "")) or None,
        location=clean_html(str(raw.get("candidate_required_location") or "")) or None,
        required_skills=skills,
        budget_type=job_type,
        posted_at=posted_at,
        source_updated_at=posted_at,
        content_hash=stable_hash(title, raw.get("company_name"), description, job_type, posted_at),
    )
