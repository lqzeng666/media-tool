"""Comic panel generator - creates styled HTML comic pages and renders to images."""
from __future__ import annotations

import json
import logging

from core.ai_client import chat
from core.content_structurer import PresentationOutline

logger = logging.getLogger(__name__)

COMIC_PROMPT = """\
你是一位专业的知识漫画编剧。请根据以下内容，创作一组知识漫画的分镜脚本。

主题: {topic}
内容:
{content}

要求:
1. 生成 4-6 个漫画面板
2. 每个面板包含：场景描述、角色对话/旁白、视觉元素
3. 第一个面板是封面/标题面板
4. 用讲故事的方式传达知识，有趣味性
5. 角色可以用简单的表情符号代替

请严格按以下 JSON 格式输出:
{{
  "title": "漫画标题",
  "panels": [
    {{
      "type": "cover",
      "scene": "场景描述",
      "dialogue": "标题文字",
      "narrator": "旁白文字",
      "emotion": "emoji表情"
    }},
    {{
      "type": "panel",
      "scene": "场景描述",
      "dialogue": "角色对话",
      "narrator": "旁白/知识点",
      "emotion": "emoji表情"
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


ART_STYLES = {
    "ligne-claire": {
        "bg": "#FFF8E7", "panel_bg": "#FFFFFF", "border": "#2C2C2C",
        "title_color": "#D32F2F", "text_color": "#2C2C2C",
        "narrator_bg": "#FFF3CD", "dialogue_bg": "#FFFFFF",
        "font": "Comic Sans MS, cursive, sans-serif",
    },
    "manga": {
        "bg": "#F5F5F5", "panel_bg": "#FFFFFF", "border": "#000000",
        "title_color": "#E91E63", "text_color": "#1A1A1A",
        "narrator_bg": "#E8EAF6", "dialogue_bg": "#FFFFFF",
        "font": "'PingFang SC', sans-serif",
    },
    "ink-brush": {
        "bg": "#F5F0E8", "panel_bg": "#FAF7F0", "border": "#4A3728",
        "title_color": "#8B0000", "text_color": "#3E2723",
        "narrator_bg": "#EFEBE9", "dialogue_bg": "#FAF7F0",
        "font": "'STKaiti', 'KaiTi', serif",
    },
    "chalk": {
        "bg": "#2D3436", "panel_bg": "#353B3C", "border": "#FFEAA7",
        "title_color": "#FFEAA7", "text_color": "#FFFFFF",
        "narrator_bg": "#4A5568", "dialogue_bg": "#3D4448",
        "font": "'Comic Sans MS', cursive",
    },
}


def _build_comic_html(script: dict, art: str = "ligne-claire") -> list[str]:
    """Build HTML pages for each comic panel."""
    style = ART_STYLES.get(art, ART_STYLES["ligne-claire"])
    panels = script.get("panels", [])
    title = script.get("title", "")

    css = f"""
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      width: 1080px; height: 1080px;
      font-family: {style['font']};
      overflow: hidden;
    }}
    .panel {{
      width: 1080px; height: 1080px;
      background: {style['bg']};
      display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      padding: 60px;
      position: relative;
    }}
    .panel-inner {{
      width: 100%; height: 100%;
      background: {style['panel_bg']};
      border: 4px solid {style['border']};
      border-radius: 16px;
      display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      padding: 48px;
      position: relative;
      overflow: hidden;
    }}
    .panel-num {{
      position: absolute; top: 16px; left: 20px;
      font-size: 18px; font-weight: 700;
      color: {style['border']}; opacity: 0.5;
    }}
    /* Cover */
    .cover-title {{
      font-size: 52px; font-weight: 800;
      color: {style['title_color']};
      text-align: center; line-height: 1.4;
      margin-bottom: 24px;
    }}
    .cover-subtitle {{
      font-size: 24px; color: {style['text_color']};
      text-align: center; opacity: 0.7;
    }}
    .emoji {{
      font-size: 80px; margin-bottom: 32px;
    }}
    /* Content panel */
    .scene {{
      font-size: 18px; color: {style['text_color']};
      opacity: 0.5; margin-bottom: 20px;
      font-style: italic; text-align: center;
    }}
    .dialogue-bubble {{
      background: {style['dialogue_bg']};
      border: 3px solid {style['border']};
      border-radius: 24px;
      padding: 24px 36px;
      font-size: 28px; color: {style['text_color']};
      line-height: 1.6;
      max-width: 85%;
      margin-bottom: 24px;
      position: relative;
      text-align: center;
    }}
    .dialogue-bubble::after {{
      content: '';
      position: absolute; bottom: -16px; left: 50%;
      transform: translateX(-50%);
      border: 8px solid transparent;
      border-top-color: {style['border']};
    }}
    .narrator-box {{
      background: {style['narrator_bg']};
      border-left: 5px solid {style['title_color']};
      border-radius: 0 12px 12px 0;
      padding: 20px 28px;
      font-size: 22px; color: {style['text_color']};
      line-height: 1.6;
      width: 85%;
      margin-top: 16px;
    }}
    .panel-emoji {{
      font-size: 64px; margin-bottom: 20px;
    }}
    """

    template = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'
    pages = []

    for i, panel in enumerate(panels):
        ptype = panel.get("type", "panel")
        emotion = panel.get("emotion", "💡")
        dialogue = panel.get("dialogue", "")
        narrator = panel.get("narrator", "")
        scene = panel.get("scene", "")

        if ptype == "cover":
            body = f"""<div class="panel">
  <div class="panel-inner">
    <div class="emoji">{emotion}</div>
    <div class="cover-title">{dialogue or title}</div>
    <div class="cover-subtitle">{narrator}</div>
  </div>
</div>"""
        else:
            scene_html = f'<div class="scene">{scene}</div>' if scene else ""
            dialogue_html = f'<div class="dialogue-bubble">{dialogue}</div>' if dialogue else ""
            narrator_html = f'<div class="narrator-box">{narrator}</div>' if narrator else ""
            body = f"""<div class="panel">
  <div class="panel-inner">
    <div class="panel-num">#{i}</div>
    <div class="panel-emoji">{emotion}</div>
    {scene_html}
    {dialogue_html}
    {narrator_html}
  </div>
</div>"""
        pages.append(template.format(css=css, body=body))

    return pages


async def render_comic(topic: str, content: str, art: str = "ligne-claire") -> tuple[dict, list[bytes]]:
    """Generate comic script and render to images."""
    from playwright.async_api import async_playwright

    script = generate_comic_script(topic, content)
    pages = _build_comic_html(script, art)

    images = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1080})
        for html in pages:
            await page.set_content(html, wait_until="networkidle")
            images.append(await page.screenshot(type="png"))
        await browser.close()

    return script, images
