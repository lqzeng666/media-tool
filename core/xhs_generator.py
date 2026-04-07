"""Xiaohongshu (小红书) infographic series generator.

Follows baoyu-xhs-images methodology:
1. Generate XHS-optimized outline from presentation content
2. Render styled HTML cards as images via Playwright
3. Optionally export prompts for baoyu-imagine AI generation
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from core.ai_client import chat
from core.content_structurer import PresentationOutline

logger = logging.getLogger(__name__)

# XHS style presets matching baoyu-xhs-images
XHS_STYLES = {
    "notion": {
        "name": "Notion 知识卡",
        "bg": "#FAFAF8",
        "accent": "#37352F",
        "accent2": "#2383E2",
        "text": "#37352F",
        "text_secondary": "#787774",
        "card_bg": "#FFFFFF",
        "border": "#E3E2E0",
        "tag_bg": "#E3E2E0",
    },
    "cute": {
        "name": "甜美少女风",
        "bg": "#FFF0F5",
        "accent": "#FF6B9D",
        "accent2": "#C084FC",
        "text": "#4A3240",
        "text_secondary": "#8B7082",
        "card_bg": "#FFFFFF",
        "border": "#FFD6E7",
        "tag_bg": "#FFD6E7",
    },
    "chalkboard": {
        "name": "黑板教学风",
        "bg": "#2D3436",
        "accent": "#FFEAA7",
        "accent2": "#81ECEC",
        "text": "#FFFFFF",
        "text_secondary": "#B2BEC3",
        "card_bg": "#353B3C",
        "border": "#4A5568",
        "tag_bg": "#4A5568",
    },
    "fresh": {
        "name": "清新自然风",
        "bg": "#F0FFF4",
        "accent": "#38A169",
        "accent2": "#4299E1",
        "text": "#22543D",
        "text_secondary": "#68D391",
        "card_bg": "#FFFFFF",
        "border": "#C6F6D5",
        "tag_bg": "#C6F6D5",
    },
    "bold": {
        "name": "醒目冲击风",
        "bg": "#1A1A2E",
        "accent": "#E94560",
        "accent2": "#0F3460",
        "text": "#FFFFFF",
        "text_secondary": "#A0AEC0",
        "card_bg": "#16213E",
        "border": "#E94560",
        "tag_bg": "#E94560",
    },
}

XHS_OUTLINE_PROMPT = """\
你是一位专业的小红书内容创作者。请根据以下演示文稿内容，生成一组小红书风格的图文卡片大纲。

标题: {title}
副标题: {subtitle}
章节:
{sections}

要求:
1. 生成 5-8 张卡片的内容，包括封面、内容卡和结尾
2. 封面要有吸引眼球的标题（可用 emoji）
3. 每张内容卡包含一个核心要点，文字精简有力
4. 结尾卡包含总结和互动引导（收藏/关注/评论）
5. 语言风格活泼、口语化，符合小红书平台调性
6. 每张卡片的文字控制在 50-150 字以内

请严格按以下 JSON 格式输出:
{{
  "cards": [
    {{
      "type": "cover",
      "title": "封面大标题",
      "subtitle": "一句话钩子",
      "tags": ["标签1", "标签2"]
    }},
    {{
      "type": "content",
      "title": "卡片标题",
      "points": ["要点1", "要点2", "要点3"],
      "highlight": "核心金句"
    }},
    {{
      "type": "ending",
      "title": "结尾标题",
      "cta": "互动引导语",
      "tags": ["标签1", "标签2"]
    }}
  ]
}}

只输出 JSON，不要输出其他内容。"""


def generate_xhs_outline(outline: PresentationOutline) -> list[dict]:
    """Generate XHS-optimized card outline from a presentation outline."""
    sections_text = ""
    for i, sec in enumerate(outline.sections, 1):
        bullets = "\n".join(f"  - {b}" for b in sec.bullets)
        sections_text += f"\n第{i}部分: {sec.title}\n{bullets}\n"

    response = chat(
        messages=[{
            "role": "user",
            "content": XHS_OUTLINE_PROMPT.format(
                title=outline.title,
                subtitle=outline.subtitle,
                sections=sections_text,
            ),
        }],
        temperature=0.8,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    data = json.loads(response)
    return data.get("cards", [])


def _render_cover_html(card: dict, style: dict) -> str:
    tags_html = "".join(
        f'<span class="tag">#{t}</span>' for t in card.get("tags", [])
    )
    return f"""<div class="card cover">
  <div class="cover-deco"></div>
  <h1>{card.get("title", "")}</h1>
  <p class="subtitle">{card.get("subtitle", "")}</p>
  <div class="tags">{tags_html}</div>
