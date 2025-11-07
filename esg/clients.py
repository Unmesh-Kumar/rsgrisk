from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from django.conf import settings

from dotenv import load_dotenv

from .keywords import ALL_KEYWORDS
from .utils import deduplicate_articles, safe_parse_datetime, take_latest


dotenv_path = Path(getattr(settings, 'BASE_DIR', '.')) / '.env'
try:  # Ensure environment variables are available before accessing OpenAI keys
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except PermissionError:
    pass


try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


LOOKBACK_DAYS = 730


def fetch_articles(company_name: str, limit: int = 50) -> List[Dict]:
    if not (OpenAI and settings.OPENAI_API_KEY):
        logger.warning('OpenAI is not configured; skipping web search for ESG articles.')
        return []

    keywords = ', '.join(sorted(ALL_KEYWORDS))
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = (
        'You are an ESG research assistant. Use the web_search tool to find recent (last 2 years) '
        'news items describing environmental, social, or governance risks involving the requested company. Make the search less strict and retrieve several relevant results. '
        'Return strictly valid JSON with a top-level key "articles" containing a list of objects with '
        'keys: title, description, url, source, published_at (ISO 8601). Include up to {limit} distinct articles '
        'from credible sources. Focus on risk/controversy narratives, not generic corporate press releases.'
    ).format(limit=limit)

    user_prompt = (
        f"Company: {company_name}\n"
        f"Time horizon: last {LOOKBACK_DAYS} days (approx. 2 years).\n"
        f"Relevant ESG keywords: {keywords}.\n"
        "Provide concise descriptions summarising the ESG risk highlighted by each article."
    )

    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            input=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            tools=[{'type': 'web_search'}],
            max_output_tokens=2000,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning('OpenAI web search request failed: %s', exc)
        return []

    try:
        response_text = response.output_text
    except AttributeError:  # pragma: no cover - API change
        logger.warning('Unexpected response structure from OpenAI web search.')
        return []

    try:
        payload = _parse_articles_payload(response_text)
    except json.JSONDecodeError as exc:
        logger.warning('Failed to parse OpenAI web search response: %s\nResponse snippet: %.200s', exc, response_text)
        return []

    articles: List[Dict] = []
    for item in payload.get('articles', []):
        published_at = safe_parse_datetime(item.get('published_at')) or datetime.utcnow()
        articles.append(
            {
                'title': item.get('title', ''),
                'description': item.get('description', ''),
                'url': item.get('url'),
                'source': item.get('source'),
                'published_at': published_at,
                'source_type': 'openai_web_search',
            }
        )

    unique_articles = deduplicate_articles(articles)
    return take_latest(unique_articles, limit)


def _parse_articles_payload(raw_text: str) -> Dict:
    """Extract JSON payload from the LLM response, handling markdown fences."""
    text = raw_text.strip()

    # Attempt direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Look for fenced code blocks
    fenced_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    for block in fenced_blocks:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    # Fallback: slice between first and last brace
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        return json.loads(candidate)

    raise json.JSONDecodeError('Unable to extract JSON object from response.', text, 0)

