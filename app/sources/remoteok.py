from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import NormalizedOpportunity
from app.text import canonicalize_url, clean_html, stable_hash

SOURCE_NAME = "Remote OK"
ALLOWED_API_HOSTS = {"remoteok.com", "www.remoteok.com"}


def _validate_api_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_API_HOSTS:
        raise ValueError("Remote OK API URL must use HTTPS on an official Remote OK host")


async def fetch_remoteok(url: str, limit: int) -> list[dict[str, Any]]:
    _validate_api_url(url)
    headers = {
        "Accept": "application/json",
        "User-Agent": "FREELY/0.1 personal opportunity assistant; source credited in delivery",
    }
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Remote OK returned a non-list payload")
    jobs = [item for item in payload if isinstance(item, dict) and item.get("id")]
    return jobs[:limit]


def normalize_remoteok(raw: dict[str, Any]) -> NormalizedOpportunity:
    external_id = str(raw["id"])
    title = clean_html(str(raw.get("position") or "Untitled opportunity"))
    description = clean_html(str(raw.get("description") or ""))
    if not description:
        raise ValueError(f"Remote OK item {external_id} has no description")
    tags = sorted({clean_html(str(tag)).casefold() for tag in raw.get("tags", []) if tag})
    canonical_url = canonicalize_url(str(raw.get("url") or raw.get("apply_url") or ""))
    if not canonical_url:
        raise ValueError(f"Remote OK item {external_id} has no canonical URL")
    posted_at = None
    if raw.get("date"):
        posted_at = datetime.fromisoformat(str(raw["date"]).replace("Z", "+00:00"))
    salary_min = Decimal(str(raw["salary_min"])) if raw.get("salary_min") else None
    salary_max = Decimal(str(raw["salary_max"])) if raw.get("salary_max") else None
    content_hash = stable_hash(title, raw.get("company"), description, salary_min, salary_max)
    return NormalizedOpportunity(
        platform="remoteok",
        external_id=external_id,
        canonical_url=canonical_url,
        title=title,
        description_clean=description,
        client_name=clean_html(str(raw.get("company") or "")) or None,
        location=clean_html(str(raw.get("location") or "")) or None,
        required_skills=tags,
        budget_min=salary_min,
        budget_max=salary_max,
        currency="USD" if salary_min or salary_max else None,
        budget_type="annual_salary" if salary_min or salary_max else None,
        posted_at=posted_at,
        source_updated_at=posted_at,
        content_hash=content_hash,
    )
