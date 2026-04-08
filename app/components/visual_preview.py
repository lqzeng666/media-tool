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
    st.markdown("AI 生成知识漫画，直接在页面预览。")

    art_options = {
        "ligne-claire": "丁丁历险记风（推荐）",
        "manga": "日漫风",
        "ink-brush": "水墨风",
        "chalk": "粉笔风",
    }

    col1, col2 = st.columns([3, 1])
    with col1:
        art = st.selectbox("画风", options=list(art_options.keys()),
                           format_func=lambda k: art_options[k], key="comic_art")
    with col2:
        st.markdown("")
        gen_clicked = st.button("生成漫画", type="primary", key="gen_comic")

    if gen_clicked:
        with st.spinner("AI 正在创作知识漫画..."):
            try:
                content = _prepare_content_markdown(ctx)
                resp = api_post(
                    "/api/visuals/generate-comic",
                    json={"topic": ctx["topic"], "content": content, "art": art},
                    timeout=180.0,
                )
                data = resp.json()
                st.session_state.comic_script = data["script"]
                st.session_state.comic_images = data["images"]
            except Exception as e:
                st.error(f"生成失败: {e}")

    if st.session_state.get("comic_images"):
        script = st.session_state.comic_script
        images = st.session_state.comic_images
        st.markdown("---")
        st.markdown(f"**{script.get('title', '漫画')}** — {len(images)} 格")

        cols = st.columns(2)
        for i, img_b64 in enumerate(images):
            img_bytes = base64.b64decode(img_b64)
            panel = script.get("panels", [{}])[i] if i < len(script.get("panels", [])) else {}
            with cols[i % 2]:
                st.image(img_bytes, caption=f"#{i+1} {panel.get('scene', '')[:30]}",
                         use_container_width=True)
                st.download_button("下载", data=img_bytes,
                                   file_name=f"comic-{i+1:02d}.png", mime="image/png",
                                   key=f"dl_comic_{i}")


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
    st.markdown("将幻灯片合成为视频，可选配音。")

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

    with_audio = st.checkbox("添加 AI 配音", value=True, key="video_audio")
    if with_audio:
        voice = st.selectbox("语音", options=[
            "zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural",
            "zh-CN-YunjianNeural", "zh-CN-XiaoyiNeural",
        ], format_func=lambda v: {
            "zh-CN-YunxiNeural": "云希（男声）",
            "zh-CN-XiaoxiaoNeural": "晓晓（女声）",
            "zh-CN-YunjianNeural": "云健（男声，沉稳）",
            "zh-CN-XiaoyiNeural": "晓艺（女声，活泼）",
        }.get(v, v), key="video_voice")
    else:
        voice = "zh-CN-YunxiNeural"

    if st.button("生成视频", type="primary", key="gen_video"):
        with st.spinner("正在生成视频（渲染幻灯片 + 合成音频 + 编码 MP4）..."):
            try:
                resp = api_post(
                    "/api/visuals/compose-video",
                    json={"outline": outline, "with_audio": with_audio, "voice": voice},
                    timeout=300.0,
                )
                st.session_state.video_bytes = resp.content
            except Exception as e:
                st.error(f"生成失败: {e}")

    if st.session_state.get("video_bytes"):
        st.markdown("---")
        st.video(st.session_state.video_bytes, format="video/mp4")
        st.download_button("下载 MP4", data=st.session_state.video_bytes,
                           file_name="video.mp4", mime="video/mp4", key="dl_video")


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
