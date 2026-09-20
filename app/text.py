import hashlib
import html
import re

import bleach

_SPACE_RE = re.compile(r"\s+")


def clean_html(value: str) -> str:
    """Convert source HTML into compact plain text without retaining executable content."""
    without_tags = bleach.clean(value or "", tags=[], attributes={}, strip=True)
    decoded = html.unescape(without_tags)
    return _SPACE_RE.sub(" ", decoded).strip()


def stable_hash(*parts: object) -> str:
    joined = "\x1f".join(str(part or "").strip().casefold() for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def canonicalize_url(value: str) -> str:
    return (
        value.strip()
        .replace("http://remoteOK.com", "https://remoteok.com")
        .replace("https://remoteOK.com", "https://remoteok.com")
    )
