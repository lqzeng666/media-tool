"""Step 2: Source material management - manual URLs or AI auto-search."""

import streamlit as st

from app.state import go_to_step
from app.http import api_post


def render():
    st.markdown("### 步骤二 · 勾选信息")
    st.caption("提供相关素材链接，或让 AI 自动搜索")
    st.markdown(f"当前主题: **{st.session_state.topic}**")

    tab_manual, tab_auto = st.tabs(["🔗 手动提供链接", "🤖 AI 自动搜索"])

    with tab_manual:
        st.markdown("输入相关网页链接（每行一个），系统将自动抓取并提取正文。")
        urls_text = st.text_area(
            "网页链接",
            value=st.session_state.get("urls_text", ""),
            height=150,
            placeholder="https://example.com/article-1\nhttps://example.com/article-2",
        )
        st.session_state.urls_text = urls_text
        urls = [u.strip() for u in urls_text.strip().split("\n") if u.strip()]

        if st.button("🔗 抓取内容", disabled=not urls):
            _fetch_urls(urls)

    with tab_auto:
        st.markdown("AI 将根据主题自动搜索相关文章，你可以选择需要的素材。")

        col_q, col_t = st.columns([3, 1])
        with col_q:
            search_query = st.text_input(
                "搜索关键词",
                value=st.session_state.get("topic", ""),
                key="search_query",
            )
        with col_t:
            search_type = st.selectbox(
                "搜索类型",
                options=["新闻", "网页"],
                index=0,
            )

        col_n, col_time = st.columns(2)
        with col_n:
            max_results = st.slider("搜索数量", 3, 15, 8)
        with col_time:
            time_label = st.selectbox(
                "时间范围",
                options=["最近一天", "最近一周", "最近一月"],
                index=1,
                key="search_time",
            )
            time_map = {"最近一天": "d", "最近一周": "w", "最近一月": "m"}

        if st.button("🔍 搜索素材", type="primary"):
            with st.spinner("正在联网搜索相关素材..."):
                try:
                    resp = api_post(
                        "/api/sources/search",
                        json={
                            "query": search_query,
                            "max_results": max_results,
                            "time_range": time_map[time_label],
                            "search_type": "news" if search_type == "新闻" else "web",
                        },
                        timeout=30.0,
                    )
                    st.session_state.search_results = resp.json()["results"]
                except Exception as e:
                    st.error(f"搜索失败: {e}")

        # Display search results with checkboxes
        search_results = st.session_state.get("search_results", [])
        if search_results:
            st.markdown(f"**找到 {len(search_results)} 条结果，勾选后点击「抓取选中」：**")

            selected_urls = []
            for i, r in enumerate(search_results):
                checked = st.checkbox(
                    f"**{r['title']}**",
                    key=f"search_sel_{i}",
                    value=True,
                )
                st.caption(f"{r['snippet'][:120]}...  [{r['url'][:60]}...]")
                if checked:
                    selected_urls.append(r["url"])

            if st.button("📥 抓取选中素材", disabled=not selected_urls):
                _fetch_urls(selected_urls)

    # Show fetched materials
    st.divider()
    _show_materials()

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        if st.button("← 上一步", use_container_width=True):
            go_to_step(1)
            st.rerun()
    with col3:
        materials = st.session_state.get("materials", [])
        if st.button("下一步 →", disabled=not materials, use_container_width=True):
            go_to_step(3)
            st.rerun()


def _fetch_urls(urls: list):
    """Fetch content from a list of URLs."""
    with st.spinner(f"正在抓取 {len(urls)} 个链接的内容..."):
        try:
            resp = api_post(
                "/api/sources/fetch",
                json={"urls": urls},
                timeout=120.0,
            )
            data = resp.json()
            # Append to existing materials (avoid duplicates by URL)
            existing_urls = {m["url"] for m in st.session_state.get("materials", [])}
            new_materials = [m for m in data["materials"] if m["url"] not in existing_urls]
            st.session_state.materials = st.session_state.get("materials", []) + new_materials
            st.session_state.fetch_errors = data.get("errors", [])
            if new_materials:
                st.success(f"新增 {len(new_materials)} 篇素材")
            if data.get("errors"):
                for err in data["errors"]:
                    st.warning(f"抓取失败: {err}")
            st.rerun()
        except Exception as e:
            st.error(f"抓取失败: {e}")


def _show_materials():
    """Display fetched materials with option to remove."""
    materials = st.session_state.get("materials", [])
    if not materials:
        st.info("暂无素材，请通过上方提供链接或使用 AI 搜索。")
        return

    st.subheader(f"已获取素材 ({len(materials)} 篇)")
    to_remove = []
    for i, m in enumerate(materials):
        col_info, col_del = st.columns([9, 1])
        with col_info:
            with st.expander(f"📄 {m['title']} ({m['word_count']} 字)"):
                st.text(m["text"][:500] + ("..." if len(m["text"]) > 500 else ""))
        with col_del:
            if st.button("✕", key=f"rm_mat_{i}", help="移除此素材"):
                to_remove.append(i)

    if to_remove:
        st.session_state.materials = [
            m for i, m in enumerate(materials) if i not in to_remove
        ]
        st.rerun()
