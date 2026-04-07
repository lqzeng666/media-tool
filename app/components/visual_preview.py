"""Step 4: Output generation - Infographic / Video / Podcast."""

import base64

import streamlit as st

from app.state import go_to_step
from app.http import api_post


def render():
    st.header("步骤 4: 生成输出")

    outline = st.session_state.outline
    if outline is None:
        st.warning("请先完成内容结构化")
        if st.button("← 返回上一步"):
            go_to_step(3)
            st.rerun()
        return

    # Quick outline summary
    st.markdown(f"**{outline['title']}** — {len(outline['sections'])} 个章节")

    tab_xhs, tab_infographic, tab_video, tab_podcast = st.tabs([
        "📱 小红书图文",
        "🖼️ 幻灯片 / PPT",
        "🎬 视频 (Remotion)",
        "🎙️ 播客 (Podcast)",
    ])

    with tab_xhs:
        _render_xhs_tab(outline)

    with tab_infographic:
        _render_infographic_tab(outline)

    with tab_video:
        _render_video_tab(outline)

    with tab_podcast:
        _render_podcast_tab(outline)

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← 上一步", use_container_width=True):
            go_to_step(3)
            st.rerun()
    with col3:
        if st.button("重新开始", use_container_width=True):
            from app.state import reset
            reset()
            st.rerun()


def _render_xhs_tab(outline: dict):
    """XHS (小红书) infographic card generation using baoyu-xhs-images methodology."""
    st.markdown("生成小红书风格的精美图文卡片系列，适合社交媒体分享。")

    style_options = {
        "notion": "📝 Notion 知识卡（推荐）",
        "cute": "🎀 甜美少女风",
        "chalkboard": "📚 黑板教学风",
        "fresh": "🌿 清新自然风",
        "bold": "⚡ 醒目冲击风",
    }

    col_style, col_gen = st.columns([3, 1])
    with col_style:
        style = st.selectbox(
            "选择风格",
            options=list(style_options.keys()),
            format_func=lambda k: style_options[k],
            key="xhs_style",
        )
    with col_gen:
        st.write("")  # spacing
        generate_clicked = st.button("🎨 生成小红书图文", type="primary", key="gen_xhs")

    if generate_clicked:
        with st.spinner("AI 正在创作小红书图文卡片...（生成内容 + 渲染图片）"):
            try:
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

    # Display XHS images
    if st.session_state.get("xhs_images"):
        cards = st.session_state.xhs_cards
        images = st.session_state.xhs_images
        st.divider()
        st.markdown(f"**生成完成！共 {len(images)} 张卡片**")

        # Display in a grid (2 columns for portrait images)
        cols = st.columns(2)
        for i, (card, img_b64) in enumerate(zip(cards, images)):
            img_bytes = base64.b64decode(img_b64)
            with cols[i % 2]:
                card_type = card.get("type", "content")
                card_title = card.get("title", f"Card {i+1}")
                type_emoji = {"cover": "📕", "content": "📄", "ending": "🎯"}.get(card_type, "📄")
                st.image(img_bytes, caption=f"{type_emoji} {card_title}", use_container_width=True)
                st.download_button(
                    f"📥 下载",
                    data=img_bytes,
                    file_name=f"xhs-{i+1:02d}-{card_type}.png",
                    mime="image/png",
                    key=f"dl_xhs_{i}",
                )


def _render_infographic_tab(outline: dict):
    """Infographic / Slide deck generation using baoyu-skills methodology."""
    st.markdown("生成精美幻灯片图片，可用于社交媒体分享或演示。")

    col_ppt, col_img = st.columns(2)

    with col_ppt:
        st.markdown("**📊 PPT 文件**")
        if st.button("生成 PPT", type="primary", key="gen_ppt"):
            with st.spinner("正在生成 PPT..."):
                try:
                    resp = api_post(
                        "/api/visuals/generate-ppt",
                        json={"outline": outline},
                        timeout=60.0,
                    )
                    st.session_state.ppt_bytes = resp.content
                except Exception as e:
                    st.error(f"生成失败: {e}")

        if st.session_state.get("ppt_bytes"):
            st.download_button(
                "📥 下载 PPT",
                data=st.session_state.ppt_bytes,
                file_name="presentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key="dl_ppt",
            )

    with col_img:
        st.markdown("**🖼️ 幻灯片图片**")
        if st.button("生成图片", key="gen_images"):
            with st.spinner("正在渲染幻灯片图片..."):
                try:
                    resp = api_post(
                        "/api/visuals/generate-slide-images",
                        json={"outline": outline},
                        timeout=120.0,
                    )
                    st.session_state.slide_images = resp.json()["images"]
                except Exception as e:
                    st.error(f"生成失败: {e}")

    # Show slide images
    if st.session_state.get("slide_images"):
        st.divider()
        st.markdown(f"**预览 ({len(st.session_state.slide_images)} 张)**")
        for i, img_b64 in enumerate(st.session_state.slide_images):
            img_bytes = base64.b64decode(img_b64)
            st.image(img_bytes, caption=f"Slide {i+1}", use_container_width=True)
            st.download_button(
                f"📥 下载 Slide {i+1}",
                data=img_bytes,
                file_name=f"slide-{i:02d}.png",
                mime="image/png",
                key=f"dl_slide_{i}",
            )

    # baoyu-skills integration hint
    st.divider()
    st.markdown("**💡 高级图文生成**")
    st.info(
        "已安装 baoyu-skills。你可以在 Claude Code 中使用以下命令生成更精美的图文：\n\n"
        "```\n"
        "/baoyu-slide-deck output/content.md --style blueprint --lang zh\n"
        "/baoyu-infographic output/content.md --layout bento-grid --style craft-handmade\n"
        "```"
    )
    if st.button("📝 导出内容 Markdown", key="export_md"):
        try:
            resp = api_post(
                "/api/visuals/prepare-slide-deck-content",
                json={"outline": outline},
            )
            md = resp.json()["markdown"]
            st.download_button(
                "📥 下载 content.md",
                data=md.encode("utf-8"),
                file_name="content.md",
                mime="text/markdown",
                key="dl_md",
            )
        except Exception as e:
            st.error(f"导出失败: {e}")


