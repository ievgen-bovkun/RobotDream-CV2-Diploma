from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from app.domain.config import ProcessingConfig
from app.domain.models import VideoMetadata
from app.pipeline.orchestrator import FramePreview


def render_header() -> None:
    st.title("Drone Detection, Approval, Tracking, and Guidance Demo")
    st.caption(
        "Milestone 1 foundation: a clean Streamlit shell with typed models, placeholder pipeline stages, and regression-safe scaffolding."
    )


def render_project_overview(config: ProcessingConfig, metadata: VideoMetadata) -> None:
    overview_col, metadata_col, notes_col = st.columns(3)

    with overview_col:
        st.subheader("Current Scope")
        st.write(
            {
                "milestone": "Milestone 1",
                "status": "Foundation in place",
                "next_target": "Video upload and metadata extraction",
            }
        )

    with metadata_col:
        st.subheader("Placeholder Metadata")
        st.write(asdict(metadata))

    with notes_col:
        st.subheader("Active Config")
        st.write(config.to_dict())

    st.info(
        "The preview below is deterministic placeholder behavior. It validates contracts and UI flow without pretending to be a real detector or tracker yet."
    )


def render_preview_results(preview_frames: list[FramePreview]) -> None:
    st.subheader("Pipeline Preview")

    if not preview_frames:
        st.write(
            "Click `Start Processing` to generate a placeholder end-to-end preview of detection, approval, tracking, and guidance data flow."
        )
        return

    st.success(
        "Preview generated. The first detection is auto-approved here only to exercise the contracts we will reuse in later milestones."
    )

    for preview in preview_frames:
        with st.expander(f"Frame {preview.frame_index}", expanded=preview.frame_index == preview_frames[0].frame_index):
            st.write("Events")
            for event in preview.events:
                st.write(f"- [{event.stage}] {event.message}")

            if preview.detections:
                st.write("Detections")
                st.write([asdict(detection) for detection in preview.detections])
            else:
                st.write("Detections: none")

            if preview.approved_target is not None:
                st.write("Approved Target")
                st.write(asdict(preview.approved_target))

            if preview.tracking is not None:
                st.write("Tracking")
                st.write(asdict(preview.tracking))

            if preview.guidance is not None:
                st.write("Guidance")
                st.write(asdict(preview.guidance))

            if preview.overlay_lines:
                st.write("Overlay Text")
                for line in preview.overlay_lines:
                    st.code(line)
