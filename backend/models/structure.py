from pydantic import BaseModel

from core.content_structurer import Section, PresentationOutline


class GenerateOutlineRequest(BaseModel):
    topic: str
    materials: list[dict]
    instruction: str = ""


class RegenerateSectionRequest(BaseModel):
    outline_title: str
    section: Section
    instruction: str = "重新生成此章节，使内容更丰富"


class OutlineResponse(BaseModel):
    outline: PresentationOutline


class SectionResponse(BaseModel):
    section: Section
