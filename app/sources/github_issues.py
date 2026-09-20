from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import NormalizedOpportunity
from app.text import canonicalize_url, clean_html, stable_hash

SOURCE_NAME = "GitHub"
ALLOWED_API_HOSTS = {"api.github.com"}


def _validate_api_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_API_HOSTS:
        raise ValueError("GitHub API URL must use HTTPS on api.github.com")


async def fetch_github_issues(
    url: str,
    queries: str,
    limit: int,
    token: str = "",
) -> list[dict[str, Any]]:
    _validate_api_url(url)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FREELY/0.2 personal opportunity assistant",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    query_list = [query.strip() for query in queries.split("||") if query.strip()]
    if not query_list:
        raise ValueError("At least one GitHub issue query is required")
    per_query = max(1, min(50, (limit + len(query_list) - 1) // len(query_list)))
    items_by_id: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, headers=headers) as client:
        for query in query_list:
            params = {"q": query, "per_page": per_query, "sort": "updated", "order": "desc"}
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                raise ValueError("GitHub returned an unexpected issue-search payload")
            for item in items:
                if isinstance(item, dict) and item.get("id") and "pull_request" not in item:
                    items_by_id[str(item["id"])] = item
    return sorted(
        items_by_id.values(),
        key=lambda item: str(item.get("updated_at") or ""),
        reverse=True,
    )[:limit]


def normalize_github_issue(raw: dict[str, Any]) -> NormalizedOpportunity:
    external_id = str(raw["id"])
    title = clean_html(str(raw.get("title") or "Untitled GitHub issue"))
    description = clean_html(str(raw.get("body") or ""))
    if not description:
        raise ValueError(f"GitHub issue {external_id} has no description")
    canonical_url = canonicalize_url(str(raw.get("html_url") or ""))
    if not canonical_url:
        raise ValueError(f"GitHub issue {external_id} has no canonical URL")
    labels = raw.get("labels") if isinstance(raw.get("labels"), list) else []
    skills = sorted(
        {
            clean_html(str(label.get("name"))).casefold()
            for label in labels
            if isinstance(label, dict) and label.get("name")
        }
    )
    repository_url = str(raw.get("repository_url") or "").rstrip("/")
    repository_name = repository_url.rsplit("/repos/", 1)[-1] if "/repos/" in repository_url else ""
    created_at = datetime.fromisoformat(str(raw["created_at"]).replace("Z", "+00:00"))
    updated_at = datetime.fromisoformat(str(raw["updated_at"]).replace("Z", "+00:00"))
    return NormalizedOpportunity(
        platform="github",
        external_id=external_id,
        canonical_url=canonical_url,
        title=title,
        description_clean=description,
        client_name=repository_name or None,
        location="Online",
        required_skills=skills,
        budget_type="paid issue or bounty; compensation requires manual verification",
        posted_at=created_at,
        source_updated_at=updated_at,
        content_hash=stable_hash(title, repository_name, description, skills, updated_at),
    )
