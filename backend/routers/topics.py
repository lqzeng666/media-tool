from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from core.topic_detector import detect_trending_topics, TrendingTopic

router = APIRouter(prefix="/api/topics", tags=["topics"])


class DetectRequest(BaseModel):
    time_range: str = "d"
    region: str = "zh-cn"
    category: str = ""


class DetectResponse(BaseModel):
    topics: list[TrendingTopic]


@router.post("/detect", response_model=DetectResponse)
async def detect_topics(req: DetectRequest):
    """Detect trending topics from recent news."""
    topics = detect_trending_topics(
        time_range=req.time_range,
        region=req.region,
        category=req.category,
    )
    return DetectResponse(topics=topics)
