"""Video composer - combines slide images + TTS audio into MP4 using ffmpeg."""
from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def compose_video(
    images: list[bytes],
    audio_bytes: bytes = None,
    seconds_per_slide: float = 5.0,
    fps: int = 1,
) -> bytes:
    """Compose a video from slide images and optional audio.

    Returns MP4 bytes.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write images
        for i, img in enumerate(images):
            (tmp / f"slide-{i:04d}.png").write_bytes(img)

        # Write audio if provided
        audio_path = None
        if audio_bytes:
            audio_path = tmp / "audio.mp3"
            audio_path.write_bytes(audio_bytes)

        output_path = tmp / "output.mp4"

        # Build ffmpeg command
        # Use image sequence as input with duration per frame
        cmd = [
            "ffmpeg", "-y",
            "-framerate", f"1/{seconds_per_slide}",
            "-i", str(tmp / "slide-%04d.png"),
        ]

        if audio_path:
            cmd.extend(["-i", str(audio_path)])

        cmd.extend([
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
        ])

        if audio_path:
            cmd.extend(["-c:a", "aac", "-shortest"])
        else:
            # Set duration based on number of slides
            total_duration = len(images) * seconds_per_slide
            cmd.extend(["-t", str(total_duration)])

        cmd.append(str(output_path))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("ffmpeg stderr: %s", result.stderr)
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        return output_path.read_bytes()
