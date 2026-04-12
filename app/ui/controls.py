from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from app.domain.config import ProcessingConfig, SUPPORTED_CAMERA_PROFILES, get_camera_profile_preset


@dataclass(slots=True, frozen=True)
class UiActions:
    start_processing: bool
    reset_state: bool
    tactical_pause: bool = False


def _format_camera_profile(camera_profile: str) -> str:
    return "Daylight RGB" if camera_profile == "daylight" else "Thermal"


def render_detection_settings() -> ProcessingConfig:
    defaults = ProcessingConfig()

    with st.expander("Detection Settings", expanded=True):
        st.caption(
            "Tune the runtime thresholding and output behavior here. These settings stay wired to the typed config model."
        )

        selected_camera_profile = st.segmented_control(
            "Camera profile",
            options=list(SUPPORTED_CAMERA_PROFILES),
            default=defaults.camera_profile,
            format_func=_format_camera_profile,
            width="stretch",
            help="Switch between daylight RGB and thermal presets so detector backends start with a better baseline.",
        )
        camera_profile = str(selected_camera_profile or defaults.camera_profile)
        profile_preset = get_camera_profile_preset(camera_profile)
        st.caption(
            "Preset detector backend hints: "
            f"imgsz={profile_preset['input_size']}, "
            f"nms_iou={profile_preset['nms_iou_threshold']}, "
            f"max_det={profile_preset['max_detections']}, "
            f"prompt_profile={len(profile_preset['prompt_terms'])} terms."
        )

        top_row = st.columns(2)
        detection_threshold = top_row[0].slider(
            "Detection confidence threshold",
            min_value=0.1,
            max_value=1.0,
            value=float(defaults.detection_threshold),
            step=0.05,
        )
        frame_sampling_interval = top_row[1].number_input(
            "Frame sampling interval",
            min_value=1,
            max_value=60,
            value=int(defaults.frame_sampling_interval),
            step=1,
            help="Run detector on every Nth frame and use tracking on the frames in between.",
        )
        mid_row = st.columns(2)
        tracker_max_missed_refreshes = mid_row[0].number_input(
            "Tracker hold after missed detections",
            min_value=0,
            max_value=12,
            value=int(defaults.tracker_max_missed_refreshes),
            step=1,
            help="Keep the current track alive for this many detector refresh misses before resetting it.",
        )

        bottom_row = st.columns(3)
        save_output_video = bottom_row[0].checkbox("Save annotated video", value=False)
        save_logs = bottom_row[1].checkbox("Save structured logs", value=True)
        debug_mode = bottom_row[2].checkbox("Debug mode", value=True)

    config = ProcessingConfig(
        camera_profile=camera_profile,
        detection_threshold=detection_threshold,
        frame_sampling_interval=int(frame_sampling_interval),
        tracker_max_missed_refreshes=int(tracker_max_missed_refreshes),
        save_output_video=save_output_video,
        save_logs=save_logs,
        debug_mode=debug_mode,
    )
    config.validate()
    return config
