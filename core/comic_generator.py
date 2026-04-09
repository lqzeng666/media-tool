"""Comic generator - parallel AI image generation + HTML composite layout."""
from __future__ import annotations

import base64
import json
import logging
import re

from core.ai_client import chat
from core.image_gen import generate_batch

logger = logging.getLogger(__name__)

ART_PROMPTS = {
    "ligne-claire": "Clear line art comic style like Tintin, flat colors, clean outlines",
    "manga": "Japanese manga style, expressive characters, dynamic, anime aesthetic",
    "ink-brush": "Chinese ink brush painting style, elegant brushstrokes, watercolor",
    "chalk": "Colorful chalk drawing style, playful, hand-drawn, educational",
}

COMIC_PROMPT = """\
你是专业知识漫画编剧。根据以下内容创作 4 格漫画分镜。

主题: {topic}
内容: {content}

要求:
1. 恰好 4 个面板（封面+2内容+结尾）
2. 每个面板有具体画面描述（用于AI绘图）和文字内容
3. 画面描述要具体：人物、动作、表情、场景

JSON 格式:
{{
  "title": "漫画标题",
  "panels": [
    {{"type":"cover","scene":"封面画面描述","title_text":"大标题","sub_text":"副标题"}},
    {{"type":"content","scene":"画面描述","dialogue":"对话","knowledge":"知识点"}},
    {{"type":"content","scene":"画面描述","dialogue":"对话","knowledge":"知识点"}},
    {{"type":"ending","scene":"画面描述","title_text":"结语","sub_text":"互动引导"}}
  ]
}}

只输出 JSON。"""


def generate_comic_script(topic: str, content: str) -> dict:
    for attempt in range(2):
        response = chat(
            messages=[{"role": "user", "content": COMIC_PROMPT.format(
                topic=topic, content=content[:2000],
            )}],
            temperature=0.7,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
    return {"title": topic, "panels": [
        {"type": "cover", "scene": f"Cover about {topic}", "title_text": topic, "sub_text": ""},
        {"type": "content", "scene": f"Illustration about {topic}", "dialogue": "", "knowledge": content[:150]},
        {"type": "ending", "scene": "Friendly ending", "title_text": "总结", "sub_text": "感谢阅读"},
    ]}


COMIC_PAGE_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1080px; height:1080px; overflow:hidden; font-family:-apple-system,"PingFang SC","Noto Sans SC",sans-serif; }
.page { width:1080px; height:1080px; position:relative; }
.page .bg { position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; }
.page .overlay { position:absolute; top:0; left:0; width:100%; height:100%; }
/* Cover */
.page.cover .overlay { background:linear-gradient(180deg,rgba(0,0,0,0.1) 0%,rgba(0,0,0,0.7) 60%,rgba(0,0,0,0.85) 100%); display:flex; flex-direction:column; justify-content:flex-end; padding:60px; }
.page.cover .title { font-size:56px; font-weight:800; color:#fff; line-height:1.3; margin-bottom:16px; text-shadow:0 2px 8px rgba(0,0,0,0.5); }
.page.cover .sub { font-size:24px; color:#ddd; }
/* Content */
.page.content .overlay { background:linear-gradient(180deg,transparent 40%,rgba(0,0,0,0.75) 100%); display:flex; flex-direction:column; justify-content:flex-end; padding:48px; }
.page.content .bubble { background:rgba(255,255,255,0.95); border-radius:24px; padding:20px 28px; margin-bottom:16px; max-width:80%; font-size:24px; color:#222; line-height:1.6; position:relative; box-shadow:0 4px 12px rgba(0,0,0,0.15); }
.page.content .bubble::after { content:''; position:absolute; bottom:-12px; left:40px; border:8px solid transparent; border-top-color:rgba(255,255,255,0.95); }
.page.content .knowledge { background:rgba(0,210,255,0.9); border-radius:16px; padding:16px 24px; font-size:22px; color:#fff; line-height:1.6; font-weight:500; }
.page.content .panel-num { position:absolute; top:24px; left:28px; background:rgba(0,210,255,0.85); color:#fff; width:48px; height:48px; border-radius:24px; display:flex; align-items:center; justify-content:center; font-size:22px; font-weight:700; }
/* Ending */
.page.ending .overlay { background:linear-gradient(180deg,rgba(0,0,0,0.2) 0%,rgba(0,0,0,0.8) 100%); display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; padding:60px; }
.page.ending .title { font-size:48px; font-weight:700; color:#fff; margin-bottom:20px; text-shadow:0 2px 8px rgba(0,0,0,0.5); }
.page.ending .sub { font-size:26px; color:#00d2ff; }
"""


def _build_comic_pages(script: dict, image_data: list[bytes]) -> list[str]:
    """Build HTML pages compositing AI images + text overlays."""
    panels = script.get("panels", [])
    pages = []

    for i, panel in enumerate(panels):
        ptype = panel.get("type", "content")
        img_b64 = base64.b64encode(image_data[i]).decode() if i < len(image_data) and image_data[i] else ""
        img_tag = f'<img class="bg" src="data:image/png;base64,{img_b64}" />' if img_b64 else '<div class="bg" style="background:#1a1a2e;"></div>'

        if ptype == "cover":
            body = f'''<div class="page cover">
  {img_tag}
  <div class="overlay">
    <div class="title">{panel.get("title_text", "")}</div>
    <div class="sub">{panel.get("sub_text", "")}</div>
  </div>
</div>'''
        elif ptype == "ending":
            body = f'''<div class="page ending">
  {img_tag}
  <div class="overlay">
    <div class="title">{panel.get("title_text", "")}</div>
    <div class="sub">{panel.get("sub_text", "")}</div>
  </div>
</div>'''
        else:
            dialogue = panel.get("dialogue", "")
            knowledge = panel.get("knowledge", "")
            dialogue_html = f'<div class="bubble">{dialogue}</div>' if dialogue else ""
            knowledge_html = f'<div class="knowledge">💡 {knowledge}</div>' if knowledge else ""
            body = f'''<div class="page content">
  {img_tag}
  <div class="overlay">
    <div class="panel-num">{i}</div>
    {dialogue_html}
    {knowledge_html}
  </div>
</div>'''

        html = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{COMIC_PAGE_CSS}</style></head><body>{body}</body></html>'
        pages.append(html)

    return pages


def render_comic_ai(topic: str, content: str, art: str = "ligne-claire") -> tuple[dict, list[bytes]]:
    """Generate comic: script → parallel image gen → HTML composite → render."""
    from playwright.sync_api import sync_playwright

    # Step 1: Script
    script = generate_comic_script(topic, content)
    panels = script.get("panels", [])
    if not panels:
        return script, []

    art_desc = ART_PROMPTS.get(art, ART_PROMPTS["ligne-claire"])

    # Step 2: Build prompts and generate ALL images in parallel
    prompts = []
    for panel in panels:
        scene = panel.get("scene", f"illustration about {topic}")
        prompts.append(f"{scene}. {art_desc}. High quality illustration, vivid colors, detailed.")

    logger.info("Generating %d comic images in parallel...", len(prompts))
    image_data = generate_batch(prompts, size="1024*1024")

    # Step 3: Build HTML composite pages
    html_pages = _build_comic_pages(script, image_data)

    # Step 4: Render to final images
    final_images = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        for html in html_pages:
            page.set_content(html, wait_until="networkidle")
            final_images.append(page.screenshot(type="png"))
        browser.close()

    return script, final_images
