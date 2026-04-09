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
4. 内容卡尽量包含可视化数据（百分比、数字对比、评分等），用 stats 字段
5. 结尾卡包含总结和互动引导
6. 语言风格活泼、口语化

请严格按以下 JSON 格式输出:
{{
  "cards": [
    {{
      "type": "cover",
      "title": "封面大标题",
      "subtitle": "一句话钩子",
      "tags": ["标签1", "标签2"],
      "image_prompt": "封面配图描述（英文）"
    }},
    {{
      "type": "content",
      "title": "卡片标题",
      "points": ["要点1", "要点2", "要点3"],
      "highlight": "核心金句",
      "stats": [{{"label": "指标名", "value": "85%"}}, {{"label": "指标名", "value": "10x"}}],
      "image_prompt": "配图描述（英文）"
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


def _stats_html(stats: list[dict], style: dict) -> str:
    """Render stats as visual data cards."""
    if not stats:
        return ""
    items = []
    for s in stats[:4]:
        items.append(f'''<div class="stat-item">
  <div class="stat-value">{s.get("value", "")}</div>
  <div class="stat-label">{s.get("label", "")}</div>
</div>''')
    return f'<div class="stats-row">{"".join(items)}</div>'


def _img_html(img_b64: str) -> str:
    if not img_b64:
        return ""
    return f'<div class="card-img"><img src="data:image/png;base64,{img_b64}" /></div>'


def build_xhs_html(cards: list[dict], style_name: str = "notion", card_images: list[str] = None) -> list[str]:
    """Build HTML pages for XHS cards with data viz and optional AI images."""
    import base64 as b64mod
    style = XHS_STYLES.get(style_name, XHS_STYLES["notion"])
    if card_images is None:
        card_images = [""] * len(cards)
    while len(card_images) < len(cards):
        card_images.append("")

    css = f"""
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ width:1080px; height:1440px; font-family:-apple-system,"PingFang SC","Noto Sans SC",sans-serif; overflow:hidden; }}
    .card {{ width:1080px; height:1440px; background:{style['bg']}; display:flex; flex-direction:column; padding:72px 64px; position:relative; }}
    /* Cover */
    .card.cover {{ justify-content:center; align-items:center; text-align:center; }}
    .card.cover .deco {{ width:80px; height:5px; background:{style['accent']}; border-radius:3px; margin-bottom:40px; }}
    .card.cover h1 {{ font-size:60px; font-weight:800; color:{style['accent']}; line-height:1.3; margin-bottom:24px; max-width:900px; }}
    .card.cover .sub {{ font-size:28px; color:{style['text_secondary']}; margin-bottom:40px; line-height:1.5; }}
    .card.cover .card-img {{ margin-bottom:40px; }}
    .card.cover .card-img img {{ width:400px; height:400px; object-fit:cover; border-radius:24px; }}
    .tags {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:center; }}
    .tag {{ padding:8px 22px; border-radius:20px; background:{style['tag_bg']}; color:{style['text']}; font-size:22px; }}
    /* Content */
    .card.content {{ justify-content:flex-start; }}
    .card.content .top-row {{ display:flex; align-items:center; margin-bottom:32px; }}
    .card.content .card-num {{ font-size:18px; color:{style['accent2']}; font-weight:700; margin-right:12px; }}
    .card.content h2 {{ font-size:44px; font-weight:700; color:{style['text']}; line-height:1.3; margin-bottom:28px; }}
    .card.content .card-img {{ margin-bottom:28px; }}
    .card.content .card-img img {{ width:100%; max-height:400px; object-fit:cover; border-radius:16px; }}
    .card.content .points {{ width:100%; }}
    .card.content .point {{ display:flex; align-items:flex-start; margin-bottom:20px; font-size:28px; color:{style['text']}; line-height:1.6; }}
    .card.content .point-num {{ background:{style['accent']}; color:{style['bg']}; min-width:40px; height:40px; border-radius:20px; display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:700; margin-right:16px; flex-shrink:0; margin-top:4px; }}
    .card.content .highlight {{ margin-top:24px; padding:24px 28px; background:{style['card_bg']}; border-left:5px solid {style['accent']}; border-radius:0 12px 12px 0; font-size:26px; color:{style['accent']}; font-weight:600; line-height:1.6; }}
    /* Stats */
    .stats-row {{ display:flex; gap:16px; margin:24px 0; width:100%; }}
    .stat-item {{ flex:1; background:{style['card_bg']}; border:2px solid {style['border']}; border-radius:16px; padding:20px; text-align:center; }}
    .stat-value {{ font-size:36px; font-weight:800; color:{style['accent']}; margin-bottom:8px; }}
    .stat-label {{ font-size:18px; color:{style['text_secondary']}; }}
    /* Ending */
    .card.ending {{ justify-content:center; align-items:center; text-align:center; }}
    .card.ending h2 {{ font-size:48px; font-weight:800; color:{style['text']}; margin-bottom:28px; }}
    .card.ending .cta {{ font-size:28px; color:{style['text_secondary']}; margin-bottom:40px; line-height:1.6; }}
    .card.ending .footer {{ font-size:26px; color:{style['accent']}; font-weight:600; letter-spacing:3px; }}
    """

    tpl = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'
    pages = []
    content_idx = 0

    for i, card in enumerate(cards):
        ct = card.get("type", "content")
        img = _img_html(card_images[i])

        if ct == "cover":
            tags = "".join(f'<span class="tag">#{t}</span>' for t in card.get("tags", []))
            body = f'''<div class="card cover">
  <div class="deco"></div>
  {img}
  <h1>{card.get("title","")}</h1>
  <div class="sub">{card.get("subtitle","")}</div>
  <div class="tags">{tags}</div>
</div>'''
        elif ct == "ending":
            tags = "".join(f'<span class="tag">#{t}</span>' for t in card.get("tags", []))
            body = f'''<div class="card ending">
  {img}
  <h2>{card.get("title","")}</h2>
  <div class="cta">{card.get("cta","")}</div>
  <div class="tags">{tags}</div>
  <div class="footer">点赞 ❤️  收藏 ⭐  关注 ➕</div>
</div>'''
        else:
            content_idx += 1
            pts = "".join(
                f'<div class="point"><span class="point-num">{j+1}</span><span>{p}</span></div>'
                for j, p in enumerate(card.get("points", []))
            )
            hl = card.get("highlight", "")
            hl_html = f'<div class="highlight">{hl}</div>' if hl else ""
            stats = _stats_html(card.get("stats", []), style)
            body = f'''<div class="card content">
  <div class="top-row"><span class="card-num">{content_idx:02d}</span></div>
  <h2>{card.get("title","")}</h2>
  {img}
  {stats}
  <div class="points">{pts}</div>
  {hl_html}
</div>'''
        pages.append(tpl.format(css=css, body=body))

    return pages


async def render_xhs_images(
    outline: PresentationOutline,
    style: str = "notion",
) -> tuple[list[dict], list[bytes]]:
    """Generate XHS cards with AI images and render as final images."""
    from playwright.async_api import async_playwright
    from core.image_gen import generate_batch
    import base64

    cards = generate_xhs_outline(outline)
    if not cards:
        return [], []

    # Generate AI images for cards that have image_prompt
    prompts = []
    for card in cards:
        prompt = card.get("image_prompt", "")
        if prompt:
            prompts.append(prompt + ". Cute illustration, flat design, pastel colors, no text.")
        else:
            prompts.append("")

    # Only generate for non-empty prompts
    has_prompts = [i for i, p in enumerate(prompts) if p]
    card_images_b64 = [""] * len(cards)

    if has_prompts:
        actual_prompts = [prompts[i] for i in has_prompts]
        logger.info("Generating %d XHS card images...", len(actual_prompts))
        raw_images = generate_batch(actual_prompts, size="1024*1024")
        for idx, img_bytes in zip(has_prompts, raw_images):
            if img_bytes:
                card_images_b64[idx] = base64.b64encode(img_bytes).decode()

    # Build HTML with images
    html_pages = build_xhs_html(cards, style, card_images_b64)

    # Render
    images = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1440})
        for html in html_pages:
            await page.set_content(html, wait_until="networkidle")
            images.append(await page.screenshot(type="png"))
        await browser.close()

    return cards, images