def _render_video_tab(outline: dict):
    """Video generation using Remotion."""
    st.markdown("使用 Remotion (React 视频框架) 生成动画视频。")

    if st.button("🎬 初始化 Remotion 项目", type="primary", key="setup_video"):
        with st.spinner("正在设置 Remotion 项目并写入数据..."):
            try:
                resp = api_post(
                    "/api/visuals/setup-video",
                    json={"outline": outline},
                    timeout=180.0,
                )
                data = resp.json()
                st.session_state.video_project_dir = data["project_dir"]
                st.success("Remotion 项目已就绪！")
            except Exception as e:
                st.error(f"初始化失败: {e}")

    if st.session_state.get("video_project_dir"):
        project_dir = st.session_state.video_project_dir
        st.markdown("**项目已准备好，请在终端执行以下命令：**")
        st.code(f"cd {project_dir}\nnpm run dev    # 预览\nnpm run render # 渲染视频", language="bash")

        st.info(
            "已安装 remotion-best-practices skill。你也可以在 Claude Code 中直接修改 Remotion 组件，\n"
            "skill 会自动提供最佳实践指导（动画、转场、字幕等）。"
        )


def _render_podcast_tab(outline: dict):
    """Podcast generation using Edge TTS."""
    st.markdown("使用 AI 语音合成生成播客音频。")

    voice = st.selectbox(
        "选择语音",
        options=[
            "zh-CN-YunxiNeural",
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-YunjianNeural",
            "zh-CN-XiaoyiNeural",
        ],
        format_func=lambda v: {
            "zh-CN-YunxiNeural": "云希 (男声，推荐)",
            "zh-CN-XiaoxiaoNeural": "晓晓 (女声)",
            "zh-CN-YunjianNeural": "云健 (男声，沉稳)",
            "zh-CN-XiaoyiNeural": "晓艺 (女声，活泼)",
        }.get(v, v),
        key="podcast_voice",
    )

    col_script, col_audio = st.columns(2)

    with col_script:
        if st.button("📝 生成讲稿", key="gen_script"):
            with st.spinner("AI 正在撰写播客讲稿..."):
                try:
                    resp = api_post(
                        "/api/visuals/generate-podcast-script",
                        json={"outline": outline, "voice": voice},
                        timeout=60.0,
                    )
                    st.session_state.podcast_script = resp.json()["script"]
                except Exception as e:
                    st.error(f"生成失败: {e}")

    with col_audio:
        if st.button("🎙️ 生成音频", key="gen_audio",
                     disabled=not st.session_state.get("podcast_script")):
            with st.spinner("正在合成语音..."):
                try:
                    resp = api_post(
                        "/api/visuals/generate-podcast-audio",
                        json={"outline": outline, "voice": voice},
                        timeout=120.0,
                    )
                    st.session_state.podcast_audio = resp.content
                except Exception as e:
                    st.error(f"生成失败: {e}")

    # Show script
    if st.session_state.get("podcast_script"):
        st.divider()
        st.markdown("**讲稿预览**")
        script = st.session_state.podcast_script
        st.text_area("讲稿内容", value=script, height=300, key="script_preview")
        st.download_button(
            "📥 下载讲稿",
            data=script.encode("utf-8"),
            file_name="podcast_script.txt",
            mime="text/plain",
            key="dl_script",
        )

    # Audio player + download
    if st.session_state.get("podcast_audio"):
        st.divider()
        st.markdown("**音频预览**")
        st.audio(st.session_state.podcast_audio, format="audio/mp3")
        st.download_button(
            "📥 下载 MP3",
            data=st.session_state.podcast_audio,
            file_name="podcast.mp3",
            mime="audio/mpeg",
            key="dl_audio",
        )
