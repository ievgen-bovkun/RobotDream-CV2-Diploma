from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.domain.config import ProcessingConfig
from app.pipeline.orchestrator import PlaceholderPipelineOrchestrator
from app.services.metadata_service import build_placeholder_metadata
from app.services.metadata_service import extract_video_metadata
from app.pipeline.video_io import suggest_runtime_chunk_size, suggest_runtime_detection_interval
from app.ui.controls import render_detection_settings
from app.ui.state import (
    begin_preview_processing,
    finish_preview_processing,
    get_current_video,
    get_current_video_metadata,
    initialize_session_state,
    request_full_reset,
    request_video_pause,
    request_video_playback,
    reset_session_state,
    store_uploaded_video,
)
from app.ui.views import (
    render_header,
    render_operator_runtime_block,
    render_other_details,
    render_runtime_styles,
)


def _get_active_config() -> ProcessingConfig:
    config_dict = st.session_state.get("active_processing_config_dict")
    if isinstance(config_dict, dict):
        return ProcessingConfig(**config_dict)
    return ProcessingConfig()


def _start_incremental_processing(config: ProcessingConfig, metadata) -> None:
    effective_interval = suggest_runtime_detection_interval(
        source_fps=metadata.fps,
        requested_interval=config.frame_sampling_interval,
    )
    begin_preview_processing()
    st.session_state.preview_frames = []
    st.session_state.processing_config_dict = config.to_dict()
    st.session_state.processing_cursor_frame = 0
    st.session_state.processing_effective_interval = effective_interval
    st.session_state.processing_chunk_size = suggest_runtime_chunk_size(
        detection_interval=effective_interval,
    )
    st.session_state.processing_target = None
    st.session_state.processing_missed_detection_refreshes = 0
    st.session_state.processing_playback_started = False
    st.session_state.play_request_nonce = 0
    st.session_state.pause_request_nonce = 0


def _process_next_runtime_chunk(current_video: dict, metadata) -> None:
    if not st.session_state.get("is_processing_preview"):
        return

    video_path = current_video.get("path")
    if not video_path:
        finish_preview_processing()
        return

    config_dict = st.session_state.get("processing_config_dict")
    if not isinstance(config_dict, dict):
        finish_preview_processing()
        return

    base_config = ProcessingConfig(**config_dict)
    runtime_config = ProcessingConfig(
        **{
            **base_config.to_dict(),
            "frame_sampling_interval": int(
                st.session_state.get("processing_effective_interval", base_config.frame_sampling_interval)
            ),
        }
    )

    orchestrator = PlaceholderPipelineOrchestrator()
    result = orchestrator.build_preview_chunk_from_video_path(
        video_path=video_path,
        metadata=metadata,
        config=runtime_config,
        start_frame_index=int(st.session_state.get("processing_cursor_frame", 0)),
        max_frames=int(st.session_state.get("processing_chunk_size", runtime_config.frame_sampling_interval * 4)),
        filename=current_video.get("name"),
        mime_type=current_video.get("type"),
        approved_target=st.session_state.get("processing_target"),
        missed_detection_refreshes=int(st.session_state.get("processing_missed_detection_refreshes", 0)),
    )

    st.session_state.preview_frames.extend(result.previews)
    st.session_state.processing_cursor_frame = result.next_frame_index
    st.session_state.processing_target = result.approved_target
    st.session_state.processing_missed_detection_refreshes = result.missed_detection_refreshes

    if result.previews and not st.session_state.get("processing_playback_started", False):
        request_video_playback()
        st.session_state.processing_playback_started = True

    if result.completed:
        finish_preview_processing()


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

    @st.fragment(run_every=0.5)
    def runtime_fragment() -> None:
        current_video = get_current_video()
        metadata = get_current_video_metadata() or build_placeholder_metadata()

        if st.session_state.get("is_processing_preview") and current_video is not None:
            _process_next_runtime_chunk(current_video, metadata)

        pending_upload, actions = render_operator_runtime_block(
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
            st.rerun(scope="app")

        if actions.reset_state:
            request_full_reset()
            st.rerun(scope="app")

        if actions.tactical_pause:
            request_video_pause()
            st.rerun(scope="fragment")

        if actions.start_processing:
            if current_video is not None:
                _start_incremental_processing(_get_active_config(), metadata)
                _process_next_runtime_chunk(current_video, metadata)
                st.rerun(scope="fragment")
            else:
                begin_preview_processing()
                orchestrator = PlaceholderPipelineOrchestrator()
                st.session_state.preview_frames = orchestrator.build_preview(
                    metadata=metadata,
                    config=_get_active_config(),
                    max_processed_frames=None,
                )
                finish_preview_processing()
                st.rerun(scope="fragment")

    with runtime_container:
        runtime_fragment()

    with details_container:
        metadata = get_current_video_metadata() or build_placeholder_metadata()
        render_other_details(config=config, metadata=metadata)


if __name__ == "__main__":
    main()
