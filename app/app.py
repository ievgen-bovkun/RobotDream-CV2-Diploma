from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.pipeline.orchestrator import PlaceholderPipelineOrchestrator
from app.services.metadata_service import build_placeholder_metadata
from app.services.metadata_service import extract_video_metadata
from app.ui.controls import render_detection_settings
from app.ui.state import (
    begin_preview_processing,
    finish_preview_processing,
    get_current_video,
    get_current_video_metadata,
    initialize_session_state,
    reset_session_state,
    store_uploaded_video,
)
from app.ui.views import (
    render_header,
    render_operator_runtime_block,
    render_other_details,
    render_runtime_styles,
)


def main() -> None:
    st.set_page_config(
        page_title="Drone Tracking Demo",
        layout="wide",
    )

    initialize_session_state()
    if st.session_state.get("pending_full_reset"):
        reset_session_state()
    render_runtime_styles()
    render_header()

    runtime_container = st.container()
    settings_container = st.container()
    details_container = st.container()

    with settings_container:
        config = render_detection_settings()
        st.session_state.active_processing_config_dict = config.to_dict()

    with runtime_container:
        current_video = get_current_video()
        metadata = get_current_video_metadata() or build_placeholder_metadata()

        pending_upload, _actions = render_operator_runtime_block(
            preview_frames=st.session_state.preview_frames,
            metadata=metadata,
            is_processing_preview=bool(st.session_state.is_processing_preview),
            processing_cursor_frame=int(st.session_state.get("processing_cursor_frame", 0)),
            processing_total_frames=metadata.frame_count if current_video is not None else None,
            effective_interval=int(st.session_state.get("processing_effective_interval", 0)),
        )

        if pending_upload is not None:
            uploaded_bytes = pending_upload.getvalue()
            uploaded_metadata = extract_video_metadata(
                video_bytes=uploaded_bytes,
                filename=pending_upload.name,
                mime_type=pending_upload.type,
            )
            store_uploaded_video(
                name=pending_upload.name,
                mime_type=pending_upload.type or "video/mp4",
                size=pending_upload.size,
                video_bytes=uploaded_bytes,
                metadata=uploaded_metadata,
            )

            begin_preview_processing()
            st.session_state.processing_cursor_frame = 0
            st.session_state.processing_effective_interval = int(config.frame_sampling_interval)
            try:
                with st.spinner("Processing uploaded video and preparing tracking preview..."):
                    orchestrator = PlaceholderPipelineOrchestrator()
                    st.session_state.preview_frames = orchestrator.build_preview_from_video(
                        video_bytes=uploaded_bytes,
                        metadata=uploaded_metadata,
                        config=config,
                        filename=pending_upload.name,
                        mime_type=pending_upload.type,
                    )
                    st.session_state.processing_cursor_frame = uploaded_metadata.frame_count
            finally:
                finish_preview_processing()

            st.rerun()

    with details_container:
        metadata = get_current_video_metadata() or build_placeholder_metadata()
        render_other_details(config=config, metadata=metadata)


if __name__ == "__main__":
    main()
