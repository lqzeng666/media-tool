"""Media Tool - 多模态资讯展示工具"""

import streamlit as st

from app.state import init_state

CUSTOM_CSS = """
<style>
    /* 整体风格 */
    .stApp { background-color: #FAFAF9; }
    section[data-testid="stSidebar"] {
        background-color: #F5F3EF;
        border-right: 1px solid #E8E4DE;
    }
    /* 侧边栏标题 */
    section[data-testid="stSidebar"] h1 {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        color: #2C2C2C !important;
        letter-spacing: 0.5px;
    }
    /* 步骤指示器 */
    .step-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        font-size: 0.9rem;
        transition: all 0.2s;
    }
    .step-active {
        background: #2C2C2C;
        color: #FFFFFF !important;
        font-weight: 600;
    }
    .step-done {
        color: #8B8680;
        text-decoration: line-through;
    }
    .step-pending {
        color: #B5B0A8;
    }
    /* 主内容区 */
    .main .block-container {
        max-width: 960px;
        padding-top: 2rem;
    }
    /* 按钮 */
    .stButton > button[kind="primary"] {
        background-color: #2C2C2C !important;
        border: none !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        border-color: #D4D0C8 !important;
    }
    /* 输入框 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px !important;
        border-color: #D4D0C8 !important;
    }
    /* 分割线 */
    hr { border-color: #E8E4DE !important; }
    /* Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-size: 0.9rem;
    }
    /* 页面标题 */
    h1, h2 {
        color: #2C2C2C !important;
        font-weight: 600 !important;
    }
    h3 { color: #4A4A4A !important; }
</style>
"""


def run():
    st.set_page_config(
        page_title="Media Tool",
        page_icon="◆",
        layout="wide",
    )

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_state()

    # Sidebar
    with st.sidebar:
        st.markdown("#### ◆ Media Tool")
        st.caption("多模态资讯展示工具")
        st.markdown("---")

        steps = [
            "选择主题",
            "勾选信息",
            "结构化提取",
            "多模态内容生产",
        ]
        for i, name in enumerate(steps, 1):
            if i == st.session_state.current_step:
                st.markdown(
                    f'<div class="step-item step-active">● 步骤{i}  {name}</div>',
                    unsafe_allow_html=True,
                )
            elif i < st.session_state.current_step:
                st.markdown(
                    f'<div class="step-item step-done">✓ 步骤{i}  {name}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="step-item step-pending">○ 步骤{i}  {name}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")
        if st.session_state.topic:
            st.markdown(f"**主题**　{st.session_state.topic}")
        if st.session_state.materials:
            st.markdown(f"**素材**　{len(st.session_state.materials)} 篇")

    # Main content
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


if __name__ == "__main__":
    run()
