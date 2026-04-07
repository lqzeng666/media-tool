import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from backend.models.source import FetchRequest, FetchResponse, SourceMaterialResponse
from core.scraper import fetch_and_extract
from core.web_searcher import search_articles, search_news

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.post("/fetch", response_model=FetchResponse)
async def fetch_sources(req: FetchRequest):
    """Fetch and extract content from provided URLs."""
    materials = []
    errors = []

    async def _fetch_one(url: str):
        try:
            result = await fetch_and_extract(url)
            materials.append(
                SourceMaterialResponse(
                    url=result.url,
                    title=result.title,
                    text=result.text,
                    word_count=result.word_count,
                )
            )
        except Exception as e:
            errors.append(f"{url}: {e}")

    await asyncio.gather(*[_fetch_one(url) for url in req.urls])
    return FetchResponse(materials=materials, errors=errors)


class SearchRequest(BaseModel):
    query: str
    max_results: int = 8
    time_range: str = "w"
    region: str = "zh-cn"
    search_type: str = "news"  # "news" or "web"


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


@router.post("/search", response_model=SearchResponse)
async def search_sources(req: SearchRequest):
    """Search the web for articles related to a query."""
    if req.search_type == "news":
        raw = search_news(
            req.query,
            max_results=req.max_results,
            region=req.region,
            time_range=req.time_range,
        )
        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("body", ""),
            )
            for r in raw
            if r.get("url")
        ]
    else:
        raw = search_articles(
            req.query,
            max_results=req.max_results,
            region=req.region,
            time_range=req.time_range,
        )
        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
            for r in raw
            if r.get("href")
        ]

    return SearchResponse(results=results)
