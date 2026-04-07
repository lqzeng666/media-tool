from __future__ import annotations

import json

from pydantic import BaseModel

from core.ai_client import chat


class Section(BaseModel):
    title: str
    bullets: list[str]
    image_prompt: str = ""
    speaker_notes: str = ""


class PresentationOutline(BaseModel):
    title: str
    subtitle: str
    sections: list[Section]


STRUCTURING_PROMPT = """\
你是一个专业的内容编辑。请根据以下主题和素材，生成一份结构化的演示文稿大纲。

主题: {topic}

素材:
{materials}

要求:
1. 生成一个引人注目的标题和副标题
2. 生成 6-10 个章节，每个章节包含:
   - 章节标题
   - 2-4 个要点（关键事实/见解）
   - 一个用于配图生成的图片描述提示词（英文）
3. 内容要有逻辑性，从引入到总结
4. 语言简洁有力，适合演示文稿

请严格按以下 JSON 格式输出:
{{
  "title": "演示文稿标题",
  "subtitle": "副标题",
  "sections": [
    {{
      "title": "章节标题",
      "bullets": ["要点1", "要点2", "要点3"],
      "image_prompt": "A descriptive image prompt in English"
    }}
  ]
}}

只输出 JSON，不要输出其他内容。"""


def _format_materials(materials: list[dict]) -> str:
    parts = []
    for i, m in enumerate(materials, 1):
        title = m.get("title", "")
        text = m.get("text", "")
        parts.append(f"[素材{i}] {title}\n{text}")
    return "\n\n".join(parts)


def generate_outline(topic: str, materials: list[dict]) -> PresentationOutline:
    """Generate a structured presentation outline from topic and source materials."""
    prompt = STRUCTURING_PROMPT.format(
        topic=topic,
        materials=_format_materials(materials),
    )

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    # Parse and validate
    data = json.loads(response)
    return PresentationOutline(**data)


REGENERATE_SECTION_PROMPT = """\
你是一个专业的内容编辑。请根据以下信息，重新生成演示文稿的一个章节。

演示文稿主题: {title}
当前章节标题: {section_title}
用户指令: {instruction}

请严格按以下 JSON 格式输出:
{{
  "title": "章节标题",
  "bullets": ["要点1", "要点2", "要点3"],
  "image_prompt": "A descriptive image prompt in English"
}}

只输出 JSON，不要输出其他内容。"""


def regenerate_section(
    outline_title: str,
    section: Section,
    instruction: str = "重新生成此章节，使内容更丰富",
) -> Section:
    """Regenerate a single section of the outline."""
    prompt = REGENERATE_SECTION_PROMPT.format(
        title=outline_title,
        section_title=section.title,
        instruction=instruction,
    )

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    data = json.loads(response)
    return Section(**data)
