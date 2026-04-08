"""Media Tool - 多模态资讯展示工具"""

import sys
from pathlib import Path

# Ensure project root is in sys.path (fixes Streamlit's path handling in Docker)
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.state import init_state

st.set_page_config(
    page_title="Media Tool",
    page_icon="📰",
    layout="wide",
)

init_state()

# Sidebar
with st.sidebar:
    st.title("📰 Media Tool")
    st.caption("多模态资讯展示工具")
    st.divider()

    steps = ["选择主题", "提供素材", "结构化内容", "生成文稿"]
    for i, name in enumerate(steps, 1):
        if i == st.session_state.current_step:
            st.markdown(f"**→ 步骤 {i}: {name}**")
        elif i < st.session_state.current_step:
            st.markdown(f"✅ 步骤 {i}: {name}")
        else:
            st.markdown(f"○ 步骤 {i}: {name}")

    st.divider()
    if st.session_state.topic:
        st.markdown(f"**主题:** {st.session_state.topic}")
    if st.session_state.materials:
        st.markdown(f"**素材:** {len(st.session_state.materials)} 篇")

# Main content - render current step
step = st.session_state.current_step

if step == 1:
    from app.components.topic_selector import render
    render()
elif step == 2:
    from app.components.source_manager import render
    render()
elif step == 3:
    from app.components.outline_editor import render
    render()
elif step == 4:
    from app.components.visual_preview import render
    render()
