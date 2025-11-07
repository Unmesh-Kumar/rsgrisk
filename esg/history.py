from __future__ import annotations

from typing import List

from django.utils import timezone

from dashboard.models import SearchHistory
from .utils import normalize_company_name


class SearchHistoryRepository:
    """Repository for user search history stored in the relational database."""

    def record_search(self, user_id: int, company_name: str) -> None:
        if not user_id or not company_name:
            return
        company_label = normalize_company_name(company_name)
        SearchHistory.objects.create(
            user_id=user_id,
            company_name=company_label,
            searched_at=timezone.now(),
        )

    def get_recent_searches(self, user_id: int, limit: int = 10) -> List[dict]:
        if not user_id:
            return []
        qs = SearchHistory.objects.filter(user_id=user_id).order_by('-searched_at')
        seen = set()
        results: List[dict] = []
        for entry in qs:
            key = entry.company_name.lower()
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    'company_name': entry.company_name,
                    'searched_at': entry.searched_at,
                }
            )
            if len(results) >= limit:
                break
        return results

