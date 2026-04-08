"""Session state management for the Streamlit app."""

import streamlit as st

# Keys that should be saved/loaded for project persistence
SAVE_KEYS = [
    "current_step", "topic", "urls_text", "materials", "outline",
    "ppt_bytes", "slide_images", "podcast_script", "podcast_audio",
    "xhs_cards", "xhs_images", "comic_script", "comic_images", "video_bytes",
]


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
        "comic_script": None,
        "comic_images": None,
        "video_bytes": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def go_to_step(step: int):
    st.session_state.current_step = step


def reset():
    for key in SAVE_KEYS + ["fetch_errors", "trending_topics", "search_results", "video_project_dir"]:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.current_step = 1
