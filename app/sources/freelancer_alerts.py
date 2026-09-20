import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.models import FreelancerAlertInput, NormalizedOpportunity
from app.text import clean_html, stable_hash

_PLAIN_URL_RE = re.compile(r"https://(?:www\.)?freelancer\.com/projects/[^\s<>\"']+", re.I)
_TRAILING_PUNCTUATION = ".,;:!?)]}"


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        self._href = dict(attrs).get("href")
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._href:
            self.links.append((self._href, clean_html(" ".join(self._text))))
            self._href = None
            self._text = []


def canonical_project_url(value: str) -> str | None:
    """Return a strict, tracking-free Freelancer project URL or None."""
    candidate = value.strip().rstrip(_TRAILING_PUNCTUATION)
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme.casefold() != "https" or parts.hostname not in {
        "freelancer.com",
        "www.freelancer.com",
    }:
        return None
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/")
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 3 or segments[0].casefold() != "projects":
        return None
    return urlunsplit(("https", "www.freelancer.com", path, "", ""))


def split_freelancer_alert(alert: FreelancerAlertInput) -> list[dict[str, Any]]:
    """Split one official alert email into one raw item per unique project URL."""
    parser = _LinkParser()
    parser.feed(alert.html or "")
    candidates = list(parser.links)
    combined = "\n".join(part for part in (alert.text, alert.html) if part)
    candidates.extend((match.group(0), "") for match in _PLAIN_URL_RE.finditer(combined))

    unique: dict[str, str] = {}
    for href, anchor_text in candidates:
        url = canonical_project_url(href)
        if url and url not in unique:
            unique[url] = anchor_text
    if not unique:
        raise ValueError("Alert contains no valid Freelancer.com project link")

    payload = alert.model_dump(mode="json")
    return [
        {**payload, "project_url": url, "anchor_text": anchor_text}
        for url, anchor_text in unique.items()
    ]


def normalize_freelancer_alert(raw: dict[str, Any]) -> NormalizedOpportunity:
    url = canonical_project_url(str(raw.get("project_url") or ""))
    if not url:
        raise ValueError("Invalid Freelancer.com project URL")
    subject = clean_html(str(raw.get("subject") or "Freelancer project alert"))
    anchor = clean_html(str(raw.get("anchor_text") or ""))
    generic_anchors = {"view project", "view job", "see details", "bid now", "apply now"}
    title = anchor if anchor and anchor.casefold() not in generic_anchors else subject
    description = clean_html(str(raw.get("text") or ""))
    if not description:
        description = clean_html(str(raw.get("html") or ""))
    if not description:
        description = subject
    external_id = stable_hash(url)[:32]
    return NormalizedOpportunity(
        platform="freelancer_alert",
        external_id=external_id,
        canonical_url=url,
        title=title[:500],
        description_clean=description,
        budget_type="Official Freelancer job alert; verify budget on linked project page",
        source_updated_at=raw.get("received_at"),
        content_hash=stable_hash(url, title, description),
    )
