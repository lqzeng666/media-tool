"""AI image generation via DashScope (阿里通义万象)."""
from __future__ import annotations

import time
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

DASHSCOPE_SUBMIT_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
DASHSCOPE_TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"


def _headers():
    return {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }


def generate_image(
    prompt: str,
    *,
    model: str = "wanx-v1",
    size: str = "1024*1024",
    n: int = 1,
    timeout: float = 120.0,
) -> list[str]:
    """Generate images via DashScope. Returns list of image URLs.

    Args:
        prompt: Text description for image generation
        model: Model name (wanx-v1, wanx2.1-t2i-turbo, etc.)
        size: Image size like "1024*1024"
        n: Number of images
        timeout: Max wait time in seconds
    """
    # Submit task
    with httpx.Client(timeout=30, proxy=None) as client:
        resp = client.post(
            DASHSCOPE_SUBMIT_URL,
            headers=_headers(),
            json={
                "model": model,
                "input": {"prompt": prompt},
                "parameters": {"size": size, "n": n},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    task_id = data["output"]["task_id"]
    logger.info("DashScope task submitted: %s", task_id)

    # Poll for result
    start = time.time()
    while time.time() - start < timeout:
        with httpx.Client(timeout=30, proxy=None) as client:
            resp = client.get(
                DASHSCOPE_TASK_URL.format(task_id=task_id),
                headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        status = data["output"]["task_status"]
        if status == "SUCCEEDED":
            results = data["output"].get("results", [])
            return [r["url"] for r in results if r.get("url")]
        elif status in ("FAILED", "UNKNOWN"):
            msg = data["output"].get("message", "Unknown error")
            raise RuntimeError(f"DashScope image generation failed: {msg}")

        time.sleep(3)

    raise TimeoutError(f"DashScope task {task_id} timed out after {timeout}s")


def download_image(url: str) -> bytes:
    """Download image from URL, returns bytes."""
    with httpx.Client(timeout=30, proxy=None) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content
