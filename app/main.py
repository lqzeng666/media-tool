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

        # Save / Load / History
        st.markdown("---")
        _render_sidebar_projects()

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


def _render_sidebar_projects():
    """Render save/load project controls in sidebar."""
    from app.http import api_post, api_get, api_delete

    st.caption("项目管理")

    # Save
    col_name, col_save = st.columns([3, 1])
    with col_name:
        proj_name = st.text_input("项目名", placeholder="给项目起个名字",
                                  key="save_proj_name", label_visibility="collapsed")
    with col_save:
        if st.button("保存", use_container_width=True, key="btn_save"):
            _save_current_project(proj_name)

    # Load history
    try:
        resp = api_get("/api/projects/list", timeout=5.0)
        projects = resp.json().get("projects", [])
    except Exception:
        projects = []

    if projects:
        with st.expander(f"历史项目 ({len(projects)})", expanded=False):
            for p in projects[:10]:
                outputs_str = "、".join(p.get("outputs", [])) or "无输出"
                col_info, col_load, col_del = st.columns([5, 1, 1])
                with col_info:
                    st.markdown(f"**{p.get('topic', '未命名')}**")
                    st.caption(f"{p.get('created', '')}　{outputs_str}")
                with col_load:
                    if st.button("载入", key=f"load_{p['id']}", use_container_width=True):
                        _load_project(p["id"])
                with col_del:
                    if st.button("删除", key=f"del_{p['id']}", use_container_width=True):
                        try:
                            api_delete(f"/api/projects/{p['id']}", timeout=5.0)
                        except Exception:
                            pass
                        st.rerun()


def _save_current_project(name: str = ""):
    """Save current session state as a project."""
    from app.http import api_post
    from app.state import SAVE_KEYS

    state_to_save = {}
    for key in SAVE_KEYS:
        val = st.session_state.get(key)
        if val is not None:
            # Convert bytes to base64 for JSON serialization
            if isinstance(val, bytes):
                import base64
                state_to_save[key] = base64.b64encode(val).decode()
            else:
                state_to_save[key] = val

    try:
        resp = api_post(
            "/api/projects/save",
            json={"state": state_to_save, "name": name or st.session_state.get("topic", "")},
            timeout=10.0,
        )
        st.sidebar.success("已保存")
    except Exception as e:
        st.sidebar.error(f"保存失败: {e}")


def _load_project(project_id: str):
    """Load a project into session state."""
    from app.http import api_get

    try:
        resp = api_get(f"/api/projects/load/{project_id}", timeout=10.0)
        state = resp.json().get("state", {})
        for key, val in state.items():
            st.session_state[key] = val
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"载入失败: {e}")


if __name__ == "__main__":
    run()
