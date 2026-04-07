"""Trending topic detection using DuckDuckGo news search."""
from __future__ import annotations

import json
import logging
from typing import Optional

from pydantic import BaseModel

from core.ai_client import chat

logger = logging.getLogger(__name__)


class TrendingTopic(BaseModel):
    title: str
    summary: str
    keywords: list[str]


# Search queries by region to get broad news coverage
REGION_QUERIES = {
    "zh-cn": ["今日热点", "latest news China", "科技新闻", "财经新闻"],
    "us-en": ["trending news today", "breaking news", "tech news", "business news"],
    "wt-wt": ["world news today", "global trending", "tech news", "breaking news"],
}


def fetch_trending_news(
    *,
    time_range: str = "d",
    region: str = "zh-cn",
    max_results: int = 30,
) -> list[dict]:
    """Fetch recent news headlines via DuckDuckGo.

    Args:
        time_range: "d" (day), "w" (week), "m" (month)
        region: region code, e.g. "zh-cn", "us-en"
        max_results: max number of headlines to fetch
    """
    from ddgs import DDGS

    queries = REGION_QUERIES.get(region, REGION_QUERIES["wt-wt"])
    per_query = max(max_results // len(queries), 5)
    all_results = []

    with DDGS() as ddgs:
        for query in queries:
            try:
                results = list(ddgs.news(
                    query,
                    region=region,
                    timelimit=time_range,
                    max_results=per_query,
                ))
                all_results.extend(results)
            except Exception as e:
                logger.warning("DuckDuckGo news search failed for '%s': %s", query, e)
                continue

    # Deduplicate by title
    seen = set()
    unique = []
    for r in all_results:
        title = r.get("title", "")
        if title and title not in seen:
            seen.add(title)
            unique.append(r)

    return unique[:max_results]


TOPIC_EXTRACTION_PROMPT = """\
你是一位资讯分析专家。以下是最近的新闻标题和摘要，请从中提炼出 5-8 个热门话题。

新闻列表:
{headlines}

要求:
1. 每个话题包含标题、一句话摘要、以及 2-3 个关键词
2. 话题要有代表性，覆盖不同领域（科技、财经、社会等）
3. 按热度排序

请严格按以下 JSON 格式输出:
{{
  "topics": [
    {{
      "title": "话题标题",
      "summary": "一句话摘要",
      "keywords": ["关键词1", "关键词2"]
    }}
  ]
}}

只输出 JSON，不要输出其他内容。"""


def detect_trending_topics(
    *,
    time_range: str = "d",
    region: str = "zh-cn",
) -> list[TrendingTopic]:
    """Detect trending topics from recent news using AI summarization."""
    news = fetch_trending_news(time_range=time_range, region=region)
    if not news:
        return []

    # Format headlines
    headlines = "\n".join(
        f"- {item.get('title', '')}：{item.get('body', '')[:100]}"
        for item in news
    )

    response = chat(
        messages=[{"role": "user", "content": TOPIC_EXTRACTION_PROMPT.format(headlines=headlines)}],
        temperature=0.5,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    data = json.loads(response)
    return [TrendingTopic(**t) for t in data.get("topics", [])]
