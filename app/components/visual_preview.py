"""Step 4: Output generation - multiple modalities."""

import base64

import streamlit as st

from app.state import go_to_step
from app.http import api_post


def _get_content_context():
    """Build a content context dict for generation, works with or without outline."""
    outline = st.session_state.outline
    topic = st.session_state.topic
    materials = st.session_state.materials

    # Outline was skipped - build a minimal one from materials
    if outline is None or outline == "skipped":
        materials_text = "\n".join(
            f"- {m.get('title', '')}: {m.get('text', '')[:200]}"
            for m in materials
        )
        return {
            "has_outline": False,
            "topic": topic,
            "materials": materials,
            "materials_summary": materials_text,
        }

    return {
        "has_outline": True,
        "topic": topic,
        "materials": materials,
        "outline": outline,
    }


def render():
    st.markdown("### 步骤四 · 多模态内容生产")
    st.caption("选择输出格式，一键生成多种形态的内容")

    ctx = _get_content_context()

    if ctx["has_outline"]:
        outline = ctx["outline"]
        st.markdown(f"**{outline['title']}** — {len(outline['sections'])} 个章节")
    else:
        st.info(f"已跳过结构化提取，将基于主题「{ctx['topic']}」和 {len(ctx['materials'])} 篇素材直接生成")

    tab_xhs, tab_comic, tab_infographic, tab_video, tab_podcast = st.tabs([
        "📱 小红书图文",
        "🎨 漫画",
        "🖼️ 幻灯片 / PPT",
        "🎬 视频",
        "🎙️ 播客",
    ])

    with tab_xhs:
        _render_xhs_tab(ctx)
    with tab_comic:
        _render_comic_tab(ctx)
    with tab_infographic:
        _render_infographic_tab(ctx)
    with tab_video:
        _render_video_tab(ctx)
    with tab_podcast:
        _render_podcast_tab(ctx)

    # Navigation
    st.markdown("---")
    col1, _, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← 上一步", use_container_width=True):
            go_to_step(3)
            st.rerun()
    with col3:
        if st.button("重新开始", use_container_width=True):
            from app.state import reset
            reset()
            st.rerun()


def _get_outline_or_generate(ctx):
    """Get existing outline or auto-generate one when skipped."""
    if ctx["has_outline"]:
        return ctx["outline"]

    # Auto-generate outline from materials
    with st.spinner("正在根据素材自动生成内容结构..."):
        resp = api_post(
            "/api/structure/generate",
            json={
                "topic": ctx["topic"],
                "materials": ctx["materials"],
            },
            timeout=120.0,
        )
        outline = resp.json()["outline"]
        st.session_state.outline = outline
        return outline


def _prepare_content_markdown(ctx):
    """Prepare markdown content for skills, works with or without outline."""
    if ctx["has_outline"]:
        outline = ctx["outline"]
        lines = [f"# {outline['title']}", "", f"> {outline['subtitle']}", ""]
        for sec in outline["sections"]:
            lines.append(f"## {sec['title']}")
            for b in sec["bullets"]:
                lines.append(f"- {b}")
            lines.append("")
        return "\n".join(lines)

    # No outline - use raw materials
    lines = [f"# {ctx['topic']}", ""]
    for m in ctx["materials"]:
        lines.append(f"## {m.get('title', '')}")
        lines.append(m.get("text", "")[:1000])
        lines.append("")
    return "\n".join(lines)


# ─── XHS Tab ─────────────────────────────────────────────

