from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Iterable, List, Sequence, Tuple

try:
    from dateutil import parser
except ImportError:  # pragma: no cover
    parser = None


def normalize_company_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def make_cache_key(company_name: str) -> str:
    normalized = normalize_company_name(company_name).lower()
    digest = hashlib.sha1(normalized.encode('utf-8'), usedforsecurity=False).hexdigest()  # noqa: S324
    return f"esg:company:{digest}"


def safe_parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if parser is not None:
            parsed = parser.parse(value)
            return ensure_aware(parsed)
        parsed = datetime.fromisoformat(value)
        return ensure_aware(parsed)
    except Exception:
        return None


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo:
        return dt
    return dt.replace(tzinfo=timezone.utc)


def isoformat(dt: datetime) -> str:
    return ensure_aware(dt).isoformat()


def detect_esg_aspects(text: str, keyword_map: dict[str, Iterable[str]]) -> List[str]:
    lowered = text.lower()
    detected: List[str] = []
    for aspect, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            detected.append(aspect)
    return detected


def deduplicate_articles(entries: Sequence[dict]) -> List[dict]:
    seen: set[str] = set()
    unique: List[dict] = []
    for entry in entries:
        key_candidates: Tuple[str | None, ...] = (
            entry.get('url'),
            entry.get('title'),
        )
        unique_key = next((kc for kc in key_candidates if kc), None)
        if not unique_key:
            continue
        if unique_key in seen:
            continue
        seen.add(unique_key)
        unique.append(entry)
    return unique


def take_latest(entries: Sequence[dict], limit: int) -> List[dict]:
    sorted_entries = sorted(
        entries,
        key=lambda item: item.get('published_at') or datetime.min,
        reverse=True,
    )
    return list(sorted_entries[:limit])

