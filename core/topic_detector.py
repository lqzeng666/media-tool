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


# Category-specific search queries
CATEGORY_QUERIES = {
    "AI 领域": {
        "zh": ["人工智能最新进展", "AI应用落地", "大模型动态"],
        "en": ["artificial intelligence news", "AI breakthroughs", "LLM updates"],
    },
    "商业内容": {
        "zh": ["商业头条", "创业融资", "企业战略"],
        "en": ["business news", "startup funding", "corporate strategy"],
    },
    "互联网": {
        "zh": ["互联网行业动态", "科技公司新闻", "产品发布"],
        "en": ["internet industry news", "tech company updates", "product launches"],
    },
    "新闻时政": {
        "zh": ["今日要闻", "时政热点", "社会民生"],
        "en": ["breaking news today", "political news", "current events"],
    },
    "科技前沿": {
        "zh": ["前沿科技", "科学发现", "技术突破"],
        "en": ["technology breakthroughs", "science discoveries", "tech innovation"],
    },
    "财经金融": {
        "zh": ["财经头条", "股市动态", "经济趋势"],
        "en": ["finance news", "stock market", "economic trends"],
    },
}

# Fallback queries when no category specified
DEFAULT_QUERIES = {
    "zh-cn": ["今日热点", "latest news China", "科技新闻", "财经新闻"],
    "us-en": ["trending news today", "breaking news", "tech news", "business news"],
    "wt-wt": ["world news today", "global trending", "tech news", "breaking news"],
}


def _get_queries(category: str, region: str) -> list[str]:
    """Get search queries based on category and region."""
    if category and category in CATEGORY_QUERIES:
        cat = CATEGORY_QUERIES[category]
        if "zh" in region:
            return cat["zh"] + cat["en"][:1]
        else:
            return cat["en"] + cat["zh"][:1]
    return DEFAULT_QUERIES.get(region, DEFAULT_QUERIES["wt-wt"])


def fetch_trending_news(
    *,
    time_range: str = "d",
    region: str = "zh-cn",
    category: str = "",
    max_results: int = 30,
) -> list[dict]:
    """Fetch recent news headlines via DuckDuckGo."""
    from ddgs import DDGS

    queries = _get_queries(category, region)
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
你是一位资讯分析专家。以下是最近关于「{category}」的新闻标题和摘要，请从中提炼出 5-8 个热门话题。

新闻列表:
{headlines}

要求:
1. 每个话题包含标题、一句话摘要、以及 2-3 个关键词
2. 话题要有代表性，聚焦于{category}领域
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
    category: str = "",
) -> list[TrendingTopic]:
    """Detect trending topics from recent news using AI summarization."""
    news = fetch_trending_news(time_range=time_range, region=region, category=category)
    if not news:
        return []

    headlines = "\n".join(
        f"- {item.get('title', '')}：{item.get('body', '')[:100]}"
        for item in news
    )

    cat_label = category if category else "综合资讯"
    response = chat(
        messages=[{"role": "user", "content": TOPIC_EXTRACTION_PROMPT.format(
            headlines=headlines, category=cat_label,
        )}],
        temperature=0.5,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    data = json.loads(response)
    return [TrendingTopic(**t) for t in data.get("topics", [])]
