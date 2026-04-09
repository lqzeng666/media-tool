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
    timeout: float = 180.0,
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


def submit_task(prompt: str, size: str = "1024*1024", model: str = "wanx-v1") -> str:
    """Submit an image generation task. Returns task_id."""
    with httpx.Client(timeout=30, proxy=None) as client:
        resp = client.post(
            DASHSCOPE_SUBMIT_URL,
            headers=_headers(),
            json={
                "model": model,
                "input": {"prompt": prompt},
                "parameters": {"size": size, "n": 1},
            },
        )
        resp.raise_for_status()
        return resp.json()["output"]["task_id"]


def poll_task(task_id: str, timeout: float = 120.0) -> list[str]:
    """Poll a submitted task until completion. Returns image URLs."""
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
            return [r["url"] for r in data["output"].get("results", []) if r.get("url")]
        elif status in ("FAILED", "UNKNOWN"):
            raise RuntimeError(data["output"].get("message", "Failed"))
        time.sleep(3)
    raise TimeoutError(f"Task {task_id} timed out")


def generate_batch(prompts: list[str], size: str = "1024*1024") -> list[bytes]:
    """Generate multiple images in parallel. Returns list of image bytes."""
    # Submit all tasks at once
    task_ids = []
    for prompt in prompts:
        try:
            tid = submit_task(prompt, size=size)
            task_ids.append(tid)
            logger.info("Submitted task %s", tid)
        except Exception as e:
            logger.warning("Failed to submit task: %s", e)
            task_ids.append(None)

    # Poll all tasks
    results = []
    for i, tid in enumerate(task_ids):
        if tid is None:
            results.append(b"")
            continue
        try:
            urls = poll_task(tid, timeout=120)
            if urls:
                results.append(download_image(urls[0]))
            else:
                results.append(b"")
        except Exception as e:
            logger.warning("Task %d failed: %s", i, e)
            results.append(b"")

    return results


def generate_and_download(prompt: str, size: str = "1024*1024") -> bytes:
    """Generate one image and return its bytes. Returns empty bytes on failure."""
    try:
        urls = generate_image(prompt, size=size, timeout=120)
        if urls:
            return download_image(urls[0])
    except Exception as e:
        logger.warning("Image generation failed: %s", e)
    return b""


def generate_illustrations_for_outline(outline) -> list[bytes]:
    """Generate one illustration per section using image_prompt field.

    Returns list of image bytes (one per section). Empty bytes for failures.
    """
    images = []
    for i, sec in enumerate(outline.sections):
        prompt = sec.image_prompt or f"Professional illustration about: {sec.title}"
        prompt += ". Clean, modern, flat design illustration, no text, suitable as a presentation visual."
        logger.info("Generating illustration %d/%d: %s", i + 1, len(outline.sections), sec.title)
        img = generate_and_download(prompt, size="1280*720")
        images.append(img)
    return images