</div>"""


def _render_content_html(card: dict, index: int, style: dict) -> str:
    points_html = "".join(
        f'<div class="point"><span class="point-num">{i+1}</span><span>{p}</span></div>'
        for i, p in enumerate(card.get("points", []))
    )
    highlight = card.get("highlight", "")
    highlight_html = f'<div class="highlight">{highlight}</div>' if highlight else ""
    return f"""<div class="card content">
  <div class="card-num">{index:02d}</div>
  <h2>{card.get("title", "")}</h2>
  <div class="points">{points_html}</div>
  {highlight_html}
</div>"""


def _render_ending_html(card: dict, style: dict) -> str:
    tags_html = "".join(
        f'<span class="tag">#{t}</span>' for t in card.get("tags", [])
    )
    return f"""<div class="card ending">
  <h2>{card.get("title", "")}</h2>
  <p class="cta">{card.get("cta", "")}</p>
  <div class="tags">{tags_html}</div>
  <div class="footer">点赞 ❤️ 收藏 ⭐ 关注 ➕</div>
</div>"""


def build_xhs_html(cards: list[dict], style_name: str = "notion") -> list[str]:
    """Build individual HTML pages for each XHS card. Returns list of full HTML strings."""
    style = XHS_STYLES.get(style_name, XHS_STYLES["notion"])

    css = f"""
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      width: 1080px; height: 1440px;
      font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
      overflow: hidden;
    }}
    .card {{
      width: 1080px; height: 1440px;
      background: {style['bg']};
      display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      padding: 80px 72px;
      position: relative;
    }}
    /* Cover */
    .card.cover {{ text-align: center; }}
    .card.cover .cover-deco {{
      width: 80px; height: 6px;
      background: {style['accent']};
      border-radius: 3px;
      margin-bottom: 48px;
    }}
    .card.cover h1 {{
      font-size: 64px; font-weight: 800;
      color: {style['accent']};
      line-height: 1.3; margin-bottom: 28px;
      max-width: 900px;
    }}
    .card.cover .subtitle {{
      font-size: 32px; color: {style['text_secondary']};
      margin-bottom: 48px; line-height: 1.5;
    }}
    /* Content */
    .card.content {{ align-items: flex-start; }}
    .card.content .card-num {{
      font-size: 20px; color: {style['accent2']};
      font-weight: 700; margin-bottom: 16px;
      letter-spacing: 2px;
    }}
    .card.content h2 {{
      font-size: 48px; font-weight: 700;
      color: {style['text']}; line-height: 1.3;
      margin-bottom: 40px;
    }}
    .card.content .points {{ width: 100%; }}
    .card.content .point {{
      display: flex; align-items: flex-start;
      margin-bottom: 28px; font-size: 30px;
      color: {style['text']}; line-height: 1.6;
    }}
    .card.content .point-num {{
      background: {style['accent']};
      color: {style['bg']};
      width: 44px; height: 44px;
      border-radius: 22px;
      display: flex; align-items: center; justify-content: center;
      font-size: 22px; font-weight: 700;
      margin-right: 20px; flex-shrink: 0;
      margin-top: 4px;
    }}
    .card.content .highlight {{
      margin-top: 40px; padding: 32px 36px;
      background: {style['card_bg']};
      border-left: 6px solid {style['accent']};
      border-radius: 0 16px 16px 0;
      font-size: 28px; color: {style['accent']};
      font-weight: 600; line-height: 1.6;
      width: 100%;
    }}
    /* Ending */
    .card.ending {{ text-align: center; }}
    .card.ending h2 {{
      font-size: 52px; font-weight: 800;
      color: {style['text']}; margin-bottom: 32px;
    }}
    .card.ending .cta {{
      font-size: 30px; color: {style['text_secondary']};
      margin-bottom: 48px; line-height: 1.6;
    }}
    .card.ending .footer {{
      margin-top: 48px; font-size: 28px;
      color: {style['accent']}; font-weight: 600;
      letter-spacing: 4px;
    }}
    /* Tags */
    .tags {{
      display: flex; flex-wrap: wrap;
      gap: 12px; justify-content: center;
    }}
    .tag {{
      padding: 8px 24px; border-radius: 20px;
      background: {style['tag_bg']}; color: {style['text']};
      font-size: 24px;
    }}
    """

    html_template = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{body}</body></html>"""

    pages = []
    content_idx = 0
    for card in cards:
        card_type = card.get("type", "content")
        if card_type == "cover":
            body = _render_cover_html(card, style)
        elif card_type == "ending":
            body = _render_ending_html(card, style)
        else:
            content_idx += 1
            body = _render_content_html(card, content_idx, style)
        pages.append(html_template.format(css=css, body=body))

    return pages


