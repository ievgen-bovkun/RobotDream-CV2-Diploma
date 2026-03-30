from __future__ import annotations

import streamlit as st


def _default_state() -> dict[str, object]:
    return {
        "preview_frames": [],
    }


def initialize_session_state() -> None:
    for key, value in _default_state().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state() -> None:
    for key, value in _default_state().items():
        st.session_state[key] = value
