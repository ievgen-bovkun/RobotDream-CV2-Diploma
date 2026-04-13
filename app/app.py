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
    release_processing_session,
    request_full_reset,
    request_video_pause,
    request_video_playback,
    reset_session_state,
    store_uploaded_video,
)
from app.ui.views import (
    render_debug_preview_section,
    render_detection_log_panel,
    render_header,
    render_runtime_video_panel,
    render_other_details,
    render_runtime_styles,
)


def _get_active_config() -> ProcessingConfig:
    config_dict = st.session_state.get("active_processing_config_dict")
    if isinstance(config_dict, dict):
        return ProcessingConfig(**config_dict)
    return ProcessingConfig()


def _start_incremental_processing(config: ProcessingConfig, metadata) -> None:
    effective_refresh_interval = suggest_runtime_detection_interval(
        source_fps=metadata.fps,
        requested_interval=config.frame_sampling_interval,
    )
    current_video = get_current_video()
    if current_video is None or not current_video.get("path"):
        raise ValueError("No uploaded video is available for runtime processing")

    orchestrator = PlaceholderPipelineOrchestrator()
    processing_session = orchestrator.create_runtime_processing_session(
        video_path=str(current_video["path"]),
        config=config,
    )

    release_processing_session()
    begin_preview_processing()
    st.session_state.preview_frames = []
    st.session_state.processing_config_dict = config.to_dict()
    st.session_state.processing_cursor_frame = 0
    st.session_state.processing_effective_interval = effective_refresh_interval
    st.session_state.processing_chunk_size = suggest_runtime_chunk_size(
        detection_interval=effective_refresh_interval,
    )
    st.session_state.processing_target = None
    st.session_state.processing_missed_detection_refreshes = 0
    request_video_playback()
    st.session_state.processing_playback_started = True
    st.session_state.pause_request_nonce = 0
    st.session_state.processing_session = processing_session


def _process_next_runtime_chunk(current_video: dict, metadata) -> bool:
    if not st.session_state.get("is_processing_preview"):
        return False

    video_path = current_video.get("path")
    if not video_path:
        finish_preview_processing()
        return True

    config_dict = st.session_state.get("processing_config_dict")
    if not isinstance(config_dict, dict):
        finish_preview_processing()
        return True

    processing_session = st.session_state.get("processing_session")
    if processing_session is None:
        finish_preview_processing()
        return True

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
    result = orchestrator.build_preview_chunk_from_session(
        session=processing_session,
        metadata=metadata,
        config=runtime_config,
        start_frame_index=int(st.session_state.get("processing_cursor_frame", 0)),
        max_frames=int(
            st.session_state.get(
                "processing_chunk_size",
                suggest_runtime_chunk_size(
                    detection_interval=runtime_config.frame_sampling_interval,
                ),
            )
        ),
        approved_target=st.session_state.get("processing_target"),
        missed_detection_refreshes=int(st.session_state.get("processing_missed_detection_refreshes", 0)),
    )

    st.session_state.preview_frames.extend(result.previews)
    st.session_state.processing_cursor_frame = result.next_frame_index
    st.session_state.processing_target = result.approved_target
    st.session_state.processing_missed_detection_refreshes = result.missed_detection_refreshes

    if result.completed:
        finish_preview_processing()
        return True
    return False


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

    runtime_fragment_interval = 0.2 if st.session_state.get("is_processing_preview") else None

    @st.fragment(run_every=runtime_fragment_interval)
    def runtime_fragment(*, player_storage_key: str | None) -> None:
        current_video = get_current_video()
        metadata = get_current_video_metadata() or build_placeholder_metadata()
        render_detection_log_panel(
            preview_frames=st.session_state.preview_frames,
            metadata=metadata,
            is_processing_preview=bool(st.session_state.is_processing_preview),
            processing_cursor_frame=int(st.session_state.get("processing_cursor_frame", 0)),
            processing_total_frames=metadata.frame_count if current_video is not None else None,
            effective_interval=int(st.session_state.get("processing_effective_interval", 0)),
            debug_mode=bool(config.debug_mode),
            player_storage_key=player_storage_key,
        )

        if st.session_state.get("is_processing_preview") and current_video is not None:
            completed_now = _process_next_runtime_chunk(current_video, metadata)
            if completed_now:
                st.rerun(scope="app")

        render_debug_preview_section(
            preview_frames=st.session_state.preview_frames,
            player_storage_key=player_storage_key,
            is_processing_preview=bool(st.session_state.is_processing_preview),
            debug_mode=bool(config.debug_mode),
        )

    with runtime_container:
        with st.container(border=True):
            st.subheader("Operator Runtime Block")
            video_col, log_col = st.columns([3.15, 1.15], gap="large")

            with video_col:
                pending_upload, actions, player_storage_key = render_runtime_video_panel(
                    preview_frames=st.session_state.preview_frames,
                    is_processing_preview=bool(st.session_state.is_processing_preview),
                )

            with log_col:
                runtime_fragment(player_storage_key=player_storage_key)

        current_video = get_current_video()
        metadata = get_current_video_metadata() or build_placeholder_metadata()

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
            st.rerun(scope="app")

        if actions.start_processing:
            if current_video is not None:
                _start_incremental_processing(_get_active_config(), metadata)
                st.rerun(scope="app")
            else:
                begin_preview_processing()
                orchestrator = PlaceholderPipelineOrchestrator()
                st.session_state.preview_frames = orchestrator.build_preview(
                    metadata=metadata,
                    config=_get_active_config(),
                    max_processed_frames=None,
                )
                finish_preview_processing()
                st.rerun(scope="app")

    with details_container:
        metadata = get_current_video_metadata() or build_placeholder_metadata()
        render_other_details(config=config, metadata=metadata)


if __name__ == "__main__":
    main()
