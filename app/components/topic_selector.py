"""Step 1: Topic selection UI - custom input or trending topic recommendation."""

import streamlit as st

from app.state import go_to_step
from app.http import api_post


def render():
    st.header("步骤 1: 选择主题")

    tab_custom, tab_trending = st.tabs(["✏️ 自定义主题", "🔥 热点推荐"])

    with tab_custom:
        st.markdown("输入你感兴趣的资讯主题。")
        topic = st.text_input(
            "主题",
            value=st.session_state.get("topic", ""),
            placeholder="例如：2024年AI行业发展趋势",
        )
        if topic:
            st.session_state.topic = topic

    with tab_trending:
        st.markdown("选择时间范围，AI 将自动检索并推荐热门话题。")

        col_time, col_region = st.columns(2)
        with col_time:
            time_label = st.selectbox(
                "时间范围",
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

        if st.button("🔍 获取热点话题", type="primary"):
            with st.spinner("正在联网检索热门资讯..."):
                try:
                    resp = api_post(
                        "/api/topics/detect",
                        json={"time_range": time_range, "region": region},
                        timeout=60.0,
                    )
                    st.session_state.trending_topics = resp.json()["topics"]
                except Exception as e:
                    st.error(f"获取热点失败: {e}")

        # Display trending topics
        topics = st.session_state.get("trending_topics", [])
        if topics:
            st.markdown("**点击选择一个话题：**")
            for i, t in enumerate(topics):
                keywords_str = "、".join(t["keywords"])
                with st.container():
                    col_info, col_btn = st.columns([8, 2])
                    with col_info:
                        st.markdown(f"**{t['title']}**")
                        st.caption(f"{t['summary']}  ·  关键词: {keywords_str}")
                    with col_btn:
                        if st.button("选择", key=f"pick_topic_{i}"):
                            st.session_state.topic = t["title"]
                            st.rerun()

    st.divider()

    current_topic = st.session_state.get("topic", "")
    if current_topic:
        st.info(f"当前选择: **{current_topic}**")

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("下一步 →", disabled=not current_topic, use_container_width=True):
            go_to_step(2)
            st.rerun()
