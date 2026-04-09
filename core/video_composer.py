"""Video composer - combines slide images + per-slide TTS audio into MP4."""
from __future__ import annotations

import asyncio
import io
import logging
import subprocess
import tempfile
from pathlib import Path

from core.content_structurer import PresentationOutline

logger = logging.getLogger(__name__)

NARRATION_PROMPT = """\
你是一位专业的视频旁白撰稿人。请为以下演示文稿的每一页撰写口播旁白。

标题: {title}
副标题: {subtitle}

各页内容:
{pages_content}

要求:
1. 为每一页写一段旁白（包括标题页和结尾页）
2. 语言自然流畅、有故事感，像在给朋友讲一个有趣的话题
3. 不要照搬要点原文，要用口语化的方式重新表达和扩展
4. 加入过渡语句，让各页之间衔接自然
5. 每页旁白控制在 50-120 字
6. 标题页：用引人入胜的方式介绍主题
7. 结尾页：总结要点 + 引导互动

请严格按以下 JSON 格式输出:
{{
  "narrations": ["标题页旁白", "第1页旁白", "第2页旁白", ..., "结尾页旁白"]
}}

只输出 JSON。"""


def _generate_slide_narrations(outline: PresentationOutline) -> list[str]:
    """Generate storytelling narrations for each slide using AI."""
    from core.ai_client import chat
    import json

    pages = []
    pages.append(f"[标题页] {outline.title} — {outline.subtitle}")
    for i, sec in enumerate(outline.sections, 1):
        bullets = "；".join(sec.bullets)
        pages.append(f"[第{i}页] {sec.title}: {bullets}")
    pages.append("[结尾页] 总结与互动")

    try:
        response = chat(
            messages=[{"role": "user", "content": NARRATION_PROMPT.format(
                title=outline.title,
                subtitle=outline.subtitle,
                pages_content="\n".join(pages),
            )}],
            temperature=0.8,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        data = json.loads(response)
        narrations = data.get("narrations", [])
        if narrations:
            return narrations
    except Exception as e:
        logger.warning("AI narration failed, falling back: %s", e)

    # Fallback: simple narration
    result = [f"大家好，今天我们来聊聊{outline.title}。{outline.subtitle}"]
    for sec in outline.sections:
        result.append(f"接下来看{sec.title}。" + "；".join(sec.bullets))
    result.append("以上就是今天分享的全部内容，感谢观看，我们下次再见。")
    return result


async def _generate_slide_audio(text: str, voice: str) -> bytes:
    """Generate TTS audio for a single slide's narration."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    return buf.getvalue()


async def compose_video(
    images: list[bytes],
    outline: PresentationOutline = None,
    with_audio: bool = False,
    voice: str = "zh-CN-YunxiNeural",
    seconds_per_slide: float = 5.0,
) -> bytes:
    """Compose a video from slide images + optional per-slide TTS narration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        if with_audio and outline:
            # Generate per-slide narrations and audio
            narrations = _generate_slide_narrations(outline)
            audio_files = []

            for i, (img, narr) in enumerate(zip(images, narrations)):
                # Write image
                img_path = tmp / f"slide-{i:04d}.png"
                img_path.write_bytes(img)

                # Generate audio for this slide
                try:
                    audio_bytes = await _generate_slide_audio(narr, voice)
                    audio_path = tmp / f"audio-{i:04d}.mp3"
                    audio_path.write_bytes(audio_bytes)
                    audio_files.append((img_path, audio_path))
                except Exception as e:
                    logger.warning("TTS failed for slide %d: %s", i, e)
                    audio_files.append((img_path, None))

            # Handle extra images without narration
            for i in range(len(narrations), len(images)):
                img_path = tmp / f"slide-{i:04d}.png"
                img_path.write_bytes(images[i])
                audio_files.append((img_path, None))

            # Build ffmpeg concat file: each slide shown for its audio duration
            concat_list = tmp / "concat.txt"
            segment_files = []

            for i, (img_path, audio_path) in enumerate(audio_files):
                segment_path = tmp / f"segment-{i:04d}.mp4"

                if audio_path and audio_path.exists():
                    # Slide + its audio
                    cmd = [
                        "ffmpeg", "-y",
                        "-loop", "1", "-i", str(img_path),
                        "-i", str(audio_path),
                        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black",
                        "-c:v", "libx264", "-tune", "stillimage",
                        "-c:a", "aac", "-shortest",
                        "-pix_fmt", "yuv420p",
                        "-preset", "ultrafast",
                        str(segment_path),
                    ]
                else:
                    # Slide without audio, show for fixed duration
                    cmd = [
                        "ffmpeg", "-y",
                        "-loop", "1", "-i", str(img_path),
                        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black",
                        "-c:v", "libx264", "-tune", "stillimage",
                        "-t", str(seconds_per_slide),
                        "-pix_fmt", "yuv420p",
                        "-preset", "ultrafast",
                        str(segment_path),
                    ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    logger.error("ffmpeg segment %d failed: %s", i, result.stderr[-300:])
                    continue

                segment_files.append(segment_path)

            # Concatenate all segments
            with open(concat_list, "w") as f:
                for seg in segment_files:
                    f.write(f"file '{seg}'\n")

            output_path = tmp / "output.mp4"
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg concat failed: {result.stderr[-500:]}")

        else:
            # No audio - simple slideshow
            for i, img in enumerate(images):
                (tmp / f"slide-{i:04d}.png").write_bytes(img)

            output_path = tmp / "output.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-framerate", f"1/{seconds_per_slide}",
                "-i", str(tmp / "slide-%04d.png"),
                "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                "-t", str(len(images) * seconds_per_slide),
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        return output_path.read_bytes()
