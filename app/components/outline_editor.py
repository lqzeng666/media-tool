"""Step 3: Content structuring and outline editing UI."""

import streamlit as st

from app.state import go_to_step
from app.http import api_post


def render():
    st.header("步骤 3: 内容结构化")
    st.markdown(f"当前主题: **{st.session_state.topic}** | 素材: {len(st.session_state.materials)} 篇")

    # Generate outline
    if st.session_state.outline is None:
        if st.button("生成大纲", type="primary"):
            with st.spinner("AI 正在分析素材并生成内容大纲..."):
                try:
                    resp = api_post(
                        "/api/structure/generate",
                        json={
                            "topic": st.session_state.topic,
                            "materials": st.session_state.materials,
                        },
                        timeout=120.0,
                    )
                    st.session_state.outline = resp.json()["outline"]
                    st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {e}")
        return

    outline = st.session_state.outline

    # Display editable outline
    st.subheader(outline["title"])
    st.caption(outline["subtitle"])

    new_title = st.text_input("标题", value=outline["title"], key="edit_title")
    new_subtitle = st.text_input("副标题", value=outline["subtitle"], key="edit_subtitle")
    outline["title"] = new_title
    outline["subtitle"] = new_subtitle

    st.divider()

    sections_to_delete = []
    for i, section in enumerate(outline["sections"]):
        col_title, col_del = st.columns([9, 1])
        with col_title:
            section["title"] = st.text_input(
                f"章节 {i+1} 标题",
                value=section["title"],
                key=f"sec_title_{i}",
            )
        with col_del:
            st.write("")  # spacing
            if st.button("🗑", key=f"del_{i}", help="删除此章节"):
                sections_to_delete.append(i)

        # Edit bullets
        bullets_text = "\n".join(section["bullets"])
        new_bullets = st.text_area(
            f"要点（每行一个）",
            value=bullets_text,
            key=f"sec_bullets_{i}",
            height=100,
        )
        section["bullets"] = [b.strip() for b in new_bullets.split("\n") if b.strip()]

        # Regenerate button
        col_regen, col_space = st.columns([2, 8])
        with col_regen:
            if st.button("🔄 重新生成", key=f"regen_{i}"):
                with st.spinner(f"重新生成章节 {i+1}..."):
                    try:
                        resp = api_post(
                            "/api/structure/regenerate-section",
                            json={
                                "outline_title": outline["title"],
                                "section": section,
                                "instruction": "重新生成此章节，使内容更丰富",
                            },
                            timeout=60.0,
                        )
                        outline["sections"][i] = resp.json()["section"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"重新生成失败: {e}")

        st.divider()

    # Delete marked sections
    if sections_to_delete:
        for idx in sorted(sections_to_delete, reverse=True):
            outline["sections"].pop(idx)
        st.session_state.outline = outline
        st.rerun()

    # Regenerate all
    col_actions = st.columns(3)
    with col_actions[0]:
        if st.button("🔄 重新生成全部大纲"):
            st.session_state.outline = None
            st.rerun()

    st.session_state.outline = outline

    st.divider()

    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← 上一步", use_container_width=True):
            go_to_step(2)
            st.rerun()
    with col3:
        if st.button("下一步 →", use_container_width=True):
            go_to_step(4)
            st.rerun()
