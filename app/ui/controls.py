from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.domain.config import ProcessingConfig


@dataclass(slots=True, frozen=True)
class UiActions:
    start_processing: bool
    reset_state: bool


def render_sidebar_controls() -> tuple[ProcessingConfig, UiActions]:
    st.sidebar.header("Operator Controls")
    st.sidebar.caption(
        "These controls are already connected to the typed config model so later milestones can reuse the same interface."
    )

    detection_threshold = st.sidebar.slider(
        "Detection confidence threshold",
        min_value=0.1,
        max_value=1.0,
        value=0.5,
        step=0.05,
    )
    frame_sampling_interval = st.sidebar.number_input(
        "Frame sampling interval",
        min_value=1,
        max_value=60,
        value=1,
        step=1,
    )
    save_output_video = st.sidebar.checkbox("Save annotated video", value=False)
    save_logs = st.sidebar.checkbox("Save structured logs", value=True)
    debug_mode = st.sidebar.checkbox("Debug mode", value=True)

    st.sidebar.divider()
    start_processing = st.sidebar.button("Start Processing", type="primary")
    reset_state = st.sidebar.button("Reset State")

    config = ProcessingConfig(
        detection_threshold=detection_threshold,
        frame_sampling_interval=int(frame_sampling_interval),
        save_output_video=save_output_video,
        save_logs=save_logs,
        debug_mode=debug_mode,
    )
    config.validate()

    return config, UiActions(
        start_processing=start_processing,
        reset_state=reset_state,
    )
