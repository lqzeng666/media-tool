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


def _generate_slide_narrations(outline: PresentationOutline) -> list[str]:
    """Generate a short narration text for each slide, matching the slide content."""
    narrations = []

    # Title slide
    narrations.append(f"{outline.title}。{outline.subtitle}")

    # Content slides
    for sec in outline.sections:
        points = "；".join(sec.bullets)
        narrations.append(f"{sec.title}。{points}")

    # End slide
    narrations.append("以上就是本次内容的全部分享，感谢观看。")

    return narrations


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
