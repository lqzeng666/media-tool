from pydantic import BaseModel

from core.content_structurer import PresentationOutline


class GeneratePPTRequest(BaseModel):
    outline: PresentationOutline
