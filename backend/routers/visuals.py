import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from backend.models.visual import GeneratePPTRequest
from core.ppt_generator import generate_ppt
from core.content_structurer import PresentationOutline
from core.infographic_generator import render_slides_to_images, prepare_slide_deck_content
from core.podcast_generator import generate_podcast_script, generate_audio

router = APIRouter(prefix="/api/visuals", tags=["visuals"])


@router.post("/generate-ppt")
async def create_ppt(req: GeneratePPTRequest):
    """Generate a PowerPoint presentation from an outline."""
    ppt_bytes = generate_ppt(req.outline)
    return Response(
        content=ppt_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": "attachment; filename=presentation.pptx"},
    )


class SlideImagesRequest(BaseModel):
    outline: PresentationOutline


@router.post("/generate-slide-images")
async def create_slide_images(req: SlideImagesRequest):
    """Generate slide images from an outline. Returns JSON with base64 images."""
    import base64
    images = await render_slides_to_images(req.outline)
    result = [base64.b64encode(img).decode() for img in images]
    return {"images": result, "count": len(result)}


class ContentFileRequest(BaseModel):
    outline: PresentationOutline


@router.post("/prepare-slide-deck-content")
async def prepare_content(req: ContentFileRequest):
    """Prepare markdown content for baoyu-slide-deck skill."""
    md = prepare_slide_deck_content(req.outline)
    return {"markdown": md}


class PodcastRequest(BaseModel):
    outline: PresentationOutline
    voice: str = "zh-CN-YunxiNeural"


@router.post("/generate-podcast-script")
async def create_podcast_script(req: PodcastRequest):
    """Generate a podcast script from an outline."""
    script = generate_podcast_script(req.outline)
    return {"script": script}


@router.post("/generate-podcast-audio")
async def create_podcast_audio(req: PodcastRequest):
    """Generate podcast audio (MP3) from an outline."""
    script = generate_podcast_script(req.outline)
    audio_bytes = await generate_audio(script, req.voice)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "attachment; filename=podcast.mp3"},
    )


class VideoSetupRequest(BaseModel):
    outline: PresentationOutline


class XhsRequest(BaseModel):
    outline: PresentationOutline
    style: str = "notion"


@router.post("/generate-xhs-images")
async def create_xhs_images(req: XhsRequest):
    """Generate XHS (小红书) infographic card images."""
    import base64
    from core.xhs_generator import render_xhs_images
    cards, images = await render_xhs_images(req.outline, style=req.style)
    return {
        "cards": cards,
        "images": [base64.b64encode(img).decode() for img in images],
        "count": len(images),
    }


class ComicRequest(BaseModel):
    topic: str
    content: str
    art: str = "ligne-claire"


@router.post("/generate-comic")
async def create_comic(req: ComicRequest):
    """Generate comic panels as images."""
    import base64
    from core.comic_generator import render_comic
    script, images = await render_comic(req.topic, req.content, art=req.art)
    return {
        "script": script,
        "images": [base64.b64encode(img).decode() for img in images],
        "count": len(images),
    }


class VideoComposeRequest(BaseModel):
    outline: PresentationOutline
    with_audio: bool = False
    voice: str = "zh-CN-YunxiNeural"


@router.post("/compose-video")
async def compose_video_endpoint(req: VideoComposeRequest):
    """Generate a video from slide images + optional TTS audio."""
    from core.infographic_generator import render_slides_to_images
    from core.video_composer import compose_video

    # Render slides
    images = await render_slides_to_images(req.outline)

    # Optional TTS audio
    audio_bytes = None
    if req.with_audio:
        from core.podcast_generator import generate_podcast_script, generate_audio
        script = generate_podcast_script(req.outline)
        audio_bytes = await generate_audio(script, req.voice)

    # Compose video
    seconds_per_slide = 5.0
    if audio_bytes and images:
        # Estimate duration from audio (rough: 150 chars/min for Chinese)
        seconds_per_slide = max(3.0, 60.0 / max(len(images), 1))

    video_bytes = await compose_video(images, audio_bytes, seconds_per_slide=seconds_per_slide)

    return Response(
        content=video_bytes,
        media_type="video/mp4",
        headers={"Content-Disposition": "attachment; filename=video.mp4"},
    )


@router.post("/setup-video")
async def setup_video(req: VideoSetupRequest):
    """Set up Remotion project with outline data."""
    from core.video_generator import write_outline_data, _ensure_remotion_project
    project_dir = _ensure_remotion_project()
    write_outline_data(req.outline)
    return {"project_dir": str(project_dir)}