def _render_xhs_tab(ctx):
    st.markdown("生成小红书风格的精美图文卡片系列。")

    style_options = {
        "notion": "Notion 知识卡（推荐）",
        "cute": "甜美少女风",
        "chalkboard": "黑板教学风",
        "fresh": "清新自然风",
        "bold": "醒目冲击风",
    }

    col_style, col_gen = st.columns([3, 1])
    with col_style:
        style = st.selectbox("风格", options=list(style_options.keys()),
                             format_func=lambda k: style_options[k], key="xhs_style")
    with col_gen:
        st.markdown("")
        generate_clicked = st.button("生成图文", type="primary", key="gen_xhs")

    if generate_clicked:
        with st.spinner("AI 正在创作小红书图文卡片..."):
            try:
                outline = _get_outline_or_generate(ctx)
                resp = api_post(
                    "/api/visuals/generate-xhs-images",
                    json={"outline": outline, "style": style},
                    timeout=180.0,
                )
                data = resp.json()
                st.session_state.xhs_cards = data["cards"]
                st.session_state.xhs_images = data["images"]
            except Exception as e:
                st.error(f"生成失败: {e}")

    if st.session_state.get("xhs_images"):
        cards = st.session_state.xhs_cards
        images = st.session_state.xhs_images
        st.markdown("---")
        cols = st.columns(2)
        for i, (card, img_b64) in enumerate(zip(cards, images)):
            img_bytes = base64.b64decode(img_b64)
            with cols[i % 2]:
                card_title = card.get("title", f"Card {i+1}")
                st.image(img_bytes, caption=card_title, use_container_width=True)
                st.download_button(f"下载", data=img_bytes,
                                   file_name=f"xhs-{i+1:02d}.png", mime="image/png",
                                   key=f"dl_xhs_{i}")


# ─── Comic Tab ───────────────────────────────────────────

def _render_comic_tab(ctx):
    st.markdown("生成知识漫画或封面图，由 baoyu-comic / baoyu-cover-image skill 驱动。")

    sub_comic, sub_cover = st.tabs(["知识漫画", "封面图"])

    with sub_comic:
        st.markdown("将内容转化为多格漫画，支持多种画风。")

        col1, col2, col3 = st.columns(3)
        with col1:
            art_style = st.selectbox("画风", options=[
                "ligne-claire", "manga", "realistic", "ink-brush", "chalk", "minimalist",
            ], format_func=lambda x: {
                "ligne-claire": "丁丁历险记风（默认）",
                "manga": "日漫风",
                "realistic": "写实风",
                "ink-brush": "水墨风",
                "chalk": "粉笔风",
                "minimalist": "极简风",
            }.get(x, x), key="comic_art")
        with col2:
            tone = st.selectbox("氛围", options=[
                "neutral", "warm", "dramatic", "energetic", "vintage",
            ], format_func=lambda x: {
                "neutral": "中性（默认）",
                "warm": "温暖",
                "dramatic": "戏剧性",
                "energetic": "活力",
                "vintage": "复古",
            }.get(x, x), key="comic_tone")
        with col3:
            layout = st.selectbox("布局", options=[
                "standard", "cinematic", "four-panel", "webtoon",
            ], format_func=lambda x: {
                "standard": "标准（默认）",
                "cinematic": "电影分镜",
                "four-panel": "四格漫画",
                "webtoon": "条漫",
            }.get(x, x), key="comic_layout")

        if st.button("生成漫画内容", type="primary", key="gen_comic"):
            md_content = _prepare_content_markdown(ctx)
            # Save content file for skill
            import os
            os.makedirs("output", exist_ok=True)
            with open("output/comic-source.md", "w", encoding="utf-8") as f:
                f.write(md_content)

            st.success("内容已保存到 `output/comic-source.md`")
            st.markdown("在 Claude Code 中执行以下命令生成漫画：")
            st.code(
                f"/baoyu-comic output/comic-source.md --art {art_style} --tone {tone} --layout {layout} --lang zh",
                language="bash",
            )

    with sub_cover:
        st.markdown("为内容生成精美封面图。")

        col1, col2 = st.columns(2)
        with col1:
            cover_type = st.selectbox("类型", options=[
                "conceptual", "hero", "typography", "metaphor", "scene", "minimal",
            ], format_func=lambda x: {
                "conceptual": "概念图（推荐）",
                "hero": "主视觉",
                "typography": "文字排版",
                "metaphor": "隐喻",
                "scene": "场景",
                "minimal": "极简",
            }.get(x, x), key="cover_type")
        with col2:
            cover_palette = st.selectbox("色调", options=[
                "warm", "elegant", "cool", "dark", "vivid", "pastel", "mono",
            ], format_func=lambda x: {
                "warm": "暖色调",
                "elegant": "优雅",
                "cool": "冷色调",
                "dark": "暗黑",
                "vivid": "鲜艳",
                "pastel": "粉彩",
                "mono": "黑白",
            }.get(x, x), key="cover_palette")

        col3, col4 = st.columns(2)
        with col3:
            cover_rendering = st.selectbox("渲染风格", options=[
                "flat-vector", "hand-drawn", "painterly", "digital", "pixel",
            ], format_func=lambda x: {
                "flat-vector": "扁平矢量（推荐）",
                "hand-drawn": "手绘",
                "painterly": "油画",
                "digital": "数字",
                "pixel": "像素",
            }.get(x, x), key="cover_rendering")
        with col4:
            cover_aspect = st.selectbox("比例", options=[
                "16:9", "1:1", "3:4", "2.35:1",
            ], key="cover_aspect")

        if st.button("生成封面图", type="primary", key="gen_cover"):
            md_content = _prepare_content_markdown(ctx)
            import os
            os.makedirs("output", exist_ok=True)
            with open("output/cover-source.md", "w", encoding="utf-8") as f:
                f.write(md_content)

            st.success("内容已保存到 `output/cover-source.md`")
            st.markdown("在 Claude Code 中执行以下命令生成封面：")
            st.code(
                f"/baoyu-cover-image output/cover-source.md --type {cover_type} --palette {cover_palette} --rendering {cover_rendering} --aspect {cover_aspect} --lang zh",
                language="bash",
            )


