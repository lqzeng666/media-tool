"""Comic generator - AI generates panel scripts then DashScope renders images."""
from __future__ import annotations

import json
import logging

from core.ai_client import chat
from core.image_gen import generate_image, download_image

logger = logging.getLogger(__name__)

ART_PROMPTS = {
    "ligne-claire": "Clear line art style, like Tintin comics, flat colors, clean outlines, European BD comic aesthetic",
    "manga": "Japanese manga style, expressive characters, screentones, dynamic poses, black and white with selective color",
    "ink-brush": "Chinese ink brush painting style, elegant brushstrokes, traditional watercolor, artistic and flowing",
    "chalk": "Colorful chalk drawing on blackboard, educational style, hand-drawn feel, warm and playful",
    "minimalist": "Minimalist cartoon style, simple shapes, limited color palette, clean and modern",
    "realistic": "Semi-realistic illustration, detailed shading, cinematic lighting, professional comic art",
}

COMIC_PROMPT = """\
你是一位专业的知识漫画编剧。请根据以下内容，创作一组知识漫画的分镜脚本。

主题: {topic}
内容:
{content}

要求:
1. 生成 4-6 个漫画面板
2. 每个面板包含详细的画面描述（用于 AI 绘图）
3. 第一个是封面面板
4. 用讲故事的方式传达知识
5. 画面描述要具体：场景、人物动作、表情、构图

请严格按以下 JSON 格式输出:
{{
  "title": "漫画标题",
  "panels": [
    {{
      "type": "cover",
      "scene": "详细的封面画面描述，包括主角形象、场景、氛围",
      "text_overlay": "封面上显示的标题文字",
      "narrator": "副标题或引言"
    }},
    {{
      "type": "panel",
      "scene": "详细的面板画面描述，包括角色动作、表情、环境细节",
      "dialogue": "角色的对话内容",
      "narrator": "旁白或知识点说明"
    }}
  ]
}}

只输出 JSON。"""


def generate_comic_script(topic: str, content: str) -> dict:
    """Generate a comic script from content."""
    response = chat(
        messages=[{"role": "user", "content": COMIC_PROMPT.format(
            topic=topic, content=content[:3000],
        )}],
        temperature=0.8,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    return json.loads(response)


def _build_image_prompt(panel: dict, art_style: str, title: str, panel_index: int) -> str:
    """Build a DashScope image generation prompt for a comic panel."""
    art_desc = ART_PROMPTS.get(art_style, ART_PROMPTS["ligne-claire"])
    scene = panel.get("scene", "")
    ptype = panel.get("type", "panel")

    if ptype == "cover":
        return (
            f"Comic book cover illustration. {art_desc}. "
            f"Title: '{title}'. "
            f"Scene: {scene}. "
            f"Professional comic book cover composition, eye-catching, "
            f"high quality illustration, detailed artwork."
        )
    else:
        dialogue = panel.get("dialogue", "")
        return (
            f"Comic panel illustration, panel #{panel_index}. {art_desc}. "
            f"Scene: {scene}. "
            f"{'Character saying: ' + dialogue + '. ' if dialogue else ''}"
            f"Single comic panel with clear composition, expressive characters, "
            f"high quality illustration."
        )


def render_comic_ai(topic: str, content: str, art: str = "ligne-claire") -> tuple[dict, list[bytes]]:
    """Generate comic with AI-rendered images via DashScope.

    Returns (script, list_of_image_bytes).
    """
    # Step 1: Generate script
    script = generate_comic_script(topic, content)
    panels = script.get("panels", [])
    title = script.get("title", topic)

    if not panels:
        return script, []

    # Step 2: Generate images for each panel
    images = []
    for i, panel in enumerate(panels):
        prompt = _build_image_prompt(panel, art, title, i)
        logger.info("Generating comic panel %d/%d", i + 1, len(panels))

        try:
            urls = generate_image(prompt, size="1024*1024", timeout=90)
            if urls:
                img_bytes = download_image(urls[0])
                images.append(img_bytes)
            else:
                logger.warning("No image URL returned for panel %d", i)
                images.append(b"")
        except Exception as e:
            logger.error("Failed to generate panel %d: %s", i, e)
            images.append(b"")

    return script, [img for img in images if img]
