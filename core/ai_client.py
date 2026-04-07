from __future__ import annotations

from typing import Optional

from openai import OpenAI

from core.config import settings

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


def chat(
    messages: list[dict],
    *,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> str:
    """Send a chat completion request and return the assistant message content."""
    kwargs: dict = {
        "model": model or settings.deepseek_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    resp = get_client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""
