from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache

from .clients import LOOKBACK_DAYS, fetch_articles
from .exceptions import ESGServiceError
from .keywords import ESG_KEYWORDS
from .utils import (
    detect_esg_aspects,
    isoformat,
    make_cache_key,
    normalize_company_name,
    safe_parse_datetime,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


WEIGHTS = {
    'environment': 4,
    'social': 3,
    'governance': 3,
}


class ESGService:
    def __init__(self, cache_timeout: int = 60 * 60, max_items: int = 50) -> None:
        self.cache_timeout = cache_timeout
        self.max_items = max_items

    def get_company_esg_profile(self, company_name: str) -> Tuple[Dict[str, Any], bool]:
        normalized = normalize_company_name(company_name)
        cache_key = make_cache_key(normalized)
        cached_value = cache.get(cache_key)
        if cached_value:
            return cached_value, True

        profile = self._build_profile(normalized)
        cache.set(cache_key, profile, timeout=self.cache_timeout)
        return profile, False

    # -----------------------------------------------------------------

    def _build_profile(self, company_name: str) -> Dict[str, Any]:
        overview = self._fetch_company_overview(company_name)
        articles = fetch_articles(company_name, limit=self.max_items)
        analysis = self._analyse_articles(company_name, articles)

        now = datetime.utcnow()
        return {
            'company': company_name,
            'generated_at': isoformat(now),
            'generated_at_display': now.strftime('%b %d, %Y at %I:%M %p UTC'),
            'overview': overview,
            'overall_score': analysis.get('overall_score', 0),
            'items': analysis.get('items', []),
            'total_items': len(analysis.get('items', [])),
            'search_window_days': LOOKBACK_DAYS,
        }

    def _fetch_company_overview(self, company_name: str) -> str:
        if not self._openai_available():
            return (
                f"Overview unavailable for {company_name}. Configure OPENAI_API_KEY to enable this summary."
            )

        prompt = (
            "Provide a concise two-sentence overview of the company named "
            f"'{company_name}'. Focus on its core business, scale, and recent strategic priorities."
        )
        try:
            response_text = self._execute_openai_prompt(user_prompt=prompt)
            return response_text.strip()
        except ESGServiceError as exc:
            logger.warning('OpenAI overview request failed: %s', exc)
            return f"Overview unavailable for {company_name}."

    def _analyse_articles(self, company_name: str, articles: List[Dict]) -> Dict[str, Any]:
        if not articles:
            return {'items': [], 'overall_score': 0}

        if self._openai_available():
            try:
                return self._analyse_with_openai(company_name, articles)
            except ESGServiceError as exc:
                logger.warning('OpenAI ESG analysis failed, falling back to heuristics: %s', exc)

        return self._analyse_with_heuristics(articles)

    def _analyse_with_openai(self, company_name: str, articles: List[Dict]) -> Dict[str, Any]:
        payload = [
            {
                'title': article.get('title'),
                'description': article.get('description'),
                'url': article.get('url'),
                'source': article.get('source'),
                'published_at': isoformat(article.get('published_at')) if article.get('published_at') else None,
            }
            for article in articles
        ]

        system_prompt = (
            "You are an ESG analyst. Analyse the provided news items for "
            f"{company_name} and return a JSON report with keys 'items' and 'overall_score'. "
            "Each item must include 'title', 'description', 'date', 'source', 'url', and a 'scores' object "
            "with numeric values (0-100) for 'environment', 'social', 'governance', and 'overall'."
        )

        user_prompt = "News items JSON:\n" + json.dumps(payload) + "\n\nRespond strictly in JSON."

        response_text = self._execute_openai_prompt(user_prompt=user_prompt, system_prompt=system_prompt)
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ESGServiceError(f'Failed to parse OpenAI ESG analysis: {exc}') from exc

        items = [self._normalize_item_structure(item) for item in parsed.get('items', [])]
        items = self._sort_items_by_score(items)
        overall_score = parsed.get('overall_score')
        if overall_score is None:
            overall_score = self._compute_overall_score(items)

        return {
            'items': items,
            'overall_score': overall_score or 0,
        }

    def _analyse_with_heuristics(self, articles: List[Dict]) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        for article in articles:
            text = ' '.join(filter(None, [article.get('title', ''), article.get('description', '')]))
            aspects = detect_esg_aspects(text, ESG_KEYWORDS)
            scores = {'environment': 0, 'social': 0, 'governance': 0}
            base_score = 70
            for aspect in aspects:
                scores[aspect] = base_score
            overall = self._calculate_weighted_score(scores)
            date_iso = isoformat(article.get('published_at')) if article.get('published_at') else None
            items.append(
                {
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'date': date_iso,
                    'display_date': self._format_display_date(date_iso),
                    'source': article.get('source'),
                    'url': article.get('url'),
                    'scores': {
                        'environment': scores['environment'],
                        'social': scores['social'],
                        'governance': scores['governance'],
                        'overall': overall,
                    },
                }
            )

        items = self._sort_items_by_score(items)
        overall_score = self._compute_overall_score(items)
        return {'items': items, 'overall_score': overall_score}

    def _normalize_item_structure(self, item: Dict[str, Any]) -> Dict[str, Any]:
        scores = item.get('scores') or {}
        normalized_scores = {
            'environment': self._coerce_score(scores.get('environment')),
            'social': self._coerce_score(scores.get('social')),
            'governance': self._coerce_score(scores.get('governance')),
        }
        normalized_scores['overall'] = self._coerce_score(
            scores.get('overall'),
            default=self._calculate_weighted_score(normalized_scores),
        )

        date_value = item.get('date') or item.get('published_at')
        if isinstance(date_value, datetime):
            date_value = isoformat(date_value)
        return {
            'title': item.get('title', ''),
            'description': item.get('description', ''),
            'date': date_value,
            'display_date': self._format_display_date(date_value),
            'source': item.get('source'),
            'url': item.get('url'),
            'scores': normalized_scores,
        }

    def _compute_overall_score(self, items: List[Dict[str, Any]]) -> float:
        if not items:
            return 0.0
        valid_scores = [item.get('scores', {}).get('overall') for item in items]
        valid_scores = [score for score in valid_scores if isinstance(score, (int, float))]
        if not valid_scores:
            return 0.0
        return round(sum(valid_scores) / len(valid_scores), 2)

    def _calculate_weighted_score(self, scores: Dict[str, Any]) -> float:
        total_weight = sum(WEIGHTS.values())
        weighted_sum = (
            WEIGHTS['environment'] * self._coerce_score(scores.get('environment'))
            + WEIGHTS['social'] * self._coerce_score(scores.get('social'))
            + WEIGHTS['governance'] * self._coerce_score(scores.get('governance'))
        )
        return round(weighted_sum / total_weight, 2) if total_weight else 0.0

    def _coerce_score(self, value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(100.0, number))

    def _sort_items_by_score(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            items,
            key=lambda item: item.get('scores', {}).get('overall', 0),
            reverse=True,
        )

    def _format_display_date(self, value: Any) -> str:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = safe_parse_datetime(value) if value else None
        if not dt:
            return value or 'N/A'
        return dt.strftime('%b %d, %Y')

    def _openai_available(self) -> bool:
        return bool(OpenAI and settings.OPENAI_API_KEY)

    def _execute_openai_prompt(self, user_prompt: str, system_prompt: str | None = None) -> str:
        if not self._openai_available():
            raise ESGServiceError('OpenAI is not configured.')

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': user_prompt})

        try:
            response = client.responses.create(
                model=settings.OPENAI_MODEL,
                input=messages,
            )
        except Exception as exc:  # noqa: BLE001
            raise ESGServiceError(f'OpenAI request failed: {exc}') from exc

        try:
            return response.output_text
        except AttributeError as exc:  # pragma: no cover - API surface change
            raise ESGServiceError('Unexpected OpenAI response format.') from exc


__all__ = ['ESGService']

