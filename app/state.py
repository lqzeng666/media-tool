"""Session state management for the Streamlit app."""

import streamlit as st


def init_state():
    """Initialize session state with default values."""
    defaults = {
        "current_step": 1,
        "topic": "",
        "urls_text": "",
        "materials": [],
        "fetch_errors": [],
        "outline": None,
        "ppt_bytes": None,
        "trending_topics": [],
        "search_results": [],
        "slide_images": None,
        "podcast_script": None,
        "podcast_audio": None,
        "video_project_dir": None,
        "xhs_cards": None,
        "xhs_images": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def go_to_step(step: int):
    st.session_state.current_step = step


def reset():
    for key in ["topic", "urls_text", "materials", "fetch_errors", "outline", "ppt_bytes",
                 "trending_topics", "search_results", "slide_images", "podcast_script",
                 "podcast_audio", "video_project_dir", "xhs_cards", "xhs_images"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.current_step = 1
