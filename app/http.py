"""Shared HTTP client for frontend -> backend calls, bypassing system proxy."""

import os

import httpx

from core.config import settings

# Ensure localhost requests bypass any system proxy
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")
if "localhost" not in os.environ.get("NO_PROXY", ""):
    os.environ["NO_PROXY"] = os.environ["NO_PROXY"] + ",localhost,127.0.0.1"


def _url(path: str) -> str:
    return f"{settings.backend_url}{path}"


def api_post(path: str, *, json: dict = None, timeout: float = 60.0) -> httpx.Response:
    """POST to the backend API."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(_url(path), json=json)
        resp.raise_for_status()
        return resp


def api_get(path: str, *, timeout: float = 30.0) -> httpx.Response:
    """GET from the backend API."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(_url(path))
        resp.raise_for_status()
        return resp


def api_delete(path: str, *, timeout: float = 10.0) -> httpx.Response:
    """DELETE from the backend API."""
    with httpx.Client(timeout=timeout) as client:
        resp = client.delete(_url(path))
        resp.raise_for_status()
        return resp
