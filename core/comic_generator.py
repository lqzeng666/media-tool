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


def generate_comic_script(topic: str, content: str, max_retries: int = 2) -> dict:
    """Generate a comic script from content, with JSON parse retry."""
    for attempt in range(max_retries + 1):
        response = chat(
            messages=[{"role": "user", "content": COMIC_PROMPT.format(
                topic=topic, content=content[:3000],
            )}],
            temperature=0.7,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            if attempt < max_retries:
                logger.warning("JSON parse failed, retrying (attempt %d)", attempt + 1)
                continue
            # Last resort: return minimal script
            logger.error("Failed to parse comic script after %d attempts", max_retries + 1)
            return {
                "title": topic,
                "panels": [
                    {"type": "cover", "scene": f"Cover illustration about {topic}", "text_overlay": topic, "narrator": ""},
                    {"type": "panel", "scene": f"Educational illustration explaining {topic}", "dialogue": "", "narrator": content[:200]},
                ],
            }


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
            urls = generate_image(prompt, size="1024*1024", timeout=180)
            if urls:
                img_bytes = download_image(urls[0])
                images.append(img_bytes)
            else:
                logger.warning("No image URL returned for panel %d", i)
                images.append(b"")
        except Exception as e:
            logger.error("Failed to generate panel %d: %s", i, e)
            images.append(b"")

    # Step 3: Overlay text on images
    final_images = []
    for i, (img_bytes, panel) in enumerate(zip(images, panels)):
        if not img_bytes:
            continue
        try:
            img_bytes = _overlay_text(img_bytes, panel)
        except Exception as e:
            logger.warning("Failed to overlay text on panel %d: %s", i, e)
        final_images.append(img_bytes)

    return script, final_images


def _overlay_text(img_bytes: bytes, panel: dict) -> bytes:
    """Overlay dialogue and narrator text on a comic panel image."""
    from PIL import Image, ImageDraw, ImageFont
    import io

    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    width, height = img.size
    ptype = panel.get("type", "panel")

    # Try to load a Chinese font
    font_large = None
    font_medium = None
    font_small = None
    for font_path in [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
    ]:
        try:
            font_large = ImageFont.truetype(font_path, 42)
            font_medium = ImageFont.truetype(font_path, 28)
            font_small = ImageFont.truetype(font_path, 22)
            break
        except (OSError, IOError):
            continue

    if font_large is None:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    if ptype == "cover":
        # Title banner at top
        title = panel.get("text_overlay", "") or panel.get("dialogue", "")
        if title:
            # Semi-transparent banner
            banner_h = 120
            draw.rectangle([(0, 0), (width, banner_h)], fill=(0, 0, 0, 160))
            _draw_centered_text(draw, title, font_large, width, 20, fill=(255, 255, 255, 255))

        # Subtitle at bottom
        narrator = panel.get("narrator", "")
        if narrator:
            banner_y = height - 80
            draw.rectangle([(0, banner_y), (width, height)], fill=(0, 0, 0, 120))
            _draw_centered_text(draw, narrator, font_small, width, banner_y + 15, fill=(220, 220, 220, 255))
    else:
        # Dialogue bubble at top
        dialogue = panel.get("dialogue", "")
        if dialogue:
            bubble_h = max(70, 30 + len(dialogue) // 15 * 30)
            bubble_h = min(bubble_h, 160)
            margin = 40
            draw.rounded_rectangle(
                [(margin, 20), (width - margin, 20 + bubble_h)],
                radius=20, fill=(255, 255, 255, 220), outline=(60, 60, 60, 200), width=2,
            )
            _draw_wrapped_text(draw, dialogue, font_medium, margin + 20, 30, width - 2 * margin - 40,
                               fill=(30, 30, 30, 255))

        # Narrator box at bottom
        narrator = panel.get("narrator", "")
        if narrator:
            box_h = max(60, 20 + len(narrator) // 20 * 28)
            box_h = min(box_h, 140)
            box_y = height - box_h - 10
            draw.rectangle([(0, box_y), (width, height)], fill=(0, 0, 0, 150))
            _draw_wrapped_text(draw, narrator, font_small, 20, box_y + 10, width - 40,
                               fill=(240, 240, 240, 255))

    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def _draw_centered_text(draw, text, font, width, y, fill):
    """Draw centered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = max(0, (width - tw) // 2)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_wrapped_text(draw, text, font, x, y, max_width, fill, line_spacing=4):
    """Draw text with word wrapping."""
    chars = list(text)
    lines = []
    current = ""
    for ch in chars:
        test = current + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
