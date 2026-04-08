"""Step 3: Content structuring - custom template or AI auto-generate."""

import streamlit as st

from app.state import go_to_step
from app.http import api_post

# Preset structure templates
TEMPLATES = {
    "通用资讯": {
        "description": "适合新闻报道、行业动态等通用资讯内容",
        "structure": "背景概述 → 核心事件 → 关键数据 → 多方观点 → 影响分析 → 未来展望",
        "sections": ["背景概述", "核心事件", "关键数据", "多方观点", "影响分析", "未来展望"],
    },
    "产品测评": {
        "description": "适合产品对比、使用体验等测评内容",
        "structure": "产品概览 → 核心功能 → 使用体验 → 优缺点对比 → 适用人群 → 总结推荐",
        "sections": ["产品概览", "核心功能", "使用体验", "优缺点对比", "适用人群", "总结推荐"],
    },
    "技术解析": {
        "description": "适合技术原理、架构分析等深度内容",
        "structure": "技术背景 → 核心原理 → 架构设计 → 关键创新 → 应用场景 → 发展趋势",
        "sections": ["技术背景", "核心原理", "架构设计", "关键创新", "应用场景", "发展趋势"],
    },
    "商业分析": {
        "description": "适合市场分析、商业模式等商业内容",
        "structure": "市场概况 → 商业模式 → 竞争格局 → 财务数据 → 风险因素 → 投资建议",
        "sections": ["市场概况", "商业模式", "竞争格局", "财务数据", "风险因素", "投资建议"],
    },
    "教程指南": {
        "description": "适合操作教程、入门指南等教学内容",
        "structure": "目标说明 → 前置准备 → 步骤详解 → 常见问题 → 进阶技巧 → 总结回顾",
        "sections": ["目标说明", "前置准备", "步骤详解", "常见问题", "进阶技巧", "总结回顾"],
    },
    "自定义": {
        "description": "完全自定义内容框架",
        "structure": "",
        "sections": [],
    },
}


def render():
    st.markdown("### 步骤三 · 结构化提取")
    st.caption("AI 分析素材并生成结构化大纲，可自由编辑调整")

    topic = st.session_state.topic
    materials_count = len(st.session_state.materials)
    st.markdown(f"主题：**{topic}**　｜　素材：**{materials_count}** 篇")

    # If outline already generated, show editor
    if st.session_state.outline is not None:
        _render_outline_editor()
        return

    # Otherwise show generation options
    st.markdown("---")
    tab_ai, tab_template = st.tabs(["AI 智能生成", "选择框架模板"])

    with tab_ai:
        st.markdown("")
        st.markdown("AI 将自动分析素材内容，智能生成结构化大纲。")

        custom_instruction = st.text_area(
            "补充指令（可选）",
            placeholder="对生成内容的额外要求，如「侧重技术细节」「语言活泼有趣」「控制在 8 个章节以内」",
            height=80,
            key="ai_instruction",
        )

        if st.button("AI 一键生成", type="primary"):
            with st.spinner("AI 正在分析素材并生成结构化大纲..."):
                try:
                    resp = api_post(
                        "/api/structure/generate",
                        json={
                            "topic": topic,
                            "materials": st.session_state.materials,
                            "instruction": custom_instruction,
                        },
                        timeout=120.0,
                    )
                    st.session_state.outline = resp.json()["outline"]
                    st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {e}")

    with tab_template:
        st.markdown("")
        template_name = st.selectbox(
            "选择内容框架",
            options=list(TEMPLATES.keys()),
            format_func=lambda k: f"{k} — {TEMPLATES[k]['description']}",
        )

        template = TEMPLATES[template_name]

        if template_name == "自定义":
            st.markdown("输入自定义章节标题（每行一个）：")
            custom_sections = st.text_area(
                "章节列表",
                placeholder="背景介绍\n核心观点\n数据支撑\n案例分析\n总结展望",
                height=150,
                key="custom_sections",
                label_visibility="collapsed",
            )
            section_names = [s.strip() for s in custom_sections.split("\n") if s.strip()]
        else:
            st.markdown(f"**框架结构**：{template['structure']}")
            section_names = list(template["sections"])

            # Allow editing
            st.markdown("可以调整章节（每行一个）：")
            edited = st.text_area(
                "编辑章节",
                value="\n".join(section_names),
                height=150,
                key="edit_template_sections",
                label_visibility="collapsed",
            )
            section_names = [s.strip() for s in edited.split("\n") if s.strip()]

        if section_names:
            st.caption(f"共 {len(section_names)} 个章节")

        if st.button("按框架生成内容", type="primary", disabled=not section_names):
            with st.spinner("AI 正在按指定框架填充内容..."):
                try:
                    resp = api_post(
                        "/api/structure/generate",
                        json={
                            "topic": topic,
                            "materials": st.session_state.materials,
                            "instruction": f"请严格按照以下章节结构组织内容：{' → '.join(section_names)}。每个章节 2-4 个要点。",
                        },
                        timeout=120.0,
                    )
                    st.session_state.outline = resp.json()["outline"]
                    st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {e}")

    # Navigation
    st.markdown("---")
    col1, _, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← 上一步", use_container_width=True):
            go_to_step(2)
            st.rerun()


