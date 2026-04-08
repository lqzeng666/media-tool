"""Step 1: Topic selection UI - custom input or trending topic recommendation."""

import streamlit as st

from app.state import go_to_step
from app.http import api_post

# Category definitions with search queries
CATEGORIES = {
    "AI 领域": {
        "queries_zh": ["人工智能最新进展", "AI应用落地", "大模型动态"],
        "queries_en": ["artificial intelligence news", "AI breakthroughs", "LLM updates"],
    },
    "商业内容": {
        "queries_zh": ["商业头条", "创业融资", "企业战略"],
        "queries_en": ["business news", "startup funding", "corporate strategy"],
    },
    "互联网": {
        "queries_zh": ["互联网行业动态", "科技公司新闻", "产品发布"],
        "queries_en": ["internet industry news", "tech company updates", "product launches"],
    },
    "新闻时政": {
        "queries_zh": ["今日要闻", "时政热点", "社会民生"],
        "queries_en": ["breaking news today", "political news", "current events"],
    },
    "科技前沿": {
        "queries_zh": ["前沿科技", "科学发现", "技术突破"],
        "queries_en": ["technology breakthroughs", "science discoveries", "tech innovation"],
    },
    "财经金融": {
        "queries_zh": ["财经头条", "股市动态", "经济趋势"],
        "queries_en": ["finance news", "stock market", "economic trends"],
    },
}


def render():
    st.markdown("### 步骤一 · 选择主题")
    st.caption("确定你想要了解和展示的资讯主题")

    tab_custom, tab_trending = st.tabs(["自定义输入", "热点推荐"])

    with tab_custom:
        st.markdown("")
        topic = st.text_input(
            "主题关键词",
            value=st.session_state.get("topic", ""),
            placeholder="输入你感兴趣的主题，如「AI Agent 发展趋势」",
            label_visibility="collapsed",
        )
        st.caption("输入你感兴趣的资讯主题，后续将围绕该主题采集和生成内容。")
        if topic:
            st.session_state.topic = topic

    with tab_trending:
        st.markdown("")

        col_cat, col_time, col_region = st.columns([2, 1, 1])
        with col_cat:
            category = st.selectbox(
                "类别",
                options=list(CATEGORIES.keys()),
                index=0,
            )
        with col_time:
            time_label = st.selectbox(
                "时间",
                options=["最近一天", "最近一周", "最近一月"],
                index=0,
            )
            time_map = {"最近一天": "d", "最近一周": "w", "最近一月": "m"}
            time_range = time_map[time_label]
        with col_region:
            region_label = st.selectbox(
                "地区",
                options=["中国", "美国", "全球"],
                index=0,
            )
            region_map = {"中国": "zh-cn", "美国": "us-en", "全球": "wt-wt"}
            region = region_map[region_label]

        if st.button("获取热点话题", type="primary"):
            with st.spinner("正在联网检索..."):
                try:
                    resp = api_post(
                        "/api/topics/detect",
                        json={
                            "time_range": time_range,
                            "region": region,
                            "category": category,
                        },
                        timeout=60.0,
                    )
                    st.session_state.trending_topics = resp.json()["topics"]
                except Exception as e:
                    st.error(f"获取失败: {e}")

        # Display trending topics
        topics = st.session_state.get("trending_topics", [])
        if topics:
            st.markdown("")
            for i, t in enumerate(topics):
                keywords_str = " · ".join(t["keywords"])
                with st.container():
                    col_info, col_btn = st.columns([8, 1])
                    with col_info:
                        st.markdown(f"**{t['title']}**")
                        st.caption(f"{t['summary']}　｜　{keywords_str}")
                    with col_btn:
                        if st.button("选用", key=f"pick_topic_{i}", use_container_width=True):
                            st.session_state.topic = t["title"]
                            st.rerun()
                    st.markdown("<hr style='margin:4px 0;border-color:#EDE9E3'>", unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    current_topic = st.session_state.get("topic", "")
    if current_topic:
        st.markdown(f"当前主题：**{current_topic}**")

    col1, col2 = st.columns([7, 1])
    with col2:
        if st.button("下一步 →", disabled=not current_topic, use_container_width=True):
            go_to_step(2)
            st.rerun()
