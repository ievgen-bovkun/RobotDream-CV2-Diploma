from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.pipeline.orchestrator import PlaceholderPipelineOrchestrator
from app.services.metadata_service import build_placeholder_metadata
from app.ui.controls import render_sidebar_controls
from app.ui.state import initialize_session_state, reset_session_state
from app.ui.views import render_header, render_project_overview, render_preview_results


def main() -> None:
    st.set_page_config(
        page_title="Drone Tracking Demo",
        layout="wide",
    )

    initialize_session_state()
    render_header()

    config, actions = render_sidebar_controls()
    metadata = build_placeholder_metadata()

    if actions.reset_state:
        reset_session_state()
        st.rerun()

    render_project_overview(config=config, metadata=metadata)

    uploaded_video = st.file_uploader(
        "Upload prerecorded drone video",
        type=["mp4", "mov", "avi"],
        help="Real upload handling and metadata extraction will be enabled in Milestone 2.",
    )

    if uploaded_video is not None:
        st.success(
            "The file was received by the UI. Real validation, metadata extraction, and preview will be connected in Milestone 2."
        )
        st.write(
            {
                "filename": uploaded_video.name,
                "size_bytes": uploaded_video.size,
            }
        )
    else:
        st.info(
            "No video uploaded yet. The current build uses placeholder metadata so we can validate the app shell and pipeline contracts."
        )

    if actions.start_processing:
        orchestrator = PlaceholderPipelineOrchestrator()
        st.session_state.preview_frames = orchestrator.build_preview(
            metadata=metadata,
            config=config,
            max_processed_frames=6,
        )

    render_preview_results(st.session_state.preview_frames)


if __name__ == "__main__":
    main()
