"""Shared HTTP client for frontend -> backend calls, bypassing system proxy."""

import os

import httpx

from core.config import settings

# Ensure localhost requests bypass any system proxy
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
if "localhost" not in os.environ.get("NO_PROXY", ""):
    os.environ["NO_PROXY"] = os.environ["NO_PROXY"] + ",localhost,127.0.0.1"


def api_post(path: str, *, json: dict = None, timeout: float = 60.0) -> httpx.Response:
    """POST to the backend API, bypassing any system proxy."""
    url = f"{settings.backend_url}{path}"
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=json)
        resp.raise_for_status()
        return resp