async def render_xhs_images(
    outline: PresentationOutline,
    style: str = "notion",
) -> tuple[list[dict], list[bytes]]:
    """Generate XHS cards and render them as images.

    Returns (cards_data, image_bytes_list).
    """
    from playwright.async_api import async_playwright

    # Step 1: Generate XHS outline
    cards = generate_xhs_outline(outline)
    if not cards:
        return [], []

    # Step 2: Build HTML
    html_pages = build_xhs_html(cards, style)

    # Step 3: Render to images
    images = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1440})

        for html in html_pages:
            await page.set_content(html, wait_until="networkidle")
            screenshot = await page.screenshot(type="png")
            images.append(screenshot)

        await browser.close()

    return cards, images


def export_xhs_prompts(cards: list[dict], outline: PresentationOutline, output_dir: str | Path) -> Path:
    """Export XHS card data and prompts for baoyu-imagine generation."""
    out = Path(output_dir) / "xhs-images"
    out.mkdir(parents=True, exist_ok=True)
    prompts_dir = out / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    # Save source content
    source = f"# {outline.title}\n\n> {outline.subtitle}\n\n"
    for sec in outline.sections:
        source += f"## {sec.title}\n"
        for b in sec.bullets:
            source += f"- {b}\n"
        source += "\n"
    (out / "source.md").write_text(source, encoding="utf-8")

    # Save outline
    (out / "outline.json").write_text(
        json.dumps({"cards": cards}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Generate prompts for each card
    for i, card in enumerate(cards):
        card_type = card.get("type", "content")
        title_slug = card.get("title", "card")[:20].replace(" ", "-").lower()
        prompt_file = prompts_dir / f"{i+1:02d}-{card_type}-{title_slug}.md"

        prompt = _build_image_prompt(card, i)
        prompt_file.write_text(prompt, encoding="utf-8")

    return out


def _build_image_prompt(card: dict, index: int) -> str:
    """Build an image generation prompt for a single XHS card."""
    card_type = card.get("type", "content")
    title = card.get("title", "")

    if card_type == "cover":
        return f"""Create a Xiaohongshu (Little Red Book) cover infographic card.
Style: Cute cartoon illustration, pastel colors, hand-drawn elements.
Aspect ratio: 3:4 (portrait, 1080x1440px)
Content:
- Main title: "{title}"
- Subtitle: "{card.get('subtitle', '')}"
- Tags: {', '.join(card.get('tags', []))}
- Decorations: sparkles, hearts, cute doodles
- Typography: Bold, eye-catching Chinese title with decorative elements
"""
    elif card_type == "ending":
        return f"""Create a Xiaohongshu (Little Red Book) ending/CTA infographic card.
Style: Cute cartoon illustration, pastel colors, warm and inviting.
Aspect ratio: 3:4 (portrait, 1080x1440px)
Content:
- Title: "{title}"
- Call to action: "{card.get('cta', '')}"
- Footer: "点赞 ❤️ 收藏 ⭐ 关注 ➕"
- Tags: {', '.join(card.get('tags', []))}
"""
    else:
        points = card.get("points", [])
        points_text = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(points))
        highlight = card.get("highlight", "")
        return f"""Create a Xiaohongshu (Little Red Book) content infographic card.
Style: Cute cartoon illustration, clean layout, numbered bullet points.
Aspect ratio: 3:4 (portrait, 1080x1440px)
Content:
- Card number: {index+1:02d}
- Title: "{title}"
- Key points:
{points_text}
- Highlight quote: "{highlight}"
"""
