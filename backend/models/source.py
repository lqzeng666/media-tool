from pydantic import BaseModel


class FetchRequest(BaseModel):
    urls: list[str]


class SourceMaterialResponse(BaseModel):
    url: str
    title: str
    text: str
    word_count: int


class FetchResponse(BaseModel):
    materials: list[SourceMaterialResponse]
    errors: list[str] = []