# ─── Infographic Tab ─────────────────────────────────────

def _render_infographic_tab(ctx):
    st.markdown("生成幻灯片图片或 PPT 文件。")

    if not ctx["has_outline"]:
        st.caption("需要先生成结构化大纲才能生成幻灯片。")
        if st.button("自动生成大纲并继续", type="primary", key="auto_outline_ppt"):
            try:
                _get_outline_or_generate(ctx)
                st.rerun()
            except Exception as e:
                st.error(f"生成失败: {e}")
        return

    outline = ctx["outline"]
    col_ppt, col_img = st.columns(2)

    with col_ppt:
        st.markdown("**PPT 文件**")
        if st.button("生成 PPT", type="primary", key="gen_ppt"):
            with st.spinner("生成中..."):
                try:
                    resp = api_post("/api/visuals/generate-ppt",
                                   json={"outline": outline}, timeout=60.0)
                    st.session_state.ppt_bytes = resp.content
                except Exception as e:
                    st.error(f"失败: {e}")

        if st.session_state.get("ppt_bytes"):
            st.download_button("下载 PPT", data=st.session_state.ppt_bytes,
                               file_name="presentation.pptx",
                               mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                               key="dl_ppt")

    with col_img:
        st.markdown("**幻灯片图片**")
        if st.button("生成图片", key="gen_images"):
            with st.spinner("渲染中..."):
                try:
                    resp = api_post("/api/visuals/generate-slide-images",
                                   json={"outline": outline}, timeout=120.0)
                    st.session_state.slide_images = resp.json()["images"]
                except Exception as e:
                    st.error(f"失败: {e}")

    if st.session_state.get("slide_images"):
        st.markdown("---")
        for i, img_b64 in enumerate(st.session_state.slide_images):
            img_bytes = base64.b64decode(img_b64)
            st.image(img_bytes, caption=f"Slide {i+1}", use_container_width=True)
            st.download_button(f"下载 Slide {i+1}", data=img_bytes,
                               file_name=f"slide-{i:02d}.png", mime="image/png",
                               key=f"dl_slide_{i}")

    # Export markdown
    st.markdown("---")
    if st.button("导出 Markdown", key="export_md"):
        md = _prepare_content_markdown(ctx)
        st.download_button("下载 content.md", data=md.encode("utf-8"),
                           file_name="content.md", mime="text/markdown", key="dl_md")


