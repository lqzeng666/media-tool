"""Web search for auto-fetching source materials on a given topic."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def search_articles(
    query: str,
    *,
    max_results: int = 8,
    region: str = "zh-cn",
    time_range: str = "w",
) -> list[dict]:
    """Search for articles related to a query using DuckDuckGo.

    Returns list of dicts with keys: title, href, body.
    """
    from ddgs import DDGS

    with DDGS() as ddgs:
        try:
            results = list(ddgs.text(
                query,
                region=region,
                timelimit=time_range,
                max_results=max_results,
            ))
        except Exception as e:
            logger.warning("DuckDuckGo text search failed for '%s': %s", query, e)
            results = []

    # Fallback: try without region/time filter
    if not results:
        logger.info("Retrying search without region filter for '%s'", query)
        with DDGS() as ddgs:
            try:
                results = list(ddgs.text(
                    query,
                    max_results=max_results,
                ))
            except Exception as e:
                logger.warning("DuckDuckGo fallback text search failed: %s", e)
                results = []

    return results


def search_news(
    query: str,
    *,
    max_results: int = 8,
    region: str = "zh-cn",
    time_range: str = "w",
) -> list[dict]:
    """Search for news articles related to a query using DuckDuckGo.

    Returns list of dicts with keys: title, url, body, date, source.
    Falls back to web search if news search returns no results.
    """
    from ddgs import DDGS

    # Try news search
    with DDGS() as ddgs:
        try:
            results = list(ddgs.news(
                query,
                region=region,
                timelimit=time_range,
                max_results=max_results,
            ))
            if results:
                return results
        except Exception as e:
            logger.warning("DuckDuckGo news search failed for '%s': %s", query, e)

    # Fallback: news search without filters
    with DDGS() as ddgs:
        try:
            results = list(ddgs.news(
                query,
                max_results=max_results,
            ))
            if results:
                return results
        except Exception as e:
            logger.warning("DuckDuckGo news fallback failed: %s", e)

    # Final fallback: use web search and adapt format
    logger.info("Falling back to web search for '%s'", query)
    articles = search_articles(query, max_results=max_results, region=region, time_range=time_range)
    return [
        {
            "title": a.get("title", ""),
            "url": a.get("href", ""),
            "body": a.get("body", ""),
        }
        for a in articles
    ]
