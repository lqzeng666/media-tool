from fastapi import APIRouter

from backend.models.structure import (
    GenerateOutlineRequest,
    OutlineResponse,
    RegenerateSectionRequest,
    SectionResponse,
)
from core.content_structurer import generate_outline, regenerate_section

router = APIRouter(prefix="/api/structure", tags=["structure"])


@router.post("/generate", response_model=OutlineResponse)
async def create_outline(req: GenerateOutlineRequest):
    """Generate a structured presentation outline from topic and materials."""
    outline = generate_outline(req.topic, req.materials, instruction=req.instruction)
    return OutlineResponse(outline=outline)


@router.post("/regenerate-section", response_model=SectionResponse)
async def regen_section(req: RegenerateSectionRequest):
    """Regenerate a single section of the outline."""
    section = regenerate_section(
        req.outline_title, req.section, req.instruction
    )
    return SectionResponse(section=section)
