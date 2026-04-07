"""Podcast generation using Edge TTS (free Microsoft TTS, supports Chinese)."""
from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path

from core.ai_client import chat
from core.content_structurer import PresentationOutline

logger = logging.getLogger(__name__)

SCRIPT_PROMPT = """\
你是一位专业的播客主持人。请根据以下演示文稿大纲，撰写一份播客讲稿。

标题: {title}
副标题: {subtitle}

章节内容:
{sections}

要求:
1. 用口语化、自然流畅的中文撰写
2. 开头有引人入胜的开场白
3. 每个章节之间有自然过渡
4. 结尾有总结和收尾语
5. 总时长控制在 3-5 分钟阅读量（约 800-1200 字）
6. 不要加任何标记或标签，只输出纯文本讲稿

直接输出讲稿内容。"""


def generate_podcast_script(outline: PresentationOutline) -> str:
    """Generate a podcast script from a presentation outline."""
    sections_text = ""
    for i, sec in enumerate(outline.sections, 1):
        bullets = "\n".join(f"  - {b}" for b in sec.bullets)
        sections_text += f"\n第{i}章: {sec.title}\n{bullets}\n"

    response = chat(
        messages=[{
            "role": "user",
            "content": SCRIPT_PROMPT.format(
                title=outline.title,
                subtitle=outline.subtitle,
                sections=sections_text,
            ),
        }],
        temperature=0.8,
        max_tokens=4096,
    )
    return response


async def generate_audio(text: str, voice: str = "zh-CN-YunxiNeural") -> bytes:
    """Generate audio from text using Edge TTS. Returns MP3 bytes."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def generate_podcast(outline: PresentationOutline, voice: str = "zh-CN-YunxiNeural") -> tuple[str, bytes]:
    """Generate a full podcast: script + audio. Returns (script_text, mp3_bytes)."""
    script = generate_podcast_script(outline)
    audio = await generate_audio(script, voice)
    return script, audio


def save_podcast(script: str, audio_bytes: bytes, output_dir: str | Path) -> tuple[Path, Path]:
    """Save podcast script and audio to files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    script_path = out / "podcast_script.txt"
    audio_path = out / "podcast.mp3"
    script_path.write_text(script, encoding="utf-8")
    audio_path.write_bytes(audio_bytes)
    return script_path, audio_path