def _render_outline_editor():
    """Render the outline editor when outline is already generated."""
    outline = st.session_state.outline

    st.markdown("---")

    # Title editing
    col_t, col_s = st.columns(2)
    with col_t:
        outline["title"] = st.text_input("标题", value=outline["title"], key="edit_title")
    with col_s:
        outline["subtitle"] = st.text_input("副标题", value=outline["subtitle"], key="edit_subtitle")

    st.markdown("")

    # Sections
    sections_to_delete = []
    for i, section in enumerate(outline["sections"]):
        col_title, col_del = st.columns([9, 1])
        with col_title:
            section["title"] = st.text_input(
                f"章节 {i+1}",
                value=section["title"],
                key=f"sec_title_{i}",
            )
        with col_del:
            st.markdown("")
            if st.button("✕", key=f"del_{i}", help="删除"):
                sections_to_delete.append(i)

        bullets_text = "\n".join(section["bullets"])
        new_bullets = st.text_area(
            "要点",
            value=bullets_text,
            key=f"sec_bullets_{i}",
            height=80,
            label_visibility="collapsed",
        )
        section["bullets"] = [b.strip() for b in new_bullets.split("\n") if b.strip()]

        # Per-section actions
        col_r1, col_r2, _ = st.columns([1, 1, 6])
        with col_r1:
            if st.button("重新生成", key=f"regen_{i}"):
                with st.spinner(f"重新生成章节 {i+1}..."):
                    try:
                        resp = api_post(
                            "/api/structure/regenerate-section",
                            json={
                                "outline_title": outline["title"],
                                "section": section,
                                "instruction": "重新生成此章节，使内容更丰富更有深度",
                            },
                            timeout=60.0,
                        )
                        outline["sections"][i] = resp.json()["section"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"失败: {e}")

        st.markdown("<hr style='margin:8px 0;border-color:#EDE9E3'>", unsafe_allow_html=True)

    # Delete sections
    if sections_to_delete:
        for idx in sorted(sections_to_delete, reverse=True):
            outline["sections"].pop(idx)
        st.session_state.outline = outline
        st.rerun()

    # Global actions
    col_a1, col_a2, _ = st.columns([1, 1, 5])
    with col_a1:
        if st.button("重新生成全部"):
            st.session_state.outline = None
            st.rerun()
    with col_a2:
        if st.button("换个框架"):
            st.session_state.outline = None
            st.rerun()

    st.session_state.outline = outline

    # Navigation
    st.markdown("---")
    col1, _, col3 = st.columns([1, 6, 1])
    with col1:
        if st.button("← 上一步", use_container_width=True):
            go_to_step(2)
            st.rerun()
    with col3:
        if st.button("下一步 →", use_container_width=True):
            go_to_step(4)
            st.rerun()