# ─── Video Tab ───────────────────────────────────────────

def _render_video_tab(ctx):
    st.markdown("使用 Remotion 生成动画视频。")

    if not ctx["has_outline"]:
        st.caption("需要先生成结构化大纲。")
        if st.button("自动生成大纲并继续", type="primary", key="auto_outline_video"):
            try:
                _get_outline_or_generate(ctx)
                st.rerun()
            except Exception as e:
                st.error(f"失败: {e}")
        return

    outline = ctx["outline"]
    if st.button("初始化 Remotion 项目", type="primary", key="setup_video"):
        with st.spinner("设置中..."):
            try:
                resp = api_post("/api/visuals/setup-video",
                               json={"outline": outline}, timeout=180.0)
                st.session_state.video_project_dir = resp.json()["project_dir"]
                st.success("Remotion 项目已就绪！")
            except Exception as e:
                st.error(f"失败: {e}")

    if st.session_state.get("video_project_dir"):
        d = st.session_state.video_project_dir
        st.code(f"cd {d}\nnpm run dev    # 预览\nnpm run render # 渲染视频", language="bash")


# ─── Podcast Tab ─────────────────────────────────────────

def _render_podcast_tab(ctx):
    st.markdown("AI 语音合成生成播客音频。")

    if not ctx["has_outline"]:
        st.caption("需要先生成结构化大纲。")
        if st.button("自动生成大纲并继续", type="primary", key="auto_outline_podcast"):
            try:
                _get_outline_or_generate(ctx)
                st.rerun()
            except Exception as e:
                st.error(f"失败: {e}")
        return

    outline = ctx["outline"]
    voice = st.selectbox("语音", options=[
        "zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunjianNeural", "zh-CN-XiaoyiNeural",
    ], format_func=lambda v: {
        "zh-CN-YunxiNeural": "云希（男声）",
        "zh-CN-XiaoxiaoNeural": "晓晓（女声）",
        "zh-CN-YunjianNeural": "云健（男声，沉稳）",
        "zh-CN-XiaoyiNeural": "晓艺（女声，活泼）",
    }.get(v, v), key="podcast_voice")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("生成讲稿", key="gen_script"):
            with st.spinner("撰写中..."):
                try:
                    resp = api_post("/api/visuals/generate-podcast-script",
                                   json={"outline": outline, "voice": voice}, timeout=60.0)
                    st.session_state.podcast_script = resp.json()["script"]
                except Exception as e:
                    st.error(f"失败: {e}")
    with col2:
        if st.button("生成音频", key="gen_audio",
                     disabled=not st.session_state.get("podcast_script")):
            with st.spinner("合成中..."):
                try:
                    resp = api_post("/api/visuals/generate-podcast-audio",
                                   json={"outline": outline, "voice": voice}, timeout=120.0)
                    st.session_state.podcast_audio = resp.content
                except Exception as e:
                    st.error(f"失败: {e}")

    if st.session_state.get("podcast_script"):
        st.markdown("---")
        st.text_area("讲稿", value=st.session_state.podcast_script, height=250, key="script_preview")
        st.download_button("下载讲稿", data=st.session_state.podcast_script.encode("utf-8"),
                           file_name="podcast_script.txt", mime="text/plain", key="dl_script")

    if st.session_state.get("podcast_audio"):
        st.markdown("---")
        st.audio(st.session_state.podcast_audio, format="audio/mp3")
        st.download_button("下载 MP3", data=st.session_state.podcast_audio,
                           file_name="podcast.mp3", mime="audio/mpeg", key="dl_audio")
