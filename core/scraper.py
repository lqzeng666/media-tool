from __future__ import annotations

import asyncio
import json
import logging

import httpx
import trafilatura

from core.config import settings

logger = logging.getLogger(__name__)

# Sites known to require browser rendering
JS_HEAVY_DOMAINS = {"zhihu.com", "weibo.com", "bilibili.com", "douyin.com", "toutiao.com"}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


class SourceMaterial:
    def __init__(self, url: str, title: str, text: str):
        self.url = url
        self.title = title
        self.text = text
        self.word_count = len(text)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "word_count": self.word_count,
        }


def _needs_browser(url: str) -> bool:
    """Check if the URL likely needs browser rendering."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    return any(d in domain for d in JS_HEAVY_DOMAINS)


async def fetch_url_httpx(url: str, *, timeout: float = 30.0) -> str:
    """Fetch raw HTML via httpx with enhanced headers."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers=BROWSER_HEADERS,
        proxy=None,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_url_playwright(url: str, *, timeout: float = 45.0) -> str:
    """Fetch rendered HTML via Playwright (headless Chromium)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=BROWSER_HEADERS["User-Agent"],
            locale="zh-CN",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            # Extra wait for dynamic content
            await asyncio.sleep(2)
            html = await page.content()
            return html
        finally:
            await browser.close()


async def fetch_url(url: str, *, timeout: float = 30.0) -> str:
    """Fetch HTML with automatic fallback: httpx first, Playwright if needed."""
    use_browser = _needs_browser(url)

    if not use_browser:
        try:
            html = await fetch_url_httpx(url, timeout=timeout)
            # Check if we got meaningful content (not just a shell)
            if len(html) > 2000:
                return html
            logger.info("httpx got thin HTML for %s, falling back to Playwright", url)
        except Exception as e:
            logger.info("httpx failed for %s: %s, falling back to Playwright", url, e)

    # Playwright fallback
    try:
        return await fetch_url_playwright(url, timeout=45.0)
    except Exception as e:
        if use_browser:
            raise
        # If Playwright also fails and httpx didn't raise, try httpx as last resort
        return await fetch_url_httpx(url, timeout=timeout)


def extract_article(html: str, url: str) -> SourceMaterial:
    """Extract article text from HTML using trafilatura."""
    text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
    metadata = trafilatura.extract(
        html, output_format="json", include_comments=False
    )

    title = ""
    if metadata:
        try:
            meta = json.loads(metadata)
            title = meta.get("title", "")
        except (json.JSONDecodeError, TypeError):
            pass

    # Truncate to max length
    if len(text) > settings.max_source_length:
        text = text[: settings.max_source_length] + "\n...(truncated)"

    return SourceMaterial(url=url, title=title or url, text=text)


async def fetch_and_extract(url: str) -> SourceMaterial:
    """Fetch a URL and extract article content."""
    html = await fetch_url(url)
    return extract_article(html, url)
